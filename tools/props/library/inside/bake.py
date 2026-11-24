"""Runs inside Blender: bake pieces' library materials into the maps the game draws (base colour, roughness and
metal, normal), several pieces into one shared set of pictures, and write each piece as a .gltf beside them.

    import bake
    atlas = bake.Atlas("hub_slice", [piece, ...], density=512)        # every piece's UVs packed into one square
    atlas.bake_self(piece, specs, wear, dirt, seed)                    # a code-built piece's own surfaces
    atlas.bake_from(high, low, specs, wear, dirt, seed, reach)         # a generated piece, from its full model
    atlas.finish(); atlas.export(piece, folder)

A generated piece too big for one picture set at its density (`split`) is cut into several maps instead of capped: its
faces fall into blocks of near-equal area, each block its own picture set and its own material on the piece, all at
SPLIT_DENSITY, the room kit's density. The .gltf then holds one primitive per map.

Texture memory (the owner, round two: share textures between pieces, size them per piece): the pieces of one job
share one picture set instead of one set each, every face at the set's one density (a sharp part's at its larger
share). A face toward the kit's back once packed at a twentieth of it baked onto the picture's unpainted black: 1,137
of the October 2026 code-built library models, a median 37% of each one's surface (2026-11-23). Base colour and
metal-roughness are baked at half the normal map's side, since the ink look draws flat colour by region and the
detail lives in the normal map.

Each material slot is named for a library variant; `specs` maps that name to its resolved entry (library.py). The
recipe (recipes.py) is built per slot and each channel given off as light is baked, so the game gets the recipe's
exact colour, roughness and metal, not a lit picture; the normal map is baked from the shaded recipe.
"""
import math
import pathlib

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import recipes
import route

LARGEST = 4096
# A generated piece past one LARGEST picture set at its density is split into maps (`split`), each a LARGEST set at most,
# baked at the room kit's density (route.FAR, 512 texels a metre of normal map; the kit
# measured 152 to 567 colour texels a metre near the films' cameras, the audit of 2026-10-18, against 52 to 89 on the
# capped ship, wreck, lander and old station modules). The ship (854 m2) takes 22 maps; MOST_MAPS holds the memory a
# piece's bake and the game's textures take, and past it the piece takes the density that fits and says so.
SPLIT_DENSITY = 512
MOST_MAPS = 32
# A shared set a little past the cap (round six: a set planned by its boxes held 9.8 m2, 1% over) takes the density
# that fits and reports it, as a single piece does; further past, it stops.
CAP_SLACK = 1.15
SMALLEST = 256
# How much of the square a packed UV layout fills, to size the pictures for a texel density.
UV_FILL = 0.6
# How many times the texel density a printed or screen part's faces get (labels, keypads, notices, screen content):
# read up close, they came out soft at the room's density (the owner, 2026-10-06).
SHARP_SCALE = 3.0
# Only a set drawn near the player gets its print sharp (round six: the high status display's screen alone, at three
# times a far set's density, needed a 4096 picture set and put the hub past its room budget).
SHARP_FROM = 1024
# The library families whose parts are drawn sharp.
SHARP_FAMILIES = ("print", "screen")
# A part carrying decals (score #164) is drawn at route.PRINT colour texels a metre, NVIDIA's median for small and
# medium models (#161 rule 7): colour is baked at half the normal map's side, so its faces take 2 * PRINT over the
# set's density (about 5.9 times a near set's), never less than SHARP_SCALE; a 6 mm key legend is then 18 px across.
# A text decal drawn denser (its `px_per_m`, score text_decals.density: a line under 1 cm tall, #159 round 8) has its
# part drawn at its own density, so the bake prints its letters as sharp as they were drawn.
COLOUR_SHARE = 2.0
MARGIN_PIXELS = 3
# A per-face packed piece's gap round each face, in normal-map pixels (packed_per_face). Measured on the greenhouse
# crops' cut-down copies (2026-10-16): smart_project split the herb's into 2,913 islands of one or two triangles, and
# pack_islands' MARGIN_PIXELS round each left them 1% of the square, every face under a colour texel (72% baked
# black); packed face by face with this gap the herb filled 60% and every face held a texel (lettuce 98%, greens 100%).
FACE_MARGIN_PIXELS = 0.5
# A generated piece's full model is lumpy (Pixal3D), and its lumps came through as relief: baked into the normal map
# and read as edges by the wear's bevel test and as cavities by the dirt (the materials audit, 2026-10-18: blotches
# on the consoles, ragged wear). Only the finishes whose own surface is lumpy keep the model's normals (cast metal,
# rubber, fabric); every other finish is shaded by the model's normals smoothed over SMOOTH_REACH, so it takes the
# recipe's own relief over the model's shape, and its wear and dirt read that shape, not its lumps.
OWN_LUMPS = ("cast_metal", "rubber", "cloth", "quilted")
SMOOTH_REACH = 0.03
# Neighbouring faces whose smoothed normals part by SMOOTH_CREASE or more do not smooth into each other: a real edge
# stays sharp, so its wear stays on it.
SMOOTH_CREASE = math.radians(35.0)
SMOOTH_ROUNDS_MOST = 200
# A generated model's ambient occlusion (occlusion, #206): samples a texel, and its rays' reach as a share of the
# model's box diagonal (occlusion_reach). On tc6w2's anesthesia machine (bench finish.shade, its parts held to the input
# close-up's shading): unshaded 0.22 of its area held, at 0.05 of its diagonal 0.76, at 0.1 0.76 with its white body's
# creases 3.9 deep for the input's 5.1, at 0.02 0.22 (a seam's shadow too narrow to show at the look's pixels).
OCCLUSION_SAMPLES = 128
OCCLUSION_SHARE = 0.1
# The seams a generated model's remesh closed (seamed, #159 r11: TRELLIS.2's decoded mesh holds every drawer seam and
# door line, a voxel or less wide, and to_glb's remesh closes them with #191's pinholes). The decoded mesh's occlusion is
# baked onto the model's UVs from a cage SEAM_CAGE of the model's longest side out (its surface lies a voxel, a 1024th
# of the box, or so off the model's: on the bench's anesthesia machine 1.8 mm at the median, 2.6 at the 95th
# percentile, for 2.3 m). Its holes and flipped patches bake dark blots there too, so only a thin long dark run is kept:
# a texel SEAM_DARK of its mean within SEAM_REACH texels or darker, on a run SEAM_LENGTH texels long along one of four
# ways at SEAM_ALONG full and at most SEAM_ACROSS of the 9 texels across it, both its sides SEAM_REACH texels across
# lighter by SEAM_DARK (a blot's rim, dark on one side, is no seam), grown a texel; it shades the model's own
# occlusion by its ratio to that mean, never below SEAM_LEAST. Seen on r206ao's anesthesia machine and locker (r11):
# the locker's door outlines and the cabinet's side seam drawn, no blot; unfiltered, blots and black flipped patches
# over the drawers and the bench's leg.
SEAM_CAGE = 0.004
SEAM_REACH = 4
SEAM_DARK = 0.85
SEAM_LENGTH = 12
SEAM_ALONG = 0.8
SEAM_ACROSS = 3
SEAM_LEAST = 0.55


