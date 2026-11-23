# Register implementation plan

> **Ground truth has moved (18 Nov 2026).** The product is a broad-brush comparison tool. The five edges — comparison across separate axes, a shared picture as the side effect of holding the schemes, natural-language intervention, the wind channel, and labelled screening — are recorded in [STATUS.md](STATUS.md) and are the ones the demo and the next deck lead with. This document is the engineering design for the shared record that follows once several parties compare in the same model. Where this file still opens by calling the register the product, [STATUS.md](STATUS.md) wins.

**Date:** 14 Nov 2026 · **Branch:** `main` @ `bcec6f7` · **Working tree:** `contracts/openapi.json` modified (see §1.5)

> ### ⚠️ State note — this plan was written against `bcec6f7`, and the repo has moved since
>
> **A second session has been working this repository concurrently** (same git identity,
> `ISFEdwin <bleepbopnotabot@gmail.com>`). Two commits landed and one work-in-flight change set
> appeared **while this document was being written**. Nothing in this plan has been reverted or
> overwritten; the note below records what has moved so the plan is not read as current.
>
> | When | What landed | Effect on this plan |
> |---|---|---|
> | 16:43 | `7f0f41c` — TODO.md: **A3 (deck rewrite) marked met** by a new 15-slide deck built from scratch (kept outside this public repo because it carries the fee schedule); **A3b** split out for the governance slide, which still depends on A4 | TODO A3 is closed. The governance slide (A3b) is the remaining piece of §10's Code-of-Practice track |
> | 17:14 | `1210193` — "contract: regenerate under pydantic 2.13.5" — **the openapi drift committed** | **W0.1 is done.** §1.4's recommendation was implemented, with the commit message this plan proposed |
> | in flight (uncommitted) | `app/config.py` — **the design storm settled at 50 mm**, with the three reasons written into the constant's docstring; `app/services/siting.py` — `RESERVOIR_MIN_INFLOW_M3 = 300.0` replaced by a storm-invariant `RESERVOIR_MIN_INFLOW_FRACTION = 0.001665`, and a hard-coded 450 mm removed from `_direct_inflow`; `scripts/_overlay_common.py` — the same rainfall correction; `scripts/make_wetgrid.py` — `--rainfall` now defaults to `DEFAULT_RAINFALL_MM` instead of 450; plus `routers/scenes.py`, `services/preview.py`, `services/scenario.py`, `services/suggest.py` | **D5 is decided** (§3.5) and **W0.4 is being executed** (§7). The `siting.py` change independently confirms the §3.6 finding that the reservoir rule was calibrated against the 450 mm world |
> | in flight | **The committed rasters are now regenerated at 50 mm** — `wetgrid_hsk.json` reads `rainfall_mm: 50.0`, `unstoredVolumeM3: 9056.8`, `wetAreaHa: 0.83`. The map and the ledger now agree | **W0.4's regeneration step is done.** The 450 → 50 drift this plan measured (§1.3) is closed |
> | in flight | `backend/tests/test_artefact_drift.py` is **referenced in `config.py` but does not exist yet** | W0.4's acceptance test is named but not written |
>
> **Status of the backend suite in that tree, measured mid-flight** (so treat it as indicative, not final):
> `test_openapi_contract` **fails** — the contract committed at 17:14 is stale again, because `routers/scenes.py` and the services changed after it was regenerated. `test_sandbox`, `test_proposal_contract`, `test_ai_plan` and `test_ledger` also fail. **None of these were touched by this session** — they belong to the concurrent work, and the tree was changing while the run executed.
>
> **§1 and §3 below are the plan as written against `bcec6f7`.** Where a row above supersedes them, the
> row above wins. Nothing else in the document has changed.
>
> **Nothing in this session committed or reverted the concurrent work.** The working-tree changes above
> belong to the other session and are left exactly as found.

---

## What this document is

The detailed build plan behind the pivot recorded in [STATUS.md](STATUS.md) §4.1 — the sandbox becomes a
**coordination register**. [TODO.md](TODO.md) remains the checklist of record; this document is the
engineering design, the sequencing, and the acceptance criteria behind TODO §A2 and §B1–B12.

**What it is not.** It is not a pitch, not a pricing document, and not a second opinion on the business
model. The business model is decided (§4.1 of STATUS); what is missing is the code.

**Two rules this document obeys, because STATUS §8 requires them to survive edits:**

- Every claim about the current code is marked **[verified]** (measured or read directly this session) or
  **[unverified]** (inferred, needs confirmation before it is relied on).
- No fee figures, competitor analysis or partner names. This repository is public (TODO E3).

---

## 0. The one page

The prototype is a **sandbox**: it runs a scenario and returns a result. The business model needs a
**register**: it holds a dated, signed, immutable record of what each project in a district declared about
its neighbours, and it can say what a given project *inherited* versus what it *caused*.

The distance between those two things is not a UI problem. It is a data-model problem: **versions,
signatures, roles, tenancy** (STATUS §3, rows 5–16). Every one of those is unbuilt.

Five findings from this session change how the work should be sequenced:

1. **The committed raster set and the engine disagree about the design storm, and five CI suites
   fail because of it.** The whole API was unified to a 50 mm default on 17 Oct 2026, but the committed
   wet-grid artefact was never regenerated — its sidecar still says `rainfall_mm: 450.0` and publishes
   180,566.3 m³ where the ledger computes 9,056.8 m³. The backend CI job is **red on this machine
   today**. The map pictures 16.8 ha of water where the ledger says 0.8 ha. → §1.3.

2. **Attribution is computable, and it is not always additive.** Measured on the real 43.5 ha grid at
   50 mm: two disjoint projects decompose with a **0.00 m³ residual** (exactly additive); two projects
   with a 50% footprint overlap leave a **+73.18 m³ residual** — 26% of the summed effect. The residual is
   not a rounding artifact. It is the legally meaningful quantity under EIAO TM §4.3.4(c), and the
   register must publish it rather than distribute it silently. → §3.1.

3. **The 40% cumulative coverage guard would silently drop real projects from a district-scale
   register.** The guard refuses the *intervention*, not the run: the project is skipped, the run still
   returns numbers, and the "aggregate" quietly omits a real development. A register whose aggregate
   omits real projects is wrong in the way that destroys its credibility. → §3.3.

4. **The register's own lifecycle gate does not exist.** `app/schemas/intervention.py:7` states "the
   engine refuses to compute on non-validated [features]". It does not: no engine path reads `status`
   at all, and every seeded project carries `status: "draft"` while being scored in live runs today.
   The claim is stale and the gate has to be built. → §3.2.

5. **The Government already publishes the wind simulation we declined to build.** The Planning
   Department's **"Site Wind Availability Data"** on the CSDI portal is the CFD and wind-tunnel
   wind regime **for the site** — free, per site, at multiple heights, with annual/summer/winter
   frequencies. So the register can *cite* the authoritative wind reference instead of modelling one:
   stronger provenance than anything this project could produce, and it removes the last argument for
   a solver. It also retires the project's own workaround of using AVRG73's single NE/ENE/E fact as
   "the one published wind-rose fact we use". → §3.6, §12.1.

**The plan in one line:** fix the committed data and the design-storm decision first (they are cheap and
they unblock CI), then build the record (declarations, versions, roles), then the thing the record is
*for* (attribution), then the coordination loop on top, and change the coverage guard before the first
real declaration lands rather than after.

**What §12 adds:** the open-source components each wave should use (and the ones it should refuse), the
skills already equipped for this work, the statutory clauses the register implements, the free public
data it can cite, and — the resource the plan is genuinely short of — **the people**: a Hong Kong EIA
consultant to sign the attribution definition, and a project office to hold the register.

---

## 1. Verified baseline

### 1.1 What runs today — [verified]

Read directly from the route table and services on `main` @ `bcec6f7`, not inferred.

| Capability | Evidence | State |
|---|---|---|
| Scenario run | `POST /scenes/{id}/run` → `run_service.run_scenario` | Built |
| Toggle / swap / compare | `/scenarios`, `/scenario/compare`, `/scenario/evaluate` → `services/scenario.py` | Built |
| Cumulative multi-project run | `RunRequest.plan_ids` merges plans server-side (`schemas/scene.py:400`) | Built |
| Assumption transparency | `GET /parameter-card` → `services/parameter_card.py` | Built |
| Storage accounting | `GET /ledger` | Built |
| Grounded GenAI | `agent/chat_service.py`, `agent/grounding.py` | Built |
| Pins | `/pins`, `services/pins.py` | Built |
| Declarations, signatures, versions, roles, tenancy, phasing | — | **Absent.** No `attribution`, `declaration`, `signature`, `tenant`, `role` or `as_at` identifier exists anywhere in `backend/app`. |

**The single most important code question in the project** (STATUS §7.1 — "Does attribution exist?") is
now **answered: no.** `/scenario/compare` ranks whole scenarios against each other under caller-supplied
weights and returns `combinedScore: null` by design. There is no per-project inherited-vs-caused object,
no signature, no version history. The *ingredients* exist — a per-cell ledger, a scenario-vs-scenario
delta, a per-project plan selection — but the decomposition itself is unbuilt.

### 1.2 Test status — [verified] (answers TODO A8)

**The headline number is misleading, and the real one is worse.**

A plain `pytest -q` in `backend/.venv313` (Python 3.13.12, pydantic 2.13.5) reports:

```
247 passed, 112 warnings in 154.06s
```

**That run did not execute five of the suites.** CI does not run `pytest` over the directory; it runs
**per file**, choosing `python file` or `pytest file` by whether the file has a `__main__` guard
(`.github/workflows/ci.yml`, "Backend suites"). Five suites — `test_hydrology`, `test_sandbox`,
`test_building_fit`, `test_ai_plan`, `test_proposal_contract` — are **standalone scripts with `check()`
calls, not `def test_*` functions**. Pytest collects nothing from them, so the 247 excludes them
entirely.

Running them the way CI does, **five suites fail**:

```
FAILING: tests/test_ai_plan.py tests/test_building_fit.py tests/test_hydrology.py
         tests/test_proposal_contract.py tests/test_sandbox.py
```

`npx tsc --noEmit` → clean (exit 0). `npm run lint` → clean (exit 0). `npm test` → **111 passed across
11 files** (191 s). `npm run build` fails in this sandbox for an environment reason, not a code reason:
Vite's `emptyDir` calls `rmSync`, which the host's delete-shim intercepts — `node-safe-delete-shim.cjs`
throws before the build starts.

**So the backend CI job is red on this machine, right now.** §1.3 is why, and it is one command to fix.

**The trap:** `backend/.venv` is Python 3.10.9 with **pydantic 2.9.2** — off-pin, and it has no pytest
at all. `requirements.txt` pins `pydantic==2.13.5` and explains why (the cp314 wheel). A green run on
`backend/.venv` proves nothing about the contract job. **Use `backend/.venv313`, or rebuild `.venv`.**

### 1.3 The committed raster set and the engine disagree about the design storm — [verified]

**This is the cause of all five failures above, and it is a live product defect, not only a test problem.**

`backend/app/config.py` records the story: the run request, the sandbox, the suggester and the preview
each defaulted to 450 mm while the scene's own `env_params.precipitation` said 50 mm, so "the default
rainfall" had two answers. The API was **unified to 50 mm on 17 Oct 2026**, and the constant carries
this note:

> "the static wet-grid overlay -- generated at 450 -- pictures 16.8 ha of water where the ledger at 50
> computes 0.8 ha. 50 mm is a one-hour design storm and 450 mm a 24-hour one, so this is not a rounding
> difference. **The overlay needs regenerating at 50 (`scripts/make_wetgrid.py --rainfall 50`) for the map
> and the ledger to agree.**"

**That regeneration was never done.** The committed sidecar still says:

```
backend/data/rasters/wetgrid_hsk.json → inputs.rainfall_mm = 450.0
                                       results.unstoredVolumeM3 = 180,566.3
```

against a ledger that computes **9,056.8 m³** at the API's own default of 50 mm — a 171,509.5 m³ gap,
against a test tolerance of 0.5 m³.

**Verified fix.** Running `scripts/make_wetgrid.py --rainfall 50` and re-running the five suites:

| Suite | Before | After |
|---|---|---|
| `test_hydrology` | 35/36 | **36/36 ✓** |
| `test_building_fit` | 30/32 | **32/32 ✓** |
| `test_sandbox` | ✗ | ✗ — *"No candidate site for the water reservoir"* |
| `test_ai_plan` | ✗ | ✗ — *"No candidate site for the water reservoir"* |
| `test_proposal_contract` | ✗ | ✗ — *"list index out of range"* |

