"""posture: a clip standing at ease hangs its upper arms near its sides and looks ahead, and the check fails one that
holds its arms out or gazes up. Each row is a toy rig (the clips rig's joint names, straight bones) posed with its
upper arms some degrees out and its head some degrees back, with a gaze at rest some degrees up (the face's), feet
some way apart: measured as played, its faults are the ones it shows; relaxed, its arms hang at ARM_HANG_DEGREES (or
where a body that blocks them lets them, its shoulders brought forward where only that clears them), its highest gaze is GAZE_TOP_DEGREES up, its feet under its hips, and it has
no faults. A welded toy hand (a 3 mm grid slab, fingers fanned, thumb out) is read into its five fingers' joints off
its skin; its thumb out, fingers spread and held straight (or bent back) are each faulted, and laid at rest it has no
fault, every bone its length, the fingertips towards the palm, the thumb's tip on the palm's side and the palm where it
was. A toy's hands hooked to the little finger's side or bent back fault their wrists; a toy walk whose arms swing
with their own legs, whose arms hardly swing and feet land flat, or whose knees hardly bend faults its walk, a good one
none; a toy standing whose elbows and wrists sit too high for its height faults its reach.

Breaks that turn it red (each applied once, seen red, reverted), 2026-11-25:
- faults' `values["median"] > ARM_MOST_DEGREES` made `> 90`: an arm held 20 degrees out passes.
- faults' gaze check dropped: a head tipped 10 degrees back passes.
- arms_out's `sign *` dropped: the right arm, out to its own side, reads as turned in and is never brought in.
- relaxed's head turn made `-excess / 2.0`: the head is tipped further back, not levelled.
- gaze_up's `@ bind[head].T` dropped: a head whose bind is turned reads its bind's turn as the gaze's.
- relaxed's `stance.narrowed` dropped: the feet stay twice the hips apart.
- hung's `clears` ignored (the first angle taken): the arm is put through the body that blocks it.
Each seen red 2026-11-26:
- hand_faults' thumb gap read at 1 m, its spread at 90 degrees: the thumb out, the fanned fingers pass.
- finger_bend's sign dropped: the fingers bent back read as bent and pass.
- the fingers' bend line turned (`np.cross(palm, first)`): laid at rest, the fingers bend back.
- fingers_of parting a branch only where three meet (`len(big) > 2`): the hand parts into the wrong fingers.
- the thumb laid 5 cm to the back of the hand: its tip off the palm's side.
- wrist_faults' turn read at 90 degrees, its bend check dropped: the hooked and bent-back hands pass.
- walk_faults' arm-with-leg read at 1, its knee check dropped: those walks pass.
- walk_measured's heel read off the foot's lowest pitch (its push off) instead of its flat stance: the flat feet pass.
- reach_faults reading every joint at half the height: the short toy passes.
- the bones' blend read over 1 m: the palm moves with the fingers.
- the four fingers left in their skin's order: the index told from the little finger wrongly.
- hung's SHOULDER_STEPS left at (0,): the arms a chest blocks unless the shoulders come forward stay out.
"""
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation

from tools.characters import played, posture

NAMES = ["Root", "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd",
         "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm",
         "RightHand", "LeftLeg", "LeftShin", "LeftFoot", "RightLeg", "RightShin", "RightFoot", "LeftToeBase",
         "RightToeBase"]
PARENTS = np.array([-1, 0, 1, 2, 3, 4, 5, 6, 7, 4, 9, 10, 11, 4, 13, 14, 15, 1, 17, 18, 1, 20, 21, 19, 22])
OFFSETS = np.array([[0, 0, 0], [0, 1.0, 0], [0, 0.1, 0], [0, 0.1, 0], [0, 0.15, 0], [0, 0.15, 0], [0, 0.05, 0],
                    [0, 0.05, 0], [0, 0.2, 0], [0.05, 0.1, 0], [0.12, 0, 0], [0, -0.3, 0], [0, -0.25, 0],
                    [-0.05, 0.1, 0], [-0.12, 0, 0], [0, -0.3, 0], [0, -0.25, 0], [0.1, 0, 0], [0, -0.45, 0],
                    [0, -0.45, 0], [-0.1, 0, 0], [0, -0.45, 0], [0, -0.45, 0], [0, -0.06, 0.13],
                    [0, -0.06, 0.13]], dtype=float)
