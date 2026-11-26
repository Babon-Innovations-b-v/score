"""Runs inside Blender (`session.py batch`): one puff of smoke simulated by Mantaflow (Blender's gas solver) and
rendered on the processor by Cycles as the frames of a six-way lit flipbook, each frame six times, lit from one side
each time (right, left, top, bottom, back, front of the card as the camera sees it).

    python3 tools/blender/session.py batch --version 5.2.2 tools/props/smoke_card/billow.py -- <out folder>

Writes <out>/frames/<frame>_<side>.png (RGBA, the card's colour lit from that side, its alpha the smoke's cover) and
<out>/sim.json (the solver's settings and the frames taken). card.py packs them into the atlases.
"""
import json
import math
import pathlib
import sys

import bpy

OUT = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
DOMAIN = 3.0          # the domain's side, metres: the card's side
RESOLUTION = 96       # the solver's cells along the domain's longest side
FRAMES = 60           # simulated frames at 24 a second
TAKEN = 16            # flipbook frames, evenly spaced over the puff's life
FIRST = 9             # the first frame taken: the puff out of its source, no longer its ball
PIXELS = 256          # each flipbook frame's side
SIDES = {"right": (1, 0, 0), "left": (-1, 0, 0), "top": (0, 0, 1), "bottom": (0, 0, -1),
         "back": (0, 1, 0), "front": (0, -1, 0)}


def cleared():
    """An empty scene in metres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return scene


def domain_object():
    """The gas domain: a cube DOMAIN a side standing on z = 0, its smoke dissolving slowly and curling."""
    bpy.ops.mesh.primitive_cube_add(size=DOMAIN, location=(0, 0, DOMAIN / 2))
    domain = bpy.context.active_object
    modifier = domain.modifiers.new("gas", "FLUID")
    modifier.fluid_type = "DOMAIN"
    settings = modifier.domain_settings
    settings.domain_type = "GAS"
    settings.resolution_max = RESOLUTION
    settings.cache_type = "ALL"
    settings.cache_directory = str(OUT / "cache")
    settings.cache_frame_start = 1
    settings.cache_frame_end = FRAMES
    settings.alpha = 0.6            # density's buoyancy: the puff rises and rolls
    settings.beta = 0.4             # heat's buoyancy
    settings.vorticity = 0.35       # curls: the billows' small lumps
    settings.use_dissolve_smoke = False  # the card fades by its particle's opacity over life, not by the solver
    settings.use_adaptive_domain = False
    settings.use_noise = True       # the solver's wavelet noise: finer curls on the billows' edges
    settings.noise_scale = 2
    settings.noise_strength = 1.0
    for wall in ("use_collision_border_front", "use_collision_border_back", "use_collision_border_right",
                 "use_collision_border_left", "use_collision_border_top", "use_collision_border_bottom"):
        if hasattr(settings, wall):
            setattr(settings, wall, False)
    return domain


def source_object():
    """The puff's source: a ball below the domain's middle letting out smoke and heat for its first 16 frames,
    pushed up and a little sideways so the puff rolls over as it grows."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(0, 0, DOMAIN * 0.32))
    source = bpy.context.active_object
    modifier = source.modifiers.new("gas", "FLUID")
    modifier.fluid_type = "FLOW"
    flow = modifier.flow_settings
    flow.flow_type = "SMOKE"
    flow.flow_behavior = "INFLOW"
    flow.flow_source = "MESH"
    flow.surface_distance = 0.2
    flow.use_initial_velocity = True
    flow.velocity_coord = (0.2, 0.0, 1.2)
    flow.density = 1.0
    flow.temperature = 1.5
    flow.smoke_color = (1.0, 1.0, 1.0)
    flow.use_plane_init = False
    if hasattr(flow, "subframes"):
        flow.subframes = 1
    flow.use_inflow = True
    flow.keyframe_insert("use_inflow", frame=1)
    flow.use_inflow = False
    flow.keyframe_insert("use_inflow", frame=17)
    source.hide_render = True
    return source


def smoke_material(domain):
    """White smoke: a principled volume, its density the solver's, scattering forward a little as water and soot do."""
    material = bpy.data.materials.new("smoke")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    volume.inputs["Density"].default_value = 30.0
    volume.inputs["Anisotropy"].default_value = 0.2
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    domain.data.materials.append(material)


def camera(scene):
    """An orthographic camera looking along +y at the domain, framing its side exactly."""
    data = bpy.data.cameras.new("card")
    data.type = "ORTHO"
    data.ortho_scale = DOMAIN
    view = bpy.data.objects.new("card", data)
    scene.collection.objects.link(view)
    view.location = (0, -DOMAIN * 3, DOMAIN / 2)
    view.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = view


def lights(scene):
    """{side: a sun shining from that side onto the card}, all off."""
    found = {}
    for side, way in SIDES.items():
        data = bpy.data.lights.new(side, "SUN")
        data.energy = 8.0
        data.angle = math.radians(2)
        sun = bpy.data.objects.new(side, data)
        scene.collection.objects.link(sun)
        sun.rotation_mode = "QUATERNION"
        sun.rotation_quaternion = (-__import__("mathutils").Vector(way)).to_track_quat("-Z", "Y")
        sun.hide_render = True
        found[side] = sun
    return found


def render_settings(scene):
    """Cycles on the processor, a transparent film, the frame's side PIXELS, no world light."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.cycles.volume_bounces = 4
    scene.cycles.max_bounces = 4
    scene.render.film_transparent = True
    scene.render.resolution_x = PIXELS
    scene.render.resolution_y = PIXELS
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("none")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world
    scene.frame_start, scene.frame_end = 1, FRAMES


def taken_frames():
    """The flipbook's frames: TAKEN evenly spaced from FIRST to the last simulated frame."""
    return [round(FIRST + index * (FRAMES - FIRST) / (TAKEN - 1)) for index in range(TAKEN)]


def baked(domain):
    """The solver run over every frame (its cache under OUT)."""
    bpy.context.view_layer.objects.active = domain
    bpy.ops.fluid.bake_all()


def rendered(scene, suns):
    """Each taken frame rendered once per side, that side's sun alone on."""
    frames = OUT / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(taken_frames()):
        scene.frame_set(frame)
        for side, sun in suns.items():
            for other in suns.values():
                other.hide_render = other is not sun
            scene.render.filepath = str(frames / f"{index:02d}_{side}.png")
            bpy.ops.render.render(write_still=True)
        print(f"billow: frame {index + 1}/{TAKEN} rendered", flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scene = cleared()
    domain = domain_object()
    source_object()
    smoke_material(domain)
    camera(scene)
    suns = lights(scene)
    render_settings(scene)
    baked(domain)
    rendered(scene, suns)
    record = {"solver": "Mantaflow (Blender %s) gas" % bpy.app.version_string, "domain_m": DOMAIN,
              "resolution": RESOLUTION, "noise_upres": 2, "frames": FRAMES, "fps": 24, "taken": taken_frames(), "pixels": PIXELS,
              "renderer": "Cycles CPU, 48 samples denoised, volume bounces 4", "sides": list(SIDES)}
    (OUT / "sim.json").write_text(json.dumps(record, indent=1) + "\n")
    print("billow: done", flush=True)


main()
