# Project import — bringing a scheme into the existing scene

**Status: spec only, written 26 Nov 2026.** Nothing described here is implemented. The one import path
that works today is a repository edit plus a seed script (§2). This file exists so the work has a
contract before it has code, and so the next person does not have to rediscover why the engine cannot
accept a file yet.

**What this document is:** the shape of `POST /api/scenes/{sceneId}/imports`, what it must compute,
what it must refuse, and the order the pieces have to land in.

**What it is not:** a declaration. An import puts geometry and stated effects on the sandbox so the run
can score them. It does not sign anything, it is not a hash-and-timestamp record, and it is not the
object B3 describes. An imported project is a *staged scheme* — the same trust level as a hand-drawn
intervention today. The register's standing starts at B3/B4.

---

## 1. Three things "import" can mean

They are different amounts of work and must not be conflated in a plan or a demo.

| Tier | What arrives | What it needs | Where it stands |
|---|---|---|---|
| **T1 — effect-only project** | A footprint polygon plus declared effects (`storageDepthM`, green, paving). No 3D model. | A `data/projects/<id>.json`, a footprint file, `seed_projects.py` | **Works today, off-repo only.** It appears as a row in `ProjectCatalog` because the seeder tags the plan with `params.projectId`, and toggling it changes the run. Nothing is drawn at its location beyond the intervention polygons. |
| **T2 — modelled project** | T1 plus a GLB, an origin and a scale. | `compute_plan_project_footprint.py` derives the footprint from the model; the GLB is 79–82 MB at present | **Works today, off-repo only.** Drawn by `SandboxViewer` from `terrain.projects`; the label and marker come from `data/projects/<id>.json`. |
| **T3 — a third party's file** | IFC, RVT, DWG, GeoJSON massing, Shapefile/GPKG. | A converter, a massing path, and an asset store | **Not supported at all.** There is no IFC/DXF/DWG/Shapefile/GPKG reader anywhere in `app/` or `scripts/`. |

The urgent ask is T1 and T2 over HTTP. T3 is a different project (I2) and should not be promised in
the same breath.

---

## 2. What exists today, and the seam it already leaves

Everything below is real and reusable. The importer should call it rather than re-derive it.

| Piece | Where | What the import uses it for |
|---|---|---|
| Project declaration | `backend/data/projects/<id>.json` | The schema an import writes: `id`, `name`, `footprint`, `model`, `origin`, `scale`, `label`, `effects[]` |
| Seeder | `scripts/seed_projects.py` | `interventions_for()` already does the right thing: **one intervention per declared effect, all on the same ring**, and refuses an unknown kind |
| Plan id | `seed_projects.plan_id_for()` | Deterministic `project-<id>`; the `project-` prefix is what `.gitignore` allowlists |
| Effect table | `sandbox_model.INTERVENTION_EFFECTS` | The closed set of kinds and — more importantly — the kinds that are **declared but not scored** (`road`, `drainage`, `drainage_alignment`, `massing_height`) with the reason |
| Scored predicate | `sandbox_model.effect_is_scored()` | Separates "this moves the grid" from "this is drawn and disclosed" — the importer must report which, per effect |
| Placement guard | `services/proposal_constraints.py` | Building overlap, single cap 25%, cumulative cap 40%, clip fraction 0.25. It currently reads a fixed `rasters/buildings_hsk.json`; §4 step 4 points it at the scene's own file |
| Cell rasterisation | `sandbox_model._polygon_cells`, `services/intervention_geometry.py` | Cells, hectares, coverage fraction. Marching-squares contours already exist if an imported footprint needs re-tracing |
| Consent seam | `services/consent.py` | A declared project over the cap is applied and flagged, not refused; an undeclared one is refused. The importer must pass `declarationId`/`declarationStatus` through |
| Wire validation | `schemas/intervention.py::InterventionIn` | EPSG:4326 range check, ring closure, minimum positions — reuse it, do not retype the predicates |
| Render path | `view/interventionLayer.ts`, `view/SandboxViewer.tsx` | `style {color, opacity, extrusionHeight}`; project models are loaded per `terrainMeta.projects` entry |
| List surface | `frontend/src/components/ProjectCatalog.tsx` | Rows are *plans carrying `params.projectId`*, so a new project needs no frontend list edit |

