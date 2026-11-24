"""Inside Blender (bench.py's look step, through the card queue, #182): a made model's finish drawn as the bake paints
it, the model whole (its own vertex normals kept) under one material, each slot's library recipe mixed in by its texel
mask on the model's own UVs (recipes.masked) and darkened by the model's own ambient occlusion baked on them
(bake.occlusion, #206: tc6w2's anesthesia machine drawn one flat white where NVIDIA's shades into its seams), and
in the seams its decoded mesh holds where the job names one (`decoded`: bake.seamed, #159), seen from
the close-up's view direction and up (a flat row from straight above, +y up), framed on its own box under the close-up's
own studio light (closeup.lit: two large area lamps and a dim grey sky), so it is lit as NVIDIA's input render it is
held to. Under the library renders' two suns and a bright, even grey world a mirror finish reflects only that grey:
tc5r's chrome chucks, nozzle and rods were drawn dull flat grey at roughness 0.13, where the input's chrome shines
(#159). Drawn at wear 0 and dirt 0: the bench names none. Then the mesh alone (`bare.png`, the job's `bare`): the same
model, camera and light in one plain white surface, its own vertex normals kept, which the look's holes check reads
(bench.py look_holes, #159: the printer box's normals turned inward drew black holes through its front).
The mesh is laid in the model's own frame first (`laid`), as its finish placed the decals and the recipes measure in
metres; the blob under each hardware piece the finish laid is cut away (`cut_away`, #212) and the piece's library
mesh laid there in its finish's recipe (`laid_pieces`), drawn in the look and in the mesh alone; each text decal's box
as drawn is written beside the picture (`marks.json`), which the bench reads back (#185).
Under each mark its plate is closed, as the place's bake closes it (#159 round 13): TRELLIS.2's vent bumps pressed flat
before its occlusion is baked (bake.pressed_under) and the holes it cut through a locker's door covered after
(bake.cards_over).
A job naming a `usd` in place of a `glb` draws NVIDIA's own model, its own materials, by this camera and light alone
(`truth_drawn`): the look's light held to the close-up it was drawn into (bench.light_step, #206).

    blender -b -P look.py -- <look.json (finish.look_job's)>
"""
import json
import math
import pathlib
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "library" / "inside"))
sys.path.insert(0, str(HERE))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402  (the model's own ambient occlusion, #206)
import closeup  # noqa: E402  (the close-up's light, `lit`)
import recipes  # noqa: E402
import scene_setup  # noqa: E402
from finish import look_axes  # noqa: E402

BARE_WHITE = (0.8, 0.8, 0.8, 1.0)  # the mesh-alone picture's one surface: the principled default's white


def look_material(masks, occlusion=None):
    """One material: each slot's recipe (at wear 0, dirt 0 and its spec's seed) mixed over the ones before it by its
    texel mask, read on the model's active UVs, a glass's alpha drawn as the bake carries it (recipes.shaded's
    `through`, #186), every base colour darkened by the model's own ambient occlusion (`occlusion`, #206)."""
    entries = [(mask["mask"], recipes.channels(mask["spec"], 0.0, 0.0, mask["spec"]["seed"])) for mask in masks]
    material = recipes.masked(entries, lambda found: recipes.shaded(found, through=True), uv_map="",
                              occlusion=occlusion).item()
    material.displacement_method = "BUMP"
    return material


def occluded(meshes, masks, decoded=None):
    """The model's own ambient occlusion on its active UVs, at its texel masks' side (bake.occlusion, as the place's
    bake gives its finish, #206), darkened in the seams its `decoded` mesh holds where the job names one
    (bake.seamed, #159)."""
    side = bpy.data.images.load(str(masks[0]["mask"]), check_existing=True).size[0]
    if decoded is None:
        return bake.occlusion(meshes, "", side, bake.occlusion_reach(meshes))
    return bake.seamed(meshes, decoded, "", side, bake.occlusion_reach(meshes))


def decoded_of(job):
    """The job's `decoded` mesh (TRELLIS.2's before its remesh, set in the place as the model is: make's
    <entry>-decoded.glb) imported as one object, or None where the job names none."""
    if not job.get("decoded"):
        return None
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=job["decoded"])
    found = [item for item in bpy.context.scene.objects if item not in before and item.type == "MESH"]
    if len(found) != 1:
        raise SystemExit(f"{job['decoded']}: {len(found)} meshes, not the one decoded mesh")
    return found[0]


def laid(meshes):
    """Each mesh's own data moved into the model's frame and its object left at none (#185): final.glb's mesh sits
    under a `fitted` node that turns and scales it, so in its object coordinates the decals (placed in the model's
    frame) printed on its side, smeared, and the recipes' sizes in metres were drawn a third too large."""
    for item in meshes:
        placed = item.matrix_world.copy()
        item.parent = None
        item.data.transform(placed)
        item.data.update()
        item.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()  # each bound_box (framed's) read anew


