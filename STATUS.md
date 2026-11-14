# STATUS

**As of 14 Nov 2026.** Branch `main`, at `07a4d98` (`docs: the attribution spec, the ADR trail, and two corrected wind claims`), five commits ahead of
`origin/main` (`bcec6f7`). Working tree: `PLAN.md` untracked; everything else committed.

What this file is: the measured state of the project — what runs today, what the chosen business model requires, and
which of those requirements exist. It is not a roadmap (see [TODO.md](TODO.md)) and not a pitch (see the deck).

---

## 1. Where the project stands

| | |
|---|---|
| **Stage** | Hack4SDG prototype complete; moving to first paid pilot and institutional track |
| **Product** | Runs locally, end to end: 3D scene → project toggles → run → stats + parameter card → grounded chat |
| **Model chosen** | **Coordination register** — a district-level record of what each project declared about its neighbours, kept by a public-sector coordinator, licensed to developers |
| **Biggest gap** | Everything that makes it a *register* rather than a *sandbox*: declarations, versions, roles, attribution code. None of it is built |
| **Biggest risk** | No written signal that a public body intends to designate it. A voluntary coordination platform has a cold-start problem |
| **Next milestone** | One real development declared into the sandbox by a real developer, with a real neighbour in the baseline |
| **This week** | The engineering base is now clean: the design storm is settled and the committed artefacts agree with the ledger, the whole suite is green on a clean checkout, the attribution *definition* exists as a spec, and the coverage guard has been moved to where it belongs — the consent layer |

---

## 2. What the prototype does today (verified 14 Nov 2026)

Verified by reading the route table and services, and by running the suites.

- **Scenario simulation.** `POST /scenes/{id}/run` executes the analysis. `sandbox_model.py` is pure numpy; the engine
  runs on a laptop in under a second per the project's own measurements.
- **Toggle, swap, compare.** Planned projects are selectable from a catalog with real footprints. `/scenarios`,
  `/scenario/compare` and `/scenario/evaluate` support alternatives; a run is refused if interventions rework more than
  40% of the study area.
- **Environmental variables.** Rainfall intensity and duration, surface temperature, sea level (`/sea-level`), heat
  field (`/heat-field`), ventilation (`/ventilation`, `/ventilation/corridors`), routed and hourly drainage
  (`/drainage/routed`, `/drainage/hourly`), design metrics (`/design-metrics`).
- **Assumption transparency.** `/parameter-card` exists as both a service (`services/parameter_card.py`) and a route
  (`routers/scenes.py:637`). Every run publishes the assumptions it used, including what it does not know.
- **Storage ledger.** `/ledger` reports the storage accounting for a run — this is the shape the register needs.
- **Grounded GenAI.** The model never produces numbers. `chat_service.py` checks every number in an answer card against
  the run outputs and re-prompts once on mismatch; unmatched values are flagged. Interventions are drafted, then
  confirmed by the user before anything is computed.
- **Pinning.** `/pins` and `/pins/{feature_id}/pin` let a feature persist across runs.
- **One design storm.** 50 mm, settled today (§6). The API, the run service, the suggester, the preview, the siting
  rule and the offline raster script all read it from `app.config.DEFAULT_RAINFALL_MM`. The committed raster set is
  generated at it and `tests/test_artefact_drift.py` fails if the two ever disagree.
- **A consent layer.** `app/services/consent.py` holds the coverage thresholds and what happens at them: an
  *undeclared* feature over the cap is refused as before; a *declared* one is applied and flagged for a
  counter-signature or a joint review. The declaration objects themselves are not built (§3).

### 2.1 Measured test status (run 14 Nov 2026, `backend/.venv313`, Python 3.13.12, pydantic 2.13.5)

