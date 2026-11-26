"""The area-bundle seal: what a prepared area actually produced.

This module is the contract between the preparation pipeline and the engine.
The engine never guesses an artefact path and never assumes a stage ran: it
reads a :class:`Manifest` and asks what the area can support.

Design rules, each load-bearing:

* **A stage has an explicit status.** ``ok``, ``degraded``, ``stale``, ``failed``,
  ``running`` or ``pending``. There is no "absent means fine" state, because
  that is the state that lets a missing input become a plausible number.
* **``degraded`` is usable.** The artefact exists; a gate did not pass. The
  limit is recorded and the capability level drops. Refusing the artefact
  outright would throw away the only honest reading available.
* **``stale`` is usable and flagged.** The DSD release is quarterly; a bundle
  built in July and read in November must say so rather than present a 2024
  network as current.
* **Capabilities are per axis, not per run.** "Drainage is L2, wind is L0" is
  the fact the criteria panel needs. A single global confidence score is the
  combined score this project refuses to publish.

Standard library only: a stage and a script both need this, and neither should
have to load numpy or the service layer to read a seal.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1


class ManifestError(ValueError):
    """A seal that cannot be read or cannot be trusted."""


class StageStatus(str, Enum):
    """A stage's state. ``usable`` is derived, never stored."""

    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILED = "failed"

    @property
    def usable(self) -> bool:
        """True when a consumer may read this stage's artefacts.

        ``degraded`` and ``stale`` are deliberately usable: the artefact is
        real, and the manifest carries the reason it is limited.
        """
        return self in (StageStatus.OK, StageStatus.DEGRADED, StageStatus.STALE)

    @property
    def terminal(self) -> bool:
        return self not in (StageStatus.PENDING, StageStatus.RUNNING)


class CapabilityLevel(str, Enum):
    """How an axis's number was obtained. Ordered least to most evidenced."""

    UNAVAILABLE = "L0"
    STANDARD_PROXY = "L1"
    ASSET_DERIVED = "L2"
    EVENT_CALIBRATED = "L3"

    @property
    def rank(self) -> int:
        return {
            CapabilityLevel.UNAVAILABLE: 0,
            CapabilityLevel.STANDARD_PROXY: 1,
            CapabilityLevel.ASSET_DERIVED: 2,
            CapabilityLevel.EVENT_CALIBRATED: 3,
        }[self]

    @property
    def label(self) -> str:
        return {
            CapabilityLevel.UNAVAILABLE: "unavailable",
            CapabilityLevel.STANDARD_PROXY: "published-standard proxy",
            CapabilityLevel.ASSET_DERIVED: "public-asset derived",
            CapabilityLevel.EVENT_CALIBRATED: "event-calibrated",
        }[self]


def utcnow() -> str:
    """Seconds-precision UTC, so two manifests from one run can be compared."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Gate:
    """One named check a stage ran, with the value it measured.

    ``passed=False`` does not fail the stage -- it degrades it. A gate is how a
    stage says "usable, but only within this limit", which is the difference
    between an honest bundle and a silent one.
    """

    name: str
    value: float | int | str | None
    passed: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "passed": bool(self.passed),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Gate:
        return cls(
            name=str(raw.get("name", "")),
            value=raw.get("value"),
            passed=bool(raw.get("passed")),
            note=str(raw.get("note") or ""),
        )


@dataclass(frozen=True)
class SourceRef:
    """Where one input came from, and when.

    ``retrieved`` is the date the provider was read, not the date the dataset
    describes. The two differ for a quarterly release and the difference is the
    whole point of recording it.
    """

    provider: str
    dataset: str
    url: str
    retrieved: str
    licence: str | None = None
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "provider": self.provider,
            "dataset": self.dataset,
            "url": self.url,
            "retrieved": self.retrieved,
        }
        if self.licence:
            out["licence"] = self.licence
        if self.checksum:
            out["checksum"] = self.checksum
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SourceRef:
        return cls(
            provider=str(raw.get("provider", "")),
            dataset=str(raw.get("dataset", "")),
            url=str(raw.get("url", "")),
            retrieved=str(raw.get("retrieved", "")),
            licence=raw.get("licence"),
            checksum=raw.get("checksum"),
        )


@dataclass
class StageRecord:
    """One stage's outcome. ``artefacts`` are bundle-relative paths."""

    name: str
    status: StageStatus
    artefacts: list[str] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    started: str | None = None
    finished: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "artefacts": list(self.artefacts),
            "sources": [s.to_dict() for s in self.sources],
            "gates": [g.to_dict() for g in self.gates],
            "started": self.started,
            "finished": self.finished,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, name: str, raw: dict[str, Any]) -> StageRecord:
        try:
            status = StageStatus(str(raw.get("status", "")))
        except ValueError as exc:
            raise ManifestError(
                f"stage {name!r} has unknown status {raw.get('status')!r}"
            ) from exc
        return cls(
            name=name,
            status=status,
            artefacts=[str(p) for p in raw.get("artefacts") or []],
            sources=[SourceRef.from_dict(s) for s in raw.get("sources") or []],
            gates=[Gate.from_dict(g) for g in raw.get("gates") or []],
            started=raw.get("started"),
            finished=raw.get("finished"),
            note=str(raw.get("note") or ""),
        )