FRAMES = 12
TOE_OFF_DEGREES = 40.0  # a toy walk's foot tipped toes down as it pushes off


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


def shoulders_forward(degrees):
    """A chest that lets the arms in only with each shoulder brought at least `degrees` forward."""
    def clears(clip, side):
        world = played.chained(clip, PARENTS)
        bone = world[:, NAMES.index(f"{side}Arm"), :3, 3] - world[:, NAMES.index(f"{side}Shoulder"), :3, 3]
        return bool(np.degrees(np.arcsin(bone[:, 2] / np.linalg.norm(bone, axis=1))).min() >= degrees - 0.1)
    return clears


def feet_apart(local):
    """The ankles' spacing over the hips' (median over the clip)."""
    world = played.chained(local, PARENTS)
    feet = np.linalg.norm(world[:, NAMES.index("LeftFoot"), :3, 3] - world[:, NAMES.index("RightFoot"), :3, 3], axis=1)
    hips = np.linalg.norm(world[:, NAMES.index("LeftLeg"), :3, 3] - world[:, NAMES.index("RightLeg"), :3, 3], axis=1)
    return float(np.median(feet / hips))


def turned_about_x(local, name, degrees):
    """`local` with the joint `name` turned `degrees` about x (one angle, or one a frame) against its parent."""
    angles = np.broadcast_to(np.asarray(degrees, float), (len(local),))[:, None]
    local[:, NAMES.index(name), :3, :3] = Rotation.from_euler("x", angles, degrees=True).as_matrix()
    return local


def toy_walk(arm_with_leg=-0.7, foot_lift=20.0, knee=60.0):
    """A toy walk of two strides (each thigh swinging 25 degrees, its knee bending to `knee` in the swing, its foot
    kept level but tipped `foot_lift` degrees toes up as it lands and TOE_OFF_DEGREES toes down as it pushes off,
    each upper arm swinging `arm_with_leg` times its
    own thigh)."""
    local = np.tile(np.eye(4), (FRAMES * 4, len(NAMES), 1, 1))
    local[:, :, :3, 3] = OFFSETS
    phase = np.linspace(0.0, 4.0 * np.pi, FRAMES * 4, endpoint=False)
    for name, shift in (("Left", 0.0), ("Right", np.pi)):
        thigh = -25.0 * np.sin(phase + shift)  # about x, negative forward
        shin = knee * np.clip(np.sin(phase + shift - np.pi / 2), 0.0, None)
        lift = foot_lift * np.clip(np.sin(phase + shift + np.pi / 4), 0.0, None) ** 4 - \
            TOE_OFF_DEGREES * np.clip(np.sin(phase + shift - 3.0 * np.pi / 4), 0.0, None) ** 4
        turned_about_x(local, f"{name}Leg", thigh)
        turned_about_x(local, f"{name}Shin", shin)
        turned_about_x(local, f"{name}Foot", -(thigh + shin) - lift)  # kept level but for its lift
        turned_about_x(local, f"{name}Arm", arm_with_leg * thigh)
    return local


