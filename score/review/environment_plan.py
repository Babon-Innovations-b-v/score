"""The environment's plan (CONTEXT.md "environment plan"; the owner, 2026-10-21): the environment is the first parent,
so its concept gets a plan of its own, as every place's does, and each top place's concept is drawn on the blockout
of its site there (score/review/blockout.py). One map a ground of its setting (score/review/setting.py, the
environment concept's: a body, at its true radius, or a plot), each top place's site on it where the setting puts it
(its latitude, longitude and height on a body, metres on a plot), its footprint and rough size, its blocks, the ground
and terrain heights round it and its scene time; the true distances between sites on the same ground; and the
setting, from which what is seen overhead at each site at its scene time is worked out (score/review/overhead.py),
never written by hand: every other body at its true direction, size and phase, every light and backdrop. The engine
runs the same setting live. The game 2099's ground plans (data/ground/plan/<ground>.json) are read only as the layout
of a site's parts in metres (the Base's modules), never for a ground's size or a site's place.

It is made like a place's plan: what data already says is worked out free (`facts_of`: each site's place and parts,
the fall of its ground's curve round it); Gemini 3.1 Pro writes the rest (`write`: one direct call through the plan
writer's own call, score/review/plan_writing.py, run without asking under the owner's standing allowance of
2026-10-21 for plan writing); the code then checks it, keeps the fixed facts over the answer, and works out the
distances and what each site sees overhead (`settled`). Until it is written the plan shown is the free one
(`derived`). He fixes it on its plan page (a site's time and size), his edit kept as his own and settled again;
where a site stands is the environment concept's. A writing or edit records the environment concept's version it
was made under, and one made under another is out of date: the plan shown is then the free one again (`current`).

The store keeps it:

    environment-plans/<world>/writings/<time>.json  {world, at, by, method, environment, plan, euros, seconds}
                                                    (or `refused`)
    environment-plans/<world>/edits/<time>.json     {world, environment, plan, by, at}       (his process only)

    python -m score.review.environment_plan write [--by <name>]   write environment 1's plan
"""
import argparse
import json
import math
import sys

import numpy as np

from score.review import concepts, overhead, setting as settings
from score.store import stamp_key

AREA = "environment-plans"
METHOD = 2  # 2: sites placed by the environment concept's setting, at true sizes
NOTE_MOST = 300  # characters of a written ground's words
LOOK_MOST = 400  # characters of a site's look the writing is told
ITEMS_MOST = 30  # a site's plan items the writing is told
DROP_RINGS = (0.5, 1.0, 2.0)  # of a site's reach: the rings its ball-fall spots stand on
ROOFS = ("flat", "dome", "pitched", "vault")
SAME_SPOT = 1.0  # metres: two sites closer than this stand on one spot
ASKED = """You are an architect drawing the site plan of a game environment's worlds: one map a world, each top place's
site on it, in metres. The facts below are fixed: where each site stands on its ground (a world at its true radius,
or a flat plot), the parts of a site with their sizes and headings, the fall of the ground round each site on its
world's curve. Write what they leave open.

The facts (JSON):
{facts}

Write one JSON object: {{"time": the environment's moment in UTC (ISO 8601), "maps": [{{"on": the ground's key,
"ground": a short line on its ground, "sites": [{{"place": the site's place,
  "time": the place's scene time in UTC (ISO 8601): when its look happens at its own longitude (night, dusk, day as
  its look says), on or near the environment's moment,
  "size": [wide, deep, tall] in metres of the whole site,
  "footprint": [[x, y], ...] the site's outline in site metres (x east, y south, its middle at 0, 0),
  "blocks": [{{"name": words, "points": [[x, y], ...] in site metres, "base": m, "tall": m, "roof": "flat"|"dome"|
  "pitched"|"vault", "rise": m}}] its main masses (a site with parts: one block a part, at its place and size; an
  outdoor site: its biggest things from its plan's items and height words),
  "terrain": {{"spots": [[x, y, height], ...]}} spot heights in site metres round the site, the facts' ball-fall
  spots kept, craters, flats, ridges and water near it added at their heights}}]}}]}}
No text besides the JSON."""


