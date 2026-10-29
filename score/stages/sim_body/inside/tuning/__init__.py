"""Level 1 of the fit (#70; CONTEXT.md "landmark set"; numpy and scipy): ONE joint optimisation of the landmark set
over every tuning body at once, never a round of pieces judged alone. The unknowns (`layout`): each landmark's link
on its bone (a joint-defining one only across the bone's long axis), its trust (log), and the two global weights
(the markers' goal against the turns', a group end's weight); a left and a right landmark share their unknowns, the
right mirrored (`paired`). The residuals (`case_residuals`) are what following SOMA means, from levels 2 and 3 run on
each tuning case: bones outside SOMA's skin by region, each group's rotation error on a FROZEN calibration table,
each joint's error beside them (`JOINT_SHARE`, since SOMA's group ends are fit targets); never a landmark distance the
solver pulls on. A prior (`prior`) pulls each link toward its anatomical start. scipy's least_squares (trf) runs it
with finite differences on a sparse pattern (`sparsity`: a landmark reaches its own group and the groups next to it,
a global weight everything), every evaluation checkpointed (`checkpointed`) and the run stopped when the objective
settles (`settled`) or a wall-clock limit passes. `rewritten` writes the result into the landmark table's source."""
import json
import re
import time

import numpy as np
from scipy.optimize import least_squares

LONG_AXIS = 1  # MyoFullBody's bodies run along their own y (OpenSim's convention): the axis a joint link keeps
MIRROR = np.array([1.0, 1.0, -1.0])  # a right landmark's body-frame vector as its left one's
LINK_UNIT = 0.005  # metres per unknown's unit: finite-difference steps and bounds are in these units
LOG_UNIT = 0.25  # natural-log units per unknown's unit, for trusts and global weights
REACH = 0.030  # metres: no link ends further than this from its anatomical start (the bound)
PRIOR = 0.010  # metres: the anatomical start's spread (the prior's residual is the offset over it)
STEP = 0.4  # unknown's units: the finite-difference step (2 mm of link, 0.1 of log weight)
WEIGHT_REACH = 3.0  # unknown's units of log either way a trust or global weight may move (e^0.75: about 2x)
JOINT_SHARE = 0.5  # joint error's weight beside skin and turns: SOMA's group ends are fit targets (#70 honesty rule)
SCALES = {"skin": 10.0, "turn": 5.0, "joint": 10.0}  # %, degrees, mm: one unit of each counts the same (the score's)
GLOBALS = ("marker goal", "end weight")
# SOMA's bone groups: each one's parent, and the skin region its bones are measured in
PARENT = {"Spine1": "Hips", "Spine2": "Spine1", "Chest": "Spine2", "Neck1": "Chest", "Neck2": "Neck1",
          "Head": "Neck2", **{f"{side}{part}": f"{side}{parent}" if parent else root
                              for side in ("Left", "Right") for part, parent, root in
                              (("Shoulder", None, "Chest"), ("Arm", "Shoulder", None), ("ForeArm", "Arm", None),
                               ("Hand", "ForeArm", None), ("Leg", None, "Hips"), ("Shin", "Leg", None),
                               ("Foot", "Shin", None), ("ToeBase", "Foot", None))}}
REGION = {"Hips": "pelvis", "Spine1": "spine", "Spine2": "spine", "Chest": "spine", "Neck1": "spine",
          "Neck2": "spine", "Head": "head", **{f"{side}{part}": region for side in ("Left", "Right") for part, region in
                                                (("Shoulder", "shoulder"), ("Arm", "shoulder"), ("ForeArm", "forearm"),
                                                 ("Hand", "hand"), ("Leg", "thigh"), ("Shin", "shin"),
                                                 ("Foot", "foot"), ("ToeBase", "foot"))}}


def paired(name):
    """The name a landmark shares its unknowns under (its left side's) and the factor that turns its vectors into it."""
    if name.endswith("_r"):
        return name[:-2] + "_l", MIRROR
    return name, np.ones(3)


def mirrored(segment):
    """A SOMA segment and its other side's ([one] for a middle one)."""
    for one, other in (("Left", "Right"), ("Right", "Left")):
        if segment.startswith(one):
            return [segment, other + segment[len(one):]]
    return [segment]


