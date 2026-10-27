"""tools/usd/motion.py's own rules, free of any place's record: a move before the last one ended is refused, a
looping round that ends open is refused, a light's spans join across rounds and a climb stands still until it lifts.
(The checks of the old places' game motion records went with them, 2026-10-21.)

Breaks that turn each check red (each applied once and seen red, 2026-10-27):
- a_move_before_the_last_ended_is_refused: motion.py's `if seconds < free_at:` made `if False:`.
- a_looping_round_that_ends_open_is_refused: motion.py's `if motion.get("loop") and abs(keys[0][1] - keys[-1][1]) >
  1e-9:` made `if False:`.
- a_lights_spans_join_across_rounds: motion.py's `if spans and abs(spans[-1][1] - begin) < 1e-9:` made `if False:`.
- a_climb_stands_still_until_it_lifts: motion.py's `max(0.0, seconds - float(climb["lift"]))` made
  `seconds - float(climb["lift"])`.

Run: .venv/bin/python tools/usd/test_a_motion_that_cannot_play_is_refused.py
"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import motion  # noqa: E402

DOOR = {"by": [0, -2.8, 0], "speed": 3.0, "starts": "shut"}


def refused(make):
    try:
        make()
    except ValueError:
        return True
    return False


def a_move_before_the_last_ended_is_refused():
    """2.8 m at 3 m/s takes 0.933 s: opening at 1.0 s is open at 1.933 s; shutting again at 1.5 s is refused."""
    keys = motion.slide_keys({**DOOR, "moves": [[1.0, "open"]]})
    assert [(round(moment, 3), share) for moment, share in keys] == [(0.0, 0.0), (1.0, 0.0), (1.933, 1.0)], keys
    assert refused(lambda: motion.slide_keys({**DOOR, "moves": [[1.0, "open"], [1.5, "shut"]]})), \
        "a move before the last one ended was accepted"


def a_looping_round_that_ends_open_is_refused():
    keys = motion.slide_keys({**DOOR, "moves": [[1.0, "open"]]})
    assert refused(lambda: motion.rounds(keys, {"name": "door", "length": 4.0, "loop": True}, 20.0)), \
        "a looping round that ends open was accepted"


def a_lights_spans_join_across_rounds():
    """On 0-1 s and 3-4 s of a 4 s loop: the 3-4 span and the next round's 4-5 span are one, on 3 s to 5 s."""
    switches = motion.light_switches({"name": "beacon", "length": 4.0, "loop": True,
                                      "light": {"on": [[0.0, 1.0], [3.0, 4.0]]}}, 8.0)
    assert switches == [(0.0, 1.0), (1.0, 0.0), (3.0, 1.0), (5.0, 0.0), (7.0, 1.0), (8.0, 0.0)], switches


def a_climb_stands_still_until_it_lifts():
    """Lift at 3 s, net push 24 - 9.81 m/s²: still at 2 s, 0.5 x 14.19 x 1² = 7.095 m at 4 s."""
    climb = {"lift": 3.0, "push": 24.0, "pull": 9.81}
    assert math.isclose(motion.climb_height(climb, 2.0), 0.0)
    assert math.isclose(motion.climb_height(climb, 4.0), 7.095)


CHECKS = (a_move_before_the_last_ended_is_refused, a_looping_round_that_ends_open_is_refused,
          a_lights_spans_join_across_rounds, a_climb_stands_still_until_it_lifts)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failed = 0
    for check in CHECKS:
        try:
            check()
            print(f"ok    {check.__name__}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL  {check.__name__}: {error}")
    sys.exit(1 if failed else 0)