def toy_hand(spread=12.0, thumb_out=50.0):
    """A left hand's skin as a welded slab 16 mm thick on a 3 mm grid, its back up (+y), fingers along +x, the thumb
    on the +z side (the palm then faces -y), its forearm before x = 0: the fingers fanned `spread` degrees apart, the
    thumb `thumb_out` degrees off the fingers' line. Points, faces, the hand's points (mask), the wrist."""
    step, half = 0.003, 0.008
    bones = [((0.08, 0.0225 - 0.015 * number), np.radians(spread * (1.5 - number)), 0.085, 0.0065)
             for number in range(4)]
    bones.append(((0.035, 0.035), np.radians(thumb_out), 0.06, 0.008))
    xs, zs = np.arange(-0.06, 0.2, step), np.arange(-0.1, 0.14, step)
    grid_x, grid_z = np.meshgrid(xs + step / 2, zs + step / 2, indexing="ij")
    inside = ((grid_x < 0.0) & (np.abs(grid_z) < 0.025)) | ((grid_x >= 0.0) & (grid_x < 0.085) & (np.abs(grid_z) < 0.035))
    for (start_x, start_z), angle, length, radius in bones:
        along = (grid_x - start_x) * np.cos(angle) + (grid_z - start_z) * np.sin(angle)
        across = -(grid_x - start_x) * np.sin(angle) + (grid_z - start_z) * np.cos(angle)
        inside |= (along > -0.01) & (along < length) & (np.abs(across) < radius)
    corner = lambda row, column, top: (row * len(zs) + column) * 2 + top  # noqa: E731 (a one-line lookup)
    faces = []
    for row, column in zip(*np.nonzero(inside)):
        a, b, c, d = [(row, column), (row + 1, column), (row + 1, column + 1), (row, column + 1)]
        faces += [[corner(*a, 1), corner(*b, 1), corner(*c, 1)], [corner(*a, 1), corner(*c, 1), corner(*d, 1)],
                  [corner(*a, 0), corner(*c, 0), corner(*b, 0)], [corner(*a, 0), corner(*d, 0), corner(*c, 0)]]
        for (one, two), (next_row, next_column) in (((a, b), (row, column - 1)), ((b, c), (row + 1, column)),
                                                     ((c, d), (row, column + 1)), ((d, a), (row - 1, column))):
            if not inside[next_row, next_column]:
                faces += [[corner(*one, 0), corner(*one, 1), corner(*two, 1)],
                          [corner(*one, 0), corner(*two, 1), corner(*two, 0)]]
    rows, columns = np.meshgrid(np.arange(len(xs) + 1), np.arange(len(zs) + 1), indexing="ij")
    points = np.zeros((len(xs) * len(zs) * 2 + 2 * len(zs) + 2 * len(xs) + 2, 3))
    for top in (0, 1):
        index = corner(rows.ravel(), columns.ravel(), top)
        keep = index < len(points)
        points[index[keep]] = np.stack([rows.ravel() * step - 0.06, np.full(rows.size, top * 2 * half - half),
                                        columns.ravel() * step - 0.1], axis=1)[keep]
    mesh = trimesh.Trimesh(points, np.array(faces), process=False)
    mesh.remove_unreferenced_vertices()
    points = np.asarray(mesh.vertices)
    return points, np.asarray(mesh.faces), points[:, 0] >= 0.0, np.zeros(3)


def toy_hanging_hands(local):
    """Each toy hand's joints at the toy's bind, hanging (the wrist-to-knuckles line down, the thumb forward): the
    hand joint and its four knuckles."""
    world = played.chained(local[:1], PARENTS)[0]
    hands = {}
    for side, _ in posture.SIDES:
        wrist = world[NAMES.index(f"{side}Hand"), :3, 3]
        hands[f"{side}Hand"] = wrist
        for number, finger in enumerate(posture.FINGERS):
            hands[f"{side}Hand{finger}2"] = wrist + [0.0, -0.09, 0.03 - 0.02 * number]
    return hands


KINDS = {"thumb's tip stands": "thumb", "are spread": "spread", "held straight": "straight", "wrist is turned": "turned",
         "wrist is bent": "bent", "with its own leg": "swings with", "degrees (from": "swings", "lands": "heel",
         "knee bends": "knee", "joint stands": "joint stands"}


def shown_of(found):
    """The kinds of fault named (KINDS: a phrase of the fault's sentence, its kind)."""
    return {kind for phrase, kind in KINDS.items() for fault in found if phrase in fault and
            (phrase != "degrees (from" or " arm swings " in fault)}


