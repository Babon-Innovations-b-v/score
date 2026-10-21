"""scene-record@<place>: the place's scene record written by SCORE from its design alone (the owner, 2026-10-21: every
stage builds from the creator's design; nothing old is read): its locked plan (the plan row's plan.json, and the kept
plan itself for what the plan row does not carry: its outline, walls, openings, levels, stairs, roofs, items' shapes
and the places its holder's plan holds), its scene inventory (the row kinds: which rows glow), the library's lamp,
and its sky inputs (`{home}/design/sky/<place>.json`: the environment concept's physics, its site and scene time,
worked out by score/review/overhead.py). Contract `scene-record` v1 is today's record schema, so tools/usd/scene.py
builds it unchanged; it lands as record/<place>.json in the output.

    inside       the plan encloses the place (walls or roofs drawn) on no ground of its own (no terrain spots)
    structure    an inside place's room shell from its plan (earth_seed/design_shell.pieces: each level's deck, the
                 outline's walls with every opening cut, the roofs), stood in the place's frame as builders' `slab` and
                 `gable` entries BACKING behind the plan's inside line; none where the place's base already lays it
                 (design_shell.laid_for: a room whose plan says its kit holds its walls); and each stair or ramp the
                 plan draws as a flight of steps; each entry's surface the scene's surface library's for its kind
                 (surface-library@<place>, read as an `after`: design_shell.PART_KINDS), else none and
                 `surface_missing` says why (the scene builder names it on the mesh, never paints another way)
    lights       one at each plan item of a glowing row (its row kind, score/stages/row_kinds.py): over the item's
                 middle, as high on it as the library's lamp for the row's mount says, its numbers that lamp's
                 (data/library/lamps.json, tools/props/scene/lamps.py), reaching by how high it hangs
    environment  inside or not, and the sky at the place's site at its scene time from the physics (overhead.py: each
                 light over the horizon, every other body, every backdrop), which the light layer draws
                 (score/stages/light/sky.py); the record draws no sky and holds no air the design does not give
    views        one from inside each doorway looking across, one from each of the plan's person spots (an inside
                 place's only where the eye stands inside its outline: the others in `views_left_out`, with why)
    doorways     the plan's doorways in the place's frame (the plan row's), which ground-fit judges
    places       each other place its holder's plan holds that a door or opening of this place leads to, stood where
                 the holder's plan holds it (`holds`), turned as its own plan's frame is

Every entry's `from` names the plan element, inventory row or physics it was made from. Nothing of a game, a kit, a
filed definition or an old record is read.
"""
import json
import math
import pathlib
import sys

import numpy as np

from score import contracts
from score.review import overhead
from score.stages import row_kinds
from score.stages.earth_seed import design_shell
from score.stages.scene_record import plan as place_plan

REPO = pathlib.Path(__file__).resolve().parents[3]
# The shell's backing: it stands this far behind the plan's inside line, its deck this far under the floor
# (design_shell's, which lays the same shell in a kit room's base).
BACKING = design_shell.BACKING
DECK_BELOW = design_shell.DECK_BELOW
# A part's surface is the scene's surface library's for its kind (design_shell.PART_KINDS), else none and named
# missing (`surface_missing`, which tools/usd/scene.py marks the mesh with).
LIBRARY_ROW = "surface-library"
# A ramp is laid as a flight of steps this high each (metres), fine enough to walk as a slope.
RAMP_STEP = 0.05
# A view stands this far inside its doorway, and every view sees this wide (degrees).
VIEW_IN = 1.0
VIEW_FOV = 80
AIM_HEIGHT = 1.0
# What a door may lead to that is no place.
NOT_PLACES = ("outside", "sealed")


def files(place):
    """The design files the writer reads: the place's kept plan and every other (its holder's `holds`, its siblings'
    frames), its scene inventory, its sky inputs (scene_sky.keep's), the row-kind rules, the library's lamp and the
    environment's eye height (place.json `shared`)."""
    return {"inventory": "{home}/design/inventory/{place}.json", "plans": "{home}/design/plans",
            "sky": "{home}/design/sky/{place}.json", "row kinds": "{data}/checks/row-kinds.json",
            "lamp library": "{data}/library/lamps.json", "places": "{data}/definitions/place.json"}


def read(path):
    return json.loads(pathlib.Path(path).read_text())


