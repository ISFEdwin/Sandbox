"""Air-ventilation screening by frontal area density, against published HSK data.

## Why this is not a wind tunnel

It is not, and it does not pretend to be. A wind tunnel or a CFD solve is the
published way to get a velocity ratio; this module does geometry.

What it computes is **frontal area density** (FAD) per wind direction: the total
building face presented perpendicular to the wind, over the site area. Low FAD
means the wind can penetrate; high FAD means the site is sheltered from that
direction. It needs nothing but the building footprints and heights, which the
project already has for all 396 surveyed footprints (Open3dhk 3D Tiles fused
with Overture Maps; the count is published in
``data/rasters/buildings_meta.json``). An earlier version of this note said
2,639, which was the envelope count of the tile-only city model the footprints
were derived from -- 396 merged buildings plus the tiles that did not survive
the merge.

**FAD is not a velocity ratio and the two are never interchanged.** VR is
Vp / V-inf and comes from a wind tunnel or CFD. The relationship between the two
depends on upstream wind profile, roughness and flow separation, none of which we
model. So this module reports FAD in its own units, and reports the published
HSK velocity ratios beside it purely as a *reference range* to read against.

## Where the wind directions come from

The one published fact this uses: the AVRG73 air ventilation assessment for
Hung Shui Kiu Area 13 states the dominant wind directions for the site are **NE,
ENE and E, together 40.8% of wind frequency**. No frequency is invented for any
other direction, and every direction is still computed and reported so the shape
of the site is visible even where the frequency is unknown.

## There is no threshold, and that is the finding

An earlier version of this note said the pass/fail bands "have not been
extracted". They were never there to extract. The policy document behind Hong
Kong's own guidance -- Ng & Cheng, *Policies and technical guidelines for urban
planning of high-density cities - air ventilation assessment (AVA) of Hong Kong*,
Building and Environment 44 (2009) 1478-1488 -- states:

    "A design having a higher velocity ratio would be considered as a better
    design than one having a lower velocity ratio. At this stage, only the better
    design option is known, but whether the better design option meets a standard
    cannot be known."

It does publish *empirical reference values*, which are not criteria: velocity
ratios of **0.3** near the waterfront and in open spaces, and **0.05-0.1** in
streets and congested urban spaces. Those live in
:mod:`app.services.design_metrics` as ``VR_OPEN_SPACE`` and
``VR_CONGESTED_STREET``.

**So this module still asserts no threshold, but now for the opposite reason:**
not because we could not find one, but because the guidance says none exists yet.
That is a stronger position than the old note claimed, and it is cited.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings

# The geometry primitives are defined once, in design_metrics, and re-exported
# here so this module's callers and tests are unaffected. Two copies of
# projected_width_m existed between these modules, and two implementations of one
# formula is how a screening starts disagreeing with itself -- which is the one
# failure this module exists to rule out.
from app.services.design_metrics import (  # noqa: F401
    CARDINALS,
    GROUND_LEVEL_BAND_M,
    Footprint,
    _TRAVEL,
    cell_fad,
    directional_exposure,
    frontal_area_density as design_frontal_area_density,
    projected_width_m,
    rasterise_height,
)

# scipy is used for exactly one thing -- the least-cost-path corridors below. It
# is imported defensively so that a host where `scipy.sparse` will not load (the
# 1.15.3 `_propack`/dyld failure the requirements pin fixes) gets a loud
# RuntimeError rather than a silently degraded corridor. A degraded corridor is a
# wrong corridor, and this module would rather fail than draw one.
try:  # pragma: no cover - exercised by the import-failure branch, not the happy path
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
except Exception:  # noqa: BLE001
    csr_matrix = None  # type: ignore[assignment]
    dijkstra = None  # type: ignore[assignment]

REFERENCE_PATH = "reference/hsk_ava_reference.json"
SITE_WIND_PATH = "reference/hsk_site_wind.json"

# A stated screening weight on the land-class raster. It is not a roughness
# length (z0), not a speed, and not folded into frontal area density. Vegetated
# classes slow the near-ground reading the corridor cost sees; paved, water and
# tank do not. The numbers are a convention so the term is visible beside
# ``1 + cellFAD``, and the sidecar says so.
ROUGHNESS_PENALTY: dict[str, float] = {
    "green": 0.35,
    "wetland": 0.20,
    "floodable": 0.20,
    "bare": 0.05,
    "water": 0.0,
    "paved": 0.0,
    "tank": 0.0,
}

GEOMETRIC_EFFECT_STATUS = "GEOMETRIC_EFFECT_NOT_A_SPEED"
GEOMETRIC_EFFECT_METHOD = (
    "Tags on corridor segments from the height raster only. "
    "Venturi acceleration: the path cell is open and both cells perpendicular "
    "to the travel direction contain massing. "
    "downwash risk: along the path, the upwind cell is taller than the "
    "downwind cell and the upwind cell contains massing. "
    "corner acceleration: a massing cell beside the path has two perpendicular "
    "open neighbours (an exposed corner)."
)
GEOMETRIC_EFFECT_LIMITATION = (
    "Geometry labels, not speeds. No velocity, no turbulence, no Lawson / NEN / "
    "Davenport threshold, and no pass/fail. A label names a pattern on the "
    "massing raster. It does not say the wind accelerated."
)

# The eight principal wind directions the corridor endpoint defaults to.
PRINCIPAL_DIRECTIONS: tuple[str, ...] = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

# Which grid edge a wind FROM each direction enters through (Stage 5c's
# arrangement half). Meteorological naming: a north-easterly wind comes FROM the
# north-east, so it crosses the district's north-eastern edge moving
# south-westward. This table is presentation -- the entry edge is also derivable
# from the path's first cell -- but stating it per direction keeps a NE reading
# and a SW reading from being interchangeable in the response. ONE table, in the
# same convention as ``_TRAVEL``; a second travel table elsewhere is exactly the
# NE/SW-swap drift the canonical-table rule exists to prevent.
ENTRY_EDGES: dict[str, str] = {
    "N": "north", "NE": "north-east", "E": "east", "SE": "south-east",
    "S": "south", "SW": "south-west", "W": "west", "NW": "north-west",
}

# Meteorological convention: the direction a wind comes FROM. Named explicitly
# because "wind from the east" and "wind towards the east" differ by 180 degrees,
# and getting that backwards points every building at the wrong side.

# M_PER_DEG_LAT used to be defined here and is now unused in this module: the one
# function that needed it moved to design_metrics. Left behind as a second source
# of a physical constant is exactly the drift this consolidation removed.


def load_reference() -> dict[str, Any] | None:
    path: Path = settings.data_dir / REFERENCE_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def frontal_area_density(
    footprints: list[dict[str, Any]],
    site_area_m2: float,
    directions: dict[str, float] | None = None,
) -> dict[str, Any]:
    """FAD per wind direction, from the canonical implementation.

    ``footprints`` items need ``widthM``, ``depthM`` and ``heightM``, and may
    carry ``bearingDeg``, ``sideAM`` and ``sideBM``. ``widthM`` / ``depthM``
    stay the geographic bounding box. The side fields are the principal-axis
    lengths the formula rotates; they are omitted (0) for an axis-aligned ring.
    This is a **thin adapter** over
    :func:`app.services.design_metrics.frontal_area_density`, which is the
    canonical typed version.

    It used to be a second, independent implementation of the same formula. Two
    copies of one geometric calculation is how a screening starts disagreeing with
    itself, and it had already drifted once: when footprints gained an orientation
    the canonical version learned to use it and this one silently did not, so the
    two endpoints would have reported different frontal areas for the same scheme.
    One definition, one adapter.
    """
    typed = [
        Footprint(
            0.0, 0.0,
            float(fp["widthM"]), float(fp["depthM"]), float(fp["heightM"]),
            bearing_deg=float(fp.get("bearingDeg", fp.get("bearing_deg", 0.0)) or 0.0),
            side_a_m=float(fp.get("sideAM", fp.get("side_a_m", 0.0)) or 0.0),
            side_b_m=float(fp.get("sideBM", fp.get("side_b_m", 0.0)) or 0.0),
        )
        for fp in footprints
    ]
    return design_frontal_area_density(typed, site_area_m2,
                                       directions or CARDINALS)


def ventilation_screening(
    footprints: list[dict[str, Any]],
    site_area_m2: float,
    prevailing: list[str] | None = None,
    combined_frequency_percent: float | None = None,
) -> dict[str, Any]:
    """FAD screening, with the published prevailing directions weighted.

    ``prevailing`` defaults to the AVRG73 directions for Hung Shui Kiu. Only those
    directions carry a frequency; every other direction is computed but reported
    without one, because inventing a wind rose is how a screening turns into a
    fiction.
    """
    dirs = CARDINALS
    fad = frontal_area_density(footprints, site_area_m2, dirs)
    if "error" in fad:
        return fad

    wind = prevailing or ["NE", "ENE", "E"]
    known = [d for d in wind if d in fad["byDirection"]]
    prevailing_fad = (sum(fad["byDirection"][d] for d in known) / len(known)
                      if known else None)
    least = min(known, key=lambda d: fad["byDirection"][d]) if known else None

    return {
        "metric": "frontal area density",
        "units": "dimensionless (projected frontal area / site area)",
        "siteAreaM2": round(site_area_m2, 1),
        "buildingCount": len(footprints),
        "frontalAreaDensity": fad,
        "prevailingDirections": wind,
        "combinedFrequencyPercent": combined_frequency_percent,
        "prevailingMeanFad": (None if prevailing_fad is None
                               else round(prevailing_fad, 4)),
        "leastExposedPrevailingDirection": least,
        "limitation": (
            "The closed form is symmetric under a 180-degree reversal, for any "
            "footprint bearing. Each footprint contributes a*|sin(φ−θ)| + "
            "b*|cos(φ−θ)|, which is even in (φ−θ), so a north-easterly and a "
            "south-westerly always sum to the same total. Orientation does "
            "separate NE from E for a non-square footprint, and a rotated ring "
            "can separate NE from SE; it cannot separate NE from SW. That is "
            "exact geometry -- a convex body presents the same face to wind "
            "from either side -- not a missing bearing. This screening "
            "compares schemes and compares axes, but it cannot distinguish a "
            "north-easterly from a south-westerly. Distinguishing them needs "
            "the arrangement, which directional_exposure reads by marching "
            "rays over the height raster rather than by summing footprint "
            "contributions."
        ),
        "note": (
            "Low frontal area density means the wind can penetrate the site; "
            "high means it is sheltered from that direction. This is geometry, "
            "not flow. It is NOT a velocity ratio and no pass/fail threshold is "
            "asserted -- the bands are in Technical Circular 1/06 and its Annex A "
            "Technical Guide, which we have not extracted. Read it as a shape "
            "indicator for comparing schemes, never as an assessment."
        ),
    }


# --------------------------------------------------------------------------- #
# Stage 5b -- least-cost-path wind corridors
# --------------------------------------------------------------------------- #


def _edge_arrays(grids: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The 8-neighbour graph as ``(src, dst, step_cells, indptr)``, built once.

    ``src``/``dst`` are flat cell indices, ``step_cells`` is the step length in
    CELLS (1 for a cardinal neighbour, sqrt(2) for a diagonal), and ``indptr`` is
    the CSR row pointer. The arrays are sorted by ``src`` so each direction's edge
    weights drop straight into a CSR without re-sorting -- the "build the
    structure once" the design asks for.
    """
    rows, cols = grids.rows, grids.cols
    rr, cc = np.meshgrid(np.arange(rows, dtype=np.int64),
                         np.arange(cols, dtype=np.int64), indexing="ij")
    srcs, dsts, steps = [], [], []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r2, c2 = rr + dr, cc + dc
            ok = (r2 >= 0) & (r2 < rows) & (c2 >= 0) & (c2 < cols)
            srcs.append((rr[ok] * cols + cc[ok]).astype(np.int64))
            dsts.append((r2[ok] * cols + c2[ok]).astype(np.int64))
            steps.append(np.full(int(ok.sum()), math.hypot(dr, dc), dtype=np.float64))
    src = np.concatenate(srcs)
    dst = np.concatenate(dsts)
    step_cells = np.concatenate(steps)
    order = np.lexsort((dst, src))
    src, dst, step_cells = src[order], dst[order], step_cells[order]
    counts = np.bincount(src, minlength=rows * cols)
    indptr = np.zeros(rows * cols + 1, dtype=np.int64)
    np.cumsum(counts, out=indptr[1:])
    return src, dst, step_cells, indptr


