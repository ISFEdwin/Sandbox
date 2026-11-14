"""Fail the suite loudly when the interpreter is not the one the repo is pinned to.

**What this guards.** The repository pins its dependencies in
``backend/requirements.txt``, and two of those pins are load-bearing in a way
that is invisible from a machine whose environment happens to be right:

- ``pydantic==2.13.5``. From 2.9.2 a ``dict[str, Any]`` field renders the
  OpenAPI schema **without** ``additionalProperties``; from 2.13.5 it renders
  **with** it. ``contracts/openapi.json`` is committed and byte-compared by the
  contract job, so an artefact generated under the wrong patch level fails CI
  while every local run passes -- and the diff is 62 lines of one key, which
  reads as noise rather than as a version drift.
- the interpreter itself. The committed artefacts were generated on 3.13 and
  CI runs 3.14; 3.10 is not supported (the wheels are not there).

**Why it is a hard failure and not a warning.** A warning is read by nobody at
the moment it would have mattered, which is exactly when the stale environment
is *not* the one the developer is looking at. The message names the fix.

**Why it lives here.** ``conftest.py`` is imported by pytest before anything
else runs, so the failure lands on every suite rather than on the one that
happens to notice.

The same check guards the contract renderer itself
(``app/export_openapi.py``), because that is where the drift did its damage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def _pinned(name: str) -> str | None:
    """The pinned version of ``name`` in requirements.txt, or None if unpinned."""
    requirements = BACKEND_DIR / "requirements.txt"
    if not requirements.exists():  # pragma: no cover - the repo always has it
        return None
    pattern = re.compile(rf"^{re.escape(name)}\s*==\s*([0-9][^\s#]*)")
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    return None


def _check_environment() -> None:
    """Raise with an actionable message when the environment is off-pin."""
    problems: list[str] = []

    if sys.version_info < (3, 13):
        problems.append(
            "this interpreter is Python %d.%d; the project needs 3.13 or "
            "later (3.14 in CI)"
            % (sys.version_info[0], sys.version_info[1])
        )

    pinned = _pinned("pydantic")
    if pinned:
        try:
            import pydantic
        except ImportError:  # pragma: no cover - pytest needs it anyway
            problems.append("pydantic is not installed")
        else:
            if pydantic.VERSION != pinned:
                problems.append(
                    "pydantic %s is installed; requirements.txt pins %s. The "
                    "OpenAPI schema renders differently between the two "
                    "(a dict[str, Any] field gains \"additionalProperties\"), so "
                    "the committed contract and the contract job will disagree"
                    % (pydantic.VERSION, pinned)
                )

    if problems:
        raise RuntimeError(
            "This environment does not match backend/requirements.txt:\n"
            + "\n".join("  - " + p for p in problems)
            + "\n\nCreate or use the pinned environment and re-run:\n"
            "  cd backend\n"
            "  python -m venv .venv313 && ./.venv313/bin/pip install -r "
            "requirements.txt pytest\n"
            "  ./.venv313/bin/python -m pytest -q\n\n"
            "backend/.venv is stale (Python 3.10, pydantic 2.9.2) and is the "
            "usual cause; it is not the environment this repository is pinned "
            "to."
        )


_check_environment()
