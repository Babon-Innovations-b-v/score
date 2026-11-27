"""Inside Blender (Cycles on the CPU): a generated person made whole (`person.py`) drawn standing and walking, her
head's own pieces carried onto the rigged, clothed body.

    blender -b --python blender_person.py -- <repo> <rig body.glb> <cloth.npz> <library> <renders> <samples> <size> \
        <film samples> <film size> <person out> <close-up photo>

The body is `blender_cloth.py`'s (still_rig's rigged shell, its jacket and jeans as tethered cloth, the body under
them), the park's light and the 85 mm, developed in plain sRGB. Its head is the swap's own (<person out>/swap's head
primitive: the mended head, cut and eased onto the neck, its paint blended into the body's), not the rig's thinned
copy: above the cut the rig's faces it covers are taken off and the head drawn as `blender_head.py` draws it (the face
texture on its planar UV and score_lib's skin, the eyeballs in the photo's iris, the cornea and wet line, the
lashes), with the hair step's painted hair taken off, its skin laid onto the scalp, and the scalp and strands laid
(`blender_sheet.py`'s). The head mesh is skinned by the rig's nearest weights under its chin, so its neck bends as
the rig's does; from the chin up it rides the Head joint rigidly, as the eyes, lashes, scalp and strands do. Every
piece made on the head model reaches the rig through one matrix (pieces.npz's head_to_rig).

Writes <renders>/standing_<view>.png (front, three_quarter, side, back), close_front.png and close_three_quarter.png
(the head, FACE_FRAME_M tall), walk_<view>_<point>.png (side and three quarters at left ahead, passing, right ahead),
walk_back_passing.png and film/<frame>.png (FILM_DEGREES; none with <film samples> 0).
"""
import json
import math
import pathlib
import sys
import types

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
REPO, RIG, CLOTH, LIBRARY, OUT, SAMPLES, SIZE, FILM_SAMPLES, FILM_SIZE, MADE, PHOTO = ARGS[:11]
MADE = pathlib.Path(MADE)
HERE = pathlib.Path(__file__).resolve().parent
HEAD_DIR = MADE / "head"


def loaded_with(arguments, loader):
    """`loader()` run with sys.argv's arguments after "--" set to `arguments` (the generated scripts read theirs on
    import), then put back."""
    kept = sys.argv
    sys.argv = [kept[0], "--", *map(str, arguments)]
    try:
        return loader()
    finally:
        sys.argv = kept


def cloth_module():
    """blender_cloth.py's functions without running its main (its last line calls it)."""
    path = HERE / "blender_cloth.py"
    source = path.read_text()
    body, tail = source.rsplit("\nmain()", 1)
    if tail.strip():
        raise RuntimeError(f"{path} no longer ends with its main() call")
    module = types.ModuleType("blender_cloth")
    module.__file__ = str(path)
    exec(compile(body, str(path), "exec"), module.__dict__)
    return module


sys.path.insert(0, str(HERE))
cloth = loaded_with([REPO, RIG, CLOTH, LIBRARY, OUT, "cloth", SAMPLES, SIZE, FILM_SAMPLES, FILM_SIZE], cloth_module)
blender_head = loaded_with([HEAD_DIR / "head.glb", HEAD_DIR / "eyes/eyes.npz", LIBRARY, 0.42, SAMPLES, OUT, HEAD_DIR],
                           lambda: __import__("blender_head"))
import blender_eyes  # noqa: E402  (loaded above with the head's arguments)
import blender_sheet  # noqa: E402
import blender_skin  # noqa: E402
import head_swap  # noqa: E402
import render  # noqa: E402
from blender_eyes import blender_face  # noqa: E402

TO_BLENDER = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # glTF (y up) to Blender (z up)
FAN_MATCH = 1e-4  # a shell face whose middle lies this near a fan's middle in pieces.npz (the rig's units) is that fan
UNDER_NECK = 0.02  # the collision body is drawn only this far (body heights) under the cut and lower
COVER_M = 0.015  # a rig face above the cut this near the swap's head (the rig's metres) is the head's: taken off
# A face of the swap's head whose nearest rig face is a cloth garment's and lies this near (the rig's metres; its
# faces some 5 mm across) is that garment's: the cloth draws it (`garment_cut`). The head model's high puffer collar,
# drawn by both, stood as torn shards round the neck and shimmered as she walked (whole person round 5, 2026-11-27).
GARMENT_MATCH_M = 0.008
STANDING = {"front": 180.0, "three_quarter": 215.0, "side": 270.0, "back": 0.0}  # blender_cloth's turns
FACE_FRAME_M = render.FACE_FRAME_M  # the close-ups: the head and the neck's top
FACE_UNDER_EYES_M = 0.07  # the close-up aimed this far under the eyes
CLOSE = {"front": 180.0, "three_quarter": 215.0}