# --- the shell ----------------------------------------------------------------------------------------------------

def inside(design):
    """Whether the plan encloses the place: walls or roofs drawn, and no ground of its own (terrain spots)."""
    return bool(design.get("walls") or design.get("roofs")) and not (design.get("terrain") or {}).get("spots")


def in_frame(design, points, level=0.0):
    """Plan points [[x, y]] as [[x, z]] in the place's frame, and the frame's height `level` metres over its floor."""
    corner, east, south = place_plan.frame_of(design)
    placed = [corner + east * float(x) + south * float(y) for x, y in points]
    return [[round(float(point[0]), 4), round(float(point[2]), 4)] for point in placed], \
        round(float(corner[1]) + level, 4)


def library_of(inputs):
    """The scene's surface library (its surface-library output's materials.json content), else None: none made."""
    return design_shell.library_of(pathlib.Path(inputs[LIBRARY_ROW]) / "materials.json") \
        if LIBRARY_ROW in inputs else None


def painted(entry, kind, place, library):
    """The entry with its surface: the scene library's for a part of `kind`, else none and why (`surface_missing`)."""
    surface = design_shell.surface_for(kind, library)
    if surface is None:
        return dict(entry, surface=None, surface_missing=design_shell.missing_why(place, kind, library))
    return dict(entry, surface=surface)


def shell_entry(name, number, piece, design, said):
    """One shell piece (design_shell.pieces) as a structure entry in the place's frame, its surface not yet given."""
    points, floor = in_frame(design, piece["points"])
    entry = {"name": name if number == 0 else f"{name}_{number + 1}", "builder": piece["builder"], "points": points,
             "plain": "shell", "from": said}
    if piece["builder"] == "gable":
        entry.update(eave=round(floor + piece["eave"], 4), top=round(floor + piece["top"], 4), layer=2)
    else:
        entry.update(low=round(floor + piece["low"], 4), high=round(floor + piece["high"], 4))
        if name.startswith("roof"):
            entry["layer"] = 2
    return entry


def shell(design, place, library):
    """The room shell's entries (design_shell.pieces) stood in the place's frame, each painted from the scene's
    library by its part's kind."""
    return [painted(shell_entry(name, number, piece, design, said), design_shell.part_kind(name), place, library)
            for name, parts, said in design_shell.pieces(design) for number, piece in enumerate(parts)]


def stair(number, entry, design):
    """A stair or ramp the plan draws as a flight of steps up its footprint the way it says (`angle`: degrees from east,
    clockwise as y runs south), from its `from` height to its `to`."""
    points = np.asarray(entry["points"], dtype=float)
    turn = math.radians(float(entry.get("angle") or 0.0))
    way, across = np.array([math.cos(turn), math.sin(turn)]), np.array([-math.sin(turn), math.cos(turn)])
    along, side = points @ way, points @ across
    middle = way * (along.min() + along.max()) / 2 + across * (side.min() + side.max()) / 2
    half = way * (along.max() - along.min()) / 2
    (foot, top), floor = in_frame(design, [middle - half, middle + half])
    low, high = float(entry["from"]), float(entry["to"])
    steps = int(entry.get("steps") or 0) if entry.get("kind") != "ramp" else \
        max(1, math.ceil(abs(high - low) / RAMP_STEP))
    return {"name": f"{entry.get('kind', 'stair')}_{number}", "builder": "stairs",
            "foot": [foot[0], round(floor + low, 4), foot[1]], "top": [top[0], round(floor + high, 4), top[1]],
            "wide": round(float(side.max() - side.min()), 4), "steps": max(1, steps),
            "from": f"the plan's {entry.get('kind', 'stair')} {number}: from {low:g} m to {high:g} m, "
                    f"{max(1, steps)} steps up its footprint at {float(entry.get('angle') or 0.0):g} degrees"}


def structure(plan, design, library=None):
    """The record's structure: an inside place's shell where its base does not lay it, and the plan's stairs, each
    painted from the scene's surface library (`library`: its materials.json content, None while not made)."""
    shelled = shell(design, plan["place"], library) if inside(design) and not design_shell.laid_for(design) else []
    return shelled + [painted(stair(number, entry, design), "stair", plan["place"], library)
                      for number, entry in enumerate(design.get("stairs") or [], 1)
                      if len(entry.get("points") or []) >= 3]