**The seam is already the right shape.** A project is data, not code; a plan id is deterministic; the
panel reads the plans, not a constant. What is missing is a route, a report, and a place to put an
uploaded asset.

---

## 3. The contract

Two-phase on purpose: `dryRun` validates and reports without writing, then the same body commits.
A rejected import must not leave a half-written plan behind, because a plan is a thing the run scores.

```http
POST /api/scenes/{sceneId}/imports?dryRun=true
Content-Type: application/json

{
  "projectId": "acme-tower",
  "name": "ACME Tower",
  "footprint": { "type": "Polygon", "coordinates": [[[113.9931, 22.4322], "..."]] },
  "effects": [
    { "kind": "underground_tank", "params": { "storageDepthM": 2.5 } },
    { "kind": "green_space", "params": {} }
  ],
  "model": {
    "url": "/static/model/acme_tower.glb",
    "origin": [113.9931, 22.4322],
    "scale": 50,
    "label": "ACME Tower"
  },
  "declaredBy": null,
  "note": "scheme issued for comment 2026-11-26"
}
```

`model` is optional: without it the import is T1, and the project is byte-for-byte the shape the
seeder already produces.

### The report

The response is the product. A number the user cannot read a caveat from is the failure mode this
project has spent its whole design avoiding (E2 in TODO.md).

```json
{
  "importId": "imp_...",
  "status": "ACCEPTED | REJECTED | NEEDS_FACTS",
  "dryRun": true,
  "digest": "sha256:...",
  "projectId": "acme-tower",
  "planId": "project-acme-tower",
  "footprint": { "served": { "..." : "..." }, "clippedCells": 0, "clippedFraction": 0.0 },
  "size": { "cells": 812, "areaHa": 2.04, "coverageFraction": 0.0469 },
  "buildings": { "overlapCells": 0, "buildingIds": [] },
  "caps": { "singleCap": 0.25, "cumulativeCap": 0.40,
            "withinSingleCap": true, "withinCumulativeCap": true },
  "effects": [
    { "kind": "underground_tank", "scored": true,  "why": "stores water beneath an unchanged surface" },
    { "kind": "green_space",     "scored": true,  "why": "vegetated ground generates less runoff" }
  ],
  "axes": { "flood": true, "heat": false, "green": true, "wind": false, "impervious": false },
  "assumptions": [ { "parameter": "storageDepthM", "value": 2.5, "status": "USER_INPUT",
                     "source": "imported declaration", "date": "2026-11-26" } ],
  "furtherInformation": [
    "Storeys are not supplied. Massing height is not applied.",
    "Phase dates are not supplied. The project is scored as present in every run.",
    "Soil group is not declared. Curve numbers use the district default (HSG D)."
  ],
  "screeningLabel": "Broad-brush screening. Not an environmental permit, not a section 16 decision.",
  "rejections": []
}
```

Three fields carry the honesty:

- **`axes`** is *derived from the effect kinds*, not asked of the user. A project that declares only
  `underground_tank` and `green_space` cannot claim it changes wind. This mirrors `comparison.py`'s
  refusal to emit a combined score.
- **`furtherInformation`** is not optional and not empty when a fact is missing. Removing it must fail
  a test, exactly as it does for the government fit (G5).
- **`effects[].scored`** publishes the distinction that already exists in `effect_is_scored()`. An
  imported `road` is drawn, disclosed, and contributes nothing — and the report says so rather than
  leaving the user to wonder why the numbers did not move.

---

## 4. What the importer must compute, in this order

