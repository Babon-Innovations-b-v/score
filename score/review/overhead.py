"""What is seen overhead at a site at one moment, worked out from the environment's setting (score/review/setting.py,
decided in its environment concept; the owner, 2026-10-21: no fixed sky, each thing in the form its scale calls for):
every other body where its orbit and the site's body's spin put it, every light (a shining body's, falling off with
the square of its distance; a far light's from its path) and every backdrop. The engine runs the same setting live; the
concept's draw and its blockout take one moment of it, the place's scene time.

    seen(setting, site, when)
        -> {lights: [{name, of, azimuth, altitude, kelvin, lux, across?}],
            bodies: [{body, name, azimuth, altitude, across, lit, lit_from}],
            backdrops: [{name, shape, lux, kelvin?}]}

Degrees throughout: azimuth from north towards east, altitude over the level horizon. A light's `of` is the body that
gives it, None for a far light; the lights brightest first. A body's `across` is its true angular diameter (a shining
body's light carries its own; a far light has none), `lit` the
share of its face the brightest shining body lights as seen from here (0 new, 1 full), `lit_from` the way from the body
to that light in the site's [east, north, up], so a drawing lights its phase from the right side.
"""
import datetime
import math

import numpy as np

from score.review import setting as settings

DAY_ZERO = datetime.datetime(1999, 12, 31, tzinfo=datetime.timezone.utc)  # 2000 Jan 0.0 UT, the orbits' day 0
J2000_DAY = 1.5  # J2000.0 (2000 Jan 1.5 TT, read as UT) in those days: the spins' epoch


def day_of(when):
    """Days since 2000 Jan 0.0 UT of an ISO time (a time with no zone is UT)."""
    moment = datetime.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    moment = moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)
    return (moment - DAY_ZERO).total_seconds() / 86400.0


def unit(vector):
    return np.asarray(vector, dtype=float) / np.linalg.norm(vector)


def node_on(body, day):
    """Its orbit's ascending node on `day`, degrees."""
    return (body.get("node_deg") or 0.0) + (body.get("node_drift_deg_day") or 0.0) * day


def orbit_pole(body, day):
    """The pole of a body's orbit on the ecliptic on `day` (the ecliptic's own for one that orbits nothing)."""
    if not body.get("around"):
        return np.array([0.0, 0.0, 1.0])
    node, tilt = math.radians(node_on(body, day)), math.radians(body["inclination_deg"])
    return np.array([math.sin(tilt) * math.sin(node), -math.sin(tilt) * math.cos(node), math.cos(tilt)])


def orbit_position(body, day):
    """Where its orbit puts a body round what it orbits on `day`, in km on the ecliptic (x to the equinox)."""
    node_drift, periapsis_drift = body.get("node_drift_deg_day") or 0.0, body.get("periapsis_drift_deg_day") or 0.0
    node = math.radians(node_on(body, day))
    tilt = math.radians(body["inclination_deg"])
    periapsis = math.radians((body.get("periapsis_deg") or 0.0) + periapsis_drift * day)
    mean_rate = 360.0 / body["period_days"] - node_drift - periapsis_drift
    size, roundness = body["distance_km"], body["eccentricity"]
    mean = math.radians(((body.get("mean_anomaly_deg") or 0.0) + mean_rate * day) % 360.0)
    eccentric = mean + roundness * math.sin(mean) * (1.0 + roundness * math.cos(mean))
    for _ in range(8):  # Kepler's equation, Newton's steps
        eccentric -= (eccentric - roundness * math.sin(eccentric) - mean) / (1.0 - roundness * math.cos(eccentric))
    across = size * (math.cos(eccentric) - roundness)
    along = size * math.sqrt(1.0 - roundness * roundness) * math.sin(eccentric)
    distance, true = math.hypot(across, along), math.atan2(along, across)
    turn = true + periapsis
    return distance * np.array([
        math.cos(node) * math.cos(turn) - math.sin(node) * math.sin(turn) * math.cos(tilt),
        math.sin(node) * math.cos(turn) + math.cos(node) * math.sin(turn) * math.cos(tilt),
        math.sin(turn) * math.sin(tilt)])


