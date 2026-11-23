"""Coarse OpenFOAM wind channel around the 2.5D massing.

The obstacles are the same extruded footprints the viewer draws in 2.5D
(``buildings_hsk.json``: each ring, height ``height_m``). They are snapped
onto a Cartesian mesh and removed with ``subsetMesh``, so the air cannot
pass through a box.

The solve is steady incompressible RANS (``simpleFoam``, k-epsilon). It is
run from this script through the OpenCFD runtime image, never from an API
request. OpenFOAM source is not vendored. The image is GPL-3.0.

Nothing here is a velocity ratio, a Lawson criterion, or a pass/fail.
The inlet speed is the PlanD annual 500 m frequency-weighted bin midpoint
for NE, brought down to 10 m with a stated power law. PlanD does not
publish that 10 m speed.

Run from backend/:

    ./.venv313/bin/python scripts/openfoam_channel/run_channel.py
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

# Meteorological FROM bearings, clockwise from north. Same table as
# design_metrics.CARDINALS. Kept here so the script runs without the app package.
CARDINALS: dict[str, float] = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5, "E": 90.0, "ESE": 112.5,
    "SE": 135.0, "SSE": 157.5, "S": 180.0, "SSW": 202.5, "SW": 225.0,
    "WSW": 247.5, "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}

BACKEND = Path(__file__).resolve().parents[2]
# The case sits outside the repo. Docker Desktop is denied the Desktop folder
# by macOS, and the mesh is not source. The GeoJSON and sidecar are copied back.
CASE = Path.home() / ".cache" / "sandbox-openfoam" / "channel"
BUILDINGS = BACKEND / "data" / "rasters" / "buildings_hsk.json"
BOUNDS_FILE = BACKEND / "data" / "rasters" / "wetgrid_hsk.json"
SITE_WIND = BACKEND / "data" / "reference" / "hsk_site_wind.json"
STREAMLINES = BACKEND / "data" / "openfoam" / "channel_streamlines.geojson"
STREAM_DIR = BACKEND / "data" / "openfoam" / "streamlines"
INDEX = BACKEND / "data" / "openfoam" / "wind_index.json"
SIDECAR = BACKEND / "data" / "openfoam" / "channel_sidecar.json"
SEASONS = ("annual", "summer", "winter")
HEIGHTS = ("500", "300", "200")

IMAGE = "opencfd/openfoam-run:2512"
DX_TARGET = 20.0
DY_TARGET = 20.0
DZ = 8.0
Z_MAX = 120.0
M_PER_DEG_LAT = 110_540.0
POWER_ALPHA = 0.22
POWER_Z_REF_M = 500.0
INLET_Z_M = 10.0
DIRECTION = "NE"

HEADER = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _study_bounds() -> tuple[float, float, float, float]:
    doc = json.loads(BOUNDS_FILE.read_text(encoding="utf-8"))
    west, south, east, north = doc["inputs"]["bounds"]
    return float(west), float(south), float(east), float(north)


def _inlet_speed() -> tuple[float, float, str]:
    """``(u_10, u_500, note)``. Refuses to invent a speed if the file is absent."""
    if not SITE_WIND.exists():
        raise RuntimeError("hsk_site_wind.json is missing; refusing to invent an inlet speed")
    doc = json.loads(SITE_WIND.read_text(encoding="utf-8"))
    if not doc.get("verified"):
        raise RuntimeError("hsk_site_wind.json is not verified; refusing to invent an inlet speed")
    level = doc["seasons"]["annual"]["heightsM"]["500"]
    derived = level["derivedMeanSpeedMps"][DIRECTION]
    if derived is None:
        raise RuntimeError(f"no derived {DIRECTION} speed in the PlanD table")
    u_500 = float(derived)
    u_10 = u_500 * (INLET_Z_M / POWER_Z_REF_M) ** POWER_ALPHA
    note = (
        f"Inlet speed {u_10:.3f} m/s is the PlanD annual 500 m frequency-weighted "
        f"bin midpoint for {DIRECTION} ({u_500:.4f} m/s, grid cell "
        f"{doc.get('gridCellId')}) times (10/500)^{POWER_ALPHA}. "
        "PlanD publishes occurrence bins, not this 10 m speed. "
        "The profile is uniform across the inlet at that 10 m value."
    )
    return u_10, u_500, note


def inlet_components(name: str, speed: float) -> tuple[float, float]:
    """Velocity of a wind blowing *from* ``name``. East and north are positive."""
    travel = math.radians(CARDINALS[name] + 180.0)
    return speed * math.sin(travel), speed * math.cos(travel)


def face_roles(u_east: float, u_north: float) -> dict[str, str]:
    """Which boundary the wind enters, leaves, or passes along.

    A component near zero is a side, not an inlet. Pure north is the north
    face only; a diagonal uses the two upwind faces.
    """
    eps = 1e-8

    def role(inward: float) -> str:
        if inward > eps:
            return "inlet"
        if inward < -eps:
            return "outlet"
        return "side"

    return {
        # Inward is the component pointing into the domain.
        "east": role(-u_east),
        "west": role(u_east),
        "north": role(-u_north),
        "south": role(u_north),
        "ground": "wall",
        "top": "side",
        "buildings": "wall",
    }


def _tables() -> dict:
    if not SITE_WIND.exists():
        raise RuntimeError("hsk_site_wind.json is missing; refusing to invent an inlet speed")
    doc = json.loads(SITE_WIND.read_text(encoding="utf-8"))
    if not doc.get("verified"):
        raise RuntimeError("hsk_site_wind.json is not verified; refusing to invent an inlet speed")
    tables: dict = {}
    for season in SEASONS:
        tables[season] = {}
        for height in HEIGHTS:
            level = doc["seasons"][season]["heightsM"][height]
            directions = {}
            for name in CARDINALS:
                derived = level["derivedMeanSpeedMps"][name]
                freq = level["frequencyByDirection"][name]
                if derived is None or freq is None:
                    directions[name] = {
                        "frequency": freq,
                        "derivedMeanSpeedMps": derived,
                        "inletSpeedMps": None,
                    }
                    continue
                u_500 = float(derived)
                u_10 = u_500 * (INLET_Z_M / POWER_Z_REF_M) ** POWER_ALPHA
                directions[name] = {
                    "frequency": float(freq),
                    "derivedMeanSpeedMps": round(u_500, 4),
                    "inletSpeedMps": round(u_10, 4),
                }
            tables[season][height] = {
                "fileUrl": level.get("fileUrl"),
                "directions": directions,
            }
    return {
        "artefact": "openfoam-wind-index",
        "verified": True,
        "gridCellId": doc.get("gridCellId"),
        "directions": list(CARDINALS),
        "degreesFrom": CARDINALS,
        "seasons": list(SEASONS),
        "heightsM": [int(h) for h in HEIGHTS],
        "solvedSeason": "annual",
        "solvedHeightM": 500,
        "defaultDirection": DIRECTION,
        "tables": tables,
        "scaleNote": (
            "Each bearing is solved at its annual 500 m inlet. Another table "
            "keeps those paths and multiplies the recorded speeds by the ratio "
            "of the two 10 m inlets. PlanD does not publish the 10 m speed."
        ),
    }


def _point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _buildings(west: float, south: float, m_lon: float) -> list[tuple[list[tuple[float, float]], float]]:
    doc = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    out = []
    for feature in doc["features"]:
        props = feature.get("properties") or {}
        try:
            height = float(props.get("height_m") or 0.0)
        except (TypeError, ValueError):
            continue
        if height <= 0.0:
            continue
        geom = feature.get("geometry") or {}
        rings = []
        if geom.get("type") == "Polygon":
            rings = [geom["coordinates"][0]]
        elif geom.get("type") == "MultiPolygon":
            rings = [part[0] for part in geom["coordinates"] if part]
        for ring in rings:
            local = [
                ((float(pt[0]) - west) * m_lon, (float(pt[1]) - south) * M_PER_DEG_LAT)
                for pt in ring
            ]
            if len(local) >= 3:
                out.append((local, height))
    return out


def _occupancy(buildings, nx: int, ny: int, nz: int, dx: float, dy: float) -> np.ndarray:
    """True where a 2.5D extrusion occupies the cell. The top layer stays open."""
    solid = np.zeros((nx, ny, nz), dtype=bool)
    probes = ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75))
    for ring, height in buildings:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        i0 = max(0, int(min(xs) / dx))
        i1 = min(nx, int(max(xs) / dx) + 1)
        j0 = max(0, int(min(ys) / dy))
        j1 = min(ny, int(max(ys) / dy) + 1)
        k_top = min(nz - 1, int(math.ceil(height / DZ)))
        if k_top <= 0:
            k_top = 1
        for i in range(i0, i1):
            for j in range(j0, j1):
                hit = False
                for fx, fy in probes:
                    if _point_in_ring((i + fx) * dx, (j + fy) * dy, ring):
                        hit = True
                        break
                if hit:
                    solid[i, j, :k_top] = True
    return solid


def _foam(cls: str, obj: str, body: str) -> str:
    return HEADER.format(cls=cls, obj=obj) + "\n" + body


def write_case(solid: np.ndarray, dx: float, dy: float) -> None:
    nx, ny, nz = solid.shape
    lx, ly, lz = nx * dx, ny * dy, nz * DZ
    _write(CASE / "system" / "blockMeshDict", _foam("dictionary", "blockMeshDict", f"""
