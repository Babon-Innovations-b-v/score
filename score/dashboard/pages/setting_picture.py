"""The environment concept page's setting (CONTEXT.md "setting", owner 2026-10-21: "this won't tell anyone anything";
a framework: a sky cannot be defined, it is up to the environment): a picture of it and a short plain card a thing.

- bodies: a system drawn round the body that orbits nothing, the orbits round it to scale with one another, every
  body's size and every orbit round a body other than the root enlarged to read (said under the picture), each site a
  dot on its body where its latitude and longitude put it (a hollow dot on the far side);
- a plot: the ground from above at its metres, each site where its metres put it, and each far light's path over the
  sky (midsummer, the equinox, midwinter) drawn as seen from the ground, the horizon its ring;
- a card a thing: its name, what it is (body, light, backdrop or ground), one line in plain words and the sites on it,
  every raw number only as its hover text.

Hosted builds this too, so no score.review import (and no numpy): `far_way` is score/review/overhead.far_light's sum,
held equal by tests/environment_test.py.
"""
import html
import math

from django.utils.safestring import mark_safe

WIDE, TALL = 640, 420
MIDDLE = (WIDE / 2, TALL / 2)
REACH = 180  # pixels from the middle to the outermost orbit, or to a plot's horizon
GROUND = 90  # pixels from a plot's middle to its edge
KINDS = {"body": "body", "light": "light", "backdrop": "backdrop", "plot": "ground"}


def short(value):
    """A number for a line: whole above 10 with thousands marked, else one decimal; a tiny one as written."""
    if abs(value) >= 10:
        return f"{value:,.0f}"
    return f"{value:.1f}" if abs(value) >= 0.1 else f"{value:g}"


def raw(row, *left_out):
    """A row's every number and name as hover text, `field value` each."""
    return " · ".join(f"{field} {value}" for field, value in row.items()
                      if field not in left_out and value not in (None, ""))


def every(days):
    """'27 days', '1.9 years'."""
    return f"{short(days)} days" if days < 1000 else f"{short(days / 365.25)} years"


def body_line(body, names):
    """One body in plain words: what it orbits and how often, how it turns, its gravity; the root says so."""
    shines = "; gives light" if body.get("lux") is not None else ""
    if not body.get("around"):
        return "the centre the others orbit" + shines
    turn = (f", one face to {names.get(body['locked_to'], body['locked_to'])}" if body.get("locked_to") else
            f", a day of {short(body['day_hours'])} h" if body.get("day_hours") else "")
    return (f"orbits {names.get(body['around'], body['around'])} every {every(body['period_days'])}{turn}; "
            f"gravity {short(body['gravity'])} m/s²{shines}")


def light_line(light):
    return f"a far light crossing the sky every {short(light['day_hours'])} h; {short(light['lux'])} lux"


def backdrop_line(backdrop):
    where = "a dome round everything" if backdrop["shape"] == "dome" else "a skyline round the horizon"
    return f"{where}, giving {short(backdrop['lux'])} lux"


def cards(setting, place_names):
    """[{name, kind, line, tip, sites}] a thing of the setting: bodies, lights, backdrops, then plots."""
    names = {body["body"]: body["name"] for body in setting.get("bodies", [])}
    standing = {}
    for site in setting.get("sites", []):
        standing.setdefault(site["on"], []).append(place_names.get(site["place"], site["place"]))
    found = [{"name": body["name"], "kind": "body", "line": body_line(body, names),
              "tip": raw(body, "body", "name", "cited"), "sites": standing.get(body["body"], [])}
             for body in setting.get("bodies", [])]
    found += [{"name": light["name"], "kind": "light", "line": light_line(light), "tip": raw(light, "light", "name"),
               "sites": []} for light in setting.get("lights", [])]
    found += [{"name": backdrop["name"], "kind": "backdrop", "line": backdrop_line(backdrop),
               "tip": raw(backdrop, "backdrop", "name"), "sites": []} for backdrop in setting.get("backdrops", [])]
    return found + [{"name": plot["name"], "kind": KINDS["plot"],
                     "line": f"flat ground; gravity {short(plot['gravity'])} m/s²", "tip": raw(plot, "plot", "name"),
                     "sites": standing.get(plot["plot"], [])} for plot in setting.get("plots", [])]


def disc_size(body):
    """A body's disc in pixels: grows with the log of its radius, so a star and a moon both read."""
    return min(20.0, max(4.0, 4.0 + 5.0 * math.log10(max(body["radius_km"], 1.0) / 500.0)))


def scene_time(times, site):
    """', scene time <its time on the environment's plan>', '' while it has none."""
    return f", scene time {times[site['place']]}" if times.get(site["place"]) else ""


