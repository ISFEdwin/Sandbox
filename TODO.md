# TODO — deliverables from here

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

- [ ] **A6 `[P0]` Cyberport CIP application — deadline 1 Dec 2026.**

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

## The one-line version

One real declaration (A1), attribution defined (A2), a company (A5) and a Code of Practice (A4) — by mid-December.
Everything else is downstream of those four.
