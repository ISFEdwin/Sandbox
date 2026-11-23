# TODO — deliverables from here

The product edges live in [STATUS.md](STATUS.md) (18 Nov 2026): comparison across separate axes, the shared picture as a side effect of holding the schemes, natural-language intervention, the wind channel, and labelled screening. This file is the checklist. It is not the definition of the product.

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
      contradictions. — **met.** The deck lives in the team's working folder, deliberately outside this public
      repository because it carries the fee schedule.

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
- [ ] **D5′ `[P2]` The site wind regime.** The build plan's Wave 0 also asks for CSDI's "Site Wind Availability Data"
      into `backend/data/reference/hsk_site_wind.json`, replacing AVRG73's single wind-rose fact with the government's
      published site wind regime. **Not started:** it needs a fetch from the CSDI portal, which is a separate piece of
      work from anything in this repository.
- [ ] **D6 `[P2]` The statutory clause texts.** EIAO TM and GN6/2010 into `backend/data/reference/`, plus
      `oasdiff breaking` in the CI contract job. **Not started:** the extracts are external documents.

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
      **Met (23 Nov 2026).** `POST /api/declarations/intake` and `tests/test_government_fit.py`. The same read is the Criteria fit panel beside the parameter card (`frontend/src/components/GovernmentFitPanel.tsx`). A blank field is not sent. The read is not a statutory determination.

- [x] **G3 `[P0]` Put the thresholds in reference data, not prose.** `backend/data/reference/hk_screening_thresholds.json`, each entry with value, unit, source URL, effective date and superseded-by field.
      *Done when:* G2 reads from the file, D6 can point at it, and a drift test fails if a superseded value reappears.
      **Met (23 Nov 2026).** G2 reads the file. `assert_no_superseded_value_is_live` fails if a superseded value is put back on a live entry, or if a repealed entry is deleted. D6 can point at the same file; the clause texts themselves are still G7.

- [ ] **G4 `[P1]` HKPSG buffer advisory layer.** Table 1.3 residential road and rail buffers plus the NEF 25 rule, shown as "check against HKPSG", never as compliance.
      *Done when:* a missing receiver distance produces `furtherInformation`, not a silent pass.
      *23 Nov:* the fit read and the Criteria fit panel already print that check, and a missing distance is `furtherInformation`. G4 stays open because there is no map layer.

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

## The one-line version

One real declaration (A1), attribution defined (A2), a company (A5) and a Code of Practice (A4) — by mid-December.
Everything else is downstream of those four.

**Competition overlay (18 Nov):** a 4-person entry team, the CCMF milestone budget, honest attribution claims, and a
fresh suite run — before 1 Dec. See §F.

**Government-criteria overlay (23 Nov):** G1–G3 and G5–G6 are met. The Criteria fit panel sits beside the parameter
card and reads `POST /api/declarations/intake`. The read is not a statutory determination. G4 (no map layer), G7, G8
and G9 are still open. G8 still comes before any site-specific HSK–HT claim. See §G.