class Refused(ValueError):
    pass


# --- the grounds and their sites, from the setting -----------------------------------------------------------------

def world_name():
    return json.loads((concepts.DATA / "definitions/world.json").read_text())["name"]


def layout(ground):
    """The game 2099's ground plan of `ground` (data/ground/plan/<ground>.json), read only for the layout of a site's
    parts in metres; None with none."""
    path = concepts.DATA / f"ground/plan/{ground}.json"
    return json.loads(path.read_text()) if path.is_file() else None


def seat_frame(out):
    """(across, out, along) of a seat at `out` on its ball, as the game builds it (tools/usd/orbits.seat_frame)."""
    out = np.asarray(out, float) / np.linalg.norm(out)
    reference = np.array([0.0, 0.0, 1.0]) if abs(out[2]) <= 0.9 else np.array([1.0, 0.0, 0.0])
    along = reference - out * reference.dot(out)
    along /= np.linalg.norm(along)
    return np.cross(out, along), out, along


def map_point(out, flat, reference, radius):
    """Where a seat's flat point stands in the game's layout: [x, y] metres from the reference seat's middle along its
    across and along axes, the game's ball unrolled round it."""
    across, up, along = seat_frame(out)
    point = radius * up + across * flat[0] + along * flat[1]
    ref_across, ref_up, ref_along = seat_frame(reference)
    way = point / np.linalg.norm(point)
    angle = math.acos(max(-1.0, min(1.0, float(np.dot(way, ref_up)))))
    level = way - ref_up * float(np.dot(way, ref_up))
    if np.linalg.norm(level) < 1e-12:
        return [0.0, 0.0]
    level /= np.linalg.norm(level)
    return [round(radius * angle * float(np.dot(level, ref_across)), 2),
            round(radius * angle * float(np.dot(level, ref_along)), 2)]


def seat_flat(seat):
    """A seat's middle on its own plane: its `flat`, else its yard level's middle, else its seat's middle."""
    if seat.get("flat"):
        return list(seat["flat"])
    if seat.get("level"):
        box = seat["level"]["box"]
        return [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]
    return [0.0, 0.0]


def parts_on(ground, tree):
    """{top place or shell: [{place, at, heading}]} of the game's layout of `ground`: every seat on its ground plan and
    every base module seated on one of them (data/definitions/base.json), grouped by the outside place or shell
    holding it, in layout metres; {} with no ground plan."""
    from score.review import environment_concept
    plan = layout(ground)
    if plan is None:
        return {}
    seats, radius = plan["seats"], float(plan["radius"])
    reference = next((seat for seat in seats.values() if seat.get("flat") == [0.0, 0.0]),
                     next(iter(seats.values())))["out"]
    found = {}
    for name, seat in seats.items():
        if name in tree["parts"]:
            continue  # a part of a place's outside (the Square's launch) stands in its place's own site
        found.setdefault(environment_concept.outermost(name, tree), []).append(
            {"place": name, "at": map_point(seat["out"], seat_flat(seat), reference, radius),
             "heading": float(seat.get("heading") or 0.0)})
    base = json.loads((concepts.DATA / "definitions/base.json").read_text())
    if base.get("ground") == ground and base.get("seat_of") in seats:
        seat = seats[base["seat_of"]]
        node = environment_concept.outermost(base["seat_of"], tree)
        for module in base["modules"].values():
            found[node].append({"place": module["stage"], "at": map_point(seat["out"], module["flat"], reference,
                                                                          radius),
                                "heading": float(module.get("heading") or 0.0)})
    return found