def ground_level_fad(footprints: list[Footprint], grids: Any,
                     bearing_deg: float) -> np.ndarray:
    """Frontal area density of the pedestrian band only.

    Height is clipped to :data:`GROUND_LEVEL_BAND_M`. A footprint marked
    ``ground_floor_gap`` contributes nothing here and still contributes its
    full height to :func:`cell_fad`. The two rasters are not added into one
    FAD figure.
    """
    clipped: list[Footprint] = []
    for f in footprints:
        if f.ground_floor_gap or f.height_m <= 0:
            continue
        clipped.append(Footprint(
            f.lon, f.lat, f.width_m, f.depth_m,
            min(float(f.height_m), GROUND_LEVEL_BAND_M),
            bearing_deg=f.bearing_deg,
            side_a_m=f.side_a_m,
            side_b_m=f.side_b_m,
        ))
    if not clipped:
        return np.zeros((grids.rows, grids.cols), dtype=np.float32)
    return cell_fad(clipped, grids, bearing_deg)


def roughness_penalty(grids: Any) -> np.ndarray:
    """Per-cell screening weight from the land-class raster, or zeros.

    Missing ``land_class`` (a synthetic grid, a test double) is zeros, not a
    guessed cover. The weights are :data:`ROUGHNESS_PENALTY`.
    """
    rows, cols = int(grids.rows), int(grids.cols)
    land = getattr(grids, "land_class", None)
    if land is None:
        return np.zeros((rows, cols), dtype=np.float64)
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from _overlay_common import LAND_CLASSES

    penalty = np.zeros(land.shape, dtype=np.float64)
    for name, weight in ROUGHNESS_PENALTY.items():
        if name not in LAND_CLASSES or weight == 0.0:
            continue
        penalty[land == LAND_CLASSES.index(name)] = weight
    return penalty


