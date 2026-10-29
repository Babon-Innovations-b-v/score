"""MyoFullBody fitted to the clip's SOMA body (#70: SOMA is the truth), one solver: the person's constants (the size
factors, an overall one and each size group's, and where each landmark's marker sits on its bone) and every frame's
joint angles, against one cost of the bone groups' turns (the main term: each SOMA segment's world turn on its group's
calibration site, OpenSense's orientation tracking with the static table, never a fitted offset) and the landmarks'
markers (SCORE's landmark set on the clip's own skin, each weighed by its trust, and SOMA's rig joint at each bone
group's start, `group_ends`), weighed as OpenSim's IK weighs its goals; SOMA's joints are also the measure
(`following`), within the joints' ranges and with the model's couplings held.

- `targets`: the clip's targets in MuJoCo's frame: each group's segment turn, each solver landmark skinned.
- `constants`: on SAMPLE frames spread over the clip, staged (Cotton et al. 2026, arXiv:2608.29928, the idea
  only): the whole body placed and posed by mink at the landmark sizing's sizes (`_frames`), then the poses with the
  size factors, then the poses with the markers' moves, each stage scipy's bounded `least_squares` over its
  constants and those frames' angles together, warm from the stage before (`_constants`).
- `angles`: mink on every frame of the clip, on the person's file written with the found constants.
- `following` and `riding` (`_follow`): the judgement (joint mm, group degrees, at a range limit or not) and where each
  SOMA segment rides its group's frame body.
Nothing here moves, scales or grounds SOMA: the run writes no SOMA pose, and MyoFullBody's root follows the markers on
SOMA's skin."""
import numpy as np

from bone_groups import groups
from calibration import turn
from fit._constants import MARKS, staged
from fit._follow import following, riding
from fit._frames import LM_DAMPING, Frames, NotConverged, solved
from fit._model import Fitting, filed, followers_free
from landmarks import HELD, LANDMARKS, MIDDLE_CENTRES, marker, posed, solver_marks, trust
from landmarks._table import CENTRES
from model import TO_OWN
from sizing import OWN_PLACED, stretches

SAMPLE = 30  # frames the constants are fitted on, spread over the clip (recipe 2026-10-28: the sparse problem did not
# finish in 3 minutes at 150 frames; 30 frames hold the clip's range)
HAND_TOP = "lunate"  # the hand group's frame body: the finger bones under it have no target and are held
# The size groups (#70, 2026-10-29; Cotton et al. 2026's fourteen, the idea only): each bone group's, mirrored, beside
# the overall one: the trunk (pelvis, spine, chest, neck, head and the shoulder girdle), and per side the thigh, shin, foot
# (with its toes), upper arm, forearm and hand.
SIZE_GROUPS = {"Hips": "trunk", "Spine1": "trunk", "Spine2": "trunk", "Chest": "trunk", "Neck1": "trunk",
               "Head": "trunk", "LeftShoulder": "trunk", "RightShoulder": "trunk",
               **{f"{side}{group}": f"{size}_{side[0].lower()}" for side in ("Left", "Right")
                  for group, size in {"Arm": "upper_arm", "ForeArm": "forearm", "Hand": "hand", "Leg": "thigh",
                                      "Shin": "shin", "Foot": "foot", "ToeBase": "foot"}.items()}}

END = "end:"  # a group end's marker's name prefix: MyoFullBody's joint centre there, SOMA's rig joint its target
# A group end's weight among the markers (#70, 2026-10-29: SOMA's rig joints mark where each bone group starts and
# ends): this times the landmarks' mean trust, the same for every end; the landmarks' goal keeps its own sum.
END_WEIGHT = 10.0

METHOD = ("one solver (#70): mink 1.3.0 per frame (the bone groups' turns on the static calibration table and SCORE's "
          "landmark set on the SOMA skin as markers weighed by their trust, as OpenSim's IK weighs its goals; "
          "couplings held, leading joints in range) and scipy's bounded least_squares over the person's constants in "
          "stages (the size factors of 14 mirrored size groups pulled gently to 1, then the markers' moves off their "
          "links), each with the angles of frames spread over all the body's recordings, once per body; then mink on "
          "every frame, the pose alone")
__all__ = ["Fitting", "Frames", "NotConverged", "LM_DAMPING", "solved", "followers_free", "following", "riding",
           "followed", "group_ends", "targets", "fitting", "sampled", "constants", "constants_record", "angles", "SIZE_GROUPS"]


def followed(segments):
    """The bone groups whose turns are targets: every group SOMA has (OpenSense: every segment a sensor, weight 1),
    in `groups()` order. One with no joint of its own (the thorax, neck and head, rigid on lumbar1) or whose joints
    follow another's (the lumbar levels above L5, the shoulder girdle on the arm's elevation) is met as near as the
    joints that lead it allow (`LACKS`); leaving them out was measured worse on the Kimodo walker (2026-10-28: joints
    24 mm median against 17 with every group)."""
    return [group for group in groups() if group in segments]


