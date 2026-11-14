# Architecture decision records

**Status:** reconstructed 14 Nov 2026. **Read this first.**

The original ADR records were written in the project's private working folder and did not survive into
this repository. The *decisions* did: the code enforces all twelve of them, and the citations in
`backend/app` and `frontend/src` name them. What is below is therefore a **reconstruction**, written from
the code that enforces each decision — not the original records, and not a claim to know the reasoning
that was discussed when they were taken.

That distinction matters for how to use this file:

- It is enough to **review** the design. Each entry states the decision, where it is enforced, and what
  it costs, and every entry is checkable against the code it names.
- It is not enough to **reconstruct the history**. If the reasoning behind one of these matters — why the
  curve-number table is what it is, why the error envelope has two shapes — the reasoning is not here and
  has to come from the team.
- Each entry is a **commitment**. A decision that is no longer right should be superseded by a new entry
  that says so, not quietly edited. The numbering continues from the originals; the gaps (ADR-001 to
  ADR-006, and the numbers between those listed here) are entries that were never cited by anything and
  are not reconstructed here.

The decisions below are load-bearing for the register work: ADR-020 in particular is what lets the
PostGIS swap stay a storage swap rather than a schema migration, and ADR-027 is what keeps the wire and
the store from having to agree on column names.

---

## ADR-007 — Coordinates on the wire, metres only for measurement

All coordinate values are EPSG:4326 (degrees) on the wire, everywhere, in every schema and every store
row. The one exception is *measurement*: the degree-to-metre conversion happens exactly once, at
`app/services/geo_import.py::build_grid`, which derives a metric working grid from a lon/lat extent using
a local equirectangular approximation about the extent centre. At a 3 km extent the error against
HK1980 Grid is far below the 5 m cell size, and nothing projected ever leaves that function. **Enforced
by:** `app/config.py` (the rule is stated there), `app/services/geo_import.py::build_grid`. **Cost:** the
API cannot accept projected coordinates, so a client that has them must convert first. **Kept because:**
one coordinate system on the wire means every consumer — frontend, tests, the store — agrees without a
conversion table.

## ADR-009 — The metric working grid is derived, not stored

The scene's `working_grid` (extent, 5 m cell size, row/column counts) is *derived* from the study area's
bounds by the same `build_grid` the ingest path uses, and recorded on the scene so that every raster and
every run is built against the same grid. **Enforced by:** `scripts/seed_scene.py`, `app/services/geo_import.py::build_grid`.
**Cost:** the grid is only as good as the bounds it came from. **Kept because:** the overlay scripts, the
ledger and the rasteriser must agree on cell indexing exactly, and one derivation is the only way to
guarantee that.

## ADR-012 — The documented ingest path is not implemented

The target ingest path — `ogr2ogr` / `ST_Transform` for vectors, `gdal_translate` plus a MinIO upload
for raster COGs — is documented but deliberately not implemented, because neither toolchain can be
provisioned on the machine this project runs on. What survives the swap is the contract: everything
downstream keeps consuming `scene.terrain_url` and `scene.imagery_url` as opaque references, so the
implementer of the real path changes nothing else. **Enforced by:** `app/services/geo_import.py` (module
docstring). **Cost:** the demo's data was prepared by hand rather than ingested. **Kept because:** a
documented-but-unimplemented path that everything else is written against is better than an
implementation nobody can run.

## ADR-015 — Generation and retention are partitioned; no cell is counted twice

Land cover sets the **generation** term (how much runoff a cell produces) and explicit storage sets the
**retention** term (how much water a cell can hold), and no cell contributes to both. A retention class
generates nothing of its own: open water and wetland produce no runoff, so a pond is never counted as
runoff *and* as storage. The partition is driven off one declaration (`COUNTED_AS`) rather than a literal
list, so the declaration and the implementation cannot drift apart. **Enforced by:**
`app/services/sandbox_model.py` (`_runoff_and_unstored`, the curve-number and storage-depth tables),
`scripts/_overlay_common.py` (`COUNTED_AS`, `STORAGE_DEPTH_M`), and the `assumptions` block of
`data/rasters/wetgrid_hsk.json`, which publishes it. **Cost:** the wetland case was worth roughly 2× on
the wetland contribution before the partition was enforced. **Kept because:** it is the difference between
a runoff number and a double-counted one.

## ADR-020 — Store mode is configuration, not architecture

`STORE_MODE=file` backs the identical API contract with JSON on disk. `STORE_MODE=postgis` is the
documented target and is a swap of `app/db.py` and `app/services/scene_service.py` **only** — no route,
no schema, no frontend change. The contract must not move when the store does, and
`tests/test_openapi_contract.py` is the tripwire that proves it. **Enforced by:** `app/config.py`
(`store_mode`), `app/db.py` (the `assert_store_mode` guard), and the contract test. **Cost:** the file
store cannot serve two concurrent customers, and `app/db.py` raises on the `postgis` path rather than
serving it. **Kept because:** it is what makes the multi-tenant store a *storage swap* and not a schema
migration — the difference between a three-week job and a three-month one.