def site_dots(sites, x, y, size, times, place_names):
    """Each site a dot on its body's disc where its latitude and longitude face (longitude 0 toward the viewer)."""
    found = []
    for site in sites:
        lat, lon = math.radians(site.get("latitude") or 0.0), math.radians(site.get("longitude") or 0.0)
        near = math.cos(lat) * math.cos(lon) >= 0
        dot_x, dot_y = x + size * math.cos(lat) * math.sin(lon), y - size * math.sin(lat)
        name = place_names.get(site["place"], site["place"])
        tip = (f"{name}: latitude {site.get('latitude')}, longitude {site.get('longitude')}, height "
               f"{site.get('height_m', 0)} m" + scene_time(times, site))
        found.append(f'<circle class="sp-site{"" if near else " far"}" cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="2.6">'
                     f'<title>{html.escape(tip)}</title></circle>')
    return found


def system_svg(setting, times, place_names):
    """(the SVG of the setting's bodies round its root, the note on what is enlarged); (None, "") with no bodies."""
    bodies = setting.get("bodies", [])
    if not bodies:
        return None, ""
    by_around = {}
    for body in bodies:
        by_around.setdefault(body.get("around"), []).append(body)
    root = next(iter(by_around.get(None, [])), None)
    if root is None:  # a ring with no root: the setting's check refuses it, so only an unchecked one
        return None, ""
    on = {}
    for site in setting.get("sites", []):
        on.setdefault(site["on"], []).append(site)
    rings, discs, notes = [], [], []
    top = sorted(by_around.get(root["body"], []), key=lambda body: body["distance_km"])
    farthest = max((body["distance_km"] for body in top), default=1.0)

    def disc(body, x, y, side):
        """Its disc, its name below it (`side` False) or to its right, and its sites' dots."""
        size = disc_size(body)
        tip = html.escape(f"{body['name']}: radius {body['radius_km']:g} km")
        label = (f'<text class="sp-name" x="{x:.1f}" y="{y + size + 14:.1f}">' if not side else
                 f'<text class="sp-name side" x="{x + size + 5:.1f}" y="{y + 4:.1f}">')
        discs.append(f'<circle class="sp-body{" shines" if body.get("lux") is not None else ""}" cx="{x:.1f}" '
                     f'cy="{y:.1f}" r="{size:.1f}"><title>{tip}</title></circle>{label}{html.escape(body["name"])}'
                     f'</text>')
        discs.extend(site_dots(on.get(body["body"], []), x, y, size, times, place_names))
        return size

    def draw(body, x, y, side=False):
        """A body and what orbits it, each orbit a ring round it enlarged to read."""
        ring = disc(body, x, y, side) + 22.0
        for turn, moon in enumerate(sorted(by_around.get(body["body"], []), key=lambda found: found["distance_km"])):
            ring += 14.0 * bool(turn)
            true = REACH * moon["distance_km"] / farthest
            notes.append(f"{moon['name']}'s orbit ×{ring / true:,.0f}")
            rings.append(f'<circle class="sp-orbit near" cx="{x:.1f}" cy="{y:.1f}" r="{ring:.1f}"/>')
            angle = math.radians(-40.0 + 70.0 * turn)
            draw(moon, x + ring * math.cos(angle), y + ring * math.sin(angle), side=True)
    for turn, body in enumerate(top):
        radius = max(REACH * body["distance_km"] / farthest, disc_size(root) + 16.0)
        rings.append(f'<circle class="sp-orbit" cx="{MIDDLE[0]}" cy="{MIDDLE[1]}" r="{radius:.1f}"/>')
        angle = math.radians(-30.0 + 360.0 * turn / len(top))
        draw(body, MIDDLE[0] + radius * math.cos(angle), MIDDLE[1] + radius * math.sin(angle))
    disc(root, *MIDDLE, False)
    domes = backdrop_rings(setting, REACH + 24)
    note = " · ".join([f"orbits round {root['name']} to scale" if len(top) > 1 else "", "sizes enlarged to read",
                       *notes])
    return picture(domes + rings + discs, "the physics' bodies"), note.strip(" ·")


def backdrop_rings(setting, radius):
    """Each backdrop as a ring round everything (a dome) or a band at the horizon (a skyline)."""
    return [f'<circle class="sp-backdrop {backdrop["shape"]}" cx="{MIDDLE[0]}" cy="{MIDDLE[1]}" '
            f'r="{radius + 6 * order:.1f}"><title>{html.escape(backdrop["name"] + ": " + backdrop_line(backdrop))}'
            f'</title></circle>' for order, backdrop in enumerate(setting.get("backdrops", []))]


def picture(shapes, label):
    return mark_safe(f'<svg class="sp-picture" viewBox="0 0 {WIDE} {TALL}" role="img" aria-label="{label}">'
                     f'{"".join(shapes)}</svg>')


def far_way(light, since_days):
    """(azimuth, altitude) in degrees of a far light `since_days` after its equinox moment (local noon): overhead.
    far_light's sum."""
    season = math.radians(light["tilt_deg"]) * math.sin(2.0 * math.pi * since_days / light["year_days"])
    hour = 2.0 * math.pi * since_days / (light["day_hours"] / 24.0)
    lat = math.radians(light["latitude"])
    east = -math.cos(season) * math.sin(hour)
    north = math.cos(lat) * math.sin(season) - math.sin(lat) * math.cos(season) * math.cos(hour)
    up = math.sin(lat) * math.sin(season) + math.cos(lat) * math.cos(season) * math.cos(hour)
    return math.degrees(math.atan2(east, north)) % 360.0, math.degrees(math.asin(max(-1.0, min(1.0, up))))


