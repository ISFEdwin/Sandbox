"""Area definition and the resolution policy.

An area is a polygon plus a name. Everything else -- rows, columns, cell area,
which capabilities are even representable -- is derived. This module is pure
arithmetic: no IO, no network, no numpy, so the preview shown before a download
is the same function the build uses afterwards.

The policy that matters is the one in :data:`RESOLUTION_LADDER`: a **constant
cell budget with a coarsening grid**. A screening model that keeps 5 m over
5,000 ha would need four million cells and would still be no more accurate than
the 90 m DEM under it. Coarsening the grid and recording the loss is the honest
trade, and it is why :func:`drainage_ceiling` returns L1 at 20 m.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from app.services.geo_import import build_grid, polygon_bounds

#: ``(area ceiling in ha, cell size in m)``, evaluated top to bottom.
#: The cell counts are deliberately flat: 200k, 250k, 250k.
RESOLUTION_LADDER: tuple[tuple[float, float], ...] = (
    (500.0, 5.0),
    (2_500.0, 10.0),
    (10_000.0, 20.0),
)

#: Hard cell budget. Above this the grid coarsens; it never silently grows.
MAX_CELLS = 250_000

#: Above this area, sub-basin decomposition is required (Increment D). Refusing
#: is better than producing a 4M-cell array the process cannot hold.
MAX_AREA_HA = 10_000.0

#: The smallest grid on which a conduit's contributing area is still meaningful.
#: At 20 m a cell is 400 m2 and a 300 mm pipe serving 0.2 ha drains half a cell.
MIN_CELLS_PER_CONDUIT_CATCHMENT_M = 10.0

Bounds = tuple[float, float, float, float]


class AreaError(ValueError):
    """An area the pipeline refuses, with the reason it refuses."""


@dataclass(frozen=True)
class GridSpec:
    """The analysis grid every raster in a bundle shares."""

    bounds: Bounds
    resolution_m: float
    rows: int
    cols: int
    cell_area_m2: float
    area_ha: float
    #: Set when the policy coarsened the grid beyond its first choice.
    coarsened_from_m: float | None = None
    note: str = ""

    @property
    def cells(self) -> int:
        return self.rows * self.cols

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "bounds": list(self.bounds),
            "resolutionM": self.resolution_m,
            "rows": self.rows,
            "cols": self.cols,
            "cellAreaM2": self.cell_area_m2,
            "areaHa": round(self.area_ha, 4),
            "cells": self.cells,
        }
        if self.coarsened_from_m is not None:
            out["coarsenedFromM"] = self.coarsened_from_m
        if self.note:
            out["note"] = self.note
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GridSpec:
        bounds = tuple(float(v) for v in raw["bounds"])
        if len(bounds) != 4:
            raise AreaError("grid.bounds must be (west, south, east, north)")
        return cls(
            bounds=bounds,  # type: ignore[arg-type]
            resolution_m=float(raw["resolutionM"]),
            rows=int(raw["rows"]),
            cols=int(raw["cols"]),
            cell_area_m2=float(raw.get("cellAreaM2") or 0.0),
            area_ha=float(raw.get("areaHa") or 0.0),
            coarsened_from_m=(
                float(raw["coarsenedFromM"]) if raw.get("coarsenedFromM") else None
            ),
            note=str(raw.get("note") or ""),
        )


def bounds_of(geometry: dict[str, Any] | Bounds) -> Bounds:
    """Accept a GeoJSON polygon or an already-computed bounds tuple."""
    if isinstance(geometry, dict):
        return polygon_bounds(geometry)
    bounds = tuple(float(v) for v in geometry)
    if len(bounds) != 4:
        raise AreaError("bounds must be (west, south, east, north)")
    return bounds  # type: ignore[return-value]


def area_ha_of(bounds: Bounds) -> float:
    """Extent area in hectares on the project's local equirectangular metric.

    Reuses :func:`app.services.geo_import.build_grid` so the preview and the
    build cannot disagree about how a degree becomes a metre.
    """
    return float(build_grid(bounds, 5.0)["area_m2"]) / 10_000.0


def choose_resolution(area_ha: float) -> tuple[float, str]:
    """The policy's cell size for this area, and the sentence explaining it."""
    if area_ha <= 0:
        raise AreaError("area must be positive")
    if area_ha > MAX_AREA_HA:
        raise AreaError(
            f"{area_ha:,.0f} ha exceeds the {MAX_AREA_HA:,.0f} ha single-bundle "
            "limit. Split it into sub-basins (Increment D) or tighten the "
            "selection."
        )
    for ceiling_ha, resolution_m in RESOLUTION_LADDER:
        if area_ha <= ceiling_ha:
            return resolution_m, (
                f"{area_ha:,.1f} ha is within the {ceiling_ha:,.0f} ha band, "
                f"so the grid is {resolution_m:g} m."
            )
    # Unreachable while MAX_AREA_HA equals the last ladder ceiling.
    raise AreaError(f"no resolution band covers {area_ha:,.1f} ha")


