# STATUS

**As of 23 Nov 2026.** Branch `main`, at `e196c91` (`docs: record the week's state, and commit the build plan`), seven commits ahead of
`origin/main` (`bcec6f7`). The comparison build is §9 (18 Nov). The measurements in §2.1 were taken at `07a4d98` on 14 Nov;
the suites were re-run on 18 Nov against the comparison build (265 backend, 115 frontend).
The header previously named `07a4d98` and an untracked `PLAN.md` — both superseded by `e196c91`. Later findings are collected in §9 rather
than scattered through the earlier text.

What this file is: the measured state of the project — what runs today, what the chosen product is, and
which of those requirements exist. It is not a roadmap (see [TODO.md](TODO.md)) and not a pitch (see the deck).

**Main edges (ground truth, 23 Nov 2026).** The product is a broad-brush comparison tool. These five edges are the ones the demo and the next deck lead with. Deck v2 and the opening of [PLAN.md](PLAN.md) still lead with a coordination register; they are behind this section until revised.

| Edge | What it is | Where it stands |
|---|---|---|
| **1. Comparison across separate axes** | Two schemes, read side by side, each axis in its own units: drainage deficit and flood extent, surface heat, tide, greenery and impervious share, wind channel. No combined score and no pass/fail. | **On screen.** `POST /scenes/{id}/compare-schemes` scores A and B against one baseline and storm; `ComparisonPanel` prints A / B / B−A for seven rows and returns `combinedScore: null`. `/scenario/compare` still ranks whole scenarios separately. |
| **2. A shared picture follows from holding the schemes** | The schemes already on the table sit in one model, so the comparison is also what each project assumed about the others. The dated register is that side effect. It is not the product the demo opens on. | Toggles, swap and compare run today. Declarations, versions, roles and tenancy do not, and they are downstream of the comparison. |
| **3. Natural-language intervention** | A sentence such as "add a retention pond in the north" becomes a draft on the map. The site is chosen from the terrain, land cover and flood grid; the model cannot invent coordinates. The user confirms before the comparison scores it. A height or density request goes to the massing tool with an explicit scope. | **Built.** Routing is `app/agent/intent.py` (the model can raise a turn to an intervention and cannot lower one). Placement is `app/services/ai_plan.py`. Drafts stay drafts until confirm. |
| **4. Wind channel as a comparison axis** | The channel is the prevailing inflow (NE), drawn so a toggled scheme can be read against it. The inflow is the Planning Department site-wind table, cited. With the 2.5D massing on, the drawing is a coarse OpenFOAM solve around those extruded footprints. The least-cost corridor remains the fallback, and it is what the textured 3D view draws. Neither drawing is a velocity ratio or a pass/fail. | **Solved, off the request path.** `scripts/openfoam_channel/run_channel.py` runs `simpleFoam` (k-epsilon) in the image `opencfd/openfoam-run:2512` (GPL-3.0). The Foundation tree is cited and not vendored. Obstacles are the 2.5D footprints. The inlet, 2.922 m/s, is the PlanD annual 500 m NE bin midpoint (6.9095 m/s, cell 3463) times (10/500)^0.22; PlanD does not publish that 10 m speed. Sidecar `data/openfoam/channel_sidecar.json` is SOLVED, 23 Nov 2026. The compass selects the from-bearing (16 PlanD directions) and the season and height table. Each bearing is solved at its annual 500 m inlet; another table scales those speeds by the inlet ratio. The comparison row is still the geometric corridor. `POST /ventilation/diagnostic` stays a shelter index. The window also touches cells 3462, 3559 and 3560; those roses are not merged. The default corridor weight is still the AVRG73 combined 40.8% fact. |
| **5. Screening, labelled** | Every figure says what was assumed and what is unknown. The engine is arithmetic on the schemes it was given. | The parameter card and the grounded chat do this today. |

---

## 1. Where the project stands

