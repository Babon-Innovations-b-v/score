"""Check the prop route's rig on a made-up body of tubes (a torso, a head, arms held down and out, legs) whose joints
and weights are known: placed into itself the skeleton and the weights come back; placed into the same body with
the arms held lower the arm bones turn onto the new arms at their own lengths, with their offsets against their
parents as the mean skeleton's (so the clips play unchanged); RSWT's inpainting fills an unmatched strip between two matched sides with
a blend of both; a tuck runs a part's open border on along its bone, drawn in under the garment, and a border with no garment by it gets
none; the poke check reads a tuck under its cloth as
hidden and one over it as showing; a body leaning sideways is stood level; thinning part by part keeps the parts
shut along their borders; a hard part rides one joint and the cloth next to it eases onto that joint; the poke check
reads a hard part's stretch; the settle's offsets go into the bind pose and back out of the bake's shapes, as few as
miss them by MISS_MOST, a frame whose shapes put the cloth through the body keeps the unsettled cloth, a sparse morph
target reads back, and piping is cut as a thin strip down the outside of a limb.

Run: .venv/bin/python tools/characters/maker/prop_rig_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import garment_bake  # noqa: E402
import piping  # noqa: E402
import pokes  # noqa: E402
import prop_build  # noqa: E402
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


def body(arm_reach=1.0, hand_at=(0.55, 1.05)):
    """The tube body, its arms reaching from the shoulders towards `hand_at` (x, height), `arm_reach` times as far."""
    parts = [tube((0, 0.85, 0), (0, 1.45, 0), 0.15), trimesh.creation.icosphere(3, 0.1).apply_translation((0, 1.6, 0)),
             tube((0, 1.42, 0), (0, 1.52, 0), 0.05)]
    for sign in (1.0, -1.0):
        shoulder = np.array([sign * 0.2, 1.4, 0])
        hand = shoulder + arm_reach * (np.array([sign * hand_at[0], hand_at[1], 0]) - shoulder)
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


def test_lowered_arms_turn_the_arm_bones():
    lowered = (0.42, 0.92)
    _, mean, fit = fitted(body(hand_at=lowered))
    out, offsets = prop_rig.fitted_bind(bind(), NAMES, parents(), mean, fit)
    shoulder = np.array([0.2, 1.4, 0.0])
    line = np.array([lowered[0], lowered[1], 0.0]) - shoulder
    line /= np.linalg.norm(line)
    for name in ("LeftForeArm", "LeftHand"):
        place = out[NAMES.index(name), :3, 3] - shoulder
        assert np.linalg.norm(place - (place @ line) * line) < 0.02, name
    forearm = np.subtract(JOINTS["LeftHand"], JOINTS["LeftForeArm"])
    assert abs(np.linalg.norm(offsets[NAMES.index("LeftHand")]) - np.linalg.norm(forearm)) < 0.005
    assert np.allclose(offsets[NAMES.index("LeftHand")], forearm, atol=0.005)


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
    hand.merge_vertices()
    open_hand = hand.faces[hand.triangles_center[:, 1] < -0.1]
    used, renumbered = np.unique(open_hand, return_inverse=True)
    points, faces = hand.vertices[used], renumbered.reshape(-1, 3)
    weights = np.tile([1.0, 0.0], (len(points), 1))
    turns = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    cuff = np.concatenate([np.stack([0.055 * np.cos(turns), np.full(48, height), 0.055 * np.sin(turns)], 1)
                           for height in np.linspace(-0.13, 0.0, 14)])
    bones = {0: [(np.array([0.0, -0.3, 0.0]), np.zeros(3))], 1: [(np.zeros(3), np.array([0.0, 0.3, 0.0]))]}
    whole = trimesh.creation.cylinder(radius=0.056, segment=[(0, -0.3, 0), (0, 0.0, 0)], sections=48)
    parents = np.array([1, -1])
    out_points, out_faces, out_weights = tucks.tucked(points, faces, weights, cuff, np.tile([0.0, 1.0], (len(cuff), 1)),
                                                      bones, whole, parents)
    band = out_points[len(points):]
    ring = np.unique(tucks.border_edges(faces))
    assert len(band) and abs(band[:, 1].mean() - (points[ring, 1].mean() + tucks.TUCK_LENGTH)) < 0.002
    assert np.linalg.norm(band[:, [0, 2]], axis=1).max() < 0.05 * (1 - tucks.TUCK_SHRINK) + 1e-6
    assert np.allclose(out_weights[len(points):], [0.0, 1.0])
    alone, _, _ = tucks.tucked(points, faces, weights, cuff + [0.0, 1.0, 0.0], np.tile([0.0, 1.0], (len(cuff), 1)),
                               bones, whole, parents)
    assert len(alone) == len(points)
    short = trimesh.creation.cylinder(radius=0.056, segment=[(0, -0.3, 0), (0, -0.09, 0)], sections=48)
    alone, _, _ = tucks.tucked(points, faces, weights, cuff, np.tile([0.0, 1.0], (len(cuff), 1)), bones, short,
                               parents)
    assert len(alone) == len(points)


def test_pokes_read_inside_and_outside():
    outer = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    heights = pokes.tuck_out(np.array([[0.0, 0.0, 0.04], [0.0, 0.0, 0.06]]), outer)
    assert heights[0] < 0 < heights[1]


def test_pokes_read_a_band_under_two_overlapping_parts_as_hidden():
    first = trimesh.creation.box(extents=(0.2, 0.1, 0.1))
    second = trimesh.creation.box(extents=(0.1, 0.1, 0.3))
    overlapping = trimesh.util.concatenate([first, second])
    heights = pokes.tuck_out(np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.3]]), overlapping)
    assert heights[0] < 0 < heights[1]


def test_pokes_hold_cloth_to_the_shipped_bodys_record():
    record = {"rest_crossings": 20, "verdict": {}, "clips": {"walking": {"most_crossings": 400},
                                                            "new": {"most_crossings": 30}}}
    pokes.against(record, {"body": "shipped.glb", "clips": {"walking": {"most_crossings": 5000}}})
    assert record["cloth_worse_than_shipped"] == ["new"] and not record["verdict"]["cloth_through_cloth"]


def test_a_leaning_body_is_stood_level():
    angle = np.radians(7.0)
    lean = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    points = prop_rig.sampled(body(), 60000) @ lean.T
    turn, scale, shift = prop_rig.stood(points, 1.75)
    stood = points @ turn.T * scale + shift
    head = stood[stood[:, 1] > 1.75 - 0.06 * 1.75].mean(0)
    feet = stood[stood[:, 1] < 0.08 * 1.75]
    assert abs(head[0] - (feet[feet[:, 0] > 0].mean(0)[0] + feet[feet[:, 0] < 0].mean(0)[0]) / 2) < 0.005


def test_thinning_keeps_the_parts_shut():
    sphere = trimesh.creation.icosphere(4, 0.2)
    part_of = (sphere.triangles_center[:, 1] > 0).astype(int)
    thin, thin_parts = prop_rig.decimated(sphere, part_of, 1500)
    assert thin.is_watertight and len(thin.faces) <= 1500
    border = sphere.vertices[np.intersect1d(sphere.faces[part_of == 0], sphere.faces[part_of == 1])]
    kept = thin.vertices[np.intersect1d(thin.faces[thin_parts == 0], thin.faces[thin_parts == 1])]
    assert len(border) == len(kept) and np.allclose(np.sort(border, 0), np.sort(kept, 0))


def test_a_band_takes_its_own_limbs_weights():
    parents = np.array([-1, 0, 0, 1, 2])  # hips; left and right shin; left and right foot
    garment = np.array([[0.05, 0.3, 0.0], [-0.02, 0.3, 0.0]])
    weights = np.zeros((2, 5))
    weights[0, 1], weights[1, 2] = 1.0, 1.0
    found = tucks.limb_weights(np.array([[0.0, 0.3, 0.0]]), np.array([3]), garment, weights, parents)
    assert found[0, 1] == 1.0


def test_a_hard_part_rides_one_joint_and_the_cloth_by_it_follows():
    names = ["Hips", "LeftShin", "LeftFoot"]
    boot = np.array([[0.1, 0.05, 0.0], [0.1, 0.2, 0.0]])
    assert prop_build.rigid_joint("boot_l", boot, np.ones((2, 3)), names) == "LeftFoot"
    cloth = np.array([[0.1, 0.21, 0.0], [0.1, 0.5, 0.0]])
    eased = prop_build.eased_to_hard(cloth, np.array([[0, 1.0, 0], [0, 1.0, 0]]), boot,
                                     np.array(["LeftFoot", "LeftFoot"], dtype=object), names, np.array([-1, 0, 1]))
    assert eased[0, 2] > 0.6 and eased[1, 2] == 0.0


def test_pokes_read_a_hard_parts_stretch():
    part = pokes.joins.Part("boot_l", np.array([[0, 0, 0], [1.0, 0, 0], [0, 1.0, 0]]), np.zeros((3, 4)),
                            np.eye(4)[:3], np.array([[0, 1, 2]]))
    edges = pokes.hard_edges([(part, "hard", None)])
    assert abs(pokes.stretch({id(part): part.points * 1.5}, edges) - 1.5) < 1e-9


def test_pokes_read_a_tuck_standing_out_at_the_bind_pose(monkeypatch):
    """#21: pokes.bind measures the tucks in the bind pose alone; a band 10 mm out of the person fails before any clip,
    one 2 mm under it passes."""
    box = trimesh.creation.box(extents=(0.2, 0.2, 0.2))

    def found(height):
        coat = pokes.joins.Part("coat", np.asarray(box.vertices), np.zeros((8, 4)), np.tile([1.0, 0, 0, 0], (8, 1)),
                                np.asarray(box.faces))
        band = np.array([[0.0, 0.0, height], [0.01, 0.0, height], [0.0, 0.01, height]])
        boot = pokes.joins.Part("boot_r", np.vstack([np.asarray(box.vertices) * 0.5, band]), np.zeros((11, 4)),
                                np.tile([1.0, 0, 0, 0], (11, 1)), np.vstack([np.asarray(box.faces), [[8, 9, 10]]]))
        return [(coat, pokes.GARMENT, None), (boot, "hard", 8)]

    monkeypatch.setattr(pokes.joins, "read_glb", lambda path: ({}, b""))
    for height, passes in ((0.11, False), (0.098, True)):
        monkeypatch.setattr(pokes, "surfaces", lambda document, blob, outfit=None, height=height: found(height))
        record = pokes.bind("body.glb")
        assert record["pass"] is passes and set(record["parts"]) == {"boot_r"}, record
    assert abs(record["worst_tuck_out_mm"] + 2.0) < 0.5, record


def test_the_bake_carries_offsets_into_the_bind_pose_and_keeps_them():
    turn = np.eye(4)
    turn[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
    frames = np.linspace(0, 1, 6)
    wanted = np.stack([np.outer(np.ones(5), [0.01 * share, 0.002 * share ** 2, 0.0]) for share in frames])
    data = {"moves_walking": np.tile(turn, (6, 5, 1, 1)), "lead_in": 0, "cloth_joints": np.zeros((5, 4), int),
            "cloth_weights": np.tile([1.0, 0, 0, 0], (5, 1))}
    offsets = np.einsum("ab,fpb->fpa", turn[:3, :3], wanted)
    blended = garment_bake.blended_turns(data, "walking")
    assert np.allclose(garment_bake.bind_offsets(blended, offsets), wanted, atol=1e-6)
    shapes, weights, owner, missed = garment_bake.clip_shapes(blended, offsets, np.ones((5, 1)))
    assert missed <= garment_bake.MISS_MOST and len(shapes) == 1 and list(owner) == [0], "one shape is near enough"
    assert np.abs(np.einsum("fs,spa->fpa", weights, shapes) - wanted).max() <= garment_bake.MISS_MOST


def test_a_frame_whose_shape_crosses_the_body_keeps_the_unsettled_cloth():
    cloth = np.array([[-1.0, 0.0, -1.0], [1.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
    body = np.array([[0.0, 0.1, 0.0], [0.0, 0.3, 0.0], [0.2, 0.3, 0.0]])
    data = {"moves_walking": np.tile(np.eye(4), (2, 1, 1, 1)), "lead_in": 0, "cloth_points": cloth,
            "cloth_faces": np.array([[0, 1, 2]]), "cloth_joints": np.zeros((3, 4), int),
            "cloth_weights": np.tile([1.0, 0, 0, 0], (3, 1)), "held": np.zeros(3, bool),
            "held_collider": np.full(3, -1), "collider_points": body, "collider_faces": np.array([[0, 1, 2]]),
            "collider_joints": np.zeros((3, 4), int), "collider_weights": np.tile([1.0, 0, 0, 0], (3, 1))}
    blended = garment_bake.blended_turns(data, "walking")
    up = np.tile([0.0, 0.2, 0.0], (1, 3, 1))
    shares, plain, kept = garment_bake.frame_shares(data, "walking", blended, up, np.array([[0.0], [1.0]]),
                                                    np.zeros(1, int), np.ones((3, 1)))
    assert list(shares[:, 0]) == [1.0, 0.0] and plain == [0, 0] and kept == [0, 0], (shares, plain, kept)


def test_regions_follow_the_limbs_and_share_their_borders():
    cloth = trimesh.creation.box(extents=[0.4, 0.1, 0.1]).subdivide_to_size(0.01)
    left = cloth.vertices[:, 0] > 0
    data = {"cloth_points": cloth.vertices, "cloth_faces": cloth.faces,
            "cloth_joints": np.where(left, 1, 0)[:, None].repeat(4, 1), "cloth_weights": np.tile([1.0, 0, 0, 0],
                                                                                                (len(left), 1)),
            "joint_names": np.array(["Chest", "LeftArm"])}
    shares = garment_bake.regions(data)
    assert shares.shape == (len(left), 2) and np.allclose(shares.sum(1), 1)
    far = np.abs(cloth.vertices[:, 0]) > 0.15
    assert (shares[far & left, 0] > 0.99).all() and (shares[far & ~left, 1] > 0.99).all(), "LeftArm sorts first"
    assert ((shares > 0.05) & (shares < 0.95)).any(1).sum() > 0, "the border is softened"


def test_piping_is_cut_down_the_outside_of_a_limb():
    tube = trimesh.creation.cylinder(radius=0.05, height=0.6, sections=24)
    tube.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tube = tube.subdivide().subdivide()
    tube.apply_translation([0.1, 0.6, 0.0])
    places = {name: np.array(place, float) for name, place in JOINTS.items()}
    places.update(LeftLeg=np.array([0.1, 0.9, 0.0]), LeftShin=np.array([0.1, 0.6, 0.0]),
                  LeftFoot=np.array([0.1, 0.3, 0.0]))
    points, faces, weights, strip = piping.cut_piping(tube.vertices, tube.faces, np.ones((len(tube.vertices), 1)),
                                                      places)
    width = piping.PIPING_WIDTH
    middles = points[faces[strip]].mean(1)
    assert strip.any() and (middles[:, 0] > 0.14).all() and (np.abs(middles[:, 2]) < width / 2).all()
    area = np.linalg.norm(np.cross(*(points[faces[strip]][:, 1:] - points[faces[strip]][:, :1]).transpose(1, 0, 2)),
                          axis=1).sum() / 2
    assert abs(area - width * (0.6 - piping.LEG_RUN[0])) < 0.15 * width * 0.6, area


def test_a_sparse_morph_target_reads_back():
    contents = garment_bake.glb.Contents()
    values = np.zeros((6, 3))
    values[[1, 4]] = [[0.01, 0.0, 0.0], [0.0, -0.02, 0.0]]
    index = garment_bake.sparse_target(contents, values)
    document = {"accessors": contents.accessors, "bufferViews": contents.views}
    assert np.allclose(garment_bake.joins.target_values(document, contents.blob(), index, 6), values, atol=1e-7)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
