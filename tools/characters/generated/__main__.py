"""A generated person's hair split off and regrown as strands (#223): see this package's docstring.

    python -m tools.characters.generated <model.glb> <style.json> <out folder> --height <m> --closeup <photo>

Writes to <out>: `labels.png` (the hair's and beard's triangles tinted red on the paint, four sides), `kept.glb` (the
model without its hair and beard, its own texture), `groom.npz` (the scalp, the neck's back where the model had none,
the skin under the beard, the strands, the head's frame), `fibre.json` (the strands' finishes), `stats.json` (the
label shares, the scalp, the strands) and prints one line.
"""
import argparse
import json
import pathlib

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from skimage.color import lab2rgb

from tools.characters.generated import beard, cover, curl, fibre, flow, labels, pictures, scalp, strands, volume
from tools.characters.whole import hair

SCALP_DARK = 0.45  # the scalp painted this share towards the hair's colour where the roots are full
SCALP_DARK_M = 0.008  # rising over this from the seam
HAIRLINE_TABLE_SLACK_M = 0.02  # a hair edge this far under hair.py's HAIRLINE table is still a hairline (not a lock
# hanging by the jaw)
HAIRLINE_NEAR_M = 0.003  # a hair triangle with skin this near is on the hairline
VOLUME_REACH_M = 0.08  # the model's triangles this far round the hair are read for its volume
HEAD_UNDER_EYES_M = 0.08  # skin under this, further than NECK_RADIUS_M off the head's upright, is not the head's or
NECK_RADIUS_M = 0.07  # the neck's (a camel coat reads as skin; a ray meeting it put a bob's ends inside the head)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("style")
    parser.add_argument("out")
    parser.add_argument("--height", type=float, required=True, help="the model's height in m (a person's, a bust's)")
    parser.add_argument("--closeup", required=True, help="the close-up photograph the model was made from")
    return parser.parse_args()


def outward(points, faces, middle, axis_only):
    """The triangles' normals turned to face away from `middle` (from its upright when `axis_only`)."""
    normals = volume.face_normals(points, faces)
    away = points[faces].mean(axis=1) - middle
    if axis_only:
        away[:, 1] = 0.0
    return normals * np.sign(np.einsum("pi,pi->p", normals, away) + 1e-12)[:, None]


def hairline_of(points, faces, labelled, skin_like, frame):
    """Places on the hairline: hair triangles' middles with a skin triangle within HAIRLINE_NEAR_M, on the head (not
    lower than HAIRLINE_TABLE_SLACK_M under hair.py's HAIRLINE table)."""
    middles = points[faces].mean(axis=1)
    skin = middles[~labelled & skin_like]
    edge = middles[labelled][cKDTree(skin).query(middles[labelled], distance_upper_bound=HAIRLINE_NEAR_M)[0] < 1.0]
    return edge[hair.over_hairline(edge, frame["eyes"], frame["centre"]) > -HAIRLINE_TABLE_SLACK_M]


def scalp_colours(patch, skin_srgb, hair_srgb, frame):
    """Each scalp point's colour (sRGB): the skin's, darker towards the hair's where the roots are full."""
    grows = strands.grows_here(patch["points"], frame)
    share = SCALP_DARK * np.clip(patch["depth"] / SCALP_DARK_M, 0.0, 1.0) * grows
    return skin_srgb * (1.0 - share[:, None]) + hair_srgb * share[:, None]


def body_of(points, faces, labelled, patch, neck, frame, skin_like=None):
    """The head's skin (and clothes) and the new scalp and neck as one surface: (points, triangles, normals, how many
    of the first triangles are the model's own, which triangles are the head's skin, scalp or neck: those `skin_like`
    marks (all without it) on the head or the neck). The scalp's and neck's normals face out of the head; the skin's
    are as wound (`volume.hair_volume` turns them outward)."""
    near = np.linalg.norm(points[faces].mean(axis=1) - frame["centre"], axis=1) < scalp.HEAD_M
    skin_faces = faces[near & ~labelled]
    middles = points[skin_faces].mean(axis=1)
    off_axis = np.linalg.norm((middles - frame["centre"])[:, [0, 2]], axis=1)
    head_or_neck = (middles[:, 1] > frame["eyes_middle"][1] - HEAD_UNDER_EYES_M) | (off_axis < NECK_RADIUS_M)
    skin = head_or_neck & (True if skin_like is None else skin_like[near & ~labelled])
    start = scalp.origin(frame)
    pieces = [(points, skin_faces, volume.face_normals(points, skin_faces)),
              (patch["points"], patch["triangles"], outward(patch["points"], patch["triangles"], start, False))]
    if neck is not None:
        pieces.append((neck[0], neck[1], outward(neck[0], neck[1], start, True)))
    offset, all_points, all_faces, all_normals = 0, [], [], []
    for piece_points, piece_faces, piece_normals in pieces:
        all_points.append(piece_points)
        all_faces.append(piece_faces + offset)
        all_normals.append(piece_normals)
        offset += len(piece_points)
    rays = np.concatenate([skin, np.ones(sum(len(item) for item in all_faces[1:]), dtype=bool)])
    return np.vstack(all_points), np.vstack(all_faces), np.vstack(all_normals), len(skin_faces), rays