def group_ends(segments):
    """The bone groups' ends that are a SOMA rig joint, in `groups()` order ([(SOMA joint, MyoFullBody centre)]):
    each group's start (every joint between two groups starts one; a chain's tip is no joint), a centre that is the
    middle of two bodies' (one site cannot hold it: the hips' middle, the neck's) left out."""
    return [(soma[0], myo[0]) for soma, myo, _, _ in groups().values()
            if soma[0] in segments and myo[0] in CENTRES and myo[0] not in MIDDLE_CENTRES]


def targets(rig, segments, worlds, held):
    """The clip's targets in MuJoCo's frame: (each frame's turns of the `held` groups, frames x groups x 3 x 3; each
    frame's solver landmarks on the clip's skin, then SOMA's rig joint at each `group_ends`, frames x points x 3)."""
    worlds = np.asarray(worlds, dtype=float)
    turns = np.einsum("ij,fgjk->fgik", TO_OWN.T, worlds[:, [segments.index(group) for group in held], :3, :3])
    joints = worlds[:, [segments.index(soma_end) for soma_end, _ in group_ends(segments)]][..., :3, 3]
    return turns, np.concatenate([posed(rig, segments, worlds), joints], axis=1) @ TO_OWN


def fitting(path, scales, held, segments, moves=None):
    """The fitting model of the person's file at `path` (`Fitting`): a calibration site per `held` group, a marker
    per solver landmark (`landmarks.marker` on its body sized by `scales`, moved by `moves` {landmark: 3}) weighed by
    its trust, then one at each of `segments`' `group_ends` (MyoFullBody's centre, sized, never moved) weighed
    END_WEIGHT times the landmarks' mean trust, the size groups' owners and the fingers held."""
    table, moves = groups(), moves or {}
    frames = [(group, table[group][2], turn(group)) for group in held]
    names = solver_marks()
    marks = [(name, filed(LANDMARKS[name][3]), marker(name, scales[LANDMARKS[name][3]]) + moves.get(name, 0.0))
             for name in names]
    ends = [(f"{END}{centre}", filed(CENTRES[centre][0]), np.asarray(CENTRES[centre][1], dtype=float)
             * scales[CENTRES[centre][0]]) for _, centre in group_ends(segments)]
    trusts = [trust(name) for name in names]
    owners = {filed(body): SIZE_GROUPS[group] for group, (_, _, bodies) in stretches().items() for body in bodies}
    fingers = {body for _, _, frame, bodies in table.values() if frame.startswith(HAND_TOP)
               for body in bodies if body != frame}
    return Fitting(path, frames, marks + ends, owners, {filed(body) for body in OWN_PLACED}, fingers,
                   trusts + [END_WEIGHT * float(np.mean(trusts))] * len(ends), len(marks))


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
    points)]: CONTEXT.md "person constants"), staged on the frames `sampled` picks: mink's angles at the start
    constants (the lengths are SOMA's, from sizing: no size unknowns), then the markers' moves (all but HELD's):
    {"sizes": {bone group: factor, the overall one's times its size group's}, "size factors": {size group: factor}, "marks":
    {landmark: [3] m, its body's frame}, "evaluations": [n, n], "followed": [group]}."""
    turns, points, path = sampled(fit, recordings)
    sized, sizing = fit.neutral(), 0
    free = [index for index, name in enumerate(fit.marks) if name not in HELD and not name.startswith(END)]
    found, _, marking = staged(fit, path, turns, points, MARKS, sized, free)
    sizes, marks = fit.unpack(found)
    factors = dict(zip(fit.sizes, map(float, fit.factors(sizes))))
    return {"sizes": {group: factors[size] for group, size in SIZE_GROUPS.items() if size in factors},
            "size factors": {size: float(value) for size, value in zip(fit.sizes, sizes)},
            "marks": {name: move.tolist() for name, move in zip(fit.marks, marks) if not name.startswith(END)},
            "evaluations": [sizing, marking],
            "followed": list(fit.groups)}


def angles(fit, turns, points):
    """Every frame's joint angles on `fit` (frames x nq of its model; MuJoCo's own compile): the pose alone, the
    person's constants laid on `fit` held fixed."""
    return Frames(fit).fitted(turns, points)


def constants_record(found):
    """The constants as the model record keeps them: each size group's factor (the overall one's alone, the others
    before it is applied), the markers' moves (mm: median and largest), each stage's evaluations and the groups followed."""
    moves = [float(np.linalg.norm(move)) * 1000 for move in found["marks"].values()]
    return {"size factor": {size: round(factor, 4) for size, factor in found["size factors"].items()},
            "markers moved mm": [round(float(np.median(moves)), 1), round(max(moves), 1)] if moves else [],
            "evaluations": found["evaluations"], "followed": found["followed"]}
