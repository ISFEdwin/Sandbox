"""Fetch the PlanD 500 m site-wind cell that contains the HSK/HT window.

Projection stays in this script. The API continues to speak EPSG:4326.
The index columns named MIN_LAT / MAX_LAT hold longitude and MIN_LNG /
MAX_LNG hold latitude; the cell is chosen on the HK1980 easting and
northing (EPSG:2326), not on those headers.

Writes ``data/reference/hsk_site_wind.json``. ``verified`` is true only when
all nine occurrence tables (annual / summer / winter at 500, 300 and 200 m)
parse. A failed fetch leaves ``verified: false`` and does not invent a rose.

``--window-only`` writes ``data/reference/hsk_site_wind_window.json``: the
area-weighted annual 500 m rose of every cell the study window touches. It
does not rewrite the centroid file.

Run from backend/:  python scripts/fetch_site_wind.py
                    python scripts/fetch_site_wind.py --window-only
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from datetime import date, timezone
from pathlib import Path

from rasterio.warp import transform

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND / "data" / "reference" / "hsk_site_wind.json"
WINDOW_OUT = BACKEND / "data" / "reference" / "hsk_site_wind_window.json"
INDEX_URL = (
    "https://www.pland.gov.hk/pland_en/resources/site_wind/open_data/"
    "site_wind_open_data.csv"
)
DATASET_URL = (
    "https://data.gov.hk/en-data/dataset/hk-pland-pland1-site-wind-availability-data"
)
BOUNDS_PATH = BACKEND / "data" / "rasters" / "wetgrid_hsk.json"
DIRECTIONS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)
SEASONS = ("annual", "summer", "winter")
HEIGHTS = (500, 300, 200)


def _study_window() -> tuple[float, float, float, float]:
    doc = json.loads(BOUNDS_PATH.read_text(encoding="utf-8"))
    west, south, east, north = doc["inputs"]["bounds"]
    return float(west), float(south), float(east), float(north)


def _to_hk1980(lon: float, lat: float) -> tuple[float, float]:
    xs, ys = transform("EPSG:4326", "EPSG:2326", [lon], [lat])
    return float(xs[0]), float(ys[0])


def _index_rows() -> list[dict[str, str]]:
    with urllib.request.urlopen(INDEX_URL, timeout=120) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _cell_contains(row: dict[str, str], easting: float, northing: float) -> bool:
    return (
        float(row["MIN_X"]) <= easting <= float(row["MAX_X"])
        and float(row["MIN_Y"]) <= northing <= float(row["MAX_Y"])
    )


def _interpreted_wgs84(row: dict[str, str]) -> dict[str, float]:
    """The degree columns are swapped relative to their headers.

    Values near 113 are longitude; values near 22 are latitude. The names
    MIN_LAT / MIN_LNG are recorded so the swap is visible.
    """
    a, b = float(row["MIN_LAT"]), float(row["MIN_LNG"])
    c, d = float(row["MAX_LAT"]), float(row["MAX_LNG"])
    longs = [v for v in (a, b, c, d) if v > 100.0]
    lats = [v for v in (a, b, c, d) if v < 100.0]
    return {
        "west": min(longs),
        "east": max(longs),
        "south": min(lats),
        "north": max(lats),
    }


def _parse_table(text: str) -> dict:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    header = lines[0].split("\t")
    directions = [name for name in header[2:] if name]
    if directions != list(DIRECTIONS):
        raise ValueError(f"direction header {directions} is not the 16 canonical names")
    frequency: dict[str, float] = {}
    bins: list[dict] = []
    for line in lines[1:]:
        parts = line.split("\t")
        label = parts[0]
        values = [float(part) for part in parts[2:2 + len(directions)]]
        if label.startswith("V_infinity"):
            frequency = dict(zip(directions, values))
            continue
        lo_s, _, hi_s = label.partition("_to_")
        bins.append({
            "bin": label,
            "speedLowMps": int(lo_s),
            "speedHighMps": int(hi_s),
            "occurrenceByDirection": dict(zip(directions, values)),
        })
    if not frequency:
        raise ValueError("table has no V_infinity occurrence row")
    derived: dict[str, float | None] = {}
    for name in directions:
        total = 0.0
        moment = 0.0
        for band in bins:
            occurrence = band["occurrenceByDirection"][name]
            midpoint = 0.5 * (band["speedLowMps"] + band["speedHighMps"])
            total += occurrence
            moment += occurrence * midpoint
        derived[name] = (round(moment / total, 4) if total > 0.0 else None)
    return {
        "frequencyByDirection": frequency,
        "frequencySum": round(sum(frequency.values()), 6),
        "speedBins": bins,
        "derivedMeanSpeedMps": derived,
        "derivedMeanSpeedMethod": (
            "Frequency-weighted midpoint of the published speed bins. "
            "PlanD does not publish a single speed; this figure is calculated "
            "from the occurrence table and is not a measurement of its own."
        ),
    }


def _fetch_text(url: str) -> str:
    with urllib.request.urlopen(url.strip(), timeout=60) as response:
        return response.read().decode("utf-8")


def _grid_id(row: dict[str, str]) -> str:
    return row.get("GRID_ID") or row.get("\ufeffGRID_ID") or ""


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def merge_roses(cells: list[dict]) -> dict:
    """Area-weighted mean of annual occurrence tables.

    ``cells`` each carry ``weightM2``, ``frequencyByDirection`` and
    ``speedBins`` with the same bin labels and the 16 canonical directions.
    A zero total weight is refused: an empty overlap is not a rose.
    """
    weighted = [cell for cell in cells if float(cell["weightM2"]) > 0.0]
    total = sum(float(cell["weightM2"]) for cell in weighted)
    if total <= 0.0 or not weighted:
        raise ValueError("window overlap has no positive area")
    template = weighted[0]["speedBins"]
    for cell in weighted[1:]:
        labels = [band["bin"] for band in cell["speedBins"]]
        if labels != [band["bin"] for band in template]:
            raise ValueError("speed-bin labels differ between PlanD cells")
    frequency: dict[str, float] = {}
    for name in DIRECTIONS:
        frequency[name] = round(
            sum(float(cell["weightM2"]) * float(cell["frequencyByDirection"][name])
                for cell in weighted) / total,
            6,
        )
    bins: list[dict] = []
    for index, band in enumerate(template):
        occurrence = {
            name: round(
                sum(float(cell["weightM2"])
                    * float(cell["speedBins"][index]["occurrenceByDirection"][name])
                    for cell in weighted) / total,
                6,
            )
            for name in DIRECTIONS
        }
        bins.append({
            "bin": band["bin"],
            "speedLowMps": band["speedLowMps"],
            "speedHighMps": band["speedHighMps"],
            "occurrenceByDirection": occurrence,
        })
    derived: dict[str, float | None] = {}
    for name in DIRECTIONS:
        moment = 0.0
        mass = 0.0
        for band in bins:
            occurrence = band["occurrenceByDirection"][name]
            midpoint = 0.5 * (band["speedLowMps"] + band["speedHighMps"])
            mass += occurrence
            moment += occurrence * midpoint
        derived[name] = (round(moment / mass, 4) if mass > 0.0 else None)
    return {
        "frequencyByDirection": frequency,
        "frequencySum": round(sum(frequency.values()), 6),
        "speedBins": bins,
        "derivedMeanSpeedMps": derived,
        "derivedMeanSpeedMethod": (
            "Frequency-weighted midpoint of the area-weighted speed bins. "
            "PlanD does not publish a window mean; this figure is calculated "
            "from the occurrence tables and is not a measurement of its own."
        ),
        "weightM2": round(total, 3),
    }


def collect_window() -> int:
    """Write the area-weighted annual 500 m rose for every cell the window touches.

    The centroid file stays as cell 3463. This file is the study window.
    """
    west, south, east, north = _study_window()
    corner_xy = {
        "sw": _to_hk1980(west, south),
        "se": _to_hk1980(east, south),
        "nw": _to_hk1980(west, north),
        "ne": _to_hk1980(east, north),
    }
    min_e = min(point[0] for point in corner_xy.values())
    max_e = max(point[0] for point in corner_xy.values())
    min_n = min(point[1] for point in corner_xy.values())
    max_n = max(point[1] for point in corner_xy.values())
    try:
        rows = _index_rows()
    except Exception as exc:  # noqa: BLE001
        WINDOW_OUT.write_text(json.dumps({
            "artefact": "site_wind_window",
            "verified": False,
            "reason": f"index fetch failed: {exc}",
            "retrieved": date.today().isoformat(),
        }, indent=2), encoding="utf-8")
        print("window unverified:", exc)
        return 1

    annual_500 = [
        row for row in rows
        if row.get("RANGE_TYPE") == "annual" and row.get("HEIGHT") == "500"
    ]
    hits = []
    for row in annual_500:
        area = (
            _overlap(min_e, max_e, float(row["MIN_X"]), float(row["MAX_X"]))
            * _overlap(min_n, max_n, float(row["MIN_Y"]), float(row["MAX_Y"]))
        )
        if area > 0.0:
            hits.append((area, row))
    hits.sort(key=lambda item: _grid_id(item[1]))
    if not hits:
        WINDOW_OUT.write_text(json.dumps({
            "artefact": "site_wind_window",
            "verified": False,
            "reason": "no annual/500 cell intersects the study window",
            "retrieved": date.today().isoformat(),
        }, indent=2), encoding="utf-8")
        print("window unverified: no cells")
        return 1

    cells: list[dict] = []
    errors: list[str] = []
    for area, row in hits:
        grid_id = _grid_id(row)
        url = (row.get("FILE_URL") or "").strip()
        try:
            parsed = _parse_table(_fetch_text(url))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{grid_id}: {exc}")
            continue
        cells.append({
            "gridCellId": grid_id,
            "weightM2": round(area, 3),
            "hk1980": {
                "minEasting": float(row["MIN_X"]),
                "minNorthing": float(row["MIN_Y"]),
                "maxEasting": float(row["MAX_X"]),
                "maxNorthing": float(row["MAX_Y"]),
            },
            "fileUrl": url,
            "frequencyByDirection": parsed["frequencyByDirection"],
            "frequencySum": parsed["frequencySum"],
            "speedBins": parsed["speedBins"],
            "derivedMeanSpeedMps": parsed["derivedMeanSpeedMps"],
        })
    verified = not errors and len(cells) == len(hits)
    merged: dict = {}
    if verified:
        try:
            merged = merge_roses(cells)
        except ValueError as exc:
            errors.append(str(exc))
            verified = False
    total = sum(cell["weightM2"] for cell in cells) or 1.0
    for cell in cells:
        cell["weightShare"] = round(cell["weightM2"] / total, 6)
    document = {
        "artefact": "site_wind_window",
        "verified": verified,
        "retrieved": date.today().isoformat(),
        "retrievedTimezone": timezone.utc.tzname(None),
        "season": "annual",
        "heightM": 500,
        "method": (
            "Area-weighted mean of the PlanD annual 500 m occurrence tables "
            "for every cell whose HK1980 rectangle intersects the study "
            "window's HK1980 bounding box. The weight is that intersection "
            "area. It is not a new measurement and it is not a velocity."
        ),
        "studyWindow": {
            "west": west, "south": south, "east": east, "north": north,
            "hk1980Bbox": {
                "minEasting": round(min_e, 3),
                "minNorthing": round(min_n, 3),
                "maxEasting": round(max_e, 3),
                "maxNorthing": round(max_n, 3),
            },
        },
        "gridCellIds": [cell["gridCellId"] for cell in cells],
        "cells": cells,
        "merged": merged,
        "errors": errors,
        "whatThisIsNot": [
            "Not a velocity ratio and not a model result.",
            "Not a replacement for the centroid cell in hsk_site_wind.json. "
            "directionWeights=site still reads that cell.",
            "The corridor cost does not use these frequencies. "
            "directionWeights=window selects the headline corridor only.",
        ],
    }
    WINDOW_OUT.parent.mkdir(parents=True, exist_ok=True)
    WINDOW_OUT.write_text(json.dumps(document, indent=2), encoding="utf-8")
    print(
        "wrote", WINDOW_OUT, "verified", verified,
        "cells", document["gridCellIds"],
    )
    if errors:
        print("errors:", errors)
    return 0 if verified else 1


def main() -> int:
    west, south, east, north = _study_window()
    centre_lon = (west + east) / 2.0
    centre_lat = (south + north) / 2.0
    centre_xy = _to_hk1980(centre_lon, centre_lat)
    corners = {
        "sw": _to_hk1980(west, south),
        "se": _to_hk1980(east, south),
        "nw": _to_hk1980(west, north),
        "ne": _to_hk1980(east, north),
        "centre": centre_xy,
    }
    try:
        rows = _index_rows()
    except Exception as exc:  # noqa: BLE001 — the file must record the failure
        OUT.write_text(json.dumps({
            "artefact": "site_wind_regime",
            "verified": False,
            "reason": f"index fetch failed: {exc}",
            "indexUrl": INDEX_URL,
            "retrieved": date.today().isoformat(),
        }, indent=2), encoding="utf-8")
        print("unverified:", exc)
        return 1

    annual_500 = [
        row for row in rows
        if row.get("RANGE_TYPE") == "annual" and row.get("HEIGHT") == "500"
    ]
    centre_hits = [row for row in annual_500 if _cell_contains(row, *centre_xy)]
    if len(centre_hits) != 1:
        OUT.write_text(json.dumps({
            "artefact": "site_wind_regime",
            "verified": False,
            "reason": f"expected one annual/500 cell at the study centroid, found {len(centre_hits)}",
            "hk1980Centroid": {"easting": centre_xy[0], "northing": centre_xy[1]},
            "indexUrl": INDEX_URL,
            "retrieved": date.today().isoformat(),
        }, indent=2), encoding="utf-8")
        print("unverified: cell count", len(centre_hits))
        return 1

    cell = centre_hits[0]
    grid_id = cell.get("GRID_ID") or cell.get("\ufeffGRID_ID")
    covered_by: dict[str, str] = {}
    for name, xy in corners.items():
        hits = [row for row in annual_500 if _cell_contains(row, *xy)]
        covered_by[name] = (hits[0].get("GRID_ID") or hits[0].get("\ufeffGRID_ID")) if len(hits) == 1 else f"{len(hits)} hits"
    window_inside = set(covered_by.values()) == {grid_id}

    seasons: dict[str, dict] = {}
    errors: list[str] = []
    for season in SEASONS:
        heights: dict[str, dict] = {}
        for height in HEIGHTS:
            match = [
                row for row in rows
                if (row.get("GRID_ID") or row.get("\ufeffGRID_ID")) == grid_id
                and row.get("RANGE_TYPE") == season
                and row.get("HEIGHT") == str(height)
            ]
            if len(match) != 1:
                errors.append(f"{season} {height} m: {len(match)} index rows")
                continue
            url = (match[0].get("FILE_URL") or "").strip()
            try:
                parsed = _parse_table(_fetch_text(url))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{season} {height} m: {exc}")
                continue
            parsed["fileUrl"] = url
            heights[str(height)] = parsed
        seasons[season] = {"heightsM": heights}

    verified = not errors and all(
        str(height) in seasons[season]["heightsM"]
        for season in SEASONS for height in HEIGHTS
    )
    document = {
        "artefact": "site_wind_regime",
        "verified": verified,
        "retrieved": date.today().isoformat(),
        "retrievedTimezone": timezone.utc.tzname(None),
        "gridCellId": grid_id,
        "hk1980": {
            "crs": "EPSG:2326",
            "minEasting": float(cell["MIN_X"]),
            "minNorthing": float(cell["MIN_Y"]),
            "maxEasting": float(cell["MAX_X"]),
            "maxNorthing": float(cell["MAX_Y"]),
            "studyCentroid": {"easting": round(centre_xy[0], 3), "northing": round(centre_xy[1], 3)},
        },
        "wgs84": {
            "studyWindow": {"west": west, "south": south, "east": east, "north": north},
            "cell": _interpreted_wgs84(cell),
            "windowContainedInCell": window_inside,
            "cornerGridIds": covered_by,
            "headerNote": (
                "The published index headers MIN_LAT/MAX_LAT hold values near "
                "113 (longitude) and MIN_LNG/MAX_LNG hold values near 22 "
                "(latitude). cell above is interpreted by magnitude. The cell "
                "was selected on HK1980 easting/northing."
            ),
        },
        "provenance": {
            "dataset": "Planning Department Site Wind Availability Data",
            "datasetUrl": DATASET_URL,
            "indexUrl": INDEX_URL,
            "tableNote": (
                "Each table is percentage occurrence of directional winds, "
                "published as a fraction per speed bin. frequencyByDirection "
                "is the V_infinity Sum row. derivedMeanSpeedMps is calculated "
                "here from bin midpoints and is not a PlanD field."
            ),
        },
        "seasons": seasons,
        "errors": errors,
        "whatThisIsNot": [
            "Not a velocity ratio and not a model result.",
            "Not a replacement for the AVRG73 combined 40.8% NE/ENE/E fact. "
            "That reference file is unchanged.",
            "The corridor endpoint does not use these frequencies unless the "
            "caller passes directionWeights=site.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(document, indent=2), encoding="utf-8")
    print("wrote", OUT, "verified", verified, "grid", grid_id, "window inside", window_inside)
    if errors:
        print("errors:", errors)
    return 0 if verified else 1


if __name__ == "__main__":
    if "--window-only" in sys.argv:
        sys.exit(collect_window())
    sys.exit(main())