def model_near_hair(points, faces, labelled):
    """The model's triangles within VOLUME_REACH_M of the hair's box and their labels: ((points, triangles), labels)."""
    hair_places = points[faces[labelled]].reshape(-1, 3)
    low, high = hair_places.min(axis=0) - VOLUME_REACH_M, hair_places.max(axis=0) + VOLUME_REACH_M
    middles = points[faces].mean(axis=1)
    near = ((middles > low) & (middles < high)).all(axis=1)
    return (points, faces[near]), labelled[near]


def scalp_hair(points, faces, paint, frame, labelled, style):
    """The scalp, the model's points with its skin laid onto it, the neck's back, the hair's volume and its strands:
    {patch, laid, neck, space, counts, points, radius}. `paint` is (colours per triangle, uv, texture)."""
    colours, uv, texture = paint
    skin_like = labels.skin_like(colours)
    patch = scalp.scalp_patch(points, faces, labelled, frame)
    points = scalp.laid(points, faces, labelled, patch, frame)
    neck = scalp.neck_back(points, faces, labelled, skin_like, frame) if patch["open_neck"] else None
    body = body_of(points, faces, labelled, patch, neck, frame, skin_like)
    model, model_labels = model_near_hair(points, faces, labelled)
    space = volume.hair_volume(model, model_labels, body, np.random.default_rng(strands.SEED), scalp.origin(frame))
    field = flow.flow_field(points, faces, uv, texture, labelled, space)
    hairline = hairline_of(points, faces, labelled, skin_like, frame)
    counts, strand_points, radius = strands.regrown(space, field, patch, (points, faces[~labelled & skin_like]),
                                                    hairline, frame, style)
    return {"patch": patch, "laid": points, "neck": neck, "space": space, "counts": counts, "points": strand_points,
            "radius": radius}


def facial_hair(points, faces, colours, frame, labelled, skin_srgb, style):
    """The beard split off and regrown: {labels, smooth (points), colours (per point), counts, points, radius,
    srgb, lab}."""
    bearded, model = beard.beard_labels(points, faces, colours, frame, labelled)
    smooth, normals = beard.beard_split(points, faces, bearded)
    beard_srgb = lab2rgb(model[0][None, None])[0, 0]
    counts, strand_points, radius = beard.beard_strands(smooth, faces, bearded, normals, frame, style)
    return {"labels": bearded, "smooth": smooth, "counts": counts, "points": strand_points, "radius": radius,
            "colours": beard.stubble_colours(smooth, faces, bearded, skin_srgb, beard_srgb), "srgb": beard_srgb,
            "lab": model[0]}


def beard_record(points, faces, grown):
    """The beard's arrays for groom.npz (empty without a beard)."""
    if grown is None:
        return {"beard_skin_points": np.zeros((0, 3)), "beard_skin_triangles": np.zeros((0, 3), np.int64),
                "beard_skin_colours": np.zeros((0, 3)), "beard_counts": np.zeros(0, np.int64),
                "beard_points": np.zeros((0, 3), np.float32), "beard_radius": np.zeros(0, np.float32)}
    triangles = faces[grown["labels"]]
    used, renumbered = np.unique(triangles, return_inverse=True)
    return {"beard_skin_points": grown["smooth"][used], "beard_skin_triangles": renumbered.reshape(-1, 3),
            "beard_skin_colours": grown["colours"][used], "beard_counts": grown["counts"],
            "beard_points": grown["points"].astype(np.float32), "beard_radius": grown["radius"].astype(np.float32)}


def kept_written(path, points, faces, uv, removed, out):
    """The model without the `removed` triangles, its own texture, written to <out>/kept.glb."""
    material = trimesh.load(str(path), force="mesh", process=False).visual.material
    kept = trimesh.Trimesh(points, faces[~removed], visual=trimesh.visual.TextureVisuals(uv=uv, material=material),
                           process=False)
    kept.export(str(out / "kept.glb"))