def vertex_normals(mesh):
    """Each vertex's normal as the mesh draws it (its corners' own normals, the model's kept ones, averaged)."""
    import numpy as np
    corners = np.empty(len(mesh.loops) * 3)
    mesh.corner_normals.foreach_get("vector", corners)
    vertex = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", vertex)
    found = np.zeros((len(mesh.vertices), 3))
    np.add.at(found, vertex, corners.reshape(-1, 3))
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-9)


def cut_away(meshes, pieces):
    """Each hardware piece's blob cut away (#212, hardware_pieces.py's `cut`): every vertex of the laid meshes within
    its radius of the line through the cut's point along the piece's facing, and between its depth under the face and
    its rise over it (the blob's, standing `stands` over the face, or the face's own, turned within `edge_turn` of its
    facing: never an edge to another face), laid on the face (the plane through the cut's point, which lies on the face) and drawn in
    to the line (closed), each moved vertex's drawn normal turned to the face's. The blob, inside the radius's flat core (all
    but its outer `falloff`), closes to its point, its faces of no area; the ring of face round it is drawn in over the
    core, its own paint with it, so the face's own surface fills the cut, flat. Laid flat in place the blob folded over
    itself and its coincident faces drew the cut as a dark crumpled ring (the tc6 locker's locks), and a patch in one
    finish over it painted out the gas stove's printed panel."""
    import numpy as np
    for item in meshes:
        points = np.empty(len(item.data.vertices) * 3)
        item.data.vertices.foreach_get("co", points)
        points = points.reshape(-1, 3)
        normals = vertex_normals(item.data)
        for piece in pieces:
            normal, cut = np.asarray(piece["normal"]), piece["cut"]
            reach = points - np.asarray(cut["at"])
            height = reach @ normal
            way = reach - np.outer(height, normal)
            across = np.linalg.norm(way, axis=1)
            core = cut["radius"] * (1 - cut["falloff"])
            inside = ((across < cut["radius"]) & (height > -cut["depth"]) & (height < cut["rise"])
                      & ((height > cut["stands"]) | (normals @ normal > np.cos(np.radians(cut["edge_turn"])))))
            drawn = np.clip((across[inside] - core) / (cut["radius"] - core), 0.0, 1.0)
            eased = 1.0 - drawn
            rim = np.asarray(cut["at"]) + way[inside] / np.maximum(across[inside], 1e-12)[:, None] * cut["radius"]
            closed = np.outer(eased, cut["at"]) + rim * drawn[:, None]
            points[inside] = closed + np.outer(height[inside] * drawn, normal)
            normals[inside] = normals[inside] * drawn[:, None] + normal * eased[:, None]
        item.data.vertices.foreach_set("co", points.ravel())
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        item.data.normals_split_custom_set_from_vertices((normals / np.maximum(lengths, 1e-9)).tolist())
        item.data.update()


def laid_pieces(scene, pieces):
    """Each hardware piece's library mesh (its glb: +z out of its face, its back at z 0, glTF's Y up, which Blender's
    import turns to its -y) laid at its point on its face, its +z along the facing, its +y along the up, scaled evenly
    to its size (the geometric mean of its two sides' ratios, turned a quarter when its long side runs the other way),
    in the recipe of the finish it is painted in; the pieces' objects."""
    import numpy as np
    laid = []
    for piece in pieces:
        before = set(scene.objects)
        bpy.ops.import_scene.gltf(filepath=piece["glb"])
        found = [item for item in scene.objects if item not in before and item.type == "MESH"]
        for item in found:
            placed = item.matrix_world.copy()
            item.parent = None
            item.data.transform(placed)
            item.matrix_world = Matrix.Identity(4)
        points = np.array([list(vertex.co) for item in found for vertex in item.data.vertices])
        wide, tall = np.ptp(points[:, 0]), np.ptp(points[:, 2])  # its own x and y (y up turned to Blender's z)
        across, upward = piece["size_m"]
        turned = (wide > tall) != (across > upward) and max(wide, tall) > 1.2 * min(wide, tall)
        if turned:
            wide, tall = tall, wide
        scale = math.sqrt(across / max(wide, 1e-9) * upward / max(tall, 1e-9))
        normal, up = Vector(piece["normal"]).normalized(), Vector(piece["up"]).normalized()
        right = up.cross(normal)
        if turned:
            right, up = -up, right
        # its own axes in Blender after the import: x across, -y out of its face, z up
        basis = Matrix((right, -normal, up)).transposed().to_4x4()
        material = recipes.shaded(recipes.channels(piece["spec"], 0.0, 0.0, piece["spec"]["seed"]),
                                  through=True).item()
        for item in found:
            item.matrix_world = Matrix.Translation(Vector(piece["at"])) @ basis @ Matrix.Scale(scale, 4)
            item.data.materials.clear()
            item.data.materials.append(material)
        laid += found
    return laid


