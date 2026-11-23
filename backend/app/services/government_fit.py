"""Broad-brush fit of a declaration against the published Hong Kong gates.

The figures come from ``data/reference/hk_screening_thresholds.json``. A
repealed entry stays in that file so it can be seen, and it is not applied.
If a superseded value is put back on a live entry, the read is refused.

The result is a fit read. It is not a determination under the EIAO or the
Town Planning Ordinance, and it does not assert that the Secretary has
specified contiguous projects under section 4(4). A missing fact is listed
in ``furtherInformation``. It is not filled in.

Hung Shui Kiu–Ha Tsuen is named only as the plan identity on the reference
file (S/HSK/4). Zone Notes, Deep Bay Buffer Zone overlap, receiver distances
and the direct environmental-permit route were not read.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Mapping

from app.config import settings
from app.schemas.government_fit import (
    SCREENING_LABEL,
    DeclarationIntake,
    GovernmentFit,
)

# Product convention for two statements of one area. It is float noise, not a
# statutory tolerance, and it is not a Schedule 3 figure.
_AREA_NOISE_HA = 1e-4

_RETIRED_IDS = (
    "eiao.sch3.area.pre-2023",
    "eiao.sch3.population.pre-2023",
    "eiao.sch3.engineering_feasibility_study.pre-2023",
    "eiao.sch2.p2",
    "hkpsg.residential.misread_20_10_5",
)

_REQUIRED_KEYS = (
    "id",
    "family",
    "role",
    "status",
    "value",
    "unit",
    "sourceUrl",
    "effectiveDate",
    "supersededBy",
)

_EA_USES = {
    "cda",
    "comprehensive_development_area",
    "residential",
    "school",
    "religious",
    "religious_institution",
    "hospital",
    "residential_care",
    "residential_care_home",
    "concrete_batching",
    "concrete_batching_plant",
    "asphalt",
    "asphalt_plant",
    "slaughterhouse",
}
_SMALL_USES = {"shop", "eating_place", "off_course_betting", "enclosed_substation"}
_NTEH_USES = {
    "nteh",
    "new_territories_exempted_house",
    "new_territories_exempted_houses",
}
_P1_USES = {"residential", "recreational"}
_ROAD_ALIASES = {
    "primary": "primary_distributor",
    "district": "district_distributor",
    "local": "local_distributor",
}
_HKPSG_ROAD = {
    "trunk": "hkpsg.residential.trunk",
    "primary_distributor": "hkpsg.residential.primary",
    "district_distributor": "hkpsg.residential.district_local",
    "local_distributor": "hkpsg.residential.district_local",
}
_HKPSG_RAIL = {
    "mtr": "hkpsg.rail.mtr",
    "kcr": "hkpsg.rail.kcr",
    "lrt": "hkpsg.rail.lrt",
}


class ThresholdDrift(RuntimeError):
    """The threshold file brought a superseded value back, or dropped one."""


def thresholds_path():
    return settings.data_dir / "reference" / "hk_screening_thresholds.json"


def load_thresholds() -> dict[str, Any]:
    """The reference file. Read on each call so a test can substitute it."""
    path = thresholds_path()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ThresholdDrift(f"screening thresholds could not be read: {path}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("entries"), list):
        raise ThresholdDrift("screening thresholds file has no entries list")
    return document


def _values_of(entry: Mapping[str, Any]) -> list[Any]:
    listed = entry.get("values")
    if listed:
        return list(listed)
    if entry.get("value") is not None:
        return [entry["value"]]
    return []


def _collides(live: Mapping[str, Any], retired: Mapping[str, Any]) -> bool:
    """True when a live entry carries a retired entry's family and value."""
    if live.get("family") != retired.get("family"):
        return False
    retired_values = _values_of(retired)
    if not retired_values:
        return True
    if live.get("unit") != retired.get("unit"):
        return False
    return any(value in retired_values for value in _values_of(live))


