"""The comparison board's acceptance tests (18 Nov 2026 edge 1).

The product claim is a broad-brush comparison across *separate* axes. These
tests pin the parts that make that claim honest:

1. Two schemes are read side by side, and no combined score exists.
2. Every row keeps its own unit; the delta is B - A.
3. A real intervention moves at least one axis, so the board is not a static
   table.
4. Tide is context applied to both, not an outcome either scheme controls.
5. The sensitivity strip re-runs the ledger and moves with rainfall.
6. The storm playhead's frames come from the same march, so its books balance.
7. The recorded gauge is usable and labelled; the live reading is never silently
   converted into an intensity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _extra in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from app.services import scene_service  # noqa: E402
from app.services.comparison import (  # noqa: E402
    COMPARISON_STATUS,
    compare_schemes,
    rainfall_sensitivity,
)
from app.services.sandbox_model import load_grids  # noqa: E402
from app.services.storm_playback import render_playback  # noqa: E402
from app.services.weather import current_weather  # noqa: E402


def _scene_id() -> str:
    ids = sorted(p.stem for p in (BACKEND_DIR / "data" / "scenes").glob("*.json"))
    assert ids, "no committed scene"
    return ids[0]


def _grids():
    grids = load_grids()
    assert grids is not None, "no ledger grid: run scripts/make_wetgrid.py"
    return grids


def _buildings(scene_id: str) -> list[dict]:
    model = scene_service.buildings_path(scene_id)
    assert model, "no city model: run scripts/build_buildings.py"
    return json.loads(Path(model).read_text())["features"]


def _band(grids, fraction: float) -> list[list[float]]:
    """A rectangle over the western ``fraction`` of the study area."""
    min_lon, min_lat, max_lon, max_lat = grids.bounds
    lon = min_lon + (max_lon - min_lon) * fraction
    return [
        [min_lon, min_lat],
        [lon, min_lat],
        [lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]


def _feature(kind: str, ring: list[list[float]]) -> dict:
    return {
        "id": f"f-{kind}",
        "intervention_type": kind,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "params": {},
    }


def _compare(grids, scene_id: str, a_features, b_features,
             rainfall_mm: float = 50.0) -> dict:
    sides = [
        {"key": "a", "label": "Today", "planIds": [], "features": a_features},
        {"key": "b", "label": "With storage", "planIds": [], "features": b_features},
    ]
    return compare_schemes(
        scene_id, grids, sides, _buildings(scene_id),
        rainfall_mm=rainfall_mm, temperature_c=30.0, tide_state="low",
    )


def test_two_schemes_are_read_without_a_combined_score() -> None:
    grids = _grids()
    scene_id = _scene_id()
    result = _compare(grids, scene_id, [], [])

    assert result["status"] == COMPARISON_STATUS
    assert result["combinedScore"] is None, "a combined score was invented"
    assert result["whyNoCombinedScore"], "no reason given for having no score"

    keys = [row["key"] for row in result["axes"]]
    for required in ("drainage", "floodExtent", "heat", "greenery",
                     "impervious", "wind", "tide"):
        assert required in keys, f"axis {required!r} missing from {keys}"
    assert not any("score" in key for key in keys), keys


def test_every_row_keeps_its_own_unit_and_the_delta_is_b_minus_a() -> None:
    grids = _grids()
    result = _compare(grids, _scene_id(), [], [])

    units = {row["key"]: row["unit"] for row in result["axes"]}
    assert units["drainage"] == "m³"
    assert units["floodExtent"] == "ha"
    assert units["heat"].startswith("index")
    assert units["greenery"] == "ha"
    assert units["impervious"] == "%"
    assert units["wind"] == "m"

    for row in result["axes"]:
        if row["a"] is None or row["b"] is None:
            assert row["delta"] is None
        else:
            assert row["delta"] == round(row["b"] - row["a"], 4), row


def test_a_real_intervention_moves_an_axis() -> None:
    grids = _grids()
    scene_id = _scene_id()
    storage = _feature("flood_storage", _band(grids, 0.05))
    result = _compare(grids, scene_id, [], [storage])

    moved = [row for row in result["axes"]
             if row["comparable"] and row["delta"] not in (None, 0.0)]
    assert moved, "a storage basin moved no axis: the board is static"
    drainage = next(r for r in result["axes"] if r["key"] == "drainage")
    assert drainage["delta"] is not None and drainage["delta"] < 0, (
        "a storage basin did not reduce the buffer deficit: %s" % drainage
    )
    assert result["schemes"]["b"]["metrics"]["applied"], (
        "the basin was skipped, so the comparison is of two empty schemes"
    )


def test_tide_is_context_for_both_not_an_outcome() -> None:
    grids = _grids()
    result = _compare(grids, _scene_id(), [], [])
    tide = next(r for r in result["axes"] if r["key"] == "tide")
    assert tide["comparable"] is False
    assert tide["a"] == tide["b"], "tide was scored as if a scheme changed it"
    assert tide["note"]


def test_wind_corridor_is_geometry_with_a_line_on_the_map() -> None:
    grids = _grids()
    result = _compare(grids, _scene_id(), [], [])
    wind = result["schemes"]["b"]["wind"]

    assert wind["status"] in ("WIND_CORRIDOR_GEOMETRY",
                              "WIND_CORRIDOR_UNAVAILABLE")
    if wind["status"] != "WIND_CORRIDOR_GEOMETRY":
        return  # scipy is an optional runtime; the refusal is honest.
    corridor = wind["corridor"]
    assert corridor and corridor["type"] == "LineString"
    assert len(corridor["coordinates"]) >= 2
    assert "not a velocity ratio" in (wind.get("warning") or "").lower()


def test_sensitivity_moves_the_ledger_with_rainfall() -> None:
    grids = _grids()
    result = rainfall_sensitivity(grids, [], rainfall_mm=50.0, spread=0.2)

    assert [r["label"] for r in result["rows"]] == ["−20%", "base", "+20%"]
    assert [r["rainfallMm"] for r in result["rows"]] == [40.0, 50.0, 60.0]
    low, base, high = (r["unstoredM3"] for r in result["rows"])
    assert low < base < high, (low, base, high)
    assert result["swingM3"] == round(high - low, 1)
    assert result["driver"]


def test_storm_playback_frames_share_the_same_books() -> None:
    grids = _grids()
    result = render_playback(grids, hyetograph_name="hko_2023_09_07")

    assert result.get("status") == "SCREENING_STORM_PLAYBACK", result
    assert result["massBalance"]["enforced"] is True
    assert abs(result["massBalance"]["residualM3"]) < 1e-6
    assert len(result["hours"]) == result["hours"][-1]["hour"] + 1
    assert all(h["overlayUrl"] for h in result["hours"]), (
        "an hour has no frame to draw"
    )


def test_recorded_gauge_is_usable_and_labelled() -> None:
    reading = current_weather(mode="recorded")
    assert reading["usableAsIntensity"] is True
    assert reading["rainfallMmHr"] == 158.1
    assert reading["hyetograph"]["name"] == "hko_2023_09_07"
    assert "not a live gauge" in reading["note"].lower() or \
        "not a live gauge" in reading["source"].lower()


def test_live_reading_is_never_silently_turned_into_an_intensity() -> None:
    """The live branch either fails or returns an accumulation, never a guess.

    This does not require the network: both outcomes satisfy the contract. What
    it forbids is a live payload being reported as an hourly intensity, which
    would need an interval the payload does not carry.
    """
    reading = current_weather(mode="live")
    if reading["status"] == "LIVE_FEED_UNAVAILABLE":
        assert reading["rainfallMmHr"] is None
        assert reading["recordedFallback"], "no offline fallback offered"
        return
    assert reading["usableAsIntensity"] is False
    assert reading["rainfallMmHr"] is None
    assert reading["sinceMidnightMm"] is not None


def test_depth_frames_do_not_paint_the_whole_catchment() -> None:
    """A millimetre film must not tint the district.

    The hourly march spreads retained water over every cell, so a ramp that
    started at the first non-zero depth painted the entire catchment and the map
    read as a flat wash rather than as ponds. Under the visible threshold a cell
    is transparent; above it alpha rises with depth, so a deepening pond reads as
    deepening, and it saturates instead of becoming an opaque wall.
    """
    import numpy as np  # noqa: PLC0415

    from app.services.storm_playback import (  # noqa: PLC0415
        _MIN_PAINTED_DEPTH_M,
        _depth_rgba,
    )

    field = np.array(
        [0.0, 0.002, _MIN_PAINTED_DEPTH_M - 1e-6, _MIN_PAINTED_DEPTH_M,
         0.03, 0.10, 0.40, 1.20],
        dtype=np.float64,
    ).reshape(2, 4)
    alpha = _depth_rgba(field)[..., 3]

    assert alpha[0, 0] == 0
    assert alpha[0, 1] == 0, "a 2 mm film must not be painted"
    assert alpha[0, 2] == 0, "just under the threshold is still unpainted"
    assert alpha[0, 3] > 0, "at the threshold the cell is painted"

    painted = [alpha[0, 3], alpha[1, 0], alpha[1, 1], alpha[1, 2], alpha[1, 3]]
    assert painted == sorted(painted), "deeper must not read as lighter"
    assert alpha[1, 3] == alpha[1, 2], "the ramp saturates at the top stop"
    assert alpha[1, 2] < 255, "saturated is not opaque: the terrain must show"
