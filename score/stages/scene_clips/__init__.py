"""The scene-made clips (experimental, PRD #56; CONTEXT.md "scene-made clip"): row `scene-clips@<place>`, paid, for a
place whose design shows people. Each walker of the place's accepted cast gets a Kimodo clip made from its own walk
through the scene, not a walk on a flat floor played over it.

    make     each cast single whose clip is `walking`: its route (the cast's `path`, else a straight leg from its spot
             the way it faces, cast.py's front -z, for the walking sentence's seconds at its pace) walked at its pace
             (cast.py WALK_PACE) one frame at a time at Kimodo's RATE, and the walk check run along it on the same
             geometry the cast is measured on (its seed's base layer with its scene record, on its made ground:
             cast/measure.py's knee-down ray for the ground under each frame, its body cylinder for what it runs
             into): the route ends where it runs into a solid, finds no ground or would step over KNEE. The route
             becomes Kimodo constraints (constraints_of) in Kimodo's canonical frame (its start at the origin, its
             first heading +Z, its start's ground y = 0; the placement back into the scene recorded):
               root2d      the route's root path and heading at every frame (dense: Kimodo is trained on dense
                           root paths)
               left-foot,  each foot at its stance's middle, every STEP_FRAMES from FIRST_STANCE, right foot first
               right-foot  (the cadence of people-clips-made's own walking clip), fewer than 20 a foot (Kimodo's
                           limit): SOMA77's rest pose turned to the route's heading with its hips HIP_OVER_SOLE over
                           the ground under that foot, so Kimodo's FK puts the sole on the scene's surface there
             Kimodo then makes each clip on one rented characters machine (tools/characters/clips/scene_clips.py
             through tools/cloud/characters.py): `kimodo_gen` with the walking sentence, model and fixed seed of
             people/clips.py and `--constraints`, `--no-postprocess` where the footfalls' ground is not flat (see
             Not held), and SOMA-X's mean rig with every clip (the maker's prop_skeleton.py, as people-clips-made).
             Written as people-clips-made writes: rig.npz (clip_<name>), motions/ (<name>.npz Kimodo's own output,
             <name>.record.json) and make.json, and scene_clips.json (each walker's route, ground, footfalls,
             placement, what was cut or left out).
    gates    made      every planned clip is in the rig and has its motion and record
             path held the clip's root (hips) keeps to its route: mean distance on the ground at most PATH_HELD
             feet held  at each constrained stance the foot's sole (its toe end) is on the ground it was asked for:
                        mean off at most FOOT_HELD

Not held, with evidence (kimodo 1.0.0 as vendored, vendor/kimodo, its CHANGELOG at 2026-05-03): Kimodo has no ground
of its own; its training motion is canonicalised on one floor (docs/source/user_guide/constraints.md, "Y is the
absolute hip height above the ground"), so the scene's relief reaches it only through the foot keyframes. Its
post-processing (MotionCorrection) holds a toe in contact at the rig's own flat-floor height: the one-bone contact
pass sets the toe's target `target.SetY(c.minHeight)` (src/cpp/AnimProcessing/Utility.cpp), minHeight the toe's
height in the default pose stood on y = 0 (src/cpp/BindingsPython.cpp), outside the constrained frames themselves.
On ground that is not flat it would pull a toe on a step back to the start's floor, so those clips are made with
`--no-postprocess` and keep Kimodo's foot skate, which the sim body's contacts on the real ground take up. An
end-effector constraint also pins the hips' height and heading at its frame (constraints.py
EndEffectorConstraintSet.update_constraints), which is why the keyframe is a stance's middle, where Kimodo's own walk
stands within 5 mm of the rest pose's hip height (people-clips-made's walking clip: hips 0.998 to 1.004 m at its
stances' middles, the rest pose 1.005). The CLI takes no first heading (it is 0, +Z), so the route is turned to it.
A walk longer than MOST_SECONDS is cut there (Kimodo makes at most 10 s a prompt, docs key_concepts/limitations.md).

Price: no scene-made clip was ever made; EUROS is a guess kept apart by the runner, from people-clips-made's measured
runs (data/costs/per-unit.json: one L4 at EUR 0.80 an hour, its set-up 14.5 min at the high, four clips and the rig
245.6 s): a place's machine about 15 min plus a minute a clip, EUR 0.22 for env1's camp (one walker) and EUR 0.30
for its street (seven), when the cast stands them as singles.
"""
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys

