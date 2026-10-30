"""`adjoint_rows` with EVERY level 1 column on one real body, timed, run in Newton's own Python (`python
_check_columns.py <this folder> <seeds root> <set folder> <out root> <npz> <case>=<job.json> ...`): at the base set,
level 3 on `taped_sites(fitting=, constants=)` with placed(theta) = trusted_outer + `picked_columns(ends=ends_of(...))`
@ theta over every entry of `tuning.layout(ends=)` (as `evaluation/level1.py`: 263 on depth1, 63 of them centres),
level 2 on `_real.problem_at` over every entry; the steps of `adjoint_rows` run one by one so each is timed: factor
(`arrow_hessian` on both levels), solves (`schur_solve`) and taping (R_q, R_c rows; `products` and level 2's
transposed mixed term). Prints one JSON line a step as it ends, then the result: the rows x columns block's shape, its
largest entry and the seconds; the block, R_theta (direct) and the level-3 term alone (level3; block - level3 is level 2's) are saved to <npz>."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
import landmarks  # noqa: E402
import tuning  # noqa: E402
from bone_groups import groups  # noqa: E402
from _bodies import Pinned, RootTurns, level3_body, pose_of  # noqa: E402
from _measures import TapedMeasures  # noqa: E402
from _taped import turned_offsets  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit import sampled_targets  # noqa: E402
from fit._card._level2 import jacobian  # noqa: E402
from fit._constants import INSIDE, Problem, told  # noqa: E402
from tuning._adjoint import arrow_hessian, case_rows, schur_solve, transposed_mixed  # noqa: E402
from tuning._adjoint._level2 import (goal_weights, level2_arrow, level2_body, sited_problem_at,  # noqa: E402
                                     turned_frame_sites)
from tuning._adjoint._outer import picked_columns  # noqa: E402

STEPS = (1e-4, 1e-3)  # as `_check_motion.py`
seeds_root, folder, out, saved_to = (pathlib.Path(arg) for arg in sys.argv[2:6])
cases = dict(given.split("=", 1) for given in sys.argv[6:] if not given.startswith("--"))
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
table, weights = (json.loads((out / name).read_text()) for name in ("table.json", "weights.json"))
entries = tuning.layout(table, held=landmarks.HELD, joints=set(),
                        ends=tuning.ended(groups(), landmarks.MIDDLE_CENTRES))
starts = {name: row["link"] for name, row in table.items()}
saved, seconds, began = _card_batch.Saved(), {}, time.time()


def applied(outer):
    """The set's (table rows, weights) at level 1's point `outer` over every entry."""
    return tuning.applied(np.asarray(outer, dtype=float), entries, starts, table, weights)


def measures_on(clip, sites):
    """`TapedMeasures` on `sites` with the base set's SOMA parts (as `_check_chained.py`)."""
    scales, segments, worlds, rig = _real.soma_of(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                                  saved)
    return TapedMeasures(sites, _real.joint_parts(clip, scales, segments, worlds), __import__("model").TO_OWN,
                         _real.turn_groups(clip, segments, worlds), _real.skin_parts(clip, rig, segments, worlds))


def level2_at_base():
    """Level 2's Body at the base set over every entry (as `_check_chained.py`'s, `_real.problem_at` off the base)."""
    fitting, recordings = _card_batch.body_unfitted(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                                    saved)
    path, constants, angles = _real.level2_solved(fitting, *sampled_targets(recordings))
    turns, points, _ = sampled_targets(recordings)
    first = Problem(fitting, path, turns, points, fitting.neutral(), _real.level2_free(fitting))
    low, high = first.bounds()
    begin = np.clip(first.start(), np.where(np.isfinite(low), low + INSIDE, low),
                    np.where(np.isfinite(high), high - INSIDE, high))
    kept = told(first, jacobian(first, begin))
    problem = Problem(fitting, angles, turns, points, constants, _real.level2_free(fitting))
    if problem.fitting.marks != names:
        raise ValueError("level 2's marks are not level 3's place sites in order")
    ends = sites.ends or 0
    base_costs = goal_weights(trusted[3 * len(names):], ends)
    print(json.dumps({"base costs gap": float(np.abs(base_costs - problem.costs[1]).max())}), flush=True)
    print(json.dumps(moved_site_rows(columns, len(names), problem.free)), flush=True)
    rebuilt = _real.problem_at(applied, out, cases, saved, angles, constants)
    sited = sited_problem_at(problem, columns, trusted, ends)
    return sited, rebuilt, level2_body(sited, jacobian, problem.start(), kept, np.zeros(len(entries))), kept


def moved_site_rows(columns, marks, free):
    """How many of level 3's outer rows level 1 moves (a non-zero row of `columns`): the site coordinates of the free
    marks, of the fixed marks, and the trusts and globals after them (level 2's mixed term's differencing calls)."""
    moved = np.abs(columns).max(axis=1) > 0
    on_free = np.zeros(3 * marks, dtype=bool)
    on_free[(3 * np.asarray(free, dtype=int)[:, None] + np.arange(3)).ravel()] = True
    sited = moved[:3 * marks]
    return {"moved site rows free": int((sited & on_free).sum()), "moved site rows fixed": int((sited & ~on_free).sum()),
            "moved tail rows": int(moved[3 * marks:].sum()), "entries": int(columns.shape[1])}