def positions(bodies, day):
    """{body: km from the star on the ecliptic} of every body on `day`."""
    found = {body["body"]: np.zeros(3) for body in bodies if not body.get("around")}
    left = [body for body in bodies if body.get("around")]
    while left:
        placed = [body for body in left if body["around"] in found]
        if not placed:
            raise settings.Refused("a body orbits round in a ring")
        for body in placed:
            found[body["body"]] = found[body["around"]] + orbit_position(body, day)
            left.remove(body)
    return found


def from_equator(vector, obliquity):
    """A way on the J2000 equator turned onto the ecliptic."""
    tilt = math.radians(obliquity)
    return np.array([vector[0], vector[1] * math.cos(tilt) + vector[2] * math.sin(tilt),
                     -vector[1] * math.sin(tilt) + vector[2] * math.cos(tilt)])


def spun(pole, node, meridian):
    """The axes (prime meridian, 90 degrees east of it, pole) of a body turned `meridian` degrees from `node`."""
    turn = math.radians(meridian)
    first = math.cos(turn) * node + math.sin(turn) * np.cross(pole, node)
    return np.column_stack([first, np.cross(pole, first), pole])


def body_frame(by_key, body, places, day):
    """A body's own axes on `day` as columns on the ecliptic: its prime meridian, 90 degrees east of it, its pole.
    Locked: its prime meridian toward the body it faces, its pole its orbit's. A real pole: on the J2000 equator, its
    meridian from that equator's node. Else its pole tilted `tilt_deg` from its orbit's about the orbit's node line,
    its meridian from the node of its equator on its orbit."""
    if body.get("locked_to"):
        pole = orbit_pole(body, day)
        toward = unit(places[body["locked_to"]] - places[body["body"]])
        toward = unit(toward - pole * np.dot(toward, pole))
        return np.column_stack([toward, np.cross(pole, toward), pole])
    meridian = (body.get("meridian_deg") or 0.0) + 360.0 * 24.0 / body["day_hours"] * (day - J2000_DAY)
    if body.get("pole_ra_deg") is not None:
        obliquity = settings.reference()["frame_obliquity_deg"]
        right, rising = math.radians(body["pole_ra_deg"]), math.radians(body["pole_dec_deg"])
        pole = from_equator([math.cos(rising) * math.cos(right), math.cos(rising) * math.sin(right), math.sin(rising)],
                            obliquity)
        return spun(pole, from_equator([-math.sin(right), math.cos(right), 0.0], obliquity), meridian)
    above = orbit_pole(body, day)
    node_way = math.radians(node_on(body, day))
    line = np.array([math.cos(node_way), math.sin(node_way), 0.0])
    tilt = math.radians(body.get("tilt_deg") or 0.0)
    pole = math.cos(tilt) * above + math.sin(tilt) * np.cross(line, above)
    return spun(pole, unit(line - pole * np.dot(line, pole)), meridian)


def site_axes(frame, latitude, longitude):
    """(east, north, up) of a site at `latitude`, `longitude` (degrees, east positive) on a body of axes `frame`."""
    lat, lon = math.radians(latitude), math.radians(longitude)
    up = frame @ np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    east = frame @ np.array([-math.sin(lon), math.cos(lon), 0.0])
    return east, np.cross(up, east), up


def bearing(way, axes):
    """(azimuth, altitude) in degrees of a way, in a site's (east, north, up)."""
    east, north, up = (float(np.dot(way, axis)) for axis in axes)
    return round(math.degrees(math.atan2(east, north)) % 360.0, 2), round(math.degrees(math.asin(up)), 2)


def shining(bodies):
    """The bodies that give light."""
    return [body for body in bodies if body.get("lux") is not None]


