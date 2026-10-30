"""Level 3 across sets for one body (card build step 6a's next lever, #70): every nudged set of one level 1
Jacobian set up as `_card_batch.body_run` sets it up (its own state laid, level 2 cold, its own `Fitting` and
`_clip.Clip`), then every set's frames solved in ONE `fit._card._sets.Sets` batch (rows = set x frame, each row its
own set's joint places, offsets, weights, couplings and targets), then each set's clips written with its own state
put back. Same seeds and stop rules as each set alone, so the answers equal each set's own batch within the card's
float32 floor (`_sets`' test). Newton's Python and a CUDA card. Gate 2026-10-30: heavy_kimodo x 3 nudged sets, angles within 5.5e-5 deg, joints 5.4e-5 mm."""
import time

import numpy as np

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from evaluation import _card_batch, _case  # noqa: E402
from fit._card import _clip, _measure as card_measure, _seeds, _sets  # noqa: E402


class Prepared:
    """One set's body ready for level 3: its folder, clips, targets, set-up, file, card clip, seeds and laid state."""

    def __init__(self, folder, clips, targets, set_up, path, clip, seeds, laid, seconds):
        self.folder, self.clips, self.targets, self.set_up, self.path = folder, clips, targets, set_up, path
        self.clip, self.seeds, self.laid, self.seconds = clip, seeds, laid, seconds


def prepared(seeds_root, folder, cases, saved):
    """One set's body (`cases` {case: job path}) laid and set up as `body_run` does, up to its card clip."""
    saved.restore()
    recordings = _case.prepared(str(folder / "table.json"), str(folder / "weights.json"), folder, cases)
    began = time.time()
    clips = {case: _case.case_of(pathlib.Path(job), recordings) for case, job in cases.items()}
    rig = _card_batch.shared_rig(clips)
    first, (job, person, _, worlds) = next(iter(clips.items()))
    path = folder / first / f"{person['name']}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    targets = _card_batch.clip_targets(clips)
    set_up = _card_batch.cached_set_up(job, person, rig, worlds, path, _card_batch.recorded_targets(clips, targets))
    seeds = {case: _seeds.first(seeds_root, case) for case in clips}
    for case, (turns, _) in targets.items():
        if len(seeds[case]) != len(turns):
            raise ValueError(f"{case}: {len(seeds[case])} seeds for {len(turns)} frames")
    clip = _clip.for_fitting(set_up[2], path)
    return Prepared(folder, clips, targets, set_up, path, clip, seeds, _card_batch.Saved(), time.time() - began)


def joined(per_case, cases):
    """One set's rows: `per_case` {case: array} concatenated in `cases`' order."""
    return np.concatenate([per_case[case] for case in cases])


def solved_together(sets):
    """[{case: angles}] per set, every set's frames in one `Sets` batch."""
    together = _sets.Sets([one.clip for one in sets])
    found = together.angles([joined({case: turns for case, (turns, _) in one.targets.items()}, one.clips)
                             for one in sets],
                            [joined({case: points for case, (_, points) in one.targets.items()}, one.clips)
                             for one in sets],
                            [joined(one.seeds, one.clips) for one in sets])
    answers = []
    for one, (angles, _) in zip(sets, found):
        ends = np.cumsum([len(one.seeds[case]) for case in one.clips])
        answers.append({case: angles[end - len(one.seeds[case]):end].astype(float)
                        for case, end in zip(one.clips, ends)})
    return answers


def written(one, angles, batch_share):
    """One set's clips written by `_case.written` with its own laid state put back; `batch_share` its seconds."""
    one.laid.restore()
    record, scales, fitting = one.set_up
    seconds, frames = one.seconds + batch_share, sum(len(found) for found in angles.values())
    for case, (_, person, rig, worlds) in one.clips.items():
        out = one.folder / case
        out.mkdir(parents=True, exist_ok=True)
        if out / f"{person['name']}.xml" != one.path:
            (out / f"{person['name']}.xml").write_bytes(one.path.read_bytes())
        _case.written(out, person, rig, worlds,
                      (record, scales, fitting.model, angles[case], seconds * len(angles[case]) / frames),
                      card_measure.measures, one.targets[case][1])


def body_run(seeds_root, folders, cases, saved):
    """One body's clips (`cases`) for every set in `folders`: each set up alone, level 3 in one batch, each written."""
    sets = [prepared(seeds_root, folder, cases, saved) for folder in folders]
    began = time.time()
    answers = solved_together(sets)
    share = (time.time() - began) / len(sets)
    for one, angles in zip(sets, answers):
        written(one, angles, share)
