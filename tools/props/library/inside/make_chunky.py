"""Runs inside Blender (on a rented machine, cloud/library_bake.py): re-material generated pieces from the library and
give them back their small detail as clean parts.

The job: {"out", "density", "wear", "dirt", "seed", "faces": the cut-down copy's triangles, "specs",
"chunky": [{"name", "parts": folder of <library variant>.ply (labels.py), "base": the kind's turn (nine numbers),
"size": its laid size, "details": [{"part", "at", "size", "variant"}], "screens": [{"at", "size", "variant"}]}]}.

Per piece: its labelled parts are joined into the full-detail model, turned into the kit's frame and fitted to its
laid size (so the game stretches nothing); a copy is closed into a solid (`solid_copy`: a Pixal3D model is a
paper-thin shell, under 1 mm, which the model check fails) and cut down to `faces` triangles, and the library is baked
from the full model onto it, which keeps the full model's shape relief in the normal map without its photo colour. Then its
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
# The solid copy: every surface thickened inward by WALL, then the whole rebuilt as one closed surface on a voxel grid
# of VOXEL_SHARE of the piece's largest side (no finer than VOXEL_FINEST), so no wall is thinner than the model check's
# 3 mm and no hole is left open.
WALL = 0.005
VOXEL_SHARE = 1 / 300
VOXEL_FINEST = 0.0012
# How far the solid copy's box may grow past the full model's on any side: a share of the piece's largest side, plus
# the wall. Thickening a noisy shell with even offset threw spikes tens of metres long (2026-10-06, a 0.6 m roof apex
# came back 64 m tall and took 14 minutes), so the step thickens by the plain normal and checks its own box.
DRIFT_SHARE = 0.03
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


def solid_copy(whole, faces, name, size):
    """A closed, solid copy of the full model with about `faces` triangles: thickened, rebuilt on a voxel grid,
    cut down."""
    copy = whole.copy()
    copy.data = whole.data.copy()
    copy.name = name
    bpy.context.scene.collection.objects.link(copy)
    thick = copy.modifiers.new("thick", "SOLIDIFY")
    thick.thickness = WALL
    thick.offset = -1.0
    thick.use_even_offset = False
    shapes.apply_modifiers(copy)
    held_to_box(copy, whole, size)
    closed = copy.modifiers.new("closed", "REMESH")
    closed.mode = "VOXEL"
    closed.voxel_size = max(VOXEL_FINEST, max(size) * VOXEL_SHARE)
    closed.use_smooth_shade = False
    shapes.apply_modifiers(copy)
    held_to_box(copy, whole, size)
    change = copy.modifiers.new("cut", "DECIMATE")
    change.ratio = min(1.0, faces / max(1, len(copy.data.polygons)))
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


def detail_parts(item, details, size, name):
    """The piece's detail as one object of code-built parts, each seated on the piece's front where it stands."""
    tree = BVHTree.FromObject(item, bpy.context.evaluated_depsgraph_get())
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
    low = solid_copy(whole, job["faces"], entry["name"], entry["size"])
    # Details and screens are seated on the solid copy, which stands about a voxel proud of the paper-thin model: seated
    # on the model they sank into it, and the model check read the overlap as a wall under 3 mm (2026-10-06).
    detail = detail_parts(low, entry.get("details", []), entry["size"], entry["name"])
    tree = BVHTree.FromObject(low, bpy.context.evaluated_depsgraph_get())
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
    report.update(side=atlas.side, high_triangles=len(whole.data.polygons), bounds=bounds(low), details=len(entry.get("details", [])),
                  detail_slots=detail_slots, screens=screens, seconds=round(time.time() - began, 1))
    return report


def held_to_box(copy, whole, size):
    """Stop the job when the thickened copy reaches past the full model's box by more than DRIFT_SHARE."""
    allowed = DRIFT_SHARE * max(size) + WALL
    grown = max(abs(after - before) for corner_after, corner_before in zip(bounds(copy), bounds(whole))
                for after, before in zip(corner_after, corner_before))
    if grown > allowed:
        raise SystemExit(f"{copy.name}: the solid copy grew {grown:.3f} m past the model (allowed {allowed:.3f} m)")


def bounds(item):
    """The piece's box in the kit frame (Blender x, -z, y back), as its low and high corners."""
    points = [(vertex.co.x, vertex.co.z, -vertex.co.y) for vertex in item.data.vertices]
    return [[round(min(point[axis] for point in points), 5) for axis in range(3)],
            [round(max(point[axis] for point in points), 5) for axis in range(3)]]


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for entry in job["chunky"]:
        scene_setup.empty_scene(256, BAKE_SAMPLES)
        report[entry["name"]] = make_piece(entry, job, out)
        print("PIECE", entry["name"], json.dumps(report[entry["name"]]), flush=True)
    (out / job.get("report", "report.json")).write_text(json.dumps(report, indent=1))


main()
