"""The picture check: a generated piece's colour as the bake will lay it, worked out here before any bake, and failed
when shade leaks in (hub round four, 2026-10-07; the coordinator, after stage one's renders: dark blotches on the comms
desk, comb-like streaks down the locker's side).

    ~/.farm-factory-props/env/bin/python tools/props/library/picture_check.py <labelled folder> ... [--place hub]

A labelled folder is labels.py's: a .ply per library material and picture.obj (the finished model, its faces `seen` or
`unseen` by the picture's camera, its texture the picture's own pixels). Each face of the picture model takes the
material of the nearest labelled face, texel by texel; the detail layer (inside/detail_layer.py, the bake's own) then runs over the
model's texture with each material's flat token colour as the library. Two measures, each a share of the texels:

    dark      patches of the result much darker than both the clean picture there and the piece's main library
              colour, wider than a thin line: shade or a mislabelled dark part come through
    streaks   on faces the camera never saw, thin lines of strong contrast in the result: Pixal3D's guesses come through

A piece fails when either passes its limit. Writes <folder>/predicted.png (the result in the model's UV space) and
flagged.png (the same, flagged texels magenta), and
prints one line per piece; exits 1 when any fails. numpy, trimesh and Pillow; no model, no render.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "inside"))
import detail_layer  # noqa: E402
import library  # noqa: E402

SIDE = 1024
# A dark texel: its L* this far under both its library colour's and its body's.
DARK_LEAK = 15.0
DARK_LIMIT = 0.01
# A streak texel (unseen faces only): its L* this far from its 7 x 7 neighbourhood's mean.
STREAK_STEP = 12.0
STREAK_LIMIT = 0.02


def picture_faces(folder):
    """The picture model's faces: their UV corners, 3D corners, normals, whether seen, and the texture (RGB, 0..1)."""
    scene = trimesh.load(folder / "picture.obj", force="scene")
    corners, points, normals, seen, texture = [], [], [], [], None
    for geometry in scene.geometry.values():
        material = geometry.visual.material
        image = getattr(material, "image", None) or getattr(material, "baseColorTexture", None)
        texture = image if texture is None else texture
        corners.append(geometry.visual.uv[geometry.faces])
        points.append(geometry.triangles)
        normals.append(geometry.face_normals)
        seen.append(np.full(len(geometry.faces), not getattr(material, "name", "").startswith("unseen")))
    picture = np.asarray(texture.convert("RGB").resize((SIDE, SIDE)), dtype=np.float64) / 255
    return np.vstack(corners), np.vstack(points), np.vstack(normals), np.concatenate(seen), picture


def point_materials(folder, middles):
    """Each point's library material: the nearest labelled face's (per texel, as the bake's rays find it; per face
    of the picture model, a large face took one small tool's material whole, 2026-10-07)."""
    names, points, owners = [], [], []
    for index, path in enumerate(sorted(folder.glob("*.ply"))):
        part = trimesh.load(path, process=False)
        names.append(path.stem)
        points.append(part.triangles_center)
        owners.append(np.full(len(part.faces), index))
    _, nearest = cKDTree(np.vstack(points)).query(middles)
    return np.concatenate(owners)[nearest], names


def rasterised(corners, points):
    """Each texel's face (-1 where none) and its point on the model, from the faces' UV corners."""
    face = -np.ones((SIDE, SIDE), dtype=np.int64)
    where = np.zeros((SIDE, SIDE, 3))
    pixel = np.clip(corners, 0.0, 1.0) * [SIDE, SIDE]
    pixel[..., 1] = SIDE - pixel[..., 1]
    for index, (triangle, corner_points) in enumerate(zip(pixel, points)):
        low = np.floor(triangle.min(0)).astype(int)
        high = np.minimum(np.ceil(triangle.max(0)).astype(int), SIDE - 1)
        columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
        centres = np.stack([columns + 0.5, rows + 0.5], -1).reshape(-1, 2)
        first, second, third = triangle
        area = (second[0] - first[0]) * (third[1] - first[1]) - (third[0] - first[0]) * (second[1] - first[1])
        if abs(area) < 1e-9:
            continue
        along = ((second[0] - centres[:, 0]) * (third[1] - centres[:, 1]) -
                 (third[0] - centres[:, 0]) * (second[1] - centres[:, 1])) / area
        across = ((third[0] - centres[:, 0]) * (first[1] - centres[:, 1]) -
                  (first[0] - centres[:, 0]) * (third[1] - centres[:, 1])) / area
        rest = 1.0 - along - across
        inside = (along >= 0) & (across >= 0) & (rest >= 0)
        if not inside.any():
            continue
        weights = np.stack([along, across, rest], -1)[inside]
        row_at, column_at = rows.reshape(-1)[inside], columns.reshape(-1)[inside]
        face[row_at, column_at] = index
        where[row_at, column_at] = weights @ corner_points
    return face, where


def blurred(values, radius=3):
    """A (2 radius + 1) square mean."""
    padded = np.pad(values, radius, mode="edge")
    size = 2 * radius + 1
    return sum(padded[down:down + values.shape[0], across:across + values.shape[1]]
               for down in range(size) for across in range(size)) / size ** 2


def checked(folder, place):
    corners, points, normals, seen, picture = picture_faces(folder)
    face, where = rasterised(corners, points)
    covered = face >= 0
    owner, names = point_materials(folder, where[covered])
    materials = library.resolved(place)
    tokens = np.array([detail_layer.encoded(np.array(materials[name]["colour"])) for name in names])
    texel_face = np.maximum(face, 0)
    slots = np.zeros((SIDE, SIDE), dtype=np.int64)
    slots[covered] = owner
    library_colour = tokens[slots]
    seen_here = seen[texel_face] & covered
    colour, _, _, share = detail_layer.laid(library_colour, np.zeros((SIDE, SIDE)), np.zeros((SIDE, SIDE)), picture,
                                            slots, normals[texel_face], covered, seen_here)
    lightness = detail_layer.lab(colour)[..., 0]
    main = np.bincount(slots[covered]).argmax()
    dark = covered & (lightness < detail_layer.lab(picture)[..., 0] - DARK_LEAK) & \
        (lightness < detail_layer.lab(tokens[main])[0] - DARK_LEAK)
    dark = detail_layer.dilated(detail_layer.eroded(dark, detail_layer.BLOB_RADIUS), detail_layer.BLOB_RADIUS)
    unseen = covered & ~seen_here
    streaks = unseen & (np.abs(lightness - blurred(lightness)) > STREAK_STEP)
    shown = (np.clip(colour, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(shown).save(folder / "predicted.png")
    shown[dark | streaks] = (255, 0, 255)
    Image.fromarray(shown).save(folder / "flagged.png")
    found = {"piece": folder.name, "dark": round(float(dark.sum() / covered.sum()), 4),
             "streaks": round(float(streaks.sum() / max(1, unseen.sum())), 4), "detail": round(share, 3)}
    found["pass"] = found["dark"] <= DARK_LIMIT and found["streaks"] <= STREAK_LIMIT
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folders", nargs="+", type=pathlib.Path)
    parser.add_argument("--place", default="hub")
    arguments = parser.parse_args()
    failed = 0
    for folder in arguments.folders:
        found = checked(folder, arguments.place)
        print(json.dumps(found))
        failed += not found["pass"]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
