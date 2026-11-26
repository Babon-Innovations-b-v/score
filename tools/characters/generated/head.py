"""A generated head mended in one ordered run (#223): each step reads what the one before it made, on one head.

    python -m tools.characters.generated.head <model.glb> <cut-out.png> <close-up photo> <marks.json> <out> \
        --height <m>

1. **Colour** (`colour.py`): the paint toned toward the cut-out photo the model was made from, garment by garment.
2. **Eyes** (`eyes.py`): the face module's eyeball set behind each painted eye, the painted floor pushed back; the
   photo's own iris unrolled onto the eyeball's UV (`eyes.iris_picture`).
3. **Lids** (`lids.py`): the openings laid on the photo's (`marks.json`, `marks.py`), the lids thin over the ball, the
   lashes as many and as long as the photo shows (`lids.lash_share`). No brows are regrown and the painted ones stay:
   the photo's own brows come with the skin (round 1, 2026-11-26: regrown strands over the leftover painted blocks
   read as smudges).
4. **Skin** (`skin.py`) on the lids' mended mesh: the photo reaches the lid margins (the lids lie on the photo's, so
   no clearance from the eye's floor), its brows painted on, the model's own paint on the skin given the photo
   skin's colour (`skin.paint_toned`) and its dark baked shading lifted where the photo does not reach
   (`skin.paint_shade`); registered on the raw paint (the toning moves the face's clusters apart), its fade toned to
   that paint.
5. The hair (later) and the swap onto the body (`head_swap.py`) follow.

Writes <out>/colour.glb and colour.json (not with --keep-paint), <out>/eyes/, <out>/lids/ and <out>/skin/ (each
step's own files), <out>/iris.png (the photo's iris on the eyeball's UV, sRGB), <out>/head.glb (the model's own
units and frame: the mended head in its paint, its skin toned to the photo's, the eyeballs wearing iris.png, the
cornea's clear shell) and stats.json; prints one line.
The face texture (skin/face.png on its planar UV), the library skin and the lashes are laid by `blender_head.py`.
"""
import argparse
import json
import pathlib

import numpy as np
import trimesh
from PIL import Image

from tools.characters.generated import colour, eyes, lids, skin

SCLERA_LINEAR = (0.68, 0.58, 0.5)  # score_lib's face_sclera diffuse colour: the eyeball's white in head.glb


def picture(linear):
    """A linear picture (0 to 1) as an 8-bit sRGB image."""
    return Image.fromarray(np.round(skin.encoded(linear) * 255.0).astype(np.uint8))


def textured_mesh(points, triangles, uv, image):
    """A trimesh mesh of `points` (one UV each) wearing `image` as its base colour."""
    material = trimesh.visual.material.PBRMaterial(baseColorTexture=image, metallicFactor=0.0, roughnessFactor=0.5)
    return trimesh.Trimesh(points, triangles, visual=trimesh.visual.TextureVisuals(uv=uv, material=material),
                           process=False)


def corners_welded(points, triangles, corner_uv):
    """A mesh with UVs per triangle corner as one with a point per distinct (point, UV): (points, triangles, uv)."""
    keys = np.column_stack([triangles.reshape(-1), np.round(corner_uv.reshape(-1, 2) * 1e6).astype(np.int64)])
    unique, first, index = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return points[unique[:, 0]], index.reshape(-1, 3), corner_uv.reshape(-1, 2)[first]


def head_scene(mended, texture, eyes_npz, iris):
    """head.glb's scene (the model's own units): the mended head in its paint, the eyeballs in the iris picture, the
    cornea's clear shell."""
    scene = trimesh.Scene()
    scene.add_geometry(textured_mesh(*corners_welded(*mended), picture(texture)), geom_name="head")
    eye_points, eye_triangles, eye_uv = corners_welded(eyes_npz["eyes.points"], eyes_npz["eyes.triangles"],
                                                       eyes_npz["eyes.uv"])
    scene.add_geometry(textured_mesh(eye_points, eye_triangles, eye_uv, picture(iris)), geom_name="eyes")
    clear = trimesh.visual.material.PBRMaterial(baseColorFactor=[255, 255, 255, 20], alphaMode="BLEND",
                                                metallicFactor=0.0, roughnessFactor=0.0)
    cornea = trimesh.Trimesh(eyes_npz["cornea.points"], eyes_npz["cornea.triangles"], process=False)
    cornea.visual = trimesh.visual.TextureVisuals(material=clear)
    scene.add_geometry(cornea, geom_name="cornea")
    return scene


