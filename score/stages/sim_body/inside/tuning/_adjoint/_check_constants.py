"""The real body's level 2 constants on the tape, run in Newton's own Python (`python _check_constants.py <this folder>
<seeds root> <set folder> <out root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` (as
`_check_real.py`), `_real.taped_sites(..., constants=_real.level2_constants(...))` on the per-frame model at the
solved rows with the moves 0; prints JSON: the pose part of its gradient against the constant-free one (the largest
|difference| and the largest entry), and its constants' gradient on its `PICKED` largest entries against central
differences of the cost (0.5 |residuals|^2, float64 off the taped rows) at each of `STEPS` (m), the largest gap over
the largest entry; and the seconds."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from _bodies import pose_of  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit._card import _seeds  # noqa: E402

PICKED = 8
STEPS = (1e-3, 1e-4)

seeds_root, folder, out = (pathlib.Path(arg) for arg in sys.argv[2:5])
cases = dict(given.split("=", 1) for given in sys.argv[5:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
began = time.time()
clip, fitting, targets, path = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                            _card_batch.Saved())
rows, _ = _real.solved_rows(clip, targets, {case: _seeds.first(seeds_root, case) for case in cases})
model = _real.per_frame_model(fitting, path, len(rows))
plain, offsets = _real.taped_sites(clip, model, rows, targets)
constants = _real.level2_constants(fitting, model, len(rows))
sites, _ = _real.taped_sites(clip, model, rows, targets, constants=constants)
pose = np.asarray(pose_of(_real.frame_couplings(clip, rows), rows), dtype=np.float64)
inner = np.concatenate([pose, np.zeros(sites.constants.size)])
found = sites.gradient(inner, offsets)
without = plain.gradient(pose, offsets)


def cost(moved):
    """The level 3 cost at the solved pose with level 2's moves `moved`, float64 off the taped rows."""
    return 0.5 * float(np.sum(np.square(sites.residuals(np.concatenate([pose, moved]), offsets))))


moves = found[len(pose):]
picked = np.argsort(-np.abs(moves))[:PICKED]
gaps = {}
for step in STEPS:
    differenced = []
    for entry in picked:
        nudge = np.zeros(len(moves))
        nudge[entry] = step
        differenced.append((cost(nudge) - cost(-nudge)) / (2 * step))
    gaps[str(step)] = float(np.max(np.abs(np.array(differenced) - moves[picked])) / np.max(np.abs(moves)))
print(json.dumps({"pose most": float(np.max(np.abs(found[:len(pose)] - without))),
                  "pose largest": float(np.max(np.abs(without))), "constants": int(sites.constants.size),
                  "free marks": int(constants[0].shape[1]), "inside joints": int(constants[1].shape[1]),
                  "constants largest": float(np.max(np.abs(moves))), "picked": picked.tolist(),
                  "gap over largest": gaps, "seconds": time.time() - began}))