@pytest.mark.parametrize("case, arms, head, feet, bind_head, clears, played_faults, hang", [
    ("arms", 20.0, 10.0, 0.1, 0.0, None, {"left", "right", "gaze"}, posture.ARM_HANG_DEGREES),
    ("arms", 10.0, 8.0, 0.0, 0.0, None, {"gaze"}, posture.ARM_HANG_DEGREES),
    ("arms", 17.0, 0.0, 0.1, -30.0, None, {"left", "right"}, posture.ARM_HANG_DEGREES),
    ("arms", 20.0, 4.0, 0.1, 0.0, blocked_below(12.0), {"left", "right"}, 12.0),
    ("arms", 4.0, -6.0, 0.0, 0.0, None, set(), 4.0),
    ("arms", 20.0, 0.0, 0.0, 0.0, shoulders_forward(3.0), {"left", "right"}, posture.ARM_HANG_DEGREES),
    ("hand", 12.0, 50.0, None, None, None, {"thumb", "spread", "straight"}, None),
    ("hand", 0.0, 45.0, None, None, None, {"thumb", "straight"}, None),
    ("hand bent back", 0.0, 45.0, None, None, None, {"thumb", "straight"}, None),
    ("wrist", 25.0, 0.0, None, None, None, {"turned"}, None),
    ("wrist", 0.0, -40.0, None, None, None, {"bent"}, None),
    ("wrist", 5.0, 10.0, None, None, None, set(), None),
    ("walk", -0.7, 20.0, 60.0, None, None, set(), None),
    ("walk", 0.7, 20.0, 60.0, None, None, {"swings with"}, None),
    ("walk", -0.2, 0.0, 60.0, None, None, {"swings", "heel"}, None),
    ("walk", -0.7, 20.0, 20.0, None, None, {"knee"}, None),
    ("reach", 1.8, None, None, None, None, set(), None),
    ("reach", 1.5, None, None, None, None, {"joint stands"}, None),
])
def test_a_relaxed_clip_hangs_its_arms_and_looks_ahead(case, arms, head, feet, bind_head, clears, played_faults,
                                                       hang):
    if case == "arms":
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
    if case.startswith("hand"):  # arms: the fingers' fan, head: the thumb's angle out
        points, faces, mask, wrist = toy_hand(arms, head)
        joints = posture.finger_joints(points, faces, mask, wrist, "Left")
        if case == "hand bent back":
            for finger in posture.FINGERS:
                for joint in (3, 4, "End"):
                    name = f"LeftHand{finger}{joint}"
                    joints[name] = joints[name] + [0.0, 1.2 * (joints[name][0] - 0.08), 0.0]  # up: the back
        assert joints["LeftHandThumbEnd"][2] > joints["LeftHandIndexEnd"][2] - 0.01  # the thumb told from the rest
        assert [joints[f"LeftHand{finger}End"][2] for finger in posture.FINGERS] == sorted(
            [joints[f"LeftHand{finger}End"][2] for finger in posture.FINGERS], reverse=True)
        assert shown_of(posture.hand_faults(posture.hand_measured(joints, "Left"), "Left")) == played_faults
        moved, laid = posture.hand_rested(points[mask], joints, "Left")
        assert posture.hand_faults(posture.hand_measured(laid, "Left"), "Left") == []
        for finger in posture.FINGERS + ("Thumb",):
            chain = posture.finger_chain("Left", finger)
            lengths = [np.linalg.norm(joints[two] - joints[one]) for one, two in zip(chain, chain[1:])]
            assert [np.linalg.norm(laid[two] - laid[one]) for one, two in zip(chain, chain[1:])] == \
                pytest.approx(lengths, abs=1e-9)
        tips = points[mask][:, 0] > 0.15
        assert moved[tips, 1].mean() < points[mask][tips, 1].mean() - 0.02  # the fingertips towards the palm (-y)
        palm = (points[mask][:, 0] > 0.03) & (points[mask][:, 0] < 0.06) & (np.abs(points[mask][:, 2] + 0.008) < 0.008)
        assert np.abs(moved[palm] - points[mask][palm]).max() < 1e-3
        assert laid["LeftHandThumbEnd"][1] < laid["LeftHandIndex2"][1]  # the thumb's tip on the palm's side
    if case == "wrist":  # arms: the hand's turn to the little finger's side, head: its bend back
        local, bind, _ = toy(0.0, 0.0, 0.0)
        hands = toy_hanging_hands(local)
        local[:, [NAMES.index("LeftHand"), NAMES.index("RightHand")], :3, :3] = Rotation.from_euler(
            "xz", [arms, head * 1.0], degrees=True).as_matrix() @ np.diag([1.0, 1.0, 1.0])
        local[:, NAMES.index("RightHand"), :3, :3] = Rotation.from_euler("xz", [arms, -head], degrees=True).as_matrix()
        world = played.chained(local, PARENTS)
        assert shown_of(posture.wrist_faults(world, NAMES, bind, hands)) == played_faults
    if case == "walk":  # arms: the arm's swing with its leg, head: the heel's lift, feet: the knee's swing
        world = played.chained(toy_walk(arms, head, feet), PARENTS)
        assert shown_of(posture.walk_faults(posture.walk_measured(world, NAMES))) == played_faults
        assert posture.reach_faults(world[:1], NAMES, 1.8) == []
    if case == "reach":  # arms: the person's height
        local, _, _ = toy(5.0, 0.0, 0.0)
        assert shown_of(posture.reach_faults(played.chained(local, PARENTS), NAMES, arms)) == played_faults
