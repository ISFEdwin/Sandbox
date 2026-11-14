"""The consent layer: what may be **declared**, as distinct from what may be computed.

The engine has one guard against a feature that rewrites too much of the study
area: a single intervention may not rework more than
:data:`sandbox_model.MAX_INTERVENTION_COVERAGE` of it, and all the active
interventions together may not rework more than
:data:`sandbox_model.MAX_TOTAL_COVERAGE`. Those numbers are right for a
*sandbox*, where the user is exploring and there is no counterparty to
object.

They are wrong for a *register*, where a feature is a **declaration**: a
developer's own massing, drainage and phasing, submitted for the record. A
declared project that reworks 30% of the district is not a mistake to be
refused -- it is a land-use change of a size the district has to know about,
and the thing that has to happen next is not "refuse it" but "the neighbours
of that change have to be asked".

So the cap moves here, out of the engine's arithmetic and into the layer that
decides what is allowed to be *declared*:

======================  ==========================  ==========================
Case                    Sandbox behaviour           Register behaviour
======================  ==========================  ==========================
Single feature > 25%    refuse, and report it      accept; flag it as a major
                                                    land-use change and require
                                                    a counter-signature from
                                                    the affected neighbours
Cumulative > 40%        refuse the excess feature   accept; flag it as a
                                                    district-scale composition
                                                    and trigger a joint review
A feature is fictional  refuse                      unchanged -- drafts are
(AI-proposed,                                             never computed on
unconfirmed)
======================  ==========================  ==========================

**The engine keeps a guard.** This module does not remove the refusal; it
moves *who* the refusal belongs to. A feature that nobody has declared is
still refused, exactly as before, because nothing has been asserted about it
and the engine is not in the business of computing on an invention. The
difference is what happens to a feature that **has** been declared and has
passed the consent layer: it is applied, and it is applied *with a flag*
rather than silently.

## What "declared" means here, and what it will mean

A declaration is the signed record of what a project asserts about its own
inputs (the register's core object, built in F1). A feature is **declared**
when it came from an accepted declaration.

Until F1 exists there is no declaration object, so this module reads the
marker a feature carries instead of resolving a declaration:

- ``params.declarationId`` -- the declaration the feature was built from.
  Present means the feature came from a declaration at all.
- ``params.declarationStatus`` -- that declaration's status, when the caller
  knows it. Only ``accepted`` counts: a draft or a submitted declaration has
  not been through review, and a feature built on one is still an assertion
  nobody has signed.

The status is optional because the plan that owns the features carries it, and
the feature loader copies it down (see ``app.routers.scenes.intervention_features``).
When F1 lands, the two markers are replaced by a resolved declaration, and
nothing else in the engine changes: the engine already asks this module the
only question it has.

## Why the flag, and not a refusal

A refusal is a closed door: the feature is not computed on, the numbers do
not move, and the planner is told what happened. That is the right answer
for an invention and the wrong answer for a declaration, because the whole
point of a register is that what was declared is *in* the record -- including
the parts of it that need a counter-signature. If the engine refused to
compute on a major land-use change, the register would be missing exactly the
information it exists to hold.

So a declared over-cap feature is applied, and the review it requires travels
with it: on the applied entry, and rolled up onto the scenario.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.services.sandbox_model import (
    MAX_INTERVENTION_COVERAGE,
    MAX_TOTAL_COVERAGE,
)

#: The two review levels. Named, because the coordination record refers to them
#: by name: a "major land-use change" is counter-signed by the affected
#: neighbours, a "district-scale composition" goes to a joint review.
LEVEL_MAJOR_CHANGE = "major_land_use_change"
LEVEL_DISTRICT_COMPOSITION = "district_scale_composition"

#: The declaration statuses that count as declared. A declaration that has not
#: been through review is not an assertion anybody has signed.
ACCEPTED_DECLARATION_STATUS = "accepted"


def feature_is_declared(feature: Mapping[str, Any]) -> bool:
    """Is this feature built from an accepted declaration?

    ``params.declarationId`` says the feature came from a declaration at all;
    ``params.declarationStatus``, when present, says whether that declaration
    has been accepted. A status of anything other than ``accepted`` -- a
    draft, a submitted declaration, an unknown value -- means the feature is
    not declared, and the engine's own refusal stands.
    """
    params = feature.get("params") or {}
    if not params.get("declarationId"):
        return False
    status = params.get("declarationStatus")
    if status is None:
        # The declaration is named but its status was not carried down. The
        # feature is treated as declared: the caller said it came from a
        # declaration, and the status check exists for the case where the
        # caller says otherwise.
        return True
    return str(status).lower() == ACCEPTED_DECLARATION_STATUS


def major_change_review(coverage: float) -> dict[str, Any]:
    """The review a single declared feature over the single-feature cap needs."""
    return {
        "required": True,
        "level": LEVEL_MAJOR_CHANGE,
        "coverageFraction": round(float(coverage), 5),
        "counterSignatureRequired": True,
        "jointReviewRequired": False,
        "why": (
            "the declared project reworks %.1f%% of the study area, over the "
            "%.0f%% threshold for a single intervention. It is a major land-use "
            "change, so it is computed on and recorded, and the neighbours it "
            "affects are asked to counter-sign it."
            % (100 * float(coverage), 100 * MAX_INTERVENTION_COVERAGE)
        ),
    }


def district_composition_review(total_coverage: float) -> dict[str, Any]:
    """The review a declared scenario over the cumulative cap needs."""
    return {
        "required": True,
        "level": LEVEL_DISTRICT_COMPOSITION,
        "totalCoverageFraction": round(float(total_coverage), 5),
        "counterSignatureRequired": False,
        "jointReviewRequired": True,
        "why": (
            "the declared projects rework %.1f%% of the study area between "
            "them, over the %.0f%% cumulative threshold. The composition is "
            "recorded as declared and goes to a joint review."
            % (100 * float(total_coverage), 100 * MAX_TOTAL_COVERAGE)
        ),
    }


def roll_up(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """The scenario-level view of the reviews its features require.

    ``required`` is true when anything needs a sign-off, and the levels are
    listed so a coordinator can see at a glance whether the question is a
    counter-signature or a joint review.
    """
    if not reviews:
        return {"required": False, "levels": [], "reasons": []}
    levels: list[str] = []
    reasons: list[str] = []
    for review in reviews:
        level = str(review.get("level") or "")
        if level and level not in levels:
            levels.append(level)
        why = review.get("why")
        if why:
            reasons.append(str(why))
    return {
        "required": True,
        "levels": levels,
        "reasons": reasons,
        "counterSignatureRequired": any(
            bool(r.get("counterSignatureRequired")) for r in reviews
        ),
        "jointReviewRequired": any(
            bool(r.get("jointReviewRequired")) for r in reviews
        ),
    }
