"""Make one Infinigen job on the rented machine: the patch (or the fish) as Infinigen builds it, a picture of it at
eye height in Infinigen's renderer, and the game's version of it (game_export.py). Run by cloud/infinigen.py from
Infinigen's folder under its own Python; never on the owner's PC.

    cd /root/infinigen && /root/venv/bin/python <repo>/tools/props/infinigen/patch.py <spec.json> <out folder>

Writes into the out folder: infinigen.png (the render), the game files, stats.json, and timings.json (seconds a step).
"""
import json
import math
import os
import pathlib
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import game_export  # noqa: E402
import ground  # noqa: E402
import life  # noqa: E402

# Infinigen's own scene type for each kind, so its gin choices (materials, densities) are its own for that place.
SCENE_TYPE = {"meadow": "plain", "underwater": "coral_reef", "moon": "desert", "fish": "under_water"}
# The full ground's cell for the render, and the render's size and samples.
RENDER_CELL_M = {"meadow": 0.1, "underwater": 0.05}
RESOLUTION = (1280, 720)
SAMPLES = 96


class Steps:
    """Seconds each step took, written as the job goes so a failed job still says how far it got."""

    def __init__(self, folder):
        self.path, self.seconds, self.began = folder / "timings.json", {}, time.time()

    def __call__(self, name):
        now = time.time()
        self.seconds[name] = round(now - self.began, 1)
        self.began = now
        self.path.write_text(json.dumps(self.seconds, indent=1))
        print(f"[patch] {name}: {self.seconds[name]} s", flush=True)


def start_infinigen(kind, seed):
    """Infinigen's gin configuration for the kind's scene type, its Blender settings, and the seed."""
    from infinigen.core import init
    from infinigen.core.util.math import FixedSeed  # noqa: F401 - imported so a broken install fails here
    init.apply_gin_configs(config_folders="infinigen_examples/configs_nature",
                           configs=["base_nature.gin", SCENE_TYPE[kind]], skip_unknown=True)
    init.configure_blender()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    np.random.seed(seed)


def camera(spec, side):
    """The eye-height camera the spec names, in Blender's metres."""
    shot = spec["camera"]
    obj = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    bpy.context.scene.collection.objects.link(obj)
    obj.data.lens = shot["lens_mm"]
    obj.data.clip_end = 1000
    obj.location = (shot["x"] - side / 2, shot["y"] - side / 2, shot["z"])
    target = Vector((shot["look_x"] - side / 2, shot["look_y"] - side / 2, shot["look_z"]))
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    return obj


def sun(look, energy, angle_deg):
    lamp = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.scene.collection.objects.link(lamp)
    lamp.data.energy = energy
    lamp.data.angle = math.radians(angle_deg)
    lamp.rotation_euler = Euler((math.radians(90 - look["sun_elevation_deg"]), 0,
                                 math.radians(look["sun_azimuth_deg"])))
    return lamp


def world_colour(colour, strength):
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (*colour, 1)
    background.inputs["Strength"].default_value = strength


def light(spec, cam):
    """The kind's light: Infinigen's sky for an Earth-like place, a black sky and a hard sun on the Moon, a blue
    murk with a volume of water below the surface."""
    look = spec["look"]
    if look["sky"] == "earth":
        from infinigen.assets.lighting import sky_lighting
        sky_lighting.add_lighting(cam)
        for node in bpy.context.scene.world.node_tree.nodes:
            if node.type == "TEX_SKY":
                node.sun_elevation = math.radians(look["sun_elevation_deg"])
                node.sun_rotation = math.radians(look["sun_azimuth_deg"])
    elif look["sky"] == "black":
        world_colour((0, 0, 0), 0)
        sun(look, 6.0, 0.53)
    else:
        world_colour((0.02, 0.10, 0.14), 0.6)
        sun(look, 3.0, 2.0)
        water_volume(spec)


def water_volume(spec):
    """A box of sea water from the floor to the surface: blue-green absorption and a little scatter."""
    side, depth = spec.get("side_m", 6.0) * 3, spec.get("water_depth_m", 8.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, depth / 2 - 2))
    box = bpy.context.active_object
    box.scale = (side, side, depth + 4)
    box.name = "water"
    material = bpy.data.materials.new("sea water")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.remove(next(node for node in nodes if node.type == "BSDF_PRINCIPLED"))
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value = (0.35, 0.75, 0.8, 1)
    volume.inputs["Density"].default_value = spec.get("water_density", 0.035)
    volume.inputs["Absorption Color"].default_value = (0.2, 0.6, 0.7, 1)
    links.new(volume.outputs["Volume"], next(node for node in nodes if node.type == "OUTPUT_MATERIAL").inputs["Volume"])
    box.data.materials.append(material)
    return box


def render(folder, samples=SAMPLES):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(folder / "infinigen.png")
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


def water_planes(spec, zones, side):
    """The plan's pools as flat water at their own levels, each over its zone's box; their records for Godot."""
    if "water" not in (zones.files if zones is not None else []) or "water_level" not in spec:
        return []
    from scipy import ndimage
    mask = zones["water"]
    labels, count = ndimage.label(mask)
    levels = np.load(spec["_folder"] / spec["water_level"])
    rows, cols = mask.shape
    records = []
    for label in range(1, count + 1):
        where = np.argwhere(labels == label)
        top, left = where.min(axis=0)
        bottom, right = where.max(axis=0)
        level = float(np.median(levels[labels == label]))
        x0, x1 = left / (cols - 1) * side - 1, right / (cols - 1) * side + 1
        y1, y0 = side - top / (rows - 1) * side + 1, side - bottom / (rows - 1) * side - 1
        bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2 - side / 2, (y0 + y1) / 2 - side / 2, level))
        plane = bpy.context.active_object
        plane.scale = (x1 - x0, y1 - y0, 1)
        material, shader = ground.principled("pool water", (0.05, 0.09, 0.08), 0.02)
        shader.inputs["Transmission Weight"].default_value = 0.9
        shader.inputs["IOR"].default_value = 1.33
        plane.data.materials.append(material)
        records.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "level": level})
    return records