def mark_boxes(scene, masks):
    """[{"text", "box": [left, top, right, bottom] pixels}] of each text decal of the slots' specs as drawn: its four
    corners (recipes.decal_axes about its `at`, its size) seen through the scene's camera."""
    side = scene.render.resolution_x
    found = []
    for mask in masks:
        for decal in mask["spec"].get("decals") or []:
            if not decal.get("text"):
                continue
            right, up, _ = recipes.decal_axes(decal)
            width, height = decal["size_m"]
            corners = [Vector(decal["at"]) + Vector(right) * (across * width / 2) + Vector(up) * (upward * height / 2)
                       for across in (-1, 1) for upward in (-1, 1)]
            seen = [world_to_camera_view(scene, scene.camera, corner) for corner in corners]
            columns, rows = [point.x * side for point in seen], [(1 - point.y) * side for point in seen]
            found.append({"text": decal["text"], "box": [min(columns), min(rows), max(columns), max(rows)]})
    return found


def framed(scene, meshes, job):
    """A camera on the close-up's view direction and up (finish.look_axes of the job's eye, aim and up), framing the
    meshes' box at its fov."""
    corners = [item.matrix_world @ Vector(corner) for item in meshes for corner in item.bound_box]
    low = Vector([min(corner[axis] for corner in corners) for axis in range(3)])
    high = Vector([max(corner[axis] for corner in corners) for axis in range(3)])
    centre, radius = (low + high) / 2, (high - low).length / 2
    right, up, back = (Vector(axis) for axis in look_axes(job))
    distance = radius / math.sin(math.radians(job["fov"]) / 2) * 1.05
    data = bpy.data.cameras.new("look")
    data.sensor_fit, data.angle = "VERTICAL", math.radians(job["fov"])
    data.clip_start, data.clip_end = 0.001 * radius, 100 * radius
    camera = bpy.data.objects.new("look", data)
    scene.collection.objects.link(camera)
    camera.matrix_world = Matrix.Translation(centre + back * distance) @ Matrix((right, up, back)).transposed().to_4x4()
    scene.camera = camera
    return [list(low), list(high)]


def drawn(scene, path):
    """The scene rendered to `path` as an RGBA PNG."""
    scene.render.filepath = path
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def bare_material():
    """One plain white surface: the mesh alone, shaded by its own normals."""
    material = bpy.data.materials.new("bare")
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = BARE_WHITE
    return material


def seen(scene, meshes, job):
    """The look's camera framing the meshes (framed) and the close-up's own light on their box (closeup.lit, #200):
    one setting for a made model and for NVIDIA's own (truth_drawn), so the light the bench holds to the close-up is
    the light every look is drawn under (#206). The box."""
    box = framed(scene, meshes, job)
    closeup.lit(scene, *box, {"eye": list(scene.camera.matrix_world.translation)})
    return box


def truth_drawn(scene, job):
    """NVIDIA's own model (the job's `usd`, read as closeup.imported reads it, its own materials) drawn by this look's
    camera and light to the job's `out`: the look's light calibration (bench.light_step, #206), held to the
    close-up NVIDIA's model was drawn into."""
    meshes = closeup.imported(pathlib.Path(job["usd"]))
    box = seen(scene, meshes, job)
    drawn(scene, job["out"])
    print("LOOK", json.dumps({"out": job["out"], "box": box, "truth": job["usd"]}), flush=True)


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    scene = scene_setup.empty_scene(job["side"], job["samples"])
    if job.get("usd"):
        truth_drawn(scene, job)
        return
    bpy.ops.import_scene.gltf(filepath=job["glb"])
    meshes = [item for item in scene.objects if item.type == "MESH"]
    decoded = decoded_of(job)
    laid(meshes + ([decoded] if decoded else []))
    cut_away(meshes + ([decoded] if decoded else []), job.get("hardware") or [])
    decals = [decal for mask in job["masks"] for decal in mask["spec"].get("decals") or []]
    closing = len(meshes) == 1  # closed under its marks (score #159 round 13) as the place's bake closes it
    if closing:
        bake.pressed_under(meshes[0], decals)
    material = look_material(job["masks"], occluded(meshes, job["masks"], decoded))
    if closing:
        bake.cards_over(meshes[0], decals)
    if decoded is not None:
        bpy.data.objects.remove(decoded)
    for item in meshes:
        item.data.materials.clear()
        item.data.materials.append(material)
    pieces = laid_pieces(scene, job.get("hardware") or [])
    box = seen(scene, meshes, job)
    drawn(scene, job["out"])
    bare = bare_material()
    for item in meshes + pieces:
        item.data.materials.clear()
        item.data.materials.append(bare)
    drawn(scene, job["bare"])
    marks = pathlib.Path(job["out"]).with_name("marks.json")
    marks.write_text(json.dumps(mark_boxes(scene, job["masks"]), indent=1))
    print("LOOK", json.dumps({"out": job["out"], "box": box, "slots": [mask["slot"] for mask in job["masks"]]}),
          flush=True)


main()
