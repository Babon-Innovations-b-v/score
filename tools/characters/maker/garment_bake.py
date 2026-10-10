"""The garment settle baked into the built person as corrective shapes per clip, so the clips still play from the
skeleton: glTF morph targets on the garment surfaces, each clip keying its own few by weight frame by frame. Plain
numpy, here, on files on disk.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/garment_bake.py <body.glb> <settle_in.npz> \
        <settle_out.npz> <settled.glb>

- **Into the bind pose.** The settle's offsets are in the world, after skinning; a morph target is added before it.
  Each offset is carried back through its point's blended joint turn in that frame (the inverse of the weighted sum
  of its joints' 3x3s), so skinned again it lands where the settle put the point.
- **A few shapes a clip.** A clip's offsets, frame by frame, are cut to their SHAPES_A_CLIP strongest shapes (the
  singular vectors of frames by points); each shape is a morph target, its weight the clip's own coefficient frame by
  frame, scaled so the largest is 1. Weights of every other clip's shapes are 0 in that clip. A clip the settle left
  alone (every offset under KEPT) keys no shape. The record says how far the kept shapes miss the settle (`missed_mm`).
- **Only what moved is written**: each target is a sparse accessor of the points that move more than KEPT in it; the
  other surfaces' targets have no data (all zeros, as glTF allows), since every surface of a mesh must have as many
  targets.
- Refitting the garments' weights and bind places instead (smooth skinning decomposition's per-point step, tried
  first) kept little of the settle (the player, 2026-10-10: standing's crossings 579 to 548 against the settle's 23):
  one set of weights cannot make a dent in one pose only.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))
sys.path.insert(0, str(MAKER.parent / "people"))

import glb  # noqa: E402
import joins  # noqa: E402

SHAPES_A_CLIP = 8
KEPT = 0.0002


def bind_offsets(data, settled, clip):
    """A clip's offsets carried into the bind pose (frames, cloth points, 3)."""
    moves = data[f"moves_{clip}"][int(data["lead_in"]):].astype(float)
    offsets = settled[f"offset_{clip}"].astype(float)
    count = min(len(moves), len(offsets))
    turns = moves[:count, :, :3, :3][:, data["cloth_joints"]]  # frames, points, 4, 3, 3
    blended = np.einsum("ps,fpsab->fpab", data["cloth_weights"], turns)
    return np.linalg.solve(blended, offsets[:count][..., None])[..., 0]


def clip_shapes(offsets):
    """A clip's strongest shapes (shapes, points, 3), their weights frame by frame (frames, shapes), and how far they
    miss the offsets at worst (metres)."""
    frames, points = offsets.shape[:2]
    if np.abs(offsets).max() < KEPT:
        return np.zeros((0, points, 3)), np.zeros((frames, 0)), 0.0
    rows, strengths, shapes = np.linalg.svd(offsets.reshape(frames, -1), full_matrices=False)
    kept = min(SHAPES_A_CLIP, len(strengths))
    weights = rows[:, :kept] * strengths[:kept]
    scale = np.maximum(np.abs(weights).max(0), 1e-12)
    shapes = shapes[:kept] * scale[:, None]
    weights = weights / scale
    missed = np.linalg.norm((offsets.reshape(frames, -1) - weights @ shapes).reshape(frames, points, 3), axis=2)
    return shapes.reshape(kept, points, 3), weights, float(missed.max())


def sparse_target(contents, values):
    """A morph target of a surface's offsets as a sparse accessor (only the points that move); its number."""
    moving = np.flatnonzero(np.linalg.norm(values, axis=1) > KEPT)
    accessor = {"componentType": glb.FLOAT, "count": len(values), "type": "VEC3"}
    if len(moving):
        accessor["sparse"] = {
            "count": len(moving),
            "indices": {"bufferView": contents._slice(moving.astype(np.uint32).tolist(), glb.UNSIGNED_INT, None),
                        "componentType": glb.UNSIGNED_INT},
            "values": {"bufferView": contents._slice(values[moving].astype(np.float32).ravel().tolist(), glb.FLOAT,
                                                     None)}}
        accessor["min"] = values.min(0).astype(np.float32).tolist()
        accessor["max"] = values.max(0).astype(np.float32).tolist()
    else:
        accessor["min"], accessor["max"] = [0.0] * 3, [0.0] * 3
    contents.accessors.append(accessor)
    return len(contents.accessors) - 1