def matrix_of(array):
    return Matrix([list(map(float, row)) for row in np.asarray(array)])


def coordinates(mesh):
    found = np.zeros(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", found)
    return found.reshape(-1, 3)


def tree_of(points):
    tree = KDTree(len(points))
    for number, point in enumerate(points):
        tree.insert(Vector(point), number)
    tree.balance()
    return tree


def swap_record():
    """The swap's head-to-body record: the JSON beside its glb in <person out>/swap (colour.json has none)."""
    return next(path for path in sorted((MADE / "swap").glob("*.json")) if path.with_suffix(".glb").exists())


def swap_head(pieces):
    """The swap's head primitive as its own object, its mesh in the head model's own frame (Blender's z up, the
    model's units) so the head's pieces lay on it as they lay on head.glb."""
    record = swap_record()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(record.with_suffix(".glb")))
    new = [item for item in bpy.data.objects if item not in before]
    item = next(found for found in new if found.type == "MESH")
    item.data.transform(item.matrix_world)
    item.parent = None
    item.matrix_world.identity()
    for other in new:
        if other is not item:
            bpy.data.objects.remove(other)
    mesh = item.data
    heights = {slot: [] for slot in range(len(mesh.materials))}
    for polygon in mesh.polygons:
        heights[polygon.material_index].append(polygon.center.z)
    head_slot = max(heights, key=lambda slot: np.mean(heights[slot]) if heights[slot] else -1e9)
    edit = bmesh.new()
    edit.from_mesh(mesh)
    bmesh.ops.delete(edit, geom=[face for face in edit.faces if face.material_index != head_slot], context="FACES")
    edit.to_mesh(mesh)
    edit.free()
    material = mesh.materials[head_slot]
    mesh.materials.clear()
    mesh.materials.append(material)
    mesh.polygons.foreach_set("material_index", np.zeros(len(mesh.polygons), np.int32))
    to_body = TO_BLENDER @ matrix_of(json.loads(record.read_text())["head_to_body_gltf"]) @ TO_BLENDER.inverted()
    mesh.transform(to_body.inverted())
    mesh.update()
    item.name = "head"
    return item


def rest_matrix(shell, pieces):
    """The head model's frame (Blender's z up) in the scene at the rig's bind."""
    return shell.matrix_world @ TO_BLENDER @ matrix_of(pieces["head_to_rig"]) @ TO_BLENDER.inverted()


def in_body(local):
    """Head-model points (Blender's frame, the model's units) in the swapped body's glTF frame, in its heights (y up,
    facing +z)."""
    model = np.stack([local[:, 0], local[:, 2], -local[:, 1]], 1)  # back to glTF
    record = json.loads(swap_record().read_text())
    body = model @ np.asarray(record["head_to_body_gltf"])[:3, :3].T + np.asarray(record["head_to_body_gltf"])[:3, 3]
    return body / float(record["body_height_units"])


def over_cut(local, pieces):
    """How high head-model points (Blender's frame, the model's units) lie over the swap's cut, in the body's units
    (its heights)."""
    record = json.loads(swap_record().read_text())
    return in_body(local)[:, 1] - float(pieces["level"]) / float(record["body_height_units"])


def rigid_share(local, pieces):
    """Each head point's share riding the Head alone: 0 at the cut, rising to 1 at the chin (`head_swap.chin_over_cut`
    on the head itself) and 1 above, so the whole face, lips and chin ride the Head rigidly and only the neck under
    the chin bends with the rig's (eased from 3 to 6 cm over the cut, the lips and chin rode half the neck's weights
    and the lower lip tore off the upper while she stood and walked, 2026-11-27); (shares, the chin's height)."""
    heights = over_cut(local, pieces)
    body = in_body(local)
    face = body[heights > 0.06]
    across = body[:, 0] - np.median(face[:, 0])
    chin = head_swap.chin_over_cut(heights, body[:, 2], across)
    return np.clip(heights / chin, 0.0, 1.0), chin


