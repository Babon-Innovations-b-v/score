"""Check the prop route's rig on a made-up body of tubes (a torso, a head, arms held down and out, legs) whose joints
and weights are known: placed into itself the skeleton and the weights come back; placed into the same body with
longer arms the hands move to the new hands; RSWT's inpainting fills an unmatched strip between two matched sides with
a blend of both; a tuck runs a part's open border on under the garment; the poke check reads a tuck under its cloth as
hidden and one over it as showing.

Run: .venv/bin/python tools/characters/maker/prop_rig_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pokes  # noqa: E402
import prop_rig  # noqa: E402
import tucks  # noqa: E402

JOINTS = {"Root": (0, 0.0, 0), "Hips": (0, 0.95, 0), "Spine1": (0, 1.1, 0), "Chest": (0, 1.3, 0),
          "Neck1": (0, 1.48, 0), "Head": (0, 1.58, 0)}
PARENTS = {"Hips": "Root", "Spine1": "Hips", "Chest": "Spine1", "Neck1": "Chest", "Head": "Neck1"}
for SIDE, SIGN in (("Left", 1.0), ("Right", -1.0)):
    JOINTS.update({SIDE + "Shoulder": (SIGN * 0.08, 1.42, 0), SIDE + "Arm": (SIGN * 0.2, 1.4, 0),
                   SIDE + "ForeArm": (SIGN * 0.375, 1.225, 0), SIDE + "Hand": (SIGN * 0.55, 1.05, 0),
                   SIDE + "Leg": (SIGN * 0.1, 0.9, 0), SIDE + "Shin": (SIGN * 0.1, 0.48, 0),
                   SIDE + "Foot": (SIGN * 0.1, 0.08, 0), SIDE + "ToeBase": (SIGN * 0.1, 0.02, 0.1)})
    PARENTS.update({SIDE + "Shoulder": "Chest", SIDE + "Arm": SIDE + "Shoulder", SIDE + "ForeArm": SIDE + "Arm",
                    SIDE + "Hand": SIDE + "ForeArm", SIDE + "Leg": "Hips", SIDE + "Shin": SIDE + "Leg",
                    SIDE + "Foot": SIDE + "Shin", SIDE + "ToeBase": SIDE + "Foot"})
NAMES = list(JOINTS)


def tube(start, end, radius, sections=24):
    """A closed cylinder from `start` to `end`."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    return trimesh.creation.cylinder(radius=radius, segment=[start, end], sections=sections)


def body(arm_reach=1.0):
    """The tube body, its arms' hands `arm_reach` times as far from the shoulders."""
    parts = [tube((0, 0.85, 0), (0, 1.45, 0), 0.15), trimesh.creation.icosphere(3, 0.1).apply_translation((0, 1.6, 0)),
             tube((0, 1.42, 0), (0, 1.52, 0), 0.05)]
    for sign in (1.0, -1.0):
        shoulder = np.array([sign * 0.2, 1.4, 0])
        hand = shoulder + arm_reach * (np.array([sign * 0.55, 1.0, 0]) - shoulder)
        parts += [tube(shoulder, hand, 0.04), tube((sign * 0.1, 0.0, 0), (sign * 0.1, 0.9, 0), 0.07)]
    mesh = trimesh.util.concatenate(parts)
    return trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, 0.02), process=False)


def bind():
    found = np.tile(np.eye(4), (len(NAMES), 1, 1))
    found[:, :3, 3] = [JOINTS[name] for name in NAMES]
    return found


def parents():
    return np.array([NAMES.index(PARENTS[name]) if name in PARENTS else -1 for name in NAMES])


