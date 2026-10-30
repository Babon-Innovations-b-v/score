"""Runs inside Blender on a rented card (tools/cloud/blender_cloud.py): a place's stage rendered on its views as
tools/blender/inside/usd_views.py renders a look, with each of the place's own lamps in a light group of its own, so
one render gives the place's light lamp by lamp (Cycles light groups: each a pass of what that lamp alone lights).

    blender -b --python light_passes.py -- <stage.usda> <views.json> <out folder>

views.json is usd_views.py's ({"size", "views": [{"name", "eye", "aim", "up", "fov", "frame"}]}) with "lamps": the
prim paths of the place's own lamps, and "device": "CPU" where the job is predicted past its card (passes.py
with_devices): Cycles then renders on the processor at the same samples and denoising. Per view it writes <name>-look.png (the look as usd_views draws it, glow and all)
and <name>-passes.npz: the linear luminance (Rec. 709) of the whole picture (`combined`) and of each lamp's group
(`lamp_<n>`, n its place in "lamps"), each averaged over 2 x 2 pixels, as float16; and passes.json, which lamp each
group holds. Light is linear in a lamp's strength, so the picture at any strengths is `combined` plus each group
times its scale less one: the light stage's sweep needs no other render. The npz also holds `missing`: the share of
the view's pixels whose surface colour (Cycles' diffuse or glossy colour pass) is Blender's missing-picture magenta
(1, 0, 1), which passes.judge_magenta reads; and `sky`: at full size, where the eye's ray met no surface but the sky's
own (the world's background or the day dome, Cycles' object index pass), which light's exposure leaves to the sky
check.
"""
import json
import pathlib
import re
import sys

import bpy

INSIDE = pathlib.Path(__file__).resolve().parents[4] / "tools/blender/inside"
sys.path.insert(0, str(INSIDE))
import usd_views  # noqa: E402

LUMINANCE = (0.2126, 0.7152, 0.0722)
GROUP = re.compile(r"Combined_(lamp_\d+)\.([RGB])$")
# A missing picture's (1, 0, 1) reaches the colour passes scaled, never tinted (a tiny stage in Blender 5.0.1,
# 2026-10-30): a plain finish's diffuse colour (0.956, 0, 0.956), its specular layer taking the rest; a metal's diffuse
# colour black and its glossy colour (1, 0, 1); half metal (0.48, 0, 0.48) and (0.52, 0.02, 0.52). Within MISSING_NEAR
# of red in green and in red less blue, red at least MISSING_LEAST: a grey or a lit grey never comes near it.
MISSING_NEAR = 0.05
MISSING_LEAST = 0.3


def lamp_order(stage):
    """The stage's lights in the order usd_views.stage_lights finds them (its `stage_light_<n>` objects)."""
    from pxr import Usd, UsdLux
    opened = Usd.Stage.Open(str(stage))
    return [str(prim.GetPath()) for prim in opened.Traverse()
            if prim.IsA(UsdLux.SphereLight) or prim.IsA(UsdLux.DistantLight)]


def light_groups(scene, stage, lamps):
    """Each of the place's lamps in a light group of its own: {group: prim path}."""
    order = lamp_order(stage)
    groups = {}
    layer = scene.view_layers[0]
    for number, path in enumerate(lamps):
        if path not in order:
            raise RuntimeError(f"lamp {path} is not a light of {stage}")
        name = f"lamp_{number}"
        layer.lightgroups.add(name=name)
        bpy.data.objects[f"stage_light_{order.index(path)}"].lightgroup = name
        groups[name] = path
    return groups


def render_both(scene, view, out):
    """One render: the passes to a multilayer EXR, the look (the composite under the view transform) to a PNG."""
    settings = scene.render.image_settings
    kept = (settings.media_type, settings.file_format, settings.color_mode, settings.color_depth)
    settings.media_type = "MULTI_LAYER_IMAGE"
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_depth = "32"
    exr = out / f"{view['name']}-passes.exr"
    scene.render.use_compositing = scene.compositing_node_group is not None
    usd_views.render(scene, exr, transparent=False)
    settings.media_type, settings.file_format, settings.color_mode, settings.color_depth = kept
    settings.color_mode = "RGB"
    bpy.data.images["Render Result"].save_render(filepath=str(out / f"{view['name']}-look.png"), scene=scene)
    scene.render.use_compositing = False
    return exr