def box_of(items):
    """The low and high corners of `items`' box in the scene (each one's bound box as placed)."""
    corners = [item.matrix_world @ Vector(corner) for item in items for corner in item.bound_box]
    low = Vector([min(corner[axis] for corner in corners) for axis in range(3)])
    high = Vector([max(corner[axis] for corner in corners) for axis in range(3)])
    return low, high


def occlusion_reach(items):
    """How far the ambient occlusion of `items` looks: OCCLUSION_SHARE of their box's diagonal, in metres."""
    low, high = box_of(items)
    return OCCLUSION_SHARE * (high - low).length


def unwrap(item):
    """The piece's faces laid flat on its own `bake` UV map (made the one the game reads), leaving any `content` map
    (a label's or a screen's picture) as it is."""
    layers = item.data.uv_layers
    layer = layers.get("bake") or layers.new(name="bake")
    layers.active = layer
    layer.active_render = True
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=1.0,
                             scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def visible_area(items, sharp=()):
    return sum(visible_area_of(item, sharp) for item in items)


def visible_area_of(item, sharp=()):
    """The area of the piece's faces, a sharp part's at its larger share."""
    return float(face_weights(item, sharp).sum())


def face_weights(item, sharp=()):
    """Each face's share of the picture set as area: its area, a sharp part's at its larger share."""
    scales = sharp_slots_of(item, sharp)
    return np.array([face.area * scales.get(face.material_index, 1.0) ** 2 for face in item.data.polygons])


def blocks(middles, weights, chosen, count):
    """The faces `chosen` (their numbers) cut into `count` blocks of near-equal weight: the longest side of their box
    cut where the weight on each side is in proportion to the blocks it gets, then each side again. A block is a
    piece of the model in space, so a map holds whole neighbourhoods and its seams are few."""
    if count == 1 or len(chosen) <= 1:
        return [chosen]
    first = count // 2
    points = middles[chosen]
    axis = int(np.argmax(points.max(axis=0) - points.min(axis=0)))
    order = chosen[np.argsort(points[:, axis], kind="stable")]
    running = np.cumsum(weights[order])
    cut = int(np.searchsorted(running, running[-1] * first / count)) + 1
    cut = min(max(cut, 1), len(order) - 1)
    return blocks(middles, weights, order[:cut], first) + blocks(middles, weights, order[cut:], count - first)