@dataclass(frozen=True)
class Capability:
    """What one axis may claim, and the limits on that claim."""

    axis: str
    level: CapabilityLevel
    basis: str
    limits: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "levelLabel": self.level.label,
            "basis": self.basis,
            "limits": list(self.limits),
        }

    @classmethod
    def from_dict(cls, axis: str, raw: dict[str, Any]) -> Capability:
        try:
            level = CapabilityLevel(str(raw.get("level", "")))
        except ValueError as exc:
            raise ManifestError(
                f"capability {axis!r} has unknown level {raw.get('level')!r}"
            ) from exc
        return cls(
            axis=axis,
            level=level,
            basis=str(raw.get("basis") or ""),
            limits=tuple(str(x) for x in raw.get("limits") or []),
        )


@dataclass
class Manifest:
    """The seal for one area bundle."""

    area_id: str
    stages: dict[str, StageRecord] = field(default_factory=dict)
    capabilities: dict[str, Capability] = field(default_factory=dict)
    gaps: list[dict[str, str]] = field(default_factory=list)
    grid: dict[str, Any] = field(default_factory=dict)
    sealed_at: str | None = None
    schema_version: int = SCHEMA_VERSION

    # -- reads -------------------------------------------------------------- #

    def stage(self, name: str) -> StageRecord | None:
        return self.stages.get(name)

    def ready(self, *names: str) -> bool:
        """True when every named stage is present and usable.

        A caller that needs terrain must say so; a missing stage is not an
        error here, it is an answer of ``False``.
        """
        for name in names:
            record = self.stages.get(name)
            if record is None or not record.status.usable:
                return False
        return True

    def blocking(self, order: Iterable[str]) -> str | None:
        """First stage in ``order`` that is not usable, or None when all are."""
        for name in order:
            record = self.stages.get(name)
            if record is None or not record.status.usable:
                return name
        return None

    def capability(self, axis: str) -> Capability | None:
        return self.capabilities.get(axis)

    def level_of(self, axis: str) -> CapabilityLevel:
        """The axis's level, or ``UNAVAILABLE`` when it was never assessed."""
        cap = self.capabilities.get(axis)
        return cap.level if cap else CapabilityLevel.UNAVAILABLE

    @property
    def is_sealed(self) -> bool:
        return self.sealed_at is not None

    @property
    def has_failures(self) -> bool:
        return any(s.status is StageStatus.FAILED for s in self.stages.values())

    # -- writes ------------------------------------------------------------- #

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "areaId": self.area_id,
            "grid": dict(self.grid),
            "stages": {name: rec.to_dict() for name, rec in self.stages.items()},
            "capabilities": {
                axis: cap.to_dict() for axis, cap in self.capabilities.items()
            },
            "gaps": list(self.gaps),
            "sealedAt": self.sealed_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Manifest:
        version = int(raw.get("schemaVersion") or 0)
        if version != SCHEMA_VERSION:
            raise ManifestError(
                f"manifest schemaVersion {version} is not {SCHEMA_VERSION}; "
                "re-prepare the area with the current pipeline"
            )
        area_id = str(raw.get("areaId") or "")
        if not area_id:
            raise ManifestError("manifest has no areaId")
        stages = {
            str(name): StageRecord.from_dict(str(name), body or {})
            for name, body in (raw.get("stages") or {}).items()
        }
        capabilities = {
            str(axis): Capability.from_dict(str(axis), body or {})
            for axis, body in (raw.get("capabilities") or {}).items()
        }
        return cls(
            area_id=area_id,
            stages=stages,
            capabilities=capabilities,
            gaps=[dict(g) for g in raw.get("gaps") or []],
            grid=dict(raw.get("grid") or {}),
            sealed_at=raw.get("sealedAt"),
            schema_version=version,
        )

    def write(self, path: Path) -> Path:
        """Write atomically: a half-written seal is worse than an old one."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=False)
            + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
        return path

    @classmethod
    def read(cls, path: Path) -> Manifest:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ManifestError(f"no manifest at {path}") from exc
        except (OSError, ValueError) as exc:
            raise ManifestError(f"manifest at {path} is unreadable: {exc}") from exc
        if not isinstance(raw, dict):
            raise ManifestError(f"manifest at {path} is not an object")
        return cls.from_dict(raw)

    @classmethod
    def load_or_new(cls, path: Path, area_id: str) -> Manifest:
        """Resume from disk when a seal exists, otherwise start a fresh one."""
        if not path.exists():
            return cls(area_id=area_id)
        manifest = cls.read(path)
        if manifest.area_id != area_id:
            raise ManifestError(
                f"manifest at {path} belongs to area {manifest.area_id!r}, "
                f"not {area_id!r}"
            )
        return manifest
