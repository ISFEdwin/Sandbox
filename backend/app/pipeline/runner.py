"""Stage DAG, idempotent and resumable, with the seal written after every step.

The runner's job is to make an interrupted build safe. A preparation run is
network-heavy and can take minutes; killing it must not leave a bundle that
looks finished. So the manifest is written *before* a stage starts (as
``running``) and again after it finishes, and a re-run resumes at the first
stage that is not usable.

Two failure modes are distinguished, and the distinction is the whole point:

* :class:`GateFailure` -- the stage ran, produced an artefact, and a named check
  did not pass. The stage is ``degraded``: usable, with the limit recorded.
* any other exception -- no artefact worth trusting. The stage is ``failed``.
  The run does not seal, and every stage that depends on it is recorded as
  ``pending`` with the blocking stage named. Independent branches still run, so
  one broken source does not discard the work that succeeded.

Collapsing the two is how a screening model starts publishing numbers it cannot
support.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

from app.pipeline.area import STAGE_ORDER, AreaRecord
from app.pipeline.manifest import (
    Gate,
    Manifest,
    ManifestError,
    StageRecord,
    StageStatus,
    utcnow,
)


class RunnerError(RuntimeError):
    """A stage graph or a run request the runner refuses."""


class GateFailure(Exception):
    """The stage produced an artefact, but a gate did not pass.

    Raised instead of ``StageRecord(status=DEGRADED)`` so a stage body can stop
    at the failing check without building the record by hand. The artefact is
    still expected to be on disk when this is raised.
    """

    def __init__(self, gate: Gate, note: str = "") -> None:
        self.gate = gate
        self.note = note or f"gate {gate.name!r} did not pass"
        # Carry the gate's own explanation into the stage note: a reader of the
        # seal sees one line, not two records that have to be joined.
        if gate.note and gate.note not in self.note:
            self.note = f"{self.note}: {gate.note}"
        super().__init__(self.note)


@dataclass
class StageContext:
    """What a stage is given. No globals, no settings reads inside a stage body."""

    area: AreaRecord
    root: Path
    offline: bool = False

    def path(self, *parts: str) -> Path:
        """A bundle-relative path, with its parent created."""
        target = self.root.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def existing(self, *parts: str) -> Path | None:
        target = self.root.joinpath(*parts)
        return target if target.exists() else None


class Stage(Protocol):
    """A pipeline step.

    Implementations declare ``name`` (one of :data:`STAGE_ORDER`) and
    ``requires`` (the stages that must be usable first) as class attributes.
    """

    name: str
    requires: tuple[str, ...]

    def run(self, ctx: StageContext) -> StageRecord:
        ...


def topological_order(stages: Sequence[Stage]) -> list[Stage]:
    """Dependency order, with duplicate names and cycles rejected.

    A stage name outside :data:`STAGE_ORDER` is a typo, not an extension point:
    it would place an entry in the seal no consumer knows how to read. Reject it
    here rather than discover it in a panel six months later.
    """
    by_name: dict[str, Stage] = {}
    for stage in stages:
        if stage.name in by_name:
            raise RunnerError(f"two stages are named {stage.name!r}")
        if stage.name not in STAGE_ORDER:
            raise RunnerError(
                f"stage {stage.name!r} is not in STAGE_ORDER; add it there "
                "before registering it"
            )
        by_name[stage.name] = stage

    for stage in stages:
        for dependency in stage.requires:
            if dependency not in by_name:
                raise RunnerError(
                    f"stage {stage.name!r} requires {dependency!r}, which is "
                    "not registered"
                )

    order: list[str] = []
    state: dict[str, int] = {}  # 0 = visiting, 1 = done

    def visit(name: str, stack: tuple[str, ...]) -> None:
        if state.get(name) == 1:
            return
        if state.get(name) == 0:
            cycle = " -> ".join((*stack, name))
            raise RunnerError(f"stage dependency cycle: {cycle}")
        state[name] = 0
        for dependency in by_name[name].requires:
            visit(dependency, (*stack, name))
        state[name] = 1
        order.append(name)

    for name in STAGE_ORDER:
        if name in by_name:
            visit(name, ())

    return [by_name[name] for name in order]


class Runner:
    """Run registered stages for one area, writing the seal as it goes."""

    def __init__(
        self,
        stages: Sequence[Stage],
        area: AreaRecord,
        root: Path,
        *,
        offline: bool = False,
        on_event: Callable[[str, StageRecord], None] | None = None,
    ) -> None:
        self.stages = tuple(stages)
        self.area = area
        self.root = root
        self.offline = offline
        self.on_event = on_event
        self.manifest_path = root / "manifest.json"

    def load(self) -> Manifest:
        return Manifest.load_or_new(self.manifest_path, self.area.id)

    def run(
        self,
        only: Sequence[str] | None = None,
        force: bool = False,
    ) -> Manifest:
        if not self.stages:
            raise RunnerError(
                "no stages are registered. Increment A ports the existing "
                "scripts into app/pipeline/stages/ before a prepare can run."
            )

        order = topological_order(self.stages)
        wanted = set(only) if only is not None else None
        if wanted is not None:
            unknown = wanted - {s.name for s in order}
            if unknown:
                raise RunnerError(f"unknown stage(s): {sorted(unknown)}")

        manifest = self.load()
        ctx = StageContext(area=self.area, root=self.root, offline=self.offline)

        for stage in order:
            if wanted is not None and stage.name not in wanted:
                continue

            previous = manifest.stages.get(stage.name)
            if previous is not None and previous.status.usable and not force:
                continue

            missing = [r for r in stage.requires if not manifest.ready(r)]
            if missing:
                manifest.stages[stage.name] = StageRecord(
                    name=stage.name,
                    status=StageStatus.PENDING,
                    note=(
                        "blocked: "
                        + ", ".join(missing)
                        + " is not usable, so this stage was not run"
                    ),
                )
                manifest.write(self.manifest_path)
                self._emit(stage.name, manifest.stages[stage.name])
                # A blocked stage's dependants are blocked too; the loop's
                # requires check reports each of them with its own reason.
                continue

            started = utcnow()
            manifest.stages[stage.name] = StageRecord(
                name=stage.name,
                status=StageStatus.RUNNING,
                started=started,
                note="",
            )
            manifest.write(self.manifest_path)

            record = self._execute(stage, ctx, started)
            manifest.stages[stage.name] = record
            manifest.write(self.manifest_path)
            self._emit(stage.name, record)
            # Do not break: a dependent stage must still be recorded as
            # pending, with the failure named, rather than silently absent.

        self._seal(manifest)
        manifest.write(self.manifest_path)
        return manifest

    # -- internals ---------------------------------------------------------- #

    def _execute(
        self, stage: Stage, ctx: StageContext, started: str
    ) -> StageRecord:
        try:
            record = stage.run(ctx)
        except GateFailure as exc:
            return StageRecord(
                name=stage.name,
                status=StageStatus.DEGRADED,
                gates=[exc.gate],
                started=started,
                finished=utcnow(),
                note=exc.note,
            )
        except ManifestError as exc:
            return StageRecord(
                name=stage.name,
                status=StageStatus.FAILED,
                started=started,
                finished=utcnow(),
                note=f"manifest: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - a stage body may raise anything
            return StageRecord(
                name=stage.name,
                status=StageStatus.FAILED,
                started=started,
                finished=utcnow(),
                note=f"{type(exc).__name__}: {exc}",
            )

        if not isinstance(record, StageRecord):
            return StageRecord(
                name=stage.name,
                status=StageStatus.FAILED,
                started=started,
                finished=utcnow(),
                note=(
                    f"stage returned {type(record).__name__}, not StageRecord"
                ),
            )

        record.name = stage.name
        record.started = record.started or started
        record.finished = record.finished or utcnow()
        return record

    def _seal(self, manifest: Manifest) -> None:
        """Seal only when every registered stage reached a terminal state."""
        registered = {s.name for s in self.stages}
        terminal = all(
            manifest.stages.get(name) is not None
            and manifest.stages[name].status.terminal
            for name in registered
        )
        if terminal and not manifest.has_failures:
            manifest.sealed_at = manifest.sealed_at or utcnow()
        else:
            manifest.sealed_at = None

    def _emit(self, name: str, record: StageRecord) -> None:
        if self.on_event is not None:
            self.on_event(name, record)
