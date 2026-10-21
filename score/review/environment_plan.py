"""The environment's plan (CONTEXT.md "environment plan"; the owner, 2026-10-21): the environment is the first parent,
so its concept gets a plan of its own, as every place's does, and each top place's concept is drawn on the blockout
of its site there (score/review/blockout.py). One map a world (environment 1: the Moon with the Base, the Old station
and the Wreck; Mars with the Campgrounds; Earth with the Square on the Hong Kong shore; which place is on which world
read from the ground plans' seats, data/ground/plan/<world>.json), each top place's site on it: where it stands, its
footprint and rough size, its blocks, the ground and terrain heights round it, its latitude and longitude on its
world and its scene time; the distances between sites on the same world; and the environment's physics state
(data/physics/worlds.json, score/review/sky.py: every world's and the Sun's radius, orbit and spin, and the
environment's time), from which each site's sky at its scene time is worked out, never written by hand: every other
world at its true direction, size and phase, lit from the Sun's side. A later sky layer runs the same state live.

It is made like a place's plan: what data already says is worked out free (`facts_of`: positions on the world's ball,
the parts of a site from their seats, the latitude and longitude where the game's frames give them, the ball's fall
round each site); Gemini 3.1 Pro writes the rest (`write`: one direct call through the plan writer's own call,
score/review/plan_writing.py, run without asking under the owner's standing allowance of 2026-10-21 for plan
writing); the code then checks it, keeps the fixed facts over the answer, and works out the distances and skies
(`settled`). Until it is written the plan shown is the free one (`derived`). He fixes it on its plan page (a site's
time, latitude, longitude, size), his edit kept as his own and settled again.

The store keeps it:

    environment-plans/<world>/writings/<time>.json  {world, at, by, method, plan, euros, seconds} (or `refused`)
    environment-plans/<world>/edits/<time>.json     {world, plan, by, at}       (his process only)

    python -m score.review.environment_plan write [--by <name>]   write environment 1's plan
"""
import argparse
import json
import math
import sys

import numpy as np

from score.review import concepts, sky
from score.store import stamp_key

AREA = "environment-plans"
METHOD = 1
NOTE_MOST = 300  # characters of a written ground's words
LOOK_MOST = 400  # characters of a site's look the writing is told
ITEMS_MOST = 30  # a site's plan items the writing is told
DROP_RINGS = (0.5, 1.0, 2.0)  # of a site's reach: the rings its ball-fall spots stand on
ROOFS = ("flat", "dome", "pitched", "vault")
ASKED = """You are an architect drawing the site plan of a game environment's worlds: one map a world, each top place's
site on it, in metres. The facts below are fixed: where each site stands on its world's map, the parts of a site with
their sizes and headings, a latitude and longitude where given, the fall of the ground round each site on its world's
ball. Write what they leave open.

The facts (JSON):
{facts}

Write one JSON object: {{"time": the environment's moment in UTC (ISO 8601), "maps": [{{"world": the world's key,
"ground": a short line on its ground, "sites": [{{"place": the site's place,
  "time": the place's scene time in UTC (ISO 8601): when its look happens at its own longitude (night, dusk, day as
  its look says), on or near the environment's moment,
  "latitude": degrees north, "longitude": degrees east (only where the facts give none: the real place it stands),
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


# --- the worlds and their sites, from data -------------------------------------------------------------------------

def world_name():
    return json.loads((concepts.DATA / "definitions/world.json").read_text())["name"]


def ground_plan(world):
    return json.loads((concepts.DATA / f"ground/plan/{world}.json").read_text())


def seat_frame(out):
    """(across, out, along) of a seat at `out` on its ball, as the game builds it (tools/usd/orbits.seat_frame)."""
    out = np.asarray(out, float) / np.linalg.norm(out)
    reference = np.array([0.0, 0.0, 1.0]) if abs(out[2]) <= 0.9 else np.array([1.0, 0.0, 0.0])
    along = reference - out * reference.dot(out)
    along /= np.linalg.norm(along)
    return np.cross(out, along), out, along


def map_point(out, flat, reference, radius):
    """Where a seat's flat point stands on its world's map: [x, y] metres from the reference seat's middle along its
    across and along axes, the ball unrolled round it (an azimuthal equidistant map)."""
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


def parts_on(world, tree):
    """{top place or shell: [{place, at, heading}]} of every seat on the world's ground plan and every base module
    seated on one of them (data/definitions/base.json), grouped by the outside place or shell holding it; map metres
    from the ground plan's own middle (its seat at flat 0, 0)."""
    from score.review import environment_concept
    plan = ground_plan(world)
    seats, radius = plan["seats"], float(plan["radius"])
    reference = next((seat for seat in seats.values() if seat.get("flat") == [0.0, 0.0]),
                     next(iter(seats.values())))["out"]  # the ground plan's numbers: that seat's middle at 0, 0
    found = {}
    for name, seat in seats.items():
        node = environment_concept.outermost(name, tree)
        if name in tree["parts"]:
            continue  # a part of a place's outside (the Square's launch) stands in its place's own site
        found.setdefault(node, []).append({"place": name, "at": map_point(seat["out"], seat_flat(seat), reference, radius),
                                           "heading": float(seat.get("heading") or 0.0)})
    base = json.loads((concepts.DATA / "definitions/base.json").read_text())
    if base.get("ground") == world and base.get("seat_of") in seats:
        seat = seats[base["seat_of"]]
        node = environment_concept.outermost(base["seat_of"], tree)
        for module in base["modules"].values():
            found[node].append({"place": module["stage"], "at": map_point(seat["out"], module["flat"], reference,
                                                                          radius),
                                "heading": float(module.get("heading") or 0.0)})
    return found


