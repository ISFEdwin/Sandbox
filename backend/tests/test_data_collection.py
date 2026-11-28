"""Data collection and the wind-channel comparison.

Guidance Note 6/2023 paragraph 21 requires the projects in the vicinity to be
named at data collection. Technical Circular 1/06 requires a comparison of
options and defines SVR and LVR from pedestrian test points. These tests pin
both: the inventory names what the files hold, and the velocity ratios stay
empty.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = BACKEND_DIR / "scripts"
for _extra in (BACKEND_DIR, SCRIPTS):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from fetch_site_wind import merge_roses  # noqa: E402

from app.services import scene_service  # noqa: E402
from app.services.comparison import compare_schemes  # noqa: E402
from app.services.data_collection import (  # noqa: E402
    SCREENING_LABEL,
    STATUS,
    WIND_CHANNEL_STATUS,
    collect,
    live_duties,
)
from app.services.design_metrics import Footprint  # noqa: E402
from app.services.sandbox_model import load_grids  # noqa: E402
from app.services.ventilation import (  # noqa: E402
    least_cost_corridors,
    window_direction_frequencies,
)


def _scene_id() -> str:
    ids = sorted(p.stem for p in (BACKEND_DIR / "data" / "scenes").glob("*.json"))
    assert ids, "no committed scene"
    return ids[0]


def _buildings(scene_id: str) -> list[dict]:
    model = scene_service.buildings_path(scene_id)
    assert model
    return json.loads(Path(model).read_text())["features"]


def test_merge_roses_is_an_area_weighted_mean() -> None:
    band = {
        "bin": "00_to_01",
        "speedLowMps": 0,
        "speedHighMps": 1,
        "occurrenceByDirection": {"N": 1.0, "E": 0.0},
    }
    other = {
        "bin": "00_to_01",
        "speedLowMps": 0,
        "speedHighMps": 1,
        "occurrenceByDirection": {"N": 0.0, "E": 1.0},
    }
    # The helper expects the canonical 16 names. Build them from the two.
    names = (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    )

    def full(seed: dict[str, float]) -> dict[str, float]:
        return {name: float(seed.get(name, 0.0)) for name in names}

    left_freq = full({"N": 1.0})
    right_freq = full({"E": 1.0})
    left_bin = dict(band, occurrenceByDirection=full({"N": 1.0}))
    right_bin = dict(other, occurrenceByDirection=full({"E": 1.0}))
    merged = merge_roses([
        {"weightM2": 1.0, "frequencyByDirection": left_freq, "speedBins": [left_bin]},
        {"weightM2": 3.0, "frequencyByDirection": right_freq, "speedBins": [right_bin]},
    ])
    assert merged["frequencyByDirection"]["N"] == 0.25
    assert merged["frequencyByDirection"]["E"] == 0.75
    assert abs(merged["frequencySum"] - 1.0) < 1e-6


def test_window_rose_covers_the_four_cells_and_matches_the_centroid() -> None:
    window = json.loads(
        (BACKEND_DIR / "data" / "reference" / "hsk_site_wind_window.json").read_text()
    )
    centroid = json.loads(
        (BACKEND_DIR / "data" / "reference" / "hsk_site_wind.json").read_text()
    )
    assert window["verified"] is True
    assert window["gridCellIds"] == ["3462", "3463", "3559", "3560"]
    shares = [cell["weightShare"] for cell in window["cells"]]
    assert abs(sum(shares) - 1.0) < 1e-4
    cell = next(cell for cell in window["cells"] if cell["gridCellId"] == "3463")
    published = centroid["seasons"]["annual"]["heightsM"]["500"]["frequencyByDirection"]
    assert cell["frequencyByDirection"]["NE"] == published["NE"]
    assert cell["frequencyByDirection"]["E"] == published["E"]
    merged = window["merged"]["frequencyByDirection"]
    assert abs(sum(merged.values()) - window["merged"]["frequencySum"]) < 1e-4
    # E outranks NE on every cell the window touches, so the merge cannot
    # flip back to the centroid's narrative that NE is the headline.
    assert merged["E"] > merged["NE"]


def test_inventory_names_existing_and_planned_and_not_committed() -> None:
    record = collect(_scene_id())
    assert record["status"] == STATUS
    assert record["screeningLabel"] == SCREENING_LABEL
    assert record["notADetermination"] is True
    assert record["furtherInformation"], "a missing fact was not listed"
    classes = {row["class"] for row in record["inventory"]}
    assert classes == {"existing", "planned"}
    assert "committed" in record["classesNotHeld"]
    names = {row["name"] for row in record["inventory"]}
    assert "HSK Park" in names
    assert "HSK MTR station" in names
    existing = next(row for row in record["inventory"] if row["class"] == "existing")
    assert existing["count"] == 396
    duty_ids = {duty["id"] for duty in record["duties"]}
    assert "gn6.2023.s21" in duty_ids
    assert "eiao.tm.4.4.3" in duty_ids
    assert "tc106.annexA.para30" in duty_ids
    assert "gn6.2010.s21" not in duty_ids
    assert "gn6.2010.s21" in record["supersededNotApplied"]
    assert all(duty.get("live") is True for duty in live_duties())
    quote = next(duty["quote"] for duty in record["duties"] if duty["id"] == "gn6.2023.s21")
    assert "identified during data collection stage" in quote
    inflow = record["windInflow"]
    assert inflow["verified"] is True
    assert inflow["headlineDirection"] == "E"
    assert inflow["cellIds"] == ["3462", "3463", "3559", "3560"]


def test_wind_channel_compares_options_and_does_not_invent_a_velocity_ratio() -> None:
    scene_id = _scene_id()
    grids = load_grids()
    assert grids is not None
    sides = [
        {"key": "a", "label": "Today", "planIds": [], "features": []},
        {"key": "b", "label": "Today", "planIds": [], "features": []},
    ]
    result = compare_schemes(
        scene_id, grids, sides, _buildings(scene_id),
        rainfall_mm=50.0, temperature_c=30.0, tide_state="low",
    )
    channel = result["windChannel"]
    assert channel["status"] == WIND_CHANNEL_STATUS
    assert channel["notAnAva"] is True
    assert channel["velocityRatio"]["svr"] is None
    assert channel["velocityRatio"]["lvr"] is None
    assert "not that ratio" in channel["velocityRatio"]["reason"]
    directions = [row["direction"] for row in channel["options"]]
    assert directions == ["NE", "ENE", "E"]
    ne = channel["options"][0]
    assert ne["frequency"] is not None
    assert ne["aFirstObstructionMeanM"] == ne["bFirstObstructionMeanM"]
    assert result["dataCollection"]["screeningLabel"] == SCREENING_LABEL
    assert result["combinedScore"] is None
    east = channel["east"]
    assert east["status"] == "EAST_CHANNEL_WINDOW_HEADLINE"
    assert east["direction"] == "E"
    assert east["notAVelocity"] is True
    assert east["annualRank"] == 1
    assert east["annualOf"] == 16
    by_season = {row["season"]: row for row in east["seasons"]}
    assert by_season["summer"]["rank"] == 7
    assert by_season["summer"]["leadingDirection"] == "SSW"
    assert by_season["winter"]["rank"] == 2
    assert by_season["winter"]["leadingDirection"] == "NE"
    assert abs(by_season["annual"]["frequency"] - 0.150531) < 1e-6
    assert abs(by_season["summer"]["frequency"] - 0.065346) < 1e-6
    assert abs(by_season["winter"]["frequency"] - 0.188246) < 1e-6
    assert [cell["gridCellId"] for cell in east["cells"]] == ["3462", "3463", "3559", "3560"]
    assert east["centroid"]["gridCellId"] == "3463"
    assert east["centroid"]["inletSpeedMps"] == 2.3009
    # The count is the sidecar's, not a fixed number: the channel is re-solved
    # at a different mesh from time to time, and the contract is that the API
    # reports what was actually solved.
    sidecar = json.loads(
        (BACKEND_DIR / "data" / "openfoam" / "channel_sidecar.json").read_text(encoding="utf-8")
    )
    assert east["solvedStreamlineCount"] == sidecar["directions"]["E"]
    assert east["solvedOnRequestPath"] is False
    assert east["scheme"]["a"]["firstObstructionMeanM"] == east["scheme"]["b"]["firstObstructionMeanM"]
    assert east["scheme"]["b"]["pathLengthM"] is not None
    assert "leads the 16 directions" in east["reading"]
    assert "behind SSW" in east["reading"]
    assert any(source.get("url") for source in east["sources"])


def test_window_weights_select_the_headline_and_do_not_enter_the_cost() -> None:
    class _Grid:
        rows = 4
        cols = 4
        cell_area_m2 = 25.0

        def cell_of(self, lon, lat):
            return int(lat), int(lon)

    weights = window_direction_frequencies()
    assert abs(sum(weights.values()) - 0.998701) < 1e-4
    grid = _Grid()
    footprint = [Footprint(1.0, 1.0, 8.0, 8.0, 12.0)]
    plain = least_cost_corridors(
        footprint, grid, directions={"NE": 45.0, "E": 90.0},
    )
    picked = least_cost_corridors(
        footprint, grid, directions={"NE": 45.0, "E": 90.0},
        direction_weights=weights,
        weight_source="PlanD site wind window, annual, 500 m, area-weighted",
    )
    assert picked["directionWeights"]["selectedDirection"] == "E"
    assert "window" in picked["directionWeights"]["limitation"]
    assert plain["directions"]["NE"]["meanCost"] == picked["directions"]["NE"]["meanCost"]