def from_body(bodies, on, latitude, longitude, when, height_m=0.0):
    """{lights, bodies} as seen from a site on body `on` at `when` (module docstring): each shining body's light at
    this distance, every other body lit by the brightest of them from here (else by the root body)."""
    day = day_of(when)
    by_key = {body["body"]: body for body in bodies}
    places = positions(bodies, day)
    axes = site_axes(body_frame(by_key, by_key[on], places, day), latitude, longitude)
    eye = places[on] + axes[2] * (by_key[on]["radius_km"] + height_m / 1000.0)
    lights = []
    for star in shining(bodies):
        if star["body"] == on:
            continue
        azimuth, altitude = bearing(unit(places[star["body"]] - eye), axes)
        apart = float(np.linalg.norm(places[star["body"]] - eye))
        lux = star["lux"] * (star["lux_at_km"] / apart) ** 2
        lights.append({"name": star["name"], "of": star["body"], "azimuth": azimuth, "altitude": altitude,
                       "kelvin": star["kelvin"], "lux": float(f"{lux:.4g}"),
                       "across": round(math.degrees(2.0 * math.asin(star["radius_km"] / apart)), 5)})
    lights.sort(key=lambda light: -light["lux"])
    lighter = lights[0]["of"] if lights else next(body["body"] for body in bodies if not body.get("around"))
    found = []
    for other in bodies:
        if other["body"] == on or other.get("lux") is not None:
            continue
        toward = places[other["body"]] - eye
        to_light = unit(places[lighter] - places[other["body"]])
        lit = (1.0 + float(np.dot(to_light, unit(-toward)))) / 2.0
        other_azimuth, other_altitude = bearing(unit(toward), axes)
        found.append({"body": other["body"], "name": other["name"], "azimuth": other_azimuth,
                      "altitude": other_altitude,
                      "across": round(math.degrees(2.0 * math.asin(other["radius_km"] / np.linalg.norm(toward))), 5),
                      "lit": round(lit, 3), "lit_from": [round(float(np.dot(to_light, axis)), 4) for axis in axes]})
    return {"lights": lights, "bodies": found}


def far_light(light, when):
    """A far light at `when` from its path: its height over the year swinging `tilt_deg` either side of the equator
    from the spring equinox, its hour from local noon at that equinox moment."""
    since = day_of(when) - day_of(light["equinox"])
    season = math.radians(light["tilt_deg"]) * math.sin(2.0 * math.pi * since / light["year_days"])
    hour = 2.0 * math.pi * since / (light["day_hours"] / 24.0)
    lat = math.radians(light["latitude"])
    way = np.array([-math.cos(season) * math.sin(hour),  # east, north, up of the light over its ground
                    math.cos(lat) * math.sin(season) - math.sin(lat) * math.cos(season) * math.cos(hour),
                    math.sin(lat) * math.sin(season) + math.cos(lat) * math.cos(season) * math.cos(hour)])
    azimuth, altitude = bearing(way, np.eye(3))
    return {"name": light["name"], "of": None, "azimuth": azimuth, "altitude": altitude, "kelvin": light["kelvin"],
            "lux": light["lux"]}


def seen(setting, site, when):
    """What is seen overhead at `site` at `when` (module docstring); None while its position is not known."""
    _, kind = settings.ground_of(setting, site["on"])
    if kind is None or (kind == "body" and None in (site.get("latitude"), site.get("longitude"))):
        return None
    found = (from_body(setting["bodies"], site["on"], site["latitude"], site["longitude"], when,
                       site.get("height_m") or 0.0) if kind == "body" else {"lights": [], "bodies": []})
    lights = sorted(found["lights"] + [far_light(light, when) for light in setting.get("lights", [])],
                    key=lambda light: -light["lux"])
    backdrops = [{field: backdrop[field] for field in ("name", "shape", "lux", "kelvin") if field in backdrop}
                 for backdrop in setting.get("backdrops", [])]
    return {"lights": lights, "bodies": found["bodies"], "backdrops": backdrops}