import numpy as np

from score import contracts
from score.checks import FAIL, PASS, UNKNOWN, Check, Verdict
from score.stages import layer_base
from score.stages.cast import measure

REPO = pathlib.Path(__file__).resolve().parents[3]
PEOPLE = REPO / "tools/characters/people"
CLOUD = REPO / "tools/cloud"
ROW = "scene-clips"
RECORD = "scene_clips.json"
CLIP = "walking"  # the cast's clip a walker plays (people_rows.doing_of)
RATE = 30  # Kimodo's frames a second (kimodo/exports/motion_io.py KIMODO_CONVERT_TARGET_FPS)
MOST_SECONDS = 10.0  # Kimodo's longest clip a prompt (docs/source/key_concepts/limitations.md)
MOST_KEYFRAMES = 19  # fewer than 20 constrained frames a constraint type (the same page)
WALK_PACE = 1.333  # tools/characters/cast.py WALK_PACE, metres a second (test_... checks they agree)
# SOMA77's rest pose (Kimodo's standard T-pose: every local turn zero) by Kimodo's own FK (SOMASkeleton77.fk,
# measured 2026-10-27): with the hips at the origin the left ankle (LeftFoot) at (0.1004, -0.9381, -0.0169), the left
# toe end at (0.1003, -1.0052, 0.1806), the right mirrored; the toe end is the sole's lowest point.
HIP_OVER_SOLE = 1.0052
FOOT_SIDE = 0.1004
HEEL, TOE = -0.0169, 0.1806  # along the foot from the hips' line, where the ground under a foot is read
# The cadence of people-clips-made's walking clip (seed 1, Kimodo-SOMA-RP-v1.1, 150 frames): the left foot down over
# frames 0-16, 35-49, 69-84, 104-120, 139-149, the right over 17-32, 52-67, 86-104, 122-137: a stride 34.5 frames,
# the right's first stance middle at frame 24.5.
STEP_FRAMES = 17.25
FIRST_STANCE = 24
END_MARGIN = 8  # frames: no stance asked for this near the clip's end
FLAT_RELIEF = 0.02  # metres of ground height over the footfalls under which the ground counts as flat
# SOMA77 joint indices in Kimodo's NPZ (SOMASkeleton77.bone_order_names).
TOE_END = {"left": 71, "right": 76}
PATH_HELD = 0.10  # metres, mean
FOOT_HELD = 0.05  # metres, mean
# Not measured (see the docstring's Price): a place's machine with its set-up and up to eight clips. Replaced once a
# run is measured.
EUROS = 0.35


def files(place):
    """What the cast is measured on (its seed and kit, the scene record written over it), the walking sentence and
    Kimodo's model and seed (people/clips.py), and the machine's program."""
    return {"seed": "{seeds}/usd-r3/{place}", **layer_base.files(place),
            "sentences": "{repo}/tools/characters/people/clips.py",
            "machine": "{repo}/tools/characters/clips/scene_clips.py"}


# --- the route ------------------------------------------------------------------------------------------------------

def heading_of(start, end):
    """Kimodo's heading of a step from `start` to `end` (radians about up, 0 facing +Z, pi/2 facing +X:
    kimodo/motion_rep/feature_utils.py compute_heading_angle)."""
    return math.atan2(end[0] - start[0], end[2] - start[2])


