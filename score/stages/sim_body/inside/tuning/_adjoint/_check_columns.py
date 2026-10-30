"""`adjoint_rows` with EVERY level 1 column on one real body, timed, run in Newton's own Python (`python
_check_columns.py <this folder> <seeds root> <set folder> <out root> <npz> <case>=<job.json> ...`): at the base set,
level 3 on `taped_sites(fitting=, constants=)` with placed(theta) = trusted_outer + `picked_columns(ends=ends_of(...))`
@ theta over every entry of `tuning.layout`, level 2 on `_real.problem_at` over every entry; the steps of
`adjoint_rows` run one by one so each is timed: factor (`arrow_hessian` on both levels), solves (`schur_solve`) and
taping (R_q, R_c rows; `products` and level 2's transposed mixed term). Prints one JSON line a step as it ends, then
the result: the rows x columns block's shape, its largest entry and the seconds; the block is saved to <npz>."""
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
from _bodies import Pinned, RootTurns, level3_body, pose_of  # noqa: E402
from _measures import TapedMeasures  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit import sampled_targets  # noqa: E402
from fit._card._level2 import jacobian  # noqa: E402
from fit._constants import INSIDE, Problem, told  # noqa: E402
from tuning._adjoint import arrow_hessian, case_rows, schur_solve, transposed_mixed  # noqa: E402
from tuning._adjoint._level2 import level2_body  # noqa: E402
from tuning._adjoint._outer import picked_columns  # noqa: E402

STEPS = (1e-4, 1e-3)  # as `_check_motion.py`
seeds_root, folder, out, saved_to = (pathlib.Path(arg) for arg in sys.argv[2:6])
cases = dict(given.split("=", 1) for given in sys.argv[6:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
table, weights = (json.loads((out / name).read_text()) for name in ("table.json", "weights.json"))
entries = tuning.layout(table, held=landmarks.HELD, joints=set())
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
    rebuilt = _real.problem_at(applied, out, cases, saved, angles, constants)
    at = lambda outer: problem if not np.any(outer) else rebuilt(outer)  # noqa: E731
    return level2_body(at, jacobian, problem.start(), kept, np.zeros(len(entries)))


def timed(name, work):
    """`work()`'s result, its seconds kept under `name` and printed as one JSON line."""
    start = time.time()
    result = work()
    seconds[name] = seconds.get(name, 0.0) + time.time() - start
    print(json.dumps({"step": name, "seconds": round(time.time() - start, 2)}), flush=True)
    return result


def factored_solve(body, outer, right, step):
    """H^-T `right` at `body`'s optimum, the factor and the solve timed apart."""
    blocks, couplings, corner = timed(f"factor {body.name}", lambda: arrow_hessian(
        body.gradient, body.inner, outer, body.frames, body.pose_size, step))
    return timed(f"solve {body.name}", lambda: schur_solve(blocks.transpose(0, 2, 1), couplings, corner, right))


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
by_poses = timed("taping R_q", lambda: pinned.rows(turns.pulled_rows(turns.reduced(), case_rows(
    *measures.measured(inner, trusted), frames=len(rows))[1])))
by_constants = timed("taping R_c", lambda: case_rows(*measures.constant_measured(inner, trusted))[1])
level2 = timed("level 2 build", lambda: level2_at_base())
solved = level2.inner[level2.frames * level2.pose_size:]
moved = np.zeros(len(entries))
moved[0] = STEPS[1]
timed("one level 2 rebuild and gradient", lambda: level2.gradient(level2.inner, moved))
level3 = level3_body("level3", sites, turns, pinned, lambda theta: trusted + columns @ theta, len(entries),
                     len(rows), columns=columns)
joined = np.concatenate([np.zeros(len(entries)), np.zeros(solved.size)])
lifted = factored_solve(level3, joined, np.asarray(by_poses, dtype=float).T, STEPS[0])
both = np.hstack([np.zeros((len(by_poses), len(entries))), by_constants]) - timed(
    "taping level 3 products", lambda: transposed_mixed(level3, lifted, joined, STEPS[1]))
right = np.zeros((len(level2.inner), len(both)))
right[level2.frames * level2.pose_size:] = both[:, len(entries):].T
lowered = factored_solve(level2, np.zeros(len(entries)), right, STEPS[0])
block = both[:, :len(entries)] - timed("taping level 2 mixed", lambda: transposed_mixed(
    level2, lowered, np.zeros(len(entries)), STEPS[1]))
np.savez(saved_to, block=block, entries=np.array([json.dumps(list(map(str, entry))) for entry in entries]))
print(json.dumps({"shape": list(block.shape), "largest": float(np.abs(block).max()),
                  "finite": bool(np.isfinite(block).all()), "seconds": seconds, "total": time.time() - began}))
