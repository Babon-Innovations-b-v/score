"""MyoFullBody fitted to the clip's SOMA body (#70: SOMA is the truth), one solver: the person's constants (each bone
group's size, the joint centres SOMA places, where each virtual marker sits on its bone) and every frame's joint
angles, against one cost of the bone groups' turns (the main term: each SOMA segment's world turn on its group's
calibration site, OpenSense's orientation tracking with the static table, never a fitted offset), the landmarks'
markers (the SOMA mesh's bony landmarks on the clip's own skin) and SOMA's joints on MyoFullBody's centres (`placed`),
weighed as OpenSim's IK weighs its goals, within the joints' ranges and with the model's couplings held.

- `targets`: the clip's targets in MuJoCo's frame: each group's segment turn, each landmark skinned (`landmarks`).
- `constants`: on SAMPLE frames spread over the clip, mink per frame at the start constants (`_frames`), then scipy's
  bounded `least_squares` over the constants and those frames' angles together, one sparse problem (`_constants`).
- `angles`: mink on every frame of the clip, on the person's file written with the found constants.
- `following` and `riding` (`_follow`): the judgement (joint mm, group degrees, at a range limit or not) and where each
  SOMA segment rides its group's frame body.
Nothing here moves, scales or grounds SOMA: the run writes no SOMA pose, and MyoFullBody's root follows the markers on
SOMA's skin."""
import mujoco
import numpy as np

from bone_groups import groups
from calibration import turn
from fit._constants import constants as fitted_constants
from fit._follow import following, judged, riding
from fit._frames import Frames, NotConverged
from fit._model import Fitting, filed, own_name
from landmarks import MARKS, myo_parts, posed, solver_marks
from landmarks._table import CENTRES
from model import TO_OWN
from sizing import OWN_PLACED, stretches

SAMPLE = 30  # frames the constants are fitted on, spread over the clip (recipe 2026-10-28: the sparse problem did not
# finish in 3 minutes at 150 frames; 30 frames hold the clip's range)
# The joint centres the constants move (each side): the limbs' joints SOMA places.
PLACED_JOINTS = ("hip", "knee", "ankle", "mtp", "sternoclavicular", "glenohumeral", "elbow", "wrist")
HAND_TOP = "lunate"  # the hand group's frame body: the finger bones under it have no target and are held

METHOD = ("one solver (#70): mink 1.3.0 per frame (the bone groups' turns on the static calibration table, the SOMA "
          "skin's landmarks and SOMA's joints as markers, weighed as OpenSim's IK weighs its goals; couplings held, "
          "leading joints in range) and scipy's bounded least_squares over the person's constants (group sizes, "
          "joint centres, marker places; each stretch held to SOMA's length) with the angles of frames spread over "
          "the clip, one sparse problem; then mink on every frame")
__all__ = ["Fitting", "Frames", "NotConverged", "following", "riding", "followed", "placed", "targets", "fitting",
           "constants", "constants_record", "angles"]


def followed(segments):
    """The bone groups whose turns are targets: every group SOMA has (OpenSense: every segment a sensor, weight 1),
    in `groups()` order. One with no joint of its own (the thorax, neck and head, rigid on lumbar1) or whose joints
    follow another's (the lumbar levels above L5, the shoulder girdle on the arm's elevation) is met as near as the
    joints that lead it allow (`LACKS`); leaving them out was measured worse on the Kimodo walker (2026-10-28: joints
    24 mm median against 17 with every group)."""
    return [group for group in groups() if group in segments]


def placed(segments):
    """[(SOMA joint, MyoFullBody centre)] of the judged joints SOMA has whose centre one body holds (all but Neck2's,
    the middle of C7/T1 and C0/C1): SOMA's joints as virtual markers on MyoFullBody's centres."""
    return [(soma, myo) for soma, myo in judged() if soma in segments and len(myo_parts(myo)) == 1]


def targets(rig, segments, worlds, held):
    """The clip's targets in MuJoCo's frame: (each frame's turns of the `held` groups, frames x groups x 3 x 3; each
    frame's places, frames x (solver landmarks, then `placed` joints) x 3)."""
    worlds = np.asarray(worlds, dtype=float)
    turns = np.einsum("ij,fgjk->fgik", TO_OWN.T, worlds[:, [segments.index(group) for group in held], :3, :3])
    joints = worlds[:, [segments.index(soma) for soma, _ in placed(segments)]][..., :3, 3]
    return turns, np.concatenate([posed(rig, segments, worlds), joints], axis=1) @ TO_OWN