def above_cut(local, pieces):
    """Which head-model points (Blender's frame, the model's units) lie above the swap's cut."""
    return over_cut(local, pieces) > 0.0


def shell_cut(shell, head, pieces, garment):
    """The rig's faces above the cut that the swap's head covers taken off the shell, never a cloth garment's
    (`garment`, per polygon: the jacket's collar round the neck is the body's, drawn by the cloth), and still_rig's
    fans across the cut's loops (pieces.npz's `fan_centres`, `person.neck_fans`: wedges reaching across the neck's
    hollow and out under the hair, drawn as dark shards between the neck and the collar); how many."""
    to_head = (head.matrix_world.inverted() @ shell.matrix_world)
    tree = tree_of([head.matrix_world @ vertex.co for vertex in head.data.vertices])
    centres = np.array([to_head @ polygon.center for polygon in shell.data.polygons])
    above = above_cut(centres, pieces) & ~garment
    doomed = set()
    for index in np.flatnonzero(above):
        world = shell.matrix_world @ shell.data.polygons[int(index)].center
        if tree.find(world)[2] < COVER_M:
            doomed.add(int(index))
    fans = tree_of(cloth.to_blender(pieces["fan_centres"]))
    doomed.update(polygon.index for polygon in shell.data.polygons if fans.find(polygon.center)[2] < FAN_MATCH)
    edit = bmesh.new()
    edit.from_mesh(shell.data)
    edit.faces.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[edit.faces[index] for index in sorted(doomed)], context="FACES")
    edit.to_mesh(shell.data)
    edit.free()
    shell.data.update()
    return len(doomed)


def garment_cut(head, shell, garment):
    """The swap head's faces that are a cloth garment's (`garment`, per shell polygon) taken off the head: those whose
    nearest rig face is a garment's within GARMENT_MATCH_M (both at the bind; the rig is the thinned swap, so each of
    the head's faces has its copy there); how many."""
    centres = [shell.matrix_world @ polygon.center for polygon in shell.data.polygons]
    tree = tree_of(centres)
    doomed = []
    for polygon in head.data.polygons:
        _, index, distance = tree.find(head.matrix_world @ polygon.center)
        if garment[index] and distance < GARMENT_MATCH_M:
            doomed.append(polygon.index)
    edit = bmesh.new()
    edit.from_mesh(head.data)
    edit.faces.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[edit.faces[index] for index in doomed], context="FACES")
    edit.to_mesh(head.data)
    edit.free()
    head.data.update()
    return len(doomed)


def under_cut(body, head, pieces):
    """The collision body's faces above UNDER_NECK under the cut taken off (it is drawn for a garment's gaps; pushed
    under the rig's neck, it stood out of the swap's slimmer one as dark strips at the collar, whole person round 3,
    2026-11-27); how many."""
    to_head = head.matrix_world.inverted() @ body.matrix_world
    centres = np.array([to_head @ polygon.center for polygon in body.data.polygons])
    doomed = np.flatnonzero(over_cut(centres, pieces) > -UNDER_NECK)
    edit = bmesh.new()
    edit.from_mesh(body.data)
    edit.faces.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[edit.faces[int(index)] for index in doomed], context="FACES")
    edit.to_mesh(body.data)
    edit.free()
    body.data.update()
    return len(doomed)


def skin_marked(head, lids, skin):
    """The `painted_skin` face mark: the mark of the mended mesh's face nearest each face (the swap cut and eased the
    neck's, so exact middles no longer match: `blender_skin.skin_marked`'s test)."""
    centres = lids["head.points"][lids["head.triangles"]].mean(1)
    skin_tree = tree_of(blender_face.z_up(np.asarray(skin["skin_centres"], np.float64)))
    marks = np.array([skin_tree.find(Vector(point))[2] < 1e-6 for point in blender_face.z_up(centres)], np.int32)
    tree = tree_of(blender_face.z_up(centres))
    found = np.array([marks[tree.find(polygon.center)[1]] for polygon in head.data.polygons], np.int32)
    head.data.attributes.new("painted_skin", "INT", "FACE").data.foreach_set("value", found)
    return int(found.sum())


