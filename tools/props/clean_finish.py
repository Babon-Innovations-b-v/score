"""Finish a raw Pixal3D model cleanly: the chain pixal.py runs on every new or re-finished model.

The generator's raw model is clean (about a million faces, a 4096 texture); every bit of the mess
our models showed up close was added after it, by the finish. Measured 2026-10-01 on the crate,
the ice mine, the rover and the lab's own garden gnome, the old finish (`retopo_repaint.py
--skip-paint`) lost it in four places, and each step below answers one:

1. Loose specks. A raw model carries hundreds to thousands of tiny loose pieces (the ice mine
   4,542); slimming melts them into crumbs. They go first (`remove_loose_parts.py`, the lab's).
2. Slimming. The lab's voxel remesh then collapse stays: decimating the raw directly shatters it
   (seen again here on the crate). Only its shape is kept.
3. Unwrapping and baking. The lab unwraps with one huge island per side and bakes nearest-texel
   with one ray, over smooth corners: stretched streaks on the crate's back, gold triangles across
   its panels, and a detail normal map whose noise the ink pass draws as black specks. Here xatlas
   (MIT) unwraps it again, and `blender_clean_bake.py` bakes base colour and metal-roughness with
   hard edges set first, several rays a texel and no normal map.
4. Pixel Match. Every surface the source picture sees takes the picture's own pixel (the lab's
   `photo_paint`, image-to-3dlab 0.3.5+), so bolts, screens and edges come out as drawn. The
   lab's palette shift is left off: fitted on the front it tinted the crate's unseen back yellow.

Then the lab's compression (JPEG, 2048). About a minute a model on the processor; nothing here
touches the graphics card.
"""
import json
import math
import pathlib
import subprocess

import numpy as np
from PIL import Image

from paths import BLENDER, IMAGE_TO_3DLAB, REPO

LAB_PYTHON = IMAGE_TO_3DLAB / ".venv" / "bin" / "python"
# The finishing scripts are run from the vendored copy, which is at least the release with Pixel
# Match; generating still runs from the runtime checkout, which holds the Pixal3D build.
LAB = REPO / "vendor" / "image-to-3dlab"
HERE = pathlib.Path(__file__).resolve().parent
# Loose pieces under this many faces are specks, not parts: the lab's own default.
SMALLEST_PART = 100
# Folds sharper than this are shaded as corners, not rounded over.
FOLD_DEGREES = 40.0
# Rays averaged for each texel of the bake.
RAYS = 8
ATLAS = 2048

# pixal3d.cpp's --sv-image crop (src/image_preprocess.cpp), restated so a raw model made before
# its camera folder was kept (every cloud batch) can still be Pixel Matched: the picture shrunk
# to this long side if bigger, the box of alpha above this, a square this much bigger, centred.
STAGED_SIDE = 1024
SOLID_ALPHA = 204
CROP_MARGIN = 1.1
# Its fixed front camera: 20 degrees, mesh scale 1 (distance 1 / (2 tan 10 degrees)).
GAUGE_FOV = 0.34906584
GAUGE_CAMERA = [[1, 0, 0, 0], [0, 0, -1, -2.83564091], [0, 1, 0, 0], [0, 0, 0, 1]]


def run(command, log):
    """Run one step with its output in `log`, failing loudly with the log's end."""
    with open(log, "w") as handle:
        done = subprocess.run([str(part) for part in command], stdout=handle,
                              stderr=subprocess.STDOUT, check=False)
    if done.returncode:
        tail = "\n".join(pathlib.Path(log).read_text().splitlines()[-15:])
        raise SystemExit(f"{pathlib.Path(log).stem} failed ({done.returncode}):\n{tail}")


