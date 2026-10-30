"""Level 2's constant motion on one real body against settled re-solves, run in Newton's own Python (`python
_check_motion.py <this folder> <set folder> <out root> <step> [--entry=<index>] <case>=<job.json> ...`): the set's
table.json, weights.json and rest.json copied into <out root>; level 1's point bound to `tuning.layout`'s "marker goal",
or its entry <index> (every other entry held at its start) through `tuning.applied`; level 2 solved by `_real.level2_solved` (staged with its
float64 polish); dc/dtheta by `constant_motion` on `_level2.level2_body` at that solve (`kept` told at its start)
against central differences of level 2 re-solved at marker goal +-<step>, on the told, unpinned slots off their
MARK_MOST bounds; prints JSON: those slots, the free gradient at the base, the largest |difference|, the re-solved
column's largest entry, the slots over 2 % of it, the told slots at a bound or pinned (their largest re-solved and implicit move, and the
slots 0-2, the first free mark's x, y, z), the entry and the seconds."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
import tuning  # noqa: E402
from tuning._adjoint import constant_motion  # noqa: E402
from tuning._adjoint._level2 import level2_body, pinned_mask  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit import sampled_targets  # noqa: E402
from fit._card._level2 import jacobian  # noqa: E402
from fit._constants import INSIDE, MARK_MOST, Problem, off_bounds, told  # noqa: E402
import landmarks  # noqa: E402

BOUND_ROOM = 5e-4  # a slot within this of MARK_MOST counts as at its bound (its re-solve may sit on it)
folder, out = (pathlib.Path(arg) for arg in sys.argv[2:4])
step = float(sys.argv[4])
picks = [int(given.split("=", 1)[1]) for given in sys.argv[5:] if given.startswith("--entry=")]
cases = dict(given.split("=", 1) for given in sys.argv[5:] if not given.startswith("--entry="))
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
table, weights = (json.loads((out / name).read_text()) for name in ("table.json", "weights.json"))
starts = {name: row["link"] for name, row in table.items()}
entries = tuning.layout(table, held=landmarks.HELD, joints=set())
chosen = picks or [next(index for index, entry in enumerate(entries) if entry[:2] == ("marker goal", "global"))]


def applied(outer):
    """The set's (table rows, weights) with marker goal at `outer`, every other entry at its start."""
    unknowns = np.zeros(len(entries))
    unknowns[chosen] = outer
    return tuning.applied(unknowns, entries, starts, table, weights)


def solved_at(outer):
    """Level 2 re-solved from scratch at `outer` (the set written, the body read again): (fitting, recordings,
    (path, constants, angles))."""
    rows, moved = applied(outer)
    (out / "table.json").write_text(json.dumps(rows, indent=1))
    (out / "weights.json").write_text(json.dumps(moved))
    fitting, recordings = _card_batch.body_unfitted(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                                    saved)
    return fitting, recordings, _real.level2_solved(fitting, *sampled_targets(recordings))


began, saved = time.time(), _card_batch.Saved()
base = np.zeros(1)
fitting, recordings, (path, constants, angles) = solved_at(base)
turns, points, _ = sampled_targets(recordings)
first = Problem(fitting, path, turns, points, fitting.neutral(), _real.level2_free(fitting))
held = len(first.slots)
low, high = first.bounds()
begin = np.clip(first.start(), np.where(np.isfinite(low), low + INSIDE, low),
                np.where(np.isfinite(high), high - INSIDE, high))
kept = told(first, jacobian(first, begin))
problem = Problem(fitting, angles, turns, points, constants, _real.level2_free(fitting))  # the base solve's, not read again
rebuilt = _real.problem_at(applied, out, cases, saved, angles, constants)
at = lambda outer: problem if np.array_equal(outer, base) else rebuilt(outer)
settled = problem.start()
free = off_bounds(settled, kept, (low, high))
free_gradient = float(np.abs(jacobian(problem, settled)[:, free].T @ problem.residuals(settled)).max())
implicit = constant_motion(level2_body(at, jacobian, settled, kept, base), base, (1e-4, step), 1e-3)[:, 0]
pinned = pinned_mask(problem, settled, kept).astype(bool)[-held:]
told_slots = np.asarray(kept)[np.asarray(kept) < held]
off = told_slots[(np.abs(settled[told_slots]) < MARK_MOST - BOUND_ROOM) & ~pinned[told_slots]]
ends = [solved_at(base + sign * step)[2][1][first.slots] for sign in (1, -1)]
re_solved = (ends[0] - ends[1]) / (2 * step)
difference = np.abs(implicit[off] - re_solved[off])
top = float(np.abs(re_solved[off]).max())
bound = np.setdiff1d(told_slots, off)
print(json.dumps({"off": int(off.size), "free gradient": free_gradient, "most difference": float(difference.max()),
                  "top": top, "over 2 %": int((difference > 0.02 * top).sum()), "bound": int(bound.size),
                  "bound re-solved": float(np.abs(re_solved[bound]).max(initial=0.0)),
                  "bound implicit": float(np.abs(implicit[bound]).max(initial=0.0)),
                  "first mark re-solved": re_solved[:3].tolist(), "first mark implicit": implicit[:3].tolist(),
                  "first mark settled": settled[:3].tolist(), "entry": str(entries[chosen[0]][:3]),
                  "seconds": time.time() - began}))
