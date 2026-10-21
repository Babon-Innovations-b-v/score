"""Check the motion writers' own rules, free of any place's record: a move before the last one ended is refused,
a looping round that ends open is refused, a light's spans join across rounds and a climb stands still until it
lifts. (The checks of the old places' game motion records went with them, 2026-10-21.)

Run: .venv/bin/python tools/usd/motion_test.py   (make tests runs it with the framework's environment)
"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import motion  # noqa: E402


def check_bad_rounds_are_refused():
    try:
        motion.slide_keys({"by": [0, -2.8, 0], "speed": 3.0, "starts": "shut", "moves": [[1.0, "open"], [1.5, "shut"]]})
    except ValueError:
        pass
    else:
        raise AssertionError("a move before the last one ended was accepted")
    keys = motion.slide_keys({"by": [0, -2.8, 0], "speed": 3.0, "starts": "shut", "moves": [[1.0, "open"]]})
    try:
        motion.rounds(keys, {"name": "door", "length": 4.0, "loop": True}, 20.0)
    except ValueError:
        pass
    else:
        raise AssertionError("a looping round that ends open was accepted")
    switches = motion.light_switches({"name": "beacon", "length": 4.0, "loop": True, "light": {"on": [[0.0, 1.0],
                                                                                                    [3.0, 4.0]]}}, 8.0)
    assert switches == [(0.0, 1.0), (1.0, 0.0), (3.0, 1.0), (5.0, 0.0), (7.0, 1.0), (8.0, 0.0)], switches
    assert math.isclose(motion.climb_height({"lift": 3.0, "push": 24.0, "pull": 9.81}, 2.0), 0.0)
    print("ok  overlapping moves, an unjoined loop refused; a light's spans across rounds joined")


def main():
    check_bad_rounds_are_refused()


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
