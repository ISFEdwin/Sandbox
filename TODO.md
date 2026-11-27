# TODO — deliverables from here

The product edges live in [STATUS.md](STATUS.md) (18 Nov 2026): comparison across separate axes, the shared picture as a side effect of holding the schemes, natural-language intervention, the wind channel, and labelled screening. This file is the checklist. It is not the definition of the product.

The same items are tracked on the team board, <https://trello.com/b/Bz0W639T/sandbox> — Done, Pending, Blocked and To Do. The board is a view of this file, updated on 26 Nov 2026; if the two disagree, this file wins and the board is stale.

Ordered by when it must be done, not by how interesting it is. `[P0]` = the pathway stalls without it.
Update as items close; move the reason (not just the tick) into [STATUS.md](STATUS.md) when a capability lands.

---

## A. Now → 15 Dec 2026

The next four weeks decide whether this is a pilot or a slide deck.

- [ ] **A1 `[P0]` Land one real declaration.** A real developer's massing, drainage assumptions and phasing entered
      into the sandbox, alongside at least one real neighbour already in the baseline.
      *Done when:* a report exists for a real site showing what the project inherited and what it caused.
      *Why:* this single artefact replaces the demo in every conversation — with a funder, a coordinator and a
      developer. Nothing else on this list matters if it does not happen.
      *Unblocked today:* the coverage guard no longer refuses a declared project for being large
      (`app/services/consent.py`), so a 30%-of-district declaration is applied and flagged rather than dropped.
      **Blocked in practice by ingestion (26 Nov 2026).** "Entered into the sandbox" currently means editing
      `backend/data/projects/<id>.json` in this repository and re-running `scripts/seed_projects.py`. H1 is the
      route that makes A1 a data entry rather than a commit; the spec is `docs/PROJECT_IMPORT.md`.

- [ ] **A2 `[P0]` Define attribution, in writing, then in code.** Exactly what counts as "inherited" versus "caused":
      baseline state, neighbour contributions, phase timing, rounding, and how the split is reported when it does not sum
      cleanly.
      *Done when:* a short spec exists, an `attribution` object is in the schema, an endpoint returns a split that
      reconciles to the total, and there is a test for the reconciliation.
      *Why:* it is the product's central claim and it is currently undefined. See STATUS §7.1.
      **Partly done (14 Nov 2026).** The spec exists: `docs/ATTRIBUTION.md` — the three terms, the leave-one-out
      basis for "caused", the interaction term, and the axes that are *not* attributed per project. The code is not
      written. **B5 now needs a sign-off, not a definition.**

- [ ] **A2b `[P0]` Implement the attribution object.** The `attribution` schema, `POST /api/scenes/{id}/attribution`,
      and `tests/test_attribution.py::test_attribution_reconciles_to_the_total` asserting
      `Σ caused + interaction == total effect` to 1e-9 m³. This is F5 in the build plan, and A1 is waiting on it.

- [x] **A3 `[P0]` Rewrite the deck's business section.** Superseded by a new 15-slide deck built from scratch on
      14 Nov 2026: problem → three failures → the three legal instruments → product → variables → where we come in
      the approval path → three axes → declaration/computation/record → three roles → licence bands → BEAM Plus and
      CORENET X precedent → market → competitive field → the ask.
      *Done when:* the deck states one thesis on one line, three roles, and one fee architecture with no internal
      contradictions. — **met.** The decks sit in the local, git-ignored `deliverables/` because they carry the fee
      schedule; `deliverables/*.pptx` is excluded for that reason.

- [ ] **A3b `[P1]` Governance slide.** The new deck covers the precedent slide; it still needs the Code of Practice
      and governance slide, which depends on A4.

- [ ] **A4 `[P0]` Code of Practice v0.1.** Inputs required, size bands, disclosure rules, what a declaration asserts,
      and the dispute path. Ten pages, not fifty.
      *Done when:* a project office could attach it to a contract without asking you what it means.
      *Now has something to reference:* the attribution definitions in `docs/ATTRIBUTION.md` are the section the Code
      of Practice will point at, so A4 is less of a blank page than it was.

- [ ] **A5 `[P0]` Incorporate and name two full-time people.** Company by shares, founder holding ≥51%.
      *Done when:* incorporation certificate plus two named FTEs.
      *Why:* gates incubatee status, which gates PSTS. Structural, not commercial.

- [ ] **A6 `[P0]` Cyberport application — deadline 1 Dec 2026.** ⚠️ **Corrected 18 Nov:** this is almost certainly the
      **CCMF Hong Kong Programme** (Feb 2027 intake, deadline 1 Dec 2026, HK$100k no-equity grant), not the Incubation
      Programme — CIP's Oct 2026 intake closed 3 Aug 2026. Confirm on the Cyberport portal, but prepare CCMF:
      15-slide deck + 6-month milestone plan + line-item HK$100k budget + 3-month time-to-market + a
      social-responsibility paragraph. Gap analysis in [STATUS.md](STATUS.md) §9.2.

- [x] **A7 `[P1]` Resolve the working tree.** `contracts/openapi.json` is modified and uncommitted. Either commit with a
      reason or revert. A drifting contract file will bite the register work in B1.
      **Met (14 Nov 2026).** Committed under the pinned pydantic: the file had been rendered under 2.9.2, which
      renders a `dict[str, Any]` field without `"additionalProperties"`. All 62 added lines were that one key — no
      route, schema or field changed. `app/export_openapi.py` now refuses to render off-pin.

- [x] **A8 `[P1]` Run the test suites and record the result in STATUS.** No pass count goes into any document until it
      has been run in that session.
      **Met (14 Nov 2026).** Recorded in STATUS §2.1: 256 pytest checks and 27 CI-style suites, all green; frontend
      111 tests, clean typecheck, lint and build. Two environment defects had to be fixed first — the suites were
      booting from the machine's runtime residue and its live model settings rather than from the repository.

---

## B. Q1 2027 — make it a register, not a sandbox

Two months of engineering that is invisible in a demo and decisive in a pilot.

- [ ] **B1 `[P0]` Multi-tenant store.** Move off `STORE_MODE=file` to the PostGIS path that `config.py` already declares
      but `db.py` refuses to serve.
      *Done when:* two organisations use one instance with no data bleed, and the API contract is unchanged (ADR-020
      says store mode is configuration, so the contract must not move).
      *Note:* the tenancy carrier the plan depends on is the `declarationId` / `tenantId` marker, and
      `app/services/consent.py` now reads the first of those — so the seam exists before the store does.

