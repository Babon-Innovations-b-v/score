"""The environment's plan (CONTEXT.md "environment plan"; the owner, 2026-10-21): the environment is the first parent,
so its concept gets a plan of its own, as every scene's does. One map a ground of its setting (score/review/setting.py,
the environment concept's: a body, at its true radius, or a plot), each top scene's site on it where the setting puts
it (its latitude, longitude and height on a body, metres on a plot), the ground and terrain heights round it and its
scene time; the true distances between sites on the same ground; and the setting, from which what is seen overhead at
each site at its scene time is worked out (score/review/overhead.py), never written by hand: every other body at its
true direction, size and phase, every light and backdrop. The engine runs the same setting live.

A site's footprint, size and blocks are its top scene's own plan, the one its plan page shows (score/review/plans.py
`current`; the owner, 2026-10-23: "why are they diff from the scene anyway"): read again on every settle
(`from_plan`), so neither the plan writer nor an edit here can make them differ from the scene. Its rough model, where
one exists, is registered to that plan (stages/rough_model, rough-align), so the plan stays the one source.

It is made like a place's plan: what data already says is worked out free (`facts_of`: each site's place and its plan's shape,
the fall of its ground's curve round it); Gemini 3.1 Pro writes the rest (`write`: one direct call through the plan
writer's own call, score/review/plan_writing.py, run without asking under the owner's standing allowance of
2026-10-21 for plan writing); the code then checks it, keeps the fixed facts over the answer, and works out the
distances and what each site sees overhead (`settled`). Until it is written the plan shown is the free one
(`derived`). He fixes it on its plan page (a site's scene time), his edit kept as his own and settled again;
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

from score.review import concepts, overhead, setting as settings
from score.store import stamp_key

AREA = "environment-plans"
METHOD = 2  # 2: sites placed by the environment concept's setting, at true sizes
NOTE_MOST = 300  # characters of a written ground's words
LOOK_MOST = 400  # characters of a site's look the writing is told
ITEMS_MOST = 30  # a site's plan items the writing is told
DROP_RINGS = (0.5, 1.0, 2.0)  # of a site's reach: the rings its ball-fall spots stand on
SAME_SPOT = 1.0  # metres: two sites closer than this stand on one spot
WALLS_ITEM = "ON THE WALLS AND CEILING"  # a plan's item that is no thing standing (plan.js's WALLS)
ASKED = """You are an architect drawing the site plan of a game environment's worlds: one map a world, each top place's
site on it, in metres. The facts below are fixed: where each site stands on its ground (a world at its true radius,
or a flat plot), each site's size and outline from its own plan, the fall of the ground round each site on its
world's curve. Write what they leave open.

The facts (JSON):
{facts}

Write one JSON object: {{"time": the environment's moment in UTC (ISO 8601), "maps": [{{"on": the ground's key,
"ground": a short line on its ground, "sites": [{{"place": the site's place,
  "time": the place's scene time in UTC (ISO 8601): when its look happens at its own longitude (night, dusk, day as
  its look says), on or near the environment's moment,
  "terrain": {{"spots": [[x, y, height], ...]}} spot heights in site metres (x east, y south, its middle at 0, 0)
  round the site, the facts' ball-fall spots kept, craters, flats, ridges and water near it added at their
  heights}}]}}]}}
No text besides the JSON."""


class Refused(ValueError):
    pass


# --- the grounds and their sites, from the setting and each top scene's own plan -----------------------------------

def world_name():
    return json.loads((concepts.DATA / "definitions/world.json").read_text())["name"]


def site_plan(store, place):
    """The top scene's own plan as its plan page shows it (plans.current), None while it has none."""
    from score.review import plans
    shown = plans.current(store, place) if store is not None else None
    return shown["plan"] if shown else None


