"""Only a passing output that is no worse than the accepted one can be accepted, only from the owner's terminal, and
its page shows what its own record says.

Run: .venv/bin/python score/review/review_test.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph, review  # noqa: E402
from score.store import Store  # noqa: E402


def make_tally(inputs, out, seed, params):
    (out / "tally.txt").write_text(inputs["tally"].read_text())
    (out / "origin.json").write_text(json.dumps({"seed": True, "from": str(inputs["tally"]),
                                                 "note": "an old output brought in"}))


def judge_tally(output, inputs, evidence):
    faults = int((output / "tally.txt").read_text())
    return checks.Verdict("faults", checks.PASS if faults <= 3 else checks.FAIL, f"{faults} faults, at most 3 pass",
                          {"faults": faults}, {"faults": "lower"}, tuple(f"fault {number}" for number in range(faults)))


TALLY = graph.Stage("tally", "place", make_tally, contracts.Contract("toy-tally", 1, lambda folder: []),
                    (checks.Check("faults", judge_tally),),
                    files={"tally": "{data}/{place}.txt"})


def made(faults, store=None, data=None):
    """Run the tally stage on a place with that many faults; the store, the data folder and the output."""
    data = data or pathlib.Path(tempfile.mkdtemp())
    store = store or Store.in_folder(tempfile.mkdtemp())
    (data / "hangar.txt").write_text(str(faults))
    graph.Runner([TALLY], graph.World("toy", 1, {"data": data}), store).run(["hangar"])
    return store, data, review.record_of(store, "tally@hangar")["output"]


def refusal(call):
    try:
        call()
    except review.Refused as refused:
        return str(refused)
    raise AssertionError("taken")


def test_an_output_that_did_not_pass_cannot_be_accepted():
    store, _, output = made(5)
    assert "answered fail" in refusal(lambda: review.accept(store, "tally@hangar", output, "owner"))
    assert store.accepted("tally@hangar") is None


def test_a_passing_output_is_accepted_and_a_worse_one_only_with_a_reason():
    store, data, first = made(1)
    review.accept(store, "tally@hangar", first, "owner")
    assert store.accepted("tally@hangar") == first
    _, _, second = made(2, store, data)
    assert "faults 1 became 2" in refusal(lambda: review.accept(store, "tally@hangar", second, "owner"))
    assert store.accepted("tally@hangar") == first
    written = review.accept(store, "tally@hangar", second, "owner", worse_reason="the second fault is a false alarm")
    assert written["worse"] == ["faults: faults 1 became 2 (lower is better)"]
    assert store.accepted("tally@hangar") == second


def test_the_page_shows_the_record_the_gates_and_the_accept():
    store, _, output = made(2)
    text = review.page(store, "tally@hangar").read_text()
    assert "Unverified seed." in text and "an old output brought in" in text
    assert "2 faults, at most 3 pass" in text and "fault 1" in text
    assert f"score.review accept tally@hangar {output}" in text
    review.accept(store, "tally@hangar", output, "owner")
    assert "The owner accepted this output." in review.page(store, "tally@hangar").read_text()


def test_a_failed_output_page_offers_no_accept():
    store, _, _ = made(9)
    text = review.page(store, "tally@hangar").read_text()
    assert "It cannot be accepted" in text and "score.review accept" not in text


def test_the_accept_command_refuses_without_the_owners_terminal():
    store, _, output = made(1)
    found = subprocess.run([sys.executable, "-m", "score.review", "accept", "tally@hangar", output], cwd=REPO,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           env={**os.environ, "PROPS_HOME": tempfile.mkdtemp()})
    assert found.returncode != 0 and "only the owner" in found.stderr, found.stderr


def test_a_waived_gate_lets_its_output_be_accepted_for_that_key_only():
    """Fault (review of step 0, 2026-10-11): the hook guarded waivers/, but nothing wrote or read a waiver, so the
    owner had no way to let a gate he judged wrong pass."""
    store, data, output = made(5)
    key = review.record_of(store, "tally@hangar", output)["key"]
    assert "needs a reason" in refusal(lambda: review.waive(store, "tally@hangar", key, "faults", "owner", " "))
    assert "has no check" in refusal(lambda: review.waive(store, "tally@hangar", key, "tilt", "owner", "why"))
    review.waive(store, "tally@hangar", key, "faults", "owner", "the five are one fault seen five times")
    review.accept(store, "tally@hangar", output, "owner")
    assert store.accepted("tally@hangar") == output
    text = review.page(store, "tally@hangar").read_text()
    assert "Waived by owner" in text and "seen five times" in text
    _, _, later = made(6, store, data)  # a new key: the waiver does not carry over
    assert "answered fail" in refusal(lambda: review.accept(store, "tally@hangar", later, "owner"))


def test_the_waive_command_refuses_without_the_owners_terminal():
    store, _, output = made(5)
    found = subprocess.run([sys.executable, "-m", "score.review", "waive", "tally@hangar", "k", "faults",
                            "--reason", "x"], cwd=REPO, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           env={**os.environ, "PROPS_HOME": tempfile.mkdtemp()})
    assert found.returncode != 0 and "only the owner" in found.stderr, found.stderr

if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
