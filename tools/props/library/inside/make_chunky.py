"""Runs inside Blender (on a rented machine, cloud/library_bake.py): re-material generated pieces from the library
(method B, hub rounds five and six: the pipeline gives shape only, the surfaces are the library's alone).

The job: {"out", "density", "wear", "dirt", "seed", "faces": the cut-down copy's triangles, "specs",
"chunky": [{"name", "parts": folder of <library variant>.ply (labels.py), "base": the kind's turn (nine numbers),
"size": its laid size, "screens": [{"at", "size", "variant"}], "cuts": [{"box": [x0, y0, x1, y1]} or
{"circle": [x, y, radius]}], "density": optional,
"foot": how high its foot stands over its floor (the kick wear), "decals": [{"at", "size", "variant", "turn"}],
"per_face": optional, every face packed as its own island (bake.packed_per_face: foliage),
"stands": whether its paint levelled its feet (library_bake.py reads it from the labels; then levelled_feet),
A take bodies.BODIES names is a big object seen up close: its code-built body under the take's details it keeps
(make_bodied), laid with its body's turn where that is given}]}.

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
import bodies  # noqa: E402
import pieces  # noqa: E402
import scene_setup  # noqa: E402
import shapes  # noqa: E402

BAKE_SAMPLES = 16
# How far the bake looks from the cut-down copy for the full model's surface, in the copy's voxels (bake_reach). The
# copy lies within a wall and a voxel or two of the full model: measured from its points (the materials fix,
# 2026-10-18) the farthest lay 2.4 to 2.7 voxels off on the cargo rack, the main console, the galley counter and the
# wreck's two sections. At 3% of the piece's size (9 voxels) the cage stood so far out that its rays met whatever
# lay in front first: the cargo rack's orange slats baked black from the shelf over them, and borders came out ragged.
REACH_VOXELS = 4
# The cage reaches at least twice the inward thickening (WALL): on a small piece 3% of its side fell short of the
# thickened copy's inner faces, and the bowl stack (15 cm) baked 36% of its area black, its bowls' insides
# (job repaint, 2026-10-08).
REACH_LEAST = 0.01
# How far a decal plate stands in front of the solid copy's face: the bake's rays meet it before the face.
DECAL_PROUD = 0.002
# The solid copy: every surface thickened inward by WALL, then the whole rebuilt as one closed surface on a voxel grid
# of VOXEL_SHARE of the piece's largest side (no finer than VOXEL_FINEST), so no wall is thinner than the model check's
# 3 mm and no hole is left open.
WALL = 0.005
VOXEL_SHARE = 1 / 300
# A piece whose job names no wall of its own is thickened by WALL_VOXELS of its voxels where that is more than WALL, as
# place_route.py's jobs do for all but its THIN_WALLED masts (its WALL_SHARE): a shell thinner than a voxel falls
# between the grid's samples and comes back as lace. route.py's room jobs name their wall (route.ROOM_WALL, 5 mm as
# accepted in hub round six), so this default reaches only jobs written without one. The 60 m launch rocket, baked from a job that named no wall, came back at 5 mm under 0.2 m voxels full
# of holes, its lumpy feet, seen plain grey with no maps at all; at two voxels its shape came back whole (2026-10-10).
WALL_VOXELS = 2
# The solid copy is shaded smooth but for folds of SHARP_FOLD or more (the materials fix, 2026-10-18). Shaded flat, every
# cut-down facet sent the bake's rays out one way, so a finish's border broke along the facets (the cargo rack's orange
# slats came out in polygons of black shelf), and the game drew the remeshed facets as lumps; smooth all over, the
# copy's real edges went soft.
SHARP_FOLD = math.radians(60.0)
VOXEL_FINEST = 0.0012
# How far the solid copy's box may grow past the full model's on any side: a share of the piece's largest side, plus
# the wall. Thickening a noisy shell with even offset threw spikes tens of metres long (2026-10-06, a 0.6 m roof apex
# came back 64 m tall and took 14 minutes), so the step thickens by the plain normal and checks its own box.
DRIFT_SHARE = 0.03
# A standing piece's cut-down copy is brought down level where the remesh and the cut moved its feet apart: each
# footprint quadrant of its lowest LEVEL_BAND of height whose lowest point ends over LEVEL_GAP over the lowest comes
# down its whole gap there, spread and faded as the paint's place_line.flattened_base does (the check's quadrants
# and 3 cm: bake_check.STANCE_BAND, STANCE_GAP). The paint levels the full model, but the remesh's voxels (a 31 m ship
# at 10 cm) and the cut move its feet: the hangar's ship, level in its paint, baked one front foot 22.2 cm up and
# the other 5.8 (2026-10-15); a quadrant over LEVEL_MOST of the piece's size up is the model's fault, left as it is.
LEVEL_BAND, LEVEL_GAP, LEVEL_MOST = 0.25, 0.03, 0.15
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
        laid_flat(part)
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


def laid_flat(part):
    """The part's `content` UV map (a screen's or a print's picture reads it, recipes.picture_on): its points laid on
    the plane of its two longest sides, filling 0 to 1, the glTF up axis (y) as the picture's up when it is one of
    them, turned so the picture reads from the side its faces look to. A new UV map lays every face on the whole
    picture: navigation's wall screen baked its readout once a triangle, as amber speckle (2026-10-15)."""
    points = [vertex.co for vertex in part.data.vertices]
    low = [min(point[axis] for point in points) for axis in range(3)]
    span = [max(point[axis] for point in points) - low[axis] for axis in range(3)]
    across, up = sorted(sorted(range(3), key=lambda axis: -span[axis])[:2], key=lambda axis: axis == 1)
    facing = 3 - across - up
    mirrored = sum(face.normal[facing] * face.area for face in part.data.polygons) < 0
    layer = part.data.uv_layers.new(name="content")
    for loop in part.data.loops:
        point = points[loop.vertex_index]
        u = (point[across] - low[across]) / max(span[across], 1e-9)
        layer.data[loop.index].uv = (1 - u if mirrored else u, (point[up] - low[up]) / max(span[up], 1e-9))


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


