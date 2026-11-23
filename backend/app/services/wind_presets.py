"""Named 10 m winds the screening can apply to the coarse channel.

The PlanD inlet is the site's own derived speed for the selected table. The
three signal presets are the onset of the Hong Kong Observatory's sustained
near-sea-level ranges, not a forecast for this study window and not a new
solve. A Signal 8 colouring multiplies the stored streamline speeds by
``onset / solved inlet``. The paths stay the annual coarse channel.

Sources, read 24 Nov 2026:

- Strong Wind Signal No. 3, 41–62 km/h, and Gale or Storm Signal No. 8,
  63–117 km/h: Hong Kong Observatory, "Reference for the Issue of No. 3 and
  No. 8 Signals", https://www.hko.gov.hk/en/informtc/tcsignal3_ref.htm
- Hurricane Signal No. 10, 118 km/h or above, and the same No. 3 and No. 8
  ranges: Hong Kong Observatory, Tropical Cyclones in 2024, Table 1.4,
  https://www.hko.gov.hk/en/publica/tc/tc2024/table14.html
"""

from __future__ import annotations

import json
from typing import Any

from app.config import settings

# Compass bearing the wind blows FROM. Matches the frontend rose.
BEARINGS_DEG: dict[str, float] = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
    "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
    "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
    "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}

# Onset of the sustained range, converted from the published km/h. The signal
# is a range; the preset uses the threshold the signal is defined by.
_KMH = 1.0 / 3.6
SIGNAL_SOURCE = "https://www.hko.gov.hk/en/publica/tc/tc2024/table14.html"
SIGNAL_3_SOURCE = "https://www.hko.gov.hk/en/informtc/tcsignal3_ref.htm"

PRESETS: dict[str, dict[str, Any]] = {
    "signal3": {
        "label": "HKO Signal 3",
        "speedMps": round(41.0 * _KMH, 3),
        "rangeKmh": "41–62",
        "sourceUrl": SIGNAL_3_SOURCE,
        "note": (
            "Onset of Strong Wind Signal No. 3: sustained 41 km/h near sea "
            "level, generally in Hong Kong. Not this site's measured wind."
        ),
    },
    "signal8": {
        "label": "HKO Signal 8",
        "speedMps": round(63.0 * _KMH, 3),
        "rangeKmh": "63–117",
        "sourceUrl": SIGNAL_SOURCE,
        "note": (
            "Onset of Gale or Storm Signal No. 8: sustained 63 km/h near sea "
            "level. The channel paths are not re-solved at this speed."
        ),
    },
    "signal10": {
        "label": "HKO Signal 10",
        "speedMps": round(118.0 * _KMH, 3),
        "rangeKmh": "118 and above",
        "sourceUrl": SIGNAL_SOURCE,
        "note": (
            "Onset of Hurricane Signal No. 10: sustained 118 km/h near sea "
            "level. Colour and the heat allowance use this speed. The lines "
            "are still the coarse annual paths."
        ),
    },
}

MANUAL_MIN_MPS = 0.5
MANUAL_MAX_MPS = 45.0


def pland_inlet(direction: str, season: str, height_m: int) -> float | None:
    """The derived 10 m inlet in the committed wind index, or None."""
    path = settings.data_dir / "openfoam" / "wind_index.json"
    if not path.exists():
        return None
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    table = ((index.get("tables") or {}).get(season) or {}).get(str(height_m)) or {}
    cell = (table.get("directions") or {}).get(direction) or {}
    speed = cell.get("inletSpeedMps")
    if isinstance(speed, (int, float)) and speed > 0:
        return float(speed)
    return None


def resolve_wind(
    *,
    direction: str | None,
    season: str | None = None,
    height_m: int | None = None,
    preset: str | None = None,
    speed_mps: float | None = None,
) -> dict[str, Any] | None:
    """The 10 m speed to apply, plus the PlanD inlet it is measured against.

    ``None`` when the caller did not ask for a wind, so a run that omits
    these fields keeps the heat field it had. An unknown preset is refused
    by the caller; this function returns a reason instead of guessing.
    """
    if direction is None and preset is None and speed_mps is None:
        return None
    name = (direction or "NE").upper()
    if name not in BEARINGS_DEG:
        return {"ok": False, "reason": f"windFrom {direction!r} is not a PlanD bearing"}
    season_name = season or "annual"
    if season_name not in ("annual", "summer", "winter"):
        return {"ok": False, "reason": f"windSeason {season!r} is not annual, summer or winter"}
    height = int(height_m or 500)
    if height not in (500, 300, 200):
        return {"ok": False, "reason": f"windHeightM {height_m!r} is not 500, 300 or 200"}
    reference = pland_inlet(name, season_name, height)
    chosen = (preset or "pland").lower()
    if chosen == "pland":
        speed = reference
        label = f"PlanD {season_name} {height} m"
        note = "The derived 10 m inlet for this table. PlanD does not publish that speed."
        source = None
    elif chosen == "manual":
        if speed_mps is None:
            return {"ok": False, "reason": "a manual wind needs windSpeedMps"}
        speed = float(speed_mps)
        if not MANUAL_MIN_MPS <= speed <= MANUAL_MAX_MPS:
            return {
                "ok": False,
                "reason": f"windSpeedMps must be {MANUAL_MIN_MPS}–{MANUAL_MAX_MPS}",
            }
        label = "Manual 10 m speed"
        note = "A speed you set. The channel paths are not re-solved at it."
        source = None
    elif chosen in PRESETS:
        speed = float(PRESETS[chosen]["speedMps"])
        label = PRESETS[chosen]["label"]
        note = PRESETS[chosen]["note"]
        source = PRESETS[chosen]["sourceUrl"]
    else:
        return {"ok": False, "reason": f"windPreset {preset!r} is not known"}
    if speed is None or reference is None:
        return {
            "ok": False,
            "reason": f"no PlanD 10 m inlet for {name} {season_name} {height} m",
        }
    return {
        "ok": True,
        "direction": name,
        "bearingDeg": BEARINGS_DEG[name],
        "season": season_name,
        "heightM": height,
        "preset": chosen,
        "label": label,
        "speedMps": round(float(speed), 3),
        "referenceSpeedMps": round(float(reference), 4),
        "scale": round(float(speed) / float(reference), 4),
        "note": note,
        "sourceUrl": source,
    }
