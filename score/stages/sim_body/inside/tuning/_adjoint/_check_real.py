"""The real body check's run in Newton's own Python (`python _check_real.py <this folder> <seeds root> <set folder>
<out root> <reference root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` from the set's
table.json, weights.json and rest.json (copied into <out root>, where the person's file is written), its rows against
the card solve's own (<reference root>/<case>/angles.npz, Newton's order); prints JSON per case (frames, nq, the
largest |difference|) and the seconds; saves rows.npz (rows, steps, per case) into <out root>."""
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from evaluation import _card_batch  # noqa: E402
from fit._card import _seeds  # noqa: E402

seeds_root, folder, out, reference = (pathlib.Path(arg) for arg in sys.argv[2:6])
cases = dict(given.split("=", 1) for given in sys.argv[6:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
began = time.time()
clip, fitting, targets = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases,
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
print(json.dumps({"cases": found, "rows": int(rows.shape[0]), "seconds": seconds}))
