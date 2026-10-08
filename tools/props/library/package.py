"""A place's scene package: what any engine loads, written from a finished route run (JoeyKardolus/2099#129). Every
object is its own glTF model as baked (objects/<name>.gltf, its .bin and its pictures), and scene.json says where
each copy of an object stands in the place's frame. No engine's format is in it: the game 2099 loads it through its
Godot adapter, Blender or a benchmark through theirs. OpenUSD as the canonical scene format is the next step.

    .venv/bin/python tools/props/library/package.py <place> <work> <out>        # write the package, then check it
    .venv/bin/python tools/props/library/package.py --check <out>               # check a package that is there

scene.json:
    format, version      "score.scene", 1
    place, frame         the place and its frame in words (from its inventory): metres, y up
    ground               how a copy's height is meant: a lift off the ground under its spot, so an engine with terrain
                         stands each copy on its own ground (a flat place frame has its ground at y = 0)
    on_seat              where the place's middle sits on its seat, (across, along)
    objects              {name: {file, kind, route, size (x, y, z as laid, metres), triangles, check}}
    instances            [{object, row, at, facing, tilt, scale, matrix}]: `facing` a bearing in degrees (0 looks
                         along -z, 90 along +x), `tilt` degrees about the copy's own across, `matrix` the whole
                         transform as 16 numbers, column by column, as glTF writes a node's matrix
    children, lamps      objects standing on another object; the place's lamps

The check refuses a package with a missing or unreadable model file, buffer or picture, a model that failed its model
check, an object no copy uses, a transform that is not a turn and an even scale, or an inventory row whose count of
copies differs from the package's.
"""
import argparse
import json
import math
import pathlib
import shutil
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
INVENTORIES = REPO / "data/inventory"
FORMAT = "score.scene"
VERSION = 1
GROUND = ("each copy's y is its lift off the ground under its own spot; on a flat place frame the ground is y = 0, "
          "an engine with terrain stands each copy on the ground there")


def turned(facing, tilt, scale):
    """A copy's 3 x 3: turned about up by -facing (a bearing), tipped about its own across by tilt, scaled evenly."""
    yaw, tip = math.radians(-facing), math.radians(tilt)
    about_up = np.array([[math.cos(yaw), 0.0, math.sin(yaw)], [0.0, 1.0, 0.0], [-math.sin(yaw), 0.0, math.cos(yaw)]])
    about_across = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(tip), -math.sin(tip)], [0.0, math.sin(tip), math.cos(tip)]])
    return about_up @ about_across * scale


def standing_at(entry, spot):
    """Where a copy's origin stands: its spot; a piece laid front up (tilted: a cable, a plate on the ground) is lifted
    by half its depth and moved back by half its tall side, which the tilt lays along the ground, so its middle lands
    on its spot."""
    at = np.array([float(spot["x"]), float(spot.get("y", 0.0)), float(spot["z"])])
    if entry.get("tilt"):
        _, tall, deep = entry["size"]
        facing = math.radians(float(spot.get("facing", 0.0)))
        along = np.array([-math.sin(facing), 0.0, math.cos(facing)])  # the copy's own +z, turned
        at = at - along * tall / 2 + np.array([0.0, deep / 2, 0.0])
    return at


def instance(planned, piece):
    """One copy as scene.json has it."""
    entry = planned["models"][piece["model"]]
    spot = piece["spot"]
    facing, tilt, scale = float(spot.get("facing", 0.0)), float(entry.get("tilt", 0.0)), float(spot.get("scale", 1.0))
    matrix = np.eye(4)
    matrix[:3, :3] = turned(facing, tilt, scale)
    matrix[:3, 3] = standing_at(entry, spot)
    return {"object": piece["model"], "row": piece["row"], "at": [round(float(value), 4) for value in matrix[:3, 3]],
            "facing": facing, "tilt": tilt, "scale": scale,
            "matrix": [round(float(value), 6) + 0.0 for value in matrix.T.reshape(-1)]}


def made_reports(work):
    """What the bake said of each model it made (triangles, bounds), by model."""
    found = {}
    for path in sorted((work / "made").glob("report*.json")):
        data = json.loads(path.read_text())
        found.update(data.get("pieces", data))
    return found


def model_files(gltf):
    """Every file a .gltf names (its buffers and pictures), relative to its folder."""
    found = json.loads(gltf.read_text())
    return [item["uri"] for item in found.get("buffers", []) + found.get("images", []) if "uri" in item]


def copy_object(source, target, name):
    """A made model and everything it names, into the package's objects folder."""
    gltf = source / f"{name}.gltf"
    shutil.copy(gltf, target / gltf.name)
    for uri in model_files(gltf):
        (target / uri).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source / uri, target / uri)


def passed_checks(work, planned):
    """The model gate's verdict for every planned model; refuses a package while any failed or is unchecked."""
    checks = json.loads((work / "checks.json").read_text())
    held = sorted(name for name in planned["models"] if not checks.get(name, {}).get("pass"))
    if held:
        raise SystemExit(f"models that failed or missed their check: {', '.join(held)}")
    return checks