def legs_of(single):
    """A walker's route as points (x, feet, z): its cast `path`, else a straight leg from its spot the way it faces
    (cast.py's front is -z, turned by `turn` degrees about up) for its walking sentence's seconds at its pace."""
    if single.get("path"):
        return [list(map(float, point)) for point in single["path"]]
    sys.path.insert(0, str(PEOPLE))
    import clips
    turn = math.radians(float(single.get("turn", 0.0)))
    length = clips.SENTENCES[CLIP][1] * float(single.get("pace", WALK_PACE))
    at = list(map(float, single["at"]))
    return [at, [at[0] - math.sin(turn) * length, at[1], at[2] - math.cos(turn) * length]]


def walked(points, pace):
    """The route's root at every frame of RATE when walked at `pace` (frames x 3) and its heading there (radians):
    each leg's own heading, the last leg's held at the end. At most MOST_SECONDS."""
    points = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(np.diff(points[:, [0, 2]], axis=0), axis=1)
    keep = lengths > 1e-9
    points = np.vstack([points[:1], points[1:][keep]])
    lengths = lengths[keep]
    if not len(lengths):
        raise ValueError("the route does not go anywhere")
    along = np.concatenate([[0.0], np.cumsum(lengths)])
    frames = min(int(along[-1] / pace * RATE) + 1, int(MOST_SECONDS * RATE))
    distance = np.arange(frames) * pace / RATE
    leg = np.clip(np.searchsorted(along, distance, side="right") - 1, 0, len(lengths) - 1)
    share = (distance - along[leg]) / lengths[leg]
    roots = points[leg] + (points[leg + 1] - points[leg]) * share[:, None]
    headings = np.array([heading_of(points[index], points[index + 1]) for index in leg])
    return roots, headings


def foot_points(root, heading, side, ground):
    """A foot's heel and toe on the ground (x, feet, z) when its hips stand at `root` facing `heading`."""
    across = FOOT_SIDE if side == "left" else -FOOT_SIDE
    sin, cos = math.sin(heading), math.cos(heading)
    return [[root[0] + across * cos + along * sin, ground, root[2] - across * sin + along * cos]
            for along in (HEEL, TOE)]


def checked(roots, headings, found):
    """The walk check along the route on the cast's geometry (cast/measure.py), frame by frame from its start's
    feet: the ground under each frame, and where the route ends (the frame it runs into a solid, finds no ground or
    steps over KNEE) with why; (grounds, the frames kept, why it was cut or None)."""
    grounds, feet = [], float(roots[0][1])
    for frame, root in enumerate(roots):
        spot = [float(root[0]), feet, float(root[2])]
        under = measure.ground_under([spot], found)[0]
        if under["gap"] is None or under["gap"] > measure.KNEE:
            return grounds, frame, f"no ground within a knee under frame {frame} at {np.round(spot, 2).tolist()}"
        feet -= under["gap"]
        clash = measure.run_into([[spot[0], feet, spot[2]]], found)[0]
        if clash:
            return grounds, frame, f"runs into {', '.join(clash)} at frame {frame}"
        grounds.append(feet)
    return grounds, len(roots), None


def ground_at(points, feet, found):
    """The ground under each point (x, z), looked for down from a knee over `feet`; the feet where none."""
    under = measure.ground_under([[point[0], feet, point[2]] for point in points], found)
    return [feet - stand["gap"] if stand["gap"] is not None else feet for stand in under]


# --- the constraints -----------------------------------------------------------------------------------------------

def canonical(points, origin, heading):
    """Scene points (x, y, z) in Kimodo's canonical frame: `origin` at (0, 0, 0), `heading` turned to +Z."""
    offset = np.asarray(points, dtype=float) - origin
    sin, cos = math.sin(heading), math.cos(heading)
    return np.column_stack([offset[:, 0] * cos - offset[:, 2] * sin, offset[:, 1],
                            offset[:, 0] * sin + offset[:, 2] * cos])


def stances(frames):
    """The constrained stance middles (frame, foot): every STEP_FRAMES from FIRST_STANCE, right foot first, none in
    the last END_MARGIN frames."""
    found, step = [], 0
    while round(FIRST_STANCE + step * STEP_FRAMES) < frames - END_MARGIN:
        found.append((int(round(FIRST_STANCE + step * STEP_FRAMES)), "right" if step % 2 == 0 else "left"))
        step += 1
    return found