# --- lights -------------------------------------------------------------------------------------------------------

def library_lamps():
    """The library's lamp code (tools/props/scene/lamps.py: its mounts and how a row is mounted)."""
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import lamps
    return lamps


def game_lamp():
    """The lamp the library's strengths are shares of (tools/usd/scene.py): (energy, colour, attenuation)."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    return scene.LAMP_ENERGY, scene.LAMP_COLOUR, scene.LAMP_ATTENUATION


def item_lamp(item, row, rows, design, library, path):
    """The light of a glowing row's plan item: over its middle, as high on it as the library's lamp for the row's
    mount puts it, reaching by how high that is over the floor."""
    name, x, y, wide, deep = item[0], *[float(value) for value in item[1:5]]
    shape = (design.get("shapes") or {}).get(name) or {}
    base, tall = float(shape.get("base") or 0.0), float(shape.get("tall") or 0.0)
    mounts, words = library.mounts(path), library.mount_words(path)
    share = float(mounts[library.mount_of(row, rows, words)]["high"])
    high = base + tall * share
    light = library.light_at(row, high, rows, mounts, words)
    energy, colour, attenuation = game_lamp()
    (spot,), floor = in_frame(design, [[x + wide / 2, y + deep / 2]], high)
    return {"type": "omni", "at": [spot[0], floor, spot[1]], "colour": colour,
            "energy": round(energy * light["strength"], 4), "range": light["reach"], "attenuation": attenuation,
            "shadows": light["shadows"],
            "from": f"plan item {name!r}, inventory row {row['id']} (row kind {row['row_kind']}, it glows): the "
                    f"library's lamp (data/library/lamps.json) for its mount, {high:.2f} m over the floor"}


def lights(design, inputs):
    """A light at each plan item of the scene's glowing rows (row_kinds.rows_that)."""
    inventory = read(inputs["inventory"])
    glowing = {row["id"]: row for row in row_kinds.rows_that(inventory, "glows", row_kinds.table(inputs["row kinds"]))}
    rows_of, library = design.get("rows") or {}, library_lamps()
    found = []
    for item in design.get("items") or []:
        if len(item) > 6 and item[6] == "zone":
            continue
        for row_id in rows_of.get(item[0]) or []:
            if row_id in glowing:
                found.append(item_lamp(item, glowing[row_id], inventory["rows"], design, library,
                                       inputs["lamp library"]))
    return found


# --- the sky ------------------------------------------------------------------------------------------------------

def sky_seen(kept):
    """What overhead.py says is overhead at the kept site at its scene time: its lights over the horizon (their disc
    at least partly up), its bodies and backdrops; None while the site's position is not known."""
    seen = overhead.seen(kept["setting"], kept["site"], kept["time"])
    if seen is None:
        return None
    risen = [light for light in seen["lights"] if light["altitude"] + (light.get("across") or 0.0) / 2.0 > 0.0]
    return {"lights": [{key: light[key] for key in ("name", "of", "azimuth", "altitude", "kelvin", "lux")
                        if key in light} for light in risen],
            "bodies": [{key: body[key] for key in ("body", "name", "azimuth", "altitude", "across", "lit")
                        if key in body} for body in seen["bodies"]],
            "backdrops": seen["backdrops"]}


def environment(design, kept):
    """Inside or not, and the place's sky from the physics at its site at its scene time (sky_seen)."""
    site = kept["site"]
    return {"inside": inside(design), "site": site, "time": kept["time"], "sky": sky_seen(kept),
            "from": f"the environment concept's physics (score/review/overhead.py) at the place's site on "
                    f"{site.get('on')} at its scene time {kept['time']}; its sky is drawn by the light layer"}


# --- views --------------------------------------------------------------------------------------------------------

