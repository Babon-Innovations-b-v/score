"""Checks for warm.py without the cloud: a class with no offer is refused and rents nothing, a class with one is
measured on one machine that is deleted and recorded in the ledger by its class.

Run: .venv/bin/python tools/cloud/images/warm_test.py   (make tests runs it)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build_test  # noqa: E402
import warm  # noqa: E402


def test_a_class_without_an_offer_is_refused_and_one_with_is_measured_and_recorded():
    seen, restore = build_test.renting("gpu-24gb", None)
    measured = []
    kept = warm.set_up, warm.measure, warm.batch.offers
    warm.set_up = lambda machine, registry, store_spec: None
    warm.measure = lambda machine, image, store_spec, results: measured.append(machine["class"])
    try:
        warm.batch.offers = lambda classes: []
        warm.measure_class("gpu-none", "image", {}, {}, "tester", {})
        assert seen["said"] == ["gpu-none: refused: no offer"] and not seen["ledger"]
        warm.batch.offers = kept[2]
        warm.measure_class("gpu-24gb", "image", {}, {}, "tester", {})
    finally:
        warm.set_up, warm.measure, warm.batch.offers = kept
        restore()
    assert measured == ["gpu-24gb"] and [machine["class"] for machine in seen["deleted"]] == ["gpu-24gb"]
    entry = seen["ledger"][0]
    assert entry["kind"] == "warm" and entry["class"] == "gpu-24gb" and entry["batch"].startswith("warm-gpu-24gb-")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("warm_test: ok")
