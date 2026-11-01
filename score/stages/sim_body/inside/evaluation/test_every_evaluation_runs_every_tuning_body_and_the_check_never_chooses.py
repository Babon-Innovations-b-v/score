"""Level 1's runner (#70): an evaluation runs levels 2 and 3 on every tuning body, side by side and no more than
`most` at once, every clip of a body in one process; the check bodies never enter an evaluation, are scored every
few iterations and at the end, and pass within 10 % of the tuning bodies. A toy worker writes each clip's measures;
the solver reads them unrounded, m.json is the rounded copy people read.

Breaks that turn a test red (each seen red once, 2026-10-29):
- run_all's `len(running) < most` made `<= most`: more bodies at once than allowed.
- (2026-11-01) read_back's `if unconverged: return None` made to fall through: a Jacobian set one body's level 3
  did not stop on raises (l1e's s00014 killed level 1); its `raise` for an evaluation dropped: an evaluation reads a
  body missing as nothing wrong.
- by_body's `.setdefault(body_of(case), {})[case]` keyed by case: a body's clips split over processes.
- body_of's TWO_WORD_MOTIONS made `()`: mean_sit_stand reads as body mean_sit, its clips split from mean's and off the split.
- tuning.whole's `checks.append(("end", ...))` dropped: no held-out score at the end.
- accepted's `1 + HELD_OUT_SHARE` made `1`: a check 5 % worse fails.
- (2026-11-01) case_score given back its joints and turns terms: the score is no longer the bones outside alone.
- measured's rest.json write dropped: the worker never sees the group ends' centres (2026-10-29).
- blocked's second `run_all` over `again` dropped: a block the card refused once fails the whole step (2026-10-31).
- measured reading `m.json` for `SOLVED`: the solver is handed the rounded copy (2026-10-29).
- rounded's list branch dropped: a summary's floats reach m.json unrounded (2026-10-29).
- measured_many's folders zipped reversed: a set is handed another set's measures (2026-10-29).
- measured_many's every chunk written from the first sets: a later chunk's sets get the first chunk's measures (2026-10-30).
- measured_many launching one process a chunk again: each body's start-up is repeated every chunk (2026-10-30).
- measured_many launching every body in one process again (by_body dropped), or its second `run_all` over `again`
  dropped: one process holds every body at ~1.3 cores, or a body the card refused once fails the step (2026-10-31).
- sets_command's SAME_SEEDS dropped: the nudged sets start from the base set's angles, not the seeds root's.
- tuning.case_residuals' skin read from "bones outside skin %": level 1 solves on the share, a step, not the
  depth outside (2026-10-30).
- _card_batch.targets_key's landmark rows dropped: a set that moves a landmark's face weights reuses the targets
  of the set before it (2026-10-30).
- (2026-11-01) batched_angles' `if evaluation.SKIN_ROWS` dropped, or fitted_case not passing `evaluation.SKIN_ROWS`
  to fitted_person: level 1's level 3 holds the skin rows, whose jumps between minima its gradient cannot follow;
  sim_body.clip_angles' `skin_rows` defaulting to False: the stage's people lose their skin rows.
- blocked launching one process a case again (`by_body` dropped: level 2 solved from one clip, seven times a body,
  2026-10-31), or exact_stacked stacking the blocks in their given order
  and not sorted as tuning.whole's rows are: a case's exact rows land on another case's residuals (2026-10-30).

Run: .venv/bin/python score/stages/sim_body/inside/evaluation/test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py
(the clip targets' test runs in Newton's own Python, its env's bin/python on this file; the score venv skips it)
"""
import importlib.util
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
             "per group rms deg": {"LeftLeg": 5.0}, "turns deg": [5.0, 6.0, 7.0],
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
        assert evaluation.side_score(found) == 10 / 10  # the bones outside alone (2026-11-01): turns, joints reported
        assert evaluation.reported(found) == {"turns median deg": 5.0, "turns worst group": "LeftLeg 5.00",
                                              "joints median mm": 1.0}
        assert all(value["joints mm"][0] == 1.0000004 for value in found.values())  # the solver's, unrounded


