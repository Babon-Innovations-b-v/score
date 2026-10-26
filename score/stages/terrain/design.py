"""The grounds of the environment from its design alone (the owner, 2026-10-21: every stage builds from the creator's
design; the game's ground plans and copied grounds were retired): each top scene stands at its site on the body or
plot its environment concept's setting puts it (`{home}/design/sky/<scene>.json`, scene_sky.keep's), and every scene
its plan holds stands where that plan holds it. A ground is one body or plot: the body's true sphere (its radius from
the setting's bodies) or the plot's plane, raised by the relief of each kept plan's terrain spots standing on it
(`terrain.spots`: [x, y, height] in plan metres over the scene's floor), interpolated by a thin-plate spline
through the spots, faded out past the farthest spot.

    found = design.layout(plans, skies)         # {ground: {on, kind, radius, tops, places, sources}}
    design.ground_points(ground, place, xz)     # the ground under (x, z) spots of a place's frame, as [x, y, z]
    design.on_ground(place)                     # whether the design stands the place on a ground

Frames: a place's frame is its plan's (scene_record.plan.frame_of: x east, z south, y up, its floor at the frame's
corner height). World: a body's middle at the origin, its pole along +z (east, north and up at a site from its
latitude and longitude); a plot's plane z = 0, x east and y north. A scene its top holds is laid unturned in its hold's
box on the top's plan, its floor on the top's floor.
"""
import hashlib
import json
import math
import pathlib

import numpy as np

from score.stages import natural_grounds
from score.stages.scene_record import plan as place_plan
from score.store import PROPS_HOME

KEPT_PLANS = PROPS_HOME / "design" / "plans"
KEPT_SKIES = PROPS_HOME / "design" / "sky"
# A source's relief is faded out between its farthest spot's distance from its plan's middle and this many times it.
FADE_PAST = 1.3
# The far ground's landforms (far_row): a terrain row of the ground or the backdrop the plan marks beyond the place
# (the campgrounds' distant hills), raised round it over the bearings its concept box spans (as water's, water_span;
# all round without a heading), fading to nothing its breadth past them, at the horizon a person's eye (EYE metres up)
# sees on a body (FAR_SHARE of the far ground's reach on a plot, which has none), as tall as its box rises in the
# concept seen with the framework's view (scene_record.writer.VIEW_FOV across), as broad as its read size is to its
# height, never broader than FAR_BROAD of its distance; its height along the ring varies by FAR_WAVES seeded waves of
# its id.
FAR_PARTS = ("ground", "backdrop")
EYE = 1.7
FAR_SHARE = 0.6
FAR_BROAD = 0.5
FAR_WAVES = 6
# A body of water (water_row: a terrain row whose words name the ocean recipe, the square's sea) lies at its plan
# level's height, else FREEBOARD under the place's floor (a quay's edge), over the ground lowered SEABED under that
# line wherever it lies: its level's points on the plan and, out past the place's outline, the bearings its concept
# box spans (scene_record/far.py) out to the far shore its far objects stand on, else the far landforms' horizon.
SEABED = 2.0
FREEBOARD = 1.0


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def kept(folder):
    """{name: record} of every json file in a folder."""
    return {path.stem: read(path) for path in sorted(pathlib.Path(folder).glob("*.json"))}


def holder_of(place, plans):
    """(the scene whose plan holds the place, its hold) or (None, None)."""
    for name, plan in sorted(plans.items()):
        for hold in plan.get("holds") or []:
            if hold.get("place") == place and name != place:
                return name, hold
    return None, None


def body_of(setting, on):
    """(the body or plot a site stands on, "body" or "plot"); (None, None) when the setting has neither."""
    for body in setting.get("bodies", []):
        if body["body"] == on:
            return body, "body"
    for plot in setting.get("plots", []):
        if plot["plot"] == on:
            return plot, "plot"
    return None, None


def site_axes(site, kind):
    """(the site's point, its east, south and up) in the ground's world, before its radius: a body's on the unit
    sphere, a plot's in metres."""
    if kind == "plot":
        east, north, up = np.eye(3)
        return east * float(site.get("x") or 0.0) - north * float(site.get("y") or 0.0), east, -north, up
    lat, lon = math.radians(float(site["latitude"])), math.radians(float(site["longitude"]))
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)])
    return up, east, -north, up


