"""A clip played on a person's build, the people route's one definition (numpy only, #70): the clip's rotations and its
travel (`TRAVELLING_JOINT`, scaled by the built hips' height over the rig's) on the build's bones (`offsets`: each
joint's place in its parent), every clip lifted so the standing clip's first frame puts the feet joints (`FEET`) where
the build's bind does (`floor_lift`). The clips rig's own offsets are never played: people-clips-made's clips are posed
on SOMA's zero-identity body, 7 cm shorter than the template its bind and surface are (#70, 2026-10-29).

The people build (`../maker/prop_build.py`) holds its own copy of `fk`, `clip_world` and `floor_lift`, the same
arithmetic: changing its bytes re-makes every people-body row on a rented card, so it moves onto this module at its next
paid re-make (the owner's call). The sim body (`score/stages/sim_body` `person_rig`) plays its clips through it."""
import numpy as np

TRAVELLING_JOINT = 1  # the Hips, whose translation is the clip's own travel (prop_build.py's)
FEET = ("LeftFoot", "RightFoot")


def laid(local, offsets, parents):
    """`local` (frames x joints x 4 x 4, against the parents) with every joint's translation the build's offset but the
    root's and the travelling joint's."""
    moved = np.array(local, dtype=float)
    for joint in range(moved.shape[1]):
        if joint != TRAVELLING_JOINT and parents[joint] >= 0:
            moved[:, joint, :3, 3] = offsets[joint]
    return moved


def chained(local, parents):
    """World transforms (frames x joints x 4 x 4) of transforms against the parents, chained down the tree."""
    world = np.zeros_like(local)
    for joint in range(local.shape[1]):
        world[:, joint] = local[:, joint] if parents[joint] < 0 else world[:, parents[joint]] @ local[:, joint]
    return world


def fk(local, offsets, parents):
    """World transforms (frames, joints, 4, 4) from rotations against the parents (`local`, whose translations are
    used only for the travelling joint) and the fitted offsets."""
    return chained(laid(local, offsets, parents), parents)


def clip_local(mean_rig, name, offsets, parents, scale, lift):
    """One clip on the fitted bones against its parents: its travel scaled, lifted by `lift`."""
    local = laid(mean_rig[f"clip_{name}"], offsets, parents)
    local[:, TRAVELLING_JOINT, :3, 3] *= scale
    local[:, TRAVELLING_JOINT, 1, 3] += lift
    return local


def clip_world(mean_rig, name, offsets, parents, scale, lift):
    """One clip's world transforms on the fitted bones: its travel scaled, lifted by `lift`."""
    return chained(clip_local(mean_rig, name, offsets, parents, scale, lift), parents)


def floor_lift(mean_rig, fit_rig, names, scale):
    """How far the clips are raised so the standing clip's first frame puts the feet joints where the bind does (the
    FEET the rig has: prop_build.py's copy asks for both)."""
    world = clip_world(mean_rig, "standing", fit_rig["offsets"], fit_rig["parents"], scale, 0.0)
    feet = [names.index(name) for name in FEET if name in names]
    return float(np.asarray(fit_rig["bind"])[feet, 1, 3].min() - world[0, feet, 1, 3].min())


