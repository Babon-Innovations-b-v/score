"""The complete stage's gates are tools/usd/complete.py's checks: on a place made here, every gate of the stage answers
what complete.py answers on the same stage, both on a place that holds what it should (all pass) and on one whose cast
shows a person not on the stage (people fails in both).

Run: .venv/bin/python score/stages/complete/complete_test.py
"""
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
# Run as a script, this folder is sys.path[0], and its `library` package would shadow tools/props/library's
# `library` that the export imports bare (palette_library appends that folder, so this one would win).
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
sys.path.insert(0, str(REPO / "tools/review"))
from score import checks  # noqa: E402
from score.stages import complete as stage  # noqa: E402
import complete  # noqa: E402
import complete_test  # noqa: E402
import contents  # noqa: E402
import contents_test  # noqa: E402
import resting_test  # noqa: E402


def answers(folder):
    """{gate: (the stage's answer, complete.py's)} on the assembled stage in folder/stage."""
    inputs = {"assembly": folder / "stage"}
    out = folder / "out"
    out.mkdir(exist_ok=True)
    stage.make_manifest(inputs, out, 0, {})
    usd = stage.assembled_stage(inputs)
    found = {}
    for check in stage.CHECKS:
        verdict = checks.judge(check, out, inputs, None)
        if check.name == "manifest":
            found[check.name] = (verdict.answer, checks.PASS)
            continue
        alone = complete.run_check(check.name, resting_test.PLACE, usd, dict.fromkeys(contents.OUTPUTS))
        mine = complete.recorded(alone["result"], "")[0] if check.name in complete.EXPERIMENTAL else alone["result"]
        found[check.name] = (verdict.answer, mine)
    return found


def gates_agree_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        complete_test.laid(folder)
        problems = []
        found = answers(folder)
        if set(found) != {"manifest", *stage.GATE} or "resting" in found:
            problems.append(f"the stage's gates are not complete.py's checks less resting: {sorted(found)}")
        problems += [f"{name}: the stage says {mine}, complete.py {theirs}" for name, (mine, theirs) in found.items()
                     if mine != theirs]
        if {mine for mine, _ in found.values()} != {checks.PASS}:
            problems.append(f"a place that holds what it should does not pass every gate: {found}")
        contents_test.people_mapped(contents_test.BRAM, resting_test.PLACE)
        found = answers(folder)
        if found["people"] != (checks.FAIL, checks.FAIL):
            problems.append(f"a cast person not on the stage reads {found['people']} (stage, complete.py)")
        return problems


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = gates_agree_both_ways()
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