def write(place, work, out):
    """The package of a finished route run in <work>, into <out>; returns scene.json's content."""
    planned = json.loads((work / "plan-route.json").read_text())
    checks = passed_checks(work, planned)
    reports = made_reports(work)
    children = {child["model"] for child in planned["children"]}
    if out.exists():
        shutil.rmtree(out)
    (out / "objects").mkdir(parents=True)
    objects = {}
    for name, entry in planned["models"].items():
        copy_object(work / "made", out / "objects", name)
        objects[name] = {"file": f"objects/{name}.gltf", "kind": entry["kind"], "route": entry["route"],
                         "size": entry["size"], "triangles": reports.get(name, {}).get("triangles"),
                         "check": checks[name]}
    scene = {"format": FORMAT, "version": VERSION, "place": place, "frame": planned.get("frame", ""),
             "units": "metre", "up": "+y", "ground": GROUND, "on_seat": planned["on_seat"], "objects": objects,
             "instances": [instance(planned, piece) for piece in planned["pieces"] if piece["model"] not in children],
             "children": [{"object": child["model"], "on": child["parent"]} for child in planned["children"]],
             "lamps": json.loads((work / "lamps.json").read_text()) if (work / "lamps.json").exists() else []}
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    return scene


def object_problems(out, name, about):
    """What is wrong with one object of a package: its files, its mesh, its check."""
    import trimesh
    gltf = out / about["file"]
    if not gltf.is_file():
        return [f"{name}: no model at {about['file']}"]
    found = [f"{name}: {uri} is missing" for uri in model_files(gltf) if not (gltf.parent / uri).is_file()]
    if found:
        return found
    mesh = trimesh.load(gltf, force="mesh", skip_materials=True)
    if len(mesh.faces) == 0:
        found.append(f"{name}: its model has no faces")
    if not about.get("check", {}).get("pass"):
        found.append(f"{name}: failed its model check")
    return found


def transform_problems(index, copy):
    """What is wrong with one copy's transform: not finite, or not a turn with an even scale."""
    matrix = np.array(copy["matrix"], dtype=float).reshape(4, 4).T
    if not np.all(np.isfinite(matrix)) or not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0]):
        return [f"copy {index} ({copy['object']}): its matrix is not a transform"]
    basis = matrix[:3, :3] / copy["scale"]
    if not np.allclose(basis.T @ basis, np.eye(3), atol=1e-5) or np.linalg.det(basis) < 0:
        return [f"copy {index} ({copy['object']}): its matrix is not a turn with an even scale"]
    return []


def count_problems(scene, inventory):
    """Every inventory row's count of copies against the package's (a child row stands in its parent's)."""
    copies = {}
    for copy in scene["instances"]:
        copies[copy["row"]] = copies.get(copy["row"], 0) + 1
    standing_on = {child["object"] for child in scene["children"]}
    return [f"row {row['id']}: the inventory has {row['count']} copies, the package {copies.get(row['id'], 0)}"
            for row in inventory["rows"] if row["id"] not in standing_on and copies.get(row["id"], 0) != row["count"]]


def problems(out, inventory=None):
    """Everything wrong with the package at <out>, against its place's inventory; [] when it is sound."""
    scene = json.loads((out / "scene.json").read_text())
    if scene.get("format") != FORMAT or scene.get("version") != VERSION:
        return [f"scene.json is not {FORMAT} version {VERSION}"]
    inventory = inventory or json.loads((INVENTORIES / f"{scene['place']}.json").read_text())
    found = []
    for name, about in scene["objects"].items():
        found += object_problems(out, name, about)
    used = {copy["object"] for copy in scene["instances"]} | {child["object"] for child in scene["children"]}
    found += [f"{name}: no copy uses it" for name in sorted(set(scene["objects"]) - used)]
    found += [f"copy {index}: no object {copy['object']}" for index, copy in enumerate(scene["instances"])
              if copy["object"] not in scene["objects"]]
    for index, copy in enumerate(scene["instances"]):
        found += transform_problems(index, copy)
    return found + count_problems(scene, inventory)


def summary(out):
    """One line: objects, copies, triangles placed, size on disk."""
    scene = json.loads((out / "scene.json").read_text())
    placed = sum(scene["objects"][copy["object"]].get("triangles") or 0 for copy in scene["instances"])
    size = sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
    return (f"{scene['place']}: {len(scene['objects'])} objects, {len(scene['instances'])} copies, "
            f"{placed:,} triangles placed, {size / 1e6:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+", type=str, help="<place> <work> <out>, or with --check <out>")
    parser.add_argument("--check", action="store_true", help="only check the package at <out>")
    options = parser.parse_args()
    if options.check:
        out = pathlib.Path(options.names[0])
    else:
        place, work, out = options.names[0], pathlib.Path(options.names[1]), pathlib.Path(options.names[2])
        write(place, work, out)
    found = problems(out)
    for line in found:
        print("PROBLEM", line)
    print(summary(out), "| check:", "sound" if not found else f"{len(found)} problems")
    if found:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
