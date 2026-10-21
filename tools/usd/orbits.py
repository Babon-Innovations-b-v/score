"""The game 2099's Earth and Moon pair, repeated in numpy (its sim/engine/space/orbits/orbits.gd, with Pace's and
Worlds' numbers): their middles round the Sun at a base minute and the pulls at their faces, as the library's
gravity demos show them (score/stages/library/demo) and the physics trial's scene pulls. Never a scene's sky: what is
overhead is the environment concept's physics (score/review/overhead.py, score/stages/light/sky.py).

    centre_at(body, minute) -> (3,)     "moon" or "earth" from the Sun, in metres (Orbits.centre_at)
    turn_about(axis, angle) -> 3 x 3    Godot's Basis(axis, angle)
"""
import math

import numpy as np

# sim/engine/world/pace.gd and sim/engine/space/worlds.gd.
TICKS_PER_BASE_MINUTE = 5
TICKS_PER_REAL_SECOND = 60
RADIUS = 220.0
PULL = {"moon": 1.62, "earth": 9.81}
# orbits.gd's constants.
SUN_TO_EARTH_M = 120000.0
EARTH_YEAR_MINUTES = 14400
MARS_SUN_TO_M = 192000.0
MOON_SUN_DAYS_PER_WINDOW = 4
MOON_ANGLE_AT_START = 0.0
MOON_TILT_DEGREES = 20.0
MOON_RISING_AT_START = math.radians(72.5)

REAL_SECONDS_PER_MINUTE = TICKS_PER_BASE_MINUTE / TICKS_PER_REAL_SECOND
EARTH_YEAR_S = EARTH_YEAR_MINUTES * REAL_SECONDS_PER_MINUTE
SUN_PULL = 4.0 * math.pi ** 2 * SUN_TO_EARTH_M ** 3 / EARTH_YEAR_S ** 2
EARTH_PULL = PULL["earth"] * RADIUS ** 2
MOON_PULL = PULL["moon"] * RADIUS ** 2
PAIR_RATE = math.sqrt(SUN_PULL / SUN_TO_EARTH_M ** 3)
MARS_RATE = math.sqrt(SUN_PULL / MARS_SUN_TO_M ** 3)
WINDOW_S = 2.0 * math.pi / (PAIR_RATE - MARS_RATE)
MOON_RISING_RATE = MARS_RATE
MOON_TILT = math.radians(MOON_TILT_DEGREES)
MOON_RATE = 2.0 * math.pi * (1.0 / EARTH_YEAR_S + MOON_SUN_DAYS_PER_WINDOW / WINDOW_S)
EARTH_TO_MOON_M = ((EARTH_PULL + MOON_PULL) / MOON_RATE ** 2) ** (1.0 / 3.0)
MOON_OFF_MIDDLE_M = EARTH_TO_MOON_M * EARTH_PULL / (EARTH_PULL + MOON_PULL)
EARTH_OFF_MIDDLE_M = EARTH_TO_MOON_M * MOON_PULL / (EARTH_PULL + MOON_PULL)


def turn_about(axis, angle):
    """Godot's Basis(axis, angle): a right-handed turn about a unit axis."""
    axis = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) * math.cos(angle) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * np.outer(axis, axis)


def moon_angle(seconds):
    return MOON_ANGLE_AT_START + MOON_RATE * seconds


def round_point(distance, angle):
    """Orbits._round: a point on a circle about the middle, going round from +x toward -z."""
    return np.array([distance * math.cos(angle), 0.0, -distance * math.sin(angle)])


def on_moon_circle(distance, seconds):
    """Orbits._on_moon_circle: a place this far off the pair's middle where the Moon stands on its tipped circle."""
    rising = MOON_RISING_AT_START + MOON_RISING_RATE * seconds
    past = moon_angle(seconds) - rising
    along_rising, toward_highest = distance * math.cos(past), distance * math.sin(past)
    level = toward_highest * math.cos(MOON_TILT)
    return np.array([along_rising * math.cos(rising) - level * math.sin(rising), toward_highest * math.sin(MOON_TILT),
                     -along_rising * math.sin(rising) - level * math.cos(rising)])


def centre_at(body, minute):
    """Orbits.centre_at for the Moon or Earth: its middle from the Sun, in metres."""
    seconds = minute * REAL_SECONDS_PER_MINUTE
    pair = round_point(SUN_TO_EARTH_M, PAIR_RATE * seconds)
    if body == "moon":
        return pair + on_moon_circle(MOON_OFF_MIDDLE_M, seconds)
    if body == "earth":
        return pair - on_moon_circle(EARTH_OFF_MIDDLE_M, seconds)
    raise ValueError(f"orbits: no body called {body}")
