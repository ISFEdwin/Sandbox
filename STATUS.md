# STATUS

**As of 14 Nov 2026.** Branch `main`, at `8ee2009` (`docs: describe where GenAI is used in the prototype`), in sync with
`origin/main`. Working tree: `contracts/openapi.json` modified, uncommitted.

What this file is: the measured state of the project — what runs today, what the chosen business model requires, and
which of those requirements exist. It is not a roadmap (see [TODO.md](TODO.md)) and not a pitch (see the deck).

---

## 1. Where the project stands

| | |
|---|---|
| **Stage** | Hack4SDG prototype complete; moving to first paid pilot and institutional track |
| **Product** | Runs locally, end to end: 3D scene → project toggles → run → stats + parameter card → grounded chat |
| **Model chosen** | **Coordination register** — a district-level record of what each project declared about its neighbours, kept by a public-sector coordinator, licensed to developers |
| **Biggest gap** | Everything that makes it a *register* rather than a *sandbox*: declarations, versions, roles, attribution. None of it is built |
| **Biggest risk** | No written signal that a public body intends to designate it. A voluntary coordination platform has a cold-start problem |
| **Next milestone** | One real development declared into the sandbox by a real developer, with a real neighbour in the baseline |

---

## 2. What the prototype does today (verified in code, 14 Nov 2026)

Verified by reading the route table and services, not by running the app.

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

**Not verified in this session:** the test suites. `backend/tests` and the frontend checks exist and CI runs them, but
no run was executed while writing this file. Do not quote a pass count from memory — run it.

---

## 3. What the register model requires, and what exists

The model needs the sandbox to hold a *record*, not just a *result*. Capability by capability:

| # | Register capability | Status | Basis |
|---|---|---|---|
| 1 | Simulate coordinated projects (toggle / swap / compare) | **Built** | Routes + README features |
| 2 | Publish every assumption a run used | **Built** | `/parameter-card` |
| 3 | Storage accounting per run | **Built** | `/ledger` |
| 4 | Multi-hazard layers, separate axes, no combined score | **Built (partial)** | Flood, heat, sea level, ventilation present; wind as geometry is partial |
| 5 | **Declared inputs, signed by the declaring party** | **Not built** | No declaration object anywhere in the schema |
| 6 | **Hash + timestamp per declaration** | **Not built** | No signing or provenance layer |
| 7 | **Versioned baseline, queryable "as at" a date** | **Not built** | Scenarios are saved, not versioned |
| 8 | **Attribution: inherited vs caused, per project** | **Not built / unverified** | Compare and ledger exist; an explicit inherited-vs-caused split was not found |
| 9 | **Roles: developer, QP, submission coordinator, agency** | **Not built** | No authentication or authorisation layer at all |
| 10 | **Joint lock-then-declare across parties** | **Not built** | Single-user model throughout |
| 11 | **Agency review surface (comments, written direction)** | **Not built** | No review workflow |
| 12 | **Amendment / resubmission** | **Not built** | Plans are editable; there is no submission lifecycle |
| 13 | **Tiered disclosure (aggregate public, detail restricted)** | **Not built** | Everything is visible to every user |
| 14 | **Public read-only aggregate view** | **Not built** | — |
| 15 | **Multi-tenant store** | **Not built** | `STORE_MODE=file` is the only working mode; `db.py` raises on `postgis` |
| 16 | **Construction phasing / overlapping timelines** | **Not built** | Listed as future work in the deck; projects toggle but carry no dates |

**Reading of this table:** rows 1–4 are a good sandbox. Rows 5–15 are the product. The distance between them is the
whole of the next phase, and it is not a UI problem — it is a data-model problem (versions, signatures, roles, tenancy).

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
| B5 | Attribution definition: what exactly counts as "caused" vs "inherited" | It is the product's central claim and it is currently undefined | Engineering |

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

---

## 6. Decisions log

| Date | Decision | Note |
|---|---|---|
| 2026-10-06 | `STORE_MODE=file` chosen deliberately | No Docker/PostGIS on the target machine. Recorded as configuration, not architecture (ADR-020) |
| 2026-10-18 | Six revenue models examined, four ranked | Superseded |
| 2026-11-14 | **Pivot: coordination register, government-anchored, developer-licensed** | Supersedes the consultancy-first sequence |
| 2026-11-14 | **Sell attribution, not simulation** | The engine is a component; the dated declaration record is the product |
| 2026-11-14 | **Developers are free users, not the first customer** | Their submissions are the data inventory; the convener is the buyer |

---

## 7. Open questions and things not verified

1. **Does attribution exist?** `/scenario/compare` computes deltas between scenarios. Whether the code can express
   "this share is mine, that share I inherited" as a separate object was not confirmed. This is the single most
   important code question in the project.
2. **Test status.** Not run this session. Do not state a pass count without running it.
3. **Number of HK projects above the 20,000 m² SBDG threshold.** Not published as far as this research found. It is the
   number that decides whether the market is under-priced or under-covered.
4. **Whether anything comparable exists for inter-project cumulative screening in HK.** No product found; absence of
   evidence is not evidence of absence, and this should be re-checked before it is claimed on a slide.

---

## 8. Maintenance

Update this file when a row in §3 changes status, when a §4.2 item is decided, or when the model changes. The
"verified / inherited / unverified" distinction must survive edits — an unverified claim written as fact here will be
quoted as fact later.
