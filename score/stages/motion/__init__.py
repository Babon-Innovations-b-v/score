"""The motion stage (experimental, PRD #6, until the owner reviews it): everything that moves in a place, moving in
its OpenUSD motion layer. The game's own timed motions (`data/motion/<place>.json`: doors, lights, the launch's
climb, the turntable) and the movers SCORE gives the things the game left standing (`data/movers/<place>.json`: a
ferry's round of the harbour, a boom's travel on its rail, a hatch swung open on its hinge, each with its kind and the
source of its numbers) are written into one layer over the place's seed stage.

    make     tools/usd/movers.py's write_layer: layers/motion.usda (taking the place of the seed's) and movers.json
             (what it moved and the layer's seconds)
    gates    clear     no mover reaches into a still thing or another mover over its whole motion: sampled every
                       STEP seconds over the layer's seconds, the points over each still surface near its sweep and
                       over every other mover's surface lie no deeper than REACH_MOST in its hull. A thing it already
                       reaches into where it starts is what it is mounted on (a boom's rail, a hatch's frame), named in
                       the findings and not judged; so is what the movers record's `through` says a motion passes
                       through by its design, with why (a door sunk through a floor the floor plate does not cut)
             speeds    each mover of a kind with a cited speed range (data/checks/motion.json) keeps to it: its peak
                       speed at most the top, its median moving speed at least the bottom (metres a second of its
                       middle, or degrees a second of its turn); a kind the game times is the game's
             loops     every looping motion stands at the end of each round exactly where it started (its hull within
                       SEAM_MOST), takes no bigger step at a seam than anywhere else in its round, and the layer's
                       seconds hold a whole number of each mover's rounds, so the layer itself loops
             grounded  each mover stays on what it moves on: on water or ground every corner of its footprint has
                       that surface under it and it keeps its rest height over it (within HEIGHT_MOST); on a rail it
                       keeps touching what it is mounted on (within TOUCH); in the air it stays AIR_LEAST over all
             covered   every prim of a moving kind in the place (its objects, fixtures and structure) moves in the
                       layer, or the movers record says why it stands still (`still`)

Only places with a movers record have the row. The assembly does not take the layer yet: the final assembly of each
place picks it up in place of the seed's motion layer.
"""
import fnmatch
import json
import pathlib
import re
import sys

import numpy as np

from score import checks, contracts
from score.stages.motion import space

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import motion as game_motion  # noqa: E402
import movers as mover_layer  # noqa: E402

# How often the composed stage is read along the layer, seconds; a fast turn is read finer (TURN_STEP degrees a read).
STEP = 0.25
TURN_STEP = 30.0
# How deep a point may lie in a mover's hull before it is a strike, metres: a hull is the mover's convex outline, so
# a little reach is its own looseness, not a touch.
REACH_MOST = 0.03
# Points over a surface this share of a mover's thinnest size apart (within SPACING_RANGE), metres: a wall crossing a
# hatch's 12 cm leaf still leaves points inside it, and a rail under a 1 m trolley is read every 10 cm.
SPACING_SHARE, SPACING_RANGE = 0.25, (0.02, 0.1)
SEAM_MOST = 0.001
HEIGHT_MOST = 0.05
# How near a mover on a rail keeps to what it is mounted on, metres, past the spacing of the points it is read at.
TOUCH = 0.02
AIR_LEAST = 0.5
ON = ("water", "ground", "rail", "air")
MOVING_SCOPES = ("Objects", "Fixtures", "Structure")


def files(place):
    """What the stage reads: the place's movers record, the moving kinds and their speeds, its seed stage, and its
    game motion record where it has one."""
    found = {"movers": "{data}/movers/{place}.json", "kinds": "{data}/checks/motion.json",
             "seed": "{seeds}/usd-r3/{place}"}
    if (REPO / f"data/motion/{place}.json").exists():
        found["motion"] = "{data}/motion/{place}.json"
    return found


def applies(place):
    return (REPO / f"data/movers/{place}.json").exists()


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


