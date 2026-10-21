"""The sky over a site at one moment, run from the environment's physics state (data/physics/worlds.json: each world's
true radius, its Kepler elements round what it orbits and its spin; the owner, 2026-10-21: the worlds and the sun are
moving objects driven by the environment's physics, never painted backdrops). A later sky layer runs the same state
live in the engine; the concept's draw and its blockout take one moment of it, the place's scene time.

    bodies()                                   the physics state: {sun, worlds, obliquity} as the data holds it
    sky_at(bodies, world, latitude, longitude, when)
        -> {sun: {azimuth, altitude}, worlds: [{world, name, azimuth, altitude, across, lit, lit_from}]}

Degrees throughout: azimuth from north towards east, altitude over the level horizon, `across` the body's true
angular diameter, `lit` the share of its face the Sun lights as seen from here (0 new, 1 full), `lit_from` the way
from the body to the Sun in the site's [east, north, up], so a drawing lights its phase from the right side.
"""
import datetime
import json
import math

import numpy as np

from score.review import concepts

AU_KM = 149597870.7
EARTH_RADIUS_KM = 6378.14  # the Moon's `a` is in Earth's equatorial radii
UNITS = {"au": AU_KM, "earth_radii": EARTH_RADIUS_KM, "km": 1.0}
DAY_ZERO = datetime.datetime(1999, 12, 31, tzinfo=datetime.timezone.utc)  # 2000 Jan 0.0 UT, the elements' day 0
J2000_DAY = 1.5  # J2000.0 (2000 Jan 1.5 TT, read as UT) in those days: the spins' epoch


def bodies(path=concepts.DATA / "physics/worlds.json"):
    """The environment's physics state as the data holds it: {sun, worlds {world: {name, radius_km, orbit, spin,
    ...}}, obliquity}."""
    found = json.loads(path.read_text())
    return {"sun": found["sun"], "worlds": found["worlds"], "obliquity": found["obliquity"]}


def day_of(when):
    """Days since 2000 Jan 0.0 UT of an ISO time (a time with no zone is UT)."""
    moment = datetime.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    moment = moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)
    return (moment - DAY_ZERO).total_seconds() / 86400.0


def at(element, day):
    return element[0] + element[1] * day


def orbit_position(orbit, day):
    """Where an orbit puts its body round what it orbits on `day`, in km on the ecliptic (x to the equinox)."""
    node, tilt, perihelion = (math.radians(at(orbit[name], day)) for name in ("N", "i", "w"))
    size, roundness = at(orbit["a"], day) * UNITS[orbit["unit"]], at(orbit["e"], day)
    mean = math.radians(at(orbit["M"], day) % 360.0)
    eccentric = mean + roundness * math.sin(mean) * (1.0 + roundness * math.cos(mean))
    for _ in range(8):  # Kepler's equation, Newton's steps
        eccentric -= (eccentric - roundness * math.sin(eccentric) - mean) / (1.0 - roundness * math.cos(eccentric))
    across = size * (math.cos(eccentric) - roundness)
    along = size * math.sqrt(1.0 - roundness * roundness) * math.sin(eccentric)
    distance, true = math.hypot(across, along), math.atan2(along, across)
    turn = true + perihelion
    return distance * np.array([
        math.cos(node) * math.cos(turn) - math.sin(node) * math.sin(turn) * math.cos(tilt),
        math.sin(node) * math.cos(turn) + math.cos(node) * math.sin(turn) * math.cos(tilt),
        math.sin(turn) * math.sin(tilt)])


def positions(state, day):
    """{body: km from the Sun on the ecliptic} of the Sun and every world on `day`."""
    found = {"sun": np.zeros(3)}
    left = dict(state["worlds"])
    while left:
        for world, facts in list(left.items()):
            around = facts["orbit"]["around"]
            if around in found:
                found[world] = found[around] + orbit_position(facts["orbit"], day)
                del left[world]
    return found


def from_equator(vector, obliquity):
    """A way on the J2000 equator turned onto the ecliptic."""
    tilt = math.radians(obliquity)
    return np.array([vector[0], vector[1] * math.cos(tilt) + vector[2] * math.sin(tilt),
                     -vector[1] * math.sin(tilt) + vector[2] * math.cos(tilt)])


def unit(vector):
    return np.asarray(vector, dtype=float) / np.linalg.norm(vector)


def world_frame(state, world, places, day):
    """The world's own axes on `day` as columns on the ecliptic: its prime meridian, 90 degrees east of it, its pole."""
    spin, obliquity = state["worlds"][world]["spin"], at(state["obliquity"], day)
    if "locked" in spin:  # its prime meridian toward what it orbits, its pole its orbit's
        orbit = state["worlds"][world]["orbit"]
        node, tilt = math.radians(at(orbit["N"], day)), math.radians(at(orbit["i"], day))
        pole = np.array([math.sin(tilt) * math.sin(node), -math.sin(tilt) * math.cos(node), math.cos(tilt)])
        toward = unit(places[spin["locked"]] - places[world])
        toward = unit(toward - pole * np.dot(toward, pole))
        return np.column_stack([toward, np.cross(pole, toward), pole])
    right, rising = (math.radians(value) for value in spin["pole"])
    pole = from_equator([math.cos(rising) * math.cos(right), math.cos(rising) * math.sin(right), math.sin(rising)],
                        obliquity)
    node = from_equator([-math.sin(right), math.cos(right), 0.0], obliquity)
    turn = math.radians(at(spin["w"], day - J2000_DAY))
    meridian = math.cos(turn) * node + math.sin(turn) * np.cross(pole, node)
    return np.column_stack([meridian, np.cross(pole, meridian), pole])


def site_axes(frame, latitude, longitude):
    """(east, north, up) of a site at `latitude`, `longitude` (degrees, east positive) on a world of axes `frame`."""
    lat, lon = math.radians(latitude), math.radians(longitude)
    up = frame @ np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    east = frame @ np.array([-math.sin(lon), math.cos(lon), 0.0])
    return east, np.cross(up, east), up


def bearing(way, axes):
    """(azimuth, altitude) in degrees of a way, in a site's (east, north, up)."""
    east, north, up = (float(np.dot(way, axis)) for axis in axes)
    return round(math.degrees(math.atan2(east, north)) % 360.0, 2), round(math.degrees(math.asin(up)), 2)


def sky_at(state, world, latitude, longitude, when):
    """The Sun and every other world as seen from a site on `world` at `when` (module docstring)."""
    day = day_of(when)
    places = positions(state, day)
    axes = site_axes(world_frame(state, world, places, day), latitude, longitude)
    eye = places[world] + axes[2] * state["worlds"][world]["radius_km"]
    azimuth, altitude = bearing(unit(places["sun"] - eye), axes)
    found = []
    for other, facts in state["worlds"].items():
        if other == world:
            continue
        toward, to_sun = places[other] - eye, unit(places["sun"] - places[other])
        lit = (1.0 + float(np.dot(to_sun, unit(-toward)))) / 2.0
        other_azimuth, other_altitude = bearing(unit(toward), axes)
        found.append({"world": other, "name": facts["name"], "azimuth": other_azimuth, "altitude": other_altitude,
                      "across": round(math.degrees(2.0 * math.asin(facts["radius_km"] / np.linalg.norm(toward))), 5),
                      "lit": round(lit, 3), "lit_from": [round(float(np.dot(to_sun, axis)), 4) for axis in axes]})
    return {"sun": {"azimuth": azimuth, "altitude": altitude}, "worlds": found}
