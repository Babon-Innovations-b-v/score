"""Independent body-through-cloth count for issue #5's check (the reviewer's of 2026-10-10, moved into the repo so the
people stage's gate is in its code version): in the bind pose and in every frame of the named clips, how many edges of
the drawn body parts (skin: head, neck, hands, tucks) and of the hard end pieces (boots, mitts, helmet, buckles) pass
through a cloth triangle, read from the built glb as the engine skins it (joins.py's reader), and how deep: an edge's
depth is the nearer of its two ends to the crossed triangle's plane, so an edge that only grazes the cloth is
shallow. Edges deeper than MARGIN_MM are `deep`; the people stage's gate holds every frame at none.

    python bodycloth.py BODY.glb --outfit work --out OUT.json [--clips walking sitting ...] [--every 1]

A pair whose edge touches a triangle corner at the same place (a welded border between two parts) is not counted.
Cloth = fabric parts (by the prop route's material role "garment", or the shipped parts' fabric names).
"""
import argparse
import json
import pathlib
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "people"))
import joins  # noqa: E402

SHIPPED_CLOTH = ("work_cloth", "work_collar", "work_placket", "work_pocket", "work_belt", "work_lining", "cloth",
                 "belt", "strap_l", "strap_r", "flag")
SHIPPED_CLOTH_START = ("band_",)
WELD = 1e-5
# The settle's cloth is 3 mm thick (garment_settle.SETTINGS: radius 1.5 mm a point, each side of the surface), so a
# body edge within 3 mm of the cloth's middle surface lies inside the cloth the settle models: contact, not poking.
MARGIN_MM = 3.0


def kind_of(name, extras):
    """'skin', 'cloth' or 'hard' for a part."""
    role = (extras or {}).get("role")
    if role:
        if role in ("garment", "cloth", "fabric"):
            return "cloth"
        if role in ("skin", "tuck"):
            return "skin"
        if role == "hair":
            return "hair"
        return "hard"
    if name in SHIPPED_CLOTH or name.startswith(SHIPPED_CLOTH_START):
        return "cloth"
    if name.startswith("skin"):
        return "skin"
    if name in ("hair", "eyes", "irises", "eyebrows", "glasses"):
        return "hair"
    return "hard"


def parts_of(document, blob, outfit):
    """The outfit node's parts: [(name, kind, Part)]."""
    node = next(node for node in document["nodes"] if node.get("name") == outfit and "mesh" in node)
    found = []
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        material = document["materials"][primitive["material"]]
        attributes = primitive["attributes"]
        part = joins.Part(material["name"], joins.accessor(document, blob, attributes["POSITION"]),
                          joins.accessor(document, blob, attributes["JOINTS_0"]),
                          joins.accessor(document, blob, attributes["WEIGHTS_0"]),
                          joins.accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3))
        named = sum(name == material["name"] or name.startswith(material["name"] + "#") for name, _, _ in found)
        name = material["name"] + (f"#{named}" if named else "")  # several tucks share a material: one entry each
        found.append((name, kind_of(material["name"], material.get("extras")), part))
    return found


def merged(posed, parts):
    """Points and triangles of several parts in one numbering."""
    points, faces, offset = [], [], 0
    for part in parts:
        points.append(posed[id(part)])
        faces.append(part.faces + offset)
        offset += len(part.points)
    if not points:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    return np.concatenate(points), np.concatenate(faces)


def edges_of(faces):
    return np.unique(np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)


def segment_hits(start, end, corner_a, corner_b, corner_c):
    """Whether each segment crosses its triangle (Moller-Trumbore, the segment's ends inclusive)."""
    direction = end - start
    edge_one, edge_two = corner_b - corner_a, corner_c - corner_a
    cross = np.cross(direction, edge_two)
    det = np.einsum("ij,ij->i", edge_one, cross)
    ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    offset = start - corner_a
    first = np.einsum("ij,ij->i", offset, cross) * inv
    across = np.cross(offset, edge_one)
    second = np.einsum("ij,ij->i", direction, across) * inv
    along = np.einsum("ij,ij->i", edge_two, across) * inv
    return ok & (first >= 0) & (second >= 0) & (first + second <= 1) & (along >= 0) & (along <= 1)


