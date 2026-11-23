"""The comparison board's routes: two schemes, five axes, no verdict.

Kept out of ``routers/scenes.py`` so the scene router keeps its shape (scene,
terrain, overlays, runs) and this file owns the demo's comparison surface:
the board, its one sensitivity knob, the wind corridor's sidecar, the storm
playhead and the labelled gauge.

Every response repeats what it is not. That is not decoration: these routes are
what a judge sees during the pitch, and a number on screen without its caveat is
the one mistake this project has consistently refused to make.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.routers.scenes import (
    _require_buildings,
    _require_grids,
    intervention_features_many,
)
from app.services import scene_service
from app.services.sandbox_model import (
    DEFAULT_RAINFALL_MM,
    TIDE_STATES,
    apply_interventions,
)
from app.services.run_service import MAX_RAINFALL_MM
from app.services.wind_diagnostic import shelter_diagnostic

router = APIRouter()

DEFAULT_TEMPERATURE_C = 30.0
DEFAULT_TIDE_STATE = "low"


def _rainfall(body: dict[str, Any]) -> float:
    value = body.get("rainfallMm", body.get("rainfall_mm", DEFAULT_RAINFALL_MM))
    try:
        rainfall = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422,
                            detail=f"rainfallMm must be a number, got {value!r}") from None
    if not 0.0 <= rainfall <= MAX_RAINFALL_MM:
        raise HTTPException(
            status_code=422,
            detail=f"rainfallMm must be 0-{MAX_RAINFALL_MM:.0f}, got {rainfall}",
        )
    return rainfall


def _tide(body: dict[str, Any]) -> str:
    state = str(body.get("tideState", body.get("tide_state", DEFAULT_TIDE_STATE)))
    if state not in TIDE_STATES:
        raise HTTPException(
            status_code=422,
            detail=f"tideState must be one of {sorted(TIDE_STATES)}, got {state!r}",
        )
    return state


def _side(body: dict[str, Any], key: str, fallback_label: str) -> dict[str, Any]:
    raw = body.get(key)
    if raw is None:
        raw = body.get(f"{key}PlanIds") or {}
        raw = {"planIds": raw} if isinstance(raw, list) else {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=422,
                            detail=f"{key!r} must be an object with planIds")
    plan_ids = [str(p) for p in (raw.get("planIds") or raw.get("plan_ids") or [])
                if p]
    # Nothing is compared that the caller did not name: a plan id that does not
    # exist yields no features, and the response would quietly describe "today".
    # Resolving through the same helper a run uses means a bad id simply has no
    # interventions, which is what the run would do too -- stated here, not hidden.
    features = intervention_features_many(plan_ids)
    return {
        "key": key,
        "label": str(raw.get("label") or fallback_label),
        "planIds": plan_ids,
        "features": features,
    }


@router.post("/scenes/{scene_id}/compare-schemes")
def post_compare_schemes(scene_id: str, body: dict) -> dict:
    """POST /api/scenes/{sceneId}/compare-schemes

    Two schemes on one set of axes. Request body::

        {
          "a": {"planIds": [], "label": "Today"},
          "b": {"planIds": ["..."], "label": "HSK Park + MTR"},
          "rainfallMm": 450, "temperatureC": 30, "tideState": "low"
        }

    ``a`` and ``b`` are scored against the same baseline and the same storm.
    The response's rows keep their own units and ``combinedScore`` is null on
    every call -- the axis-by-axis read is the product, not a ranking.

    The wind corridor is returned as a GeoJSON LineString per scheme, so the map
    can draw the same walk the row reports rather than a second computation.
    """
    from app.services.comparison import compare_schemes

    scene_service.get_scene(scene_id)
    grids = _require_grids()
    buildings = _require_buildings(scene_id)

    rainfall_mm = _rainfall(body)
    tide_state = _tide(body)
    try:
        temperature_c = float(body.get("temperatureC",
                                       body.get("temperature_c",
                                                DEFAULT_TEMPERATURE_C)))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422,
                            detail="temperatureC must be a number") from None

    sides = [_side(body, "a", "Scheme A"), _side(body, "b", "Scheme B")]
    return compare_schemes(
        scene_id,
        grids,
        sides,
        buildings,
        rainfall_mm=rainfall_mm,
        temperature_c=temperature_c,
        tide_state=tide_state,
    )


@router.get("/scenes/{scene_id}/data-collection")
def get_data_collection(scene_id: str) -> dict:
    """GET /api/scenes/{sceneId}/data-collection

    The projects and the wind regime the committed files can name, with the
    duties those names are answering. Existing envelopes and planned catalog
    rows are listed. Committed projects are not held, and the response says
    so. Site and local velocity ratios are null.

    This is the data-collection inventory Guidance Note 6/2023 paragraph 21
    asks for. It is not the cumulative assessment that follows it, and it is
    not an air ventilation assessment.
    """
    from app.services.data_collection import collect

    return collect(scene_id)


@router.post("/scenes/{scene_id}/sensitivity")
def post_sensitivity(scene_id: str, body: dict) -> dict:
    """POST /api/scenes/{sceneId}/sensitivity

    One assumption moved: rainfall at ±20% (or a caller's ``spread``), holding
    curve number and storage fixed. Three ledger readings, one sentence on what
    moved. This is a sensitivity, never an uncertainty analysis.
    """
    from app.services.comparison import rainfall_sensitivity

    scene_service.get_scene(scene_id)
    grids = _require_grids()

    rainfall_mm = _rainfall(body)
    plan_ids = [str(p) for p in (body.get("planIds") or []) if p]
    features = intervention_features_many(plan_ids)
    try:
        spread = float(body.get("spread", 0.2))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="spread must be a number") from None

    try:
        result = rainfall_sensitivity(grids, features,
                                      rainfall_mm=rainfall_mm, spread=spread)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    result["sceneId"] = scene_id
    result["planIds"] = plan_ids
    return result


@router.post("/scenes/{scene_id}/ventilation/diagnostic")
def post_ventilation_diagnostic(scene_id: str, body: dict) -> dict:
    """POST /api/scenes/{sceneId}/ventilation/diagnostic

    The district's geometric shelter index for one prevailing inflow direction,
    plus a PNG to drape. A sidecar to the corridor line, for when one line is too
    thin to read as a channel. Not a speed field, and the response says so.
    """
    from app.services.design_metrics import footprints_from_geojson

    scene_service.get_scene(scene_id)
    grids = _require_grids()
    buildings = _require_buildings(scene_id)

    direction = str(body.get("direction", "NE")).upper()
    footprints = footprints_from_geojson(buildings)

    # A scheme's massing joins today's city, the same way the corridor does.
    plan_ids = [str(p) for p in (body.get("planIds") or []) if p]
    features = intervention_features_many(plan_ids)
    from app.services.design_metrics import footprint_from_ring
    from app.services.run_service import _massing_overrides

    for override in _massing_overrides(features):
        fp = footprint_from_ring(override.get("ring"),
                                 override.get("heightM") or 0)
        if fp is not None:
            footprints.append(fp)

    try:
        result = shelter_diagnostic(grids, footprints, direction=direction)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    result["sceneId"] = scene_id
    result["planIds"] = plan_ids
    return result


@router.post("/scenes/{scene_id}/storm/playback")
def post_storm_playback(scene_id: str, body: dict) -> dict:
    """POST /api/scenes/{sceneId}/storm/playback

    The named hourly storm rendered as one PNG per hour, for a playhead on the
    map. The march is the existing one; this route only renders its frames.

    ``planIds`` runs the march on the composed scheme's land class, so the
    playhead responds to the schemes on the table. Per-cell curve-number and
    storage overrides are not carried into the hourly march -- it is land-class
    driven -- and the response's ``frameNote`` says so rather than implying the
    static ledger and the playback are the same arithmetic.
    """
    from app.services.storm_playback import render_playback

    scene_service.get_scene(scene_id)
    grids = _require_grids()

    plan_ids = [str(p) for p in (body.get("planIds") or []) if p]
    features = intervention_features_many(plan_ids)
    trial = None
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if features:
        trial, _cn, _storage, applied, skipped = apply_interventions(grids, features)

    try:
        fill = float(body.get("initialRetentionFill", 0.0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422,
                            detail="initialRetentionFill must be a number") from None

    drained = body.get("drainedM3PerHour")
    if drained is not None:
        try:
            drained = float(drained)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422,
                                detail="drainedM3PerHour must be a number") from None
    elif body.get("noDrainage") is True:
        drained = 0.0

    result = render_playback(
        grids,
        hyetograph_name=body.get("hyetographName") or body.get("hyetograph_name"),
        initial_retention_fill=fill,
        drained_m3_per_hour=drained,
        land_class_overrides=trial,
    )
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    result["sceneId"] = scene_id
    result["planIds"] = plan_ids
    result["interventionsApplied"] = applied
    result["interventionsSkipped"] = skipped
    return result


@router.get("/scenes/{scene_id}/weather/current")
def get_weather_current(
    scene_id: str,
    mode: str = Query("recorded", pattern="^(recorded|live)$"),
    hour: int | None = Query(None, ge=0, le=23),
) -> dict:
    """GET /api/scenes/{sceneId}/weather/current?mode=recorded|live

    A labelled storm input for the Run button. ``recorded`` is the project's
    cited reference series and is deterministic; ``live`` makes one short attempt
    at HKO's public report and returns the reading with its own units. The live
    payload is an accumulation since midnight, so it is never silently turned
    into an intensity -- see ``services/weather.py``.
    """
    from app.services.weather import current_weather

    scene_service.get_scene(scene_id)
    result = current_weather(mode=mode, hour=hour)
    result["sceneId"] = scene_id
    result["tide"] = {
        "state": DEFAULT_TIDE_STATE,
        "label": TIDE_STATES[DEFAULT_TIDE_STATE]["label"],
        "tailwaterM": float(TIDE_STATES[DEFAULT_TIDE_STATE]["tailwaterM"]),
        "note": ("Tide stays a stated screening condition applied by the run; "
                 "this endpoint supplies the rainfall input only."),
    }
    result["staticBase"] = settings.static_base_url
    return result
