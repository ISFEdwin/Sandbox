#!/usr/bin/env python
"""Storm frames, the HKO gauge, and the rainfall sensitivity strip.

The numbers come from the existing engine. A frame is that hour's unstored
runoff painted with the live run's own colour ramp. The gauge either parses
an HKO payload or returns the cited 2023-09-07 peak. The strip's three
unstored volumes are ``storage_ledger`` calls, and the sentence's deltas
are those volumes minus the baseline.

Run from backend/: python tests/test_demo_features.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (BACKEND_DIR, BACKEND_DIR / "scripts", BACKEND_DIR / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app.services.demo_features import (  # noqa: E402
    SCREENING_LINE,
    gauge_reading,
    hk_tide_clock,
    parse_hourly_rainfall,
    parse_tide_height,
    rainfall_sensitivity,
    recorded_gauge,
    render_hourly_frames,
    screening_tide_state,
)
from app.services.sandbox_model import (  # noqa: E402
    REFERENCE_HYETOGRAPHS,
    hourly_storm_simulation,
    load_grids,
    storage_ledger,
)
from app.routers.scenes import get_drainage_hourly  # noqa: E402

SCENE = "51e03c37-5360-43b0-a094-fbaca38cd70b"
PASSED = 0
FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  PASS  {label}" + (f" -- {detail}" if detail else ""))
    else:
        FAILED += 1
        print(f"  FAIL  {label}" + (f" -- {detail}" if detail else ""))


def test_tide_bins() -> None:
    check("0.0 mCD is the low screening bin", screening_tide_state(0.0) == "low")
    check("1.4 mCD is the mean screening bin", screening_tide_state(1.4) == "mean")
    check("2.2 mCD is the high screening bin", screening_tide_state(2.2) == "high")
    # 0.90 is closer to 1.4 than to 0.0.
    check("0.90 mCD bins to mean", screening_tide_state(0.90) == "mean")


def test_recorded_gauge_is_the_cited_peak() -> None:
    storm = REFERENCE_HYETOGRAPHS["hko_2023_09_07"]
    reading = recorded_gauge()
    check(
        "recorded rainfall is the published peak, not a typed stand-in",
        reading["rainfallMm"] == max(storm["mmPerHour"]) == 158.1,
    )
    check("recorded mode names the date and is not live",
          reading["mode"] == "recorded" and reading["observedAt"] == "2023-09-07")
    check("recorded source is the hyetograph citation",
          reading["source"] == storm["source"] and "158.1" in reading["source"])
    check("recorded trace does not invent a tide", reading["tideState"] is None)
    check("the label says recorded trace", reading["label"].startswith("Recorded trace"))


def test_parsers() -> None:
    rain = parse_hourly_rainfall({
        "obsTime": "2026-11-18T10:15:00+08:00",
        "hourlyRainfall": [
            {"automaticWeatherStation": "Wetland Park",
             "automaticWeatherStationID": "RF002", "value": "M", "unit": "mm"},
            {"automaticWeatherStation": "Lau Fau Shan",
             "automaticWeatherStationID": "RF001", "value": "12", "unit": "mm"},
        ],
    })
    check("a missing Wetland Park reading falls through to Lau Fau Shan",
          rain is not None and rain["place"] == "Lau Fau Shan" and rain["rainfallMm"] == 12.0)
    kept = parse_hourly_rainfall({
        "obsTime": "2026-11-18T10:15:00+08:00",
        "hourlyRainfall": [
            {"automaticWeatherStation": "Wetland Park",
             "automaticWeatherStationID": "RF002", "value": "4", "unit": "mm"},
        ],
    })
    check("Wetland Park wins when it has a number",
          kept is not None and kept["place"] == "Wetland Park" and kept["rainfallMm"] == 4.0)
    height = parse_tide_height(
        {"fields": ["MM", "DD", "10"], "data": [["11", "18", "0.90"]]},
        11, 18, 10,
    )
    check("HHOT hour column is the predicted height", height == 0.90)
    when = datetime(2026, 11, 18, 2, 32, tzinfo=ZoneInfo("UTC"))  # 10:32 HKT
    check("Hong Kong clock selects the HHOT hour column",
          hk_tide_clock(when) == (2026, 11, 18, 10))


def test_live_gauge_uses_the_fetcher() -> None:
    def fetch(url: str) -> dict:
        if "hourlyRainfall" in url:
            return {
                "obsTime": "2026-11-18T10:15:00+08:00",
                "hourlyRainfall": [{
                    "automaticWeatherStation": "Wetland Park",
                    "automaticWeatherStationID": "RF002",
                    "value": "6", "unit": "mm",
                }],
            }
        return {"fields": ["MM", "DD", "10"], "data": [["11", "18", "0.90"]]}

    reading = gauge_reading(
        "live",
        now=datetime(2026, 11, 18, 2, 32, tzinfo=ZoneInfo("UTC")),
        fetch=fetch,
    )
    check("live rainfall is the station value", reading["rainfallMm"] == 6.0)
    check("live tide is the nearest screening bin", reading["tideState"] == "mean")
    check("live label names the station and the time",
          "Wetland Park" in reading["label"] and "2026-11-18T10:15:00+08:00" in reading["label"])
    check("a dead feed falls back to the recorded peak and says so",
          gauge_reading("live", fetch=lambda _url: (_ for _ in ()).throw(OSError("down")))["fallback"]
          and gauge_reading(
              "live", fetch=lambda _url: (_ for _ in ()).throw(OSError("down"))
          )["rainfallMm"] == 158.1)


def test_sensitivity_is_the_ledger() -> None:
    grids = load_grids()
    check("grids load", grids is not None)
    if grids is None:
        return
    report = rainfall_sensitivity(grids, 50.0, 0.2)
    expected = [
        storage_ledger(grids, grids.land_class, mm)["unstoredM3"]
        for mm in (40.0, 50.0, 60.0)
    ]
    got = [point["unstoredM3"] for point in report["points"]]
    check("the three volumes are storage_ledger, not typed", got == expected, str(got))
    base = expected[1]
    check(
        "the sentence moves by the amount the engine returns",
        report["deltas"]["lowM3"] == expected[0] - base
        and report["deltas"]["highM3"] == expected[2] - base
        and f"{report['deltas']['lowM3']:+,.0f}" in report["sentence"],
    )
    check("low and high disagree with the baseline",
          expected[0] != base and expected[2] != base)


def test_playback_frames_and_mass_balance() -> None:
    grids = load_grids()
    if grids is None:
        check("grids load", False)
        return
    storm = hourly_storm_simulation(grids, hyetograph_name="hko_2023_09_07")
    check("mass balance is still enforced",
          storm["massBalance"]["enforced"] is True and storm["massBalance"]["residualM3"] == 0.0)
    frames = render_hourly_frames(
        grids, storm["hyetograph"]["mmPerHour"], storm["hyetograph"]["name"]
    )
    check("one frame per hour of the named storm",
          len(frames) == storm["hours"] == 8)
    check("the frame names the storm and the hour",
          all("hko_2023_09_07" in frame["url"] for frame in frames)
          and [frame["hour"] for frame in frames] == list(range(8)))
    check("hour 4 is the 158.1 mm peak", frames[4]["rainfallMm"] == 158.1)
    route = get_drainage_hourly(SCENE, hyetograph_name="hko_2023_09_07")
    check("the route keeps the screening line and the storm name",
          route["screeningLine"] == SCREENING_LINE
          and route["hyetograph"]["name"] == "hko_2023_09_07"
          and len(route["frames"]) == 8
          and route["frames"][4]["standingM3"] == route["hourly"][4]["standingM3"])


def main() -> int:
    test_tide_bins()
    test_recorded_gauge_is_the_cited_peak()
    test_parsers()
    test_live_gauge_uses_the_fetcher()
    test_sensitivity_is_the_ledger()
    test_playback_frames_and_mass_balance()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