def layout(table, held, joints):
    """The unknowns: [(pool, kind, axes or None, segments)], kind "link" (axes: the body-frame components it moves)
    or "trust", then each global weight ("global", None, None). `table` {name: row} (the harness's rows: "segment",
    "solver"), `held` names whose links stay, `joints` the joint-defining names."""
    pools = {}
    for name, row in table.items():
        if row["solver"]:
            pools.setdefault(paired(name)[0], []).append(name)
    out = []
    for pool, names in pools.items():
        segments = sorted({side for name in names for side in mirrored(table[name]["segment"])})
        if not any(name in held for name in names):
            axes = [axis for axis in range(3) if axis != LONG_AXIS] if any(name in joints for name in names) \
                else [0, 1, 2]
            out.extend((pool, "link", axis, segments) for axis in axes)
        out.append((pool, "trust", None, segments))
    return out + [(name, "global", None, None) for name in GLOBALS]


def applied(unknowns, entries, starts, table, globals_):
    """The landmark table ({name: row}) and the global weights ({name: value}) at `unknowns` (the unknowns' units,
    0 = the start): each link its anatomical start (`starts` {name: link}) plus the move, mirrored on the right;
    each trust and global its start (`table`'s trust, `globals_`) times e^(LOG_UNIT * unknown)."""
    rows = {name: dict(row) for name, row in table.items()}
    weights = dict(globals_)
    members = {}
    for name, row in table.items():
        if row["solver"]:
            members.setdefault(paired(name)[0], []).append(name)
    moves = {pool: np.zeros(3) for pool in members}
    for value, (pool, kind, axis, _) in zip(unknowns, entries):
        if kind == "link":
            moves[pool][axis] = LINK_UNIT * value
        elif kind == "trust":
            for name in members[pool]:
                rows[name]["trust"] = float(table[name]["trust"] * np.exp(LOG_UNIT * value))
        else:
            weights[pool] = float(globals_[pool] * np.exp(LOG_UNIT * value))
    for pool, names in members.items():
        for name in names:
            rows[name]["link"] = [float(value) for value in np.asarray(starts[name]) + moves[pool] * paired(name)[1]]
    return rows, weights


def bounds(entries):
    """least_squares' bounds (lower, upper) in the unknowns' units: links within REACH, weights within WEIGHT_REACH."""
    reach = np.array([REACH / LINK_UNIT if kind == "link" else WEIGHT_REACH for _, kind, _, _ in entries])
    return -reach, reach


def prior(unknowns, entries):
    """The prior's residuals: each link's move from its anatomical start over PRIOR."""
    return np.array([LINK_UNIT * value / PRIOR for value, (_, kind, _, _) in zip(unknowns, entries) if kind == "link"])


def labels(found):
    """One case's residual labels ([(kind, key)]) in a fixed order, from its measures (the harness's m.json)."""
    return ([("skin", key) for key in sorted(found["bones outside skin %"])]
            + [("turn", key) for key in sorted(found["per group deg"])]
            + [("joint", key) for key in sorted(found["per joint mm"])])


def case_residuals(found):
    """One case's residuals: each region's bones outside the skin (%), each group's median turn error (deg, frozen
    table), each joint's median error (mm, times JOINT_SHARE), each over its SCALES unit and the square root of its
    kind's count, so each kind is its mean."""
    values = {"skin": found["bones outside skin %"], "turn": {key: value[0] for key, value in found["per group deg"].items()},
              "joint": {key: value[0] for key, value in found["per joint mm"].items()}}
    share = {"skin": 1.0, "turn": 1.0, "joint": JOINT_SHARE}
    return np.array([np.sqrt(share[kind] / len(values[kind])) * values[kind][key] / SCALES[kind]
                     for kind, key in labels(found)])


def reached(segments):
    """The segments a landmark on `segments` mainly moves: their own, their parents and their children."""
    near = set(segments)
    for segment in segments:
        near.add(PARENT.get(segment, segment))
        near.update(child for child, parent in PARENT.items() if parent == segment)
    return near


def sparsity(entries, rows, cases):
    """The Jacobian's pattern (residuals x unknowns, 0/1): `rows` one case's labels, repeated for `cases` cases, then
    the prior's rows (each link's own). A landmark reaches the rows of the groups it reaches (`reached`) and their
    regions; a global weight every row; a trust no prior row."""
    links = [index for index, (_, kind, _, _) in enumerate(entries) if kind == "link"]
    pattern = np.zeros((len(rows) * cases + len(links), len(entries)), dtype=np.int8)
    for column, (_, kind, _, segments) in enumerate(entries):
        near = reached(segments) if segments else None
        regions = {REGION[segment] for segment in near} if near else None
        hit = [near is None or (key in regions if label == "skin" else key in near) for label, key in rows]
        pattern[:len(rows) * cases, column] = np.tile(hit, cases)
    for row, column in enumerate(links):
        pattern[len(rows) * cases + row, column] = 1
    return pattern