The order is the guard. Every step is a refusal point, and a refusal is a `REJECTED` report, not a
500.

1. **Validate the geometry.** EPSG:4326, closed outer ring, ≥4 positions, Polygon or MultiPolygon.
   Reuse `InterventionIn._check_geometry`.
2. **Clip to the scene bbox.** Refuse when the whole footprint falls outside (`clipFraction == 1.0`),
   refuse above `MAX_CLIP_FRACTION` (0.25). This is the check that stops a scheme being silently
   scored against the wrong district — the same class of fault the Linux deploy exposed (§11.2 of
   STATUS.md).
3. **Rasterise to the working grid.** Cells, hectares, `coverageFraction` against the scene's own
   cell count. Never a hard-coded 17,316: read `Grids.rows * cols`.
4. **Test building overlap** against `scene_service.buildings_path(sceneId)`, not against a fixed
   `buildings_hsk.json`. Return the ids so the user can see *which* buildings the scheme lands on.
5. **Apply the caps.** Single 25%, cumulative 40% over the plans already active. Over a cap and
   `declaredBy` present → applied and flagged (consent seam). Over a cap and undeclared → refused.
6. **Resolve each effect** through `INTERVENTION_EFFECTS`. An unknown kind is a 422 naming the known
   kinds — the seeder already refuses this way.
7. **Ground the drawing.** Set polygon `height` from the DEM at the footprint and
   `extrudedHeight = height + extrusionHeight`. **This is a known defect in the existing pipeline**:
   `applyStyle` sets `extrusionHeight` and `heightReference = NONE` but no base height, so a 1.5–2 m
   extrusion on ground at 8–12 m is buried and does not draw. The importer must not inherit it, and
   the fix should be made in `interventionLayer.ts` so the drawn layer and the import agree.
8. **Write the plan** with `params.projectId`, `params.importId`, `params.digest`, and the note.
   One plan per project, deterministic id, refusing to overwrite an existing one (see §6).
9. **Return the report.** A run is a separate, explicit `POST /run` — importing must not start one.

---

## 5. Formats

| Format | Verdict | Note |
|---|---|---|
| GeoJSON Polygon / MultiPolygon | **Accept (I0)** | The native shape. Already validated by the intervention schema. |
| GLB + origin + scale | **Accept (I0)** | Asset goes to the model store by reference; the JSON body carries the URL, never the bytes. |
| GeoJSON FeatureCollection with `height_m` per feature | **Accept (I1)** | Becomes a `station_massing`-style geometry-only effect: shade and exposure move, land cover does not. Same shape as the existing 396 footprints. |
| CSV / JSON of declared numbers (storage depth, green area, phase dates) | **Accept (I0)** as facts, not geometry | These are the `params` a run reads; they belong in `assumptions[]`. |
| GPKG / Shapefile | **Defer (I2)** | The realistic QP deliverable. Needs `pyogrio`/`fiona`; the team's rule is no new dependency without permission. |
| IFC | **Defer (I2)** | Only a footprint-plus-heights subset is usable; needs IfcOpenShell. Do not claim BIM ingestion. |
| RVT / DWG | **Refuse, with the reason** | No open converter, no licence. Say so in the 422 rather than accepting a file that was converted by hand off-record. |
| Anything with a non-4326 CRS | **Refuse, with the CRS named** | Silent axis swapping is the failure the schema validator already prevents. |

---

## 6. What an import must never do

1. **Never claim an effect the engine cannot compute.** `road` and `drainage` are drawn and disclosed
   with `scored: false`. Inventing a curve number for them is the invariant-5 failure the effect table
   was written to prevent.
2. **Never combine the axes.** No score, no verdict, no "net benefit".
3. **Never guess a footprint from a model's bounding box** when no footprint was supplied and no
   declared ring exists. A bbox claims empty corners, which is the fault `intervention_geometry.py`
   was written to fix.
