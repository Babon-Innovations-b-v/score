"""An environment's setting (CONTEXT.md "setting"; the owner, 2026-10-21: "an environment is an environment: it can be a
planet, a system of planets, or just a house on some terrain"): what everything in it stands on and in, at the scale
the creator sets, decided in its environment concept (step one) and read from there by the environment's plan and its
blockouts, never from older game data. Each thing in it is present in the form its scale calls for, never a fixed sky
(the owner, 2026-10-21: "when the environment is just one house, the sun is just a big light"): a body moves under the
physics, a light is a far source of light, a backdrop is too far to move. What is seen overhead at a site and a moment
is worked out from these (score/review/overhead.py). No branch names a world.

    {bodies: [body], lights: [light], backdrops: [backdrop], plots: [plot], sites: [site]}

- a **body** moves under the physics (a star, a world, a moon), each optional: `body` its key, `name`, `reference` a
  key of the reference table of real bodies (data/physics/bodies.json, every value cited) whose values it takes for any
  it does not give, else every value given: radius_km, mass_kg (its `gravity` at the surface, m/s², worked out: G mass
  / radius squared), its orbit round `around` (distance_km, period_days, eccentricity, inclination_deg; node_deg,
  periapsis_deg, mean_anomaly_deg at day 0 and the node's and periapsis's drift a day, 0 when not given), its spin
  (day_hours and tilt_deg to its orbit, or `locked_to` the body it keeps facing; a real body's pole_ra_deg,
  pole_dec_deg and meridian_deg, dropped once its day or tilt is set off the table's). A body that shines gives its
  light: `kelvin` (its colour) and `lux` at `lux_at_km` from it, falling off with the square of the distance. The one
  body that orbits nothing is the root the others move round.
- a **light** is a far source of light with no body (a house's sun): `light` its key, `name`, `kelvin`, `lux` (on
  ground facing it) and its path over the day and year: `latitude` of the ground it lights, `tilt_deg` (its swing over
  the year), `day_hours`, `year_days` and `equinox`, a moment of a spring equinox at local noon (ISO).
- a **backdrop** is too far to move (the stars, a distant skyline): `backdrop` its key, `name`, `shape` (`dome` round
  everything, `skyline` round the horizon), the `lux` it gives and its `kelvin` when given.
- a **plot** is a flat piece of ground with no body under it: `plot` its key, `name`, `gravity` in m/s².
- a **site** is where a top place stands: `place`, `on` (a body's or a plot's key), on a body its `latitude`,
  `longitude` (degrees, east positive) and `height_m` over its mean radius, the ground round it curving with that
  radius; on a plot its `x` (east) and `y` (south) in metres and `height_m`.

`checked` puts a setting in this shape (Refused otherwise); `now()` is environment 1's as its data proposes it
(data/physics/setting.json).
"""
import datetime
import json
import math
import re

from score.review import concepts

REFERENCE = concepts.DATA / "physics/bodies.json"
PROPOSED = concepts.DATA / "physics/setting.json"
MOST = 60  # bodies, plots and sites, each
RANGES = {  # a body's numbers and the range each may take
    "radius_km": (1e-6, 1e8), "mass_kg": (0.0, 1e35), "distance_km": (0.0, 1e13), "period_days": (1e-4, 1e10),
    "eccentricity": (0.0, 0.999), "inclination_deg": (-180.0, 180.0), "node_deg": (-360.0, 360.0),
    "node_drift_deg_day": (-10.0, 10.0), "periapsis_deg": (-360.0, 360.0), "periapsis_drift_deg_day": (-10.0, 10.0),
    "mean_anomaly_deg": (-360.0, 360.0), "day_hours": (1e-3, 1e8), "tilt_deg": (0.0, 180.0),
    "pole_ra_deg": (-360.0, 360.0), "pole_dec_deg": (-90.0, 90.0), "meridian_deg": (-360.0, 360.0),
    "kelvin": (500.0, 1e5), "lux": (0.0, 1e12), "lux_at_km": (1e-6, 1e13)}
ORBIT = ("distance_km", "period_days", "eccentricity", "inclination_deg")
POLE = ("pole_ra_deg", "pole_dec_deg", "meridian_deg")
SHINE = ("kelvin", "lux", "lux_at_km")  # a shining body's light: all three or none
PLOT_RANGES = {"gravity": (0.0, 1000.0)}
LIGHT_RANGES = {"kelvin": (500.0, 1e5), "lux": (0.0, 1e12), "latitude": (-90.0, 90.0), "tilt_deg": (0.0, 90.0),
                "day_hours": (1e-3, 1e8), "year_days": (1e-3, 1e10)}
