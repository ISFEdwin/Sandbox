# Agents

Working notes for anyone — human or agent — changing this repository. It carries the product statement, the map of
which document wins, the current state, and the setup that actually works on this machine. It is not a substitute for
[STATUS.md](STATUS.md): that file is the record, this one is the orientation.

---

## Value proposition

This is the ground truth for the product. Do not reframe Sandbox as a coordination register, a certified model, or a combined score. Copy, decks, and new features have to stay inside this statement. Where each feature stands is in [STATUS.md](STATUS.md). The same statement opens [README.md](README.md).

A quick, broad-brush sandbox that lets developers and planners test any scenario, real or hypothetical, against the projects being planned around them, without anyone having to reveal their designs.

The Northern Metropolis is being built piece by piece, by developers who are competitors and won’t share their plans, so every project is designed blind to its neighbours. Sandbox lets you test your layout in minutes against what’s public, what the neighbours could build, and rough numbers shared through a neutral host. It’s quick and dirty by design: rough enough to need only rough data, and early enough to change the design while it’s still cheap.

## Keywords

- Broad-brush
- Quick-and-dirty
- Hypothetical scenarios
- Early stage
- Incremental planning
- Coordination

---

## 1. Which document wins

Read in this order. When two disagree, the higher row wins.

| # | File | Holds | If it disagrees |
|---|---|---|---|
| 1 | `AGENTS.md` (this) | Product statement, ground rules, orientation | — |
| 2 | [STATUS.md](STATUS.md) | Where every capability actually stands, with evidence and dates. §5 is the constraint list; §9–§12 are dated updates | Wins over everything below |
| 3 | [TODO.md](TODO.md) | The checklist, §A–H, ordered by deadline. `[P0]` = the pathway stalls without it | Wins for what is left to do |
| 4 | [docs/](docs/) | The specs, each one normative for its subject | Wins for its own subject |
| 5 | [PLAN.md](PLAN.md) | Engineering design for the register that follows the comparison | **Historical.** Written 14 Nov against commit `bcec6f7`; it says so at the top. Do not read it as current |
| 6 | [README.md](README.md) | Public-facing description, setup, deployment | Copy and onboarding only |

Board: <https://trello.com/b/Bz0W639T/sandbox> mirrors TODO §A–H across Done / Pending / Blocked / To Do. It is a
**view**, populated 26 Nov 2026. A capability counts as moved when STATUS.md says so — not when a card says so.

### The specs, and what each one is allowed to claim

| Doc | Subject | State |
|---|---|---|
| [STATUS.md](STATUS.md) | The record: capabilities, constraints, dated updates | Live |
| [TODO.md](TODO.md) | Deliverables, §A–H | Live |
| [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md) | Definition of "inherited" vs "caused": three terms, leave-one-out basis, interaction term, what is *not* attributed | Definition only — **no code** (A2b) |
| [docs/PROJECT_IMPORT.md](docs/PROJECT_IMPORT.md) | The import contract: three tiers, two-phase route with `dryRun`, report shape, refusal list | **Spec only** (H0). Nothing built |
| [docs/GOVERNMENT_CRITERIA_FIT.md](docs/GOVERNMENT_CRITERIA_FIT.md) | Each axis → the statutory gate → where the tool stops | Built (G1) |
| [docs/SCREENING_BASIS_ANNEX.md](docs/SCREENING_BASIS_ANNEX.md) | The one-page annex a consultant can paste into a s. 16 submission | Built (G6) |
| [docs/CODE_OF_PRACTICE.md](docs/CODE_OF_PRACTICE.md) | What a fit assertion is and is not | Partly — A4's remaining sections are open |
| [docs/ADR.md](docs/ADR.md) | Architecture decisions. ADR-020: store mode is configuration, so the API contract must not move | Live |
| [docs/PIPELINE.md](docs/PIPELINE.md) | How an area is prepared: sources → DEM → land cover → drainage → overlays → seal | Live |

