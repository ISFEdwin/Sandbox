# Code of Practice — what a government-criteria fit assertion is

**Status.** This is the liability section TODO G5 asks for, read with E2. TODO A4, the full Code of Practice (inputs, size bands, disclosure rules, the dispute path), is not closed by this page.
**As at 23 November 2026.**

## What a fit assertion is

A fit assertion is a broad-brush reading of facts a party has declared, against the figures in `backend/data/reference/hk_screening_thresholds.json`. It names the Schedule 3 area test, any Schedule 2 item those facts meet, the planning-permission column if one was supplied, and whether an environmental assessment may be required on the TPB section 16 Guidance Notes. It carries the screening label, the assumption register, and the `furtherInformation` list.

The label is `BROAD_BRUSH_FIT_READ_NOT_A_STATUTORY_DETERMINATION`. `notADetermination` is true on every result.

## What a fit assertion is not

It is not an environmental permit, a section 16 decision, a section 12A decision, or a determination under the Environmental Impact Assessment Ordinance or the Town Planning Ordinance.

A current section 16 planning permission is not an environmental permit. Section 9(1) still requires an environmental permit for a Schedule 2 project. Section 9(2)(a) exempts only a permission granted before 1 April 1998. Section 9(5) means a Schedule 3 listing does not remove that need. The read does not determine whether section 9 has been contravened. Contravention of section 9 is an offence under section 26(1); naming that offence is not a finding that anyone has committed it.

A section 4(4) flag means contiguous projects by the same or associated persons may be specified. The read does not make that specification.

An HKPSG Table 1.3 note is a prompt to check against the guideline. It is not a pass and it is not a fail. The drainage deficit, the frontal-area figure, and the attribution interaction term are not substituted for a declared capacity, a noise buffer, or a specification.

A competition deck does not describe this read as a shipped statutory screening decision. F5 still holds.

## The label and the unknowns list

Every fit result and every screening-basis annex keeps both the screening label and the `furtherInformation` list. The assumption register is kept with them. Removing the label or the unknowns list fails validation (`tests/test_government_fit.py`). A commercial request to drop either one is a no, for the same reason E2 already gives: the label is the liability architecture, not decoration.

If a fact the threshold needs is absent, the result says so. It does not choose a figure that would make a gate fire, and it does not choose one that would make a gate go quiet.