def solid_copy(whole, faces, name, size, wall=WALL, voxel=None):
    """A closed, solid copy of the full model with about `faces` triangles: thickened, rebuilt on a voxel grid (of
    `voxel` metres, else VOXEL_SHARE of its largest side), cut down."""
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
    closed.voxel_size = voxel or voxel_of(size)
    closed.use_smooth_shade = False  # shaded after the cut (sharp_folds)
    shapes.apply_modifiers(copy)
    held_to_box(copy, whole, size)
    change = copy.modifiers.new("cut", "DECIMATE")
    triangles = sum(len(face.vertices) - 2 for face in copy.data.polygons)  # the remesh gives quads: count triangles
    change.ratio = min(1.0, faces / max(1, triangles))
    shapes.apply_modifiers(copy)
    sharp_folds(copy.data)
    return copy


def sharp_folds(mesh):
    """Every edge between two faces that fold by SHARP_FOLD or more marked sharp (the `sharp_edge` attribute, which
    Blender 4.2 and 5 both read), the faces shaded smooth."""
    import numpy as np
    count = len(mesh.polygons)
    normals = np.empty(count * 3)
    mesh.polygons.foreach_get("normal", normals)
    normals = normals.reshape(count, 3)
    first, second = bake.face_pairs(mesh)
    shared = bake.shared_edges(mesh)
    sharp = np.ones(len(mesh.edges), dtype=bool)  # an open edge or one of three faces stays sharp
    sharp[shared] = np.einsum("ij,ij->i", normals[first], normals[second]) < math.cos(SHARP_FOLD)
    layer = mesh.attributes.get("sharp_edge") or mesh.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    layer.data.foreach_set("value", sharp)
    mesh.polygons.foreach_set("use_smooth", np.ones(count, dtype=bool))
    mesh.update()


def voxel_of(size):
    """The solid copy's voxel: VOXEL_SHARE of the piece's largest side, no finer than VOXEL_FINEST."""
    return max(VOXEL_FINEST, max(size) * VOXEL_SHARE)


def default_wall(size):
    """The wall a piece takes when its job names none: WALL, or WALL_VOXELS of its voxels where those are thicker."""
    return max(WALL, WALL_VOXELS * voxel_of(size))


def bake_reach(size):
    """How far the bake's cage stands out from the cut-down copy: REACH_VOXELS of its voxels, at least REACH_LEAST."""
    return max(REACH_LEAST, REACH_VOXELS * voxel_of(size))


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
    take = take_of(entry["parts"])
    into_kit_frame(whole, bodies.laid_turn(take, entry["base"]), entry["size"])
    regioned(whole, entry.get("regions", []))
    if bodies.body_of(take):
        return make_bodied(entry, job, out, whole, bodies.body_of(take), began)
    low = solid_copy(whole, entry.get("faces", job["faces"]), entry["name"], entry["size"],
                     entry.get("wall", default_wall(entry["size"])))
    opened(low, entry.get("cuts", []), entry["size"])
    levelled = levelled_feet(low, entry["size"]) if entry.get("stands") else None
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
    atlas = bake.Atlas(entry["name"], [low], entry.get("density", job["density"]), job["specs"], one_piece=True,
                        backs_hidden=False, per_face=entry.get("per_face", False))
    atlas.bake_from(whole, low, job["specs"], job["wear"], job["dirt"], job["seed"],
                    bake_reach(entry["size"]), entry.get("foot"))
    atlas.finish()
    report = atlas.export(low, out)
    report.update(side=atlas.side, high_triangles=len(whole.data.polygons), bounds=bounds(low), screens=screens,
                  decals=[decal["variant"] for decal in decals], decals_off=decals_off,
                  cuts=len(entry.get("cuts", [])), capped_density=atlas.capped, levelled=levelled,
                  seconds=round(time.time() - began, 1))
    return report


