"""The area-bundle contract: grid policy, seal semantics, and the stage runner.

These tests exist because the pipeline's failure modes are silent ones. A
coarsened grid that does not say it was coarsened, a degraded stage that reads
as ``ok``, a failed stage whose dependants are simply absent -- each produces a
plausible bundle and a wrong claim. The assertions here are about honesty, not
about raster values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipeline import area as area_module  # noqa: E402
from app.pipeline.area import (  # noqa: E402
    MAX_AREA_HA,
    MAX_CELLS,
    AreaError,
    AreaRecord,
    area_root,
    choose_resolution,
    derive_grid,
    drainage_ceiling,
    preview,
)
from app.pipeline.cache import CacheError, content_key, source_path  # noqa: E402
from app.pipeline.manifest import (  # noqa: E402
    Capability,
    CapabilityLevel,
    Gate,
    Manifest,
    ManifestError,
    SourceRef,
    StageRecord,
    StageStatus,
)
from app.pipeline.runner import (  # noqa: E402
    GateFailure,
    Runner,
    RunnerError,
    StageContext,
    topological_order,
)

HSK = (113.9922, 22.4310, 113.9994, 22.4363)
HSK_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [HSK[0], HSK[1]], [HSK[2], HSK[1]], [HSK[2], HSK[3]],
        [HSK[0], HSK[3]], [HSK[0], HSK[1]],
    ]],
}


def _area(area_id: str = "test-area") -> AreaRecord:
    return AreaRecord(id=area_id, name="Test area", geometry=HSK_POLYGON)


# --------------------------------------------------------------------------- #
# Resolution policy
# --------------------------------------------------------------------------- #


def test_ladder_bands_are_what_the_spec_says() -> None:
    assert choose_resolution(1.0)[0] == 5.0
    assert choose_resolution(500.0)[0] == 5.0
    assert choose_resolution(500.1)[0] == 10.0
    assert choose_resolution(2_500.0)[0] == 10.0
    assert choose_resolution(2_500.1)[0] == 20.0
    assert choose_resolution(10_000.0)[0] == 20.0


def test_area_above_the_single_bundle_limit_is_refused() -> None:
    with pytest.raises(AreaError, match="sub-basins"):
        choose_resolution(MAX_AREA_HA + 1.0)


def test_hsk_derives_the_grid_the_scripts_hardcoded() -> None:
    """The policy must reproduce 117 x 148 at 5 m for the current study area.

    This is the Increment A acceptance property in miniature: if the derived
    grid differs from what the committed rasters were built on, the port is not
    byte-identical and every downstream array is misaligned.
    """
    grid = derive_grid(HSK)
    assert (grid.rows, grid.cols) == (117, 148)
    assert grid.resolution_m == 5.0
    assert grid.coarsened_from_m is None
    assert 40.0 < grid.area_ha < 47.0


def test_every_policy_grid_fits_the_cell_budget() -> None:
    # Three extents, one per band. Each is checked against the same budget the
    # runtime enforces, so a future ladder edit cannot quietly overshoot.
    for extent in ((113.98, 22.43, 113.995, 22.44),
                   (113.95, 22.43, 113.99, 22.47),
                   (113.95, 22.43, 114.04, 22.52)):
        grid = derive_grid(extent)
        assert grid.cells <= MAX_CELLS, (extent, grid.cells)


def test_explicit_resolution_that_does_not_fit_is_rejected_not_coarsened() -> None:
    # HSK at 1 m is ~433k cells. Silently giving 2 m would make two areas look
    # comparable when they are not.
    with pytest.raises(AreaError, match="budget"):
        derive_grid(HSK, resolution_m=1.0)


def test_coarsening_is_recorded_when_the_budget_forces_it(monkeypatch) -> None:
    monkeypatch.setattr(area_module, "MAX_CELLS", 1_000)
    grid = derive_grid(HSK)
    assert grid.cells <= 1_000
    assert grid.resolution_m > 5.0
    assert grid.coarsened_from_m == 5.0
    assert "coarsened" in grid.note.lower()


def test_drainage_ceiling_drops_with_cell_size() -> None:
    assert drainage_ceiling(5.0)[0] == "L2"
    assert drainage_ceiling(10.0)[0] == "L2"
    assert drainage_ceiling(20.0)[0] == "L1"
    assert drainage_ceiling(20.0)[1], "an L1 ceiling must say why"


def test_preview_states_the_ceiling_and_leaves_terrain_unverified() -> None:
    result = preview(HSK)
    assert result["rows"] == 117 and result["cols"] == 148
    assert result["cells"] == result["rows"] * result["cols"]
    assert result["drainageCeiling"]["level"] == "L2"
    # Terrain is only knowable after s01, so the preview must not promise it.
    assert result["terrainCeiling"]["level"] == "unverified"


def test_preview_cost_class_is_derived_not_timed() -> None:
    result = preview(HSK)
    assert result["costClass"] in {"small", "medium", "large"}
    assert "minutes" not in json.dumps(result).lower()


# --------------------------------------------------------------------------- #
# Seal semantics
# --------------------------------------------------------------------------- #


def _manifest() -> Manifest:
    return Manifest(
        area_id="test-area",
        grid={"rows": 117, "cols": 148, "resolutionM": 5.0},
        stages={
            "s03_terrain": StageRecord(
                name="s03_terrain",
                status=StageStatus.OK,
                artefacts=["dem.npy"],
                sources=[SourceRef(
                    provider="csdi", dataset="open3dhk",
                    url="https://example.test/x", retrieved="2026-11-26",
                    licence="CSDI terms",
                )],
                gates=[Gate("nodataShare", 0.0, True)],
                started="t0", finished="t1",
            ),
            "s04_buildings": StageRecord(
                name="s04_buildings",
                status=StageStatus.DEGRADED,
                artefacts=["buildings.geojson"],
                gates=[Gate("footprintCount", 0, False, "no footprints")],
                note="no footprints; massing axes unavailable",
            ),
        },
        capabilities={
            "drainage": Capability(
                axis="drainage",
                level=CapabilityLevel.STANDARD_PROXY,
                basis="SDM 2024, 134 mm/h",
                limits=("no channel geometry in this extent",),
            ),
        },
        gaps=[{"axis": "massing", "reason": "no footprints"}],
        sealed_at="t2",
    )


def test_manifest_round_trips_through_disk(tmp_path: Path) -> None:
    original = _manifest()
    path = tmp_path / "manifest.json"
    original.write(path)

    restored = Manifest.read(path)
    assert restored.to_dict() == original.to_dict()
    assert restored.capability("drainage").level is CapabilityLevel.STANDARD_PROXY
    assert restored.level_of("massing") is CapabilityLevel.UNAVAILABLE
    assert restored.is_sealed


def test_degraded_and_stale_are_usable_but_failed_is_not() -> None:
    ok = StageRecord(name="s03_terrain", status=StageStatus.OK)
    degraded = StageRecord(name="s03_terrain", status=StageStatus.DEGRADED)
    stale = StageRecord(name="s03_terrain", status=StageStatus.STALE)
    failed = StageRecord(name="s03_terrain", status=StageStatus.FAILED)
    for record in (ok, degraded, stale):
        assert record.status.usable
        assert Manifest(area_id="a", stages={"s03_terrain": record}).ready("s03_terrain")
    assert not failed.status.usable
    assert not Manifest(area_id="a", stages={"s03_terrain": failed}).ready("s03_terrain")


def test_missing_stage_is_not_ready_rather_than_an_error() -> None:
    assert Manifest(area_id="a").ready("s03_terrain") is False


def test_unknown_schema_version_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schemaVersion": 99, "areaId": "a"}))
    with pytest.raises(ManifestError, match="schemaVersion"):
        Manifest.read(path)


def test_manifest_read_reports_a_missing_file_by_name(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="no manifest"):
        Manifest.read(tmp_path / "absent.json")


def test_resuming_a_manifest_for_another_area_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    _manifest().write(path)
    with pytest.raises(ManifestError, match="belongs to area"):
        Manifest.load_or_new(path, "other-area")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


class _FakeStage:
    def __init__(self, name: str, requires: tuple[str, ...],
                 action) -> None:
        self.name = name
        self.requires = requires
        self._action = action

    def run(self, ctx: StageContext) -> StageRecord:
        return self._action(ctx)


def _ok(name: str):
    return lambda ctx: StageRecord(name=name, status=StageStatus.OK,
                                   artefacts=[f"{name}.bin"])


def _runner(stages, tmp_path: Path) -> Runner:
    return Runner(stages, _area(), tmp_path)


def test_runner_orders_by_dependency(tmp_path: Path) -> None:
    calls: list[str] = []

    def record(name):
        def action(ctx):
            calls.append(name)
            return StageRecord(name=name, status=StageStatus.OK)
        return action

    stages = [
        _FakeStage("s06_waterways", ("s03_terrain",), record("s06_waterways")),
        _FakeStage("s03_terrain", (), record("s03_terrain")),
        _FakeStage("s05_landcover", ("s03_terrain",), record("s05_landcover")),
    ]
    manifest = _runner(stages, tmp_path).run()
    assert calls.index("s03_terrain") < calls.index("s05_landcover")
    assert calls.index("s03_terrain") < calls.index("s06_waterways")
    assert manifest.is_sealed


def test_runner_skips_usable_stages_on_a_second_run(tmp_path: Path) -> None:
    calls: list[str] = []

    def action(ctx):
        calls.append("s03_terrain")
        return StageRecord(name="s03_terrain", status=StageStatus.OK)

    runner = _runner([_FakeStage("s03_terrain", (), action)], tmp_path)
    runner.run()
    runner.run()
    assert calls == ["s03_terrain"]


def test_force_reruns_a_usable_stage(tmp_path: Path) -> None:
    calls: list[str] = []

    def action(ctx):
        calls.append("s03_terrain")
        return StageRecord(name="s03_terrain", status=StageStatus.OK)

    runner = _runner([_FakeStage("s03_terrain", (), action)], tmp_path)
    runner.run()
    runner.run(force=True)
    assert calls == ["s03_terrain", "s03_terrain"]


def test_gate_failure_degrades_and_keeps_the_artefact(tmp_path: Path) -> None:
    def action(ctx):
        raise GateFailure(Gate("nodataShare", 0.4, False, "40% nodata"), "filled")

    manifest = _runner([_FakeStage("s03_terrain", (), action)], tmp_path).run()
    record = manifest.stages["s03_terrain"]
    assert record.status is StageStatus.DEGRADED
    assert record.status.usable
    assert "40% nodata" in record.note
    assert manifest.is_sealed, "a degraded stage is still a finished run"


def test_exception_fails_the_stage_and_names_the_blocker_downstream(
    tmp_path: Path,
) -> None:
    def boom(ctx):
        raise RuntimeError("tile service returned 503")

    stages = [
        _FakeStage("s03_terrain", (), boom),
        _FakeStage("s04_buildings", ("s03_terrain",), _ok("s04_buildings")),
    ]
    manifest = _runner(stages, tmp_path).run()

    assert manifest.stages["s03_terrain"].status is StageStatus.FAILED
    assert "RuntimeError" in manifest.stages["s03_terrain"].note
    assert manifest.stages["s04_buildings"].status is StageStatus.PENDING
    assert "s03_terrain" in manifest.stages["s04_buildings"].note
    assert not manifest.is_sealed
    assert manifest.has_failures


def test_a_stage_returning_the_wrong_type_is_a_failure(tmp_path: Path) -> None:
    manifest = _runner(
        [_FakeStage("s03_terrain", (), lambda ctx: {"status": "ok"})], tmp_path
    ).run()
    assert manifest.stages["s03_terrain"].status is StageStatus.FAILED
    assert "StageRecord" in manifest.stages["s03_terrain"].note


def test_empty_registry_refuses_instead_of_sealing_nothing(tmp_path: Path) -> None:
    with pytest.raises(RunnerError, match="no stages"):
        Runner((), _area(), tmp_path).run()


def test_unknown_stage_name_is_a_typo_not_an_extension(tmp_path: Path) -> None:
    with pytest.raises(RunnerError, match="not in STAGE_ORDER"):
        topological_order([_FakeStage("s99_made_up", (), _ok("s99_made_up"))])


def test_duplicate_stage_names_are_refused() -> None:
    with pytest.raises(RunnerError, match="two stages"):
        topological_order([
            _FakeStage("s03_terrain", (), _ok("s03_terrain")),
            _FakeStage("s03_terrain", (), _ok("s03_terrain")),
        ])


def test_dependency_cycle_is_refused() -> None:
    with pytest.raises(RunnerError, match="cycle"):
        topological_order([
            _FakeStage("s03_terrain", ("s04_buildings",), _ok("s03_terrain")),
            _FakeStage("s04_buildings", ("s03_terrain",), _ok("s04_buildings")),
        ])


def test_only_runs_the_named_stage_and_records_the_rest_as_blocked(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def action(ctx):
        calls.append("s04_buildings")
        return StageRecord(name="s04_buildings", status=StageStatus.OK)

    stages = [
        _FakeStage("s03_terrain", (), _ok("s03_terrain")),
        _FakeStage("s04_buildings", ("s03_terrain",), action),
    ]
    manifest = _runner(stages, tmp_path).run(only=["s04_buildings"])
    assert calls == []
    assert "s03_terrain" not in manifest.stages
    assert manifest.stages["s04_buildings"].status is StageStatus.PENDING
    assert not manifest.is_sealed


def test_unknown_only_target_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunnerError, match="unknown stage"):
        _runner([_FakeStage("s03_terrain", (), _ok("s03_terrain"))], tmp_path).run(
            only=["s99_nope"]
        )


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #


def test_area_root_rejects_traversal() -> None:
    with pytest.raises(AreaError):
        area_root(Path("/tmp/data"), "../escape")
    with pytest.raises(AreaError):
        area_root(Path("/tmp/data"), "a/b")


def test_source_path_rejects_traversal() -> None:
    with pytest.raises(CacheError):
        source_path("../evil", "pipe", "key", ".tif")
    with pytest.raises(CacheError):
        source_path("dsd", "pipe", "key", "/etc/passwd")
    with pytest.raises(CacheError):
        source_path("dsd", "pipe", "key", ".tif/../x")


def test_content_key_is_stable_and_separator_disjoint() -> None:
    assert content_key("dsd", "pipe", "SWD1") == content_key("dsd", "pipe", "SWD1")
    assert content_key("dsd", "pipe", "SWD1") != content_key("dsd", "pi", "peSWD1")
    assert len(content_key("a", "b")) == 16