def sizes_of(place):
    """(wide, deep, walls, rise, roof) of a place's data plan (blockout.heights_of), None with no plan."""
    from score.review import blockout
    plan = concepts.plan_of(place)
    if not plan.get("w"):
        return None
    walls, rise, roof = blockout.heights_of(plan)
    return float(plan["w"]), float(plan["d"]), (0.0 if blockout.outdoor(plan) else walls), rise, roof


def turned_box(middle, wide, deep, heading):
    """The corners of a wide by deep box about `middle`, turned `heading` radians (the game's: about up)."""
    cos, sin = math.cos(heading), math.sin(heading)
    return [[round(middle[0] + x * cos + y * sin, 3), round(middle[1] - x * sin + y * cos, 3)]
            for x, y in ((-wide / 2, -deep / 2), (wide / 2, -deep / 2), (wide / 2, deep / 2), (-wide / 2, deep / 2))]


def radius_m(ground):
    """A ground's radius in metres: a body's mean radius, None for a flat plot."""
    return ground["radius_km"] * 1000.0 if "radius_km" in ground else None


def site_facts(site, parts, tree):
    """What data says of one site: its name and look, where the setting puts it, its parts in site metres with their
    sizes (the game's layout), its own plan's items and height words."""
    from score.review import environment_concept
    node = site["place"]
    middle = np.mean([part["at"] for part in parts], axis=0) if parts else np.zeros(2)
    shown = []
    for part in parts:
        size = sizes_of(part["place"])
        local = [round(float(part["at"][0] - middle[0]), 2), round(float(part["at"][1] - middle[1]), 2)]
        shown.append({"place": part["place"], "at": local, "heading": round(part["heading"], 4),
                      "size": None if size is None else [size[0], size[1], size[2]],
                      "roof": None if size is None else {"kind": size[4], "rise": size[3]}})
    plan = concepts.plan_of(node)
    where = {name: site.get(name) for name in ("latitude", "longitude", "x", "y", "height_m") if name in site}
    return {"place": node, "name": environment_concept.name_in(node, tree), **where,
            "look": concepts.look_text(node)[:LOOK_MOST],
            "parts": shown if len({tuple(part["at"]) for part in shown}) > 1 or node in tree["shells"] else [],
            "plan": {"w": plan.get("w"), "d": plan.get("d"), "height": plan.get("height"),
                     "items": [item[0] for item in plan.get("items", [])][:ITEMS_MOST]} if plan else None}


def grounds_of(setting):
    """[(ground, kind)] of the setting's bodies and plots that hold a site, in its order."""
    held = {site["on"] for site in setting["sites"]}
    return [(body, "body") for body in setting["bodies"] if body["body"] in held] + \
        [(plot, "plot") for plot in setting["plots"] if plot["plot"] in held]


def facts_of(store, world_id=None):
    """Everything the writing is told: each ground of the environment concept's setting with its sites (module
    docstring), its gravity, radius and what it orbits."""
    from score.review import environment_concept
    tree = concepts.tree(store)
    world_id = world_id or world_name()
    setting = environment_concept.setting_of(store, world_id)
    found = []
    for ground, kind in grounds_of(setting):
        key = ground[kind]
        layouts = parts_on(key, tree)
        sites = [site_facts(site, layouts.get(site["place"], []), tree)
                 for site in setting["sites"] if site["on"] == key]
        for site in sites:
            site["ball fall spots"] = fall_spots(site, radius_m(ground))
        around = next((body["name"] for body in setting["bodies"] if body["body"] == ground.get("around")), None)
        found.append({"on": key, "kind": kind, "name": ground["name"], "gravity": ground["gravity"],
                      "radius m": radius_m(ground), **({"orbits": around} if around else {}), "sites": sites})
    return {"environment": world_id, "grounds": found}