scale   1;
vertices
(
    (0 0 0)
    ({lx:.4f} 0 0)
    ({lx:.4f} {ly:.4f} 0)
    (0 {ly:.4f} 0)
    (0 0 {lz:.4f})
    ({lx:.4f} 0 {lz:.4f})
    ({lx:.4f} {ly:.4f} {lz:.4f})
    (0 {ly:.4f} {lz:.4f})
);
blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);
edges ();
boundary
(
    east
    {{
        type patch;
        faces ((1 5 6 2));
    }}
    north
    {{
        type patch;
        faces ((3 2 6 7));
    }}
    west
    {{
        type patch;
        faces ((0 4 7 3));
    }}
    south
    {{
        type patch;
        faces ((0 1 5 4));
    }}
    ground
    {{
        type wall;
        faces ((0 3 2 1));
    }}
    top
    {{
        type patch;
        faces ((4 5 6 7));
    }}
);
mergePatchPairs ();
"""))

    actions = []
    first = True
    for i in range(nx):
        for j in range(ny):
            ks = np.flatnonzero(solid[i, j])
            if ks.size == 0:
                continue
            k1 = int(ks.max()) + 1
            verb = "new" if first else "add"
            first = False
            actions.append(f"""
    {{
        name    buildings;
        type    cellSet;
        action  {verb};
        source  boxToCell;
        box     ({i * dx:.4f} {j * dy:.4f} 0) ({(i + 1) * dx:.4f} {(j + 1) * dy:.4f} {k1 * DZ:.4f});
    }}""")
    if not actions:
        raise RuntimeError("no building cells; refusing to solve an empty channel")
    # subsetMesh keeps the named set. Keep the air, so the boxes are the hole.
    actions.append(f"""
    {{
        name    air;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     (0 0 0) ({lx:.4f} {ly:.4f} {lz:.4f});
    }}
    {{
        name    air;
        type    cellSet;
        action  subtract;
        source  cellToCell;
        sourceInfo
        {{
            set buildings;
        }}
    }}""")
    _write(CASE / "system" / "topoSetDict", _foam("dictionary", "topoSetDict",
                                                  "actions\n(\n" + "\n".join(actions) + "\n);\n"))

    _write(CASE / "system" / "controlDict", _foam("dictionary", "controlDict", """
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         250;
deltaT          1;
writeControl    timeStep;
writeInterval   250;
purgeWrite      1;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable false;
"""))
    _write(CASE / "system" / "fvSchemes", _foam("dictionary", "fvSchemes", """
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
"""))
    _write(CASE / "system" / "fvSolution", _foam("dictionary", "fvSolution", """
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-6;
        relTol          0.05;
        smoother        GaussSeidel;
    }
    "(U|k|epsilon)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-6;
        relTol          0.05;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    residualControl
    {
        p               1e-3;
        U               1e-3;
        "(k|epsilon)"   1e-3;
    }
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; k 0.5; epsilon 0.5; }
}
"""))
    _write(CASE / "constant" / "transportProperties", _foam(
        "dictionary", "transportProperties",
        "transportModel  Newtonian;\nnu              [0 2 -1 0 0 0 0] 1.5e-05;\n"))
    _write(CASE / "constant" / "physicalProperties", _foam(
        "dictionary", "physicalProperties",
        "viscosityModel  constant;\nnu              1.5e-05;\n"))
    _write(CASE / "constant" / "turbulenceProperties", _foam(
        "dictionary", "turbulenceProperties",
        "simulationType  RAS;\nRAS\n{\n    RASModel    kEpsilon;\n    turbulence  on;\n    printCoeffs on;\n}\n"))
    _write(CASE / "constant" / "momentumTransport", _foam(
        "dictionary", "momentumTransport",
        "simulationType  RAS;\nRAS\n{\n    model       kEpsilon;\n    turbulence  on;\n    printCoeffs on;\n}\n"))


def _docker(args: list[str]) -> None:
    cmd = [
        "docker", "run", "--rm", "--platform", "linux/arm64",
        "-v", f"{CASE}:/case", "-w", "/case",
        "-u", f"{__import__('os').getuid()}:{__import__('os').getgid()}",
        IMAGE, "-c", "cd /case && " + " ".join(args),
    ]
    print(" ".join(args), flush=True)
    subprocess.run(cmd, check=True)


def _patches() -> list[tuple[str, str]]:
    text = (CASE / "constant" / "polyMesh" / "boundary").read_text(encoding="utf-8")
    found = re.findall(r"\n\s{4}(\w+)\n\s{4}\{[^}]*?type\s+(\w+);", text)
    return [(name, kind) for name, kind in found if name != "FoamFile"]


def _mark_buildings_as_walls() -> None:
    path = CASE / "constant" / "polyMesh" / "boundary"
    text = path.read_text(encoding="utf-8")
    text2, n = re.subn(
        r"(buildings\s*\{[^}]*?type\s+)\w+;",
        r"\1wall;",
        text,
        count=1,
    )
    text2 = text2.replace("inGroups        1(empty);", "inGroups        1(wall);", 1)
    if n != 1:
        raise RuntimeError("subsetMesh did not leave a buildings patch")
    path.write_text(text2, encoding="utf-8")


def _write_fields(dest: Path, u_east: float, u_north: float, roles: dict[str, str]) -> None:
    u = (u_east, u_north, 0.0)
    k = 1.5 * (0.10 * math.hypot(u_east, u_north)) ** 2
    eps = (0.09 ** 0.75) * (k ** 1.5) / 10.0
    patches = _patches()

    def role(name: str, kind: str) -> str:
        return roles.get(name, "wall" if kind == "wall" else "side")

    def bc_u(name: str, kind: str) -> str:
        which = role(name, kind)
        if which == "inlet":
            return f"        type fixedValue;\n        value uniform ({u[0]:.6f} {u[1]:.6f} 0);\n"
        if which == "outlet":
            return (
                "        type inletOutlet;\n"
                f"        inletValue uniform ({u[0]:.6f} {u[1]:.6f} 0);\n"
                "        value uniform (0 0 0);\n"
            )
        if which == "wall":
            return "        type noSlip;\n"
        return "        type slip;\n"

    def bc_p(name: str, kind: str) -> str:
        if role(name, kind) == "outlet":
            return "        type fixedValue;\n        value uniform 0;\n"
        return "        type zeroGradient;\n"

    def bc_k(name: str, kind: str) -> str:
        which = role(name, kind)
        if which == "inlet":
            return f"        type fixedValue;\n        value uniform {k:.6e};\n"
        if which == "outlet":
            return (
                "        type inletOutlet;\n"
                f"        inletValue uniform {k:.6e};\n"
                f"        value uniform {k:.6e};\n"
            )
        if which == "wall":
            return "        type kqRWallFunction;\n        value uniform 1e-10;\n"
        return "        type zeroGradient;\n"

    def bc_eps(name: str, kind: str) -> str:
        which = role(name, kind)
        if which == "inlet":
            return f"        type fixedValue;\n        value uniform {eps:.6e};\n"
        if which == "outlet":
            return (
                "        type inletOutlet;\n"
                f"        inletValue uniform {eps:.6e};\n"
                f"        value uniform {eps:.6e};\n"
            )
        if which == "wall":
            return f"        type epsilonWallFunction;\n        value uniform {eps:.6e};\n"
        return "        type zeroGradient;\n"

    def bc_nut(name: str, kind: str) -> str:
        if role(name, kind) == "wall":
            return "        type nutkWallFunction;\n        value uniform 0;\n"
        return "        type calculated;\n        value uniform 0;\n"

    def body(dimensions: str, internal: str, writer) -> str:
        blocks = []
        for name, kind in patches:
            blocks.append(f"    {name}\n    {{\n{writer(name, kind)}    }}")
        return f"dimensions      {dimensions};\ninternalField   {internal};\nboundaryField\n{{\n" + "\n".join(blocks) + "\n}\n"

    _write(dest / "U", _foam("volVectorField", "U", body(
        "[0 1 -1 0 0 0 0]", f"uniform ({u[0]:.6f} {u[1]:.6f} 0)", bc_u)))
    _write(dest / "p", _foam("volScalarField", "p", body(
        "[0 2 -2 0 0 0 0]", "uniform 0", bc_p)))
    _write(dest / "k", _foam("volScalarField", "k", body(
        "[0 2 -2 0 0 0 0]", f"uniform {k:.6e}", bc_k)))
    _write(dest / "epsilon", _foam("volScalarField", "epsilon", body(
        "[0 2 -3 0 0 0 0]", f"uniform {eps:.6e}", bc_eps)))
    _write(dest / "nut", _foam("volScalarField", "nut", body(
        "[0 2 -1 0 0 0 0]", "uniform 0", bc_nut)))


def _vectors(text: str) -> np.ndarray:
    match = re.search(r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s+\((.*?)\)\s*;", text, re.S)
    if not match:
        raise RuntimeError("U/C field is not an ascii nonuniform vector list")
    rows = re.findall(r"\(([^)]*)\)", match.group(2))
    return np.array([[float(p) for p in row.split()] for row in rows], dtype=np.float64)


def _latest_time() -> Path:
    times = []
    for path in CASE.iterdir():
        if path.is_dir():
            try:
                value = float(path.name)
            except ValueError:
                continue
            if value > 0:
                times.append((value, path))
    if not times:
        raise RuntimeError("simpleFoam wrote no time directory")
    return max(times)[1]


def trace(grid: dict, time_dir: Path, roles: dict[str, str]) -> dict:
    centres = _vectors((time_dir / "C").read_text(encoding="utf-8"))
    velocity = _vectors((time_dir / "U").read_text(encoding="utf-8"))
    if not np.isfinite(velocity).all():
        raise RuntimeError("the velocity field contains non-finite values")
    nx, ny, nz = grid["nx"], grid["ny"], grid["nz"]
    dx, dy, dz = grid["dx"], grid["dy"], grid["dz"]
    occupied = np.zeros((nx, ny, nz), dtype=bool)
    ugrid = np.zeros((nx, ny, nz, 3), dtype=np.float64)
    for centre, vel in zip(centres, velocity):
        i = int(centre[0] / dx)
        j = int(centre[1] / dy)
        k = int(centre[2] / dz)
        if 0 <= i < nx and 0 <= j < ny and 0 <= k < nz:
            occupied[i, j, k] = True
            ugrid[i, j, k] = vel

    west, south = grid["west"], grid["south"]
    m_lon = grid["mPerDegLon"]
    seeds = []
    heights = (1, 2, 4)

    def plant(i: int, j: int, k: int, x: float, y: float) -> None:
        if 0 <= k < nz and occupied[i, j, k]:
            seeds.append((x, y, (k + 0.5) * dz))

    if roles.get("north") == "inlet":
        for i in range(0, nx, 2):
            for k in heights:
                plant(i, ny - 1, k, (i + 0.5) * dx, (ny - 0.5) * dy)
    if roles.get("south") == "inlet":
        for i in range(0, nx, 2):
            for k in heights:
                plant(i, 0, k, (i + 0.5) * dx, 0.5 * dy)
    if roles.get("east") == "inlet":
        for j in range(0, ny, 2):
            for k in heights:
                plant(nx - 1, j, k, (nx - 0.5) * dx, (j + 0.5) * dy)
    if roles.get("west") == "inlet":
        for j in range(0, ny, 2):
            for k in heights:
                plant(0, j, k, 0.5 * dx, (j + 0.5) * dy)

    features = []
    for seed in seeds:
        pos = np.array(seed, dtype=np.float64)
        line = []
        speeds = []
        for _ in range(180):
            i = int(pos[0] / dx)
            j = int(pos[1] / dy)
            k = int(pos[2] / dz)
            if not (0 <= i < nx and 0 <= j < ny and 0 <= k < nz) or not occupied[i, j, k]:
                break
            vel = ugrid[i, j, k]
            speed = float(np.linalg.norm(vel))
            if speed < 0.2:
                break
            line.append((
                west + pos[0] / m_lon,
                south + pos[1] / M_PER_DEG_LAT,
                float(pos[2]),
            ))
            speeds.append(speed)
            pos = pos + vel / speed * 10.0
        if len(line) < 4:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "speedMps": round(float(np.mean(speeds)), 3),
                "speedMinMps": round(float(min(speeds)), 3),
                "speedMaxMps": round(float(max(speeds)), 3),
            },
            "geometry": {"type": "LineString", "coordinates": [[x, y, z] for x, y, z in line]},
        })
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "solver": "simpleFoam",
            "cellsReportingVelocity": int(occupied.sum()),
        },
    }


def _sidecar(status: str, **extra) -> None:
    body = {
        "artefact": "openfoam-wind-channel",
        "status": status,
        "verified": status == "SOLVED",
        "method": (
            "Steady incompressible RANS, simpleFoam, k-epsilon, on a Cartesian "
            "mesh. 2.5D footprint extrusions are removed with subsetMesh so the "
            "air flows around them. Streamlines are integrated on the solved "
            "velocity. The solve is not on the API request path."
        ),
        "limitation": (
            "Coarse steady RANS on a flat ground. Vertical blockage is snapped "
            f"to {DZ:.0f} m layers and the top layer is left open. The inlet is "
            "a uniform vector, not a measured profile. This is not a velocity "
            "ratio, not a Lawson / NEN / Davenport result, and not a pass/fail. "
            "OpenFOAM source is not in this repository."
        ),
        "licence": "GPL-3.0",
        "image": IMAGE,
        "sourceRepositories": [
            "https://github.com/OpenFOAM/OpenFOAM-dev",
            "https://develop.openfoam.com/Development/openfoam",
        ],
        "direction": DIRECTION,
        "retrieved": date.today().isoformat(),
        **extra,
    }
    _write(SIDECAR, json.dumps(body, indent=2))


def _solve_script(names: list[str]) -> str:
    quoted = " ".join(names)
    return f"""shopt -s nullglob
