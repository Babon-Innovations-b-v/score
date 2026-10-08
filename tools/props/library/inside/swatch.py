"""Runs inside Blender (`session.py batch`): render every library material on one test piece at each wear setting, lit
and as its flat base colour, so the owner sees the library and the tools can score it.

    python3 tools/blender/session.py batch tools/props/library/inside/swatch.py -- <job.json>

The job names the output folder, the resolved materials (library.py), the wear settings, the dirt, the seed, the
picture size and samples. The test piece has true edges, as a code-built piece has: a bevelled plate, a raised boss,
two bolt heads and a pipe across it, so wear shows where it would on a real panel. Writes
<out>/<material>-w<wear>.png (lit) and <material>-w<wear>-base.png (the base colour alone) and timings.json.
"""
import json
import math
import pathlib
import sys
import time

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import recipes  # noqa: E402
import scene_setup  # noqa: E402
import shapes  # noqa: E402


def test_piece():
    """The swatch's piece, its parts joined, smooth where curved, true edges kept."""
    parts = []
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.015))
    plate = bpy.context.object
    plate.scale = (0.4, 0.4, 0.03)
    parts.append(plate)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.06, 0.05, 0.045))
    boss = bpy.context.object
    boss.scale = (0.16, 0.12, 0.03)
    parts.append(boss)
    for across in (-0.15, 0.15):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.014, depth=0.012, vertices=12, location=(across, 0.15, 0.036))
        parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.42, vertices=32, location=(0.0, -0.11, 0.065),
                                        rotation=(0.0, math.pi / 2, 0.0))
    parts.append(bpy.context.object)
    for part in parts:
        bpy.ops.object.select_all(action="DESELECT")
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bevel = part.modifiers.new("bevel", "BEVEL")
        bevel.width = 0.003
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.join()
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return plate


PICTURE_RECIPES = ("screen", "printed")


def picture_piece():
    """The swatch for a picture variant (a screen, a label): an upright plate whose front carries the picture, turned
    to face the camera."""
    plate = shapes.content_plate((-0.2, 0.0, -0.01), (0.2, 0.28, 0.01), "swatch", "picture")
    plate.rotation_euler = (0.0, 0.0, math.pi)
    plate.location = (0.0, 0.05, 0.0)
    return plate


def shown(pieces_by_kind, kind):
    """Only one swatch piece draws at a time."""
    for name, item in pieces_by_kind.items():
        item.hide_render = name != kind
    return pieces_by_kind[kind]


def render_material(piece, material, path):
    piece.data.materials.clear()
    piece.data.materials.append(material)
    bpy.context.scene.render.filepath = str(path)
    began = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - began


def recipe_settings(out):
    """Each recipe's settings, node count and lines of code, as ProcFunc's tracer and the source give them."""
    found = {}
    for recipe in recipes.RECIPES:
        try:
            found[recipe] = recipes.settings_of(recipe)
        except Exception as error:  # the tracer's own limits are a finding for the paper, not a stop
            found[recipe] = {"error": f"{type(error).__name__}: {error}"}
        found[recipe]["source"] = recipes.SOURCES[recipe]
    (out / "settings.json").write_text(json.dumps(found, indent=1))


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    scene_setup.empty_scene(job["size"], job["samples"])
    swatch_pieces = {"test": test_piece(), "picture": picture_piece()}
    cameras = {"": scene_setup.camera_on(swatch_pieces["test"], (0.55, -0.75, 0.62), 2.6),
               "-close": scene_setup.camera_aimed((0.12, -0.12, 0.33), (0.12, 0.08, 0.03), 50)}
    scene_setup.studio_light()
    if job.get("settings"):
        recipe_settings(out)
    timings = {}
    for name, spec in job["materials"].items():
        piece = shown(swatch_pieces, "picture" if spec["recipe"] in PICTURE_RECIPES else "test")
        for wear in job["wears"]:
            found = recipes.channels(spec, wear, job["dirt"] if wear > 0 else 0.0, job["seed"])
            lit = recipes.shaded(found).item()
            lit.displacement_method = "BUMP"
            base = recipes.emitted(found.base_color).item()
            for view in job.get("views", [""]):
                bpy.context.scene.camera = cameras[view]
                timings[f"{name}-w{wear}{view}"] = render_material(piece, lit, out / f"{name}-w{wear}{view}.png")
                render_material(piece, base, out / f"{name}-w{wear}{view}-base.png")
            print("SWATCH", name, wear, flush=True)
    (out / "timings.json").write_text(json.dumps(timings, indent=1))


main()
