"""posture: a clip standing at ease hangs its upper arms near its sides and looks ahead, and the check fails one that
holds its arms out or gazes up. Each row is a toy rig (the clips rig's joint names, straight bones) posed with its
upper arms some degrees out and its head some degrees back, with a gaze at rest some degrees up (the face's), feet
some way apart: measured as played, its faults are the ones it shows; relaxed, its arms hang at ARM_HANG_DEGREES (or
where a body that blocks them lets them), its highest gaze is GAZE_TOP_DEGREES up, its feet under its hips, and it has
no faults.

Breaks that turn it red (each applied once, seen red, reverted), 2026-11-25:
- faults' `values["median"] > ARM_MOST_DEGREES` made `> 90`: an arm held 20 degrees out passes.
- faults' gaze check dropped: a head tipped 10 degrees back passes.
- arms_out's `sign *` dropped: the right arm, out to its own side, reads as turned in and is never brought in.
- relaxed's head turn made `-excess / 2.0`: the head is tipped further back, not levelled.
- gaze_up's `@ bind[head].T` dropped: a head whose bind is turned reads its bind's turn as the gaze's.
- relaxed's `stance.narrowed` dropped: the feet stay twice the hips apart.
- hung's `clears` ignored (the first angle taken): the arm is put through the body that blocks it.
"""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from tools.characters import played, posture

NAMES = ["Root", "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd",
         "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm",
         "RightHand", "LeftLeg", "LeftShin", "LeftFoot", "RightLeg", "RightShin", "RightFoot"]
PARENTS = np.array([-1, 0, 1, 2, 3, 4, 5, 6, 7, 4, 9, 10, 11, 4, 13, 14, 15, 1, 17, 18, 1, 20, 21])
OFFSETS = np.array([[0, 0, 0], [0, 1.0, 0], [0, 0.1, 0], [0, 0.1, 0], [0, 0.15, 0], [0, 0.15, 0], [0, 0.05, 0],
                    [0, 0.05, 0], [0, 0.2, 0], [0.05, 0.1, 0], [0.12, 0, 0], [0, -0.3, 0], [0, -0.25, 0],
                    [-0.05, 0.1, 0], [-0.12, 0, 0], [0, -0.3, 0], [0, -0.25, 0], [0.1, 0, 0], [0, -0.45, 0],
                    [0, -0.45, 0], [-0.1, 0, 0], [0, -0.45, 0], [0, -0.45, 0]], dtype=float)
FRAMES = 12


def toy(arms_out, head_back, feet_out, bind_head=0.0):
    """The toy clip against its parents, its bind and its gaze at rest (level, under the bind's head turned
    `bind_head` degrees about x): each upper arm `arms_out` degrees out (a degree of sway over the clip), the
    head `head_back` degrees back off its bind's turn, each thigh turned out so the ankles stand `feet_out` m further
    from the hips."""
    local = np.tile(np.eye(4), (FRAMES, len(NAMES), 1, 1))
    local[:, :, :3, 3] = OFFSETS
    bind = local[:1].copy()
    bind[0, NAMES.index("Head"), :3, :3] = Rotation.from_euler("x", bind_head, degrees=True).as_matrix()
    sway = np.linspace(-1.0, 1.0, FRAMES)
    for name, sign in (("LeftArm", 1.0), ("RightArm", -1.0)):
        local[:, NAMES.index(name), :3, :3] = Rotation.from_euler("z", sign * (arms_out + sway)[:, None], degrees=True).as_matrix()
    for name, sign in (("LeftLeg", 1.0), ("RightLeg", -1.0)):
        local[:, NAMES.index(name), :3, :3] = Rotation.from_euler(
            "z", sign * np.degrees(np.arcsin(feet_out / 0.9)), degrees=True).as_matrix()
    local[:, NAMES.index("Head"), :3, :3] = Rotation.from_euler("x", bind_head - head_back, degrees=True).as_matrix()
    return local, played.chained(bind, PARENTS)[0], np.array([0.0, 0.0, 1.0])


def blocked_below(degrees):
    """A body beside the arms that lets no upper arm in closer than `degrees` out."""
    def clears(clip, side):
        return posture.arms_out(played.chained(clip, PARENTS), NAMES)[side].min() >= degrees - 1.5
    return clears


def feet_apart(local):
    """The ankles' spacing over the hips' (median over the clip)."""
    world = played.chained(local, PARENTS)
    feet = np.linalg.norm(world[:, NAMES.index("LeftFoot"), :3, 3] - world[:, NAMES.index("RightFoot"), :3, 3], axis=1)
    hips = np.linalg.norm(world[:, NAMES.index("LeftLeg"), :3, 3] - world[:, NAMES.index("RightLeg"), :3, 3], axis=1)
    return float(np.median(feet / hips))


@pytest.mark.parametrize("arms, head, feet, bind_head, clears, played_faults, hang", [
    (20.0, 10.0, 0.1, 0.0, None, {"left", "right", "gaze"}, posture.ARM_HANG_DEGREES),
    (10.0, 8.0, 0.0, 0.0, None, {"gaze"}, posture.ARM_HANG_DEGREES),
    (17.0, 0.0, 0.1, -30.0, None, {"left", "right"}, posture.ARM_HANG_DEGREES),
    (20.0, 4.0, 0.1, 0.0, blocked_below(12.0), {"left", "right"}, 12.0),
    (4.0, -6.0, 0.0, 0.0, None, set(), 4.0),
])
def test_a_relaxed_clip_hangs_its_arms_and_looks_ahead(arms, head, feet, bind_head, clears, played_faults, hang):
    local, bind, gaze = toy(arms, head, feet, bind_head)
    found = posture.faults(posture.measured(local, PARENTS, NAMES, bind, gaze))
    shown = {word for word in ("left", "right", "gaze") if any(word in fault for fault in found)}
    relaxed = posture.relaxed(local, PARENTS, NAMES, bind, gaze, clears or (lambda clip, side: True))
    measures = posture.measured(relaxed, PARENTS, NAMES, bind, gaze)
    medians = [values["median"] for values in measures["arms out degrees"].values()]
    tops = measures["gaze up degrees"]["most"]
    assert (shown, posture.faults(measures)) == (played_faults, [])
    assert np.allclose(medians, hang, atol=0.6), medians
    assert tops == pytest.approx(min(posture.GAZE_TOP_DEGREES, head + 0.0), abs=0.2) if head > 0 else tops <= 0.0
    assert feet_apart(relaxed) <= 1.0 + 1e-6
