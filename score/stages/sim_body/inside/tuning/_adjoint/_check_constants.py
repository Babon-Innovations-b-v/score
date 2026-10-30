"""The real body's level 2 constants on the tape, run in Newton's own Python (`python _check_constants.py <this folder>
<seeds root> <set folder> <out root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` (as
`_check_real.py`), `_real.taped_sites(..., constants=_real.level2_constants(...))` on the per-frame model at the
solved rows with the moves 0; prints JSON: the pose part of its gradient against the constant-free one (the largest
|difference| and the largest entry), and its constants' gradient on its `PICKED` largest entries against central
differences of the cost (0.5 |residuals|^2, float64 off the taped rows) at each of `STEPS` (m), the largest gap over
the largest entry; level 3 as `_bodies.level3_body` (outer theta = the site offsets' moves, then the moves): g_q,c
by `mixed` over the `PICKED` constants against the constants' gradient differenced over the `PICKED` largest free pose
entries of those columns (H's symmetry), the largest gap over the largest entry; g_q,theta on the picked free marks'
own site offsets against their g_q,c columns (a free mark's move is its site offset's move: the same column), the
largest gap over the largest entry; and the seconds."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from _bodies import Pinned, RootTurns, level3_body, pose_of  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit._card import _seeds  # noqa: E402

PICKED = 8
STEPS = (1e-3, 1e-4)
MIXED_STEP = 1e-4  # m on a constant, rad or m on a pose entry

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

couplings = _real.frame_couplings(clip, rows)
turns = RootTurns(pose, len(couplings[0]) // len(rows))
pinned = Pinned(turns.reduced(), _real.bound_held(clip, couplings, rows))
level3 = level3_body("heavy_kimodo", sites, turns, pinned, lambda theta: offsets + theta, len(offsets), len(rows))
from tuning._adjoint import mixed  # noqa: E402


def _laid(few):
    """Level 3's outer point (theta the site offsets' moves, then level 2's moves): zero but the picked constants at
    `few`."""
    moves = np.zeros(len(offsets) + sites.constants.size)
    moves[len(offsets) + picked] = few
    return moves


marks = [index for index, entry in enumerate(picked) if entry < 3 * constants[0].shape[1]]
offset_columns = [3 * int(constants[0][0][picked[index] // 3]) + picked[index] % 3 for index in marks]


def _offset_laid(few):
    """Level 3's outer point zero but the picked free marks' own site offsets (theta) at `few`."""
    moved = np.zeros(len(offsets) + sites.constants.size)
    moved[offset_columns] = few
    return moved


def constants_gradient(inner):
    """The constants' gradient at the chart point `inner`, the moves 0."""
    return sites.gradient(np.concatenate([turns.full(pinned.whole(inner)), np.zeros(sites.constants.size)]),
                          offsets)[len(pose):][picked]


cross = mixed(lambda inner, few: level3.gradient(inner, _laid(few)), level3.inner, np.zeros(PICKED), MIXED_STEP)
entries = np.argsort(-np.max(np.abs(np.where(pinned.held[:, None], 0.0, cross)), axis=1))[:PICKED]
transposed = []
for entry in entries:
    up, down = level3.inner.copy(), level3.inner.copy()
    up[entry] += MIXED_STEP
    down[entry] -= MIXED_STEP
    transposed.append((constants_gradient(up) - constants_gradient(down)) / (2 * MIXED_STEP))
by_theta = mixed(lambda inner, few: level3.gradient(inner, _offset_laid(few)), level3.inner,
                 np.zeros(len(marks)), MIXED_STEP)
theta_gap = float(np.max(np.abs(by_theta - cross[:, marks])) / np.max(np.abs(cross[:, marks])))
symmetry = float(np.max(np.abs(np.array(transposed) - cross[entries])) / np.max(np.abs(cross[entries])))
print(json.dumps({"cross shape": list(cross.shape), "cross largest": float(np.max(np.abs(cross[entries]))),
                  "cross symmetry": symmetry, "theta marks": len(marks), "theta gap": theta_gap, "cross held most": float(np.max(np.abs(cross[pinned.held]))),
                  "pose most": float(np.max(np.abs(found[:len(pose)] - without))),
                  "pose largest": float(np.max(np.abs(without))), "constants": int(sites.constants.size),
                  "free marks": int(constants[0].shape[1]), "inside joints": int(constants[1].shape[1]),
                  "constants largest": float(np.max(np.abs(moves))), "picked": picked.tolist(),
                  "gap over largest": gaps, "seconds": time.time() - began}))
