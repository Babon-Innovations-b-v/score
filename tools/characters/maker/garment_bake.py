"""The garment settle baked into the built person as corrective shapes per clip, so the clips still play from the
skeleton: glTF morph targets on the garment surfaces, each clip keying its own by weight frame by frame. Plain numpy,
on the card after the settle (prop_chain.py settle) or here, on files on disk.

    python tools/characters/maker/garment_bake.py <body.glb> <settle_in.npz> <settle_out.npz> <settled.glb>

- **Into the bind pose.** The settle's offsets are in the world, after skinning; a morph target is added before it.
  Each offset is carried back through its point's blended joint turn in that frame by damped least squares (the
  blend's 3x3 with DAMPING on its square), so skinned again it lands where the settle put the point; where two joints
  turned far apart all but fold the blend, the damping keeps the carried offset short (a plain inverse gave Nev's
  suit offsets of 0.7 m, and the strongest joint's turn alone, tried next, missed the settle by up to 92 mm).
- **As many shapes a clip as it needs.** A clip's carried offsets, frame by frame, are cut to their strongest shapes
  (the singular vectors of frames by points), as few as keep every point of every frame within MISS_MOST of where
  the settle put it, measured in the world after skinning (eight a clip missed the player's door by 74 mm,
  2026-10-10; per-frame shapes would hold every frame's moving points, about three times the bytes). Each shape is
  a morph target named `<clip>.<number>` (the mesh's `extras.targetNames`), its weight the clip's own coefficient
  frame by frame, scaled so the largest is 1; every other clip's shapes are 0 in that clip. A clip the settle left
  alone (every offset under KEPT) keys no shape. The record says how far the kept shapes miss (`missed_mm`).
- **Never worse than unsettled.** In every frame the body's edges (skin, tucks and hard parts: the collider less the
  hair) through the cloth are counted with the frame's shapes in, and unsettled; where the shapes cross more, the
  frame's weights are halved, and where that still crosses more, set to 0 (the player's settle crossed 633 times in
  the waiting clip's worst frame against 357 unsettled, 2026-10-10). The record counts the frames each way.
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

KEPT = 0.0002
MISS_MOST = 0.004
DAMPING = 1e-4
SHARES = (1.0, 0.5, 0.0)


def blended_turns(data, clip, count=None):
    """Each cloth point's blended joint 3x3 frame by frame after the lead-in (frames, points, 3, 3)."""
    moves = data[f"moves_{clip}"][int(data["lead_in"]):][:count].astype(float)
    return np.einsum("ps,fpsab->fpab", data["cloth_weights"], moves[:, :, :3, :3][:, data["cloth_joints"]])


def bind_offsets(blended, offsets):
    """A clip's world offsets carried into the bind pose through the blended turns (damped least squares)."""
    turned = np.swapaxes(blended, -1, -2)
    return np.linalg.solve(turned @ blended + DAMPING * np.eye(3), (turned @ offsets[..., None]))[..., 0]


def world_miss(blended, offsets, carried):
    """The worst distance, in metres, between where `carried` (bind offsets) puts a point after skinning and where
    the settle put it."""
    return float(np.linalg.norm(np.einsum("fpab,fpb->fpa", blended, carried) - offsets, axis=2).max())


def clip_shapes(blended, offsets):
    """A clip's strongest shapes (shapes, points, 3), as few as miss the settle by at most MISS_MOST in the world,
    their weights frame by frame (frames, shapes), and how far they miss at worst (metres)."""
    frames, points = offsets.shape[:2]
    if np.abs(offsets).max() < KEPT:
        return np.zeros((0, points, 3)), np.zeros((frames, 0)), 0.0
    carried = bind_offsets(blended, offsets)
    rows, strengths, shapes = np.linalg.svd(carried.reshape(frames, -1), full_matrices=False)
    for kept in range(1, len(strengths) + 1):
        weights = rows[:, :kept] * strengths[:kept]
        missed = world_miss(blended, offsets, (weights @ shapes[:kept]).reshape(frames, points, 3))
        if missed <= MISS_MOST:
            break
    scale = np.maximum(np.abs(weights).max(0), 1e-12)
    return (shapes[:kept] * scale[:, None]).reshape(kept, points, 3), weights / scale, missed


