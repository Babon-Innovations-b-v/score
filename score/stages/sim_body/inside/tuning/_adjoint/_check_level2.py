"""Level 2's stationarity check on one real body, run in Newton's own Python (`python _check_level2.py <this folder>
<set folder> <out root> <case>=<job.json> ...`): the set's table.json, weights.json and rest.json copied into <out root>,
level 2 solved by `_real.level2_solved` (its angles kept), the told unknowns `kept` from the exact host Jacobian at the
solve's start (as `fit/_constants.staged` reads them), and `_level2.level2_body` built on `_real.problem_at` at the
solved point; prints JSON: the sampled frames, width, constant slots, pinned entries, the pinned Body's largest gradient
entry at the solve ("solved most") against the same at the start ("start most"), and the seconds."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from tuning._adjoint import gradient_norm  # noqa: E402
from tuning._adjoint._level2 import level2_body, pinned_mask  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit import sampled_targets  # noqa: E402
from fit._card._level2 import jacobian  # noqa: E402
from fit._constants import INSIDE, Problem, told  # noqa: E402

folder, out = (pathlib.Path(arg) for arg in sys.argv[2:4])
cases = dict(given.split("=", 1) for given in sys.argv[4:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
table, weights = (json.loads((out / name).read_text()) for name in ("table.json", "weights.json"))
began, saved = time.time(), _card_batch.Saved()
fitting, recordings = _card_batch.body_unfitted(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
turns, points, lengths = sampled_targets(recordings)
path, constants, angles = _real.level2_solved(fitting, turns, points, lengths)
first = Problem(fitting, path, turns, points, fitting.neutral(), _real.level2_free(fitting))
low, high = first.bounds()
begin = np.clip(first.start(), np.where(np.isfinite(low), low + INSIDE, low),
                np.where(np.isfinite(high), high - INSIDE, high))
kept = told(first, jacobian(first, begin))
at = _real.problem_at(lambda outer: (table, weights), out, cases, saved, angles, constants)
outer = np.zeros(0)
solved = level2_body(at, jacobian, at(outer).start(), kept, outer)
started = level2_body(lambda moved: first, jacobian, begin, kept, outer)
print(json.dumps({"frames": solved.frames, "width": solved.pose_size, "slots": len(first.slots),
                  "pinned": int(pinned_mask(first, at(outer).start(), kept).sum()),
                  "solved most": gradient_norm(solved.gradient, solved.inner, outer),
                  "start most": gradient_norm(started.gradient, started.inner, outer),
                  "seconds": round(time.time() - began, 1)}))