| | |
|---|---|
| **Stage** | Hack4SDG prototype complete; the comparison runs; the shared record around it does not |
| **Product** | A broad-brush comparison: 3D scene, project toggles, a natural-language intervention, then two schemes side by side on seven axes, a wind corridor, a storm playhead and a labelled gauge |
| **Model chosen** | **Comparison first.** Holding the schemes in one model is what makes the comparison a shared picture. The coordination register is that consequence, not the headline |
| **Biggest gap** | The comparison is a panel of numbers, not a diff of the two schemes' rasters on the map; the register rows (declarations, versions, roles, tenancy) remain unbuilt |
| **Biggest risk** | No written signal that a public body intends to designate it, and no paying pilot. A voluntary record has a cold-start problem |
| **Next milestone** | A real developer's scheme declared into the sandbox next to a real neighbour, then one comparison demoed end to end |
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
| 4 | Multi-hazard layers, separate axes, no combined score | **Built (partial)** | Flood, heat, sea level, ventilation present; the wind channel adds a coarse OpenFOAM overlay on the 2.5D massing, off the request path |
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

**Reading of this table:** rows 1–4, together with natural-language intervention, are the comparison product. Rows 5–15 are the shared record that appears once several parties compare inside the same model. They stay listed because the record is real work. They are not the headline, and they are not what the demo leads with.

---

## 4. Business model status

### 4.1 Decided

**The product is the comparison.** The five edges above are the ground truth. The coordination register is what that comparison becomes once the schemes in it belong to more than one party. It is one product, and the record is the consequence of holding the plans.

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
| B5 | Attribution definition: what exactly counts as "caused" vs "inherited" | It is the claim of the shared record, which follows the comparison. The comparison itself does not wait on it | Engineering |

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
| 2026-11-18 | **Comparison is the product; the register is the side effect** | Supersedes the 14 Nov headline. The demo and the next deck lead with scheme-against-scheme on drainage, heat, tide, greenery and the wind channel, plus a natural-language intervention. Deck v2 still titles itself as the coordination register and is behind this decision |

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

---

## 9. Update — 18 Nov 2026: competition entry readiness

### 9.1 What moved since 14 Nov 2026

| | |
|---|---|
| **Code** | **Landed 18 Nov, uncommitted.** The comparison surface (§9.6): `routers/compare.py`, `services/comparison.py`, `wind_diagnostic.py`, `storm_playback.py`, `weather.py`, the `ComparisonPanel` / `StormPlayback` / `WeatherGauge` components, the wind corridor layer, and 9 new backend tests. 265 backend and 115 frontend tests pass; `tsc` and `vite build` are clean |
| **Business / deck** | Moved outside this repo: `03_business/Sandbox_Business_Model_v2_2026-11-14.md`, `Sandbox_Coordination_Register_Model_2026-11-14.md`, `Sandbox_Competitive_Landscape_2026-11-14.md`; deck rebuilt as `04_submission/Sandbox_Pitch_v3_2026-11-18.pptx` (15 slides, comparison-first). The v2 deck remains as `Sandbox_Pitch_v2_2026-11-16.pdf` |
| **Deck honesty** | The new deck states its own limits on slide 4: **4/16 register capabilities built · 0 declarations · 0 paid pilots · 1 study window · file-based store**. It does not claim the register exists |
| **Competition scouting** | `02_planning/2026-27_competition_pipeline.md` and `2026-27_entry_readiness_todo.md` produced 18 Nov |
| **Tests** | §2.1's numbers are 14 Nov measurements, **not re-run since**. Re-run before any competition demo (TODO E1) |

### 9.2 Gap against competition entry requirements

| Competition · deadline | Existing asset | Gap that blocks a strong entry | Severity |
|---|---|---|---|
| **Cyberport CCMF GBA YEP** · 27 Nov | Individual eligibility is likely met (age / institution) | **No Guangdong or Macau resident teammate identified.** Stage 1 is a 2-hour individual form; Stage 2 needs a cross-region team (≥50% HKID) | ⚠️ Stage 1 can still be entered; Stage 2 cannot |
| **Cyberport CCMF HK** · 1 Dec | 15-slide comparison-first deck v3; digital-tech project; working demo | No 6-month milestone plan; no HK$100k line-item budget; no explicit 3-month time-to-market; no incorporation decision (individual route is available and unblocks this) | 🔴 Must write in the next 7 days |
| **Techathon+ 11th** · 11 Jan | Working engine; parameter card; grounded chat; 14 Nov test evidence | **Team on the deck has 5 members** — fine for Techathon+ (2–6), but the same 5 cannot enter Hult or Imagine Cup. Project must also be free of HKSTP funding — do not take Ideation first | 🟡 Form a 4-person subset |
| **Hult Prize** · 28 Feb | For-profit B2G model; SDG framing available | No 4-minute pitch video, no one-pager, no ≤4 team locked. Hult takes ~10% equity — decide before entering | 🟡 |
| **Imagine Cup** · 28 Feb | Product runs on Azure-compatible stack | **No company** (must be founded on/after 2 Nov 2024), **no Azure usage on 10 services**, no business verification. 4–6 weeks of lead time | 🔴 Effectively unreachable if not started now |
| **13th HK University Student Innovation & Entrepreneurship** · ~Mar | Deck-only submission; cross-institution teams allowed | Call not published. Need to choose 创新 vs 创业 track and decide company-registration cut-off category | 🟡 Watch January |
| **IMC Prosperity / WorldQuant IQC** · ~Mar–Apr | CEng + Finance team profile fits | No team, no BRAIN accounts, no Python harness or practice alphas | ⚪ Optional side track |

