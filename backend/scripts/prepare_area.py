#!/usr/bin/env python
"""Prepare one area bundle, or inspect what a bundle already holds.

    python scripts/prepare_area.py --area hsk-ht-nda --preview
    python scripts/prepare_area.py --area hsk-ht-nda --status
    python scripts/prepare_area.py --area hsk-ht-nda
    python scripts/prepare_area.py --area hsk-ht-nda --stage s07_drainage --force

The preview is pure arithmetic: it answers "what grid will this area get, how
many cells, and what can that grid support" before a single byte is downloaded.

A prepare currently refuses to run: no stage is registered yet (`docs/PIPELINE.md`
Increment A ports the existing scripts). The refusal is deliberate — a runner
with an empty registry could otherwise seal a bundle that contains nothing.

Exit codes: 0 ok, 1 a stage failed, 2 bad input or nothing to run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.pipeline.area import (  # noqa: E402
    AreaError,
    AreaRecord,
    area_root,
    preview,
)
from app.pipeline.manifest import Manifest, ManifestError, StageStatus  # noqa: E402
from app.pipeline.runner import Runner, RunnerError  # noqa: E402
from app.pipeline.stages import STAGES  # noqa: E402


def _legacy_scene_area() -> AreaRecord | None:
    """Read the old ``scene_hsk.json`` as an area record.

    Bridge for Increment A only: the study-area file is the current source of
    truth, and the port will write it as ``data/areas/<id>/aoi.json``. This
    function disappears when that lands.
    """
    path = settings.data_dir / "scene_hsk.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    geometry = raw.get("geometry") or raw.get("bbox")
    if not isinstance(geometry, dict):
        return None
    return AreaRecord(
        id=str(raw.get("id") or path.stem),
        name=str(raw.get("name") or path.stem),
        geometry=geometry,
        provenance=dict(raw.get("provenance") or {}),
        created=str(raw.get("provenance", {}).get("retrieved") or ""),
    )


def _load_area(area_id: str) -> tuple[AreaRecord, str]:
    """The area's own record, else the legacy study-area file, with its origin."""
    path = area_root(settings.data_dir, area_id) / "aoi.json"
    if path.exists():
        return AreaRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))), str(path)
    legacy = _legacy_scene_area()
    if legacy is not None and legacy.id == area_id:
        return legacy, "data/scene_hsk.json (legacy layout)"
    raise AreaError(
        f"no aoi.json at {path}. Create one, or ask for the area id the "
        "legacy data/scene_hsk.json declares."
    )


def _print_status(manifest: Manifest, path: Path) -> None:
    print(f"area      {manifest.area_id}")
    print(f"manifest  {path}")
    print(f"sealed    {manifest.sealed_at or 'no'}")
    if manifest.grid:
        print(
            "grid      {rows} x {cols} @ {res:g} m".format(
                rows=manifest.grid.get("rows"),
                cols=manifest.grid.get("cols"),
                res=float(manifest.grid.get("resolutionM") or 0.0),
            )
        )
    print()
    if not manifest.stages:
        print("no stages recorded.")
        return
    width = max(len(name) for name in manifest.stages)
    for name, record in manifest.stages.items():
        mark = {
            StageStatus.OK: "ok      ",
            StageStatus.DEGRADED: "degraded",
            StageStatus.STALE: "stale   ",
            StageStatus.FAILED: "FAILED  ",
            StageStatus.RUNNING: "running ",
            StageStatus.PENDING: "pending ",
        }[record.status]
        detail = record.note or (
            f"{len(record.artefacts)} artefact(s)" if record.artefacts else ""
        )
        print(f"  [{mark}] {name.ljust(width)}  {detail}")
    if manifest.capabilities:
        print()
        for axis, cap in manifest.capabilities.items():
            print(f"  {axis.ljust(width)}  {cap.level.value}  {cap.level.label}")
            for limit in cap.limits:
                print(f"  {' ' * width}    - {limit}")
    if manifest.gaps:
        print()
        for gap in manifest.gaps:
            print(f"  gap: {gap.get('axis')}: {gap.get('reason')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", help="area id (the aoi.json id)")
    parser.add_argument("--preview", action="store_true",
                        help="print the grid and capability ceiling and exit")
    parser.add_argument("--status", action="store_true",
                        help="print the seal and exit")
    parser.add_argument("--stage", action="append", default=None,
                        help="run only these stages (repeatable)")
    parser.add_argument("--force", action="store_true",
                        help="re-run stages that are already usable")
    parser.add_argument("--offline", action="store_true",
                        help="forbid network reads; use cached sources only")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    if args.preview:
        if args.area:
            try:
                area, origin = _load_area(args.area)
            except (AreaError, OSError, ValueError) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            result = preview(area.geometry, area.requested_resolution_m)
            result["source"] = origin
            result["name"] = area.name
        else:
            print(
                "error: --preview needs --area (or a bbox via the API). The "
                "preview is derived from a polygon, not typed from memory.",
                file=sys.stderr,
            )
            return 2
        print(json.dumps(result, indent=2) if args.json else _format_preview(result))
        return 0

    if not args.area:
        parser.error("--area is required")

    return _run(args)


def _run(args: argparse.Namespace) -> int:
    try:
        area, origin = _load_area(args.area)
    except (AreaError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root = area_root(settings.data_dir, area.id)

    if args.status:
        path = root / "manifest.json"
        try:
            manifest = Manifest.read(path)
        except ManifestError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(manifest.to_dict(), indent=2))
        else:
            _print_status(manifest, path)
        return 1 if manifest.has_failures else 0

    print(f"area  {area.id} ({area.name})")
    print(f"from  {origin}")
    if not STAGES:
        sys.stdout.flush()
        print(
            "\nnothing to run: no stage is registered yet.\n"
            "Increment A ports s03_terrain .. s09_presentation into "
            "app/pipeline/stages/. See docs/PIPELINE.md §10.",
            file=sys.stderr,
        )
        return 2

    try:
        manifest = Runner(
            STAGES,
            area,
            root,
            offline=args.offline,
            on_event=lambda name, record: print(f"  {name}: {record.status.value}"),
        ).run(only=args.stage, force=args.force)
    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_status(manifest, root / "manifest.json")
    return 1 if manifest.has_failures else 0


def _format_preview(result: dict) -> str:
    lines = [
        f"{result.get('name') or result.get('areaId') or 'area'}",
        f"  area          {result['areaHa']:,.1f} ha",
        f"  grid          {result['rows']} x {result['cols']} @ "
        f"{result['resolutionM']:g} m  ({result['cells']:,} cells)",
        f"  cost class    {result['costClass']}",
        f"  drainage      {result['drainageCeiling']['level']} ceiling",
    ]
    for reason in result["drainageCeiling"]["reasons"]:
        lines.append(f"                - {reason}")
    lines.append(f"  terrain       {result['terrainCeiling']['level']}")
    for reason in result["terrainCeiling"]["reasons"]:
        lines.append(f"                - {reason}")
    for note in result.get("notes") or []:
        lines.append(f"  note          {note}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
