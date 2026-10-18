"""The shared gate rules: missing evidence is unknown, unknown blocks like fail, and a worse scorecard shows.

Run: .venv/bin/python score/checks/checks_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks  # noqa: E402


def drop_run_check(answer="pass"):
    return checks.Check("resting", lambda output, inputs, evidence: checks.Verdict("resting", answer, "judged"),
                        evidence="a drop run")


def test_missing_evidence_answers_unknown_without_asking_the_check():
    asked = []
    check = checks.Check("resting", lambda *arguments: asked.append(arguments), evidence="a drop run")
    found = checks.judge(check, "out", {}, None)
    assert found.answer == checks.UNKNOWN and "no evidence" in found.reason
    assert not asked


def test_evidence_present_asks_the_check():
    assert checks.judge(drop_run_check(), "out", {}, "drop.json").answer == checks.PASS


def test_unknown_blocks_like_fail_and_nothing_judged_is_unknown():
    unknown = checks.Verdict("a", checks.UNKNOWN, "no drop run")
    passed = checks.Verdict("b", checks.PASS, "fine")
    failed = checks.Verdict("c", checks.FAIL, "a ship")
    assert checks.overall([passed, unknown]) == checks.UNKNOWN
    assert checks.overall([unknown, failed]) == checks.FAIL
    assert checks.overall([]) == checks.UNKNOWN
    assert checks.blocks(checks.UNKNOWN) and checks.blocks(checks.FAIL) and not checks.blocks(checks.PASS)


def test_a_verdict_without_a_reason_or_with_a_fourth_answer_is_refused():
    for answer, reason in (("pass", " "), ("maybe", "a reason")):
        try:
            checks.Verdict("a", answer, reason)
        except ValueError:
            continue
        raise AssertionError(f"{answer!r}, {reason!r} was taken")


def test_a_check_returning_something_else_than_its_verdict_is_an_error():
    wrong = checks.Check("placeholders", lambda *arguments: checks.Verdict("other", checks.PASS, "fine"))
    try:
        checks.judge(wrong, "out", {}, None)
    except TypeError:
        return
    raise AssertionError("another check's verdict was taken")


def test_a_worse_answer_or_measure_is_a_regression_and_an_equal_one_is_not():
    accepted = checks.scorecard([checks.Verdict("placeholders", checks.PASS, "none", {"faults": 0},
                                                {"faults": "lower"})])
    same = checks.scorecard([checks.Verdict("placeholders", checks.PASS, "none", {"faults": 0}, {"faults": "lower"})])
    more = checks.scorecard([checks.Verdict("placeholders", checks.FAIL, "a ship", {"faults": 12},
                                            {"faults": "lower"})])
    assert checks.regressions(same, accepted) == []
    worse = checks.regressions(more, accepted)
    assert any("pass became fail" in line for line in worse) and any("faults 0 became 12" in line for line in worse)
    assert checks.regressions({}, accepted) == ["placeholders: judged on the accepted output, not on this one"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
