# Sandbox — broad-brush comparison for schemes in one district

## Value proposition

A quick, broad-brush sandbox that lets developers and planners test any scenario, real or hypothetical, against the projects being planned around them, without anyone having to reveal their designs.

The Northern Metropolis is being built piece by piece, by developers who are competitors and won’t share their plans, so every project is designed blind to its neighbours. Sandbox lets you test your layout in minutes against what’s public, what the neighbours could build, and rough numbers shared through a neutral host. It’s quick and dirty by design: rough enough to need only rough data, and early enough to change the design while it’s still cheap.

This is the ground truth for the product. Feature status lives in [STATUS.md](STATUS.md). The same statement is in [AGENTS.md](AGENTS.md).

## Keywords

- Broad-brush
- Quick-and-dirty
- Hypothetical scenarios
- Early stage
- Incremental planning
- Coordination

## Live instance

| | |
|---|---|
| App | <https://sandbox-azure-five.vercel.app> |
| API | <https://sandbox-api-t1.azurewebsites.net> (`/health`, `/docs`) |

No login, no key required. The backend runs the keyless fallback, so the chat answers from template cards and the
rule-based parser rather than a hosted model — the same fallback described under
[Where GenAI is used](#where-genai-is-used). Every figure on screen is screening output, not a statutory assessment.

The API is on a student credit and is not sized for load: one worker, a file store with no tenancy boundary, and a
region in Europe (see [Deployment](#deployment) for why). Treat it as a demo endpoint.

A 3D comparison tool for Hung Shui Kiu / Ha Tsuen (HSK/HT) in the Northern Metropolis. Place the developments that are
actually planned for a district, turn them on and off, add one in a sentence, swap one for another, change rainfall and
temperature, and see what each combination does — drainage, surface heat, tide, greenery, and the wind channel — in
seconds, before a design is fixed.

The prototype was built for Hack4SDG (Team 1007). Holding those schemes in one model is what makes the comparison a
shared picture of what each project assumed about the others. The dated register is that consequence. The comparison
is the product.

> **Status:** the comparison runs, in public: two schemes on seven rows, each in its own units, with no combined score.
> The wind corridor is drawn, the storm plays hour by hour, and the gauge is a labelled reading. Criteria fit sits
> with the comparison: four rows for air ventilation, sustainable building design, drainage and the EIA Ordinance.
> That read is a broad-brush fit read, not a statutory determination. The shared record around the comparison is not
> built. See [STATUS.md](STATUS.md) and [TODO.md](TODO.md).

## The problem it addresses

Three specific failures, not one general complaint:

1. **Coordination.** The Northern Metropolis is delivered in stages, by different parties, at different speeds. HSK and
   San Tin are under construction while other areas are still in planning. A CDE coordinates information *inside* one
   project; nothing coordinates *between* projects. Each new development is assessed in isolation, ignoring the
   neighbour that is half-built or the phase that arrives in 2029.
2. **Legal compliance.** Cumulative and attributed impact is already required, not optional: EIAO Technical Memorandum
   §4.3.4 (cumulative effects where projects interact) and §4.3.1(c)(iii) (differentiate the impact caused by this
   project from that caused by other projects); Air Ventilation Assessment under TC 1/06 (compare design options by
   spatial-average velocity ratio); Sustainable Building Design Guidelines under PNAP APP-152, where compliance gates
   GFA concessions. Each needs a comparison between options. Today each costs days of specialist time.
3. **Dirty testing.** Real schemes are tested against messy conditions — estimated inputs, neighbours not yet built,
   phases out of order, assumptions that change mid-design. Engineering models are built for one calibrated,
   authoritative run. They are the wrong shape for thirty quick comparisons.

## What the sandbox does

- **Compare schemes.** The planned projects, with real footprints, switched on and off in combination. The axes stay
  separate: drainage volume, surface heat, tide, greenery, and the wind channel. There is no combined score and no
  pass/fail verdict.
- **Add an intervention in a sentence.** "Add a retention pond in the north" becomes a draft on the map. The site comes
  from the terrain, land cover and flood grid, so the model cannot invent a coordinate. You confirm it before the
  comparison scores it. A height or density request goes to the massing tool, with the place it applies to stated.
- **Change the conditions.** Rainfall intensity and duration, surface temperature, sea level. The parameter card
  publishes every assumption a run used, including what the model does not know.
- **Watch the storm.** A playhead steps the named `hko_2023_09_07` hyetograph hour by hour, with the mass balance
  printed beside the frame and the screening label on screen. The gauge can use the recorded storm or a live HKO
  reading, returned in its own units rather than guessed into an intensity.
- **One knob at a time.** Rainfall at ±20% re-runs the ledger and reports which assumption moved the deficit.

Screening only. It sits in front of the statutory hydraulic assessment; it does not replace it, and every output is
labelled as derived rather than certified. Criteria fit is the same kind of label for the published gates: a fit
read of the facts you type, not a permit and not a planning decision.

## Who it is for

| Role | What they do |
|---|---|
| District coordinator (public sector) | Compares the schemes already on the table, on one set of axes |
| Developer | Puts their massing, drainage and phasing into that comparison, including by describing an intervention |
| Consultant / QP | Prepares the scheme and reads the comparison for the developer |

How this is paid for — licensing structure, tier boundaries and the tariff route — is documented in the internal
planning notes rather than here, because this repository is public.

## Features

- **3D sandbox:** terrain and buildings in Cesium, in textured 3D or 2.5D massing, with buttons for tilt, orbit, zoom, top-down and north-up.
- **Overlays:** flood (wet grid) and heat layers you can switch on and off.
- **Scenario inputs:** rainfall intensity, duration and surface temperature sliders feed each run.
- **Project catalog:** planned projects with real footprints. Selecting several scores their combined effect. The backend refuses a run that reworks more than 40% of the study area.
- **Natural-language interventions:** a core feature. Describe one in the chat (for example, a park or a retention pond). It shows up as a draft grounded in the site's own grids, and you confirm it before it is placed. A details card asks for each value the run uses, and you either enter your own or let the AI estimate it. Estimated values are labelled as such.
- **Grounded chat:** ask about a run and get a structured answer card covering what the run shows, what to do, confidence and caveats. Every number in it is checked against the run's outputs.
- **Stats and parameter card:** a live summary after each run, plus a reference table of the run's assumptions, including what the model doesn't know.
- **Criteria fit:** four rows with the comparison — air ventilation (Technical Circular 1/06), sustainable building design (PNAP APP-152), drainage (Drainage Services Department), and the EIA Ordinance (Cap. 499). Each row names who set the rule, what this sandbox screens, and one limit. Wind paths come from the comparison when it has been run; site and local velocity ratios are not held. Greenery, when the comparison has it, stays in its own units; separation and setback are not checked. Runoff and flood storage are the ledger, not an installed sewage capacity and not a Drainage Impact Assessment. Cap. 499 facts sit behind Show. A blank is not sent. Read fit returns Schedule 2 and Schedule 3 flags from those facts. Neighbours on the map are not a cumulative-impact finding. It is a broad-brush fit read, not an environmental permit and not a section 16 decision.
- **LLM settings:** set the provider, base URL and model in the app. The API key is never shown back.

## User flow

1. Open the app. The HSK/HT scene loads and the camera frames the study area.
2. Turn on the Flood or Heat overlay to see the baseline.
3. Pick projects from the catalog, add interventions through the chat, or both.
4. Set the sliders and press **Run**.
5. Read the stats panel, then ask the chat why the numbers changed or what to try next.
6. Adjust or delete interventions in the Interventions panel and run again to compare.
7. Read **Criteria fit** with the comparison. The four rows are the aim of the sandbox. Open **Show** only to type Cap. 499 facts you hold, then press **Read fit**. Unknowns stay closed until you ask.

## Where GenAI is used

The language model explains results and picks from options the analysis has already worked out. It never produces the numbers itself.

- **Chat answers** (`backend/app/agent/chat_service.py`): turns a question about a run into a structured answer card. Every number in the card is checked against the run's outputs. If a number doesn't match, the card goes back to the model once with the problem named. Anything still unmatched is flagged in the card.
- **Run explanation** (`backend/app/services/run_service.py`): after each run, the model writes a short card on what the run changed.
- **Interventions from plain language** (`backend/app/services/ai_plan.py`): the model turns an instruction like "add a retention pond in the north" into a choice from a fixed list of candidate sites drawn from the terrain, land cover and flood data. It can't invent coordinates. Building-height and density requests go to a separate massing tool. Anything the AI proposes starts as a draft, and nothing is calculated on it until the user confirms it.
- **Estimated values**: on the details card, the user can let the AI estimate a value instead of entering one. Estimated values are labelled differently from values the user entered.

Telling a question apart from an intervention request is done by fixed rules, not the model. The app supports Anthropic or any OpenAI-compatible endpoint (`backend/app/agent/llm.py`) and forces structured output. If no model is set up, it falls back to template cards, labelled as templates, and a rule-based parser.

## Stack

- **Backend:** FastAPI (Python 3.14), with numpy, scipy, rasterio and trimesh for the analysis. Data is stored as files in `backend/data` (`STORE_MODE=file`).
- **Frontend:** React 18, TypeScript, Vite, Cesium, MUI and Zustand.
- **Contracts:** `contracts/openapi.json` and `contracts/intent_vocabulary.json`.

## API surface

Most routes are grouped under `/scenes/{scene_id}`. Criteria fit is the exception: it takes the facts in the request and does not attach them to a scene. The ones that matter for the register direction:

| Route | Purpose |
|---|---|
| `POST /scenes/{id}/run` | Run the scenario |
| `POST /scenes/{id}/scenario/compare`, `/scenario/evaluate` | Compare and evaluate alternatives |
| `GET /scenes/{id}/scenarios` | List saved scenarios |
| `GET /scenes/{id}/ledger` | Storage ledger for the run |
| `GET /scenes/{id}/parameter-card` | Every assumption the run used, plus what is unknown |
| `POST /declarations/intake` | Broad-brush government-criteria fit for the facts you send. Does not store a declaration. Not a statutory determination |
| `GET /scenes/{id}/sea-level`, `/heat-field`, `/ventilation/corridors` | Individual hazard layers |
| `GET/POST /scenes/{id}/pins`, `/pins/{feature_id}/pin` | Pin and unpin features across runs |
| `POST /chat`, `/chat/stream` | Grounded chat over a run |
| `/plans/{plan_id}` and `/plans/{plan_id}/interventions` | Persisted plans and interventions |

## Running locally

Backend (port 8000):

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python scripts/preflight.py   # checks the environment
uvicorn app.main:app --reload
```

Frontend (port 5173, sends `/api` and `/static` requests to the backend):

```bash
cd frontend
npm ci
cp .env.local.example .env.local
npm run dev
```

## Deployment

Two services, because the API cannot run on a serverless host. The unzipped Python dependency set is ~265 MB against
Vercel Functions' 250 MB package limit, and the file store writes rasters to disk between requests. So the frontend is
static and the backend is a container-backed web app.

| Piece | Host | Config |
|---|---|---|
| Frontend | Vercel, built from the repo root | `vercel.json`, `.vercelignore` |
| Backend | Azure App Service (Linux, Python 3.13, B1) | `scripts/deploy_azure.sh`, `backend/startup.sh` |

The frontend build runs from the repository root, not `frontend/`, because `frontend/src/api/intentVocabulary.test.ts`
imports `contracts/intent_vocabulary.json` from the root. `.vercelignore` keeps the ~476 MB of 3D tiles out of the
upload.

Deploy the API:

```bash
brew install azure-cli && az login
LOCATION=italynorth PLAN_NAME=<your-plan> bash scripts/deploy_azure.sh
SKIP_ASSETS=1 bash scripts/deploy_azure.sh   # code-only redeploy; tiles stay on /home
```

Point the frontend at it, then redeploy:

```bash
vercel env add VITE_API_BASE_URL production   # https://<app>.azurewebsites.net/api
vercel deploy --prod
```

That value needs the `/api` suffix. The default is same-origin `/api` because the Vite dev server proxies it, so a bare
origin produces `404`s on every request — the app reports "Could not load the scene".

Three things `backend/startup.sh` handles that are easy to get wrong on this host, each of which produced a failed
deploy first:

- Dependencies are installed into `antenv`, and a custom startup command does not get it on `PATH`. It is sourced
  explicitly; without that, `uvicorn` is not found.
- With build automation on, the code is extracted to `/tmp`, which is ephemeral. `DATA_DIR` and `MODEL_DIR` are pinned
  to `/home` (10 GB on B1) and seeded additively behind a marker, so generated overlays survive a redeploy.
- `app/main.py` mounts `/static/model` only if the directory exists at import time. The directory is created before
  `uvicorn` starts and the 476 MB copy runs detached, or the mount is silently skipped and every tile 404s.

Region: App Service is `italynorth`. An Azure for Students subscription carries a policy permitting only five regions,
and appears to carry zero App Service quota in all but Italy North — `francecentral` and `germanywestcentral` reject a
B1 plan outright. Expect ~200 ms latency from Hong Kong.

`render.yaml` is an unused alternative that deploys the API to Render's free plan; it is kept because the free plan
needs no card, but it is not the live deployment, and its filesystem is ephemeral.

## Configuration

- `backend/.env`: the chat model is optional. Set `ANTHROPIC_API_KEY`, or point `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` at an OpenAI-compatible endpoint. Without a model, chat falls back to template answers that are labelled as such.
- `frontend/.env.local`: `VITE_CESIUM_ION_TOKEN` is optional. `VITE_API_BASE_URL` and `VITE_SCENE_ID` override the defaults.

## Layout

```
backend/app/       API: routers, services, schemas, chat agent
backend/scripts/   data preparation (DEM, land cover, heat, wet grid, buildings, seeding)
backend/data/      scenes, plans, rasters and other generated data, served at /static
backend/model/     3D models (city tiles, terrain, station, park)
backend/tests/     pytest suite
frontend/src/      viewer, panels and state
frontend/scripts/  end-to-end verification scripts (npm run verify:*)
scripts/           deploy_azure.sh, the API deploy
backend/startup.sh Azure startup command (venv, persistent dirs, tile seed)
vercel.json        frontend build, run from the repo root
```

## Checks

```bash
cd backend && pytest
cd frontend && npx tsc --noEmit && npm run lint && npm test && npm run build
```

CI runs the same checks (`.github/workflows/ci.yml`) on Node.js 24 actions. The contract job also runs `oasdiff breaking` against the base `contracts/openapi.json`.

## Limitations

- One study window (43.5 ha in HSK/HT). Not district-wide.
- Screening-grade: simplified hydrology, no piped network, no calibrated hydraulics.
- Some land-cover and soil inputs are estimated rather than surveyed; the parameter card says which.
- Single-tenant file store. It will not survive a second concurrent customer.
- Planned projects can be toggled, but construction phasing and overlapping timelines are not yet modelled.
- Criteria fit uses the facts you type and the thresholds in `backend/data/reference/hk_screening_thresholds.json`. It does not decide a permit or a planning permission. Hung Shui Kiu–Ha Tsuen is named as plan S/HSK/4 only; the zone notes and any Deep Bay overlap were not read.
- The panel does not store a declaration. A dated declaration record is still unbuilt.
- The live instance runs one worker against a file store, with no authentication and no tenancy boundary. It is a demo, not a deployment: anything a visitor generates is written to the same store a visitor reads from.

## Licence and attribution

Built for Hack4SDG 2026 by Team 1007: Leung Hoi Tung Bernice, Fang Yi Zhou Edwin, Chen Xu, Chloe Chik, Chu Ka Wai Katie.
Outputs are screening estimates and are not a statutory environmental assessment.
