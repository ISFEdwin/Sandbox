"""Two schemes, side by side, on axes that never combine.

The product edge recorded in ``STATUS.md`` (18 Nov 2026) is a broad-brush
comparison: load the schemes already on the table and read, on separate axes,
what each combination does to flood storage, surface heat, tide, greenery and
the wind channel. This module is that read. It deliberately returns **rows**,
not a score: every number keeps its own unit, and ``combinedScore`` is null with
a sentence saying why.

One definition of every axis
----------------------------

Nothing here re-implements physics. Drainage and greenery come from
:func:`sandbox_model._scenario_ledger` -- the same ledger a live run scores.
Flood extent comes from :func:`hydrology.fill_and_spill` -- the project's one
router. The wind corridor comes from :func:`ventilation.least_cost_corridors`,
the same least-cost walk the map draws. A comparison that computed its own copy
of any of these would be a second truth, and the picture and the number would
eventually disagree.

What is *not* compared
----------------------

Tide is a boundary condition, not an outcome. The same tailwater is applied to
both schemes, so the row is reported as context with ``comparable: False``
rather than as a delta that would imply one scheme changed the sea.

The surface-temperature mean is pinned to the slider by construction (see
``run_service._temperature_fields``), so comparing it would always read zero.
The land-cover heat index is the number that moves with a scheme, and it is
the one reported.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.services.sandbox_model import (
    TIDE_STATES,
    Grids,
    _runoff_and_unstored,
    _scenario_ledger,
    apply_interventions,
    cn_grid_for,
)
from app.services.ventilation import least_cost_corridors

# The renderer and the router are the offline pipeline's own, imported -- never
# re-implemented, for the reason in the module docstring.
from make_wetgrid import FLOOD_DEPTH_M, _fill_to_volume  # noqa: E402
from hydrology import fill_and_spill  # noqa: E402

COMPARISON_STATUS = "SCREENING_COMPARISON_NOT_A_VERDICT"
COMPARISON_WARNING = (
    "Screening comparison. Each axis keeps its own units and no axis is combined "
    "into a score, a rank or a pass/fail. Not an engineering assessment and not a "
    "regulatory submission."
)

# The published prevailing inflow for Hung Shui Kiu (AVRG73): NE / ENE / E.
# Corridors need a travel vector, and the canonical table in `design_metrics`
# carries the eight principal directions; ENE is a 16-point name with no travel
# vector and is refused there rather than approximated. NE and E are the two
# prevailing principals the walker can take, and the pair is stated on the row.
PREVAILING_CORRIDOR_DIRECTIONS = ("NE", "E")
# The canonical table, restated only as the literal the corridor walker needs.
PREVAILING_BEARINGS = {"NE": 45.0, "E": 90.0}

# Which end of a row is the better one. Not a score -- a direction of travel the
# board can arrow, so "moved by 3,000 m3" does not have to be decoded.
LOWER_IS_BETTER = "lower-better"
HIGHER_IS_BETTER = "higher-better"


def _cell_center(grids: Grids, row: int, col: int) -> list[float]:
    """The lon/lat centre of one analysis cell.

    The inverse of :meth:`Grids.cell_of`, which is the only place the pixel
    convention is written down. Rounded to ~0.1 m so the polyline payload does
    not carry float noise the map cannot draw.
    """
    x0, y0, x1, y1 = grids.bounds
    lon = x0 + (col + 0.5) / grids.cols * (x1 - x0)
    lat = y1 - (row + 0.5) / grids.rows * (y1 - y0)
    return [round(float(lon), 6), round(float(lat), 6)]


def _path_geometry(
    grids: Grids,
    path: list[list[int]],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """A corridor's cell path as a GeoJSON LineString, or None if too short."""
    if len(path) < 2:
        return None
    line: dict[str, Any] = {
        "type": "LineString",
        "coordinates": [_cell_center(grids, int(r), int(c)) for r, c in path],
    }
    if properties:
        line["properties"] = properties
    return line


