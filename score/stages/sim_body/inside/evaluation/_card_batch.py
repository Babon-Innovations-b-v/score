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
import hashlib
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
from landmarks import CENTRES, LANDMARKS, solver_marks  # noqa: E402
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


TARGETS = {}  # {`targets_key`: `fit.targets`}, one per clip and landmark set, shared by every nudged set


def targets_key(rig, segments, worlds):
    """What a clip's `fit.targets` reads: its rig, segments and worlds, the held groups (`fit.followed`) and the
    solver landmarks' faces and barycentric weights in order (a set that changes those makes them anew)."""
    digest = hashlib.sha256(np.ascontiguousarray(worlds, dtype=float).tobytes())
    for key in sorted(rig):
        digest.update(key.encode() + np.ascontiguousarray(np.asarray(rig[key])).tobytes())
    rows = [(name, LANDMARKS[name][0], tuple(LANDMARKS[name][1])) for name in solver_marks()]
    return digest.hexdigest(), tuple(segments), tuple(fit.followed(segments)), repr(rows)


def clip_targets(clips):
    """{case: `fit.targets`} of every clip of a body, made once per `targets_key` for every set's level 3 batch and
    writing."""
    found = {}
    for case, (_, person, rig, worlds) in clips.items():
        key = targets_key(rig, person["segments"], worlds)
        if key not in TARGETS:
            TARGETS[key] = fit.targets(rig, person["segments"], worlds, fit.followed(person["segments"]))
            for made in TARGETS[key]:
                made.flags.writeable = False  # shared by later sets: a write in place would reach them
        found[case] = TARGETS[key]
    return found


def recorded_targets(clips, targets):
    """The body's recordings' targets for level 2 from `targets` (`clip_targets`): its recordings are its clips' own
    worlds in order (`_case.prepared`), refused otherwise."""
    _, person, _, _ = next(iter(clips.values()))
    for (case, (_, _, _, worlds)), recording in zip(clips.items(), sim_body.recordings(person, None), strict=True):
        if not np.array_equal(worlds, recording):
            raise ValueError(f"{case}: its worlds are not the body's recording in its place")
    return list(targets.values())


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


def cached_sized(job, person, rig, path):
    """The body's `Size` and scales, its file without constants written at `path`: made once per `sized_key`,
    written again for every later set."""
    key = sized_key(job, person)
    if key not in SIZED:
        size = Size(rig)
        _, scales = myo.person_file(job["model"], size, person["kg"], path)
        SIZED[key] = size, path.read_text(), scales
    size, text, scales = SIZED[key]
    path.write_text(text)
    return size, scales


def cached_set_up(job, person, rig, worlds, path, made, found=None):
    """`sim_body.person_set_up` on `cached_sized`'s file; `made` the recordings' targets (`clip_targets`, the
    recordings being the body's clips in order), `found` the constants when solved already."""
    size, scales = cached_sized(job, person, rig, path)
    return sim_body.constants_set_up(job, person, rig, worlds, path, size, scales, made, found)


def laid_clips(root, cases, recordings):
    """One body's clips (`cases` {case: job path}) laid for one set from its `_case.prepared` recordings: the clips,
    the shared rig, the file's path and every clip's targets."""
    clips = {case: _case.case_of(pathlib.Path(job), recordings) for case, job in cases.items()}
    _, (_, person, _, _) = next(iter(clips.items()))
    path = root / next(iter(clips)) / f"{person['name']}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return clips, shared_rig(clips), path, clip_targets(clips)


def body_unfitted(table, weights, root, cases, saved):
    """One body's `Fitting` without constants for one set and its recordings' targets, what
    `fit.constants_across` takes for that set (phase A of `_card_sets`: a set's constants solved with every other
    set's)."""
    saved.restore()
    clips, rig, path, targets = laid_clips(root, cases, _case.prepared(table, weights, root, cases))
    _, (job, person, _, _) = next(iter(clips.items()))
    _, scales = cached_sized(job, person, rig, path)
    held = fit.followed(person["segments"])
    return fit.fitting(path, scales, held, person["segments"]), recorded_targets(clips, targets)


def body_run(seeds_root, table, weights, root, cases, saved, constants=None, found=None, fitting=None):
    """One body's clips (`cases` {case: job path}) on the card: state restored, laid, set up once, solved in one batch,
    each clip written by `_case.written`. `found`: the set's constants when solved already (`fit.constants_across`);
    with `fitting` too (that solve's `Fitting`, the constants laid on in place) no second person's file is written or
    compiled: its group ends are laid again on it (`fit.ends_relaid`) and Newton's model is built from the file without
    constants with the inside joints moved (`_clip.for_fitting`), each clip's folder holding no copy of the file."""
    saved.restore(constants)
    recordings = _case.prepared(table, weights, root, cases)
    began = time.time()
    clips, rig, path, targets = laid_clips(root, cases, recordings)
    _, (job, person, _, worlds) = next(iter(clips.items()))
    filed = fitting is None  # the file at `path` holds the set's constants
    if filed:
        record, scales, fitting = cached_set_up(job, person, rig, worlds, path, recorded_targets(clips, targets),
                                               found)
    else:
        _, scales = cached_sized(job, person, rig, path)
        fitting = fit.ends_relaid(fitting, scales, person["segments"])
        record = {"fit": {"method": fit.METHOD, "constants": fit.constants_record(found)}}
    angles = batched_angles(_clip.for_fitting(fitting, path), clips,
                            {case: _seeds.first(seeds_root, case) for case in clips}, targets)
    seconds, frames = time.time() - began, sum(len(found) for found in angles.values())
    for case, (_, person, rig, worlds) in clips.items():
        out = root / case
        out.mkdir(parents=True, exist_ok=True)
        if filed and out / f"{person['name']}.xml" != path:
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