- [ ] **B2 `[P0]` Authentication and four roles:** developer, QP/consultant, submission coordinator, agency.
      *Done when:* a declaration cannot be created by a party that is not entitled to create it.

- [ ] **B3 `[P0]` Declaration object with hash and timestamp.** The declared inputs, who signed, when, and an immutable
      digest.
      *Done when:* editing a declared project creates a new declaration rather than mutating the old one.

- [ ] **B4 `[P0]` Versioned baseline with "as at" queries.** The neighbour's design changes; the record must not silently
      change with it.
      *Done when:* a run can be reproduced against "the baseline as at 12 March 2027" and returns the same numbers.

- [ ] **B5 `[P0]` Regulatory output templates.** AVA-style SVR/LVR table; SBDG separation/setback/greenery check;
      an attribution annex in the shape EIAO TM §4.3.1(c)(iii) asks for.
      *Done when:* a consultant can paste the output into a submission and a reviewer can follow it.
      *Why:* this is the difference between a planning toy and a compliance tool.
      *Now has its definition:* the attribution annex is the decomposition in `docs/ATTRIBUTION.md`, in submission form.

- [ ] **B6 `[P1]` Temporal overlap / phasing.** Projects carry start and end dates; a run can express "my neighbour's
      phase 2 arrives in 2029, before my phase 1 completes".
      *Done when:* the phasing toggle changes a result, and the result says why.

- [ ] **B7 `[P1]` Agency review surface.** Comments anchored to a project, and an exportable written-direction record.

- [ ] **B8 `[P1]` Amendment / resubmission lifecycle.** Real schemes change; a register that cannot amend is a one-shot
      report.

- [ ] **B9 `[P1]` Tiered disclosure.** Aggregate visible to every participant; detailed massing and phasing visible only
      to the agency and the declaring party.
      *Done when:* a developer can be shown exactly who sees what, before they submit.

- [ ] **B10 `[P2]` Public read-only aggregate view.** Transparency is what makes the arrangement politically defensible.

- [ ] **B11 `[P2]` Wind as a geometry axis.** Currently partial; needed before any AVA-style claim is made.
      *Note:* the wind docstrings said two things that were not true and now do (396 surveyed footprints, and the
      symmetry being the metric's rather than the buildings'). Fixed 14 Nov 2026; the axis itself is still partial.
      23 Nov 2026: footprint bearing and principal-axis sides feed the projected width; NE ≡ SW in FAD stays, because
      the closed form is 180-degree periodic. NE ≠ SW is the directional-exposure march and the shelter rays. Corridor
      cost is still `1 + cellFAD`, plus a separate ground-level term and a separate land-class roughness penalty.
      Geometric effect labels are patterns, not speeds. No velocity ratio and no pass/fail.
      23 Nov 2026: the comparison board now carries a wind-channel option table under the
      window rose (NE / ENE / E). SVR and LVR stay null, because TC 1/06 Annex A defines
      them from pedestrian test points this screening does not hold. The coarse channel
      solve remains off the request path and is not re-solved per scheme.
      The east channel is a card on that board: annual, summer and winter frequencies
      and ranks for the four window cells, the centroid 10 m inlet, the solved
      streamline count, and the A/B first-obstruction and path length in metres.
      Draw E sets the compass to east. The axis is still partial.
      24 Nov 2026: the compass can set a 10 m speed, including the HKO Signal 3,
      8 and 10 onsets. Display traces fill the coarse channel. The heat field
      cools open cells more than sheltered cells at that speed, and the board
      has a surface-mean row in °C. The allowance is capped at 3 °C. SVR and
      LVR stay null. The corridor cost is still geometry.
      26 Nov 2026: the channel was re-solved at 8 m instead of 20 m, on the 396
      surveyed rings with a centre-or-majority test so a footprint is not grown
      by a cell on every side. Threads are seeded at 4, 12, 20, 36 and 52 m and
      every bearing now carries about 400 of them (NE was 92). The drawn threads
      are thinner, display traces sit underneath, and the polylines no longer
      use a depth-fail material: a thread behind a massing block is hidden, so
      the drawing reads as flow around the block rather than through it. The
      textured city model stays a separate 1,650-tile Draco mesh; voxelising it
      would need a Draco decoder and it is not the obstacle field the solver
      used, so the threads stay paired with the 2.5D footprints.

- [ ] **B12 `[P2]` Paid or local model id for the LLM path.** Rate limits in a paying session are a churn event.

---

## C. Q2–Q3 2027 — the institutional step

- [ ] **C1 `[P0]` PSTS-SPC application.** HK$1.0M cap, year-round, requires current incubatee status **and an
      authorised letter from the participating public-sector body.**
      *Done when:* the letter exists. Without it the application does not exist.

- [ ] **C2 `[P0]` One funded pilot with a public-sector body.** Ideally one NDA phase, not a whole district.
      *Done when:* a named public user is running the register, with a written intent to continue.

- [ ] **C3 `[P1]` District calibration playbook.** What it takes to stand up a second study area: soils, LST anchor,
      tide states, footprint provenance, register pre-fill.
      *Done when:* a second district can be calibrated without the original team.

- [ ] **C4 `[P1]` Governance body convened.** REDA, HKIP, HKIE, one project office. A vendor-written rulebook is not
      adopted; a co-signed one is.

- [ ] **C5 `[P2]` Techathon+ 11th edition — team and deck, 11 Jan 2027.** Use it to test the register framing on a
      judging panel before it meets a procurement officer.

---

## D. Research that unblocks decisions

- [ ] **D1 `[P0]` Count HK projects above the 20,000 m² SBDG threshold.** This single number decides whether the model
      is under-priced or under-covered. Building Department plan approvals, or a sample of OZP submissions.
- [ ] **D2 `[P0]` Verify Autodesk Forma has no flood or drainage capability** against Autodesk's own product page, not
      review sites. It is currently inferred from three third-party feature lists.
- [ ] **D3 `[P1]` Confirm the legal route for a developer-paid fee.** Can a private operator charge a mandatory fee, or
      must it be a schedule to a government contract, or a pass-through? This determines the whole revenue architecture.
- [ ] **D4 `[P1]` Confirm how BEAM Plus is levered** — the specific lease condition or practice note, not the general
      claim that land sale conditions reference it.