BACKDROP_RANGES = {"lux": (0.0, 1e12), "kelvin": (500.0, 1e5)}
SHAPES = ("dome", "skyline")


class Refused(ValueError):
    """A setting that cannot be kept as given."""


def reference():
    """The reference table of real bodies: {gravity_constant, frame_obliquity_deg, sources, cited, bodies}."""
    return json.loads(REFERENCE.read_text())


def key_of(value):
    """A key from a name: lower case, words joined by _."""
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")[:60]


def number(value, low, high, what):
    """A number in [low, high] from a number or its text (a decimal comma read as a point), None when not given;
    Refused otherwise."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        found = float(str(value).replace(",", ".")) if isinstance(value, str) else float(value)
    except (TypeError, ValueError) as wrong:
        raise Refused(f"{what} is a number, not {value!r}") from wrong
    if isinstance(value, bool) or not math.isfinite(found) or not low <= found <= high:
        raise Refused(f"{what} of {found} is out of {low} to {high}")
    return found


def text(value, what, most=60):
    found = " ".join(str(value or "").split())
    if len(found) > most:
        raise Refused(f"{what} is {len(found)} characters; at most {most}")
    return found


def gravity_of(body, constant):
    """The pull at a body's surface in m/s², 3 decimals: G mass / radius squared."""
    return round(constant * body["mass_kg"] / (body["radius_km"] * 1000.0) ** 2, 3)


def body_given(row):
    """A body's own values from a row, each in range; None for one not given."""
    name = text(row.get("name"), "a body's name")
    found = {"body": key_of(row.get("body") or name), "name": name,
             "reference": key_of(row.get("reference")) or None, "around": key_of(row.get("around")) or None,
             "locked_to": key_of(row.get("locked_to")) or None}
    for field, (low, high) in RANGES.items():
        found[field] = number(row.get(field), low, high, f"{name or found['body']}'s {field}")
    return found


def body_filled(row, table):
    """A body with the reference table's values for those it does not give (its `reference`), its pole dropped once
    its day or tilt is set off the table's; Refused for an unknown reference or a value missing."""
    given = body_given(row)
    real = table["bodies"].get(given["reference"]) if given["reference"] else {}
    if real is None:
        raise Refused(f"no real body {given['reference']!r} in the reference table")
    found = {**{field: real.get(field) for field in (*RANGES, "around", "locked_to", "name")},
             **{field: value for field, value in given.items() if value not in (None, "")}}
    found["body"] = found.get("body") or given["reference"] or key_of(found["name"])
    if real and any(given[field] is not None and given[field] != real.get(field) for field in ("day_hours", "tilt_deg")):
        found.update(dict.fromkeys(POLE))
    if not found["name"] or not found["body"]:
        raise Refused("a body has a name")
    for field in ("radius_km", "mass_kg", *(ORBIT if found["around"] else ())):
        if found.get(field) is None:
            raise Refused(f"{found['name']} has no {field}")
    if any(found.get(field) is not None for field in SHINE) and None in (found.get(field) for field in SHINE):
        raise Refused(f"{found['name']} shines with a kelvin, a lux and the lux_at_km it is measured at, or not at all")
    found["gravity"] = gravity_of(found, table["gravity_constant"])
    return {field: value for field, value in found.items() if value is not None}


def plot_checked(row):
    name = text(row.get("name"), "a plot's name")
    found = {"plot": key_of(row.get("plot") or name), "name": name}
    for field, (low, high) in PLOT_RANGES.items():
        found[field] = number(row.get(field), low, high, f"{name}'s {field}")
        if found[field] is None:
            raise Refused(f"the plot {name or '?'} has no {field}")
    return found


def light_checked(row):
    """A far light with its colour, strength and path; Refused for one missing a value."""
    name = text(row.get("name"), "a light's name")
    found = {"light": key_of(row.get("light") or name), "name": name}
    for field, (low, high) in LIGHT_RANGES.items():
        found[field] = number(row.get(field), low, high, f"{name}'s {field}")
        if found[field] is None:
            raise Refused(f"the light {name or '?'} has no {field}")
    try:
        found["equinox"] = equinox_of(row.get("equinox"))
    except (TypeError, ValueError) as wrong:
        raise Refused(f"the light {name}'s equinox is no moment") from wrong
    return found


