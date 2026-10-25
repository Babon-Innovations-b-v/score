"""The likeness gate: a made model held to its close-up by its outline from eight ways round it and by DINOv2.

tools/usd/compare.py's candidate check (render-and-compare, WorldAct's idea) promoted to a gate, on the model alone:
the model's silhouette from YAWS ways round it at each of look_downs() (compare.py's ring, drawn here from the mesh
with no renderer: a silhouette needs none), each scored by compare.outline against the close-up's object (its alpha
where the close-up was cut out, else compare.closeup_mask), and the best way and look-down stand for the close-up's
camera, which a code build never had. DINOv2 (similar.py on a rented machine, paid evidence) then scores the best way's silhouette against
the close-up's, both black on white: a silhouette, since the library paint keeps the picture's colours off the model
on purpose (method B), so colours would mark every right model down.

    .venv/bin/python -m score.stages.props.likeness measure <models folder> <close-ups.json> <out folder>

`measure` scores made models against their close-ups ({model: close-up picture}) and writes outline.json and the
DINOv2 pairs (pairs.json, for similar.py) into the out folder: how OUTLINE_LEAST was set.
"""
import argparse
import json
import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw

import score.stages.props.prop_data as prop_data

SIDE = 384
# Set on the hub's twelve accepted round-six generated models (2026-10-12, `measure`, against each take's cut-out
# close-up): best outlines 0.555 (telephone_1), 0.564, 0.623, 0.627, 0.627, 0.730, 0.779, 0.782, 0.798, 0.807, 0.811,
# 0.818 (median 0.754); the least less a margin of 0.05. The same models against the other kinds' close-ups score a
# median 0.31 but up to 0.60 (11 of 72 pairs at 0.50 or more): the outline alone does not tell like shapes apart,
# which is why DINOv2 must pass too.
OUTLINE_LEAST = 0.50
# Degrees between the look-downs a model's outline is drawn at (look_downs).
LOOK_DOWN_STEP = 5.0


def candidate():
    """tools/usd/compare.py, the candidate check: its ring (YAWS, ELEVATION, FOV), outline and close-up mask."""
    with prop_data.tools("usd", "props"):
        import compare
    return compare


def look_downs():
    """The look-downs a close-up is drawn from, every LOOK_DOWN_STEP degrees from the close-up check's least to its
    most (tools/props/closeup/check.py: Nano Banana Pro draws from 15 to about 30 degrees above level whatever the
    wording says, so one look-down would fault the camera, not the model)."""
    with prop_data.tools("props/closeup", "props"):
        import check
    return [float(value) for value in np.arange(check.LOOK_DOWN_DEGREES, check.LOOK_DOWN_MOST + 1e-6, LOOK_DOWN_STEP)]


def gltf_mesh(path):
    """(positions, triangles) of a .gltf's or .glb's meshes, every primitive, in the file's own frame."""
    with prop_data.tools("props"):
        import glb_file
    path = pathlib.Path(path)
    if path.suffix == ".glb":
        document, views = glb_file.read(path)
    else:
        document = json.loads(path.read_text())
        blob = (path.parent / document["buffers"][0]["uri"]).read_bytes()
        views = [blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
                 for view in document["bufferViews"]]
    points, triangles = [], []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            found = glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"])
            indices = glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3)
            triangles.append(indices + sum(len(block) for block in points))
            points.append(found)
    return np.concatenate(points).astype(float), np.concatenate(triangles)


