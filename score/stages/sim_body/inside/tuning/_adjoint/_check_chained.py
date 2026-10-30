"""`chained_rows` on one real body against both levels re-solved, run in Newton's own Python (`python
_check_chained.py <this folder> <seeds root> <set folder> <out root> <step> <case>=<job.json> ...`): level 1's point
one link entry of `tuning.layout` (the first that moves a placed solver landmark's site), every other entry at its
start, through `tuning.applied`; at the base point level 3 set up and solved by `_real` (as `_check_rows.py`), R_q
and R_c taped by `TapedMeasures` at the solved rows, level 3 as `_bodies.level3_body` with `placed(theta)` the site
offsets plus `_outer.picked_columns`' link column (theta in metres of link units) and its c read as the moves off
level 2's solved constants, level 2 as `_level2.level2_body` (as `_check_motion.py`); against central differences of
`case_rows` at +-<step>, each side `_real.set_up` (both levels re-solved) plus `solved_rows`, its per-frame measures
put through `case_rows` at the base medians' frames (the median's derivative wherever it is smooth). Prints JSON: the
entry, the rows, the largest |gap| over the largest entry (passing under 0.02), the worst rows and the seconds."""
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
from fit._card import _seeds  # noqa: E402
from fit._card._level2 import jacobian  # noqa: E402
from fit._constants import INSIDE, Problem, told  # noqa: E402
from tuning._adjoint import Body, case_rows, chained_rows  # noqa: E402
from tuning._adjoint._level2 import level2_body  # noqa: E402
from tuning._adjoint._outer import picked_columns  # noqa: E402

STEPS, TOLERANCE = (1e-4, 1e-3), 1e-3  # as `_check_motion.py`
seeds_root, folder, out = (pathlib.Path(arg) for arg in sys.argv[2:5])
step = float(sys.argv[5])
cases = dict(given.split("=", 1) for given in sys.argv[6:])
out.mkdir(parents=True, exist_ok=True)
for name in ("table.json", "weights.json", "rest.json"):
    shutil.copyfile(folder / name, out / name)
table, weights = (json.loads((out / name).read_text()) for name in ("table.json", "weights.json"))
starts = {name: row["link"] for name, row in table.items()}
entries = tuning.layout(table, held=landmarks.HELD, joints=set())
seeds = {case: _seeds.first(seeds_root, case) for case in cases}
began, saved = time.time(), _card_batch.Saved()


def applied(outer, chosen):
    """The set's (table rows, weights) with entry `chosen` at `outer`, every other entry at its start."""
    unknowns = np.zeros(len(entries))
    unknowns[np.atleast_1d(chosen).astype(int)] = outer
    return tuning.applied(unknowns, entries, starts, table, weights)


def written(outer, chosen):
    """The set at `outer` written into `out` (table.json, weights.json)."""
    rows, moved = applied(outer, chosen)
    (out / "table.json").write_text(json.dumps(rows, indent=1))
    (out / "weights.json").write_text(json.dumps(moved))


def solved_point():
    """Both levels set up and solved at the written set: (clip, fitting, rows, model, path)."""
    clip, fitting, targets, path = _real.set_up(str(out / "table.json"), str(out / "weights.json"), out, cases, saved)
    rows, _ = _real.solved_rows(clip, targets, seeds)
    return clip, fitting, targets, rows, _real.per_frame_model(fitting, path, len(rows))


def measures_on(clip, sites):
    """`TapedMeasures` on `sites` with the written set's SOMA parts."""
    scales, segments, worlds, rig = _real.soma_of(str(out / "table.json"), str(out / "weights.json"), out, cases,
                                                  saved)
    return TapedMeasures(sites, _real.joint_parts(clip, scales, segments, worlds), __import__("model").TO_OWN,
                         _real.turn_groups(clip, segments, worlds), _real.skin_parts(clip, rig, segments, worlds))


def raw_measures(measures, pose, offsets):
    """Every per-frame measure (joint differences m, turn degrees, skin depths m) flat at `pose`."""
    measures._evaluate(pose, offsets)
    return np.concatenate([measures.differences.numpy().astype(np.float64).ravel(),
                           measures.degrees.numpy().astype(np.float64), measures.skins.depths.numpy().astype(np.float64)])