def crossings(edge_points, edges, tri_points, faces, chunk=8192):
    """The edges that pass through any of the triangles, welded neighbours not counted: {edge: depth in mm}, each its
    deepest crossing's (the nearer end's distance from the crossed triangle's plane)."""
    if not len(edges) or not len(faces):
        return {}
    corners = tri_points[faces]
    centres = corners.mean(axis=1)
    radius = float(np.linalg.norm(corners - centres[:, None], axis=2).max())
    tree = cKDTree(centres)
    starts, ends = edge_points[edges[:, 0]], edge_points[edges[:, 1]]
    middles, halves = 0.5 * (starts + ends), 0.5 * np.linalg.norm(ends - starts, axis=1)
    depths = {}
    for begin in range(0, len(edges), chunk):
        rows = np.arange(begin, min(begin + chunk, len(edges)))
        near = tree.query_ball_point(middles[rows], halves[rows] + radius)
        counts = np.array([len(found) for found in near])
        if not counts.sum():
            continue
        edge_index = np.repeat(rows, counts)
        face_index = np.concatenate([np.asarray(found, dtype=np.int64) for found in near if found])
        tri = corners[face_index]
        hit = segment_hits(starts[edge_index], ends[edge_index], tri[:, 0], tri[:, 1], tri[:, 2])
        if not hit.any():
            continue
        edge_index, tri = edge_index[hit], tri[hit]
        touching = np.zeros(len(edge_index), bool)
        for end_points in (starts[edge_index], ends[edge_index]):
            touching |= (np.linalg.norm(tri - end_points[:, None], axis=2) < WELD).any(axis=1)
        edge_index, tri = edge_index[~touching], tri[~touching]
        normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
        apart = [np.abs(np.einsum("ij,ij->i", points[edge_index] - tri[:, 0], normal)) for points in (starts, ends)]
        for edge, depth in zip(edge_index.tolist(), (np.minimum(*apart) * 1000).tolist()):
            depths[edge] = max(depth, depths.get(edge, 0.0))
    return depths


def frame_counts(parts, posed):
    """Edge counts through the cloth for one posed frame: {'skin': n, 'hard': n, 'skin_deep': n, 'hard_deep': n,
    'deepest_mm': d, 'by_part': {name: n}, 'deep_by_part': {name: n}}; deep is over MARGIN_MM."""
    cloth_points, cloth_faces = merged(posed, [part for _, kind, part in parts if kind == "cloth"])
    found = {"skin": 0, "hard": 0, "skin_deep": 0, "hard_deep": 0, "deepest_mm": 0.0, "by_part": {},
             "deep_by_part": {}}
    for name, kind, part in parts:
        if kind not in ("skin", "hard"):
            continue
        depths = list(crossings(posed[id(part)], edges_of(part.faces), cloth_points, cloth_faces).values())
        deep = sum(depth > MARGIN_MM for depth in depths)
        found[kind] += len(depths)
        found[kind + "_deep"] += deep
        found["deepest_mm"] = round(max([found["deepest_mm"], *depths]), 2)
        found["by_part"][name] = len(depths)
        found["deep_by_part"][name] = deep
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb")
    parser.add_argument("--outfit", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--clips", nargs="*")
    parser.add_argument("--every", type=int, default=1)
    options = parser.parse_args()
    began = time.time()
    document, blob = joins.read_glb(options.glb)
    skin = document["skins"][0]
    inverse_bind = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = joins.parents_of(document)
    rest_rotations, rest_translations, scales = joins.node_rest(document)
    parts = parts_of(document, blob, options.outfit)
    record = {"body": options.glb, "outfit": options.outfit, "margin_mm": MARGIN_MM,
              "parts": {kind: [name for name, part_kind, _ in parts if part_kind == kind]
                        for kind in ("skin", "cloth", "hard", "hair")}}

    def counts_at(rotations, translations):
        world = joins.world_matrices(rotations, translations, scales, parent)[skin["joints"]]
        posed = {id(part): joins.skinned(part.points, part.joints, part.weights, world, inverse_bind)
                 for _, _, part in parts}
        return frame_counts(parts, posed)

    record["bind"] = counts_at(rest_rotations, rest_translations)
    record["clips"] = {}
    for animation in document.get("animations", []):
        if options.clips and animation["name"] not in options.clips:
            continue
        rotations, translations = joins.clip_frames(document, blob, animation)
        per_frame = [counts_at(rotations[frame], translations[frame])
                     for frame in range(0, len(rotations), options.every)]
        clip = {"frames": len(per_frame)}
        for kind in ("skin", "hard", "skin_deep", "hard_deep"):
            values = np.array([frame[kind] for frame in per_frame])
            clip[kind] = {"frames_with_any": int((values > 0).sum()), "worst": int(values.max()),
                          "worst_frame": int(values.argmax()) * options.every, "mean": round(float(values.mean()), 1),
                          "frames_over_bind": int((values > record["bind"][kind]).sum())}
        clip["worst_by_part"] = {name: max(frame["by_part"][name] for frame in per_frame)
                                 for name in per_frame[0]["by_part"]}
        clip["deep_by_part"] = {name: max(frame["deep_by_part"][name] for frame in per_frame)
                                for name in per_frame[0]["deep_by_part"]}
        clip["deepest_mm"] = max(frame["deepest_mm"] for frame in per_frame)
        record["clips"][animation["name"]] = clip
        print(animation["name"], clip, flush=True)
    record["seconds"] = round(time.time() - began, 1)
    pathlib.Path(options.out).write_text(json.dumps(record, indent=1))
    print("bind", record["bind"], "->", options.out)


if __name__ == "__main__":
    main()