# Kimodo's own foot correction (#70, 2026-11-06): its post-processing, MotionCorrection's `correct_motion` (Kimodo's
# kimodo/postprocess.py post_process_motion calls it on its somaskel30), run on the person's own bones, so a longer
# leg meets the floor where its own foot is. Kimodo's skeleton, as kimodo/skeleton/definitions.py SOMASkeleton30
# `bone_order_names_with_parents` gives it (the test reads that file); the joints of it a SCORE rig has no part of
# (`KIMODO_ONLY`: the jaw, eyes and hand end sites, none on a foot's chain) are left out of the correction's rig.
KIMODO_SKELETON = (
    ("Hips", None), ("Spine1", "Hips"), ("Spine2", "Spine1"), ("Chest", "Spine2"), ("Neck1", "Chest"),
    ("Neck2", "Neck1"), ("Head", "Neck2"), ("Jaw", "Head"), ("LeftEye", "Head"), ("RightEye", "Head"),
    ("LeftShoulder", "Chest"), ("LeftArm", "LeftShoulder"), ("LeftForeArm", "LeftArm"), ("LeftHand", "LeftForeArm"),
    ("LeftHandThumbEnd", "LeftHand"), ("LeftHandMiddleEnd", "LeftHand"), ("RightShoulder", "Chest"),
    ("RightArm", "RightShoulder"), ("RightForeArm", "RightArm"), ("RightHand", "RightForeArm"),
    ("RightHandThumbEnd", "RightHand"), ("RightHandMiddleEnd", "RightHand"), ("LeftLeg", "Hips"),
    ("LeftShin", "LeftLeg"), ("LeftFoot", "LeftShin"), ("LeftToeBase", "LeftFoot"), ("RightLeg", "Hips"),
    ("RightShin", "RightLeg"), ("RightFoot", "RightShin"), ("RightToeBase", "RightFoot"))
KIMODO_ONLY = ("Jaw", "LeftEye", "RightEye", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightHandThumbEnd",
               "RightHandMiddleEnd")
# Kimodo's foot_contacts channels in its saved clips (somaskel77's six: left heel, toe, toe end, right heel, toe, toe
# end; postprocess.py output_to_SOMASkeleton77) or its model's own four, to the correction's four (left heel, left
# toe, right heel, right toe).
CONTACT_CHANNELS = {6: (0, 1, 3, 4), 4: (0, 1, 2, 3)}
# post_process_motion's own settings (kimodo/postprocess.py defaults).
CONTACT_THRESHOLD = 0.5
ROOT_MARGIN = 0.04
# Kimodo's skeleton ends at the toe base and its toe pin turns the foot alone, so a foot pitched onto its toes carries
# its toes down with it; `toward_flat` bends a toe back toward lying flat (the sim body's `toes_lifted` uses it).
TOES = (("LeftToeBase", "LeftToeEnd"), ("RightToeBase", "RightToeEnd"))


def kimodo_joints(names, parents):
    """Each joint of Kimodo's skeleton but KIMODO_ONLY, in its order: (its index in the rig `names`, its parent's place
    in that list, -1 for the Hips); refused when the rig lacks one or its parent is not Kimodo's."""
    kept = [(name, parent) for name, parent in KIMODO_SKELETON if name not in KIMODO_ONLY]
    order = [name for name, _ in kept]
    joints = []
    for name, parent in kept:
        if name not in names:
            raise ValueError(f"the rig has no {name}, a joint of Kimodo's skeleton on its correction")
        own = names.index(name)
        theirs = None if parents[own] < 0 or names[parents[own]] == "Root" else names[parents[own]]
        if theirs != parent:
            raise ValueError(f"the rig's {name} hangs from {theirs}, Kimodo's from {parent}")
        joints.append((own, -1 if parent is None else order.index(parent)))
    return joints


def foot_contacts(contacts):
    """Kimodo's foot_contacts (frames x 6 or 4) as the correction's four channels, float32."""
    contacts = np.asarray(contacts, dtype=np.float32)
    if contacts.ndim != 2 or contacts.shape[1] not in CONTACT_CHANNELS:
        raise ValueError(f"foot contacts of shape {contacts.shape}: Kimodo's are frames x 6 or frames x 4")
    return np.ascontiguousarray(contacts[:, list(CONTACT_CHANNELS[contacts.shape[1]])])