def reach_of(site):
    """Half the site's span in metres: its parts' extent, else its plan's, else 10 m."""
    if site["parts"]:
        points = [corner for part in site["parts"] if part["size"]
                  for corner in turned_box(part["at"], part["size"][0], part["size"][1], part["heading"])]
        if points:
            spread = np.ptp(np.asarray(points), axis=0)
            return float(max(spread)) / 2
    if site.get("plan") and site["plan"].get("w"):
        return max(float(site["plan"]["w"]), float(site["plan"]["d"])) / 2
    return 10.0


def fall_spots(site, radius):
    """Spot heights [[x, y, height]] round a site where its ground's curve falls away from its middle, d² / 2R, on
    rings at DROP_RINGS of its reach (level on a flat plot: `radius` None)."""
    reach = reach_of(site)
    found = [[0.0, 0.0, 0.0]]
    for ring in DROP_RINGS:
        far = reach * (1 + ring)
        for step in range(8):
            turn = math.pi / 4 * step
            found.append([round(far * math.cos(turn), 2), round(far * math.sin(turn), 2),
                          round(-(far * far) / (2 * radius), 4) if radius else 0.0])
    return found


def map_at(site, origin, radius):
    """Where a site stands on its ground's map in metres (x east, y south): on a body the azimuthal equidistant map
    round `origin` (the map's first site) at its true radius, on a plot its own x and y."""
    if radius is None:
        return [float(site.get("x") or 0.0), float(site.get("y") or 0.0)]
    if site.get("latitude") is None or origin.get("latitude") is None:
        return [0.0, 0.0]
    lat, lon = math.radians(site["latitude"]), math.radians(site["longitude"])
    lat0, lon0 = math.radians(origin["latitude"]), math.radians(origin["longitude"])
    angle = great_angle(origin, site)
    if angle < 1e-15:
        return [0.0, 0.0]
    toward = math.atan2(math.sin(lon - lon0) * math.cos(lat),
                        math.cos(lat0) * math.sin(lat) - math.sin(lat0) * math.cos(lat) * math.cos(lon - lon0))
    return [round(radius * angle * math.sin(toward), 2), round(-radius * angle * math.cos(toward), 2)]


def great_angle(one, two):
    """The angle in radians between two sites on a ball, from their latitudes and longitudes (haversine)."""
    lat1, lat2 = math.radians(one["latitude"]), math.radians(two["latitude"])
    half = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(
        math.radians(two["longitude"] - one["longitude"]) / 2) ** 2
    return 2 * math.asin(min(1.0, math.sqrt(half)))


# --- the plan: derived, written, settled -----------------------------------------------------------------------

def derived_site(site):
    """A site of the free plan: its parts as blocks (an outdoor site: its plan's box, no walls), its footprint the box
    round them, its ground the ball's fall, no scene time yet."""
    blocks = [{"name": part["place"], "points": turned_box(part["at"], part["size"][0], part["size"][1],
                                                           part["heading"]),
               "base": 0.0, "tall": part["size"][2], "roof": part["roof"]["kind"], "rise": part["roof"]["rise"]}
              for part in site["parts"] if part["size"]]
    if not blocks and site.get("plan") and site["plan"].get("w"):
        wide, deep = float(site["plan"]["w"]), float(site["plan"]["d"])
        blocks = [{"name": site["place"], "points": turned_box([0, 0], wide, deep, 0.0), "base": 0.0, "tall": 0.0,
                   "roof": "flat", "rise": 0.0}]
    points = np.asarray([corner for block in blocks for corner in block["points"]] or [[-10, -10], [10, 10]])
    low, high = points.min(axis=0), points.max(axis=0)
    tall = max([block["tall"] + block["rise"] for block in blocks] or [0.0])
    where = {name: site[name] for name in ("latitude", "longitude", "x", "y", "height_m") if name in site}
    return {"place": site["place"], "name": site["name"], **where, "time": None,
            "size": [round(float(high[0] - low[0]), 2), round(float(high[1] - low[1]), 2), round(tall, 2)],
            "footprint": [[float(low[0]), float(low[1])], [float(high[0]), float(low[1])],
                          [float(high[0]), float(high[1])], [float(low[0]), float(high[1])]],
            "blocks": blocks, "terrain": {"spots": site["ball fall spots"]}}