### 9.3 Three conflicts to settle before any submission

1. **Team of 5 vs team of 4.** Deck v2 names Bernice Leung, Edwin Fang, Chen Xu, Chloe Chik, Katie Chu. Hult allows 2–4; Imagine Cup allows ≤4 official members; IQC 1–4; Techathon+ 2–6; IMC ≤5. A **4-person subset** satisfies all of them. Do not submit five names to Hult or Imagine Cup.
2. **TODO A6 is almost certainly misnamed.** It reads "Cyberport CIP application — deadline 1 Dec 2026". Cyberport's published intake table gives the **CCMF Hong Kong Programme** a 1 Dec 2026 deadline for the Feb 2027 intake; the Incubation Programme's Oct 2026 intake closed 3 Aug 2026. ⚠️ Verify on the Cyberport portal, but prepare the **CCMF** application, not CIP.
3. **The deck sells attribution; the code does not have it.** STATUS §3 row 8 and §7.1 still hold: `docs/ATTRIBUTION.md` is a definition, not an endpoint. Any competition question that asks for a live "inherited vs caused" split must be answered as *designed, not yet built* — slide 4 supports that answer, a live demo does not.

### 9.4 Reusable assets already in hand

- `04_submission/Sandbox_Pitch_v3_2026-11-18.pptx` — 15-slide comparison-first deck; `Sandbox_Pitch_v2_2026-11-16.pdf` is the prior version
- `04_submission/deck/build_pitch_deck.py` — reproducible deck build; slide/style profiles alongside it
- `T1/docs/ATTRIBUTION.md` — the central product claim in written form
- `03_business/Sandbox_Competitive_Landscape_2026-11-14.md` and the three business notes — market and positioning material
- `04_submission/Team 1 – T1.md`, `workbuddy_usecases.md` — prize report and prompt register
- The verified test state in §2.1 — usable as evidence, only after a fresh run

### 9.5 The product decision moved the same day

§1 now leads with the comparison. The register gap is unchanged and is no longer the headline: no real declaration has been entered, and attribution exists only as a spec. A1 and A2b remain the work that turns the shared picture into a record. They are not the edges the demo leads with. Those are the five rows at the top of this file.

### 9.6 The comparison surface, built 18 Nov 2026

| Surface | Route / file | What it answers, and what it refuses to claim |
|---|---|---|
| Comparison board | `POST /api/scenes/{id}/compare-schemes` · `services/comparison.py` | A vs B on drainage deficit, routed flood extent, heat index, greenery, impervious share, wind obstruction and tide tailwater. `combinedScore` is always `null`; `whyNoCombinedScore` says why |
| Sensitivity | `POST /api/scenes/{id}/sensitivity` · same service | Rainfall at ±20% through the same ledger. Three readings, one `swingM3`, one sentence naming the assumption that moved. Not an uncertainty analysis |
| Wind corridor | `/ventilation/corridors` · `view/corridorLayer.ts` · `view/openfoamLayer.ts` | The least-cost path, plus the OpenFOAM streamlines when 2.5D massing is on and `data/openfoam/channel_streamlines.geojson` is present. Colour on those lines is the solved speed from that coarse run, not a velocity ratio |
| Shelter diagnostic | `POST /api/scenes/{id}/ventilation/diagnostic` · `wind_diagnostic.py` | Share of the upwind path blocked by massing, as a PNG + sidecar (`DIAGNOSTIC_SHELTER_INDEX_NOT_A_SPEED`). URock / pyqes named as the external check; neither vendored |
| Storm playhead | `POST /api/scenes/{id}/storm/playback` · `storm_playback.py` | One PNG per hour from the existing `hko_2023_09_07` march. Mass balance `rain_in == stored_gain + drained + standing_end` enforced (`residualM3: 0.0`), screening label kept on screen |
| Gauge | `GET /api/scenes/{id}/weather/current?mode=recorded\|live` · `weather.py` | Recorded storm (deterministic) or HKO `rhrread` with its own units. Live rainfall since midnight is returned as `usableAsIntensity: false`, never converted into an intensity |

