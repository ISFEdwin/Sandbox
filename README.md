# Sandbox — cumulative screening for coordinated developments

A 3D planning sandbox for Hung Shui Kiu / Ha Tsuen (HSK/HT) in the Northern Metropolis. Place the developments that are
actually planned for a district, turn them on and off, swap one for another, change rainfall and temperature, and see
what each combination does to flood storage and surface heat — in seconds, before a design is fixed.

The prototype was built for Hack4SDG (Team 1007). It is now being taken forward as **a coordination register**: the
shared, dated record of what each project in a district assumed about its neighbours.

> **Status:** prototype complete and running; the register capabilities are not built yet.
> See [STATUS.md](STATUS.md) for what exists today and [TODO.md](TODO.md) for what comes next.

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

- **Toggle projects.** The planned projects for the area, with real footprints, switched on and off in combination.
- **Swap and compare.** Change the set of projects in the scenario and compare the resulting flood deficit and heat
  field against the previous run.
- **Add environmental variables.** Rainfall intensity and duration, surface temperature, sea level, ventilation. The
  parameter card publishes every assumption a run used, including what the model does not know.
- **Attribute, don't grade.** Three axes — drainage volume, surface temperature, wind geometry — reported separately.
  There is deliberately no combined score, and no pass/fail verdict.

Screening only. It sits in front of the statutory hydraulic assessment; it does not replace it, and every output is
labelled as derived rather than certified.

## Who it is for

| Role | What they do |
|---|---|
| District coordinator (public sector) | Holds the register for one development area; sees the cumulative picture across all projects and phases |
| Developer | Declares their project's massing, drainage and phasing; receives a dated statement of what they inherited versus what they caused |
| Consultant / QP | Prepares and submits the declaration on the developer's behalf |

How this is paid for — licensing structure, tier boundaries and the tariff route — is documented in the internal
planning notes rather than here, because this repository is public.

## Features

- **3D sandbox:** terrain and buildings in Cesium, in textured 3D or 2.5D massing, with buttons for tilt, orbit, zoom, top-down and north-up.
- **Overlays:** flood (wet grid) and heat layers you can switch on and off.
- **Scenario inputs:** rainfall intensity, duration and surface temperature sliders feed each run.
- **Project catalog:** planned projects with real footprints. Selecting several scores their combined effect. The backend refuses a run that reworks more than 40% of the study area.
- **Interventions:** describe one in the chat (for example, a park or a retention pond). It shows up as a draft, and you confirm it before it is placed. A details card asks for each value the run uses, and you either enter your own or let the AI estimate it. Estimated values are labelled as such.
- **Grounded chat:** ask about a run and get a structured answer card covering what the run shows, what to do, confidence and caveats. Every number in it is checked against the run's outputs.
- **Stats and parameter card:** a live summary after each run, plus a reference table of the run's assumptions, including what the model doesn't know.
- **LLM settings:** set the provider, base URL and model in the app. The API key is never shown back.

## User flow

1. Open the app. The HSK/HT scene loads and the camera frames the study area.
2. Turn on the Flood or Heat overlay to see the baseline.
3. Pick projects from the catalog, add interventions through the chat, or both.
4. Set the sliders and press **Run**.
5. Read the stats panel, then ask the chat why the numbers changed or what to try next.
6. Adjust or delete interventions in the Interventions panel and run again to compare.

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

Routes are grouped under `/scenes/{scene_id}`. The ones that matter for the register direction:

| Route | Purpose |
|---|---|
| `POST /scenes/{id}/run` | Run the scenario |
| `POST /scenes/{id}/scenario/compare`, `/scenario/evaluate` | Compare and evaluate alternatives |
| `GET /scenes/{id}/scenarios` | List saved scenarios |
| `GET /scenes/{id}/ledger` | Storage ledger for the run |
| `GET /scenes/{id}/parameter-card` | Every assumption the run used, plus what is unknown |
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
```

## Checks

```bash
cd backend && pytest
cd frontend && npx tsc --noEmit && npm run lint && npm test && npm run build
```

CI runs the same checks (`.github/workflows/ci.yml`).

## Limitations

- One study window (43.5 ha in HSK/HT). Not district-wide.
- Screening-grade: simplified hydrology, no piped network, no calibrated hydraulics.
- Some land-cover and soil inputs are estimated rather than surveyed; the parameter card says which.
- Single-tenant file store. It will not survive a second concurrent customer.
- Planned projects can be toggled, but construction phasing and overlapping timelines are not yet modelled.

## Licence and attribution

Built for Hack4SDG 2026 by Team 1007: Leung Hoi Tung Bernice, Fang Yi Zhou Edwin, Chen Xu, Chloe Chik, Chu Ka Wai Katie.
Outputs are screening estimates and are not a statutory environmental assessment.