def stats_of(points, faces, frame, labelled, models, grown, finish, bearded):
    """The run's numbers for stats.json (`grown` with its `coverage` and `curl`)."""
    head = np.linalg.norm(points[faces].mean(axis=1) - frame["centre"], axis=1) < scalp.HEAD_M
    stats = {"hair_triangles": int(labelled.sum()), "triangles": int(len(faces)),
             "hair_share_of_head": round(float(labelled[head].mean()), 4),
             "hair_share_of_model": round(float(labelled.mean()), 4),
             "hair_paint_lab": np.round(models["hair"][0], 2).tolist(),
             "scalp_points": int(len(grown["patch"]["points"])), "open_neck": bool(grown["patch"]["open_neck"]),
             "strands": int(len(grown["counts"])),
             "hair_volume_l": round(float(grown["space"]["filled"].sum()) * volume.VOXEL_M ** 3 * 1000.0, 3),
             "fibre": {key: finish["hair"][key] for key in ("melanin", "redness", "white_share")},
             "coverage": grown["coverage"], "curl": grown["curl"]}
    if bearded is not None:
        stats.update({"beard_triangles": int(bearded["labels"].sum()),
                      "beard_share_of_head": round(float(bearded["labels"][head].mean()), 4),
                      "beard_strands": int(len(bearded["counts"])),
                      "beard_fibre": {key: finish["beard"][key] for key in ("melanin", "redness", "white_share")}})
    return stats


def main():
    args = arguments()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    style = json.loads(pathlib.Path(args.style).read_text())
    points, faces, uv, texture = labels.loaded(args.model, args.height)
    colours = labels.face_colours(faces, uv, texture)
    frame = labels.head_frame(points, faces, colours)
    labelled, models = labels.hair_labels(points, faces, colours, frame, bool(style.get("beard")), style["reach_m"])
    read_curl = curl.photo_curl(args.closeup)
    style = curl.styled(style, read_curl)
    skin_srgb = lab2rgb(models["skin"][0][None, None])[0, 0]
    hair_srgb = lab2rgb(models["hair"][0][None, None])[0, 0]
    bearded = facial_hair(points, faces, colours, frame, labelled, skin_srgb, style) if style.get("beard") else None
    shown = labelled | (bearded["labels"] if bearded is not None else False)
    pictures.label_picture(points, faces, colours, shown, frame, out / "labels.png")
    grown = scalp_hair(points, faces, (colours, uv, texture), frame, labelled, style)
    grown["curl"] = read_curl
    grown["coverage"] = cover.coverage(grown["points"].reshape(len(grown["counts"]), -1, 3), points, faces,
                                       labelled, grown["space"], scalp.origin(frame),
                                       np.random.default_rng(strands.SEED))
    closeup = labels.closeup_hair(args.closeup)
    finish = {"hair": fibre.fibre_of(closeup["srgb"], closeup["lab"], closeup["spread"])}
    if bearded is not None:
        finish["beard"] = fibre.fibre_of(bearded["srgb"], bearded["lab"])
    kept_written(args.model, grown["laid"], faces, uv, shown, out)
    patch, neck = grown["patch"], grown["neck"]
    np.savez_compressed(
        out / "groom.npz", scalp_points=patch["points"], scalp_triangles=patch["triangles"],
        scalp_colours=scalp_colours(patch, skin_srgb, hair_srgb, frame),
        neck_points=neck[0] if neck is not None else np.zeros((0, 3)),
        neck_triangles=neck[1] if neck is not None else np.zeros((0, 3), np.int64), skin_colour=skin_srgb,
        counts=grown["counts"], points=grown["points"].astype(np.float32), radius=grown["radius"].astype(np.float32),
        eyes=frame["eyes"], centre=frame["centre"], top=frame["top"], low=points[:, 1].min(), height=args.height,
        **beard_record(points, faces, bearded))
    (out / "fibre.json").write_text(json.dumps(finish, indent=1))
    stats = stats_of(points, faces, frame, labelled, models, grown, finish, bearded)
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    print(f"generated hair: {stats['strands']} strands, hair {stats['hair_share_of_head']:.1%} of the head's "
          f"triangles, beard strands {stats.get('beard_strands', 0)}, outer surface covered "
          f"{stats['coverage']['outer']:.1%}, curl {read_curl['swing_deg']} deg -> {out}", flush=True)


if __name__ == "__main__":
    main()