def lat_lon(world, out):
    """(latitude, longitude, from) of a seat on its world where the game's frames say it, else (None, None, why)."""
    out = np.asarray(out, float) / np.linalg.norm(out)
    if world == "moon":  # the game's Moon frame: toward Earth (longitude 0) and its pole (tools/usd/orbits.py)
        sys.path.insert(0, str(concepts.REPO / "tools/usd"))
        try:
            import orbits
        finally:
            sys.path.pop(0)
        frame = orbits.moon_own_frame()
        toward, pole, third = frame[:, 0], frame[:, 1], frame[:, 2]
        return (round(math.degrees(math.asin(float(np.dot(out, pole)))), 3),
                round(math.degrees(math.atan2(-float(np.dot(out, third)), float(np.dot(out, toward)))), 3),
                "the game's Moon frame (tools/usd/orbits.moon_own_frame): longitude 0 toward Earth")
    if world == "mars":
        return (round(math.degrees(math.asin(float(out[1]))), 3), round(math.degrees(math.atan2(out[0], out[2])), 3),
                "the seat on Mars's ball, its pole the ball's up (the game has no Mars frame; the longitude is "
                "the ball's own)")
    return None, None, "the game's ball gives no latitude here: the writing gives the real place's"


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


def site_facts(store, world, node, parts, tree):
    """What data says of one site: its name and look, its middle on the map, its parts in site metres with their
    sizes, its latitude and longitude where the game gives them, its own plan's items and height words."""
    from score.review import environment_concept
    middle = np.mean([part["at"] for part in parts], axis=0)
    shown = []
    for part in parts:
        size = sizes_of(part["place"])
        local = [round(float(part["at"][0] - middle[0]), 2), round(float(part["at"][1] - middle[1]), 2)]
        shown.append({"place": part["place"], "at": local, "heading": round(part["heading"], 4),
                      "size": None if size is None else [size[0], size[1], size[2]],
                      "roof": None if size is None else {"kind": size[4], "rise": size[3]}})
    seat = ground_plan(world)["seats"].get(node) or ground_plan(world)["seats"][parts[0]["place"]]
    latitude, longitude, said = lat_lon(world, seat["out"])
    plan = concepts.plan_of(node)
    return {"place": node, "name": environment_concept.name_in(node, tree), "at": [round(float(value), 2)
                                                                                   for value in middle],
            "look": concepts.look_text(node)[:LOOK_MOST], "latitude": latitude, "longitude": longitude,
            "latitude from": said,
            "parts": shown if len({tuple(part["at"]) for part in shown}) > 1 or node in tree["shells"] else [],
            "plan": {"w": plan.get("w"), "d": plan.get("d"), "height": plan.get("height"),
                     "items": [item[0] for item in plan.get("items", [])][:ITEMS_MOST]} if plan else None}


