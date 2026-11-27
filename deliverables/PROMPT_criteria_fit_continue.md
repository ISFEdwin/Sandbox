# Prompt — make the criteria fit visible, and finish only what is still open

Copy everything between the two `===` lines into a fresh agent session.

===

Work in `/Users/edwin/Desktop/Coding/Projects/Hack4sdg/T1`. The repo root is `T1`, not the parent `Hack4sdg` folder. Date: 24 November 2026, Hong Kong SAR. Do not ask clarifying questions. Do not redo the statutory research. Do not create another research note. Do not commit unless asked.

The product is a quick, broad-brush sandbox. Do not reframe it as a coordination register, a certified model, or a combined score. The fit stays a **broad-brush fit read, not a statutory determination**. Every fit result keeps the screening label `BROAD_BRUSH_FIT_READ_NOT_A_STATUTORY_DETERMINATION`, `notADetermination: true`, a non-empty assumption register, and a non-empty `furtherInformation` list. A missing fact is stated. It is not guessed. F5 still holds: no deck may call this a shipped statutory screening decision.

The working tree is dirty with unrelated wind, OpenFOAM, comparison, and site-wind work. Touch only the files this prompt names. Leave those other diffs unstaged. `frontend/src/App.tsx` already contains both `GovernmentFitPanel` and `WindCompass`; keep the compass and the wind toggle that turns on 2.5D massing.

## Where the fit stands

Shipped on `main` as `2af10d6` (24 Nov the wind work is still uncommitted on top of that commit):

| Piece | Where | What it does |
|---|---|---|
| Thresholds | `backend/data/reference/hk_screening_thresholds.json` | Runtime source of the figures. Repealed tests stay in the file and must not fire. Drift guard: `assert_no_superseded_value_is_live`. |
| Service | `backend/app/services/government_fit.py` | `government_fit`, `declaration_intake`, `render_screening_basis_annex`. Reads the JSON on each call. Does not hardcode 50 / 20 / 100000 / 2000 / 15000. |
| Wire | `backend/app/schemas/government_fit.py` | CamelCase `WireModel`. `GovernmentFit` rejects a dropped label or an empty assumptions / furtherInformation list. |
| Route | `POST /api/declarations/intake` in `backend/app/routers/declarations.py`, mounted from `backend/app/main.py` | Returns `governmentFit` and `screeningBasisAnnex`. Does not store a declaration. A1 is still open. |
| Contract | `contracts/openapi.json` | The committed contract has `/api/declarations/intake` and does not describe `directionWeights`. The dirty working copy of that file may. Do not regenerate the contract from the dirty Python tree. |
| Tests | `backend/tests/test_government_fit.py` (24), `frontend/src/api/governmentFit.test.ts` (9) | Strict >50 ha, exact 50 does not trigger, 30% of this district is not 50 ha, conflicting site area vs fraction is `insufficient_facts`, A.1 from class alone, local distributor does not fire, repealed bundle does not fire, missing distance is further information, label cannot be dropped. |
| Docs | `docs/GOVERNMENT_CRITERIA_FIT.md`, `docs/CODE_OF_PRACTICE.md`, `docs/SCREENING_BASIS_ANNEX.md` | G1, G5, G6. A4's other sections and B5's other templates stay open. |
| Panel | `frontend/src/components/GovernmentFitPanel.tsx`, client in `frontend/src/api/governmentFit.ts` | Collapsed HUD panel. Blank fields are omitted. Share of district is entered as a percent and sent as `coverageFraction`. |

`TODO.md` section G: G1, G2, G3, G5, G6 are met. G4, G7, G8, G9 are open. Do not rewrite sections A–F. Do not check a G box you have not actually finished.

Settled tests, already encoded. Do not reopen them:

- Two gates. A current section 16 permission is not an environmental permit. The screen does not find a section 9 or section 26 contravention.
- Schedule 3 is urban development or redevelopment **more than 50 ha** only. Exactly 50 ha does not trigger. The 20 ha test, the 100,000-population test, and the engineering-feasibility wording are repealed.
- Schedule 2: A.1 is road class only (expressway, trunk, primary distributor, district distributor), no length. Local distributor does not fire. C.1 >5 ha. C.2 is >1 ha AND a distance limb. C.12 is a separate dredging test. F.1 >15,000 m³/day. F.2 is >5,000 m³/day AND <200 m. I.1 is width >100 m OR <300 m from a named area. P.1 is residential or recreational inside Deep Bay Buffer Zone 1 or 2, NTEH excepted, no size threshold. P.2 is repealed. Q.1 exemptions stay with EPD. Q.2 is a portal <100 m.
- Section 4(4) may flag a possible specification. `assertedAggregation` stays false.
- Town planning column comes only from a supplied OZP column. HKPSG Chapter 9 is advisory, `passFail` always false. 20/10/5 m is open-space separation, never a residential buffer.
- Hung Shui Kiu–Ha Tsuen is plan identity only: S/HSK/4, approved 29 September 2026, gazetted 9 October 2026. Do not assert a zone column or a Deep Bay intersection.

## What is wrong on screen

The panel is mounted, and there are no conflict markers left in the tree. It still does not read as part of the sandbox:

1. In `frontend/src/App.tsx` it sits at the bottom of the 330px right column, after the sliders, the catalog, the comparison, the gauge, the storm, the interventions, and the stats. The column already fills the viewport, so the fit is below the fold.
2. It opens closed (`useState(false)`), behind a Show button, so a user who does scroll there still sees a title and one sentence.
3. Once open it is a statutory form: about twelve fields before a disclosure, then about twenty more (sewage, channel, reclamation, permission date, sensitive area, rock cavern, EA triggers, rail, NEF 25). The answer is a second card of flag rows plus a scrolling "Still unknown" list that repeats standing gaps even when the user typed two facts.
4. The title-row headline is 9px. In the 330px column it is the first thing that clips.

Match the existing HUD: `HudPanel`, the colours in `frontend/src/theme.ts` (green `#5cff9d`, cyan `#3fe0ff`, amber `#ff9d2e`), uppercase mono labels, tabular numbers. Stay on MUI components the app already imports (`Box`, `Button`, `Stack`, `Typography`, `Alert`). Do not add a new MUI package import; Vite re-optimises deps and can drop the dev server. A native `<select>` is already the pattern in this panel.

Verify in the browser on the running app (Vite `5173`, API `8000`) before calling the UI done. Open the column, read a fit, and confirm the new card is visible without hunting. A screenshot of a closed panel is not verification.

## The four rules the simulation is aiming at

This is the table to put on screen. It is the aim of the sandbox, not a compliance result.

| Rule | Set by | What Sandbox will screen |
|---|---|---|
| Air Ventilation Assessment | Technical Circular 1/06 | Wind paths, comparing layout options |
| Sustainable Building Design Guidelines | Buildings Department, PNAP APP-152 | Building separation, setback, site greenery |
| Drainage Impact Assessment | Drainage Services Department | Runoff and flood storage |
| Environmental Impact Assessment | EPD, EIA Ordinance (Cap. 499) | Cumulative effects with neighbouring projects |

`docs/GOVERNMENT_CRITERIA_FIT.md` already draws the line. Keep it.

- **AVA.** The comparison and the wind channel compare layout options as geometry under the study-window inflow. Technical Circular 1/06 defines a velocity ratio from pedestrian test points. This screen does not hold those points. Site and local velocity ratios stay empty. Frontal area and the coarse channel are not a velocity ratio. The row can say which wind paths were compared. It cannot say an AVA passed.
- **SBDG / PNAP APP-152.** Not applied. Greenery may already appear as its own comparison row, in its own units. Separation and setback are not checked. The row names the three checks and says they are not a concession test. Do not invent APP-152 thresholds. B5's SBDG template stays open. Do not close it in this pass.
- **Drainage.** The storm and the drainage ledger screen runoff and flood storage for the schemes on the table. That volume is not an installed sewage capacity and not a Drainage Impact Assessment. EIAO F.1, F.2, I.1, and C.12 fire only from facts the user typed into the fit, read from the threshold file.
- **EIA / Cap. 499.** This is the fit that already exists: Schedule 2 and Schedule 3 flags from typed facts, section 4(4) only when the user says the projects are contiguous and by the same or associated persons, and the data-collection list of neighbours. Neighbours on the map are not a cumulative-impact finding under the Technical Memorandum. Do not score one.

