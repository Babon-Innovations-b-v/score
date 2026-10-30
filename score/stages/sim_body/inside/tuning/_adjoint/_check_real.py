"""The real body check's run in Newton's own Python (`python _check_real.py <this folder> <seeds root> <set folder>
<out root> <reference root> <case>=<job.json> ...`): one tuning body set up and solved by `_real` from the set's
table.json, weights.json and rest.json (copied into <out root>, where the person's file is written), its rows against
the card solve's own (<reference root>/<case>/angles.npz, Newton's order); prints JSON per case (frames, nq, the
largest |difference|), the per-frame model's check (`_real.per_frame_model` at the rows' pose through
`frame_couplings` and `RootTurns`' full(reduced()), its body_q against the clip's own model's at each row: the
largest |difference|), the trusted sites' rows (`taped_sites(fitting=)`, its weights taped) against the fixed weights'
at the solve ("trusted"), the joints' check (`TapedMeasures` on `_real.joint_parts` against
`evaluation._measure.centre` in MuJoCo: the largest |difference| of the misses; the turn groups'
degrees on `_real.turn_groups` against `fit/_card/_measure.turn_errors`: "turn most"; the bone points' depths outside
the skin on `_real.skin_parts` against `fit/_card/_measure.outside_marks`: "skin most", m) and the seconds; saves rows.npz (rows, steps, per case) into <out root>."""
import json
import pathlib
import shutil
import sys
import time

import newton
import numpy as np

sys.path.insert(0, sys.argv[1])
import _real  # noqa: E402
from _bodies import Pinned, RootTurns, pose_of  # noqa: E402
from _taped import _Couplings  # noqa: E402
from tuning._adjoint import Body, refused  # noqa: E402
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
TOLERANCE = float(__import__('os').environ.get('SCORE_ADJOINT_TOLERANCE', '1e-5'))  # float32's floor: interior 1.35e-6
began = time.time()
sites, offsets = _real.taped_sites(clip, copied, rows, targets)
couplings = _real.frame_couplings(clip, rows)
turns = RootTurns(pose_of(couplings, rows), len(couplings[0]) // len(rows))
held = _real.bound_held(clip, couplings, rows)


pinned = Pinned(turns.reduced(), held)
body = Body("heavy_kimodo", lambda inner, outer: sites.residuals(turns.full(pinned.whole(inner)), outer),
            lambda inner, outer: pinned.gradient(inner, turns.pulled(pinned.whole(inner), sites.gradient(
                turns.full(pinned.whole(inner)), outer))),
            turns.reduced(), len(rows), turns.per_copy - 1)
most = float(np.max(np.abs(body.gradient(body.inner, offsets))))
taped = {"most": most, "refused": refused([body], offsets, TOLERANCE), "held": int(held.sum()), "frames": body.frames,
         "pose size": body.pose_size, "inner": int(body.inner.size), "seconds": time.time() - began}
trusted_sites, trusted = _real.taped_sites(clip, copied, rows, targets, fitting=fitting)
at_solve = turns.full(turns.reduced())
plain_rows = sites.residuals(at_solve, offsets)
taped["trusted"] = {"outer": int(trusted.size), "ends": int(trusted_sites.ends), "largest": float(
    np.abs(plain_rows).max()), "most": float(np.abs(trusted_sites.residuals(at_solve, trusted) - plain_rows).max())}


def card_joints(clip, joints, scales, rows):
    """|MyoFullBody's centre - SOMA's joint| (joints, frames) m as `evaluation._measure.centre` reads it in MuJoCo."""
    import mujoco
    from evaluation import _measure as cpu
    from model import TO_OWN
    data, found = mujoco.MjData(clip.mjm), []
    for frame, row in enumerate(rows):
        data.qpos[:] = np.concatenate([row[:3], row[[6, 3, 4, 5]], row[7:]])
        mujoco.mj_kinematics(clip.mjm, data)
        found.append([np.linalg.norm(cpu.centre(clip.mjm, data, cpu.JOINTS[name], scales) - TO_OWN.T @ soma[frame])
                      for name, (_, soma) in sorted(joints.items())])
    return np.array(found).T


began = time.time()
from _measures import TapedMeasures  # noqa: E402
scales, segments, worlds, rig = _real.soma_of(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                         _card_batch.Saved())
joints = _real.joint_parts(clip, scales, segments, worlds)
groups = _real.turn_groups(clip, segments, worlds)
skins = _real.skin_parts(clip, rig, segments, worlds)
taped_joints = TapedMeasures(sites, joints, __import__("model").TO_OWN, groups, skins)
taped_joints._evaluate(turns.full(turns.reduced()), offsets)
mine = np.linalg.norm(taped_joints.differences.numpy().reshape(len(joints), len(rows), 3), axis=2)
wanted = card_joints(clip, joints, scales, rows)
from fit._card import _measure as card  # noqa: E402
degrees = taped_joints.degrees.numpy().reshape(len(groups), len(rows))
card_degrees = card.turn_errors(clip.mjm, card.Posed(clip.mjm, np.concatenate(
    [rows[:, :3], rows[:, [6, 3, 4, 5]], rows[:, 7:]], axis=1), {0}), worlds, segments)
turned = np.array([card_degrees[name] for name in sorted(groups)])
card_skins = card.Skins(rig, segments, worlds)
card_data = card.Posed(clip.mjm, np.concatenate([rows[:, :3], rows[:, [6, 3, 4, 5]], rows[:, 7:]], axis=1),
                       set(card_skins.frames.tolist()))
card_depths = card.outside_marks(card_data, card_skins)[1]
labels = card.scored_labels(card_data.bones)
skin_wanted = np.concatenate([card_depths[:, labels == name].ravel() for name in sorted(skins)])
skin_mine = taped_joints.skins.depths.numpy().astype(float)
measures = {"joints": len(joints), "most": float(np.max(np.abs(mine - wanted))), "largest": float(wanted.max()),
            "groups": len(groups), "turn most": float(np.max(np.abs(degrees - turned))),
            "turn largest": float(turned.max()), "regions": len(skins),
            "skin points": int(skin_mine.size), "skin most": float(np.max(np.abs(skin_mine - skin_wanted))),
            "skin largest": float(skin_wanted.max()), "seconds": time.time() - began}
began = time.time()
from tuning._adjoint import case_rows  # noqa: E402
values, derivative = case_rows(*taped_joints.measured(turns.full(turns.reduced()), offsets), frames=len(rows))
charted = pinned.rows(turns.pulled_rows(turns.reduced(), derivative))
pulled = {"full": list(derivative.shape), "charted": list(charted.shape), "finite": bool(np.isfinite(charted).all()),
          "held columns most": float(np.max(np.abs(charted[:, held]))), "seconds": time.time() - began}
print(json.dumps({"cases": found, "rows": int(rows.shape[0]), "seconds": seconds, "fk": fk, "taped": taped,
                  "measures": measures, "pulled": pulled}))