## ADR-024 — Per-run inputs are not persisted onto the scene

The run request's inputs (rainfall, temperature, tide state) belong to a *run*, not to the object every
plan hangs off, so they are never written onto the scene. `scene.envParams` holds only *static,
location-derived* defaults. **Enforced by:** `app/schemas/scene.py` (`RunRequest`, `EnvParams`),
`frontend/src/state/sceneStore.ts`, `frontend/src/components/SlidersPanel.tsx`. **Cost:** a run is not
reproducible from the scene alone; the run's inputs have to be carried with the run. **Kept because:**
persisting them made every plan depend on the last slider position, which is the trap the frontend
store's own comment warns about.

## ADR-026 — One data authority, one place

Every read and write of a scene, plan or intervention passes through `app/services/scene_service.py`.
The frontend never touches storage directly, and the boundary between what a model may propose and what
the system will compute is enforced in this one place. **Enforced by:** `app/services/scene_service.py`
(module docstring), and the absence of any other write path. **Cost:** the service is the bottleneck for
every new feature — which is why the register work routes its own writes through it rather than
alongside it. **Kept because:** the store is a file store today and a Postgres store tomorrow, and one
choke point is what makes that swap possible.

## ADR-027 — The wire is camelCase, the store is snake_case, and the translation lives in one place

Storage is snake_case and mirrors the DDL column for column; the wire is camelCase. The translation
happens exclusively in `app/schemas` (`WireModel` / `RowModel`), never in a router and never in a
service. This is what resolves the specification's own `id` vs `sceneId` contradiction without renaming
a column. **Enforced by:** `app/schemas/scene.py` (the `WireModel` / `RowModel` bases),
`app/services/scene_service.py`. **Cost:** two names for one thing, and a mapping to keep in step.
**Kept because:** the column names are the PostGIS schema, and the schema is not ours to rename.

## ADR-028 — One error envelope, with `detail` kept

The specification says both "422 returns FastAPI's default detail array" and "externally always use
`{"error": {...}}`", which contradict. Both are satisfied: handlers emit `error` *and* keep `detail`,
and every body also carries a machine-readable `code`. **Enforced by:** `app/main.py` (the error
handlers), `app/services/scene_service.py` (`code` feeds the envelope). **Cost:** a body carries the
same fact twice. **Kept because:** the frontend then needs one error branch instead of three, and a
client that expects FastAPI's default shape is not broken by the richer one.

## ADR-030 — `status` is a server-owned column

A caller cannot assert `status='validated'` on create: the service hard-codes `draft`, and a separate
validation step is required before the engine will compute on the geometry. The column is
`CHECK IN ('draft','validated')`. **Enforced by:** `app/models/intervention.py` (the storage contract),
`app/services/scene_service.py`. **Cost:** the lifecycle is declared in the schema but not yet read by
any engine path — a feature's status does not currently affect whether it is computed on. That gap is
the register's first job (F1) and it is recorded in `STATUS.md` §3. **Kept because:** without it, any
client could mark its own proposal as validated.

## ADR-032 — Discrete features may extrude; continuous fields never do

An intervention is geometry with a style, and `extrusion_height` is only meaningful for discrete
features. Continuous fields (the heat field, the flood extent, the wind corridor) are rendered as
georeferenced imagery — one image beats thousands of extruded polygons, both in payload and in
legibility. **Enforced by:** `app/schemas/intervention.py` (`Style.extrusion_height`),
`frontend/src/view/terrainLoader.ts`, `frontend/src/view/SandboxViewer.tsx`. **Cost:** a continuous
field cannot be styled per-cell. **Kept because:** the viewer's performance is a function of what it
draws, and this is the rule that keeps it drawing fields as fields.

## ADR-033 — No Cesium Ion token is ever required

The demo runs with zero credentials: imagery comes from an OSM tile template rather than Cesium Ion, and
the frontend treats a `terrain_url` / `imagery_url` as an opaque reference so a real COG can be
swapped in later without touching the viewer. **Enforced by:** `scripts/seed_scene.py`
(`OSM_TILE_TEMPLATE`), `frontend/src/view/terrainLoader.ts`, `frontend/src/vite-env.d.ts`. **Cost:**
OSM tiles are not a terrain product. **Kept because:** a demo that needs a token is a demo that cannot
be run by the person evaluating it.

---

## Adding an entry

One paragraph, in the same shape as the entries above: the decision, where it is enforced (file and
symbol), what it costs, and why it was kept. Number it after the highest number here. If it supersedes an
existing decision, say so in the new entry and leave the old one alone — a record that is edited is not a
record.