def drainage_ceiling(resolution_m: float) -> tuple[str, list[str]]:
    """The best drainage capability level this cell size can support.

    This is a property of the method, not of the data: per-conduit attribution
    needs a contributing area larger than a cell. The actual level is decided by
    stage ``s07`` and written into the seal.
    """
    if resolution_m <= 5.0:
        return "L2", []
    if resolution_m <= 10.0:
        return "L2", [
            "conduits whose contributing area is smaller than one cell fall "
            "back to the L1 published standard",
        ]
    return "L1", [
        f"a {resolution_m:g} m cell is {resolution_m ** 2:.0f} m2; a conduit "
        "serving less than one cell cannot be attributed, so drainage is the "
        "published-standard proxy only",
    ]


def _coarsen_until_fits(bounds: Bounds, resolution_m: float) -> tuple[float, int, int]:
    """Double the cell size until the grid fits :data:`MAX_CELLS`."""
    step = resolution_m
    while True:
        grid = build_grid(bounds, step)
        if grid["rows"] * grid["cols"] <= MAX_CELLS:
            return step, int(grid["rows"]), int(grid["cols"])
        step *= 2.0


def derive_grid(
    geometry: dict[str, Any] | Bounds,
    resolution_m: float | None = None,
) -> GridSpec:
    """Derive the one grid this area's bundle will use.

    An explicit ``resolution_m`` is honoured only when it fits the budget. A
    request that does not fit raises: silently coarsening a caller's stated
    resolution would make two areas look comparable when they are not.
    """
    bounds = bounds_of(geometry)
    west, south, east, north = bounds
    if not (east > west and north > south):
        raise AreaError(f"degenerate bounds {bounds}")

    area_ha = area_ha_of(bounds)
    policy_m, policy_note = choose_resolution(area_ha)

    requested = float(resolution_m) if resolution_m is not None else None
    if requested is not None and requested <= 0:
        raise AreaError("resolutionM must be positive")

    coarsened_from: float | None = None
    if requested is None:
        resolution = policy_m
        note = policy_note
    else:
        grid = build_grid(bounds, requested)
        cells = int(grid["rows"]) * int(grid["cols"])
        if cells > MAX_CELLS:
            raise AreaError(
                f"{requested:g} m over {area_ha:,.1f} ha needs {cells:,} cells, "
                f"above the {MAX_CELLS:,} budget. Ask for {policy_m:g} m, or "
                "leave resolutionM unset to apply the policy."
            )
        resolution = requested
        note = (
            f"explicit {requested:g} m requested; the policy would have chosen "
            f"{policy_m:g} m ({policy_note})"
        )

    # The ladder already fits its bands, but a caller may supply a resolution
    # finer than the band allows while still under the cell budget. Coarsen
    # only when the budget is actually exceeded.
    grid = build_grid(bounds, resolution)
    cells = int(grid["rows"]) * int(grid["cols"])
    if cells > MAX_CELLS:
        coarsened_from = resolution
        resolution, rows, cols = _coarsen_until_fits(bounds, resolution)
        grid = build_grid(bounds, resolution)
        note = (
            f"{coarsened_from:g} m needed {cells:,} cells; coarsened to "
            f"{resolution:g} m to stay within {MAX_CELLS:,}."
        )
    else:
        rows, cols = int(grid["rows"]), int(grid["cols"])

    return GridSpec(
        bounds=bounds,
        resolution_m=resolution,
        rows=rows,
        cols=cols,
        cell_area_m2=float(grid["area_m2"]) / (rows * cols),
        area_ha=area_ha,
        coarsened_from_m=coarsened_from,
        note=note,
    )


