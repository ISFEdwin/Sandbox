# Attribution: what "inherited" and "caused" mean

**Status:** draft for Engineering sign-off (TODO A2, STATUS §4.2 B5). Not yet implemented.
**Date:** 14 Nov 2026. **Scope:** the definition only. The implementation is F5.

This document exists because the product's central claim — *sell attribution, not simulation* — is
currently undefined, and an undefined claim is one a competitor can define more conveniently. It is
written to be attached to a contract without asking what it means, so it states the terms precisely and
names what it deliberately does not say.

---

## 1. The three terms

Let `L(S)` be the district ledger for a set of active projects `S` — the buffer deficit, in m³, computed
by the engine on the composed land cover at the baseline design storm. Let `L(∅)` be the same ledger with
no project active.

For a project `P` under examination, in a scenario with active set `S`:

| Term | Definition | Plain meaning |
|---|---|---|
| **Inherited** | `L(S \ {P})` | The condition the project found when it arrived: the district without it |
| **Caused** | `L(S) − L(S \ {P})` | The project's **marginal** contribution to the district as it stands |
| **Interaction** | `L(S) − L(∅) − Σ_P [L(S) − L(S \ {P})]` | What the projects do *together* that none does alone |

The **reconciliation identity** holds by construction:

```
Σ_P caused(P) + interaction  ==  L(S) − L(∅)          (the total effect)
```

so the three terms always sum to the total effect, exactly, with no residual term to argue about.

## 2. Why "caused" is the leave-one-out marginal

"Caused" is **not** the standalone effect `L({P}) − L(∅)`. The standalone effect is order-dependent: with
two projects on overlapping ground, "what did P cause" depends on whether you added P before or after Q.
The leave-one-out marginal does not have that problem — removing `P` from the district as it actually
stands and measuring what changes is the same measurement whatever the order the projects were added in.

The price is that the marginal is not additive, and that is what the interaction term is for. The three
terms together are complete; any two of them are not.

## 3. The measured behaviour this definition has to handle

Grid: 117 × 148 cells at 25.12 m²/cell = 43.50 ha. Baseline design storm 50 mm: 9,056.8 m³ unstored,
17,379.4 m³ runoff. Measured 14 Nov 2026.

| Case | A alone | B alone | Sum | Combined | Residual |
|---|---|---|---|---|---|
| MTR station + park (disjoint, real seeded projects) | −32.93 m³ | −26.83 m³ | −59.77 m³ | −59.77 m³ | **0.00 m³** |
| Two green spaces, 50% footprint overlap | −153.08 m³ | −125.63 m³ | −278.71 m³ | −205.52 m³ | **+73.18 m³** |
| Routed flood area, same overlapping pair | −0.0528 ha | −0.0126 ha | −0.0653 ha | −0.0553 ha | **+0.0100 ha** |

**This table is the product thesis.** With disjoint footprints the split is exact, and the register hands a
developer a clean number. With overlapping footprints, **26% of the effect is attributable to neither
party alone** — and that 26% is exactly what EIAO Technical Memorandum §4.3.4(c) asks about when it
requires cumulative effects "where projects interact". A register that published only per-project numbers
would publish a number that does not add up. Publishing the interaction term is what makes the register
*more* credible, not less: it is the only way to publish a per-project figure and still be able to add the
figures up.

## 4. Where the interaction sits

The interaction term is a number without a location, and a number without a location cannot be reviewed.
The specification therefore pairs the decomposition with **cell ownership**: each 5 m cell is attributed to
the project or projects that changed it, and the interaction is reported over the cells where two or more
projects changed the same ground.

The two are not alternatives and neither is sufficient alone:

- **Leave-one-out** gives *how much*, and is the only definition of "caused" that reconciles.
- **Cell ownership** gives *where*, and is the only way to point a reviewer at the ground the interaction
  is about.

The reconciliation test asserts the two agree: the sum of the owned-cell contributions, per project, must
reproduce the leave-one-out marginal to within the same tolerance the ledger itself uses.

