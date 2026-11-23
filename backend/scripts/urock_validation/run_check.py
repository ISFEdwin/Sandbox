"""Offline URock 2023a check. Not on the API path.

URock (Bernard, Lindberg & Oswald, GMD 2023, doi:10.5194/gmd-16-5703-2023)
is GPL-3.0 and needs Java >= 8, H2GIS and Jaydebeapi, plus Numba. None of
those are added to backend/requirements.txt. This script does not vendor
URock. If the prerequisite is missing it writes a sidecar and stops. It
does not invent a speed ranking.

Run from backend/:  python scripts/urock_validation/run_check.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIDECAR = HERE / "last_run.json"

SIDECAR_BODY = {
    "artefact": "urock-validation",
    "status": "NOT_RUN",
    "verified": False,
    "method": (
        "URock 2023a, one NE baseline and one proposed scheme, sampled at "
        "1.5 m, speed ranking compared with the geometric corridor ranking. "
        "Offline only."
    ),
    "limitation": (
        "Not executed in this environment. No speed ranking is reported. "
        "A missing solver is not a result, and this file does not estimate one. "
        "The screening corridor remains geometry, not a velocity ratio."
    ),
    "licence": "GPL-3.0",
    "citation": "Bernard, Lindberg & Oswald, Geosci. Model Dev. 16, 5703–5727, 2023. doi:10.5194/gmd-16-5703-2023",
    "repositories": [
        "https://github.com/bbrangeo/urock_processing",
        "https://github.com/UMEP-dev/UMEP",
    ],
    "prerequisite": (
        "Python + Numba, Java >= 8, H2GIS, Jaydebeapi. "
        "The missing list is what this environment actually lacked. "
        "A present binary is not a completed solve."
    ),
    "sampleHeightM": 1.5,
    "directions": ["NE"],
    "cases": ["baseline", "proposed"],
    "retrieved": date.today().isoformat(),
}


def _missing() -> list[str]:
    missing = []
    if shutil.which("java") is None:
        missing.append("java")
    for name in ("numba", "jaydebeapi"):
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    # URock is not a single importable name across the two repositories.
    if importlib.util.find_spec("urock") is None and importlib.util.find_spec("URock") is None:
        missing.append("urock")
    return missing


def main() -> int:
    missing = _missing()
    body = dict(SIDECAR_BODY)
    body["missing"] = missing
    if not missing:
        body["status"] = "PREREQUISITE_PRESENT_NOT_EXECUTED"
        body["limitation"] = (
            "The imports resolved, but this harness does not launch a solve "
            "from the API process and does not vendor URock. Run the GPL "
            "tool offline and replace this sidecar with the sampled ranking. "
            "Do not paste that ranking into the corridor response."
        )
    SIDECAR.write_text(json.dumps(body, indent=2), encoding="utf-8")
    print(body["status"], "missing:", ", ".join(missing) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