def silhouette(points, triangles, step, look_down=None):
    """The mesh's mask seen from way `step` of YAWS, `look_down` degrees above level (compare.ELEVATION when none), as
    compare.ring_views frames it (its box's middle, fitted)."""
    ring = candidate()
    low, high = points.min(axis=0), points.max(axis=0)
    middle = (low + high) / 2
    radius = max(0.05, float(np.linalg.norm(high - low)) / 2)
    distance = radius / math.sin(math.radians(ring.FOV / 2)) * 1.05
    yaw, pitch = math.radians(360.0 * step / ring.YAWS), math.radians(ring.ELEVATION if look_down is None else look_down)
    back = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    right = np.cross([0.0, 1.0, 0.0], back)
    right /= np.linalg.norm(right)
    up = np.cross(back, right)
    seen = points - (middle + back * distance)
    depth = -seen @ back
    focal = SIDE / 2 / math.tan(math.radians(ring.FOV / 2))
    pixels = np.stack([SIDE / 2 + focal * (seen @ right) / depth, SIDE / 2 - focal * (seen @ up) / depth], axis=1)
    picture = Image.new("L", (SIDE, SIDE), 0)
    draw = ImageDraw.Draw(picture)
    for corner in pixels[triangles]:
        draw.polygon([tuple(point) for point in corner], fill=255)
    return np.asarray(picture) > 127


def closeup_object(path):
    """The close-up's object: its alpha where it was cut out (a Pixal3D take's input.png), else compare.closeup_mask."""
    picture = Image.open(path)
    if picture.mode == "RGBA" and np.asarray(picture)[..., 3].min() < 128:
        return np.asarray(picture)[..., 3] > 127
    return candidate().closeup_mask(picture)


def best_way(model, closeup):
    """{"way", "look_down", "outline", "ways"} of a model against its close-up: every way's outline at the look-down
    that fits it best, and the best way."""
    points, triangles = gltf_mesh(model)
    target, ring = closeup_object(closeup), candidate()
    scored = [[round(ring.outline(silhouette(points, triangles, step, look_down), target), 4) for look_down in
               look_downs()] for step in range(ring.YAWS)]
    ways = [max(row) for row in scored]
    best = int(np.argmax(ways))
    return {"way": best, "look_down": look_downs()[int(np.argmax(scored[best]))], "outline": ways[best], "ways": ways}


def silhouette_picture(mask):
    """A mask as black on white, cut to its box: DINOv2's side of the pair."""
    return Image.fromarray(np.where(candidate().boxed(mask), 0, 255).astype(np.uint8)).convert("RGB")


def write_pair(model, closeup, way, folder, name, look_down=None):
    """The best way's silhouette (at its look-down) and the close-up's, each black on white in `folder`; the pair for
    similar.py."""
    points, triangles = gltf_mesh(model)
    folder.mkdir(parents=True, exist_ok=True)
    made, drawn = folder / f"{name}-model.png", folder / f"{name}-closeup.png"
    silhouette_picture(silhouette(points, triangles, way, look_down)).save(made)
    silhouette_picture(closeup_object(closeup)).save(drawn)
    return [str(made), str(drawn)]


def measure(models, closeups, out):
    """Every model of {model: close-up} in `models` (<model>.gltf) scored; outline.json and pairs.json in `out`."""
    out = pathlib.Path(out)
    scored, pairs = {}, {}
    for name, closeup in sorted(closeups.items()):
        model = pathlib.Path(models) / f"{name}.gltf"
        scored[name] = {"closeup": str(closeup), **best_way(model, closeup)}
        pairs[name] = write_pair(model, closeup, scored[name]["way"], out / "pairs", name, scored[name]["look_down"])
    outlines = sorted(entry["outline"] for entry in scored.values())
    summary = {"models": len(outlines), "least": outlines[0], "median": float(np.median(outlines)),
               "most": outlines[-1], "outline_least": OUTLINE_LEAST}
    (out / "outline.json").write_text(json.dumps({"summary": summary, "models": scored}, indent=1) + "\n")
    (out / "pairs.json").write_text(json.dumps(pairs, indent=1) + "\n")
    return summary, scored


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("action", choices=("measure",))
    parser.add_argument("models", type=pathlib.Path)
    parser.add_argument("closeups", type=pathlib.Path, help="{model: close-up picture}")
    parser.add_argument("out", type=pathlib.Path)
    options = parser.parse_args()
    options.out.mkdir(parents=True, exist_ok=True)
    summary, scored = measure(options.models, json.loads(options.closeups.read_text()), options.out)
    for name, entry in sorted(scored.items(), key=lambda item: item[1]["outline"]):
        print(f"{name:20} outline {entry['outline']:.3f}  (way {entry['way']})")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