def derived(store, world_id=None):
    """The free plan from the setting and data alone (`facts_of`), settled: no scene times yet, so no skies (each a
    gap)."""
    facts = facts_of(store, world_id)
    return settled({"environment": facts["environment"], "time": None,
                    "maps": [{"on": ground["on"], "name": ground["name"], "ground": "",
                              "sites": [derived_site(site) for site in ground["sites"]]}
                             for ground in facts["grounds"]]}, store)


def number(value, low=-1e6, high=1e6):
    """A finite number in range, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value) if low <= value <= high else None


def points_of(value, least=3):
    found = [[number(point[0]), number(point[1])] for point in value
             if isinstance(point, list) and len(point) == 2] if isinstance(value, list) else []
    return found if len(found) >= least and all(None not in point for point in found) else None


def moment(value):
    """An ISO time in UTC as written, None when it is none."""
    try:
        overhead.day_of(value)
    except (TypeError, ValueError):
        return None
    return str(value)


def block_of(block):
    points = points_of(block.get("points")) if isinstance(block, dict) else None
    if not points or number(block.get("tall"), 0, 2000) is None:
        return None
    return {"name": str(block.get("name") or "")[:60], "points": points, "base": number(block.get("base")) or 0.0,
            "tall": number(block["tall"], 0, 2000), "roof": block.get("roof") if block.get("roof") in ROOFS else "flat",
            "rise": number(block.get("rise"), 0, 500) or 0.0}


def site_from(answer, fixed):
    """One written site over its free one: the fixed facts kept (where it stands, its parts' blocks), the rest as
    written where it is in shape."""
    found = dict(fixed)
    found["time"] = moment(answer.get("time")) or None
    size = answer.get("size")
    if isinstance(size, list) and len(size) == 3 and all(number(value, 0, 1e5) is not None for value in size):
        found["size"] = [number(value) for value in size]
    found["footprint"] = points_of(answer.get("footprint")) or fixed["footprint"]
    written = [block for block in map(block_of, answer.get("blocks") or []) if block]
    if written and not any(block["tall"] for block in fixed["blocks"]):  # a site with parts keeps its parts
        found["blocks"] = written
    spots = [[number(spot[0]), number(spot[1]), number(spot[2], -1e4, 1e4)] for spot in
             (answer.get("terrain") or {}).get("spots") or [] if isinstance(spot, list) and len(spot) == 3]
    spots = [spot for spot in spots if None not in spot]
    found["terrain"] = {"spots": fixed["terrain"]["spots"] + [spot for spot in spots if spot[:2] != [0.0, 0.0]]}
    return found


def plan_from(answer, free, store):
    """The written plan: each written site over its free one (`site_from`), the environment's time and each map's
    ground words, settled."""
    written = {(world.get("on"), site.get("place")): site for world in answer.get("maps") or []
               if isinstance(world, dict) for site in world.get("sites") or [] if isinstance(site, dict)}
    grounds = {world.get("on"): str(world.get("ground") or "")[:NOTE_MOST] for world in answer.get("maps") or []
               if isinstance(world, dict)}
    return settled({**free, "time": moment(answer.get("time")) or None,
                    "maps": [{**world, "ground": grounds.get(world["on"], world.get("ground", "")),
                              "sites": [site_from(written.get((world["on"], site["place"]), {}), site)
                                        for site in world["sites"]]} for world in free["maps"]]}, store)


def distances(sites, radius):
    """[{from, to, metres}] between every two sites on one ground: along its curve on a body (`radius`), straight
    across a plot."""
    return [{"from": one["place"], "to": two["place"],
             "metres": round(radius * great_angle(one, two) if radius else
                             math.dist([one.get("x") or 0.0, one.get("y") or 0.0],
                                       [two.get("x") or 0.0, two.get("y") or 0.0]), 1)}
            for order, one in enumerate(sites) for two in sites[order + 1:]
            if not radius or None not in (one.get("latitude"), two.get("latitude"))]


def gaps_of(plan):
    """What the plan does not know yet, each in words: a site's scene time or its place on its ground, and two sites
    standing on one spot of a ground (under a metre apart: each site has its own place in the setting)."""
    names = {site["place"]: site["name"] for world in plan["maps"] for site in world["sites"]}
    return [f"{site['name']}: no {what}" for world in plan["maps"] for site in world["sites"]
            for what, missing in (("scene time", site.get("time") is None),
                                  ("place on its ground", "x" not in site and site.get("latitude") is None))
            if missing] + \
        [f"{names[found['from']]} and {names[found['to']]} stand on one spot of {world['name']}"
         for world in plan["maps"] for found in world.get("distances", []) if found["metres"] < SAME_SPOT]


def settled(plan, store=None):
    """The plan with what follows from it worked out from the environment concept's setting (kept with it as
    `setting`): where each site stands, each map's place on its map and distances, what each site sees overhead, its
    gaps."""
    from score.review import environment_concept
    setting = environment_concept.setting_of(store, plan.get("environment")) if store is not None else settings.now()
    placed = {site["place"]: site for site in setting["sites"]}
    maps = []
    for world in plan["maps"]:
        ground, _ = settings.ground_of(setting, world["on"])
        if ground is None:
            continue  # a ground the setting no longer has
        radius = radius_m(ground)
        sites = []
        for site in world["sites"]:
            if placed.get(site["place"], {}).get("on") != world["on"]:
                continue  # moved off this ground in the setting
            where = {name: placed[site["place"]].get(name) for name in ("latitude", "longitude", "x", "y", "height_m")
                     if name in placed[site["place"]]}
            sites.append({**site, **where})
        origin = sites[0] if sites else {}
        sites = [{**site, "at": map_at(site, origin, radius),
                  "overhead": overhead.seen(setting, {**site, "on": world["on"]}, site["time"]) if site.get("time")
                  else None} for site in sites]
        maps.append({**world, "radius_m": radius, "sites": sites, "distances": distances(sites, radius)})
    found = {**plan, "setting": setting, "maps": maps}
    found.pop("bodies", None)
    return {**found, "gaps": gaps_of(found)}


# --- kept ---------------------------------------------------------------------------------------------------------

def records(store, world, kind):
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{world}/{kind}/"))]


def concept_version(store):
    """The environment concept's version a writing or edit is made under (environment_concept.version)."""
    from score.review import environment_concept
    return environment_concept.version(store)