def sky_point(azimuth, altitude):
    """Where a direction falls on the picture seen from the ground: the horizon at the ring, straight up in the
    middle, north up."""
    out = REACH * (90.0 - altitude) / 90.0
    return MIDDLE[0] + out * math.sin(math.radians(azimuth)), MIDDLE[1] - out * math.cos(math.radians(azimuth))


def light_paths(light):
    """A far light's path over one day at midsummer, the equinox and midwinter, each a polyline above the horizon."""
    found = []
    day = light["day_hours"] / 24.0
    noons = {season: round(season * light["year_days"] / day) * day for season in (0.25, 0.0, 0.75)}  # a local noon
    for season, tip in ((0.25, "midsummer"), (0.0, "the equinox"), (0.75, "midwinter")):
        points = [sky_point(*way) for step in range(97)
                  for way in [far_way(light, noons[season] + day * (step / 96 - 0.5))] if way[1] >= 0]
        if len(points) > 1:
            found.append(f'<polyline class="sp-path" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in points)}">'
                         f'<title>{html.escape(light["name"])} over a day at {tip}</title></polyline>')
    noon = sky_point(*far_way(light, noons[0.25]))
    return found + [f'<circle class="sp-body shines" cx="{noon[0]:.1f}" cy="{noon[1]:.1f}" r="7"><title>'
                    f'{html.escape(light["name"])} at midsummer noon</title></circle>']


def plot_svg(setting, plot, times, place_names):
    """The plot from above at its metres, its sites, its compass and horizon, and each far light's path (module
    docstring)."""
    sites = [site for site in setting.get("sites", []) if site["on"] == plot["plot"]]
    reach = max([50.0] + [1.3 * max(abs(site.get("x") or 0.0), abs(site.get("y") or 0.0)) for site in sites])
    scale = GROUND / reach
    shapes = backdrop_rings(setting, REACH + 8)
    shapes.append(f'<circle class="sp-orbit" cx="{MIDDLE[0]}" cy="{MIDDLE[1]}" r="{REACH}"><title>the horizon'
                  f'</title></circle>')
    shapes.append(f'<rect class="sp-ground" x="{MIDDLE[0] - GROUND}" y="{MIDDLE[1] - GROUND}" width="{2 * GROUND}" '
                  f'height="{2 * GROUND}"><title>{html.escape(plot["name"])}: {2 * reach:,.0f} m across</title></rect>')
    for letter, (x, y) in (("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("W", (-1, 0))):
        shapes.append(f'<text class="sp-compass" x="{MIDDLE[0] + x * (REACH + 14)}" '
                      f'y="{MIDDLE[1] + y * (REACH + 14) + 4}">{letter}</text>')
    for light in setting.get("lights", []):
        shapes.extend(light_paths(light))
    for site in sites:
        x, y = MIDDLE[0] + (site.get("x") or 0.0) * scale, MIDDLE[1] + (site.get("y") or 0.0) * scale
        name = place_names.get(site["place"], site["place"])
        tip = (f"{name}: {site.get('x')} m east, {site.get('y')} m south, height {site.get('height_m', 0)} m"
               + scene_time(times, site))
        shapes.append(f'<rect class="sp-plot-site" x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8"><title>'
                      f'{html.escape(tip)}</title></rect><text class="sp-name" x="{x:.1f}" y="{y + 18:.1f}">'
                      f'{html.escape(name)}</text>')
    bar = 10 ** math.floor(math.log10(reach))
    shapes.append(f'<line class="sp-scale" x1="{MIDDLE[0] - GROUND}" y1="{MIDDLE[1] + GROUND + 10}" '
                  f'x2="{MIDDLE[0] - GROUND + bar * scale:.1f}" y2="{MIDDLE[1] + GROUND + 10}"/>'
                  f'<text class="sp-metres" x="{MIDDLE[0] - GROUND + bar * scale / 2:.1f}" '
                  f'y="{MIDDLE[1] + GROUND + 24}">{bar:g} m</text>')
    note = "the ground to scale from above · the sky's directions round it, the horizon the ring"
    return picture(shapes, f"{plot['name']} from above"), note


def view_of(setting, times, place_names):
    """{pictures [{svg, note}], cards} of a setting for the concept page."""
    pictures = []
    system, note = system_svg(setting, times, place_names)
    if system is not None:
        pictures.append({"svg": system, "note": note})
    for plot in setting.get("plots", []):
        svg, note = plot_svg(setting, plot, times, place_names)
        pictures.append({"svg": svg, "note": note})
    return {"pictures": pictures, "cards": cards(setting, place_names)}
