"""_card_case.py <seeds root> <table.json> <weights.json> <out root> <case>=<job.json> ...: `_case.py` with level 3
on the card (#70, the card build plan's step 5): each clip's frames solved side by side by `fit._card._clip` (one row
a frame, each seeded from <seeds root>/<case>/angles.npz, `fit._card._seeds.first`) in place of mink's frame-by-frame
`fit.angles`, and the honest measures by `fit._card._measure` (the CPU's keys). Level 2 is `_case`'s (its exact
Jacobian already the card's). Writes what `_case` writes; angles.npz is the card's solve. `_case.py` stays the
reference: the card worker replaces it only where its measures equal the CPU's to their rounding.
Newton's Python (newton, warp, mujoco_warp) and a CUDA card; run one process per body."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import fit  # noqa: E402
from evaluation import _case  # noqa: E402
from fit._card import _clip, _measure as card_measure, _seeds  # noqa: E402


def card_angles(seeds, path):
    """fit.angles(fitting, turns, points, skins) on the card for one clip: its frames from `seeds` (qpos [frames, nq]), the
    Newton model read from the person's file at `path` (the constants written there); float64 qpos like mink's."""
    def angles(fitting, turns, points, skins=None):
        if len(seeds) != len(turns):
            raise ValueError(f"{path}: {len(seeds)} seeds for {len(turns)} frames")
        found, _ = _clip.for_fitting(fitting, path).angles(turns, points, seeds, skins)
        return found.astype(float)
    return angles


def main():
    seeds_root, table, weights, root = (pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3],
                                        pathlib.Path(sys.argv[4]))
    cases = dict(given.split("=", 1) for given in sys.argv[5:])
    recordings = _case.prepared(table, weights, root, cases)
    for case, job in cases.items():
        name = json.loads(pathlib.Path(job).read_text())["people"][0]["name"]
        fit.angles = card_angles(_seeds.first(seeds_root, case), root / case / f"{name}.xml")
        _case.fitted_case(pathlib.Path(job), root / case, recordings, card_measure.measures)


if __name__ == "__main__":
    main()