# A body's kept details are closed on a grid this fine (bodies.py: buttons and lamps a few millimetres proud of their
# bay): at a 300th of a 3.6 m console (12 mm) a button row came back as one slab.
DETAIL_VOXEL = 0.003


def details_over(whole, body, size):
    """The full model cut to the details its body keeps (bodies.kept: its kept surfaces, and whatever stands in the
    body's detail boxes); every other face deleted. How many faces stay."""
    import numpy as np
    names = [slot.name.split(".")[0] for slot in whole.data.materials]
    middles = [(face.center.x, face.center.z, -face.center.y) for face in whole.data.polygons]
    surfaces = [names[face.material_index] for face in whole.data.polygons]
    keep = bodies.kept(body["builder"], size, middles, surfaces, body.get("keep", []))
    mesh = bmesh.new()
    mesh.from_mesh(whole.data)
    mesh.faces.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[mesh.faces[int(index)] for index in np.flatnonzero(~keep)], context="FACES")
    mesh.to_mesh(whole.data)
    mesh.free()
    whole.data.update()
    return int(keep.sum())


# The laid parts' triangles are split until no side is longer than this: whatever names a baked triangle by its
# nearest laid point (the scene's export) finds a point of its own surface under it, never a corner of a neighbour
# a metre off across a body's big flat face.
LAID_SIDE = 0.05


def split_triangles(corners, longest):
    """Triangles (n x 3 x 3) split in four at their sides' middles until none has a side over `longest`."""
    import numpy as np
    done = []
    while len(corners):
        sides = np.linalg.norm(corners - np.roll(corners, 1, axis=1), axis=2).max(axis=1)
        done.append(corners[sides <= longest])
        big = corners[sides > longest]
        first, second, third = big[:, 0], big[:, 1], big[:, 2]
        near, far, back = (first + second) / 2, (second + third) / 2, (third + first) / 2
        corners = np.concatenate([np.stack(triangle, axis=1) for triangle in
                                  ((first, near, back), (near, second, far), (back, far, third), (near, far, back))])
    return np.concatenate(done) if done else np.zeros((0, 3, 3))


def write_ply(path, corners):
    """Triangles (n x 3 x 3) as a binary .ply, each its own three corners."""
    import numpy as np
    points = np.asarray(corners, dtype="<f4").reshape(-1, 3)
    faces = np.zeros(len(corners), dtype=[("count", "u1"), ("corners", "<i4", 3)])
    faces["count"] = 3
    faces["corners"] = np.arange(len(points), dtype="<i4").reshape(-1, 3)
    header = (f"ply\nformat binary_little_endian 1.0\nelement vertex {len(points)}\nproperty float x\n"
              f"property float y\nproperty float z\nelement face {len(corners)}\n"
              "property list uchar int vertex_indices\nend_header\n")
    path.write_bytes(header.encode() + points.tobytes() + faces.tobytes())


def write_laid_parts(items, folder):
    """The model's faces as the bake made it, one .ply per library surface in the kit frame (`<name>.parts/` beside
    it: the body's and the take's details it kept), split to LAID_SIDE: the bake check and the scene's export name
    each baked triangle by them, as they name a generated piece's by its labelled parts."""
    import numpy as np
    folder.mkdir(parents=True, exist_ok=True)
    found = {}
    for item in items:
        points = np.empty(len(item.data.vertices) * 3)
        item.data.vertices.foreach_get("co", points)
        points = points.reshape(-1, 3)[:, [0, 2, 1]] * [1.0, 1.0, -1.0]  # Blender (x, y, z) -> kit (x, z, -y)
        names = [slot.name.split(".")[0] for slot in item.data.materials]
        for face in item.data.polygons:
            corners = list(face.vertices)
            found.setdefault(names[face.material_index], []).extend(
                points[[corners[0], corners[step], corners[step + 1]]] for step in range(1, len(corners) - 1))
    for name, triangles in found.items():
        write_ply(folder / f"{name}.ply", split_triangles(np.asarray(triangles), LAID_SIDE))