4. **Never overwrite `project-<id>`.** A re-import is a new plan; superseding is B8's lifecycle, and
   silently mutating a scored plan is the opposite of a record.
5. **Never write a declaration.** No hash, no signature, no "as at". Those are B3 and B4, and
   pretending otherwise is the overclaim F5 guards against.
6. **Never accept model bytes in the request body.** The 250 MB serverless limit and the 82 MB GLBs
   already decided this. Reference an asset; do not transport it.
7. **Never store an import outside the scene's own record.** Two scenes must not share a project
   unless it was imported twice, deliberately.

---

## 7. Done-when — the tests that would make this real

Each of these is a test, not a sentence:

- [ ] Import a GeoJSON footprint of HSK Park's size → `ProjectCatalog` gains a third row, toggling it
      changes the run, and the ledger attributes cells to it.
- [ ] Import a 30%-of-district footprint with `declaredBy` set → **applied and flagged**, not refused
      (`consent.py`'s whole point).
- [ ] Import the same footprint without `declaredBy` → refused with `OVER_SINGLE_CAP`.
- [ ] Import a footprint entirely outside the scene bbox → `REJECTED`, no plan written, no partial file.
- [ ] Import an unknown `kind` → 422 naming every known kind.
- [ ] Import a project declaring `road` → report says `scored: false` with the reason, and a run
      reports identical numbers with the skip disclosed.
- [ ] Import twice → two plans, the first byte-identical to before.
- [ ] A/B compare with the imported project on side B → the axes the effects touch differ, and
      `combinedScore` is still `null`.
- [ ] Delete the label or the `furtherInformation` list → the test fails.

---

## 8. Phases

| Phase | Scope | Done when |
|---|---|---|
| **I0** (urgent, this sprint) | `POST /imports` with `dryRun`, T1 and T2, the report, one frontend panel | A third project enters the running app without a repository edit and a run scores it |
| **I1** (weeks) | GeoJSON massing with `height_m`; per-cell landing; a 2.5D preview *before* commit | A planner sees what will be drawn and what it covers before pressing import |
| **I2** (months) | GPKG and IFC through an offline converter script, not the API | A QP's deliverable can be brought in with one documented command |
| **I3** | Signing, versioning, supersession | B3/B4/B8 — not this document |

I0 is a precondition for A1, not a competitor to it: A1 needs "a real developer's massing entered into
the sandbox", and today that means editing JSON in a repository and re-running a seed script.

---

## 9. Known risks, with the code that causes them

| Risk | Cause | Trigger |
|---|---|---|
| An import is silently scored against the wrong grid | `load_grids()` is `@lru_cache(maxsize=1)` over fixed `*_hsk.npy` names and never compares its bounds to the scene bbox | Step 2 of §4 must refuse on bbox mismatch until the per-scene raster set lands |
| The imported feature is drawn but invisible | `applyStyle` sets `extrudedHeight` with no base `height` | Fix in `interventionLayer.ts` before I0 ships, or the demo shows nothing |
| Anyone can import anything into the public demo | No auth layer (B2) | Keep `dryRun` default-on and gate writes behind `ALLOW_IMPORTS=1` until B2 |
| Two visitors collide in the store | `STORE_MODE=file`, one worker | Same class as the existing run/residue caveat (STATUS §11.4) |
| Large massing stalls the opening view | 79–82 MB GLBs at `scale: 50`, loaded per selected project | I0 should cap the model size and prefer a decimated asset; the import report names the size |
| An import is mistaken for a declaration | The word "project" means both | Every report carries the screening label; the UI says "staged scheme", never "declared" |

---

## 10. Non-goals

- A second study area. That is the raster-set and calibration work (TODO C3), not import.
- Multi-tenant isolation for imported schemes. That is B1/B9.
- Any claim that an imported scheme is what was submitted to a board. It is what the user typed.
- A file-format zoo. Two accepted shapes and four explicit refusals beat twelve half-parsers.