def sited_gaps(sited, rebuilt, unknowns, picks):
    """The largest gap, over `picks`' entries moved by STEPS[1] alone, between level 2's J^T r change off the Problem
    moved in place (`sited`) and off rebuilt Problems (`rebuilt`), over the rebuilt change's largest entry."""
    def change(problem_at, pick):
        """J^T r at `unknowns` with entry `pick` moved, less at the base point."""
        moved = np.zeros(len(entries))
        moved[pick] = STEPS[1]
        found = [np.asarray(jacobian(problem, unknowns).T @ problem.residuals(unknowns)).ravel()
                 for problem in map(problem_at, (moved, 0 * moved))]  # each read before the next move (one Problem)
        return found[0] - found[1]
    gaps = {}
    for pick in picks:
        again = change(rebuilt, pick)
        gaps[str(entries[pick])] = float(np.abs(change(sited, pick) - again).max() / max(np.abs(again).max(), 1e-30))
    return gaps


def direct_rows(measures, pose_parts, frames):
    """R_theta: the case rows' derivative over level 1's entries at the base pose, its joints' direct partial alone
    (a centre entry moves the measure's joint centre, `_real.centre_columns`); the turns' and skins' read no entry."""
    joints, turns, skins = pose_parts
    moved = np.einsum("pij,pje->pie", measures.part_turns(), _real.centre_columns(segments, frames, entries, scales))
    slotted = np.zeros((len(measures.joint_names) * frames, 3, len(entries)))
    np.add.at(slotted, measures.part_slot.numpy(), moved)
    by_joint = slotted.reshape(len(measures.joint_names), frames, 3, len(entries))
    return case_rows({name: (joints[name][0], by_joint[index]) for index, name in enumerate(measures.joint_names)},
                     {name: (values, np.zeros((frames, len(entries)))) for name, (values, _) in turns.items()},
                     {name: (values, np.zeros((len(values), len(entries)))) for name, (values, _, _) in skins.items()})[1]


def group_turned_gradient(level3, sites, groups_of_rows, outer, moves):
    """Level 3's gradient at its optimum with every turn row of a group in `moves` ({group: body-side rad}) turned."""
    rows = {row: moves[group] for row, group in enumerate(groups_of_rows) if group in moves}
    return turned_offsets(sites, rows, lambda: level3.gradient(level3.inner, outer))


def table_mixed(turned_gradient, weights, dtable, step):
    """weights^T g_z,centre along the recalibrated TABLE (`dtable`, b4/table/dtable_vec's 'body' rad/m, times
    LINK_UNIT): per centre column that turns a calibration site, the level's gradient (`turned_gradient(moves)`, moves
    {group: body-side rad}) central-differenced by `step` units of the site turn; (rows, entries), zero elsewhere."""
    found = np.zeros((weights.shape[1], len(entries)))
    for column, (pool, kind, axis, _) in enumerate(entries):
        moved = dtable["columns"].get(f"{pool} {'xyz'[axis]}", {}) if kind == "centre" else {}
        moves = {group: tuning.LINK_UNIT * step * np.asarray(sides["body"]) for group, sides in moved.items()}
        if moves:
            ahead = turned_gradient(moves)
            behind = turned_gradient({group: -turn for group, turn in moves.items()})
            found[:, column] = weights.T @ ((ahead - behind) / (2 * step))
    return found


def timed(name, work):
    """`work()`'s result, its seconds kept under `name` and printed as one JSON line."""
    start = time.time()
    result = work()
    seconds[name] = seconds.get(name, 0.0) + time.time() - start
    print(json.dumps({"step": name, "seconds": round(time.time() - start, 2)}), flush=True)
    return result


def factored_solve(body, factor, right):
    """(H^-T `right` at `body`'s optimum, H's arrow) off `factor()` (its arrow blocks), the factor and the solve timed
    apart."""
    blocks, couplings, corner = timed(f"factor {body.name}", factor)
    return timed(f"solve {body.name}", lambda: schur_solve(blocks.transpose(0, 2, 1), couplings, corner, right)), (
        blocks, couplings, corner)


def differenced_arrow(body, outer, step):
    """`arrow_hessian` of `body`'s gradient at its optimum."""
    return lambda: arrow_hessian(body.gradient, body.inner, outer, body.frames, body.pose_size, step)


def level2_factor(problem, solved, kept, step):
    """`level2_arrow` of level 2's Problem at its solve, the inside joints' slots differenced."""
    return lambda: level2_arrow(problem, jacobian, solved, kept, np.arange(3 * len(problem.free), len(problem.slots)),
                                step)