def in_date(store, found):
    """Whether a writing or edit was made under today's environment concept and METHOD."""
    return found.get("method") == METHOD and found.get("environment") == concept_version(store)


def written_of(store, world):
    """The newest writing by today's METHOD under today's environment concept, None with none (or only refused
    ones)."""
    return next((found for found in reversed(records(store, world, "writings"))
                 if in_date(store, found) and not found.get("refused")), None)


def current(store, world=None):
    """{plan, how, at, by} of the environment's plan shown, settled again on the setting: the newer of his newest
    edit and the writing made under today's environment concept (how: edited or written), else the free one (how:
    derived)."""
    world = world or world_name()
    edits = [found for found in records(store, world, "edits") if in_date(store, found)]
    written = written_of(store, world)
    found = max([found for found in (edits[-1] if edits else None, written) if found], key=lambda found: found["at"],
                default=None)
    if found is None:
        return {"plan": derived(store, world), "how": "derived", "at": None, "by": None}
    return {"plan": settled(found["plan"], store), "how": "edited" if found in edits else "written",
            "at": found["at"], "by": found["by"]}


def site_of(store, place, world=None):
    """The site of a top place on the environment's plan shown, with the ground it stands on (`on`) and that
    ground's radius in metres (`radius_m`, None on a plot), None when it has none."""
    for found in current(store, world)["plan"]["maps"]:
        for site in found["sites"]:
            if site["place"] == place:
                return {**site, "on": found["on"], "radius_m": found.get("radius_m")}
    return None