def tall_of(plan):
    """The plan's tallest top in metres: its things' shapes, walls and roofs."""
    tops = [float(form.get("base") or 0) + float(form.get("tall") or 0) for form in (plan.get("shapes") or {}).values()]
    tops += [float(wall.get("tall") or 0) for wall in plan.get("walls") or []]
    tops += [float(roof.get("top") or 0) for roof in plan.get("roofs") or []]
    return round(max(tops, default=0.0), 2)


def holding_item(plan, hold):
    """The plan's item holding a child scene's box (its row among the item's rows), None with none."""
    rows = plan.get("rows") or {}
    return next((item for item in plan.get("items") or [] if hold.get("row") in rows.get(item[0], [])), None)


def block_of_box(name, box, form, middle):
    """One mass in site metres about `middle`: a box (x, y, wide, deep in plan metres) at its shape's base and tall."""
    left, top, wide, deep = box[0] - middle[0], box[1] - middle[1], box[2], box[3]
    corners = [[left, top], [left + wide, top], [left + wide, top + deep], [left, top + deep]]
    return {"name": name, "points": [[round(x, 3), round(y, 3)] for x, y in corners],
            "base": float(form.get("base") or 0), "tall": float(form.get("tall") or 0),
            "roof": "dome" if form.get("shape") == "circle" else "flat", "rise": 0.0}


def plan_blocks(plan, middle):
    """The plan's masses in site metres about `middle`: each child scene's box named by its place, at its holding
    item's height, and each other thing standing up, at its own."""
    shapes = plan.get("shapes") or {}
    holds = plan.get("holds") or []
    holding = [holding_item(plan, hold) for hold in holds]
    found = [block_of_box(hold["place"], (hold["x"], hold["y"], hold["w"], hold["d"]),
                          shapes.get(item[0], {}) if item else {}, middle) for hold, item in zip(holds, holding)]
    return found + [block_of_box(item[0], item[1:5], shapes[item[0]], middle) for item in plan.get("items") or []
                    if item not in holding and item[0] != WALLS_ITEM and item[6:7] != ["zone"]
                    and float((shapes.get(item[0]) or {}).get("tall") or 0) > 0]


def from_plan(plan):
    """{size, footprint, blocks} of a site from its top scene's own plan (`site_plan`): its wide, deep and tallest,
    its outline and its masses in site metres (x east, y south, its middle at 0, 0); None sizes with no plan."""
    if not plan or not plan.get("w"):
        return {"size": None, "footprint": None, "blocks": []}
    wide, deep = float(plan["w"]), float(plan["d"])
    middle = (wide / 2, deep / 2)
    outline = plan["outline"] if len(plan.get("outline") or []) >= 3 else [[0, 0], [wide, 0], [wide, deep], [0, deep]]
    return {"size": [round(wide, 2), round(deep, 2), tall_of(plan)],
            "footprint": [[round(x - middle[0], 3), round(y - middle[1], 3)] for x, y in outline],
            "blocks": plan_blocks(plan, middle)}


def radius_m(ground):
    """A ground's radius in metres: a body's mean radius, None for a flat plot."""
    return ground["radius_km"] * 1000.0 if "radius_km" in ground else None


def site_facts(store, site, tree):
    """What data says of one site: its name and look, where the setting puts it, its size and outline from its own
    plan (`from_plan`) and that plan's things."""
    from score.review import environment_concept
    node = site["place"]
    plan = site_plan(store, node)
    shape = from_plan(plan)
    where = {name: site.get(name) for name in ("latitude", "longitude", "x", "y", "height_m") if name in site}
    return {"place": node, "name": environment_concept.name_in(node, tree), **where,
            "look": concepts.look_text(node)[:LOOK_MOST], "size": shape["size"], "footprint": shape["footprint"],
            "things": [item[0] for item in (plan or {}).get("items", [])][:ITEMS_MOST]}


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
        sites = [site_facts(store, site, tree) for site in setting["sites"] if site["on"] == key]
        for site in sites:
            site["ball fall spots"] = fall_spots(site, radius_m(ground))
        around = next((body["name"] for body in setting["bodies"] if body["body"] == ground.get("around")), None)
        found.append({"on": key, "kind": kind, "name": ground["name"], "gravity": ground["gravity"],
                      "radius m": radius_m(ground), **({"orbits": around} if around else {}), "sites": sites})
    return {"environment": world_id, "grounds": found}