def geometric_effects(path: list[list[int]], height: np.ndarray,
                      direction: str) -> list[dict[str, Any]]:
    """Pattern tags along one corridor. No speeds and no numeric cutoff.

    A cell is "open" when its height is 0 and "massing" when it is not. The
    only comparisons are those two states and which of two heights is larger.
    """
    if direction not in _TRAVEL or len(path) < 2:
        return []
    dr, dc = _TRAVEL[direction]
    rows, cols = height.shape

    def at(r: int, c: int) -> float:
        if r < 0 or c < 0 or r >= rows or c >= cols:
            return 0.0
        return float(height[r, c])

    out: list[dict[str, Any]] = []
    for i, (r, c) in enumerate(path):
        labels: list[str] = []
        if at(r, c) == 0.0 and at(r + dc, c - dr) > 0.0 and at(r - dc, c + dr) > 0.0:
            labels.append("Venturi acceleration")
        if i + 1 < len(path):
            r2, c2 = path[i + 1]
            if at(r, c) > at(r2, c2) and at(r, c) > 0.0:
                labels.append("downwash risk")
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if at(nr, nc) <= 0.0:
                continue
            # An exposed corner: two perpendicular neighbours of the massing
            # cell are open. The path merely has to be beside that cell.
            open_n = at(nr - 1, nc) == 0.0
            open_s = at(nr + 1, nc) == 0.0
            open_w = at(nr, nc - 1) == 0.0
            open_e = at(nr, nc + 1) == 0.0
            if (open_n or open_s) and (open_e or open_w):
                labels.append("corner acceleration")
                break
        if labels:
            out.append({"row": int(r), "col": int(c), "labels": labels})
    return out