---

## 2. Where the project stands (as at 26 Nov 2026)

Update this section only by copying a date from STATUS.md, never from memory.

**What runs, in public:** the comparison — two schemes on seven axes, each in its own units, **no combined score and no
pass/fail**. The wind corridor is drawn; the storm plays hour by hour; the gauge is a labelled reading. Criteria fit
sits with the comparison as four rows (air ventilation, sustainable building design, drainage, EIA Ordinance) with
Cap. 499 facts behind Show.

**Met, with evidence:** G1, G2, G3, G5, G6 (government criteria fit, 23 Nov); H0 (import contract, 26 Nov); A3, A7, A8
(deck, pinned contract, recorded suites, 14 Nov); D5 and D5′ (50 mm storm, verified site wind, 14 Nov–23 Nov); public
deployment (24 Nov).

**Not built, and must not be described as built:**

- **Attribution in code.** `/scenario/compare` computes deltas; nothing expresses "this share is mine, that share I
  inherited". Definition exists, endpoint does not (A2b). This is the single most important open code question.
- **A declaration record.** No hash, no signature, no "as at" (B3/B4). The intake route returns a fit read and stores
  nothing.
- **Auth, roles, multi-tenancy.** No login, one worker, `STORE_MODE=file` with no tenant boundary (B1, B2).
- **A third-party project import.** A project is still a repository edit plus `scripts/seed_projects.py` (H1, H2, H3).
- **Underside view.** Four locks, not one: pitch clamped to −88…−8°, collision detection, single-sided tilesets/GLBs/
  globe, clipped globe floor (H10–H13).
- **SVR/LVR.** Stay null. TC 1/06 Annex A defines them from pedestrian test points this screening does not hold.

**Hard limits that are deliberate:** one 43.5 ha study window (HSK/HT); screening-grade hydrology, no piped network; some
land-cover and soil inputs estimated. Every output carries the screening label, the assumption register and the
`furtherInformation` list — that is the liability architecture, not decoration.

---

## 3. Rules that are not negotiable

1. **Stay inside the statement.** Not a coordination register, not a certified model, not a combined score. No combined
   score is also a product decision: the axes stay in their own units.
2. **Never drop the label.** Every output keeps the screening label and the assumption register. Removing either fails
   `tests/test_government_fit.py`. E2.
3. **A fit read is not a determination.** Do not let copy, a deck or a new feature upgrade G2 to a statutory screening
   decision, an environmental permit or a s. 16 decision. F5, G9.
4. **This repository is public.** No fee figures, no competitor analysis, no partner names. E3. Submission decks
   live in `deliverables/` and `deliverables/*.pptx` is git-ignored because they carry the fee schedule; the
   reproducible cut is `scripts/build_deeptech_deck.py`.
5. **An import is a staged scheme, not a declaration.** Geometry plus *stated* effects. No hash, no signature, no "as
   at". Those are B3/B4; borrowing them is the overclaim F5 warns about.
6. **`contracts/openapi.json` is generated.** Regenerate with the pinned pydantic; never hand-edit it.
7. **A blank is not sent.** In intake and in fit, a missing fact becomes `furtherInformation`, never a silent zero or a
   guessed default.
8. **Do not move a published figure silently.** Nothing in H14–H22 changes a scored number; if a change does, it needs a
   note in STATUS.md §5 with the reason.

---

## 4. Layout

```
backend/app/        FastAPI: routers, services, schemas, chat agent
backend/app/services/   scene_service, run_service, consent, siting, scenario, ai_plan,
                        proposal_constraints, government_fit, ventilation, parameter_card
backend/scripts/    data preparation: DEM, land cover, heat, wet grid, buildings, seeding, preflight
backend/data/       committed scenes, plans, interventions and rasters — 65 tracked files
backend/model/      3D models: city tiles, terrain, station, park — 1,686 tracked files, ~476 MB
backend/tests/      the suites (see §6)
frontend/src/       view (Cesium), panels, state (Zustand)
frontend/scripts/   verify-*.mjs browser suites, local only
contracts/          openapi.json (generated), intent_vocabulary.json
docs/               the specs in §1
scripts/            deploy_azure.sh, setup_azure_oidc.sh
.github/workflows/  ci.yml, deploy-api.yml
vercel.json         frontend build, run from the repo root
```

