"""What scene.js draws for a setting animation and a scale zoom, worked out from what exists: the setting's bodies on
their orbits (score/review/overhead.py, frame by frame), the environment plan's sites, blocks and skies, the picked
concepts, and each body's and ground's colour from its face (the `body-face-<body>` rows' outputs, in the state's
`body_faces`; a plain colour of its own, said waiting, while its row has not run). Read from the export
the preview's cockpit serves (state.json), so the scenes and the takes show the same state."""
import colorsys
import datetime
import hashlib
import math
import pathlib

from score.dashboard.pages.setting_picture import REACH, disc_size
from score.review import overhead

UNITS = 100.0  # the farthest orbit round the root, in scene units
WAITING = "waiting on the body's surface"


def face_colour(state, body):
    """A body's face colour, sRGB 0 to 1: its face as its `body-face-<body>` row made it (the state's `body_faces`,
    score/stages/surfaces/body_faces.py; never a library name), else a plain colour of its own while that row has
    not run (its leg's tag says WAITING)."""
    face = (state.get("body_faces") or {}).get(body)
    if face:
        return [round(int(face["hex"][at:at + 2], 16) / 255, 4) for at in (1, 3, 5)]
    hue = int(hashlib.sha256(body.encode()).hexdigest()[:4], 16) / 0xFFFF
    return [round(value, 4) for value in colorsys.hls_to_rgb(hue, 0.55, 0.25)]


def tagged(state, leg):
    """The leg with the bodies it draws (its `waits`, taken off) whose face waits on its row named in its tag
    (WAITING), after its own."""
    waits = [body for body in dict.fromkeys(leg.pop("waits", [])) if body not in (state.get("body_faces") or {})]
    said = f"{', '.join(body.capitalize() for body in waits)}: {WAITING}" if waits else None
    return {**leg, "tag": " · ".join(filter(None, (leg.get("tag"), said))) or None}


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