def _term_sidecars() -> dict[str, Any]:
    """One sidecar per cost term. They are not combined into a score."""
    return {
        "cellFad": {
            "status": "FAD_IS_NOT_A_VELOCITY_RATIO",
            "method": "cost term = 1 + cellFAD, from the canonical projected width",
            "limitation": (
                "Frontal area density is dimensionless area per area. It is not "
                "a velocity ratio. The term stays 1 + cellFAD; the reciprocal "
                "written in the design text would route the corridor through "
                "the most blocked cells."
            ),
        },
        "groundLevelOpenness": {
            "status": "GROUND_OPENNESS_NOT_A_VELOCITY_RATIO",
            "method": (
                f"A second frontal-area raster using only the height within "
                f"{GROUND_LEVEL_BAND_M:.0f} m. A groundFloorGap footprint is "
                "omitted from this raster and kept in cellFAD."
            ),
            "limitation": (
                "Pedestrian-band blockage, reported on its own. It is not added "
                "into the published FAD, it is not a speed, and a gap is only "
                "as open as the footprint property says. The massing model has "
                "no separate podium solid."
            ),
        },
        "roughnessPenalty": {
            "status": "ROUGHNESS_PENALTY_NOT_A_ROUGHNESS_LENGTH",
            "method": (
                "A stated weight on the ESA WorldCover land-class raster "
                "(landclass via grids.land_class). Green 0.35, wetland and "
                "floodable 0.20, bare 0.05, water paved and tank 0."
            ),
            "limitation": (
                "Not a measured aerodynamic roughness length, not a speed, and "
                "not a change to FAD. The weights are a screening convention so "
                "vegetation is visible on the corridor cost. A grid with no "
                "land class contributes zero."
            ),
        },
    }


