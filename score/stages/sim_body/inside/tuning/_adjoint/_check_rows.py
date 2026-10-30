"""R_c on the real body, run in Newton's own Python (`python _check_rows.py <this folder> <seeds root> <set folder>
<out root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` (as `_check_real.py`),
`TapedMeasures.constant_measured` on `_real.taped_sites(..., constants=_real.level2_constants(...))` at the solved
rows, the moves 0, through `case_rows` (no `frames`): its `PICKED` largest columns against central differences of
`case_rows`' values with level 2's moves stepped `STEP` (m) on each; prints JSON: the rows' shape, the largest gap
over the largest entry of those columns (medians' frames free to swap), the same gap with the per-frame measures'
differences put through `case_rows` at the taped medians' frames ("masked", the judged one), the per-frame gap with
its worst entries, and the seconds."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from _bodies import pose_of  # noqa: E402
from _measures import TapedMeasures  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit._card import _seeds  # noqa: E402
from tuning._adjoint import case_rows  # noqa: E402

PICKED = 3
STEP = 1e-4

seeds_root, folder, out = (pathlib.Path(arg) for arg in sys.argv[2:5])
cases = dict(given.split("=", 1) for given in sys.argv[5:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
began = time.time()
saved = _card_batch.Saved()
clip, fitting, targets, path = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
rows, _ = _real.solved_rows(clip, targets, {case: _seeds.first(seeds_root, case) for case in cases})
model = _real.per_frame_model(fitting, path, len(rows))
sites, offsets = _real.taped_sites(clip, model, rows, targets, constants=_real.level2_constants(fitting, model, len(rows)))
scales, segments, worlds, rig = _real.soma_of(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
measures = TapedMeasures(sites, _real.joint_parts(clip, scales, segments, worlds), __import__("model").TO_OWN,
                         _real.turn_groups(clip, segments, worlds), _real.skin_parts(clip, rig, segments, worlds))
pose = np.asarray(pose_of(_real.frame_couplings(clip, rows), rows), dtype=np.float64)
moves = np.zeros(sites.constants.size)
measured = measures.constant_measured(np.concatenate([pose, moves]), offsets)
_, constant_rows = case_rows(*measured)
raw_rows = np.concatenate([np.concatenate([rows.reshape(-1, rows.shape[-1]) for _, rows in part.values()])
                           for part in measured[:2]] + [np.concatenate([part[1] for part in measured[2].values()])])


def raw(moved):
    """Every per-frame measure (joint differences m, turn degrees, skin depths m) flat, in `raw_rows`' order."""
    measures._evaluate(np.concatenate([pose, moved]), offsets)
    return np.concatenate([measures.differences.numpy().astype(np.float64).ravel(),
                           measures.degrees.numpy().astype(np.float64), measures.skins.depths.numpy().astype(np.float64)])


def values(moved):
    """`case_rows`' values at the solved pose with level 2's moves `moved` (one evaluation, no tape)."""
    measures._evaluate(np.concatenate([pose, moved]), offsets)
    differences = measures.differences.numpy().astype(np.float64).reshape(len(measures.joint_names), len(rows), 3)
    degrees = measures.degrees.numpy().astype(np.float64).reshape(len(measures.turn_names), len(rows))
    depths = measures.skins.depths.numpy().astype(np.float64)
    bounds = np.cumsum([0] + measures.skins.counts)
    blank = np.zeros((len(rows), 1))
    return case_rows({name: (differences[index], np.zeros((len(rows), 3, 1)))
                      for index, name in enumerate(measures.joint_names)},
                     {name: (degrees[index], blank) for index, name in enumerate(measures.turn_names)},
                     {name: (depths[bounds[index]:bounds[index + 1]], np.zeros((bounds[index + 1] - bounds[index], 1)))
                      for index, name in enumerate(measures.skins.names)})[0]


picked = np.argsort(-np.linalg.norm(constant_rows, axis=0))[:PICKED]
differenced, raw_differenced = [], []
for entry in picked:
    nudge = np.zeros(len(moves))
    nudge[entry] = STEP
    differenced.append((values(nudge) - values(-nudge)) / (2 * STEP))
    raw_differenced.append((raw(nudge) - raw(-nudge)) / (2 * STEP))
differenced, raw_differenced = np.array(differenced).T, np.array(raw_differenced).T
raw_gap = np.abs(raw_differenced - raw_rows[:, picked])


def with_rows(flat):
    """`measured` with its rows replaced by `flat` (raw entries, columns) in `raw_rows`' order."""
    laid, start = [], 0
    for part in measured:
        given = {}
        for name, entry in part.items():
            count = int(np.prod(entry[1].shape[:-1]))
            given[name] = (entry[0], flat[start:start + count].reshape(*entry[1].shape[:-1], -1), *entry[2:])
            start += count
        laid.append(given)
    return laid


masked = case_rows(*with_rows(raw_differenced))[1]
largest = float(np.max(np.abs(constant_rows[:, picked])))
print(json.dumps({"rows shape": list(constant_rows.shape), "picked": picked.tolist(), "largest": largest,
                  "gap over largest": float(np.max(np.abs(differenced - constant_rows[:, picked])) / largest),
                  "worst rows": [[int(row), differenced[row].tolist(), constant_rows[row, picked].tolist()] for row in np.argsort(-np.max(np.abs(differenced - constant_rows[:, picked]), axis=1))[:6]],
                  "masked gap over largest": float(np.max(np.abs(masked - constant_rows[:, picked])) / largest),
                  "raw gap over largest": float(raw_gap.max() / np.abs(raw_rows[:, picked]).max()),
                  "raw worst": [[int(row), raw_differenced[row].tolist(), raw_rows[row, picked].tolist()]
                                for row in np.argsort(-raw_gap.max(axis=1))[:4]],
                  "finite": bool(np.isfinite(constant_rows).all()), "seconds": time.time() - began}))