def hair_taken_off(head, pieces):
    """The hair step's painted hair taken off the head and its skin laid onto the scalp (its points moved as kept.glb
    moved them); (faces taken off, points laid)."""
    points = blender_face.z_up(pieces["hair_points"].astype(np.float64))
    laid = blender_face.z_up(pieces["hair_laid"].astype(np.float64))
    tree = tree_of(points)
    moved = 0
    for vertex in head.data.vertices:
        _, index, distance = tree.find(vertex.co)
        if distance < 1e-6 and np.abs(laid[index]).max() > 1e-7:
            vertex.co = vertex.co + Vector(laid[index])
            moved += 1
    centres = tree_of(blender_face.z_up(pieces["hair_centres"].astype(np.float64)))
    removed = pieces["hair_removed"]
    edit = bmesh.new()
    edit.from_mesh(head.data)
    edit.faces.ensure_lookup_table()
    doomed = [face for face in edit.faces if removed[centres.find(face.calc_center_median())[1]]]
    bmesh.ops.delete(edit, geom=doomed, context="FACES")
    edit.to_mesh(head.data)
    edit.free()
    head.data.update()
    return len(doomed), moved


def weights_held(shell, armature):
    """The shell's skin weights at the bind, read before any of its faces are taken off: (a tree of its points in the
    scene, each point's (group, weight) pairs, each group's joint, every joint under the Head read as the Head)."""
    under_head = {bone.name for bone in armature.data.bones["Head"].children_recursive}
    print(f"head joints: {sorted(under_head)} read as the Head", flush=True)
    names = ["Head" if group.name in under_head else group.name for group in shell.vertex_groups]
    tree = tree_of([shell.matrix_world @ vertex.co for vertex in shell.data.vertices])
    held = [[(group.group, group.weight) for group in vertex.groups] for vertex in shell.data.vertices]
    return tree, held, names


def weights_copied(item, weights, armature, rigid):
    """`item` skinned by the shell's `weights` (`weights_held`) at its nearest point (both at the bind), eased to the
    Head alone by `rigid` (0 to 1 per point): the face rides the Head as its eyes, lashes and hair do (copied all the
    way up, the rig's thinned head's weights pulled the lips and chin off the face, 2026-11-27), the neck at the cut
    bends as the rig's below it. The shell is read whole: read after its faces under the head were taken off, the
    neck's nearest points were the jacket collar's and the neck flew into the jacket in shards (2026-11-27)."""
    tree, held, names = weights
    groups = {name: item.vertex_groups.new(name=name) for name in dict.fromkeys(names)}
    for vertex in item.data.vertices:
        share = float(rigid[vertex.index])
        summed = {"Head": share}
        for group, weight in held[tree.find(item.matrix_world @ vertex.co)[1]]:
            summed[names[group]] = summed.get(names[group], 0.0) + weight * (1.0 - share)
        for name, weight in summed.items():
            groups[name].add([vertex.index], weight, "REPLACE")
    modifier = item.modifiers.new("skin", "ARMATURE")
    modifier.object = armature


def riding(armature, matrix):
    """An empty on the Head joint at `matrix` in the scene (set with the armature at its bind)."""
    frame = bpy.data.objects.new("head_frame", None)
    bpy.context.scene.collection.objects.link(frame)
    frame.parent = armature
    frame.parent_type = "BONE"
    frame.parent_bone = "Head"
    bpy.context.view_layer.update()
    frame.matrix_world = matrix
    bpy.context.view_layer.update()
    return frame


def groomed(frame, pieces):
    """The scalp, the neck's back and the strands (the hair step's, in its metres) under `frame`; the objects."""
    groom = dict(np.load(MADE / "hair/groom.npz"))
    fibre = json.loads((MADE / "hair/fibre.json").read_text())
    space = bpy.data.objects.new("groom_space", None)
    bpy.context.scene.collection.objects.link(space)
    space.parent = frame
    space.scale = (1.0 / float(pieces["hair_scale"]),) * 3
    scalp = blender_sheet.mesh_of("scalp", groom["scalp_points"], groom["scalp_triangles"], space)
    blender_sheet.painted(scalp, groom["scalp_colours"])
    items = [scalp]
    if len(groom["neck_points"]):
        neck = blender_sheet.mesh_of("neck", groom["neck_points"], groom["neck_triangles"], space)
        blender_sheet.painted(neck, np.tile(groom["skin_colour"], (len(groom["neck_points"]), 1)))
        items.append(neck)
    for item in items:  # never below the cut, inside the collar
        local = np.array([(Matrix.Diagonal((*space.scale, 1.0)) @ vertex.co)[:] for vertex in item.data.vertices])
        under = ~above_cut(local, pieces)
        edit = bmesh.new()
        edit.from_mesh(item.data)
        edit.faces.ensure_lookup_table()
        bmesh.ops.delete(edit, geom=[face for face in edit.faces if all(under[vert.index] for vert in face.verts)],
                         context="FACES")
        edit.to_mesh(item.data)
        edit.free()
    items += blender_sheet.strand_pieces("hair", groom["counts"], groom["points"], groom["radius"], fibre["hair"],
                                         space)
    return items