def toy_sets_launch(calls, root, fail_once=()):
    """A toy `measured_many` launch: writes every set's measures (its table) for the body's cases, as the card
    process would; a body in `fail_once` fails its first try."""
    def launch(body, cases):
        command = evaluation.sets_command(sys.executable, "/seeds", root, cases)
        calls.append((body, command))
        if body in fail_once and [called for called, _ in calls].count(body) == 1:
            return subprocess.Popen(["false"])  # the card refused its context once
        for folder in sorted(root.glob("p*/s*")):
            for case in cases:
                (folder / case).mkdir(exist_ok=True)
                (folder / case / "measures.json").write_text((folder / "table.json").read_text())
        return subprocess.Popen(["true"])
    return launch


def test_every_set_of_a_jacobian_runs_in_one_card_process_a_body_and_gets_its_own_measures():
    with tempfile.TemporaryDirectory() as folder:
        root, calls, cases = pathlib.Path(folder) / "jacobian", [], evaluation.picked(CASES, SPLIT, "tuning")
        sets = [({"set": index}, {"marker goal": 1.0}, {"centres": {}}) for index in range(3)]
        found = evaluation.measured_many(sets, cases, root, sys.executable, "/seeds",
                                         launch=toy_sets_launch(calls, root, fail_once=("short",)), free_gb=0)
        assert sorted(body for body, _ in calls) == ["short", "short", "slim", "tall"]  # a failed body once more
        assert all(evaluation.SAME_SEEDS in command and "/seeds" in command for _, command in calls)
        assert all(sorted(given.split("=")[0] for given in command[-2:]) == [f"{body}_kimodo", f"{body}_rigwalk"]
                   for body, command in calls)
        assert [found_set["slim_kimodo"] for found_set in found] == [{"set": index} for index in range(3)]


def test_a_jacobian_over_the_chunk_runs_its_chunks_in_one_process_a_body_each_set_keeping_its_own_measures():
    with tempfile.TemporaryDirectory() as folder:
        root, calls, cases = pathlib.Path(folder) / "jacobian", [], evaluation.picked(CASES, {"tuning": ["tall"]}, "tuning")
        sets = [({"set": index}, {"marker goal": 1.0}, {"centres": {}}) for index in range(5)]
        found = evaluation.measured_many(sets, cases, root, sys.executable, "/seeds",
                                         launch=toy_sets_launch(calls, root), chunk=2, free_gb=0)
        assert len(calls) == 1
        assert sorted(path.parent.name for path in root.glob("p*/s*")) == \
            ["p000", "p000", "p001", "p001", "p002"]
        assert [found_set["tall_kimodo"] for found_set in found] == [{"set": index} for index in range(5)]


def test_a_set_a_body_did_not_converge_on_is_none_for_a_jacobian_and_fails_an_evaluation():
    with tempfile.TemporaryDirectory() as root:
        folder = pathlib.Path(root) / "s00014"
        (folder / "tall_kimodo").mkdir(parents=True)
        (folder / "tall_kimodo" / evaluation.SOLVED).write_text(json.dumps({"joints mm": [1, 2, 3]}))
        (folder / evaluation.UNCONVERGED.format(body="heavy")).write_text("heavy: 1 rows did not stop in 300 steps")
        cases = {"tall_kimodo": "/t.json", "heavy_kimodo": "/h.json"}
        assert evaluation.read_back(folder, cases, {"tall": 0, "heavy": 0}, unconverged=True) is None
        try:
            evaluation.read_back(folder, cases, {"tall": 0, "heavy": 0})
        except RuntimeError as error:
            assert "did not stop" in str(error)
        else:
            raise AssertionError("an evaluation read a body that did not converge as nothing wrong")


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
    if importlib.util.find_spec("mujoco") is None:  # _card_batch imports fit, which needs Newton's own Python
        print("skipped: a clip's targets need MuJoCo (Newton's own Python, score/stages/physics/inside/newton_env.sh)")
        return
    from evaluation import _card_batch
    from landmarks import LANDMARKS, solver_marks
    calls, kept = [], _card_batch.fit.targets
    from fit._skin import PosedSkins
    _card_batch.fit.targets = lambda *given: calls.append(given) or (np.zeros((2, 1, 3, 3)), np.zeros((2, 4, 3)),
                                                                     PosedSkins(np.zeros((2, 3, 3)), [[0, 1, 2]]))
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
    assert not first["tall_kimodo"][1].flags.writeable and not first["tall_kimodo"][2].verts.flags.writeable



