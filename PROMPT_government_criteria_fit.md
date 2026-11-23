# One-shot prompt — HK government screening criteria + broad-brush TODO integration

Copy everything between the two `===` lines and paste it into a fresh agent session.

===

Work in `/Users/edwin/Desktop/Coding/Projects/Hack4sdg`. Current date: 23 November 2026. Do not ask clarifying questions — assume **Hong Kong SAR** and proceed. In one pass, produce two things: (1) a research note on government screening criteria for urban planning, and (2) an edit to `T1/TODO.md` that turns those criteria into a broad-brush "government criteria fit" checklist. Do not create any other files. Do not modify code.

## Context you need

Hack4SDG T1 is a screening-grade tool for cumulative inter-project effects in Hung Shui Kiu–Ha Tsuen. Its stated product edges live in `T1/STATUS.md`; one of them is **labelled screening**. `T1/TODO.md` is the checklist, not the product definition. `T1/docs/ATTRIBUTION.md` defines the attribution claim. TODO item **E2** requires every output to keep the screening label and assumption register. **B5** needs regulatory output templates. **D6** collects statutory clause texts. **A4** is the Code of Practice. **F5** forbids overclaiming shipped features in competition decks.

If `01_research/HK_Government_Screening_Criteria_Urban_Planning.md` already exists, reconcile and improve it rather than writing a conflicting duplicate. If `T1/TODO.md` already has a section G, update it in place. Preserve all existing A–F items unchanged.

Use primary sources only: eLegislation (Cap. 499, Cap. 131), EPD, LegCo, TPB, PlanD. Use WebFetch/WebSearch; for PDFs, download with Bash and extract with `pdftotext -layout`. Never invent a number, date, threshold or citation. If something cannot be verified, label it "unverified" and say what is unknown.

## Deliverable 1 — `01_research/HK_Government_Screening_Criteria_Urban_Planning.md`

Write a research note in English with inline source links. It must contain:

1. **Scope and as-at date**, and the two-gate distinction: EIAO (Cap. 499) environmental screening vs town planning (Cap. 131) zoning/permission screening. State that a s. 16 planning permission does not substitute for an Environmental Permit.
2. **EIAO screening**: s. 4(1), s. 4(4) anti-splitting, s. 4(5) confirmation, s. 5 project profile / 14-day comment / 45-day study brief / s. 5(9)–(11) direct-EP route, s. 8(3) 30-day decision, s. 9(1) offence.
3. **Schedule 3 current test**: urban development or redevelopment **>50 ha only** (L.N. 77 of 2023). Explain that the old 20 ha and 100,000-population tests, and the engineering-feasibility-study requirement, were deleted; cite the LegCo paper explaining why.
4. **Schedule 2 trigger table** for the development-relevant items: A.1 (any expressway/trunk/primary/district distributor road, no length threshold), A.7–A.9, C.1 (>5 ha reclamation), C.2 (>1 ha with 500 m seaward / 200 m landward / 100 m residential buffers), C.12, F.1 (>15,000 m³/day STP), F.2 (>5,000 m³/day within 200 m), I.1 (>100 m channel or within 300 m), P.1 (residential/recreational in Deep Bay Buffer Zones 1/2, no size threshold), **P.2 repealed**, Q.1 sensitive-area catch-all, Q.2 rock cavern <100 m. Cite the EPD Schedule 2/3 list.
5. **Post-screen criteria**: EIAO TM effective 30 June 2023 with transitional arrangements ending 30 June 2025; new Air Quality Objectives effective 11 April 2025 applied at the date of decision, with the 36-month VEP transition.
6. **Town planning screening**: OZP Notes Column 1 (always permitted) / Column 2 (s. 16 permission) / neither (s. 12A amendment); temporary-use provisions (≤5 years urban/new town, ≤2 months specified rural events with no site formation, usually ≤3 years otherwise). From the TPB s. 16 Guidance Notes (October 2026), an Environmental Assessment may be required where a proposal (i) may cause environmental impacts by nature or location, (ii) is pollution-sensitive, or (iii) is major/large-scale; examples include CDA projects, residential, schools/religious institutions/hospitals/residential care homes, concrete batching plants, asphalt plants and slaughterhouses. No EA where impacts are unlikely and the use is not susceptible, e.g. small premises-based uses or uses fully meeting HKPSG buffers.
7. **HKPSG Chapter 9, Table 1.3**: residential road buffers **300 m / 180 m / 120 m** for trunk / primary / district-local distributors, reducible to **50 m / 40 m / 30 m** with screening; MTR/KCR/LRT 150/85/25 m; no noise-sensitive development within NEF 25. Explicitly correct the common secondary-source error that quotes 20/10/5 m — those are active-open-space buffers, not residential.
8. A **practical 7-step screening workflow**, a short **relevance to Hack4SDG / HSK–HT** section, an **obsolete-claims table**, and a numbered **primary-source list** with working URLs. End with a one-line "not legal advice" caveat.

