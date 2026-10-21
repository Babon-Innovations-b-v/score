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
share one picture set instead of one set each, and each face gets the texels its place needs: a face the room never
sees (a back against the wall, the top of a roof panel) is packed at a twentieth of the density. Base colour and
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
HIDDEN_SHARE = 0.05
# How many times the texel density a printed or screen part's faces get (labels, keypads, notices, screen content):
# read up close, they came out soft at the room's density (the owner, 2026-10-06).
SHARP_SCALE = 3.0
# Only a set drawn near the player gets its print sharp (round six: the high status display's screen alone, at three
# times a far set's density, needed a 4096 picture set and put the hub past its room budget).
SHARP_FROM = 1024
# The library families whose parts are drawn sharp.
SHARP_FAMILIES = ("print", "screen")
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
OWN_LUMPS = ("cast_metal", "rubber", "quilted")
SMOOTH_REACH = 0.03
# Neighbouring faces whose smoothed normals part by SMOOTH_CREASE or more do not smooth into each other: a real edge
# stays sharp, so its wear stays on it.
SMOOTH_CREASE = math.radians(35.0)
SMOOTH_ROUNDS_MOST = 200


def hidden_faces(item):
    """Faces the room never sees: those facing the kit frame's back (+z, Blender -y), against a wall or a roof."""
    return {face.index for face in item.data.polygons if face.normal.dot(Vector((0.0, -1.0, 0.0))) > 0.9}


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


def shrink_hidden(item):
    """Hidden faces' UV islands scaled down about their own middle."""
    hidden = hidden_faces(item)
    if not hidden:
        return
    mesh = bmesh.new()
    mesh.from_mesh(item.data)
    layer = mesh.loops.layers.uv["bake"]
    for face in mesh.faces:
        if face.index in hidden:
            middle = sum((loop[layer].uv for loop in face.loops), Vector((0.0, 0.0))) / len(face.loops)
            for loop in face.loops:
                loop[layer].uv = middle + (loop[layer].uv - middle) * HIDDEN_SHARE
    mesh.to_mesh(item.data)
    mesh.free()


def visible_area(items, sharp=(), backs_hidden=True):
    return sum(visible_area_of(item, sharp, backs_hidden) for item in items)


def visible_area_of(item, sharp=(), backs_hidden=True):
    """The area of the faces the room sees, a sharp part's at its larger share."""
    return float(face_weights(item, sharp, backs_hidden).sum())


def face_weights(item, sharp=(), backs_hidden=True):
    """Each face's share of the picture set as area: its area, a sharp part's at its larger share, a hidden face's 0
    (the hidden set found once: per face it made a 40k-face generated piece take 12 minutes, 2026-10-06)."""
    hidden = hidden_faces(item) if backs_hidden else set()
    sharp_slots = sharp_slots_of(item, sharp)
    return np.array([0.0 if face.index in hidden else
                     face.area * (SHARP_SCALE ** 2 if face.material_index in sharp_slots else 1.0)
                     for face in item.data.polygons])


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
    """The library names whose parts a set at `density` draws sharp: those of SHARP_FAMILIES, from SHARP_FROM up."""
    if density < SHARP_FROM:
        return set()
    return {slot for slot, spec in (specs or {}).items() if spec.get("family") in SHARP_FAMILIES}


def sharp_slots_of(item, sharp):
    """The material slots of `item` that are drawn sharp (their library names in `sharp`)."""
    return {index for index, name in enumerate(slot_names(item)) if name in sharp}


def sharpen(item, sharp):
    """A sharp part's faces' UV islands scaled up SHARP_SCALE about their own middle, after the islands were evened."""
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
                loop[layer].uv = middle + (loop[layer].uv - middle) * SHARP_SCALE
    mesh.to_mesh(item.data)
    mesh.free()


def packed_together(items, side, sharp=(), backs_hidden=True):
    """Every piece's islands at one texel density, packed into the one square; with `backs_hidden`, the faces facing
    the kit's back shrunk (shrink_hidden)."""
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
        if backs_hidden:
            shrink_hidden(item)
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


def new_picture(name, side, colour_data):
    picture = bpy.data.images.new(name, side, side, alpha=False, float_buffer=False)
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
    found = []
    for channels in found_by_slot:
        material = recipes.shaded(channels).item()
        material.displacement_method = "BUMP"
        found.append(material)
    return found


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