def checked_edit(plan, base, store=None):
    """His plan as he left it: each site's time and size where in shape, the rest from `base` (where a site stands is
    the environment concept's setting)."""
    if not isinstance(plan, dict) or not isinstance(plan.get("maps"), list):
        raise Refused("an environment plan has maps")
    sent = {(world.get("on"), site.get("place")): site for world in plan["maps"] if isinstance(world, dict)
            for site in world.get("sites") or [] if isinstance(site, dict)}
    maps = []
    for world in base["maps"]:
        sites = []
        for site in world["sites"]:
            his = sent.get((world["on"], site["place"]), {})
            size = his.get("size")
            sites.append({**site, "time": moment(his["time"]) if his.get("time") else site.get("time"),
                          "size": [number(value, 0, 1e5) for value in size] if isinstance(size, list) and len(size) == 3
                          and all(number(value, 0, 1e5) is not None for value in size) else site["size"]})
        maps.append({**world, "sites": sites})
    return settled({**base, "time": moment(plan.get("time")) or base.get("time"), "maps": maps}, store)


def edited(store, plan, by, world=None):
    """Keep his edit of the environment's plan (`checked_edit` over the plan shown); the record. PermissionError in an
    agent's process on the framework's store."""
    world = world or world_name()
    record = {"world": world, "method": METHOD, "environment": concept_version(store),
              "plan": checked_edit(plan, current(store, world)["plan"], store), "by": by, "at": concepts.now()}
    concepts.recorded(store, f"{AREA}/{world}/edits/{stamp_key(record['at'])}.json", record)
    return record


def asked_body(facts):
    return {"contents": [{"role": "user", "parts": [{"text": ASKED.format(facts=json.dumps(facts, indent=1))}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}


def write(store, by, world=None, ask=None, clear=None):
    """Write the environment's plan: one Gemini call through the plan writer (plan_writing.asked), cleared as a plan
    writing under the owner's standing allowance; the record kept (refused when the answer is no plan)."""
    from score.adapters import compute
    from score.review import plan_writing, reading
    world = world or world_name()
    facts = facts_of(store, world)
    with plan_writing.cleared(store, [f"environment-{world}"], plan_writing.price(store), clear):
        compute.require_cleared("a plan writing", store)
        response, seconds = (ask or plan_writing.asked)(asked_body(facts))
    record = {"world": world, "at": concepts.now(), "by": by, "method": METHOD, "environment": concept_version(store),
              "euros": plan_writing.call_euros(response), "seconds": seconds}
    try:
        record["plan"] = plan_from(json.loads(reading.answer_text(response)), derived(store, world), store)
    except (ValueError, TypeError, AttributeError) as wrong:
        record["refused"] = f"the plan answer is no plan: {str(wrong)[:200]}"
    store.write_once(f"{AREA}/{world}/writings/{stamp_key(record['at'])}.json", record)
    return record


def main(argv):
    """`write [--by NAME]`: write environment 1's plan in the framework's store; one line."""
    from score.adapters.compute import Refused as NotCleared
    from score.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=("write",))
    parser.add_argument("--by", default="the owner's standing allowance")
    options = parser.parse_args(argv)
    try:
        record = write(Store.default(), options.by)
    except (concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    if record.get("refused"):
        print(json.dumps({"refused": record["refused"], "euros": record["euros"]}))
        return 1
    print(json.dumps({"sites": sum(len(world["sites"]) for world in record["plan"]["maps"]),
                      "gaps": record["plan"]["gaps"], "euros": record["euros"], "seconds": record["seconds"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