Data and models are committed, so a clone runs without fetching external assets.

---

## 5. Setup

Target Python is **3.14** (what CI and Azure use). **3.13 is the known-good local interpreter** — the recorded 256-check
run was on `backend/.venv313`, Python 3.13.12. `scripts/preflight.py` enforces ≥3.10 and recommends 3.13.

> **`backend/.venv` was removed on 28 Nov 2026.** It was Python 3.10.9 at pydantic 2.9.2, kept an old contract render,
> and every raster script that used it failed at import. A local venv at that path is untrustworthy by definition, so
> `scripts/preflight.py` still probes for one and says so if it reappears. Use `.venv313`, or make a fresh 3.13 venv. A
> green local suite proves nothing about the contract job when the local venv is off-pin — check `pip show pydantic`
> before trusting it.

### Backend (port 8000)

```bash
cd backend
python3.13 -m venv .venv313          # or your own; check preflight before trusting it
source .venv313/bin/activate
pip install -r requirements.txt pytest   # pytest is deliberately not in requirements.txt
cp .env.example .env
python scripts/preflight.py          # exit 0 means this machine can run the project
uvicorn app.main:app --reload
```

`cp .env.example .env` is the documented first-run step: every key in the template is empty, so no model is configured
and chat assembles its template card. That is the intended default, and it is what CI does.

Two backend settings that bite:

- **`STATIC_BASE_URL=/static`** is the one value with no safe default. It must match the `StaticFiles` mount in
  `app/main.py`; left empty, the API hands the frontend `/rasters/...` for a file served at `/static/rasters/...`, and
  the failure presents as "the toggle does nothing".
- **`STORE_MODE=file`** writes to `DATA_DIR` (`./data`, resolved against `backend/`, never the working directory).
  `postgis` is the documented target, not provisionable here.

### Frontend (port 5173)

```bash
cd frontend
npm ci
cp .env.local.example .env.local
npm run dev        # proxies /api and /static to localhost:8000
```

`VITE_CESIUM_ION_TOKEN` is deliberately empty — the viewer sets `baseLayer: false` and supplies OpenStreetMap imagery,
so it runs with zero credentials. `VITE_SCENE_ID` is optional; `scripts/seed_scene.py` prints it.

### Live instance

| | |
|---|---|
| App | <https://sandbox-azure-five.vercel.app> |
| API | <https://sandbox-api-t1.azurewebsites.net> (`/health`, `/docs`) |

Keyless by design: the demo cannot die for want of a key. It is a demo endpoint — one worker, a file store with no
tenancy boundary, no auth, region `italynorth` (~200 ms from Hong Kong).

---

## 6. Checks — exactly what CI runs

Run both halves before calling anything done. `.github/workflows/ci.yml` is path-filtered, so a frontend-only change
skips the backend job and vice versa.

**Backend, two runners — this is the trap.** Most suites are standalone scripts with a `__main__` guard that pytest
collects nothing from, so `pytest -q` alone silently skips most of the checks STATUS.md counts.
`test_overlay_masking.py` has no `__main__` and only runs under pytest. Pick per file, never both:

```bash
cd backend
for f in tests/test_*.py; do
  if grep -q '^if __name__ ==' "$f"; then python "$f"; else python -m pytest -q "$f"; fi
done
```

A file with neither a `__main__` guard nor `def test_*` makes pytest exit 5 with zero checks — a green-looking job with a
skipped suite. Name that as the problem, do not paper over it.

**Frontend:**

```bash
cd frontend
npx tsc --noEmit && npm run lint && npm test && npm run build
```

