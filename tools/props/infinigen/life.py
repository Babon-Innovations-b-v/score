"""What grows and lies on the patch, made by Infinigen's own generators on the rented machine: its scatters (grass,
moss, pebbles, corals, kelp, urchins) on the plan's zones, its assets (shrubs, boulders) on the plan's marked spots,
and one fish with its swim baked into a loop.

Every scatter keeps Infinigen's own numbers except the selection, which is the plan's zone (ground.add_zones).
A spot's kind names a few variants made once and shared by every spot of that kind (linked copies), so the game
instances them as Infinigen instances its scatters.
"""
import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

# The game's word for each zone scatter, and the Infinigen scatter that makes it.
VARIANTS = 4


def scatter(kind, ground, zone):
    """Run one of Infinigen's scatters over the ground, limited to `zone`; the scatter object."""
    from infinigen.assets.scatters import coral_reef, grass, moss, pebbles, seaweed, urchin
    if kind == "grass":
        made = grass.apply(ground, selection=zone)
    elif kind == "moss":
        made = moss.MossCover().apply(ground, selection=zone)
    elif kind == "pebbles":
        made = pebbles.apply(ground, selection=zone)
    elif kind == "rubble":
        made = rubble(ground, zone)
    elif kind == "coral":
        made = coral_reef.apply(ground, selection=zone)
    elif kind == "seaweed":
        made = seaweed.apply(ground, selection=zone)
    elif kind == "urchin":
        made = urchin.apply(ground, selection=zone)
    elif kind == "kelp":
        made = kelp(ground, zone)
    else:
        raise ValueError(f"no scatter for {kind}")
    made = made[0] if isinstance(made, tuple) else made
    made.name = f"scatter-{kind}"
    return made


def kelp(ground, zone):
    """Kelp standing up from the sand: Infinigen's kelp monocot, scattered as its kelp forest scenes do."""
    from infinigen.assets.objects.monocot.kelp import KelpMonocotFactory
    from infinigen.core.placement.factory import make_asset_collection
    from infinigen.core.placement.instance_scatter import scatter_instances
    collection = make_asset_collection(KelpMonocotFactory(np.random.randint(1e5)), name="kelp", n=4)
    return scatter_instances(base_obj=ground, collection=collection, density=0.6, min_spacing=0.8, scale=1.0,
                             scale_rand=0.4, normal=(0, 0, 1), selection=zone)


def rubble(ground, zone):
    """Moon rubble: Infinigen's pebble rocks, kept small (3 to 25 cm) and thinner on the ground than its pebbles,
    since the plan's boulders are placed one by one."""
    from infinigen.assets.objects.rocks.blender_rock import BlenderRockFactory
    from infinigen.core.placement.factory import make_asset_collection
    from infinigen.core.placement.instance_scatter import scatter_instances
    from infinigen.assets.composition import material_assignments
    from infinigen.core.util.random import weighted_sample
    rocks = make_asset_collection(BlenderRockFactory(np.random.randint(1e5), detail=3), name="rubble", n=5)
    weighted_sample(material_assignments.rock)().apply(list(rocks.objects))
    return scatter_instances(base_obj=ground, collection=rocks, vol_density=0.03, ground_offset=0.02,
                             scale=0.12, scale_rand=0.8, scale_rand_axi=0.5, selection=zone, taper_density=True)


def factory_for(kind, seed):
    """The Infinigen factory a spot kind is made by."""
    from infinigen.assets.objects.rocks import BoulderFactory
    from infinigen.assets.objects.trees import BushFactory
    if kind in ("hardy-shrub", "shrub"):
        return BushFactory(seed)
    if kind in ("lichen-boulder", "boulder"):
        return BoulderFactory(seed)
    raise ValueError(f"no Infinigen factory for the spot kind {kind}")


def hierarchy(obj):
    return [obj, *obj.children_recursive]


def realized(obj, name):
    """One plain mesh object holding everything `obj` draws (its children and geometry-node instances), its
    modifiers applied; the original is removed.

    It walks every instance the scene draws, so call it while the scatters are hidden (game_export.scattered) or
    not yet made (patch.py places the spots first): with them, one call walked 6.3 M moss clumps."""
    items = hierarchy(obj)
    names = {item.name for item in items}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    parts = []
    for instance in depsgraph.object_instances:
        source = instance.instance_object if instance.is_instance else instance.object
        owner = instance.parent.original if instance.is_instance and instance.parent else source.original
        if owner.name not in names or source.type != "MESH":
            continue
        mesh = bpy.data.meshes.new_from_object(source if instance.is_instance else source.evaluated_get(depsgraph),
                                               depsgraph=depsgraph)
        mesh.transform(instance.matrix_world.copy())
        parts.append(mesh)
    joined = join_meshes(parts, name)
    for item in items:
        bpy.data.objects.remove(item, do_unlink=True)
    return joined


def join_meshes(meshes, name):
    """Several meshes, already in world space, as one object with their materials kept."""
    import bmesh
    combined = bmesh.new()
    materials = []
    for mesh in meshes:
        offset = len(materials)
        materials += list(mesh.materials)
        part = bmesh.new()
        part.from_mesh(mesh)
        for face in part.faces:
            face.material_index += offset
        temporary = bpy.data.meshes.new("part")
        part.to_mesh(temporary)
        part.free()
        combined.from_mesh(temporary)
        bpy.data.meshes.remove(temporary)
    out = bpy.data.meshes.new(name)
    combined.to_mesh(out)
    combined.free()
    for material in materials:
        out.materials.append(material)
    obj = bpy.data.objects.new(name, out)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def bounds(obj):
    """(lowest corner, highest corner) of a mesh object's vertices in its own space."""
    points = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", points)
    points = points.reshape(-1, 3)
    return points.min(axis=0), points.max(axis=0)