## 5. Which axes are attributed, and which are not

The engine reports three axes separately and never combines them: drainage volume, surface temperature,
wind geometry.

| Axis | Attributed per project? | Why |
|---|---|---|
| Drainage volume (buffer deficit) | **Yes** | The decomposition above is defined on it, and it reconciles exactly |
| Land-cover area change | **Yes** | Additive by construction: a cell changes class once |
| Surface temperature | **Yes, with the same caveat as volume** | It is a linear function of the composed land cover, so the marginal is well defined |
| Routed flood extent | **No — aggregate only** | See below |

**Routed flood extent is not published as a per-project figure.** The flood-extent axis routes through a
D8 cascade with a depth threshold, so it is non-linear by construction and its residual — 15% in the
measured case above, against 26% for the volume axis — will always exceed the volume axis's. The
register publishes flood extent **at district level only**, and reports the per-project margin as a
*range*, saying so.

**Never publish a per-project flood extent that does not reconcile.** A number that does not add up is
worse than no number: it is a number a reviewer will find wrong, and finding it wrong costs the register
more than omitting it.

## 6. What this document does not say

- **It does not certify risk.** The register does not own a hydrology verdict. The declaring party signs
  its inputs; the engine computes on those inputs and is liable for nothing, because it is arithmetic; the
  keeper is liable only for the record's integrity. Every attributed figure carries the screening label
  and the assumption register it was computed under.
- **It does not assign legal responsibility.** "Caused" here is a marginal contribution to a screening
  number under a stated storm. It is not a finding of causation, and it must not be presented as one.
- **It does not survive a change of storm.** Every attributed figure is computed at the baseline design
  storm (50 mm, settled 14 Nov 2026 — see `app.config.DEFAULT_RAINFALL_MM`). The attribution is a
  statement about that storm, and the storm is part of the record, not an ambient assumption.
- **It does not cover phasing.** With construction phasing, "the condition the project found when it
  arrived" depends on *when* it arrives, and the baseline must be composed as at a date rather than as it
  stands. Phasing is a separate feature (F6) and this definition extends to it unchanged; it does not
  define it.

## 7. Open questions for the sign-off

These are the points this draft does not decide on its own. Each needs Engineering, and each is marked
here rather than buried.

1. **Sign-off of the definitions themselves** (STATUS §4.2 B5): the three terms, the leave-one-out basis
   for "caused", and the reconciliation identity. Everything else follows from these.
2. **Tolerance.** The identity holds exactly in exact arithmetic; in floating point it holds to within
   the ledger's own tolerance. The acceptance test is `tests/test_attribution.py::
   test_attribution_reconciles_to_the_total`, asserting the sum to within 1e-9 m³. Whether that tolerance
   is the right one for a screening figure, or whether it should be looser and stated as a fraction of the
   total effect, is a judgement the sign-off should make.
3. **Cell-ownership precedence.** Where two projects changed the same cell, the cell can be attributed to
   both (split), to the later declaration (precedence), or left unowned (the interaction). The
   reconciliation test in §4 is what chooses: only a rule that reproduces the leave-one-out marginal is
   admissible.
4. **The number of run evaluations.** Leave-one-out costs `n + 1` runs for `n` projects. For a district
   of fifty projects that is fifty-one runs per attribution. Whether that is affordable at the pilot's
   scale, or whether a restricted form (a fixed set of reference projects) is acceptable, is a product
   decision with a cost attached.

## 8. Acceptance

The definition is done when:

- the three terms are implemented as an `attribution` object in the schema, with the reconciliation
  identity asserted by a test;
- the cell-ownership report agrees with the leave-one-out marginal to the tolerance the sign-off
  chooses;
- the flood-extent rule of §5 holds: no per-project flood extent is published anywhere, and the
  aggregate figure says what it is;
- every attributed figure carries the storm, the assumption register and the screening label it was
  computed under.

Until then, the product's central claim is undefined, and this document is the proposal that will be
adopted or replaced.