- [x] **D5 `[P0]` Which storm is the baseline design storm?** **Settled 14 Nov 2026: 50 mm.** The committed raster set
      is regenerated at it and `tests/test_artefact_drift.py` fails if the two ever disagree. The storm is now a
      *stated input* of every published figure, not an ambient default.
- [x] **D5′ `[P2]` The site wind regime.** Fetched 23 Nov 2026 from the Planning Department Site Wind Availability Data
      ([data.gov.hk](https://data.gov.hk/en-data/dataset/hk-pland-pland1-site-wind-availability-data),
      [index](https://www.pland.gov.hk/pland_en/resources/site_wind/open_data/site_wind_open_data.csv)).
      `backend/data/reference/hsk_site_wind.json` is `verified: true` for HK1980 grid cell **3463** (annual / summer /
      winter at 500, 300 and 200 m). The study-window centroid falls in that cell; the window itself also touches cells
      3462, 3559 and 3560. Those four annual 500 m roses are now area-weighted in
      `backend/data/reference/hsk_site_wind_window.json`. `directionWeights=window`
      selects the headline corridor from that merge and does not enter the cell cost.
      `directionWeights=site` is still cell 3463 alone. AVRG73's combined 40.8% NE/ENE/E fact stays in
      `hsk_ava_reference.json` and remains the default corridor weight. `site` and `window` select the headline
      corridor. Neither weight enters the cell cost. The same four cells now also carry summer and winter
      500 m frequencies and derived speeds in that window file (`seasons`). Annual east leads the sixteen
      directions (15.1%). Summer east ranks 7th, behind SSW. Winter east ranks 2nd, behind NE.
- [ ] **D6 `[P2]` The statutory clause texts.** EIAO TM and GN6/2010 into `backend/data/reference/`, plus
      `oasdiff breaking` in the CI contract job. **Partly started (23 Nov 2026):** the sentences the
      data-collection and wind-channel reads apply are in `backend/data/reference/regulatory_duties.json`,
      including GN 6/2023 §21 (GN 6/2010 §21 kept, not applied) and TC 1/06's comparison duty and VR
      definition. The rest of each instrument is not copied. `oasdiff breaking` v1.39.0 now runs in the
      CI contract job against the base `contracts/openapi.json`. G7 is still the wider extract.

---

## E. Standing hygiene

- [x] **E1** Full suite green before any pilot demo: `cd backend && pytest`, and the frontend checks in the README.
      **Green as of 14 Nov 2026** — 256 pytest checks, 27 CI-style suites, 111 frontend tests, clean typecheck, lint
      and build. It is standing, not closed: re-run it before a demo, and note that `pytest -q` alone does not cover
      the standalone suites (the CI-style loop is the runner CI uses).
- [ ] **E2** Every output keeps the screening label and the assumption register. It is not decoration — it is the
      liability architecture. If a commercial conversation asks to remove it, that is a no.
- [ ] **E3** No fee figures, competitor analysis or partner names in this repository. It is public.
- [ ] **E4** STATUS.md of §3 updated whenever a capability moves from "not built" to "built", with the evidence.
      *Moved 14 Nov 2026:* §3 rows 5, 8 and 10 now say "not built" but name what does exist — the consent seam, the
      attribution definition, the joint-review flag.
- [ ] **E5** The local store is a runtime store and may hold residue from hand-poking the API — on this machine, a
      staged scenario of 10 unconfirmed AI drafts, 7 of them pinned, claiming 37% of the district. The suites no longer
      inherit it; **the app does.** Clear it before the next demo on that machine.

---

## F. Competition entry gates — added 18 Nov 2026

These do not replace A–E. They are the *application* layer on top of it: what has to exist in the next few weeks for the
register thesis to survive a judging panel. Full dates and eligibility in
`02_planning/2026-27_entry_readiness_todo.md`; measured gaps in [STATUS.md](STATUS.md) §9.

- [ ] **F1 `[P0]` Lock a 4-person entry team by 22 Nov.** Deck v2 names five people. Four is the universal size:
      Techathon+ 2–6, Hult 2–4, Imagine Cup ≤4, IQC 1–4, IMC ≤5. Five disqualifies Hult and Imagine Cup.
- [ ] **F2 `[P0]` Write the CCMF milestone plan and HK$100k budget by 24 Nov.** Six months, three disbursement gates
      (10k / 45k / 45k), credible line items, explicit ≤3-month time-to-market, and a social-responsibility paragraph.
      This is the part the 15-slide deck does not contain.
      **Partly met (26 Nov 2026).** The final CCMF deck does carry three gates and a line-item budget; but the
      timeline footnote says a six-month project while the timeline table shows four calendar quarters, and slide 13
      puts launch in Q4. Reconcile before the 1 Dec form, or the milestone plan contradicts itself.
- [ ] **F3 `[P0]` Submit the two Cyberport forms.** GBA YEP Stage 1 by **27 Nov** (individual, cheap, keeps the option
      open — but Stage 2 needs a Guangdong/Macau teammate); CCMF HK by **1 Dec**. Pick one as primary; two applications
      for the same idea to one vetting committee reads badly.
- [ ] **F4 `[P0]` Protect Techathon+ eligibility.** Confirm the project has received no HKSTP funding and won no
      Gold/Silver/Bronze in the last three editions. Form the team on the portal and pick one AI+ track by 30 Nov;
      10–20 page deck by **11 Jan**. **Sequencing:** Techathon+ must come before Ideation, never after.
      C5 is promoted from P2 to P0 by this item.
- [ ] **F5 `[P0]` Keep the attribution claim honest in every application.** The spec is written; the endpoint is not.
      A2b is still open. Slide 4 of the comparison-first deck says "4/16 register capabilities" — do not let an
      application deck quietly upgrade that to a shipped feature.
- [ ] **F6 `[P1]` Decide Imagine Cup by 1 Dec.** Requires a company founded on/after 2 Nov 2024 and ≥US$1 usage on
      ≥10 Azure services. Both have 4–6 weeks of lead time. If the decision is no, drop it rather than starting in February.
- [ ] **F7 `[P1]` Hult Prize by 28 Feb** — 4-minute video, deck, one-pager, SDG framing, and an explicit decision on
      the ~10% equity the winner gives up.
- [ ] **F8 `[P2]` Watch `hkchallengeplus.com` from January** for the 13th HK University Student Innovation &
      Entrepreneurship Competition (~Mar). Cross-institution teams allowed; choose 创新 vs 创业 track early.
- [ ] **F9 `[P1]` Re-run the suites and clear the runtime store before any competition demo.** §2.1's 256/27/111 are
      14 Nov numbers (E1); the local store still holds hand-poked residue that distorts the app, though not the suites
      (E5). A demo is the one place where both matter.
      **Suites re-run (26 Nov 2026):** 333 pytest passed in 82 s, the per-file dual-runner loop had 0 failures,
      133 frontend tests passed, `tsc` and `eslint --max-warnings 0` clean, demo returns 200. The runtime store has
      **not** been cleared.

- [ ] **F10 `[P0]` DeepTech100+ Cohort 8 — 29 Nov 2026, 23:59.** HKU TEC + HKSTP. A deck of **at most 15 slides**,
      proof of the Person-in-Charge's HKU association, and the Qualtrics form. Feeds HKSTP Ideation (HK$100k, three
      tranches) and Incubation (HK$1.29M). Incorporation is not required to apply; if approved, incorporate a Hong
      Kong limited company and keep HKU member(s) at ≥20%.
      **Deck cut (26 Nov 2026):** `deliverables/Sandbox Pitch Deck (DeepTech100+) v1.pptx`, 15 slides, rebranded from
      CCMF, counts recomputed, timeline on the Ideation year, G9 line added. **Interim only** — a separate
      submission version is in progress, and v1 is its content base rather than the file to upload. Check that
      version with `python3 scripts/deck_diff.py "<deck>.pptx"`.
      **Still human:** the form, the HKU affiliation proof, the PIC choice, and whether the submission version uses
      HKU TEC's published deck template.
      See `deliverables/DEEPTECH100_SUBMISSION.md`.

---

## G. Government criteria fit — broad-brush screen — added 23 Nov 2026

These do not replace A–F. They make the "labelled screening" edge legible to a government reviewer: a declaration can be triaged against the statutory gates it appears to touch, with an explicit list of what is still unknown. Full statutory detail and primary sources are in
[the screening-criteria research note](../01_research/HK_Government_Screening_Criteria_Urban_Planning.md).

**The rule for this section:** the output is a **broad-brush fit read, not a statutory determination**. Every result carries the screening label, the assumption register and a `furtherInformation` list. If a threshold needs a fact we do not hold (zone, road class, receiver distance, Deep Bay buffer status), we say so rather than guessing.

### Criteria to encode

| Gate | Broad-brush test | Product read |
|---|---|---|
| EIAO Sch. 3 | Urban development / redevelopment site **>50 ha** | Flag schedule 3 review. Do **not** use 20 ha or 100,000 population. |
| EIAO Sch. 2 A.1 | Expressway / trunk / primary / district distributor road — no length threshold | Flag a Schedule 2 component from road class alone. |
| EIAO Sch. 2 C.1 / C.2 | Reclamation >5 ha; or >1 ha within 500 m seaward / 200 m landward specified area / 100 m residential | Flag; ask for reclamation area and receiver distances. |
| EIAO Sch. 2 F.1 / F.2 | STP >15,000 m³/day; or >5,000 m³/day within 200 m of sensitive uses | Flag from declared drainage assumptions. |
| EIAO Sch. 2 I.1 | Channel width more than 100 m, or located less than 300 m from an area named in I.1(b) | Flag from the drainage axis; do not invent the distances or the receiving area. |
| EIAO Sch. 2 P.1 | Residential / recreational use inside Deep Bay Buffer Zone 1 or 2 — no size threshold | Ask for buffer-zone status. The repealed P.2 (not less than 2,000 flats, and not served by public sewerage) is not a test. |
| EIAO Sch. 2 Q.1 / Q.2 | Works in country park / SSSI / conservation area / marine park / cultural heritage site; rock-cavern portal <100 m from receivers | Sensitive-area catch-all flag, with the long exemption list left to EPD. |
| EIAO s. 4(4) | Contiguous projects by the same / associated persons that appear split to evade the Ordinance | Flag phasing / neighbour combinations for aggregation review; never assert aggregation. |
| Cap. 131 OZP Notes | Column 1 always permitted; Column 2 needs s. 16 permission; neither needs s. 12A | Zone-level triage, read from the HSK–HT OZP Notes, not guessed from land use. |
| TPB s. 16 EA triggers | May cause impacts; pollution-sensitive; or major / large-scale | Advisory "EA may be required" for CDA, residential, sensitive uses, batching / asphalt plants, slaughterhouses. |
| HKPSG Ch. 9 Table 1.3 | Residential buffers 300/180/120 m from trunk / primary / district-local roads (50/40/30 m with screening); NEF 25 | Advisory only, never pass/fail. 20/10/5 m is the open-space separation (trunk and primary / district / local), not a residential buffer. |
| Post-screen criteria | Amended EIAO TM from 30 Jun 2023 (transition ended 30 Jun 2025); new AQOs from 11 Apr 2025 applied at decision date | Stated as "as at" inputs in the assumption register. |

- [x] **G1 `[P0]` Write `docs/GOVERNMENT_CRITERIA_FIT.md`.** One page: each product axis (drainage, wind/AVA, massing/SBDG, attribution) → the statutory gate it can inform → what our screening number can and cannot say.
      *Done when:* a reviewer can read it beside the parameter card and see exactly where the tool stops.
      **Met (23 Nov 2026).** `docs/GOVERNMENT_CRITERIA_FIT.md`.

- [x] **G2 `[P0]` Add broad-brush triage to declaration intake.** Given site area, zone, road class, reclamation / STP / drainage inputs and receiver distances, return a `governmentFit` object: `schedule3`, `schedule2[]`, `planningPermission`, `eaMayBeRequired`, `assumptions[]`, `furtherInformation[]`, `notADetermination: true`.
      *Done when:* tests cover a >50 ha flag, a 30%-of-district declaration that is **not** 50 ha, a road-class-only flag, and assertions that the obsolete 20 ha / 100,000 population / P.2 / 20-10-5 m residential rules do not fire.
      *Why:* this is the "fitting government criteria" claim. Without the unknowns list it is an overclaim, and E2 becomes a lie.
      **Met (23 Nov 2026).** `POST /api/declarations/intake` and `tests/test_government_fit.py`. The same read is the Criteria fit panel (`frontend/src/components/GovernmentFitPanel.tsx`), with the comparison and above the storm. The closed state is four rows — air ventilation, sustainable building design, drainage, and the EIA Ordinance — each naming who set the rule, what this sandbox screens, and one limit. Cap. 499 facts sit behind Show. A blank is not sent. Assumptions, the annex and the unknowns stay closed until asked. The read is a broad-brush fit read, not a statutory determination.

- [x] **G3 `[P0]` Put the thresholds in reference data, not prose.** `backend/data/reference/hk_screening_thresholds.json`, each entry with value, unit, source URL, effective date and superseded-by field.
      *Done when:* G2 reads from the file, D6 can point at it, and a drift test fails if a superseded value reappears.
      **Met (23 Nov 2026).** G2 reads the file. `assert_no_superseded_value_is_live` fails if a superseded value is put back on a live entry, or if a repealed entry is deleted. D6 can point at the same file; the clause texts themselves are still G7.

- [ ] **G4 `[P1]` HKPSG buffer advisory layer.** Table 1.3 residential road and rail buffers plus the NEF 25 rule, shown as "check against HKPSG", never as compliance.
      *Done when:* a missing receiver distance produces `furtherInformation`, not a silent pass.
      *23 Nov:* the fit read and the Criteria fit panel already print that check, and a missing distance is `furtherInformation`. G4 stays open because there is no map layer.
      *24 Nov:* the EIA row carries one line, "HKPSG noise, check only". Still no map layer.

- [x] **G5 `[P1]` Close the liability loop in A4 and E2.** Code of Practice states what a fit assertion is and is not; every output keeps the label plus the unknowns list.
      *Done when:* removing either the label or the unknowns list fails a test.
      **Met (23 Nov 2026).** `docs/CODE_OF_PRACTICE.md` states the fit assertion. A4's remaining sections are still open. Dropping the label or `furtherInformation` fails `tests/test_government_fit.py`.

- [x] **G6 `[P1]` B5 gains a screening-basis annex.** One page alongside the AVA SVR/LVR table and attribution annex: gate flags, thresholds applied, sources, "as at" dates, further information.
      *Done when:* a consultant can paste it into a s. 16 submission without editing a number.
      **Met (23 Nov 2026).** `screeningBasisAnnex` is rendered from the fit and the threshold file. `docs/SCREENING_BASIS_ANNEX.md` describes the page. B5's other templates are still open.

- [ ] **G7 `[P1]` Extend D6 with the current statutory texts.** L.N. 77/2023, the consolidated Cap. 499 Schedules 2/3, TPB s. 16 Guidance Notes (Oct 2026), HKPSG Ch. 9, and the EPD AQO notice — with the old 20 ha / P.2 material marked superseded, not deleted.
      *Done when:* every threshold in G3 has a primary-source citation and an effective date.

- [ ] **G8 `[P2]` Site-specific follow-ups before any HSK–HT claim.** The plan identity is recorded (S/HSK/4, approved 29 September 2026, gazetted 9 October 2026). Still to read: zone-by-zone Notes; whether the site intersects Deep Bay Buffer Zones 1/2; which receiver distances are actually held; the s. 5(9)–(11) direct-EP conditions; and any Schedule 2/3 amendment after the 30 June 2023 point in time.
      *Done when:* answers are recorded in the research note with citations and the `furtherInformation` list shrinks on evidence, not assumption.

- [ ] **G9 `[P1]` Keep the competition framing honest.** Add one line to the deck's approval-path slide: two gates (EIAO and town planning), broad-brush fit read only.
      *Done when:* F5 still holds — no application deck upgrades G2 to a statutory screening decision.

---

## H. Project import — getting a scheme into the existing scene — added 26 Nov 2026

This is the current build priority, and it sits **inside** A1 rather than beside it: A1 needs a real developer's
scheme in the sandbox, and today that means editing a JSON file in this repository and re-running a seeder. A third
party cannot add a project without a developer and a redeploy, which makes every "bring your scheme and we will
score it" conversation a demo request rather than a product.

The contract is written and not implemented: [docs/PROJECT_IMPORT.md](docs/PROJECT_IMPORT.md). Read §1 (three tiers)
and §6 (what an import must never do) before scoping any of the items below. "The plan was written" is only the first
half; the second is **integration readiness** (the subsection after H13), which is what makes a newly imported project
part of the whole system rather than a row only the catalog can see.

**The rule for this section:** an import puts geometry and *stated* effects on the sandbox so the run can score them.
It is a staged scheme, not a declaration — no hash, no signature, no "as at". Those are B3/B4. An import that reads
as a signed submission is the overclaim F5 keeps warning about.

### What already works, off-repo

A project is data, not code: `backend/data/projects/<id>.json` → `scripts/seed_projects.py` → a plan whose
`params.projectId` makes it a row in `ProjectCatalog`. Toggling the row changes the run, and `terrainMeta.projects`
draws the GLB. Two tiers exist — effect-only (footprint + declared effects) and modelled (adds a GLB, origin and
scale). Both require a repository edit. Nothing in the effect, cap, consent or render path needs rebuilding; what is
missing is a route, a report, and a place to put an uploaded asset.

### Items

- [x] **H0 `[P0]` Write the import contract.** `docs/PROJECT_IMPORT.md`: the three tiers, the two-phase
      `POST /api/scenes/{id}/imports` with `dryRun`, the `ImportReport`, the compute order, the format matrix, the
      refusal list, the acceptance tests and the risks.
      **Met (26 Nov 2026).** Contract only; no code. The two defects it recorded are real and predate it: the
      `interventions` extrusion has no DEM base height (so a 1.5–2 m feature on 8–12 m ground does not draw), and
      `load_grids()` never compares its raster bounds to the scene bbox (so a project outside the window is scored
      against it silently).

- [ ] **H1 `[P0]` `POST /api/scenes/{sceneId}/imports` — T1 and T2, dry run first.** Validate geometry, clip to the
      scene bbox, rasterise against the scene's own grid, test building overlap, apply the 25% / 40% caps through
      the consent seam, resolve every effect through `INTERVENTION_EFFECTS`, write `project-<id>` with
      `params.importId` and a digest, and return the report. `dryRun=true` writes nothing. No run is started.
      *Done when:* a third project enters the running app without a repository edit, toggles in `ProjectCatalog`,
      and a run's ledger attributes cells to it — and every refusal in `docs/PROJECT_IMPORT.md` §7 is a test.
      *Reuse, do not retype:* `proposal_constraints` (overlap, caps, clipping), `InterventionIn` (geometry
      validation), `seed_projects.interventions_for` (one intervention per effect on one ring),
      `effect_is_scored` (the scored/skipped split).

- [ ] **H2 `[P0]` Import panel in the app.** Drop a footprint (and optionally a GLB URL), see the report, then
      confirm. The confirm step is the same gate the AI-proposal path already uses: nothing is written until the
      user accepts, and the report is what they accept.
      *Done when:* the panel shows cells, area, coverage fraction, building overlap, which axes will move, the
      assumptions, and the `furtherInformation` list — and shows them *before* the write.
      *Gated by:* H1. Keep it behind `ALLOW_IMPORTS=1` until B2, because the public demo has no auth.

- [ ] **H3 `[P0]` Fix the DEM base on extruded interventions.** `applyStyle` sets `extrudedHeight` and
      `heightReference = NONE` but never a `height`, so every extruded intervention starts at ellipsoid zero and is
      buried on 3.4–17.3 m ground. Sample the DEM at the ring, set `height = base` and
      `extrudedHeight = base + h`, as `footprintLayer` already does.
      *Done when:* the 2 m paving slab and the 1.5 m flood storage are visible on the terrain in both 3D modes (today
      they are entirely below it), the 14 m reservoir sits on the ground instead of sunk to its top 6 m, and a test
      asserts a non-zero base height.
      *Why it is P0:* an import that is scored but not drawn is indistinguishable from an import that failed, which
      is exactly the class of fault `interventionLayer.ts` was written to avoid.

- [ ] **H4 `[P1]` GeoJSON massing with height, previewed before commit.** A FeatureCollection with `height_m` per
      feature becomes a geometry-only effect (`station_massing` shape): shade and wind exposure move, land cover
      does not, and the report says so. Preview in 2.5D, then commit.
      *Done when:* a planner sees the extruded massing and the cells it covers before pressing import, and the
      comparison reports the heat/exposure change with no land-cover claim.

- [ ] **H5 `[P1]` Derive a footprint from an uploaded model, server-side.** Move `compute_plan_project_footprint.py`
      behind the route so a GLB alone is enough, with the derived ring shown for confirmation rather than trusted.
      *Done when:* a GLB plus an origin and a scale produces a footprint the user can inspect and edit, and a model
      whose base is not flat is flagged rather than silently averaged.

- [ ] **H6 `[P1]` Model asset budget.** The two committed GLBs are 79 MB and 82 MB at `scale: 50`. Cap the accepted
      size, report it in the import response, and prefer a decimated asset.
      *Done when:* an import cannot add a model that stalls the opening view, and the report names the bytes.
      *Why:* `SandboxViewer` opens the city tileset at screen-space error 128 precisely because 24 would pull about
      250 MB into the opening view. A third 80 MB project at `scale: 50` is the same problem with no LOD to fall back on.

- [ ] **H7 `[P1]` Refuse-or-convert matrix as a preflight.** GPKG, Shapefile and IFC are deferred to an offline
      converter (I2); RVT/DWG are refused with the reason; a non-4326 CRS is refused with the CRS named.
      *Done when:* the refusal is a labelled 422 naming the format and the supported alternative, never a generic
      "unsupported file", and there is a test for each row of `docs/PROJECT_IMPORT.md` §5.

- [ ] **H8 `[P2]` Re-import, supersede, and bulk import.** A second import of the same `projectId` is a new plan,
      never a mutation of the scored one; supersession is B8. Bulk import of a district's worth of projects is where
      the per-scene raster set (C3's first half) becomes mandatory rather than tidy.
      *Done when:* importing the same project twice leaves the first plan byte-identical, and a bulk import refuses
      cleanly on a scene whose rasters do not cover the footprints.

- [ ] **H9 `[P2]` Carry import provenance onto the ledger and parameter card.** `importId`, `digest`, the importing
      party and the date, so a reader can tell an imported scheme from a hand-drawn one.
      *Done when:* the parameter card names the import a run used, and the seam is the one B3 will sign.

### Underside view — requested 26 Nov 2026

The ask: *do not limit the viewport, so users can see the underside of the development.* Checked against the running
app and the code on 26 Nov, and the honest answer is that the viewport is only one of four locks. Only the first two
are camera settings; the third is why freeing the camera alone would show a black rectangle.

1. **Pitch is clamped below the horizon.** `cameraRig.ts` sets `MIN_PITCH_DEG = -88`, `MAX_PITCH_DEG = -8`, and
   `pitchDelta` clamps every tilt into that band. `-8` is the *near-horizon* end, so the tilt control, the tilt
   buttons and the arrow keys all stop just short of horizontal. The limit is also encoded as a test —
   `geometry.test.ts` "never allows the camera to swing above the horizon" asserts `MAX_PITCH_DEG < 0` — so it is an
   invariant, not a slider.
2. **The camera cannot go under the terrain.** `tuneNavigation` sets `enableCollisionDetection = true`, which is what
   stops a drag dropping the eye through a 139 m relief surface. Negative-pitch-only plus collision detection means
   the eye is always above ground and always looking down: there is no pose in the app from which an underside is
   visible.
3. **Every surface in the scene is one-sided.** Queried live in the running viewer: both `Cesium3DTileset`s, all
   three projection `Model`s and `scene.globe` report `backFaceCulling: true`, and nothing in `tilesetLayer.ts` or
   `modelLayer.ts` changes it. From beneath, the terrain, the textured buildings and the committed GLBs rasterise
   nothing — you see the page background. The 2.5D massing and the intervention extrusions are the exception, because
   a Cesium extruded polygon is a closed volume with a bottom cap; they are the only geometry that would draw.
4. **The globe is clipped to the bbox** (`clipGlobeToBBox`), so the "floor" of the scene is a clipped disc with no
   underside geometry either.

Convenient detail: `frameExtent` already places the camera *below* its target for a positive pitch
(`back.z = -range·sin(pitch)`), so a below-view is a parameter, not new framing maths.

- [ ] **H10 `[P0]` Underside view: open the pitch past the horizon and lift collision detection.** Add an explicit
      `cameraControl.underside()` that frames the scene from below its pivot at a shallow upward pitch (the same
      `frameExtent` call with a positive `pitchDeg`), and suspend `enableCollisionDetection` only while the eye is
      below the DEM. Keep the orbit clamp for the normal view: a tilt button that can wander above the horizon is a
      way to lose the map, so *below ground* is the condition for the wider range, not a global loosening.
      Restore both on reset, top-down and on leaving the view.
      *Done when:* the button drops the camera beneath the slab looking up, every axis still moves independently
      there, and reset returns the clamp. Replace the `MAX_PITCH_DEG < 0` assertion with one that states the real
      rule — the orbit clamp holds above ground, and the underside view is the only way below it.

- [ ] **H11 `[P0]` Make the masses have an underside.** H10 alone renders an empty frame. Either set
      `backFaceCulling = false` on the two tilesets and the projection models (cheapest, but the inside-out faces are
      lit by inverted normals and the city tileset costs roughly double its rasterised triangles — measure against the
      existing screen-space error of 128 before keeping it), or keep culling and give the import a solid: a base cap
      polygon at the DEM, plus `Model` bottom caps for the GLBs. The 2.5D massing path needs neither.
      *Done when:* from below, the study area reads as a slab with buildings standing on it in both 3D modes, the
      underground tank and flood-storage volumes are visible in section, and the opening frame is unchanged.

- [ ] **H12 `[P1]` Make depth readable once you are under there.** An underside with no scale is a dark shape. Add a
      horizontal section (a `ClippingPlane` at a chosen elevation over the tilesets, the same plane class
      `clipGlobeToBBox` already uses) with a depth read-out in metres above the DEM, so a 2.5 m tank and a 14 m
      reservoir can be told apart. Read-only; nothing here changes a scored cell.
      *Done when:* a user can cut the development at 0, −5 and −15 m and read the height on screen.

- [ ] **H13 `[P2]` No dead ends from below.** `groundPoint` picks the depth buffer first, then `globe.pick`, then the
      ellipsoid, and from underneath there is nothing to pick: the depth buffer is background, the globe is a
      one-sided clipped disc, and `pickEllipsoid` from *inside* the ellipsoid returns a far-side point or nothing. The
      orbit and zoom anchor therefore lands somewhere unrelated to the view, and a zoom would lurch instead of holding
      the anchor still. Anchor on the pivot whenever the eye is below the DEM, and refuse to leave the camera
      underground on any view change.
      *Done when:* zoom from below moves the eye along the line to the pivot with the anchor fixed on screen, and no
      interaction can strand the camera below the terrain with the clamp back on.

### Integration readiness — onboarding a project to the whole system — added 26 Nov 2026

The ask: a newly imported project should arrive **integration ready**, not merely written to disk. "Integrated" is a
claim about every consumer of a project, and nothing in the codebase enumerates those consumers, so a route can pass
its own tests while the import is absent from the wind field, missing from a drawn corridor, or scored against rasters
that do not cover it. This subsection is that enumeration plus the adapters that close it.

Readiness is reported per consumer in one of four states. The last one refuses the commit:

- **ready** — the consumer already sees the project.
- **adapted** — the onboarding step derived or defaulted what the consumer needs, and the value is in `assumptions[]`
  with `status: DERIVED`, the method and the date.
- **abstained** — the consumer will not use this project, and the report says so in words. Abstention is allowed;
  silence is not.
- **blocked** — the consumer needs a fact the import does not carry and cannot safely default. `REJECTED`; no plan
  is written (`docs/PROJECT_IMPORT.md` §6.7).

| Consumer | What it needs | How it learns today | Ready today |
|---|---|---|---|
| Land-cover ledger | one resolved effect per `INTERVENTION_EFFECTS` kind | `seed_projects.interventions_for` | via H1 |
| Heat and massing rasters | a `station_massing` feature carrying `heightM` | `run_service._massing_overrides` | only if the import declares massing |
| Comparison board wind | the same `station_massing` override | `board._scheme_footprints` | only if the import declares massing |
| Drawn corridor | the scheme's footprint set | `/ventilation/corridors` reads `_require_buildings(scene_id)` — the scene file, **not** scheme interventions | **no** — the drawn line and the board can disagree once a scheme adds massing |
| OpenFOAM obstacle field | the extruded footprints | `openfoam_channel/run_channel.py::_buildings` reads `buildings_hsk.json` only | **no** — imported massing never enters the solved flow |
| Raster coverage | footprint inside the loaded grid | `load_grids()` is a fixed-name `lru_cache` singleton that never compares its bounds to the scene bbox | **no** — an out-of-window import is silently scored |
| Project catalog | a plan with `params.projectId` | `ProjectCatalog.tsx` reads plans, not a constant | via H1 |
| 3D model and label | `model`, `origin`, `scale` and `footprint` on disk | `scene_service.project_models` | T1 (no GLB) is listed as *unavailable*, so it has no label or marker |
| Intervention drawing | a DEM base height | `interventionLayer.applyStyle` | **no** — H3 |
| Consent and caps | declaration status and active plans | `services/consent.py` | via H1 |
| Provenance | `importId` and digest | parameter card and ledger | H9 |

- [ ] **H14 `[P0]` Make the readiness contract code, not prose.** One `PROJECT_CONSUMERS` registry: each entry names a
      consumer, the artifact it reads, and a predicate `(project, scene) -> ready | adapted | abstained | blocked` with
      a one-line reason. `POST /imports` (H1) returns the results as `readiness[]`; `dryRun` returns the same list
      without writing.
      *Done when:* every row of the table above is a registry entry, **and a test fails when a project consumer in the
      code has no entry.** The second half is the point — it is what makes the *next* consumer (a new axis, a new
      export, a re-solve) fail loudly instead of quietly ignoring imports.
      *Why a registry:* four different mechanisms already carry project information (scene file, plan, massing
      override, raster set). Three separate "add import support" tickets will drift.

- [ ] **H15 `[P0]` Onboarding adapters: derive what can be derived, and label it.** For a T1/T2 import: derive the
      footprint from the GLB when only a model is supplied (H5), derive a massing height when the model has one (else
      abstain for massing), default land class and curve number with the source named, and set the DEM base. Each
      derived value enters `assumptions[]` as `status: DERIVED` with its method. A field that cannot be derived becomes
      `furtherInformation`, never a silent zero.
      *Done when:* an import carrying only a footprint, a GLB and a storage depth becomes ready with every derived
      value named — and removing one derivation turns it into an abstention rather than a default.

- [ ] **H16 `[P0]` One corridor per scheme, drawn and compared.** Let `/ventilation/corridors` apply the scheme's
      `station_massing` overrides — the same `_scheme_footprints` rule the board already uses — so the line the map
      draws and the line the comparison scores come from one footprint set.
      *Done when:* an imported massing moves the drawn corridor and the board's corridor by the same amount, and a test
      asserts the two agree for the fixture in H20. Without this the picture and the number disagree exactly where the
      product says they must not.

- [ ] **H17 `[P1]` Say when the wind field is not the scheme's.** The solved channel is the base city only
      (STATUS.md edge 4). An import must report `wind: abstained — the solve predates this project; the drawing is the
      base massing`, and the compass must not imply otherwise.
      *Done when:* the import report and the wind panel print the same abstention, so nobody reads the threads as the
      imported scheme's flow.
      *Follow-on, separate:* re-solving per scheme is a batch job with a per-scheme obstacle set and its own sidecar,
      not a request-path feature — and not this item.

- [ ] **H18 `[P1]` Refuse an import the rasters do not cover.** Compare the footprint bbox to the loaded `Grids` bounds
      before rasterising: `REJECTED` outside, flagged when only partly inside the clip fraction. This is H1 step 2; the
      per-scene raster set is C3's first half, so until C3 a second district is refused rather than mis-scored.
      *Done when:* a footprint 2 km outside the study window is refused with both bboxes named and no plan written.

- [ ] **H19 `[P1]` A T1 project still has a place on the map.** `project_models()` requires a model **and** a
      footprint, so an effect-only import is listed as unavailable and gets no label or marker. Give it a footprint
      outline and a label without a GLB, styled as distinct from a modelled project.
      *Done when:* a T1 import is visible with its name and outline, and its catalog row says "effect-only".

- [ ] **H20 `[P1]` One onboarding fixture, end to end.** A committed fixture — a footprint, two effects, a small
      decimated GLB — that the suite drives from file to ready, then through a run and an A/B compare. This is the
      regression that stops the onboarding path rotting quietly after the demo.
      *Done when:* the fixture passes with no repository edit beyond the fixture itself, and the test asserts the same
      readiness list the panel shows.

- [ ] **H21 `[P2]` The same checklist for a new *format*.** When the offline converter (I2) lands it produces the same
      import body and goes through H14's registry, so a new format cannot bypass readiness. The converter stays off the
      API, per `docs/PROJECT_IMPORT.md` §5.

- [ ] **H22 `[P1]` One onboarding pipeline, two entry points.** A single `onboard_project(body, scene)` that runs the
      order — validate, clip, rasterise, overlap, caps, resolve effects, adapt (H15), readiness (H14) — and is called by
      both `POST /imports` and `scripts/seed_projects.py`. The seeder is today's only working route, so if the two paths
      adapt differently then a committed project and an imported one are not the same kind of object, and every demo
      that mixes them is scored on a different shape of data.
      *Done when:* the same project body through either entry point produces the same plan, the same interventions and
      the same readiness list, and a test fails on any difference. This is what "import onboarding" means as code rather
      than as a checklist a person follows.

### Sequencing

H3 before H1's demo (a scored-but-invisible import is a broken demo). H1 before H2. H1 gates A1. H8's bulk-import
half is the same blocker as a second study area, and should be scoped after C3's playbook rather than inside the
urgent work. Nothing here depends on attribution (A2b), so import does not wait on it.

H10 and H11 are one demo and must land together: freeing the camera with nothing two-sided behind it shows a black
frame, which is worse than the limit it replaced. Neither depends on H1, so they can run in parallel with H3 — but
H11's culling decision should be measured on the same opening frame that H6's model budget is judged against.

Readiness runs through the same order: H14 before H2 (the panel's accept step is the readiness list), H15 beside H1
(an adapter that is not in the route is a manual step again), and H16 before any demo that turns the wind on with an
imported massing, because that is the first frame where the drawing and the board can part company. H22 should land with
H1 rather than after it — a second pipeline bolted on later is exactly how the seeder and the route drift apart. H18 can
land with H1's refusal path; H17 is a sentence, not a solve. None of H14–H22 changes a scored number, so none of them
can quietly move a previously published figure.

---

## The one-line version

One real declaration (A1), attribution defined (A2), a company (A5) and a Code of Practice (A4) — by mid-December.
Everything else is downstream of those four.

**Competition overlay (18 Nov, updated 26 Nov):** a 4-person entry team, the CCMF milestone budget, honest attribution
claims, and a fresh suite run — before 1 Dec. DeepTech100+ (29 Nov) is now a separate gate in §F: its 15-slide deck
exists, but the form, the HKU affiliation proof and the PIC choice are human actions. See §F10.

**Government-criteria overlay (24 Nov):** G1–G3 and G5–G6 are met. The Criteria fit panel sits with the comparison,
above the storm. Its closed state is four rows (air ventilation, sustainable building design, drainage, EIA). Cap. 499
facts sit behind Show; a blank is not sent. Assumptions, the annex and the unknowns stay closed until asked. The read
is a broad-brush fit read, not a statutory determination. It does not report an AVA, an SBDG concession, a Drainage
Impact Assessment, or a cumulative-impact finding. The comparison also names the projects held at data collection and
compares the wind channel under the study-window inflow. SVR and LVR stay empty. G4 (no map layer), G7, G8 and G9 are
still open. G8 still comes before any site-specific HSK–HT claim. See §G.

**Project-import overlay (26 Nov):** H0 is met — `docs/PROJECT_IMPORT.md` is the contract, and nothing in it is built.
H1 (the route and its report) and H3 (the DEM base on extrusions) are the two that have to land before a third party
can put a scheme in front of a run and see it. H1 is a precondition of A1, not a competitor. Import is a staged
scheme, not a declaration: no hash, no signature, no "as at". See §H.

**Integration-readiness overlay (26 Nov):** writing the plan is half the job. H14's consumer registry, H15's adapters
and H22's one pipeline (shared with the seeder) are what make an import part of the whole system rather than a catalog
row: today the drawn corridor reads only the scene file (H16), the OpenFOAM field is the base city only (H17), and an
out-of-window footprint is scored without a bounds check (H18). Readiness is reported per consumer as ready / adapted /
abstained / blocked, and an abstention must be said in words. Nothing in H14–H22 changes a scored number. See §H.

**Underside overlay (26 Nov):** the request to look under the development is four locks, not one — a −8° pitch clamp,
collision detection, single-sided tilesets/GLBs/globe, and a clipped globe floor. H10 makes the pose possible; H11 is
the one that makes it visible, and it is the only item here that spends render budget. See §H.