def footfalls(roots, headings, grounds, found):
    """Each stance middle's foot: its frame, side, hips (x, z), heading and the ground under it (the higher of its
    heel's and its toe's, so a sole over a step's edge stands on the step)."""
    falls = []
    for frame, side in stances(len(grounds)):
        points = foot_points(roots[frame], headings[frame], side, grounds[frame])
        falls.append({"frame": frame, "side": side, "hips": [float(roots[frame][0]), float(roots[frame][2])],
                      "heading": float(headings[frame]), "ground": max(ground_at(points, grounds[frame], found))})
    return falls


def constraints_of(roots, headings, falls, origin):
    """Kimodo's constraints JSON (docs/source/user_guide/constraints.md) in its canonical frame: the dense root2d
    path with its heading, and each foot's stance middles as SOMA77's rest pose turned to the heading, its hips
    HIP_OVER_SOLE over the ground asked (its FK puts the sole there)."""
    start = headings[0]
    path = canonical(roots, origin, start)
    turned = np.asarray(headings) - start
    found = [{"type": "root2d", "frame_indices": list(range(len(roots))),
              "smooth_root_2d": np.round(path[:, [0, 2]], 5).tolist(),
              "global_root_heading": np.round(np.column_stack([np.cos(turned), np.sin(turned)]), 6).tolist()}]
    for side in ("left", "right"):
        mine = [fall for fall in falls if fall["side"] == side]
        if not mine:
            continue
        if len(mine) > MOST_KEYFRAMES:
            raise ValueError(f"{len(mine)} {side} foot stances: Kimodo holds fewer than 20 a constraint type")
        hips = canonical([[fall["hips"][0], fall["ground"] + HIP_OVER_SOLE, fall["hips"][1]] for fall in mine],
                         origin, start)
        poses = np.zeros((len(mine), 77, 3))
        poses[:, 0, 1] = [fall["heading"] - start for fall in mine]
        found.append({"type": f"{side}-foot", "frame_indices": [fall["frame"] for fall in mine],
                      "root_positions": np.round(hips, 5).tolist(), "local_joints_rot": np.round(poses, 6).tolist()})
    return found


def seconds_of(frames):
    """The `--duration` that makes Kimodo give exactly `frames` frames (it takes int(duration * fps))."""
    seconds = f"{(frames + 0.5) / RATE:.4f}"
    assert int(float(seconds) * RATE) == frames
    return seconds


def plan_of(single, found):
    """A walker's scene-made clip: its route walked and checked, its footfalls and constraints, its placement (the
    clip's canonical frame under translate `origin`, rotateY `turn` degrees), seconds and post-processing; or None and
    why it has none."""
    pace = float(single.get("pace", WALK_PACE))
    roots, headings = walked(legs_of(single), pace)
    grounds, kept, cut = checked(roots, headings, found)
    if kept < 2 * RATE:
        return None, f"{single['name']}: under two seconds of its route walk clear ({cut})"
    roots, headings = roots[:kept], headings[:kept]
    falls = footfalls(roots, headings, grounds, found)
    origin = np.array([roots[0][0], grounds[0], roots[0][2]])
    heights = [fall["ground"] for fall in falls] or [grounds[0]]
    relief = float(max(heights) - min(heights))
    return {"name": single["name"], "clip": f"scene_{single['name']}", "pace": pace,
            "seconds": seconds_of(kept), "frames": kept, "cut": cut,
            "placement": {"origin": np.round(origin, 5).tolist(), "turn": round(math.degrees(headings[0]), 4)},
            "route": np.round(np.column_stack([roots[:, 0], grounds, roots[:, 2]]), 4).tolist(),
            "footfalls": falls, "relief": round(relief, 4), "postprocess": relief <= FLAT_RELIEF,
            "constraints": constraints_of(roots, headings, falls, origin)}, None


