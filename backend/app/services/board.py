"""The comparison board: two schemes, five separate axes, no combined score.

## What this is

The product's headline (STATUS.md edge 1): load the schemes already on the
table and read, side by side and each in its own units, what each combination
does to flood storage, surface heat, tide, greenery and the wind channel.
Because the schemes sit in one model, a district record of what each project
assumed about its neighbours falls out -- that record is the side effect, not
this endpoint's job.

## One definition of every number

Nothing here is new arithmetic. Each axis reads the function the rest of the
project already scores with:

- drainage deficit / runoff / storage: ``sandbox_model.apply_interventions``
  + ``_scenario_ledger`` (the run's own ledger path);
- flood extent: ``hydrology.fill_and_spill`` at the shared tailwater, the same
  cascade ``run_service`` routes with;
- surface heat: ``design_metrics.heat_field_report`` over the scheme's land
  class and massing terms (the heat-field route's own blend);
- greenery / impervious share: the ledger's ``_area_stats`` figures;
- wind channel: ``ventilation.least_cost_corridors`` over the scheme's
  footprints, geometry only -- never a velocity ratio.

A second copy of any of these would be the drift this project forbids, so the
board composes them and adds only the delta between two readings.

## What it refuses to do

No combined score, no pass/fail, no ranking. The units are incompatible and
the axes genuinely conflict; a total would settle the trade-off silently.
``combinedScore`` is None on every response and the reason travels with it.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from app.config import DEFAULT_RAINFALL_MM, settings
from app.services import scene_service
from app.services.design_metrics import (
    CARDINALS,
    HEAT_SUMMER_DAY_OF_YEAR,
    SITE_LAT_DEG,
    SITE_LON_DEG,
    footprints_from_geojson,
    footprint_from_ring,
    heat_field_report,
    load_heat_calibration,
    rasterise_height,
    shade_mask,
    sky_view_factor_raster,
)
from app.services.sandbox_model import (
    TIDE_STATES,
    Grids,
    _runoff_and_unstored,
    _scenario_ledger,
    apply_interventions,
    cn_grid_for,
    load_grids,
)
from app.services.ventilation import least_cost_corridors, load_reference
from hydrology import fill_and_spill
from make_wetgrid import FLOOD_DEPTH_M
from _overlay_common import HEAT_INDEX, LAND_CLASSES

BOARD_STATUS = "COMPARISON_BOARD_SEPARATE_AXES_NO_COMBINED_SCORE"
BOARD_WARNING = (
    "Screening comparison of two schemes on five separate axes, each in its "
    "own units. No combined score and no pass/fail: the units are "
    "incompatible and the axes conflict, so a total would settle the "
    "trade-off silently. The wind channel is geometry (a least-cost "
    "corridor), not a velocity ratio. Flood extent is routed screening "
    "depth, not a flood prediction."
)
WHY_NO_COMBINED_SCORE = (
    "The five axes carry incompatible units (m3 of deficit, a 0-1 heat index, "
    "mCD of tailwater, m2 of green, metres of corridor obstruction) and they "
    "genuinely conflict -- more storage can mean less green, taller massing "
    "shades more ground but blocks more wind. Any weights that made them add "
    "would be a statement about the weights, not about the schemes. Read the "
    "axes separately; the row that moved is the finding."
)

# The prevailing inflow the corridor is drawn under. AVRG73 names NE/ENE/E;
# the canonical travel table carries the eight principal directions, so ENE
# has no travel vector and is refused rather than approximated. The board
# draws NE and E and states that ENE is part of the cited inflow but not a
# drawable corridor direction.
DRAWN_DIRECTIONS = ("NE", "E")


def _scheme_footprints(features: list[dict[str, Any]],
                       interventions: list[dict[str, Any]]) -> list:
    """The city model with the scheme's planned-project massing applied.

    Mirrors ``run_service._heat_terms``' override rule exactly: remove the
    envelopes a ``station_massing`` feature sits on, then add the project's
    own block. A second rule here would let the board's wind axis disagree
    with the run's heat axis about the same scheme.
    """
    from app.services.ai_plan import _point_in_ring

    fps = footprints_from_geojson(features)
    for feature in interventions:
        kind = str(feature.get("intervention_type")
                   or feature.get("interventionType") or "")
        if kind != "station_massing":
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        ring = coords[0] if coords and isinstance(coords[0], (list, tuple)) else coords
        params = feature.get("params") or {}
        try:
            height = float(params.get("heightM", params.get("height_m")))
        except (TypeError, ValueError):
            continue
        if height <= 0 or len(ring) < 3:
            continue
        fps = [f for f in fps if not _point_in_ring(f.lon, f.lat, ring)]
        block = footprint_from_ring(ring, height)
        if block is not None:
            fps.append(block)
    return fps


def _flood_extent(grids: Grids, trial: np.ndarray, cn_over: dict,
                  storage_over: dict, rainfall_mm: float,
                  tailwater_m: float) -> float | None:
    """Routed flood extent (ha) for one scheme at the shared tailwater.

    The same cascade ``run_service`` uses: the ledger's per-cell unstored
    volume routed down the D8 chain, cells at or above FLOOD_DEPTH_M counted
    as flooded. None when the routing inputs are absent -- reported, not
    guessed.
    """
    if grids.receiver is None or grids.raw_elevation_5m is None:
        return None
    cn_grid = cn_grid_for(trial, cn_over) if cn_over else None
    _, unstored_m = _runoff_and_unstored(
        trial, rainfall_mm, cn_grid=cn_grid,
        storage_over=storage_over or None)
    cascade = fill_and_spill(
        filled=np.asarray(grids.elevation_5m, dtype=np.float64),
        raw=np.asarray(grids.raw_elevation_5m, dtype=np.float64),
        receiver=grids.receiver,
        runoff_in_m3=unstored_m * grids.cell_area_m2,
        cell_area_m2=grids.cell_area_m2,
        tailwater_m=tailwater_m,
    )
    depth = np.asarray(cascade["depthField"], dtype=np.float32)
    cells = int((depth >= FLOOD_DEPTH_M).sum())
    return round(cells * grids.cell_area_m2 / 10_000.0, 2)


def _heat_index(grids: Grids, trial: np.ndarray, fps: list) -> dict[str, Any]:
    """The blended heat field for one scheme (the heat-field route's blend)."""
    cell_m = float(grids.cell_area_m2) ** 0.5
    lut = np.array([HEAT_INDEX[name] for name in LAND_CLASSES], dtype=np.float32)
    land_index = lut[trial].astype(np.float32)
    height = rasterise_height(fps, grids)
    svf = sky_view_factor_raster(height, cell_m)
    shaded = shade_mask(fps, grids, SITE_LAT_DEG, SITE_LON_DEG,
                        HEAT_SUMMER_DAY_OF_YEAR, 14.0).astype(np.float32)
    report = heat_field_report(land_index, svf, shaded,
                               calibration=load_heat_calibration(), cell_m=cell_m)
    return {
        "meanHeatIndex": report["meanHeatIndex"],
        "maxHeatIndex": report["maxHeatIndex"],
        "status": report["status"],
        "warning": report["warning"],
    }


def _wind_channel(grids: Grids, fps: list) -> dict[str, Any]:
    """The least-cost corridor under the prevailing inflow, geometry only."""
    requested = {name: CARDINALS[name] for name in DRAWN_DIRECTIONS}
    corridors = least_cost_corridors(fps, grids, directions=requested)
    reference = load_reference() or {}
    wind = reference.get("windRegime") or {}
    return {
        "directions": corridors["directions"],
        "resolutionM": corridors["resolutionM"],
        "prevailingDirections": wind.get("prevailing", ["NE", "ENE", "E"]),
        "combinedFrequencyPercent": wind.get("combinedFrequencyPercent"),
        "inflowSource": (reference.get("source") or {}).get("name"),
        "eneNote": (
            "ENE is part of the cited prevailing inflow (AVRG73) but has no "
            "travel vector in the canonical eight-direction table, so it is "
            "not drawn as a corridor; NE and E are. Refused rather than "
            "approximated."
        ),
        "status": corridors["status"],
        "warning": corridors["warning"],
        "limitation": corridors["limitation"],
    }


def _read_scheme(grids: Grids, features: list[dict[str, Any]],
                 interventions: list[dict[str, Any]], rainfall_mm: float,
                 tailwater_m: float) -> dict[str, Any]:
    """One scheme's five-axis reading, from the project's own functions."""
    trial, cn_over, storage_over, applied, skipped = apply_interventions(
        grids, interventions)
    ledger = _scenario_ledger(grids, trial, cn_over, rainfall_mm,
                              storage_over or None)
    fps = _scheme_footprints(features, interventions)
    flood_ha = _flood_extent(grids, trial, cn_over, storage_over,
                             rainfall_mm, tailwater_m)
    heat = _heat_index(grids, trial, fps)
    wind = _wind_channel(grids, fps)
    return {
        "drainage": {
            "unstoredM3": round(float(ledger["unstoredM3"]), 1),
            "runoffM3": round(float(ledger["runoffM3"]), 1),
            "storageCapacityM3": round(float(ledger["storageCapacityM3"]), 1),
            "floodAreaHa": flood_ha,
            "units": "m3 of runoff with nowhere to go; ha of routed flood extent",
        },
        "heat": heat,
        "greenery": {
            "greenAreaM2": round(float(ledger["greenAreaM2"]), 1),
            "pavedAreaM2": round(float(ledger["pavedAreaM2"]), 1),
            "imperviousShare": round(float(ledger["imperviousShare"]), 4),
            "greenWaterAreaM2": round(float(ledger["greenWaterAreaM2"]), 1),
            "units": "m2 of land class; fraction paved",
        },
        "wind": wind,
        "interventionsApplied": applied,
        "interventionsSkipped": skipped,
    }


def _delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """B minus A on the numeric fields both readings share, per axis.

    Only subtraction -- no normalisation, no weighting. The wind axis reports
    the change in first-obstruction height and corridor length per drawn
    direction, which is the arrangement the corridor geometry carries.
    """
    def sub(x: Any, y: Any, places: int = 1) -> float | None:
        if x is None or y is None:
            return None
        return round(float(y) - float(x), places)

    da, db = a["drainage"], b["drainage"]
    ga, gb = a["greenery"], b["greenery"]
    wind_delta: dict[str, Any] = {}
    for name in DRAWN_DIRECTIONS:
        wa = (a["wind"]["directions"].get(name) or {})
        wb = (b["wind"]["directions"].get(name) or {})
        wind_delta[name] = {
            "firstObstructionDeltaM": sub(wa.get("firstObstructionMeanM"),
                                          wb.get("firstObstructionMeanM"), 3),
            "pathLengthDeltaM": sub(wa.get("pathLengthM"),
                                    wb.get("pathLengthM"), 2),
        }
    return {
        "drainage": {
            "unstoredM3": sub(da["unstoredM3"], db["unstoredM3"]),
            "runoffM3": sub(da["runoffM3"], db["runoffM3"]),
            "storageCapacityM3": sub(da["storageCapacityM3"], db["storageCapacityM3"]),
            "floodAreaHa": sub(da["floodAreaHa"], db["floodAreaHa"], 2),
        },
        "heat": {
            "meanHeatIndex": sub(a["heat"]["meanHeatIndex"],
                                 b["heat"]["meanHeatIndex"], 4),
        },
        "greenery": {
            "greenAreaM2": sub(ga["greenAreaM2"], gb["greenAreaM2"]),
            "pavedAreaM2": sub(ga["pavedAreaM2"], gb["pavedAreaM2"]),
            "imperviousShare": sub(ga["imperviousShare"], gb["imperviousShare"], 4),
            "greenWaterAreaM2": sub(ga["greenWaterAreaM2"], gb["greenWaterAreaM2"]),
        },
        "wind": wind_delta,
    }


def board(scene_id: str, scheme_a: list[str], scheme_b: list[str],
          rainfall_mm: float | None = None,
          tide_state: str = "low") -> dict[str, Any]:
    """Compare two schemes (each a list of plan ids) on the five axes.

    ``scheme_a`` / ``scheme_b`` are plan-id lists composed exactly as a run
    composes them (``routers.scenes.intervention_features_many``), so the
    board scores the same scenario the Run button would. An empty list is
    today's land cover. The tide is a shared forcing: both schemes are routed
    at the same tailwater, so a difference between them is the scheme's.
    """
    from app.routers.scenes import intervention_features_many

    scene_service.get_scene(scene_id)
    grids = load_grids()
    if grids is None:
        raise ValueError(
            "no analysis on disk: run scripts/fetch_dem.py, "
            "scripts/fetch_landcover.py and scripts/make_wetgrid.py")
    model = scene_service.buildings_path(scene_id)
    if not model:
        raise ValueError("this scene has no building footprints; "
                         "run scripts/build_buildings.py")
    features = json.loads(model.read_text()).get("features", [])
    if not features:
        raise ValueError("the city model has no features")

    if tide_state not in TIDE_STATES:
        raise ValueError(f"tideState must be one of {sorted(TIDE_STATES)}, "
                         f"got {tide_state!r}")
    rain = float(rainfall_mm) if rainfall_mm is not None else DEFAULT_RAINFALL_MM
    tailwater_m = float(TIDE_STATES[tide_state]["tailwaterM"])

    feats_a = intervention_features_many([p for p in scheme_a if p])
    feats_b = intervention_features_many([p for p in scheme_b if p])
    reading_a = _read_scheme(grids, features, feats_a, rain, tailwater_m)
    reading_b = _read_scheme(grids, features, feats_b, rain, tailwater_m)

    return {
        "sceneId": scene_id,
        "status": BOARD_STATUS,
        "warning": BOARD_WARNING,
        "rainfallMm": rain,
        "tide": {
            "state": tide_state,
            "label": TIDE_STATES[tide_state]["label"],
            "tailwaterM": tailwater_m,
            "source": TIDE_STATES[tide_state]["source"],
            "active": tailwater_m > 0.0,
            "note": ("Shared forcing: both schemes routed at this tailwater. "
                     "A screening backwater boundary condition, not a "
                     "hydraulic outfall model."),
        },
        "schemeA": {"planIds": [p for p in scheme_a if p], **reading_a},
        "schemeB": {"planIds": [p for p in scheme_b if p], **reading_b},
        "deltaBminusA": _delta(reading_a, reading_b),
        "combinedScore": None,
        "whyNoCombinedScore": WHY_NO_COMBINED_SCORE,
        "sources": {
            "terrain": grids.terrain_source,
            "landCover": grids.landcover_source,
        },
    }