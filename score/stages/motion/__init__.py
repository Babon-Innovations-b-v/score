"""The motion stage (experimental, PRD #6, until the owner reviews it): the rigid module of the motion layer
(CONTEXT.md "motion"; the overlay has the layer's modules), everything rigid that moves in a scene, moving in its
OpenUSD motion layer, made from the scene's design (the owner, 2026-10-21: "the modules are not agnostic"), never from
a record written for it: every object of a scene inventory row whose kind moves (score/stages/row_kinds.py) swings,
spins or stands as its kind's rule says (from_design.py, data/checks/row-kinds.json), at the speeds its motion kind
cites (data/checks/motion.json). The moves are written into one layer over the scene's stage: its seed with its accepted
scene record written over the seed's record prims, as the assembly writes it (score/stages/layer_base.py), or the
seed alone for a place with no scene-record row.
The stage is the place itself (motion_layer.place_only): the places it shows are left out, all but their prims that
move, so two places that show each other never load each other round.

    make     the rigid record made from the design over the scene's stage (from_design.py: moves.json), then
             tools/usd/motion_layer.py's write_layer: layers/motion.usda (taking the place of the seed's) and
             moved.json (what it moved and the layer's seconds)
    gates    clear     no moving thing reaches into a still thing or another moving thing over its whole motion: sampled every
                       STEP seconds over the layer's seconds, the points over each still surface near its sweep and
                       over every other moving thing's surface lie no deeper than REACH_MOST in its hull. A thing it already
                       reaches into where it starts is what it is mounted on (a boom's rail, a hatch's frame), named in
                       the findings and not judged; so is what the rigid record's `through` says a motion passes
                       through by its design, with why (a door sunk through a floor the floor plate does not cut)
             speeds    each moving thing of a kind with a cited speed range (data/checks/motion.json) keeps to it: its peak
                       speed at most the top, its median moving speed at least the bottom (metres a second of its
                       middle, or degrees a second of its turn); a kind the game times is the game's
             loops     every looping motion stands at the end of each round exactly where it started (its hull within
                       SEAM_MOST), takes no bigger step at a seam than anywhere else in its round, and the layer's
                       seconds hold a whole number of each moving thing's rounds, so the layer itself loops
             grounded  each moving thing stays on what it moves on: on water or ground every corner of its footprint has
                       that surface under it and it keeps its rest height over it (within HEIGHT_MOST); on a rail it
                       keeps touching what it is mounted on (within TOUCH); in the air it stays AIR_LEAST over all
             covered   every object of an inventory row whose kind moves moves in the layer, or the record says
                       why it stands still (`still`); a prim named like an old record's moving kind
                       (data/checks/motion.json `prims`) that no moving row has is not asked for
             designed  every move and every still thing is an object of a row of the scene's inventory, and every
                       row whose kind moves has an object on the stage
             follows, steps, moving area
                       the motion check (check.py, #23): each move keeps to its record's intended motion at any speed,
                       never jumps from one frame to the next, and what moves is exactly what the records move

Only scenes whose design has a row that moves have the row (applies); the assembly takes the accepted layer in place of
the seed's motion layer.
"""
import fnmatch
import functools
import json
import pathlib
import re
import sys
import tempfile

import numpy as np

from score import checks, contracts
from score.stages import batch_gaps, layer_base, row_kinds
from score.stages.motion import from_design, space

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import motion as game_motion  # noqa: E402
import motion_layer  # noqa: E402
from score.stages.motion import check  # noqa: E402

# How often the composed stage is read along the layer, seconds; a fast turn is read finer (TURN_STEP degrees a read).
STEP = 0.25
TURN_STEP = 30.0
# How deep a point may lie in a moving thing's hull before it is a strike, metres: a hull is the moving thing's convex outline, so
# a little reach is its own looseness, not a touch.
REACH_MOST = 0.03
# A swing that strikes is tried the other way, then FIT_STEP degrees less each time, down to FIT_LEAST (a hatch opens
# into its room as far as `clear` allows); one that strikes at every angle stands, its strike its reason.
FIT_STEP, FIT_LEAST = 10.0, 60.0
# Points over a surface this share of a moving thing's thinnest size apart (within SPACING_RANGE), metres: a wall crossing a
# hatch's 12 cm leaf still leaves points inside it, and a rail under a 1 m trolley is read every 10 cm.
SPACING_SHARE, SPACING_RANGE = 0.25, (0.02, 0.1)
SEAM_MOST = 0.001
HEIGHT_MOST = 0.05
# How near a moving thing on a rail keeps to what it is mounted on, metres, past the spacing of the points it is read at.
TOUCH = 0.02
AIR_LEAST = 0.5
# What a moving thing on the ground drives on is every still thing under it no higher than this over its underside, metres:
# a floor, a sill, the yard past a door; the lift's beam over the rover is not.
CLIMB_MOST = 0.3
ON = ("water", "ground", "rail", "air")
MOVING_SCOPES = ("Objects", "Fixtures", "Structure")