def head_dressed(armature, shell, pieces, data):
    """The swap's head on the rig with its face, eyes, lashes and hair; (head, the Head joint's frame)."""
    eyes = dict(np.load(HEAD_DIR / "eyes/eyes.npz", allow_pickle=False))
    lids = dict(np.load(HEAD_DIR / "lids/lids.npz", allow_pickle=False))
    skin = dict(np.load(HEAD_DIR / "skin/skin.npz", allow_pickle=False))
    head = swap_head(pieces)
    head.parent = shell.parent
    matrix = rest_matrix(shell, pieces)
    head.matrix_world = matrix
    bpy.context.view_layer.update()
    weights = weights_held(shell, armature)
    simulated = [cloth.kinds_of(data).index(kind) for kind in cloth.simulated_of(data)]
    garment = np.isin(cloth.face_kinds(shell, data), simulated)
    print(f"head faces the cloth draws taken off: {garment_cut(head, shell, garment)}", flush=True)
    print(f"rig faces under the head taken off: {shell_cut(shell, head, pieces, garment)}", flush=True)
    blender_skin.attributes(head, skin)
    blender_skin.face_uv(head, skin["box"])
    print(f"painted skin faces: {skin_marked(head, lids, skin)}", flush=True)
    folder = MADE / "renders_skin"  # face.png alone: the head's own (blended) paint, not skin/paint.png
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / "face.png").exists():
        (folder / "face.png").symlink_to(HEAD_DIR / "skin/face.png")
    frame = riding(armature, matrix)
    space = bpy.data.objects.new("skin_metres", None)  # the pores on metric coordinates riding the head
    bpy.context.scene.collection.objects.link(space)
    space.parent = frame
    blender_skin.skin_material(head, LIBRARY, folder, space)
    print(f"hair faces taken off, skin points laid: {hair_taken_off(head, pieces)}", flush=True)
    rigid, chin = rigid_share(coordinates(head.data), pieces)
    print(f"the head rides the Head alone from its chin, {chin:.4f} body heights over the cut", flush=True)
    weights_copied(head, weights, armature, rigid)
    eyes.update({"wet.points": lids["wet.points"], "wet.triangles": lids["wet.triangles"]})
    laid = blender_eyes.laid(head, eyes)
    for item in laid.values():
        item.parent = frame
    blender_head.iris_pictured(laid["eyes"])
    fibres = json.loads((HEAD_DIR / "lids/fibre.json").read_text())
    lashes = blender_sheet.strand_pieces("lashes", lids["lashes.counts"], lids["lashes.points"],
                                         lids["lashes.radius"], fibres["lashes"], frame)
    print(f"lashes {len(lashes)} pieces, hair {len(groomed(frame, pieces))} pieces", flush=True)
    return head, frame, space, eyes


def metric(space, frame):
    """The skin's coordinates in metres: `space` under the head's frame with no scale of its own in the scene."""
    world = frame.matrix_world
    location, rotation, _ = world.decompose()
    space.matrix_world = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()


def eyes_point(frame, eyes):
    """The corneas' middle in the scene."""
    points = blender_face.z_up(np.asarray(eyes["cornea_apex"], np.float64))
    return sum((frame.matrix_world @ Vector(point) for point in points), Vector()) / len(points)