`tsc` alone does not prove Vite resolves the same imports (the `@/*` alias is registered in both), so the build runs too.

**Contract** — a route or schema change means regenerate, not edit:

```bash
cd backend && python -m app.export_openapi && git add ../contracts/openapi.json
```

CI regenerates and diffs, then runs `oasdiff breaking` against the PR base. A missing `"additionalProperties"` key is the
signature of pydantic version drift, not a schema change.

**Browser suites are local only:** `npm run verify:3d | verify:ux | verify:chat | verify:nav | verify:sandbox`. They need
both servers up plus Playwright's Chromium and exit 2 without them, so they cannot run in CI. Run the relevant one before
merging a rendering change.

**Last recorded green (14 Nov 2026, STATUS §2.1):** 256 pytest checks, 27 CI-style suites, 111 frontend tests, clean
typecheck/lint/build. Treat those as a date, not a standing fact — re-run before quoting them.

---

## 7. Deployment

Two services, because the API cannot run serverless: the unzipped Python dependency set is ~265 MB against Vercel
Functions' 250 MB limit, and the file store writes rasters to disk between requests.

| Piece | Host | Trigger |
|---|---|---|
| Frontend | Vercel, built from the repo root | `git push` to `main`; every PR gets a preview URL |
| Backend | Azure App Service (Linux, 3.13, B1, `italynorth`) | `.github/workflows/deploy-api.yml`, after `ci` passes on `main` |

The frontend builds from the root, not `frontend/`, because `frontend/src/api/intentVocabulary.test.ts` imports
`contracts/intent_vocabulary.json`. `.vercelignore` keeps the tiles out of the upload.

One-time setup: connect `ISFEdwin/Sandbox` in Vercel → Settings → Git (done 25 Nov; it was unlinked before, so pushes
built nothing); run `bash scripts/setup_azure_oidc.sh` for OIDC (no cloud credential in the repo; federated to
`refs/heads/main` only, so a branch or fork cannot deploy even with a green CI).

Two limits to know before trusting the pipeline:

- **It deploys code, not data.** The workflow passes `SKIP_ASSETS=1`; tiles and the store stay on `/home`. Worse,
  `startup.sh` seeds `/home/data` once behind a `.seeded` marker, so a committed change under `backend/data/` never
  replaces what is there. Data changes need a full `bash scripts/deploy_azure.sh` **and** the marker removed.
- **Manual deploys ship the working tree.** `vercel deploy --prod` and `deploy_azure.sh` do not read git history, so a
  deploy from a dirty tree ships unreviewed work.

`render.yaml` is an unused alternative; its filesystem is ephemeral.

---

## 8. Known traps

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: numpy` from a raster script | Wrong interpreter — not the venv the deps were installed into. `python scripts/preflight.py` says so in one line |
| Every request 404s in production, "Could not load the scene" | `VITE_API_BASE_URL` without the `/api` suffix |
| A toggle does nothing; rasters 404 | `STATIC_BASE_URL` empty |
| Contract job red, local suite green | Local venv off-pin. Regenerate with the pinned pydantic |
| A committed `backend/data/` change never appears on Azure | The `.seeded` marker. Full deploy plus marker removal |
| Every tile 404s after a deploy | `/static/model` must exist at import time; `app/main.py` skips the mount silently if it does not |
| CI reports nothing at all | Missing `pull-requests: read` — the path filter cannot evaluate, every downstream `if:` is false |

---

## 9. First five minutes

1. Read the value proposition above, then [STATUS.md](STATUS.md) §2 and §5.
2. `cd backend && python scripts/preflight.py` — fix the environment before reading code.
3. Open [TODO.md](TODO.md) §H. It is the current build priority: a third party cannot put a scheme in front of a run
   without a repository edit, which makes A1 a commit rather than a data entry.
4. If you are changing a number on screen, find the assumption that produced it in the parameter card first. Every figure
   is supposed to be traceable to a stated input.