Verified on 18 Nov by running the app against the seeded scene: the panel printed A / B / B−A for all seven rows with B = HSK Park + HSK MTR station, the shelter PNG was fetched and draped, the sensitivity strip returned 4,339 / 7,335 / 10,352 m³, and the playhead fetched frames h02–h07 as it advanced.

Two defects found and fixed in that pass:

1. The playhead wrote the new overlay URL from inside a React `setFrame` updater, which updated `SandboxViewer` while `StormPlayback` rendered. React warned and the map kept frame 0 while the readout advanced. The frame index now moves first; one effect applies the frame from committed state.
2. Generated overlays landed outside `.gitignore`; `backend/data/rasters/comparison/` and `.../storm/` now sit with `.../run/` as transient render output.

---

## 10. Update — 23 Nov 2026: government-criteria fit

A declaration can be read against the published gates. The output is a broad-brush fit read. It is not an environmental permit and not a section 16 decision. Primary sources stay in [the screening-criteria note](../01_research/HK_Government_Screening_Criteria_Urban_Planning.md). The product page is [docs/GOVERNMENT_CRITERIA_FIT.md](docs/GOVERNMENT_CRITERIA_FIT.md).

| Surface | Where | What it says, and what it refuses to say |
|---|---|---|
| Intake | `POST /api/declarations/intake` · `services/government_fit.py` | `governmentFit` plus a pasteable `screeningBasisAnnex`. The route does not store a declaration |
| Thresholds | `backend/data/reference/hk_screening_thresholds.json` | Value, unit, source URL, effective date, superseded-by. Repealed entries stay. A live entry that reuses a superseded value fails the drift guard |
| Panel | `frontend/src/components/GovernmentFitPanel.tsx` | Beside the parameter card. One row per fact. A blank is not sent. The card leads with “Not a determination”, then Schedule 3, Schedule 2, town planning, environmental assessment, section 4(4) and HKPSG noise, then the unknowns list |
| Liability | `docs/CODE_OF_PRACTICE.md` · `docs/SCREENING_BASIS_ANNEX.md` | What a fit assertion is. Dropping the screening label or `furtherInformation` fails `tests/test_government_fit.py` |

Schedule 3 is urban development or redevelopment of more than 50 ha (L.N. 77 of 2023, commenced 30 June 2023). The 20 ha test, the 100,000-population test, the engineering-feasibility wording and P.2 do not fire. A.1 is road class only. A share of the district is converted to hectares when the district area is supplied; on this study window, 30% is not 50 ha. HKPSG Chapter 9 is a check, never a pass or a fail. 20/10/5 m stays the open-space separation.

Hung Shui Kiu–Ha Tsuen is recorded as plan **S/HSK/4**, approved 29 September 2026, gazetted 9 October 2026. Zone Notes, Deep Bay overlap, receiver distances and section 5(9)–(11) were not read. Those gaps stay in `furtherInformation`.

Checked in the running app on 23 Nov: 60 ha and a trunk road returned Schedule 3 **Review** and Schedule 2 **A.1**, with the label and the unknowns list on the panel. `tests/test_government_fit.py` (24) and `frontend/src/api/governmentFit.test.ts` (9) pass. §2.1’s full-suite counts were not re-run for this pass.

Still open, and not claimed here: G4 has no map layer; G7 has not copied the statutory texts into the repo; G8 has not read the site-specific Notes; G9 has not edited the deck. A1 is still unmet: the panel does not store a declaration.