def to_kimodo(local, bind, joints, parents):
    """`local` (the clip against its parents on the build) as Kimodo's motion on the build's bones: (each kept joint's
    turn against its Kimodo parent, frames x joints x 3 x 3, off a rest whose turns are all none; the Hips' place,
    frames x 3; the rest's joint places, joints x 3: the Hips at the bind's, every other its parent's place plus its
    played offset turned by its parent's bind)."""
    world = chained(np.asarray(local, dtype=float), parents)
    turns = world[:, [own for own, _ in joints], :3, :3] @ np.swapaxes(np.asarray(bind)[[own for own, _ in joints],
                                                                                      :3, :3], 1, 2)
    kimodo = np.array(turns)
    rest = np.zeros((len(joints), 3))
    for place, (own, parent) in enumerate(joints):
        if parent < 0:
            rest[place] = np.asarray(bind)[own, :3, 3]
            continue
        kimodo[:, place] = np.swapaxes(turns[:, parent], 1, 2) @ turns[:, place]
        rest[place] = rest[parent] + np.asarray(bind)[parents[own], :3, :3] @ np.asarray(local)[0, own, :3, 3]
    return kimodo, world[:, joints[0][0], :3, 3], rest


def from_kimodo(local, bind, joints, parents, kimodo, hips):
    """`local` with every kept joint's rotation, and the Hips' place, Kimodo's corrected motion's (to_kimodo's
    inverse); the joints Kimodo's skeleton lacks keep theirs against their parents."""
    moved = np.array(local, dtype=float)
    world = chained(moved, parents)
    turns = np.array(kimodo)
    for place, (own, parent) in enumerate(joints):
        if parent >= 0:
            turns[:, place] = turns[:, parent] @ kimodo[:, place]
    for place, (own, _) in enumerate(joints):
        world[:, own, :3, :3] = turns[:, place] @ np.asarray(bind)[own, :3, :3]
    world[:, joints[0][0], :3, 3] = hips
    for own, _ in joints:
        above = world[:, parents[own]] if parents[own] >= 0 else np.eye(4)
        moved[:, own, :3, :3] = np.swapaxes(above[..., :3, :3], -1, -2) @ world[:, own, :3, :3]
        if own == joints[0][0]:
            moved[:, own, :3, 3] = np.einsum("...ba,...b->...a", above[..., :3, :3], hips - above[..., :3, 3])
    return moved


def toward_flat(local, names, parents, bind, toe, share):
    """`local` with the toe `toe` (its base and end joints, as TOES gives them) bent on every frame `share` (0 to 1,
    one or one a frame) of the least way from its turn to flat: flat its turn the bind's, turned only about the upright
    as the clip turns it (the twist about the upright of its turn from the bind), so its sole lies as the bind's
    does."""
    moved = np.array(local, dtype=float)
    bind = np.asarray(bind)
    base, end = (names.index(name) for name in toe)
    if parents[end] != base:
        raise ValueError(f"the rig's {names[end]} hangs from {names[parents[end]]}, not from {names[base]}")
    world = chained(moved, parents)
    own = world[:, base, :3, :3]
    turn = own @ bind[base, :3, :3].T
    angle = np.arctan2(turn[:, 0, 2] - turn[:, 2, 0], turn[:, 0, 0] + turn[:, 2, 2])
    flat = turned_about(np.tile([0.0, 1.0, 0.0], (len(moved), 1)), angle) @ bind[base, :3, :3]
    axis, whole = turn_vector(flat @ np.swapaxes(own, 1, 2))
    bent = turned_about(axis, np.broadcast_to(np.asarray(share, dtype=float), whole.shape) * whole) @ own
    moved[:, base, :3, :3] = np.swapaxes(world[:, parents[base], :3, :3], 1, 2) @ bent
    return moved


def turned_about(axes, angles):
    """Turns (n x 3 x 3) of `angles` (n, radians) about the unit `axes` (n x 3)."""
    axes = np.asarray(axes, dtype=float)
    cross = np.zeros((len(axes), 3, 3))
    cross[:, 0, 1], cross[:, 0, 2], cross[:, 1, 2] = -axes[:, 2], axes[:, 1], -axes[:, 0]
    cross -= np.swapaxes(cross, 1, 2)
    sine, cosine = np.sin(angles)[:, None, None], np.cos(angles)[:, None, None]
    return np.eye(3) + sine * cross + (1.0 - cosine) * cross @ cross


