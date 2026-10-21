"""Check the game's Earth and Moon pair as repeated here (tools/usd/orbits.py): the two stand opposite each other
about their shared middle, the whole Earth to Moon distance apart, and that middle goes round the Sun at the pair's
distance; a turn about an axis is a true turn that leaves its axis still.

Run: .venv/bin/python tools/usd/orbits_test.py   (make tests runs it with the framework's environment)
"""
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import orbits  # noqa: E402


def main():
    for minute in (0.0, 123.4, 9876.5):
        moon, earth = orbits.centre_at("moon", minute), orbits.centre_at("earth", minute)
        assert math.isclose(np.linalg.norm(moon - earth), orbits.EARTH_TO_MOON_M, rel_tol=1e-9)
        middle = (moon * orbits.MOON_PULL + earth * orbits.EARTH_PULL) / (orbits.MOON_PULL + orbits.EARTH_PULL)
        assert math.isclose(np.linalg.norm(middle), orbits.SUN_TO_EARTH_M, rel_tol=1e-9)
    turn = orbits.turn_about([0.0, 0.0, 2.0], math.pi / 2)
    assert np.allclose(turn @ [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) and np.allclose(turn @ [0.0, 0.0, 1.0], [0, 0, 1])
    print("orbits_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
