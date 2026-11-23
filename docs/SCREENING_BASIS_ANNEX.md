# Screening-basis annex

The pasteable page is the `screeningBasisAnnex` string returned with `POST /api/declarations/intake`, beside the `governmentFit` object. It is filled by `render_screening_basis_annex` from that object and from `backend/data/reference/hk_screening_thresholds.json`. A consultant pastes the string into a section 16 bundle. The figures are the reference file's figures. They are not retyped.

The page has these parts, in this order:

1. The screening label and `notADetermination: true`.
2. As-at dates: Schedules point in time, the amended EIAO Technical Memorandum, the close of the transitional route for EIA-report approval, the Air Quality Objectives and the variation-of-EP transition, and the Hung Shui Kiu–Ha Tsuen plan identity.
3. Gate flags: Schedule 3, any Schedule 2 item flagged, the planning-permission column, the environmental-assessment advisory, section 4(4), and the HKPSG check.
4. Thresholds applied: value, unit, effective date, superseded-by, source URL, for each live test the screen can flag.
5. Advisory distances, marked as not a pass or a fail. Open-space separations are labelled `active-open-space`. They are not residential buffers.
6. Superseded tests not applied, including the repealed Schedule 3 area, the repealed population test, P.2, and the 20/10/5 m residential misreading.
7. The assumption register and the further-information list.

The annex is not an environmental permit and not a section 16 decision. It sits with the attribution annex in [ATTRIBUTION.md](ATTRIBUTION.md) as material for the regulatory templates in TODO B5. The AVA velocity ratios the templates also need stay in `backend/data/reference/hsk_ava_reference.json`. This annex does not convert a frontal-area figure into a velocity ratio.

If the label or the unknowns list is missing, the annex is not rendered.
