"""Inside Blender (Cycles on the CPU): a generated head drawn as the raw model, then as `head.py` made it whole, in
`blender_skin.py`'s shots (the face from the front and three quarters, the eyes in a 9 cm frame, the cheek and nose
close up), the whole route's photo way.

    blender -b --python blender_head.py -- <raw model.glb> <head out>/eyes/eyes.npz <library> <height m> <samples> \
        <renders> <head out>

Before: the raw model in its glTF material, no eyes. After: the mesh replaced by the lids' mended one in the toned
paint (`blender_lids.mended`), the face texture and the library skin laid on the skin's faces (`blender_skin`), the
eyeballs, cornea and wet line laid (`blender_eyes.laid`), the iris wearing the photo's own (<head out>/iris.png on
the eyeball's UV, the pupil's triangles with it: the picture holds the photo's pupil), the lashes as hair curves.
Writes <renders>/before-*.png, after-*.png and frames.json.
"""
import json
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_eyes  # noqa: E402  (reads its six arguments; the head's out folder is the seventh)
import blender_lids  # noqa: E402
import blender_sheet  # noqa: E402
import blender_skin  # noqa: E402
from blender_eyes import blender_face, render  # noqa: E402

HEAD = pathlib.Path(sys.argv[sys.argv.index("--") + 1:][6])
blender_lids.LIDS = HEAD / "lids"
IRIS, PUPIL = 1, 2  # the eyeballs' finish indices (face.eye_finish)


def iris_pictured(eyes):
    """The eyeballs' iris wearing the photo's iris (iris.png on their UV `st`) as its base colour, and their pupil's
    triangles turned to it (the picture holds the photo's pupil, its own size)."""
    material = eyes.data.materials[IRIS].copy()
    material.name = "iris_photo"
    tree = material.node_tree
    principled = blender_face.principled_of(material)
    for link in list(principled.inputs["Base Color"].links):
        tree.links.remove(link)
    image = tree.nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(str(HEAD / "iris.png"))
    image.image.colorspace_settings.name = "sRGB"
    image.interpolation = "Cubic"
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "st"
    tree.links.new(uv.outputs["UV"], image.inputs["Vector"])
    tree.links.new(image.outputs["Color"], principled.inputs["Base Color"])
    eyes.data.materials[IRIS] = material
    finish = np.zeros(len(eyes.data.polygons), np.int32)
    eyes.data.polygons.foreach_get("material_index", finish)
    eyes.data.polygons.foreach_set("material_index", np.where(finish == PUPIL, IRIS, finish).astype(np.int32))
    eyes.data.update()


def lashes(head):
    """The lashes as hair curves on the head (`lids.py`'s, in the library's strand finish fitted to the photo)."""
    lids = dict(np.load(HEAD / "lids" / "lids.npz", allow_pickle=False))
    fibres = json.loads((HEAD / "lids" / "fibre.json").read_text())
    return blender_sheet.strand_pieces("lashes", lids["lashes.counts"], lids["lashes.points"], lids["lashes.radius"],
                                       fibres["lashes"], head)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    eyes = dict(np.load(blender_eyes.EYES, allow_pickle=False))
    lids = dict(np.load(HEAD / "lids" / "lids.npz", allow_pickle=False))
    skin = dict(np.load(HEAD / "skin" / "skin.npz", allow_pickle=False))
    head, holder = blender_eyes.imported()
    low, high = render.bounds([head])
    camera, turntable = blender_eyes.staged(holder, (low + high) / 2.0)
    pathlib.Path(blender_eyes.OUT).mkdir(parents=True, exist_ok=True)
    corneas = blender_eyes.mean_point(blender_eyes.world_points(head, eyes["cornea_apex"]))
    aim = corneas + Vector((0.0, 0.0, -blender_skin.FACE_DROP_M))
    close = blender_eyes.world_points(head, [skin["close_point"]])[0]
    blender_skin.frames(bpy.context.scene)
    blender_skin.shots(camera, turntable, aim, corneas, close, "before")
    print(f"mended head: {blender_lids.mended(head, lids)} triangles", flush=True)
    blender_skin.attributes(head, skin)
    blender_skin.face_uv(head, skin["box"])
    blender_skin.skin_marked(head, skin["skin_centres"])
    blender_skin.skin_material(head, blender_eyes.LIBRARY, HEAD / "skin", blender_skin.metric_space(turntable))
    eyes.update({"wet.points": lids["wet.points"], "wet.triangles": lids["wet.triangles"]})
    iris_pictured(blender_eyes.laid(head, eyes)["eyes"])
    print(f"lashes: {len(lashes(head))} curve objects", flush=True)
    blender_skin.shots(camera, turntable, aim, corneas, close, "after")
    print("HEAD RENDER DONE", flush=True)


if __name__ == "__main__":
    main()
