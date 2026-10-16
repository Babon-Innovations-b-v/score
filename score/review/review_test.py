"""The runner accepts a passing output that is no worse than the accepted one; a worse one waits for the owner's
accept with a reason; his reject moves the accepted output back; his commands run only from his terminal; and a page
shows what its own record says.

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
from score.store import RUNNER, Store  # noqa: E402


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


def test_a_passing_output_is_accepted_by_the_runner_and_a_worse_one_only_by_the_owner_with_a_reason():
    store, data, first = made(1)
    assert store.accepted("tally@hangar") == first and store.current_accept("tally@hangar")["by"] == RUNNER
    _, _, second = made(2, store, data)  # passes, but worse: the runner leaves it
    assert "faults 1 became 2" in refusal(lambda: review.accept(store, "tally@hangar", second, "owner"))
    assert store.accepted("tally@hangar") == first
    written = review.accept(store, "tally@hangar", second, "owner", worse_reason="the second fault is a false alarm")
    assert written["worse"] == ["faults: faults 1 became 2 (lower is better; worse from 1)"]
    assert store.accepted("tally@hangar") == second


def test_the_runner_accepts_within_what_the_owner_allowed_and_no_further():
    """His worse accept records each measure's from and to; a later passing output no worse than the one he took is
    accepted by the runner with his accept named, one beyond it waits for him."""
    store, data, first = made(1)
    _, _, second = made(2, store, data)
    given = review.accept(store, "tally@hangar", second, "owner", worse_reason="two faults are fine here")
    assert given["allowed"] == {"faults": {"faults": {"from": 1, "to": 2}}}, given["allowed"]
    _, _, third = made(1, store, data)  # better: the runner takes it as ever
    _, _, fourth = made("2\n", store, data)  # worse than the third, as bad as the one he took
    assert store.accepted("tally@hangar") == fourth
    assert store.current_accept("tally@hangar")["reason"].startswith("accepted automatically: within the owner's "
                                                                    f"accept of {given['at'][:10]} ({second[:12]})")
    _, _, fifth = made(3, store, data)  # beyond what he allowed
    assert store.accepted("tally@hangar") == fourth


def card(answer, **measures):
    sides = {"halo": "higher", "veil": "lower", "faults": "lower", "lowest clap": "higher", "ferry reach": "lower"}
    return {"heads": {"answer": answer, "measures": measures, "better": {name: sides[name] for name in measures}}}


def test_a_measure_is_worse_only_by_a_step_a_viewer_could_see_and_a_fail_stays_a_fail():
    """A halo 0.01 darker or a veil 0.019 more washed out reads the same; 0.02 is worse. One more fault is worse;
    a score no viewer reads is worse by any move; a 4 mm reach is not, 5 mm is; and an answer that drops is worse
    whatever the measures did."""
    assert review.regressions(card("pass", halo=0.31), card("pass", halo=0.32)) == []
    assert review.regressions(card("pass", veil=0.059), card("pass", veil=0.04)) == []
    assert review.regressions(card("pass", halo=0.30), card("pass", halo=0.32)) != []
    assert review.regressions(card("pass", faults=3), card("pass", faults=2)) != []
    assert review.regressions(card("pass", **{"lowest clap": 0.3760}), card("pass", **{"lowest clap": 0.3761})) != []
    assert review.regressions(card("pass", **{"ferry reach": 0.024}), card("pass", **{"ferry reach": 0.02})) == []
    assert review.regressions(card("pass", **{"ferry reach": 0.026}), card("pass", **{"ferry reach": 0.02})) != []
    assert review.regressions(card("fail", halo=0.33), card("pass", halo=0.32)) == ["heads: pass became fail"]


def test_the_page_shows_the_record_the_gates_and_the_accept():
    store, data, first = made(1)
    text = review.page(store, "tally@hangar").read_text()
    assert "Unverified seed." in text and "an old output brought in" in text
    assert "1 faults, at most 3 pass" in text and "fault 0" in text
    assert "The runner accepted this output automatically" in text
    assert f"score.review reject tally@hangar {first}" in text
    _, _, second = made(2, store, data)
    text = review.page(store, "tally@hangar").read_text()
    assert f"score.review accept tally@hangar {second}</code> --worse" in text
    review.accept(store, "tally@hangar", second, "owner", worse_reason="one fault is a false alarm")
    assert "The owner accepted it" in review.page(store, "tally@hangar").read_text()


def test_an_owners_reject_moves_the_accepted_output_back_and_the_runner_never_takes_it_again():
    store, data, first = made(1)
    _, _, second = made(0, store, data)
    assert store.accepted("tally@hangar") == second  # better: accepted by the runner
    assert "not tally@hangar's accepted output" in refusal(
        lambda: review.reject(store, "tally@hangar", first, "owner", "why"))
    assert "needs a reason" in refusal(lambda: review.reject(store, "tally@hangar", second, "owner", " "))
    review.reject(store, "tally@hangar", second, "owner", "zero faults means the gate saw nothing")
    assert store.accepted("tally@hangar") == first
    assert review.accept_automatically(store, "tally@hangar", second) is None
    graph.Runner([TALLY], graph.World("toy", 1, {"data": data}), store).run(["hangar"])
    assert store.accepted("tally@hangar") == first
    assert "The owner rejected this output." in review.page(store, "tally@hangar").read_text()
    review.accept(store, "tally@hangar", second, "owner", "on a second look it is right")
    assert store.accepted("tally@hangar") == second


def test_the_reject_command_refuses_without_the_owners_terminal():
    store, _, output = made(1)
    found = subprocess.run([sys.executable, "-m", "score.review", "reject", "tally@hangar", output, "--reason", "x"],
                           cwd=REPO, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           env={**os.environ, "PROPS_HOME": tempfile.mkdtemp()})
    assert found.returncode != 0 and "only the owner" in found.stderr, found.stderr


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

def test_a_named_gaps_objects_leave_the_comparison_and_any_other_object_still_blocks():
    """The got-worse comparison is a gate a named gap moves its objects' faults from (overseer 2026-10-16;
    assembly@wreck: resting objects 2 became 3, all three in "wreck: three pieces do not rest"). With the world's own
    wreck gaps: the gap's objects at new faults pass; another object at a new fault still reads worse."""
    def resting(objects, findings):
        return {"resting": {"answer": "pass", "measures": {"objects": objects}, "better": {"objects": "lower"},
                            "findings": findings}}
    old = resting(2, ["/wreck/Objects/leg_strut_1: floats 0.0469: nothing under it",
                      "/wreck/Objects/leg_foot_1: tips 0.2474: its weight falls outside", "/wreck/Objects/crate_1: sunk 0.03: below"])
    named = ["/wreck/Objects/leg_strut_1: tips 0.4439: its weight falls outside",
             "/wreck/Objects/forward_section_1: unstable 0.3228: moves", "/wreck/Objects/crate_1: sunk 0.05: below"]
    saved = review.accepted_card
    review.accepted_card = lambda store, node, output: old
    try:
        judged = {"output": "new", "verdicts": resting(3, named)}
        assert review.worse_than_accepted(None, "assembly@wreck", judged) == []
        judged = {"output": "new", "verdicts": resting(3, named + ["/wreck/Objects/hull_plate_1: tips 0.3: outside"])}
        assert review.worse_than_accepted(None, "assembly@wreck", judged) == [
            "resting: objects 2 became 3 (lower is better; worse from 1)"]
        judged = {"output": "new", "verdicts": resting(3, named)}  # no gap reaches this node's gate
        assert review.worse_than_accepted(None, "assembly@hub", judged) != []
    finally:
        review.accepted_card = saved


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