## Deliverable 2 — edit `T1/TODO.md`

Insert a new section immediately after section F and before `## The one-line version`, headed exactly:

`## G. Government criteria fit — broad-brush screen — added 23 Nov 2026`

It must include:

- An intro saying these items do not replace A–F; they make the labelled-screening edge legible to a reviewer. Link relatively to `../01_research/HK_Government_Screening_Criteria_Urban_Planning.md`.
- A bold rule: the output is a **broad-brush fit read, not a statutory determination**. Every result carries the screening label, assumption register and a `furtherInformation` list; if a required fact is missing, say so instead of guessing.
- A `### Criteria to encode` table with these rows (gate — broad-brush test — product read):

  - EIAO Sch. 3 — site >50 ha — flag review; do not use 20 ha or 100,000 population.
  - EIAO Sch. 2 A.1 — expressway/trunk/primary/district distributor road, no length threshold — flag from road class alone.
  - EIAO Sch. 2 C.1/C.2 — reclamation >5 ha, or >1 ha within the 500/200/100 m buffers — flag; ask for area and distances.
  - EIAO Sch. 2 F.1/F.2 — STP >15,000 m³/day, or >5,000 m³/day within 200 m — flag from drainage assumptions.
  - EIAO Sch. 2 I.1 — channel >100 m or within 300 m of specified areas — flag; do not invent distances.
  - EIAO Sch. 2 P.1 — residential/recreational in Deep Bay Buffer Zones 1/2 — ask for buffer status; do not use repealed P.2.
  - EIAO Sch. 2 Q.1/Q.2 — works in sensitive areas; rock-cavern portal <100 m — catch-all flag; exemptions left to EPD.
  - EIAO s. 4(4) — contiguous projects apparently split to evade — flag phasing for aggregation review; never assert aggregation.
  - Cap. 131 OZP Notes — Column 1 / Column 2 / neither — zone-level triage from HSK–HT OZP Notes.
  - TPB s. 16 EA triggers — may cause impacts / pollution-sensitive / major-large — advisory "EA may be required".
  - HKPSG Ch. 9 Table 1.3 — 300/180/120 m (50/40/30 m screened), NEF 25 — advisory only, never pass/fail; 20/10/5 m is for active open space.
  - Post-screen criteria — amended TM from 30 Jun 2023, AQOs from 11 Apr 2025 at decision date — stated as "as at" inputs.

- Nine checkbox tasks, keeping the existing style (`- [ ] **G# \`[P#]\` Title.**` with `*Done when:*` lines):

  - G1 `[P0]` Write `docs/GOVERNMENT_CRITERIA_FIT.md`: product axis → statutory gate → what our number can and cannot say.
  - G2 `[P0]` Add a `governmentFit` object at declaration intake with `schedule3`, `schedule2[]`, `planningPermission`, `eaMayBeRequired`, `assumptions[]`, `furtherInformation[]`, `notADetermination: true`; tests for >50 ha, a 30%-of-district declaration that is not 50 ha, road-class-only flag, and non-firing of the obsolete rules.
  - G3 `[P0]` Put thresholds in `backend/data/reference/hk_screening_thresholds.json` with value, unit, source URL, effective date, `superseded-by`; drift test fails if a superseded value reappears.
  - G4 `[P1]` HKPSG buffer advisory layer; missing receiver distance produces `furtherInformation`, not a silent pass.
  - G5 `[P1]` Close the liability loop in A4 and E2; removing the label or unknowns list fails a test.
  - G6 `[P1]` B5 gains a screening-basis annex: gate flags, thresholds, sources, "as at" dates, further information.
  - G7 `[P1]` Extend D6 with L.N. 77/2023, consolidated Cap. 499 Schedules 2/3, TPB s. 16 GN Oct 2026, HKPSG Ch. 9, EPD AQO notice; mark old material superseded, not deleted.
  - G8 `[P2]` Site-specific checks before any HSK–HT claim: OZP zone Notes, Deep Bay buffer overlap, receiver distances held, s. 5(9)–(11) conditions, later amendments.
  - G9 `[P1]` Keep the competition deck honest: one line naming the two gates; F5 still holds.

- Add to the end of `## The one-line version` a paragraph beginning `**Government-criteria overlay (23 Nov):**` that sequences G1–G3 before A1, G5–G6 before B5, and G8 before any site-specific HSK–HT claim.

## Verification before you finish

- Read back both files.
- Confirm the relative link from `T1/TODO.md` resolves to the research note.
- Confirm section G sits between F and the one-line version, and that A–F are untouched.
- Grep both files for `20 ha`, `100,000`, `P.2`, and `20/10/5` / `20-10-5`: every occurrence must be in an explicitly obsolete/corrective context, never as a live rule.
- Report the two files changed and the substantive changes in each.

===