def halved(values):
    """The mean over each 2 x 2 block (an odd last row or column dropped)."""
    tall, wide = values.shape[0] // 2 * 2, values.shape[1] // 2 * 2
    return values[:tall, :wide].reshape(tall // 2, 2, wide // 2, 2).mean(axis=(1, 3))


def passes_of(exr):
    """{"combined" or group: linear luminance, top row first, halved} from the render's multilayer EXR."""
    import numpy
    import OpenImageIO
    channels = {}
    for part in range(OpenImageIO.ImageBuf(str(exr)).nsubimages):
        held = OpenImageIO.ImageBuf(str(exr), part, 0)
        pixels = numpy.asarray(held.get_pixels(OpenImageIO.FLOAT))
        for index, name in enumerate(held.spec().channelnames):
            channels[name] = pixels[:, :, index]
    found = {}
    combined = [next(values for name, values in channels.items() if name.endswith(f"Combined.{axis}")
                     and "Composite" not in name) for axis in "RGB"]
    found["combined"] = sum(weight * values for weight, values in zip(LUMINANCE, combined))
    for name, values in channels.items():
        match = GROUP.search(name)
        if match:
            weight = LUMINANCE["RGB".index(match.group(2))]
            found[match.group(1)] = found.get(match.group(1), 0.0) + weight * values
    held = {name: halved(values).astype(numpy.float16) for name, values in found.items()}
    return dict(held, missing=missing_share(channels), sky=sky_mask(channels))


def sky_mask(channels):
    """Where the object index pass is 0: no object met (sky_apart), or only the day dome."""
    return next(values for name, values in channels.items() if name.endswith("IndexOB.X")) == 0


def sky_apart(scene):
    """Every object in the object index pass as 1 but the day dome (usd_views.sky_domes' score:sky_strength), so the
    pass's 0 is the sky."""
    for item in scene.objects:
        item.pass_index = 0 if item.type == "MESH" and usd_views.score_value(item, "sky_strength") is not None else 1


def magenta_colour(channels, colour_pass):
    """Where a colour pass is Blender's missing-picture (1, 0, 1) scaled: red and blue equal and lit, no green."""
    import numpy
    red, green, blue = [next(values for name, values in channels.items() if name.endswith(f"{colour_pass}.{axis}"))
                        for axis in "RGB"]
    return (red > MISSING_LEAST) & (green < MISSING_NEAR * red) & (numpy.abs(red - blue) < MISSING_NEAR * red)


def missing_share(channels):
    """The share of the picture's pixels whose surface colour (Cycles' diffuse or glossy colour pass) is magenta."""
    import numpy
    return numpy.float32((magenta_colour(channels, "Diffuse Color") | magenta_colour(channels, "Glossy Color")).mean())


def main():
    import numpy
    stage, views, out = usd_views.arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene = usd_views.empty_scene()
    objects = [item for item in usd_views.import_stage(stage) if not item.hide_render]
    effects = usd_views.effect_points(stage, objects)
    usd_views.renderer(scene, views["size"])
    if views.get("device") == "CPU" and scene.render.engine == "CYCLES":  # a job past its card (passes.with_devices)
        scene.cycles.device = "CPU"
    if effects and scene.render.engine == "CYCLES":
        scene.cycles.transparent_max_bounces = usd_views.EFFECT_BOUNCES
    if not usd_views.stage_lights(stage)[0]:  # usd_views.lit would light it with its fixed sun, a light not designed
        raise SystemExit("light_passes: the stage holds no light of its own; refused rather than lit by a stand-in sun")
    environment = usd_views.lit(scene, stage)
    plane = usd_views.stage_ground(objects)
    if plane is None and (environment is None or environment["ground_plane"]):
        usd_views.ground(scene)
    usd_views.haze_volumes(objects)
    usd_views.sky_domes(objects)
    usd_views.water_mirrors(stage, objects)
    beams = usd_views.beam_materials(stage, objects)
    if environment is not None and environment.get("glow"):
        usd_views.glow_pass(scene, environment["glow"], environment["exposure"])
    groups = light_groups(scene, stage, views["lamps"])
    # The surface colour, so a missing picture is told from a surface a magenta lamp lights (passes.judge_magenta).
    scene.view_layers[0].use_pass_diffuse_color = scene.view_layers[0].use_pass_glossy_color = True
    scene.view_layers[0].use_pass_object_index = True  # the sky apart (sky_mask)
    (out / "passes.json").write_text(json.dumps({"groups": groups, "size": views["size"]}, indent=1))
    for view in views["views"]:
        scene.frame_set(int(view.get("frame", scene.frame_current)))
        usd_views.draw_effects(effects, scene.frame_current)
        usd_views.camera(scene, view)
        sky_apart(scene)
        usd_views.widen_beams(beams, scene.camera.matrix_world.translation)
        exr = render_both(scene, view, out)
        numpy.savez_compressed(out / f"{view['name']}-passes.npz", **passes_of(exr))
        exr.unlink()
    print("light_passes: wrote", out)


main()
