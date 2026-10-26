"""The people tools' pieces hold a body together: the glTF writer (glb.py) writes back what it was given and refuses a
node graph that is no tree; every joint hangs its points on one surface (regions.py: skin, clothes or boots); the join
measures (joins.py) read a sleeve over a hand as overlap and one short of it as a gap, a stance as ankles across over
hips across, and hold each to its range; and a clip's wide feet are brought in (stance.py) with the legs' lengths, the
feet's turn and a planted foot's place kept.

Shapes made here (tubes, legs, small files) whose answers are set by how they are made.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_a_tangled_node_graph_is_refused_and_a_tree_let_through: refuse_a_tangled_graph's two-parents check (`if child
  in parent_of: raise ...`) dropped; and, apart, its loop walk (`if walk in seen: raise ...`) dropped (the test then
  never ends: red by the time limit). The own-child check alone dropped stays green: the loop walk refuses that graph
  too.
- test_the_numbers_come_back_out_as_they_went_in: Contents.reading's `"count": len(values) // each` made
  `len(values)`.
- test_a_picture_is_kept_byte_for_byte_on_a_four_byte_boundary: Contents.picture's `self._pad()` dropped.
- test_a_run_of_numbers_that_does_not_divide_is_refused: reading's `if len(values) % each: raise` dropped.
- test_every_joint_hangs_its_points_on_one_surface: regions' `(SKIN, ("Hand",))` rule dropped; and, apart,
  surfaces' order `(SKIN, CLOTHES, BOOTS)` made `sorted(found)`.
- test_a_sleeve_past_the_hand_overlaps_and_one_short_of_it_is_a_gap: overlap's `outer[near].max() - begins` made
  `outer[near].min() - begins`.
- test_a_slanted_cuff_is_judged_on_its_short_side: opening's `distance.max()` made `distance.min()`.
- test_a_hand_with_no_sleeve_fails: measure_join's `if not len(outer): return NO_SLEEVE, ...` dropped (no sleeve
  then measures as no number at all, which no gate fails).
- test_the_stance_is_ankles_across_over_hips_across: stance_ratio's `abs(float(ankles @ hips))` made
  `float(np.linalg.norm(ankles)) * hip_spacing` (a step forward counted as width).
- test_the_verdict_holds_each_measure_to_its_range: verdict's `overlap_value >= LEAST_OVERLAP` made `>= -1`.
- test_a_hand_pressed_into_other_clothes_is_hidden: unburied returns `points` always.
- test_cloth_is_measured_over_its_triangles: SAMPLES_A_SIDE = 1 (corners only).
- test_wide_feet_are_brought_in_to_hip_width: moves_in's `max(0.0, out - allowed)` made `max(0.0, out - 2 * allowed)`.
- test_the_legs_keep_their_lengths_and_the_feet_their_turn: knee_for's `height = np.sqrt(...)` made `height = 0.0`
  (the knee laid on the hip-ankle line).
- test_a_planted_foot_stays_planted_while_the_hips_sway_and_turn: narrowed's `shift = -sign * moves[side] * across`
  made `shift = -sign * moves[side] * hips_line(world, names)[1][frame]` (each frame's own hips line).
- test_a_narrow_stance_is_left_alone: narrowed's `if not any(moves.values()): return world` dropped.
"""
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import glb  # noqa: E402
import joins  # noqa: E402
import regions  # noqa: E402
import stance  # noqa: E402

BARE = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}]}


def refusal(document):
    """What the writer said turning this document away, or "" when it let it through."""
    try:
        glb.refuse_a_tangled_graph(document)
    except ValueError as complaint:
        return str(complaint)
    return ""


def test_a_tangled_node_graph_is_refused_and_a_tree_let_through():
    """A node its own child cost fifteen minutes of Godot at full tilt (#36); two parents and a ring are no tree."""
    assert refusal({"nodes": [{"children": [0]}]})
    assert refusal({"nodes": [{"children": [2]}, {"children": [2]}, {}]})
    assert refusal({"nodes": [{"children": [1]}, {"children": [2]}, {"children": [0]}]})
    assert refusal({"nodes": [{"children": [1, 2]}, {"children": [3]}, {}, {}]}) == ""


