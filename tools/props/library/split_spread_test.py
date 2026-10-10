"""Check the splitter spread (split_spread.py, job splits 2026-10-10): a regions painting is matched to the close-up's
regions only when they are the same regions, the share of finishes owned counts only the counted finishes, and the
spread line reads its values right.

It needs numpy, scipy and trimesh, which only the prop environment has. Run by the gate with the system python, this
hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/library/split_spread_test.py
"""
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    import trimesh  # noqa: F401
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("SPREAD_TEST_HANDED") != "1":
        os.environ["SPREAD_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import split_spread  # noqa: E402


def pixels():
    """A 10 x 10 close-up: a 4-pixel border off the object, region 0 on 60 pixels, region 1 on 4."""
    found = np.full((10, 10), -1)
    found[1:9, 1:9] = 0
    found[1:3, 1:3] = 1
    return found


def test_region_shares_are_shares_of_the_object():
    assert np.allclose(split_spread.region_shares(pixels()), [60 / 64, 4 / 64])


def test_same_regions_needs_the_count_and_the_shares():
    painted = [{"share": round(60 / 64, 3)}, {"share": round(4 / 64, 3)}]
    assert split_spread.same_regions(painted, pixels())
    assert not split_spread.same_regions(painted[:1], pixels())
    assert not split_spread.same_regions([{"share": 0.9}, {"share": 0.1}], pixels())


def test_owned_share_counts_owned_and_missed_only():
    assert split_spread.owned_share({"owned": [0, 2], "missed": [1]}) == 2 / 3
    assert split_spread.owned_share({"owned": [], "missed": []}) is None


def test_finish_indices_join_regions_of_one_material():
    with tempfile.TemporaryDirectory() as folder:
        run = pathlib.Path(folder)
        (run / "take").mkdir()
        split_spread.write_finishes(run, "take", ["steel", "paint", "steel"], "test")
        indices, names = split_spread.finish_indices(run, "take")
        assert names == ["paint", "steel"] and indices.tolist() == [1, 0, 1]
        assert json.loads((run / "take" / "finishes.json").read_text())["source"] == "test"


def test_spread_line_reads_the_values():
    line = split_spread.spread_line("owned", [0.0, 0.5, 1.0, None])
    assert "n=3" in line and "mean 0.500" in line and "min 0.000" in line and "max 1.000" in line
    assert split_spread.spread_line("owned", [None]).endswith("none")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("split_spread_test: ok")
