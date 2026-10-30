"""_card_sets.py <seeds root> <sets root> [--same-seeds] <case>=<job.json> ...: every set of unknowns of one level 1
Jacobian (card build step 6a, the owner's batch: `tuning._differences.nudged`'s sets with the base point first) in ONE card process.
<sets root>/<chunk>/<set>/ holds (chunks p000, p001.. of at most `evaluation.CHUNK` sets, run one after another in this
process, so each body's start-up caches serve every chunk and only a chunk's card state is freed between them) the set's table.json, weights.json and rest.json (what `evaluation.measured` writes for one
evaluation), the sets in name order, the first of each chunk its base point. Per body: every set's constants solved together
(`fit.constants_across`: each set's sampled frames posed in one card launch a frame), then per set `_card_batch.body_run`
given its constants, the module state restored from the copy saved before the first, so no set adds on top of another; the base point seeded from
<seeds root>, every other set from the base point's own angles (<sets root>/<base>/<case>/angles.npz: a nudged set
starts where the base point ended); with --same-seeds every set from <seeds root> (`evaluation.measured_many`:
level 1's sets, whose base point another call made). Writes what `_case` writes into <sets root>/<set>/<case>/. Newton's Python and a
CUDA card."""
import gc
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
import fit  # noqa: E402
from evaluation import _card_batch  # noqa: E402


def sets_of(root):
    """The sets' folders in name order (the base point first), each holding table.json, weights.json, rest.json."""
    found = sorted(folder for folder in root.iterdir() if (folder / "table.json").exists())
    if not found:
        raise ValueError(f"{root}: no set holds a table.json")
    return found


def chunks_of(root):
    """The chunks' folders under `root` in name order (p000, p001..), each holding sets (`sets_of`)."""
    found = sorted(folder for folder in root.iterdir() if folder.is_dir() and any(folder.glob("*/table.json")))
    if not found:
        raise ValueError(f"{root}: no chunk holds a set")
    return found


def body_constants(folders, body_cases, saved):
    """Every set's constants of one body (`body_cases` {case: job path}), `fit.constants_across`: each set's
    `Fitting` without constants laid on its own state (phase A), every set's sampled frames posed in one card launch a
    frame (phase B)."""
    unfitted = [_card_batch.body_unfitted(str(folder / "table.json"), str(folder / "weights.json"), folder,
                                          body_cases, saved) for folder in folders]
    return fit.constants_across([fitting for fitting, _ in unfitted], [made for _, made in unfitted])


def sets_run(seeds_root, folders, cases, saved, same):
    """Every set's every body (`cases` {case: job path}) on the card, set by set in `folders`' order (the base point
    first), each body's constants solved across all sets first (`body_constants`); a nudged set seeded from the base
    point's own angles unless `same`."""
    base = folders[0]
    for body_cases in evaluation.by_body(cases).values():
        found = body_constants(folders, body_cases, saved)
        for folder, constants in zip(folders, found, strict=True):
            seeds = seeds_root if same or folder == base else base
            _card_batch.body_run(seeds, str(folder / "table.json"), str(folder / "weights.json"), folder, body_cases,
                                 saved, found=constants)


def main():
    seeds_root, root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    same = sys.argv[3] == evaluation.SAME_SEEDS
    cases = dict(given.split("=", 1) for given in sys.argv[4 if same else 3:])
    saved = _card_batch.Saved()
    for part in chunks_of(root):
        sets_run(seeds_root, sets_of(part), cases, saved, same)
        gc.collect()  # the chunk's per-set constants and card arrays go; each body's start-up caches stay


if __name__ == "__main__":
    main()