The regenerated sidecar reads `rainfall_mm: 50.0`, `unstoredVolumeM3: 9056.8`, `wetAreaHa: 0.83` — the
ledger's own numbers, exactly.

**The remaining three failures are one cause, and it is a design question rather than a bug.** The
reservoir siting rule (`services/siting.py`) requires a *gentle-slope basin* of at least
`RESERVOIR_MIN_SITE_CELLS = 20` cells and refuses to site a reservoir in a channel. At 450 mm the ponding
spread across flats and a candidate existed. At 50 mm the only ponding left is **one 329-cell component
in the steep channel** — which the rule correctly refuses, because a channel is where the water already
goes. The rule was calibrated against the old design storm.

> **This raises a question TODO.md does not list: what *is* the baseline design storm?** 50 mm is a
> one-hour event; 450 mm is a 24-hour one. They are different physical events, not different numbers.
> The engine, the API default, the committed artefact and the siting rules currently disagree about
> which one the register's baseline is. For a product whose numbers will be quoted to a public body,
> this must be settled, in writing, and stated in the Code of Practice. → §3.5, D5.

**Note on what was changed.** The regeneration was performed as a *diagnostic* and the working tree was
restored (`git checkout --` on the raster and scene paths). The repository is left exactly as it was
found, with only `contracts/openapi.json` (the pre-existing modification, §1.5) and this plan as changes.
Deciding whether to commit regenerated artefacts is an owner call, not a side effect of a planning pass.

### 1.4 The 40% guard behaves differently than documented — [verified]

[README.md](README.md) says "The backend refuses a run that reworks more than 40% of the study area."
It does not. In `sandbox_model.apply_interventions` (`sandbox_model.py:1553-1566`) the guard skips the
**intervention** and returns it in `skipped`; `run_service` then completes the run normally and reports
the skip in `interventionsSkipped`. The run is never refused.

That distinction is the difference between "the tool says no" and "the tool quietly returns an aggregate
that omits a project" — see §3.3.

### 1.5 The openapi drift is resolved, and the fix is to commit — [verified] (answers TODO A7)

```
HEAD file    == render(pydantic 2.13.5)?  False   (5036 lines)
worktree     == render(pydantic 2.13.5)?  True    (5098 lines)
```

The uncommitted diff is **62 inserted lines, every one `"additionalProperties": true`** — a pydantic
2.9.2 → 2.13.5 rendering change on `dict[str, Any]` fields (`params`, `style`, `geometry`). `requirements.txt`
documents this exact drift and its cause.

**Action: commit the working-tree file. Do not revert it.** Reverting re-breaks the CI `contract` job,
which regenerates with the pinned 2.13.5. Commit message should say *"contract: regenerate under pydantic
2.13.5"* so the next reader knows the diff is a version artifact, not a schema change.

### 1.6 Documentation debt found while reading the code — [verified]

`backend/app` cites **ADR-007, 012, 015, 020, 024, 026, 027, 028, 030, 032** and references
`docs/ARCHITECTURE.md` and `CLAUDE.md` from dozens of docstrings. **Neither `docs/` nor `CLAUDE.md` exists
in this repository.** `.gitignore` still refers to `docs/FILE_STRUCTURE.md`.

The decisions are real and the code follows them (ADR-020's store-mode seam is visible in `db.py`; ADR-027's
camelCase-on-the-wire rule is enforced in `schemas/scene.py`). But a reader — including a future engineer —
cannot look up *why*. For a project whose pitch is "we hold a defensible record", the decision record
being unfindable is a credibility cost and a real onboarding cost.

**Recommendation:** either restore a public `docs/ADR.md` with one-paragraph entries for the ten ADRs
above, or delete the citations. Restoring is better: the ADRs are load-bearing for the register work
below (ADR-020's "store mode is configuration" constraint is what makes §3.4's tenancy carrier work).

---

## 2. The capability set

Derived from the four roles in STATUS §4.1. Each row states what the role must be *able to do* that the
product cannot do today.

| # | Capability | Who needs it | STATUS row | Wave |
|---|---|---|---|---|
| F1 | **Declaration**: declared inputs, signed, immutable, versioned | Developer, QP | 5, 6, 12 | 1 |
| F2 | **Versioned baseline**: "as at" a date, reproducible | Coordinator, Developer | 7 | 1 |
| F3 | **Roles & identity**: developer / QP / coordinator / agency | Coordinator | 9 | 2 |
| F4 | **Tenancy**: two organisations, no bleed | Coordinator, Developer | 15 | 2 |
| F5 | **Attribution**: inherited vs caused, reconciling | Developer, QP, agency | 8 | 3 |
| F6 | **Joint lock-then-declare**: see neighbours before declaring | Developer | 10 | 4 |
| F7 | **Agency review**: comments, written direction, export | Coordinator, agency | 11 | 4 |
| F8 | **Amendment lifecycle**: resubmit, supersede, withdraw | Developer | 12 | 4 |
| F9 | **Tiered disclosure**: aggregate open, detail restricted | All | 13 | 5 |
| F10 | **Public aggregate view** | Coordinator (political defence) | 14 | 5 |
| F11 | **Phasing / temporal overlap** | Developer, QP | 16 | 6 |
| F12 | **Regulatory output templates** | QP | TODO B5 | 6 |
| F13 | **Guard re-specification**: coverage cap → consent threshold | Coordinator | — (new, §1.4) | 0 |
| F14 | **Grounded chat over the register** | All | — | 3 |

F13 is not in STATUS's list because STATUS did not notice it. It is listed first because it blocks the
first real declaration (TODO A1) — see §3.3.

---

## 3. The six decisions to make before code

Each of these is a decision, not an implementation detail. Each has a recommended default so the work can
start while the decision-maker is unavailable.

### 3.1 D1 — What "caused" and "inherited" mean

**Owner:** Engineering (STATUS §4.2 B5). **Blocks:** F5, F14, TODO A2, and the whole product claim.

**Recommendation: a three-term decomposition that reconciles by construction.**

Let `L(S)` be the district ledger for a set of active projects `S`, and `L(∅)` the baseline.

| Term | Definition | Meaning |
|---|---|---|
| **Inherited** | `L(S \ {P})` evaluated for the project under examination | The condition the project found when it arrived |
| **Caused** | `L(S) − L(S \ {P})` | The project's **marginal** contribution to the current district |
| **Interaction** | `L(S) − L(∅) − Σ_P [L(S) − L(S \ {P})]` | What the projects do *together* that none does alone |

"Caused" is defined as the **leave-one-out marginal**, not the standalone effect. This matters: the
standalone effect (`L({P}) − L(∅)`) is order-dependent and does not reconcile when projects overlap. The
marginal is order-independent and the interaction term absorbs the remainder exactly.

**Why this definition and not cell-ownership alone.** Cell-ownership (assign each 5 m cell to the
project(s) that changed it) is cheaper — one run instead of n+1 — and it *localises* the interaction to
specific cells. But it cannot give a per-project marginal without also making a choice about overlap
precedence. The recommended build is **both**: cell-ownership to say *where* the interaction is, leave-one-out
to say *how much*, with the reconciliation test asserting the two agree.

**The measured behaviour this must handle — [verified]:**

| Case | A alone | B alone | Sum | Combined | Residual |
|---|---|---|---|---|---|
| MTR station + park (disjoint, real seeded projects) | −32.93 m³ | −26.83 m³ | −59.77 m³ | −59.77 m³ | **0.00 m³** |
| Two green spaces, 50% footprint overlap | −153.08 m³ | −125.63 m³ | −278.71 m³ | −205.52 m³ | **+73.18 m³** |
| Routed flood area, same overlapping pair | −0.0528 ha | −0.0126 ha | −0.0653 ha | −0.0553 ha | **+0.0100 ha** |

Grid: 117 × 148 cells @ 25.12 m² = 43.50 ha, 50 mm default rainfall. Baseline: 9,056.8 m³ unstored,
17,379.4 m³ runoff.

**Read this table as the product thesis.** With disjoint footprints the split is exact and the register
can hand a developer a clean number. With overlapping footprints, **26% of the effect is not
attributable to either party alone** — and that 26% is exactly what EIAO TM §4.3.4(c) asks about when it
requires cumulative effects "where projects interact". A register that published only per-project numbers
would publish a number that does not add up. Publishing the interaction term is what makes the register
*more* credible, not less.

**Open sub-question (needs Engineering):** the flood-extent axis routes through a D8 cascade with a
depth threshold, so it is non-linear by construction and its residual (15% in the measured case) will
always exceed the volume axis's. Does the register publish flood extent as an attributed figure at all,
or only as an aggregate? **Recommendation:** publish the volume/area axes per project (they decompose),
publish flood extent only at district level with the per-project margin reported as a *range*, and say so.
Never publish a per-project flood extent that does not reconcile.

**Acceptance (TODO A2, restated as a test):** for every scenario, `Σ caused + interaction == total effect`
to within 1e-9 m³, asserted by `tests/test_attribution.py::test_attribution_reconciles_to_the_total`.

### 3.2 D2 — The declaration lifecycle and what "signed" means

**Owner:** Team + whoever signs the Code of Practice (STATUS §4.2 B4). **Blocks:** F1, F3, F8.

**Recommendation: a content-addressed declaration with a hash chain.**

A declaration is immutable. Editing it creates a new declaration that `supersedes` the old one. The
digest is `sha256` over a canonical JSON serialisation of the declared inputs plus the previous
declaration's digest — so the chain is tamper-evident and the record's history is reconstructible.

**What "signed" must mean, honestly.** There is no PKI here and there should not be one for the pilot.
Three levels, in increasing cost, and the pilot needs only the first two:

1. **Attributed assertion** — the declaration records *who* submitted it (organisation + named individual)
   and *when*, with the digest. The server refuses to accept a declaration from a party that is not
   entitled to submit it. This is what "signed" means in a statutory-submission sense for most practical
   purposes, and it is achievable with F3 alone.
2. **Detached signature** — the submitting organisation holds a key and signs the digest. Verifiable by
   anyone holding the public key. Requires key management, rotation and revocation.
3. **Qualified electronic signature** — the Hong Kong eLegislation (Cap. 553) regime. Out of scope for the
   pilot and should not be implied.

**Recommendation: build level 1, design the digest so level 2 is an additive column, and be explicit in
the Code of Practice about which level a given declaration carries.** Over-claiming signature strength in
a document that a public body will attach to a contract is the kind of thing that ends a pilot.

**Lifecycle states** (extend `InterventionStatus`, which today has exactly two values —
`Literal["draft", "validated"]`, `schemas/scene.py:371`):

`draft → submitted → under_review → accepted → superseded` (with `withdrawn` reachable from `submitted`
and `under_review`).

**And the gate must be built, not assumed.** STATUS §3 lists the lifecycle as absent; §1.1 of this
document found that the *existing* `status` field is not read by any engine path. `apply_interventions`
never checks it — which is why the two seeded projects, both `status: "draft"`, are scored in live runs
today. Before the register accepts a declaration, `apply_interventions` must refuse features whose
declaration is not `accepted`, and `tests/test_declaration.py` must prove a non-accepted declaration is
not computed on. **This is a behaviour change to the existing sandbox**: the seeded projects will need
their declarations accepted, or the existing runs break. Sequence it deliberately, not as a side effect.

### 3.3 D3 — The coverage guard is the wrong instrument at district scale

**Owner:** Engineering + coordinator. **Blocks:** TODO A1 (the first real declaration).

**The problem — [verified].** `MAX_INTERVENTION_COVERAGE = 0.25` and `MAX_TOTAL_COVERAGE = 0.40`
(`sandbox_model.py:1194, 1203`), checked against the whole study area. On a 43.5 ha window, the
cumulative cap is 17.4 ha of reworked land. A district with eight real projects at 8% each is 64% — over
the cap. The guard was written for a specific bug (a seeded "retention basin" that was really a bounding
box over 45% of the district and produced a fictitious 63% reduction in the deficit). It solved that
problem correctly.

But its behaviour at district scale is wrong in a way the sandbox never exposed: the guard **skips the
intervention and the run completes** (§1.4). The register would publish an "aggregate" that silently
omits a real, consented development. For a product whose entire claim is that it holds a truthful record
of the district, this is the worst possible failure mode — and it would be invisible, because the run
returns plausible numbers and a `skipped` list nobody reads.

**Recommendation: replace the refusal with a threshold that escalates instead of dropping.**

| Case | Sandbox behaviour (today) | Register behaviour (proposed) |
|---|---|---|
| Single feature > 25% of study area | Refuse, report | Accept. Flag as a **major land-use change**; require counter-signature from affected neighbours |
| Cumulative > 40% | Refuse the excess feature | Accept. Flag as **district-scale composition**; trigger joint review (F6) |
| A feature is fictional (AI-proposed, unconfirmed) | Refuse | Unchanged — drafts are never computed on (§3.2) |