# --- the make ------------------------------------------------------------------------------------------------------

def make_folder(place, plans, name):
    """The make folder characters.py runs scene_clips.py on: in/spec.json and each clip's constraints in in/files/."""
    sys.path.insert(0, str(PEOPLE))
    import clips
    (place / "in" / "files").mkdir(parents=True)
    scene = {}
    for plan in plans:
        (place / "in" / "files" / f"{plan['clip']}.json").write_text(json.dumps(plan["constraints"]))
        scene[plan["clip"]] = {"sentence": clips.SENTENCES[CLIP][0], "seconds": plan["seconds"],
                               "constraints": f"in/files/{plan['clip']}.json", "postprocess": plan["postprocess"]}
    spec = {"name": f"{ROW}-{name}", "program": "scene_clips.py", "steps": ["scene clips", "rig"], "references": [],
            "clips": list(scene), "scene clips": scene, "approved": f"the batch's {ROW}@{name} row"}
    (place / "in" / "spec.json").write_text(json.dumps(spec, indent=1))
    return place


def on_machine(place, who):
    """The make folder run on a rented characters machine (place/out/ rig.npz, motions/ and make.json); the run folder
    characters.py wrote, named by its process id (None when it rented nothing)."""
    sys.path.insert(0, str(REPO / "tools/props"))
    from paths import HOME, WORK
    process = subprocess.Popen([str(HOME / "env/bin/python"), str(CLOUD / "characters.py"), str(place), "--who", who])
    if process.wait():
        raise subprocess.CalledProcessError(process.returncode, process.args)
    runs = sorted((WORK / "cloud").glob(f"characters-*-{process.pid}"))
    return runs[-1] if runs else None


def last_line(log):
    lines = [line for line in log.read_text().splitlines() if line.strip()]
    return lines[-1] if lines else "empty"


def failure_of(run, work):
    """Why a machine brought back no rig: its chain's last log line when the chain ran, else the set-up steps that
    failed and the set-up log's last line (characters.py leaves a failed set-up as a gap and exits 0)."""
    chain = work / "out" / "chain.log"
    if chain.exists():
        return f"its chain failed ({last_line(chain)}; {chain})"
    for log in sorted(run.glob("*/setup.log")) if run else []:
        steps = re.findall(r"^setup step (\S+) failed:", log.read_text(), re.M)
        if steps:
            return f"the set-up step {', '.join(steps)} failed ({last_line(log)}; {log})"
    return f"the machine brought back nothing (run folder {run})"


def walkers_of(cast):
    return [single for single in cast["characters"] if single.get("doing") == CLIP]


def make(inputs, out, seed, params):
    """Every walker's scene-made clip: rig.npz, motions/, make.json and scene_clips.json."""
    from score.stages.cast import made_ground
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    place, walkers = cast["place"], walkers_of(cast)
    plans, left_out = [], []
    if walkers:
        with layer_base.built(inputs) as folder:
            found = measure.solids(folder / "layers/base.usda", place, made_ground(inputs, place))
        for single in walkers:
            plan, why = plan_of(single, found)
            if plan:
                plans.append(plan)
            else:
                left_out.append(why)
    if plans:
        work = make_folder(out / "make", plans, place)
        run = on_machine(work, f"{ROW}-{place}")
        if not (work / "out" / "rig.npz").exists():
            raise RuntimeError(f"{ROW}@{place}: no rig.npz came back: {failure_of(run, work)}")
        for made in ("rig.npz", "make.json"):
            shutil.copy2(work / "out" / made, out / made)
        shutil.copytree(work / "out" / "motions", out / "motions")
        shutil.rmtree(work)
    (out / RECORD).write_text(json.dumps({"place": place, "clips": plans, "left out": left_out}, indent=1))


# --- the gates -----------------------------------------------------------------------------------------------------

def plans_of(output):
    return json.loads((pathlib.Path(output) / RECORD).read_text())["clips"]