def cost_class(cells: int) -> str:
    """A coarse build cost, derived from cell count alone.

    Deliberately not a duration. There is no measured timing for an arbitrary
    area, and inventing minutes would be the first fabricated number in a
    pipeline whose job is to avoid them.
    """
    if cells <= 50_000:
        return "small"
    if cells <= MAX_CELLS:
        return "medium"
    return "large"


def preview(geometry: dict[str, Any] | Bounds,
            resolution_m: float | None = None) -> dict[str, Any]:
    """What a planner is told before anything is downloaded.

    Every value is derived, none is guessed: the area, the grid, the cell count,
    the drainage ceiling the cell size permits, and which axes wait on which
    stage. The terrain ceiling is left ``unverified`` because only stage ``s01``
    can decide whether Open3Dhk tiles exist for this extent.
    """
    grid = derive_grid(geometry, resolution_m)
    level, reasons = drainage_ceiling(grid.resolution_m)
    notes = [grid.note] if grid.note else []
    if grid.coarsened_from_m is not None:
        notes.append(
            f"resolution was coarsened from {grid.coarsened_from_m:g} m; the "
            "bundle records the coarsening and the capability ceiling reflects it."
        )
    return {
        "areaHa": round(grid.area_ha, 2),
        "resolutionM": grid.resolution_m,
        "rows": grid.rows,
        "cols": grid.cols,
        "cells": grid.cells,
        "costClass": cost_class(grid.cells),
        "notes": notes,
        "drainageCeiling": {"level": level, "reasons": reasons},
        "terrainCeiling": {
            "level": "unverified",
            "reasons": [
                "stage s01 decides whether Open3Dhk terrain tiles exist for "
                "this extent; if they do not, terrain falls back to the ~90 m "
                "Open-Meteo DEM and is reported as L1"
            ],
        },
        "requires": {
            "flood": ["s03_terrain"],
            "massing": ["s04_buildings"],
            "heat": ["s05_landcover", "s04_buildings"],
            "wind": ["s04_buildings", "s08_climate"],
            "drainage": ["s07_drainage"],
        },
        "grid": grid.to_dict(),
    }


@dataclass
class AreaRecord:
    """The pipeline's only input. Persisted as ``aoi.json``."""

    id: str
    name: str
    geometry: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)
    requested_resolution_m: float | None = None
    created: str = ""

    @property
    def bounds(self) -> Bounds:
        return bounds_of(self.geometry)

    def grid(self) -> GridSpec:
        return derive_grid(self.geometry, self.requested_resolution_m)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "geometry": self.geometry,
            "requestedResolutionM": self.requested_resolution_m,
            "created": self.created,
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AreaRecord:
        area_id = str(raw.get("id") or "").strip()
        if not area_id:
            raise AreaError("aoi.json has no id")
        geometry = raw.get("geometry")
        if not isinstance(geometry, dict):
            raise AreaError("aoi.json has no geometry object")
        return cls(
            id=area_id,
            name=str(raw.get("name") or area_id),
            geometry=geometry,
            provenance=dict(raw.get("provenance") or {}),
            requested_resolution_m=(
                float(raw["requestedResolutionM"])
                if raw.get("requestedResolutionM") is not None
                else None
            ),
            created=str(raw.get("created") or ""),
        )


#: The stage order the seal is checked against. Kept here so a caller that only
#: wants "what is ready" does not have to import the runner.
STAGE_ORDER: tuple[str, ...] = (
    "s00_area",
    "s01_sources",
    "s02_grid",
    "s03_terrain",
    "s04_buildings",
    "s05_landcover",
    "s06_waterways",
    "s07_drainage",
    "s08_climate",
    "s09_presentation",
    "s10_seal",
)


def unresolved(manifest: Any, names: Iterable[str] | None = None) -> list[str]:
    """Names in ``names`` (default: every stage) that are not usable yet."""
    wanted = tuple(names) if names is not None else STAGE_ORDER
    return [n for n in wanted if not manifest.ready(n)]


def area_root(data_dir: Path, area_id: str) -> Path:
    """``data/areas/<area_id>``. One place builds this path."""
    safe = "".join(c for c in area_id if c.isalnum() or c in "-_.")
    if not safe or safe != area_id:
        raise AreaError(
            f"area id {area_id!r} may contain only letters, digits, '-', '_' "
            "and '.'"
        )
    return data_dir / "areas" / area_id