def top_entry(top, plan, kept_sky):
    """A top scene's site on its ground: its point, east, south and up in the world, its plan's middle there."""
    site = kept_sky["site"]
    found, kind = body_of(kept_sky["setting"], site["on"])
    point, east, south, up = site_axes(site, kind)
    radius = float(found["radius_km"]) * 1000.0 if kind == "body" else None
    height = float(site.get("height_m") or 0.0)
    middle = point * (radius + height) if kind == "body" else point + up * height
    return {"site": site, "kind": kind, "radius": radius, "middle": middle.tolist(), "east": east.tolist(),
            "south": south.tolist(), "up": up.tolist(), "half": [float(plan["w"]) / 2, float(plan["d"]) / 2]}


def tangent(top, plan_points):
    """Plan points [[x, y]] of a top scene, on its floor's tangent plane in the world."""
    middle, east, south = (np.asarray(top[key], dtype=float) for key in ("middle", "east", "south"))
    points = np.asarray(plan_points, dtype=float).reshape(-1, 2) - np.asarray(top["half"])
    return middle + np.outer(points[:, 0], east) + np.outer(points[:, 1], south)


def place_entry(top, plan, offset):
    """A place's frame in the world: its origin and axes (columns: its x, y, z) and its floor's height in its frame,
    its plan laid at `offset` (plan metres) on its top's plan."""
    corner, east_p, south_p = place_plan.frame_of(plan)
    origin_plan = np.array([-float(corner @ east_p), -float(corner @ south_p)]) + np.asarray(offset, dtype=float)
    east, south, up = (np.asarray(top[key], dtype=float) for key in ("east", "south", "up"))
    axes = np.column_stack([east * east_p[0] + south * south_p[0], up, east * east_p[2] + south * south_p[2]])
    origin = tangent(top, [origin_plan])[0] - up * float(corner[1])
    corners = np.array([corner + east_p * x + south_p * y for x in (0.0, float(plan["w"]))
                        for y in (0.0, float(plan["d"]))])[:, [0, 2]]
    return {"origin": origin.tolist(), "axes": axes.tolist(), "floor": float(corner[1]),
            "box": [corners.min(axis=0).round(4).tolist(), corners.max(axis=0).round(4).tolist()]}


def layout(plans, skies):
    """Every ground of the design: {ground (its body or plot): {on, kind, radius, tops: {top: site entry}, places:
    {place: frame entry, its top}, sources: [the terrain spots standing on it]}}. A top scene is one no plan holds,
    whose kept sky names it as its own top with a site its setting knows; it and each scene its plan holds stand on
    the ground."""
    found = {}
    for top, plan in sorted(plans.items()):
        kept_sky = skies.get(top)
        if holder_of(top, plans)[0] is not None or not kept_sky or kept_sky.get("top") != top:
            continue
        if body_of(kept_sky["setting"], kept_sky["site"]["on"])[1] is None:
            continue
        entry = top_entry(top, plan, kept_sky)
        ground = found.setdefault(kept_sky["site"]["on"], {"on": kept_sky["site"]["on"], "kind": entry["kind"],
                                                           "radius": entry["radius"], "tops": {}, "places": {},
                                                           "sources": []})
        ground["tops"][top] = entry
        held = [(top, plan, [0.0, 0.0])] + [(hold["place"], plans[hold["place"]], [hold["x"], hold["y"]])
                                            for hold in plan.get("holds") or [] if hold.get("place") in plans]
        for name, own, offset in held:
            ground["places"][name] = {**place_entry(entry, own, offset), "top": top}
            spots = (own.get("terrain") or {}).get("spots") or []
            if spots:
                ground["sources"].append({"place": name, "top": top, "offset": offset,
                                          "middle": [float(own["w"]) / 2, float(own["d"]) / 2],
                                          "spots": [[float(value) for value in spot[:3]] for spot in spots]})
    return found


def on_ground(place, plans_folder=KEPT_PLANS, skies_folder=KEPT_SKIES):
    """Whether the design stands the place on a ground (a top scene at its site, or a scene its plan holds)."""
    return any(place in ground["places"] for ground in layout(kept(plans_folder), kept(skies_folder)).values())


# --- the ground's surface ------------------------------------------------------------------------------------------