def game_record(inputs):
    return read_json(inputs["motion"]) if "motion" in inputs else None


def make(inputs, out, seed, params):
    """The place's motion layer from its game motions and its movers."""
    place = place_of(inputs)
    written = mover_layer.write_layer(place, game_record(inputs), read_json(inputs["movers"]), inputs["seed"], out)
    (out / "movers.json").write_text(json.dumps({"place": place, "moved": written["moved"],
                                                 "seconds": written["seconds"]}, indent=1))


# --- what moves ---------------------------------------------------------------------------------------------------

def composed(output, inputs):
    """The motion layer over the place's seed stage (its edit, its other layers and base), opened as one stage."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / game_motion.LAYER))
    return game_motion.working_stage(place_of(inputs), inputs["seed"], layer)


def entries(inputs):
    """Every motion the layer holds, the game's and the movers', each marked with whose it is."""
    game = [dict(entry, game=True) for entry in (game_record(inputs) or {}).get("motions", [])]
    return game + [dict(entry, game=False) for entry in read_json(inputs["movers"]).get("movers", [])]


def bodies(inputs):
    """The motions that move a body (a light's switching moves none)."""
    return [entry for entry in entries(inputs) if "light" not in entry]


def seconds_of(output):
    return float(read_json(pathlib.Path(output) / "movers.json")["seconds"])


def rate_of(stage):
    return stage.GetTimeCodesPerSecond()


def kinds_of(inputs):
    return read_json(inputs["kinds"])["kinds"]


def named_kind(entry, kinds):
    """A motion's kind: the mover's own, or for a game motion the kind whose prims its prim is one of."""
    if entry.get("kind"):
        return entry["kind"]
    name = entry["prim"].rsplit("/", 1)[-1]
    return next((kind for kind, rule in kinds.items() if any(of_kind(name, prefix) for prefix in rule["prims"])), None)


def of_kind(name, prefix):
    """A prim named for a kind: the kind's own name, or a row's object `<row>_<n>`."""
    return re.fullmatch(rf"{re.escape(prefix)}(_\d+)?", name) is not None


def spacing_of(shape):
    return float(np.clip((shape.high - shape.low).min() * SPACING_SHARE, *SPACING_RANGE))


def moments(seconds):
    return np.arange(0.0, seconds + 1e-9, STEP)


def shapes(stage, moving):
    """{path: Shape} of each moving prim, as it stands at the layer's start."""
    return {path: shaped(stage, path) for path in moving}


def shaped(stage, path):
    """A mover's Shape with its surface points spaced for its size."""
    prim = stage.GetPrimAtPath(path)
    if not prim:
        raise ValueError(f"the stage has no prim {path}")
    rough = space.Shape(prim, 0.0, SPACING_RANGE[1])
    return space.Shape(prim, 0.0, spacing_of(rough))


# --- clear --------------------------------------------------------------------------------------------------------

def still_reach(shape, near, codes):
    """(the still things it starts inside: {path: depth}, the deepest any other reaches over the codes and where);
    at each code only the points within the mover's bounding ball are tested."""
    mounts = {}
    for path, points in near.items():
        start = float(shape.depth(points, codes[0]).max())
        if start > REACH_MOST:
            mounts[path] = round(start, 3)
    others = [(path, points) for path, points in near.items() if path not in mounts]
    if not others:
        return mounts, -np.inf, None
    points = np.concatenate([points for _, points in others])
    owners = np.concatenate([np.full(len(points), index) for index, (_, points) in enumerate(others)])
    worst, where = -np.inf, None
    for code in codes:
        middle = shape.in_world(shape.middle[None, :], code)[0]
        close = np.linalg.norm(points - middle, axis=1) <= shape.radius
        if not close.any():
            continue
        depth = shape.depth(points[close], code)
        deepest = int(depth.argmax())
        if depth[deepest] > worst:
            worst, where = float(depth[deepest]), (others[owners[close][deepest]][0], code)
    return mounts, worst, where


def designed(near, place, entry, through):
    """The still things near a motion less those its record says it passes through by design (a prim path in the
    place, `*` for any part of a name)."""
    allowed = [f"/{place}/{pattern}" for pattern in through.get(entry["name"], {})]
    return {path: points for path, points in near.items()
            if not any(fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern + "/*")
                       for pattern in allowed)}