def settled(costs, share=0.005, span=3):
    """True when the objective (one cost per iteration) changed under `share` over the last `span` iterations."""
    if len(costs) <= span:
        return False
    return abs(costs[-1 - span] - costs[-1]) <= share * abs(costs[-1 - span])


def checkpointed(path, unknowns, cost, note):
    """One evaluation appended to the checkpoint (JSON lines: time, note, cost, unknowns)."""
    with open(path, "a") as file:
        file.write(json.dumps({"time": round(time.time(), 1), "note": note, "cost": float(cost),
                               "unknowns": [float(value) for value in unknowns]}) + "\n")


def resumed(path, size):
    """The best unknowns the checkpoint holds (lowest cost; zeros, the start, when there is none)."""
    try:
        lines = [json.loads(line) for line in open(path) if line.strip()]
    except FileNotFoundError:
        return np.zeros(size)
    lines = [line for line in lines if line["note"] == "evaluation" and len(line["unknowns"]) == size]
    return np.asarray(min(lines, key=lambda line: line["cost"])["unknowns"]) if lines else np.zeros(size)


def solved(residuals, entries, pattern, checkpoint, limit_seconds, every=None, start=None):
    """The one optimisation: least_squares over `residuals(unknowns)` (the cases' residuals then the prior's) from
    `start` (default: the checkpoint's best), every evaluation checkpointed; stopped when the objective settles or
    `limit_seconds` pass; `every` (iteration, unknowns) is called after each iteration (the check bodies' score, logged,
    never used to choose). Returns scipy's result."""
    began, costs = time.time(), []
    start = resumed(checkpoint, len(entries)) if start is None else start

    def evaluated(unknowns):
        found = residuals(unknowns)
        checkpointed(checkpoint, unknowns, 0.5 * float(found @ found), "evaluation")
        return found

    def iterated(intermediate_result):
        costs.append(float(intermediate_result.cost))
        checkpointed(checkpoint, intermediate_result.x, intermediate_result.cost, f"iteration {len(costs)}")
        if every:
            every(len(costs), intermediate_result.x)
        if settled(costs) or time.time() - began > limit_seconds:
            raise StopIteration

    lower, upper = bounds(entries)
    return least_squares(evaluated, np.clip(start, lower, upper), jac="2-point", bounds=(lower, upper), method="trf",
                         jac_sparsity=pattern, diff_step=STEP, x_scale=1.0,
                         callback=iterated)


def whole(evaluate, check, entries, checkpoint, limit_seconds, start=None, every=3):
    """Level 1 entire: `solved` over every tuning case at once, `evaluate(unknowns)` ({case: measures} of levels 2
    and 3 on every tuning body, the evaluation runner's) giving each evaluation's residuals with the prior, and
    `check(unknowns)` (the held-out bodies' score) logged every `every` iterations and at the end, never used to
    choose. Returns (scipy's result, [(iteration, check score)])."""
    start = resumed(checkpoint, len(entries)) if start is None else start
    first = evaluate(start)
    names = sorted(first)
    pattern = sparsity(entries, labels(first[names[0]]), len(names))
    kept = {start.tobytes(): first}
    checks = []

    def residuals(unknowns):
        found = kept.pop(np.asarray(unknowns, dtype=float).tobytes(), None) or evaluate(unknowns)
        return np.concatenate([case_residuals(found[case]) for case in names] + [prior(unknowns, entries)])

    def checked(iteration, unknowns):
        if iteration % every == 0:
            checks.append((iteration, check(unknowns)))
    result = solved(residuals, entries, pattern, checkpoint, limit_seconds, every=checked, start=start)
    checks.append(("end", check(result.x)))
    return result, checks


def rewritten(source, rows):
    """The landmark table's source with each named row's link and trust replaced ({name: (link, trust)})."""
    for name, (link, trust) in rows.items():
        pattern = re.compile(r'("%s": \([^\n]*\n\s+\([^)]*\), )\([^)]*\), [0-9.]+(, (?:True|False)\),)' % re.escape(name))
        text = "(" + ", ".join(f"{value:g}" for value in link) + ")"
        source, count = pattern.subn(lambda match: f"{match.group(1)}{text}, {trust}{match.group(2)}", source)
        if count != 1:
            raise ValueError(f"{name}: {count} rows matched in the table's source")
    return source


def weight_rewritten(source, name, value):
    """A module's source with its global weight `name = <number>` set to `value` (level 1's MARKER_GOAL in
    fit/_frames.py, END_WEIGHT in fit/__init__.py)."""
    found, count = re.subn(r"^%s = [0-9.eE+-]+$" % re.escape(name), f"{name} = {value:g}", source, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"{name}: {count} lines matched in the source")
    return found
