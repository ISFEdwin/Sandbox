"""Identify the projects and the wind regime a screening is allowed to name.

EIAO Guidance Note No. 6/2023 paragraph 21 says development projects in the
vicinity should be identified during data collection, and the cumulative
impacts then assessed. The Technical Memorandum says the same thing as
existing, committed and planned projects (sections 4.3.1(c)(ii), 4.4.3).
This module names what the committed files actually hold. It does not
assess the cumulative impact, and it does not invent a class the files do
not carry.

Technical Circular No. 1/06 asks for a comparison of design options and
defines a velocity ratio from pedestrian test points. The wind-channel
block reports the published inflow and the geometric comparison. Site and
local velocity ratios stay null.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.services import scene_service

DUTIES_PATH = "reference/regulatory_duties.json"
WINDOW_WIND_PATH = "reference/hsk_site_wind_window.json"
AVA_PATH = "reference/hsk_ava_reference.json"
WIND_INDEX_PATH = "openfoam/wind_index.json"
CHANNEL_SIDECAR_PATH = "openfoam/channel_sidecar.json"

STATUS = "PROJECTS_IDENTIFIED_NOT_AN_EIA_INVENTORY"
SCREENING_LABEL = "DATA_COLLECTION_NOT_A_CUMULATIVE_ASSESSMENT"
WIND_CHANNEL_STATUS = "WIND_CHANNEL_COMPARISON_NOT_AN_AVA"

# The three published prevailing directions. ENE is in the group and is not
# marched: the corridor table has no travel vector for it.
PREVAILING = ("NE", "ENE", "E")


def _read(relative: str) -> dict[str, Any] | None:
    path = settings.data_dir / relative
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_duties() -> list[dict[str, Any]]:
    """Every excerpt in the reference file, live and superseded."""
    doc = _read(DUTIES_PATH) or {}
    entries = doc.get("entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def live_duties() -> list[dict[str, Any]]:
    """Excerpts the screen may cite. A superseded entry is not in this list."""
    return [entry for entry in load_duties() if entry.get("live") is True]


def _duty(entry_id: str) -> dict[str, Any] | None:
    for entry in live_duties():
        if entry.get("id") == entry_id:
            return entry
    return None


def window_frequencies() -> dict[str, float] | None:
    """Area-weighted annual 500 m occurrences, or None when unverified.

    None is a missing rose. Callers list it; they do not estimate one.
    """
    doc = _read(WINDOW_WIND_PATH)
    if not doc or doc.get("verified") is not True:
        return None
    freq = (doc.get("merged") or {}).get("frequencyByDirection") or {}
    if not isinstance(freq, dict) or not freq:
        return None
    return {str(name): float(value) for name, value in freq.items()}


def _existing_envelopes(scene_id: str) -> dict[str, Any]:
    path = scene_service.buildings_path(scene_id)
    if path is None:
        return {
            "id": "existing-envelopes",
            "class": "existing",
            "name": "Existing massing envelopes",
            "count": None,
            "source": None,
            "known": [],
            "unknown": ["The scene has no committed massing file."],
        }
    try:
        features = json.loads(path.read_text(encoding="utf-8")).get("features") or []
        count = len(features)
    except (OSError, ValueError):
        count = None
    relative = str(path.relative_to(settings.data_dir))
    return {
        "id": "existing-envelopes",
        "class": "existing",
        "name": "Existing massing envelopes",
        "count": count,
        "source": relative,
        "known": [
            "Count of footprint features in the committed massing file.",
        ],
        "unknown": [
            "Individual building names, occupiers and completion dates are not held.",
        ],
    }


def _planned_projects() -> list[dict[str, Any]]:
    folder = settings.data_dir / "projects"
    plans_by_project: dict[str, str] = {}
    plans_dir = settings.data_dir / "plans"
    if plans_dir.exists():
        for path in sorted(plans_dir.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            project_id = str((doc.get("params") or {}).get("projectId") or "")
            if project_id and project_id not in plans_by_project:
                plans_by_project[project_id] = str(doc.get("id") or path.stem)
    rows: list[dict[str, Any]] = []
    if not folder.exists():
        return rows
    for path in sorted(folder.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        project_id = str(doc.get("id") or path.stem)
        effects = []
        for effect in doc.get("effects") or []:
            kind = effect.get("kind")
            if kind:
                effects.append(str(kind))
        rows.append({
            "id": project_id,
            "class": "planned",
            "name": doc.get("name") or project_id,
            "count": 1,
            "planId": plans_by_project.get(project_id),
            "source": f"projects/{path.name}",
            "known": [
                doc.get("note") or "Catalog footprint.",
                "Effects: " + (", ".join(effects) if effects else "none declared."),
            ],
            "unknown": [
                "Not classified as committed. A catalog row is not a planning approval.",
                "Phasing dates are not held.",
            ],
        })
    return rows


def _wind_inflow() -> dict[str, Any]:
    doc = _read(WINDOW_WIND_PATH)
    freq = window_frequencies()
    if freq is None:
        return {
            "status": "WINDOW_WIND_UNAVAILABLE",
            "verified": False,
            "headlineDirection": None,
            "headlineFrequency": None,
            "cellIds": [],
            "frequencies": None,
        }
    marched = {name: freq[name] for name in ("NE", "E") if name in freq}
    headline = max(marched, key=marched.get) if marched else None
    index = _read(WIND_INDEX_PATH) or {}
    table = (((index.get("tables") or {}).get("annual") or {}).get("500") or {})
    directions = table.get("directions") or {}
    inlet = None
    if headline and isinstance(directions.get(headline), dict):
        inlet = directions[headline].get("inletSpeedMps")
    sidecar = _read(CHANNEL_SIDECAR_PATH) or {}
    return {
        "status": "WINDOW_WIND_AREA_WEIGHTED",
        "verified": True,
        "season": doc.get("season") if doc else "annual",
        "heightM": doc.get("heightM") if doc else 500,
        "cellIds": list((doc or {}).get("gridCellIds") or []),
        "method": (doc or {}).get("method"),
        "headlineDirection": headline,
        "headlineFrequency": marched.get(headline) if headline else None,
        "frequencies": {name: freq.get(name) for name in PREVAILING},
        "centroidCellInletMps": inlet,
        "centroidCellId": index.get("gridCellId"),
        "inletNote": (
            "The inlet is the centroid cell's annual 500 m bin midpoint scaled "
            "to 10 m in the committed wind index. The window file does not "
            "publish its own 10 m speed. PlanD does not publish that speed."
        ),
        "solvedChannel": {
            "status": sidecar.get("status"),
            "onRequestPath": False,
            "limitation": sidecar.get("limitation"),
        },
    }


def _rank_of(frequencies: dict[str, Any], name: str) -> int | None:
    if name not in frequencies:
        return None
    ordered = sorted(frequencies, key=lambda key: (-float(frequencies[key]), key))
    return ordered.index(name) + 1


def _east_side(wind: dict[str, Any]) -> dict[str, Any]:
    direction = (wind.get("directions") or {}).get("E") or {}
    ratio = (wind.get("fadRatioByDirection") or {}).get("E") or {}
    return {
        "firstObstructionMeanM": direction.get("firstObstructionMeanM"),
        "pathLengthM": direction.get("pathLengthM"),
        "entryEdge": direction.get("entryEdge"),
        "fadRatio": ratio.get("ratio"),
        "unit": "m",
    }


def _east_channel(
    inflow: dict[str, Any],
    scheme_winds: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """The east reading of the window rose, with the cells and seasons behind it.

    East is the annual headline among the marched directions. Summer and
    winter are shown beside it so that headline is not read as the year-round
    prevailing wind. None of the speeds is a velocity ratio.
    """
    doc = _read(WINDOW_WIND_PATH) or {}
    seasons_doc = doc.get("seasons") or {}
    seasons: list[dict[str, Any]] = []
    for name in ("annual", "summer", "winter"):
        block = seasons_doc.get(name) or {}
        frequencies = block.get("frequencyByDirection") or {}
        east = block.get("east") or {}
        if block.get("verified") is not True or not frequencies:
            seasons.append({"season": name, "verified": False})
            continue
        leader = max(frequencies, key=lambda key: (float(frequencies[key]), key))
        seasons.append({
            "season": name,
            "verified": True,
            "heightM": block.get("heightM") or 500,
            "frequency": east.get("frequency"),
            "derivedMeanSpeedMps": east.get("derivedMeanSpeedMps"),
            "rank": _rank_of(frequencies, "E"),
            "of": len(frequencies),
            "leadingDirection": leader,
            "leadingFrequency": frequencies.get(leader),
        })
    index = _read(WIND_INDEX_PATH) or {}
    table = (((index.get("tables") or {}).get("annual") or {}).get("500") or {})
    centroid_east = (table.get("directions") or {}).get("E") or {}
    sidecar = _read(CHANNEL_SIDECAR_PATH) or {}
    count = (sidecar.get("directions") or {}).get("E")
    reference = _read(AVA_PATH) or {}
    provenance = doc.get("provenance") or {}
    source = reference.get("source") or {}
    annual = next((row for row in seasons if row.get("season") == "annual"), {})
    headline = inflow.get("headlineDirection") == "E"

    def _season_sentence(row: dict[str, Any]) -> str:
        label = str(row.get("season") or "season").capitalize()
        if row.get("verified") is not True or not isinstance(row.get("frequency"), (int, float)):
            return f"{label} east is not in the window file."
        share = f"{float(row['frequency']) * 100:.1f}%"
        if row.get("leadingDirection") == "E":
            return f"{label} east is {share} and leads the {row.get('of')} directions."
        return (
            f"{label} east is {share} and ranks {row.get('rank')} of {row.get('of')}, "
            f"behind {row.get('leadingDirection')}."
        )

    return {
        "status": (
            "EAST_CHANNEL_WINDOW_HEADLINE" if headline
            else "EAST_CHANNEL_NOT_THE_ANNUAL_HEADLINE"
        ),
        "direction": "E",
        "role": (
            "Highest frequency among the marched directions NE and E on the "
            "annual area-weighted window rose. ENE is in the prevailing set "
            "and has no travel vector, so it is not marched."
        ),
        "notAVelocity": True,
        "annualFrequency": annual.get("frequency"),
        "annualRank": annual.get("rank"),
        "annualOf": annual.get("of"),
        "derivedMeanSpeedMps": annual.get("derivedMeanSpeedMps"),
        "heightM": 500,
        "seasons": seasons,
        "cells": list(((seasons_doc.get("annual") or {}).get("cells") or [])),
        "centroid": {
            "gridCellId": index.get("gridCellId"),
            "frequency": centroid_east.get("frequency") if isinstance(centroid_east, dict) else None,
            "derivedMeanSpeedMps": (
                centroid_east.get("derivedMeanSpeedMps") if isinstance(centroid_east, dict) else None
            ),
            "inletSpeedMps": (
                centroid_east.get("inletSpeedMps") if isinstance(centroid_east, dict) else None
            ),
            "note": inflow.get("inletNote"),
        },
        "solvedStreamlineCount": count if isinstance(count, int) else None,
        "solvedOnRequestPath": False,
        "scheme": {
            "a": _east_side(scheme_winds.get("a") or {}),
            "b": _east_side(scheme_winds.get("b") or {}),
        },
        "sources": [
            {
                "name": provenance.get("dataset") or "Planning Department Site Wind Availability Data",
                "url": provenance.get("datasetUrl"),
            },
            {"name": "PlanD site-wind index", "url": provenance.get("indexUrl")},
            {"name": source.get("name"), "url": source.get("url")},
            {
                "name": "Technical Circular No. 1/06",
                "url": (_duty("tc106.annexA.para4") or {}).get("sourceUrl"),
            },
        ],
        "reading": (
            " ".join(_season_sentence(row) for row in seasons)
            + " The scheme comparison is the east first-obstruction height, in metres."
        ),
    }


def wind_channel_comparison(
    scheme_winds: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Option comparison under the window inflow. Not an AVA.

    ``scheme_winds`` is ``{"a": wind_metrics, "b": wind_metrics}`` from the
    geometric corridor. SVR and LVR are null: Annex A defines them from
    pedestrian test points, and this screening does not hold those points.
    """
    inflow = _wind_inflow()
    freq = inflow.get("frequencies") or {}
    reference = _read(AVA_PATH) or {}
    published = reference.get("publishedVelocityRatios") or {}
    options = []
    for name in PREVAILING:
        row: dict[str, Any] = {
            "direction": name,
            "frequency": freq.get(name),
        }
        for key, wind in scheme_winds.items():
            direction = (wind.get("directions") or {}).get(name) or {}
            ratio = (wind.get("fadRatioByDirection") or {}).get(name) or {}
            row[f"{key}FirstObstructionMeanM"] = direction.get("firstObstructionMeanM")
            row[f"{key}PathLengthM"] = direction.get("pathLengthM")
            row[f"{key}EntryEdge"] = direction.get("entryEdge")
            row[f"{key}FadRatio"] = ratio.get("ratio")
        options.append(row)
    vr_duty = _duty("tc106.annexA.para4")
    return {
        "status": WIND_CHANNEL_STATUS,
        "notAnAva": True,
        "notADetermination": True,
        "inflow": inflow,
        "options": options,
        "velocityRatio": {
            "svr": None,
            "lvr": None,
            "reason": (
                "Technical Circular 1/06 Annex A defines VR as Vp/V∞ at "
                "pedestrian test points (2 m) against wind at the top of the "
                "boundary layer. This screening has no test points. Frontal "
                "area density and the coarse channel solve are not that ratio."
            ),
            "definition": (vr_duty or {}).get("quote"),
            "publishedReference": {
                "source": (reference.get("source") or {}).get("name"),
                "siteSpatialAverage": published.get("siteSpatialAverage"),
                "localSpatialAverage": published.get("localSpatialAverage"),
                "note": (
                    "AVRG73's own baseline and proposed schemes. Not a "
                    "measurement of the schemes on this board."
                ),
            },
        },
        "benchmark": (_duty("tc106.para6") or {}).get("quote"),
        "east": _east_channel(inflow, scheme_winds),
    }