def split_into_maps(item, weights, count):
    """The piece's faces cut into `count` maps (blocks), each face's map as its material slot."""
    middles = np.array([face.center[:] for face in item.data.polygons])
    tile = np.zeros(len(middles), dtype=np.int32)
    for number, faces in enumerate(blocks(middles, weights, np.arange(len(middles)), count)):
        tile[faces] = number
    item.data.polygons.foreach_set("material_index", tile)
    item.data.update()
    return tile


def maps_needed(wanted):
    """How many LARGEST picture sets a piece wanting a `wanted` pixel side takes when split."""
    return math.ceil((wanted / LARGEST) ** 2)


def sharp_slots(specs, density):
    """{library name: how many times the set's density its parts are drawn at} of the parts a set at `density` draws
    sharp, from SHARP_FROM up: SHARP_SCALE for those of SHARP_FAMILIES, enough for route.PRINT colour texels a metre,
    or a decal's own `px_per_m` where more (never less), for those carrying decals."""
    if density < SHARP_FROM:
        return {}
    found = {slot: SHARP_SCALE for slot, spec in (specs or {}).items() if spec.get("family") in SHARP_FAMILIES}
    found.update({slot: max(SHARP_SCALE, COLOUR_SHARE * max(route.PRINT, *(decal.get("px_per_m", 0.0)
                                                                         for decal in spec["decals"])) / density)
                  for slot, spec in (specs or {}).items() if spec.get("decals")})
    return found


def sharp_slots_of(item, sharp):
    """{material slot of `item`: its scale} of the slots drawn sharp (their library names in `sharp`)."""
    return {index: sharp[name] for index, name in enumerate(slot_names(item)) if name in sharp}


def sharpen(item, sharp):
    """A sharp part's faces' UV islands scaled up by its slot's scale about their own middle, after the islands were
    evened."""
    slots = sharp_slots_of(item, sharp)
    if not slots:
        return
    mesh = bmesh.new()
    mesh.from_mesh(item.data)
    layer = mesh.loops.layers.uv["bake"]
    for face in mesh.faces:
        if face.material_index in slots:
            middle = sum((loop[layer].uv for loop in face.loops), Vector((0.0, 0.0))) / len(face.loops)
            for loop in face.loops:
                loop[layer].uv = middle + (loop[layer].uv - middle) * slots[face.material_index]
    mesh.to_mesh(item.data)
    mesh.free()


def packed_together(items, side, sharp=()):
    """Every piece's islands at one texel density, packed into the one square."""
    bpy.ops.object.select_all(action="DESELECT")
    for item in items:
        item.select_set(True)
    bpy.context.view_layer.objects.active = items[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    for item in items:
        sharpen(item, sharp)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=2 * MARGIN_PIXELS / side)
    bpy.ops.object.mode_set(mode="OBJECT")


def packed_per_face(items, side):
    """Every face its own island, packed tight into the one square with FACE_MARGIN_PIXELS round each (Blender's
    lightmap pack): for a foliage piece, whose islands under smart_project are single triangles."""
    bpy.ops.object.select_all(action="DESELECT")
    for item in items:
        item.select_set(True)
    bpy.context.view_layer.objects.active = items[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                             PREF_MARGIN_DIV=100.0 * FACE_MARGIN_PIXELS / side)
    bpy.ops.object.mode_set(mode="OBJECT")


def select_map(item, tile, number):
    """Only the faces of map `number` selected, in edit mode, their UVs too."""
    selected = (tile == number)
    bpy.ops.object.mode_set(mode="OBJECT")
    item.data.polygons.foreach_set("select", selected)
    item.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.select_all(action="SELECT")


