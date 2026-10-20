"""Pixal3D's steps by shape (pixal_steps.py): the lock held equal to pixal.py's, P2's list of chunky takes at both
settings, the sort that lowers a shape only when every take sorts the same on every told check, and nothing lowered
without the owner's yes.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/complete/prepare/pixal_steps_test.py
"""
import json
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score.stages.complete.prepare import benchmarks, pixal_steps  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[4]
PASS = {"thin and in proportion": "pass", "outline": "pass", "likeness": "pass"}


def test_the_lock_is_pixals_own_steps():
    text = (REPO / "tools/props/pixal.py").read_text()
    assert re.search(r"^STEPS, GUIDANCE = (\d+), \d+$", text, re.M).group(1) == str(pixal_steps.LOCKED)


def test_the_list_takes_chunky_close_ups_twice_with_one_seed():
    closeups = pathlib.Path(tempfile.mkdtemp())
    rows = [{"id": "crate", "size": [1, 1, 0.8]}, {"id": "pipe", "size": [2, 0.1, 0.1]},
            {"id": "mat", "size": [1, 1, 0.01]}, {"id": "drum", "size": [0.6, 0.9, 0.6]},
            {"id": "lost", "size": [1, 1, 1]}]
    for row in rows[:4]:
        (closeups / f"{row['id']}.png").write_bytes(b"")
    chosen = pixal_steps.chunky_rows(closeups, {"rows": rows})
    assert [row["id"] for row in chosen] == ["crate", "drum"]  # a rod, a sheet and one with no close-up left out
    lines = pixal_steps.benchmark_lines(closeups, chosen)
    assert [line.split()[0] for line in lines] == ["crate-st12", "crate-st8", "drum-st12", "drum-st8"]
    assert all(line.endswith(f"--seed 1 --steps {line.split()[0].split('-st')[1]}") for line in lines)


def test_a_shape_runs_lower_only_when_every_take_sorts_the_same_on_every_told_check():
    same = {row: {12: PASS, 8: PASS} for row in ("a", "b", "c")}
    shapes = dict.fromkeys(same, "solid")
    assert pixal_steps.sorted_same(same, shapes)["solid"]["steps"] == 8
    failed_lower = {**same, "c": {12: PASS, 8: {**PASS, "outline": "fail"}}}
    verdict = pixal_steps.sorted_same(failed_lower, shapes)["solid"]
    assert verdict["steps"] == 12 and "c" in verdict["why"]
    untold = {**same, "b": {12: PASS, 8: {**PASS, "likeness": None}}}
    assert pixal_steps.sorted_same(untold, shapes)["solid"]["why"] == "could not tell: likeness"
    two = {row: arms for row, arms in same.items() if row != "c"}
    assert pixal_steps.sorted_same(two, shapes)["solid"]["steps"] == 12  # under MIN_TAKES measured


def test_both_failing_alike_still_sorts_the_same():
    failing = {**PASS, "thin and in proportion": "fail"}
    sorts = {row: {12: failing, 8: failing} for row in ("a", "b", "c")}
    assert pixal_steps.sorted_same(sorts, dict.fromkeys(sorts, "solid"))["solid"]["steps"] == 8


def test_nothing_runs_lower_without_the_owners_yes():
    assert pixal_steps.OWNER_YES is None and pixal_steps.ADOPTED == {}
    assert pixal_steps.steps_for("solid") == pixal_steps.LOCKED
    assert pixal_steps.record()["adopted"] == {} and pixal_steps.record()["locked"] == 12


def test_p2_is_priced_from_pixals_measured_per_unit_and_listed_at_that():
    per_unit = json.loads((REPO / "data/costs/per-unit.json").read_text())["stages"]["pixal"]
    euros = pixal_steps.benchmark_euros(per_unit, 1.0)
    listed = next(each for each in benchmarks.BENCHMARKS if each["id"] == "P2")
    assert listed["euros"] >= euros["likely_euros"] and benchmarks.total() <= benchmarks.CAP_EUROS
    assert "pixal_steps list" in listed["command"] and "--no-finish" in listed["command"]
    assert not any(each["id"] == "R1" for each in benchmarks.BENCHMARKS)  # its samples ship and no check sorts them


def test_the_sort_measures_both_raw_models_of_each_take_free_and_waits_on_dinov2():
    import numpy as np
    import trimesh
    from PIL import Image
    folder = pathlib.Path(tempfile.mkdtemp())
    models, closeups = folder / "models", folder / "closeups"
    models.mkdir()
    closeups.mkdir()
    rows = []
    for name in ("crate", "drum", "chest"):
        for steps, deep in ((12, 0.9), (8, 0.85)):
            trimesh.creation.box((1.0, 0.8, deep)).export(models / f"{name}-st{steps}.glb")
        picture = np.zeros((256, 256, 4), np.uint8)
        picture[60:200, 50:210] = (120, 90, 60, 255)
        Image.fromarray(picture).save(closeups / f"{name}.png")
        rows.append({"id": name, "size": [1.0, 0.9, 0.8]})
    (folder / "inventory.json").write_text(json.dumps({"place": "hub", "rows": rows}))
    pixal_steps.main(["sort", str(models), str(closeups), str(folder / "inventory.json"), str(folder / "out")])
    result = json.loads((folder / "out/sorted.json").read_text())
    assert set(result["sorts"]) == {"crate", "drum", "chest"}
    assert all(arms[str(steps)]["outline"] in ("pass", "fail") for arms in result["sorts"].values()
               for steps in (12, 8))
    assert result["shapes"]["solid"] == {"steps": 12, "takes": 3, "why": "could not tell: likeness"}  # no scores yet
    assert len(json.loads((folder / "out/pairs.json").read_text())) == 6


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