def opened(body_path):
    """The built glb as a document and a Contents holding its blob, views and accessors, to add to."""
    document, blob = joins.read_glb(body_path)
    contents = glb.Contents()
    contents._blob = bytearray(blob)
    contents.views, contents.accessors = document.pop("bufferViews"), document.pop("accessors")
    contents.images = document.pop("images", [])
    document.pop("buffers", None)
    return document, contents


def outfit_node(document):
    """The outfit's node number (the skinned mesh that is not the far body)."""
    return next(number for number, node in enumerate(document["nodes"])
                if "mesh" in node and "skin" in node and node.get("name") != "far")


def write_targets(document, contents, data, shapes):
    """Every outfit surface's morph targets: a garment's from the shapes (all clips', in order), the rest empty."""
    node = outfit_node(document)
    names = [str(name) for name in data["cloth_names"]]
    garment = 0
    for primitive in document["meshes"][document["nodes"][node]["mesh"]]["primitives"]:
        material = document["materials"][primitive["material"]]
        count = contents.accessors[primitive["attributes"]["POSITION"]]["count"]
        if material.get("extras", {}).get("role") == "garment":
            if material["name"] != names[garment]:
                raise SystemExit("the garment surfaces are not in settle_in's order")
            mine = data[f"cloth_numbers_{garment}"]
            primitive["targets"] = [{"POSITION": sparse_target(contents, shape[mine])} for shape in shapes]
            garment += 1
        else:
            primitive["targets"] = [{"POSITION": sparse_target(contents, np.zeros((count, 3)))} for _ in shapes]
    document["meshes"][document["nodes"][node]["mesh"]]["weights"] = [0.0] * len(shapes)
    return node


def key_weights(document, contents, node, clip_weights, total):
    """Each clip's animation keys the outfit's morph weights at its own frame times: its shapes' weights, the others'
    0."""
    first = 0
    for animation in document["animations"]:
        weights = clip_weights.get(animation["name"])
        if weights is None:
            continue
        times = animation["samplers"][animation["channels"][0]["sampler"]]["input"]
        frames = contents.accessors[times]["count"]
        keyed = np.zeros((frames, total))
        shown = weights[:frames]
        keyed[:len(shown), first:first + weights.shape[1]] = shown
        if len(shown):
            keyed[len(shown):, first:first + weights.shape[1]] = shown[-1]
        output = contents.reading(keyed.astype(np.float32).ravel().tolist(), "SCALAR", glb.FLOAT)
        animation["samplers"].append({"input": times, "output": output, "interpolation": "LINEAR"})
        animation["channels"].append({"sampler": len(animation["samplers"]) - 1,
                                      "target": {"node": node, "path": "weights"}})
        first += weights.shape[1]


def bake(body_path, data, settled, out):
    """The settled glb and the record."""
    document, contents = opened(body_path)
    shapes, clip_weights, record = [], {}, {}
    for clip in [str(name) for name in data["clips"]]:
        found, weights, missed = clip_shapes(bind_offsets(data, settled, clip))
        shapes += list(found)
        clip_weights[clip] = weights
        record[clip] = {"shapes": len(found), "missed_mm": round(missed * 1000, 2)}
    node = write_targets(document, contents, data, shapes)
    key_weights(document, contents, node, clip_weights, len(shapes))
    glb.write(out, document, contents)
    return {"targets": len(shapes), "clips": record, "bytes": pathlib.Path(out).stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("settle_in", type=pathlib.Path)
    parser.add_argument("settle_out", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    options = parser.parse_args()
    record = bake(options.body, dict(np.load(options.settle_in)), np.load(options.settle_out), options.out)
    options.out.with_suffix(".bake.json").write_text(json.dumps(record, indent=1))
    worst = max(clip["missed_mm"] for clip in record["clips"].values())
    print(f"baked: {record['targets']} shapes, worst miss {worst} mm, {record['bytes']:,} bytes; {options.out}",
          flush=True)


if __name__ == "__main__":
    main()