def counted_world(data):
    """What the body-through-cloth count reads: the cloth's and the collider's points in one numbering (a held cloth
    point is its collider point, so a seam is shared), the cloth's triangles in it, and the counted collider's edges
    (skin, tucks and hard parts; the hair left out)."""
    sys.path.insert(0, str(MAKER))
    cloth_count = len(data["cloth_points"])
    number = np.where(data["held"], cloth_count + data["held_collider"], np.arange(cloth_count))
    faces = data["collider_faces"][data["collider_counted"]] if "collider_counted" in data else data["collider_faces"]
    edges = np.unique(np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0) + cloth_count
    return number[data["cloth_faces"]], edges


def skinned(points, joints, weights, moves):
    """Linear blend skinning of points by four joints each under one frame's matrices."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return sum(weights[:, slot, None] * np.einsum("pij,pj->pi", moves[joints[:, slot]], homogeneous)[:, :3]
               for slot in range(joints.shape[1]))


def frame_shares(data, clip, blended, shapes, weights):
    """Each frame's share of its shapes (SHARES' first whose body-through-cloth count is no more than unsettled), and
    the counts: unsettled and with the share taken, frame by frame."""
    import drape_measure
    faces, edges = counted_world(data)
    moves = data[f"moves_{clip}"][int(data["lead_in"]):].astype(float)
    shares, plain_counts, kept_counts = [], [], []
    for frame in range(len(weights)):
        cloth = skinned(data["cloth_points"], data["cloth_joints"], data["cloth_weights"], moves[frame])
        collider = skinned(data["collider_points"], data["collider_joints"], data["collider_weights"], moves[frame])
        shifted = np.einsum("pab,pb->pa", blended[frame], np.tensordot(weights[frame], shapes, axes=1))
        plain = drape_measure.edge_crossings(np.concatenate([cloth, collider]), faces, edges)
        for share in SHARES:
            count = plain if share == 0.0 else drape_measure.edge_crossings(
                np.concatenate([cloth + share * shifted, collider]), faces, edges)
            if count <= plain:
                break
        shares.append(share)
        plain_counts.append(plain)
        kept_counts.append(count)
    return np.array(shares), plain_counts, kept_counts


def clip_bake(data, settled, clip):
    """One clip's shapes, weights (each frame's share in) and record."""
    offsets = settled[f"offset_{clip}"].astype(float)
    blended = blended_turns(data, clip, len(offsets))
    offsets = offsets[:len(blended)]
    shapes, weights, missed = clip_shapes(blended, offsets)
    record = {"shapes": len(shapes), "missed_mm": round(missed * 1000, 2)}
    if len(shapes):
        shares, plain, kept = frame_shares(data, clip, blended, shapes, weights)
        weights = weights * shares[:, None]
        record.update(frames_full=int((shares == 1.0).sum()), frames_halved=int((shares == 0.5).sum()),
                      frames_unsettled=int((shares == 0.0).sum()), body_through_cloth_plain_worst=int(max(plain)),
                      body_through_cloth_worst=int(max(kept)))
    return shapes, weights, record


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


def write_targets(document, contents, data, shapes, shape_names):
    """Every outfit surface's morph targets: a garment's from the shapes (all clips', in order), the rest empty; the
    targets' `shape_names` in the mesh's extras."""
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
    mesh = document["meshes"][document["nodes"][node]["mesh"]]
    mesh["weights"] = [0.0] * len(shapes)
    mesh.setdefault("extras", {})["targetNames"] = shape_names
    # Blender's importer names a mesh object with shape keys by its mesh ("Mesh_1"), not its node ("work").
    mesh["name"] = document["nodes"][node]["name"]
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
    from concurrent.futures import ProcessPoolExecutor
    document, contents = opened(body_path)
    clips = [str(name) for name in data["clips"]]
    with ProcessPoolExecutor() as pool:
        baked = list(pool.map(clip_bake, [data] * len(clips), [settled] * len(clips), clips))
    shapes, names, clip_weights, record = [], [], {}, {}
    for clip, (found, weights, entry) in zip(clips, baked):
        shapes += list(found)
        names += [f"{clip}.{number}" for number in range(len(found))]
        clip_weights[clip] = weights
        record[clip] = entry
        print(clip, entry, flush=True)
    node = write_targets(document, contents, data, shapes, names)
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
    settled = np.load(options.settle_out)
    record = bake(options.body, dict(np.load(options.settle_in)), {name: settled[name] for name in settled.files},
                  options.out)
    options.out.with_suffix(".bake.json").write_text(json.dumps(record, indent=1))
    worst = max(clip["missed_mm"] for clip in record["clips"].values())
    print(f"baked: {record['targets']} shapes, worst miss {worst} mm, {record['bytes']:,} bytes; {options.out}",
          flush=True)


if __name__ == "__main__":
    main()
