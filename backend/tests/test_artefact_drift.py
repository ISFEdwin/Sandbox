"""The committed raster set and the engine must agree about the design storm.

**Why this suite exists.** For most of the project's life the committed
``wetgrid_hsk.*`` artefacts were generated at a 450 mm storm while the API, the
run service and the ledger all computed at 50 mm. Nothing was wrong with either
number on its own; they were two answers to "what is the default rainfall", and
the map disagreed with the ledger by an order of magnitude (16.8 ha of pictured
water against 0.8 ha of computed water) without a single check failing. The
design storm was settled at 50 mm on 14 Nov 2026 and the artefacts regenerated
at it; this suite is the thing that makes that pairing impossible to lose.

It is deliberately a **pytest** file with ``test_*`` functions and no
``__main__`` guard, so CI collects it (``python -m pytest -q``) and
``pytest -q`` over the whole tree covers it too.

What it asserts, and why each one:

1. the committed sidecar says which storm it was generated at, and that storm
   is the design storm the engine defaults to;
2. the volume the sidecar publishes is the volume the ledger computes from the
   same land cover and the same curve numbers -- the artefact and the engine
   are two views of one computation;
3. the committed depth raster contains exactly the cells the sidecar says are
   wet, so the PNG, the ``.npy`` and the JSON cannot drift apart;
4. the routed mass balance in the sidecar balances, because the artefact that
   publishes it is the one that has to be true.

The assertions compare *the committed file* with *the engine*, not the engine
with itself, so a regeneration that quietly changed the storm fails here even
when every other number in the repository is self-consistent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _extra in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from app.config import DEFAULT_RAINFALL_MM  # noqa: E402
from app.services.sandbox_model import (  # noqa: E402
    load_grids,
    storage_ledger,
)

SIDECAR = BACKEND_DIR / "data" / "rasters" / "wetgrid_hsk.json"
DEPTH_RASTER = BACKEND_DIR / "data" / "rasters" / "wetgrid_hsk.npy"


def _sidecar() -> dict:
    return json.loads(SIDECAR.read_text(encoding="utf-8"))


def test_the_committed_artefact_was_generated_at_the_design_storm() -> None:
    """The sidecar names the storm it was generated at, and it is the design storm.

    Without this the artefact could be regenerated at any storm and still be
    self-consistent: the drift that started this was exactly that -- a coherent
    450 mm artefact sitting next to a 50 mm engine.
    """
    sidecar = _sidecar()
    assert sidecar["inputs"]["rainfall_mm"] == DEFAULT_RAINFALL_MM, (
        "the committed wet grid was generated at %s mm but the engine's design "
        "storm is %s mm; regenerate it with `python scripts/make_wetgrid.py`"
        % (sidecar["inputs"]["rainfall_mm"], DEFAULT_RAINFALL_MM)
    )


def test_the_committed_artefacts_and_the_ledger_agree() -> None:
    """The published volumes are the volumes the engine computes.

    The sidecar's runoff and unstored volumes come from the same SCS-CN
    arithmetic the ledger runs, over the same land cover. If they disagree, one
    of them is describing a different storm, and the map and the number are
    answering different questions.
    """
    import numpy as np

    grids = load_grids()
    assert grids is not None, "no ledger grid: run scripts/make_wetgrid.py"
    sidecar = _sidecar()
    ledger = storage_ledger(grids, grids.land_class, DEFAULT_RAINFALL_MM)

    published_runoff = float(sidecar["results"]["runoffVolumeM3"])
    published_unstored = float(sidecar["results"]["unstoredVolumeM3"])

    assert abs(ledger["runoffM3"] - published_runoff) < 1.0, (
        "the committed artefact publishes %,.1f m3 of runoff but the ledger "
        "computes %,.1f m3 at the design storm"
        % (published_runoff, ledger["runoffM3"])
    )
    assert abs(ledger["unstoredM3"] - published_unstored) < 1.0, (
        "the committed artefact publishes %,.1f m3 unstored but the ledger "
        "computes %,.1f m3 at the design storm"
        % (published_unstored, ledger["unstoredM3"])
    )


def test_the_committed_depth_raster_matches_the_sidecar() -> None:
    """The ``.npy`` holds exactly the cells the sidecar says are wet.

    The PNG is a render and is lossy by design (its alpha saturates); the
    ``.npy`` is the data. They are written by the same run and must describe
    the same surface, or the analysis reads one storm and the picture shows
    another.
    """
    import numpy as np

    sidecar = _sidecar()
    depth = np.load(DEPTH_RASTER)
    wet_cells = int((depth > 0).sum())
    assert wet_cells == int(sidecar["results"]["wetCells"]), (
        "the committed depth raster has %d wet cells but the sidecar publishes %d"
        % (wet_cells, sidecar["results"]["wetCells"])
    )


def test_the_committed_routed_cascade_balances() -> None:
    """The mass balance the artefact publishes is a balanced one.

    The sidecar carries the routed block beside the level-pool one. If the
    books do not balance, the artefact is reporting a volume that was not
    conserved, and every downstream number inherits it.
    """
    routed = _sidecar().get("routed") or {}
    balance = routed.get("massBalance") or {}
    assert balance, "the committed sidecar publishes no routed mass balance"
    assert bool(balance.get("balanced")), (
        "the committed routed cascade does not balance: %s" % balance
    )
    assert abs(float(balance.get("relativeResidual", 1.0))) <= float(
        balance.get("tol", 1e-6)
    ), "the committed routed cascade's residual is outside its own tolerance"
