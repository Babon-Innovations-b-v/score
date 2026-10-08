"""Runs inside Blender (on a rented machine, cloud/library_bake.py): re-material generated pieces from the library
(method B, hub rounds five and six: the pipeline gives shape only, the surfaces are the library's alone).

The job: {"out", "density", "wear", "dirt", "seed", "faces": the cut-down copy's triangles, "specs",
"chunky": [{"name", "parts": folder of <library variant>.ply (labels.py), "base": the kind's turn (nine numbers),
"size": its laid size, "screens": [{"at", "size", "variant"}], "cuts": [{"box": [x0, y0, x1, y1]} or
{"circle": [x, y, radius]}], "density": optional,
"foot": how high its foot stands over its floor (the kick wear), "decals": [{"at", "size", "variant", "turn"}]}]}.

Per piece: its labelled parts are joined into the full-detail model, turned into the kit's frame and fitted to its
laid size (so the game stretches nothing); a copy is closed into a solid (`solid_copy`: a Pixal3D model is a
paper-thin shell, under 1 mm, which the model check fails), cut down to `faces` triangles and given its openings
(`cuts`: a doorway, a porthole, a window, which a single picture's model fills in), and the library is baked from the
full model onto it, which keeps the full model's shape relief in the normal map without its photo colour, never the
picture's (round four's picture layer brought each piece its own rust and stains). Its print comes as decals, each
placed by rule on a clear flat area (clear_spot) and joined into the full model before the bake. A screen is laid as a glowing piece of its own, so the report gives the depth of the front where each
stands. Writes <out>/<name>.gltf with its own pictures in textures/, and report.json.
"""
import json
import math
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
import scene_setup  # noqa: E402
import shapes  # noqa: E402

BAKE_SAMPLES = 16
# How far the bake looks from the cut-down copy for the full model's surface, as a share of the piece's size.
REACH_SHARE = 0.03
# How far a decal plate stands in front of the solid copy's face: the bake's rays meet it before the face.
DECAL_PROUD = 0.002
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


def regioned(whole, regions):
    """The full model's faces inside each region's box given its region's library variant (details.json `regions`:
    [{"box": [x0, y0, z0, x1, y1, z1] in the kit frame at the laid size, "variant"}], later ones over earlier ones):
    what labelling by the picture's colour cannot tell apart (the lab, 2026-10-08: a chair's grey vinyl seat read as
    its cast steel frame, a glovebox's window as its painted panel)."""
    for region in regions:
        low, high = region["box"][:3], region["box"][3:]
        names = [slot.name for slot in whole.data.materials]
        if region["variant"] not in names:
            whole.data.materials.append(shapes.slot(region["variant"]))
            names.append(region["variant"])
        index = names.index(region["variant"])
        for face in whole.data.polygons:
            middle = face.center
            kit = (middle.x, middle.z, -middle.y)
            if all(low[axis] <= kit[axis] <= high[axis] for axis in range(3)):
                face.material_index = index
    whole.data.update()


def solid_copy(whole, faces, name, size, wall=WALL):
    """A closed, solid copy of the full model with about `faces` triangles: thickened, rebuilt on a voxel grid,
    cut down."""
    copy = whole.copy()
    copy.data = whole.data.copy()
    copy.name = name
    bpy.context.scene.collection.objects.link(copy)
    thick = copy.modifiers.new("thick", "SOLIDIFY")
    thick.thickness = wall
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
    triangles = sum(len(face.vertices) - 2 for face in copy.data.polygons)  # the remesh gives quads: count triangles
    change.ratio = min(1.0, faces / max(1, triangles))
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


def surface_under(tree, x, z, size):
    """How high the model's underside is at (x, z) in the kit frame: a ray from under its foot straight up; None when
    the model is not over that point. Where a lens facing down is laid (a hanging lamp's, the lab 2026-10-08: lamps
    whose lens faces the floor did not glow, a screen is only ever laid on a piece's front)."""
    start = shapes.to_blender((x, -0.05, z))
    hit = tree.ray_cast(start, shapes.to_blender((0.0, 1.0, 0.0)), size[1] + 0.1)[0]
    return None if hit is None else hit.z


def opened(item, cuts, size):
    """The piece's openings cut through it: boxes and circles in the kit frame (x across, y up), through its depth."""
    deep = max(size) * 2
    for cut in cuts:
        if "box" in cut:
            x0, y0, x1, y1 = cut["box"]
            cutter = shapes.box((x0, y0, -deep), (x1, y1, deep), "rubber", "cutter")
        else:
            x, y, radius = cut["circle"]
            cutter = shapes.cylinder((x, y, -deep), (x, y, deep), radius, "rubber", 64, "cutter")
        shapes.cut(item, cutter)