def _tops(model, names):
    """Each centre's top body (its chain's first body placed off its parent's origin: a split body's first wrapper,
    the shoulder's phantom), by name in `model`."""
    found = []
    for name in names:
        body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, CENTRES[name][0])
        while not np.any(model.body_pos[body]) and model.body_parentid[body] > 0:
            body = model.body_parentid[body]
        found.append((name, model.body(body).name))
    return found


def fitting(path, scales, segments, held, lengths, moves=None):
    """The fitting model of the person's file at `path` (`Fitting`): a calibration site per `held` group, a marker
    per solver landmark at its start on its bone (sized by `scales`, moved by `moves` {landmark: 3}), a site on each
    `placed` centre, the limbs' joint centres free to move, the fingers held, and each sizing stretch held to SOMA's
    length (`lengths` {group: m}, `sizing.soma_lengths`)."""
    table, moves = groups(), moves or {}
    frames = [(group, table[group][2], turn(group)) for group in held]
    marks = [(name, MARKS[name][3], np.asarray(MARKS[name][5]) * scales[MARKS[name][3]] + moves.get(name, 0.0))
             for name in solver_marks()]
    owners = {filed(body): group for group, (_, _, bodies) in stretches().items() for body in bodies}
    fingers = {body for _, _, frame, bodies in table.values() if frame.startswith(HAND_TOP)
               for body in bodies if body != frame}
    spec_model = mujoco.MjModel.from_xml_path(str(path))
    joints = _tops(spec_model, [f"{joint}_{side}" for joint in PLACED_JOINTS for side in "lr"])
    ends = [[[(filed(body), np.asarray(local) * scales[body], weight) for body, local, weight in myo_parts(name)]
             for name in (start, end)] for _, (start, end), _ in stretches().values()]
    held_lengths = [(start, end, lengths[group]) for group, (start, end) in zip(stretches(), ends)]
    centres = [(soma, filed(myo_parts(myo)[0][0]), np.asarray(myo_parts(myo)[0][1]) * scales[myo_parts(myo)[0][0]])
               for soma, myo in placed(segments)]
    return Fitting(path, frames, marks, owners, {filed(body) for body in OWN_PLACED}, joints, fingers, held_lengths,
                   centres)


def spread(count, most=SAMPLE):
    """Up to `most` frame indices spread evenly over `count` frames, both ends in."""
    return np.unique(np.linspace(0, count - 1, min(count, most)).round().astype(int))


def constants(fit, turns, points):
    """The person's constants on `fit` (a `Fitting`): mink's angles at the start constants on the frames `spread`
    picks, then one sparse least squares over the constants and those frames' angles together:
    {"sizes": {group: factor}, "joints": {top body: [3] m, its parent's frame}, "marks": {landmark: [3] m, its body's
    frame}, "evaluations": n, "followed": [group]}."""
    sample = spread(len(turns))
    path = Frames(fit).fitted(turns[sample], points[sample])
    found, _, evaluations = fitted_constants(fit, path, turns[sample], points[sample], fit.neutral())
    sizes, joints, marks = fit.unpack(found)
    return {"sizes": dict(zip(fit.sizes, map(float, sizes))),
            "joints": {own_name(fit.model.body(body).name): move.tolist()
                       for body, move in zip(fit.joint_bodies, joints)},
            "marks": {name: move.tolist() for name, move in zip(fit.marks, marks)}, "evaluations": evaluations,
            "followed": list(fit.groups)}


def angles(fit, turns, points):
    """Every frame's joint angles on `fit` (frames x nq of its model; MuJoCo's own compile)."""
    return Frames(fit).fitted(turns, points)


def constants_record(found):
    """The constants as the model record keeps them: each group's size factor, each joint centre's move (mm, its
    parent's frame), the markers' moves (mm: median and largest), the solve's evaluations and the groups followed."""
    moves = [float(np.linalg.norm(move)) * 1000 for move in found["marks"].values()]
    return {"size factor": {group: round(factor, 4) for group, factor in found["sizes"].items()},
            "joint centre moved mm": {body: [round(value * 1000, 1) for value in move]
                                      for body, move in found["joints"].items()},
            "markers moved mm": [round(float(np.median(moves)), 1), round(max(moves), 1)] if moves else [],
            "evaluations": found["evaluations"], "followed": found["followed"]}
