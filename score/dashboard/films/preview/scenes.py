"""What scene.js draws for a setting animation and a scale zoom, worked out from what exists: the setting's bodies on
their orbits (score/review/overhead.py, frame by frame), the environment plan's sites, blocks and skies, the picked
concepts, and each body's and ground's colour from its library surface (the score_lib cache). Read from the export
the preview's cockpit serves (state.json), so the scenes and the takes show the same state."""
import datetime
import math
import pathlib
import re

from django.conf import settings

from score.dashboard.pages.setting_picture import REACH, disc_size
from score.review import overhead

UNITS = 100.0  # the farthest orbit round the root, in scene units
DIFFUSE = re.compile(r"diffuseColor = \(([^)]*)\)")


def library_folder(kind, entry):
    """The newest version folder of a library entry in the score_lib cache the sync pass fills, or None."""
    root = settings.PROPS_HOME / "cache" / "library" / "score_lib" / kind / entry
    versions = sorted((path for path in root.glob("*") if path.name.isdigit()), key=lambda path: int(path.name))
    return versions[-1] if versions else None


def surface_colour(entry):
    """A library surface's diffuse colour (its material.usda constants), linear RGB; refused when it is not cached."""
    folder = library_folder("surface", entry)
    found = DIFFUSE.search((folder / "material.usda").read_text()) if folder else None
    if not found:
        raise ValueError(f"no library surface {entry!r} in the score_lib cache")
    return [round(float(value) ** (1 / 2.2), 4) for value in found.group(1).split(",")]  # shown as sRGB


def kelvin_colour(kelvin):
    """A star's colour from its temperature (Tanner Helland's fit of the black body), sRGB 0 to 1."""
    heat = kelvin / 100.0
    red = 255.0 if heat <= 66 else 329.698727446 * (heat - 60) ** -0.1332047592
    green = 99.4708025861 * math.log(heat) - 161.1195681661 if heat <= 66 else 288.1221695283 * (heat - 60) ** -0.0755148492
    blue = 255.0 if heat >= 66 else 0.0 if heat <= 19 else 138.5177312231 * math.log(heat - 10) - 305.0447927307
    return [round(min(255.0, max(0.0, value)) / 255.0, 4) for value in (red, green, blue)]


def three(vector):
    """A point on the ecliptic (x to the equinox, z to its north) in the scene's axes (y up)."""
    return [round(float(vector[0]), 4), round(float(vector[2]), 4), round(float(-vector[1]), 4)]


def scales(bodies):
    """{body: scene units a km of its orbit}: the orbits round the root to scale with one another, a moon's ring
    enlarged to read as the setting's picture draws it (setting_picture.system_svg)."""
    by_key = {body["body"]: body for body in bodies}
    root = next(body for body in bodies if not body.get("around"))
    top = [body for body in bodies if body.get("around") == root["body"]]
    farthest = max(body["distance_km"] for body in top)
    found = {body["body"]: UNITS / farthest for body in top}
    for parent in bodies:
        moons = sorted((body for body in bodies if body.get("around") == parent["body"] and parent is not root),
                       key=lambda body: body["distance_km"])
        ring = disc_size(parent) + 22.0
        for turn, moon in enumerate(moons):
            ring += 14.0 * bool(turn)
            found[moon["body"]] = ring * UNITS / REACH / moon["distance_km"]
    assert set(found) | {root["body"]} == set(by_key), "every body but the root has a scale"
    return found


def placed(bodies, day, scale):
    """{body: its scene position} on `day`: each orbit scaled by its own scale round its parent's scene position."""
    found = {body["body"]: [0.0, 0.0, 0.0] for body in bodies if not body.get("around")}
    left = [body for body in bodies if body.get("around")]
    while left:
        for body in [body for body in left if body["around"] in found]:
            offset = three(overhead.orbit_position(body, day) * scale[body["body"]])
            found[body["body"]] = [round(a + b, 4) for a, b in zip(found[body["around"]], offset)]
            left.remove(body)
    return found


def orbit_line(body, day, scale, points=128):
    """Its orbit round its parent over one period from `day`, in scene units relative to the parent."""
    return [three(overhead.orbit_position(body, day + body["period_days"] * step / points) * scale)
            for step in range(points)]


def system(setting, surfaces, end_day, days_per_second, seconds, rate):
    """The setting's bodies, their positions each frame (the clock ending at `end_day`) and their orbits."""
    bodies = setting["bodies"]
    scale = scales(bodies)
    start = end_day - days_per_second * seconds
    frames = max(1, round(seconds * rate))
    shown = [{"key": body["body"], "name": body["name"], "shines": body.get("lux") is not None,
              "size": round(disc_size(body) * UNITS / REACH * 0.55, 3),
              "color": kelvin_colour(body["kelvin"]) if body.get("kelvin") else surface_colour(surfaces[body["body"]])}
             for body in bodies]
    return {"bodies": shown,
            "track": [placed(bodies, start + days_per_second * frame / rate, scale) for frame in range(frames + 1)],
            "orbits": [{"around": body["around"] if body["around"] != shown_root(bodies) else None,
                        "points": orbit_line(body, start, scale[body["body"]])} for body in bodies if body.get("around")]}


def shown_root(bodies):
    return next(body["body"] for body in bodies if not body.get("around"))


def day_of(when):
    return overhead.day_of(when)


def sun_way(sky):
    """The site's sun as a way in its east, north and up, ten long (scene.js's light)."""
    azimuth, altitude = math.radians(sky["sun"]["azimuth"]), math.radians(sky["sun"]["altitude"])
    return [round(10 * value, 4) for value in (math.cos(altitude) * math.sin(azimuth),
                                               math.cos(altitude) * math.cos(azimuth), math.sin(altitude))]


