"""Stage implementations, in the order :data:`app.pipeline.STAGE_ORDER` names.

Increment A ports the existing scripts here with their physics unchanged:

| Stage | Ported from |
|---|---|
| ``s03_terrain`` | ``scripts/tiles_to_rasters.py`` + ``scripts/hydrology.py`` |
| ``s04_buildings`` | ``scripts/tiles_to_buildings.py`` + ``scripts/build_buildings.py`` |
| ``s05_landcover`` | ``scripts/fetch_landcover.py`` + ``scripts/build_landclass.py`` |
| ``s06_waterways`` | ``scripts/make_waterway_mask.py`` |
| ``s07_drainage`` | new (Increment B) |
| ``s08_climate`` | ``scripts/fetch_site_wind.py``, HKO helpers |
| ``s09_presentation`` | ``scripts/make_wetgrid.py`` + ``scripts/make_heatmap.py`` |

The port is deliberately mechanical: the scripts keep their maths and lose
their hardcoded extent. That is what makes "byte-identical HSK" a meaningful
acceptance test for Increment A.

Until a stage is implemented it is not registered. Registration is how the
runner knows a stage exists, and an empty registry is why a prepare currently
refuses to run instead of producing a sealed bundle with nothing in it.
"""

from __future__ import annotations

from app.pipeline.runner import Stage

#: Registered stages. Populate as Increment A lands each port.
STAGES: tuple[Stage, ...] = ()
