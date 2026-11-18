"""A second wind reading for when the corridor line is too thin.

The corridor is one line. If a judge cannot read it as a channel, this sidecar
adds a field over the whole district: for every cell, how much of the upwind
path is blocked by massing. It is computed by marching rays over the same height
raster the corridor walker and the sky-view factor use -- no new geometry, no
fitted coefficients, no second definition of a building.

**What this is, and what it deliberately is not.** It is a *shelter index*: the
fraction of upwind cells that contain a building, in ``[0, 1]``. It is not a
wind speed, a velocity ratio, or a Röckle (1990) field. A Röckle field needs
displacement, wake and street-canyon coefficients; producing one here would mean
inventing the coefficients and then presenting the result as if it were URock's.
The external check for this screen is a URock or ``pyqes`` run on one fixture,
kept outside this repository (both are GPL). No GPL source is vendored, and no
speed number is claimed.

The inflow is the published prevailing direction for Hung Shui Kiu (Planning
Department Site Wind Availability Data on CSDI, dataset
``pland_rcd_1634281652589_43389``: NE / ENE / E). The diagnostic reports which
direction it marched.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings

DIAGNOSTIC_STATUS = "DIAGNOSTIC_SHELTER_INDEX_NOT_A_SPEED"
DIAGNOSTIC_WARNING = (
    "A geometric shelter index, not a wind speed and not a velocity ratio. It "
    "is the share of the upwind path blocked by massing. No turbulence, no "
    "wake, no pressure field. URock or pyqes is the external check; neither is "
    "vendored here."
)
INFLOW_SOURCE = (
    "Planning Department Site Wind Availability Data, CSDI dataset "
    "pland_rcd_1634281652589_43389. Prevailing inflow: NE / ENE / E."
)

# The canonical travel table, imported rather than re-derived: a re-derived
# direction table is exactly how NE and SW get swapped.
from app.services.design_metrics import (  # noqa: E402
    _TRAVEL,
    rasterise_height,
)


def _shelter_field(height: np.ndarray, direction: str) -> np.ndarray:
    """Fraction of upwind cells that contain a building, per cell.

    Walks each cell's upwind ray in one vectorised pass per step. Out-of-grid
    steps are excluded from both the numerator and the denominator, so a cell at
    the upwind edge is judged on the ray it actually has rather than being
    penalised for the void beyond the boundary.
    """
    if direction not in _TRAVEL:
        raise ValueError(f"unknown wind direction {direction!r}; known are "
                         f"{sorted(_TRAVEL)}")
    dr, dc = _TRAVEL[direction]
    rows, cols = height.shape
    blocked = np.asarray(height, dtype=np.float64) > 0.0

    rr_base = np.arange(rows, dtype=np.int64)[:, None]
    cc_base = np.arange(cols, dtype=np.int64)[None, :]

    hits = np.zeros((rows, cols), dtype=np.float64)
    seen = np.zeros((rows, cols), dtype=np.float64)
    for step in range(1, max(rows, cols)):
        rr = rr_base - dr * step
        cc = cc_base - dc * step
        ok = (rr >= 0) & (rr < rows) & (cc >= 0) & (cc < cols)
        if not ok.any():
            break
        # A cell with no upwind neighbour contributes nothing to either count,
        # which keeps the outside-grid void out of the mean.
        seen += ok
        hits += np.where(ok, blocked[np.clip(rr, 0, rows - 1),
                                     np.clip(cc, 0, cols - 1)], False)

    return np.divide(hits, np.maximum(seen, 1.0))


# Green (open) -> red (fully sheltered). Alpha ramps with the index so the
# basemap still shows through the open ground.
_RAMP = (
    (0.00, (92, 255, 157)),
    (0.35, (232, 214, 120)),
    (0.65, (240, 150, 72)),
    (1.00, (222, 60, 60)),
)


def _shelter_rgba(field: np.ndarray) -> np.ndarray:
    stops = np.array([s[0] for s in _RAMP], dtype=np.float64)
    colours = np.array([s[1] for s in _RAMP], dtype=np.float64)
    flat = np.clip(field.reshape(-1), 0.0, 1.0)
    rgb = np.stack([np.interp(flat, stops, colours[:, i]) for i in range(3)],
                   axis=1)
    alpha = np.clip(flat * 1.6, 0.0, 0.78) * 255.0
    rgba = np.concatenate([rgb, alpha[:, None]], axis=1)
    return rgba.reshape(field.shape + (4,)).astype(np.uint8)


def shelter_diagnostic(
    grids: Any,
    footprints: list[Any],
    direction: str = "NE",
) -> dict[str, Any]:
    """The district's shelter index for one inflow direction, plus a PNG.

    The PNG is written beside the run overlays and served at ``/static``; the
    map drapes it over the study area. A direction the canonical table does not
    carry is refused here (the router turns that into a 422) rather than
    approximated.
    """
    from PIL import Image

    height = rasterise_height(footprints, grids)
    field = _shelter_field(height, direction)

    out_dir = settings.rasters_dir / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"shelter_{direction.lower()}_{uuid.uuid4().hex[:8]}.png"
    path = out_dir / name
    Image.fromarray(_shelter_rgba(field), mode="RGBA").save(path)

    # The sidecar is what a reader can check the picture against.
    sidecar = path.with_suffix(".json")
    sidecar.write_text(__import__("json").dumps({
        "artefact": "wind-shelter-diagnostic",
        "direction": direction,
        "status": DIAGNOSTIC_STATUS,
        "warning": DIAGNOSTIC_WARNING,
        "inflowSource": INFLOW_SOURCE,
        "meanShelterIndex": round(float(field.mean()), 4),
        "cells": int(field.size),
        "blockedCells": int((height > 0).sum()),
    }, indent=2), encoding="utf-8")

    covered = field[field > 0]
    return {
        "status": DIAGNOSTIC_STATUS,
        "warning": DIAGNOSTIC_WARNING,
        "direction": direction,
        "inflowSource": INFLOW_SOURCE,
        "meanShelterIndex": round(float(field.mean()), 4),
        "maxShelterIndex": round(float(field.max()), 4),
        "shelteredCells": int((field > 0).sum()),
        "cells": int(field.size),
        "meanWhereSheltered": (round(float(covered.mean()), 4)
                               if covered.size else 0.0),
        "overlayUrl": settings.public_url(f"rasters/comparison/{name}"),
        "sidecarUrl": settings.public_url(f"rasters/comparison/{sidecar.name}"),
        "method": (
            "For each cell, the fraction of the upwind path (along the published "
            "prevailing direction) whose cells contain a building. March over the "
            "shared massing height raster; out-of-grid steps are excluded."
        ),
        "externalCheck": (
            "URock 2023a or pyqes on one fixture, outside this repository. Both "
            "are GPL; neither is vendored. This index is not their output."
        ),
    }
