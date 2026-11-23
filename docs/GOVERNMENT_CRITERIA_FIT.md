# Government criteria fit

**As at 23 November 2026.** A reviewer can read this beside the parameter card (`GET /scenes/{id}/parameter-card`). The card says what a run assumed. This page says which published gates those declared facts appear to touch.

The output is a **broad-brush fit read, not a statutory determination**. Every result carries the screening label `BROAD_BRUSH_FIT_READ_NOT_A_STATUTORY_DETERMINATION`, the assumption register, and a `furtherInformation` list. `notADetermination` is true. A missing fact is stated. It is not guessed.

The screen applies the figures in [`backend/data/reference/hk_screening_thresholds.json`](../backend/data/reference/hk_screening_thresholds.json). Each entry has a value, a unit, a source URL, an effective date, and a superseded-by field. Repealed entries stay in the file and are not applied. Primary sources are the ones named in [the screening-criteria research note](../../01_research/HK_Government_Screening_Criteria_Urban_Planning.md).

There are two gates. A current section 16 planning permission is not an environmental permit. Section 9(1) still requires an environmental permit for a Schedule 2 project. Section 9(2)(a) exempts only a permission granted before 1 April 1998. Section 9(5) means a Schedule 3 listing does not remove that need. Contravention of section 9 is an offence under section 26(1). This read does not determine a contravention.

## What each product axis can inform

| Axis | Gate it can inform | What the number can say | What it cannot say |
|---|---|---|---|
| Drainage deficit, and a declared sewage capacity, channel width or dredging volume | Schedule 2 F.1 (>15,000 m³/day), F.2 (>5,000 m³/day and <200 m from a receiver named in the item), I.1 (channel width >100 m, or <300 m from an area named in I.1(b)), C.12 (>500,000 m³, or the 500 m / 200 m limbs) | Whether the **declared** capacity, width, volume or distance meets the figure in the reference file | That the drainage deficit is an installed sewage capacity. A distance or a designation the declaration does not hold. That an environmental permit is granted or refused |
| Wind / AVA | None of Schedule 2 or 3. HKPSG Chapter 9 is a noise guideline, not a ventilation test. Technical Circular 1/06 asks for a comparison of design options and defines a velocity ratio from pedestrian test points. It states there is no absolute benchmark | A geometric comparison under the area-weighted Planning Department inflow for the cells the study window touches. Frontal area density is not a velocity ratio. Site and local velocity ratios are left empty | An AVA pass, a noise-buffer pass, a velocity ratio computed from frontal area or from the coarse channel solve, or that an environmental assessment is or is not required |
| Massing, site area, road class | Schedule 3 item 1 (urban development or redevelopment **more than 50 ha**). Schedule 2 A.1 (expressway, trunk, primary distributor or district distributor — road class only, no length). P.1 if the use and the Deep Bay buffer zone are both declared | Whether the declared hectares are more than 50. Whether the declared class is an A.1 class. A 30% share of this district is converted to hectares and then compared; on the current study grid that share is not 50 ha | That 30% of the district is a Schedule 3 project. A zone column read off a land-use colour. An SBDG setback or greenery check. SBDG is a different instrument and this screen does not apply it |
| Attribution, interaction term | Section 4(4), and only when the declaration says the projects are contiguous and by the same or associated persons | That the combination is worth a possible specification | That the Secretary has specified the projects. That the interaction term is a finding under the EIAO Technical Memorandum |

HKPSG Chapter 9 Table 1.3 (March 2014 edition) is advisory on the massing axis when a receiver distance is declared: residential separations 300/180/120 m for trunk / primary / district-local, or 50/40/30 m with screening; MTR/KCR/LRT 150/85/25 m; no noise-sensitive use within NEF 25. The reading is "check against HKPSG". It is never a pass or a fail. 20/10/5 m is the open-space separation (trunk and primary / district / local), and it is not applied as a residential buffer. A missing receiver distance is `furtherInformation`, not a silent pass.

Town planning is a column the declaration supplies: Column 1, Column 2 (section 16), or neither (section 12A). The column is not guessed from the land use. An environmental assessment **may be required** where the declaration matches the TPB section 16 Guidance Notes (October 2026), Annex B: the proposal may cause impacts, is pollution-sensitive, or is major or large-scale, including the Notes' examples (CDA, residential, schools, religious institutions, hospitals, residential care homes, concrete batching plants, asphalt plants, slaughterhouses). That flag is advisory.

Post-screen criteria are as-at inputs in the assumption register, not scores: the amended EIAO Technical Memorandum from 30 June 2023; the transitional route for EIA-report approval closed after 30 June 2025; the Air Quality Objectives from 11 April 2025 applied at the date of decision, with the 36-month variation-of-EP transition.

## Repealed tests that do not fire

Schedule 3 is more than 50 ha only (L.N. 77 of 2023, commenced 30 June 2023). The 20 ha test, the 100,000-population test, and the engineering-feasibility-study wording are repealed. P.2 is repealed. The old test was not less than 2,000 flats and not served by public sewerage. A flat count does not flag a designated project.

Schedule 2 items A.7, A.8 and A.9 remain on the current Schedule. This intake does not test them. Leaving them off the read is not a finding that they do not apply. C.12 is a separate dredging test. Its specified-area list is narrower than C.2's, and it has no 100 m residential limb. Q.1 exemptions stay with EPD.

## Hung Shui Kiu–Ha Tsuen

Plan identity only: S/HSK/4, approved by the Chief Executive in Council on 29 September 2026, gazetted 9 October 2026. Zone Notes, Deep Bay Buffer Zone overlap, receiver distances, and section 5(9) to (11) availability were not read. Schedules 2 and 3 on e-Legislation show 30 June 2023 as the current point in time. The fit read says so in `furtherInformation`. It does not fill those gaps.

The fit object is returned by `POST /api/declarations/intake`. The same read is the Criteria fit panel in the sandbox, beside the parameter card. A blank field is not sent. The pasteable page is the screening-basis annex beside the fit object. What a fit assertion is, and what it is not, is in [CODE_OF_PRACTICE.md](CODE_OF_PRACTICE.md).

Data collection is a separate record, `GET /api/scenes/{id}/data-collection`. It names the existing massing envelopes and the planned catalog, which is the identification Guidance Note 6/2023 paragraph 21 asks for at that stage. Committed projects are not held, and the record says so. It does not assess the cumulative impact. The comparison board prints the same inventory and an east-channel card. The card reads annual, summer and winter occurrence at 500 m for the four Planning Department cells the study window touches, and it compares the two schemes by east first-obstruction height and path length, in metres. Annual east leads that rose. Summer east does not, and winter east is second to north-east. Site and local velocity ratios stay empty. The cell tables, the PlanD dataset, AVRG73 and Technical Circular 1/06 are linked from the card.

This page is a summary for the product. It is not legal advice.