def spline(source):
    """The relief of a source's spots in its plan metres: a function of [[x, y]] giving heights, or None when its
    spots give no relief (fewer than three, or all one height: then each spot's height is the whole relief)."""
    spots = np.asarray(source["spots"], dtype=float)
    spots = spots[np.unique(spots[:, :2], axis=0, return_index=True)[1]]
    if len(spots) < 3 or np.ptp(spots[:, 2]) < 1e-3:
        return None
    from scipy.interpolate import RBFInterpolator
    shape = RBFInterpolator(spots[:, :2], spots[:, 2], kernel="thin_plate_spline", smoothing=1e-3)
    middle = np.asarray(source["middle"])
    reach = float(np.hypot(*(spots[:, :2] - middle).T).max()) or 1.0

    def relief(points):
        points = np.atleast_2d(points)
        far = np.hypot(*(points - middle).T)
        return shape(points) * np.clip((FADE_PAST * reach - far) / ((FADE_PAST - 1.0) * reach), 0.0, 1.0)
    return relief


def flat_relief(source):
    """The relief of a source whose spots stand at one height (or are fewer than three): that height, faded out
    past its farthest spot as a spline's is."""
    spots = np.asarray(source["spots"], dtype=float)
    middle = np.asarray(source["middle"])
    reach = float(np.hypot(*(spots[:, :2] - middle).T).max()) or 1.0
    height = float(spots[:, 2].mean())

    def relief(points):
        far = np.hypot(*(np.atleast_2d(points) - middle).T)
        return height * np.clip((FADE_PAST * reach - far) / ((FADE_PAST - 1.0) * reach), 0.0, 1.0)
    return relief


def reliefs(ground):
    """[(source, its relief in its plan metres)] of a ground."""
    return [(source, spline(source) or flat_relief(source)) for source in ground["sources"]]


def far_row(row, beyond):
    """Whether a scene inventory row is a landform of the far ground (FAR_PARTS): the terrain's to make, no model."""
    return bool(row.get("terrain")) and row.get("part") in FAR_PARTS and row["id"] in beyond


def water_row(row):
    """Whether a scene inventory row is a body of water (its words name the ocean recipe, natural_grounds.named) on
    the ground (a terrain row): the terrain's to lay, no model."""
    return bool(row.get("terrain")) and natural_grounds.named(row) == "ocean"


def water_level(plan, row):
    """(height over the floor, points or None) of a water row's level on its plan: the first level whose name names
    water or shares a word with the row's id; else FREEBOARD under the floor, no points."""
    words = set(row["id"].split("_"))
    for level in plan.get("levels") or []:
        name = str(level.get("name") or "")
        if natural_grounds.named({"name": name}) == "ocean" or words & set(name.lower().split()):
            if len(level.get("points") or []) >= 3:
                return float(level.get("height") or 0.0), level["points"]
    return -FREEBOARD, None


def inside_points(points, polygon):
    """Whether each plan point lies inside a polygon [[x, y], ...]."""
    from matplotlib.path import Path
    return Path(np.asarray(polygon, dtype=float)).contains_points(np.atleast_2d(points))


def shore_of(plan, inventory, span, horizon):
    """How far out a water's span reaches: to the nearest far object (far.far_object) standing in it, less its deep,
    else to `horizon`."""
    from score.stages.scene_record import far
    beyond, found = set(plan.get("beyond") or []), []
    for row in inventory.get("rows", []):
        placed = far.far_object(row, beyond) and far.spot(plan, inventory, row)
        if placed and span[0] <= angle_of(placed["bearing"], span[2]) <= span[1]:
            found.append(placed["distance"] - max(float(side) for side in row["size"][:2]) / 2)
    return max(min(found), 0.0) if found else horizon


def angle_of(direction, ways):
    """The angle (radians, right positive) of a plan direction off the heading `ways` (far.heading's)."""
    away, right = ways
    return math.atan2(float(np.asarray(direction) @ right), float(np.asarray(direction) @ away))


def water_span(plan, inventory, row):
    """(least angle, most angle, heading) of the bearings a water or far row's concept box spans; None without a
    heading or a box."""
    from score.stages.scene_record import far
    picture, ways = inventory.get("picture"), far.heading(plan, inventory)
    box = far.box_of(row, picture)
    if ways is None or not box:
        return None
    return far.angle_at(box[0], picture), far.angle_at(box[2], picture), ways


