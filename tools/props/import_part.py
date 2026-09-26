"""Bring a made mesh into the game as the model a robot part, or the frame, is drawn from.

    bash tools/props/run.sh --import-part seed_drill --mesh part-seed_drill-2 --turn 90

A robot part is not a prop: a prop never goes on a robot (CONTEXT.md), so a part's model is written
to its own record, `data/definitions/robot_model.json`, keyed by the part id the simulation already
uses (the frame by its frame id), and never into `prop.json` (the owner's call, 2026-09-26, #55).
The bench draws a robot from that record.

What this does, and nothing else:

  turn     the mesh arrives facing wherever the picture had it face. You say how many degrees about
           the vertical to turn it so its front is -z, the way the robot faces.
  fit      it is fitted into the part's room on the robot, from `part_briefs.py`, so it stands where
           the part's old blocks stood. A wheel is first laid with its axle along x.
  look     its colour is averaged into a few flat tones, the same as a prop, and it is written
           matte, with its crease normals, so the engine lights it like the rest of the game.
  budget   it has to fit the furniture ceiling, and a mesh over it is refused here.

It writes the source line with it: how it was made, what made it, its licence. Whether an AI-made
asset can be licensed at all is still open (#4 question 9), so a generated part says so.
"""
import argparse
import collections
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_prop import BUDGETS, GENERATED_FROM, GENERATED_LICENCE, number  # noqa: E402
from part_briefs import BRIEFS  # noqa: E402
from paths import MESHES, REPO  # noqa: E402

import numpy as np  # noqa: E402
import trimesh  # noqa: E402

MODELS = REPO / "game" / "robots" / "models"
RECORD_FILE = REPO / "data" / "definitions" / "robot_model.json"
BUDGET = "furniture"


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("part", choices=tuple(BRIEFS) + ("all",),
                        help="the part id, or the frame id, as the simulation names it; all for every one")
    parser.add_argument("--mesh",
                        help="the made mesh: a name in the prop chain's meshes, or a path to a glTF file; "
                             "the brief's chosen take when left out")
    parser.add_argument("--turn", type=float,
                        help="degrees about the vertical that bring the part's front round to -z; the "
                             "brief's when left out")
    return parser.parse_args()


def find_the_mesh(given):
    """The glTF file: a path, or the name of a mesh the prop chain made."""
    path = pathlib.Path(given).expanduser()
    if not path.suffix:
        path = MESHES / f"{given}.glb"
    if not path.exists():
        raise SystemExit(f"no mesh at {path}")
    return path


def turned(mesh, degrees):
    """The mesh turned about the vertical, so its front faces -z."""
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), [0, 1, 0]))
    return mesh


def laid_as_a_wheel(mesh):
    """A wheel turned so its axle runs along x. Its thinnest side is its axle, whatever way the
    picture stood it."""
    thinnest = int(np.argmin(mesh.extents))
    if thinnest == 1:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 0, 1]))
    elif thinnest == 2:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    return mesh


def fitted(mesh, room, fill):
    """The mesh fitted into its room: stretched to it for `exact`, scaled evenly until it touches
    it for `within`, then stood on the room's floor at its middle."""
    low, high = np.array(room["low"], dtype=float), np.array(room["high"], dtype=float)
    size = high - low
    if np.any(mesh.extents <= 0.0):
        raise SystemExit("the mesh is flat in one direction, so it cannot fill a room")
    if fill == "exact":
        mesh.apply_scale(size / mesh.extents)
    else:
        mesh.apply_scale(float(np.min(size / mesh.extents)))
    bottom, top = mesh.bounds
    middle = (low + high) / 2.0
    mesh.apply_translation([middle[0] - (bottom[0] + top[0]) / 2.0,
                            low[1] - bottom[1],
                            middle[2] - (bottom[2] + top[2]) / 2.0])
    return mesh


def in_linear_light(mesh):
    """The colours as glTF means them. A glTF file's vertex colour is linear, and the prop chain's
    is as it looks on screen; left as it is, the engine reads every panel far too pale and a
    white robot comes out a white glare."""
    colours = np.asarray(mesh.visual.vertex_colors, dtype=np.float64) / 255.0
    shown = colours[:, :3]
    linear = np.where(shown <= 0.04045, shown / 12.92, ((shown + 0.055) / 1.055) ** 2.4)
    colours[:, :3] = linear
    mesh.visual.vertex_colors = np.clip(np.round(colours * 255.0), 0, 255).astype(np.uint8)
    return mesh


