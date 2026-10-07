"""Runs inside Blender: bake pieces' library materials into the maps the game draws (base colour, roughness and
metal, normal), several pieces into one shared set of pictures, and write each piece as a .gltf beside them.

    import bake
    atlas = bake.Atlas("hub_slice", [piece, ...], density=512)        # every piece's UVs packed into one square
    atlas.bake_self(piece, specs, wear, dirt, seed)                    # a code-built piece's own surfaces
    atlas.bake_from(high, low, specs, wear, dirt, seed, reach)         # a generated piece, from its full model
    atlas.finish(); atlas.export(piece, folder)

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


def visible_area(items, sharp=()):
    return sum(visible_area_of(item, sharp) for item in items)


def visible_area_of(item, sharp=()):
    """The area of the faces the room sees, a sharp part's at its larger share (the hidden set found once: per face it
    made a 40k-face generated piece take 12 minutes, 2026-10-06)."""
    hidden = hidden_faces(item)
    sharp_slots = sharp_slots_of(item, sharp)
    return sum(face.area * (SHARP_SCALE ** 2 if face.material_index in sharp_slots else 1.0)
               for face in item.data.polygons if face.index not in hidden)


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
        shrink_hidden(item)
        sharpen(item, sharp)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
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


CHANNELS = (("base_color", True), ("roughness", False), ("metallic", False))


class Atlas:
    """One shared picture set for a list of pieces: their UVs packed together at one texel density."""

    def __init__(self, name, items, density, specs=None, one_piece=False):
        """`one_piece`: the set is a single generated piece, which cannot be split: past the cap it takes the density
        that fits and says so (`self.capped`, which make_chunky reports); a shared set too, up to CAP_SLACK past the cap;
        further past, it stops."""
        self.name = name
        sharp = {slot for slot, spec in (specs or {}).items() if spec.get("family") in SHARP_FAMILIES} \
            if density >= SHARP_FROM else set()
        for item in items:
            unwrap(item)
        area = visible_area(items, sharp)
        wanted = math.sqrt(area / UV_FILL) * density
        self.capped = None
        if wanted > LARGEST and (one_piece or wanted <= LARGEST * CAP_SLACK):
            self.capped = round(density * LARGEST / wanted)
            print(f"CAPPED {name}: {area:.1f} m2 holds {self.capped} texels a metre of the {density} asked", flush=True)
            wanted = LARGEST
        elif wanted > LARGEST:
            # Capped silently, round three's furniture got about 200 texels a metre for the 512 its colour asked
            # (the detail-loss diagnosis, 2026-10-07): a job that cannot hold its density stops and says so.
            raise SystemExit(f"{name}: {area:.1f} m2 at {density} texels a metre needs a {wanted:.0f} px side, past "
                             f"the {LARGEST} cap (density {density * LARGEST / wanted:.0f}); split the job "
                             "(route.py splits shared sets by their pieces' boxes)")
        self.side = int(max(SMALLEST, 2 ** math.ceil(math.log2(wanted))))
        packed_together(items, self.side, sharp)
        half = max(SMALLEST // 2, self.side // 2)
        self.pictures = {channel: new_picture(f"{name}_{channel}", half, colour) for channel, colour in CHANNELS}
        self.pictures["normal"] = new_picture(f"{name}_normal", self.side, False)
        self.first = {channel: True for channel in self.pictures}
        self.metal_roughness = None

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
        real edges) and baked onto `low`'s place in the shared pictures."""
        found_by_slot = [recipes.channels(specs[name], wear, dirt, seed, foot) for name in slot_names(high)]
        target = bpy.data.materials.get("bake_target") or bpy.data.materials.new("bake_target")
        target.use_nodes = True
        low.data.materials.clear()
        low.data.materials.append(target)
        select_for_bake([high, low], low)
        across = {"use_selected_to_active": True, "cage_extrusion": reach, "max_ray_distance": reach * 2}
        for channel, _ in CHANNELS:
            for index, material in enumerate(channel_materials(found_by_slot, channel)):
                high.data.materials[index] = material
            with_target(target, self.pictures[channel])
            self._bake(channel, "EMIT", **across)
        for index, material in enumerate(shaded_materials(found_by_slot)):
            high.data.materials[index] = material
        with_target(target, self.pictures["normal"])
        self._bake("normal", "NORMAL", **across)

    def finish(self):
        """glTF's metal-roughness picture from the baked roughness and metal: roughness in green, metal in blue."""
        side = self.pictures["roughness"].size[0]
        rough = np.array(self.pictures["roughness"].pixels[:], dtype=np.float32).reshape(side, side, 4)
        shine = np.array(self.pictures["metallic"].pixels[:], dtype=np.float32).reshape(side, side, 4)
        both = np.ones((side, side, 4), dtype=np.float32)
        both[..., 1] = rough[..., 0]
        both[..., 2] = shine[..., 0]
        self.metal_roughness = new_picture(f"{self.name}_metal_roughness", side, False)
        self.metal_roughness.pixels.foreach_set(both.ravel())

    def game_material(self):
        """The material the pieces carry: the shared pictures on one principled surface, wired the way the glTF
        exporter reads them."""
        material = bpy.data.materials.get(f"{self.name}_game")
        if material is not None:
            return material
        material = bpy.data.materials.new(f"{self.name}_game")
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        surface = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
        colour = nodes.new("ShaderNodeTexImage")
        colour.image = self.pictures["base_color"]
        links.new(colour.outputs["Color"], surface.inputs["Base Color"])
        packed_node = nodes.new("ShaderNodeTexImage")
        packed_node.image = self.metal_roughness
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(packed_node.outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], surface.inputs["Roughness"])
        links.new(split.outputs["Blue"], surface.inputs["Metallic"])
        bumps = nodes.new("ShaderNodeTexImage")
        bumps.image = self.pictures["normal"]
        mapped = nodes.new("ShaderNodeNormalMap")
        mapped.uv_map = "bake"
        links.new(bumps.outputs["Color"], mapped.inputs["Color"])
        links.new(mapped.outputs["Normal"], surface.inputs["Normal"])
        return material

    def export(self, item, folder):
        """The piece as `<folder>/<name>.gltf` with its .bin, the shared pictures written once beside them in
        `textures/`; only its `bake` UV map goes with it."""
        item.data.materials.clear()
        item.data.materials.append(self.game_material())
        for name in [layer.name for layer in item.data.uv_layers if layer.name != "bake"]:
            layer = item.data.uv_layers.get(name)
            if layer is not None and not name.startswith("."):
                item.data.uv_layers.remove(layer)
        select_for_bake([item], item)
        folder = pathlib.Path(folder)
        bpy.ops.export_scene.gltf(filepath=str(folder / f"{item.name}.gltf"), export_format="GLTF_SEPARATE",
                                  export_texture_dir="textures", use_selection=True, export_apply=True,
                                  export_yup=True, export_image_format="AUTO", export_materials="EXPORT")
        return {"triangles": sum(len(face.vertices) - 2 for face in item.data.polygons)}