def load_site_wind() -> dict[str, Any] | None:
    """The PlanD site-wind file, or None when it has not been written."""
    path: Path = settings.data_dir / SITE_WIND_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def site_direction_frequencies() -> dict[str, float]:
    """Annual occurrence at 500 m from the verified site-wind file.

    Raises ``ValueError`` when the file is missing or not verified. Callers
    turn that into a 422. Nothing here estimates a missing rose.
    """
    doc = load_site_wind()
    if not doc or not doc.get("verified"):
        raise ValueError(
            "hsk_site_wind.json is missing or not verified; refusing to "
            "invent direction weights")
    seasons = doc.get("seasons") or {}
    annual = seasons.get("annual") or {}
    level = (annual.get("heightsM") or {}).get("500") or {}
    freq = level.get("frequencyByDirection") or {}
    out: dict[str, float] = {}
    for name in CARDINALS:
        if name not in freq:
            raise ValueError(
                f"site-wind file has no annual 500 m frequency for {name}")
        out[name] = float(freq[name])
    return out


def _direction_weight_block(
    computed: list[str],
    weights: dict[str, float] | None,
    source: str,
) -> dict[str, Any]:
    """Which corridor is the headline, and the weight fact behind that choice.

    Weights never enter the Dijkstra cost. Putting a frequency into the cost
    would be an invented coupling of a wind rose and a geometric surface.
    """
    ref = load_reference() or {}
    wind = ref.get("windRegime") or {}
    prevailing = list(wind.get("prevailing") or ["NE", "ENE", "E"])
    if weights:
        ranked = [name for name in computed if name in weights]
        selected = max(ranked, key=lambda name: (weights[name], -computed.index(name))) if ranked else (computed[0] if computed else None)
        note = (
            "Caller-supplied weights select the headline direction among the "
            "corridors that were actually marched. They are not a measured "
            "wind rose unless source is the PlanD file, and they are not "
            "applied to the cell cost."
        )
        if source.startswith("PlanD"):
            note = (
                "Headline direction is the highest annual occurrence at 500 m "
                "among the marched corridors, from the verified PlanD cell. "
                "ENE has a frequency and no travel vector, so it is not "
                "marched. The weights are not applied to the cell cost."
            )
    else:
        selected = next((name for name in ("NE", "E") if name in computed), None)
        if selected is None and computed:
            selected = computed[0]
        weights = None
        source = "AVRG73"
        note = (
            "The default is the AVRG73 fact: NE, ENE and E together, one "
            "combined frequency. That number is not split across the three "
            "directions. The headline stays NE when it was marched, because "
            "NE is the first prevailing direction with a travel vector. ENE "
            "is in the published group and is not marched."
        )
    return {
        "source": source,
        "url": (ref.get("source") or {}).get("url"),
        "prevailing": prevailing,
        "combinedFrequencyPercent": wind.get("combinedFrequencyPercent"),
        "perDirection": weights,
        "selectedDirection": selected,
        "canonicalDirections": list(CARDINALS),
        "status": "DIRECTION_WEIGHT_NOT_A_COST",
        "method": (
            "Select the headline corridor by weight. Default source is the "
            "AVRG73 combined frequency. An explicit directionWeights query, "
            "or the token 'site', replaces the selection only."
        ),
        "limitation": note,
    }


