"""The selected wind moves the heat reading, and the signal presets stay published."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import scene_service  # noqa: E402
from app.services.comparison import compare_schemes  # noqa: E402
from app.services.sandbox_model import load_grids  # noqa: E402
from app.services.wind_presets import PRESETS, resolve_wind  # noqa: E402


def _scene_id() -> str:
    ids = sorted(p.stem for p in (BACKEND_DIR / "data" / "scenes").glob("*.json"))
    assert ids
    return ids[0]


def test_signal_presets_are_the_published_onsets() -> None:
    assert PRESETS["signal3"]["speedMps"] == round(41 / 3.6, 3)
    assert PRESETS["signal8"]["speedMps"] == round(63 / 3.6, 3)
    assert PRESETS["signal10"]["speedMps"] == round(118 / 3.6, 3)
    assert "hko.gov.hk" in PRESETS["signal3"]["sourceUrl"]
    assert "hko.gov.hk" in PRESETS["signal10"]["sourceUrl"]


def test_pland_east_inlet_resolves_and_a_signal_scales_above_it() -> None:
    pland = resolve_wind(direction="E", season="annual", height_m=500, preset="pland")
    assert pland is not None and pland["ok"] is True
    assert abs(pland["speedMps"] - 2.3009) < 1e-3
    assert pland["scale"] == 1.0
    signal = resolve_wind(direction="E", season="annual", height_m=500, preset="signal8")
    assert signal is not None and signal["ok"] is True
    assert signal["speedMps"] > pland["speedMps"]
    assert signal["referenceSpeedMps"] == pland["referenceSpeedMps"]
    refused = resolve_wind(direction="E", preset="manual")
    assert refused is not None and refused["ok"] is False


def test_a_faster_wind_cools_the_comparison_and_keeps_the_land_cover_index() -> None:
    grids = load_grids()
    assert grids is not None
    scene_id = _scene_id()
    buildings = json.loads(Path(scene_service.buildings_path(scene_id)).read_text())["features"]
    sides = [
        {"key": "a", "label": "Today", "planIds": [], "features": []},
        {"key": "b", "label": "Today", "planIds": [], "features": []},
    ]
    wind = resolve_wind(direction="E", season="annual", height_m=500, preset="signal3")
    assert wind is not None and wind["ok"]
    result = compare_schemes(
        scene_id, grids, sides, buildings,
        rainfall_mm=50.0, temperature_c=30.0, tide_state="low", wind=wind,
    )
    heat = next(row for row in result["axes"] if row["key"] == "heat")
    surface = next(row for row in result["axes"] if row["key"] == "windHeat")
    assert heat["unit"].startswith("index")
    assert surface["unit"] == "°C"
    assert surface["a"] is not None and surface["a"] < 30.0
    assert surface["a"] == surface["b"]
    assert result["combinedScore"] is None
    assert "not a velocity ratio" in result["notes"][-1] or surface["note"]


def test_the_heat_picture_keeps_the_shift_below_the_slider() -> None:
    import numpy as np

    from app.services.run_service import _heat_picture

    picture = _heat_picture({
        "surfaceC": np.array([[28.0, 27.0]], dtype=np.float32),
        "scenarioMeanC": 30.0,
        "meanSurfaceC": 27.5,
    })
    assert float(picture.mean()) == -2.5