class Atlas:
    """One shared picture set for a list of pieces: their UVs packed together at one texel density; a split piece's
    several sets (`sets`, one a map)."""

    def __init__(self, name, items, density, specs=None, one_piece=False, backs_hidden=True, per_face=False,
                 split=False):
        """`one_piece`: the set is a single piece; past the cap it takes the density that fits and says so
        (`self.capped`, which make_chunky reports); a shared set too, up to CAP_SLACK past the cap; further past, it
        stops. `split`: a single generated piece past the cap is cut into maps at SPLIT_DENSITY instead (up to
        MOST_MAPS; past them it is capped as above). `backs_hidden`: the faces facing the kit's back are shrunk
        (shrink_hidden); a generated piece passes False: shrunk face by face, its small remeshed triangles fell under
        a texel and baked black, and a chair, a desk or a lander shows its back (job paint, 2026-10-08: every
        generated piece's back was 35 to 100% black). `per_face`: every face packed as its own island
        (packed_per_face; a piece's data asks it, `per_face` in its bake entry), its faces neither shrunk nor
        sharpened."""
        self.name = name
        for item in items:
            unwrap(item)
        sharp = sharp_slots(specs, density)
        area = visible_area(items, sharp, backs_hidden)
        wanted = math.sqrt(area / UV_FILL) * density
        self.capped = None
        self.maps = 1
        if wanted > LARGEST and split and one_piece:
            density = SPLIT_DENSITY
            sharp = sharp_slots(specs, density)
            weights = face_weights(items[0], sharp, backs_hidden)
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
            packed_together(items, self.side, sharp, backs_hidden)
        half = max(SMALLEST // 2, self.side // 2)
        self.sets = [self.picture_set(self.map_name(number), half) for number in range(self.maps)]
        self.first = {channel: True for channel in self.sets[0]}
        self.metal_roughness = [None] * self.maps

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
        for channel, _ in CHANNELS:
            for index, material in enumerate(channel_materials(found_by_slot, channel)):
                item.data.materials[index] = with_target(material, self.pictures[channel])
            self._bake(channel, "EMIT")
        for index, material in enumerate(shaded_materials(found_by_slot)):
            item.data.materials[index] = with_target(material, self.pictures["normal"])
        self._bake("normal", "NORMAL")

    def bake_from(self, high, low, specs, wear, dirt, seed, reach, foot=None):
        """A generated piece: its library materials worked out on the full-detail model `high` (so wear follows its
        real edges, its lumps smoothed: smoothly_shaded) and baked onto `low`'s place in the shared pictures, each map's
        faces into its own set (Blender bakes a face into its material's active picture)."""
        smoothly_shaded(high, specs)
        found_by_slot = [recipes.channels(specs[name], wear, dirt, seed, foot) for name in slot_names(high)]
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
        for channel, _ in CHANNELS:
            for index, material in enumerate(channel_materials(found_by_slot, channel)):
                high.data.materials[index] = material
            for target, pictures in zip(targets, self.sets):
                with_target(target, pictures[channel])
            self._bake(channel, "EMIT", **across)
        for index, material in enumerate(shaded_materials(found_by_slot)):
            high.data.materials[index] = material
        for target, pictures in zip(targets, self.sets):
            with_target(target, pictures["normal"])
        self._bake("normal", "NORMAL", **across)

    def finish(self):
        """glTF's metal-roughness picture of each map from its baked roughness and metal: roughness in green, metal
        in blue."""
        for number, pictures in enumerate(self.sets):
            side = pictures["roughness"].size[0]
            rough = np.array(pictures["roughness"].pixels[:], dtype=np.float32).reshape(side, side, 4)
            shine = np.array(pictures["metallic"].pixels[:], dtype=np.float32).reshape(side, side, 4)
            both = np.ones((side, side, 4), dtype=np.float32)
            both[..., 1] = rough[..., 0]
            both[..., 2] = shine[..., 0]
            self.metal_roughness[number] = new_picture(f"{self.map_name(number)}_metal_roughness", side, False)
            self.metal_roughness[number].pixels.foreach_set(both.ravel())

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
