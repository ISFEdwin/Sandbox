# DeepTech100+ Cohort 8 — submission checklist

HKU TEC + HKSTP. Deadline **29 Nov 2026, 23:59 HKT**. The programme feeds HKSTP Ideation (up to HK$100k, three
milestone tranches) and Incubation (up to HK$1.29M); up to HK$1.39M in total. Sources checked 26 Nov 2026:
<https://tec.hku.hk/deeptech100/>.

The repository's ground truth is [STATUS.md](../STATUS.md) §13 and [TODO.md](../TODO.md) §F10. This page is the
submission view of them.

> **Status 26 Nov 2026: interim.** The team is producing a separate version of the deck for submission.
> `Sandbox Pitch Deck (DeepTech100+) v1.pptx` is the content base, not the file that will be uploaded, and nothing
> here closes the 29 Nov gate. When the submission deck arrives, diff it against the CCMF source and against v1 with
> `scripts/deck_diff.py` before it goes up, and check it against *Claims to keep exactly as written* below.

## The package

| Item | State |
|---|---|
| Pitch deck, **max 15 slides**, English or Chinese | **Interim** — `Sandbox Pitch Deck (DeepTech100+) v1.pptx` is the content base; a separate submission version is in progress |
| Proof of the Person-in-Charge's HKU association (student ID, graduation certificate or staff card) | **Open** — upload in the Qualtrics form |
| Completed Qualtrics application form | **Open** |
| HKU IP licence agreement or completed declaration form | **Not applicable** unless the venture uses HKU-held IP |
| HKU TEC pitch deck template | **Open** — v1 is not built on it; if the submission version adopts it, the content below moves across unchanged |

## Eligibility, against the published rules

- **Person-in-Charge:** an HKU member (student, staff, alumnus or HKU-affiliated institution member) aged 18+ with a
  valid HKID, or a director of an existing or prospective HKU IP licensee. Bernice, Edwin, Katie and Chloe are HKU;
  Chen Xu is HKBU and cannot be the PIC. Pick one of the four and use that person in the form.
- **Company:** not required to apply. If approved, incorporate a Hong Kong limited company. If already incorporated,
  it must be a Hong Kong limited company less than 24 months old at the programme start date. HKU member(s) must
  hold at least **20% equity**.
- **Project:** a deep-tech venture supported by R&D and a clear commercialisation plan. The engine, the grounded AI
  layer and the Hong Kong reference data are the R&D content; slide 13 carries the build evidence.

## What changed from the CCMF deck

The CCMF deck was 17 slides, CCMF-branded, with CCMF's 10k/45k/45k disbursement schedule and a six-month timeline.
It could not be submitted to this programme. The interim file is a 15-slide cut, made by
`scripts/build_deeptech_deck.py`; the CCMF file is untouched, and that script is the reproducible record of every
edit, which is what the submission version should be checked against.

- **Two slides removed.** The product overview (facts live on slides 2, 5 and 7) and the illustrative Hung Shui Kiu
  scenario with its example 18% (workflow lives on slides 2 and 5). Both survive in the speaker notes of slide 1.
- **Cover** — "HKU DEEPTECH100+ · COHORT 8", not CCMF.
- **Ask** — "Ideation funding", milestones 1/2/3, a route into HKSTP Incubation up to HK$1.29M, and a speaker note
  saying the 10/45/45 split is our proposal because HKSTP sets the final milestone schedule.
- **Timeline** — months 1–12 of the Ideation year; DeepTech100+ result Jan–Feb 2027; HKSTP Incubation, not
  Cyberport.
- **Proof numbers recomputed 26 Nov 2026** — 47 `/api` paths, 333 backend tests, 212 commits. The previous 46 / 247 /
  185 were stale or used a counting method the repository does not reproduce.
- **G9 line added** to the approval-path footnote — two gates, EIAO and town planning, broad-brush fit read only.

## Verified in this pass

- `pytest` 333 passed, 82 s; per-file dual-runner loop 0 failures.
- Frontend 133 tests passed; `tsc --noEmit` and `eslint --max-warnings 0` clean.
- `https://sandbox-azure-five.vercel.app` returns 200.
- The deck converts to PDF and its 15 pages carry the expected titles in order.

## Claims to keep exactly as written

The deck is deliberately more conservative than the pitch. Do not upgrade these in the form:

- **No paying customers.** Slide 8 says two interviews and no revenue.
- **Attribution is a specification, not an endpoint.** Nothing in the deck claims a live inherited-versus-caused
  split. Do not add one to the form.
- **Screening, never a determination.** Flood, heat and criteria output is broad-brush; slide 4 and the parameter
  card say so.
- **The 18% example is gone from the slides.** If asked for a measured number, there is not one yet.

## Before pressing submit

1. Choose the Person-in-Charge and prepare the HKU proof.
2. Land the submission version of the deck. Then diff it — against the CCMF source for anything carried over
   unchanged, and against v1 for the 15-slide content base — with
   `python3 scripts/deck_diff.py "deliverables/<submission>.pptx"`. Check the hard limits it reports: slide count,
   page numbers, and any figure that moved.
3. Rehearse the final slides against the speaker notes, which carry the timings and the two dropped slides.
4. Check the deck opens in PowerPoint, not only in LibreOffice, and that the embedded fonts render.
5. Have the demo open in a second tab, and keep the runtime store clean on the demo machine (TODO E5/F9).
6. Do not force-add the deck to git. `deliverables/*.pptx` is ignored because the repository is public and the deck
   carries the fee schedule (TODO E3).