def test_the_numbers_come_back_out_as_they_went_in(tmp_path):
    contents = glb.Contents()
    where = contents.reading([0.0, 0.0, 0.0, 1.0, 2.0, 3.0], "VEC3", glb.FLOAT, glb.ARRAY_BUFFER, with_bounds=True)
    contents.reading([0, 1, 2], "SCALAR", glb.UNSIGNED_SHORT, glb.ELEMENT_ARRAY_BUFFER)
    glb.write(tmp_path / "one.glb", dict(BARE, nodes=[{"name": "one"}]), contents)
    read = glb.read_document(tmp_path / "one.glb")
    assert len(read["accessors"]) == 2 and read["accessors"][where]["count"] == 2
    assert read["accessors"][where]["min"] == [0.0, 0.0, 0.0] and read["accessors"][where]["max"] == [1.0, 2.0, 3.0]
    assert read["nodes"][0]["name"] == "one"


def test_a_picture_is_kept_byte_for_byte_on_a_four_byte_boundary(tmp_path):
    contents = glb.Contents()
    contents.reading([0.0, 0.0, 0.0], "VEC3", glb.FLOAT, glb.ARRAY_BUFFER)
    contents.reading([0], "SCALAR", glb.UNSIGNED_SHORT)  # 14 bytes so far: the picture must be padded to 16
    encoded = b"\x89PNG not really, but five bytes past the header"
    image = contents.picture(encoded)
    glb.write(tmp_path / "pictured.glb", dict(BARE, nodes=[{"name": "one"}]), contents)
    read = glb.read_document(tmp_path / "pictured.glb")
    view = read["bufferViews"][read["images"][image]["bufferView"]]
    assert read["images"][image]["mimeType"] == "image/png" and view["byteLength"] == len(encoded)
    assert view["byteOffset"] % 4 == 0
    blob = (tmp_path / "pictured.glb").read_bytes()
    body = blob[20 + int.from_bytes(blob[12:16], "little") + 8:]
    assert body[view["byteOffset"]:view["byteOffset"] + len(encoded)] == encoded


def test_a_run_of_numbers_that_does_not_divide_is_refused():
    with pytest.raises(ValueError):
        glb.Contents().reading([1.0, 2.0], "VEC3", glb.FLOAT)


def test_every_joint_hangs_its_points_on_one_surface():
    """A face and a bare hand are skin, a foot wears a boot, everything else is clothed (a forearm is no hand: `Hand`
    is in no other joint's name). A real slice of the body model's joints, names as it reports them."""
    for joint in ("Head", "HeadEnd", "Jaw", "LeftEye", "RightEye", "Neck1", "Neck2", "LeftHand", "RightHandPinkyEnd",
                  "LeftHandThumb1"):
        assert regions.region_of(joint) == regions.SKIN, joint
    for joint in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeEnd"):
        assert regions.region_of(joint) == regions.BOOTS, joint
    for joint in ("Root", "Hips", "Spine1", "Spine2", "Chest", "LeftShoulder", "LeftArm", "LeftForeArm", "RightLeg",
                  "RightShin"):
        assert regions.region_of(joint) == regions.CLOTHES, joint
    skeleton = ["Root", "Hips", "Spine1", "Chest", "Neck1", "Head", "LeftHand", "RightFoot"]
    assert regions.regions_of(skeleton) == ["clothes", "clothes", "clothes", "clothes", "skin", "skin", "skin", "boots"]
    assert regions.surfaces(skeleton) == ["skin", "clothes", "boots"]
    assert regions.surfaces(["Hips", "Spine1"]) == ["clothes"]