def facts_of(store, world_id=None):
    """Everything the writing is told: each world with its sites (module docstring), its ground's facts and the
    environment's physics names."""
    from score.review import environment_concept
    tree = concepts.tree(store)
    state = sky.bodies()
    found = []
    for world, facts in state["worlds"].items():
        plan = ground_plan(world)
        sites = [site_facts(store, world, node, parts, tree)
                 for node, parts in parts_on(world, tree).items() if node not in tree["parts"]]
        for site in sites:
            site["ball fall spots"] = fall_spots(site, float(plan["radius"]))
        found.append({"world": world, "name": facts["name"], "gravity": facts["gravity"], "orbits": facts["orbits"],
                      "ball radius m": plan["radius"], "ground": {key: plan.get(key) for key in
                                                                   ("flats", "levels", "water", "landforms")
                                                                   if plan.get(key)},
                      "craters": [{"name": crater.get("name"), "x": crater["x"], "y": crater["z"], "d": crater["d"]}
                                  for crater in plan.get("craters", [])], "sites": sites})
    return {"environment": world_id or world_name(), "worlds": found}


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
    """Spot heights [[x, y, height]] round a site where its world's ball falls away from its middle: the ground's
    curve, d² / 2R, on rings at DROP_RINGS of its reach."""
    reach = reach_of(site)
    found = [[0.0, 0.0, 0.0]]
    for ring in DROP_RINGS:
        far = reach * (1 + ring)
        for step in range(8):
            turn = math.pi / 4 * step
            found.append([round(far * math.cos(turn), 2), round(far * math.sin(turn), 2),
                          round(-(far * far) / (2 * radius), 3)])
    return found


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
    return {"place": site["place"], "name": site["name"], "at": site["at"], "latitude": site["latitude"],
            "longitude": site["longitude"], "time": None,
            "size": [round(float(high[0] - low[0]), 2), round(float(high[1] - low[1]), 2), round(tall, 2)],
            "footprint": [[float(low[0]), float(low[1])], [float(high[0]), float(low[1])],
                          [float(high[0]), float(high[1])], [float(low[0]), float(high[1])]],
            "blocks": blocks, "terrain": {"spots": site["ball fall spots"]}}


def derived(store, world_id=None):
    """The free plan from data alone (`facts_of`), settled: no scene times yet, so no skies (each a gap)."""
    facts = facts_of(store, world_id)
    return settled({"environment": facts["environment"], "time": None,
                    "maps": [{"world": world["world"], "name": world["name"], "ground": "",
                              "sites": [derived_site(site) for site in world["sites"]]} for world in facts["worlds"]]},
                   facts)


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
        sky.day_of(value)
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
    """One written site over its free one: the fixed facts kept (where it stands, its parts' blocks, a latitude and
    longitude the game gives), the rest as written where it is in shape."""
    found = dict(fixed)
    found["time"] = moment(answer.get("time")) or None
    if fixed["latitude"] is None:
        found["latitude"] = number(answer.get("latitude"), -90, 90)
        found["longitude"] = number(answer.get("longitude"), -180, 360)
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


def plan_from(answer, free, facts):
    """The written plan: each written site over its free one (`site_from`), the environment's time and each map's
    ground words, settled."""
    written = {(world.get("world"), site.get("place")): site for world in answer.get("maps") or []
               if isinstance(world, dict) for site in world.get("sites") or [] if isinstance(site, dict)}
    grounds = {world.get("world"): str(world.get("ground") or "")[:NOTE_MOST] for world in answer.get("maps") or []
               if isinstance(world, dict)}
    return settled({**free, "time": moment(answer.get("time")) or None,
                    "maps": [{**world, "ground": grounds.get(world["world"], world.get("ground", "")),
                              "sites": [site_from(written.get((world["world"], site["place"]), {}), site)
                                        for site in world["sites"]]} for world in free["maps"]]}, facts)


def distances(sites):
    """[{from, to, metres}] between every two sites on one map, straight across it."""
    return [{"from": one["place"], "to": two["place"],
             "metres": round(math.dist(one["at"], two["at"]), 1)}
            for order, one in enumerate(sites) for two in sites[order + 1:]]


