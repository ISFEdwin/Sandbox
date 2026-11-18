"""The storm as a playhead, from the hourly march that already exists.

``GET /drainage/hourly`` returns the books hour by hour, but it returns them as
numbers. This module renders the *same* march as one PNG per hour so a playhead
can move on the map: the retained-depth field the loop already carries, written
with a fixed colour scale across all frames so a pond deepening is visible as a
pond deepening rather than as a rescale.

The simulation is not re-run. :func:`sandbox_model.hourly_storm_simulation` takes
an ``on_hour`` observer (added for this), and this module's observer collects the
depth field. There is one march, one mass balance, and the frames cannot
disagree with the totals.

**What a frame shows.** The retained/pool depth per cell -- the per-cell state
the march carries forward. The district's *standing* water is a scalar in the
existing model (see ``hourly_storm_simulation``), not a per-cell field, so it is
reported in the readout and not painted as if it had a location. The panel says
so; a map that invented a location would be the overclaim this project labels
away.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import numpy as np

from app.config import settings
from app.services.sandbox_model import (
    Grids,
    _runoff_and_unstored,  # noqa: F401  (re-exported context, kept explicit)
    hourly_storm_simulation,
)

PLAYBACK_STATUS = "SCREENING_STORM_PLAYBACK"
PLAYBACK_WARNING = (
    "Screening storm playback: retained water in the per-cell storage state, "
    "hour by hour. Not a flood prediction. The drainage rate is the DSD design "
    "standard used as a capability proxy, and standing water is reported as a "
    "district total because this model gives it no per-cell location."
)

# Depth ramp for the retained field. Fixed stops in metres, not normalised per
# frame: a pond that deepens must look deeper, and a shared scale is what makes
# two hours comparable.
_DEPTH_STOPS_M = (0.0, 0.02, 0.05, 0.10, 0.20, 0.40)
_DEPTH_COLOURS = (
    (70, 150, 220),
    (46, 160, 230),
    (30, 190, 225),
    (40, 220, 190),
    (120, 240, 140),
    (210, 255, 120),
)

# Below this the cell is not painted. The march spreads retained water over the
# whole catchment -- every cell carries a millimetre or two of film, so a ramp
# that started at 1 mm tinted the entire district and the map read as a coloured
# wash rather than as ponds. Five millimetres is the point where retained depth
# is a wet surface you could see; anything shallower is left transparent and the
# readout still reports it in the totals.
_MIN_PAINTED_DEPTH_M = 0.005


def _depth_rgba(depth: np.ndarray) -> np.ndarray:
    """Retained depth (m) to RGBA with a fixed metric scale."""
    stops = np.array(_DEPTH_STOPS_M, dtype=np.float64)
    colours = np.array(_DEPTH_COLOURS, dtype=np.float64)
    flat = np.clip(depth.reshape(-1).astype(np.float64), 0.0, stops[-1])
    rgb = np.stack([np.interp(flat, stops, colours[:, i]) for i in range(3)],
                   axis=1)
    # Transparent under the threshold, then a light tint that strengthens with
    # depth and saturates short of opaque so the terrain and buildings stay
    # readable underneath. Not a per-frame rescale: 3 cm should be as blue in
    # hour 2 as in hour 7.
    painted = flat >= _MIN_PAINTED_DEPTH_M
    alpha = np.where(
        painted,
        np.clip(0.12 + (flat - _MIN_PAINTED_DEPTH_M) * 3.0, 0.0, 0.82),
        0.0,
    ) * 255.0
    rgba = np.concatenate([rgb, alpha[:, None]], axis=1)
    return rgba.reshape(depth.shape + (4,)).astype(np.uint8)


def render_playback(
    grids: Grids,
    *,
    hyetograph_name: str | None = None,
    hyetograph: list[float] | None = None,
    initial_retention_fill: float = 0.0,
    drained_m3_per_hour: float | None = None,
    land_class_overrides: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run the hourly march once and write one PNG per hour.

    ``land_class_overrides`` is the scenario grid a scheme produced: when given,
    the march runs on it, so the playhead responds to the schemes on the table.
    The pool-capacity table is land-class driven, which is why this is the part
    of a scheme the hourly march can honestly carry; per-cell curve-number and
    storage overrides belong to the static ledger and are not silently mixed in.
    """
    from PIL import Image

    # A shallow copy of the frozen grid record with the scenario's land class.
    # `dataclasses.replace` would be the obvious call, but Grids is frozen and
    # carries arrays; constructing the replacement explicitly keeps it obvious
    # which fields the playback may change and which it may not.
    run_grids = grids
    if land_class_overrides is not None:
        run_grids = Grids(
            land_class=land_class_overrides,
            depth_m=grids.depth_m,
            accumulation=grids.accumulation,
            elevation_coarse=grids.elevation_coarse,
            elevation_5m=grids.elevation_5m,
            bounds=grids.bounds,
            rows=grids.rows,
            cols=grids.cols,
            cell_area_m2=grids.cell_area_m2,
            terrain_source=grids.terrain_source,
            landcover_source=grids.landcover_source,
            water_level_m=grids.water_level_m,
            runoff_m3=grids.runoff_m3,
            unstored_m3=grids.unstored_m3,
            wet_area_ha=grids.wet_area_ha,
            dem_shape=grids.dem_shape,
            receiver=grids.receiver,
            raw_elevation_5m=grids.raw_elevation_5m,
        )

    frames: dict[int, np.ndarray] = {}

    def collect(hour: int, depth: np.ndarray, _row: dict[str, Any]) -> None:
        frames[hour] = depth

    result = hourly_storm_simulation(
        run_grids,
        hyetograph=hyetograph,
        hyetograph_name=hyetograph_name,
        initial_retention_fill=initial_retention_fill,
        drained_m3_per_hour=drained_m3_per_hour,
        on_hour=collect,
    )
    if "error" in result:
        return result
    if result.get("status") == "ROUTING_UNAVAILABLE":
        return result

    out_dir = settings.rasters_dir / "storm"
    out_dir.mkdir(parents=True, exist_ok=True)
    playback_id = uuid.uuid4().hex[:8]

    hours: list[dict[str, Any]] = []
    for row in result.get("hourly") or []:
        hour = int(row["hour"])
        depth = frames.get(hour)
        url = None
        if depth is not None:
            name = f"{playback_id}_h{hour:02d}.png"
            Image.fromarray(_depth_rgba(depth), mode="RGBA").save(out_dir / name)
            url = settings.public_url(f"rasters/storm/{name}")
        hours.append({**row, "overlayUrl": url})

    (out_dir / f"{playback_id}.json").write_text(json.dumps({
        "artefact": "storm-playback",
        "playbackId": playback_id,
        "status": PLAYBACK_STATUS,
        "warning": PLAYBACK_WARNING,
        "hyetograph": result.get("hyetograph"),
        "massBalance": result.get("massBalance"),
        "frames": [
            {"hour": h["hour"], "overlayUrl": h["overlayUrl"]} for h in hours
        ],
    }, indent=2), encoding="utf-8")

    return {
        **result,
        "status": PLAYBACK_STATUS,
        "warning": PLAYBACK_WARNING,
        "playbackId": playback_id,
        "hours": hours,
        "frameNote": (
            "Each frame is that hour's retained water from the same hourly march, "
            "on one fixed colour scale; cells under 5 mm are left unpainted and the "
            "district standing volume is in the readout beside it."
        ),
    }