def tube(radius, start, end, rings=40, around=24, axis=0):
    """Points of an open tube round the line along `axis` from `start` to `end`, and its faces."""
    angles = np.linspace(0, 2 * np.pi, around, endpoint=False)
    points = []
    for station in np.linspace(start, end, rings):
        for angle in angles:
            point = np.zeros(3)
            point[axis] = station
            others = [index for index in range(3) if index != axis]
            point[others[0]] = radius * np.cos(angle)
            point[others[1]] = radius * np.sin(angle)
            points.append(point)
    faces = []
    for ring in range(rings - 1):
        for step in range(around):
            here, next_step = ring * around + step, ring * around + (step + 1) % around
            faces.append([here, next_step, here + around])
            faces.append([next_step, next_step + around, here + around])
    return np.array(points), np.array(faces)


FOREARM, HAND = np.zeros(3), np.array([0.25, 0.0, 0.0])


def test_a_sleeve_past_the_hand_overlaps_and_one_short_of_it_is_a_gap():
    """A hand from 0.24 m: a sleeve to 0.26 overlaps it by 0.02, one to 0.20 leaves a 0.04 gap."""
    hand, _ = tube(0.03, 0.24, 0.34)
    got, gap = joins.measure_join(tube(0.05, 0.0, 0.26)[0], hand, FOREARM, HAND)
    assert abs(got - 0.02) < 0.004 and gap < 0.025, (got, gap)
    got, gap = joins.measure_join(tube(0.05, 0.0, 0.20)[0], hand, FOREARM, HAND)
    assert abs(got + 0.04) < 0.004 and gap > 0.04, (got, gap)


def test_a_slanted_cuff_is_judged_on_its_short_side():
    """A cuff cut on a slant reaches 0.30 on one side and 0.20 on the other: it overlaps the hand, but the opening on
    the short side shows it bare."""
    sleeve, _ = tube(0.05, 0.0, 0.30)
    keep = sleeve[:, 0] <= 0.25 + 0.05 * sleeve[:, 1] / 0.05
    got, gap = joins.measure_join(sleeve[keep], tube(0.03, 0.24, 0.34)[0], FOREARM, HAND)
    assert got > 0.0 and gap > 0.04, (got, gap)


def test_a_hand_with_no_sleeve_fails():
    got, _ = joins.measure_join(np.zeros((0, 3)), tube(0.03, 0.24, 0.34)[0], FOREARM, HAND)
    assert got < joins.LEAST_OVERLAP


def joint_frames(places):
    """(n, 4, 4) worlds standing at `places`, unturned."""
    worlds = np.repeat(np.eye(4)[None], len(places), axis=0)
    worlds[:, :3, 3] = places
    return worlds


def test_the_stance_is_ankles_across_over_hips_across():
    names = ["LeftLeg", "RightLeg", "LeftFoot", "RightFoot"]
    feet_wide = joint_frames(np.array([[0.1, 0.9, 0.0], [-0.1, 0.9, 0.0], [0.2, 0.1, 0.0], [-0.2, 0.1, 0.0]]))
    assert abs(joins.stance_ratio(feet_wide, names) - 2.0) < 1e-9  # 0.4 across over 0.2
    # A step forward is not width: only the spacing across the hips counts.
    stepping = joint_frames(np.array([[0.1, 0.9, 0.0], [-0.1, 0.9, 0.0], [0.1, 0.1, 0.3], [-0.1, 0.1, -0.3]]))
    assert abs(joins.stance_ratio(stepping, names) - 1.0) < 1e-9


def test_the_verdict_holds_each_measure_to_its_range():
    """A wrist overlapping 2 cm passes (at least 1 cm), an ankle 1 cm short fails, a stance of 2.1 is past 1.2."""
    record = {"outfits": {"work": {"standing": {"wrist_Left": 0.02, "wrist_Left_opening": 0.02,
                                                "ankle_Left": -0.01, "ankle_Left_opening": 0.02}}},
              "stance": {"mean": 2.1}}
    found = joins.verdict(record)
    assert found["wrist"]["pass"] and not found["ankle"]["pass"] and not found["stance"]["pass"]


