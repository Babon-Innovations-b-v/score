"""Inside Blender (Cycles on the CPU): the strand swatches `fibre.py`'s melanin table is read from. A head-sized ball
under a bob of strands in the library's strand finish (`fibre.LIBRARY`), drawn once per case of melanin, redness and
white share (`fibre.SWATCH`) the way `blender_sheet.py` draws a generated person's head: the park sky and its meter's
exposure, 85 mm from the front, plain sRGB, the lens's fall-off and grain, at the close-up photographs' scale
(`fibre.SWATCH["mm_per_px"]`). The world is not drawn (film transparent, the ground hidden from the camera but
lighting), so a picture's alpha is the swatch's own outline; its strands are read over the ball's upper part
(MEASURED_DEG), clear of the skin under them.

    blender -b --python blender_swatch.py -- none none <library> 0 <samples> <out folder>

(the first six arguments are `blender_sheet.py`'s, whose strand pieces this draws.) Writes <out>/<case>.png for each
case and <out>/cases.json. `python -m tools.characters.generated.fibre <out> <table.json>` reads them into the table.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))  # `fibre` reads the library's finish
import blender_sheet  # noqa: E402  (reads the same six arguments; puts render.py and blender_face.py on the path)
import blender_eyes  # noqa: E402
import render  # noqa: E402
import fibre  # noqa: E402

LIBRARY, SAMPLES, OUT = blender_sheet.LIBRARY, blender_sheet.SAMPLES, blender_sheet.OUT
BALL = {"radius_m": 0.09, "centre_z": 1.55, "skin_srgb": (0.74, 0.6, 0.52)}
MEASURED_DEG = 105.0  # the strands are read down to this far from the ball's top (lower, the ball shows through)
STRANDS = {"count": 120000, "points": 16, "radius_m": 4e-5, "lowest_deg": 118.0, "layer_m": (0.0005, 0.012),
           "rise": 0.15, "sway_deg": 4.0}
SEED = 223


def ball():
    """The head: a ball in a skin finish under the strands."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=BALL["radius_m"],
                                         location=(0.0, 0.0, BALL["centre_z"]))
    item = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    material = bpy.data.materials.new("skin")
    material.use_nodes = True
    shader = material.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*fibre.srgb_to_linear(np.array(BALL["skin_srgb"])), 1.0)
    shader.inputs["Roughness"].default_value = blender_sheet.SKIN_ROUGHNESS
    item.data.materials.append(material)
    return item


def bob():
    """The strands, in the groom's frame (y up, the face along +z; `strand_pieces` turns them into Blender's):
    (counts, points, radius). Each strand is rooted on
    the ball's upper part and runs down its meridian to STRANDS["lowest_deg"] from the top, lifted off the ball to its
    own layer over its first STRANDS["rise"]."""
    rng = np.random.default_rng(SEED)
    count, steps = STRANDS["count"], STRANDS["points"]
    golden = np.pi * (3.0 - np.sqrt(5.0))
    index = np.arange(count * 2)
    height = 1.0 - 2.0 * (index + 0.5) / (count * 2)
    keep = height > -0.15
    height, azimuth = height[keep][:count], (index * golden)[keep][:count]
    polar = np.arccos(height)
    along = np.linspace(0.0, 1.0, steps)
    theta = polar[:, None] + (math.radians(STRANDS["lowest_deg"]) - polar[:, None]) * along[None]
    phi = azimuth[:, None] + math.radians(STRANDS["sway_deg"]) * rng.normal(size=(len(polar), 1)) * along[None]
    layer = rng.uniform(*STRANDS["layer_m"], size=(len(polar), 1))
    lift = np.clip(along / STRANDS["rise"], 0.0, 1.0)[None]
    reach = BALL["radius_m"] + layer * (3.0 * lift ** 2 - 2.0 * lift ** 3)
    centre = np.array([0.0, BALL["centre_z"], 0.0])
    points = centre + reach[..., None] * np.stack([np.sin(theta) * np.sin(phi), np.cos(theta),
                                                   np.sin(theta) * np.cos(phi)], axis=-1)
    return np.full(len(polar), steps), points.reshape(-1, 3), np.full(len(polar) * steps, STRANDS["radius_m"])


def drawn(scene, holder, counts, points, radius, case):
    """One case's strands drawn to <out>/<case name>.png; the strands removed after."""
    block = dict(fibre.library_block(), melanin=case["melanin"], redness=case["redness"],
                 white_share=case["white_share"])
    items = blender_sheet.strand_pieces("swatch", counts, points, radius, block, holder)
    path = pathlib.Path(OUT) / f"{case['name']}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    render.developed(path, scene.camera.data.dof.aperture_fstop)
    for item in items:
        curves = item.data
        bpy.data.objects.remove(item)
        bpy.data.hair_curves.remove(curves)
    print(f"drew {case['name']}", flush=True)


def rows_measured(scene, camera):
    """The picture's rows (from the top) the strands are read in: down to MEASURED_DEG from the ball's top."""
    angle = math.radians(MEASURED_DEG)
    low = Vector((0.0, -BALL["radius_m"] * math.sin(angle), BALL["centre_z"] + BALL["radius_m"] * math.cos(angle)))
    return int((1.0 - world_to_camera_view(scene, camera, low).y) * scene.render.resolution_y)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    holder = bpy.data.objects.new("holder", None)
    scene.collection.objects.link(holder)
    ball()
    exposure = render.place(LIBRARY, Vector((0.0, 0.0, 0.0)), blender_sheet.SETTING)
    render.film(scene, exposure)
    bpy.data.objects["ground"].visible_camera = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform, scene.view_settings.look = blender_eyes.VIEW
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(SAMPLES)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = blender_sheet.THREADS
    frame_m = fibre.SWATCH["frame_m"]
    rows = int(round(frame_m * 1000.0 / fibre.SWATCH["mm_per_px"]))
    scene.render.resolution_x, scene.render.resolution_y = int(rows * 0.8), rows
    scene.render.resolution_percentage = 100
    camera = render.camera_made(scene)
    aim = Vector((0.0, 0.0, BALL["centre_z"] - 0.02))
    distance = frame_m / 2.0 / math.tan(camera.data.angle_y / 2.0)
    render.aimed(camera, aim + Vector((0.0, -distance, 0.0)), aim, render.STOPS["face"], aim)
    counts, points, radius = bob()
    out = pathlib.Path(OUT)
    out.mkdir(parents=True, exist_ok=True)
    cases = fibre.swatch_cases()
    for case in cases:
        if not (out / f"{case['name']}.png").exists():
            drawn(scene, holder, counts, points, radius, case)
    (out / "cases.json").write_text(json.dumps({"cases": cases, "samples": int(SAMPLES),
                                                "mm_per_px": fibre.SWATCH["mm_per_px"],
                                                "rows_measured": rows_measured(scene, camera)}, indent=1))
    print("SWATCH RENDER DONE", flush=True)


if __name__ == "__main__":
    main()