def close_drawn(scene, camera, turntable, frame, eyes, degrees, name):
    """The head close up (FACE_FRAME_M tall) turned `degrees`, focused on the eyes."""
    turntable.rotation_euler = (0.0, 0.0, -math.radians(degrees))
    bpy.context.view_layer.update()
    focus = eyes_point(frame, eyes)
    aim = Vector((focus.x, focus.y, focus.z - FACE_UNDER_EYES_M))
    distance = FACE_FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0)
    render.aimed(camera, Vector((aim.x, aim.y - distance, focus.z)), aim, render.STOPS["face"], focus)
    path = pathlib.Path(OUT) / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    render.developed(path, camera.data.dof.aperture_fstop)
    print(f"drew {name}", flush=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = dict(np.load(CLOTH))
    pieces = dict(np.load(MADE / "pieces.npz"))
    armature, shell = cloth.imported()
    for item in list(bpy.data.objects):  # the importer's stray sphere (as ../hair/groom.py finds it), under the ground
        if item.name.startswith("Icosphere"):
            bpy.data.objects.remove(item)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    head, frame, space, eyes = head_dressed(armature, shell, pieces, data)
    garments = cloth.garments_made(shell, data)
    print(f"collision body faces at the neck taken off: {under_cut(cloth.body_made(armature, shell, data), head, pieces)}",
          flush=True)
    armature.data.pose_position = "POSE"
    holder, turntable = cloth.staged(float(data["scale"]))
    bpy.context.view_layer.update()
    metric(space, frame)
    scene = bpy.context.scene
    standing = cloth.playing(armature, "standing")
    cloth.at(armature, standing, garments, data, "standing/standing", 0, holder)
    items = [item for item in scene.objects if item.type == "MESH" and not item.hide_render]
    low, high = render.bounds(items)
    middle = Vector((0.0, 0.0, (low.z + high.z) / 2))
    high = Vector((0.0, 0.0, high.z))
    print(f"standing height {high.z - low.z:.3f} m; tallest pieces "
          f"{sorted(((round(render.bounds([item])[1].z, 3), item.name) for item in items), reverse=True)[:4]}, "
          f"lowest {sorted((round(render.bounds([item])[0].z, 3), item.name) for item in items)[:3]}",
          flush=True)
    render.film(scene, render.place(LIBRARY, middle, cloth.SETTING))
    scene.view_settings.view_transform, scene.view_settings.look = blender_eyes.VIEW
    render.on_card(scene)
    scene.cycles.samples = int(SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = int(SIZE) * 2 // 3, int(SIZE)
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    camera = render.camera_made(scene)
    out = pathlib.Path(OUT)
    out.mkdir(parents=True, exist_ok=True)
    for view, degrees in STANDING.items():
        render.framed(camera, middle, high, render.MARGIN, render.EYE_HEIGHT, render.STOPS["side"])
        render.drawn(scene, turntable, degrees, out, f"standing_{view}")
    scene.render.resolution_x = int(SIZE) * 4 // 5
    for view, degrees in CLOSE.items():
        close_drawn(scene, camera, turntable, frame, eyes, degrees, f"close_{view}")
    scene.render.resolution_x = int(SIZE) * 2 // 3
    render.framed(camera, middle, high, render.MARGIN, render.EYE_HEIGHT, render.STOPS["side"])
    walking = cloth.playing(armature, "walking")
    for view, degrees in cloth.VIEWS:
        for point in ("left_ahead", "passing", "right_ahead"):
            cloth.at(armature, walking, garments, data, f"walking/{point}", 0, holder)
            render.drawn(scene, turntable, degrees, out, f"walk_{view}_{point}")
    cloth.at(armature, walking, garments, data, "walking/passing", 0, holder)
    render.drawn(scene, turntable, 0.0, out, "walk_back_passing")
    print("SHEET RENDER DONE", flush=True)
    if not int(FILM_SAMPLES):  # a check of the sheet alone
        return
    scene.cycles.samples = int(FILM_SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = int(FILM_SIZE) * 2 // 3, int(FILM_SIZE)
    film = out / "film"
    film.mkdir(exist_ok=True)
    for index in range(len(data["walking/film/time"])):
        path = film / f"{index:03d}.png"
        if path.exists():
            continue
        cloth.at(armature, walking, garments, data, "walking/film", index, holder)
        turntable.rotation_euler = (0.0, 0.0, -math.radians(cloth.FILM_DEGREES))
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    print("FILM RENDER DONE", flush=True)


if __name__ == "__main__":
    main()