def test_a_hand_pressed_into_other_clothes_is_hidden():
    hand = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]])
    assert np.array_equal(joins.unburied(hand, np.array([[0.51, 0.0, 0.0]])), hand[:1])


def test_cloth_is_measured_over_its_triangles():
    """A grid of 4 a side over one triangle: 15 points whose middle is the triangle's."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    samples = joins.surface_samples(points, np.array([[0, 1, 2]]))
    assert len(samples) == 15 and np.allclose(samples.mean(axis=0), points.mean(axis=0))


NAMES = ["Hips", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot",
         "RightToeBase"]
PARENTS = np.array([-1, 0, 1, 2, 3, 0, 5, 6, 7])


def legs(feet_out, frames=5, sway=0.0, twist=0.0):
    """World transforms of standing legs, hips 0.2 m apart, each ankle `feet_out` out from its hip, the hips swaying
    `sway` metres sideways and turning `twist` degrees about up frame by frame while the feet stay put."""
    world = np.repeat(np.eye(4)[None, None], frames, axis=0).repeat(len(NAMES), axis=1)
    for frame in range(frames):
        drift = sway * frame
        turn = np.radians(twist * frame)
        places = {"Hips": [drift, 1.0, 0.0]}
        for side, sign in (("Left", 1.0), ("Right", -1.0)):
            hip = np.array([drift + sign * 0.1 * np.cos(turn), 0.95, -sign * 0.1 * np.sin(turn)])
            ankle = np.array([sign * (0.1 + feet_out), 0.08, 0.0])
            places[side + "Leg"] = hip
            places[side + "Shin"] = (hip + ankle) / 2 + np.array([0.0, 0.0, 0.03])
            places[side + "Foot"] = ankle
            places[side + "ToeBase"] = ankle + np.array([0.0, -0.05, 0.12])
        for name, place in places.items():
            world[frame, NAMES.index(name), :3, 3] = place
    return world


def bone(world, first, second):
    return np.linalg.norm(world[:, NAMES.index(first), :3, 3] - world[:, NAMES.index(second), :3, 3], axis=1)


def test_wide_feet_are_brought_in_to_hip_width():
    """Ankles 0.42 m apart over hips 0.2 apart come in to 0.2 (WIDEST 1, owner 2026-10-09: "why do they stand so
    wide")."""
    moved = stance.narrowed(legs(0.11), NAMES, PARENTS)
    spacing = moved[:, NAMES.index("LeftFoot"), 0, 3] - moved[:, NAMES.index("RightFoot"), 0, 3]
    assert np.allclose(spacing, 0.2, atol=1e-9)


def test_the_legs_keep_their_lengths_and_the_feet_their_turn():
    before = legs(0.11)
    after = stance.narrowed(before, NAMES, PARENTS)
    for first, second in (("LeftLeg", "LeftShin"), ("LeftShin", "LeftFoot"), ("RightLeg", "RightShin")):
        assert np.allclose(bone(after, first, second), bone(before, first, second))
    assert np.allclose(after[:, NAMES.index("LeftFoot"), :3, :3], before[:, NAMES.index("LeftFoot"), :3, :3])
    assert np.allclose(after[:, NAMES.index("LeftFoot"), 1, 3], before[:, NAMES.index("LeftFoot"), 1, 3])


def test_a_planted_foot_stays_planted_while_the_hips_sway_and_turn():
    after = stance.narrowed(legs(0.11, sway=0.004, twist=3.0), NAMES, PARENTS)
    ankle = after[:, NAMES.index("LeftFoot"), :3, 3]
    assert np.allclose(ankle, ankle[0])


def test_a_narrow_stance_is_left_alone():
    before = legs(0.0)
    assert stance.narrowed(before, NAMES, PARENTS) is before
