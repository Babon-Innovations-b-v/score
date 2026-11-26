"""Inside Blender (Cycles on the CPU): a generated head drawn after its lids, lashes and brows are made (`lids.py`'s
lids.npz), in the same light, camera and frames as `blender_eyes.py`'s pictures, whose "after" pictures are this
step's "before".

    blender -b --python blender_lids.py -- <model.glb> <eyes.npz> <library> <height m> <samples> <out folder> \
        <lids folder>

The model's mesh is replaced by the mended one (its lids refined and moved, the painted floor already pushed back and
removed) and its texture by `lids.py`'s (the brows painted over); the eyeballs and the cornea's shell are laid as
`blender_eyes.py` lays them, the wet line `lids.py`'s; the lashes and brows are hair curves in the library's strand
finish fitted to the photo (`blender_sheet.strand_pieces`). Writes <out>/after-face.png, after-eyes.png and
after-three_quarter.png.
"""
import json
import pathlib
import sys

import bpy
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_eyes  # noqa: E402  (reads the first six arguments: the model, eyes.npz, library, height, samples, out)
import blender_sheet  # noqa: E402
import render  # noqa: E402  (on the path blender_eyes.py put it)
import blender_face  # noqa: E402

LIDS = pathlib.Path(sys.argv[sys.argv.index("--") + 7])


def mended(head, lids):
    """The head's mesh replaced by the mended one (lids.npz's `head.*`, the model's own frame) with its corners' UVs,
    smooth, in the model's own materials, its base colour picture (only that: the glb's metal and roughness picture is
    another, 2026-11-26) `lids.py`'s texture."""
    points = blender_face.z_up(lids["head.points"])
    triangles = lids["head.triangles"]
    mesh = bpy.data.meshes.new("mended")
    mesh.from_pydata(points.tolist(), [], triangles.tolist())
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", lids["head.uv"].reshape(-1).astype(np.float32))
    mesh.shade_smooth()
    for material in head.data.materials:
        mesh.materials.append(material)
    head.data = mesh
    picture = bpy.data.images.load(str(LIDS / "texture.png"))
    for material in mesh.materials:
        for link in blender_face.principled_of(material).inputs["Base Color"].links:
            if link.from_node.type == "TEX_IMAGE":
                link.from_node.image = picture
    return len(mesh.polygons)


def hairs(head, lids, fibres):
    """The lashes and the brows as hair curves on the head."""
    items = []
    for name in ("lashes", "brows"):
        items += blender_sheet.strand_pieces(name, lids[f"{name}.counts"], lids[f"{name}.points"],
                                             lids[f"{name}.radius"], fibres[name], head)
    return items


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    eyes = dict(np.load(blender_eyes.EYES, allow_pickle=False))
    lids = dict(np.load(LIDS / "lids.npz", allow_pickle=False))
    fibres = json.loads((LIDS / "fibre.json").read_text())
    head, holder = blender_eyes.imported()
    low, high = render.bounds([head])
    camera, turntable = blender_eyes.staged(holder, (low + high) / 2.0)
    painted = blender_eyes.mean_point(blender_eyes.world_points(head, eyes["painted_pupils"]))
    print(f"mended head: {mended(head, lids)} triangles", flush=True)
    eyes.update({"wet.points": lids["wet.points"], "wet.triangles": lids["wet.triangles"]})
    blender_eyes.laid(head, eyes)
    print(f"hairs: {len(hairs(head, lids, fibres))} curve objects", flush=True)
    pathlib.Path(blender_eyes.OUT).mkdir(parents=True, exist_ok=True)
    blender_eyes.shots(camera, turntable, painted + blender_eyes.Vector((0.0, 0.0, -0.03)),
                       blender_eyes.mean_point(blender_eyes.world_points(head, eyes["cornea_apex"])), "after")
    print("LIDS RENDER DONE", flush=True)


if __name__ == "__main__":
    main()