RECORD = "moves.json"


def files(place):
    """What the stage reads: the scene's design inventory, the row-kind rules, the moving kinds and their speeds, and
    its seed stage with its kit and its design's surface data (which bakes of other places it lays, as the settle)."""
    return {**row_kinds.DESIGNED, "kinds": "{data}/checks/motion.json", "seed": "{seeds}/usd-r3/{place}",
            "surfaces": "{home}/design/surfaces/{place}.json", **layer_base.files(place)}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


def game_record(inputs):
    return read_json(inputs["motion"]) if "motion" in inputs else None


def built(inputs):
    """The scene's stage built for the make and each gate (layer_base.built): its moving rows' objects are the prop
    pipeline's, laid there like any other."""
    return layer_base.built(inputs)


def on_built(judge):
    """A gate judged on the record made from the design (the output's moves.json) over the scene's stage built for it
    (built), the build removed when it is judged."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        with built(inputs) as source:
            return judge(output, dict(inputs, built=source, moves=pathlib.Path(output) / RECORD), evidence)
    return judged


def source_of(inputs):
    """The stage folder a gate reads: the one built for it (on_built), else the seed."""
    return pathlib.Path(inputs.get("built", inputs["seed"]))


def renamed(entry, names):
    """A game motion with its prims as the place's scene record names them (the rigid record's `renamed`)."""
    entry = dict(entry, prim=names.get(entry["prim"], entry["prim"]))
    if "adds" in entry and "like" in entry["adds"]:
        entry["adds"] = dict(entry["adds"], like=names.get(entry["adds"]["like"], entry["adds"]["like"]))
    return entry


def game_motions(inputs, stage):
    """(the game's motions whose prim the place has, renamed as its record names them; those whose prim is gone)."""
    names = read_json(inputs["moves"]).get("renamed", {})
    motions = [renamed(entry, names) for entry in (game_record(inputs) or {}).get("motions", [])]
    present = [entry for entry in motions if stands(stage, entry)]
    return present, [entry for entry in motions if entry not in present]


def stands(stage, entry):
    """Whether a game motion's prim is in the place's stage: a light it switches, a light it adds, a copy of a prim
    the stage draws, or a prim that draws a mesh."""
    adds = entry.get("adds", {})
    if "light" in adds:
        return True
    prim = stage.GetPrimAtPath(adds["like"] if "like" in adds else entry["prim"])
    return bool(prim) and ("light" in entry or bool(space.shown_meshes(prim)))


def make(inputs, out, seed, params):
    """The scene's rigid record made from its design over its stage, and its motion layer from it."""
    with built(inputs) as source:
        carried = batch_gaps.of(inputs)
        record = fitted(from_design.record(place_of(inputs), read_json(inputs["design"]),
                                           row_kinds.table(inputs["row kinds"]), kinds_of(inputs),
                                           layer_base.opened(source), carried), inputs, source)
        (out / RECORD).write_text(json.dumps(record, indent=1))
        batch_gaps.write(out, [*carried, *from_design.left_gaps(record)])
        write_motion(dict(inputs, moves=out / RECORD), out, source)


def write_motion(inputs, out, source):
    """The layer written over a built stage folder, and moved.json."""
    from pxr import Sdf
    place = place_of(inputs)
    names = read_json(inputs["moves"]).get("renamed", {})
    every = [renamed(entry, names) for entry in (game_record(inputs) or {}).get("motions", [])]
    every += read_json(inputs["moves"]).get("moves", [])
    stage = motion_layer.working_stage(place, source, Sdf.Layer.CreateAnonymous(".usda"),
                                      motion_layer.moving_prims(every))
    present, gone = game_motions(inputs, stage)
    moving = motion_layer.moving_prims(every)
    written = motion_layer.write_layer(place, {"motions": present}, read_json(inputs["moves"]), source, out,
                                      lambda working, entry: ground_under(working, place, entry["prim"], moving))
    (out / "moved.json").write_text(json.dumps({"place": place, "moved": written["moved"],
                                                 "gone": [f"{entry['name']}: {entry['prim']}" for entry in gone],
                                                 "seconds": written["seconds"]}, indent=1))


def ground_under(stage, place, path, moving):
    """What a moving thing on the ground drives on, as the gate reads it (surface_faults): the height of the highest still
    thing under the corners of its footprint, no higher than CLIMB_MOST over its underside where it rests, with its
    rest spot carried to each [x, z] spot and turned by each turn (degrees from its rest heading)."""
    shape, boxes = shaped(stage, path), space.box_cache(0.0)
    corners = shape.in_world(footprint(shape), 0.0)
    rest = shape.placed(0.0)[3, :3]
    offsets = corners[:, [0, 2]] - rest[[0, 2]]
    below = float(corners[:, 1].min()) + CLIMB_MOST
    corners_under = space.surface_corners([mesh for mesh in space.still_meshes(stage, place, moving)
                                           if space.mesh_box(mesh, boxes)[0][1] <= below], 0.0)
    known = {}

    def under(spots, turns):
        found = []
        for spot, turn in zip(spots, turns):
            key = (round(float(spot[0]), 4), round(float(spot[1]), 4), round(float(turn), 3))
            if key not in known:  # a moving thing standing still asks the same spot again and again
                sine, cosine = np.sin(np.radians(turn)), np.cos(np.radians(turn))  # rotateY's [x, z]
                turned = np.stack([offsets[:, 0] * cosine + offsets[:, 1] * sine,
                                   -offsets[:, 0] * sine + offsets[:, 1] * cosine], axis=1)
                heights = space.heights_over(corners_under, turned + spot, below)
                known[key] = np.nan if np.isnan(heights).any() else float(heights.max())
            found.append(known[key])
        return np.asarray(found)
    return under


# --- what moves ---------------------------------------------------------------------------------------------------

def composed(output, inputs):
    """The motion layer over the place's stage (its edit, its other layers and base), opened as one stage."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / game_motion.LAYER))
    return motion_layer.working_stage(place_of(inputs), source_of(inputs), layer,
                                     motion_layer.moving_prims(entries(inputs)))


def entries(inputs):
    """Every motion the layer holds, the game's (as the place's record names their prims) and the moving things', each marked
    with whose it is."""
    names = read_json(inputs["moves"]).get("renamed", {})
    game = [dict(renamed(entry, names), game=True) for entry in (game_record(inputs) or {}).get("motions", [])]
    return game + [dict(entry, game=False) for entry in read_json(inputs["moves"]).get("moves", [])]


def gone_of(output):
    return read_json(pathlib.Path(output) / "moved.json").get("gone", [])


def bodies(inputs, output):
    """The motions that move a body (a light's switching moves none), less the game's whose prim is gone."""
    gone = {line.split(":", 1)[0] for line in gone_of(output)}
    return [entry for entry in entries(inputs) if "light" not in entry and entry["name"] not in gone]


def seconds_of(output):
    return float(read_json(pathlib.Path(output) / "moved.json")["seconds"])


def rate_of(stage):
    return stage.GetTimeCodesPerSecond()


def kinds_of(inputs):
    return read_json(inputs["kinds"])["kinds"]


def named_kind(entry, kinds):
    """A motion's kind: the moving thing's own, or for a game motion the kind whose prims its prim is one of."""
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
    """A moving thing's Shape with its surface points spaced for its size."""
    prim = stage.GetPrimAtPath(path)
    if not prim:
        raise ValueError(f"the stage has no prim {path}")
    rough = space.Shape(prim, 0.0, SPACING_RANGE[1])
    return space.Shape(prim, 0.0, spacing_of(rough))


# --- clear --------------------------------------------------------------------------------------------------------

def still_reach(shape, near, codes):
    """(the still things it starts inside: {path: depth}, the deepest any other reaches over the codes and where);
    at each code only the points within the moving thing's bounding ball are tested."""
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


def strikes(output, inputs):
    """What `clear` reads off the layer over the place's stage: ([(prim, its strike)] of each moving thing that reaches
    into a still thing or another moving thing, the later of two that meet named), {"<name> reach": metres},
    {prim: the still things it is mounted on}, and how many prims move."""
    stage, place = composed(output, inputs), place_of(inputs)
    through = read_json(inputs["moves"]).get("through", {})
    named = {entry["prim"]: entry for entry in bodies(inputs, output)}
    rate, seconds = rate_of(stage), seconds_of(output)
    codes = [moment * rate for moment in moments(seconds)]
    moving = sorted({entry["prim"] for entry in bodies(inputs, output)})
    if not moving:
        return [], {}, {}, 0
    found = shapes(stage, moving)
    stills = space.still_meshes(stage, place, moving)
    faults, measures, mounted = [], {}, {}
    for path, shape in found.items():
        near = space.still_points_near(stills, space.swept_box(shape, codes, 0.1), 0.0, spacing_of(shape))
        mounts, worst, where = still_reach(shape, designed(near, place, named[path], through), codes)
        mounted[path] = sorted(mounts)
        measures[f"{path.rsplit('/', 1)[-1]} reach"] = round(max(worst, 0.0), 3)
        if worst > REACH_MOST:
            faults.append((path, f"{path}: reaches {worst:.2f} m into {where[0]} at {where[1] / rate:.2f} s"))
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
                faults.append((second, f"{first} and {second} meet {depth:.2f} m deep at {code / rate:.2f} s"))
                break
    return faults, measures, mounted, len(moving)


def judge_clear(output, inputs, evidence):
    """Pass when no moving thing reaches into a still thing or another moving thing over the layer's seconds."""
    faults, measures, mounted, moving = strikes(output, inputs)
    if not moving:
        return checks.Verdict("clear", checks.PASS, "nothing moves in the place")
    through = read_json(inputs["moves"]).get("through", {})
    reason = (f"{len(faults)} strikes among {moving} moving prims" if faults else
              f"{moving} moving prims keep clear of every still thing and of each other over "
              f"{seconds_of(output):.0f} s")
    return checks.Verdict("clear", checks.FAIL if faults else checks.PASS, reason, measures,
                          {name: "lower" for name in measures},
                          tuple(text for _, text in faults)
                          or tuple(f"{path}: mounted on {', '.join(paths) or 'nothing'}"
                                   for path, paths in mounted.items())
                          + tuple(f"{name}: passes through {prefix} by design: {why}"
                                  for name, allowed in through.items() for prefix, why in allowed.items()))


# --- fitted by the gate ---------------------------------------------------------------------------------------------

def swing_angles(angle):
    """The angles a swing is tried at, in order: its rule's either way, then FIT_STEP less each time, down to
    FIT_LEAST."""
    sizes = np.arange(abs(float(angle)), FIT_LEAST - 1e-9, -FIT_STEP)
    return [round(float(size), 6) * sign for size in sizes for sign in (1.0, -1.0)]


def struck_moves(record, inputs, source):
    """{prim: its first strike} of the record's moves written over the built stage, as `clear` reads them."""
    layer_base.SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fit-", dir=layer_base.SCRATCH) as scratch:
        trial = pathlib.Path(scratch)
        (trial / RECORD).write_text(json.dumps(record, indent=1))
        trial_inputs = dict(inputs, built=source, moves=trial / RECORD)
        write_motion(trial_inputs, trial, source)
        found = {}
        for path, text in strikes(trial, trial_inputs)[0]:
            found.setdefault(path, text)
        return found


def turned_to(move, angle):
    """A swing turned `angle` degrees (signed: the rule's way or the other), saying it was fitted."""
    way = "its rule's way" if angle > 0 else "the other way"
    return dict(move, swing=dict(move["swing"], angle=angle),
                **{"from": f"{move['from']}; fitted by the clear gate: {abs(angle):g} degrees {way}, the first of "
                           f"{FIT_LEAST:g} degrees up to its rule's either way that keeps clear"})


def fitted(record, inputs, source):
    """The record with each move that strikes fitted (a hatch opens as far as `clear` allows): a swing tried the other
    way, then FIT_STEP less, down to FIT_LEAST degrees; a move that strikes at every angle tried stands, its strike
    the reason."""
    first = {move["prim"]: move for move in record["moves"]}
    left = {prim: swing_angles(move["swing"]["angle"])[1:] if "swing" in move else []
            for prim, move in first.items()}
    moves, still = list(record["moves"]), dict(record["still"])
    while True:
        struck = struck_moves(dict(record, moves=moves, still=still), inputs, source)
        if not struck:
            return dict(record, moves=moves, still=still)
        kept = []
        for move in moves:
            prim = move["prim"]
            if prim not in struck:
                kept.append(move)
            elif left[prim]:
                kept.append(turned_to(first[prim], left[prim].pop(0)))
            else:
                still[prim] = f"it strikes at every way it was tried, so it stands: {struck[prim]}"
        moves = kept


def turn_between(first, second):
    """The angle turned between two transforms, degrees (each one's scale taken off its rows)."""
    one = first[:3, :3] / np.linalg.norm(first[:3, :3], axis=1, keepdims=True)
    other = second[:3, :3] / np.linalg.norm(second[:3, :3], axis=1, keepdims=True)
    return float(np.degrees(np.arccos(np.clip((np.trace(one.T @ other) - 1.0) / 2.0, -1.0, 1.0))))


def measured_speeds(shape, rule, rate, seconds):
    """The moving thing's speed at each read: metres a second of its middle, or degrees a second of its turn."""
    if "angular" in rule:
        step = min(STEP, TURN_STEP / float(rule["angular"][1]))
        times = np.arange(0.0, seconds + 1e-9, step)
        poses = [shape.placed(moment * rate) for moment in times]
        return np.array([turn_between(before, after) / step for before, after in zip(poses, poses[1:])])
    times = moments(seconds)
    middles = np.array([shape.in_world(shape.middle[None, :], moment * rate)[0] for moment in times])
    return np.linalg.norm(np.diff(middles, axis=0), axis=1) / STEP


def judge_speeds(output, inputs, evidence):
    """Pass when each moving thing of a kind with a cited range keeps to it."""
    stage, kinds = composed(output, inputs), kinds_of(inputs)
    rate, seconds = rate_of(stage), seconds_of(output)
    faults, measures, game, judged = [], {}, [], 0
    for entry in bodies(inputs, output):
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
    reason = (f"{len(faults)} moving things off their kind's speeds" if faults else
              f"{judged} moving things within their kind's cited speeds"
              + (f"; {len(game)} at the game's own timing" if game else ""))
    if not bodies(inputs, output):
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
    looping = [entry for entry in bodies(inputs, output) if entry.get("loop")]
    faults = motion_layer.round_faults(looping, seconds)
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
    """The corners of the moving thing's own box at its lowest, in its own frame."""
    low, high = shape.low, shape.high
    return np.array([[x, low[1], z] for x in (low[0], high[0]) for z in (low[2], high[2])])


def surface_faults(entry, shape, meshes, rate, seconds):
    """A moving thing on water or ground: where its footprint leaves that surface, or it leaves its rest height over it. On
    the ground the surface is what is under it no higher than CLIMB_MOST over its underside then."""
    faults, drift, rest = [], 0.0, None
    under = space.surface_corners(meshes, 0.0)  # still surfaces: read once
    for moment in np.arange(0.0, seconds + 1e-9, 0.5 if entry["on"] == "ground" else 1.0):
        corners = shape.in_world(footprint(shape), moment * rate)
        below = corners[:, 1].min() + CLIMB_MOST if entry["on"] == "ground" else np.inf
        heights = space.heights_over(under, corners[:, [0, 2]], below)
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
    """A moving thing on a rail: the reads where it touches none of what it starts mounted on, still things or other moving things
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
    """Pass when every moving thing stays on what it moves on."""
    stage, place = composed(output, inputs), place_of(inputs)
    rate, seconds = rate_of(stage), seconds_of(output)
    moves = [entry for entry in bodies(inputs, output) if not entry["game"]]
    if not moves:
        return checks.Verdict("grounded", checks.PASS, "the place has only the game's timed motions")
    moving = sorted({entry["prim"] for entry in bodies(inputs, output)})
    stills = space.still_meshes(stage, place, moving)
    surfaces = {"water": space.surface_meshes(stage, place, "water"),
                "ground": [*space.surface_meshes(stage, place, "ground"), *stills]}
    faults, measures = [], {}
    for entry in moves:
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
    reason = (f"{len(faults)} of {len(moves)} moving things leave what they move on" if faults else
              f"{len(moves)} moving things stay on what they move on")
    return checks.Verdict("grounded", checks.FAIL if faults else checks.PASS, reason, measures,
                          {name: "lower" for name in measures}, tuple(faults))


# --- covered ------------------------------------------------------------------------------------------------------

def moving_row_prims(stage, place, inputs):
    """{path: row kind} of every object on the stage of an inventory row whose kind moves."""
    kinds = row_kinds.table(inputs["row kinds"])
    return {path: row["row_kind"] for row in row_kinds.rows_that(read_json(inputs["design"]), "moves", kinds)
            for path in row_kinds.objects_of(stage, place, row["id"])}


def judge_covered(output, inputs, evidence):
    """Pass when every object of a row whose kind moves moves in the layer or its standing still is written down."""
    stage, place = composed(output, inputs), place_of(inputs)
    moved = {entry["prim"] for entry in bodies(inputs, output)}
    record = read_json(inputs["moves"])
    still, removed = record.get("still", {}), record.get("removed", {})
    wanted = moving_row_prims(stage, place, inputs)
    unmoved = [f"{path} ({kind})" for path, kind in sorted(wanted.items())
               if path not in moved and path not in still and path.rsplit("/", 1)[-1] not in still]
    gone = [line.split(":", 1)[0] for line in gone_of(output)]
    missing = unmoved + [f"{name}: the game's motion has no prim in the place's stage and the record does not say "
                         "the concept removed it" for name in gone if name not in removed]
    measures = {"moving kinds": len(wanted), "moved": len([path for path in wanted if path in moved]),
                "still with a reason": len(wanted) - len(unmoved) - len([path for path in wanted if path in moved]),
                "removed by the concept": len([name for name in gone if name in removed])}
    reason = (f"{len(missing)} prims of a moving kind or game motions neither move nor say why" if missing else
              f"all {len(wanted)} prims of a moving kind move ({measures['moved']}) or say why not")
    said = [f"{name}: {why}" for name, why in still.items()]
    said += [f"{name}: removed by the concept: {removed[name]}" for name in gone if name in removed]
    return checks.Verdict("covered", checks.FAIL if missing else checks.PASS, reason, measures, {},
                          tuple(missing) or tuple(said))


# --- the motion check (check.py) ------------------------------------------------------------------------------------

def judge_follows(output, inputs, evidence):
    """Pass when every move keeps to its record's intended motion (check.judge_follows)."""
    stage = composed(output, inputs)
    return check.judge_follows(stage, bodies(inputs, output), rate_of(stage), seconds_of(output))


def judge_steps(output, inputs, evidence):
    """Pass when no move jumps from one frame to the next (check.judge_steps)."""
    stage, entries = composed(output, inputs), bodies(inputs, output)
    return check.judge_steps(entries, shapes(stage, {entry["prim"] for entry in entries}), rate_of(stage),
                             seconds_of(output))


def judge_moving_area(output, inputs, evidence):
    """Pass when what moves is exactly what the records move (check.judge_moving_area)."""
    stage, entries = composed(output, inputs), bodies(inputs, output)
    return check.judge_moving_area(stage, place_of(inputs), entries,
                                   shapes(stage, {entry["prim"] for entry in entries}), rate_of(stage),
                                   seconds_of(output), MOVING_SCOPES)


def layer_faults(folder):
    folder = pathlib.Path(folder)
    return [f"no {name}" for name in (game_motion.LAYER, "moved.json") if not (folder / name).exists()]


def judge_designed(output, inputs, evidence):
    """Pass when every move and every still thing of the record is an object of a row of the scene's inventory, and
    every row whose kind moves has an object on the stage (the record's `missing`)."""
    record = read_json(inputs["moves"])
    named = [entry["prim"] for entry in record.get("moves", [])] + list(record.get("still", {}))
    faults = [f"{path}: no object of a row of the scene's inventory"
              for path in row_kinds.strangers(named, read_json(inputs["design"]))]
    faults += list(record.get("missing", []))
    reason = (f"{len(faults)} moving things stand on nothing of the inventory" if faults else
              f"{len(named)} moving and standing things are each an object of an inventory row")
    return checks.Verdict("designed", checks.FAIL if faults else checks.PASS, reason,
                          {"named": len(named), "missing": len(faults)}, {"missing": "lower"}, tuple(faults))


LAYER = contracts.Contract("motion-layer", 2, layer_faults, {"length": "metre", "up axis": "Y", "time": "second"})
CHECKS = (checks.Check("clear", on_built(judge_clear)), checks.Check("speeds", on_built(judge_speeds)),
          checks.Check("loops", on_built(judge_loops)), checks.Check("grounded", on_built(judge_grounded)),
          checks.Check("covered", on_built(judge_covered)), checks.Check("follows", on_built(judge_follows)),
          checks.Check("steps", on_built(judge_steps)), checks.Check("moving area", on_built(judge_moving_area)),
          checks.Check("designed", on_built(judge_designed)))