def backdrop_checked(row):
    """A backdrop with its shape and the light it gives, its colour when given."""
    name = text(row.get("name"), "a backdrop's name")
    shape = str(row.get("shape") or "dome")
    if shape not in SHAPES:
        raise Refused(f"the backdrop {name}'s shape is one of {', '.join(SHAPES)}, not {shape!r}")
    found = {"backdrop": key_of(row.get("backdrop") or name), "name": name, "shape": shape}
    for field, (low, high) in BACKDROP_RANGES.items():
        found[field] = number(row.get(field), low, high, f"{name}'s {field}")
    if found["lux"] is None:
        raise Refused(f"the backdrop {name or '?'} has no lux")
    return {field: value for field, value in found.items() if value is not None}


def equinox_of(value):
    """An ISO moment as written; ValueError when it is none."""
    datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return str(value)


def site_checked(row, bodies, plots):
    """A site on the body or plot it names, its position in the shape that ground takes."""
    place, on = text(row.get("place"), "a site's place"), key_of(row.get("on"))
    if on in bodies:
        where = {"latitude": number(row.get("latitude"), -90.0, 90.0, f"{place}'s latitude"),
                 "longitude": number(row.get("longitude"), -180.0, 360.0, f"{place}'s longitude")}
    elif on in plots:
        where = {"x": number(row.get("x"), -1e6, 1e6, f"{place}'s x"),
                 "y": number(row.get("y"), -1e6, 1e6, f"{place}'s y")}
    else:
        raise Refused(f"{place or 'a site'} stands on {on or 'nothing'}: no body or plot of the setting")
    return {"place": place, "on": on, **where, "height_m": number(row.get("height_m"), -1e5, 1e5,
                                                                  f"{place}'s height") or 0.0}


def rows(value, what):
    if not isinstance(value, list) or len(value) > MOST or not all(isinstance(row, dict) for row in value):
        raise Refused(f"{what} is a list of at most {MOST} rows")
    return value


def checked(setting, table=None):
    """The setting in its shape (module docstring), every referenced body filled from the table; Refused for one out
    of shape, a body orbiting none of the others, two bodies orbiting nothing, a body holding a site with no spin, or
    two things sharing a key."""
    if not isinstance(setting, dict):
        raise Refused("a setting is an object")
    table = table or reference()
    bodies = [body_filled(row, table) for row in rows(setting.get("bodies") or [], "bodies")
              if row.get("name") or row.get("reference") or row.get("body")]
    plots = [plot_checked(row) for row in rows(setting.get("plots") or [], "plots") if row.get("name") or row.get("plot")]
    lights = [light_checked(row) for row in rows(setting.get("lights") or [], "lights")
              if row.get("name") or row.get("light")]
    backdrops = [backdrop_checked(row) for row in rows(setting.get("backdrops") or [], "backdrops")
                 if row.get("name") or row.get("backdrop")]
    keys = [body["body"] for body in bodies] + [plot["plot"] for plot in plots]
    named = keys + [light["light"] for light in lights] + [backdrop["backdrop"] for backdrop in backdrops]
    if len(set(named)) != len(named):
        raise Refused("two things of the setting share a key")
    for body in bodies:
        for field in ("around", "locked_to"):
            if body.get(field) and body[field] not in keys:
                raise Refused(f"{body['name']}'s {field} {body[field]} is no body of the setting")
    if bodies and sum(1 for body in bodies if not body.get("around")) != 1:
        raise Refused("one body orbits nothing (the root the others move round)")
    by_key = {body["body"]: body for body in bodies}
    sites = [site_checked(row, by_key, {plot["plot"] for plot in plots})
             for row in rows(setting.get("sites") or [], "sites") if row.get("place")]
    for site in sites:
        body = by_key.get(site["on"])
        if body and body.get("around") and not (body.get("locked_to") or body.get("day_hours")):
            raise Refused(f"{body['name']} holds {site['place']} but turns neither by a day nor locked")
    return {"bodies": bodies, "lights": lights, "backdrops": backdrops, "plots": plots, "sites": sites}


def proposed(setting):
    """A model's proposed setting with the values it gave a real body dropped, so the table's stand (the owner: a real
    body's values come from the cited table)."""
    bodies = [{field: row.get(field) for field in ("body", "name", "reference")} if row.get("reference") else row
              for row in (setting.get("bodies") or []) if isinstance(row, dict)]
    return {**setting, "bodies": bodies}


def now(path=PROPOSED):
    """Environment 1's setting as its data proposes it (data/physics/setting.json), checked."""
    return checked(json.loads(path.read_text()))


def ground_of(setting, on):
    """(the body or plot a site stands on, 'body' or 'plot'); (None, None) for none."""
    for body in setting.get("bodies", []):
        if body["body"] == on:
            return body, "body"
    for plot in setting.get("plots", []):
        if plot["plot"] == on:
            return plot, "plot"
    return None, None
