---
name: Competition entry essentials
overview: Ground truth is the five edges in STATUS.md. Comparison leads, natural-language intervention is a core feature already built, and the wind channel is the axis still off the map. The register is the side effect of holding the schemes.
todos:
  - id: nlp-intervention
    content: Keep natural-language intervention in the demo path. A sentence places a grounded draft, confirm scores it, and the comparison moves. The feature is already built in intent.py and ai_plan.py.
    status: completed
  - id: comparison-board
    content: Put two schemes side by side on separate axes — drainage, heat, tide, greenery, wind corridor — with no combined score.
    status: completed
  - id: wind-channel
    content: Draw the existing prevailing-wind corridor on the map and show it change when a scheme is toggled; keep it labelled as geometry, not a velocity ratio.
    status: completed
  - id: wind-diagnostic
    content: If the corridor line is too thin, add a Röckle-style diagnostic speed field as a sidecar, using CSDI site wind as the inflow and URock or pyqes only as a check, not as vendored code.
    status: completed
  - id: deck-thesis
    content: Retitle the next deck so comparison is the product and the register is what falls out of holding everyone’s plans. Deck v2 currently does the reverse.
    status: completed
  - id: storm-playback
    content: Put the existing hourly storm on the map as a playhead, using a named hyetograph (hko_2023_09_07), with the screening label kept on screen.
    status: completed
  - id: live-gauge
    content: Drive rainfall and tide from a labelled HKO open-data feed or a recorded trace, so the IoT claim is a re-runnable input rather than a slide.
    status: completed
  - id: sensitivity-strip
    content: Add one on-screen sensitivity control (curve number or rainfall ±20%) that re-runs the ledger and shows which assumption moves the deficit.
    status: completed
isProject: false
---

# Comparison first, then the demo that proves it

Ground truth for the product edges is the table at the top of [STATUS.md](STATUS.md), dated 18 Nov 2026. [README.md](README.md) matches it. [PLAN.md](PLAN.md) is the design for the shared record that follows, and its opening now says so.

The five edges:

1. **Comparison across separate axes** — drainage, surface heat, tide, greenery, wind channel. No combined score.
2. **A shared picture follows from holding the schemes.** The coordination register is that side effect.
3. **Natural-language intervention**, and it is a core feature, already built. "Add a retention pond in the north" is classified in [backend/app/agent/intent.py](backend/app/agent/intent.py) and placed by [backend/app/services/ai_plan.py](backend/app/services/ai_plan.py) onto a site taken from the terrain, land cover and flood grid. The draft is confirmed before the comparison scores it. A height or density sentence goes to the massing tool with an explicit scope. The demo path includes one of these sentences, so the comparison moves because of something the judge just said.
4. **Wind channel** as a comparison axis. Draw the corridor that already exists. A diagnostic speed field only if that line is too thin. Cite the CSDI inflow. Leave CFD out.
5. **Screening, labelled.** The parameter card and the grounded chat already do this.

The product is a broad-brush comparison tool. Load the schemes already on the table and read, on separate axes, what each combination does to flood storage, surface heat, tide, greenery, and the wind channel. Because those schemes sit in one place, a district record of what each project assumed about its neighbours falls out. That record is a side effect. It is not the headline.

Deck v2 says the opposite. The title slide of [04_submission/deck/build_pitch_deck.py](../../04_submission/deck/build_pitch_deck.py) reads “The coordination register for the Northern Metropolis,” and comparison appears later as a feature bullet (“Swap layouts and compare three hazard axes”). The next deck leads with the comparison. The register sentence moves to a consequence: the tool already holds everyone’s plans, so the comparison is also a shared picture.

[PLAN.md](PLAN.md) §3.6 decided against a wind solver because a full CFD solve would not be defensible arithmetic and would not earn an AVA verdict. That decision still holds for OpenFOAM-class simulation. It does not hold for a broad-brush wind channel: the corridor geometry is already computed, and a diagnostic speed field is a comparison, not an assessment.

## What a judge should be able to compare

Each axis stays in its own units. No combined score, no pass/fail.

- Drainage deficit and flood extent. On screen today, as one run’s stats, not as scheme A against scheme B.
- Surface heat. On screen the same way.
- Tide and tailwater. The run already returns it; the comparison view does not.
- Greenery and impervious share. Returned on the stats object and by `/design-metrics`. Show the delta. Do not turn it into an SBDG certificate.
- Wind channel under the published prevailing inflow (NE / ENE / E). Computed by the least-cost corridor in [backend/app/services/ventilation.py](backend/app/services/ventilation.py) and served at `/ventilation/corridors`. Not drawn.

`POST /scenario/compare` already ranks whole scenarios. The demo needs that comparison on the map: two toggled sets, five rows, the row that moved.

## Wind channel — what exists, and what is worth adding

