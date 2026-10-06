"""Runs inside Blender (on a rented machine, cloud/library_bake.py): re-material generated pieces from the library and
give them back their small detail as clean parts.

The job: {"out", "density", "wear", "dirt", "seed", "faces": the cut-down copy's triangles, "specs",
"chunky": [{"name", "parts": folder of <library variant>.ply (labels.py), "base": the kind's turn (nine numbers),
"size": its laid size, "details": [{"part", "at", "size", "variant"}], "screens": [{"at", "size", "variant"}]}]}.

Per piece: its labelled parts are joined into the full-detail model, turned into the kit's frame and fitted to its
laid size (so the game stretches nothing); a copy is cut down to `faces` triangles and the library is baked from the
full model onto it, which keeps the full model's shape relief in the normal map without its photo colour. Then its
detail goes on as code-built parts read off the model's own front (a ray finds the surface under each): labels,
screws, keypads (pieces.DETAIL_PARTS), baked from their own library variants into the same pictures. A screen is
laid as a glowing piece of its own, so the report gives the depth of the front where each stands. Writes
<out>/<name>.gltf with its own pictures in textures/, and report.json.
"""
import json
import pathlib
import sys
import time

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import pieces  # noqa: E402
import scene_setup  # noqa: E402
import shapes  # noqa: E402

BAKE_SAMPLES = 16
# How far the bake looks from the cut-down copy for the full model's surface, as a share of the piece's size.
REACH_SHARE = 0.03
# glTF (y up, -z forward), which labels.py wrote in, onto Blender's frame (z up).
GLTF_TO_BLENDER = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def full_model(parts_folder, name):
    """The full-detail model: every material's part imported and joined, its slot named for the material, welded
    and wound outward."""
    found = []
    for path in sorted(pathlib.Path(parts_folder).glob("*.ply")):
        bpy.ops.wm.ply_import(filepath=str(path))
        part = bpy.context.selected_objects[0]
        part.data.materials.clear()
        part.data.materials.append(shapes.slot(path.stem))
        found.append(part)
    whole = shapes.joined(found, f"{name}_full")
    # The parts come as loose triangles; welded, the cut-down copy unwraps into whole islands, and wound outward,
    # no bake ray is sent away from the model (round one's dotted and black bakes, 2026-10-06).
    welded = bmesh.new()
    welded.from_mesh(whole.data)
    bmesh.ops.remove_doubles(welded, verts=welded.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(welded, faces=welded.faces)
    welded.to_mesh(whole.data)
    welded.free()
    return whole


def into_kit_frame(whole, base, size):
    """The model turned by its kind's `base` (glTF frame to the kit's) and fitted to its laid size, standing on the
    middle of its foot, in Blender's frame (the kit frame's x, -z, y)."""
    turn = Matrix([base[0:3], base[3:6], base[6:9]]).to_4x4()
    whole.data.transform(GLTF_TO_BLENDER @ turn)  # the .ply holds glTF numbers as they are
    corners = [vertex.co for vertex in whole.data.vertices]
    low = Vector([min(point[axis] for point in corners) for axis in range(3)])
    high = Vector([max(point[axis] for point in corners) for axis in range(3)])
    wide, tall, deep = size
    scale = Vector((wide / (high.x - low.x), deep / (high.y - low.y), tall / (high.z - low.z)))
    middle = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    whole.data.transform(Matrix.Diagonal(scale.to_4d()) @ Matrix.Translation(-middle))
    whole.data.update()


def cut_down(whole, faces, name):
    """A copy of the full model with about `faces` triangles."""
    copy = whole.copy()
    copy.data = whole.data.copy()
    copy.name = name
    bpy.context.scene.collection.objects.link(copy)
    change = copy.modifiers.new("cut", "DECIMATE")
    change.ratio = min(1.0, faces / max(1, len(whole.data.polygons)))
    shapes.apply_modifiers(copy)
    return copy


def surface_at(tree, x, y, size, footprint=(0.0, 0.0)):
    """How far forward (kit z) the model's front comes anywhere under a part's footprint centred at (x, y): rays
    from in front, straight back, over a 3 x 3 grid; the frontmost hit, so no bulge of the model covers the part
    (a label's first character sank behind the control box's rounded edge, 2026-10-06). None when the model is not
    under the part's middle at all (screws floated beside the conduit box)."""
    middle = tree.ray_cast(shapes.to_blender((x, y, -size[2])), shapes.to_blender((0.0, 0.0, 1.0)), size[2] * 2)[0]
    if middle is None:
        return None  # nothing of the model under the part's middle: the part would float (2026-10-06)
    found = []
    for across in (-0.5, 0.0, 0.5):
        for up in (-0.5, 0.0, 0.5):
            start = shapes.to_blender((x + across * footprint[0], y + up * footprint[1], -size[2]))
            hit = tree.ray_cast(start, shapes.to_blender((0.0, 0.0, 1.0)), size[2] * 2)[0]
            if hit is not None:
                found.append(-hit.y)
    return min(found)


def detail_parts(whole, details, size, name):
    """The piece's detail as one object of code-built parts, each seated on the model's front where it stands."""
    tree = BVHTree.FromObject(whole, bpy.context.evaluated_depsgraph_get())
    found = []
    for detail in details:
        x, y = detail["at"]
        surface = surface_at(tree, x, y, size, detail.get("size", (0.0, 0.0)))
        if surface is None:
            continue
        builder = pieces.DETAIL_PARTS[detail["part"]]
        if detail["part"] == "screw":
            made = builder(x, y, surface)
        elif detail["part"] == "keypad":
            made = builder(x, y, *detail["size"], surface)
        else:
            made = builder(x, y, *detail["size"], surface, detail["variant"])
        found += made if isinstance(made, list) else [made]
    return shapes.joined(found, f"{name}_detail") if found else None


def make_piece(entry, job, out):
    """One generated piece: full model in the kit frame, cut-down copy, details, one atlas of its own."""
    began = time.time()
    whole = full_model(entry["parts"], entry["name"])
    into_kit_frame(whole, entry["base"], entry["size"])
    low = cut_down(whole, job["faces"], entry["name"])
    detail = detail_parts(whole, entry.get("details", []), entry["size"], entry["name"])
    tree = BVHTree.FromObject(whole, bpy.context.evaluated_depsgraph_get())
    screens = [dict(screen, surface=surface_at(tree, *screen["at"], entry["size"], screen["size"]))
               for screen in entry.get("screens", [])]
    screens = [screen for screen in screens if screen["surface"] is not None]
    items = [low] + ([detail] if detail else [])
    detail_slots = bake.slot_names(detail) if detail else []
    atlas = bake.Atlas(entry["name"], items, job["density"])
    atlas.bake_from(whole, low, job["specs"], job["wear"], job["dirt"], job["seed"],
                    max(entry["size"]) * REACH_SHARE)
    if detail:
        atlas.bake_self(detail, job["specs"], job["wear"], job["dirt"], job["seed"])
        bpy.ops.object.select_all(action="DESELECT")
        low.select_set(True)
        detail.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.join()
    atlas.finish()
    report = atlas.export(low, out)
    report.update(side=atlas.side, high_triangles=len(whole.data.polygons), details=len(entry.get("details", [])),
                  detail_slots=detail_slots, screens=screens, seconds=round(time.time() - began, 1))
    return report


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for entry in job["chunky"]:
        scene_setup.empty_scene(256, BAKE_SAMPLES)
        report[entry["name"]] = make_piece(entry, job, out)
        print("PIECE", entry["name"], json.dumps(report[entry["name"]]), flush=True)
    (out / "report.json").write_text(json.dumps(report, indent=1))


main()
