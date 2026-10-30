"""Level 1 of the fit (#70; CONTEXT.md "landmark set"; numpy and scipy): ONE joint optimisation of the landmark set
over every tuning body at once, never a round of pieces judged alone. The unknowns (`layout`): each landmark's link
on its bone (a joint-defining one only across the bone's long axis), its trust (log), each group end's centre on
MyoFullBody (its offset in its body's frame off the model's own, each end its own: bodies are not symmetric; owner,
2026-10-29: "isn't this exactly what the solver will find"), and the two global weights (the markers' goal against
the turns', a group end's weight); a left and a right landmark share their unknowns, the right mirrored (`paired`). The residuals (`case_residuals`) are what following SOMA means, from levels 2 and 3 run on
each tuning case: bones outside SOMA's skin by region, each group's rotation error on a FROZEN calibration table,
each joint's error beside them (`JOINT_SHARE`, since SOMA's group ends are fit targets); never a landmark distance the
solver pulls on. A prior (`prior`) pulls each link toward its anatomical start and each centre toward the model's own. scipy's least_squares (trf) runs it
with finite differences of ABSOLUTE steps (`_differences`, STEP of each unknown's units) over a sparse pattern's column
groups (`sparsity`: a landmark reaches its own group and the groups next to it, a global weight everything), every
evaluation checkpointed (`checkpointed`) and the run stopped when the objective
settles (`settled`) or a wall-clock limit passes. `rewritten` writes the result into the landmark table's source."""
import json
import re
import time

import numpy as np
from scipy.optimize import least_squares

from tuning._differences import chosen_groups, hybrid, jacobian, serially, signed_steps

LONG_AXIS = 1  # MyoFullBody's bodies run along their own y (OpenSim's convention): the axis a joint link keeps
MIRROR = np.array([1.0, 1.0, -1.0])  # a right landmark's body-frame vector as its left one's
LINK_UNIT = 0.005  # metres per unknown's unit: finite-difference steps and bounds are in these units
LOG_UNIT = 0.25  # natural-log units per unknown's unit, for trusts and global weights
REACH = 0.030  # metres: no link ends further than this from its anatomical start (the bound)
END_REACH = 0.040  # metres: no group end's centre moves further than this from MyoFullBody's own (the bound)
PRIOR = 0.010  # metres: the anatomical start's spread (the prior's residual is the offset over it)
STEP = 0.4  # unknown's units: the ABSOLUTE finite-difference step (2 mm of link or centre, 0.1 of log weight)
WEIGHT_REACH = 3.0  # unknown's units of log either way a trust or global weight may move (e^0.75: about 2x)
JOINT_SHARE = 0.5  # joint error's weight beside skin and turns: SOMA's group ends are fit targets (#70 honesty rule)
SCALES = {"skin": 2.4, "turn": 5.0, "joint": 10.0}  # mm deep, degrees, mm: one unit of each counts the same; the skin's
# 2.4 mm gives its rows the norm 10 % of the share outside gave them at the start (heavy and tall_kimodo, 2026-10-30)
GLOBALS = ("marker goal", "end weight")
MOVES = ("link", "centre")  # the unknowns that are a place (metres), each with its prior row
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


def ended(groups, middles):
    """Each group end's MyoFullBody centre and the bone groups it starts ({centre: [segment]}): every group's start
    centre (`bone_groups.groups()`), a middle of two (`landmarks.MIDDLE_CENTRES`) as its two parts."""
    found = {}
    for segment, (_, (start, _), _, _) in groups.items():
        for part in middles.get(start, (start,)):
            found.setdefault(part, set()).add(segment)
    return {centre: sorted(segments) for centre, segments in found.items()}


def layout(table, held, joints, ends=None):
    """The unknowns: [(pool, kind, axes or None, segments)], kind "link" (axes: the body-frame components it moves)
    or "trust", then each group end's centre ("centre", its three body-frame axes, each end its own: bodies are not
    symmetric), then each global weight ("global", None, None). `table` {name: row} (the harness's rows: "segment",
    "solver"), `held` names whose links stay, `joints` the joint-defining names, `ends` `ended`'s."""
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
    out.extend((centre, "centre", axis, segments) for centre, segments in (ends or {}).items() for axis in range(3))
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
        elif kind == "global":
            weights[pool] = float(globals_[pool] * np.exp(LOG_UNIT * value))
    for pool, names in members.items():
        for name in names:
            rows[name]["link"] = [float(value) for value in np.asarray(starts[name]) + moves[pool] * paired(name)[1]]
    return rows, weights


def offsets(unknowns, entries):
    """Each group end's move off MyoFullBody's own centre ({centre: [3]}, metres in its body's frame, source model)."""
    found = {}
    for value, (centre, kind, axis, _) in zip(unknowns, entries):
        if kind == "centre":
            found.setdefault(centre, [0.0, 0.0, 0.0])[axis] = LINK_UNIT * float(value)
    return found


def bounds(entries):
    """least_squares' bounds (lower, upper) in the unknowns' units: links within REACH, centres within END_REACH,
    weights within WEIGHT_REACH."""
    reach = {"link": REACH / LINK_UNIT, "centre": END_REACH / LINK_UNIT}
    reach = np.array([reach.get(kind, WEIGHT_REACH) for _, kind, _, _ in entries])
    return -reach, reach


def prior(unknowns, entries):
    """The prior's residuals: each link's move from its anatomical start and each centre's from MyoFullBody's own,
    over PRIOR."""
    return np.array([LINK_UNIT * value / PRIOR for value, (_, kind, _, _) in zip(unknowns, entries)
                     if kind in MOVES])


