"""One person's head for the face and the hair: the skin above the collar (`head/skin_head.npz`) and MakeHuman's
CC0 low-poly eyes seated on it (`head/eyes.npz`, copied into the look as `eyes.npz`).

    /root/envs/motion/bin/python head.py <work folder> <makehuman folder>

The work folder holds `gc/body/ours.npz` and `joints.json` (export_body.py). The makehuman folder holds MakeHuman's
hm08 base mesh (`base.obj`) and its low-poly eyes (`eyes/low-poly.mhclo`, `.obj`), both CC0 system assets; the base
mesh is only a fitting reference and never ships. The eyes are placed on the base mesh by their .mhclo, then moved
onto this head by a per-axis scale about the eye midpoint, matched from the base head's size to this one's.
Moved here from the nev_mars job's head_prep.py and round three's fit_head.py (#100, #112).
"""
import json
import pathlib
import shutil
import sys

import numpy as np
import trimesh

# Take C's neck cut under the collar and his neck joint's height (metres); a person's cut moves with their neck.
TAKE_C_NECK_CUT, TAKE_C_NECK1 = 1.42, 1.457
HEAD_JOINTS = ("Neck2", "Head", "HeadEnd")
SKIN_JOINTS = ("Neck1", "Neck2", "Head", "HeadEnd")