def assert_no_superseded_value_is_live(document: Mapping[str, Any]) -> None:
    """Refuse a file that puts a superseded value back into use.

    Repealed entries have to remain, with ``supersededBy`` set. Deleting them
    is the same failure as promoting their value onto a current entry.
    """
    if document.get("label") != SCREENING_LABEL:
        raise ThresholdDrift("threshold file label drifted")
    if document.get("notADetermination") is not True:
        raise ThresholdDrift("threshold file dropped notADetermination")
    if not document.get("schedulesPointInTime") or not document.get("readOn"):
        raise ThresholdDrift("as-at dates missing from the threshold file")

    entries = document["entries"]
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)):
        raise ThresholdDrift("duplicate threshold id")
    id_set = set(ids)
    live: list[Mapping[str, Any]] = []
    retired: list[Mapping[str, Any]] = []

    for entry in entries:
        for key in _REQUIRED_KEYS:
            if key not in entry:
                raise ThresholdDrift(f"{entry.get('id')} missing {key}")
        source = entry["sourceUrl"]
        if not isinstance(source, str) or not source.startswith("https://"):
            raise ThresholdDrift(f"{entry['id']} has no source URL")
        status = entry["status"]
        successor = entry["supersededBy"]
        if status == "current":
            if successor is not None:
                raise ThresholdDrift(f"{entry['id']} is current and names a successor")
            live.append(entry)
        else:
            if not successor:
                raise ThresholdDrift(f"{entry['id']} is {status} and supersededBy is empty")
            retired.append(entry)
        if successor is not None and successor not in id_set and successor != "repealed":
            raise ThresholdDrift(f"{entry['id']} supersededBy {successor} does not resolve")
        if entry["id"] == "eiao.sch2.a1":
            if entry["value"] is not None or entry.get("lengthThreshold") is not None:
                raise ThresholdDrift("A.1 is road class only; a length threshold reappeared")
        if entry["role"] in {"test", "advisory", "as-at", "identity"} and status == "current":
            if not entry.get("effectiveDate"):
                raise ThresholdDrift(f"{entry['id']} has no effective date")

    index = {entry["id"]: entry for entry in entries}
    for retired_id in _RETIRED_IDS:
        entry = index.get(retired_id)
        if entry is None or entry["status"] == "current" or not entry["supersededBy"]:
            raise ThresholdDrift(f"{retired_id} must stay on file as superseded, not as a live rule")

    for old in retired:
        for current in live:
            if _collides(current, old):
                raise ThresholdDrift(
                    f"superseded value reappeared: {old['id']} on live {current['id']}"
                )

    misread = index.get("hkpsg.residential.misread_20_10_5")
    banned = set(_values_of(misread)) if misread else set()
    if not banned:
        raise ThresholdDrift("the open-space distances misread as residential buffers are missing")
    for entry in live:
        if entry.get("unit") == "m" and entry.get("value") in banned:
            if entry.get("appliesTo") != "active-open-space":
                raise ThresholdDrift(
                    f"{entry['id']} reintroduces {entry['value']} m outside the open-space row"
                )


def _index(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {entry["id"]: entry for entry in document["entries"]}


def _live(index: Mapping[str, Mapping[str, Any]], entry_id: str) -> Mapping[str, Any]:
    try:
        entry = index[entry_id]
    except KeyError as exc:
        raise ThresholdDrift(f"missing threshold {entry_id}") from exc
    if entry["status"] != "current" or entry["supersededBy"] is not None:
        raise ThresholdDrift(f"{entry_id} is not a live rule")
    return entry


def _fmt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, str):
        return value
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _same(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    return left == right


def _gt(amount: float, entry: Mapping[str, Any]) -> bool:
    if entry.get("comparator") != "gt":
        raise ThresholdDrift(f"{entry['id']} comparator is not gt")
    return amount > float(entry["value"])


def _lt(amount: float, entry: Mapping[str, Any]) -> bool:
    if entry.get("comparator") != "lt":
        raise ThresholdDrift(f"{entry['id']} comparator is not lt")
    return amount < float(entry["value"])


def _snap(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "value": entry["value"],
        "unit": entry["unit"],
        "comparator": entry.get("comparator"),
        "source_url": entry["sourceUrl"],
        "effective_date": entry.get("effectiveDate"),
        "superseded_by": entry.get("supersededBy"),
    }


def _flag(item: str, reason: str, entry: Mapping[str, Any]) -> dict[str, Any]:
    if item == "P.2" or entry.get("item") == "P.2" or entry["status"] != "current":
        raise ThresholdDrift(f"refusing to flag {item} from {entry['id']}")
    return {
        "item": item,
        "triggered": True,
        "reason": reason,
        "threshold": _snap(entry),
    }


def _token(value: str | None) -> str | None:
    if value is None:
        return None
    text = "_".join(str(value).strip().lower().replace("-", " ").replace("_", " ").split())
    return text or None


def _road_token(value: str | None) -> str | None:
    token = _token(value)
    if token is None:
        return None
    if token.endswith("_road"):
        token = token[: -len("_road")]
    return _ROAD_ALIASES.get(token, token)


def _is_nteh(intake: DeclarationIntake) -> bool:
    if intake.nteh is True:
        return True
    if intake.nteh is False:
        return False
    return _token(intake.use) in _NTEH_USES


def _areas_agree(left: float, right: float) -> bool:
    return abs(left - right) <= _AREA_NOISE_HA


def _resolve_area(
    intake: DeclarationIntake,
) -> tuple[float | None, list[str], list[str]]:
    assumptions: list[str] = []
    further: list[str] = []
    implied = None
    if intake.coverage_fraction is not None and intake.district_area_ha is not None:
        implied = intake.coverage_fraction * intake.district_area_ha
        assumptions.append(
            "The coverage fraction is the share of the stated district area. "
            "Schedule 3 uses hectares."
        )
    elif intake.coverage_fraction is not None:
        further.append(
            "A coverage fraction was declared and a district area in hectares was not. "
            "The fraction was not turned into a site area."
        )
    if intake.site_area_ha is not None and implied is not None and not _areas_agree(
        intake.site_area_ha, implied
    ):
        further.append(
            f"The declared site area is {_fmt(intake.site_area_ha)} ha and the "
            f"coverage fraction times the district area is {_fmt(implied)} ha. "
            "The two do not agree, so Schedule 3 was not applied to either figure."
        )
        return None, assumptions, further
    if intake.site_area_ha is not None:
        return intake.site_area_ha, assumptions, further
    if implied is not None:
        return implied, assumptions, further
    if intake.coverage_fraction is None:
        further.append("Site area in hectares was not held. Schedule 3 was not applied.")
    return None, assumptions, further


def _schedule3(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str], list[str]]:
    entry = _live(index, "eiao.sch3.item1.area")
    area, assumptions, further = _resolve_area(intake)
    if area is None:
        flag = "insufficient_facts"
        triggered = False
        reason = "Schedule 3 needs an area in hectares. The area was not established from the declaration."
    elif _gt(area, entry):
        flag = "review"
        triggered = True
        reason = (
            f"The area of {_fmt(area)} ha is more than {_fmt(entry['value'])} ha. "
            "Flagged for Schedule 3 review."
        )
    else:
        flag = "not_triggered"
        triggered = False
        reason = (
            f"The area of {_fmt(area)} ha is not more than {_fmt(entry['value'])} ha. "
            "Schedule 3 item 1 was not flagged."
        )
    if intake.population is not None:
        reason += " Population was supplied and was not used."
    if intake.flat_count is not None:
        assumptions.append(
            "Flat count was supplied and was not used. P.2 is repealed and is not a test."
        )
    return (
        {
            "triggered": triggered,
            "flag": flag,
            "site_area_ha": area,
            "threshold": _snap(entry),
            "reason": reason,
        },
        assumptions,
        further,
    )