def labels(found):
    """One case's residual labels ([(kind, key)]) in a fixed order, from its measures (the harness's m.json)."""
    return ([("skin", key) for key in sorted(found["bones outside depth mm"])]
            + [("turn", key) for key in sorted(found["per group deg"])]
            + [("joint", key) for key in sorted(found["per joint mm"])])


def case_residuals(found):
    """One case's residuals: each region's bones' depth outside the skin (mm, root mean square: smooth where the share
    outside, the judged measure, is a step; #70, 2026-10-30), each group's turn error (deg, frozen table) and each
    joint's error (mm, times JOINT_SHARE) as the root mean square over frames (smooth where the reported median's middle
    frames swap under a step, 23 of 36 cases measured; #70, 2026-10-30), each over its SCALES unit and the square root
    of its kind's count, so each kind is its mean."""
    values = {"skin": found["bones outside depth mm"], "turn": found["per group rms deg"],
              "joint": found["per joint rms mm"]}
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
    the prior's rows (each link's and centre's own). A landmark or group end reaches the rows of the groups it reaches (`reached`) and their
    regions; a global weight every row; a trust no prior row."""
    links = [index for index, (_, kind, _, _) in enumerate(entries) if kind in MOVES]
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


def solved(residuals, entries, pattern, checkpoint, limit_seconds, every=None, start=None, many=None, exact=None,
           by_differences=()):
    """The one optimisation: least_squares over `residuals(unknowns)` (the cases' residuals then the prior's) from
    `start` (default: the checkpoint's best), its Jacobian by absolute steps of STEP over `pattern`'s column groups
    (`_differences`; every nudged set in one call of `many(sets)` when given, else one `residuals` each), every
    evaluation checkpointed; stopped when the objective settles or `limit_seconds` pass;
    `every` (iteration, unknowns) is called after each iteration (the check bodies' score, logged, never used to
    choose). `exact(unknowns)`, when given, is the Jacobian instead (`_adjoint.stacked_jacobian` over the bodies
    solved at `unknowns`); the differences stay the default and its check. With `exact`, the `by_differences`
    columns (level 1's centres, decided 2026-10-30) are differenced and the rest exact (`hybrid`). Returns scipy's
    result."""
    began, costs, last = time.time(), [], {}
    start = resumed(checkpoint, len(entries)) if start is None else start
    lower, upper = bounds(entries)
    chosen = list(by_differences) if exact else list(range(pattern.shape[1]))
    groups = chosen_groups(pattern, chosen)

    def evaluated(unknowns):
        found = residuals(unknowns)
        checkpointed(checkpoint, unknowns, 0.5 * float(found @ found), "evaluation")
        last.clear()
        last[np.asarray(unknowns, dtype=float).tobytes()] = found
        return found

    def batched(sets):
        founds = many(sets)
        for moved, found in zip(sets, founds):
            checkpointed(checkpoint, moved, 0.5 * float(found @ found), "evaluation")
        return founds

    def differenced(unknowns):
        if exact and not chosen:
            return exact(unknowns)
        found = last.get(np.asarray(unknowns, dtype=float).tobytes())
        found = evaluated(unknowns) if found is None else found
        columns = jacobian(batched if many else serially(evaluated), unknowns, found, pattern, groups,
                           signed_steps(unknowns, STEP, upper))
        return hybrid(exact(unknowns), columns, chosen) if exact else columns

    def iterated(intermediate_result):
        costs.append(float(intermediate_result.cost))
        checkpointed(checkpoint, intermediate_result.x, intermediate_result.cost, f"iteration {len(costs)}")
        if every:
            every(len(costs), intermediate_result.x)
        if settled(costs) or time.time() - began > limit_seconds:
            raise StopIteration

    return least_squares(evaluated, np.clip(start, lower, upper), jac=differenced, bounds=(lower, upper),
                         method="trf", x_scale=1.0, callback=iterated)


def whole(evaluate, check, entries, checkpoint, limit_seconds, start=None, every=3, evaluate_many=None):
    """Level 1 entire: `solved` over every tuning case at once, `evaluate(unknowns)` ({case: measures} of levels 2
    and 3 on every tuning body, the evaluation runner's) giving each evaluation's residuals with the prior
    (`evaluate_many(sets)`, when given, every nudged set of a Jacobian at once: [{case: measures}]), and
    `check(unknowns)` (the held-out bodies' score) logged every `every` iterations and at the end, never used to
    choose. Returns (scipy's result, [(iteration, check score)])."""
    start = resumed(checkpoint, len(entries)) if start is None else start
    first = evaluate(start)
    names = sorted(first)
    pattern = sparsity(entries, labels(first[names[0]]), len(names))
    kept = {start.tobytes(): first}
    checks = []

    def stacked(unknowns, found):
        return np.concatenate([case_residuals(found[case]) for case in names] + [prior(unknowns, entries)])

    def residuals(unknowns):
        return stacked(unknowns, kept.pop(np.asarray(unknowns, dtype=float).tobytes(), None) or evaluate(unknowns))

    def many(sets):
        return [stacked(moved, found) for moved, found in zip(sets, evaluate_many(sets))]

    def checked(iteration, unknowns):
        if iteration % every == 0:
            checks.append((iteration, check(unknowns)))
    result = solved(residuals, entries, pattern, checkpoint, limit_seconds, every=checked, start=start,
                    many=many if evaluate_many else None)
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