def water_region(plan, points, span, shore):
    """A function of plan points [[x, y]]: inside the water's level points (`points`), or, out past the plan's
    outline, within its concept box's bearings (`span`) and nearer than its `shore`."""
    from score.stages.scene_record import far
    middle = far.middle_of(plan)
    outline = plan.get("outline") or [[0, 0], [plan["w"], 0], [plan["w"], plan["d"]], [0, plan["d"]]]

    def region(spots):
        spots = np.atleast_2d(spots)
        found = inside_points(spots, points) if points else np.zeros(len(spots), bool)
        if span is not None:
            apart = spots - middle
            away, right = span[2]
            angles = np.arctan2(apart @ right, apart @ away)
            found |= (angles >= span[0]) & (angles <= span[1]) & (np.hypot(*apart.T) < shore) & \
                ~inside_points(spots, outline)
        return found
    return region


def waters(ground, plans, inventories, reach):
    """[(source, the seabed's relief, its water line)] of every body of water of the places standing on the ground
    (water_row; one beyond a place that a scene holds is its holder's, laid there) and [{place, row, level, shore,
    from}] of what was laid."""
    horizon, found, laid = far_distance(ground, reach), [], []
    for place, entry in sorted(ground["places"].items()):
        path = pathlib.Path(inventories) / f"{place}.json"
        inventory, plan = (read(path) if path.is_file() else {}), plans[place]
        hold = holder_of(place, plans)[1]
        for row in inventory.get("rows", []):
            if not water_row(row) or (hold and row["id"] in set(plan.get("beyond") or [])):
                continue
            level, points = water_level(plan, row)
            span = water_span(plan, inventory, row)
            shore = shore_of(plan, inventory, span, horizon) if span else horizon
            region = water_region(plan, points, span, shore)
            source = {"place": place, "top": entry["top"], "offset": [hold["x"], hold["y"]] if hold else [0.0, 0.0],
                      "middle": [float(plan["w"]) / 2, float(plan["d"]) / 2]}
            found.append((source, seabed(region, level), level, row))
            laid.append({"place": place, "row": row["id"], "level": level, "shore": round(shore, 1) if span else None,
                         "from": ("its plan's level" if points else f"{FREEBOARD:g} m under the floor (no level of it "
                                  "on the plan)") + (", out to its far shore along its concept box's bearings"
                                                     if span else "")})
    return found, laid


def seabed(region, level):
    """The relief that lowers the ground SEABED under a water line `level` wherever `region` holds."""
    def relief(points):
        return np.where(region(points), level - SEABED, 0.0)
    return relief


def far_size(row, picture, distance):
    """(height, half breadth) in metres of a far row standing `distance` metres off: its box's rise over its foot in
    the concept seen with the framework's view, its breadth its read size's wide to tall times that (FAR_BROAD of
    its distance at most)."""
    from score.stages.scene_record.writer import VIEW_FOV
    box = (row.get("boxes") or [row.get("box")])[0]
    focal = picture[0] / 2 / math.tan(math.radians(VIEW_FOV) / 2)
    height = distance * (box[3] - box[1]) / focal
    size = row.get("size") if isinstance(row.get("size"), list) and len(row["size"]) >= 3 else [1.0, 1.0, 1.0]
    return height, min(FAR_BROAD * distance, height * float(size[0]) / max(float(size[2]), 1e-3) / 2)


def far_ring(middle, distance, height, broad, seed, span=None):
    """The relief of a ring of landforms round `middle` (plan metres): `height` at `distance`, falling as a cosine to
    nothing `broad` metres either side, its height along the ring between 0.4 and 1 of it by FAR_WAVES seeded waves;
    with a `span` (water_span's) only over its bearings, falling to nothing `broad` metres along the ring past them."""
    draws = np.random.default_rng(seed)
    turns = draws.integers(1, max(2, int(math.pi * distance / max(broad, 1.0))) + 1, FAR_WAVES)
    phases = draws.uniform(0.0, 2 * math.pi, FAR_WAVES)

    def relief(points):
        apart = np.atleast_2d(points) - np.asarray(middle)
        far, bearing = np.hypot(*apart.T), np.arctan2(apart[:, 1], apart[:, 0])
        along = 0.7 + 0.3 * np.mean([np.cos(turn * bearing + phase) for turn, phase in zip(turns, phases)], axis=0)
        apart_by = (far - distance) / broad
        across = np.where(np.abs(apart_by) < 1.0, np.cos(np.clip(apart_by, -1.0, 1.0) * math.pi / 2) ** 2, 0.0)
        return height * along * across * shown(apart)

    def shown(apart):
        if span is None:
            return 1.0
        away, right = span[2]
        angle = np.arctan2(apart @ right, apart @ away)
        past = (np.maximum(span[0] - angle, 0.0) + np.maximum(angle - span[1], 0.0)) * distance / broad
        return np.where(past < 1.0, np.cos(np.clip(past, 0.0, 1.0) * math.pi / 2) ** 2, 0.0)
    return relief


