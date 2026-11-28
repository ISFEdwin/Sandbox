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
| `Sandbox Pitch Deck (CCMF) Final.pptx` | The CCMF deck. Source for the cut below | yes |
| `Sandbox Pitch Deck (DeepTech100+) v1.pptx` | Content base for the DeepTech100+ submission | yes |
| `Sandbox Pitch Deck (Seed X).pdf` | The 20-slide deck reviewed on 27 Nov 2026 | yes |
| `deck_review/` | The annotated review of the Seed X deck: slide-by-slide notes, a claims audit against STATUS, and a 20→15 restructure for DeepTech100+ | yes |
| `qa/seed-x-deeptech-review/` | Page renders of the Seed X deck, for checking an annotation against the slide it refers to | yes |

## The decks are tracked — read this before adding one

Everything in `deliverables/` is committed. That is a deliberate reversal: until 27 Nov 2026 `.gitignore` excluded
`deliverables/*.pptx` because a deck carries the fee schedule, competitor prices and partner targets, and this
repository is public (TODO E3). The decks are now kept as context for whoever writes the next submission.

**What that publishes**, deliberately: the proposed prices (HK$30k evaluation, HK$80–150k firm licence, HK$500k
technology licence), the market table, competitor prices, and one named firm used as an example of a target profile.

Two consequences:

- **It cannot be undone by later ignoring.** `git rm --cached` stops tracking a file; it does not remove it from the
  history someone already cloned. A fee that goes up once stays readable.
- **AGENTS.md §3 rule 4 and TODO E3 still say no fee figures belong in this repository.** They are now behind this
  decision rather than ahead of it, and the repository contradicts itself until they are rewritten or the block above
  in `.gitignore` is restored.

The reproducible cut is still `scripts/build_deeptech_deck.py`, and `scripts/deck_diff.py` still compares a submission
deck against either base, including the 15-slide gate. Both are worth running before a deck is committed.

## Adding something here

Put a document a person reads in this folder and add a row above. If it is a deck, work through
`scripts/build_deeptech_deck.py` so the committed artefact stays reproducible, and remember that committing it
publishes whatever it says about price. Engineering specifications do **not** belong here — they go in
[docs/](../docs/), which is normative for its subject.