def make_piece(entry, job, out):
    """One generated piece: full model in the kit frame, cut-down copy with its openings, one atlas of its own."""
    began = time.time()
    whole = full_model(entry["parts"], entry["name"])
    into_kit_frame(whole, entry["base"], entry["size"])
    regioned(whole, entry.get("regions", []))
    low = solid_copy(whole, entry.get("faces", job["faces"]), entry["name"], entry["size"], entry.get("wall", WALL))
    opened(low, entry.get("cuts", []), entry["size"])
    # Screens are seated on the solid copy, which stands about a voxel proud of the paper-thin model: seated on the
    # model they sank into it, and the model check read the overlap as a wall under 3 mm (2026-10-06).
    tree = BVHTree.FromObject(low, bpy.context.evaluated_depsgraph_get())
    screens = [dict(screen, surface=surface_under(tree, *screen["at"], entry["size"]) if screen.get("facing") == "down"
                    else surface_at(tree, *screen["at"], entry["size"], screen["size"]))
               for screen in entry.get("screens", [])]
    screens = [screen for screen in screens if screen["surface"] is not None]
    decals = [clear_spot(tree, decal, entry["size"]) for decal in entry.get("decals", [])]
    decals_off = [decal["variant"] for decal in decals if decal["surface"] is None]
    decals = [decal for decal in decals if decal["surface"] is not None]
    with_decals(whole, decals)
    atlas = bake.Atlas(entry["name"], [low], entry.get("density", job["density"]), job["specs"], one_piece=True)
    atlas.bake_from(whole, low, job["specs"], job["wear"], job["dirt"], job["seed"],
                    max(entry["size"]) * REACH_SHARE, entry.get("foot"))
    atlas.finish()
    report = atlas.export(low, out)
    report.update(side=atlas.side, high_triangles=len(whole.data.polygons), bounds=bounds(low), screens=screens,
                  decals=[decal["variant"] for decal in decals], decals_off=decals_off,
                  cuts=len(entry.get("cuts", [])), capped_density=atlas.capped,
                  seconds=round(time.time() - began, 1))
    return report


# A decal is placed by rule (round six): on a clear flat area of the piece's front, never over a vent, a handle or a
# tool. Its footprint is probed on a 4 x 4 grid; the face under it may step in or out at most FLAT_UNDER (a generated
# surface's own noise), and when it does not, the nearest clear spot within SHIFTS of where it was asked is taken.
FLAT_UNDER = 0.003
# The spots tried, nearest first: every point of a SHIFT_STEP grid within SHIFT_REACH of where the decal was asked (the
# lab, 2026-10-08: eight ways at four distances missed flat spots a 1 cm scan of the same model found, and labels were
# dropped).
SHIFT_STEP = 0.01
SHIFT_REACH = 0.15
SHIFTS = sorted(((across * SHIFT_STEP, up * SHIFT_STEP)
                 for across in range(-round(SHIFT_REACH / SHIFT_STEP), round(SHIFT_REACH / SHIFT_STEP) + 1)
                 for up in range(-round(SHIFT_REACH / SHIFT_STEP), round(SHIFT_REACH / SHIFT_STEP) + 1)
                 if math.hypot(across, up) * SHIFT_STEP <= SHIFT_REACH + 1e-9), key=lambda shift: math.hypot(*shift))


def clear_spot(tree, decal, size):
    """The decal at the nearest clear flat spot (its `at` and `surface`), or with `surface` None when there is none:
    its footprint wholly on the piece's front, within the piece's width and height."""
    (x, y), (wide, tall) = decal["at"], decal["size"]
    for shift_x, shift_y in SHIFTS:
        if abs(x + shift_x) + wide / 2 > size[0] / 2 or not tall / 2 <= y + shift_y <= size[1] - tall / 2:
            continue
        depths = []
        for across in (-0.4, -0.13, 0.13, 0.4):
            for up in (-0.4, -0.13, 0.13, 0.4):
                start = shapes.to_blender((x + shift_x + across * wide, y + shift_y + up * tall, -size[2]))
                hit = tree.ray_cast(start, shapes.to_blender((0.0, 0.0, 1.0)), size[2] * 2)[0]
                depths.append(None if hit is None else -hit.y)
        if None not in depths and max(depths) - min(depths) <= FLAT_UNDER:
            return dict(decal, at=[x + shift_x, y + shift_y], surface=min(depths))
    return dict(decal, surface=None)


def with_decals(whole, decals):
    """The piece's print (method B, hub round five: labels, notes, number plates placed on purpose, a few a piece)
    as thin printed plates joined into the full model just in front of the solid copy's face, so the bake from the
    full model carries them onto the piece in their own library colours; the picture's own colours never do."""
    plates = []
    for decal in decals:
        (x, y), (wide, tall) = decal["at"], decal["size"]
        plate = shapes.content_plate((x - wide / 2, y - tall / 2, decal["surface"] - DECAL_PROUD),
                                     (x + wide / 2, y + tall / 2, decal["surface"] + DECAL_PROUD / 2),
                                     decal["variant"], "decal")
        if decal.get("turn"):
            centre = shapes.to_blender((x, y, 0.0))
            plate.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(decal["turn"]), 4, "Y")
                                 @ Matrix.Translation(-centre))
        plates.append(plate)
    if not plates:
        return
    if whole.data.uv_layers.get("content") is None:
        whole.data.uv_layers.new(name="content")
    bpy.ops.object.select_all(action="DESELECT")
    for plate in plates:
        plate.select_set(True)
    whole.select_set(True)
    bpy.context.view_layer.objects.active = whole
    bpy.ops.object.join()


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
