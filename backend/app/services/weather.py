"""Where the storm input comes from, stated rather than implied.

The Huawei claim is that a real reading can drive the model, not that a slide
says so. This module gives the Run button two honest sources:

* **recorded** -- the project's own cited Hong Kong storm series
  (``REFERENCE_HYETOGRAPHS['hko_2023_09_07']``), whose shape is a reconstruction
  and whose peak hour (158.1 mm) is the published HKO HQ reading. Deterministic,
  offline, and re-runnable on a judge's laptop.
* **live** -- one attempt at the Hong Kong Observatory's public current-weather
  feed, with a short timeout. What HKO publishes there is rainfall **since
  midnight**, not an hourly intensity, so the reading is returned with
  ``usableAsIntensity: false`` rather than silently divided by an interval this
  project would have had to invent. If the feed is unreachable the response says
  which feed failed and offers the recorded trace.

The refusal is the point. Converting an accumulation into an intensity needs the
accumulation's start time and the gauge's interval; neither is in that payload.
A number produced by guessing them would be the exact overclaim the rest of this
project labels away.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.services.sandbox_model import DEFAULT_HYETOGRAPH, REFERENCE_HYETOGRAPHS

# HKO current weather report. Public, no key. Short timeout because the demo
# screen must not wait on a network that may be unavailable in a hall.
HKO_RHRREAD_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
    "?dataType=rhrread&lang=en"
)
LIVE_TIMEOUT_S = 4.0

RECORDED_TRACE_SOURCE = (
    "Recorded reference storm, not a live gauge. Peak hour from the HKO HQ "
    "reading of 158.1 mm (DEVB LegislCo reply 13896, July 2024); the hour-by-hour "
    "shape is the project's own reconstruction, as the committed hyetograph says."
)


def _recorded(hour: int | None = None) -> dict[str, Any]:
    """The cited storm series, read at its peak hour (or a stated hour)."""
    entry = REFERENCE_HYETOGRAPHS[DEFAULT_HYETOGRAPH]
    series = [float(v) for v in entry["mmPerHour"]]
    peak_hour = max(range(len(series)), key=lambda i: series[i])
    chosen = peak_hour if hour is None else max(0, min(len(series) - 1, hour))
    return {
        "mode": "recorded",
        "status": "RECORDED_REFERENCE_STORM",
        "usableAsIntensity": True,
        "rainfallMmHr": series[chosen],
        "sinceMidnightMm": None,
        "station": "HKO HQ (reference reading)",
        "observedAt": None,
        "hour": chosen,
        "hyetograph": {
            "name": DEFAULT_HYETOGRAPH,
            "label": entry["label"],
            "mmPerHour": series,
            "peakHour": peak_hour,
            "peakMmHr": series[peak_hour],
            "totalMm": round(sum(series), 1),
            "source": entry["source"],
        },
        "label": "Recorded reference storm — peak hour",
        "source": RECORDED_TRACE_SOURCE,
        "note": (
            "Applying the peak hour as a one-hour storm to the current scheme. "
            "This is a recorded reference, not a live gauge, and the hourly "
            "shape is a reconstruction rather than a gauge trace."
        ),
        "fallbackReason": None,
    }


def _live() -> dict[str, Any]:
    """One attempt at HKO's current report, or a stated failure.

    Never raises: a dead network is a reading the caller can display, not a 500.
    """
    try:
        with urllib.request.urlopen(HKO_RHRREAD_URL,
                                    timeout=LIVE_TIMEOUT_S) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "mode": "live",
            "status": "LIVE_FEED_UNAVAILABLE",
            "usableAsIntensity": False,
            "rainfallMmHr": None,
            "sinceMidnightMm": None,
            "station": None,
            "observedAt": None,
            "label": "HKO feed unavailable",
            "source": HKO_RHRREAD_URL,
            "note": (
                "The live feed could not be reached. The recorded reference "
                "storm remains available and re-runnable offline."
            ),
            "fallbackReason": f"{type(exc).__name__}: {exc}",
        }

    rainfall = ((payload.get("rainfall") or {}).get("data") or [])
    # Each entry is {"place": ..., "max": <mm since midnight>, "main": ...}.
    # `max` is an accumulation, not an intensity -- see the module docstring.
    readings: list[tuple[str, float]] = []
    for item in rainfall:
        try:
            readings.append((str(item.get("place") or "unknown"),
                             float(item.get("max"))))
        except (TypeError, ValueError):
            continue
    readings.sort(key=lambda pair: pair[1], reverse=True)
    place, since_midnight = readings[0] if readings else (None, None)

    return {
        "mode": "live",
        "status": "LIVE_HKO_ACCUMULATION_NOT_INTENSITY",
        "usableAsIntensity": False,
        "rainfallMmHr": None,
        "sinceMidnightMm": since_midnight,
        "station": place,
        "observedAt": payload.get("updateTime"),
        "label": "HKO rainfall since midnight",
        "source": HKO_RHRREAD_URL,
        "note": (
            "This is rainfall accumulated since midnight, not a one-hour "
            "intensity. It is shown as a live reading and is not converted into "
            "a storm input, because the payload does not carry the interval "
            "needed to do that honestly."
        ),
        "fallbackReason": None,
    }


def current_weather(mode: str = "recorded", hour: int | None = None) -> dict[str, Any]:
    """The labelled storm input for the Run button.

    ``mode`` is ``recorded`` (deterministic) or ``live`` (one HKO attempt). An
    unknown mode is refused by the router, not guessed at here.
    """
    if mode == "live":
        result = _live()
        if result["status"] == "LIVE_FEED_UNAVAILABLE":
            # Offer the deterministic input beside the failure so a demo can
            # continue, and say that this is what happened.
            result["recordedFallback"] = _recorded(hour)
        return result
    return _recorded(hour)
