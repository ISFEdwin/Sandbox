"""Demo surfaces that sit on the existing engine.

Three reads, no new hydrology:

* hourly frames are the precipitation-flow picture the live run already
  paints, one frame per hour of a named hyetograph;
* the gauge writes a labelled HKO observation (or the recorded 2023-09-07
  peak) into the rainfall and tide the Run button already sends;
* the sensitivity strip is ``storage_ledger`` at the current rainfall and
  at ±20%, nothing else.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parents[2]
for _extra in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from app.config import settings  # noqa: E402
from app.services.sandbox_model import (  # noqa: E402
    REFERENCE_HYETOGRAPHS,
    TIDE_STATES,
    Grids,
    _runoff_and_unstored,
    storage_ledger,
)
from make_wetgrid import flow_rgba, runoff_accumulation  # noqa: E402

HK = ZoneInfo("Asia/Hong_Kong")

# Wetland Park sits in the study area. Lau Fau Shan is the next station
# up the same coast if Wetland Park is marked missing ("M").
RAINFALL_STATIONS = ("Wetland Park", "Lau Fau Shan")
HOURLY_RAINFALL_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/hourlyRainfall.php?lang=en"
)
# Tsim Bei Tsui is the Deep Bay tide station nearest Hung Shui Kiu.
# HHOT is the predicted astronomical tide, not a measured water level.
TIDE_STATION = "TBT"
TIDE_PLACE = "Tsim Bei Tsui"
TIDE_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
    "?dataType=HHOT&lang=en&rformat=json&station=TBT"
    "&year={year}&month={month}&day={day}"
)
RECORDED_STORM = "hko_2023_09_07"
SCREENING_LINE = (
    "Not a flood prediction. Drainage rate is the DSD design standard. "
    "No pipe network."
)


def screening_tide_state(height_m: float) -> str:
    """Nearest of the three screening bins the run already accepts.

    The bins are the model's own tailwater steps (0 / 1.4 / 2.2 mCD), not a
    new tide scale. A height exactly halfway between two bins takes the
    lower name so the choice does not depend on dict order.
    """
    bins = tuple((name, float(spec["tailwaterM"])) for name, spec in TIDE_STATES.items())
    return min(bins, key=lambda item: (abs(height_m - item[1]), item[0]))[0]


def _get_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_hourly_rainfall(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The past-hour total at Wetland Park, else Lau Fau Shan.

    ``value`` is a string. ``M`` means the station is missing, which is
    skipped rather than treated as zero.
    """
    rows = payload.get("hourlyRainfall") or []
    by_name = {row.get("automaticWeatherStation"): row for row in rows}
    for place in RAINFALL_STATIONS:
        row = by_name.get(place)
        if not row:
            continue
        raw = str(row.get("value", "")).strip()
        if raw in {"", "M"}:
            continue
        return {
            "place": place,
            "stationId": row.get("automaticWeatherStationID"),
            "rainfallMm": float(raw),
            "observedAt": payload.get("obsTime"),
            "source": (
                "HKO Open Data hourlyRainfall.php — rainfall in the past "
                "hour at an automatic weather station. Provisional."
            ),
            "sourceUrl": HOURLY_RAINFALL_URL,
        }
    return None


def parse_tide_height(
    payload: dict[str, Any], month: int, day: int, hour: int
) -> float | None:
    """One hour's predicted height (m) from an HHOT day table."""
    fields = list(payload.get("fields") or [])
    key = f"{hour:02d}"
    if key not in fields:
        return None
    index = fields.index(key)
    for row in payload.get("data") or []:
        if int(row[0]) == month and int(row[1]) == day:
            return float(row[index])
    return None


def hk_tide_clock(now: datetime) -> tuple[int, int, int, int]:
    """Year, month, day and HHOT hour column (1–24) in Hong Kong time.

    Column 24 is the last hour of the civil day. Midnight belongs to the
    previous day's column 24, which is the hour that just ended.
    """
    local = now.astimezone(HK)
    if local.hour == 0:
        previous = local - timedelta(hours=1)
        return previous.year, previous.month, previous.day, 24
    return local.year, local.month, local.day, local.hour


def recorded_gauge() -> dict[str, Any]:
    """The cited peak hour of hko_2023_09_07.

    The peak (158.1 mm) is the published HKO HQ figure. The hour-by-hour
    shape around it is a reconstruction, which the source string already
    says. This trace has no tide.
    """
    storm = REFERENCE_HYETOGRAPHS[RECORDED_STORM]
    peak = max(float(value) for value in storm["mmPerHour"])
    body = {
        "mode": "recorded",
        "rainfallMm": peak,
        "place": "Hong Kong Observatory",
        "observedAt": "2023-09-07",
        "source": storm["source"],
        "sourceUrl": None,
        "tideState": None,
        "tideHeightM": None,
        "tidePlace": None,
        "tideObservedAt": None,
        "tideSource": None,
        "note": (
            "Recorded peak hour of hko_2023_09_07. Not a live feed. "
            "This trace does not include a tide."
        ),
        "fallback": None,
    }
    body["label"] = _gauge_label(body)
    return body


def _gauge_label(body: dict[str, Any]) -> str:
    rain = (
        f"{body['place']} {body['rainfallMm']:.1f} mm at {body['observedAt']}"
    )
    if body["mode"] == "recorded":
        text = f"Recorded trace · {rain}"
    else:
        text = f"Gauge · {rain}"
    if body.get("tideState") and body.get("tideHeightM") is not None:
        text += (
            f" · tide {body['tideState']} "
            f"({body['tidePlace']} {body['tideHeightM']:.2f} mCD, predicted)"
        )
    return text


