"""Checks the join and stance measures (`joins.py`) and the two fixes they were made for, on shapes made here: the bare
hand running up under the cuff (`skin.bare_hands`) and a short trouser leg drawn down into its boot
(`boots.lengthened`), and a short sleeve drawn down to the wrist (`work_suit.sleeves_to_the_wrists`). Numpy, scipy and trimesh, nothing else; runs as a script or under pytest."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import boots  # noqa: E402
import joins  # noqa: E402
import skin  # noqa: E402


def tube(radius, start, end, rings=40, around=24, axis=0):
    """Points of an open tube round the line along `axis` from `start` to `end`, and its faces."""
    angles = np.linspace(0, 2 * np.pi, around, endpoint=False)
    stations = np.linspace(start, end, rings)
    points = []
    for station in stations:
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


def test_a_sleeve_past_the_hand_overlaps_by_the_difference():
    sleeve, _ = tube(0.05, 0.0, 0.26)
    hand, _ = tube(0.03, 0.24, 0.34)
    got, gap = joins.measure_join(sleeve, hand, np.zeros(3), np.array([0.25, 0.0, 0.0]))
    assert abs(got - 0.02) < 0.004, got
    assert gap < 0.025, gap


def test_a_sleeve_short_of_the_hand_is_a_gap():
    sleeve, _ = tube(0.05, 0.0, 0.20)
    hand, _ = tube(0.03, 0.24, 0.34)
    got, gap = joins.measure_join(sleeve, hand, np.zeros(3), np.array([0.25, 0.0, 0.0]))
    assert abs(got + 0.04) < 0.004, got
    assert gap > 0.04, gap


def test_a_hand_with_no_sleeve_fails():
    hand, _ = tube(0.03, 0.24, 0.34)
    got, _ = joins.measure_join(np.zeros((0, 3)), hand, np.zeros(3), np.array([0.25, 0.0, 0.0]))
    assert got == joins.NO_SLEEVE


def test_a_slanted_cuff_is_judged_on_its_short_side():
    sleeve, _ = tube(0.05, 0.0, 0.30)
    # Cut the cuff on a slant: one side reaches 0.30, the far side only 0.20.
    keep = sleeve[:, 0] <= 0.25 + 0.05 * sleeve[:, 1] / 0.05
    hand, _ = tube(0.03, 0.24, 0.34)
    got, gap = joins.measure_join(sleeve[keep], hand, np.zeros(3), np.array([0.25, 0.0, 0.0]))
    # It reaches past the hand on one side, so only the opening shows the bare side.
    assert got > 0.0, got
    assert gap > 0.04, gap


def joint_frames(places):
    """(n, 4, 4) worlds standing at `places`, unturned."""
    worlds = np.repeat(np.eye(4)[None], len(places), axis=0)
    worlds[:, :3, 3] = places
    return worlds


def test_the_stance_is_ankles_across_over_hips_across():
    names = ["LeftLeg", "RightLeg", "LeftFoot", "RightFoot"]
    feet_wide = joint_frames(np.array([[0.1, 0.9, 0.0], [-0.1, 0.9, 0.0], [0.2, 0.1, 0.0], [-0.2, 0.1, 0.0]]))
    assert abs(joins.stance_ratio(feet_wide, names) - 2.0) < 1e-9
    # A step forward is not width: only the spacing across the hips counts.
    stepping = joint_frames(np.array([[0.1, 0.9, 0.0], [-0.1, 0.9, 0.0], [0.1, 0.1, 0.3], [-0.1, 0.1, -0.3]]))
    assert abs(joins.stance_ratio(stepping, names) - 1.0) < 1e-9


def test_the_verdict_holds_each_measure_to_its_range():
    record = {"outfits": {"work": {"standing": {"wrist_Left": 0.02, "wrist_Left_opening": 0.02,
                                                "ankle_Left": -0.01, "ankle_Left_opening": 0.02}}},
              "stance": {"mean": 2.1}}
    found = joins.verdict(record)
    assert found["wrist"]["pass"] and not found["ankle"]["pass"] and not found["stance"]["pass"]


def test_a_hand_pressed_into_other_clothes_is_hidden():
    hand = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]])
    cover = np.array([[0.51, 0.0, 0.0]])
    assert np.array_equal(joins.unburied(hand, cover), hand[:1])


def test_cloth_is_measured_over_its_triangles():
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    samples = joins.surface_samples(points, np.array([[0, 1, 2]]))
    assert len(samples) == 15 and np.allclose(samples.mean(axis=0), points.mean(axis=0))


def upright_boot(top):
    """A boot's shaft: an open upright tube from the floor to `top`, round x = z = 0."""
    return tube(0.06, 0.0, top, axis=1)


