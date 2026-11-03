"""Level 1 of the fit (#70; CONTEXT.md "landmark set"; numpy and scipy): ONE joint optimisation of the landmark set
over every tuning body at once, never a round of pieces judged alone. The unknowns (`layout`): each landmark's link
on its bone (a joint-defining one only across the bone's long axis), its trust (log), each group end's centre on
MyoFullBody (its offset in its body's frame off the model's own: a left and right end one mirrored unknown, a middle
end's on the mid-plane, `centre_members`; 2026-11-01, the sides were poorly told apart: one knee on its bound, the
stage's own tests ask mirror symmetry within 2 mm and no sideways turn of a middle group), and the two global weights
(the markers' goal against the turns', a group end's weight); a left and a right landmark share their unknowns, the
right mirrored (`paired`); each segment end's shift (`_ends`, owner 2026-11-03: the group ends' markers shifted on
their holder bodies, never MyoFullBody's joint centres moved). The residuals (`case_residuals`, weighed by `weights`)
are the owner's two terms (2026-11-03: "aim at bones in skin, and segment orientation to bone group orientation
error, aswell"), from levels 2 and 3 run on each tuning case: each region's bones' depth outside SOMA's skin (true
value 0) and each SOMA segment's turn error against its bone group, each term over its own value at the start and the
two weighed alike; joint centre error is reported only (owner, 2026-11-01: "why should joint centres be a target at
all? we know at ultra accuracy they will be wrong"); never a landmark distance the solver pulls on. A prior (`prior`) pulls each link toward its anatomical start, each centre toward the model's own and each end shift toward its start. scipy's least_squares (trf) runs it
with finite differences of ABSOLUTE steps (`_differences`, STEP of each unknown's units) over a sparse pattern's column
groups (`sparsity`: a landmark reaches its own group and the groups next to it, a global weight everything), every
evaluation checkpointed (`checkpointed`) and the run stopped when the objective
settles (`settled`) or a wall-clock limit passes. `rewritten` writes the result into the landmark table's source."""
import json
import time

import numpy as np
from scipy.optimize import least_squares

from tuning._differences import chosen_groups, hybrid, jacobian, serially, signed_steps
from tuning._ends import SIDEWAYS, mirrored_starts, segment_ends, shifts  # noqa: F401  (level 1's ends, read as tuning.<name>)
from tuning._rewriting import centres_rewritten, relative, rewritten, weight_rewritten  # noqa: F401  (level 1's writers, read as tuning.<name>)

LONG_AXIS = 1  # MyoFullBody's bodies run along their own y (OpenSim's convention): the axis a joint link keeps
MIRROR = np.array([1.0, 1.0, -1.0])  # a right landmark's body-frame vector as its left one's
LATERAL = 2  # the body-frame axis MIRROR flips: a middle end's centre never moves along it (the mid-plane)
LINK_UNIT = 0.005  # metres per unknown's unit: finite-difference steps and bounds are in these units
LOG_UNIT = 0.25  # natural-log units per unknown's unit, for trusts and global weights
REACH = 0.030  # metres: no link ends further than this from its anatomical start (the bound)
END_REACH = 0.040  # metres: no group end's centre moves further than this from MyoFullBody's own (the bound)
PRIOR = 0.010  # metres: the anatomical start's spread (the prior's residual is the offset over it)
STEP = 0.4  # unknown's units: the ABSOLUTE finite-difference step (2 mm of link or centre, 0.1 of log weight)
WEIGHT_REACH = 3.0  # unknown's units of log either way a trust or global weight may move (e^0.75: about 2x)
TERMS = ("skin", "turn")  # the objective's two terms (owner, 2026-11-03), each over its own value at the start, weighed
# alike: a stated design choice, never tuned to pass a check
GLOBALS = ("marker goal", "end weight")
MOVES = ("link", "centre", "end")  # the unknowns that are a place (metres), each with its prior row
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


def centre_members(pool):
    """The group ends one centre unknown moves and each one's factor ([(centre, [3])]): a left end and its right twin
    mirrored, a middle end alone."""
    if pool.endswith("_l"):
        return [(pool, np.ones(3)), (pool[:-2] + "_r", MIRROR)]
    return [(pool, np.ones(3))]


def ended(groups, middles):
    """Each group end's MyoFullBody centre and the bone groups it starts ({centre: [segment]}): every group's start
    centre (`bone_groups.groups()`), a middle of two (`landmarks.MIDDLE_CENTRES`) as its two parts."""
    found = {}
    for segment, (_, (start, _), _, _) in groups.items():
        for part in middles.get(start, (start,)):
            found.setdefault(part, set()).add(segment)
    return {centre: sorted(segments) for centre, segments in found.items()}