def link_column(clip):
    """The first link entry moving a placed solver landmark, and its `_outer.picked_columns` column."""
    names = [clip.mjm.site(int(site)).name.removeprefix("mark:") for site in clip.place_sites]  # fit/_model.py
    for chosen, (_, kind, _, _) in enumerate(entries):
        if kind == "link":
            laid = picked_columns(names, [chosen], entries, table, weights)[:, 0]
            if np.any(laid):
                return chosen, laid
    raise ValueError(f"no link entry moves any of the {len(names)} placed sites")


def shifted(level3, solved):
    """`level3` with its c read as level 2's constants (`solved`) rather than the moves off them."""
    def moved(outer):
        return np.concatenate([outer[:1], np.asarray(outer[1:], dtype=float) - solved])
    return Body(level3.name, lambda inner, outer: level3.residuals(inner, moved(outer)),
                lambda inner, outer: level3.gradient(inner, moved(outer)), level3.inner, level3.frames,
                level3.pose_size)


def level2_at_base(chosen):
    """Level 2's Body at the written base set (its Problem off the base solve, `_real.problem_at` elsewhere)."""
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
    rebuilt = _real.problem_at(lambda outer: applied(outer, chosen), out, cases, saved, angles, constants)
    at = lambda outer: problem if not np.any(outer) else rebuilt(outer)  # noqa: E731
    return level2_body(at, jacobian, problem.start(), kept, np.zeros(1))


written(np.zeros(1), [])
clip, fitting, targets, rows, model = solved_point()
chosen, column = link_column(clip)
sites, offsets = _real.taped_sites(clip, model, rows, targets, constants=_real.level2_constants(fitting, model,
                                                                                                 len(rows)))
measures = measures_on(clip, sites)
pose = np.asarray(pose_of(_real.frame_couplings(clip, rows), rows), dtype=np.float64)
inner = np.concatenate([pose, np.zeros(sites.constants.size)])
turns = RootTurns(pose, len(_real.frame_couplings(clip, rows)[0]) // len(rows))
pinned = Pinned(turns.reduced(), _real.bound_held(clip, _real.frame_couplings(clip, rows), rows))
by_poses = pinned.rows(turns.pulled_rows(turns.reduced(), case_rows(*measures.measured(inner, offsets),
                                                                    frames=len(rows))[1]))
measured = measures.constant_measured(inner, offsets)
by_constants = case_rows(*measured)[1]
level2 = level2_at_base(chosen)
solved = level2.inner[level2.frames * level2.pose_size:]
if solved.size != sites.constants.size:
    raise ValueError(f"level 2 has {solved.size} constants, the taped sites {sites.constants.size}")
level3 = shifted(level3_body("heavy_kimodo", sites, turns, pinned, lambda theta: offsets + column * theta[0], 1,
                             len(rows)), solved)
implicit = chained_rows(level2, level3, (by_poses, np.zeros((len(by_poses), 1)), by_constants), np.zeros(1), STEPS,
                        TOLERANCE)[:, 0]
implicit_seconds = time.time() - began
sides = []
for sign in (1, -1):
    written(np.array([sign * step]), [chosen])
    side_clip, _, side_targets, side_rows, side_model = solved_point()
    side_sites, side_offsets = _real.taped_sites(side_clip, side_model, side_rows, side_targets)
    side_pose = np.asarray(pose_of(_real.frame_couplings(side_clip, side_rows), side_rows), dtype=np.float64)
    sides.append(raw_measures(measures_on(side_clip, side_sites), side_pose, side_offsets))
raw_differenced = ((sides[0] - sides[1]) / (2 * step))[:, None]


def with_rows(flat):
    """`measured` with its rows replaced by `flat` (raw entries, columns) in `raw_measures`' order."""
    laid, start = [], 0
    for part in measured:
        given = {}
        for name, entry in part.items():
            count = int(np.prod(entry[1].shape[:-1]))
            given[name] = (entry[0], flat[start:start + count].reshape(*entry[1].shape[:-1], -1), *entry[2:])
            start += count
        laid.append(given)
    return laid


differenced = case_rows(*with_rows(raw_differenced))[1][:, 0]
gap = np.abs(differenced - implicit)
largest = float(np.abs(differenced).max())
print(json.dumps({"entry": list(map(str, entries[chosen])), "rows": int(len(implicit)), "largest": largest,
                  "implicit largest": float(np.abs(implicit).max()), "gap over largest": float(gap.max() / largest),
                  "worst rows": [[int(row), float(differenced[row]), float(implicit[row])]
                                 for row in np.argsort(-gap)[:6]],
                  "implicit seconds": implicit_seconds, "seconds": time.time() - began}))