def turn_vector(turns):
    """Each turn's (n x 3 x 3) unit axis (n x 3; any, for no turn) and angle (n, radians, 0 to pi)."""
    cosine = np.clip((np.trace(turns, axis1=1, axis2=2) - 1.0) / 2.0, -1.0, 1.0)
    angle = np.arccos(cosine)
    skew = np.stack([turns[:, 2, 1] - turns[:, 1, 2], turns[:, 0, 2] - turns[:, 2, 0], turns[:, 1, 0] - turns[:, 0, 1]],
                    axis=1)
    length = np.linalg.norm(skew, axis=1)
    axis = np.where(length[:, None] > 1e-12, skew / np.maximum(length, 1e-12)[:, None], [1.0, 0.0, 0.0])
    return axis, angle


def contacted(local, names, parents, bind, contacts):
    """`local` (a clip against its parents on a build, its feet stood) with Kimodo's own foot correction run on the
    build's bones (MotionCorrection's correct_motion, as post_process_motion calls it, no constraints): on Kimodo's
    contact frames each foot's ankle held from sinking under, and its toe put at, its height at the build's bind, the
    feet held from skating; `contacts` Kimodo's foot_contacts for the clip. The rig's floor is the bind's own, never
    Kimodo's lowest toe plus 2 cm. Needs Kimodo's motion_correction (vendor/kimodo/MotionCorrection, its prebuilt wheel
    installed by `uv sync`), refused by name without it."""
    from scipy.spatial.transform import Rotation

    try:
        import motion_correction  # Kimodo's compiled correction: vendor/kimodo/MotionCorrection
    except ModuleNotFoundError as missing:
        raise RuntimeError("Kimodo's foot correction needs motion_correction, its prebuilt wheel from vendor/kimodo/wheels "
                           "installed by `uv sync` (pyproject's motion-correction)") \
            from missing

    names = [str(name) for name in names]
    contacts = foot_contacts(contacts)
    if len(contacts) != len(local):
        raise ValueError(f"{len(contacts)} frames of foot contacts for a clip of {len(local)}")
    joints = kimodo_joints(names, parents)
    kimodo, hips, rest = to_kimodo(local, bind, joints, parents)
    frames, count = kimodo.shape[:2]
    quats = np.ascontiguousarray(Rotation.from_matrix(kimodo.reshape(-1, 3, 3)).as_quat(scalar_first=True)
                                 .astype(np.float32).ravel())
    root = np.ascontiguousarray(hips.astype(np.float32).ravel())
    none = np.zeros(frames, dtype=np.float32)
    rest_rows = [list(map(float, rest[0]))] + [list(map(float, rest[place] - rest[parent]))
                                               for place, (_, parent) in enumerate(joints) if parent >= 0]
    tags = [names[own] for own, _ in joints]
    motion_correction.correct_motion(
        root, quats, np.zeros(frames * 3, dtype=np.float32), np.tile(np.float32([1, 0, 0, 0]), frames * count),
        none, none, none, none, none, none, np.ascontiguousarray(contacts.ravel()),
        [parent for _, parent in joints], rest_rows, [[0.0, 0.0, 0.0, 1.0]] * count,
        tags.index("LeftHand"), tags.index("RightHand"), tags.index("LeftFoot"), tags.index("RightFoot"),
        CONTACT_THRESHOLD, ROOT_MARGIN, False)
    turned = Rotation.from_quat(quats.reshape(-1, 4).astype(float), scalar_first=True).as_matrix()
    return from_kimodo(local, bind, joints, parents, turned.reshape(frames, count, 3, 3), root.reshape(frames, 3))