def collect(scene_id: str, compared: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The data-collection record for one scene.

    ``compared`` is the schemes on the board, each ``{"key", "planIds"}``.
    A plan id that is not in the catalog is named in ``furtherInformation``.
    It is not silently dropped and it is not treated as an identified project.
    """
    scene_service.get_scene(scene_id)
    inventory = [_existing_envelopes(scene_id), *_planned_projects()]
    known_plans = {
        row["planId"] for row in inventory if row.get("planId")
    }
    unnamed: list[str] = []
    if compared:
        for side in compared:
            for plan_id in side.get("planIds") or []:
                if plan_id not in known_plans and plan_id not in unnamed:
                    unnamed.append(str(plan_id))
    further = [
        "No committed-project register is held. A planned catalog row is not a finding that the project is committed.",
        "Construction phasing is not held, so overlapping timelines are not identified.",
        "Zone Notes and any Deep Bay Buffer Zone overlap were not read.",
        "Site and local velocity ratios are not computed. Technical Circular 1/06 Annex A defines them from pedestrian test points this screening does not hold.",
        "The coarse channel solve is the baseline 2.5D massing. It is not re-solved for the scheme under comparison.",
    ]
    if unnamed:
        further.append(
            "The comparison names plan ids that are not in the project catalog: "
            + ", ".join(unnamed)
            + ". They are not added to the inventory."
        )
    if window_frequencies() is None:
        further.append(
            "The study-window wind rose is missing or unverified. "
            "Direction weights are not estimated."
        )
    duties = live_duties()
    if not duties:
        further.append("The regulatory excerpt file is missing. No duty is cited from memory.")
    return {
        "sceneId": scene_id,
        "status": STATUS,
        "screeningLabel": SCREENING_LABEL,
        "notADetermination": True,
        "inventory": inventory,
        "classesHeld": sorted({row["class"] for row in inventory if row.get("count")}),
        "classesNotHeld": ["committed"],
        "duties": [
            {
                "id": entry.get("id"),
                "instrument": entry.get("instrument"),
                "paragraph": entry.get("paragraph"),
                "sourceUrl": entry.get("sourceUrl"),
                "quote": entry.get("quote"),
            }
            for entry in duties
        ],
        "supersededNotApplied": [
            entry.get("id") for entry in load_duties() if entry.get("live") is not True
        ],
        "windInflow": _wind_inflow(),
        "compared": [
            {"key": side.get("key"), "planIds": list(side.get("planIds") or [])}
            for side in (compared or [])
        ],
        "furtherInformation": further,
        "whatThisIsNot": [
            "Not an EIA report and not a cumulative impact assessment.",
            "Not an air ventilation assessment and not a velocity ratio.",
            "Not a statutory determination.",
        ],
    }
