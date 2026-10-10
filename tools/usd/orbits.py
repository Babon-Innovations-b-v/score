"""Where the game 2099 has the worlds at a base minute, repeated in numpy (its sim/engine/space/orbits/orbits.gd, with
Pace's and Worlds' numbers): the Moon's and Earth's middles in the one space round the Sun and which way the Moon faces,
so a stage turns its star field as the game does. The game hangs its stars fixed to the one space's axes and turns
them into the drawn frame (sky.gd `_stars_turn`: the frame's facing, transposed); on the Moon the drawn frame is the
Moon's own space, so the stars wheel with the Moon's turning and the hour decides where they stand.

Matrices here act on column vectors, as Godot's Basis does: `facing_at` takes a way in the Moon's own space into the
one space.

    facing_at(minute) -> 3 x 3          the Moon's own space into the one space (Orbits.facing_at)
    centre_at(body, minute) -> (3,)     "moon" or "earth" from the Sun, in metres (Orbits.centre_at)
    stars_turn(minute, frame) -> 3 x 3  the one space into a place's frame (sky.gd `_stars_turn`)
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
MOON_LEAN_DEGREES = 35.0
EARTH_BEARING = -1.98794
LEAN_FROM = (0.42, 0.72, -0.55)

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
UP = np.array([0.0, 1.0, 0.0])


def turn_about(axis, angle):
    """Godot's Basis(axis, angle): a right-handed turn about a unit axis."""
    axis = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) * math.cos(angle) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * np.outer(axis, axis)


def columns(*axes):
    """Godot's Basis(x, y, z): the three axes as its columns."""
    return np.column_stack([np.asarray(axis, dtype=np.float64) for axis in axes])


def seat_frame(out):
    """Seat.at(world, out).frame() with no heading: across, out and along as columns."""
    out = np.asarray(out, dtype=np.float64) / np.linalg.norm(out)
    reference = np.array([0.0, 0.0, 1.0]) if abs(out[2]) <= 0.9 else np.array([1.0, 0.0, 0.0])
    along = reference - out * reference.dot(out)
    along /= np.linalg.norm(along)
    return columns(np.cross(out, along), out, along)


def moon_own_frame():
    """Orbits._moon_own_frame: the Moon's way toward Earth, the way it turns about and the third, in its own space."""
    base = seat_frame(LEAN_FROM)
    bearing = np.array([math.cos(EARTH_BEARING), 0.0, math.sin(EARTH_BEARING)])
    lean = math.radians(MOON_LEAN_DEGREES)
    toward_earth = base @ (bearing * math.cos(lean) + UP * math.sin(lean))
    axis = base @ (UP * math.cos(lean) - bearing * math.sin(lean))
    return columns(toward_earth, axis, np.cross(toward_earth, axis))


def moon_angle(seconds):
    return MOON_ANGLE_AT_START + MOON_RATE * seconds


def facing_at(minute):
    """Orbits.facing_at for the Moon: its own space into the one space at a base minute."""
    toward_earth = (moon_angle(minute * REAL_SECONDS_PER_MINUTE) + math.pi) % (2.0 * math.pi)
    along = np.array([math.cos(toward_earth), 0.0, -math.sin(toward_earth)])
    return columns(along, UP, np.cross(along, UP)) @ moon_own_frame().T


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


def stars_turn(minute, frame):
    """sky.gd `_stars_turn` drawn in a place's frame: the one space into the Moon's own space (the facing, transposed)
    and on into the place's frame (`frame`, the Moon's own space into the place's: its rows the place's axes)."""
    return np.asarray(frame, dtype=np.float64) @ facing_at(minute).T


def sun_way(minute, frame):
    """Which way the true Sun lies from the Moon at a minute, in a place's frame (sky.gd `_toward_the_true_sun`)."""
    toward = -centre_at("moon", minute)
    return stars_turn(minute, frame) @ (toward / np.linalg.norm(toward))


def earth_way(minute, frame):
    """Which way Earth's middle lies from the Moon's at a minute, in a place's frame."""
    toward = centre_at("earth", minute) - centre_at("moon", minute)
    return stars_turn(minute, frame) @ (toward / np.linalg.norm(toward))
