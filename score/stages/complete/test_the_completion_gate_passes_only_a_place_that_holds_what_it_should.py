"""Invariant: the completion gate passes only a place that holds what it should. Its gates are tools/usd/complete.py's
checks less resting (the assembly's gate) plus the manifest, one gate two ways in: on a place made here that holds what
it should every gate passes and answers what complete.py answers on the same stage; once its cast shows a person not on
the stage, people fails both ways; a manifest that does not name an input it read fails.

Breaks that turn this red (each applied once and seen red, then reverted):
- __init__.GATE: resting kept (`complete.CHECKS`) -> a_whole_place_passes_every_gate_but_resting
- __init__.gate_check: the likeness and surfaces-check outputs not read (`read = {}`) -> a_whole_place_passes_every_gate_but_resting
- __init__.gate_check: every gate runs complete.py's "rows" check -> a_cast_person_not_on_the_stage_fails_people
- __init__.judge_manifest: `missing = []` -> a_manifest_that_misses_a_read_fails

Run: .venv/bin/python score/stages/complete/test_the_completion_gate_passes_only_a_place_that_holds_what_it_should.py
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
import test_a_place_completes_only_with_every_check_passed_and_current as complete_test  # noqa: E402
import test_each_contents_check_passes_what_holds_and_fails_what_lacks as contents_test  # noqa: E402
import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test  # noqa: E402


# The stage's own list (its docstring, score/CLAUDE.md): the manifest, then complete.py's checks but resting.
WHOLE = {"manifest", "rows", "made_only", "placeholders", "picks", "boxes", "reach", "people", "effects", "motion",
         "crops", "likeness", "painted", "light", "sound", "neighbours", "game", "waiting"}


def answers(folder):
    """{gate: (the stage's answer, complete.py's)} on the assembled stage in folder/stage, each reading the finished
    place's likeness and surfaces-check outputs."""
    outputs = complete_test.finished_outputs(folder, ["crate", "lamp"])
    inputs = {"assembly": folder / "stage", **{node: path for node, path in outputs.items() if path is not None}}
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
        alone = complete.run_check(check.name, resting_test.PLACE, usd, outputs)
        mine = complete.recorded(alone["result"], "")[0] if check.name in complete.EXPERIMENTAL else alone["result"]
        found[check.name] = (verdict.answer, mine)
    return found


def a_whole_place_passes_every_gate_but_resting(folder):
    found = answers(folder)
    problems = []
    if set(found) != WHOLE:
        problems.append(f"the stage's gates are not complete.py's checks less resting: {sorted(found)}")
    problems += [f"{name}: the stage says {mine}, complete.py {theirs}" for name, (mine, theirs) in found.items()
                 if mine != theirs]
    if {mine for mine, _ in found.values()} != {checks.PASS}:
        problems.append(f"a place that holds what it should does not pass every gate: {found}")
    return problems


def a_cast_person_not_on_the_stage_fails_people(folder):
    contents_test.people_mapped(contents_test.BRAM, resting_test.PLACE)
    found = answers(folder)
    return [] if found["people"] == (checks.FAIL, checks.FAIL) else \
        [f"a cast person not on the stage reads {found['people']} (stage, complete.py)"]


def a_manifest_that_misses_a_read_fails(folder):
    out = folder / "manifest-out"
    out.mkdir()
    stage.make_manifest({"assembly": folder / "stage"}, out, 0, {})
    verdict = checks.judge(stage.CHECKS[0], out, {"assembly": folder / "stage", "likeness": folder / "x"}, None)
    return [] if verdict.answer == checks.FAIL else [f"a manifest without the likeness it read reads {verdict.answer}"]


TESTS = (a_whole_place_passes_every_gate_but_resting, a_manifest_that_misses_a_read_fails,
         a_cast_person_not_on_the_stage_fails_people)  # the cast case last: it changes the place's people


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    failures = []
    with tempfile.TemporaryDirectory() as temporary:
        place = pathlib.Path(temporary)
        complete_test.laid(place)
        for test in TESTS:
            found = test(place)
            print(f"{'ok' if not found else 'FAIL'} {test.__name__}")
            failures += found
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