def joined_model(items, name):
    """The baked pieces as the one model the place lays, under the piece's name."""
    model = shapes.joined(items, name)
    model.data.name = name
    return model


def take_of(parts):
    """The take a labelled folder holds, as its labels.json names it (up on the machine the folder is named for the
    model), else the folder's own name."""
    labels = pathlib.Path(parts) / "labels.json"
    return json.loads(labels.read_text()).get("take", labels.parent.name) if labels.exists() else labels.parent.name


def make_bodied(entry, job, out, whole, body_entry, began):
    """A big object seen up close (bodies.py, the owner's rule of 2026-10-18): its code-built body at its laid size,
    baked from its own surfaces, and the take's details the body keeps, cut down and baked from the full model as a
    generated piece is; one model, one atlas."""
    size = entry["size"]
    kept = details_over(whole, body_entry, size)
    body = pieces.build(body_entry["builder"], size, body_entry.get("laid", {}), f"{entry['name']}_body")
    unknown = sorted(set(bake.slot_names(body)) - set(job["specs"]))
    if unknown:
        raise SystemExit(f"{entry['name']}: its body's surfaces {unknown} are not in the bake's specs")
    seen = json.loads(body.get("parts_seen", "{}"))
    write_laid_parts([body, whole], out / f"{entry['name']}.parts")
    body_triangles = sum(len(face.vertices) - 2 for face in body.data.polygons)
    items, low = [body], None
    if kept:
        faces = max(1000, entry.get("faces", job["faces"]) - body_triangles)
        low = solid_copy(whole, faces, f"{entry['name']}_details", size, entry.get("wall", default_wall(size)),
                         DETAIL_VOXEL)
        items.insert(0, low)
    atlas = bake.Atlas(entry["name"], items, entry.get("density", job["density"]), job["specs"], one_piece=True,
                       backs_hidden=False)
    if low is not None:
        atlas.bake_from(whole, low, job["specs"], job["wear"], job["dirt"], job["seed"],
                        max(REACH_LEAST, REACH_VOXELS * DETAIL_VOXEL), entry.get("foot"))
    atlas.bake_self(body, job["specs"], job["wear"], job["dirt"], job["seed"], entry.get("foot"))
    atlas.finish()
    model = joined_model(items, entry["name"])
    report = atlas.export(model, out)
    report.update(side=atlas.side, high_triangles=len(whole.data.polygons), bounds=bounds(model), screens=[],
                  decals=[], decals_off=[], cuts=0, capped_density=atlas.capped, levelled=None,
                  body={"builder": body_entry["builder"], "triangles": body_triangles, "kept_faces": kept,
                        "parts_seen": seen},
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


def levelled_feet(copy, size):
    """The cut-down copy's feet brought down level (LEVEL_BAND, LEVEL_GAP, LEVEL_MOST): each quadrant's gap brought
    down, as a list (empty when none was over LEVEL_GAP or one was over LEVEL_MOST)."""
    import numpy as np
    flat = np.empty(len(copy.data.vertices) * 3)
    copy.data.vertices.foreach_get("co", flat)
    points = flat.reshape(-1, 3)  # Blender's frame: z up
    low = points[:, 2].min()
    band = LEVEL_BAND * (points[:, 2].max() - low)
    base = points[points[:, 2] <= low + band]
    middle = (base.min(axis=0) + base.max(axis=0)) / 2
    gaps, places = [], []
    for x_side in (base[:, 0] < middle[0], base[:, 0] >= middle[0]):
        for y_side in (base[:, 1] < middle[1], base[:, 1] >= middle[1]):
            chosen = base[x_side & y_side]
            if len(chosen):
                lowest = chosen[chosen[:, 2].argmin()]
                gaps.append(lowest[2] - low)
                places.append(lowest[:2])
    gaps, places = np.array(gaps), np.array(places)
    if gaps.max() <= LEVEL_GAP or gaps.max() > LEVEL_MOST * max(size):
        return []
    drops = np.where(gaps > LEVEL_GAP, gaps, 0.0)
    weights = 1.0 / np.maximum(((points[:, None, :2] - places[None]) ** 2).sum(axis=2), 1e-12)
    drop = (weights * drops).sum(axis=1) / weights.sum(axis=1)
    points[:, 2] -= drop * np.clip((low + band - points[:, 2]) / np.maximum(band - drop, 1e-9), 0.0, 1.0)
    copy.data.vertices.foreach_set("co", points.ravel())
    copy.data.update()
    return [round(float(gap), 4) for gap in drops if gap > 0]


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