def matte_glb(mesh):
    """The model as a glTF file with its normals and one matte material: no shine and no metal,
    the way every surface in the game is drawn. Without a material of its own a glTF surface is
    taken as fully metallic by the standard, and without normals its creases are guessed at."""
    import struct

    data = trimesh.exchange.gltf.export_glb(mesh, include_normals=True)
    length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + length])
    document["materials"] = [{"name": "matte", "pbrMetallicRoughness": {
        "baseColorFactor": [1.0, 1.0, 1.0, 1.0], "metallicFactor": 0.0, "roughnessFactor": 1.0}}]
    for each in document["meshes"]:
        for primitive in each["primitives"]:
            primitive["material"] = 0
    text = json.dumps(document, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    rest = data[20 + length:]
    body = struct.pack("<II", len(text), 0x4E4F534A) + text + rest
    return data[:8] + struct.pack("<I", 12 + len(body)) + body


def within_the_budget(mesh, part):
    """Stops here when the mesh is over the furniture ceiling."""
    triangles = len(mesh.faces)
    if triangles > BUDGETS[BUDGET]:
        raise SystemExit(f"{part} is {triangles} triangles and the {BUDGET} ceiling is "
                         f"{BUDGETS[BUDGET]}. Make it again at a lower face count.")
    return triangles


def source_line(mesh_name):
    """Where this model came from, in the three fields the gate asks for, plus the mesh it was
    made as and the day it came in."""
    return collections.OrderedDict([
        ("made", "generated"),
        ("from", GENERATED_FROM),
        ("licence", GENERATED_LICENCE),
        ("mesh", mesh_name),
        ("imported", datetime.date.today().isoformat()),
    ])


def write_the_record(part, model_file, source):
    """Puts this part's model in its record, the parts kept in the order the briefs give them."""
    records = collections.OrderedDict()
    if RECORD_FILE.exists():
        records = json.loads(RECORD_FILE.read_text(), object_pairs_hook=collections.OrderedDict)
    records[part] = collections.OrderedDict([("model", f"res://{model_file}"), ("budget", BUDGET),
                                             ("source", source)])
    ordered = collections.OrderedDict((each, records[each]) for each in BRIEFS if each in records)
    RECORD_FILE.write_text(json.dumps(ordered, indent="\t") + "\n")


def made_model(part, mesh_path, turn):
    """The mesh turned, laid, fitted and given the look, ready to write."""
    from finish import flatten_to_the_look

    brief = BRIEFS[part]
    # process=False keeps the vertices the prop chain split along its creases, so an edge stays
    # an edge; welding them would shade every panel into the next.
    mesh = turned(trimesh.load(mesh_path, force="mesh", process=False), turn)
    if brief.get("wheel"):
        mesh = laid_as_a_wheel(mesh)
    return in_linear_light(flatten_to_the_look(fitted(mesh, brief["room"], brief["fill"])))


def import_one(part, mesh_name, turn):
    """Fits one mesh as one part's model, writes it and its record, and says what it made."""
    mesh_path = find_the_mesh(mesh_name)
    mesh = made_model(part, mesh_path, turn)
    triangles = within_the_budget(mesh, part)

    folder = MODELS / part
    folder.mkdir(parents=True, exist_ok=True)
    model_path = folder / f"{part}.glb"
    model_path.write_bytes(matte_glb(mesh))
    write_the_record(part, model_path.relative_to(REPO).as_posix(), source_line(mesh_path.stem))

    size = " x ".join(number(value) for value in mesh.extents)
    print(f"{part}: {triangles} triangles, {size} m, from {mesh_path.name}")


def main():
    arguments = parse_arguments()
    parts = tuple(BRIEFS) if arguments.part == "all" else (arguments.part,)
    for part in parts:
        brief = BRIEFS[part]
        mesh_name = arguments.mesh or brief.get("mesh")
        if not mesh_name:
            raise SystemExit(f"{part}: no take chosen in its brief, so name one with --mesh")
        turn = arguments.turn if arguments.turn is not None else brief.get("turn", 0.0)
        import_one(part, mesh_name, turn)
    print(f"records in {RECORD_FILE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