clip, fitting, targets, path = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
rows, _ = _real.solved_rows(clip, targets, {case: __import__("fit._card._seeds", fromlist=["first"]).first(
    seeds_root, case) for case in cases})
model = _real.per_frame_model(fitting, path, len(rows))
sites, trusted = _real.taped_sites(clip, model, rows, targets, fitting=fitting,
                                   constants=_real.level2_constants(fitting, model, len(rows)))
scales, segments, _, _ = _real.soma_of(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
names = [clip.mjm.site(int(site)).name.removeprefix("mark:") for site in clip.place_sites]
every = list(range(len(entries)))
columns = picked_columns(names, every, entries, table, weights, ends=_real.ends_of(path, scales, segments))
measures = measures_on(clip, sites)
pose = np.asarray(pose_of(_real.frame_couplings(clip, rows), rows), dtype=np.float64)
inner = np.concatenate([pose, np.zeros(sites.constants.size)])
turns = RootTurns(pose, len(_real.frame_couplings(clip, rows)[0]) // len(rows))
pinned = Pinned(turns.reduced(), _real.bound_held(clip, _real.frame_couplings(clip, rows), rows))
pose_parts, constant_parts = timed("taping R_q and R_c", lambda: measures.joined_measured(inner, trusted))
by_poses = pinned.rows(turns.pulled_rows(turns.reduced(), case_rows(*pose_parts, frames=len(rows))[1]))
values, by_constants = case_rows(*constant_parts)
sited, rebuilt, level2, kept = timed("level 2 build", lambda: level2_at_base())
solved = level2.inner[level2.frames * level2.pose_size:]
print(json.dumps({"sited vs rebuilt": timed("sited check", lambda: sited_gaps(
    sited, rebuilt, sited(np.zeros(len(entries))).start(), (0, len(entries) // 2, len(entries) - 1)))}), flush=True)
level3 = level3_body("level3", sites, turns, pinned, lambda theta: trusted + columns @ theta, len(entries),
                     len(rows), columns=columns, step=STEPS[1])  # float32 products: 1e-4 left 2-3 %, 1e-3 0.4-0.6 %
joined = np.concatenate([np.zeros(len(entries)), np.zeros(solved.size)])
lifted, _ = factored_solve(level3, differenced_arrow(level3, joined, STEPS[0]), np.asarray(by_poses, dtype=float).T)
direct = timed("direct rows", lambda: direct_rows(measures, pose_parts, len(rows)))
both = np.hstack([direct, by_constants]) - timed(
    "taping level 3 products", lambda: transposed_mixed(level3, lifted, joined, STEPS[1]))
if any(given.startswith("--dtable=") for given in sys.argv):
    dtable = json.loads(pathlib.Path(next(given for given in sys.argv if given.startswith("--dtable="))[9:]).read_text())
    groups_of_rows = [clip.mjm.site(int(site)).name.removeprefix("fit:") for site in clip.frame_sites] * len(rows)
    tabled = timed("level 3 table mixed", lambda: table_mixed(
        lambda moves: group_turned_gradient(level3, sites, groups_of_rows, joined, moves), lifted, dtable, 0.1))
    np.save(saved_to.with_suffix(".table.npy"), tabled)
    both[:, :len(entries)] -= tabled
right = np.zeros((len(level2.inner), len(both)))
right[level2.frames * level2.pose_size:] = both[:, len(entries):].T
base = sited(np.zeros(len(entries)))
lowered, arrow = factored_solve(level2, level2_factor(base, base.start(), kept, STEPS[0]), right)
level2 = level2_body(sited, jacobian, base.start(), kept, np.zeros(len(entries)), sited=(columns, STEPS[1], arrow))
if "--against-differences" in sys.argv:
    wanted = timed("factor level 2 differenced", differenced_arrow(level2, np.zeros(len(entries)), STEPS[0]))
    found = level2_factor(base, base.start(), kept, STEPS[0])()
    print(json.dumps({"arrow gaps": [float(np.abs(got - want).max() / np.abs(want).max())
                                     for got, want in zip(found, wanted)]}), flush=True)
block = both[:, :len(entries)] - timed("taping level 2 mixed", lambda: transposed_mixed(
    level2, lowered, np.zeros(len(entries)), STEPS[1]))
if any(given.startswith("--dtable=") for given in sys.argv):
    tabled2 = timed("level 2 table mixed", lambda: table_mixed(lambda moves: turned_frame_sites(
        base.fitting, moves, lambda: level2.gradient(level2.inner, np.zeros(len(entries)))), lowered, dtable, 0.1))
    np.save(saved_to.with_suffix(".table2.npy"), tabled2)
    block -= tabled2
np.savez(saved_to, block=block, rows=values, direct=direct, level3=both[:, :len(entries)], entries=np.array([json.dumps(list(map(str, entry))) for entry in entries]))
print(json.dumps({"shape": list(block.shape), "largest": float(np.abs(block).max()),
                  "finite": bool(np.isfinite(block).all()), "seconds": seconds, "total": time.time() - began}))