def centred_on_base(obj):
    """Move the mesh so its base's middle is its origin, so a spot puts it on the ground."""
    low, high = bounds(obj)
    middle = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]))
    obj.data.transform(Matrix.Translation(-middle))
    obj.matrix_world = Matrix.Identity(4)


def variants(kind, seed, count=VARIANTS):
    """A few made-once meshes of a spot kind, each a plain object at the origin standing on its base."""
    factory = factory_for(kind, seed)
    made = []
    for index in range(count):
        spawned = factory.spawn_asset(index)
        obj = realized(spawned, f"{kind}-{index}")
        centred_on_base(obj)
        made.append(obj)
    return made


def ground_height(ground_bvh, x, y):
    """The ground's height under (x, y), by a ray down."""
    hit = ground_bvh.ray_cast(Vector((x, y, 1e4)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else 0.0


def place_spots(spots, side, ground_bvh, seed, sink=0.1):
    """Every marked spot as a linked copy of its kind's variants, sized to the spot and set on the ground, sunk
    `sink` of its height so it sits in it; the placed objects."""
    placed, made = [], {}
    for index, spot in enumerate(spots):
        kind = spot["kind"]
        if kind not in made:
            made[kind] = variants(kind, seed + len(made))
            for variant in made[kind]:
                variant.hide_render = True
        variant = made[kind][index % len(made[kind])]
        low, high = bounds(variant)
        across = max(high[0] - low[0], high[1] - low[1], 1e-3)
        tall = high[2] - low[2]
        scale = spot.get("size_m", across) / across
        height_scale = spot["tall_m"] / max(tall, 1e-3) if "tall_m" in spot else scale
        obj = bpy.data.objects.new(f"{kind}-spot-{index}", variant.data)
        bpy.context.scene.collection.objects.link(obj)
        x, y = spot["x"] - side / 2, spot["y"] - side / 2
        z = ground_height(ground_bvh, x, y) - sink * tall * height_scale
        obj.matrix_world = (Matrix.Translation((x, y, z)) @ Euler((0, 0, math.radians(spot.get("turn_deg", 0)))).to_matrix().to_4x4()
                            @ Matrix.Diagonal((scale, scale, height_scale, 1)))
        placed.append(obj)
    return placed


def rigged_fish_factory(seed):
    """Infinigen's FishFactory with its swim rig, its materials put on the rigged body.

    v1.19.0's fish paints its body by looking for meshes directly under the fish's root, but a rigged fish's body
    has been moved under its armature by then, so a fish with a swim fails (IndexError) before any material is on
    it; this finds the body under the armature instead and paints it exactly as Infinigen does."""
    from infinigen.assets.objects.creatures.fish import FishFactory
    from infinigen.assets.objects.creatures.util import joining
    from infinigen.core import surface

    class RiggedFishFactory(FishFactory):
        def apply_materials(self, obj):
            if joining.get_parts(obj):
                return super().apply_materials(obj)
            armature = next(child for child in obj.children if child.type == "ARMATURE")
            body = max((part for part in joining.get_parts(armature)
                        if "Fin" not in part.name and "Eyeball" not in part.name),
                       key=lambda part: len(part.data.vertices))
            surface.assign_material(body, self.body_material())
            gold = body.active_material is not None and "gold" in body.active_material.name.lower()
            self.fin_material.apply(joining.get_parts(obj, False, "Fin"), shader_kwargs={"goldfish": gold})
            self.eye_material.apply(joining.get_parts(obj, False, "Eyeball"))

    return RiggedFishFactory(seed, animation_mode="idle")


def fish(seed):
    """One Infinigen fish with its swim; (root, armature, meshes the armature moves)."""
    root = rigged_fish_factory(seed).spawn_asset(0)
    armature = next(item for item in hierarchy(root) if item.type == "ARMATURE")
    meshes = [item for item in hierarchy(root) if item.type == "MESH"
              and any(modifier.type == "ARMATURE" for modifier in item.modifiers)]
    return root, armature, meshes


def looped_drivers(armature, frames):
    """Rewrite every swim driver's frequency so its period divides `frames`, so the swim loops without a seam.

    Infinigen's swim drivers read `mag*sin((freq*frame+off)/(2*pi))`: a period of (2 pi)^2 / freq frames."""
    import re
    for curve in armature.animation_data.drivers:
        expression = curve.driver.expression
        found = re.match(r"([-\d.]+)\*sin\(\(([-\d.]+)\*frame\+([-\d.]+)\)/\(2\*pi\)\)", expression)
        if not found:
            continue
        magnitude, frequency, offset = map(float, found.groups())
        period = (2 * math.pi) ** 2 / frequency
        cycles = max(1, round(frames / period))
        frequency = (2 * math.pi) ** 2 * cycles / frames
        curve.driver.expression = f"{magnitude:.4f}*sin(({frequency:.6f}*frame+{offset:.4f})/(2*pi))"


def bake_swim(armature, frames):
    """The drivers' swim written as keyframes (frames 0..frames, the last equal to the first), drivers removed."""
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 0, frames
    driven = sorted({curve.data_path.split('"')[1] for curve in armature.animation_data.drivers
                     if curve.data_path.startswith("pose.bones")})
    poses = {}
    for frame in range(frames + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses[frame] = {name: armature.pose.bones[name].rotation_euler.copy() for name in driven}
    for name in driven:
        armature.pose.bones[name].driver_remove("rotation_euler")
    armature.animation_data_create()
    armature.animation_data.action = bpy.data.actions.new("swim")
    for frame, pose in poses.items():
        for name, rotation in pose.items():
            bone = armature.pose.bones[name]
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = rotation
            bone.keyframe_insert("rotation_euler", frame=frame)
    return len(driven)