def judge_clear(output, inputs, evidence):
    """Pass when no mover reaches into a still thing or another mover over the layer's seconds."""
    stage, place = composed(output, inputs), place_of(inputs)
    through = read_json(inputs["movers"]).get("through", {})
    named = {entry["prim"]: entry for entry in bodies(inputs)}
    rate, seconds = rate_of(stage), seconds_of(output)
    codes = [moment * rate for moment in moments(seconds)]
    moving = sorted({entry["prim"] for entry in bodies(inputs)})
    if not moving:
        return checks.Verdict("clear", checks.PASS, "nothing moves in the place")
    found = shapes(stage, moving)
    stills = space.still_meshes(stage, place, moving)
    faults, measures, mounted = [], {}, {}
    for path, shape in found.items():
        near = space.still_points_near(stills, space.swept_box(shape, codes, 0.1), 0.0, spacing_of(shape))
        mounts, worst, where = still_reach(shape, designed(near, place, named[path], through), codes)
        mounted[path] = sorted(mounts)
        measures[f"{path.rsplit('/', 1)[-1]} reach"] = round(max(worst, 0.0), 3)
        if worst > REACH_MOST:
            faults.append(f"{path}: reaches {worst:.2f} m into {where[0]} at {where[1] / rate:.2f} s")
    for first, second in [(a, b) for a in moving for b in moving if a < b]:
        one, other = found[first], found[second]
        start = max(float(one.depth(other.in_world(other.surface, 0.0), 0.0).max()),
                    float(other.depth(one.in_world(one.surface, 0.0), 0.0).max()))
        if start > REACH_MOST:  # moving together from the start: one thing (a hatch's leaf, wheel and window)
            continue
        for code in codes:
            apart = np.linalg.norm(one.in_world(one.middle[None, :], code)
                                   - other.in_world(other.middle[None, :], code))
            if apart > one.radius + other.radius:  # their bounding balls do not meet
                continue
            depth = max(float(one.depth(other.in_world(other.surface, code), code).max()),
                        float(other.depth(one.in_world(one.surface, code), code).max()))
            if depth > REACH_MOST:
                faults.append(f"{first} and {second} meet {depth:.2f} m deep at {code / rate:.2f} s")
                break
    reason = (f"{len(faults)} strikes among {len(moving)} moving prims" if faults else
              f"{len(moving)} moving prims keep clear of every still thing and of each other over {seconds:.0f} s")
    return checks.Verdict("clear", checks.FAIL if faults else checks.PASS, reason, measures,
                          {name: "lower" for name in measures},
                          tuple(faults) or tuple(f"{path}: mounted on {', '.join(paths) or 'nothing'}"
                                                 for path, paths in mounted.items())
                          + tuple(f"{name}: passes through {prefix} by design: {why}"
                                  for name, allowed in through.items() for prefix, why in allowed.items()))


# --- speeds -------------------------------------------------------------------------------------------------------

def turn_between(first, second):
    """The angle turned between two transforms, degrees (each one's scale taken off its rows)."""
    one = first[:3, :3] / np.linalg.norm(first[:3, :3], axis=1, keepdims=True)
    other = second[:3, :3] / np.linalg.norm(second[:3, :3], axis=1, keepdims=True)
    return float(np.degrees(np.arccos(np.clip((np.trace(one.T @ other) - 1.0) / 2.0, -1.0, 1.0))))


