"""The part splitters side by side (job parts-test, 2026-10-09): every method's split of every take drawn in flat part
colours from the close-up's camera and from a turned view, scored three ways (split_compare.py), with its seconds and
euros, written as one page.

    python tools/props/library/split_page.py <run folder> <page folder>

Writes <page folder>/index.html and its pictures, and <run folder>/scores.json. The drawing is a point splat: the
model's surface sampled densely and each pixel taking its nearest point's part, lit flat by the face's facing; no
model and no Blender runs.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import labels  # noqa: E402
import split_compare  # noqa: E402

NAMES = {"partcrafter": "PartCrafter", "segvigen": "SegviGen", "segvigen_guided": "SegviGen guided",
         "geosam2_guided": "GeoSAM2 guided"}
SAMPLES = 3_000_000
# The turned view: the model turned this far about its up axis, seen by the same camera.
TURN_DEGREES = 140.0
# Holes in the splat up to this many pixels across are filled from their nearest drawn pixel.
HOLE = 3
LIGHT = np.array([-0.35, 0.55, 0.76])
SHOWN = 360
# Part colours, largest part first: a qualitative set that reads on light and dark pages.
PART_COLOURS = np.array([(78, 121, 167), (242, 142, 43), (89, 161, 79), (225, 87, 89), (176, 122, 161),
                         (237, 201, 72), (118, 183, 178), (255, 157, 167), (156, 117, 95), (186, 176, 172),
                         (31, 119, 180), (174, 199, 232), (255, 127, 14), (152, 223, 138), (214, 39, 40),
                         (197, 176, 213), (140, 86, 75), (227, 119, 194), (188, 189, 34), (23, 190, 207)],
                        dtype=float)


def camera_of(take):
    return json.loads((labels.PIXAL / f"{take}.svviews" / "transforms.json").read_text())


def surface_points(mesh):
    """Dense points on the model in the camera's frame (labels.VIEW_TURN) with each one's face."""
    points, faces = mesh.sample(SAMPLES, return_index=True, seed=0)
    points = np.vstack([points, mesh.triangles_center]) @ labels.VIEW_TURN.T
    return points, np.r_[faces, np.arange(len(mesh.faces))]


def turn_about_up(degrees):
    """The rotation by `degrees` about the up axis."""
    angle = np.radians(degrees)
    return np.array([[np.cos(angle), 0.0, np.sin(angle)], [0.0, 1.0, 0.0], [-np.sin(angle), 0.0, np.cos(angle)]])


def projected(points, camera, shape):
    """Each point's pixel and depth through the close-up's camera (labels.seen_faces' projection)."""
    height, width = shape
    focal = 1 / np.tan(camera["camera_angle_x"] / 2)
    depth = -camera["frames"][0]["transform_matrix"][1][3] - points[:, 2]
    column = ((0.5 + 0.5 * points[:, 0] * focal / depth) * width).astype(int)
    row = ((0.5 - 0.5 * points[:, 1] * focal / depth) * height).astype(int)
    return row, column, depth


def splat(points, faces, camera, shape):
    """Each pixel's nearest face (-1 where none), its small holes filled from the nearest drawn pixel."""
    row, column, depth = projected(points, camera, shape)
    inside = (row >= 0) & (row < shape[0]) & (column >= 0) & (column < shape[1])
    order = np.argsort(-depth[inside])  # far first, so the nearest point is written last
    found = np.full(shape, -1)
    found[row[inside][order], column[inside][order]] = faces[inside][order]
    drawn = found >= 0
    closed = ndimage.binary_closing(drawn, iterations=HOLE)
    distance, (rows, columns) = ndimage.distance_transform_edt(~drawn, return_indices=True)
    fill = closed & ~drawn & (distance <= HOLE)
    found[fill] = found[rows[fill], columns[fill]]
    return found


def coloured(face_image, part_of, normals, areas):
    """The splat in flat part colours (largest part first), lit by facing; RGBA."""
    order = np.argsort(-np.bincount(part_of, weights=areas))
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    drawn = face_image >= 0
    faces = face_image[drawn]
    colour = PART_COLOURS[rank[part_of[faces]] % len(PART_COLOURS)]
    shade = 0.62 + 0.38 * np.abs(normals[faces] @ (LIGHT / np.linalg.norm(LIGHT)))
    picture = np.zeros((*face_image.shape, 4), dtype=np.uint8)
    picture[drawn, :3] = np.clip(colour * shade[:, None], 0, 255).astype(np.uint8)
    picture[drawn, 3] = 255
    return picture


def views(take, mesh):
    """The model's faces as the close-up's camera draws them, straight and turned."""
    camera, shape = camera_of(take), np.asarray(split_compare.picture(take)).shape[:2]
    points, faces = surface_points(mesh)
    normals = mesh.face_normals @ labels.VIEW_TURN.T
    turn = turn_about_up(TURN_DEGREES)
    centre = (points.min(0) + points.max(0)) / 2
    moved = (points - centre) @ turn.T + centre
    return {"front": (splat(points, faces, camera, shape), normals),
            "turned": (splat(moved, faces, camera, shape), normals @ turn.T)}


def saved(picture, path):
    """A picture cropped to what is drawn (with a margin), shown SHOWN wide, as WebP."""
    image = Image.fromarray(picture)
    box = image.getbbox()
    if box:
        margin = int(0.04 * max(image.size))
        box = (max(0, box[0] - margin), max(0, box[1] - margin), min(image.width, box[2] + margin),
               min(image.height, box[3] + margin))
        side = max(box[2] - box[0], box[3] - box[1])
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(image.crop(box), ((side - (box[2] - box[0])) // 2, (side - (box[3] - box[1])) // 2))
        image = square
    image.resize((SHOWN, SHOWN), Image.Resampling.LANCZOS).save(path, quality=88)


def scores_of(mesh, part_of, face_image, view, finish_of_region):
    """One split's three scores and its part count."""
    on_faces = view["on_faces"]
    finish = np.where(on_faces >= 0, finish_of_region[np.maximum(on_faces, 0)], -1)
    owned, missed = split_compare.finishes_owned(mesh.area_faces, finish, part_of)
    wasted, cut = split_compare.needless_cuts(mesh, finish, part_of)
    rendered = np.where(face_image >= 0, part_of[np.maximum(face_image, 0)], -1)
    return {"parts": int(part_of.max()) + 1, "owned": owned, "missed": missed,
            "needless": round(wasted, 4), "cut_surfaces": cut,
            **split_compare.region_agreement(rendered, view["pixels"], finish_of_region)}


def take_page(run, page, take):
    """The take's pictures and scores."""
    folder = run / take
    mesh = split_compare.raw_model(take)
    view = dict(np.load(folder / "view.npz"))
    finish_of_region, finish_names = split_compare.region_finishes(take, int(view["pixels"].max()) + 1)
    drawn = views(take, mesh)
    saved(np.asarray(split_compare.picture(take)), page / f"{take}-closeup.webp")
    found = {"take": take, "finishes": finish_names, "methods": {}}
    for method in NAMES:
        path = folder / f"parts_{method}.npy"
        if not path.exists():
            continue
        part_of = np.load(path)
        for name, (face_image, normals) in drawn.items():
            saved(coloured(face_image, part_of, normals, mesh.area_faces), page / f"{take}-{method}-{name}.webp")
        found["methods"][method] = scores_of(mesh, part_of, drawn["front"][0], view, finish_of_region)
    return found


# Seconds and euros.

def machine_rate(entry):
    """Euros a second of the batch's working machines (its ledger entry), the mean over its machines."""
    rows = [row for row in entry["machines"] if row.get("minutes")]
    return sum(row["euros"] for row in rows) / sum(row["minutes"] * 60 for row in rows)


def partcrafter_cost(take):
    """PartCrafter's run on the take's picture: its seconds (the batch's timings.json) and euros at its machines'
    rate; None where the batch kept no record."""
    report = json.loads((split_compare.LABELS / take / "labels.json").read_text())
    parts = pathlib.Path(report["parts_folder"])
    timings, entry = parts.parent / "timings.json", parts.parent.parent / "cloud.json"
    if not (timings.exists() and entry.exists()):
        return None
    seconds = json.loads(timings.read_text()).get(parts.name.rsplit("-", 1)[0] + ".png-" + parts.name.rsplit("-", 1)[1],
                                                   {}).get("seconds")
    if seconds is None:
        return None
    return {"seconds": seconds, "euros": seconds * machine_rate(json.loads(entry.read_text()))}


def cloud_costs(run, take, rate):
    """SegviGen's and GeoSAM2's seconds on the take (their timings; model loading shared over its share) and euros at
    the meshparts batch's rate. Encoding counts for both SegviGen runs, the conditioning render for the unguided."""
    down, found = run / take / "down", {}
    if (down / "segvigen_timing.json").exists():
        times = json.loads((down / "segvigen_timing.json").read_text())
        common = times["encode"] + times.get("load_share", 0)
        found["segvigen"] = common + times["render"] + times["auto"]
        found["segvigen_guided"] = common + times["guided"]
    if (down / "geosam2_timing.json").exists():
        times = json.loads((down / "geosam2_timing.json").read_text())
        found["geosam2_guided"] = times["render"] + times["segment"]
    return {method: {"seconds": round(seconds, 1), "euros": seconds * rate} for method, seconds in found.items()}


def batch_rate(run):
    """The meshparts batches' euros a second, over all of them in the run folder, and their euros in all."""
    entries = [json.loads(path.read_text()) for path in sorted(run.glob("cloud-meshparts-*.json"))]
    entries = [entry for entry in entries if entry.get("machines")]
    if not entries:
        return None, 0.0
    euros = sum(row["euros"] for entry in entries for row in entry["machines"])
    seconds = sum(row["minutes"] * 60 for entry in entries for row in entry["machines"] if row.get("minutes"))
    return euros / seconds, euros + sum(row["euros"] for entry in entries for row in entry.get("attempts", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("draw", "page"))
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("page", type=pathlib.Path)
    parser.add_argument("takes", nargs="*")
    arguments = parser.parse_args()
    arguments.page.mkdir(parents=True, exist_ok=True)
    stored = arguments.run / "scores.json"
    if arguments.step == "page":
        import split_html
        rate, total = batch_rate(arguments.run)
        found = json.loads(stored.read_text())
        for take, entry in found.items():
            entry["costs"] = {**({"partcrafter": partcrafter_cost(take)} if partcrafter_cost(take) else {}),
                              **(cloud_costs(arguments.run, take, rate) if rate else {})}
        (arguments.page / "index.html").write_text(split_html.page(found, total, arguments.run))
        stored.write_text(json.dumps(found, indent=1))
        return
    takes = arguments.takes or sorted(path.parent.name for path in arguments.run.glob("*/view.npz"))
    found = json.loads(stored.read_text()) if stored.exists() else {}
    for take in takes:
        found[take] = take_page(arguments.run, arguments.page, take)
        stored.write_text(json.dumps(found, indent=1))
        print(take, json.dumps({method: {key: value for key, value in entry.items() if key != "owned"}
                                for method, entry in found[take]["methods"].items()}), flush=True)


if __name__ == "__main__":
    main()