def _scheme_metrics(
    grids: Grids,
    features: list[dict[str, Any]],
    rainfall_mm: float,
    tailwater_m: float,
) -> dict[str, Any]:
    """One scheme's ledger reading, wet extent and routed flood extent.

    The scenario grid is built once and every number below reads it, so the
    drainage row, the greenery row and the flood row describe the same scheme
    rather than three calls that could drift apart.
    """
    trial, cn_over, storage_over, applied, skipped = apply_interventions(
        grids, features)

    ledger = _scenario_ledger(grids, trial, cn_over, rainfall_mm,
                              storage_over or None)

    cn_grid = cn_grid_for(trial, cn_over) if cn_over else None
    _, unstored_m = _runoff_and_unstored(
        trial, rainfall_mm, cn_grid=cn_grid, storage_over=storage_over or None)
    volume_m3 = float(np.asarray(unstored_m, dtype=np.float64).sum()
                      * grids.cell_area_m2)

    depth_field, _level = _fill_to_volume(
        np.asarray(grids.elevation_5m, dtype=np.float64), volume_m3,
        grids.cell_area_m2)
    wet_area_ha = float((depth_field > 0).sum()) * grids.cell_area_m2 / 10_000.0

    flood_area_ha: float | None = None
    if grids.receiver is not None and grids.raw_elevation_5m is not None:
        cascade = fill_and_spill(
            filled=np.asarray(grids.elevation_5m, dtype=np.float64),
            raw=np.asarray(grids.raw_elevation_5m, dtype=np.float64),
            receiver=grids.receiver,
            runoff_in_m3=np.asarray(unstored_m, dtype=np.float64)
            * grids.cell_area_m2,
            cell_area_m2=grids.cell_area_m2,
            tailwater_m=tailwater_m,
        )
        routed = np.asarray(cascade["depthField"], dtype=np.float32)
        flood_area_ha = float((routed >= FLOOD_DEPTH_M).sum()) \
            * grids.cell_area_m2 / 10_000.0

    cell_area = grids.cell_area_m2
    site_area = float(grids.rows * grids.cols) * cell_area

    return {
        "drainageDeficitM3": round(float(ledger["unstoredM3"]), 1),
        "runoffM3": round(float(ledger["runoffM3"]), 1),
        "wetAreaHa": round(wet_area_ha, 2),
        "floodAreaHa": round(flood_area_ha, 2) if flood_area_ha is not None else None,
        "heatIndex": round(float(ledger.get("heatMean", 0.0)), 4),
        "greenWaterAreaM2": round(float(ledger.get("greenWaterAreaM2", 0.0)), 1),
        "greenWaterHa": round(float(ledger.get("greenWaterAreaM2", 0.0))
                              / 10_000.0, 2),
        "imperviousShare": round(
            float(ledger.get("imperviousShare", 0.0)), 4),
        "storageCapacityM3": round(float(ledger.get("storageCapacityM3", 0.0)), 1),
        "applied": applied,
        "skipped": skipped,
        "siteAreaM2": site_area,
    }


