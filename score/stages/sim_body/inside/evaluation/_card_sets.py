"""_card_sets.py <seeds root> <sets root> [--same-seeds] <case>=<job.json> ...: every set of unknowns of one level 1
Jacobian (card build step 6a, the owner's batch: `tuning._differences.nudged`'s sets with the base point first) in ONE card process.
<sets root>/<set>/ holds the set's table.json, weights.json and rest.json (what `evaluation.measured` writes for one
evaluation), the sets in name order, the first the base point. Per set and body: `_card_batch.body_run`, the module
state restored from the copy saved before the first, so no set adds on top of another; the base point seeded from
<seeds root>, every other set from the base point's own angles (<sets root>/<base>/<case>/angles.npz: a nudged set
starts where the base point ended); with --same-seeds every set from <seeds root> (`evaluation.measured_many`:
level 1's sets, whose base point another call made). Writes what `_case` writes into <sets root>/<set>/<case>/. Newton's Python and a
CUDA card."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
from evaluation import _card_batch  # noqa: E402


def sets_of(root):
    """The sets' folders in name order (the base point first), each holding table.json, weights.json, rest.json."""
    found = sorted(folder for folder in root.iterdir() if (folder / "table.json").exists())
    if not found:
        raise ValueError(f"{root}: no set holds a table.json")
    return found


def set_run(seeds_root, folder, cases, saved):
    """One set's every body (`cases` {case: job path}) on the card, written into `folder`."""
    for body_cases in evaluation.by_body(cases).values():
        _card_batch.body_run(seeds_root, str(folder / "table.json"), str(folder / "weights.json"), folder, body_cases,
                             saved)


def main():
    seeds_root, root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    same = sys.argv[3] == evaluation.SAME_SEEDS
    cases = dict(given.split("=", 1) for given in sys.argv[4 if same else 3:])
    saved = _card_batch.Saved()
    base, *nudged = sets_of(root)
    set_run(seeds_root, base, cases, saved)
    for folder in nudged:
        set_run(seeds_root if same else base, folder, cases, saved)


if __name__ == "__main__":
    main()
