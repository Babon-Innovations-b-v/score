"""Level 1's runner (#70): an evaluation runs levels 2 and 3 on every tuning body, side by side and no more than
`most` at once, every clip of a body in one process; the check bodies never enter an evaluation, are scored every
few iterations and at the end, and pass within 10 % of the tuning bodies. A toy worker writes each clip's measures.

Breaks that turn a test red (each seen red once, 2026-10-29):
- run_all's `len(running) < most` made `<= most`: more bodies at once than allowed.
- by_body's `.setdefault(body_of(case), {})[case]` keyed by case: a body's clips split over processes.
- tuning.whole's `checks.append(("end", ...))` dropped: no held-out score at the end.
- accepted's `1 + HELD_OUT_SHARE` made `1`: a check 5 % worse fails.
- measured's rest.json write dropped: the worker never sees the group ends' centres (2026-10-29).

Run: .venv/bin/python score/stages/sim_body/inside/evaluation/test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import evaluation  # noqa: E402
import tuning  # noqa: E402

CASES = {f"{body}_{clip}": f"/jobs/{body}/{clip}.json" for body in ("tall", "short", "slim", "heavy")
         for clip in ("kimodo", "rigwalk")}
SPLIT = {"tuning": ["tall", "short", "slim"], "check": ["heavy"]}
TOY = """import json, pathlib, sys, time
time.sleep(1.0)
out = pathlib.Path(sys.argv[3])
for given in sys.argv[4:]:
    case = given.split("=")[0]
    (out / case).mkdir()
    (out / case / "m.json").write_text(json.dumps({"per joint mm": {"knee_l": [10, 0]}, "per group deg":
        {"LeftLeg": [5, 0]}, "bones outside all %": 10, "bones outside skin %": {"thigh": 10}, "args": sys.argv[1:]}))
"""


def toy_launch(folder, seen, peaks):
    worker = folder / "toy.py"
    worker.write_text(TOY)
    live = []

    def launch(body, cases):
        live[:] = [process for process in live if process.poll() is None]
        process = subprocess.Popen(evaluation.command(sys.executable, worker, cases, seen["out"])[10:])
        live.append(process)
        peaks.append(len(live))
        seen.setdefault("bodies", []).append((body, sorted(cases)))
        return process
    return launch


def test_an_evaluation_runs_every_tuning_body_once_two_at_most_at_once():
    with tempfile.TemporaryDirectory() as folder:
        out, seen, peaks = pathlib.Path(folder) / "e1", {}, []
        seen["out"] = out
        tuning_cases = evaluation.picked(CASES, SPLIT, "tuning")
        rest = {"centres": {"knee_l": [0.001, 0.0, 0.0]}, "rig": "/rigs/template.npz"}
        found = evaluation.measured({"row": {}}, {"marker goal": 1.0}, rest, tuning_cases, out, sys.executable,
                                    most=2, free_gb=0, launch=toy_launch(pathlib.Path(folder), seen, peaks))
        assert sorted(found) == sorted(tuning_cases)
        assert sorted(body for body, _ in seen["bodies"]) == ["short", "slim", "tall"]
        assert all(cases == [f"{body}_kimodo", f"{body}_rigwalk"] for body, cases in seen["bodies"])
        assert max(peaks) <= 2
        assert json.loads((out / "weights.json").read_text()) == {"marker goal": 1.0}
        assert json.loads((out / "rest.json").read_text()) == rest
        assert evaluation.side_score(found) == 1 + 1 + 1


def test_the_check_is_scored_every_few_iterations_and_at_the_end_and_never_evaluated():
    entries = [("a", "global", None, None), ("b", "global", None, None)]
    evaluated, checked = [], []
    found = {"tall_kimodo": {"per joint mm": {"knee_l": [10, 0]}, "per group deg": {"LeftLeg": [5, 0]},
                             "bones outside skin %": {"thigh": 10}}}

    def evaluate(unknowns):
        evaluated.append(np.array(unknowns))
        moved = {**found["tall_kimodo"], "per group deg": {"LeftLeg": [5 + 4 * (unknowns[0] - 1) ** 2, 0]},
                 "bones outside skin %": {"thigh": 10 + 4 * (unknowns[1] + 1) ** 2}}
        return {"tall_kimodo": moved}

    def check(unknowns):
        checked.append(np.array(unknowns))
        return 1.0
    with tempfile.TemporaryDirectory() as folder:
        result, checks = tuning.whole(evaluate, check, entries, pathlib.Path(folder) / "checkpoint.jsonl", 60,
                                      every=1)
    assert checks[-1][0] == "end" and len(checks) >= 2
    assert np.allclose(checked[-1], result.x)
    assert len(evaluated) > 1


def test_the_held_out_bodies_pass_within_ten_percent():
    assert evaluation.accepted(1.05, 1.0)
    assert not evaluation.accepted(1.11, 1.0)
    assert evaluation.body_of("short_heavy_kimodo") == "short_heavy"


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