for d in {quoted}; do
  rm -rf /case/postProcessing /case/0
  for t in /case/[0-9]*; do rm -rf "$t"; done
  cp -a "/case/runs/$d/0" /case/0
  if simpleFoam > "/case/runs/$d/log" 2>&1 \\
     && postProcess -func writeCellCentres -latestTime >> "/case/runs/$d/log" 2>&1; then
    latest=$(ls -d /case/[0-9]* | sort -n | tail -1)
    rm -rf "/case/runs/$d/result"
    mkdir -p "/case/runs/$d/result"
    cp -a "$latest" "/case/runs/$d/result/time"
    echo "OK $d $latest"
  else
    echo "FAIL $d"
  fi
done
exit 0
"""


def main() -> int:
    try:
        index = _tables()
    except (RuntimeError, KeyError, TypeError) as exc:
        _sidecar("NOT_RUN", reason=str(exc))
        print("NOT_RUN:", exc)
        return 1
    _write(INDEX, json.dumps(index, indent=2))
    annual = index["tables"]["annual"]["500"]["directions"]

    if shutil.which("docker") is None:
        _sidecar("NOT_RUN", reason="docker is not on PATH")
        print("NOT_RUN: docker is not on PATH")
        return 1
    west, south, east, north = _study_bounds()
    mid_lat = (south + north) / 2.0
    m_lon = 111_320.0 * math.cos(math.radians(mid_lat))
    lx = (east - west) * m_lon
    ly = (north - south) * M_PER_DEG_LAT
    nx = max(8, int(round(lx / DX_TARGET)))
    ny = max(8, int(round(ly / DY_TARGET)))
    nz = int(round(Z_MAX / DZ))
    dx, dy = lx / nx, ly / ny
    buildings = _buildings(west, south, m_lon)
    solid = _occupancy(buildings, nx, ny, nz, dx, dy)
    if CASE.exists():
        shutil.rmtree(CASE)
    write_case(solid, dx, dy)
    grid = {
        "west": west, "south": south, "east": east, "north": north,
        "nx": nx, "ny": ny, "nz": nz, "dx": dx, "dy": dy, "dz": DZ,
        "mPerDegLon": m_lon, "buildingCells": int(solid.sum()),
        "footprints": len(buildings),
    }
    _write(CASE / "grid.json", json.dumps(grid, indent=2))
    print(f"mesh {nx}x{ny}x{nz} building cells {int(solid.sum())}")

    try:
        _docker(["blockMesh", "&&", "topoSet", "&&", "subsetMesh", "-overwrite", "air", "-patch", "buildings"])
        _mark_buildings_as_walls()
        solved_names = []
        for name in CARDINALS:
            cell = annual[name]
            if cell["inletSpeedMps"] is None:
                print(f"skip {name}: no derived speed")
                continue
            u_east, u_north = inlet_components(name, float(cell["inletSpeedMps"]))
            roles = face_roles(u_east, u_north)
            _write_fields(CASE / "runs" / name / "0", u_east, u_north, roles)
            _write(CASE / "runs" / name / "roles.json", json.dumps(roles))
            solved_names.append(name)
        _write(CASE / "solve.sh", _solve_script(solved_names))
        _docker(["bash", "solve.sh"])
    except (subprocess.CalledProcessError, RuntimeError, OSError) as exc:
        _sidecar("FAILED", reason=str(exc), **{k: grid[k] for k in ("nx", "ny", "nz", "buildingCells")})
        print("FAILED:", exc)
        return 1

    counts = {}
    mesh = {"nx": nx, "ny": ny, "nz": nz, "dxM": round(dx, 3), "dyM": round(dy, 3), "dzM": DZ}
    for name in solved_names:
        time_dir = CASE / "runs" / name / "result" / "time"
        if not (time_dir / "U").exists():
            print(f"missing field {name}")
            continue
        roles = json.loads((CASE / "runs" / name / "roles.json").read_text(encoding="utf-8"))
        cell = annual[name]
        try:
            collection = trace(grid, time_dir, roles)
        except RuntimeError as exc:
            print(f"trace {name}: {exc}")
            continue
        collection["properties"].update({
            "inletSpeedMps": cell["inletSpeedMps"],
            "inletSpeedAt500mMps": cell["derivedMeanSpeedMps"],
            "direction": name,
            "season": "annual",
            "heightM": 500,
            "mesh": mesh,
        })
        _write(STREAM_DIR / f"{name}.geojson", json.dumps(collection))
        if name == DIRECTION:
            _write(STREAMLINES, json.dumps(collection))
        counts[name] = len(collection["features"])
        print(f"{name} {counts[name]} streamlines inlet {cell['inletSpeedMps']} m/s")

    if len(counts) != len(solved_names):
        _sidecar("FAILED", reason="a direction did not produce a finite field", solved=counts)
        return 1
    _sidecar(
        "SOLVED",
        inletNote=index["scaleNote"],
        directions=counts,
        mesh=mesh,
        buildingCells=grid["buildingCells"],
        solvedSeason="annual",
        solvedHeightM=500,
    )
    print(f"SOLVED {len(counts)} directions -> {STREAM_DIR}")
    return 0


def test_ne_enters_on_the_north_and_east_faces():
    u_east, u_north = inlet_components("NE", 2.922)
    roles = face_roles(u_east, u_north)
    assert roles["north"] == "inlet" and roles["east"] == "inlet"
    assert roles["south"] == "outlet" and roles["west"] == "outlet"
    assert u_east < 0 and u_north < 0


def test_cardinal_winds_use_one_inlet_face():
    pairs = {
        "N": ("north", "south"),
        "E": ("east", "west"),
        "S": ("south", "north"),
        "W": ("west", "east"),
    }
    for name, (inlet, outlet) in pairs.items():
        roles = face_roles(*inlet_components(name, 2.0))
        assert roles[inlet] == "inlet"
        assert roles[outlet] == "outlet"
        for face in ("north", "south", "east", "west"):
            if face not in (inlet, outlet):
                assert roles[face] == "side"


def test_annual_500_ne_inlet_matches_the_pland_derivation():
    cell = _tables()["tables"]["annual"]["500"]["directions"]["NE"]
    assert cell["derivedMeanSpeedMps"] == 6.9095
    assert abs(cell["inletSpeedMps"] - 2.922) < 0.001
    assert cell["frequency"] == 0.107


if __name__ == "__main__":
    sys.exit(main())
