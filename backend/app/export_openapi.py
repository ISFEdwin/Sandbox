"""Write the API schema to contracts/openapi.json -- the checked-in contract.

The Pydantic schemas are the source of truth; this file is generated from them,
so it cannot be edited into disagreement. `tests/test_openapi_contract.py`
regenerates it and fails if the committed copy differs, which is what stops the
contract going stale the way hand-written docs do.

Run after any change to a route or schema, from backend/:

    python -m app.export_openapi

**With the pinned dependencies.** The schema FastAPI renders is a function of
the installed FastAPI and Pydantic versions, not only of the code: from pydantic
2.9.2 a `dict[str, Any]` field renders WITHOUT `additionalProperties`, from
2.13.5 it renders WITH it. `contracts/openapi.json` is committed and
byte-compared, so an artefact rendered under the wrong patch level fails the
contract job while every local run passes -- with a 62-line diff that is all
one key and reads as noise rather than as a version drift. So the renderer
checks the pin before it writes, and refuses rather than producing a file that
cannot be committed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"
REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements.txt"


def _pinned(name: str) -> str | None:
    """The pinned version of ``name`` in requirements.txt, or None if unpinned."""
    if not REQUIREMENTS_PATH.exists():  # pragma: no cover - the repo has it
        return None
    pattern = re.compile(rf"^{re.escape(name)}\s*==\s*([0-9][^\s#]*)")
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    return None


def _check_pins() -> None:
    """Refuse to render the contract under an off-pin pydantic."""
    pinned = _pinned("pydantic")
    if not pinned:
        return
    import pydantic

    if pydantic.VERSION == pinned:
        return
    raise RuntimeError(
        "Refusing to render contracts/openapi.json under pydantic %s: "
        "requirements.txt pins %s, and the two render the schema differently "
        "(a dict[str, Any] field gains \"additionalProperties\"), so the "
        "rendered file would not match the committed contract or the contract "
        "job.\n\n"
        "Use the pinned environment:\n"
        "  cd backend\n"
        "  ./.venv313/bin/pip install -r requirements.txt\n"
        "  ./.venv313/bin/python -m app.export_openapi\n"
        % (pydantic.VERSION, pinned)
    )


def render() -> str:
    """The schema as the exact text that gets committed.

    Sorted keys and a trailing newline so the output is byte-stable: the same
    app always renders the same file, whatever order routes were registered in.
    """
    from app.main import app

    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    _check_pins()
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": the file is committed with LF whatever platform wrote it.
    with CONTRACT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(render())
    print(f"wrote {CONTRACT_PATH}")


if __name__ == "__main__":
    main()
