"""rough-align@<place>: the place's rough model registered to its plan (shapes first, #41): scaled to the plan's metres
and stood where the plan stands in the place's frame, free and local, so every later step of the loop reads one model
in metres and in place.

    reads   rough-model@<place> (rough.glb in Pixal3D's own size, Y up; rough.json) and plan@<place> (place-plan v2:
            its floor, the place frame's box round the plan, its floor's height and its walls' height)
    makes   aligned.glb (rough.glb with one root node carrying the registration) and align.json {place, take,
            turn_degrees, scale, matrix (4x4, row-major: mesh frame to place frame, metres), plan, model, aligned and
            misfit (aligned over plan, each of wide, deep and high; high null where the plan names no height)}
    gates   registered  the model's nodes carry no transform of their own (its extent is measured in its mesh frame)
                        and its footprint and the plan's floor have area; the scale and misfits measured, no misfit
                        threshold: none is measured on accepted rough models yet (rough_model's overlay)

The registration: the turn about Y (0 or 90 degrees: a box alone cannot tell 180 from 0) whose footprint's proportions
fit the plan's best, then one scale for every axis (the geometric mean of the two footprint ratios, the least squares
fit in log space), then the footprint's middle onto the floor's middle and the model's lowest point onto the floor.
"""
import json
import math
import pathlib
import struct

from score import checks, contracts
from score.stages.rough_model import GLB_MAGIC, JSON_CHUNK, MODEL, RECORD, glb_json, triangles
from score.stages.surfaces.surface_gates import guarded, unknown, verdict

ALIGNED, REGISTRATION = "aligned.glb", "align.json"
TURNS = (0, 90)
NODE_TRANSFORMS = ("matrix", "translation", "rotation", "scale")
# The layers whose models no place owns (people, #41): each runs the loop on a line of its own name, which has no plan
# and is no place of the environment's.
NO_PLACE = ("people",)


def bounds(gltf):
    """([low x, y, z], [high x, y, z]) of every primitive's positions together, in the mesh frame."""
    accessors = gltf.get("accessors", [])
    found = [accessors[primitive["attributes"]["POSITION"]] for mesh in gltf.get("meshes", [])
             for primitive in mesh["primitives"]]
    return ([min(bound["min"][axis] for bound in found) for axis in range(3)],
            [max(bound["max"][axis] for bound in found) for axis in range(3)])


def plan_box(plan):
    """The plan's floor in the place's frame: (x0, z0, x1, z1), its floor's height and its walls' height (None for
    none named)."""
    (x0, z0), (x1, z1) = plan["floor"]
    high = float(plan.get("walls", {}).get("high") or 0.0)
    return (float(x0), float(z0), float(x1), float(z1)), float(plan["floor_height"]), high or None


def turned_corners(low, high, turn):
    """The mesh box's eight corners turned `turn` degrees about Y (x toward -z)."""
    cos, sin = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    return [(cos * x + sin * z, y, -sin * x + cos * z)
            for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]


def span(corners):
    """([low x, y, z], [high x, y, z]) round some points."""
    return ([min(corner[axis] for corner in corners) for axis in range(3)],
            [max(corner[axis] for corner in corners) for axis in range(3)])


def footprint(low, high, turn):
    """(wide, high, deep) of the mesh box turned `turn` degrees."""
    least, most = span(turned_corners(low, high, turn))
    return tuple(most[axis] - least[axis] for axis in range(3))


def best_turn(low, high, wide, deep):
    """The turn of TURNS whose footprint's proportions are nearest the plan's: |log(wide ratio) - log(deep ratio)|."""
    def misfit(turn):
        size = footprint(low, high, turn)
        return abs(math.log(wide / size[0]) - math.log(deep / size[2]))
    return min(TURNS, key=misfit)


def placement(low, high, turn, scale, floor_box, floor):
    """The 4x4 matrix (row-major) turning the mesh box, scaling it and standing its footprint's middle on the floor
    box's middle, its lowest point on the floor's height."""
    least, most = span(turned_corners(low, high, turn))
    x0, z0, x1, z1 = floor_box
    move = ((x0 + x1 - scale * (least[0] + most[0])) / 2, floor - scale * least[1],
            (z0 + z1 - scale * (least[2] + most[2])) / 2)
    cos, sin = scale * math.cos(math.radians(turn)), scale * math.sin(math.radians(turn))
    return [[cos, 0.0, sin, move[0]], [0.0, scale, 0.0, move[1]], [-sin, 0.0, cos, move[2]], [0.0, 0.0, 0.0, 1.0]]


def registration(low, high, plan):
    """{turn_degrees, scale, matrix, plan, model, aligned, misfit} of a mesh box onto a plan."""
    floor_box, floor, plan_high = plan_box(plan)
    wide, deep = floor_box[2] - floor_box[0], floor_box[3] - floor_box[1]
    turn = best_turn(low, high, wide, deep)
    size = footprint(low, high, turn)
    scale = math.sqrt(wide / size[0] * deep / size[2])
    aligned = {"wide": scale * size[0], "high": scale * size[1], "deep": scale * size[2]}
    return {"turn_degrees": turn, "scale": round(scale, 6),
            "matrix": [[round(value, 6) for value in row]
                       for row in placement(low, high, turn, scale, floor_box, floor)],
            "plan": {"wide": wide, "deep": deep, "high": plan_high,
                     "floor": [list(floor_box[:2]), list(floor_box[2:])], "floor_height": floor},
            "model": {"wide": size[0], "high": size[1], "deep": size[2]},
            "aligned": {name: round(value, 4) for name, value in aligned.items()},
            "misfit": {"wide": round(aligned["wide"] / wide, 4), "deep": round(aligned["deep"] / deep, 4),
                       "high": round(aligned["high"] / plan_high, 4) if plan_high else None}}