def _wind_metrics(
    grids: Grids,
    footprints: list[Any],
    features: list[dict[str, Any]],
) -> dict[str, Any]:
    """The prevailing-wind corridor and first-obstruction height for a scheme.

    A scheme's buildings are added to today's city, because a project that is
    not built yet still stands in the scenario being compared. The additions go
    through :func:`run_service._massing_overrides`, the same extractor the heat
    terms use, so the corridor and the heat field read one massing description.
    """
    from app.services.run_service import _massing_overrides
    from app.services.design_metrics import (
        CARDINALS,
        footprint_from_ring,
        frontal_area_density,
    )
    from app.services.ventilation import fad_ratio

    scheme_footprints = list(footprints)
    for override in _massing_overrides(features):
        fp = footprint_from_ring(override.get("ring"), override.get("heightM") or 0)
        if fp is not None:
            scheme_footprints.append(fp)

    site = float(grids.rows * grids.cols) * float(grids.cell_area_m2)
    baseline_fad = frontal_area_density(footprints, site, CARDINALS)
    scenario_fad = frontal_area_density(scheme_footprints, site, CARDINALS)
    fad_by_direction = {
        name: fad_ratio(
            baseline_fad["byDirection"][name],
            scenario_fad["byDirection"][name],
            name,
        )
        for name in CARDINALS
        if name in baseline_fad.get("byDirection", {})
        and name in scenario_fad.get("byDirection", {})
    }

    try:
        result = least_cost_corridors(
            scheme_footprints, grids, directions=dict(PREVAILING_BEARINGS))
    except (ValueError, RuntimeError) as exc:  # scipy absent or a bad bearing
        return {
            "status": "WIND_CORRIDOR_UNAVAILABLE",
            "reason": str(exc),
            "directions": {},
            "corridor": None,
            "fadRatioByDirection": fad_by_direction,
        }

    directions = result.get("directions") or {}
    ne = directions.get("NE") or {}
    east = directions.get("E") or {}

    # The headline reading is the NE walk: NE is the first of the published
    # prevailing principals and the direction the district's channel is read
    # from. E is reported beside it in `directions`. Averaging the two would
    # produce a number that matches neither published reading.
    heights = [d.get("firstObstructionMeanM") for d in (ne, east)
               if d.get("firstObstructionMeanM") is not None]
    headline = ne.get("firstObstructionMeanM")
    if headline is None and heights:
        headline = round(float(np.mean(heights)), 2)
    effect_sidecar = result.get("geometricEffectSidecar") or {}
    placed = []
    for tag in ne.get("geometricEffects") or []:
        lon, lat = _cell_center(grids, int(tag["row"]), int(tag["col"]))
        placed.append({"labels": list(tag.get("labels") or []), "at": [lon, lat]})
    corridor = _path_geometry(grids, ne.get("path") or [], {
        "geometricEffects": placed,
        "sidecar": effect_sidecar,
    })
    return {
        "status": "WIND_CORRIDOR_GEOMETRY",
        "directions": {
            "NE": {
                "pathLengthM": ne.get("pathLengthM"),
                "firstObstructionMeanM": ne.get("firstObstructionMeanM"),
                "entryEdge": ne.get("entryEdge"),
                "blocked": ne.get("blocked"),
            },
            "E": {
                "pathLengthM": east.get("pathLengthM"),
                "firstObstructionMeanM": east.get("firstObstructionMeanM"),
                "entryEdge": east.get("entryEdge"),
                "blocked": east.get("blocked"),
            },
        },
        "firstObstructionMeanM": headline,
        # The NE corridor is the one drawn on the map: it is the published
        # prevailing direction and it is the walk the district reads as the
        # channel. E is reported beside it.
        "corridor": corridor,
        "corridorDirection": "NE",
        "fadRatioByDirection": fad_by_direction,
        "terms": result.get("terms"),
        "directionWeights": result.get("directionWeights"),
        "warning": result.get("warning"),
        "limitation": result.get("limitation"),
    }


def _row(
    key: str,
    label: str,
    unit: str,
    a: float | None,
    b: float | None,
    *,
    direction: str | None,
    note: str = "",
    comparable: bool = True,
) -> dict[str, Any]:
    """One board row. A missing value stays missing; it is never zero-filled."""
    delta = None
    if a is not None and b is not None:
        delta = round(float(b) - float(a), 4)
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "a": a,
        "b": b,
        "delta": delta,
        "direction": direction,
        "comparable": comparable,
        "note": note,
    }


def _surface_with_wind(
    grids: Grids,
    footprints: list[Any],
    features: list[dict[str, Any]],
    temperature_c: float,
    wind: dict[str, Any],
) -> dict[str, Any]:
    """The site-mean surface after the screening ventilation allowance.

    The allowance uses this scheme's frontal-area raster for the selected
    bearing, so a scheme that blocks the channel cools less than one that
    leaves it open. The temperature slider is the mean at the PlanD inlet.
    """
    from app.services.design_metrics import cell_fad, footprint_from_ring
    from app.services.run_service import _massing_overrides
    from app.services.temperature_field import ventilation_report

    scheme = list(footprints)
    for override in _massing_overrides(features):
        ring = override.get("ring") or []
        height = float(override.get("heightM") or 0.0)
        if height <= 0 or len(ring) < 3:
            continue
        from app.services.ai_plan import _point_in_ring
        scheme = [item for item in scheme if not _point_in_ring(item.lon, item.lat, ring)]
        block = footprint_from_ring(ring, height)
        if block is not None:
            scheme.append(block)
    fad = cell_fad(scheme, grids, float(wind["bearingDeg"]))
    report = ventilation_report(fad, wind.get("speedMps"), wind.get("referenceSpeedMps"))
    report.pop("coolingC", None)
    report["surfaceMeanC"] = round(float(temperature_c) - float(report["meanCoolingC"]), 3)
    return report


