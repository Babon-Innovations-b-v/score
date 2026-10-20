"""Snap at work in the greenhouse: one of its beds placed again by the snap's own free placement (tools/usd/snap.py
`place_free`) among the boxes its scene record lays (the other beds, the tarps, the low plot walls): a seeded spot in
the room, dropped onto what is under it, kept when it hits nothing. The slider runs it again with other seeds.

Note: the room's furniture models are not on this machine, so the boxes of the scene record stand for what is
there; run it on the place's composed stage once its models are fetched here."""
import json
import sys

import numpy as np
import trimesh

ALGORITHM = "snap"
PLACE = "greenhouse"
MOVED = "bed_4_4"
SEEDS = tuple(range(8))
INSET = 0.5  # metres in from the floor's edge: the rectangle the spots are tried in


def plan_point(east, south):
    return [round(float(east), 2), round(float(-south), 2)]


def footprint(mesh, offset=(0.0, 0.0, 0.0)):
    (low_x, _, low_z), (high_x, _, high_z) = mesh.bounds + np.asarray(offset)
    return [plan_point(x, z) for x, z in ((low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z))]


def boxes(scene):
    """{name: box mesh} of every box the scene record lays."""
    found = {}
    for item in scene["structure"]:
        if item.get("builder") == "box":
            centre, size = np.asarray(item["centre"], dtype=float), np.asarray(item["size"], dtype=float)
            found[item["name"]] = trimesh.creation.box(bounds=(centre - size / 2, centre + size / 2))
    return found


def tone_of(name):
    return "ground" if name.startswith("tarp") else "base"


def made(inputs):
    sys.path.insert(0, str(inputs.repo / "tools/usd"))
    import snap
    scene = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
    meshes = boxes(scene)
    laid = {"place": PLACE, "objects": meshes, "matrices": {}, "statics": {}, "ground": snap.flat_ground(),
            "height": lambda flat: np.zeros(len(flat))}
    (low_x, low_z), (high_x, high_z) = scene["floor"]
    rectangle = (low_x + INSET, low_z + INSET, high_x - INSET, high_z - INSET)
    spots = [snap.place_free(laid, MOVED, rectangle, seed=seed) for seed in SEEDS]
    moved = meshes[MOVED]

    def placed(offset):
        lowest = float(moved.bounds[0][1] + offset[1])
        return [{"kind": "area", "points": footprint(moved, offset), "tone": "accent", "id": MOVED,
                 "label": "the bed, dropped onto the floor" if lowest < 0.01
                 else f"the bed, dropped onto what lies there, {lowest:.2f} m up"}]
    room = [plan_point(x, z) for x, z in ((low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z))]
    return {
        "example": f"a bed of the {PLACE}, placed again among its other beds and tarps",
        "view": "plan", "bounds": [low_x - 0.5, -high_z - 0.5, high_x + 0.5, -low_z + 0.5],
        "steps": [
            {"label": "The room and what already stands in it",
             "shapes": [{"kind": "area", "points": room, "tone": "ghost", "label": "the floor"},
                        *[{"kind": "area", "points": footprint(mesh), "tone": tone_of(name),
                           "label": name.replace("_", " ")} for name, mesh in meshes.items() if name != MOVED]]},
            {"label": "The bed to place, where the plan had it",
             "shapes": [{"kind": "area", "points": footprint(moved), "tone": "accent", "id": MOVED,
                         "label": "the bed where the plan had it"}]},
            {"label": "Snap tries spots in the room and keeps the first where it lands on something and hits nothing",
             "shapes": placed(spots[0])}],
        "slider": {"label": "try", "unit": "seed", "values": list(SEEDS), "at": 0,
                   "shapes": [placed(offset) for offset in spots]},
        "numbers": [{"label": "boxes in its way", "value": len(meshes) - 1, "unit": "",
                     "tip": "the scene record's boxes it must not hit"}]}