def system(state, setting, end_day, days_per_second, seconds, rate):
    """The setting's bodies, their positions each frame (the clock ending at `end_day`) and their orbits, and the
    bodies drawn by their face (`waits`, for `tagged`)."""
    bodies = setting["bodies"]
    scale = scales(bodies)
    start = end_day - days_per_second * seconds
    frames = max(1, round(seconds * rate))
    shown = [{"key": body["body"], "name": body["name"], "shines": body.get("lux") is not None,
              "size": round(disc_size(body) * UNITS / REACH * 0.55, 3),
              "color": kelvin_colour(body["kelvin"]) if body.get("kelvin") else face_colour(state, body["body"])}
             for body in bodies]
    return {"bodies": shown, "waits": [body["body"] for body in bodies if not body.get("kelvin")],
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


def site_centre(site):
    """The middle of a site's blocks in the ground view's metres, two up."""
    middle = block_middle(site, None)
    return [site["at"][0] + middle[0], 2.0, site["at"][1] + middle[1]]


def ground(state, place, into, sky, near_m=400.0):
    """The site and the place from outside under `sky` (its arrival's): every site of its map within `near_m`, its
    sun and the worlds in its sky, the ground's colour (its body's face), and the block the camera goes into at the
    end."""
    world, site = site_of(state, place)
    near = [other for other in world["sites"] if math.dist(other["at"], site["at"]) <= near_m]
    risen = [shown for shown in sky["worlds"] if shown["altitude"] > 0]
    return {"place": place, "into": into, "sun": sun_way(sky), "ground_color": face_colour(state, world["on"]),
            "centre": site_centre(site), "waits": [world["on"], *(shown["world"] for shown in risen)],
            "sky": [{**shown, "color": face_colour(state, shown["world"])} for shown in risen],
            "sites": [{"place": other["place"], "name": other["name"], "at": other["at"], "blocks": other["blocks"]}
                      for other in near]}


def globe(state, place, sky):
    """The world the place's site stands on, the site, and its sun under `sky` in the site's east, north and up."""
    world, site = site_of(state, place)
    return {"name": world["name"], "color": face_colour(state, world["on"]), "sun": sun_way(sky),
            "waits": [world["on"]],
            "site": {"name": site["name"], "latitude": site["latitude"], "longitude": site["longitude"]},
            "on": world["on"]}


def picked_url(state, place):
    """The cockpit's link to the place's picked concept, else its card's concept; None when it has neither."""
    sha = state["concept_picked"].get(place)
    if sha:
        return f"/files/{sha}"
    found = state["concepts"].get(place)
    return found["url"] if found else None


def setting_camera(leg, drawn, on):
    """The setting leg's camera: from the whole setting in to the body `on`, or, for a leg of the journey naming
    `from_body`, out from that body to its distance apart and in to `on`, close in on each from its sunlit side."""
    size = {body["key"]: body["size"] for body in drawn["bodies"]}
    if not leg.get("from_body"):
        return {"focus": on, "distance": 245.0, "end_distance": 3.4 * size[on], "start_deg": 200.0,
                "turn_deg_per_s": 4.0, "tilt_deg": 38.0, "end_tilt_deg": 10.0}
    away = math.dist(drawn["track"][0][leg["from_body"]], drawn["track"][0][on])
    return {"from": leg["from_body"], "focus": on, "distance": max(1.8 * away, 12.0 * max(size.values())),
            "start_distance": 3.4 * size[leg["from_body"]], "end_distance": 3.4 * size[on], "tilt_deg": 10.0,
            "end_tilt_deg": 10.0, "rise_tilt_deg": 28.0}


def zoom_legs(state, segment, setting, rate):
    """A scale zoom's legs as scene.js draws them, top down (a journey's out and across to the next body first), each
    place at its arrival (`arrival`: the script's `time` for the segment's place, else when its site is lit)."""
    place = segment["shows"]["place"]
    arrivals = {}

    def arrived(shown):
        if shown not in arrivals:
            arrivals[shown] = arrival(state, shown, segment.get("time") if shown == place else None)
        return arrivals[shown]
    end_day = arrived(place)[0]
    made = []
    for leg in segment["legs"]:
        layer, seconds = leg["layer"], float(leg["seconds"])
        shown = {"layer": layer, "seconds": seconds, "tag": leg.get("tag")}
        if layer == "setting":
            days = leg.get("days_per_second", 1.0)
            drawn = system(state, setting, end_day + days * seconds, days, seconds + 1.0, rate)
            shown.update(drawn, camera=setting_camera(leg, drawn, site_of(state, place)[0]["on"]))
        elif layer == "world":
            shown.update(globe(state, leg.get("place", place), arrived(leg.get("place", place))[1]),
                         from_height=leg.get("from", 4.2),
                         to_height=leg.get("to", 1.05))
        elif layer in ("site", "place"):
            shown.update(ground(state, place, leg.get("into"), arrived(place)[1]), view="ground",
                         camera=leg.get("camera") or GROUND_PATHS[layer])
            if leg.get("from_place"):
                shown["from_centre"] = site_centre(site_of(state, leg["from_place"])[1])
        else:
            rooms = leg.get("rooms", [])
            shown["pictures"] = [{"url": picked_url(state, room), "name": room.replace("_", " ").capitalize()}
                                 for room in rooms if picked_url(state, room)]
        made.append(tagged(state, shown))
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


# A scale zoom lands where its site is lit (owner, 2026-10-22, #51): its light at least this high over the horizon,
# looked for hour by hour from the site's scene time over at most this many days (a lunar day is 29.5).
LIT_DEGREES = 20.0
LIT_SEARCH_DAYS = 60


def sky_at(state, place, day):
    """The place's site's sky on `day` from the setting (overhead.seen): its brightest light as `sun` (None when it
    has none) and the other bodies as `worlds`, the shape the environment plan's skies have."""
    world, site = site_of(state, place)
    when = (overhead.DAY_ZERO + datetime.timedelta(days=day)).isoformat()
    seen = overhead.seen(setting_of(state), {**site, "on": world["on"]}, when)
    if seen is None:
        raise ValueError(f"no sky at {place!r}: its site has no place on its ground")
    light = seen["lights"][0] if seen["lights"] else None
    return {"sun": light and {"azimuth": light["azimuth"], "altitude": light["altitude"]},
            "worlds": [{"world": body["body"], **{key: value for key, value in body.items() if key != "body"}}
                       for body in seen["bodies"]]}


def arrival(state, place, named=None):
    """(day, sky) a scale zoom arrives at the place: at `named` (the script's ISO time) when given, else at the first
    hour from its site's scene time (the plan's, else now) when its sun stands LIT_DEGREES up; refused when there is
    none within LIT_SEARCH_DAYS."""
    if named:
        day = day_of(named)
        return day, sky_at(state, place, day)
    start = day_of(site_of(state, place)[1].get("time")) if site_of(state, place)[1].get("time") else scene_time(state)
    for hour in range(24 * LIT_SEARCH_DAYS):
        sky = sky_at(state, place, start + hour / 24.0)
        if sky["sun"] and sky["sun"]["altitude"] >= LIT_DEGREES:
            return start + hour / 24.0, sky
    raise ValueError(f"{place!r}: its site is not lit within {LIT_SEARCH_DAYS} days of its scene time; name a time")


def setting_of(state):
    """The setting the environment concept holds (its bodies filled from the reference table)."""
    return state["environment_concept"]["concept"]["setting"]


def scene_for(state, segment, rate):
    """{legs, rate} of a setting animation or a scale zoom segment."""
    setting, end_day = setting_of(state), scene_time(state)
    if segment["cut"] == "setting-animation":
        seconds = float(segment["seconds"])
        days = float(segment.get("days_per_second", 30.0))
        camera = {"distance": 245.0, "start_deg": 200.0, "turn_deg_per_s": 4.0, "tilt_deg": 38.0,
                  **(segment.get("camera") or {})}
        leg = {"layer": "setting", "seconds": seconds, "camera": camera, "note": segment.get("note"),
               **system(state, setting, end_day, days, seconds, rate)}
        return {"legs": [tagged(state, leg)], "rate": rate}
    return {"legs": zoom_legs(state, segment, setting, rate), "rate": rate}


SCENE_JS = pathlib.Path(__file__).with_name("scene.js")