def compare_schemes(
    scene_id: str,
    grids: Grids,
    sides: list[dict[str, Any]],
    building_features: list[dict[str, Any]],
    *,
    rainfall_mm: float,
    temperature_c: float,
    tide_state: str,
    wind: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score two schemes on the same axes and return the board.

    ``sides`` is exactly two ``{"key", "label", "planIds", "features"}`` dicts,
    A then B. The features are resolved by the caller (the router), because
    plan-to-feature resolution already has one home in ``routers/scenes.py``;
    resolving it a second time here would be a second truth about what a plan
    contains.
    """
    if len(sides) != 2:
        raise ValueError("compare_schemes needs exactly two sides")
    if tide_state not in TIDE_STATES:
        raise ValueError(f"tideState must be one of {sorted(TIDE_STATES)}, "
                         f"got {tide_state!r}")
    tailwater_m = float(TIDE_STATES[tide_state]["tailwaterM"])

    from app.services.design_metrics import footprints_from_geojson

    footprints = footprints_from_geojson(building_features)

    measured: list[dict[str, Any]] = []
    for side in sides:
        metrics = _scheme_metrics(grids, side.get("features") or [],
                                  rainfall_mm, tailwater_m)
        metrics["wind"] = _wind_metrics(grids, footprints,
                                        side.get("features") or [])
        measured.append(metrics)

    a, b = measured

    axes = [
        _row("drainage", "Buffer deficit (unstored runoff)", "m³",
             a["drainageDeficitM3"], b["drainageDeficitM3"],
             direction=LOWER_IS_BETTER,
             note="Runoff with nowhere to go under the stated storm."),
        _row("floodExtent", "Routed flood extent (≥ %.2f m)" % FLOOD_DEPTH_M, "ha",
             a["floodAreaHa"], b["floodAreaHa"],
             direction=LOWER_IS_BETTER,
             note="Fill-and-spill routing; null when routing inputs are absent."),
        _row("heat", "Land-cover heat index", "index 0–1",
             a["heatIndex"], b["heatIndex"],
             direction=LOWER_IS_BETTER,
             note=("The site-mean surface temperature is pinned to the slider, "
                   "so this land-cover index is what moves with a scheme.")),
    ]
    if wind is not None:
        a_surface = _surface_with_wind(
            grids, footprints, sides[0].get("features") or [], temperature_c, wind)
        b_surface = _surface_with_wind(
            grids, footprints, sides[1].get("features") or [], temperature_c, wind)
        a["windVentilation"] = a_surface
        b["windVentilation"] = b_surface
        axes.append(
            _row("windHeat", "Surface mean at this wind", "°C",
                 a_surface["surfaceMeanC"], b_surface["surfaceMeanC"],
                 direction=LOWER_IS_BETTER,
                 note=(
                     f"{wind.get('label')} at {wind.get('speedMps')} m/s from "
                     f"{wind.get('direction')}, against the PlanD inlet "
                     f"{wind.get('referenceSpeedMps')} m/s. Open cells change by "
                     f"{-a_surface['openCellCoolingC']} C and sheltered cells by "
                     f"{-a_surface['shelteredCellCoolingC']} C (negative is cooler), "
                     f"capped at {a_surface['capC']} C. A screening allowance. The "
                     "land-cover index above does not include it."
                 )),
        )
    axes.extend([
        _row("greenery", "Green + water area", "ha",
             a["greenWaterHa"], b["greenWaterHa"],
             direction=HIGHER_IS_BETTER,
             note="Not an SBDG certificate; a land-cover share."),
        _row("impervious", "Impervious share", "%",
             round(100.0 * a["imperviousShare"], 2),
             round(100.0 * b["imperviousShare"], 2),
             direction=LOWER_IS_BETTER),
        _row("wind", "First obstruction, prevailing wind", "m",
             a["wind"].get("firstObstructionMeanM"),
             b["wind"].get("firstObstructionMeanM"),
             direction=LOWER_IS_BETTER,
             note=("Mean height of the first building met from NE and E. "
                   "Geometry, not a velocity ratio.")),
        _row("tide", "Tide tailwater (applied to both)", "mCD",
             tailwater_m, tailwater_m,
             direction=None,
             comparable=False,
             note=TIDE_STATES[tide_state]["label"] + ". " +
                  TIDE_STATES[tide_state]["source"]),
    ])

    from app.services.data_collection import collect, wind_channel_comparison

    data_collection = collect(
        scene_id,
        compared=[
            {"key": "a", "planIds": sides[0].get("planIds") or []},
            {"key": "b", "planIds": sides[1].get("planIds") or []},
        ],
    )
    wind_channel = wind_channel_comparison({
        "a": a["wind"],
        "b": b["wind"],
    })

    return {
        "sceneId": scene_id,
        "status": COMPARISON_STATUS,
        "warning": COMPARISON_WARNING,
        "inputs": {
            "rainfallMm": rainfall_mm,
            "temperatureC": temperature_c,
            "tideState": tide_state,
            "tide": {
                "state": tide_state,
                "label": TIDE_STATES[tide_state]["label"],
                "tailwaterM": tailwater_m,
                "source": TIDE_STATES[tide_state]["source"],
                "active": tailwater_m > 0.0,
            },
        },
        "schemes": {
            "a": {
                "key": "a",
                "label": sides[0].get("label") or "Scheme A",
                "planIds": sides[0].get("planIds") or [],
                "metrics": a,
                "wind": a["wind"],
            },
            "b": {
                "key": "b",
                "label": sides[1].get("label") or "Scheme B",
                "planIds": sides[1].get("planIds") or [],
                "metrics": b,
                "wind": b["wind"],
            },
        },
        "axes": axes,
        "dataCollection": data_collection,
        "windChannel": wind_channel,
        "combinedScore": None,
        "whyNoCombinedScore": (
            "No combined score, rank or pass/fail. The axes are in different "
            "units and trade against each other; collapsing them would hide the "
            "trade the comparison exists to show."
        ),
        "notes": [
            "Drainage, greenery and impervious share read the same ledger a live "
            "run scores.",
            "Flood extent is routed fill-and-spill, not a flood prediction.",
            "Wind is corridor geometry under the published prevailing inflow "
            "(NE/ENE/E). The window rose selects a headline frequency. FAD is "
            "not a velocity ratio, and SVR and LVR are not computed.",
            "Data collection names the existing envelopes and the planned "
            "catalog. It does not assess cumulative impact.",
        ] + ([
            "The surface-at-this-wind row is a screening allowance on top of "
            "the slider mean. Open cells cool more than sheltered cells. It "
            "is not a velocity ratio and not a microclimate solve.",
        ] if wind is not None else []),
    }


def rainfall_sensitivity(
    grids: Grids,
    features: list[dict[str, Any]],
    *,
    rainfall_mm: float,
    spread: float = 0.2,
) -> dict[str, Any]:
    """The same scheme's deficit at rainfall −spread, base, +spread.

    This is the one assumption the board lets a reader move. It re-runs the
    ledger the run uses -- no second physics, no fitted curve -- so the three
    numbers are three readings of one model rather than a range around a point.
    """
    if not 0.0 < spread < 1.0:
        raise ValueError("spread must be in (0, 1)")
    trial, cn_over, storage_over, applied, skipped = apply_interventions(
        grids, features)

    rows: list[dict[str, Any]] = []
    for label, factor in (("−%d%%" % round(spread * 100),
                           round(rainfall_mm * (1.0 - spread), 2)),
                          ("base", rainfall_mm),
                          ("+%d%%" % round(spread * 100),
                           round(rainfall_mm * (1.0 + spread), 2))):
        ledger = _scenario_ledger(grids, trial, cn_over, factor,
                                  storage_over or None)
        rows.append({
            "label": label,
            "rainfallMm": factor,
            "unstoredM3": round(float(ledger["unstoredM3"]), 1),
        })

    low, base, high = rows
    swing = round(float(high["unstoredM3"]) - float(low["unstoredM3"]), 1)
    return {
        "status": "SCREENING_SENSITIVITY_RAINFALL",
        "warning": (
            "One assumption moved, not an uncertainty analysis. Rainfall is "
            "scaled at the same curve numbers and storage; no other input is "
            "varied, and the three readings are not a confidence interval."
        ),
        "assumption": "rainfall depth",
        "spread": spread,
        "rows": rows,
        "swingM3": swing,
        "driver": (
            "Moving rainfall by ±%d%% moves this scheme's deficit by %s m³ "
            "across the three readings. The curve number and the storage "
            "capacity are held fixed." % (round(spread * 100),
                                          format(swing, ",.0f"))
        ),
        "applied": applied,
        "skipped": skipped,
    }