## What to build

Replace the panel the user sees first. The first view is four short rows, one per rule above, inside the existing Criteria fit `HudPanel`. Each row is: the rule, who set it, what this sandbox is screening, and one limit sentence. No paragraph under every field. No second form above the fold.

Move the current fact form behind one control, labelled so a blank stays blank, for the Cap. 499 row only. Keep `buildIntake` / `postIntake` / `fitIsLabelled`. Do not send a blank. Do not drop the label check. After **Read fit**, the EIA row updates from `governmentFit` (Schedule 3, Schedule 2 item codes, town planning, section 4(4)). Put assumptions, the annex, and the unknowns list behind the controls that already exist. The standing unknowns should not occupy the panel until the user asks.

Place the panel where a reviewer will see it: with the comparison, above the storm and the stats, still inside the same scrolling column. Keep the parameter card collapsed beneath it. The fit panel itself should be readable closed: the four rows are the closed state. "Show" may open the fact form, not the whole point of the panel.

Pull live figures only from APIs the app already calls for the scene (`VITE_SCENE_ID`): the comparison rows for wind and drainage, and the parameter card where it already states an assumption. If a figure is absent, the row says it is not held. Do not call a new solver, do not compute a velocity ratio, and do not add a combined score.

## What is left of section G, and the limit of this pass

- **G4.** The HKPSG check is already in the fit object, and a missing receiver distance is already `furtherInformation`. Do not add a map layer in this pass. One line on the EIA row, "HKPSG noise, check only", is enough. Leave the checkbox open.
- **G7.** Do not copy statutory clause texts into the repo, and do not re-download the ordinances. If you touch the threshold file, only fill a missing source URL or effective date that is already in `docs/GOVERNMENT_CRITERIA_FIT.md` or `01_research/HK_Government_Screening_Criteria_Urban_Planning.md`. Leave the checkbox open.
- **G8.** Do not read the OZP Notes, do not assert Deep Bay, and do not shrink `furtherInformation` by assumption. Leave the checkbox open. G8 still comes before any site-specific HSK–HT claim.
- **G9.** Do not create a deck. If a deck file already exists in the repo, add one line to the approval-path slide: two gates, broad-brush fit read only. If it does not exist, leave the checkbox open and do not invent the slide.

Update `TODO.md` only in section G and the government-criteria overlay line, and only to describe the panel the user can now see. Update the panel row in `STATUS.md` §10 and the Criteria fit bullets in `README.md` so they describe the four rows. Do not claim AVA, SBDG, DIA, or EIA compliance. Do not "correct" the stale branch hash in the STATUS header.

## Tests

Extend `frontend/src/api/governmentFit.test.ts` only if the intake payload changes. Add a component test only if the project already tests components; otherwise the browser pass is the check. Re-run `backend/tests/test_government_fit.py` and the frontend fit tests. Do not regenerate `contracts/openapi.json` unless the wire schema changes, and then only from `backend/.venv313` after the unrelated service files are not on the import path. A dict body that drops the request schema is not an acceptable way to silence the existing Pydantic alias warnings.

## Done when

- On a desktop viewport the four rows are visible in the right column without scrolling past the storm.
- Typing 60 ha and trunk, then Read fit, shows Schedule 3 **Review** and Schedule 2 **A.1**, the label, and plan S/HSK/4, with the long unknowns list closed until asked.
- An empty read still returns a labelled fit and does not say the site is inside Deep Bay.
- AVA does not show a velocity ratio. SBDG does not show a pass. Drainage does not show the deficit as a sewage capacity. EIA does not show a cumulative-impact finding.
- G4, G7, G8, G9 remain unchecked. A–F are unchanged. Unrelated wind files are still unstaged.

===