def test_a_short_trouser_leg_is_drawn_into_its_boot():
    boot, _ = upright_boot(0.20)
    leg, _ = tube(0.08, 0.26, 0.90, axis=1)
    limbs = np.array(["left_leg"] * len(leg))
    moved = boots.lengthened(leg, limbs, boot, "Left")
    assert moved[:, 1].min() <= 0.20 - boots.REACH_INTO + 1e-6
    # The top of the leg, above the stretch, is where it was.
    high = leg[:, 1] > 0.26 + boots.STRETCH_OVER + 1e-6
    assert np.allclose(moved[high], leg[high])


def test_a_trouser_leg_that_reaches_is_left_alone():
    boot, _ = upright_boot(0.20)
    leg, _ = tube(0.08, 0.12, 0.90, axis=1)
    limbs = np.array(["left_leg"] * len(leg))
    assert np.array_equal(boots.lengthened(leg, limbs, boot, "Left"), leg)


def test_the_other_leg_is_not_stretched():
    boot, _ = upright_boot(0.20)
    leg, _ = tube(0.08, 0.26, 0.90, axis=1)
    limbs = np.array(["right_leg"] * len(leg))
    assert np.array_equal(boots.lengthened(leg, limbs, boot, "Left"), leg)


def an_arm():
    """A body that is one arm along +x: a forearm tube from the elbow at 0 to the wrist at 0.25 and a hand tube on to
    0.35, each point weighted wholly to its bone."""
    names = ["LeftForeArm", "LeftHand", "RightForeArm", "RightHand"]
    points, faces = tube(0.03, 0.0, 0.35, rings=36)
    weights = np.zeros((len(points), len(names)))
    weights[points[:, 0] < 0.25, 0] = 1.0
    weights[points[:, 0] >= 0.25, 1] = 1.0
    places = [[0.0, 0.0, 0.0], [0.25, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 1.0, 0.0]]
    return skin.Body(points, faces, weights, names, places)


def test_the_bare_hand_runs_up_under_the_cuff():
    points, _, _ = skin.bare_hands(an_arm())
    reaches_up_to = points[:, 0].min()
    assert abs(reaches_up_to - 0.25 * (1 - skin.UNDER_THE_CUFF)) < 0.012, reaches_up_to
    assert points[:, 0].max() > 0.34


def test_a_short_sleeve_is_drawn_to_the_wrist():
    import work_suit
    sleeve, _ = tube(0.05, -0.30, 0.15)
    limbs = np.array(["left_arm"] * len(sleeve))
    moved = work_suit.sleeves_to_the_wrists(sleeve, limbs, an_arm())
    assert abs(moved[:, 0].max() - (0.25 + work_suit.CUFF_PAST_WRIST)) < 1e-6
    # Above the stretch the sleeve is where it was.
    high = sleeve[:, 0] < 0.15 - work_suit.SLEEVE_STRETCH_OVER - 1e-6
    assert np.allclose(moved[high], sleeve[high])


def test_a_sleeve_that_reaches_is_left_alone():
    import work_suit
    sleeve, _ = tube(0.05, -0.30, 0.28)
    limbs = np.array(["left_arm"] * len(sleeve))
    assert np.array_equal(work_suit.sleeves_to_the_wrists(sleeve, limbs, an_arm()), sleeve)


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
