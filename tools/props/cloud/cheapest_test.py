"""Checks for cheapest.py: Blender and bakes never take an 80 GB card, and other work takes one only when no smaller
card is to be had.

Run: python3 tools/props/cloud/cheapest_test.py
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cheapest  # noqa: E402

Offer = collections.namedtuple("Offer", "machine_class stock_word")


def test_blender_never_takes_an_80gb_card():
    assert cheapest.never_big(["gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2"]) == ["gpu-24gb", "gpu-48gb"]
    try:
        cheapest.never_big(["gpu-80gb"])
    except SystemExit as refusal:
        assert "never take one" in str(refusal)
    else:
        raise AssertionError("an 80 GB card alone was taken for Blender")


def test_an_80gb_card_only_when_no_smaller_one_is_to_be_had():
    l4, h100 = Offer("gpu-24gb", "scarce"), Offer("gpu-80gb", "available")
    assert cheapest.big_last([h100, l4]) == [l4]
    gone = Offer("gpu-24gb", "shortage")
    assert cheapest.big_last([h100, gone]) == [h100, gone]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("cheapest_test: ok")
