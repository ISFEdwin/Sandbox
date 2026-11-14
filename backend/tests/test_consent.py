"""The coverage guards, and who owns them: the consent layer (F13).

The engine's guard against a feature that rewrites too much of the study area
used to be a flat refusal: over 25% for one intervention, over 40% for the
scenario, refused, full stop. That is right for a sandbox and wrong for a
register, where a feature is a **declaration** -- a developer's own massing,
drainage and phasing, submitted for the record.

The behaviour now depends on whether the feature has been declared:

- an **undeclared** feature over the cap is refused, exactly as before;
- a **declared** one is applied and flagged: a major land-use change needs a
  counter-signature from the affected neighbours, a district-scale composition
  goes to a joint review.

These are the three acceptance tests the plan names, restated as tests
(PLAN W0.6):

1. a declared 30% project is **not** dropped;
2. an unconfirmed draft 30% feature **is** refused;
3. crossing the threshold **triggers a joint review**.

The geometry is built here, in code, rather than read from the store: a guard
tested by whatever happens to be lying on disk is not a guard.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _extra in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from app.services.sandbox_model import (  # noqa: E402
    MAX_INTERVENTION_COVERAGE,
    MAX_TOTAL_COVERAGE,
    _polygon_cells,
    ledger_for_scenario,
    load_grids,
)


def _grids():
    grids = load_grids()
    assert grids is not None, "no ledger grid: run scripts/make_wetgrid.py"
    return grids


def _band(grids, fraction: float) -> list[list[float]]:
    """A rectangle over the western ``fraction`` of the study area.

    Sized by *columns*, so the cell count it covers is about the fraction
    asked for regardless of the grid's shape.
    """
    min_lon, min_lat, max_lon, max_lat = grids.bounds
    lon = min_lon + (max_lon - min_lon) * fraction
    return [
        [min_lon, min_lat],
        [lon, min_lat],
        [lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]


def _feature(kind: str, ring: list[list[float]],
             declared: bool = False, status: str | None = None) -> dict:
    """One intervention feature, optionally built from an accepted declaration."""
    params: dict = {}
    if declared:
        params["declarationId"] = "dec-0001"
        if status is not None:
            params["declarationStatus"] = status
    return {
        "id": "f-1",
        "intervention_type": kind,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "params": params,
    }


def test_a_declared_project_over_the_cap_is_not_dropped() -> None:
    """A declared 30% project is applied, and flagged for a counter-signature.

    The point of the whole re-specification: what was declared is *in* the
    record, even the part of it that is large. Refusing it would drop exactly
    the information the register exists to hold.
    """
    grids = _grids()
    ring = _band(grids, 0.30)
    coverage = len(_polygon_cells(grids, ring)) / float(grids.rows * grids.cols)
    assert coverage > MAX_INTERVENTION_COVERAGE, (
        "the fixture must be over the single-feature cap: %.1f%%" % (100 * coverage)
    )

    ledger = ledger_for_scenario(grids, [_feature("green_space", ring, declared=True)])

    assert not ledger["interventionsSkipped"], (
        "a declared project over the cap was dropped: %s"
        % ledger["interventionsSkipped"]
    )
    applied = ledger["interventionsApplied"]
    assert len(applied) == 1, "the declared project was not applied"
    review = applied[0].get("consentReview")
    assert review, "the declared project carries no consent review"
    assert review["required"] is True
    assert review["level"] == "major_land_use_change"
    assert review["counterSignatureRequired"] is True


def test_an_unconfirmed_draft_over_the_cap_is_refused() -> None:
    """An undeclared 30% feature is refused, exactly as before.

    A draft is never computed on. The guard is unchanged for anything nobody
    has declared, which is what keeps the sandbox's own safety intact.
    """
    grids = _grids()
    ring = _band(grids, 0.30)

    ledger = ledger_for_scenario(grids, [_feature("green_space", ring)])

    assert ledger["interventionsSkipped"], "an undeclared 30% feature was applied"
    skipped = ledger["interventionsSkipped"][0]
    assert "over the" in skipped["why"] and "%" in skipped["why"], skipped["why"]
    assert not ledger["interventionsApplied"], (
        "the refused feature was applied anyway: %s" % ledger["interventionsApplied"]
    )


def test_a_declaration_that_is_not_accepted_is_not_declared() -> None:
    """A draft or submitted declaration does not buy its feature a pass.

    The status marker is the difference between "somebody declared this" and
    "somebody's declaration was accepted". Only the second one is an assertion
    the register can act on.
    """
    grids = _grids()
    ring = _band(grids, 0.30)

    for status in ("draft", "submitted"):
        ledger = ledger_for_scenario(
            grids, [_feature("green_space", ring, declared=True, status=status)]
        )
        assert ledger["interventionsSkipped"], (
            "a %s declaration was treated as accepted" % status
        )


def test_crossing_the_threshold_triggers_a_joint_review() -> None:
    """A declared scenario over the cumulative cap goes to a joint review.

    Two declared features that together rework more than the cumulative cap
    are applied, and the scenario reports that a joint review is required --
    at the scenario level, because the composition is a property of the
    scenario and not of either project.
    """
    grids = _grids()
    site_cells = float(grids.rows * grids.cols)
    min_lon, min_lat, max_lon, max_lat = grids.bounds
    west = _band(grids, 0.30)
    east = [
        [min_lon + (max_lon - min_lon) * 0.55, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon + (max_lon - min_lon) * 0.55, max_lat],
        [min_lon + (max_lon - min_lon) * 0.55, min_lat],
    ]
    total = len(set(_polygon_cells(grids, west)) | set(_polygon_cells(grids, east))) \
        / site_cells
    assert total > MAX_TOTAL_COVERAGE, (
        "the fixture must be over the cumulative cap: %.1f%%" % (100 * total)
    )

    features = [
        _feature("green_space", west, declared=True),
        _feature("flood_storage", east, declared=True),
    ]
    ledger = ledger_for_scenario(grids, features)

    assert not ledger["interventionsSkipped"], (
        "a declared scenario over the cap was dropped: %s"
        % ledger["interventionsSkipped"]
    )
    review = ledger["consentReview"]
    assert review["required"] is True, "the scenario reports no review"
    assert review["jointReviewRequired"] is True, review
    assert "district_scale_composition" in review["levels"], review


def test_an_ordinary_scenario_needs_no_review() -> None:
    """Nothing under the caps, declared or not, carries a review flag."""
    grids = _grids()
    ring = _band(grids, 0.05)
    ledger = ledger_for_scenario(grids, [_feature("green_space", ring, declared=True)])
    assert ledger["consentReview"]["required"] is False, ledger["consentReview"]