def patch(spec, folder, steps):
    """A ground patch (meadow, underwater, moon): build, render, export."""
    side = spec["side_m"]
    heights = np.load(spec["_folder"] / spec["heights"])
    zones = np.load(spec["_folder"] / spec["zones"]) if "zones" in spec else None
    cam = camera(spec, side)
    if spec["kind"] == "moon":
        high, _ = ground.crater_ground(spec, heights)
        high.data.materials.append(ground.regolith())
    else:
        high = ground.heightfield(heights, side, RENDER_CELL_M[spec["kind"]])
        ground.add_zones(high, zones, side)
        ground.infinigen_material(high, "infinigen.assets.materials.terrain.Sand" if spec["kind"] == "underwater"
                                  else "infinigen.assets.materials.terrain.Dirt")
    steps("ground")
    # The spots first: realizing their assets walks the scene, which is quick before the scatters fill it.
    tree = game_export.evaluated_bvh(high)
    spots = life.place_spots(spec.get("spots", []), side, tree, spec["seed"])
    steps("spots")
    scatters = {kind: life.scatter(infinigen_kind(kind), high, None if zone == "everywhere" else zone)
                for kind, zone in spec.get("scatter", {}).items()}
    for kind, hue in spec.get("tint", {}).items():
        for collection in bpy.data.collections:
            if collection.name.startswith(kind) or kind in collection.name.lower():
                for obj in collection.objects:
                    ground.tinted(obj, hue)
    if spec["kind"] == "moon":
        for obj in [*spots, *(item for item in bpy.data.objects if item.name.startswith("scatter-"))]:
            ground.greyed(obj)
        for collection in bpy.data.collections:
            for obj in collection.objects:
                ground.greyed(obj)
    steps("scatters")
    water = water_planes(spec, zones, side)
    light(spec, cam)
    render(folder)
    steps("render")
    ground_entry = game_export.ground_model(high, side, spec["game"]["ground_cell_m"],
                                            spec["game"]["ground_texture_px"], folder,
                                            cover=spec["game"].get("cover_from_above", False))
    steps("export ground")
    models, placements = game_export.scattered(scatters, spec["game"], folder)
    more, more_placements = game_export.placed(spots, spec["game"], folder)
    steps("export models")
    shot = dict(spec["camera"], x=spec["camera"]["x"] - side / 2, y=spec["camera"]["y"] - side / 2,
                look_x=spec["camera"]["look_x"] - side / 2, look_y=spec["camera"]["look_y"] - side / 2)
    return game_export.write(folder, spec, ground_entry, models + more, {**placements, **more_placements},
                             {"water": water, "camera": shot, "look": spec["look"],
                              "water_depth_m": spec.get("water_depth_m")})


def infinigen_kind(kind):
    """The Infinigen scatter behind a game scatter kind."""
    return {"rock": "pebbles", "rubble": "rubble"}.get(kind, kind)


def fish(spec, folder, steps):
    """One fish: made, its swim looped and baked, rendered side on in the sea, exported with its animation."""
    frames = int(spec["loop_seconds"] * spec["fps"])
    bpy.context.scene.render.fps = spec["fps"]
    root, armature, meshes = life.fish(spec["seed"])
    life.looped_drivers(armature, frames)
    bones = life.bake_swim(armature, frames)
    steps(f"fish and swim ({bones} bones)")
    length = max(max(mesh.dimensions) for mesh in meshes)
    cam_obj = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = (0, -length * 2.2, length * 0.2)
    cam_obj.rotation_euler = (Vector((0, 0, 0)) - cam_obj.location).to_track_quat("-Z", "Y").to_euler()
    cam_obj.data.lens = 50
    bpy.context.scene.camera = cam_obj
    light(dict(spec, side_m=length * 4, water_depth_m=length * 3, water_density=0.004), cam_obj)
    bpy.context.scene.frame_set(frames // 4)
    render(folder, samples=64)
    steps("render")
    entry = game_export.fish_model(armature, meshes, spec["game"], folder)
    entry["loop_frames"], entry["fps"] = frames, spec["fps"]
    (folder / "stats.json").write_text(json.dumps({"kind": "fish", "fish": entry, "look": spec["look"]}, indent=1))
    steps("export")
    return entry


def main():
    spec_path, folder = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_path.read_text())
    spec["_folder"] = spec_path.parent
    steps = Steps(folder)
    start_infinigen(spec["kind"], spec["seed"])
    steps("start")
    made = fish(spec, folder, steps) if spec["kind"] == "fish" else patch(spec, folder, steps)
    bpy.ops.wm.save_as_mainfile(filepath=str(spec_path.parent / "scene.blend"))
    steps("saved")
    print(json.dumps({key: value for key, value in made.items() if key not in ("models",)}, default=str)[:2000])
    sys.stdout.flush()
    # Blender as a module can crash while it shuts down (exit 139 on 2026-10-05, after everything was saved);
    # leave without its teardown so the exit code says how the job went.
    os._exit(0)


if __name__ == "__main__":
    main()
