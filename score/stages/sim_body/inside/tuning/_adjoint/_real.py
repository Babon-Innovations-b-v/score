"""One real tuning body on the card for the adjoint (#70, Newton's Python only, never imported by `__init__.py`): its
`fit/_card/_clip.Clip` built as `evaluation/_card_batch.body_run` builds it (the module state `_case.prepared` lays,
the sizing, level 2's constants, `_clip.for_fitting`) and its clips' level 3 rows solved in one
`fit/_card/_sets.Sets([clip])` batch, each frame from its own seed, the rows in Newton's order (the free root's turn
x, y, z, w): the solved point `_bodies.copied_couplings` and `TapedSites` start from. `per_frame_model` is the body
copied once per frame for `TapedSites`, `frame_couplings` its `couplings=` off the clip's projection."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from evaluation import _card_batch, _case  # noqa: E402
from fit._card import _clip, _seeds  # noqa: E402
from _bodies import copied_couplings  # noqa: E402
from fit._card._sets import Sets  # noqa: E402


def set_up(table, weights, root, cases, saved):
    """One body's `Clip`, its `Fitting`, its clips' targets ({case: (turns, points)}) and the person's file for the set whose table.json,
    weights.json and rest.json are `table`, `weights` and `root`'s (`cases` {case: job path}, one body); `saved`
    (`_card_batch.Saved`) puts the module state back first, so a body never lays on top of another."""
    saved.restore()
    recordings = _case.prepared(table, weights, root, cases)
    clips, rig, path, targets = _card_batch.laid_clips(root, cases, recordings)
    _, (job, person, _, worlds) = next(iter(clips.items()))
    _, _, fitting = _card_batch.cached_set_up(job, person, rig, worlds, path,
                                             _card_batch.recorded_targets(clips, targets))
    return _clip.for_fitting(fitting, path), fitting, targets, path


def solved_rows(clip, targets, seeds):
    """Every clip's level 3 rows (frames x nq, Newton's order, clip after clip in `targets`' order) and steps from
    one `Sets([clip]).angles` batch; `seeds` {case: qpos [frames, nq], MuJoCo's layout}."""
    for case, (turns, _) in targets.items():
        if len(seeds[case]) != len(turns):
            raise ValueError(f"{case}: {len(seeds[case])} seeds for {len(turns)} frames")
    ((qpos, steps),) = Sets([clip]).angles([np.concatenate([turns for turns, _ in targets.values()])],
                                           [np.concatenate([points for _, points in targets.values()])],
                                           [np.concatenate([seeds[case] for case in targets])])
    return _seeds.newton_order(qpos), steps


def per_frame_model(fitting, path, frames):
    """Newton's model of the person's file at `path` (its inside joints moved as `fitting` holds them, as
    `_clip.for_fitting` builds it) copied `frames` times, joint_q copy by copy, built with requires_grad for the tape."""
    import newton
    one = newton.ModelBuilder(up_axis=newton.Axis.Z)
    one.add_mjcf(str(path), convert_mjc_equality_constraints=False, parse_meshes=False)
    _clip.moved_inside(one, fitting)
    copied = newton.ModelBuilder(up_axis=newton.Axis.Z)
    for _ in range(frames):
        copied.add_builder(one)
    return copied.finalize(device=_clip.DEVICE, requires_grad=True)


def frame_couplings(clip, rows):
    """`TapedSites`' couplings for `per_frame_model` at the solved `rows` (frames x nq, Newton's order) from the
    clip's projection (its one set's polynomials)."""
    projection = clip.projection
    return copied_couplings(projection.follower_coord.numpy(), projection.leader_coord.numpy(),
                            projection.follower_rest.numpy(), projection.leader_rest.numpy(),
                            projection.poly.numpy()[0], projection.frozen_coord.numpy(), rows)