def measured_speeds(shape, rule, rate, seconds):
    """The mover's speed at each read: metres a second of its middle, or degrees a second of its turn."""
    if "angular" in rule:
        step = min(STEP, TURN_STEP / float(rule["angular"][1]))
        times = np.arange(0.0, seconds + 1e-9, step)
        poses = [shape.placed(moment * rate) for moment in times]
        return np.array([turn_between(before, after) / step for before, after in zip(poses, poses[1:])])
    times = moments(seconds)
    middles = np.array([shape.in_world(shape.middle[None, :], moment * rate)[0] for moment in times])
    return np.linalg.norm(np.diff(middles, axis=0), axis=1) / STEP


def judge_speeds(output, inputs, evidence):
    """Pass when each mover of a kind with a cited range keeps to it."""
    stage, kinds = composed(output, inputs), kinds_of(inputs)
    rate, seconds = rate_of(stage), seconds_of(output)
    faults, measures, game, judged = [], {}, [], 0
    for entry in bodies(inputs):
        kind = named_kind(entry, kinds)
        if kind is None:
            faults.append(f"{entry['name']}: its kind is none of data/checks/motion.json's")
            continue
        rule = kinds[kind]
        if rule.get("game"):
            game.append(entry["name"])
            continue
        if entry["game"]:
            faults.append(f"{entry['name']}: the game times it, yet its kind {kind} is not one the game times")
            continue
        judged += 1
        speeds = measured_speeds(shaped(stage, entry["prim"]), rule, rate, seconds)
        low, high = rule["angular" if "angular" in rule else "linear"]
        unit = "deg/s" if "angular" in rule else "m/s"
        moving = speeds[speeds > 0.01 * high]
        peak = float(speeds.max()) if len(speeds) else 0.0
        middle = float(np.median(moving)) if len(moving) else 0.0
        measures[f"{entry['name']} peak"] = round(peak, 3)
        measures[f"{entry['name']} median"] = round(middle, 3)
        if peak > high * 1.001 or middle < low:
            faults.append(f"{entry['name']} ({kind}): peak {peak:.2f}, median {middle:.2f} {unit}; "
                          f"its kind keeps {low} to {high}")
    reason = (f"{len(faults)} movers off their kind's speeds" if faults else
              f"{judged} movers within their kind's cited speeds"
              + (f"; {len(game)} at the game's own timing" if game else ""))
    if not bodies(inputs):
        return checks.Verdict("speeds", checks.PASS, "nothing moves in the place")
    answer = checks.FAIL if faults else (checks.PASS if judged or game else checks.UNKNOWN)
    return checks.Verdict("speeds", answer, reason, measures, {}, tuple(faults))


# --- loops --------------------------------------------------------------------------------------------------------

def seam_faults(entry, shape, rate, seconds):
    """A looping motion's faults: a round's end off its start, or a jump at a seam bigger than its steps elsewhere."""
    start, length = float(entry.get("start", 0.0)), float(entry["length"])
    first = shape.in_world(shape.corners, start * rate)
    faults, worst = [], 0.0
    seams = np.arange(start + length, seconds + 1e-9, length)
    for seam in seams:
        off = float(np.linalg.norm(shape.in_world(shape.corners, seam * rate) - first, axis=1).max())
        worst = max(worst, off)
        if off > SEAM_MOST:
            faults.append(f"{entry['name']}: {off:.3f} m off its start at the round's end, {seam:.2f} s")
    step = min(STEP, length / 8)
    times = np.arange(start, min(seconds, start + length) + 1e-9, step)
    spots = [shape.in_world(shape.corners, moment * rate) for moment in times]
    steps = [float(np.linalg.norm(after - before, axis=1).max()) for before, after in zip(spots, spots[1:])]
    for seam in seams[seams + step <= seconds + 1e-9]:
        jump = float(np.linalg.norm(shape.in_world(shape.corners, (seam + step) * rate)
                                    - shape.in_world(shape.corners, seam * rate), axis=1).max())
        if jump > max(steps, default=0.0) + SEAM_MOST:
            faults.append(f"{entry['name']}: steps {jump:.3f} m over its seam at {seam:.2f} s, at most "
                          f"{max(steps):.3f} m elsewhere")
    return faults, worst


