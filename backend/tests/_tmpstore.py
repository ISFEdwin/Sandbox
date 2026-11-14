"""Redirect the file store at a throwaway copy, for the suites that write.

The suites that *create* records (plans, interventions, run
overlays) used to write into the real store in ``backend/data``, so running the test
suite accumulated scene, plan and intervention documents in the working tree.
18 plans had built up before the 12 Oct 2026 cleanup, and ``.gitignore`` only
stopped them being *committed* -- it did nothing about the accumulation.

The side effect was worse than untidiness: ``test_ledger``'s "no live seeded
intervention is over-large" check reads the store, so a stray over-large plan
left behind by an earlier run could turn a real check red. A suite whose result
depends on what previous runs left on disk is not a suite.

## Why a copy rather than an empty directory

Scenes, plans and rasters all live under one ``data_dir`` (see
``app.config.Settings``), and the suites need to *read* the seeded scene, the
canonical rasters and the committed city model. Pointing ``data_dir`` at an empty
temp dir would break every read. So the whole tree is copied (15 MB, once per
suite) and only the copy is written to: reads are identical, writes are
discarded, and the real store is untouched.

``shutil.copytree`` preserves mtimes, which matters -- the run service caches
the conditioned grid on ``wetgrid_hsk.npy``'s mtime, and a copy with a fresh
mtime would silently invalidate a cache the tests rely on being warm.

## Why the copy is pruned to the committed fixtures

The store is a *runtime* store: ``.gitignore`` says so outright ("Everything
else under those three directories is residue from running the suites or poking
the API by hand"). Copying the whole tree therefore copied the residue with it,
and the suites booted from whatever the machine happened to have lying around.

That is the same defect this module was written to fix, one level up: "a suite
whose result depends on what previous runs left on disk is not a suite". The
concrete symptom, measured on 14 Nov 2026: five suites failed on a developer
machine while CI ran the same code on a clean checkout. Two of them (the
hydrology and building-fit suites) failed for a real, committed reason -- the
committed raster set was generated at the wrong design storm -- and the other
three failed only because a hand-poked staged scenario (10 unconfirmed AI
drafts, 7 of them pinned) claimed 37 % of the district as prior work, so the
proposer had no free ground left to offer and the reservoir axis came back
empty.

So the copy is pruned to what the repository actually tracks: the seeded scene,
the baseline plan and the planned projects, and nothing else. The suites then
boot from exactly the state CI boots from, on every machine, and the residue on
a developer machine can no longer turn a suite red. The allowlist is read from
git's index -- one source of truth, the same one ``.gitignore`` defers to --
and a checkout without a git index keeps the unpruned copy, which is the old
behaviour.

## Usage

    from tests._tmpstore import isolate_store
    isolate_store()
    from app.services import run_service   # import AFTER, so paths resolve late

Called at the top of a creating suite, before anything reads ``settings``.
"""

from __future__ import annotations

import atexit
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_ISOLATED: Path | None = None

#: The store directories whose non-fixture contents are runtime residue.
RUNTIME_STORE_DIRS: tuple[str, ...] = ("scenes", "plans", "interventions")

#: Store-root files that are runtime state rather than fixtures.
#:
#: ``llm_config.json`` holds the operator's live model settings, written by
#: ``PUT /api/llm-config``. It is never committed (``.gitignore`` says so), and
#: it is the reason a developer machine's suite run can talk to a real model
#: while CI -- which has no ``.env`` LLM keys -- runs the deterministic
#: heuristic. A suite whose result depends on which model happened to be
#: configured is not a suite, so the override does not come along either.
RUNTIME_STORE_FILES: tuple[str, ...] = ("llm_config.json",)


def _git_dir() -> Path | None:
    """The repository root, if this checkout has one.

    The git directory lives at the *repository* root, which is above
    ``backend/``, so the search walks up from there. A checkout without one (a
    tarball, a copied tree) has no committed-fixture list to prune against.
    """
    for directory in (BACKEND_DIR, *BACKEND_DIR.parents):
        if (directory / ".git").exists():
            return directory
    return None


def _committed_store_files() -> set[str] | None:
    """The store files git tracks, relative to ``backend/``.

    ``None`` when the checkout has no git index (a tarball, a copied tree), in
    which case the copy is left unpruned -- the old behaviour, and a warning
    the caller can ignore.
    """
    root = _git_dir()
    if root is None:
        return None
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "data"],
            cwd=BACKEND_DIR, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {p for p in out.stdout.split("\0") if p}


def _prune_to_committed(target: Path) -> int:
    """Drop the runtime residue from the copied store. Returns files removed.

    Only the three runtime directories are pruned. The rasters, the reference
    data, the scenarios and the city model are read as they are: they are
    committed artefacts, not records a suite creates.
    """
    committed = _committed_store_files()
    if committed is None:
        return 0
    removed = 0
    for name in RUNTIME_STORE_FILES:
        path = target / name
        if path.exists():
            path.unlink()
            removed += 1
    for name in RUNTIME_STORE_DIRS:
        directory = target / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            relative = f"data/{name}/{path.name}"
            if relative in committed:
                continue
            path.unlink()
            removed += 1
    return removed


def _reset_runtime_overrides(settings) -> None:
    """Put the model settings back to the ``.env`` baseline.

    The ``Settings`` singleton is built when ``app.config`` is first imported
    -- which happens *inside* ``isolate_store`` -- so it has already applied the
    operator's runtime override from the original store's
    ``llm_config.json``. Redirecting ``data_dir`` afterwards does not undo
    that, so the override is dropped explicitly: the LLM fields go back to
    what ``.env`` says (nothing, by default) and the override file is re-read
    from the redirected store, where it has been pruned away.

    The effect is that a suite runs the deterministic heuristic path whether or
    not the machine it runs on has a live model configured -- which is what CI
    does, and what makes the suite's result the same everywhere.
    """
    from app.config import LLM_OVERRIDE_FIELDS, Settings, _read_llm_overrides

    baseline = Settings()
    for key in LLM_OVERRIDE_FIELDS:
        setattr(settings, key, getattr(baseline, key))
    for key, value in _read_llm_overrides(settings).items():
        setattr(settings, key, value)


def isolate_store() -> Path:
    """Point ``settings.data_dir`` at a temp copy of the store. Idempotent.

    Returns the temp directory. It is registered for removal at interpreter
    exit; a failure to remove it is ignored, because leaving a temp directory
    behind is strictly better than failing a suite during teardown.
    """
    global _ISOLATED
    if _ISOLATED is not None:
        return _ISOLATED

    from app.config import settings

    source = settings.data_dir
    target = Path(tempfile.mkdtemp(prefix="hsk-test-store-"))
    shutil.copytree(source, target, dirs_exist_ok=True)
    settings.data_dir = target
    _prune_to_committed(target)
    _reset_runtime_overrides(settings)
    _ISOLATED = target
    atexit.register(shutil.rmtree, target, ignore_errors=True)
    return target


def store_is_isolated() -> bool:
    """True when the store has been redirected. For a suite's own assertions."""
    return _ISOLATED is not None