def _road(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> str | None:
    entry = _live(index, "eiao.sch2.a1")
    token = _road_token(intake.road_class)
    classes = set(entry.get("classes") or [])
    if token is None:
        if intake.road_class:
            further.append(
                f"Road class '{intake.road_class}' is not an A.1 class and was not treated as one."
            )
        else:
            further.append("Road class was not held. A.1 was not applied.")
        return None
    length_bit = ""
    if intake.road_length_m is not None:
        length_bit = f" A declared length of {_fmt(intake.road_length_m)} m was not used."
    if token in classes:
        flags.append(
            _flag(
                "A.1",
                f"Declared road class {token} is an A.1 class. A.1 has no length threshold.{length_bit}",
                entry,
            )
        )
        return token
    if token == "local_distributor":
        assumptions.append(
            "Declared road class is a local distributor. A.1 was not flagged. "
            "A.1 has no length threshold, and length was not used to create one."
            + length_bit
        )
        return token
    further.append(
        f"Road class '{intake.road_class}' is not an A.1 class and was not treated as one."
    )
    return token


def _reclamation(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    if intake.reclamation_ha is None:
        further.append("Reclamation area was not held. C.1 and C.2 were not applied.")
        return
    area = intake.reclamation_ha
    c1 = _live(index, "eiao.sch2.c1.area")
    c2_area = _live(index, "eiao.sch2.c2.area")
    if _gt(area, c1):
        flags.append(
            _flag(
                "C.1",
                f"Declared reclamation of {_fmt(area)} ha is more than {_fmt(c1['value'])} ha.",
                c1,
            )
        )
    if not _gt(area, c2_area):
        assumptions.append(
            f"Declared reclamation of {_fmt(area)} ha is not more than {_fmt(c2_area['value'])} ha. "
            "C.2 was not flagged."
        )
        return
    limbs = (
        ("seaward specified area", intake.reclamation_specified_area_seaward_m, "eiao.sch2.c2.seaward_m"),
        ("landward specified area", intake.reclamation_specified_area_landward_m, "eiao.sch2.c2.landward_m"),
        ("existing residential area", intake.reclamation_residential_m, "eiao.sch2.c2.residential_m"),
    )
    fired: list[tuple[str, float, Mapping[str, Any]]] = []
    missing: list[str] = []
    for name, distance, entry_id in limbs:
        entry = _live(index, entry_id)
        if distance is None:
            missing.append(name)
        elif _lt(distance, entry):
            fired.append((name, distance, entry))
    if fired:
        name, distance, entry = fired[0]
        flags.append(
            _flag(
                "C.2",
                (
                    f"Declared reclamation of {_fmt(area)} ha is more than {_fmt(c2_area['value'])} ha, "
                    f"and the declared distance to a {name} is {_fmt(distance)} m, "
                    f"less than {_fmt(entry['value'])} m. "
                    "The distance was declared, not checked against a designation map."
                ),
                entry,
            )
        )
        return
    if missing:
        further.append(
            "C.2's area limb was met and a distance limb was not held "
            f"({', '.join(missing)}). C.2 was not flagged. That is not a pass."
        )
        return
    assumptions.append(
        "C.2's area limb was met and none of the declared distance limbs was met. C.2 was not flagged."
    )


def _dredging(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    if intake.dredging_residential_m is not None:
        assumptions.append(
            "A residential distance was declared for dredging. C.12 has no residential limb, "
            "so that distance was not applied to C.12."
        )
    volume = intake.dredging_m3
    sea = intake.dredging_specified_area_seaward_m
    land = intake.dredging_specified_area_landward_m
    if volume is None and sea is None and land is None:
        further.append("Dredging volume and C.12 distances were not held. C.12 was not applied.")
        return
    volume_entry = _live(index, "eiao.sch2.c12.volume_m3")
    sea_entry = _live(index, "eiao.sch2.c12.seaward_m")
    land_entry = _live(index, "eiao.sch2.c12.landward_m")
    if volume is not None and _gt(volume, volume_entry):
        flags.append(
            _flag(
                "C.12",
                f"Declared dredging of {_fmt(volume)} m3 is more than {_fmt(volume_entry['value'])} m3.",
                volume_entry,
            )
        )
        return
    if sea is not None and _lt(sea, sea_entry):
        flags.append(
            _flag(
                "C.12",
                (
                    f"Declared dredging is {_fmt(sea)} m from a seaward specified area, "
                    f"less than {_fmt(sea_entry['value'])} m. "
                    "C.12's specified-area list is narrower than C.2's. The area was not checked."
                ),
                sea_entry,
            )
        )
        return
    if land is not None and _lt(land, land_entry):
        flags.append(
            _flag(
                "C.12",
                (
                    f"Declared dredging is {_fmt(land)} m from a landward specified area, "
                    f"less than {_fmt(land_entry['value'])} m. The area was not checked."
                ),
                land_entry,
            )
        )
        return
    if volume is None or sea is None or land is None:
        further.append(
            "C.12 was not flagged. A volume or distance limb was not held, "
            "so the item was not treated as clear."
        )
        return
    assumptions.append(
        "C.12 was tested on the declared volume and distances and was not flagged."
    )


def _sewage(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    if intake.stp_m3_per_day is None:
        further.append("Sewage-treatment capacity was not held. F.1 and F.2 were not applied.")
        return
    capacity = intake.stp_m3_per_day
    f1 = _live(index, "eiao.sch2.f1.capacity")
    f2_capacity = _live(index, "eiao.sch2.f2.capacity")
    f2_distance = _live(index, "eiao.sch2.f2.distance_m")
    if _gt(capacity, f1):
        flags.append(
            _flag(
                "F.1",
                (
                    f"Declared sewage-treatment capacity of {_fmt(capacity)} m3/day is more than "
                    f"{_fmt(f1['value'])} m3/day."
                ),
                f1,
            )
        )
    if not _gt(capacity, f2_capacity):
        assumptions.append(
            "Declared sewage-treatment capacity met neither F.1 nor the F.2 capacity limb."
            if not _gt(capacity, f1)
            else "Declared sewage-treatment capacity is not more than the F.2 capacity figure."
        )
        return
    distance = intake.stp_receiver_m
    if distance is None:
        further.append(
            "F.2's capacity limb was met and the distance to a receiver named in F.2 was not held. "
            "F.2 was not flagged. That is not a pass."
        )
        return
    if _lt(distance, f2_distance):
        flags.append(
            _flag(
                "F.2",
                (
                    f"Declared capacity of {_fmt(capacity)} m3/day is more than {_fmt(f2_capacity['value'])} m3/day, "
                    f"and the declared distance to a receiver named in F.2 is {_fmt(distance)} m, "
                    f"less than {_fmt(f2_distance['value'])} m. The receiver class was not checked."
                ),
                f2_distance,
            )
        )
        return
    assumptions.append(
        "F.2's capacity limb was met and the declared distance was not less than the F.2 figure. "
        "F.2 was not flagged."
    )


def _channel(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    width = intake.channel_width_m
    distance = intake.channel_named_area_m
    if width is None and distance is None:
        further.append("Channel width and the I.1(b) distance were not held. I.1 was not applied.")
        return
    width_entry = _live(index, "eiao.sch2.i1.width_m")
    distance_entry = _live(index, "eiao.sch2.i1.distance_m")
    width_met = width is not None and _gt(width, width_entry)
    distance_met = distance is not None and _lt(distance, distance_entry)
    if width_met:
        flags.append(
            _flag(
                "I.1",
                (
                    f"Declared channel width of {_fmt(width)} m is more than "
                    f"{_fmt(width_entry['value'])} m."
                ),
                width_entry,
            )
        )
        if distance is None:
            assumptions.append(
                "Channel width meets I.1(a). The I.1(b) distance was not held and was not required for this flag."
            )
        return
    if distance_met:
        flags.append(
            _flag(
                "I.1",
                (
                    f"The declared distance of {_fmt(distance)} m was taken as an area named in I.1(b), "
                    f"less than {_fmt(distance_entry['value'])} m. The designation was not checked."
                ),
                distance_entry,
            )
        )
        return
    if width is None or distance is None:
        further.append(
            "I.1 was not flagged. The width limb was not met on the facts held, and a limb was missing. "
            "That is not a pass."
        )
        return
    assumptions.append(
        "Declared channel width and I.1(b) distance were both held and neither limb was met. "
        "I.1 was not flagged."
    )


def _deep_bay(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    zone = intake.deep_bay_buffer_zone
    use = _token(intake.use)
    p1_use = use in _P1_USES
    exempted = _is_nteh(intake)
    entry = _live(index, "eiao.sch2.p1")
    if zone is None:
        further.append("Deep Bay buffer zone was not held. P.1 was not applied.")
        return
    if zone == "neither":
        assumptions.append(
            "The declaration states the site is in neither Deep Bay Buffer Zone 1 nor 2. "
            "P.1 was not flagged. The statement was not read from a map."
        )
        return
    if not p1_use:
        assumptions.append(
            "A Deep Bay buffer zone was declared and the use is not residential or recreational. "
            "P.1 was not flagged. The zone was declared, not read from a map."
        )
        return
    if exempted:
        assumptions.append(
            "The declaration is a New Territories exempted house inside a Deep Bay buffer zone. "
            "P.1 excepts those houses. The zone was declared, not read from a map."
        )
        return
    if intake.nteh is None:
        further.append(
            "Deep Bay buffer zone and a residential or recreational use were declared, and "
            "New Territories exempted house status was not held. P.1 was not flagged."
        )
        return
    flags.append(
        _flag(
            "P.1",
            (
                f"Declared use is {use} inside Deep Bay Buffer Zone {zone}. "
                "P.1 has no size threshold. The buffer zone was declared, not read from a map."
            ),
            entry,
        )
    )


def _sensitive(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    flags: list[dict[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> None:
    entry = _live(index, "eiao.sch2.q1")
    if intake.in_sensitive_area is True:
        flags.append(
            _flag(
                "Q.1",
                "The declaration places works in an area named in Q.1. "
                "Exemptions stay with EPD and were not applied.",
                entry,
            )
        )
    elif intake.in_sensitive_area is False:
        assumptions.append(
            "The declaration states the works are not in a Q.1 area. That statement was not checked against a plan."
        )
    else:
        further.append("Whether the works are in a Q.1 area was not held. Q.1 was not applied.")

    portal = _live(index, "eiao.sch2.q2.portal_m")
    if intake.rock_cavern is True:
        if intake.rock_cavern_portal_m is None:
            further.append(
                "A rock cavern was declared and the portal distance was not held. "
                "Q.2 was not flagged. That is not a pass."
            )
        elif _lt(intake.rock_cavern_portal_m, portal):
            flags.append(
                _flag(
                    "Q.2",
                    (
                        f"Declared rock-cavern portal distance of {_fmt(intake.rock_cavern_portal_m)} m "
                        f"is less than {_fmt(portal['value'])} m from a receiver named in Q.2. "
                        "The receiver was not checked."
                    ),
                    portal,
                )
            )
        else:
            assumptions.append(
                "The declared portal distance is not less than the Q.2 figure. Q.2 was not flagged."
            )
    elif intake.rock_cavern is False:
        assumptions.append("The declaration states there is no rock cavern. Q.2 was not applied.")
    else:
        further.append("Whether the project is a rock cavern was not held. Q.2 was not applied.")


def _section44(intake: DeclarationIntake) -> dict[str, Any]:
    if intake.contiguous_same_or_associated_persons is True:
        note = (
            "Contiguous projects by the same or associated persons were declared. "
            "This is a flag for a possible specification under section 4(4). "
            "This read does not make that specification."
        )
        flag = "possible_specification"
    elif intake.contiguous_same_or_associated_persons is False:
        note = (
            "The declaration states the projects are not contiguous projects by the same "
            "or associated persons. That statement was not verified. "
            "This read does not make a specification under section 4(4)."
        )
        flag = "not_indicated"
    else:
        note = (
            "Whether the projects are contiguous and proposed by the same or associated "
            "persons was not held. This read does not make a specification under section 4(4)."
        )
        flag = "insufficient_facts"
    return {"flag": flag, "asserted_aggregation": False, "note": note}


def _planning(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    assumptions: list[str],
    further: list[str],
) -> dict[str, Any]:
    notes = {
        "1": "Column 1 is always permitted under the Notes. That is not an environmental permit.",
        "2": (
            "Column 2 needs permission under section 16. "
            "A section 16 planning permission is not an environmental permit."
        ),
        "neither": (
            "A use in neither column needs an application to amend the plan under section 12A. "
            "That is not an environmental permit."
        ),
    }
    column = intake.ozp_column
    route = {"1": "column1", "2": "s16", "neither": "s12A"}.get(column or "")
    if column is None:
        note = (
            "The OZP column was not supplied. Column 1, Column 2 or neither was not guessed "
            "from the land use. A section 16 planning permission is not an environmental permit."
        )
    else:
        note = notes[column]
    predates = False
    commencement = date.fromisoformat(str(_live(index, "eiao.s9.2.a")["value"]))
    if intake.planning_permission_date:
        try:
            granted = date.fromisoformat(intake.planning_permission_date)
        except ValueError:
            further.append(
                "The planning permission date could not be read. Section 9(2)(a) was not applied."
            )
        else:
            predates = granted < commencement
            if predates:
                assumptions.append(
                    "The declared permission date is before the EIAO commencement date on the "
                    "reference file. Whether section 9(2)(a) applies is not determined here."
                )
            else:
                assumptions.append(
                    "The declared permission date is not before the EIAO commencement date. "
                    "Section 9(2)(a) was not treated as applying. "
                    "The permission is not an environmental permit."
                )
    return {
        "column": column,
        "route": route,
        "is_environmental_permit": False,
        "permission_predates_eiao": predates,
        "note": note,
    }


def _ea(intake: DeclarationIntake, assumptions: list[str], further: list[str]) -> bool | None:
    use = _token(intake.use)
    limbs = (
        intake.may_cause_impacts,
        intake.pollution_sensitive,
        intake.major_or_large_scale,
    )
    if use in _EA_USES or any(limb is True for limb in limbs):
        assumptions.append(
            "An environmental assessment may be required on the declared use or on an Annex B limb. "
            "Advisory only, from the TPB section 16 Guidance Notes. Not a determination."
        )
        return True
    if all(limb is False for limb in limbs) and use in _SMALL_USES:
        assumptions.append(
            "The declaration states the Annex B limbs are not met and names a small premises-based use. "
            "The Guidance Notes give that as an example where an environmental assessment is not required. "
            "Advisory only. Not a determination."
        )
        return False
    further.append(
        "The facts the TPB section 16 Guidance Notes use for an environmental assessment "
        "were not held. No finding is made that an environmental assessment is not required."
    )
    return None


def _hkpsg(
    intake: DeclarationIntake,
    index: Mapping[str, Mapping[str, Any]],
    road_token: str | None,
    further: list[str],
) -> dict[str, Any]:
    parts: list[str] = ["Check against HKPSG."]
    buffer_m: float | None = None
    missing: list[str] = []
    if intake.receiver_distance_road_m is None:
        missing.append("road receiver distance")
    elif intake.road_screening is None:
        further.append(
            "A road receiver distance was declared and whether screening is in place was not. "
            "The Table 1.3 row was not chosen. That is not a pass."
        )
    elif road_token in _HKPSG_ROAD:
        entry_id = _HKPSG_ROAD[road_token]
        if intake.road_screening:
            entry_id = f"{entry_id}.screened"
        entry = _live(index, entry_id)
        buffer_m = float(entry["value"])
        position = "inside" if _lt(intake.receiver_distance_road_m, entry) else "outside"
        parts.append(
            f"The declared road distance is {position} the published Table 1.3 residential "
            f"figure of {_fmt(entry['value'])} {entry['unit']}."
        )
    elif road_token == "expressway":
        further.append(
            "Table 1.3's residential rows name trunk, primary and district or local distributors. "
            "An expressway was not matched to a row. That is not a pass."
        )
    else:
        further.append(
            "A road receiver distance was declared and the road class was not matched to a "
            "Table 1.3 row. That is not a pass."
        )

    if intake.receiver_distance_rail_m is None:
        missing.append("rail receiver distance")
    elif intake.rail_type is None:
        further.append(
            "A rail receiver distance was declared and the rail type was not. "
            "The Table 1.3 rail row was not chosen. That is not a pass."
        )
    else:
        entry = _live(index, _HKPSG_RAIL[intake.rail_type])
        position = "inside" if _lt(intake.receiver_distance_rail_m, entry) else "outside"
        parts.append(
            f"The declared {intake.rail_type} distance is {position} the published figure of "
            f"{_fmt(entry['value'])} {entry['unit']}."
        )

    nef = _live(index, "hkpsg.nef25")
    if intake.within_nef_25 is None:
        missing.append("NEF 25")
    elif intake.within_nef_25:
        parts.append(
            f"The declaration places a noise-sensitive use within NEF {_fmt(nef['value'])}."
        )
    else:
        parts.append(
            f"The declaration states the site is outside NEF {_fmt(nef['value'])}. "
            "Not a compliance finding."
        )
    if missing:
        verb = "were" if len(missing) != 1 else "was"
        further.append(
            f"{', '.join(missing)} {verb} not held. HKPSG was not applied to the missing fact. "
            "The omission is not a pass."
        )
    opens = [
        _live(index, "hkpsg.openspace.trunk_primary"),
        _live(index, "hkpsg.openspace.district"),
        _live(index, "hkpsg.openspace.local"),
    ]
    listed = ", ".join(f"{_fmt(entry['value'])} {entry['unit']}" for entry in opens)
    parts.append(
        f"Open-space separations on the reference file are {listed}. "
        "They were not applied as residential buffers."
    )
    parts.append("Not a pass and not a fail.")
    return {
        "advisory_only": True,
        "pass_fail": False,
        "applied_open_space_separation_as_residential": False,
        "residential_buffer_m": buffer_m,
        "note": " ".join(parts),
    }


def _retired_sentence(document: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for entry in document["entries"]:
        if entry["status"] == "current":
            continue
        shown = entry.get("values")
        value = ", ".join(_fmt(item) for item in shown) if shown else _fmt(entry.get("value"))
        parts.append(
            f"{entry['id']} ({value} {entry['unit']}, superseded by {entry['supersededBy']})"
        )
    return "Repealed or non-rule entries were not applied: " + "; ".join(parts) + "."


def _standing_unknowns(index: Mapping[str, Mapping[str, Any]]) -> list[str]:
    plan = _live(index, "ozp.s_hsk_4.identity")
    return [
        f"The zone-by-zone Notes of {plan['value']} were not read. "
        "A column is used only when the declaration supplies one.",
        "Whether the site intersects Deep Bay Buffer Zone 1 or 2 was not read. "
        "P.1 uses only a buffer zone the declaration supplies.",
        "Whether section 5(9), 5(10) or 5(11) is available was not read.",
        "Schedules 2 and 3 are applied at the point in time on the reference file. "
        "A later amendment was not searched for this read.",
        "Schedule 2 items A.7, A.8 and A.9 were not tested. They remain on the current "
        "Schedule. Leaving them off this read is not a finding that they do not apply.",
        "Exemptions in Schedule 2 item Q.1 stay with EPD. This screen does not apply them.",
        "The open-form MTR parapet case in HKPSG was not applied.",
    ]


def _as_at(
    document: Mapping[str, Any],
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    plan = _live(index, "ozp.s_hsk_4.identity")
    return {
        "schedulesPointInTime": str(document["schedulesPointInTime"]),
        "readOn": str(document["readOn"]),
        "tmEffective": str(_live(index, "eiao.tm.effective")["value"]),
        "tmTransitionClosed": str(_live(index, "eiao.tm.transition_closed")["value"]),
        "aqoEffective": str(_live(index, "apco.aqo.effective")["value"]),
        "aqoVariationOfEpMonths": str(_live(index, "apco.aqo.vep_months")["value"]),
        "hskHtPlan": str(plan["value"]),
        "hskHtApprovedOn": str(plan["approvedOn"]),
        "hskHtGazettedOn": str(plan["effectiveDate"]),
    }


def government_fit(payload: DeclarationIntake | Mapping[str, Any]) -> dict[str, Any]:
    """The fit object for one declaration. Thresholds are read from the file."""
    intake = (
        payload
        if isinstance(payload, DeclarationIntake)
        else DeclarationIntake.model_validate(payload)
    )
    document = load_thresholds()
    assert_no_superseded_value_is_live(document)
    index = _index(document)

    schedule3, assumptions, further = _schedule3(intake, index)
    flags: list[dict[str, Any]] = []
    road = _road(intake, index, flags, assumptions, further)
    _reclamation(intake, index, flags, assumptions, further)
    _dredging(intake, index, flags, assumptions, further)
    _sewage(intake, index, flags, assumptions, further)
    _channel(intake, index, flags, assumptions, further)
    _deep_bay(intake, index, flags, assumptions, further)
    _sensitive(intake, index, flags, assumptions, further)
    section44 = _section44(intake)
    if section44["flag"] == "insufficient_facts":
        further.append(section44["note"])
    planning = _planning(intake, index, assumptions, further)
    ea = _ea(intake, assumptions, further)
    hkpsg = _hkpsg(intake, index, road, further)
    as_at = _as_at(document, index)
    plan = _live(index, "ozp.s_hsk_4.identity")

    standing = [
        "This is a broad-brush fit read and not a statutory determination.",
        "A section 16 planning permission is not an environmental permit.",
        (
            "Contravention of section 9 is an offence under section 26(1). "
            "This read does not determine a contravention."
        ),
        (
            f"As at the reference file: Schedules point in time {as_at['schedulesPointInTime']}, "
            f"read on {as_at['readOn']}. Amended EIAO TM from {as_at['tmEffective']}. "
            f"Transitional route for EIA-report approval closed after {as_at['tmTransitionClosed']}. "
            f"AQOs from {as_at['aqoEffective']} applied at the date of decision, with a "
            f"{as_at['aqoVariationOfEpMonths']}-month variation-of-EP transition."
        ),
        _retired_sentence(document),
        (
            f"Plan identity only: {plan['value']}, approved {plan['approvedOn']}, "
            f"gazetted {plan['effectiveDate']}. Zone Notes were not read."
        ),
    ]
    if schedule3["triggered"]:
        standing.append(
            "Schedule 3 is flagged. Section 9(5) means a Schedule 3 listing does not "
            "remove the need for an environmental permit."
        )
    if flags:
        standing.append(
            "A Schedule 2 flag is read against section 9(1). This read does not decide "
            "whether the prohibition applies to a person or to the works."
        )
    model = GovernmentFit.model_validate(
        {
            "screening_label": SCREENING_LABEL,
            "not_a_determination": True,
            "schedule3": schedule3,
            "schedule2": flags,
            "planning_permission": planning,
            "ea_may_be_required": ea,
            "assumptions": standing + assumptions,
            "further_information": _standing_unknowns(index) + further,
            "section44": section44,
            "hkpsg": hkpsg,
            "as_at": as_at,
        }
    )
    return model.model_dump(by_alias=True)


def _entry_line(entry: Mapping[str, Any]) -> str:
    successor = entry["supersededBy"] if entry["supersededBy"] is not None else "none"
    applies = entry.get("appliesTo")
    applies_bit = f"; appliesTo {applies}" if applies else ""
    return (
        f"{entry['id']}: {_fmt(entry['value'])} {entry['unit']}{applies_bit}; "
        f"effective {entry['effectiveDate']}; supersededBy {successor}; {entry['sourceUrl']}"
    )


def render_screening_basis_annex(fit: Mapping[str, Any]) -> str:
    """One page a consultant can paste. Figures come from the fit and the file."""
    GovernmentFit.model_validate(fit)
    document = load_thresholds()
    assert_no_superseded_value_is_live(document)
    snapshot = fit["schedule3"]["threshold"]
    file_entry = next(entry for entry in document["entries"] if entry["id"] == snapshot["id"])
    if not _same(file_entry["value"], snapshot["value"]):
        raise ThresholdDrift("the annex and the fit do not use the same Schedule 3 figure")

    as_at = fit["asAt"]
    lines = [
        "Screening-basis annex",
        "Broad-brush fit read, not a statutory determination.",
        f"Label: {fit['screeningLabel']}",
        "notADetermination: true",
        "",
        "As at",
        f"- Schedules 2 and 3 point in time: {as_at['schedulesPointInTime']} (read {as_at['readOn']})",
        f"- Amended EIAO TM effective: {as_at['tmEffective']}",
        f"- Transitional route for EIA-report approval closed after: {as_at['tmTransitionClosed']}",
        (
            f"- AQOs effective: {as_at['aqoEffective']}, applied at the date of decision; "
            f"variation-of-EP transition {as_at['aqoVariationOfEpMonths']} months"
        ),
        (
            f"- Plan identity only: {as_at['hskHtPlan']}, approved {as_at['hskHtApprovedOn']}, "
            f"gazetted {as_at['hskHtGazettedOn']}. Zone Notes were not read."
        ),
        "",
        "Gate flags",
        f"- Schedule 3: {fit['schedule3']['flag']}. {fit['schedule3']['reason']}",
    ]
    if fit["schedule2"]:
        for flag in fit["schedule2"]:
            lines.append(f"- Schedule 2 {flag['item']}: {flag['reason']}")
    else:
        lines.append("- Schedule 2: no item flagged on the facts held.")
    lines.append(f"- Planning permission: {fit['planningPermission']['note']}")
    ea = fit["eaMayBeRequired"]
    if ea is True:
        lines.append(
            "- Environmental assessment: may be required. Advisory only. Not a determination."
        )
    elif ea is False:
        lines.append(
            "- Environmental assessment: the declared facts match a Guidance Notes example "
            "where an EA is not required. Advisory only. Not a determination."
        )
    else:
        lines.append(
            "- Environmental assessment: the Annex B facts were not held. "
            "No finding that an EA is not required."
        )
    lines.append(f"- Section 4(4): {fit['section44']['note']}")
    lines.append(f"- HKPSG: {fit['hkpsg']['note']}")
    lines.append("")
    lines.append("Thresholds applied")
    for entry in document["entries"]:
        if entry["status"] == "current" and entry["role"] == "test":
            lines.append(f"- {_entry_line(entry)}")
    lines.append("")
    lines.append("Advisory distances, not a pass or a fail")
    for entry in document["entries"]:
        if entry["status"] == "current" and entry["role"] == "advisory":
            lines.append(f"- {_entry_line(entry)}")
    lines.append("")
    lines.append("Superseded tests not applied")
    for entry in document["entries"]:
        if entry["status"] != "current":
            lines.append(f"- {_entry_line(entry)}")
    lines.append("")
    lines.append("Assumption register")
    for item in fit["assumptions"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Further information")
    for item in fit["furtherInformation"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append(
        "This annex is not an environmental permit, a section 16 decision, or a "
        "determination under the EIAO or the Town Planning Ordinance. "
        "A section 16 planning permission is not an environmental permit."
    )
    return "\n".join(lines) + "\n"


def declaration_intake(payload: DeclarationIntake | Mapping[str, Any]) -> dict[str, Any]:
    """Intake: the fit object and the pasteable annex, from the same facts."""
    fit = government_fit(payload)
    return {
        "governmentFit": fit,
        "screeningBasisAnnex": render_screening_basis_annex(fit),
    }