def far_distance(ground, reach):
    """How far off the far ground's landforms stand: the horizon a person's eye sees on a body, FAR_SHARE of the far
    ground's `reach` on a plot (and on a body never past it)."""
    if ground["kind"] != "body":
        return FAR_SHARE * reach
    return min(math.sqrt(2.0 * ground["radius"] * EYE), FAR_SHARE * reach)


def far_reliefs(ground, plans, inventories, reach):
    """[(source, its relief)] of every far row (far_row) of the places standing on the ground, each round its place
    over the bearings its concept box spans (far_ring, water_span; all round without a heading), and [{place, row,
    distance, height, broad, bearings}] of what was raised (bearings: [least, most] degrees right of the concept's
    view, None all round)."""
    distance, found, made = far_distance(ground, reach), [], []
    for place, entry in sorted(ground["places"].items()):
        path = pathlib.Path(inventories) / f"{place}.json"
        inventory = read(path) if path.is_file() else {}
        plan, picture = plans[place], inventory.get("picture")
        hold = holder_of(place, plans)[1]
        offset = [hold["x"], hold["y"]] if hold else [0.0, 0.0]
        for row in inventory.get("rows", []):
            if not (picture and far_row(row, set(plan.get("beyond") or [])) and (row.get("boxes") or row.get("box"))):
                continue
            height, broad = far_size(row, picture, distance)
            middle = [float(plan["w"]) / 2, float(plan["d"]) / 2]
            seed = int(hashlib.sha256(f"{place}/{row['id']}".encode()).hexdigest()[:8], 16)
            span = water_span(plan, inventory, row)
            found.append(({"place": place, "top": entry["top"], "offset": offset, "middle": middle},
                          far_ring(middle, distance, height, broad, seed, span)))
            made.append({"place": place, "row": row["id"], "distance": round(distance, 1), "height": round(height, 1),
                         "broad": round(broad, 1),
                         "bearings": [round(math.degrees(angle), 1) for angle in span[:2]] if span else None})
    return found, made


def relief_at(ground, world, shaped=None):
    """The sum of every source's relief under world points (each read in its source's plan metres)."""
    world = np.atleast_2d(world)
    total = np.zeros(len(world))
    for source, relief in shaped if shaped is not None else reliefs(ground):
        top = ground["tops"][source["top"]]
        middle, east, south = (np.asarray(top[key], dtype=float) for key in ("middle", "east", "south"))
        plan = np.column_stack([(world - middle) @ east, (world - middle) @ south]) + np.asarray(top["half"]) - \
            np.asarray(source["offset"])
        total += relief(plan)
    return total


def ground_points(ground, place, xz, shaped=None):
    """The ground under spots [[x, z]] of a place's frame, as points [x, y, z] of its frame: on the body's true sphere
    (or the plot's plane) at its top's height, raised by the relief there."""
    entry = ground["places"][place]
    top = ground["tops"][entry["top"]]
    origin, axes = np.asarray(entry["origin"], dtype=float), np.asarray(entry["axes"], dtype=float)
    xz = np.atleast_2d(np.asarray(xz, dtype=float))
    level = origin + (np.column_stack([xz[:, 0], np.full(len(xz), entry["floor"]), xz[:, 1]]) @ axes.T)
    relief = relief_at(ground, level, shaped)
    up = np.asarray(top["up"], dtype=float)
    if ground["kind"] == "body":
        height = float(top["site"].get("height_m") or 0.0)
        found = level / np.linalg.norm(level, axis=1, keepdims=True) * (ground["radius"] + height + relief)[:, None]
    else:
        found = level - np.outer(level @ up, up) + np.outer(float(np.asarray(top["middle"]) @ up) + relief, up)
    return (found - origin) @ axes


def ball_of(ground, place):
    """A body's middle and radius in a place's frame (sight.voids' small-world horizon), None on a plot."""
    if ground["kind"] != "body":
        return None
    entry = ground["places"][place]
    origin, axes = np.asarray(entry["origin"], dtype=float), np.asarray(entry["axes"], dtype=float)
    return (-origin) @ axes, float(ground["radius"])
