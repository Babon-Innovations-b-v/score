"""The prop route's A-pose outline check: the built person at its bind pose, drawn as a mask from the close-up's own
camera (the one labels.py paints by), set against the close-up's cut-out, and the same for the raw Pixal3D model.
Measures that the rig, the parts and the tucks kept the shape the picture asked for. CPU only.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/outline.py <take> <fit rig.npz> <body.glb> \
        --out <outline.json>

The built mesh lies in the skeleton's frame; it is carried back to the raw model's (prop_rig.py's stand undone, then
the finish's turn undone: labels.finish_turn refined by labels.onto_finished) and projected as labels.seen_faces
projects. Recorded: each mask's intersection over union with the cut-out (alpha over half), the drop from the raw
model's, and the widths of the bands (head, chest, waist, hips, knees) as shares of the figure's height in pixels.
Gate: the IoU drops no more than IOU_DROP and no band moves more than BAND_SHARE of the figure's height.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw

MAKER = pathlib.Path(__file__).resolve().parent
LIBRARY = MAKER.parents[1] / "props" / "library"
sys.path.insert(0, str(LIBRARY))
sys.path.insert(0, str(LIBRARY.parent))
sys.path.insert(0, str(MAKER.parent / "people"))

import joins  # noqa: E402
import labels  # noqa: E402

IOU_DROP = 0.01
BAND_SHARE = 0.01
# Band heights as shares of the figure from its top.
BANDS = {"head": 0.06, "chest": 0.25, "waist": 0.38, "hips": 0.47, "knees": 0.72}


def mask(points, faces, camera, shape):
    """The mesh's silhouette from the close-up's camera (labels.seen_faces' projection), filled triangle by triangle."""
    height, width = shape
    turned = points @ labels.VIEW_TURN.T
    focal = 1 / np.tan(camera["camera_angle_x"] / 2)
    distance = -camera["frames"][0]["transform_matrix"][1][3]
    depth = distance - turned[:, 2]
    column = (0.5 + 0.5 * turned[:, 0] * focal / depth) * width
    row = (0.5 - 0.5 * turned[:, 1] * focal / depth) * height
    picture = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(picture)
    for face in faces:
        draw.polygon([(column[corner], row[corner]) for corner in face], fill=1)
    return np.asarray(picture, bool)


def iou(first, second):
    return float((first & second).sum() / max((first | second).sum(), 1))


def bands(silhouette):
    """Each band's width in pixels over the figure's height in pixels."""
    rows = np.flatnonzero(silhouette.any(1))
    top, tall = rows.min(), rows.max() - rows.min()
    found = {}
    for name, share in BANDS.items():
        row = silhouette[int(top + share * tall)]
        columns = np.flatnonzero(row)
        found[name] = float(np.ptp(columns) / tall) if len(columns) else 0.0
    return found


def built_on_raw(take, fit_rig, built_points):
    """The built points carried back into the raw model's frame."""
    finished = (built_points - fit_rig["shift"]) / fit_rig["scale"] @ fit_rig["turn"]
    raw = labels.welded(trimesh.load(labels.PIXAL / f"{take}.glb", force="mesh", process=False))
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    matrix, _ = labels.onto_finished(raw.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                     labels.finish_turn(take))
    return (finished - matrix[:3, 3]) @ np.linalg.inv(matrix[:3, :3]).T, raw


def built_mesh(path):
    """The built outfit's points and triangles at the bind pose (every surface but the far body)."""
    document, blob = joins.read_glb(path)
    points, faces, offset = [], [], 0
    for part in [part for parts in joins.outfits(document, blob).values() for part in parts]:
        points.append(part.points)
        faces.append(part.faces + offset)
        offset += len(part.points)
    return np.concatenate(points), np.concatenate(faces)


def measure(take, fit_path, body_path):
    views = labels.PIXAL / f"{take}.svviews"
    camera = json.loads((views / "transforms.json").read_text())
    cut_out = np.asarray(Image.open(views / "input.png").convert("RGBA"))[..., 3] > 127
    points, faces = built_mesh(body_path)
    on_raw, raw = built_on_raw(take, np.load(fit_path), points)
    raw_mask = mask(raw.vertices, raw.faces, camera, cut_out.shape)
    built_mask = mask(on_raw, faces, camera, cut_out.shape)
    raw_bands, built_bands = bands(raw_mask), bands(built_mask)
    moved = {name: round(abs(built_bands[name] - raw_bands[name]), 4) for name in BANDS}
    record = {"take": take, "iou_raw": round(iou(raw_mask, cut_out), 4), "iou_built": round(iou(built_mask, cut_out), 4),
              "bands_raw": raw_bands, "bands_built": built_bands, "band_moved": moved}
    record["iou_drop"] = round(record["iou_raw"] - record["iou_built"], 4)
    record["pass"] = record["iou_drop"] <= IOU_DROP and max(moved.values()) <= BAND_SHARE
    return record, raw_mask, built_mask, cut_out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("take")
    parser.add_argument("fit", type=pathlib.Path)
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    options = parser.parse_args()
    record, raw_mask, built_mask, cut_out = measure(options.take, options.fit, options.body)
    options.out.write_text(json.dumps(record, indent=1))
    picture = np.stack([cut_out, raw_mask, built_mask], -1).astype(np.uint8) * 255
    Image.fromarray(picture).save(options.out.with_suffix(".png"))
    print(f"outline: {'pass' if record['pass'] else 'FAIL'} iou raw {record['iou_raw']} built {record['iou_built']}; "
          f"{options.out}")


if __name__ == "__main__":
    main()
