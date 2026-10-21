import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score.stages import people_takes  # noqa: E402


def test_a_take_row_a_look_of_the_takes_record():
    looks = json.loads(people_takes.TAKES.read_text())["looks"]
    assert {row.name for row in people_takes.ROWS} == {f"people-take-{look}" for look in looks}
    assert all(row.paid and row.params["outfit"] for row in people_takes.ROWS)


def test_the_crowd_look_has_a_take_row():
    """#26: the crowd's far look is made like every look, by a take row of its own."""
    assert "people-take-kit_m_avg-coat-grey" in {row.name for row in people_takes.ROWS}


def test_the_take_is_kept_in_the_output_not_the_work_folder():
    """#26: the kept take's three files are copied into the output (the store keeps them); the gate reads them there
    and fails a take whose finished model is not in it."""
    import unittest.mock
    with tempfile.TemporaryDirectory() as held:
        pixal, output = pathlib.Path(held) / "pixal", pathlib.Path(held) / "out"
        pixal.mkdir()
        output.mkdir()
        for name in ("pp-a-s1.glb", "pp-a-s1-final.glb"):
            (pixal / name).write_bytes(name.encode())
        (pixal / "pp-a-s1.svviews").mkdir()
        (pixal / "pp-a-s1.svviews" / "input.png").write_bytes(b"close-up")
        with unittest.mock.patch.object(people_takes, "PIXAL", pixal):
            people_takes.stored("pp-a-s1", output / people_takes.TAKE_FILES)
        assert (output / "take" / "pp-a-s1.svviews" / "input.png").read_bytes() == b"close-up"
        (output / "take.json").write_text(json.dumps({"take": "pp-a-s1", "finished": "take/pp-a-s1-final.glb"}))
        take = dict((check.name, check) for check in people_takes.ROWS[0].checks)["take"]
        assert take.judge(output, {}, {}).answer == "pass"
        (output / "take" / "pp-a-s1-final.glb").unlink()
        assert take.judge(output, {}, {}).answer == "fail"


def test_close_ups_pass_with_one_arms_apart_and_unknown_without_a_record():
    with tempfile.TemporaryDirectory() as held:
        output = pathlib.Path(held)
        close_ups = dict((check.name, check) for check in people_takes.ROWS[0].checks)["close-ups"]
        assert close_ups.judge(output, {}, {}).answer == "unknown"
        (output / "closeup").mkdir()
        (output / "closeup" / "checks.json").write_text(json.dumps({"pp-a-s1": {"pass": False},
                                                                   "pp-a-s2": {"pass": True}}))
        assert close_ups.judge(output, {}, {}).answer == "pass"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