The distinction is the point: the guard existed to stop **invented** land-use changes. A *declared* real
development is not an invented land-use change — refusing it is the bug. The right response to a real
project that rewrites a quarter of the district is coordination, not exclusion.

**Implementation:** the cap moves from `apply_interventions` (which decides what is computed) into the
declaration/consent layer (which decides what is allowed to be *declared*). `apply_interventions` keeps a
guard, but it fires only for unconfirmed/draft features.

**Acceptance:** `tests/test_register.py::test_a_declared_project_covering_30_percent_is_not_dropped`
and `::test_an_unconfirmed_draft_covering_30_percent_is_refused`.

### 3.4 D4 — Where tenancy lives

**Owner:** Engineering. **Blocks:** F4, and the whole of F3.

**Recommendation: add `org_id` to every new row from the first commit, and lay the file store out per
tenant — even while `STORE_MODE=file`.**

ADR-020 holds that "store mode is configuration, not architecture": the PostGIS path is a swap of
`app.db` + `app.services.scene_service` with **no route, schema or frontend change**. That is a
constraint to honour, and it is the reason the recommendation is what it is:

- `db.py` becomes the tenancy boundary. Today it exposes `scene_path`/`plan_path`/`intervention_path`
  as flat functions over `settings.*_dir`. It gains `tenant_dir(org_id)` and path helpers that take a
  tenant, so every read and write is tenant-scoped by construction.
- Every new row carries `org_id` from day one, in file mode. Retrofitting a tenancy column later means a
  backfill of every table and a window where a row has no tenant — exactly the window in which data bleeds.
- The file store becomes `data/tenants/<org_id>/{scenes,plans,declarations,...}/`. This makes the
  no-bleed requirement **testable today**, without PostGIS: `tests/test_tenancy.py` asserts that
  org A cannot read org B's scene by id, by path, or by list.

**PostGIS is still required before the second concurrent participant** (STATUS §5). But it becomes a
**storage swap**, not a **schema migration** — which is what ADR-020 promised and what nobody has yet
tested.

### 3.5 D5 — What is the baseline design storm?

**Owner:** Engineering, with the consultant who will stand behind the numbers. **Blocks:** W0.3, F2's
raster-set pinning, and every published figure.

**The problem — [verified], §1.3.** The engine's default is 50 mm (a one-hour storm). The committed
artefact is 450 mm (a 24-hour storm). The siting rules were calibrated against the 450 mm world. These
are not three values for one number; they are **two different physical events**, and the register's
baseline has to be one of them.

**Recommendation: settle on 50 mm and regenerate everything from it.** Reasons:

1. The API, the run service, the suggester, the preview and `DEFAULT_RAINFALL_MM` already agree on 50 mm.
   Choosing 450 mm means re-unifying five call sites and reversing a decision the codebase already made.
2. 50 mm is the more defensible screening event for a 5 m grid: a 24-hour 450 mm storm over 43.5 ha
   produces 180,566 m³ of unstored volume — a number that swamps the district's actual storage and makes
   every intervention look negligible.
3. F2's "as at" reproducibility requires the ledger and the raster to agree. Whichever event is chosen,
   `scripts/make_wetgrid.py --rainfall <X>` becomes a committed, versioned artefact, and the design storm
   joins the Code of Practice's assumption register as a stated input rather than an inherited default.

**Then recalibrate the siting rules against the chosen storm.** The reservoir rule's slope and channel
exclusions were tuned so that a 45%-of-district "basin" could never be proposed. At 50 mm they exclude
every candidate, because the only ponding is in the channel. The rule needs a *siting* basis that works
at the chosen storm — most likely by allowing the ponding area to be derived from the design storm
rather than from the 450 mm artefact, and by keeping the "never in a channel" exclusion, which is right
on its own terms.

**Acceptance:** `test_the_committed_artefacts_and_the_ledger_agree` — a test that compares the committed
sidecar's `rainfall_mm` and `unstoredVolumeM3` against `DEFAULT_RAINFALL_MM` and the ledger, and fails
when they drift. **This one test would have caught the current state**, and it is the cheapest guard in
the project.

### 3.6 D6 — Wind: attribute it, do not simulate it

**Owner:** Engineering. **Blocks:** nothing; this is a scope decision, and it protects Wave 1.

**The question asked:** should wind channel simulation be in the next stage? **No — and the reason is
not that wind does not matter. It is that the thing simulation would be bought for, simulation cannot
deliver.**

#### The stated limitation, and why no solver fixes it

STATUS §3 row 4 marks the wind axis "partial", and TODO B11 says "Wind as a geometry axis. Currently
partial; needed before any AVA-style claim is made." The specific deficiency, stated in
`services/ventilation.py`, is that the screening **"CANNOT distinguish a north-easterly from a
south-westerly"** — which matters because the published prevailing wind for HSK is from the north-east
(AVRG73: NE/ENE/E, 40.8% of wind frequency).

A flow solver looks like the obvious fix. It is not, and the codebase already proves why.
`design_metrics.projected_width_m` states it directly:

> "**This cannot break the NE≡SW symmetry, for any orientation.** The absolute value makes each
> footprint's contribution 180°-periodic, so wind from 45° and wind from 225° always sum to the same
> total over any set of footprints. That is exact geometry rather than an approximation error — a
> convex body presents the same face to wind from either side."

**Measured on the committed 396 envelopes** (`buildings_hsk.json`, 43.5 ha site, all 16 directions):

| Opposite pair | \|FAD difference\| |
|---|---|
| NE vs SW | 0.0000000000 |
| ENE vs WSW | 0.0000000000 |
| E vs W | 0.0000000000 |
| N vs S | 0.0000000000 |

Identical to the last bit, for every pair. The 16-direction table collapses to **8 distinct values
mirrored twice**. This is a property of the metric, not of its fidelity: better geometry changes the
*numbers* but never the *symmetry*, and a CFD solve on the same geometry inherits the same symmetry —
a potential-flow solution around a symmetric arrangement is 180°-periodic for exactly the same reason.

**What does break it is a non-symmetric *arrangement*** — which the project already measures.
`design_metrics.directional_exposure` marches rays over the height raster, and the corridor endpoint
already carries it:

| Direction | Entry edge | Mean first-obstruction height | Corridor cells |
|---|---|---|---|
| NE | north-east | **15.33 m** | 169 |
| SW | south-west | **8.88 m** | 169 |
| E | east | **13.75 m** | 148 |
| W | west | **6.64 m** | 148 |

The corridor path is the same 169 cells walked in opposite directions (exact geometry, documented in
`ventilation.py`), but the **arrangement is direction-sensitive and already 73–107% apart**. The
product is not direction-blind. The *FAD endpoint alone* is, and it says so.

#### Why a solver is the wrong instrument here, in any case

1. **Resolution.** The project runs a 5 m grid over 43.5 ha. Real AVA assessment is a *building-scale*
   exercise — CFD or wind tunnel at roughly 1 m, per building, with an atmospheric boundary layer.
   A district-scale 5 m flow model would be below what ESA WorldCover land cover and tile-derived
   massing can support. It would produce a number with more decimal places than it has evidence.
2. **Liability.** STATUS §4.1's decided liability position is: the declaring party signs its inputs,
   the engine computes on them **and is liable for nothing because it is arithmetic**, the keeper is
   liable only for record integrity. A CFD solve brings mesh resolution, boundary conditions, a
   turbulence model and calibration into that sentence. "Arithmetic" stops being a defensible
   characterisation, and the whole public-sector adoption case rests on it.
3. **Cost.** The three waves that make this a register — declarations, versions, roles, attribution —
   are unbuilt. Wave 1 alone is ~3 weeks of two people. Spending it on a solver produces a more
   impressive engine and the same empty register.
4. **It would not make an AVA claim possible anyway.** The Ng & Cheng guidance the code already cites
   says the better design option is known but *"whether the better design option meets a standard
   cannot be known"*. TC 1/06's plan-level method **is** the frontal-area method this project already
   implements. Building a second, weaker solver does not buy the right to assert a verdict.

#### What to do with wind instead — four items, all in existing waves

| # | Item | Wave | Why it is the right spend |
|---|---|---|---|
| W-a | **Attribute the wind axis per project** — leave-one-out on FAD, on corridor path, and on the arrangement fields (`firstObstructionMeanM`). Add "project B's massing raises project A's first-obstruction height from X to Y" as an attributable, reconciling statement. | W3 (F5) | **This is where wind becomes register-relevant.** Two projects blocking each other's ventilation is precisely the cumulative inter-project effect EIAO TM §4.3.4(c) asks about, and it is exactly what the register is for. |
| W-b | **Build the AVA-style SVR/LVR output template** (F12) from `fadRatio` for NE/ENE/E plus the per-direction arrangement fields. | W6 (F12) | The data is already computed and published. A template is what makes the wind axis *usable in a submission*, which is where its value is. |
| W-c | **Correct the FAD endpoint's limitation note.** It currently states the screening cannot distinguish NE from SW. True of *that endpoint*; not true of the product, whose corridor endpoint already does. The note overstates the tool's blindness, and for a product whose entire pitch is "we say exactly what we know", an over-broad disclaimer is a credibility cost. | W0 (docs) | Half a day. Change "this screening therefore…" to "this metric therefore…", and point at `directional_exposure`. |
| W-d | **Optional, cheap, and currently worth nothing:** carry the ring's orientation through `footprint_from_ring` instead of discarding it to an axis-aligned bounding box. | — | `footprint_from_ring` does drop orientation (`max(xs)-min(xs)` / `max(ys)-min(ys)`, bearing left at 0), and `Footprint` *has* a `bearing_deg` field that the rest of the code honours. But the committed footprints are **already axis-aligned** — the seeded MTR station ring's longest edge bears 180.0° — so there is no orientation to recover today. Revisit only if oriented footprints ever arrive. |

#### Two stale claims found in the wind code while checking this — [verified]

1. `services/ventilation.py:12` says the method "needs nothing but the building footprints and heights,
   which the project already has for **all 2,639 envelopes**". The committed artefact
   `data/rasters/buildings_hsk.json` holds **396** features, and the string "2639" appears nowhere else
   in `backend/` or `frontend/src`. Either the number is stale or it refers to a dropped intermediate.
   **A figure quoted in a docstring of a screening tool, in a project whose product is a defensible
   record, has to be right.** Fix it or cite the source.
2. `services/ventilation.py:194-205` attributes the NE≡SW blindness to the footprints being axis-aligned
   rectangles. The blindness is in the **metric** (180°-periodicity, as `projected_width_m` proves), not
   in the rectangle-ness — orientation does not help. The note should say so, because "we would need real
   building orientations" is a false lead: real orientations would change the FAD values but not the
   symmetry.

**Recommendation: no wind channel simulation in the next stage.** Do W-a and W-b, which are register work
on machinery that already exists, and record the wind axis's limits honestly rather than simulating past
them. Revisit a real solver only if a funded pilot asks for a building-scale AVA — which is a different
project, with different data and a different liability position.

**One thing that changes the answer further, found while researching resources (§12.1):** the Planning
Department **already publishes** the CFD and wind-tunnel site wind data for HSK — "Site Wind Availability
Data" on the CSDI portal, free, per site, at multiple heights, with annual/summer/winter frequencies. So
the register does not have to simulate wind to have an authoritative wind reference; it can **cite** one.
That is stronger provenance than anything this project could produce, and it removes the last argument for
building a solver.

---

## 4. Data model

All new tables follow the existing conventions: snake_case in the store, camelCase on the wire
(ADR-027, enforced by `WireModel`/`RowModel` in `schemas/scene.py`), and `id` as the storage primary key
with the wire name carried by `_id_field`.

### 4.1 Entities

```
organisation ──┬── membership ── (role, scope)
               │
               ├── project ──── declaration ──── declaration
               │      │              │               (supersedes chain)
               │      │              └── content_hash, declared_at, signed_by
               │      │
               │      └── phase ──── (start, end, footprint)
               │
               └── baseline_snapshot ── (as_at, composed_of[], raster_set[])
```