def read_obj(path):
    """Positions, triangles and per-point uv of an OBJ (quads split; a point keeps the first uv it is given)."""
    points, uvs, faces, uv_of = [], [], [], {}
    for line in pathlib.Path(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            points.append([float(value) for value in parts[1:4]])
        elif parts[0] == "vt":
            uvs.append([float(value) for value in parts[1:3]])
        elif parts[0] == "f":
            corners = []
            for token in parts[1:]:
                fields = token.split("/")
                vertex = int(fields[0]) - 1
                if len(fields) > 1 and fields[1]:
                    uv_of.setdefault(vertex, int(fields[1]) - 1)
                corners.append(vertex)
            faces += [[corners[0], corners[index], corners[index + 1]] for index in range(1, len(corners) - 1)]
    points = np.array(points)
    uv = np.zeros((len(points), 2))
    for vertex, index in uv_of.items():
        uv[vertex] = uvs[index]
    return points, np.array(faces), uv


def base_mesh(makehuman):
    """MakeHuman's base mesh: every position (helpers too, which asset files point at) and the body proper's."""
    points, current, body = [], None, set()
    for line in (makehuman / "base.obj").read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            points.append([float(value) for value in parts[1:4]])
        elif parts[0] == "g":
            current = parts[1]
        elif parts[0] == "f" and current == "body":
            body.update(int(token.split("/")[0]) - 1 for token in parts[1:])
    return np.array(points), np.array(sorted(body))


def fitted_eyes(makehuman, base):
    """The eyes placed on the base mesh by their .mhclo: each point a weighted sum of three base points plus an
    offset scaled by the base's own measures; points, faces and uv."""
    lines = (makehuman / "eyes" / "low-poly.mhclo").read_text().splitlines()
    scale = np.ones(3)
    for line in lines:
        parts = line.split()
        if parts and parts[0] in ("x_scale", "y_scale", "z_scale"):
            axis = "xyz".index(parts[0][0])
            first, second, denominator = int(parts[1]), int(parts[2]), float(parts[3])
            scale[axis] = abs(base[first][axis] - base[second][axis]) / denominator
    start = next(index for index, line in enumerate(lines) if line.startswith("verts"))
    placed = []
    for line in lines[start + 1:]:
        parts = line.split()
        if parts and parts[0] == "material" and not placed:
            continue
        if not parts or not parts[0][0].isdigit():
            break
        if len(parts) == 1:
            placed.append(base[int(parts[0])])
            continue
        corners = [int(value) for value in parts[:3]]
        weights = np.array([float(value) for value in parts[3:6]])
        offset = np.array([float(value) for value in parts[6:9]])
        placed.append(weights @ base[corners] + offset * scale)
    _, faces, uv = read_obj(makehuman / "eyes" / "low-poly.obj")
    return np.array(placed), faces, uv


def head_sizes(points, eye_mid):
    """The head's width, its crown's height over the eyes, and its depth, in a band just above the eyes."""
    band = (points[:, 1] > eye_mid[1]) & (points[:, 1] < eye_mid[1] + 0.35 * (points[:, 1].max() - eye_mid[1]))
    near = band & (np.abs(points[:, 2] - eye_mid[2]) < 3 * (points[:, 1].max() - eye_mid[1]))
    width = points[near, 0].max() - points[near, 0].min()
    depth = points[near, 2].max() - points[near, 2].min()
    return np.array([width, points[:, 1].max() - eye_mid[1], depth])


def onto_this_head(makehuman, head_points, eyes):
    """The move from MakeHuman's head space onto this head, and the base mesh: a per-axis scale about the eye
    midpoint, from the two heads' sizes."""
    base, body = base_mesh(makehuman)
    their_eyes, _, _ = fitted_eyes(makehuman, base)
    their_mid = (their_eyes[their_eyes[:, 0] > 0].mean(axis=0) + their_eyes[their_eyes[:, 0] < 0].mean(axis=0)) / 2
    theirs = base[body]
    theirs = theirs[(theirs[:, 1] > their_mid[1] - 1.1) & (np.abs(theirs[:, 0]) < 1.2)]
    our_mid = (eyes["left"] + eyes["right"]) / 2
    scale = head_sizes(head_points, our_mid) / head_sizes(theirs, their_mid)
    return (lambda xyz: (xyz - their_mid) * scale + our_mid), base


def skin_head(body, joints):
    """The body's skin above the collar cut (moved with the neck joint): points, faces and weights."""
    names = list(body["joint_names"])
    points, faces, weights = body["points"], body["faces"].astype(np.int64), body["weights"]
    owner = weights.argmax(axis=1)
    cut = joints["Neck1"][1] + (TAKE_C_NECK_CUT - TAKE_C_NECK1) * joints["Neck1"][1] / TAKE_C_NECK1
    keep = np.isin(owner, [names.index(name) for name in SKIN_JOINTS]) & (points[:, 1] > cut)
    kept_faces = faces[keep[faces].all(axis=1)]
    used, renumbered = np.unique(kept_faces, return_inverse=True)
    return points[used], renumbered.reshape(-1, 3), weights[used]


def outside_share(body, placed):
    """How many eye points lie outside the head's surface (a check that the eyes sit in their sockets)."""
    names = list(body["joint_names"])
    owner = body["weights"].argmax(axis=1)
    keep = np.isin(owner, [names.index(name) for name in HEAD_JOINTS])
    faces = body["faces"].astype(np.int64)
    surface = trimesh.Trimesh(body["points"], faces[keep[faces].any(axis=1)], process=False)
    closest, _, triangle = trimesh.proximity.closest_point(surface, placed)
    side = ((placed - closest) * surface.face_normals[triangle]).sum(axis=1)
    return int((side > 0).sum())


def main():
    work, makehuman = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    body = np.load(work / "gc/body/ours.npz")
    joints = json.loads((work / "gc/body/joints.json").read_text())
    (work / "head").mkdir(exist_ok=True)
    points, faces, weights = skin_head(body, joints)
    np.savez(work / "head/skin_head.npz", points=points, faces=faces, weights=weights)
    eyes = {"left": np.array(joints["LeftEye"]), "right": np.array(joints["RightEye"])}
    names = list(body["joint_names"])
    head_points = body["points"][np.isin(body["weights"].argmax(axis=1),
                                         [names.index(name) for name in HEAD_JOINTS])]
    move, base = onto_this_head(makehuman, head_points, eyes)
    eye_points, eye_faces, eye_uv = fitted_eyes(makehuman, base)
    placed = move(eye_points)
    np.savez(work / "head/eyes.npz", points=placed, faces=eye_faces, uv=eye_uv)
    shutil.copy(work / "head/eyes.npz", work / "look/eyes.npz")
    print(f"head: {len(points)} skin points; eyes {outside_share(body, placed)} of {len(placed)} points outside "
          f"the head", flush=True)


if __name__ == "__main__":
    main()