Frontal area density cannot tell a north-easterly from a south-westerly. That symmetry is the metric, and [ventilation.py](backend/app/services/ventilation.py) already says so. The arrangement metric does tell them apart: on the committed site, mean first-obstruction height is 15.33 m from the north-east and 8.88 m from the south-west. The corridor walker is the Hong Kong screening method in miniature — frontal area as friction, least-cost path as the channel — the same idea as Wong, Nichol and Ng’s frontal-area-index maps for Hong Kong. It is the right first wind feature because it is already tested and it changes when massing changes.

A speed field is the step after that, and only if the drawn corridor is too thin to carry the demo. Three open-source models were checked. All of them are diagnostic or mass-conserving. None of them is a wind-tunnel AVA.

- **URock 2023a** (Bernard, Lindberg, Oswald, Geosci. Model Dev.). GIS wind field from 2.5D building and vegetation heights. It implements the Röckle (1990) zones: displacement on the windward face, a wake on the leeward face, street-canyon adjustment, then a mass balance. A forced north-easterly inflow produces a different speed map from a south-westerly, which is the symmetry frontal area density cannot break. It ships inside UMEP as a QGIS/Python plugin and needs Java. Licence is GPL, same family as QGIS. Use it as a reference run on one fixture. Do not import it into the FastAPI process.
- **QES-Winds**, and the `pyqes` wheels (GPL-3, CPU wheels include macOS arm64; CUDA is optional). Same family as QUIC-URB: an initial empirical wind field, then a fast mass-conserving solve. It can export a GeoTIFF and streamlines. It is the right tool if a pilot later wants a 3D field at roughly 2 m. It is the wrong dependency for a December demo: a C++/CUDA stack, a GPL boundary, and more resolution than the 5 m screening grid can support.
- **OpenFOAM or a wind-tunnel-style CFD.** Still out. Resolution, calibration, and liability are the reasons in [PLAN.md](PLAN.md) §3.6, and they are unchanged. A district solve at 5 m would look more precise than the massing is.

The inflow should be cited, not invented. Planning Department Site Wind Availability Data on CSDI (dataset `pland_rcd_1634281652589_43389`) publishes speeds, frequencies, and directions by height and season from their own CFD and wind-tunnel work. [PLAN.md](PLAN.md) §12.1 already asks for that file at `backend/data/reference/hsk_site_wind.json`. Use it as the boundary condition for the channel. Keep reporting our own number as a screening delta against that inflow, not as a second CFD.

Implementation, in order:

1. Draw the existing corridor for NE, ENE, and E on the flood/massing view. Toggle a project and show the path and the first-obstruction height move. Label it geometry, not a velocity ratio. The screening sentence already in `ventilation.py` stays on the panel.
2. Only if that line does not read as a channel in the pitch: a small NumPy diagnostic on the height raster already in memory — a leeward wake and a street-canyon slowdown under one inflow direction — returning a speed-ratio map and a single district mean. Check one case against a URock or `pyqes` run kept outside the repo. Ship the check as a test fixture, not the GPL source.
3. Fetch the CSDI wind table into the reference file and drive the inflow direction and the frequency weights from it, replacing the single AVRG73 fact (NE/ENE/E, 40.8%).

## Supporting demo moments

These still earn their place once the comparison is on screen. They are not a substitute for it.

- **Storm playback.** `GET /drainage/hourly` already steps `hko_2023_09_07`. Nothing in the frontend calls it, and Cesium is created with `animation: false`. A playhead makes the flood comparison move. The frame keeps the line that this is not a flood prediction and that the drainage rate is the DSD design standard.
- **A live gauge.** Rainfall and tide are typed. One labelled Hong Kong Observatory reading, or a recorded trace of the same feed, written into the env params the Run button already sends. The stats panel names the source and the time. That is the IoT claim a Huawei re-run can actually execute. Point the existing OpenAI-compatible chat at a Huawei Cloud endpoint; leave the grounding checks as they are.
- **One sensitivity knob.** Curve number or rainfall at ±20%, three ledger deficits, one sentence on which assumption moved. This is what makes the comparison look like a model.

## What stays out

- A combined risk score or a pass/fail badge.
- A pipe network, invented sensors, or an OpenFOAM solve.
- Vendoring URock or QES into this repository. Both are GPL-3. A sidecar or a fixture is the boundary.
- Declarations, roles, tenancy, phasing, and regulatory templates. Those remain [PLAN.md](PLAN.md) Waves 1–6. They describe the register that appears once many parties are comparing in the same model. They are not the demo.

## Order

Comparison board, then the wind corridor on it, then playback and the gauge, then the sensitivity strip. The deck title changes with the board, so the December pitch and the slides describe the same product. The 29 November DeepTech form is still a deck; this is what that deck and the Huawei video should show.
