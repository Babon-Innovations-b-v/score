"""The prop route's two printed plates on a person (the plan's print rule, tools/props/library/CLAUDE.md: a print is a
plate placed on purpose): the face, cut from the close-up and laid on the head's part the close-up's camera sees, and
the flag patch, drawn here, laid on the parts judged "printed flag patch". Every other surface stays one flat library
colour. Plain CPU geometry and pictures on files on disk.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_prints.py <take> <fit rig.npz> <parts.npz> \
        <prints.npz>

The face print is the overseer's decision (2026-10-10, #5), taken in the owner's absence; the owner may veto it, and
then the head is the person's skin colour only. The close-up's face is matched to the person's own skin colour (each
channel scaled so the face's median is the library's skin token) and runs out into that colour at its edge, so the
print meets the head's flat skin without a seam.

Writes, per printed part (by its number in parts.npz): `uv_<part>`, every fit vertex's texture place (glTF's, v down
the picture; NaN where the part has none), `plain_uv_<part>` (the place of a texel of the plain colour, for the
part's points the camera does not see and its tucks) and `image_<part>` (the PNG's bytes).
"""
import argparse
import io
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))

import outline  # noqa: E402
from outline import labels  # noqa: E402

# A point is printed where a face round it looks at the camera at least this much (cosine): grazing faces smear.
FACING = 0.3
# The face picture's margin round the printed points, and the band its edge runs out into the skin colour over, in
# pixels of the close-up.
MARGIN = 12
FEATHER = 8.0
# The flag (people/paint.py's FLAG red and STAR yellow, sRGB): a red field, a five-pointed star near the hoist.
FLAG_RED, STAR = (184, 48, 38), (246, 206, 92)
FLAG_SIZE = (300, 200)
STAR_AT, STAR_RADIUS = (0.22, 0.3), 0.18


def camera_of(take):
    """The close-up's camera (the batch's transforms.json) and its picture (RGB)."""
    views = labels.PIXAL / f"{take}.svviews"
    picture = np.asarray(Image.open(views / "input.png").convert("RGB"))
    return json.loads((views / "transforms.json").read_text()), picture


def projected(points, camera, shape):
    """Each raw-frame point's (row, column) in the close-up, as labels.seen_faces projects."""
    height, width = shape
    turned = points @ labels.VIEW_TURN.T
    focal = 1 / np.tan(camera["camera_angle_x"] / 2)
    depth = -camera["frames"][0]["transform_matrix"][1][3] - turned[:, 2]
    return (0.5 - 0.5 * turned[:, 1] * focal / depth) * height, (0.5 + 0.5 * turned[:, 0] * focal / depth) * width


def seen_points(on_raw, faces, part_faces, camera, shape):
    """The faces of `part_faces` the camera sees head on (facing it past FACING, not hidden) and their points."""
    mesh = trimesh.Trimesh(on_raw, faces, process=False)
    seen, _, _ = labels.seen_faces(mesh, camera, shape)
    facing = (mesh.face_normals @ labels.VIEW_TURN.T)[:, 2] > FACING
    good = np.zeros(len(faces), bool)
    good[part_faces] = seen[part_faces] & facing[part_faces]
    found = np.zeros(len(on_raw), bool)
    found[faces[good].ravel()] = True
    return found, faces[good]


def linear(srgb):
    shares = np.asarray(srgb, float) / 255
    return np.where(shares <= 0.04045, shares / 12.92, ((shares + 0.055) / 1.055) ** 2.4)


def to_srgb(values):
    values = np.clip(values, 0.0, 1.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * values ** (1 / 2.4) - 0.055) * 255


def png(picture):
    buffer = io.BytesIO()
    Image.fromarray(picture.astype(np.uint8)).save(buffer, format="PNG")
    return np.frombuffer(buffer.getvalue(), np.uint8)