def reach_of(site):
    """Half the site's span in metres: its plan's, else 10 m."""
    return max(site["size"][0], site["size"][1]) / 2 if site.get("size") else 10.0


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
    """A site of the free plan: where it stands, its ground the ball's fall, no scene time yet (its shape is its
    plan's, laid on it by `settled`)."""
    where = {name: site[name] for name in ("latitude", "longitude", "x", "y", "height_m") if name in site}
    return {"place": site["place"], "name": site["name"], **where, "time": None,
            "terrain": {"spots": site["ball fall spots"]}}


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


def moment(value):
    """An ISO time in UTC as written, None when it is none."""
    try:
        overhead.day_of(value)
    except (TypeError, ValueError):
        return None
    return str(value)


def site_from(answer, fixed):
    """One written site over its free one: the fixed facts kept (where it stands; its shape is its plan's), its scene
    time and terrain spots as written where they are in shape."""
    found = dict(fixed)
    found["time"] = moment(answer.get("time")) or None
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


def box_on_map(site):
    """(least x, least y, most x, most y) of a site's footprint where it stands on its map, None with no plan."""
    if not site.get("footprint"):
        return None
    xs, ys = [site["at"][0] + x for x, _ in site["footprint"]], [site["at"][1] + y for _, y in site["footprint"]]
    return min(xs), min(ys), max(xs), max(ys)


def overlapping(world):
    """[(one, two)] of the sites of one map whose footprints overlap where the setting stands them."""
    boxes = [(site, box_on_map(site)) for site in world["sites"]]
    boxes = [(site, box) for site, box in boxes if box]
    return [(one, two) for order, (one, first) in enumerate(boxes) for two, second in boxes[order + 1:]
            if first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]]


def gaps_of(plan):
    """What the plan does not know yet, each in words: a site's scene time, its place on its ground or its plan (its
    shape), two sites standing on one spot of a ground (under a metre apart: each site has its own place in the
    setting), and two whose footprints overlap where the setting stands them."""
    names = {site["place"]: site["name"] for world in plan["maps"] for site in world["sites"]}
    return [f"{site['name']}: no {what}" for world in plan["maps"] for site in world["sites"]
            for what, missing in (("scene time", site.get("time") is None),
                                  ("place on its ground", "x" not in site and site.get("latitude") is None),
                                  ("plan yet", "size" in site and site["size"] is None))
            if missing] + \
        [f"{names[found['from']]} and {names[found['to']]} stand on one spot of {world['name']}"
         for world in plan["maps"] for found in world.get("distances", []) if found["metres"] < SAME_SPOT] + \
        [f"{one['name']} and {two['name']} overlap on {world['name']}: move one in the physics"
         for world in plan["maps"] for one, two in overlapping(world)]


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
            shape = from_plan(site_plan(store, site["place"])) if store is not None else {}
            sites.append({**site, **where, **shape})
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
    """His plan as he left it: each site's scene time where in shape, the rest from `base` (where a site stands is the
    environment concept's setting, its shape its own plan's)."""
    if not isinstance(plan, dict) or not isinstance(plan.get("maps"), list):
        raise Refused("an environment plan has maps")
    sent = {(world.get("on"), site.get("place")): site for world in plan["maps"] if isinstance(world, dict)
            for site in world.get("sites") or [] if isinstance(site, dict)}
    maps = []
    for world in base["maps"]:
        sites = []
        for site in world["sites"]:
            his = sent.get((world["on"], site["place"]), {})
            sites.append({**site, "time": moment(his["time"]) if his.get("time") else site.get("time")})
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
