"""MyoFullBody fitted to the clip's SOMA body (#70: SOMA is the truth), one solver: the person's constants (where each
landmark's marker sits on its bone and each joint inside a bone group sits in its parent; the lengths are SOMA's, from
the sizing) and every frame's joint angles, against one cost of the bone groups' turns (the main term: each SOMA segment's world turn on its group's
calibration site, OpenSense's orientation tracking with the static table, never a fitted offset) and the landmarks'
markers (SCORE's landmark set on the clip's own skin, each weighed by its trust, and SOMA's rig joint at each bone
group's start, `group_ends`), weighed as OpenSim's IK weighs its goals; SOMA's joints are also the measure
(`following`), within the joints' ranges and with the model's couplings held.

- `targets`: the clip's targets in MuJoCo's frame: each group's segment turn, each solver landmark skinned.
- `constants`: on SAMPLE frames spread over all the body's recordings (Cotton et al. 2026, arXiv:2608.29928, the
  idea only): the whole body placed and posed by mink at the sizing's lengths (`_frames`), then the poses with the
  markers' moves and the joints inside the groups, scipy's bounded `least_squares` over those constants and the
  frames' angles together, warm from mink's (`_constants`).
- `angles`: mink on every frame of the clip, on the person's file written with the found constants.
- `following` and `riding` (`_follow`): the judgement (joint mm, group degrees, at a range limit or not) and where each
  SOMA segment rides its group's frame body.
Nothing here moves, scales or grounds SOMA: the run writes no SOMA pose, and MyoFullBody's root follows the markers on
SOMA's skin."""
import mujoco
import numpy as np

from bone_groups import RIGID, groups
from calibration import turn
from fit._constants import staged
from fit._follow import following, riding
from fit._frames import LM_DAMPING, Frames, NotConverged, solved
from fit._model import Fitting, end_site, filed, followers_free
from landmarks import HELD, LANDMARKS, MIDDLE_CENTRES, marker, myo_parts, posed, soma_joints, solver_marks, trust
from landmarks._table import CENTRES
from model import TO_OWN

SAMPLE = 30  # frames the constants are fitted on, spread over the clip (recipe 2026-10-28: the sparse problem did not
# finish in 3 minutes at 150 frames; 30 frames hold the clip's range)
HAND_TOP = "lunate"  # the hand group's frame body: the finger bones under it have no target and are held

END = "end:"  # a group end's marker's name prefix: MyoFullBody's joint centre there, SOMA's rig joint its target
# A group end's weight among the markers (#70, 2026-10-29: SOMA's rig joints mark where each bone group starts and
# ends): this times the landmarks' mean trust, the same for every end, inside the one markers' goal (`_frames.weights`),
# never on top of it; 1 (a landmark's) unless level 1 finds otherwise, never set by hand to pass a score
END_WEIGHT = 1.0

METHOD = ("one solver (#70): mink 1.3.0 per frame (the bone groups' turns on the static calibration table, SCORE's "
          "landmark set on the SOMA skin as markers weighed by their trust and SOMA's rig joints at the group ends, "
          "as OpenSim's IK weighs its goals; couplings held, leading joints in range) and scipy's bounded "
          "least_squares over the person's constants (the markers' moves off their links and the joints inside the "
          "bone groups; the lengths SOMA's, from the sizing) with the angles of frames spread over all the body's "
          "recordings, once per body; then mink on every frame, the pose alone")
__all__ = ["Fitting", "end_site", "Frames", "NotConverged", "LM_DAMPING", "solved", "followers_free", "following", "riding",
           "followed", "group_ends", "targets", "fitting", "sampled", "constants", "constants_record", "angles"]


def followed(segments):
    """The bone groups whose turns are targets: every group SOMA has (OpenSense: every segment a sensor, weight 1),
    in `groups()` order. One with no joint of its own (the thorax, neck and head, rigid on lumbar1) or whose joints
    follow another's (the lumbar levels above L5, the shoulder girdle on the arm's elevation) is met as near as the
    joints that lead it allow (`LACKS`); leaving them out was measured worse on the Kimodo walker (2026-10-28: joints
    24 mm median against 17 with every group)."""
    return [group for group in groups() if group in segments]


def group_ends(segments):
    """The bone groups' ends that are a SOMA rig joint, in `groups()` order ([(SOMA end, MyoFullBody centre)]): each
    group's start (every joint between two groups starts one; a chain's tip is no joint) whose rig joints `segments`
    hold, one rule for every end: a middle of two (the hips', the neck's) is an end like any other (`soma_joints`,
    `myo_parts`). A group rigid on the one before it (`RIGID`) has no joint at its start, so no end there."""
    return [(soma[0], myo[0]) for group, (soma, myo, _, _) in groups().items()
            if group not in RIGID and all(joint in segments for joint in soma_joints(soma[0]))
            and (myo[0] in CENTRES or myo[0] in MIDDLE_CENTRES)]