def layout(table, held, joints, ends=None, shifted=None):
    """The unknowns: [(pool, kind, axes or None, segments)], kind "link" (axes: the body-frame components it moves)
    or "trust", then each group end's centre ("centre": a left and right pair one, under the left's name, its three
    body-frame axes; a middle end's two, off LATERAL), then each segment end's shift ("end": a left and right pair one,
    under the left's name, the person's frame's three axes; a middle end's two, off `SIDEWAYS`; `_ends`), then each
    global weight ("global", None, None). `table` {name: row} (the harness's rows: "segment", "solver"), `held` names
    whose links stay, `joints` the joint-defining names, `ends` `ended`'s, `shifted` `segment_ends`'."""
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
    centres = {}
    for centre, segments in (ends or {}).items():
        centres.setdefault(paired(centre)[0], set()).update(segments)
    out.extend((centre, "centre", axis, sorted(segments)) for centre, segments in centres.items()
               for axis in range(3) if centre.endswith("_l") or axis != LATERAL)
    pooled = {}
    for end, segments in (shifted or {}).items():
        pooled.setdefault(paired(end)[0], set()).update(side for segment in segments for side in mirrored(segment))
    out.extend((end, "end", axis, sorted(segments)) for end, segments in pooled.items()
               for axis in range(3) if end.endswith("_l") or axis != SIDEWAYS)
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
    """Each group end's move off MyoFullBody's own centre ({centre: [3]}, metres in its body's frame, source model),
    a right end its left one's mirrored."""
    found = {}
    for value, (pool, kind, axis, _) in zip(unknowns, entries):
        if kind == "centre":
            for centre, factor in centre_members(pool):
                found.setdefault(centre, [0.0, 0.0, 0.0])[axis] = LINK_UNIT * float(value) * float(factor[axis])
    return found


def bounds(entries):
    """least_squares' bounds (lower, upper) in the unknowns' units: links within REACH, centres and end shifts within
    END_REACH, weights within WEIGHT_REACH."""
    reach = {"link": REACH / LINK_UNIT, "centre": END_REACH / LINK_UNIT, "end": END_REACH / LINK_UNIT}
    reach = np.array([reach.get(kind, WEIGHT_REACH) for _, kind, _, _ in entries])
    return -reach, reach


def prior(unknowns, entries):
    """The prior's residuals: each link's move from its anatomical start, each centre's from MyoFullBody's own and
    each end shift's from its start (the shift read at rest in SOMA's skin), over PRIOR."""
    return np.array([LINK_UNIT * value / PRIOR for value, (_, kind, _, _) in zip(unknowns, entries)
                     if kind in MOVES])


def labels(found):
    """One case's residual labels ([(kind, key)]) in a fixed order, from its measures (the harness's m.json): each skin
    region's, then each SOMA segment's turn against its bone group."""
    return ([("skin", key) for key in sorted(found["bones outside depth mm"])]
            + [("turn", key) for key in sorted(found["per group rms deg"])])


def case_residuals(found):
    """One case's raw rows in `labels`' order: each region's bones' depth outside SOMA's skin (mm, root mean square:
    smooth where the share outside, the judged measure, is a step; #70, 2026-10-30) and each segment's turn error
    against its bone group (deg, root mean square over frames, on the table the stage builds its follows targets
    from: `evaluation._measure.judged_turn`). `weights` scales them into the objective."""
    values = {"skin": found["bones outside depth mm"], "turn": found["per group rms deg"]}
    return np.array([values[kind][key] for kind, key in labels(found)], dtype=float)