| Table | Key fields | Notes |
|---|---|---|
| `organisation` | `id`, `name`, `kind` (coordinator / developer / qp / agency), `created_at` | The four roles are *kinds of organisation*; membership carries the role in context. A QP firm is not a developer firm. |
| `membership` | `id`, `org_id`, `person`, `email`, `role`, `scene_id`, `created_at` | `role` ∈ `developer / qp / coordinator / agency`. `scene_id` scopes the role to a district. |
| `project` | `id`, `org_id`, `scene_id`, `name`, `reference`, `site_ring`, `status`, `created_at` | A registered development. `site_ring` is the declared footprint. `reference` is the developer's own project number — the thing a submission cites. |
| `declaration` | `id`, `project_id`, `version`, `status`, `declared_by_org`, `declared_by_person`, `declared_at`, `inputs` (JSONB), `content_hash`, `prev_hash`, `supersedes` | **Immutable.** `version` increments; `content_hash` = sha256 over canonical(inputs) + prev_hash. |
| `phase` | `id`, `project_id`, `label`, `start`, `end`, `ring`, `massing` | Drives F11. A project has ≥1 phase. |
| `baseline_snapshot` | `id`, `scene_id`, `as_at`, `composition` (JSONB: project→declaration version), `raster_set` (JSONB), `created_at` | The "as at" object. `raster_set` pins the DEM/land-cover/LST versions so the baseline is reproducible even after the offline scripts re-run. |
| `attribution_run` | `id`, `snapshot_id`, `scenario`, `result` (JSONB), `created_at` | Persisted so an attribution figure is re-readable later without recomputation. |
| `review_note` | `id`, `project_id`, `declaration_id`, `author_org`, `author_person`, `body`, `kind` (comment / direction), `created_at` | F7. `kind='direction'` is the written-direction record. |
| `disclosure_policy` | `id`, `org_id`, `scene_id`, `level` (`aggregate` / `detail`), `visible_to` (org_id list) | F9. Defaults: aggregate → everyone in the scene; detail → the declaring org + the coordinator + agency. |

### 4.2 The hash chain, precisely

```
content_hash(n) = sha256(
    canonical_json({
      project_id, version, inputs, declared_at,
      prev_hash: content_hash(n-1)
    })
)
```

`canonical_json` = sorted keys, `separators=(",", ":")`, `ensure_ascii=False`, UTF-8. The same
convention `pins.fingerprint` already uses for its SHA-1 (so there is one canonicalisation rule in the
project, not two).

**Why a chain and not a bare hash.** A bare hash proves the content was not altered. A chain proves the
*history* was not altered — you cannot delete a superseded declaration without breaking the next link. For
a record whose claim is "this is what was declared, and when", that is the difference between a
tamper-evident record and a self-consistent one.

**Verification endpoint:** `GET /register/{scene_id}/declarations/{decl_id}/verify` recomputes the chain
and returns `{"ok": true, "hash": ..., "chainLength": n}`. A public body can run this. It is also the
cheapest possible trust demonstration for a keeper who is not a cryptographer.

### 4.3 Relationship to the existing `plan` model

Today a *planned project* is a `plan` with `params.projectId` (`ProjectCatalog.tsx:56` filters on it).
The register keeps that relation but makes it first-class:

- `plan.params.projectId` stays as the **seeded/demo** anchor (the two committed projects).
- A registered `project` gets a `plan` created from its accepted `declaration` — same plan shape, so
  `apply_interventions`, `run_service` and the frontend `planStore` all keep working unchanged.
- `plan.params.declarationId` and `plan.params.declarationVersion` record which declaration the plan
  was built from. **The plan is derived; the declaration is the record.**

This matters for the liability position in STATUS §4.1: the declaring party signs the *declaration*; the
engine computes on it and is liable for nothing because it is arithmetic; the keeper is liable only for
the record's integrity. The plan is a rendering of the record, not the record itself.

---

## 5. API surface

New routes, all under `/api`. Every one changes `contracts/openapi.json` (regenerate — CI enforces it).

### Declarations

| Route | Purpose |
|---|---|
| `POST /api/scenes/{id}/projects` | Register a project (developer/QP) |
| `GET /api/scenes/{id}/projects` | List the district's projects, with each one's current declaration status |
| `GET /api/scenes/{id}/projects/{pid}` | One project: current declaration, history, phase list |
| `POST /api/scenes/{id}/projects/{pid}/declarations` | Create a declaration (draft or submit in one call) |
| `GET /api/scenes/{id}/projects/{pid}/declarations` | History, newest first, with hashes |
| `GET /api/scenes/{id}/projects/{pid}/declarations/{did}/verify` | Recompute the hash chain; return ok/hash/length |
| `POST /api/scenes/{id}/projects/{pid}/declarations/{did}/submit` | Draft → submitted |
| `POST /api/scenes/{id}/projects/{pid}/declarations/{did}/review` | Agency review outcome (accept / return for amendment / direction) |
| `POST /api/scenes/{id}/projects/{pid}/declarations/{did}/withdraw` | Submitted → withdrawn |

### Baseline and versioning

| Route | Purpose |
|---|---|
| `GET /api/scenes/{id}/baseline?as_at=2027-03-12` | The composed baseline at a date, with the snapshot id it resolved to |
| `POST /api/scenes/{id}/baseline/snapshots` | Freeze a baseline snapshot (coordinator) |
| `GET /api/scenes/{id}/baseline/snapshots/{sid}` | One snapshot: composition, raster set, and the runs against it |

### Attribution

| Route | Purpose |
|---|---|
| `POST /api/scenes/{id}/attribution` | The decomposition for a project against a scenario, at a baseline |
| `GET /api/scenes/{id}/attribution/{run_id}` | A persisted attribution result, re-readable |

### Roles, review, disclosure, public

| Route | Purpose |
|---|---|
| `POST /api/sessions` | Exchange credentials for a session (identity for F3) |
| `GET /api/scenes/{id}/review` | Review queue for the coordinator/agency |
| `POST /api/scenes/{id}/projects/{pid}/notes` | Add a review note / written direction |
| `GET /api/scenes/{id}/disclosure` | **What this org can see, and who else can see it** (the B9 acceptance criterion, made a first-class endpoint) |
| `GET /api/register/{district}` | Public, read-only aggregate view (F10) |

### Changed routes

| Route | Change |
|---|---|
| `POST /api/scenes/{id}/run` | Accepts `baselineSnapshotId` / `asAt`; the response records which baseline it ran against |
| `GET /api/scenes/{id}/parameter-card` | Adds the declaration set and raster set to the `sources` block, so the card states what it was computed from |
| `GET /api/scenes/{id}/ledger` | Adds the attribution block when the run was an attributed run |

---

## 6. Feature specs

Each spec: goal → design → files → tests → *done when*.

### F1 — Declaration (Wave 1)

**Goal.** A declared input set that is immutable, attributable, versioned and verifiable.

**Design.** `declaration` rows as §4.1. Creation is the only write. There is no `PUT` on a declaration —
amendment is a new row with `supersedes` set. The `inputs` payload reuses the existing intervention
feature shape (geometry + `intervention_type` + `params`), so a declaration is expressible in the terms
the engine already understands. The `params` on each input carry the **declared value** and a `basis`
string (the seeded projects already use `basis` for exactly this — see `data/plans/project-mtr-station.json`).

**Files.**
- New: `app/models/declaration.py`, `app/schemas/declaration.py`, `app/services/declaration_service.py`,
  `app/routers/declarations.py`
- Changed: `app/db.py` (tenant-scoped paths, `append_doc` for immutable rows), `app/schemas/scene.py`
  (extend `InterventionStatus`), `app/models/intervention.py`

**Tests.** `tests/test_declaration.py`:
`test_a_declaration_cannot_be_edited_after_creation` ·
`test_amendment_creates_a_new_declaration_and_preserves_the_old` ·
`test_the_hash_chain_verifies` ·
`test_tampering_with_a_declaration_breaks_verification` ·
`test_a_declaration_from_an_unentitled_party_is_refused`

**Done when.** Editing a declared project creates a new declaration rather than mutating the old one
(TODO B3), and `verify` detects a single-character change.

---

### F2 — Versioned baseline, "as at" (Wave 1)

**Goal.** A run reproducible against "the baseline as at 12 March 2027".

**Design.** A `baseline_snapshot` freezes (a) which declaration version of which project is in force, and
(b) the `raster_set` — the digests of the DEM, land-cover and LST artefacts the run consumed. The second
half is easy to miss and fatal if omitted: the offline scripts regenerate `wetgrid_hsk.npy` and the
raster mtimes are the only thing `run_service._grids()` keys its cache on, so a re-run of
`scripts/make_wetgrid.py` silently changes the baseline's numbers.

**Files.**
- New: `app/services/baseline.py`
- Changed: `app/services/run_service.py` (`_grids()` gains a raster-set digest to the cache key),
  `app/services/scene_service.py`

**Tests.** `tests/test_baseline.py`:
`test_a_run_against_a_frozen_snapshot_reproduces_identically` ·
`test_the_baseline_at_a_date_excludes_a_project_declared_later` ·
`test_raster_drift_changes_the_snapshot_and_is_reported`

**Done when.** A run against "the baseline as at 12 March 2027" returns the same numbers (TODO B4).

---

### F3 — Roles and identity (Wave 2)

**Goal.** A declaration cannot be created by a party that is not entitled to create it.

**Design.** The minimum viable identity, sized for a pilot rather than for a bank: an `organisation` and
a `membership`, plus a session token. **No user passwords in the pilot** — a pilot with two real
organisations can use per-organisation API keys plus a named-person assertion on each submission, which
is the level-1 signing of §3.2 and is defensible in a Code of Practice.

Authorisation is a single function, `may_declare(org, project, action)`, in one module
(`app/services/authorisation.py`), consulted by every mutating route. It must not be re-derived per
route — the existing codebase already documents this failure mode (the duplicated `MassingOp` semantics
between frontend and backend, pinned by a cross-language test).

**Files.**
- New: `app/models/tenant.py`, `app/schemas/tenant.py`, `app/services/authorisation.py`,
  `app/routers/sessions.py`
- Changed: `app/config.py` (auth settings), `app/main.py` (dependency wiring)

**Tests.** `tests/test_roles.py`: one test per role × one forbidden action, plus
`test_every_mutating_route_checks_authorisation` — a test that asserts **no** mutating route is
unregistered, so a new endpoint cannot ship without an authorisation check. That test is the one that
matters; the others are examples of it.

**Done when.** A declaration cannot be created by a party that is not entitled to create it (TODO B2).

---

### F4 — Tenancy (Wave 2)

**Goal.** Two organisations, one instance, no bleed.

**Design.** §3.4. `db.py` becomes tenant-scoped; the file store lays out per tenant. The PostGIS path
becomes a storage swap behind the same function names (ADR-020).

**Files.** New: `app/services/tenant_service.py`. Changed: `app/db.py`, `app/services/scene_service.py`.

**Tests.** `tests/test_tenancy.py`:
`test_an_organisation_cannot_read_another_organisations_scene_by_id` ·
`test_an_organisation_cannot_read_another_organisations_scene_by_listing` ·
`test_an_organisation_cannot_write_into_another_organisations_namespace`

**Done when.** Two organisations use one instance with no data bleed, and the API contract is unchanged
(TODO B1).

---

### F5 — Attribution (Wave 3)

**Goal.** A reconciling inherited-vs-caused split, per project, per axis.

**Design.** §3.1. The implementation is a new service, `app/services/attribution.py`, that composes the
existing ledger rather than reimplementing it:

- `L(∅)`, `L(S)`, and `L(S \ {P})` for each P — n+2 ledger evaluations. The ledger is numpy over a
  117 × 148 grid; the whole suite runs in 154 s, so this is comfortably interactive.