def face_print(picture, rows, columns, triangles, skin_linear):
    """The face plate: the close-up cut round the printed points (`triangles`, the seen faces' corners as point
    numbers into `rows` and `columns`), matched to the skin colour, running out into it at the edge, with a border of
    plain skin. (picture, its top-left pixel in the close-up, the plain texel's place)."""
    seen = np.unique(triangles)
    top, left = int(rows[seen].min()) - MARGIN, int(columns[seen].min()) - MARGIN
    bottom, right = int(np.ceil(rows[seen].max())) + MARGIN, int(np.ceil(columns[seen].max())) + MARGIN
    crop = linear(picture[max(top, 0):bottom, max(left, 0):right])
    drawn = Image.new("1", (crop.shape[1], crop.shape[0]), 0)
    pen = ImageDraw.Draw(drawn)
    for triangle in triangles:
        pen.polygon([(columns[corner] - max(left, 0), rows[corner] - max(top, 0)) for corner in triangle], fill=1)
    inside = np.asarray(drawn, bool)
    crop = crop * (np.asarray(skin_linear) / np.median(crop[inside], axis=0))
    blend = np.clip(ndimage.distance_transform_edt(inside) / FEATHER, 0.0, 1.0)[..., None]
    plate = crop * blend + np.asarray(skin_linear) * (1 - blend)
    framed = np.pad(to_srgb(plate), ((MARGIN, MARGIN), (MARGIN, MARGIN), (0, 0)), mode="edge")
    framed[:MARGIN // 2], framed[-MARGIN // 2:] = to_srgb(np.asarray(skin_linear)), to_srgb(np.asarray(skin_linear))
    return framed, (max(top, 0) - MARGIN, max(left, 0) - MARGIN), (0.5 / framed.shape[1], 0.5 / framed.shape[0])


def flag_picture():
    """The flag patch drawn: a red field and a yellow five-pointed star near the hoist."""
    width, height = FLAG_SIZE
    picture = Image.new("RGB", FLAG_SIZE, FLAG_RED)
    middle = np.array([STAR_AT[0] * width, STAR_AT[1] * height])
    angles = -np.pi / 2 + np.arange(10) * np.pi / 5
    radii = np.where(np.arange(10) % 2 == 0, STAR_RADIUS * height, 0.382 * STAR_RADIUS * height)
    ImageDraw.Draw(picture).polygon([tuple(middle + radius * np.array([np.cos(angle), np.sin(angle)]))
                                     for angle, radius in zip(angles, radii)], fill=STAR)
    return np.asarray(picture)


def prints(take, fit_path, parts_path):
    """The printed parts' arrays (the module's header)."""
    fit_rig, parts = np.load(fit_path), np.load(parts_path)
    part_of = fit_rig["part_of"] if "part_of" in fit_rig.files else parts["part_of"]
    camera, picture = camera_of(take)
    on_raw, _ = outline.built_on_raw(take, fit_rig, fit_rig["points"])
    faces = fit_rig["faces"]
    rows, columns = projected(on_raw, camera, picture.shape[:2])
    found = {}
    for number, part in enumerate(parts["parts"]):
        material = str(parts["materials"][number]) if "materials" in parts.files else ""
        name = str(parts["names"][number])
        if name != "skin_head" and material != "printed flag patch":
            continue
        seen, triangles = seen_points(on_raw, faces, np.flatnonzero(part_of == part), camera, picture.shape[:2])
        if seen.sum() < 3:
            continue
        uv = np.full((len(on_raw), 2), np.nan)
        if name == "skin_head":
            plate, (top, left), plain = face_print(picture, rows, columns, triangles, parts["colours"][number])
            uv[seen] = np.stack([(columns[seen] - left) / plate.shape[1], (rows[seen] - top) / plate.shape[0]], 1)
        else:
            plate = flag_picture()
            span_rows, span_columns = rows[seen], columns[seen]
            uv[seen] = np.stack([(span_columns - span_columns.min()) / np.ptp(span_columns),
                                 (span_rows - span_rows.min()) / np.ptp(span_rows)], 1)
            plain = (0.95, 0.95)
        found[f"uv_{int(part)}"] = uv
        found[f"plain_uv_{int(part)}"] = np.array(plain)
        found[f"image_{int(part)}"] = png(plate)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("take")
    parser.add_argument("fit", type=pathlib.Path)
    parser.add_argument("parts", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    options = parser.parse_args()
    found = prints(options.take, options.fit, options.parts)
    np.savez_compressed(options.out, **found)
    print(f"prints: {sorted(key[6:] for key in found if key.startswith('image_'))} parts; {options.out}", flush=True)


if __name__ == "__main__":
    main()
