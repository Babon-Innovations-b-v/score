"""_card_sets.py <seeds root> <sets root> [--across <sets>] [--same-seeds] <case>=<job.json> ...: every set of unknowns of one level 1
Jacobian (card build step 6a, the owner's batch: `tuning._differences.nudged`'s sets with the base point first) in ONE card process.
<sets root>/<set>/ holds the set's table.json, weights.json and rest.json (what `evaluation.measured` writes for one
evaluation), the sets in name order, the first the base point. Per set and body: `_card_batch.body_run`, the module
state restored from the copy saved before the first, so no set adds on top of another; the base point seeded from
<seeds root>, every other set from the base point's own angles (<sets root>/<base>/<case>/angles.npz: a nudged set
starts where the base point ended); with --same-seeds every set from <seeds root> (`evaluation.measured_many`:
level 1's sets, whose base point another call made). With --warm <tolerance> (not with --same-seeds) every nudged
set's level 2 starts from the base point's solved constants and sampled angles for the same body, at that tolerance,
the base point's too (`evaluation.warmed`); off by default until the 6a gate passes warm. Writes what `_case` writes into <sets root>/<set>/<case>/. Newton's Python and a
CUDA card."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
from evaluation import _card_across, _card_batch  # noqa: E402



def sets_of(root):
    """The sets' folders in name order (the base point first), each holding table.json, weights.json, rest.json."""
    found = sorted(folder for folder in root.iterdir() if (folder / "table.json").exists())
    if not found:
        raise ValueError(f"{root}: no set holds a table.json")
    return found


WARM = "--warm"
ACROSS = "--across"  # <sets> nudged sets a body at a time in one level 3 batch (`_card_across`), not yet gated


def set_run(seeds_root, folder, cases, saved, warm=None):
    """One set's every body (`cases` {case: job path}) on the card, written into `folder`; `warm` (kept, tolerance)
    level 2 warm from the base point per body (`evaluation.warmed`)."""
    for body, body_cases in evaluation.by_body(cases).items():
        constants = evaluation.warmed(saved.constants, warm[0], body, warm[1]) if warm else None
        _card_batch.body_run(seeds_root, str(folder / "table.json"), str(folder / "weights.json"), folder, body_cases,
                             saved, constants)


def options(argv):
    """The command's seeds root, sets root, --same-seeds, --warm tolerance (or None) and {case: job path}."""
    seeds_root, root, *rest = argv
    same = rest[:1] == [evaluation.SAME_SEEDS]
    rest = rest[1:] if same else rest
    tolerance = float(rest[1]) if rest[:1] == [WARM] else None
    if tolerance is not None and same:
        raise ValueError("--warm needs the base point in this process, not --same-seeds")
    rest = rest[2:] if tolerance is not None else rest
    return pathlib.Path(seeds_root), pathlib.Path(root), same, tolerance, dict(given.split("=", 1) for given in rest)


def across_run(seeds_root, folders, cases, saved, group):
    """The nudged sets' every body, `group` sets at a time in one level 3 batch (`_card_across.body_run`)."""
    for body_cases in evaluation.by_body(cases).values():
        for start in range(0, len(folders), group):
            _card_across.body_run(seeds_root, folders[start:start + group], body_cases, saved)


def across_of(argv):
    """`--across <sets>` taken off the front of `argv`: (group or None, the rest)."""
    if argv[2:3] == [ACROSS]:
        return int(argv[3]), argv[:2] + argv[4:]
    return None, argv


def main():
    group, argv = across_of(sys.argv[1:])
    seeds_root, root, same, tolerance, cases = options(argv)
    if group and tolerance is not None:
        raise ValueError("--across runs level 2 cold only")
    saved = _card_batch.Saved()
    warm = ({}, tolerance) if tolerance is not None else None
    base, *nudged = sets_of(root)
    set_run(seeds_root, base, cases, saved, warm)
    if group:
        across_run(seeds_root if same else base, nudged, cases, saved, group)
        return
    for folder in nudged:
        set_run(seeds_root if same else base, folder, cases, saved, warm)


if __name__ == "__main__":
    main()