| | Result |
|---|---|
| `cd backend && ./.venv313/bin/python -m pytest -q` | **256 passed**, 112 warnings, 2 m 45 s |
| CI-style per-file loop (`.github/workflows/ci.yml`'s runner) | **27 suites, all pass** — the loop, not `pytest -q`, is what CI runs |
| `cd frontend && npx tsc --noEmit && npm run lint` | clean (`eslint --max-warnings 0`) |
| `cd frontend && npm test` (vitest) | **111 passed**, 11 files |
| `cd frontend && npm run build` | built |

**The CI-vs-pytest distinction, which matters.** Most of the backend suites are standalone scripts with a `_run()`
main, so `pytest` collects nothing from them; a few are pytest-style files, so `pytest` collects nothing from those.
Neither runner alone covers the suite, and the CI job says so in a comment. The number above is therefore two
numbers: **256** pytest checks and **27** CI-style suites, not "256 tests".

**Before this week's work, the same commands gave:** `pytest -q` → 247 passed; the CI-style loop → **5 suites
failing** (`test_ai_plan`, `test_building_fit`, `test_hydrology`, `test_proposal_contract`, `test_sandbox`). Two of
those five failed for a committed reason — the committed raster set was generated at 450 mm while the engine
computed at 50 mm. The other three failed only on a machine with runtime residue in the store (§2.2).

### 2.2 The suite's environment, which had to be fixed before the numbers meant anything

Two things made a developer's result differ from CI's, both now fixed:

- **The store.** The file store is a runtime store (`.gitignore` says so), but the test isolation copied the whole
  tree into the temp store — residue and all. A hand-poked staged scenario (10 unconfirmed AI drafts, 7 of them
  pinned) claimed 37% of the district as prior work, so the proposer had no free ground left to offer any kind of
  site. The copy is now pruned to the files git tracks, so the suites boot from exactly the state CI boots from.
- **The model.** `data/llm_config.json` (the operator's live model settings, written by `PUT /api/llm-config`) was
  inherited too: the `Settings` singleton is built at import time, before the redirect, so the suites ran against a
  real model while CI runs the heuristic. The model settings are reset to the `.env` baseline.

**The `.venv` trap.** `backend/.venv` is Python 3.10.9 with pydantic 2.9.2 and no pytest — off-pin, and the
environment the committed `contracts/openapi.json` was once rendered under. `backend/conftest.py` now refuses to run
the suite on an environment that does not match `requirements.txt`, and `app/export_openapi.py` refuses to render the
contract off-pin, with the message naming the fix.

---

## 3. What the register model requires, and what exists

The model needs the sandbox to hold a *record*, not just a *result*. Capability by capability:

| # | Register capability | Status | Basis |
|---|---|---|---|
| 1 | Simulate coordinated projects (toggle / swap / compare) | **Built** | Routes + README features |
| 2 | Publish every assumption a run used | **Built** | `/parameter-card` |
| 3 | Storage accounting per run | **Built** | `/ledger` |
| 4 | Multi-hazard layers, separate axes, no combined score | **Built (partial)** | Flood, heat, sea level, ventilation present; wind as geometry is partial |
| 5 | **Declared inputs, signed by the declaring party** | **Not built** | No declaration object anywhere in the schema. The *consent seam* exists (`app/services/consent.py`) and the guard now reads `params.declarationId` / `declarationStatus`, but nothing writes them yet |
| 6 | **Hash + timestamp per declaration** | **Not built** | No signing or provenance layer |
| 7 | **Versioned baseline, queryable "as at" a date** | **Not built** | Scenarios are saved, not versioned |
| 8 | **Attribution: inherited vs caused, per project** | **Defined, not built** | The *definition* now exists: `docs/ATTRIBUTION.md` (three-term decomposition, leave-one-out marginal, interaction term). The code object, endpoint and reconciliation test are not written |
| 9 | Roles: developer, QP, submission coordinator, agency | **Not built** | No authentication or authorisation layer at all |
| 10 | Joint lock-then-declare across parties | **Not built** | Single-user model throughout. The consent layer now *flags* a district-scale composition for joint review; the joint lock is not built |
| 11 | Agency review surface (comments, written direction) | **Not built** | No review workflow |
| 12 | Amendment / resubmission | **Not built** | Plans are editable; there is no submission lifecycle |
| 13 | Tiered disclosure (aggregate public, detail restricted) | **Not built** | Everything is visible to every user |
| 14 | Public read-only aggregate view | **Not built** | — |
| 15 | Multi-tenant store | **Not built** | `STORE_MODE=file` is the only working mode; `db.py` raises on `postgis` |
| 16 | Construction phasing / overlapping timelines | **Not built** | Listed as future work in the deck; projects toggle but carry no dates |

**Reading of this table:** rows 1–4 are a good sandbox. Rows 5–15 are the product. The distance between them is the
whole of the next phase, and it is not a UI problem — it is a data-model problem (versions, signatures, roles, tenancy).
What this week added is the *definition* of row 8 and the *seam* for rows 5 and 10, not the rows themselves.

---

## 4. Business model status

### 4.1 Decided

**The pathway is the coordination register.** Not three parallel products, not a consultancy tool with extras.

| Role | Party | Relationship |
|---|---|---|
| Keeper | District coordinator / project office (public sector) | Anchor customer; holds the register; liable for record integrity only |
| Licensee | Developer companies | Company licence plus per-project registration above a size threshold |
| Submitter | Consultants / QPs | Prepare and declare on the developer's behalf; not separately charged |
| Supplier | Every project in the district | Free read access to the aggregate baseline; declares its own inputs |

**Why government is the anchor rather than a customer among equals:** a private company cannot compel participation,
and the party causing downstream flood risk has no incentive to join a system that documents it. Only a convener can
write the condition.

**Liability position (decided):** the register does not certify risk. The declaring party signs its inputs; the engine
computes on those inputs and is liable for nothing because it is arithmetic; the keeper is liable only for the record's
integrity. This is what allows a public body to adopt it — it never owns a hydrology verdict.

### 4.2 Not decided, and blocking

| # | Open item | Why it blocks | Owner |
|---|---|---|---|
| B1 | Which public body, and does it intend to designate? | Everything downstream depends on it | Edwin |
| B2 | Tariff route: contracted schedule vs pass-through vs voluntary standard | Determines whether revenue is contractual or discretionary | Edwin |
| B3 | Entity: incorporate now, or run pilots as individuals? | Gates incubatee status, which gates PSTS | Edwin |
| B4 | Governance: who signs off the Code of Practice and the fee schedule | A vendor-written rulebook will not be adopted | Team |
| B5 | Attribution definition: what exactly counts as "caused" vs "inherited" | It is the product's central claim | Engineering |

**B5, as of 14 Nov 2026:** a draft spec now exists — `docs/ATTRIBUTION.md` — defining the three terms, the
leave-one-out basis for "caused", the interaction term, and the axes that are *not* attributed per project. What B5
still needs is Engineering's **sign-off on four points** (§7.4), not a rewrite: the tolerance the reconciliation test
asserts, cell-ownership precedence, whether flood extent is published per project at all, and whether `n + 1` run
evaluations per attribution is affordable at the pilot's scale.

Fee levels, competitor positioning and market sizing are held in the internal planning notes, not in this repository,
because this repository is public.

---

## 5. Known constraints

| Constraint | Effect | Trigger to fix |
|---|---|---|
| `STORE_MODE=file` | Cannot serve two concurrent customers; no tenancy boundary | Before the second register participant |
| No auth layer | Cannot have roles, so cannot have declarations or review | Before the first real declaration |
| Single 43.5 ha window | Fine for a pilot, useless for a district licence | Before a second study area |
| Estimated soil/land-cover inputs | Weakens any number quoted to an authority | Before any output reaches a submission |
| LLM dependency on an external provider | Rate limits in a paid session are a churn event | Before charging anyone |
| Screening-grade hydrology | Cannot be sold as an assessment; every output must say so | Never — this is the design, not a gap |
| The design storm is a *stated* input, not an ambient default | Every published figure must carry the storm it was computed under, or it is not comparable with anything | Never — this is the design, not a gap |
| Runtime residue in the local store | The app on a developer machine may start with a staged scenario nobody confirmed; the *suites* are now immune, the app is not | Before the next demo on that machine |

---

## 6. Decisions log

| Date | Decision | Note |
|---|---|---|
| 2026-10-06 | `STORE_MODE=file` chosen deliberately | No Docker/PostGIS on the target machine. Recorded as configuration, not architecture (ADR-020) |
| 2026-10-18 | Six revenue models examined, four ranked | Superseded |
| 2026-11-14 | **Pivot: coordination register, government-anchored, developer-licensed** | Supersedes the consultancy-first sequence |
| 2026-11-14 | **Sell attribution, not simulation** | The engine is a component; the dated declaration record is the product |
| 2026-11-14 | **Developers are free users, not the first customer** | Their submissions are the data inventory; the convener is the buyer |
| 2026-11-14 | **Baseline design storm = 50 mm (D5 settled)** | The API, the run service, the suggester, the preview and the ledger already agreed on 50; 450 mm was a 24-hour event, and the committed raster set was generated at it while the engine computed at 50 — the map disagreed with the ledger by an order of magnitude (16.8 ha of pictured water against 0.8 ha computed). The artefacts are regenerated at 50 and `tests/test_artefact_drift.py` makes the pairing unfalsifiable |
| 2026-11-14 | **The reservoir siting threshold is a share of the district's runoff, not an absolute volume** | The old 300 m³ was a 450 mm number wearing no label; at 50 mm every inflow fell ~20× and the rule refused every face on the site. As a fraction it is storm-invariant: the same four faces are selected at either storm (verified — the same four clear both thresholds) and only the volume quoted for each face changes |
| 2026-11-14 | **Prior work is work the engine scores** | A staged row the engine skips (a `road`: no land-cover effect) claimed 6,482 cells — 37% of the district — as ground already taken, so the proposer had no free ground left to offer. "Claimed" means "the cells the run would rework", which a skipped row does not |
| 2026-11-14 | **The coverage cap belongs to the consent layer** | A declared project over the cap is applied and flagged for a counter-signature or a joint review; an undeclared one is refused as before. Refusing a declaration would drop exactly what the register exists to hold |
| 2026-11-14 | **The suggestion card offers one site per axis, never the same site twice** | The flood axis was added after the "at most three" check was written and the cap was never updated; the axes draw on overlapping pools, so the same footprint could be offered twice under two labels |

---

## 7. Open questions and things not verified

1. **Does attribution exist in code?** No. `/scenario/compare` computes deltas between scenarios, but nothing expresses
   "this share is mine, that share I inherited" as an object. The *definition* now exists (`docs/ATTRIBUTION.md`); the
   code is F5. This is still the single most important code question in the project.
2. **Number of HK projects above the 20,000 m² SBDG threshold.** Not published as far as this research found. It is the
   number that decides whether the market is under-priced or under-covered.
3. **Whether anything comparable exists for inter-project cumulative screening in HK.** No product found; absence of
   evidence is not evidence of absence, and this should be re-checked before it is claimed on a slide.
4. **The four points in the attribution spec that need a decision, not a rewrite** (from `docs/ATTRIBUTION.md` §7):
   the tolerance the reconciliation test asserts (1e-9 m³ is the proposal); cell-ownership precedence where two
   projects changed the same cell, which is settled by the requirement that it reproduce the leave-one-out marginal;
   whether flood extent is published per project at all (the spec's answer is no — aggregate only, with the
   per-project margin as a range); and whether `n + 1` run evaluations per attribution is affordable at the pilot's
   scale.

---

## 8. Maintenance

Update this file when a row in §3 changes status, when a §4.2 item is decided, or when the model changes. The
"verified / inherited / unverified" distinction must survive edits — an unverified claim written as fact here will be
quoted as fact later.
