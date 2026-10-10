"""Check the game's orbits as repeated here (tools/usd/orbits.py): the Moon's facing a true turn, back where it was
after a lap, Earth over the base rising and sinking between the heights the game measured (#114: 5.3 to 48.6 degrees),
the true Sun over the base never higher than the Moon's lean lets it, and the stars turned by the facing.

Run: .venv/bin/python tools/usd/orbits_test.py   (make tests runs it with the framework's environment)
"""
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import orbits  # noqa: E402

LAP_MINUTES = 2.0 * math.pi / orbits.MOON_RATE / orbits.REAL_SECONDS_PER_MINUTE


def heights_over_the_base(minutes):
    """Earth's and the Sun's height over the base seat (LEAN_FROM), degrees, at each minute."""
    up = np.asarray(orbits.LEAN_FROM) / np.linalg.norm(orbits.LEAN_FROM)
    earth, sun = [], []
    for minute in minutes:
        facing = orbits.facing_at(minute)
        toward = facing.T @ (orbits.centre_at("earth", minute) - orbits.centre_at("moon", minute)) - up * orbits.RADIUS
        earth.append(math.degrees(math.asin(toward @ up / np.linalg.norm(toward))))
        sunward = facing.T @ -orbits.centre_at("moon", minute)
        sun.append(math.degrees(math.asin(sunward @ up / np.linalg.norm(sunward))))
    return np.array(earth), np.array(sun)


def main():
    facing = orbits.facing_at(1234.5)
    assert np.allclose(facing @ facing.T, np.eye(3), atol=1e-9) and np.isclose(np.linalg.det(facing), 1.0)
    assert np.allclose(orbits.stars_turn(100.0, np.eye(3)), orbits.stars_turn(100.0 + LAP_MINUTES, np.eye(3)),
                       atol=1e-6)
    assert not np.allclose(orbits.stars_turn(100.0, np.eye(3)), orbits.stars_turn(100.0 + LAP_MINUTES / 4,
                                                                                     np.eye(3)), atol=0.1)
    earth, sun = heights_over_the_base(np.arange(0.0, 20000.0, 5.0))
    assert abs(earth.min() - 5.3) < 0.1 and abs(earth.max() - 48.6) < 0.1, (earth.min(), earth.max())
    assert sun.max() < 90.0 - orbits.MOON_LEAN_DEGREES + 0.5, sun.max()
    frame = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
    assert np.allclose(orbits.sun_way(50.0, frame), frame @ orbits.sun_way(50.0, np.eye(3)), atol=1e-9)
    print("orbits_test: ok")


if __name__ == "__main__":
    main()