def test_the_exact_jacobian_stacks_each_cases_own_block_in_whole_order_then_the_priors_columns():
    from evaluation import level1
    entries = [("ASIS_l", "link", 0, ("pelvis",)), ("ASIS_l", "trust", None, ("pelvis",)),
               ("Hips", "centre", 1, ("pelvis",))]
    cases = {"tall_kimodo": "/jobs/tall/kimodo.json", "heavy_kimodo": "/jobs/heavy/kimodo.json",
             "heavy_rigwalk": "/jobs/heavy/rig.json"}
    with tempfile.TemporaryDirectory() as root:
        out = pathlib.Path(root) / "exact"

        tries = []

        def launch(body, given):
            tries.append((body, sorted(given)))
            if body == "heavy" and len(tries) <= 2:
                return subprocess.Popen(["false"])  # the card refused its context once
            for case, job in given.items():
                np.savez(out / f"{case}.npz", block=np.full((2, len(entries)), float(len(job))))
            return subprocess.Popen(["true"])
        blocks = evaluation.blocked({}, {}, {}, cases, out, "python", "/seeds", launch=launch, free_gb=0)
        jacobian = level1.exact_stacked(blocks, np.zeros(len(entries)), entries)
    by_case = [len(cases[case]) for case in sorted(cases)]
    assert jacobian.shape == (6 + 2, len(entries))
    assert all((jacobian[2 * index:2 * index + 2] == length).all() for index, length in enumerate(by_case))
    assert np.allclose(jacobian[6:], [[tuning.LINK_UNIT / tuning.PRIOR, 0, 0], [0, 0, tuning.LINK_UNIT / tuning.PRIOR]])
    heavy = ["heavy_kimodo", "heavy_rigwalk"]  # one process a body, its every case in it, once more after a failure
    assert sorted(tries) == [("heavy", heavy), ("heavy", heavy), ("tall", ["tall_kimodo"])]


def test_level_1s_level_3_holds_no_skin_rows_and_the_stages_does():
    """Level 1's evaluation solves level 3 without the skin rows (`evaluation.SKIN_ROWS`); the stage holds them."""
    if importlib.util.find_spec("mujoco") is None:  # sim_body and _card_batch import fit, which needs Newton's own Python
        print("skipped: level 3's paths need MuJoCo (Newton's own Python, score/stages/physics/inside/newton_env.sh)")
        return
    import sim_body
    from evaluation import _card_batch, _case
    from fit._skin import PosedSkins
    skins = PosedSkins(np.zeros((2, 3, 3)), [[0, 1, 2]])
    targets = (np.zeros((2, 1, 3, 3)), np.zeros((2, 4, 3)), skins)
    seen = []

    class Clip:
        def angles(self, turns, points, seeds, given=None):
            seen.append(given)
            return np.zeros((len(seeds), 2)), None

    _card_batch.batched_angles(Clip(), ["a"], {"a": np.zeros((2, 2))}, {"a": targets})
    kept = (sim_body.fit.targets, sim_body.fit.angles, sim_body.fitted_person, _case.case_of, _case.written)
    try:
        sim_body.fit.targets = lambda *given: targets
        sim_body.fit.angles = lambda fitting, turns, points, given=None: seen.append(given)
        sim_body.clip_angles(None, None, ["pelvis"], None)
        sim_body.clip_angles(None, None, ["pelvis"], None, skin_rows=False)
        _case.case_of = lambda *given: ({}, {"name": "a"}, None, None)
        sim_body.fitted_person = lambda *given: seen.append(given[5:]) or (None, None, None, None)
        _case.written = lambda *given: None
        _case.fitted_case(pathlib.Path("job.json"), pathlib.Path(tempfile.mkdtemp()), {})
    finally:
        sim_body.fit.targets, sim_body.fit.angles, sim_body.fitted_person, _case.case_of, _case.written = kept
    assert evaluation.SKIN_ROWS is False
    assert seen[0] is None and seen[1] is skins and seen[2] is None and seen[3] == (False,), seen


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
