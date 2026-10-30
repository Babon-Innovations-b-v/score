"""Level 1's runner (#70): an evaluation runs levels 2 and 3 on every tuning body, side by side and no more than
`most` at once, every clip of a body in one process; the check bodies never enter an evaluation, are scored every
few iterations and at the end, and pass within 10 % of the tuning bodies. A toy worker writes each clip's measures;
the solver reads them unrounded, m.json is the rounded copy people read.

Breaks that turn a test red (each seen red once, 2026-10-29):
- run_all's `len(running) < most` made `<= most`: more bodies at once than allowed.
- by_body's `.setdefault(body_of(case), {})[case]` keyed by case: a body's clips split over processes.
- body_of's TWO_WORD_MOTIONS made `()`: mean_sit_stand reads as body mean_sit, its clips split from mean's and off the split.
- tuning.whole's `checks.append(("end", ...))` dropped: no held-out score at the end.
- accepted's `1 + HELD_OUT_SHARE` made `1`: a check 5 % worse fails.
- measured's rest.json write dropped: the worker never sees the group ends' centres (2026-10-29).
- measured reading `m.json` for `SOLVED`: the solver is handed the rounded copy (2026-10-29).
- rounded's list branch dropped: a summary's floats reach m.json unrounded (2026-10-29).
- measured_many's folders zipped reversed: a set is handed another set's measures (2026-10-29).
- measured_many's every chunk written from the first sets: a later chunk's sets get the first chunk's measures (2026-10-30).
- measured_many launching one process a chunk again: each body's start-up is repeated every chunk (2026-10-30).
- sets_command's SAME_SEEDS dropped: the nudged sets start from the base set's angles, not the seeds root's.
- tuning.case_residuals' skin read from "bones outside skin %": level 1 solves on the share, a step, not the
  depth outside (2026-10-30).
- _card_batch.targets_key's landmark rows dropped: a set that moves a landmark's face weights reuses the targets
  of the set before it (2026-10-30).

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
    found = {"per joint mm": {"knee_l": [10, 0]}, "per group deg": {"LeftLeg": [5, 0]}, "bones outside all %": 10,
             "bones outside skin %": {"thigh": 10}, "joints mm": [1.0000004, 2.0, 3.0], "args": sys.argv[1:]}
    (out / case / "measures.json").write_text(json.dumps(found))
    (out / case / "m.json").write_text(json.dumps({**found, "joints mm": [1.0, 2.0, 3.0]}))
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
        assert all(value["joints mm"][0] == 1.0000004 for value in found.values())  # the solver's, unrounded


def toy_sets_launch(calls):
    def launch(command, log):
        calls.append(command)
        root, cases = pathlib.Path(command[command.index(str(evaluation.SETS_WORKER)) + 2]), command[-2:]
        for folder in sorted(root.glob("p*/s*")):
            for case in (given.split("=")[0] for given in cases):
                (folder / case).mkdir()
                (folder / case / "measures.json").write_text((folder / "table.json").read_text())
        return 0
    return launch


def test_every_set_of_a_jacobian_runs_in_one_card_process_and_gets_its_own_measures():
    with tempfile.TemporaryDirectory() as folder:
        calls, cases = [], evaluation.picked(CASES, {"tuning": ["tall"]}, "tuning")
        sets = [({"set": index}, {"marker goal": 1.0}, {"centres": {}}) for index in range(3)]
        found = evaluation.measured_many(sets, cases, pathlib.Path(folder) / "jacobian", sys.executable,
                                         "/seeds", launch=toy_sets_launch(calls))
        assert len(calls) == 1 and evaluation.SAME_SEEDS in calls[0] and "/seeds" in calls[0]
        assert [found_set["tall_kimodo"] for found_set in found] == [{"set": index} for index in range(3)]


def test_a_jacobian_over_the_chunk_runs_its_chunks_in_one_process_each_set_keeping_its_own_measures():
    with tempfile.TemporaryDirectory() as folder:
        calls, cases = [], evaluation.picked(CASES, {"tuning": ["tall"]}, "tuning")
        sets = [({"set": index}, {"marker goal": 1.0}, {"centres": {}}) for index in range(5)]
        found = evaluation.measured_many(sets, cases, pathlib.Path(folder) / "jacobian", sys.executable,
                                         "/seeds", launch=toy_sets_launch(calls), chunk=2)
        assert len(calls) == 1
        assert sorted(path.parent.name for path in (pathlib.Path(folder) / "jacobian").glob("p*/s*")) == \
            ["p000", "p000", "p001", "p001", "p002"]
        assert [found_set["tall_kimodo"] for found_set in found] == [{"set": index} for index in range(5)]


def test_the_copy_people_read_is_rounded_and_the_solvers_is_not():
    measures = {"joints mm": [1.234567, 2.0, 3.98765], "per joint mm": {"knee_l": [10.4444, 0.0]},
                "bones outside all %": 4.5771234, "fit seconds": 12, "recordings": ["/a.npz"]}
    assert evaluation.rounded(measures) == {"joints mm": [1.23, 2.0, 3.99], "per joint mm": {"knee_l": [10.44, 0.0]},
                                            "bones outside all %": 4.58, "fit seconds": 12, "recordings": ["/a.npz"]}
    assert measures["joints mm"][0] == 1.234567


def test_the_check_is_scored_every_few_iterations_and_at_the_end_and_never_evaluated():
    entries = [("a", "global", None, None), ("b", "global", None, None)]
    evaluated, checked = [], []
    found = {"tall_kimodo": {"per joint mm": {"knee_l": [10, 0]}, "per group deg": {"LeftLeg": [5, 0]},
                             "per joint rms mm": {"knee_l": 10}, "per group rms deg": {"LeftLeg": 5},
                             "bones outside depth mm": {"thigh": 10}}}

    def evaluate(unknowns):
        evaluated.append(np.array(unknowns))
        moved = {**found["tall_kimodo"], "per group rms deg": {"LeftLeg": 5 + 4 * (unknowns[0] - 1) ** 2},
                 "bones outside depth mm": {"thigh": 10 + 4 * (unknowns[1] + 1) ** 2}}
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
    assert evaluation.body_of("short_heavy_sit_stand") == "short_heavy"
    assert evaluation.body_of("mean_arms_raise") == "mean"


def test_a_clips_targets_are_made_once_per_landmark_set_and_never_written_in_place():
    from evaluation import _card_batch
    from landmarks import LANDMARKS, solver_marks
    calls, kept = [], _card_batch.fit.targets
    _card_batch.fit.targets = lambda *given: calls.append(given) or (np.zeros((2, 1, 3, 3)), np.zeros((2, 4, 3)))
    rig = {"names": np.array(["root"]), "bind": np.eye(4)[None]}
    clips = {"tall_kimodo": (None, {"segments": ["pelvis"]}, rig, np.zeros((2, 1, 4, 4)))}
    name, row = solver_marks()[0], LANDMARKS[solver_marks()[0]]
    try:
        _card_batch.TARGETS.clear()
        first = _card_batch.clip_targets(clips)
        again = _card_batch.clip_targets(clips)
        LANDMARKS[name] = (row[0], tuple(np.asarray(row[1]) + 1e-3), *row[2:])
        moved = _card_batch.clip_targets(clips)
    finally:
        LANDMARKS[name], _card_batch.fit.targets = row, kept
        _card_batch.TARGETS.clear()
    assert len(calls) == 2 and again["tall_kimodo"] is first["tall_kimodo"] and moved["tall_kimodo"] is not first["tall_kimodo"]
    assert not first["tall_kimodo"][1].flags.writeable


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
