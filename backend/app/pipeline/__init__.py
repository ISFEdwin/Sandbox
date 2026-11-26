"""Area preparation pipeline.

One area definition in, one sealed bundle out. See ``docs/PIPELINE.md``.

The three modules that matter:

* :mod:`app.pipeline.area` -- the area record, the resolution policy, and the
  preview shown before anything is downloaded. Pure arithmetic.
* :mod:`app.pipeline.manifest` -- the seal. A consumer reads this instead of
  guessing an artefact path.
* :mod:`app.pipeline.runner` -- the stage DAG, idempotent and resumable.

Nothing in this package imports numpy, so a script can read a seal, derive a
grid, or run the stage machinery without the raster stack installed.
"""

from app.pipeline.area import (
    MAX_AREA_HA,
    MAX_CELLS,
    RESOLUTION_LADDER,
    STAGE_ORDER,
    AreaError,
    AreaRecord,
    GridSpec,
    area_root,
    derive_grid,
    drainage_ceiling,
    preview,
)
from app.pipeline.manifest import (
    Capability,
    CapabilityLevel,
    Gate,
    Manifest,
    ManifestError,
    SourceRef,
    StageRecord,
    StageStatus,
)
from app.pipeline.runner import (
    GateFailure,
    Runner,
    RunnerError,
    Stage,
    StageContext,
)

__all__ = [
    "MAX_AREA_HA",
    "MAX_CELLS",
    "RESOLUTION_LADDER",
    "STAGE_ORDER",
    "AreaError",
    "AreaRecord",
    "Capability",
    "CapabilityLevel",
    "Gate",
    "GateFailure",
    "GridSpec",
    "Manifest",
    "ManifestError",
    "Runner",
    "RunnerError",
    "SourceRef",
    "Stage",
    "StageContext",
    "StageRecord",
    "StageStatus",
    "area_root",
    "derive_grid",
    "drainage_ceiling",
    "preview",
]
