"""The toes bent as SOMA's rise (`toes_bent`, on the path after its low-pass).

MyoFullBody's toes are a leaf body on one hinge (the metatarsophalangeal joint) whose axis stands about 35 degrees off
the foot's across, as a person's toe break does; SOMA's toes bend about the across. The fit follows each segment's
turn, and the turn of a hinge nearest a bend about another axis is the bend times the cosine between them: the toes
bent about cos^2 (0.66) of SOMA's bend, and the 6 Hz low-pass took 3 to 4 degrees more off a toe-off's quick bend, so
at toe-off camp's walker's trailing toes' skin stood 4 to 6.4 mm under the floor SOMA's stood on (2026-11-14,
`on floor`'s 3 mm). The toes' tip rises as the sine of a hinge's turn times that cosine, so the hinge is set on every
frame to the turn that raises it as SOMA's bend raises SOMA's (`elevated`), from the hinge's angle at SOMA's rest
(`rest_angle`), low-passed as the path is (`solvers.smoothed`: unfiltered, the toes shook the walker past its
clip's jerk, 2.17 against 2.13), within its range. The toes carry no other body, so nothing else moves."""
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from model import TO_OWN
from solvers import smoothed


def somas_bends(rig, segments, worlds, foot, toe):
    """SOMA's toes' bend against its foot from their bind on each frame (radians, signed along the bends' main axis)
    and that axis in the foot's frame."""
    names = [str(name) for name in rig["names"]]
    binds = np.asarray(rig["bind"], dtype=float)
    worlds = np.asarray(worlds, dtype=float)
    at_bind = np.linalg.inv(binds[names.index(foot)]) @ binds[names.index(toe)]
    relative = np.linalg.inv(worlds[:, segments.index(foot)]) @ worlds[:, segments.index(toe)] @ np.linalg.inv(at_bind)
    turns = Rotation.from_matrix(relative[:, :3, :3]).as_rotvec()
    axis = np.linalg.svd(turns, full_matrices=False)[2][0]
    return turns @ axis, axis


def elevated(bends, cosine):
    """The hinge turns (radians) that raise a tip as `bends` about the across raise it, the hinge `cosine` off it."""
    return np.arcsin(np.clip(np.sin(bends) / cosine, -1.0, 1.0))


def rest_angle(angles, bends):
    """The hinge's angle where SOMA's bend is none: the intercept of the angles' least squares line on the bends."""
    return float(np.linalg.lstsq(np.c_[np.ones(len(bends)), bends], angles, rcond=None)[0][0])


def toes_bent(model, path, rig, segments, worlds, sides, rate):
    """`path` (frames x nq of `model`) with each side's toes' hinge (`sides`: (foot segment, toe segment, its body))
    set on every frame to SOMA's bend raised alike (`elevated`): the cosine between the hinge's axis and SOMA's bend
    axis, both in the person's frame, its median over the frames; the turn's sign the fitted angles' own along the
    bend; low-passed at `rate` as the path is; within the hinge's range."""
    found, data = np.array(path, dtype=float), mujoco.MjData(model)
    for foot, toe, body in sides:
        if model.body_jntnum[body] != 1 or model.jnt_type[model.body_jntadr[body]] != mujoco.mjtJoint.mjJNT_HINGE:
            raise ValueError(f"{toe}: its body is not on one hinge")
        joint = model.body_jntadr[body]
        address = model.jnt_qposadr[joint]
        low, high = model.jnt_range[joint] if model.jnt_limited[joint] else (-np.pi, np.pi)
        bends, axis = somas_bends(rig, segments, worlds, foot, toe)
        cosines = []
        for qpos, world in zip(found, np.asarray(worlds, dtype=float)):
            data.qpos[:] = qpos
            mujoco.mj_kinematics(model, data)
            hinge = TO_OWN @ data.xaxis[joint]
            cosines.append(abs(hinge @ (world[segments.index(foot), :3, :3] @ axis)))
        cosine = float(np.median(cosines))
        angles = found[:, address]
        sign = np.sign(np.polyfit(bends, angles, 1)[0]) or 1.0
        found[:, address] = np.clip(smoothed(rest_angle(angles, bends) + sign * elevated(bends, cosine), rate), low,
                                    high)
    return found