def least_cost_corridors(
    footprints: list[Footprint],
    grids: Any,
    directions: dict[str, float] | None = None,
    *,
    step_m: float | None = None,
    direction_weights: dict[str, float] | None = None,
    weight_source: str = "AVRG73",
) -> dict[str, Any]:
    """Per-direction least-cost corridor across the frontal-area cost surface.

    The corridor is the cheapest 8-neighbour route from the edge the wind enters
    to the edge it leaves. ``cell_fad`` gives the per-cell blockage; the cost of
    standing in a cell is ``1 + cellFAD``, so the least-cost route runs through
    the OPENEST ground -- which is what a ventilation corridor physically is.

    **A note on the cost formula.** The design and PRD write the surface as
    ``1/(1+FAD)``. Taken literally that INVERTS the selection: a least-cost path
    minimises the sum of ``1/(1+FAD)``, which is smallest where FAD is largest, so
    the corridor would route through the most blocked cells and the design's own
    acceptance test -- "one low-FAD lane returns a corridor along the lane" --
    would fail. The reciprocal is the physically meaningful form and is what ships;
    it is recorded here because the difference is a sign, not a typo.

    The graph is built once; per direction the edge weights are recomputed and
    ``scipy.sparse.csgraph.dijkstra`` is run with every upwind-edge cell as a
    multi-source. Deterministic: no RNG, no wall-clock. Uses
    :func:`app.services.design_metrics.cell_fad` for the cost surface, so there is
    no second geometry.

    Raises ``RuntimeError('scipy.sparse.csgraph unavailable')`` if the import
    failed, rather than silently degrading -- a degraded corridor is a wrong one.
    """
    if dijkstra is None or csr_matrix is None:  # pragma: no cover
        raise RuntimeError("scipy.sparse.csgraph unavailable")

    dirs = directions or {name: CARDINALS[name] for name in PRINCIPAL_DIRECTIONS}
    for name in dirs:
        if name not in CARDINALS or name not in _TRAVEL:
            raise ValueError(
                f"unknown wind direction {name!r}; known directions are "
                f"{sorted(CARDINALS)}")

    rows, cols = grids.rows, grids.cols
    n = rows * cols
    if step_m is None:
        step_m = float(grids.cell_area_m2) ** 0.5
    step_m = float(step_m)

    src, dst, step_cells, indptr = _edge_arrays(grids)
    rr, cc = np.meshgrid(np.arange(rows, dtype=np.int64),
                         np.arange(cols, dtype=np.int64), indexing="ij")
    flat_rr = rr.reshape(-1)
    flat_cc = cc.reshape(-1)

    per_direction: dict[str, Any] = {}
    # The arrangement half of Stage 5c. `cell_fad` is 180-degree periodic, so the
    # NE and SW cost surfaces are bit-identical and their paths are the same
    # cells walked in opposite directions -- exact geometry, not a bug. What IS
    # direction-specific is the arrangement: which edge the wind enters from and
    # the height of the first obstruction it meets there. `directional_exposure`
    # (the canonical march, in design_metrics) already carries that, and its
    # per-direction entries are attached to each corridor so a NE reading and a
    # SW reading are no longer interchangeable. The path itself is NOT re-costed
    # with arrangement information: any such cost would be an invented weight.
    height = rasterise_height(footprints, grids)
    exposure = directional_exposure(height)
    # Direction-independent. A missing land class is a zero field, so a
    # synthetic grid keeps the historical 1 + cellFAD cost exactly.
    rough = roughness_penalty(grids).reshape(-1).astype(np.float64)
    for name, bearing in dirs.items():
        fad = cell_fad(footprints, grids, bearing).reshape(-1).astype(np.float64)
        # Separate rasters. Adding them into `cost` does not rewrite cellFAD,
        # and each is reported on its own below.
        ground = ground_level_fad(footprints, grids, bearing).reshape(-1).astype(np.float64)
        fad_term = 1.0 + fad
        cost = fad_term + ground + rough
        weights = 0.5 * (cost[src] + cost[dst]) * step_cells * step_m
        graph = csr_matrix((weights, dst, indptr), shape=(n, n))

        # The travel vector (wind FROM this direction) is the canonical table in
        # design_metrics -- not re-derived here, because a re-derived direction
        # table is exactly how NE and SW get swapped.
        dr, dc = _TRAVEL[name]
        # The upwind edge is the set of cells the wind reaches FIRST: those with
        # the minimum projection onto the travel vector. The downwind edge is the
        # maximum. For a cardinal wind that is a whole row or column (a band of
        # sources, exactly the "all upwind-edge cells as multi-source" the design
        # asks for); for a diagonal it is the single leading corner, which is what
        # forces the corridor to span the district instead of hopping from the top
        # edge to the adjacent left edge one step in -- the degenerate 2-cell NE
        # corridor the first version reported.
        projection = flat_rr * dr + flat_cc * dc
        up_idx = np.flatnonzero(projection == projection.min())
        down_idx = np.flatnonzero(projection == projection.max())

        dist, pred, _nearest = dijkstra(
            graph, directed=True, indices=up_idx,
            return_predecessors=True, min_only=True)

        exit_dist = dist[down_idx]
        finite = np.isfinite(exit_dist)
        if not finite.any():
            per_direction[name] = {
                "corridorCells": 0, "pathLengthM": 0.0, "meanCost": None,
                "blocked": True, "path": [],
                "entryEdge": ENTRY_EDGES[name],
                "firstObstructionMeanM": exposure.get(name, {}).get("meanFirstHitHeightM"),
            }
            continue

        node = int(down_idx[int(np.argmin(exit_dist))])
        chain: list[int] = []
        while node >= 0 and len(chain) <= n:
            chain.append(node)
            node = int(pred[node])
        chain.reverse()
        path = [[int(v // cols), int(v % cols)] for v in chain]

        length = 0.0
        for (r0, c0), (r1, c1) in zip(path, path[1:]):
            length += step_m * math.hypot(r1 - r0, c1 - c0)
        idx = [r * cols + c for r, c in path]
        mean_cost = float(np.mean([cost[i] for i in idx]))
        mean_fad = float(np.mean([fad[i] for i in idx]))
        mean_ground = float(np.mean([ground[i] for i in idx]))
        mean_rough = float(np.mean([rough[i] for i in idx]))

        per_direction[name] = {
            "corridorCells": len(path),
            "pathLengthM": round(length, 2),
            "meanCost": round(mean_cost, 4),
            # cellFAD along the path, without the ground or roughness terms.
            # ``meanCost - 1`` is no longer this number.
            "meanCellFad": round(mean_fad, 6),
            "meanGroundFad": round(mean_ground, 6),
            "meanRoughness": round(mean_rough, 6),
            "blocked": False,
            "path": path,
            "geometricEffects": geometric_effects(path, height, name),
            # Stage 5c: the arrangement half. Same path cells for opposite
            # winds (exact geometry), but different entry edge and different
            # first-obstruction height -- the two readings differ here, and
            # the limitation below says exactly where the difference ends.
            "entryEdge": ENTRY_EDGES[name],
            "firstObstructionMeanM": exposure.get(name, {}).get("meanFirstHitHeightM"),
        }

    return {
        "metric": "least-cost-path ventilation corridors",
        "costSurface": (
            "1 + cellFAD, plus a separate ground-level openness term and a "
            "separate land-class roughness penalty. The FAD term is not inverted. "
            "The other two are not folded into FAD and are not a velocity."
        ),
        "resolutionM": round(step_m, 4),
        "directions": per_direction,
        "terms": _term_sidecars(),
        "directionWeights": _direction_weight_block(
            list(per_direction), direction_weights, weight_source),
        "geometricEffectSidecar": {
            "status": GEOMETRIC_EFFECT_STATUS,
            "method": GEOMETRIC_EFFECT_METHOD,
            "limitation": GEOMETRIC_EFFECT_LIMITATION,
        },
        "status": "FAD_IS_NOT_A_VELOCITY_RATIO",
        "warning": ("FAD is not a velocity ratio. The corridor is geometry, not "
                    "flow: it shows the openest through-route, not a measured "
                    "wind speed."),
        "limitation": (
            "Geometry, not flow. No velocity, no turbulence, no pressure field. "
            "The least-cost path is the SAME cells for opposite winds: the "
            "frontal-area surface is 180-degree periodic, so the NE and SW "
            "corridors are one path walked in opposite directions -- exact "
            "geometry, not a bug. What IS direction-specific is now attached: "
            "entryEdge (which side the wind enters from) and "
            "firstObstructionMeanM (the arrangement, from the canonical "
            "directional_exposure march). The path cost itself still cannot "
            "tell a north-easterly from a south-westerly, and any cost that "
            "claimed to would be an invented weight. Ground-level openness and "
            "the roughness penalty are separate terms with their own sidecars; "
            "they are not a combined score and they are not speeds."
        ),
    }


def fad_ratio(baseline_fad: float, scenario_fad: float,
              direction: str) -> dict[str, Any]:
    """``scenario / baseline`` frontal area density, for one direction.

    ``ratio`` is ``None`` with ``defined=False`` when the baseline is zero: a ratio
    with a zero denominator is undefined, not infinite. This is a comparison and
    never a velocity ratio.
    """
    baseline = float(baseline_fad)
    scenario = float(scenario_fad)
    defined = baseline > 0.0
    return {
        "direction": direction,
        "baselineFad": baseline,
        "scenarioFad": scenario,
        "ratio": (round(scenario / baseline, 6) if defined else None),
        "defined": defined,
        "note": ("scenario frontal area density / baseline, for one direction. A "
                 "ratio is a comparison, not an absolute velocity ratio."),
        "status": "RELATIVE_COMPARISON_NOT_A_VELOCITY_RATIO",
        "warning": "A ratio is a comparison, not an absolute VR.",
    }
