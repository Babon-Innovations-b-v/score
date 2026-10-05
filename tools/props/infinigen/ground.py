"""The patch's ground on the rented machine: a height-field mesh from the plan, or for the Moon the crater element
meshed by Infinigen's own mesher; the zones as attributes Infinigen's scatters select by; the materials.

Coordinates: Blender metres, z up, the patch's middle at the origin; the plan's metres are (x - side/2, y - side/2).
"""
import bpy
import numpy as np

import crater


def patch_metres(points, side):
    """Blender points (n x 3) as the plan's metres from the patch's south-west corner (x east, y north)."""
    return points[:, 0] + side / 2, points[:, 1] + side / 2


def sample(field, side, x, y):
    """A plan grid (row 0 north, x east) read at plan metres, bilinear."""
    rows, cols = field.shape
    column = np.clip(x / side * (cols - 1), 0, cols - 1)
    row = np.clip((side - y) / side * (rows - 1), 0, rows - 1)
    left, top = np.floor(column).astype(int), np.floor(row).astype(int)
    right, bottom = np.minimum(left + 1, cols - 1), np.minimum(top + 1, rows - 1)
    across, down = column - left, row - top
    upper = field[top, left] * (1 - across) + field[top, right] * across
    lower = field[bottom, left] * (1 - across) + field[bottom, right] * across
    return upper * (1 - down) + lower * down


def grid_object(name, side, cell, height_of):
    """A square grid mesh over the patch, `cell` metres apart, z from `height_of(x, y)` (plan metres), with UVs
    spanning the patch once."""
    count = int(round(side / cell)) + 1
    across = np.linspace(-side / 2, side / 2, count)
    east, north = np.meshgrid(across, across)
    x, y = east.ravel() + side / 2, north.ravel() + side / 2
    points = np.stack([east.ravel(), north.ravel(), height_of(x, y)], axis=1).astype(np.float32)
    corner = (np.arange(count - 1)[None, :] + np.arange(count - 1)[:, None] * count).ravel()
    quads = np.stack([corner, corner + 1, corner + count + 1, corner + count], axis=1)
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(points))
    mesh.vertices.foreach_set("co", points.ravel())
    mesh.loops.add(quads.size)
    mesh.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
    mesh.polygons.add(len(quads))
    mesh.polygons.foreach_set("loop_start", np.arange(0, quads.size, 4, dtype=np.int32))
    mesh.polygons.foreach_set("loop_total", np.full(len(quads), 4, dtype=np.int32))
    uv = mesh.uv_layers.new(name="UVMap")
    corners = points[quads.ravel(), :2] / side + 0.5
    uv.data.foreach_set("uv", corners.ravel())
    mesh.update(calc_edges=True)
    mesh.validate()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def heightfield(heights, side, cell, name="ground"):
    """The plan's heights as a grid mesh."""
    return grid_object(name, side, cell, lambda x, y: sample(heights, side, x, y))


def add_zones(obj, zones, side):
    """Each zone mask as a 0/1 point attribute named after it, read by Infinigen's scatters as their selection."""
    points = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", points)
    x, y = patch_metres(points.reshape(-1, 3), side)
    for name in zones.files:
        attribute = obj.data.attributes.new(name, "FLOAT", "POINT")
        attribute.data.foreach_set("value", sample(zones[name].astype(np.float64), side, x, y).round().astype(np.float32))