def made(model, cutout, photo_path, marks_path, out, height, toning=True):
    """The whole ordered run for one head into `out`; each step's stats by its name. Without `toning` the model keeps
    its paint as made (round 1, 2026-11-26: on a bearded man's head `colour.py` joined his skin, hair and beard into
    one garment and moved its dark median to the photo's skin, the ears and neck cream)."""
    out.mkdir(parents=True, exist_ok=True)
    toned = out / "colour.glb" if toning else model
    if toning:
        colour.toned(model, cutout, toned, out / "colour.json")
    points, triangles, uv, texture = eyes.loaded(toned)
    scale = height / float(np.ptp(points[:, 1]))
    photo = np.asarray(Image.open(photo_path).convert("RGB"), np.float64) / 255.0
    marks = json.loads(pathlib.Path(marks_path).read_text())
    _, ict = eyes.face_modules()
    model_ict = ict.load()
    sources = {side: eyes.ict_eye(model_ict, side) for side in ("right", "left")}
    eye_result = eyes.made(points * scale, triangles, uv, texture, photo, sources)
    (out / "eyes").mkdir(exist_ok=True)
    eyes.written(eye_result, scale, out / "eyes")
    eyes_npz = dict(np.load(out / "eyes" / "eyes.npz"))
    face, _ = eyes.face_modules()
    iris, iris_stats = eyes.iris_picture(photo, marks, SCLERA_LINEAR, face.IRIS_UV)
    picture(iris).save(out / "iris.png")
    lid_result = lids.made(points * scale, triangles, uv, texture, photo, marks, eyes_npz, eye_result["stats"], scale,
                           brows_grown=False)
    (out / "lids").mkdir(exist_ok=True)
    lids.written(lid_result, scale, out / "lids")
    mesh = (lid_result["points"], lid_result["triangles"])
    painted = skin.corner_split(*mesh, lid_result["uv"])
    pupils_at = np.array(eye_result["stats"]["pupils_m"])
    _, _, _, raw = eyes.loaded(model)
    skin_stats, toned = skin.repainted_written(mesh, painted, texture, photo, pupils_at, np.zeros((0, 3)),
                                               out / "skin", scale, raw)
    head_scene((lid_result["points"] / scale, lid_result["triangles"], lid_result["uv"]), toned, eyes_npz,
               iris).export(out / "head.glb")
    return {"eyes": eye_result["stats"], "iris": iris_stats, "lids": lid_result["stats"], "skin": skin_stats}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("model", type=pathlib.Path, help="the raw TRELLIS.2 head glb")
    parser.add_argument("cutout", type=pathlib.Path, help="the cut-out photo the model was made from")
    parser.add_argument("photo", type=pathlib.Path, help="the head's close-up photo")
    parser.add_argument("marks", type=pathlib.Path, help="marks.py's landmarks of the close-up")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, required=True, help="the model's height in metres as drawn")
    parser.add_argument("--keep-paint", action="store_true", help="skip the colour step (the paint as made)")
    return parser.parse_args()


def main():
    options = arguments()
    stats = made(options.model, options.cutout, options.photo, options.marks, options.out, options.height,
                 not options.keep_paint)
    (options.out / "stats.json").write_text(json.dumps(stats, indent=1))
    print(f"head: {options.out}/head.glb, eyes {stats['eyes']['eye_diameter_mm']} mm, pupil share "
          f"{stats['iris']['pupil_share']}, lashes {stats['lids']['lashes']} (share {stats['lids']['lash_share']}), "
          f"skin detail correlation {stats['skin']['detail_correlation_after']}, "
          f"{stats['skin']['points_with_photo']} points wear the photo, {stats['skin']['paint_lifted_points']} "
          f"dark painted points lifted", flush=True)


if __name__ == "__main__":
    main()