def weights(start):
    """Each case's row weights ({case: [rows]}) from the start point's measures (`start` {case: measures}): the owner's
    two terms (2026-11-03: "aim at bones in skin, and segment orientation to bone group orientation error, aswell"),
    the bones outside the skin and the turns, each its rows' mean square over every case holding it divided by that
    mean square at the start, so each term is 1 there and they weigh alike (`TERMS`). A row's weight is
    1 / sqrt(rows of its kind in its case * cases holding the kind * the kind's start mean square)."""
    shares = {kind: [] for kind in TERMS}
    for found in start.values():
        rows = case_residuals(found)
        for kind in TERMS:
            mine = rows[[index for index, (label, _) in enumerate(labels(found)) if label == kind]]
            if mine.size:
                shares[kind].append(float(np.mean(np.square(mine))))
    means = {kind: float(np.mean(values)) if values else 1.0 for kind, values in shares.items()}
    found_weights = {}
    for case, found in start.items():
        kinds = [label for label, _ in labels(found)]
        found_weights[case] = np.array([1.0 / np.sqrt(kinds.count(kind) * len(shares[kind]) * means[kind])
                                        if means[kind] > 0 else 0.0 for kind in kinds])
    return found_weights


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
           by_differences=(), paused=lambda: 0.0):
    """The one optimisation: least_squares over `residuals(unknowns)` (the cases' residuals then the prior's) from
    `start` (default: the checkpoint's best), its Jacobian by absolute steps of STEP over `pattern`'s column groups
    (`_differences`; every nudged set in one call of `many(sets)` when given, else one `residuals` each), every
    evaluation checkpointed; stopped when the objective settles or `limit_seconds` pass, less `paused()` (the
    seconds its evaluations waited for the card, `evaluation.CardShares.waited`: a wait is not level 1's time);
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
        if np.all(np.isfinite(found)):  # a refused trial (infinite) is no point to resume from
            checkpointed(checkpoint, unknowns, 0.5 * float(found @ found), "evaluation")
        last.clear()
        last[np.asarray(unknowns, dtype=float).tobytes()] = found
        return found

    def batched(sets):
        founds = many(sets)
        for moved, found in zip(sets, founds):
            if found is not None:  # a set level 3 did not stop on (`_differences.jacobian` steps it the other way)
                checkpointed(checkpoint, moved, 0.5 * float(found @ found), "evaluation")
        return founds

    def differenced(unknowns):
        if exact and not chosen:
            return exact(unknowns)
        found = last.get(np.asarray(unknowns, dtype=float).tobytes())
        found = evaluated(unknowns) if found is None else found
        columns = jacobian(batched if many else serially(evaluated), unknowns, found, pattern, groups,
                           signed_steps(unknowns, STEP, upper), (lower, upper))
        return hybrid(exact(unknowns), columns, chosen) if exact else columns

    def iterated(intermediate_result):
        costs.append(float(intermediate_result.cost))
        checkpointed(checkpoint, intermediate_result.x, intermediate_result.cost, f"iteration {len(costs)}")
        if every:
            every(len(costs), intermediate_result.x)
        if settled(costs) or time.time() - began - paused() > limit_seconds:
            raise StopIteration

    # x_scale "jac": the unknowns mix units (links, trusts, weights, centres) and start at 0, where x_scale 1.0 sets
    # trf's first trust radius to 1 (l1d, 2026-10-31: step 1 moved 263 unknowns a norm of 1.13 and took the cost only
    # 621 -> 587, the step held by the radius, not the model)
    return least_squares(evaluated, np.clip(start, lower, upper), jac=differenced, bounds=(lower, upper),
                         method="trf", x_scale="jac", callback=iterated)


def whole(evaluate, check, entries, checkpoint, limit_seconds, start=None, every=3, evaluate_many=None,
          exact=None, by_differences=(), paused=lambda: 0.0):
    """Level 1 entire: `solved` over every tuning case at once, `evaluate(unknowns)` ({case: measures} of levels 2
    and 3 on every tuning body, the evaluation runner's) giving each evaluation's residuals with the prior
    (`evaluate_many(sets)`, when given, every nudged set of a Jacobian at once: [{case: measures}]), and
    `evaluate` giving None (a trial point some body's level 3 did not stop on, `evaluation.read_back`) is refused:
    its residuals are infinite, so trf shrinks its trust region and steps again (scipy's own rule for a non-finite
    trial), never accepting it; the start itself must evaluate. Every case's rows are weighed by `weights` of the
    measures at level 1's start (every unknown 0; evaluated again when resuming from elsewhere, the store keeps it),
    so a resumed run weighs as the first did; `exact(unknowns)`'s rows are raw like `case_residuals`' and weighed the
    same. `check(unknowns)` (the held-out bodies' score) logged every `every` iterations and at the end, never used to
    choose; `exact`, `by_differences` and `paused` go to `solved` (level 1's hybrid Jacobian; the card waits left
    off its clock). Returns (scipy's result,
    [(iteration, check score)])."""
    start = resumed(checkpoint, len(entries)) if start is None else start
    first = evaluate(start)
    if first is None:
        raise RuntimeError("level 1's start did not evaluate: a body's level 3 did not stop on it")
    origin = first if not np.any(start) else evaluate(np.zeros(len(entries)))
    if origin is None:
        raise RuntimeError("level 1's start point did not evaluate: a body's level 3 did not stop on it")
    names = sorted(first)
    scaled = weights(origin)
    if sorted(scaled) != names:
        raise RuntimeError("level 1's start point and resumed point measured other cases")
    row_weights = np.concatenate([scaled[case] for case in names])
    pattern = sparsity(entries, sum((labels(first[name]) for name in names), []), 1)  # a clip with no unfolded
    # skin frame has no rows: its folds are SOMA's alone, so its rows stay none at every evaluation
    kept = {start.tobytes(): first}
    checks = []

    def stacked(unknowns, found):
        return np.concatenate([row_weights * np.concatenate([case_residuals(found[case]) for case in names]),
                               prior(unknowns, entries)])

    def weighed(unknowns):
        found = exact(unknowns)
        return np.concatenate([row_weights[:, None] * found[:len(row_weights)], found[len(row_weights):]])

    size = len(stacked(start, first))

    def residuals(unknowns):
        found = kept.pop(np.asarray(unknowns, dtype=float).tobytes(), None) or evaluate(unknowns)
        return np.full(size, np.inf) if found is None else stacked(unknowns, found)

    def many(sets):
        return [None if found is None else stacked(moved, found) for moved, found in zip(sets, evaluate_many(sets))]

    def checked(iteration, unknowns):
        if iteration % every == 0:
            checks.append((iteration, check(unknowns)))
    result = solved(residuals, entries, pattern, checkpoint, limit_seconds, every=checked, start=start,
                    many=many if evaluate_many else None, exact=weighed if exact else None, by_differences=by_differences,
                    paused=paused)
    checks.append(("end", check(result.x)))
    return result, checks

