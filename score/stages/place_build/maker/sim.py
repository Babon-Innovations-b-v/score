"""A made model made sim-ready: its collision hulls (CoACD's approximate convex decomposition), its mass from those
hulls' volume and its material class's density, its friction and restitution from the class.

A made thing is mostly hollow (a steel bed is tubes, a crate is walls), so the hulls hold the material only as a shell
of the class's sheet thickness inside their outside: each hull's solid volume is the area of its faces that lie outside
every other hull (where two hulls meet is inside the body, not its skin) times the sheet, never more than its whole
volume (a hull thinner than two sheets, a bar or a board, is solid), and a class with no sheet (stone) is solid
throughout. A picture-made mesh's own area counted both skins of every thin part and every face inside it (the
TRELLIS.2 test's masses came out 1.6 to 4 times its neighbours'). A hull still closes over a frame's gaps, so a frame's
mass is high: its record says the measure it was made by. Steel is SCORE's own row
(data/physics/materials.json, read, never copied); the other classes are textbook densities and friction pairs, their
sheets assumptions as steel's is, kept here so the physics layer's own table (which keys the physics rows) is not moved.

    MATERIALS, material(name)                     the classes
    hulls_of(vertices, faces) -> [(points, triangles)]
    physical(hull_list, name) -> {"mass_kg", "solid_m3", "hull_m3", "hulls", "static", "dynamic", "restitution", ...}
"""
import json
import pathlib

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[4]
# density kg/m^3; sheet metres (None: solid); friction against the same class, static and dynamic; restitution.
# Engineering ToolBox's densities (pine 550, ABS 1050, polyester fabric 1380 woven to about half, granite and basalt
# 2700) and friction tables (wood on wood dry 0.25-0.5, rubber about 1, stone 0.6-0.7); restitution assumptions.
OWN = {
    "wood": {"density": 550.0, "sheet": 0.018, "static": 0.45, "dynamic": 0.35, "restitution": 0.3},
    "plastic": {"density": 1050.0, "sheet": 0.003, "static": 0.40, "dynamic": 0.30, "restitution": 0.4},
    "fabric": {"density": 700.0, "sheet": 0.004, "static": 0.60, "dynamic": 0.50, "restitution": 0.1},
    "rubber": {"density": 1100.0, "sheet": 0.01, "static": 1.00, "dynamic": 0.80, "restitution": 0.6},
    "glass": {"density": 2500.0, "sheet": 0.006, "static": 0.90, "dynamic": 0.40, "restitution": 0.3},
    "paper": {"density": 700.0, "sheet": 0.002, "static": 0.50, "dynamic": 0.40, "restitution": 0.1},
    "stone": {"density": 2700.0, "sheet": None, "static": 0.65, "dynamic": 0.55, "restitution": 0.2},
}
HULLS = 48  # CoACD's most hulls a model
CONCAVITY = 0.03  # CoACD's threshold, its default's middle
SPOTS = 4000  # spots a hull's skin is read at
INSIDE = 1e-4  # metres: a spot on another hull's faces, or inside them, is covered (where two hulls meet is inside)


def materials():
    """Every class: SCORE's own rows, then the maker's."""
    own = json.loads((REPO / "data/physics/materials.json").read_text())["materials"]
    return {**OWN, **own}


def material(name):
    found = materials()
    if name not in found:
        raise ValueError(f"no material class {name!r} (the classes: {', '.join(sorted(found))})")
    return found[name]


def hulls_of(vertices, faces):
    """CoACD's convex hulls of the mesh: [(points, triangles)]."""
    import coacd
    coacd.set_log_level("error")
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(vertices, float), np.asarray(faces, int)), threshold=CONCAVITY,
                            max_convex_hull=HULLS, seed=7)
    return [(np.asarray(points, float), np.asarray(triangles, int)) for points, triangles in parts]


def area_and_volume(points, triangles):
    """A closed hull's area (m^2) and volume (m^3, by the divergence theorem over its outward faces)."""
    corners = points[triangles]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    area = np.linalg.norm(crossed, axis=1).sum() / 2
    volume = abs(np.einsum("ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum()) / 6
    return area, volume


def planes(points, triangles):
    """A convex hull's face planes as (unit outward normals, offsets): a point is inside where every n.p <= d."""
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    kept = lengths > 1e-12
    normals = normals[kept] / lengths[kept, None]
    offsets = np.einsum("ij,ij->i", normals, corners[kept, 0])
    middle = points.mean(0)
    flipped = normals @ middle > offsets  # faces wound inward
    normals[flipped], offsets[flipped] = -normals[flipped], -offsets[flipped]
    return normals, offsets


def outside_share(points, triangles, others, count=SPOTS):
    """The share of a hull's surface outside every hull in `others` (their planes), read at `count` spots spread over
    it by area (a fixed seed)."""
    if not others:
        return 1.0
    corners = points[triangles]
    areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    random = np.random.default_rng(7)
    faces = random.choice(len(triangles), count, p=areas / areas.sum())
    first, second = random.random(count), random.random(count)
    folded = first + second > 1
    first[folded], second[folded] = 1 - first[folded], 1 - second[folded]
    spots = (corners[faces, 0] + first[:, None] * (corners[faces, 1] - corners[faces, 0])
             + second[:, None] * (corners[faces, 2] - corners[faces, 0]))
    covered = np.zeros(count, bool)
    for normals, offsets in others:
        covered |= ((spots @ normals.T) <= offsets + INSIDE).all(1)
    return 1.0 - covered.mean()


def physical(hull_list, name):
    """The model's mass, volumes and contact numbers from its hulls and its material class."""
    spec = material(name)
    solid = whole = 0.0
    bounds = [planes(points, triangles) for points, triangles in hull_list]
    for number, (points, triangles) in enumerate(hull_list):
        area, volume = area_and_volume(points, triangles)
        whole += volume
        if spec["sheet"] is None:
            solid += volume
            continue
        skin = area * outside_share(points, triangles, bounds[:number] + bounds[number + 1:])
        solid += min(skin * spec["sheet"], volume)
    return {"material": name, "density": spec["density"], "sheet": spec["sheet"],
            "mass_kg": round(float(solid * spec["density"]), 2), "solid_m3": round(float(solid), 5),
            "hull_m3": round(float(whole), 5), "measure": "the hulls' outside skin times the sheet (solid when thinner)",
            "hulls": len(hull_list), "static": spec["static"], "dynamic": spec["dynamic"],
            "restitution": spec["restitution"]}