def site_of(state, place):
    """(the environment plan's map holding the place's site, the site)."""
    for world in state["environment_plan"]["plan"]["maps"]:
        for site in world["sites"]:
            if site["place"] == place:
                return world, site
    raise ValueError(f"no site of {place!r} on the environment's plan")


def block_middle(site, name):
    """The middle of a site's named block in the map's metres (east, south), or of the whole site."""
    points = [point for block in site["blocks"] if not name or block["name"] == name for point in block["points"]]
    return [(min(point[0] for point in points) + max(point[0] for point in points)) / 2,
            (min(point[1] for point in points) + max(point[1] for point in points)) / 2]


def ground(state, place, surfaces, into, near_m=400.0):
    """The site and the place from outside: every site of its map within `near_m`, its sun and the worlds in its
    sky, the ground's colour, and the block the camera goes into at the end."""
    world, site = site_of(state, place)
    near = [other for other in world["sites"] if math.dist(other["at"], site["at"]) <= near_m]
    middle = block_middle(site, None)
    return {"place": place, "into": into, "sun": sun_way(site["sky"]), "ground_color": surface_colour(surfaces["ground"]),
            "centre": [site["at"][0] + middle[0], 2.0, site["at"][1] + middle[1]],
            "sky": [{**sky, "color": surface_colour(surfaces[sky["world"]])} for sky in site["sky"]["worlds"]
                    if sky["altitude"] > 0],
            "sites": [{"place": other["place"], "name": other["name"], "at": other["at"], "blocks": other["blocks"]}
                      for other in near]}


def globe(state, place, surfaces):
    """The world the place's site stands on, the site, and its sun in the site's east, north and up."""
    world, site = site_of(state, place)
    return {"name": world["name"], "color": surface_colour(surfaces[world["on"]]), "sun": sun_way(site["sky"]),
            "site": {"name": site["name"], "latitude": site["latitude"], "longitude": site["longitude"]},
            "on": world["on"]}


def picked_url(state, place):
    """The cockpit's link to the place's picked concept, else its card's concept; None when it has neither."""
    sha = state["concept_picked"].get(place)
    if sha:
        return f"/files/{sha}"
    found = state["concepts"].get(place)
    return found["url"] if found else None


def zoom_legs(state, segment, setting, surfaces, end_day, rate):
    """A scale zoom's legs as scene.js draws them, top down."""
    place = segment["shows"]["place"]
    made = []
    for leg in segment["legs"]:
        layer, seconds = leg["layer"], float(leg["seconds"])
        shown = {"layer": layer, "seconds": seconds, "tag": leg.get("tag")}
        if layer == "setting":
            on = site_of(state, place)[0]["on"]
            drawn = system(setting, surfaces, end_day + leg.get("days_per_second", 1.0) * seconds,
                           leg.get("days_per_second", 1.0), seconds + 1.0, rate)
            focus = next(body["size"] for body in drawn["bodies"] if body["key"] == on)
            shown.update(drawn, camera={"focus": on, "distance": 245.0, "end_distance": 3.4 * focus, "start_deg": 200.0,
                                        "turn_deg_per_s": 4.0, "tilt_deg": 38.0, "end_tilt_deg": 10.0})
        elif layer == "world":
            shown.update(globe(state, place, surfaces), from_height=leg.get("from", 4.2), to_height=leg.get("to", 1.05))
        elif layer in ("site", "place"):
            shown.update(ground(state, place, surfaces, leg.get("into")), view="ground",
                         camera=leg.get("camera") or GROUND_PATHS[layer])
        else:
            rooms = leg.get("rooms", [])
            shown["pictures"] = [{"url": picked_url(state, room), "name": room.replace("_", " ").capitalize()}
                                 for room in rooms if picked_url(state, room)]
        made.append(shown)
    return made


# The camera over the site (from high above, down to an oblique look) and round the place (low, turning, then in).
GROUND_PATHS = {"site": {"from_deg": 200.0, "to_deg": 170.0, "from_tilt": 88.0, "to_tilt": 42.0,
                         "from_distance": 520.0, "to_distance": 150.0},
                "place": {"from_deg": 170.0, "to_deg": 120.0, "from_tilt": 42.0, "to_tilt": 20.0,
                          "from_distance": 150.0, "to_distance": 70.0}}


def scene_time(state):
    """The environment plan's scene time as days (overhead's clock), else now."""
    when = state["environment_plan"]["plan"].get("time") or datetime.datetime.now(datetime.timezone.utc).isoformat()
    return day_of(when)


def setting_of(state):
    """The setting the environment concept holds (its bodies filled from the reference table)."""
    return state["environment_concept"]["concept"]["setting"]


def scene_for(state, segment, rate):
    """{legs, rate} of a setting animation or a scale zoom segment."""
    setting, surfaces, end_day = setting_of(state), segment.get("surfaces") or {}, scene_time(state)
    if segment["cut"] == "setting-animation":
        seconds = float(segment["seconds"])
        days = float(segment.get("days_per_second", 30.0))
        camera = {"distance": 245.0, "start_deg": 200.0, "turn_deg_per_s": 4.0, "tilt_deg": 38.0,
                  **(segment.get("camera") or {})}
        leg = {"layer": "setting", "seconds": seconds, "camera": camera, "note": segment.get("note"),
               **system(setting, surfaces, end_day, days, seconds, rate)}
        return {"legs": [leg], "rate": rate}
    return {"legs": zoom_legs(state, segment, setting, surfaces, end_day, rate), "rate": rate}


SCENE_JS = pathlib.Path(__file__).with_name("scene.js")