def targets(rig, segments, worlds, held):
    """The clip's targets in MuJoCo's frame: (each frame's turns of the `held` groups, frames x groups x 3 x 3; each
    frame's solver landmarks on the clip's skin, then SOMA's rig joint (a middle's two's mean) at each `group_ends`, frames x points x 3)."""
    worlds = np.asarray(worlds, dtype=float)
    turns = np.einsum("ij,fgjk->fgik", TO_OWN.T, worlds[:, [segments.index(group) for group in held], :3, :3])
    joints = np.stack([worlds[:, [segments.index(joint) for joint in soma_joints(soma_end)]][..., :3, 3].mean(axis=1)
                       for soma_end, _ in group_ends(segments)], axis=1)
    return turns, np.concatenate([posed(rig, segments, worlds), joints], axis=1) @ TO_OWN


def fitting(path, scales, held, segments, moves=None):
    """The fitting model of the person's file at `path` (`Fitting`): a calibration site per `held` group, a marker
    per solver landmark (`landmarks.marker` on its body sized by `scales`, moved by `moves` {landmark: 3}) weighed by
    its trust, then one at each of `segments`' `group_ends` (MyoFullBody's centre, sized, never moved; `end_site`) weighed
    END_WEIGHT times the landmarks' mean trust, the fingers held and each group's bodies (its
    joints inside, `Fitting.inside`)."""
    table, moves = groups(), moves or {}
    frames = [(group, table[group][2], turn(group)) for group in held]
    names = solver_marks()
    marks = [(name, filed(LANDMARKS[name][3]), marker(name, scales[LANDMARKS[name][3]]) + moves.get(name, 0.0))
             for name in names]
    model = mujoco.MjModel.from_xml_path(str(path))
    ends = [(f"{END}{centre}", *end_site(model, [(filed(body), np.asarray(local, dtype=float) * scales[body], weight)
                                                  for body, local, weight in myo_parts(centre)]))
            for _, centre in group_ends(segments)]
    trusts = [trust(name) for name in names]
    fingers = {body for _, _, frame, bodies in table.values() if frame.startswith(HAND_TOP)
               for body in bodies if body != frame}
    inside = [{filed(body) for body in bodies} for _, _, _, bodies in table.values()]
    return Fitting(path, frames, marks + ends, fingers, trusts + [END_WEIGHT * float(np.mean(trusts))] * len(ends),
                   inside)


def spread(count, most=SAMPLE):
    """Up to `most` frame indices spread evenly over `count` frames, both ends in."""
    return np.unique(np.linspace(0, count - 1, min(count, most)).round().astype(int))


def sampled(fit, recordings):
    """The frames the constants are fitted on, from every recording of the body ([(turns, points)], each as `targets`
    gives them): SAMPLE spread over them by length, at least two a recording, each recording's posed by mink from its
    own start. Returns (turns, points, path), the recordings' frames end to end."""
    total = sum(len(turns) for turns, _ in recordings)
    picked = [(turns, points, spread(len(turns), max(2, round(SAMPLE * len(turns) / total))))
              for turns, points in recordings]
    turns = np.concatenate([turns[sample] for turns, _, sample in picked])
    points = np.concatenate([points[sample] for _, points, sample in picked])
    path = np.concatenate([Frames(fit).fitted(turns[sample], points[sample]) for turns, points, sample in picked])
    return turns, points, path


def constants(fit, recordings):
    """The person's constants on `fit` (a `Fitting`), once per body from all its `recordings` together ([(turns,
    points)]: CONTEXT.md "person constants"), on the frames `sampled` picks from mink's angles at the start
    constants (the lengths are SOMA's, from sizing: no size unknowns): the markers' moves (all but HELD's) and the
    joints inside the groups (#70's level 2: the vertebrae, shoulder blade, wrist bones and inner foot joints, each
    body's move in its parent, `Fitting.inside`), together:
    {"marks": {landmark: [3] m, its body's frame}, "joints": {body: [3] m, its parent's frame}, "evaluations": n,
    "followed": [group]}."""
    turns, points, path = sampled(fit, recordings)
    free = [index for index, name in enumerate(fit.marks) if name not in HELD and not name.startswith(END)]
    found, _, evaluations = staged(fit, path, turns, points, fit.neutral(), free)
    marks, joints = fit.unpack(found)
    return {"marks": {name: move.tolist() for name, move in zip(fit.marks, marks) if not name.startswith(END)},
            "joints": {name: move.tolist() for name, move in zip(fit.inside_names, joints)},
            "evaluations": evaluations,
            "followed": list(fit.groups)}


def angles(fit, turns, points):
    """Every frame's joint angles on `fit` (frames x nq of its model; MuJoCo's own compile): the pose alone, the
    person's constants laid on `fit` held fixed."""
    return Frames(fit).fitted(turns, points)


def constants_record(found):
    """The constants as the model record keeps them: the markers' moves (mm: median and largest), each inside joint's
    move (mm), the solve's evaluations and the groups followed."""
    moves = [float(np.linalg.norm(move)) * 1000 for move in found["marks"].values()]
    joints = {name: round(float(np.linalg.norm(move)) * 1000, 1) for name, move in found.get("joints", {}).items()}
    return {"inside joints moved mm": joints,
            "markers moved mm": [round(float(np.median(moves)), 1), round(max(moves), 1)] if moves else [],
            "evaluations": found["evaluations"], "followed": found["followed"]}