def motion_of(output, plan):
    with np.load(pathlib.Path(output) / "motions" / f"{plan['clip']}.npz") as held:
        return {key: held[key] for key in ("root_positions", "posed_joints")}


def path_off(plan, motion):
    """The mean distance on the ground (metres) of the clip's hips from its route, frame by frame."""
    route = canonical(plan["route"], plan["placement"]["origin"], math.radians(plan["placement"]["turn"]))
    frames = min(len(route), len(motion["root_positions"]))
    return float(np.linalg.norm(motion["root_positions"][:frames, [0, 2]] - route[:frames, [0, 2]], axis=1).mean())


def feet_off(plan, motion):
    """The mean height (metres) of each constrained foot's sole (its toe end) off the ground asked for it."""
    origin = plan["placement"]["origin"]
    offs = [abs(float(motion["posed_joints"][fall["frame"], TOE_END[fall["side"]], 1]) - (fall["ground"] - origin[1]))
            for fall in plan["footfalls"] if fall["frame"] < len(motion["posed_joints"])]
    return float(np.mean(offs)) if offs else 0.0


def judge_made(output, inputs, evidence):
    """Every planned clip in the rig, with its motion and its record."""
    plans = plans_of(output)
    held = set()
    if plans:
        with np.load(output / "rig.npz") as rig:
            held = set(rig.files)
    failing = [f"{plan['clip']}: {what}" for plan in plans for what, there in
               (("not in the rig", f"clip_{plan['clip']}" in held),
                ("no motion", (output / "motions" / f"{plan['clip']}.npz").exists()),
                ("no record", (output / "motions" / f"{plan['clip']}.record.json").exists())) if not there]
    return Verdict("made", FAIL if failing else PASS, "; ".join(failing) or f"{len(plans)} scene-made clips",
                   {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


def judge_path(output, inputs, evidence):
    """Each clip's hips within PATH_HELD of its route on the mean."""
    offs = {plan["clip"]: path_off(plan, motion_of(output, plan)) for plan in plans_of(output)}
    failing = [f"{clip}: its hips {off:.3f} m off its route on the mean" for clip, off in offs.items()
               if off > PATH_HELD]
    worst = max(offs.values(), default=0.0)
    return Verdict("path held", FAIL if failing else PASS, "; ".join(failing) or
                   f"{len(offs)} clips within {PATH_HELD} m of their routes", {"worst m": round(worst, 4)},
                   {"worst m": "lower"}, tuple(failing))


def judge_feet(output, inputs, evidence):
    """Each clip's constrained soles within FOOT_HELD of their ground on the mean."""
    offs = {plan["clip"]: feet_off(plan, motion_of(output, plan)) for plan in plans_of(output)}
    failing = [f"{clip}: its soles {off:.3f} m off their ground on the mean" for clip, off in offs.items()
               if off > FOOT_HELD]
    worst = max(offs.values(), default=0.0)
    return Verdict("feet held", FAIL if failing else PASS, "; ".join(failing) or
                   f"{len(offs)} clips' soles within {FOOT_HELD} m of their ground", {"worst m": round(worst, 4)},
                   {"worst m": "lower"}, tuple(failing))


def guarded(name, judge):
    """A check whose missing or unreadable output answers unknown, never pass."""
    def judged(output, inputs, evidence):
        try:
            return judge(pathlib.Path(output), inputs, evidence)
        except (FileNotFoundError, KeyError, ValueError, IndexError, json.JSONDecodeError) as missing:
            return Verdict(name, UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")
    return Check(name, judged)


def output_faults(folder):
    folder = pathlib.Path(folder)
    if not (folder / RECORD).exists():
        return [f"no {RECORD}"]
    return [f"no {name}" for name in ("rig.npz", "motions") if plans_of(folder) and not (folder / name).exists()]


CONTRACT = contracts.Contract(ROW, 1, output_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (guarded("made", judge_made), guarded("path held", judge_path), guarded("feet held", judge_feet))