def crop_box(alpha):
    """(left, top, side) of the square pixal3d.cpp crops from a matte of at most STAGED_SIDE."""
    rows, columns = np.nonzero(alpha > SOLID_ALPHA)
    centre_x = (columns.min() + columns.max()) / 2.0
    centre_y = (rows.min() + rows.max()) / 2.0
    span = max(columns.max() - columns.min(), rows.max() - rows.min())
    half = max(1, max(2, math.floor(span * CROP_MARGIN)) // 2)
    return math.floor(centre_x - half), math.floor(centre_y - half), 2 * half


def staged_views(cut_out, folder):
    """The camera folder pixal3d.cpp stages for a single picture, rebuilt from its cut-out."""
    matte = Image.open(cut_out).convert("RGBA")
    if max(matte.size) > STAGED_SIDE:
        shrink = STAGED_SIDE / max(matte.size)
        matte = matte.resize((math.floor(matte.size[0] * shrink), math.floor(matte.size[1] * shrink)),
                             Image.LANCZOS)
    left, top, side = crop_box(np.asarray(matte)[..., 3])
    staged = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    staged.paste(matte, (-left, -top))
    folder.mkdir(parents=True, exist_ok=True)
    staged.save(folder / "input.png")
    (folder / "transforms.json").write_text(json.dumps(
        {"camera_angle_x": GAUGE_FOV, "mesh_scale": 1,
         "frames": [{"file_path": "input.png", "transform_matrix": GAUGE_CAMERA}]}, indent=2))
    return folder


def welded(points, faces):
    """The corners merged where they sit at one place, and the faces renumbered onto them."""
    size = np.ptp(points, axis=0).max()
    _, first, index = np.unique(np.round(points / (size * 1e-6)).astype(np.int64), axis=0,
                                return_index=True, return_inverse=True)
    return points[first], index.reshape(-1)[faces]


def unwrapped(source, out):
    """The slimmed model's shape with new UVs from xatlas, charts following its panels."""
    import trimesh
    import xatlas

    loaded = trimesh.load(source, force="mesh", process=False)
    points, faces = welded(np.asarray(loaded.vertices, dtype=np.float64), np.asarray(loaded.faces))
    atlas = xatlas.Atlas()
    atlas.add_mesh(points.astype(np.float32), faces.astype(np.uint32))
    packing = xatlas.PackOptions()
    packing.resolution = ATLAS
    packing.padding = 4
    packing.bilinear = True
    atlas.generate(xatlas.ChartOptions(), packing)
    mapping, triangles, uvs = atlas[0]
    trimesh.Trimesh(points[mapping], triangles, process=False,
                    visual=trimesh.visual.TextureVisuals(uv=uvs)).export(out)
    return out


PIXEL_MATCH = """
import pathlib, sys
sys.path.insert(0, {lab!r})
from image_to_3dlab import photo_paint as pp
positions, uvs, faces, texture = pp.read_glb(pathlib.Path({model!r}))
views, scale = pp.load_views(pathlib.Path({views!r}))
painted, weight = pp.paint_texture(texture, positions, uvs, faces, views, scale,
                                   settings=pp.Settings(match_colour=False))
pathlib.Path({out!r}).write_bytes(pp.replace_base_colour(pathlib.Path({model!r}).read_bytes(),
                                                         pp.encode_png(painted)))
print(f"pixel match: {{(weight > 0.5).mean():.0%}} of the texture from the picture")
"""

COMPRESS = """
import pathlib, sys
sys.path.insert(0, {scripts!r})
from compress_glb_textures import compress
data, _ = compress(pathlib.Path({model!r}).read_bytes(), max_size={side})
pathlib.Path({out!r}).write_bytes(data)
"""


def finish(raw, picture_cut, finished, faces, views):
    """The raw model slimmed to `faces` and painted cleanly, written to `finished`. `views` is the
    run's camera folder; Pixel Match is skipped only when there is none."""
    steps = finished.with_suffix("")
    steps.mkdir(parents=True, exist_ok=True)
    pruned, slim, unwrap, bake = (steps / f"{name}.glb" for name in ("1_pruned", "2_slim", "3_unwrapped", "4_baked"))
    run([LAB_PYTHON, LAB / "scripts/remove_loose_parts.py", raw, pruned, "--min-faces", SMALLEST_PART],
        steps / "1_pruned.log")
    run([LAB_PYTHON, LAB / "scripts/retopo_repaint.py", pruned, picture_cut, slim, "--faces", faces,
         "--skip-paint", "--skip-bake", "--skip-compress", "--steps-dir", steps / "lab",
         "--blender", BLENDER], steps / "2_slim.log")
    unwrapped(slim, unwrap)
    run([BLENDER, "--background", "--python", HERE / "blender_clean_bake.py", "--", pruned, unwrap,
         bake, ATLAS, FOLD_DEGREES, RAYS], steps / "4_baked.log")
    current = bake
    if views is not None:
        current = steps / "5_matched.glb"
        run([LAB_PYTHON, "-c", PIXEL_MATCH.format(lab=str(LAB), model=str(bake), views=str(views),
                                                 out=str(current))], steps / "5_matched.log")
    run([LAB_PYTHON, "-c", COMPRESS.format(scripts=str(LAB / "scripts"), model=str(current),
                                           out=str(finished), side=ATLAS)], steps / "6_compressed.log")
    return finished