def judge_loops(output, inputs, evidence):
    """Pass when every looping motion joins its rounds cleanly and fits the layer's seconds whole."""
    stage = composed(output, inputs)
    rate, seconds = rate_of(stage), seconds_of(output)
    looping = [entry for entry in bodies(inputs) if entry.get("loop")]
    faults = mover_layer.round_faults(looping, seconds)
    worst = 0.0
    for entry in looping:
        found, off = seam_faults(entry, shaped(stage, entry["prim"]), rate, seconds)
        faults += found
        worst = max(worst, off)
    if not looping:
        return checks.Verdict("loops", checks.PASS, "no motion of the place loops")
    reason = (f"{len(faults)} faults over {len(looping)} looping motions" if faults else
              f"{len(looping)} looping motions join their rounds within {worst * 1000:.2f} mm and fit "
              f"{seconds:.0f} s whole")
    return checks.Verdict("loops", checks.FAIL if faults else checks.PASS, reason, {"seam": round(worst, 5)},
                          {"seam": "lower"}, tuple(faults))


# --- grounded -----------------------------------------------------------------------------------------------------

def footprint(shape):
    """The corners of the mover's own box at its lowest, in its own frame."""
    low, high = shape.low, shape.high
    return np.array([[x, low[1], z] for x in (low[0], high[0]) for z in (low[2], high[2])])


def surface_faults(entry, shape, meshes, rate, seconds):
    """A mover on water or ground: where its footprint leaves that surface, or it leaves its rest height over it."""
    faults, drift, rest = [], 0.0, None
    for moment in np.arange(0.0, seconds + 1e-9, 1.0):
        corners = shape.in_world(footprint(shape), moment * rate)
        heights = space.heights_under(meshes, corners[:, [0, 2]], moment * rate)
        if np.isnan(heights).any():
            faults.append(f"{entry['name']}: off the {entry['on']} at {moment:.0f} s")
            break
        gap = float(shape.in_world(shape.corners, moment * rate)[:, 1].min() - heights.max())
        rest = gap if rest is None else rest
        drift = max(drift, abs(gap - rest))
        if abs(gap - rest) > HEIGHT_MOST:
            faults.append(f"{entry['name']}: {gap - rest:+.2f} m off its height over the {entry['on']} at "
                          f"{moment:.0f} s")
            break
    return faults, drift


def rail_faults(entry, shape, stills, others, rate, seconds):
    """A mover on a rail: the reads where it touches none of what it starts mounted on, still things or other movers
    (a hatch's wheel rides its leaf)."""
    codes = [moment * rate for moment in moments(seconds)]
    spacing = spacing_of(shape)
    near = space.still_points_near(stills, space.swept_box(shape, codes, 0.1), 0.0, spacing)
    touch = -(TOUCH + spacing)
    mounts = [(lambda code, points=points: points) for points in near.values()
              if float(shape.depth(points, 0.0).max()) > touch]
    mounts += [(lambda code, other=other: other.in_world(other.surface, code)) for other in others
               if float(shape.depth(other.in_world(other.surface, 0.0), 0.0).max()) > touch]
    if not mounts:
        return [f"{entry['name']}: on a rail, yet it touches nothing where it starts"]
    for code in codes:
        if max(float(shape.depth(points(code), code).max()) for points in mounts) < touch:
            return [f"{entry['name']}: leaves what it is mounted on at {code / rate:.2f} s"]
    return []


def air_faults(entry, shape, meshes, rate, seconds):
    for moment in np.arange(0.0, seconds + 1e-9, 1.0):
        corners = shape.in_world(footprint(shape), moment * rate)
        heights = space.heights_under(meshes, corners[:, [0, 2]], moment * rate)
        lowest = float(shape.in_world(shape.corners, moment * rate)[:, 1].min())
        if not np.isnan(heights).all() and lowest - np.nanmax(heights) < AIR_LEAST:
            return [f"{entry['name']}: {lowest - np.nanmax(heights):.2f} m over the ground at {moment:.0f} s"]
    return []