def middle_of(plan):
    """The plan's inside's middle on its floor, in the place's frame (x, z)."""
    (low_x, low_z), (high_x, high_z) = plan["floor"]
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def item_middle(plan, name):
    low_x, low_z, high_x, high_z = next(item["box"] for item in plan["items"] if item["name"] == name)
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def views(plan, eye_height):
    """One view inside each doorway looking across the inside's middle (the doorway's mirror through it), one from
    each standing spot to the middle at its own level or to the plan item it looks at on the floor; each eye at
    standing height over its level (the plan row's plan.json: its `doorways` and `standing`)."""
    found, middle = [], middle_of(plan)
    for door in plan.get("doorways", []):
        at = np.asarray(door["middle"], dtype=float)
        eye = at + np.asarray(door["inward"], dtype=float) * VIEW_IN
        aim = 2 * middle - at[[0, 2]]
        found.append({"name": f"from-{door['name']}", "eye": [round(eye[0], 3), round(at[1] + eye_height, 3),
                                                             round(eye[2], 3)],
                      "aim": [round(aim[0], 3), round(at[1] + AIM_HEIGHT, 3), round(aim[1], 3)], "fov": VIEW_FOV,
                      "from": f"plan {door['name']} ({door['wide']:g} m wide, to {door['to']}), looking across"})
    for number, spot in enumerate(plan["standing"], 1):
        aim = item_middle(plan, spot["looks_at"]) if spot["looks_at"] else middle
        aim_level = plan["floor_height"] if spot["looks_at"] else spot["level"]
        found.append({"name": f"spot-{number}",
                      "eye": [round(spot["at"][0], 3), round(spot["level"] + eye_height, 3), round(spot["at"][1], 3)],
                      "aim": [round(aim[0], 3), round(aim_level + AIM_HEIGHT, 3), round(aim[1], 3)],
                      "fov": VIEW_FOV, "from": f"plan standing spot {number}, looking to " +
                                              (f"plan item {spot['looks_at']!r}" if spot["looks_at"] else "the middle")})
    return found


def inside_polygon(point, points):
    """Whether a point [x, z] lies inside an outline [[x, z]] (even-odd rule)."""
    found = False
    for one, two in zip(points, points[1:] + points[:1]):
        if (one[1] > point[1]) != (two[1] > point[1]):
            cross = one[0] + (point[1] - one[1]) * (two[0] - one[0]) / (two[1] - one[1])
            found ^= point[0] < cross
    return found


def views_inside(found, design, enclosed):
    """(kept, left out) of an inside place's views: one whose eye stands outside its plan's outline sees its walls
    from behind, so it is left out with why; an open place keeps every view."""
    if not enclosed:
        return found, []
    outline, _ = in_frame(design, design_shell.outline_of(design))
    kept = [view for view in found if inside_polygon([view["eye"][0], view["eye"][2]], outline)]
    return kept, [{"name": view["name"], "eye": view["eye"], "from": view["from"],
                   "why": "its eye stands outside the plan's outline: it would see the walls from behind"}
                  for view in found if view not in kept]


# --- places -------------------------------------------------------------------------------------------------------

def holder_of(place, plans):
    """(holder's name, its plan) of the plan that holds the place (`holds`), else (None, None)."""
    for path in sorted(pathlib.Path(plans).glob("*.json")):
        held = read(path)
        if any(hold.get("place") == place for hold in held.get("holds") or []):
            return path.stem, held
    return None, None


def leads_of(plan, design):
    """Every place a door (the plan row's `leads`) or an opening (the kept plan's `to`) of the place leads to."""
    found = {door["leads"] for door in plan["doors"]} | {opening.get("to") for opening in design.get("openings") or []}
    return sorted(name for name in found if name and name not in NOT_PLACES)


def origin_on_holder(design, hold):
    """The place's frame origin as a point of its holder's plan: its own plan laid unturned in its hold's box."""
    corner, east, south = place_plan.frame_of(design)
    return np.array([hold["x"] - float(corner @ east), hold["y"] - float(corner @ south)]), float(corner[1])


def axes_in(design, other):
    """The other place's frame axes (rows: across, up, along) in this place's frame, both plans laid unturned on
    their holder's plan."""
    _, east, south = place_plan.frame_of(design)
    _, other_east, other_south = place_plan.frame_of(other)
    return np.array([east * float(axis @ other_east) + south * float(axis @ other_south) + np.array([0.0, axis[1], 0.0])
                     for axis in np.eye(3)])


def quaternion(axes):
    """A turn (rows: the turned x, y, z axes, row vectors) as [x, y, z, w], as scene.turn reads `rotation`."""
    from pxr import Gf
    quat = Gf.Matrix3d(*np.asarray(axes, dtype=float).ravel().tolist()).ExtractRotation().GetQuat()
    return [round(value, 6) for value in (*quat.GetImaginary(), quat.GetReal())]