- Per-axis: volume axes (`unstoredM3`, `runoffM3`, `storageCapacityM3`, area axes) decompose exactly.
  Shade and ventilation decompose on their own geometry (each footprint's own frontal area and shadow),
  with the same overlap residual. Flood extent does **not** decompose — report it at district level only
  (§3.1).
- **The wind axis attributes on the arrangement, not on FAD** (§3.6). FAD is 180°-periodic by
  construction and cannot distinguish NE from SW for any footprint set, so a per-project FAD delta is
  reported as a *magnitude* change only. The direction-sensitive quantities that carry the register's
  wind value are `directional_exposure`'s `meanFirstHitHeightM` and the corridor path's entry edge and
  mean cost — and those *do* attribute cleanly under leave-one-out, because they are already
  arrangement-sensitive (measured: NE 15.33 m vs SW 8.88 m first-obstruction height).
- Cell-ownership bookkeeping runs alongside, to localise the interaction to specific cells.

**Files.**
- New: `app/services/attribution.py`, `app/schemas/attribution.py`, `app/routers/attribution.py`
- Changed: `app/services/sandbox_model.py` (expose the per-cell arrays the service needs — currently
  `_runoff_and_unstored` returns per-cell arrays but `storage_ledger` returns only sums; attribution
  needs a per-cell ledger, so add `cell_ledger()` rather than re-deriving it)
- Changed: `app/agent/grounding.py` (attribution numbers must be groundable, or the chat cannot quote them)

**Tests.** `tests/test_attribution.py`:
`test_attribution_reconciles_to_the_total` (the TODO A2 acceptance) ·
`test_disjoint_projects_decompose_exactly` (residual == 0) ·
`test_overlapping_projects_report_a_non_zero_interaction` ·
`test_the_interaction_term_is_not_distributed_silently` ·
`test_attribution_is_deterministic` (same inputs → same output, byte for byte)

**Done when.** A short spec exists, an `attribution` object is in the schema, an endpoint returns a split
that reconciles to the total, and there is a test for the reconciliation (TODO A2).

---

### F6 — Joint lock-then-declare (Wave 4)

**Goal.** A project cannot declare without seeing what its neighbours declared.

**Design.** Before a declaration can be submitted, the submitting org must have acknowledged the current
declarations of every project whose footprint intersects its own (within a margin). The acknowledgement
is a row: `acknowledged_declaration_id` per intersecting neighbour. The check is a **precondition on
submission**, not a warning.

This is the feature that makes the register a register rather than a shared document. It is also the
hardest to demo and the easiest to describe — "you cannot file until you have seen the file next door".

**Files.** New: `app/services/neighbours.py` (footprint intersection — reuse `ai_plan._point_in_ring` /
  `sandbox_model._polygon_cells`; do not write a third polygon routine). Changed:
  `app/routers/declarations.py`, `app/services/declaration_service.py`.

**Tests.** `tests/test_lock_then_declare.py`:
`test_submission_is_refused_while_a_neighbour_declaration_is_unacknowledged` ·
`test_acknowledgement_is_recorded_against_the_exact_declaration_version` ·
`test_a_new_neighbour_declaration_invalidates_a_stale_acknowledgement`

**Done when.** The joint lock-then-declare flow works across parties (TODO B10 row 10).

---

### F7 — Agency review surface (Wave 4)

**Goal.** Comments anchored to a project, and an exportable written-direction record.

**Design.** `review_note` rows with `kind` ∈ `comment` / `direction`. Comments anchor to a
`(project_id, declaration_id)` pair, so a comment on version 2 does not silently become a comment on
version 3. The written-direction record exports as a document with the declaration digest embedded, so
the direction and the declaration it refers to cannot drift apart.

**Files.** New: `app/services/review.py`, `app/routers/review.py`. Changed: `app/schemas/declaration.py`.

**Tests.** `tests/test_review.py`:
`test_a_note_anchors_to_the_declaration_version_it_was_written_against` ·
`test_the_direction_export_embeds_the_declaration_digest`

**Done when.** Comments anchored to a project, and an exportable written-direction record (TODO B7).

---

### F8 — Amendment lifecycle (Wave 4)

**Goal.** A register that cannot amend is a one-shot report.

**Design.** Supplied by F1's supersede chain plus the lifecycle states of §3.2. The states to get right:
`returned for amendment` (the coordinator sends it back, the developer files a new version, the old one
stays visible and marked superseded), and `withdrawn`.

**Tests.** `tests/test_amendment.py`:
`test_a_returned_declaration_can_be_resubmitted_as_a_new_version` ·
`test_the_superseded_declaration_remains_readable` ·
`test_withdrawal_requires_an_entitled_party`

---

### F9 — Tiered disclosure (Wave 5)

**Goal.** Aggregate visible to every participant; detailed massing and phasing visible only to the
agency and the declaring party. A developer can see exactly who sees what, before they submit.

**Design.** A `disclosure_policy` per (org, scene). Filtering happens **server-side, at the response
builder**, not in the frontend — a payload that contains restricted detail and hides it in the UI is a
data breach with a nicer interface.

**Files.** New: `app/services/disclosure.py`, `app/routers/disclosure.py`. Changed: every response
builder that can carry restricted fields.

**Tests.** `tests/test_disclosure.py`:
`test_a_non_declaring_organisation_cannot_see_another_organisations_detailed_massing` ·
`test_the_aggregate_view_is_identical_for_every_participant` ·
`test_the_disclosure_endpoint_lists_exactly_who_sees_what` ·
`test_restricted_fields_are_absent_from_the_payload_not_merely_hidden`

That last one — absence, not hiding — is the test that matters.

---

### F10 — Public read-only aggregate view (Wave 5)

**Goal.** Transparency is what makes the arrangement politically defensible.

**Design.** `GET /api/register/{district}` — no auth, aggregate only: the projects registered, their
declared status, and the district-level aggregate effect. No geometry beyond the district boundary, no
per-project detail, no intermediate values.

**Tests.** `tests/test_public_register.py`:
`test_the_public_view_contains_no_restricted_detail` ·
`test_the_public_view_carries_the_screening_label`

---

### F11 — Phasing and temporal overlap (Wave 6)

**Goal.** "My neighbour's phase 2 arrives in 2029, before my phase 1 completes" is expressible.

**Design.** `phase` rows with `start`/`end`. A run takes an `as_at` date; the baseline at that date
includes only phases active at it. The conflict detector compares phase windows across intersecting
projects and reports overlaps where construction is concurrent.

**Design note.** This is a **filter on the baseline composition**, so it depends on F2 and is cheap once
F2 exists. It should not be built before F2.

**Tests.** `tests/test_phasing.py`:
`test_a_phase_that_has_not_started_is_not_in_the_baseline_at_that_date` ·
`test_concurrent_construction_on_adjacent_projects_is_reported` ·
`test_the_run_explains_which_phase_it_used`

---

### F12 — Regulatory output templates (Wave 6)

**Goal.** A consultant can paste the output into a submission and a reviewer can follow it.

**Design.** Three templates, each generated from the run's own outputs — never re-derived:
1. **AVA-style SVR/LVR table** — per direction, from `ventilation.fadRatio` (NE/ENE/E), plus the
   direction-sensitive arrangement fields the corridor endpoint already publishes: `entryEdge` and
   `meanFirstHitHeightM` per direction. **Per §3.6, the FAD column is labelled as a magnitude that
   cannot distinguish NE from SW, and the arrangement columns are what make the NE reading distinct.**
   No template asserts a pass/fail — the cited guidance states no threshold exists.
2. **SBDG separation / setback / greenery check** — from the design metrics, with the screening label.
3. **Attribution annex** — the §3.1 decomposition, in the shape EIAO TM §4.3.1(c)(iii) asks for:
   differentiating the impact caused by this project from that caused by others.

Every template carries the screening label and the assumption register. **This is not decoration — it is
the liability architecture** (TODO E2). If a commercial conversation asks to remove it, that is a no.

**Tests.** `tests/test_templates.py`: each template's numbers are checked against the run's outputs, the
way `test_every_card_number_matches_the_ledger` already does for the parameter card. **Reuse that
pattern** — it is the established mechanism for "a card cannot disagree with a run". One test must
assert the AVA table's **NE row differs from its SW row in the arrangement columns** — otherwise the
template has silently reproduced the FAD symmetry and the whole point of §3.6 is lost.

---

### F13 — Guard re-specification (Wave 0)

**Goal.** §3.3. The coverage cap stops dropping real projects and becomes a consent threshold.

**Files.** Changed: `app/services/sandbox_model.py` (`apply_interventions`),
  `app/services/proposal_constraints.py` (the caps are imported, never re-typed — see
  `proposal_constraints.py:23-24`), `app/config.py` (make the threshold configurable, and
  scenario-dependent: the sandbox keeps 25/40, the register does not).

**Tests.** `tests/test_register.py`:
`test_a_declared_project_covering_30_percent_is_not_dropped` ·
`test_an_unconfirmed_draft_covering_30_percent_is_refused` ·
`test_exceeding_the_register_threshold_triggers_joint_review`

**Done when.** The first real declaration (TODO A1) can land without the engine silently omitting it.

---

### F14 — Grounded chat over the register (Wave 3)

**Goal.** "What did project X inherit, and what did it cause?" answered in plain language, with every
number checked.

**Design.** The existing `chat_service` machinery already checks every number in an answer card against
the run's outputs and re-prompts once on a mismatch. Attribution extends the "run" fact-shape with an
`attribution` block. Nothing new is needed in the grounding machinery — only new facts and new prompt
contract entries.

**Files.** Changed: `app/agent/chat_service.py`, `app/agent/prompts/result_analytics.py`,
  `app/agent/prompts/chat.py`, `contracts/intent_vocabulary.json` (new intents: "what did X inherit",
  "what did X cause", "which projects interact with X").

**Tests.** `tests/test_agent.py` additions: a card quoting an attribution figure that is not in the run
must be caught by grounding.

---

## 7. Sequencing

Six waves plus one branch. Each wave has an exit gate that is a *test*, not a judgement call.

```
  W0  Unblock ──▶ W1  Record core ──▶ W2  Identity ──▶ W3  Attribution ──▶ W4  Coordination ──▶ W5  Disclosure
  §1.2–1.6          F1  declarations      F3  roles          F5  attribution      F6  lock-then-declare   F9  tiered disclosure
  F13 guard         F2  baseline          F4  tenancy       F14 chat             F7  agency review      F10 public aggregate
  D5 design storm                                                                 F8  amendment
        │                                                                              │
        └───────────────────────────────▶ W6  Phasing + templates ◀─────────────────────┘
                                         F11 phasing
                                         F12 regulatory templates
```

**The branch.** W6 (phasing, regulatory templates) depends on **W1** (F2's versioned baseline) and on
**W3** (F5's attribution, because the EIAO §4.3.1(c)(iii) annex is the attribution decomposition in
submission form). It can therefore run in parallel with W4 and W5 once W3 lands — but not before.

**What is strictly serial.** W0 → W1 → W2 → W3 → W4 → W5. Each step's output is the next step's
input, and the register's integrity argument runs through all of them: an attribution figure (W3) is
only defensible if the declarations it runs against (W1) were attributable to a party (W2), and only
useful if the coordination loop that produced them (W4) and the disclosure rules that govern them
(W5) are in place.

### Wave 0 — Unblock (this week; no dependencies, ~3 days)

| Item | Action |
|---|---|
| W0.1 | Commit `contracts/openapi.json` as regenerated under pydantic 2.13.5 (§1.5). **Do not revert.** |
| W0.2 | Record the measured test status in STATUS §2 and §7.2 (TODO A8), including the CI-vs-pytest distinction and the `.venv` trap (§1.2). |
| W0.3 | Rebuild or delete `backend/.venv`, or add a loud note. It is off-pin and has no pytest. |
| W0.4 | **Settle the design storm (D5, §3.5).** Then regenerate the committed artefacts with `scripts/make_wetgrid.py --rainfall 50`, commit them, and add `test_the_committed_artefacts_and_the_ledger_agree` so the drift can never return. Recalibrate the reservoir siting rule against the chosen storm. |
| W0.5 | Write the attribution spec (§3.1) as a short document; circulate for the Engineering sign-off of B5. **The spec is a deliverable independent of the code** and is what the Code of Practice will reference. |
| W0.6 | Implement F13 (the guard re-specification). Unblocks TODO A1. |
| W0.7 | Restore `docs/ADR.md` with the ten cited ADRs, or remove the citations (§1.6). |
| W0.8 | **Fix the two stale claims in the wind code** (§3.6): the "2,639 envelopes" figure in `ventilation.py:12` against the artefact's actual 396, and the FAD limitation note that blames the axis-aligned footprints rather than the metric's 180°-periodicity. A screening tool's docstrings get quoted into submissions; they have to be right. |
| W0.9 | **Pull the CSDI "Site Wind Availability Data"** (§12.1) into `backend/data/reference/hsk_site_wind.json`, in the same `source` / `status` shape as `hsk_ava_reference.json`, and extend the wind reference loader to read it. Use the **versioned** CSDI link, not the always-latest one, and record the CSDI attribution string. This replaces AVRG73's single wind-rose fact with the government's published site wind regime. |
| W0.10 | **Extract the EIAO-TM and GN6/2010 clause texts** (§12.4) into `backend/data/reference/`, and add `oasdiff breaking` to the CI contract job. Both are cheap, and both are the difference between *citing* the statutory hooks and *asserting* them. The breaking check is in the contract job (23 Nov 2026, oasdiff v1.39.0). The remaining instrument text is still G7. |

**Gate:** the openapi drift is committed; the test status is recorded with the CI-parity caveat; the
design storm is settled and the committed artefacts agree with the ledger; the attribution spec is
written; F13's two acceptance tests pass; the site wind reference and the statutory clause extracts are
in the reference store.

### Wave 1 — The record core (~3 weeks)

F1 + F2. The whole product is downstream of this and nothing else in the plan is worth doing first.
Two people, roughly one backend each, because F1 and F2 touch adjacent surfaces.

**Gate:** `test_a_declaration_cannot_be_edited_after_creation`, `test_the_hash_chain_verifies`,
`test_a_run_against_a_frozen_snapshot_reproduces_identically` all pass; the contract is regenerated.

### Wave 2 — Identity and tenancy (~2 weeks)

F3 + F4. These travel together because authorisation needs a tenant to authorise within.

**Gate:** `test_an_organisation_cannot_read_another_organisations_scene_by_id` and the
`test_every_mutating_route_checks_authorisation` sweep both pass.

### Wave 3 — Attribution (~2 weeks)

F5 + F14. The centrepiece. Do not start before the Wave 0.4 spec is signed.

**Gate:** `test_attribution_reconciles_to_the_total` passes to 1e-9; the disjoint case has a 0.00
residual; the overlapping case reports a non-zero interaction that is **not** distributed.

### Wave 4 — The coordination loop (~3 weeks)

F6 + F7 + F8. This is what a coordinator actually uses. It is also the wave most likely to change shape
once a real project office sees it — budget slack here, not in Wave 1.

**Gate:** `test_submission_is_refused_while_a_neighbour_declaration_is_unacknowledged` passes.

### Wave 5 — Disclosure and the public view (~2 weeks)

F9 + F10. Sequenced after Wave 4 because the disclosure rules depend on what the coordination loop
actually produces.

**Gate:** `test_restricted_fields_are_absent_from_the_payload_not_merely_hidden` passes.

### Wave 6 — Phasing and regulatory templates (~2 weeks, parallel to W4–W5)

F11 + F12. Depends on F2 (W1) and F5 (W3).

**Gate:** `test_the_run_explains_which_phase_it_used` passes; the templates' numbers match the run's.

### Total: ~16 weeks of calendar time for a two-person team, ≈6 engineer-months

Sequenced against the commercial calendar this lands **Q2–Q3 2027**, matching TODO §C. Note the
dependency that cuts both ways: **C1 (PSTS-SPC) requires an authorised letter from the participating
public-sector body (B1)**, so Wave 4 — the first wave that produces something a public body would
actually adopt — is gated on a decision that is not Edwin's alone to make. If B1 is unresolved by
end of Wave 2, the engineering should proceed on the most conservative reading of the business model
(the keeper holds the register; the developer declares; everything is disclosed to the coordinator) and
the commercial track should be escalated, not quietly assumed.

---

## 8. Verification strategy

The existing patterns are good and must be preserved. Four additions:

1. **The contract is the API's specification and CI enforces it.** Every new route changes
   `contracts/openapi.json`. Regenerate with the *pinned* pydantic:
   `cd backend && ./.venv313/bin/python -m app.export_openapi`.

2. **Per-file CI discipline.** The CI loop runs `python file` for files with a `__main__` guard and
   `pytest file` for the rest. A new suite must follow one of the two shapes and must actually be
   collected by its runner — a file with neither a guard nor `def test_*` fails CI with exit 5, and one
   suite already shipped that way.

3. **The reconciliation test is the new centrepiece.** `test_attribution_reconciles_to_the_total` is the
   single test that proves the product's central claim. It must assert an exact tolerance (1e-9 m³),
   not a rounded comparison.

4. **"A card cannot disagree with a run" extends to the register.** Every template, every chat card and
   every attribution figure must be traceable to the run's own outputs. Reuse the mechanism
   `test_every_card_number_matches_the_ledger` already establishes for the parameter card. A register
   whose figures disagree with its own engine is worse than no register, because it is *relied on*.

**Standing checks (TODO E1, E2, E4) apply to every wave:** full suite green before any pilot demo;
every output keeps the screening label and the assumption register; STATUS §3 updated whenever a
capability moves from "not built" to "built", with the evidence.

---

## 9. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **The committed raster and the engine disagree about the design storm.** (§1.3) | **Certain — it is happening now** | **High — CI is red and the map contradicts the ledger** | W0.4: settle D5, regenerate at the chosen storm, commit, and add `test_the_committed_artefacts_and_the_ledger_agree`. One command plus one test. |
| R2 | **No public body designates the register (STATUS B1).** | Medium–High | Fatal to the revenue model | Engineering proceeds on the conservative reading. Prioritise the artefact that survives without designation: a *dated, signed, auditable statement* is useful to a developer on its own. Escalate B1, don't assume it. |
| R3 | **The interaction term is large and unexplained.** (26% measured) | Certain | High — looks broken if not framed | Publish it as a finding, not a defect. The Code of Practice states that interaction is expected and material. Frame it as the register earning its keep: a tool that hides it is hiding the finding. |
| R4 | **The coverage guard drops real projects** (§3.3) | High if unfixed | High — silently wrong records | F13 in Wave 0. Acceptance test asserts a 30%-coverage declared project is not dropped. |
| R5 | **The declaration lifecycle gate does not exist** (§3.2) | Certain | High — the record's integrity claim is void | Build it in Wave 1; assert a non-accepted declaration is not computed on. |
| R6 | **Retrofitting tenancy later is a backfill.** | Medium | Medium | Add `org_id` and tenant-scoped paths from the first commit (D4). |
| R7 | **The store-mode swap breaks the API contract.** | Low–Medium | Medium | ADR-020 says the contract must not move; `tests/test_openapi_contract.py` enforces it. The contract test is the tripwire — keep it green throughout. |
| R8 | **Screening-grade numbers reach a submission.** | Medium | High — credibility | TODO E2 is a no: the label is the liability architecture. Wave 6 templates carry it. |
| R9 | **LLM rate limits in a paid session.** (TODO B12) | Medium | Medium | Wave 3's chat path must degrade to the existing labelled template card. The template fallback already exists and is already labelled. |
| R10 | **The 43.5 ha window is too small for a district licence.** (STATUS §5) | Certain | High | TODO C3's calibration playbook. Out of scope for this plan; note that F2's snapshot/raster machinery is the piece a second district needs. |
| R11 | **Wave 4 depends on a decision that is not the team's to make.** (B1/B4) | Medium | Schedule | Two weeks of slack in Wave 4; the commercial track escalates in parallel. |
| R12 | **The undocumented ADR trail makes the design unreviewable.** (§1.6) | Certain | Low–Medium | W0.7. Restoring `docs/ADR.md` is half a day and unblocks a reviewer. |
| R13 | **A second party reads the register and finds it wants everything.** | Low | Medium | F9's disclosure endpoint makes the visibility matrix explicit *before* submission, per TODO B9. |
| R14 | **The published headline changes when the design storm changes.** | Certain | Medium | This is *why* D5 must be settled before F2: the design storm becomes a pinned, versioned input of the baseline snapshot, and every historical figure keeps the storm it was computed under. F2's `raster_set` carries it. |

---

## 10. Open decisions needing an owner

STATUS §4.2 lists B1–B5. This plan adds four and restates two with the new information.

| # | Decision | Owner | Needed by | Default if unanswered |
|---|---|---|---|---|
| **B1** | Which public body, and does it intend to designate? | Edwin | End of Wave 2 | Proceed on the conservative model; escalate commercially |
| **B2** | Tariff route: contracted schedule / pass-through / voluntary standard | Edwin | Wave 5 | Proceed; the fee architecture does not block engineering |
| **B3** | Incorporate now, or run pilots as individuals? | Edwin | Wave 2 | Run the pilot as individuals; incorporation is a legal step, not an engineering dependency |
| **B4** | Governance: who signs off the Code of Practice and the fee schedule | Team | Wave 4 | Draft as a *vendor proposal*, clearly marked, for adoption rather than as a rulebook |
| **B5** | Attribution definition — what counts as "caused" vs "inherited" | Engineering | **Wave 0** | Use §3.1's three-term decomposition; it reconciles by construction and is the only candidate that does |
| **D5** (new) | **What is the baseline design storm — 50 mm/1 h or 450 mm/24 h?** | Engineering + consultant | **Wave 0, immediately** | 50 mm, with every artefact regenerated from it (§3.5). The code has already unified on it; only the data and the siting rules lag |
| **D1** (new) | Which signing level does the pilot claim? | Team + coordinator | Wave 1 | Level 1 (attributed assertion), explicitly stated in the Code of Practice. Never over-claim |
| **D2** (new) | Does the register publish per-project flood extent, or district only? | Engineering + coordinator | Wave 3 | District only; per-project margins as a range (§3.1) |
| **D3** (new) | What is the disclosure default for a developer's detailed massing to other participants? | Coordinator | Wave 5 | Detail restricted to the declaring org + coordinator + agency; aggregate open to all participants |
| **D6** (new) | **Is wind channel simulation in scope?** | Edwin | **Wave 0** | **No.** Attribute the wind axis and build its template instead (§3.6). The NE≡SW symmetry is a theorem of the metric, not a fidelity gap, and `directional_exposure` already breaks it where it matters. A solver would buy a weaker claim than the one already available, at the wrong resolution, and would weaken the liability position |

**The Code of Practice (TODO A4) is the document that binds all of these together.** It should be written
*after* the Wave 0.5 attribution spec and *alongside* the Wave 1 implementation, not before — because a
rulebook written before the code exists describes a product that was never built. Two of its inputs
(attribution definition, design storm) are now specified in §3.1 and §3.5 and can be lifted directly.

---

## 11. Deliberately not in this plan

- **Pricing, tariff levels, competitor positioning, market sizing.** Held in the internal planning notes;
  this repository is public (TODO E3).
- **The second study area's calibration.** TODO C3. F2's snapshot and raster-set machinery is the piece
  it needs; the calibration playbook is a separate document.
- **A statutory (PKI-backed or eLegislation-backed) signature.** §3.2 level 3. Out of scope for the pilot.
- **Replacing the sandbox.** The sandbox stays. The register is a layer over it; the engine, the overlays
  and the parameter card are unchanged.
- **Multi-instance deployment, backups, disaster recovery.** Real, and needed before a second participant —
  but not a register *feature*, and it belongs with the PostGIS work (TODO B1) rather than in this plan.

## 12. Resources — open source, skills, references, people

### 12.0 The rule that governs this section

Two constraints from the project itself bound every recommendation below:

1. `backend/requirements.txt` states: *"Deliberately NOT installed today: sqlalchemy, geoalchemy2, psycopg,
   alembic. They are only needed once the PostGIS + MinIO target store lands, which cannot be
   provisioned on this machine."*
2. The team's working rule is **data-conservation mode**: no new dependency is installed without
   explicit permission and a confirmed network.

So every recommendation is classified, and **nothing here is an instruction to install anything today**:

| Class | Meaning |
|---|---|
| **[ADOPT]** | Add to `requirements.txt` when the wave lands. Pure-Python or already effectively present; no compiled-wheel risk. |
| **[ADOPT-PILOT]** | Adopt, but **only** when the PostGIS work lands (TODO B1) — it needs the store first. |
| **[REFERENCE-ONLY]** | Do **not** become a dependency. Use it as a cross-check, a citation, or a read-only source. |
| **[DEFER]** | A different, later project. Listed so the decision is recorded, not forgotten. |

---

### 12.1 The biggest find: the Hong Kong Government already publishes the wind simulation

**This changes the D6 answer (§3.6), and improves it.**

**CSDI — the Common Spatial Data Infrastructure portal** (`portal.csdi.gov.hk`) publishes **over 1,100
spatial datasets from 70+ departments**, free, with a Map API and a catalogue service. Among them:

> **Site Wind Availability Data (地盤總體風環境數據)** — Planning Department, Environment category,
> API available, published 2019-08-31, updated as and when there is update.
> *"The annual, summer and winter wind speeds, frequencies and wind direction data at different height
> levels for **Air Ventilation Assessment Computation Fluid Dynamics and Wind Tunnel Modelling**."*
>
> datasetId `pland_rcd_1634281652589_43389` ·
> `https://portal.csdi.gov.hk/geoportal/?datasetId=pland_rcd_1634281652589_43389&lang=en` ·
> catalogue page `data.gov.hk/en-data/dataset/hk-pland-pland1-site-wind-availability-data`

**Why this is decisive.** The Planning Department has already run the CFD and wind-tunnel modelling that
§3.6 declined to build — **per site**, at multiple heights, with annual/summer/winter frequencies, and it
is **published, free, and citable**. So the register does not need to simulate wind to have an
authoritative wind reference; it needs to **cite** one.

| What it replaces | With what |
|---|---|
| AVRG73's single fact — NE/ENE/E, 40.8% combined — as "the one published wind-rose fact we use" (the project's own words in `hsk_ava_reference.json`) | The government's published **site wind regime**: speeds, frequencies and directions by height and season |
| A screening metric with no external anchor | The screening read **against** a CFD/wind-tunnel baseline from the authority that will review the submission |
| A defensibility argument built on our own arithmetic | A defensibility argument built on **the government's own simulation** — which is the strongest possible provenance for a register a project office adopts |

**Actions.**
1. Fetch the dataset and store it as a reference artefact beside the existing ones —
   `backend/data/reference/hsk_site_wind.json` — following the exact shape `hsk_ava_reference.json`
   already uses (`artefact`, `generated`, `status: "PUBLISHED_REFERENCE_DATA_NOT_A_MODEL_RESULT"`, and a
   `source` block with `name`, `publisher`, `url`, `retrieved`, `documentDate`). The project already has
   this convention; extending it is cheaper than inventing one.
2. Extend `services/ventilation.py`'s reference loader to read the new artefact, and replace the
   "the published prevailing wind here is from the north-east" limitation with the published frequency
   table for all directions — which also retires the "no frequency is invented for any other direction"
   workaround.
3. Add the CSDI attribution string to the reference file and to every output that publishes wind
   figures. CSDI's terms require attribution: **"Map data from CSDI Portal"**, linked to the CSDI terms
   and conditions.
4. Confirm the exact API call against the dataset's own metadata record before automating it. CSDI's
   "Downloads" link always serves the latest version; the "Metadata document" link serves the specific
   version at the time the metadata was generated. **A register needs the versioned link**, so use the
   metadata-document link and record the version.

**Also worth watching:** the Spatial Data Office is developing an **MCP server** so AI platforms can query
CSDI directly, and has already shipped **GeoVisualiser** (Apr 2026) and the **"智多紛" AI assistant**
(Sep 2026) on the portal. The MCP server is a natural future integration for this product — and a
reason to keep the CSDI dataset ids in a single, swappable module rather than hard-coded.

---

### 12.2 Open source, by wave

**Wave 0 — verification, contract, and the two stale claims**

| Need | Project | Licence | Class | Note |
|---|---|---|---|---|
| Breaking-change gate on the API contract | **oasdiff** | Apache-2.0 (CLI + GitHub Action free) | **[ADOPT]** | Standalone Go binary (brew / curl / docker / release). `oasdiff breaking base.yaml revision.yaml` exits 1 on a breaking change — a one-line CI step. 755 classified change rules, so the verdict is derived, not judged. **Directly serves ADR-020**: the contract must not move when the store does, and oasdiff is what proves it did not. |
| Property-based tests generated from the spec | **Schemathesis** | MIT | **[ADOPT]** | pytest plugin; generates cases from the OpenAPI document. Catches the failure the contract test cannot: the *running* API drifting from the *declared* contract. |
| Spec lint | **Spectral** | MIT | **[ADOPT-PILOT]** | Node CLI. Keeps new endpoints consistent so the committed spec stays the single truth. |
| Property-based unit tests | **hypothesis** | MPL-2.0 | **[ADOPT]** | For the attribution reconciliation and the hash chain — the two places where "it worked on my example" is not enough. |

**Wave 1 — the record core**

| Need | Project | Class | Note |
|---|---|---|---|
| Canonical JSON + hash chain | **`hashlib` (stdlib)** | **[ADOPT]** | The chain in §4.2 needs nothing else. `pins.fingerprint` already does SHA-1 over canonical JSON — **one canonicalisation rule in the project, not two**. |
| Immutable rows | **Postgres trigger** — `BEFORE UPDATE` that raises | **[ADOPT-PILOT]** | The database refuses to mutate a declaration. Cheaper and stronger than trusting the service layer, and it holds even if a future code path forgets. |
| PostGIS schema | **SQLAlchemy 2.0** + **GeoAlchemy2** + **psycopg** + **Alembic** | **[ADOPT-PILOT]** | Already named in `requirements.txt` as the deferred set. Alembic is the migration story — no hand-written DDL. |
| Server-side tenant isolation | **Postgres Row-Level Security** | **[ADOPT-PILOT]** | See §12.3 — this is the recommended tenancy mechanism, and it is the one place the store swap earns its keep. |

**Wave 2 — identity and tenancy**

| Need | Project | Class | Note |
|---|---|---|---|
| JWT | **PyJWT[crypto]** | **[ADOPT]** | **Not `python-jose`** — it has received few updates in years and is the package most FastAPI tutorials still reach for. Pin the algorithm (`algorithms=["RS256"]`), require `exp`. |
| Password hashing | **argon2-cffi** | **[ADOPT-PILOT]** | Current recommendation over bcrypt (GPU resistance). `passlib` is in maintenance mode — prefer the library directly. |
| OIDC provider | **Keycloak** (or Authentik / Zitadel) | **[REFERENCE-ONLY]** | If the pilot's participants already have corporate identities, OIDC beats passwords. But running an IdP is an operations commitment a two-person team should not take on before the pilot. **Start with per-organisation tokens.** |
| Auth scaffolding | **fastapi-users** | **[REFERENCE-ONLY]** | Built for full user-registration/email flows. Four roles and two organisations do not need it. |
| Authorization | **an in-process policy function** | **[ADOPT]** | `may_declare(org, project, action)` in one module. See §12.3 for why this beats an external engine. |

**Wave 3 — attribution**

| Need | Project | Class | Note |
|---|---|---|---|
| The attribution maths | **own code** | **[ADOPT]** | Leave-one-out + cell ownership (§3.1). Non-negotiable: this is the product's central claim and it must be inspectable, not delegated. |
| Footprint geometry | **Shapely** | **[ADOPT-PILOT]** | Real polygon area, intersection and centroid — needed for cell ownership, footprint intersection (F6's neighbour detection), and orientation. **Note the project rule**: measurement maths belongs in a projected CRS and is confined to `scripts/`; Shapely needs the projection step done first (`pyproj`). |
| Cell-level raster access | **rasterio** | **already present ✓** | No change. |
| Sparse graph / corridors | **scipy.sparse.csgraph** | **already present ✓** | No change — the corridor machinery is already Dijkstra-based. |
| **Independent cross-check of the hydrology** | **WhiteboxTools** (`whitebox` on PyPI) | **[REFERENCE-ONLY]** | Its `fill_depressions`, `breach_depressions`, `d8_pointer` and `d8_flow_accumulation` are an **independent implementation of the Priority-Flood + D8 work this project wrote itself**. Running it once over the HSK grid as a benchmark would tell you whether the home-grown cascade is right — which is exactly what a sceptical QP will ask. **Do not put it in the runtime path**: it is a reference model, and the liability position (§3.6) depends on the engine being *arithmetic* and inspectable. |
| Benchmarking the whole model | **HydroMT** (+ `wflow`, `LFPtools` for LISFLOOD-FP) | **[REFERENCE-ONLY]** | Deltares' data-agnostic model-building framework; HydroMT has been used to build SFINCS and Wflow instances from global datasets. Relevant to TODO C3's **district calibration playbook** — it is the tool for showing a second district how to stand the model up reproducibly. Also note `LFPtools` (LISFLOOD-FP scripting) as the reference 2D hydrodynamic model the project is *not* claiming to be. |

**Wave 5 — disclosure and the public view**

| Need | Project | Class | Note |
|---|---|---|---|
| Public read-only aggregate view | **WorkBuddy `sites` skill** (publish as a link) | **[ADOPT]** | F10 without writing a deployment pipeline. |
| Policy-as-code | **OPA / Cerbos / Cedar** | **[DEFER]** | A policy engine earns its keep at many organisations and rules. This one has four roles, one district and a disclosure matrix that fits in one table. Revisit if the register goes multi-district. |
| Tamper-evident log | `hashchain` / `certificates` | **[REFERENCE-ONLY]** | The SHA-256 chain in §4.2 is already sufficient for a pilot, and it is 30 lines of stdlib the team fully controls. |

**Wind, if it ever is revisited (D6)**

| Need | Project | Class | Note |
|---|---|---|---|
| HK site wind data | **CSDI "Site Wind Availability Data"** | **[ADOPT]** | See §12.1. This is the answer, and it is already published. |
| Urban-scale CFD | **OpenFOAM**, **SU2** | **[DEFER]** | A different project: building-scale, per-site, with its own calibration and liability. Not this one. |
| Urban canopy modelling | **UrbanSim**, **CityFlow** | **[DEFER]** | Same reasoning. |

---

### 12.3 The tenancy mechanism: Row-Level Security, not an FGA engine

The market has a lot of fine-grained authorisation engines — OpenFGA, SpiceDB, Permify, Cerbos, Cedar,
OPA, Casbin — and the 2026 comparisons are careful about which fits which. **This project fits none of
them, yet.** The rule of thumb from the literature is the right one here: *"Before adopting an FGA, if your
requirement is just simple multi-tenancy, RLS alone is sufficient."*

**Recommendation: Postgres Row-Level Security**, expressed as a policy on every tenant-scoped table:

```sql
ALTER TABLE declarations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON declarations
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

with the application setting `app.current_tenant` per request, inside a transaction.

**Why this beats an external engine here:**
- **No new service to run.** The project cannot currently provision Docker or PostGIS *on this machine*;
  adding a second stateful service multiplies that problem.
- **The isolation is enforced below the application.** A bug in a service-layer filter cannot leak
  another tenant's rows, because the database refuses to return them. For a product whose product claim
  is *"the keeper is liable only for the record's integrity"*, isolation enforced in the store is a
  stronger position than one enforced in the code above it.
- **It is testable today without PostGIS**, if the file store mirrors it: `tests/test_tenancy.py` asserts
  org A cannot read org B's scene by id, by path, and by list (§6, F4). The file store's
  per-tenant directory layout is the same boundary, enforced the only way it can be without a database.
- **It composes with the roles model** in a single `SET` per request: `app.current_tenant` and
  `app.current_org` and `app.current_role`.

**When an FGA engine would become right:** when the register has many organisations, roles that differ
per organisation, and questions of the shape *"list everything this party may read"* — which is exactly
what F10's public aggregate view and F9's disclosure endpoint eventually need. That is a Wave 5+
decision, not a Wave 2 one.

---

### 12.4 Statutory hooks — verified against the current EIAO Technical Memorandum

The EIAO Technical Memorandum was **revised in 2023 (effective 30 June 2023)**, and the project's README
cites it as "§4.3.4(c)" and "§4.3.1(c)(iii)". **The §4.3.4(c) citation is accurate** — the revised text
reads:

> "4.3.4 … The assessment methodologies shall allow for the assessment and evaluation of the cumulative
> environmental effects if the following circumstances apply: … (c) **there may be interactions between the
> environmental impacts of the project and the environmental impacts of other developments**, resulting in
> accumulation of impacts and affecting the cumulative environmental impacts."

**Four further clauses in the current TM map one-to-one onto register features — [verified]:**

| Clause | What it requires | Register feature |
|---|---|---|
| §4.3.4(c) | Cumulative effects where projects interact | The product's premise |
| **§4.4.3** | *"The residual environmental impacts refer to the net environmental impacts after mitigation, **taking into account the background environmental conditions and the impacts from existing, committed and planned projects**"* | **Inherited vs caused — in statutory language.** This is F5, and the TM already uses the register's exact concept |
| §4.4.2(a) | Whether the assessment *"covers **all the phases and key sequences** of the project"* | Phasing — F11 |
| §4.4.2(g) | Whether the assessment *"has considered and compared the environmental benefits and disbenefits of various scenarios with or without the project"* | Toggle / compare — already built |
| §4.4.2(m) | Whether the report *"has listed out in a schedule the environmental protection requirements and mitigation measures the applicant is prepared to implement"* | The declaration's content, and the Code of Practice's structure |

**And AFCD & EPD Guidance Note 6/2010** (GN6/2010, *Review of EIA Reports*) says what the register
exists to fix:

> §21: *"Some EIA reports have failed to fully account for the interface with other development projects in
> the vicinity, and, hence, failed to address the cumulative impacts of the projects involved. **These
> development projects should be identified during data collection stage** and the extent of the cumulative
> impacts assessed."*

> §25 "Lack of Communication": *"It was found that there was a lack of communication between the main
> consultant of a proposed project and the environmental sub-consultants…"*

**What this changes about the Code of Practice (TODO A4).** It should be drafted as an **implementation
note against EIAO-TM §4.3.4(c), §4.4.2 and §4.4.3, and GN6/2010 §21** — not as an invention. A vendor's
rulebook is not adopted (§4.2 B4); a document that shows a project office *how the guidance note's own
weak spot gets closed* is a completely different conversation, and it gives the governance body (TODO C4)
something to co-sign that is not ours.

**Action.** The EIAO-TM PDF and GN6/2010 are public. Extract the exact clause text with the
`workbuddy-pdf` skill and store it in `backend/data/reference/` beside the other reference artefacts, in
the same `source`/`status` shape `hsk_ava_reference.json` already uses — so the register's citations are
**checked, not remembered**. A citation to a clause that was renumbered in 2023 would be an embarrassing
failure in front of exactly the audience the product depends on.

---

### 12.5 Skills to equip

**Searched the marketplace** for code review, software architecture, testing, API design, technical
writing, git, github, pull request, data analysis and research. **No installable skill matches this
project's needs** — the two hits are HR-reporting tools (PR review analytics, performance distribution
reports) that would never be used here.

> **Recommendation: install nothing from the marketplace.** The equipped set already covers the work. The
> gap in this project is **domain knowledge and people**, not tooling (§12.6).

**Already equipped, and what each is for:**

| Skill | Display name | Use it for |
|---|---|---|
| **`pstack`** | pstack | **The most relevant one available.** *"rigorous engineering discipline (investigate, fix a bug with proof, build a feature, refactor, run a perf hillclimb, ship a stack, architect a change, interrogate a design, unslop prose, write tests TDD-style)"*. Use for W1–W4: build the declaration and attribution features with the verify-first discipline the codebase already embodies — the comments throughout `sandbox_model.py` and `parameter_card.py` are exactly this discipline applied. Triggers: *"build a feature"*, *"architect a change"*, *"write tests TDD-style"*, *"investigate"*. |
| `impeccable` | impeccable | The register's new UI surfaces (declaration panel, attribution panel, review queue, disclosure matrix). *"design, redesign, shape, critique, audit, polish… accessibility, responsive behavior, empty states, and capturing or documenting design systems (DESIGN.md, tokens)"*. Use it once the panels exist, before the Code of Practice's screenshots are taken. |
| `react-bits-pro` | react-bits-pro | App UI blocks for the register (dashboards, data tables, multi-step forms) if the existing MUI house style is not enough. **Check the licence-key/shadcn-registry terms before pulling anything into a public repository.** |
| `frontend-slides` | frontend-slides | TODO A3 — rebuild the deck's business section as an HTML presentation. |
| `pptx`, `workbuddy-pptx` | pptx, workbuddy-pptx | The existing `.pptx` deck, if it must stay in PowerPoint form. The README already notes the deck is the artefact A3 rewrites. |
| `bold`, `corporate`, `editorial` | bold, corporate, editorial | Deck visual direction. **`corporate` fits a public-sector / consultancy audience; `bold` fits the hackathon-to-commercial pivot.** Two decks, two audiences — worth considering for TODO A3. |
| `csa-outbound-email` | csa-outbound-email | The **B1 approach to a project office**, consultation on the Code of Practice, and letters to REDA / HKIE / HKIP. Grounded in the authoritative Rundown, plain-text body, tone tiered to the recipient, with a pre-send red-line audit. |
| `csa-social-broadcast-copy` | csa-social-broadcast-copy | Public announcement of the register or a pilot. Paste-ready plain text. |
| `workbuddy-pdf` | workbuddy-pdf | **Reading the regulatory PDFs**: EIAO-TM, GN6/2010, TC 1/06 + Annex A, PNAP APP-152, SBDG, AVRG73. Read and extract only. Use it for §12.4's clause extracts and for the Code of Practice's citations. |
| `workbuddy-docx` | workbuddy-docx | The **Code of Practice as a formatted Word document** a project office can attach to a contract (TODO A4's acceptance criterion). |
| `workbuddy-sheet-generation`, `workbuddy-sheetagent` | — | **TODO D1** (count HK projects above the 20,000 m² SBDG threshold): spreadsheet-first, which is the team's stated working style for data work. |
| `deep-research` | deep-research | TODO D2 (verify Autodesk Forma has no flood/drainage capability, from Autodesk's own material), D3 (the legal route for a developer-paid fee), D5 (market sizing), and the §12.4 clause verification. |
| `library` | library | The register's knowledge base: Code of Practice, EIAO clause extracts, reference data, versioned. This is where the "living rulebook" lives once it is co-signed. |
| `sites` | 发布为应用 | F10 — publish the public read-only aggregate view as a link, with no deployment pipeline of its own. |
| `workbuddy-local-office-edit` | workbuddy-local-office-edit | Editing existing Word/Excel in place where the register's outputs need to land in a file the team already uses. |
| `geo-map-compliance-guard` | — | Load before publishing any HK map visualisation (F10's public view will have one). Enforces the approved data-source rules. |
| `expert-manager` | expert-manager | If the team later packages this methodology as a reusable expert for other districts — a plausible post-pivot revenue line. |

---

### 12.6 People — the resource this plan is actually short of

**No Expert in the catalogue matches** (searched: urban hydrology, flood modelling, EIA, civil
engineering, Hong Kong). So B5's sign-off cannot be sourced from the marketplace. It needs people:

| Who | Why | What they unblock |
|---|---|---|
| **A Hong Kong EIA consultant / QP** | To sign the attribution definition (B5) and co-author the Code of Practice (B4). **This is the single most valuable hire in the plan.** | The pilot, the Code of Practice, and the credibility of every number |
| **A civil / hydraulic engineer (HKIE or HKIP)** | To review the hydrology and settle the design storm (D5) with authority | D5, the governance body (TODO C4), and any output that reaches a submission |
| **REDA** (Real Estate Developers Association) | The industry body that could convene the developers who supply the register's inventory | Cold-start (STATUS §1, "biggest risk") |
| **HKIP / HKIE** | Professional institutes whose co-signed guidance carries weight a vendor rulebook does not | TODO C4 governance body |
| **The project office** | The keeper. **B1.** | Everything downstream of the pilot |
| **HKIAIA** | Hack4SDG co-organiser; a route to institutional introductions | C1–C4 |

**The pitch differs for each, and that is worth writing down before the first meeting:**

| Party | What they get | What they are being asked for |
|---|---|---|
| Project office / coordinator | A defensible, dated record of what every project in the district declared — the thing GN6/2010 §21 says gets missed | To hold the register and designate it |
| Developer | A statement of what their project inherited versus what it caused, which is the number their consultant will have to argue about anyway | To declare their inputs (which they have to do regardless) |
| QP / consultant | The cumulative assessment their own EIA study brief already requires, pre-computed and reproducible | To prepare and sign the declaration |
| REDA / HKIE / HKIP | A method, not a product — an attribution definition they could co-own | To co-sign the Code of Practice |

---

### 12.7 Programmes, funding and deadlines

| Programme | Detail | Status / action |
|---|---|---|
| **Cyberport CIP** | TODO A6 — **deadline 1 Dec 2026**, i.e. 17 days from this plan's date | Check eligibility now. It is the nearest deadline in the whole plan |
| **PSTS-SPC** | HK$1.0M cap, year-round. Requires **current incubatee status AND an authorised letter from the participating public-sector body** | **The letter (B1) is the gate, not the application.** Unblocked only by a named public body |
| **HKSTP incubation** | WriteTalent is HKSTP-incubated and already in the network | **A second route to incubatee status that does *not* need the PSTS letter.** Worth evaluating as a faster path — it may unblock C1 months before B1 resolves |
| **Techathon+ 11th edition** | 11 Jan 2027 (TODO C5) | Test the register framing on a judging panel before it meets a procurement officer |
| **Cyberport / HKSTP / HKIAIA** | Institutional network | Introductions to the keeper and the first two developers |
| **HKU CSA, CDSS, EEE** | The peer and alumni network | The first pilot participants |

---

### 12.8 Data and reference sources

| Source | What for | Access / terms |
|---|---|---|
| **CSDI** — `portal.csdi.gov.hk` | 1,100+ spatial datasets from 70+ departments: land, buildings, works, population, transport, environment | Free. **Attribution required: "Map data from CSDI Portal"**, linked to the CSDI terms. Use the *metadata-document* link for a versioned download |
| **CSDI — Site Wind Availability Data** | The wind reference (§12.1) | API; Planning Department |
| **EIAO Technical Memorandum** (EPD, effective 30 Jun 2023) | The cumulative-impact and residual-impact clauses (§12.4) | Public PDF — `epd.gov.hk/eia` |
| **GN6/2010** (AFCD & EPD) | The review guidance that names the problem the register fixes | Public PDF |
| **TC 1/06 + Annex A Technical Guide** (Buildings Department) | The AVA criteria and method the screening is compared against | Public PDF |
| **PNAP APP-152 / SBDG** | The greenery, setback and separation checks for F12 | Buildings Department |
| **AVRG73** | Already vendored as `backend/data/reference/hsk_ava_reference.json` | Already in the repo ✓ |
| **ESA WorldCover**, **Landsat** | Land cover and LST — already the project's rasters | Already in the repo ✓ |
| **CSDI climate / HKO rainfall**, Open-Meteo, ERA5 | The rainfall forcing for D5's design-storm decision | Public APIs |
| **Planning Department OZP, BD plan approvals** | TODO D1 — the count of projects above the SBDG threshold | data.gov.hk + BD records |
| **DEV Drainage Services Department** | Sewerage and drainage network maps — the piped network the screening does not model | Public map services |

---

### 12.9 What I would deliberately *not* add

| Rejected | Why |
|---|---|
| An FGA / authorisation engine (OpenFGA, SpiceDB, Cerbos, Cedar) | Four roles, one district, one disclosure matrix. **Postgres RLS is sufficient** and enforces isolation *below* the application (§12.3) |
| A CFD or urban-flow solver | §3.6 — wrong resolution, weakens the liability position, and the government already publishes the CFD result for the site (§12.1) |
| A new hydrology engine to replace the home-grown one | The liability position depends on the engine being *arithmetic* and inspectable. OSS (WhiteboxTools, HydroMT) is for **cross-checking and calibration**, not replacement |
| SQLAlchemy / Alembic before the PostGIS work | ADR-020 says store mode is configuration; adding an ORM now would move the contract that must not move |
| DVC, lakeFS, Delta Lake, a data lake | The raster set is a handful of files and a digest. `sha256` plus a manifest is the whole requirement, and F2 already specifies it |
| A React rewrite, a state-management framework swap | React 18 + Zustand + MUI are working and tested. The register adds panels, not a new front end |
| Anything from the skill marketplace | §12.5 — searched, nothing relevant; the equipped set covers the work |

---

## 13. Verification of this document

Everything in §1 was measured or read directly on 14 Nov 2026 at `main` @ `bcec6f7`. Specifically:

- The four attribution figures in §3.1 were computed by running the project's own `apply_interventions`
  and `_runoff_and_unstored` against the committed rasters, at the committed default rainfall of 50 mm.
- The test counts in §1.2 were produced by `pytest -q` (247) **and** by the CI-style per-file loop
  (5 suites failing) in `backend/.venv313`.
- The raster drift in §1.3 was established by reading `data/rasters/wetgrid_hsk.json`
  (`rainfall_mm: 450.0`, `unstoredVolumeM3: 180566.3`) against `DEFAULT_RAINFALL_MM` and the ledger,
  and **confirmed by regenerating** at 50 mm and re-running the five failing suites: two went fully green
  (`test_hydrology` 36/36, `test_building_fit` 32/32) and three changed to a single shared symptom
  ("no candidate site for the water reservoir"). The basin was then measured directly — **one 329-cell
  connected component**, above the 20-cell floor, but confined to the steep channel the siting rule
  refuses. **The working tree was restored afterwards**; the repository is as found.
- The openapi comparison in §1.5 was produced by `app.export_openapi.render()` against both the HEAD
  blob and the working-tree file.
- The absence of a status gate (§1.1, §3.2) was established by grepping every engine path
  (`sandbox_model`, `run_service`, `scenario`) for a read of `status`: zero hits.
- The absence of any declaration/attribution/signature/tenant/role identifier was established by a
  repository-wide grep.

**§12 (resources) is sourced, not recalled.** The statutory clause texts in §12.4 were read from the
published EIAO Technical Memorandum (the 2023 revised version, effective 30 June 2023) and from
AFCD/EPD Guidance Note 6/2010, and are quoted with their clause numbers. The CSDI dataset in §12.1 was
confirmed on both the CSDI portal listing and the data.gov.hk catalogue record. The open-source
recommendations were checked against their own documentation rather than recalled, and each carries its
licence and its constraint against the project's two data-conservation rules. **The EIAO-TM clause
extracts should still be pulled into `backend/data/reference/` before the Code of Practice cites them**
— §12.4's action — so the citations are checked rather than remembered.

The claims in §4–§6 are **design proposals**, not descriptions of existing code, and are marked as such.

### One note on what was *not* changed

The regeneration described in §1.3 was run as a **diagnostic**, not as a fix. The raster and scene files
were restored with `git checkout --` so that this planning pass leaves no unrequested data change
behind. The repository's only modifications are the pre-existing `contracts/openapi.json` drift (which
§1.5 recommends committing) and this document. **No dependency was installed** — §12 is a
recommendation set, and the classification in §12.0 is what makes it one.
