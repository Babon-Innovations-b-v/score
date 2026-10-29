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