class CraterGround:
    """A new Infinigen terrain element: Infinigen's own Ground (Perlin relief, compiled) with the plan's craters and
    slope added to its signed distance. It answers the meshers the way every Infinigen element does: called with
    points, it gives their signed distances and material weights. With `spherical_radius` it puts its craters on a
    small round world (Ground then measures altitude from the world's middle too)."""

    def __init__(self, spec, spherical_radius=-1.0):
        from infinigen.core.util.organization import ElementNames, Materials, Transparency
        from infinigen.terrain.elements.ground import Ground
        self.inner = Ground("cpu", None, spherical_radius=spherical_radius, freq=0.08, octaves=6, scale=0.35)
        self.name = ElementNames.Ground
        self.material, self.transparency, self.tag = Materials.GroundCollection, Transparency.Opaque, self.inner.tag
        self.attributes, self.displacement = self.inner.attributes, []
        self.side, self.craters, self.plane = spec["side_m"], spec["craters"], spec.get("plane", {})
        self.spherical_radius = spherical_radius
        self.rng_seed = spec["seed"]

    def bumps(self, points):
        """The ejecta's lumpy ground, -1 to 1, smooth and the same for the same point: crater.lumps over x and y."""
        return crater.lumps(points[:, :2], self.rng_seed)

    def __call__(self, positions, sdf_only=False):
        from infinigen.terrain.utils.kernelizer_util import Vars
        answer = self.inner(positions, sdf_only)
        if self.spherical_radius > 0:
            added = crater.lift(positions, self.craters, self.bumps(positions), self.spherical_radius)
        else:
            x, y = patch_metres(positions, self.side)
            local = np.stack([x, y, positions[:, 2]], axis=1)
            added = crater.lift(local, self.craters, self.bumps(positions))
            added += self.plane.get("base_m", 0) + self.plane.get("rise_east", 0) * x + \
                self.plane.get("rise_north", 0) * y
        answer[Vars.SDF] = (answer[Vars.SDF] - added).astype(np.float32)
        return answer

    def cleanup(self):
        self.inner.cleanup()


def crater_ground(spec, truth, voxel=0.12):
    """The Moon patch's ground: the crater element meshed by Infinigen's UniformMesher over the patch."""
    from infinigen.terrain.mesher.uniform_mesher import UniformMesher
    side = spec["side_m"]
    low, high = float(truth.min()) - 4, float(truth.max()) + 4
    divisions = int(side / (voxel * 3))
    mesher = UniformMesher((-side / 2, side / 2, -side / 2, side / 2, low, high), subdivisions=(divisions, -1, -1),
                           upscale=3)
    element = CraterGround(spec)
    mesh = mesher([element])
    obj = mesh.export_blender("ground")
    obj.data.polygons.foreach_set("use_smooth", np.ones(len(obj.data.polygons), dtype=bool))
    return obj, element


def principled(name, colour, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Roughness"].default_value = roughness
    return material, shader


def regolith():
    """Grey Moon dust: dark grey, a little mottled, fully rough, with a fine bump; Infinigen has no Moon material."""
    material, shader = principled("regolith", (0.16, 0.16, 0.155), 0.97)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.5
    noise.inputs["Detail"].default_value = 8
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.10, 1)
    ramp.color_ramp.elements[1].color = (0.22, 0.22, 0.215, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    fine = nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 60
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    links.new(fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def greyed(obj, value=1.0):
    """Turn an object's materials grey (the Moon has no colour): a saturation-0 step before each base colour."""
    for slot in obj.material_slots:
        if slot.material is None or not slot.material.use_nodes:
            continue
        tree = slot.material.node_tree
        for shader in [node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"]:
            source = shader.inputs["Base Color"]
            grey = tree.nodes.new("ShaderNodeHueSaturation")
            grey.inputs["Saturation"].default_value = 0.0
            grey.inputs["Value"].default_value = value
            if source.is_linked:
                tree.links.new(source.links[0].from_socket, grey.inputs["Color"])
            else:
                grey.inputs["Color"].default_value = source.default_value
            tree.links.new(grey.outputs["Color"], source)


def tinted(obj, hue):
    """Set every colour-ramp stop in an object's materials to `hue` (0 to 1 round the colour wheel), keeping each
    stop's saturation and brightness: how the plan's colour steers a scatter whose palette Infinigen draws at
    random (its grass came out golden on one seed and pink on the next)."""
    import colorsys
    for slot in obj.material_slots:
        if slot.material is None or not slot.material.use_nodes:
            continue
        for ramp in [node for node in slot.material.node_tree.nodes if node.type == "VALTORGB"]:
            for stop in ramp.color_ramp.elements:
                _, saturation, value = colorsys.rgb_to_hsv(*stop.color[:3])
                stop.color = (*colorsys.hsv_to_rgb(hue, saturation, value), stop.color[3])


def infinigen_material(obj, dotted_name):
    """Apply one of Infinigen's terrain materials (e.g. infinigen.assets.materials.terrain.Dirt) to the object,
    shader and its displacement."""
    import importlib
    module_name, class_name = dotted_name.rsplit(".", 1)
    generator = getattr(importlib.import_module(module_name), class_name)
    made = generator() if isinstance(generator, type) else generator
    made.apply(obj)