def skied(site, world, state):
    """The site's sky at its scene time (sky.sky_at), None while its time or place on its world is not known."""
    if site.get("time") is None or site.get("latitude") is None or site.get("longitude") is None:
        return None
    return sky.sky_at(state, world, site["latitude"], site["longitude"], site["time"])


def gaps_of(plan):
    """What the plan does not know yet, each in words: a site's scene time or its place on its world."""
    return [f"{site['name']}: no {what}" for world in plan["maps"] for site in world["sites"]
            for what, missing in (("scene time", site.get("time") is None),
                                  ("latitude and longitude", site.get("latitude") is None)) if missing]


def settled(plan, facts=None):
    """The plan with what follows from it worked out: the physics state (`bodies`), each map's distances and each
    site's sky, its gaps; the fixed facts' positions kept."""
    state = sky.bodies()
    maps = []
    for world in plan["maps"]:
        sites = [{**site, "sky": skied(site, world["world"], state)} for site in world["sites"]]
        maps.append({**world, "sites": sites, "distances": distances(sites)})
    found = {**plan, "bodies": state, "maps": maps}
    return {**found, "gaps": gaps_of(found)}


# --- kept ---------------------------------------------------------------------------------------------------------

def records(store, world, kind):
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{world}/{kind}/"))]


def written_of(store, world):
    """The newest writing by today's METHOD, None with none (or only refused ones)."""
    return next((found for found in reversed(records(store, world, "writings"))
                 if found.get("method") == METHOD and not found.get("refused")), None)


def current(store, world=None):
    """{plan, how, at, by} of the environment's plan shown: the newer of his newest edit and the writing (how: edited
    or written), else the free one (how: derived)."""
    world = world or world_name()
    edits, written = records(store, world, "edits"), written_of(store, world)
    found = max([found for found in (edits[-1] if edits else None, written) if found], key=lambda found: found["at"],
                default=None)
    if found is None:
        return {"plan": derived(store, world), "how": "derived", "at": None, "by": None}
    return {"plan": found["plan"], "how": "edited" if found in edits else "written", "at": found["at"],
            "by": found["by"]}


def site_of(store, place, world=None):
    """The site of a top place on the environment's plan shown, with its world (`world`), None when it has none."""
    for found in current(store, world)["plan"]["maps"]:
        for site in found["sites"]:
            if site["place"] == place:
                return {**site, "world": found["world"]}
    return None


def checked_edit(plan, base):
    """His plan as he left it: each site's time, latitude, longitude and size where in shape, the rest from `base`."""
    if not isinstance(plan, dict) or not isinstance(plan.get("maps"), list):
        raise Refused("an environment plan has maps")
    sent = {(world.get("world"), site.get("place")): site for world in plan["maps"] if isinstance(world, dict)
            for site in world.get("sites") or [] if isinstance(site, dict)}
    maps = []
    for world in base["maps"]:
        sites = []
        for site in world["sites"]:
            his = sent.get((world["world"], site["place"]), {})
            size = his.get("size")
            sites.append({**site, "time": moment(his["time"]) if his.get("time") else site.get("time"),
                          "latitude": number(his.get("latitude"), -90, 90) if "latitude" in his else site["latitude"],
                          "longitude": number(his.get("longitude"), -180, 360) if "longitude" in his
                          else site["longitude"],
                          "size": [number(value, 0, 1e5) for value in size] if isinstance(size, list) and len(size) == 3
                          and all(number(value, 0, 1e5) is not None for value in size) else site["size"]})
        maps.append({**world, "sites": sites})
    return settled({**base, "time": moment(plan.get("time")) or base.get("time"), "maps": maps})


def edited(store, plan, by, world=None):
    """Keep his edit of the environment's plan (`checked_edit` over the plan shown); the record. PermissionError in an
    agent's process on the framework's store."""
    world = world or world_name()
    record = {"world": world, "plan": checked_edit(plan, current(store, world)["plan"]), "by": by,
              "at": concepts.now()}
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
    record = {"world": world, "at": concepts.now(), "by": by, "method": METHOD,
              "euros": plan_writing.call_euros(response), "seconds": seconds}
    try:
        record["plan"] = plan_from(json.loads(reading.answer_text(response)), derived(store, world), facts)
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
