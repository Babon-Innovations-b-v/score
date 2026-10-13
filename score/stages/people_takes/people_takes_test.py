import json
import pathlib
import tempfile

from score.stages import people_takes


def test_a_take_row_a_look_of_the_takes_record():
    looks = json.loads(people_takes.TAKES.read_text())["looks"]
    assert {row.name for row in people_takes.ROWS} == {f"people-take-{look}" for look in looks}
    assert all(row.paid and row.params["outfit"] for row in people_takes.ROWS)


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
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