def judge_grounded(output, inputs, evidence):
    """Pass when every mover stays on what it moves on."""
    stage, place = composed(output, inputs), place_of(inputs)
    rate, seconds = rate_of(stage), seconds_of(output)
    movers = [entry for entry in bodies(inputs) if not entry["game"]]
    if not movers:
        return checks.Verdict("grounded", checks.PASS, "the place has only the game's timed motions")
    moving = sorted({entry["prim"] for entry in bodies(inputs)})
    surfaces = {surface: space.surface_meshes(stage, place, surface) for surface in ("water", "ground")}
    stills = space.still_meshes(stage, place, moving)
    faults, measures = [], {}
    for entry in movers:
        if entry.get("on") not in ON:
            faults.append(f"{entry['name']}: moves on {entry.get('on')!r}, none of {', '.join(ON)}")
            continue
        shape = shaped(stage, entry["prim"])
        if entry["on"] in surfaces:
            found, drift = surface_faults(entry, shape, surfaces[entry["on"]], rate, seconds)
            measures[f"{entry['name']} height drift"] = round(drift, 3)
        elif entry["on"] == "rail":
            others = [shaped(stage, path) for path in moving if path != entry["prim"]]
            found = rail_faults(entry, shape, stills, others, rate, seconds)
        else:
            found = air_faults(entry, shape, surfaces["ground"], rate, seconds)
        faults += found
    reason = (f"{len(faults)} of {len(movers)} movers leave what they move on" if faults else
              f"{len(movers)} movers stay on what they move on")
    return checks.Verdict("grounded", checks.FAIL if faults else checks.PASS, reason, measures,
                          {name: "lower" for name in measures}, tuple(faults))


# --- covered ------------------------------------------------------------------------------------------------------

def moving_kind_prims(stage, place, kinds):
    """{path: kind} of every prim of a moving kind in the place's own scopes."""
    found = {}
    for scope in MOVING_SCOPES:
        holder = stage.GetPrimAtPath(f"/{place}/{scope}")
        if not holder:
            continue
        for child in holder.GetChildren():
            kind = next((kind for kind, rule in kinds.items()
                         if any(of_kind(child.GetName(), prefix) for prefix in rule["prims"])), None)
            if kind:
                found[str(child.GetPath())] = kind
    return found


def judge_covered(output, inputs, evidence):
    """Pass when every prim of a moving kind moves in the layer or its standing still is written down."""
    stage, place = composed(output, inputs), place_of(inputs)
    moved = {entry["prim"] for entry in bodies(inputs)}
    still = read_json(inputs["movers"]).get("still", {})
    wanted = moving_kind_prims(stage, place, kinds_of(inputs))
    missing = [f"{path} ({kind})" for path, kind in sorted(wanted.items())
               if path not in moved and path not in still and path.rsplit("/", 1)[-1] not in still]
    measures = {"moving kinds": len(wanted), "moved": len([path for path in wanted if path in moved]),
                "still with a reason": len(wanted) - len(missing) - len([path for path in wanted if path in moved])}
    reason = (f"{len(missing)} of {len(wanted)} prims of a moving kind neither move nor say why" if missing else
              f"all {len(wanted)} prims of a moving kind move ({measures['moved']}) or say why not")
    return checks.Verdict("covered", checks.FAIL if missing else checks.PASS, reason, measures, {},
                          tuple(missing) or tuple(f"{name}: {why}" for name, why in still.items()))


def layer_faults(folder):
    folder = pathlib.Path(folder)
    return [f"no {name}" for name in (game_motion.LAYER, "movers.json") if not (folder / name).exists()]


LAYER = contracts.Contract("motion-layer", 1, layer_faults, {"length": "metre", "up axis": "Y", "time": "second"})
CHECKS = (checks.Check("clear", judge_clear), checks.Check("speeds", judge_speeds),
          checks.Check("loops", judge_loops), checks.Check("grounded", judge_grounded),
          checks.Check("covered", judge_covered))