def live_gauge(
    now: datetime,
    fetch: Callable[[str], dict[str, Any]] = _get_json,
) -> dict[str, Any]:
    rain_payload = fetch(HOURLY_RAINFALL_URL)
    rain = parse_hourly_rainfall(rain_payload)
    if rain is None:
        raise ValueError("HKO hourly rainfall had no usable station")
    year, month, day, hour = hk_tide_clock(now)
    tide_url = TIDE_URL.format(year=year, month=month, day=day)
    tide_height = None
    tide_source = None
    tide_at = None
    try:
        tide_payload = fetch(tide_url)
        tide_height = parse_tide_height(tide_payload, month, day, hour)
        if tide_height is not None:
            tide_source = (
                "HKO Open Data HHOT — predicted astronomical tide at "
                "Tsim Bei Tsui, not a measured water level."
            )
            tide_at = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00+08:00"
    except (OSError, urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError):
        tide_height = None
    body: dict[str, Any] = {
        "mode": "live",
        "rainfallMm": rain["rainfallMm"],
        "place": rain["place"],
        "observedAt": rain["observedAt"],
        "source": rain["source"],
        "sourceUrl": rain["sourceUrl"],
        "tideState": screening_tide_state(tide_height) if tide_height is not None else None,
        "tideHeightM": tide_height,
        "tidePlace": TIDE_PLACE if tide_height is not None else None,
        "tideObservedAt": tide_at,
        "tideSource": tide_source,
        "note": None,
        "fallback": None,
    }
    body["label"] = _gauge_label(body)
    return body


def gauge_reading(
    mode: str,
    *,
    now: datetime | None = None,
    fetch: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """``live`` reads HKO. ``recorded`` is the 2023-09-07 peak.

    A live failure returns the recorded trace and says why, so a quiet or
    unreachable feed still has a number a judge can re-run.
    """
    if mode == "recorded":
        return recorded_gauge()
    if mode != "live":
        return {"error": "mode must be 'live' or 'recorded'"}
    try:
        return live_gauge(now or datetime.now(HK), fetch or _get_json)
    except (OSError, urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
        recorded = recorded_gauge()
        recorded["fallback"] = (
            f"Live HKO feed unavailable ({type(exc).__name__}). "
            "Showing the recorded trace."
        )
        return recorded


def rainfall_sensitivity(
    grids: Grids, rainfall_mm: float, factor: float = 0.2
) -> dict[str, Any]:
    """Unstored volume at low, baseline and high rainfall.

    Each figure is ``storage_ledger``. The sentence reports how far the
    low and high settings sit from the baseline the engine returned.
    """
    if factor <= 0 or factor >= 1:
        return {"error": "factor must be between 0 and 1"}
    if rainfall_mm < 0:
        return {"error": "rainfallMm must be >= 0"}
    points = []
    for scale, name in ((1.0 - factor, "low"), (1.0, "baseline"), (1.0 + factor, "high")):
        mm = float(rainfall_mm) * scale
        ledger = storage_ledger(grids, grids.land_class, mm)
        points.append({
            "name": name,
            "scale": round(scale, 4),
            "rainfallMm": round(mm, 4),
            "unstoredM3": ledger["unstoredM3"],
        })
    base = points[1]["unstoredM3"]
    low = points[0]["unstoredM3"] - base
    high = points[2]["unstoredM3"] - base
    if abs(low) < 1.0 and abs(high) < 1.0:
        sentence = (
            f"Rainfall ±{factor:.0%} did not move the unstored volume "
            f"off {base:,.0f} m³."
        )
    else:
        sentence = (
            f"Rainfall ±{factor:.0%} moved the unstored volume by "
            f"{low:+,.0f} m³ at the low setting and {high:+,.0f} m³ at the "
            f"high setting (baseline {base:,.0f} m³)."
        )
    return {
        "assumption": "rainfall",
        "factor": factor,
        "baselineRainfallMm": float(rainfall_mm),
        "points": points,
        "deltas": {"lowM3": low, "highM3": high},
        "sentence": sentence,
        "source": "storage_ledger",
    }


def render_hourly_frames(
    grids: Grids, mm_per_hour: list[float], storm_name: str
) -> list[dict[str, Any]]:
    """One precipitation-flow PNG per hour, from that hour's unstored runoff.

    Same ``_runoff_and_unstored`` and ``runoff_accumulation`` the live run
    uses. Nothing here is fed back into the hourly mass balance.
    """
    if grids.receiver is None or grids.elevation_5m is None:
        return []
    out_dir = settings.rasters_dir / "hourly" / storm_name
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    for hour, mm in enumerate(mm_per_hour):
        _runoff_m, unstored_m = _runoff_and_unstored(grids.land_class, float(mm))
        flow = runoff_accumulation(
            grids.elevation_5m,
            grids.receiver,
            np.asarray(unstored_m, dtype=np.float64) * grids.cell_area_m2,
        )
        path = out_dir / f"h{hour:02d}.png"
        Image.fromarray(flow_rgba(flow), mode="RGBA").save(path)
        relative = path.relative_to(settings.data_dir).as_posix()
        frames.append({
            "hour": hour,
            "rainfallMm": round(float(mm), 2),
            "url": f"{settings.public_url(relative)}?h={hour}",
        })
    return frames
