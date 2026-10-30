"""_card_batch.py <seeds root> <table.json> <weights.json> <out root> <case>=<job.json> ...: `_card_case.py` for every
body of an evaluation in one process (card build step 5b; the profile: imports, Warp's loads and the sizing, not level
3, were each case's time). Per body: the module state `_case.prepared` lays (the landmark set, the centres, the
calibration table, the weights, level 2 held) put back from the copy saved before the first body, never added on top,
then laid again for that body; the person's sizing (`sizing.Size`) and file without constants made once per body and
calibration table across sets (`cached_set_up`), its level 2 and `Fitting` once per set (a body's
clips share one rig, refused otherwise) and every clip's frames solved in one card batch (`fit._card._clip`, each frame
seeded from <seeds root>/<case>/angles.npz), then per clip `_case.written` with the card's measures. `fit.following`
is not run: nothing an evaluation writes reads it. A clip's "fit seconds" is its share of its body's set-up and batch
by frames. Writes what `_case` writes. Newton's Python (newton, warp, mujoco_warp) and a CUDA card."""
import copy
import json
import pathlib
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import calibration  # noqa: E402
import evaluation  # noqa: E402
import fit  # noqa: E402
import myo  # noqa: E402
import sim_body  # noqa: E402
from evaluation import _case, _measure  # noqa: E402
from fit import _frames  # noqa: E402
from fit._card import _clip, _measure as card_measure, _seeds  # noqa: E402
from landmarks import CENTRES, LANDMARKS  # noqa: E402
from sizing import Size  # noqa: E402

LAID = (LANDMARKS, CENTRES, _measure.CENTRES, calibration.TABLE)  # the dicts `_case.prepared` changes in place


class Saved:
    """The module state `_case.prepared` changes, copied once before any body (the dicts in `LAID`, the two global
    weights, `fit.constants`), put back by `restore`."""

    def __init__(self):
        self.tables = [copy.deepcopy(table) for table in LAID]
        self.goal, self.end_weight, self.constants = _frames.MARKER_GOAL, fit.END_WEIGHT, fit.constants

    def restore(self, constants=None):
        """Every saved dict, weight and level 2 back as copied (`constants`, when given, as fit.constants instead)."""
        for table, kept in zip(LAID, self.tables):
            table.clear()
            table.update(copy.deepcopy(kept))
        _frames.MARKER_GOAL, fit.END_WEIGHT = self.goal, self.end_weight
        fit.constants = constants or self.constants


def shared_rig(clips):
    """The one rig of a body's clips ({case: (job, person, rig, worlds)}), refused when their model, mass, segments or
    rig differ."""
    (_, person, rig, _), *others = clips.values()
    for case, (_, other, other_rig, _) in clips.items():
        same = (other["kg"] == person["kg"] and other["segments"] == person["segments"]
                and all(np.array_equal(np.asarray(rig[key]), np.asarray(other_rig[key])) for key in rig))
        if not same:
            raise ValueError(f"{case}: its rig, mass or segments are not its body's first clip's")
    return rig


def clip_targets(clips):
    """{case: `fit.targets`} of every clip of a body, made once for its level 3 batch and its writing."""
    return {case: fit.targets(rig, person["segments"], worlds, fit.followed(person["segments"]))
            for case, (_, person, rig, worlds) in clips.items()}


def batched_angles(clip, clips, seeds, targets):
    """{case: angles} for every clip of a body in one `Clip.angles` call, rows clip after clip (`targets`:
    `clip_targets`)."""
    for case, (turns, _) in targets.items():
        if len(seeds[case]) != len(turns):
            raise ValueError(f"{case}: {len(seeds[case])} seeds for {len(turns)} frames")
    found, _ = clip.angles(np.concatenate([turns for turns, _ in targets.values()]),
                           np.concatenate([points for _, points in targets.values()]),
                           np.concatenate([seeds[case] for case in clips]))
    ends = np.cumsum([len(seeds[case]) for case in clips])
    return {case: found[end - len(seeds[case]):end].astype(float) for case, end in zip(clips, ends)}


SIZED = {}  # {(person, kg, model, calibration table): (Size, the sized file's text, its scales)}, one per body


def sized_key(job, person):
    """What a body's sizing and its file without constants depend on: the person, its mass, the model and the
    calibration table (read again from the centres, so a centre set sizes anew; links, trusts and weights do not)."""
    return person["name"], person["kg"], job["model"], tuple(sorted((group, tuple(np.asarray(quaternion).tolist()))
                                                                   for group, quaternion in calibration.TABLE.items()))


def cached_set_up(job, person, rig, worlds, path):
    """`sim_body.person_set_up` with the body's `Size` and first file (no constants) made once per `sized_key` and
    written again at `path` for every later set."""
    key = sized_key(job, person)
    if key not in SIZED:
        size = Size(rig)
        _, scales = myo.person_file(job["model"], size, person["kg"], path)
        SIZED[key] = size, path.read_text(), scales
    size, text, scales = SIZED[key]
    path.write_text(text)
    return sim_body.constants_set_up(job, person, rig, worlds, path, size, scales)


def body_run(seeds_root, table, weights, root, cases, saved, constants=None):
    """One body's clips (`cases` {case: job path}) on the card: state restored, laid, set up once, solved in one batch,
    each clip written by `_case.written`."""
    saved.restore(constants)
    recordings = _case.prepared(table, weights, root, cases)
    began = time.time()
    clips = {case: _case.case_of(pathlib.Path(job), recordings) for case, job in cases.items()}
    rig = shared_rig(clips)
    first, (job, person, _, worlds) = next(iter(clips.items()))
    path = root / first / f"{person['name']}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    record, scales, fitting = cached_set_up(job, person, rig, worlds, path)
    targets = clip_targets(clips)
    angles = batched_angles(_clip.for_fitting(fitting, path), clips,
                            {case: _seeds.first(seeds_root, case) for case in clips}, targets)
    seconds, frames = time.time() - began, sum(len(found) for found in angles.values())
    for case, (_, person, rig, worlds) in clips.items():
        out = root / case
        out.mkdir(parents=True, exist_ok=True)
        if out / f"{person['name']}.xml" != path:
            shutil.copyfile(path, out / f"{person['name']}.xml")
        _case.written(out, person, rig, worlds,
                      (record, scales, fitting.model, angles[case], seconds * len(angles[case]) / frames),
                      card_measure.measures, targets[case][1])


def main():
    seeds_root, table, weights, root = (pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3],
                                        pathlib.Path(sys.argv[4]))
    cases = dict(given.split("=", 1) for given in sys.argv[5:])
    saved = Saved()
    for body_cases in evaluation.by_body(cases).values():
        body_run(seeds_root, table, weights, root, body_cases, saved)


if __name__ == "__main__":
    main()