def sibling(place, design, holder, name, plans):
    """A place the holder's plan holds beside this one, stood in this place's frame where the holder holds it."""
    holds = {hold["place"]: hold for hold in holder.get("holds") or []}
    other = read(pathlib.Path(plans) / f"{name}.json")
    here, floor = origin_on_holder(design, holds[place])
    there, other_floor = origin_on_holder(other, holds[name])
    _, east, south = place_plan.frame_of(design)
    offset = there - here
    at = east * offset[0] + south * offset[1]
    return {"name": name, "stage": name, "at": [round(float(at[0]), 4), round(floor - other_floor, 4),
                                                round(float(at[2]), 4)],
            "rotation": quaternion(axes_in(design, other)),
            "from": f"a door of {place} leads to {name}: where its holder's plan holds both (holds)"}


def places_of(place, plan, design, plans):
    """Each place a door or opening of this one leads to that its holder's plan holds beside it."""
    _, holder = holder_of(place, plans)
    if holder is None:
        return []
    held = {hold["place"] for hold in holder.get("holds") or []}
    return [sibling(place, design, holder, name, plans) for name in leads_of(plan, design)
            if name in held and name != place and (pathlib.Path(plans) / f"{name}.json").is_file()]


# --- the record ---------------------------------------------------------------------------------------------------

def ceiling(design):
    """The highest roof's top, else the walls' tallest, over the floor; None for a place with neither."""
    heights = [float(roof.get("top") or roof.get("eave") or 0.0) for roof in design.get("roofs") or []] + \
        [float(wall.get("tall") or 0.0) for wall in design.get("walls") or []]
    return max(heights) if heights and max(heights) > 0 else None


def record_of(plan, design, inputs):
    """The place's scene record from its design (module docstring)."""
    place = plan["place"]
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    record = {"place": place,
              "about": f"{plan['title']}, written by SCORE's scene-record stage from its design: its locked plan, "
                       "its scene inventory's row kinds, the library's lamp and the environment concept's physics at "
                       "its site. Frame: the plan's (x east, z south, y up over its floor).",
              "floor": plan["floor"], "inside": inside(design), "structure": structure(plan, design, library_of(inputs)), "objects": [],
              "lights": lights(design, inputs), "environment": environment(design, read(inputs["sky"])),
              "doorways": plan.get("doorways", []), "places": places_of(place, plan, design, inputs["plans"])}
    record["views"], left_out = views_inside(views(plan if record["inside"] else dict(plan, doorways=[]), eye),
                                             design, record["inside"])
    if left_out:
        record["views_left_out"] = left_out
    high = ceiling(design)
    if record["inside"] and high is not None:
        record["ceiling"] = round(float(place_plan.frame_of(design)[0][1]) + high, 4)
    if plan.get("removes"):
        record["coordinator_removed"] = removed(plan)
    return record


def removed(plan):
    """The rows the plan's concept leaves out (its `removes`), as the record's coordinator_removed."""
    return [{"what": f"inventory row {entry['row']}", "rows": [entry["row"]], "date": entry["date"],
             "why": entry["why"], "from": f"plan removes {entry['row']} ({entry['why']})"} for entry in plan["removes"]]


def make(inputs, out, seed, params):
    """record/<place>.json: the place's scene record from its design."""
    plan = read(pathlib.Path(inputs["plan"]) / "plan.json")
    design = read(pathlib.Path(inputs["plans"]) / f"{plan['place']}.json")
    (out / "record").mkdir()
    (out / "record" / f"{plan['place']}.json").write_text(json.dumps(record_of(plan, design, inputs), indent=1))


def record_faults(folder):
    found = list(pathlib.Path(folder).glob("record/*.json"))
    if len(found) != 1:
        return [f"{len(found)} records in record/, not one"]
    record = json.loads(found[0].read_text())
    return [f"the record lacks {key}" for key in ("place", "floor", "structure", "views") if key not in record]


SCENE_RECORD = contracts.Contract("scene-record", 1, record_faults, {"length": "metre", "up axis": "Y",
                                                                     "angle": "degree"})


def record_in(output):
    """The record an output holds: (place, record)."""
    path = next(pathlib.Path(output).glob("record/*.json"))
    return path.stem, json.loads(path.read_text())