def nearest_bone_weights(points):
    """Each point on the bone (joint to its child, or the joint alone) nearest it, one-hot. The root has no bone (it
    stands on the floor under the hips)."""
    places = bind()[:, :3, 3]
    children = {PARENTS[name]: name for name in PARENTS if PARENTS[name] != "Root"}
    distance = np.full((len(points), len(NAMES)), np.inf)
    for joint, name in enumerate(NAMES):
        start = places[joint]
        end = places[NAMES.index(children[name])] if name in children else start
        line = end - start
        share = np.clip(((points - start) @ line) / max(line @ line, 1e-9), 0, 1) if line @ line > 0 \
            else np.zeros(len(points))
        distance[:, joint] = np.linalg.norm(points - (start + share[:, None] * line), axis=1)
    weights = np.zeros_like(distance)
    weights[np.arange(len(points)), distance.argmin(1)] = 1.0
    return weights


def fitted(target):
    source = body()
    mean = prop_rig.landmarks(prop_rig.sampled(source, 60000))
    fit = prop_rig.landmarks(prop_rig.sampled(target, 60000))
    return source, mean, fit


def test_skeleton_into_itself_comes_back():
    _, mean, fit = fitted(body())
    out, offsets = prop_rig.fitted_bind(bind(), NAMES, parents(), mean, fit)
    assert np.abs(out[:, :3, 3] - bind()[:, :3, 3]).max() < 0.005
    assert np.allclose(offsets[NAMES.index("LeftForeArm")], np.subtract(JOINTS["LeftForeArm"], JOINTS["LeftArm"]),
                       atol=0.005)


def test_weights_into_itself_come_back():
    source, mean, fit = fitted(body())
    weights = nearest_bone_weights(source.vertices)
    moved, matched_share, _ = prop_rig.transferred(source, weights, source, np.array(NAMES), fit)
    assert matched_share > 0.99
    assert (moved.argmax(1) == weights.argmax(1)).mean() > 0.99


def test_longer_arms_move_the_hands():
    _, mean, fit = fitted(body(arm_reach=1.2))
    out, _ = prop_rig.fitted_bind(bind(), NAMES, parents(), mean, fit)
    shoulder = np.array(JOINTS["LeftArm"])
    wanted = shoulder + 1.2 * (np.array(JOINTS["LeftHand"]) - shoulder)
    assert np.linalg.norm(out[NAMES.index("LeftHand"), :3, 3] - wanted) < 0.03


def test_inpainting_blends_the_unmatched_strip():
    grid = trimesh.creation.box(extents=(1.0, 0.01, 0.2))
    plane = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(grid.vertices, grid.faces, 0.03), process=False)
    plane.merge_vertices()
    x = plane.vertices[:, 0]
    weights = np.stack([(x < 0).astype(float), (x >= 0).astype(float)], 1)
    known = np.abs(x) > 0.25
    filled = prop_rig.inpainted(plane.vertices, plane.faces, weights, known)
    middle = np.abs(x) < 0.05
    assert np.all(filled[middle, 0] > 0.2) and np.all(filled[middle, 0] < 0.8)
    assert np.allclose(filled[known], weights[known])


def test_tuck_runs_under_the_garment():
    sleeve = tube((0, 0, 0), (0, -0.3, 0), 0.05)
    hand = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(sleeve.vertices, sleeve.faces, 0.02), process=False)
    open_hand = hand.faces[hand.triangles_center[:, 1] < -0.1]
    used, renumbered = np.unique(open_hand, return_inverse=True)
    points, faces = hand.vertices[used], renumbered.reshape(-1, 3)
    weights = np.tile([1.0, 0.0], (len(points), 1))
    garment = np.array([[0.0, 0.0, 0.05], [0.0, 0.05, 0.0]])
    out_points, out_faces, out_weights = tucks.tucked(points, faces, weights, garment, np.array([[0.0, 1.0]] * 2))
    band = out_points[len(points):]
    assert len(band) and band[:, 1].max() > -0.1 + tucks.TUCK_LENGTH - 0.005
    assert np.allclose(out_weights[len(points):], [0.0, 1.0])


def test_pokes_read_inside_and_outside():
    cloth = np.array([[0.0, 0.0, 0.05]])
    normals = np.array([[0.0, 0.0, 1.0]])
    heights = pokes.tuck_out(np.array([[0.0, 0.0, 0.04], [0.0, 0.0, 0.06]]), cloth, normals)
    assert heights[0] < 0 < heights[1]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