def packed_maps(item, tile, count, side, sharp=(), per_face=False):
    """A split piece's islands at one texel density over all its maps, each map's packed into its own square:
    evened over the whole piece first, so every map holds the same density; `per_face` as packed_per_face."""
    select_for_bake([item], item)
    if not per_face:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.object.mode_set(mode="OBJECT")
        sharpen(item, sharp)
    for number in range(count):
        select_map(item, tile, number)
        if per_face:
            bpy.ops.uv.lightmap_pack(PREF_CONTEXT="SEL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                                     PREF_MARGIN_DIV=100.0 * FACE_MARGIN_PIXELS / side)
        else:
            bpy.ops.uv.pack_islands(rotate=True, margin=2 * MARGIN_PIXELS / side)
    bpy.ops.object.mode_set(mode="OBJECT")


def seam_lines(dark, found):
    """Where `dark` (side x side bool) runs thin and long between lighter sides (SEAM_LENGTH, SEAM_ALONG and
    SEAM_ACROSS along one of four ways, `found`'s occlusion SEAM_REACH across on both sides lighter by SEAM_DARK),
    grown a texel and held to `dark`: a seam, never a pinhole's dot or a hole's blot or its rim."""
    shade = dark.astype(np.float32)
    half = SEAM_LENGTH // 2
    lines = np.zeros(dark.shape, dtype=bool)
    for row, column in ((0, 1), (1, 0), (1, 1), (1, -1)):
        along = sum(np.roll(shade, (row * step, column * step), (0, 1)) for step in range(-half, half + 1))
        across = sum(np.roll(shade, (column * step, -row * step), (0, 1)) for step in range(-4, 5))
        sides = [np.roll(found, (column * step, -row * step), (0, 1)) * SEAM_DARK >= found
                 for step in (-SEAM_REACH, SEAM_REACH)]
        lines |= (along >= SEAM_ALONG * (2 * half + 1)) & (across <= SEAM_ACROSS) & sides[0] & sides[1]
    grown = lines.copy()
    for step in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        grown |= np.roll(lines, step, (0, 1))
    return grown & dark


def seam_shade(found):
    """Each texel's shade from the seams in `found` (side x side: the decoded mesh's occlusion): its ratio to its mean
    within SEAM_REACH texels each way, held to SEAM_LEAST and 1, on seam_lines' texels; 1 everywhere else."""
    padded = np.pad(found, SEAM_REACH, mode="edge")
    width = 2 * SEAM_REACH + 1
    total = sum(padded[row:row + found.shape[0], column:column + found.shape[1]]
                for row in range(width) for column in range(width))
    ratio = np.clip(found / np.maximum(total / width ** 2, 1e-3), SEAM_LEAST, 1.0)
    return np.where(seam_lines(ratio <= SEAM_DARK, found), ratio, 1.0)


def outward(item):
    """The mesh's faces wound one way, outward (Blender's own), so a flipped patch reads open, not shut."""
    select_for_bake([item], item)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def seamed(items, decoded, uv_map, side, reach, among=()):
    """`items`' own ambient occlusion (`occlusion`, `among` the model's other meshes shading them too) darkened in the
    seams their decoded mesh `decoded` holds (the mesh TRELLIS.2 decoded before its remesh closed them,
    generate.decoded_path; #159): its occlusion baked across from it onto the same `uv_map` (`occlusion`'s `source`, a
    texel its rays miss left open) from a cage SEAM_CAGE of the whole model's longest side out, kept on its thin long
    dark runs (seam_shade). The geometry's alone, as `occlusion` is; `decoded` is never drawn."""
    own = occlusion(items, uv_map, side, reach, among=among)
    outward(decoded)
    low, high = box_of([*items, *among])
    lines = occlusion(items, uv_map, side, reach, source=decoded, cage=SEAM_CAGE * max(high - low))
    width, height = own.size
    pixels = np.asarray(own.pixels[:], dtype=np.float32).reshape(height, width, 4)
    found = np.asarray(lines.pixels[:], dtype=np.float32).reshape(height, width, 4)[..., 0]
    pixels[..., :3] *= seam_shade(found)[..., None]
    own.pixels[:] = pixels.ravel()
    own.update()
    bpy.data.images.remove(lines)
    return own


def occlusion(items, uv_map, side, reach, source=None, cage=0.0, among=()):
    """The ambient occlusion of `items` (a generated model's full meshes) from their own shape alone, baked by Cycles
    on their `uv_map` ("" the active one; the texel masks' UVs, make_chunky.TEXELS_UV) into a new Non-Color picture
    `side` square (or `side` [width, height]: a place's map, #209), rays reaching `reach` metres, every other mesh of
    the scene out of the bake but those `among` (the model's other parts, which shade these where a place bakes a part
    alone, #209) (#206: tc6w2's anesthesia machine drawn one flat white where NVIDIA's shades into every seam, drawer
    line and corner). Never the take's own texture: the shading comes from the geometry. The scene's samples, its
    world's reach and each material are as they were after. With a `source` mesh, its occlusion is baked across onto
    `items` instead (selected to active, from a cage `cage` metres out), a texel no ray of it meets left white."""
    scene = bpy.context.scene
    picture = new_picture("occlusion", side, False)
    picture.generated_color = (1.0, 1.0, 1.0, 1.0)
    others = [item for item in scene.objects if item.type == "MESH" and item not in items and item is not source
              and (source is not None or item not in among) and not item.hide_render]
    for item in items:
        if not item.data.materials:
            item.data.materials.append(bpy.data.materials.new("occlusion"))
    materials = {material for item in items for material in item.data.materials if material is not None}
    for material in materials:
        material.use_nodes = True
    nodes = [(material, with_target(material, picture).node_tree.nodes.active) for material in materials]
    if scene.world is None:
        scene.world = bpy.data.worlds.new("occlusion")
    held = scene.cycles.samples, scene.world.light_settings.distance
    scene.cycles.samples, scene.world.light_settings.distance = OCCLUSION_SAMPLES, reach
    for item in others:
        item.hide_render = True
    try:
        if source is None:
            select_for_bake(items, items[0])
            bpy.ops.object.bake(type="AO", margin=MARGIN_PIXELS, use_clear=True, uv_layer=uv_map)
        else:
            for item in items:
                select_for_bake([source, item], item)
                bpy.ops.object.bake(type="AO", margin=MARGIN_PIXELS, use_clear=False, uv_layer=uv_map,
                                    use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=2 * cage)
    finally:
        scene.cycles.samples, scene.world.light_settings.distance = held
        for item in others:
            item.hide_render = False
        for material, node in nodes:
            material.node_tree.nodes.remove(node)
    return picture


def new_picture(name, side, colour_data):
    """A new picture `side` square, or `side` [width, height]."""
    width, height = side if isinstance(side, (list, tuple)) else (side, side)
    picture = bpy.data.images.new(name, width, height, alpha=False, float_buffer=False)
    picture.colorspace_settings.name = "sRGB" if colour_data else "Non-Color"
    return picture


def with_target(material, picture):
    """A material with `picture` as its active image node, the bake's target."""
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = picture
    material.node_tree.nodes.active = node
    return material


def channel_materials(found_by_slot, channel):
    """Per slot, its recipe's channel given off as light."""
    return [recipes.emitted(getattr(found, channel)).item() for found in found_by_slot]


def shaded_materials(found_by_slot):
    return [bumped(recipes.shaded(channels).item()) for channels in found_by_slot]


def bumped(material):
    """The material with its displacement drawn as bump."""
    material.displacement_method = "BUMP"
    return material


def slot_names(item):
    return [material.name.split(".")[0] for material in item.data.materials]


def select_for_bake(selected, active):
    bpy.ops.object.select_all(action="DESELECT")
    for item in selected:
        item.select_set(True)
    bpy.context.view_layer.objects.active = active


def face_pairs(mesh):
    """The pairs of faces that share an edge (an edge of exactly two faces), as two index arrays."""
    loop_edges = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("edge_index", loop_edges)
    totals = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get("loop_total", totals)
    loop_faces = np.repeat(np.arange(len(mesh.polygons)), totals)
    order = np.argsort(loop_edges, kind="stable")
    counts = np.bincount(loop_edges, minlength=len(mesh.edges))
    starts = np.cumsum(counts) - counts
    shared = shared_edges(mesh)
    return loop_faces[order][starts[shared]], loop_faces[order][starts[shared] + 1]


def shared_edges(mesh):
    """The edges of exactly two faces, in edge order (face_pairs lists their faces in the same order)."""
    loop_edges = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("edge_index", loop_edges)
    return np.flatnonzero(np.bincount(loop_edges, minlength=len(mesh.edges)) == 2)


def smoothing_rounds(areas):
    """How many rounds of smoothing between neighbours spread a face's normal about SMOOTH_REACH: a round reaches
    about one face further, and the reach grows with the square root of the rounds."""
    spacing = math.sqrt(float(areas.mean()))
    return int(min(SMOOTH_ROUNDS_MOST, max(1, round((SMOOTH_REACH / max(spacing, 1e-9)) ** 2))))


def smoothed_normals(normals, areas, pairs, rounds):
    """Face normals smoothed between edge neighbours, each round every face taking the area-weighted mean of itself
    and its neighbours, a neighbour weighing less as their normals part and nothing from SMOOTH_CREASE on."""
    first, second = pairs
    floor = math.cos(SMOOTH_CREASE)
    current = normals.copy()
    for _ in range(rounds):
        agree = np.einsum("ij,ij->i", current[first], current[second])
        weight = np.clip((agree - floor) / (1.0 - floor), 0.0, 1.0) ** 2
        total = current * areas[:, None]
        for axis in range(3):
            total[:, axis] += np.bincount(first, weights=current[second, axis] * areas[second] * weight,
                                          minlength=len(current))
            total[:, axis] += np.bincount(second, weights=current[first, axis] * areas[first] * weight,
                                          minlength=len(current))
        current = total / np.maximum(np.linalg.norm(total, axis=1, keepdims=True), 1e-12)
    return current


def smoothly_shaded(high, specs):
    """The full model shaded by its normals smoothed over SMOOTH_REACH (smoothed_normals), as custom normals, on every
    face but those of a finish whose own surface is lumpy (OWN_LUMPS), which stay flat. Blender keeps one custom normal
    for the corners a smooth vertex joins, so the face normals given become a smooth field over the vertices."""
    mesh = high.data
    count = len(mesh.polygons)
    normals = np.empty(count * 3)
    mesh.polygons.foreach_get("normal", normals)
    normals = normals.reshape(count, 3)
    areas = np.empty(count)
    mesh.polygons.foreach_get("area", areas)
    slots = np.empty(count, dtype=np.int64)
    mesh.polygons.foreach_get("material_index", slots)
    lumpy = np.array([specs[name].get("recipe") in OWN_LUMPS for name in slot_names(high)] or [False])
    smoothed = smoothed_normals(normals, areas, face_pairs(mesh), smoothing_rounds(areas))
    shading = np.where(lumpy[slots][:, None], normals, smoothed)
    totals = np.empty(count, dtype=np.int64)
    mesh.polygons.foreach_get("loop_total", totals)
    mesh.polygons.foreach_set("use_smooth", ~lumpy[slots])  # a lumpy finish's faces stay flat, each its own normal
    mesh.normals_split_custom_set(np.repeat(shading, totals, axis=0).tolist())
    mesh.update()


CHANNELS = (("base_color", True), ("roughness", False), ("metallic", False))
# A glass's alpha (recipes.Channels.alpha, its opacity) baked as one more channel where a piece's slots let light
# through (recipes.seen_through), into its base colour's alpha (`finish`), the glTF's material blended: drawn
# opaque, every glass a prop shipped was a flat panel (the tc4r fridge's door, #186).
ALPHA = "alpha"


class Atlas:
    """One shared picture set for a list of pieces: their UVs packed together at one texel density; a split piece's
    several sets (`sets`, one a map)."""

    def __init__(self, name, items, density, specs=None, one_piece=False, per_face=False, split=False):
        """`one_piece`: the set is a single piece; past the cap it takes the density that fits and says so
        (`self.capped`, which make_chunky reports); a shared set too, up to CAP_SLACK past the cap; further past, it
        stops. `split`: a single generated piece past the cap is cut into maps at SPLIT_DENSITY instead (up to
        MOST_MAPS; past them it is capped as above). `per_face`: every face packed as its own island
        (packed_per_face; a piece's data asks it, `per_face` in its bake entry), its faces neither shrunk nor
        sharpened."""
        self.name = name
        for item in items:
            unwrap(item)
        sharp = sharp_slots(specs, density)
        area = visible_area(items, sharp)
        wanted = math.sqrt(area / UV_FILL) * density
        self.capped = None
        self.maps = 1
        if wanted > LARGEST and split and one_piece:
            density = SPLIT_DENSITY
            sharp = sharp_slots(specs, density)
            weights = face_weights(items[0], sharp)
            wanted = math.sqrt(weights.sum() / UV_FILL) * density
            self.maps = min(MOST_MAPS, maps_needed(wanted))
            wanted = self.held(wanted / math.sqrt(self.maps), density, weights.sum())
        elif wanted > LARGEST and (one_piece or wanted <= LARGEST * CAP_SLACK):
            wanted = self.held(wanted, density, area)
        elif wanted > LARGEST:
            # Capped silently, round three's furniture got about 200 texels a metre for the 512 its colour asked
            # (the detail-loss diagnosis, 2026-10-07): a job that cannot hold its density stops and says so.
            raise SystemExit(f"{name}: {area:.1f} m2 at {density} texels a metre needs a {wanted:.0f} px side, past "
                             f"the {LARGEST} cap (density {density * LARGEST / wanted:.0f}); split the job "
                             "(route.py splits shared sets by their pieces' boxes)")
        self.side = int(max(SMALLEST, 2 ** math.ceil(math.log2(wanted))))
        if self.maps > 1:
            self.tile = split_into_maps(items[0], weights, self.maps)
            packed_maps(items[0], self.tile, self.maps, self.side, sharp, per_face)
            print(f"SPLIT {name}: {weights.sum():.1f} m2 into {self.maps} maps of {self.side} at {density} texels a "
                  f"metre", flush=True)
        elif per_face:
            packed_per_face(items, self.side)
        else:
            packed_together(items, self.side, sharp)
        half = max(SMALLEST // 2, self.side // 2)
        self.sets = [self.picture_set(self.map_name(number), half) for number in range(self.maps)]
        self.first = {channel: True for channel in self.sets[0]}
        self.metal_roughness = [None] * self.maps
        self.through = False  # whether a slot let light through: its alpha baked (`_through`)

    def held(self, wanted, density, area):
        """A side past LARGEST held to it: the density that fits (`self.capped`), reported."""
        if wanted <= LARGEST:
            return wanted
        self.capped = round(density * LARGEST / wanted)
        print(f"CAPPED {self.name}: {area:.1f} m2 holds {self.capped} texels a metre of the {density} asked over "
              f"{self.maps} maps", flush=True)
        return LARGEST

    def laid_maps(self, item):
        """A split piece's faces given their maps' material slots again (clearing a mesh's materials sets every face's
        slot back to the first)."""
        if self.maps > 1:
            item.data.polygons.foreach_set("material_index", self.tile)
            item.data.update()

    def map_name(self, number):
        """A map's picture names' stem: the piece's own name for a single set, `<name>_map<n>` for a split piece's."""
        return self.name if self.maps == 1 else f"{self.name}_map{number + 1}"

    def picture_set(self, stem, half):
        """One map's pictures: base colour, roughness and metal at `half` a side, the normal map at the full side."""
        pictures = {channel: new_picture(f"{stem}_{channel}", half, colour) for channel, colour in CHANNELS}
        pictures["normal"] = new_picture(f"{stem}_normal", self.side, False)
        return pictures

    @property
    def pictures(self):
        """The first map's pictures (a code-built piece's set, which is never split)."""
        return self.sets[0]

    def _bake(self, channel, kind, **across):
        bpy.ops.object.bake(type=kind, margin=MARGIN_PIXELS, use_clear=self.first[channel], normal_space="TANGENT",
                            **across)
        self.first[channel] = False

    def bake_self(self, item, specs, wear, dirt, seed, foot=None):
        """A piece's own surfaces, each slot's recipe, into the shared pictures; `foot`: how high its foot stands
        over its floor (the kick wear's)."""
        found_by_slot = [recipes.channels(specs[name], wear, dirt, seed, foot) for name in slot_names(item)]
        select_for_bake([item], item)
        for channel in self._through(found_by_slot):
            for index, material in enumerate(channel_materials(found_by_slot, channel)):
                item.data.materials[index] = with_target(material, self.pictures[channel])
            self._bake(channel, "EMIT")
        for index, material in enumerate(shaded_materials(found_by_slot)):
            item.data.materials[index] = with_target(material, self.pictures["normal"])
        self._bake("normal", "NORMAL")

    def bake_from(self, high, low, specs, wear, dirt, seed, reach, foot=None, masks=None, occluded=None):
        """A generated piece: its library materials worked out on the full-detail model `high` (so wear follows its
        real edges, its lumps smoothed: smoothly_shaded) and baked onto `low`'s place in the shared pictures, each map's
        faces into its own set (Blender bakes a face into its material's active picture). `masks` (the paint's texel
        masks, [(surface, its mask picture)] base first: make_chunky.texel_masks): every slot of those surfaces drawn
        as one material, each surface's recipe mixed in by its mask on the model's own UVs (recipes.masked), so a
        border is the texture's colour edge, not the triangles' (#182); any other slot its own. `occluded` (the full
        model's own ambient occlusion on the masks' UVs, `occlusion`) darkens those masked surfaces' base colour
        (#206)."""
        smoothly_shaded(high, specs)
        found_by_slot = [recipes.channels(specs[name], wear, dirt, seed, foot) for name in slot_names(high)]
        masked = [(path, recipes.channels(specs[name], wear, dirt, seed, foot)) for name, path in masks or ()]
        mixed = [name in dict(masks or ()) for name in slot_names(high)]
        targets = []
        for number in range(self.maps):
            target_name = "bake_target" if self.maps == 1 else f"bake_target_{number + 1}"
            target = bpy.data.materials.get(target_name) or bpy.data.materials.new(target_name)
            target.use_nodes = True
            targets.append(target)
        low.data.materials.clear()
        for target in targets:
            low.data.materials.append(target)
        self.laid_maps(low)
        select_for_bake([high, low], low)
        across = {"use_selected_to_active": True, "cage_extrusion": reach, "max_ray_distance": reach * 2}
        for channel in self._through(found_by_slot + [found for _, found in masked]):
            mix = masked and recipes.masked(masked, lambda found: recipes.emitted(getattr(found, channel)),
                                                  relief=False, occlusion=occluded).item()
            for index, material in enumerate(channel_materials(found_by_slot, channel)):
                high.data.materials[index] = mix if mixed[index] else material
            self._bake_maps(targets, channel, "EMIT", across)
        mix = masked and bumped(recipes.masked(masked, recipes.shaded).item())
        for index, material in enumerate(shaded_materials(found_by_slot)):
            high.data.materials[index] = mix if mixed[index] else material
        self._bake_maps(targets, "normal", "NORMAL", across)

    def _through(self, found):
        """The channels to bake for these Channels: CHANNELS, and ALPHA where one lets light through (its picture
        made in every map's set the first time)."""
        if not any(recipes.seen_through(each) for each in found):
            return [channel for channel, _ in CHANNELS]
        if not self.through:  # whole where nothing is baked into it (a piece baked before, the gaps): never cleared
            for number, pictures in enumerate(self.sets):
                pictures[ALPHA] = new_picture(f"{self.map_name(number)}_{ALPHA}", pictures["roughness"].size[0], False)
                pictures[ALPHA].generated_color = (1.0, 1.0, 1.0, 1.0)
            self.first[ALPHA] = False
            self.through = True
        return [channel for channel, _ in CHANNELS] + [ALPHA]

    def _bake_maps(self, targets, channel, kind, across):
        """`channel` baked into every map's picture. One map: one bake, as a shared set always was. A split piece: one
        bake a map, the others' materials on a one-pixel stand-in, so Cycles holds one map's pixels at a time: baked all
        at once, base's dome module (604 m2, 16 maps of 4096) took 25.3 GB, near this PC's 27 GB machine (env1,
        2026-10-27), and the ship's 22 maps would pass it."""
        if self.maps == 1:
            with_target(targets[0], self.sets[0][channel])
            self._bake(channel, kind, **across)
            return
        aside = bpy.data.images.get("bake_aside") or new_picture("bake_aside", 1, False)
        for number, pictures in enumerate(self.sets):
            for other, target in enumerate(targets):
                with_target(target, pictures[channel] if other == number else aside)
            bpy.ops.object.bake(type=kind, margin=MARGIN_PIXELS, use_clear=True, normal_space="TANGENT", **across)
        self.first[channel] = False

    def finish(self):
        """glTF's metal-roughness picture of each map from its baked roughness and metal: roughness in green, metal
        in blue."""
        for number, pictures in enumerate(self.sets):
            side = pictures["roughness"].size[0]
            rough = np.empty(side * side * 4, dtype=np.float32)
            pictures["roughness"].pixels.foreach_get(rough)
            rough = rough.reshape(side, side, 4)
            shine = np.empty(side * side * 4, dtype=np.float32)
            pictures["metallic"].pixels.foreach_get(shine)
            shine = shine.reshape(side, side, 4)
            both = np.ones((side, side, 4), dtype=np.float32)
            both[..., 1] = rough[..., 0]
            both[..., 2] = shine[..., 0]
            self.metal_roughness[number] = new_picture(f"{self.map_name(number)}_metal_roughness", side, False)
            self.metal_roughness[number].pixels.foreach_set(both.ravel())
            if self.through:
                self.with_alpha(number)

    def with_alpha(self, number):
        """A map's base colour given its baked alpha (ALPHA) as a picture with alpha of its own, in its place."""
        pictures = self.sets[number]
        side = pictures["base_color"].size[0]
        colour = np.empty(side * side * 4, dtype=np.float32)
        pictures["base_color"].pixels.foreach_get(colour)
        alpha = np.empty(side * side * 4, dtype=np.float32)
        pictures[ALPHA].pixels.foreach_get(alpha)
        colour = colour.reshape(side, side, 4)
        colour[..., 3] = alpha.reshape(side, side, 4)[..., 0]
        through = bpy.data.images.new(f"{self.map_name(number)}_base_color_alpha", side, side, alpha=True)
        through.colorspace_settings.name = "sRGB"
        through.pixels.foreach_set(colour.ravel())
        pictures["base_color"] = through

    def game_material(self, number=0):
        """The material a map's faces carry: its pictures on one principled surface, wired the way the glTF
        exporter reads them."""
        stem = self.map_name(number)
        material = bpy.data.materials.get(f"{stem}_game")
        if material is not None:
            return material
        material = bpy.data.materials.new(f"{stem}_game")
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        surface = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
        colour = nodes.new("ShaderNodeTexImage")
        colour.image = self.sets[number]["base_color"]
        links.new(colour.outputs["Color"], surface.inputs["Base Color"])
        if self.through:  # the glTF exporter writes alphaMode BLEND for an image's alpha wired to the surface's
            links.new(colour.outputs["Alpha"], surface.inputs["Alpha"])
            material.surface_render_method = "BLENDED"
        packed_node = nodes.new("ShaderNodeTexImage")
        packed_node.image = self.metal_roughness[number]
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(packed_node.outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], surface.inputs["Roughness"])
        links.new(split.outputs["Blue"], surface.inputs["Metallic"])
        bumps = nodes.new("ShaderNodeTexImage")
        bumps.image = self.sets[number]["normal"]
        mapped = nodes.new("ShaderNodeNormalMap")
        mapped.uv_map = "bake"
        links.new(bumps.outputs["Color"], mapped.inputs["Color"])
        links.new(mapped.outputs["Normal"], surface.inputs["Normal"])
        return material

    def export(self, item, folder):
        """The piece as `<folder>/<name>.gltf` with its .bin, the shared pictures written once beside them in
        `textures/` (a split piece: one material and one primitive a map); only its `bake` UV map goes with it."""
        item.data.materials.clear()
        for number in range(self.maps):
            item.data.materials.append(self.game_material(number))
        self.laid_maps(item)
        for name in [layer.name for layer in item.data.uv_layers if layer.name != "bake"]:
            layer = item.data.uv_layers.get(name)
            if layer is not None and not name.startswith("."):
                item.data.uv_layers.remove(layer)
        select_for_bake([item], item)
        folder = pathlib.Path(folder)
        bpy.ops.export_scene.gltf(filepath=str(folder / f"{item.name}.gltf"), export_format="GLTF_SEPARATE",
                                  export_texture_dir="textures", use_selection=True, export_apply=True,
                                  export_yup=True, export_image_format="AUTO", export_materials="EXPORT")
        found = {"triangles": sum(len(face.vertices) - 2 for face in item.data.polygons)}
        return dict(found, maps=self.maps) if self.maps > 1 else found