def scene_roots(gltf):
    """Each scene of a glTF with its root nodes (a glTF with no scene: one, of every node no node holds)."""
    held = {child for node in gltf.get("nodes", []) for child in node.get("children", [])}
    return gltf.get("scenes") or [{"nodes": [index for index in range(len(gltf.get("nodes", [])))
                                             if index not in held]}]


def with_root(path, matrix, out):
    """The binary glTF at `path` written to `out` with one new root node carrying `matrix` (row-major; glTF stores it
    by column) over each scene's roots; its binary chunk copied as it is."""
    data = pathlib.Path(path).read_bytes()
    gltf = glb_json(path)
    scenes, nodes = scene_roots(gltf), gltf.setdefault("nodes", [])
    for scene in scenes:
        nodes.append({"name": "rough-align", "matrix": [matrix[row][column] for column in range(4) for row in range(4)],
                      "children": scene.get("nodes", [])})
        scene["nodes"] = [len(nodes) - 1]
    gltf["scenes"] = scenes
    gltf.setdefault("scene", 0)
    text = json.dumps(gltf).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), JSON_CHUNK) + text + data[20 + struct.unpack_from("<I", data, 12)[0]:]
    out.write_bytes(GLB_MAGIC + struct.pack("<II", 2, 12 + len(body)) + body)


def unregistrable(gltf, plan):
    """Why a model cannot be registered to a plan, or [] when it can."""
    found = [f"node {node.get('name', index)} carries its own {key}: the extent is measured in the mesh frame"
             for index, node in enumerate(gltf.get("nodes", [])) for key in NODE_TRANSFORMS if key in node]
    if not triangles(gltf):
        found.append(f"{MODEL} has no triangles")
        return found
    low, high = bounds(gltf)
    if high[0] - low[0] <= 0 or high[2] - low[2] <= 0:
        found.append(f"{MODEL}'s footprint has no area")
    (x0, z0, x1, z1), _, _ = plan_box(plan)
    if x1 - x0 <= 0 or z1 - z0 <= 0:
        found.append("the plan's floor has no area")
    return found


def make(inputs, out, seed, params):
    """align.json, and aligned.glb where the rough model can be registered to the plan."""
    rough = pathlib.Path(inputs["rough-model"])
    plan = json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())
    gltf, record = glb_json(rough / MODEL), json.loads((rough / RECORD).read_text())
    found = {"place": plan["place"], "take": record["take"], "unregistrable": unregistrable(gltf, plan)}
    if not found["unregistrable"]:
        found.update(registration(*bounds(gltf), plan))
        with_root(rough / MODEL, found["matrix"], out / ALIGNED)
    (out / REGISTRATION).write_text(json.dumps(found, indent=1))


def faults(folder):
    return [] if (folder / REGISTRATION).exists() else [f"no {REGISTRATION}"]


CONTRACT = contracts.Contract("rough-align", 1, faults, {"length": "metre", "up axis": "Y"})


def judge_registered(output, inputs, evidence):
    """The rough model registered to the plan: why not, by name, else its scale and misfits measured."""
    found = json.loads((output / REGISTRATION).read_text())
    if found["unregistrable"]:
        return verdict("registered", found["unregistrable"], 1, "rough models")
    misfit = {f"misfit {name}": value for name, value in found["misfit"].items() if value is not None}
    return verdict("registered", [], 1, "rough models", {"scale": found["scale"], **misfit})


CHECKS = (guarded("registered", judge_registered),)
AFTER = {"rough-model": ("rough-model", 1), "plan": ("place-plan", 2)}
# The layers whose rows lie round the place's floor, not on it: a terrain detail area reaches out into the ground
# round the place (its scene inventory's terrain rows: a crater, a track).
ROUND = ("terrain",)


def fits(size, wide, deep):
    """Whether a row's footprint (its size's wide and deep) fits a floor of `wide` by `deep`, turned or not."""
    return (size[0] <= wide and size[1] <= deep) or (size[0] <= deep and size[1] <= wide)


def judge_rows_fit(output, inputs, evidence):
    """The parts split read against the registered rough model (props-inputs, #41): every row's footprint fits the
    floor the rough model was registered to; how many rows fit no footprint of the aligned rough model is measured.
    A row of a layer that lies round the floor (ROUND) is counted, not held to it; rows of a layer no place owns
    (NO_PLACE) are held to no plan. Unknown without a registration: the loop splits a place's parts only once its
    rough model stands in its plan."""
    split = [row for row in json.loads((output / "rows.json").read_text())["rows"] if row.get("layer") not in NO_PLACE]
    if not split:
        return checks.Verdict("fits the plan", checks.PASS, "no row on a place's plan: models no place owns")
    if "rough-align" not in inputs:
        return unknown("fits the plan", "no registered rough model: the place has no plan to register one to")
    found = json.loads((pathlib.Path(inputs["rough-align"]) / REGISTRATION).read_text())
    rows = [row for row in split if row.get("layer") not in ROUND]
    if found["unregistrable"]:
        return unknown("fits the plan", "the rough model was not registered: " + "; ".join(found["unregistrable"]))
    plan, aligned = found["plan"], found["aligned"]
    failing = [f"{row['id']}: {row['size'][0]} by {row['size'][1]} m fits no way on the {plan['wide']:.2f} by "
               f"{plan['deep']:.2f} m floor" for row in rows if not fits(row["size"], plan["wide"], plan["deep"])]
    past = sum(not fits(row["size"], aligned["wide"], aligned["deep"]) for row in rows)
    return verdict("fits the plan", failing, len(rows), "rows",
                   {"rows past the rough model": past, "rows round the floor": len(split) - len(rows)})

