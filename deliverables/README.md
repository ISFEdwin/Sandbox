# Deliverables

Submission and working material that is not part of the product's source. Everything here is either a document a
person reads or an input to a script; nothing here is imported by `backend/` or `frontend/`.

The repository's canonical status is [STATUS.md](../STATUS.md). When a claim here disagrees with it, STATUS.md wins.

## What is here

| File | What it is | Tracked |
|---|---|---|
| `DEEPTECH100_SUBMISSION.md` | DeepTech100+ Cohort 8 entry checklist. Deadline 29 Nov 2026. **Interim**: the submission deck is being produced separately | yes |
| `PROMPT_criteria_fit_continue.md` | The working brief for the government criteria fit. Not a spec — the normative versions are [docs/GOVERNMENT_CRITERIA_FIT.md](../docs/GOVERNMENT_CRITERIA_FIT.md) and [docs/CODE_OF_PRACTICE.md](../docs/CODE_OF_PRACTICE.md) | yes |
| `competition_entry_essentials.plan.md` | The competition-entry plan: which product edges the demo has to show, with each item's state | yes |
| `Sandbox Pitch Deck (CCMF) Final.pptx` | The CCMF deck. Source for the cut below | **no** |
| `Sandbox Pitch Deck (DeepTech100+) v1.pptx` | Content base for the DeepTech100+ submission | **no** |

## Why the decks are not tracked

`.gitignore` excludes `deliverables/*.pptx`. They carry the fee schedule, competitor prices and partner targets, and
this repository is public (TODO E3). The reproducible cut is `scripts/build_deeptech_deck.py`, which carries no fees,
and `scripts/deck_diff.py` compares a submission deck against either base — including the 15-slide gate — without
either file entering git.

A clone therefore has the checklist and the plan, and builds the deck rather than receiving it.

## Adding something here

Put a document a person reads in this folder and add a row above. If it is a deck, work through
`scripts/build_deeptech_deck.py` so the committed artefact stays reproducible. Engineering specifications do **not**
belong here — they go in [docs/](../docs/), which is normative for its subject.
