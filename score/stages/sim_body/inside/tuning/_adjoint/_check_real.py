"""The real body check's run in Newton's own Python (`python _check_real.py <this folder> <seeds root> <set folder>
<out root> <reference root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` from the set's
table.json, weights.json and rest.json (copied into <out root>, where the person's file is written), its rows against
the card solve's own (<reference root>/<case>/angles.npz, Newton's order); prints JSON per case (frames, nq, the
largest |difference|), the per-frame model's check (`_real.per_frame_model` at the rows' pose through
`frame_couplings` and `RootTurns`' full(reduced()), its body_q against the clip's own model's at each row: the
largest |difference|) and the seconds; saves rows.npz (rows, steps, per case) into <out root>."""
import json
import pathlib
import shutil
import sys
import time

import newton
import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from _bodies import RootTurns, pose_of  # noqa: E402
from _taped import _Couplings  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit._card import _seeds  # noqa: E402

seeds_root, folder, out, reference = (pathlib.Path(arg) for arg in sys.argv[2:6])
cases = dict(given.split("=", 1) for given in sys.argv[6:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
began = time.time()
clip, fitting, targets, path = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                            _card_batch.Saved())
rows, steps = _real.solved_rows(clip, targets, {case: _seeds.first(seeds_root, case) for case in cases})
seconds = time.time() - began
found, start = {}, 0
for case in cases:
    wanted = _seeds.newton_order(_seeds.first(reference, case))
    mine = rows[start:start + len(wanted)]
    found[case] = {"frames": len(wanted), "nq": int(wanted.shape[1]), "most": float(np.max(np.abs(mine - wanted)))}
    start += len(wanted)
np.savez(out / "rows.npz", rows=rows, steps=steps)


def own_body_q(model, rows):
    """The clip's own model's body_q (frames, bodies, 7) at each solved row."""
    state, placed = model.state(), []
    for row in rows:
        model.joint_q.assign(row.astype(np.float32))
        newton.eval_fk(model, model.joint_q, model.joint_qd, state)
        placed.append(state.body_q.numpy().copy())
    return np.stack(placed)


def copied_body_q(model, couplings, rows):
    """The per-frame model's body_q (frames, bodies, 7) at the rows' charted pose written through the couplings."""
    turns = RootTurns(pose_of(couplings, rows), len(couplings[0]) // len(rows))
    written = _Couplings(model.device, *couplings)
    written.write(turns.full(turns.reduced()), model.joint_q)
    state = model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, state)
    return state.body_q.numpy().reshape(len(rows), -1, 7)


began = time.time()
copied = _real.per_frame_model(fitting, path, len(rows))
gap = np.abs(copied_body_q(copied, _real.frame_couplings(clip, rows), rows) - own_body_q(clip.model, rows))
fk = {"most": float(gap.max()), "bodies": int(gap.shape[1]), "seconds": time.time() - began}
print(json.dumps({"cases": found, "rows": int(rows.shape[0]), "seconds": seconds, "fk": fk}))
