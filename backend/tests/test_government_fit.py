"""Broad-brush government-criteria fit at declaration intake.

The screen reads ``data/reference/hk_screening_thresholds.json``. These tests
lock the settled figures and the failures that would turn the read into a
determination: a coverage fraction treated as 50 ha, a road flagged by length,
a repealed test fired, a label or an unknowns list dropped, a superseded value
put back on a live entry.

Run:  python -m pytest tests/test_government_fit.py -q
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas.government_fit import SCREENING_LABEL, GovernmentFit  # noqa: E402
from app.services.government_fit import (  # noqa: E402
    ThresholdDrift,
    assert_no_superseded_value_is_live,
    government_fit,
    load_thresholds,
    render_screening_basis_annex,
)
from app.services.sandbox_model import MAX_INTERVENTION_COVERAGE  # noqa: E402

SIDECAR = BACKEND_DIR / "data" / "rasters" / "wetgrid_hsk.json"
client = TestClient(app)


def _doc() -> dict:
    return load_thresholds()


def _by_id(entry_id: str) -> dict:
    return next(entry for entry in _doc()["entries"] if entry["id"] == entry_id)


def _district_ha() -> float:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    return (
        sidecar["conditioning"]["cellsTotal"]
        * sidecar["inputs"]["cell_area_m2"]
        / 10_000.0
    )


def _items(fit: dict) -> list[str]:
    return [flag["item"] for flag in fit["schedule2"]]


def test_the_reference_file_keeps_the_settled_tests_and_the_repealed_ones() -> None:
    document = _doc()
    assert_no_superseded_value_is_live(document)
    schedule3 = _by_id("eiao.sch3.item1.area")
    assert schedule3["value"] == 50
    assert schedule3["unit"] == "ha"
    assert schedule3["comparator"] == "gt"
    assert schedule3["effectiveDate"] == "2023-06-30"
    assert schedule3["status"] == "current"
    assert schedule3["supersededBy"] is None
    assert schedule3["sourceUrl"] == "https://www.elegislation.gov.hk/hk/cap499!en/sch3"

    repealed_area = _by_id("eiao.sch3.area.pre-2023")
    assert repealed_area["value"] == 20
    assert repealed_area["unit"] == "ha"
    assert repealed_area["status"] == "repealed"
    assert repealed_area["supersededBy"] == "eiao.sch3.item1.area"

    population = _by_id("eiao.sch3.population.pre-2023")
    assert population["value"] == 100000
    assert population["unit"] == "persons"
    assert population["status"] != "current"

    study = _by_id("eiao.sch3.engineering_feasibility_study.pre-2023")
    assert study["status"] == "repealed"
    assert study["supersededBy"] == "eiao.sch3.item1.area"

    road = _by_id("eiao.sch2.a1")
    assert road["value"] is None
    assert road["lengthThreshold"] is None
    assert road["unit"] == "road-class"

    flats = _by_id("eiao.sch2.p2")
    assert flats["value"] == 2000
    assert flats["unit"] == "flats"
    assert flats["status"] == "repealed"
    assert flats["item"] == "P.2"

    misread = _by_id("hkpsg.residential.misread_20_10_5")
    assert misread["values"] == [20, 10, 5]
    assert misread["appliesTo"] == "residential"
    assert misread["status"] == "not_a_rule"
    for entry_id, value in (
        ("hkpsg.openspace.trunk_primary", 20),
        ("hkpsg.openspace.district", 10),
        ("hkpsg.openspace.local", 5),
    ):
        entry = _by_id(entry_id)
        assert entry["value"] == value
        assert entry["appliesTo"] == "active-open-space"
        assert entry["status"] == "current"

    plan = _by_id("ozp.s_hsk_4.identity")
    assert plan["value"] == "S/HSK/4"
    assert plan["approvedOn"] == "2026-09-29"
    assert plan["effectiveDate"] == "2026-10-09"


def test_putting_a_superseded_value_back_on_the_live_test_fails() -> None:
    document = copy.deepcopy(_doc())
    for entry in document["entries"]:
        if entry["id"] == "eiao.sch3.item1.area":
            entry["value"] = 20
    with pytest.raises(ThresholdDrift, match="superseded value reappeared"):
        assert_no_superseded_value_is_live(document)


def test_deleting_a_repealed_entry_fails() -> None:
    document = copy.deepcopy(_doc())
    document["entries"] = [
        entry for entry in document["entries"] if entry["id"] != "eiao.sch2.p2"
    ]
    with pytest.raises(ThresholdDrift, match="eiao.sch2.p2"):
        assert_no_superseded_value_is_live(document)


def test_a_length_put_back_on_a1_fails() -> None:
    document = copy.deepcopy(_doc())
    for entry in document["entries"]:
        if entry["id"] == "eiao.sch2.a1":
            entry["lengthThreshold"] = 100
    with pytest.raises(ThresholdDrift, match="length threshold"):
        assert_no_superseded_value_is_live(document)


def test_schedule3_follows_the_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """12 ha flags when the file says 10, and does not when the file says 50.

    10 ha is not the repealed 20 ha figure, so the drift guard allows the
    substitution. A screen that had hardcoded 50 ha would not flag 12 ha.
    """
    document = copy.deepcopy(_doc())
    for entry in document["entries"]:
        if entry["id"] == "eiao.sch3.item1.area":
            entry["value"] = 10
    monkeypatch.setattr(
        "app.services.government_fit.load_thresholds",
        lambda: document,
    )
    assert government_fit({"siteAreaHa": 12})["schedule3"]["triggered"] is True
    assert government_fit({"siteAreaHa": 9})["schedule3"]["triggered"] is False


def test_more_than_50_ha_is_flagged_and_50_ha_is_not() -> None:
    threshold = _by_id("eiao.sch3.item1.area")["value"]
    over = government_fit({"siteAreaHa": threshold + 0.01})
    exact = government_fit({"siteAreaHa": threshold})
    assert over["schedule3"]["triggered"] is True
    assert over["schedule3"]["flag"] == "review"
    assert over["notADetermination"] is True
    assert over["screeningLabel"] == SCREENING_LABEL
    assert exact["schedule3"]["triggered"] is False
    assert exact["schedule3"]["flag"] == "not_triggered"
    assert exact["schedule3"]["threshold"]["value"] == threshold
    assert any("Section 9(5)" in line for line in over["assumptions"])


def test_thirty_percent_of_the_district_is_not_50_ha() -> None:
    """The consent-layer 30% declaration is a share of this district, not Schedule 3."""
    district_ha = _district_ha()
    assert 0.30 > MAX_INTERVENTION_COVERAGE
    assert district_ha * 0.30 < _by_id("eiao.sch3.item1.area")["value"]
    fit = government_fit({
        "coverageFraction": 0.30,
        "districtAreaHa": district_ha,
    })
    area = fit["schedule3"]["siteAreaHa"]
    assert area == pytest.approx(district_ha * 0.30)
    assert area != 50
    assert fit["schedule3"]["triggered"] is False
    assert fit["schedule3"]["flag"] == "not_triggered"
    assert any(
        "coverage fraction is the share of the stated district area" in line
        for line in fit["assumptions"]
    )
    assert "P.2" not in _items(fit)


def test_a_coverage_fraction_without_a_district_area_is_not_turned_into_50_ha() -> None:
    fit = government_fit({"coverageFraction": 0.30})
    assert fit["schedule3"]["siteAreaHa"] is None
    assert fit["schedule3"]["triggered"] is False
    assert fit["schedule3"]["flag"] == "insufficient_facts"
    assert any(
        "A coverage fraction was declared and a district area in hectares was not."
        in line
        for line in fit["furtherInformation"]
    )


def test_a_conflicting_50_ha_label_on_a_30_percent_declaration_is_not_chosen() -> None:
    fit = government_fit({
        "coverageFraction": 0.30,
        "districtAreaHa": _district_ha(),
        "siteAreaHa": 50,
    })
    assert fit["schedule3"]["triggered"] is False
    assert fit["schedule3"]["flag"] == "insufficient_facts"
    assert fit["schedule3"]["siteAreaHa"] is None
    assert any("do not agree" in line for line in fit["furtherInformation"])


def test_road_class_alone_flags_a1_with_no_length() -> None:
    fit = government_fit({"roadClass": "district_distributor"})
    assert _items(fit) == ["A.1"]
    flag = fit["schedule2"][0]
    assert flag["threshold"]["value"] is None
    assert "A.1 has no length threshold" in flag["reason"]
    short = government_fit({"roadClass": "expressway", "roadLengthM": 1})
    assert "A.1" in _items(short)
    assert "was not used" in next(item["reason"] for item in short["schedule2"] if item["item"] == "A.1")


def test_a_local_distributor_is_not_a1_however_long_it_is() -> None:
    fit = government_fit({"roadClass": "local distributor", "roadLengthM": 5000})
    assert "A.1" not in _items(fit)
    assert any("local distributor" in line for line in fit["assumptions"])


def test_repealed_rules_do_not_fire() -> None:
    """25 ha, 100,000 people, 2,000 flats off sewer, and an 8 m local-road distance.

    The repealed area test, the repealed population test, P.2, and the
    20/10/5 m residential misreading would all have fired. None of them do.
    """
    residential = _by_id("hkpsg.residential.district_local")
    open_space = _by_id("hkpsg.openspace.local")
    fit = government_fit({
        "siteAreaHa": 25,
        "population": 100000,
        "flatCount": 2000,
        "servedByPublicSewerage": False,
        "use": "residential",
        "roadClass": "local_distributor",
        "roadLengthM": 5000,
        "roadScreening": False,
        "receiverDistanceRoadM": 8,
    })
    assert fit["schedule3"]["triggered"] is False
    assert "Population was supplied and was not used." in fit["schedule3"]["reason"]
    assert "P.2" not in _items(fit)
    assert "A.1" not in _items(fit)
    assert any("P.2 is repealed" in line for line in fit["assumptions"])
    assert any("eiao.sch2.p2" in line for line in fit["assumptions"])
    assert any("eiao.sch3.area.pre-2023" in line for line in fit["assumptions"])
    hkpsg = fit["hkpsg"]
    assert hkpsg["passFail"] is False
    assert hkpsg["advisoryOnly"] is True
    assert hkpsg["appliedOpenSpaceSeparationAsResidential"] is False
    assert hkpsg["residentialBufferM"] == residential["value"]
    assert hkpsg["residentialBufferM"] != open_space["value"]
    assert "Not a pass and not a fail." in hkpsg["note"]
    assert "were not applied as residential buffers" in hkpsg["note"]


def test_a_missing_receiver_distance_is_further_information_not_a_pass() -> None:
    fit = government_fit({"roadClass": "trunk"})
    assert fit["hkpsg"]["passFail"] is False
    assert fit["hkpsg"]["residentialBufferM"] is None
    assert any(
        "road receiver distance" in line and "not a pass" in line
        for line in fit["furtherInformation"]
    )


def test_p1_has_no_size_threshold_and_is_not_assumed_for_the_district() -> None:
    quiet = government_fit({"use": "residential", "siteAreaHa": 0.1})
    assert "P.1" not in _items(quiet)
    assert any(
        "Whether the site intersects Deep Bay Buffer Zone 1 or 2 was not read."
        in line
        for line in quiet["furtherInformation"]
    )
    flagged = government_fit({
        "use": "recreational",
        "siteAreaHa": 0.1,
        "deepBayBufferZone": "1",
        "nteh": False,
    })
    assert "P.1" in _items(flagged)
    assert flagged["schedule3"]["triggered"] is False
    exempt = government_fit({
        "use": "residential",
        "deepBayBufferZone": "2",
        "nteh": True,
        "flatCount": 2000,
        "servedByPublicSewerage": False,
    })
    assert "P.1" not in _items(exempt)
    assert "P.2" not in _items(exempt)


def test_c12_does_not_use_a_residential_distance() -> None:
    fit = government_fit({"dredgingM3": 1000, "dredgingResidentialM": 50})
    assert "C.12" not in _items(fit)
    assert any("C.12 has no residential limb" in line for line in fit["assumptions"])
    assert any("not treated as clear" in line for line in fit["furtherInformation"])


def test_c2_fires_on_area_and_a_residential_distance_and_not_on_area_alone() -> None:
    area = _by_id("eiao.sch2.c2.area")["value"]
    distance = _by_id("eiao.sch2.c2.residential_m")["value"]
    incomplete = government_fit({"reclamationHa": area + 0.1})
    assert "C.2" not in _items(incomplete)
    assert any("not a pass" in line for line in incomplete["furtherInformation"])
    flagged = government_fit({
        "reclamationHa": area + 0.1,
        "reclamationResidentialM": distance - 1,
    })
    assert "C.2" in _items(flagged)
    assert "C.1" not in _items(flagged)


def test_boundaries_are_strict() -> None:
    portal = _by_id("eiao.sch2.q2.portal_m")["value"]
    at = government_fit({"rockCavern": True, "rockCavernPortalM": portal})
    inside = government_fit({"rockCavern": True, "rockCavernPortalM": portal - 0.01})
    assert "Q.2" not in _items(at)
    assert "Q.2" in _items(inside)


def test_section_4_4_flags_and_does_not_assert_aggregation() -> None:
    fit = government_fit({"contiguousSameOrAssociatedPersons": True})
    assert fit["section44"]["flag"] == "possible_specification"
    assert fit["section44"]["assertedAggregation"] is False
    text = json.dumps(fit)
    assert "Secretary has aggregated" not in text
    assert "possible specification" in fit["section44"]["note"]


def test_a_current_planning_permission_is_not_an_environmental_permit() -> None:
    fit = government_fit({
        "ozpColumn": "2",
        "planningPermissionDate": "2026-09-29",
        "roadClass": "trunk",
    })
    permission = fit["planningPermission"]
    assert permission["route"] == "s16"
    assert permission["isEnvironmentalPermit"] is False
    assert permission["permissionPredatesEiao"] is False
    assert "not an environmental permit" in permission["note"]
    assert any("section 9(1)" in line.lower() or "section 9(1)" in line for line in fit["assumptions"])


def test_hsk_claims_stay_at_plan_identity() -> None:
    fit = government_fit({})
    assert fit["asAt"]["hskHtPlan"] == "S/HSK/4"
    joined = " ".join(fit["furtherInformation"])
    assert "The zone-by-zone Notes of S/HSK/4 were not read." in joined
    assert "intersects Deep Bay Buffer Zone 1 or 2 was not read" in joined
    assert "section 5(9), 5(10) or 5(11) is available was not read" in joined
    assert "the site is inside Deep Bay" not in joined
    assert "the site does intersect" not in joined


def test_removing_the_screening_label_fails() -> None:
    fit = government_fit({"siteAreaHa": 1})
    broken = dict(fit)
    del broken["screeningLabel"]
    with pytest.raises(ValidationError):
        GovernmentFit.model_validate(broken)
    with pytest.raises(ValidationError):
        render_screening_basis_annex(broken)


def test_removing_the_unknowns_list_fails() -> None:
    fit = government_fit({"siteAreaHa": 1})
    emptied = dict(fit)
    emptied["furtherInformation"] = []
    with pytest.raises(ValidationError):
        GovernmentFit.model_validate(emptied)
    with pytest.raises(ValidationError):
        render_screening_basis_annex(emptied)
    deleted = dict(fit)
    del deleted["furtherInformation"]
    with pytest.raises(ValidationError):
        GovernmentFit.model_validate(deleted)


def test_the_annex_pastes_the_file_figures_and_the_unknowns() -> None:
    fit = government_fit({"siteAreaHa": 60, "roadClass": "primary"})
    annex = render_screening_basis_annex(fit)
    applied, _, superseded = annex.partition("Superseded tests not applied")
    assert "Broad-brush fit read, not a statutory determination." in annex
    assert SCREENING_LABEL in annex
    assert "https://www.elegislation.gov.hk/hk/cap499!en/sch3" in applied
    assert "eiao.sch3.item1.area" in applied
    assert "eiao.sch3.area.pre-2023" not in applied
    assert "eiao.sch2.p2" not in applied
    assert "eiao.sch3.area.pre-2023" in superseded
    assert "eiao.sch2.p2" in superseded
    assert "hkpsg.residential.misread_20_10_5" in superseded
    assert "Further information" in annex
    assert fit["furtherInformation"][0] in annex
    assert "not a pass or a fail" in annex
    assert "Zone Notes were not read." in annex


def test_intake_route_returns_the_fit_and_the_annex() -> None:
    response = client.post(
        "/api/declarations/intake",
        json={"siteAreaHa": 60, "roadClass": "trunk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["governmentFit"]["notADetermination"] is True
    assert body["governmentFit"]["schedule3"]["triggered"] is True
    assert "A.1" in _items(body["governmentFit"])
    assert "Broad-brush fit read, not a statutory determination." in body["screeningBasisAnnex"]
    assert body["governmentFit"]["screeningLabel"] == SCREENING_LABEL
