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
                 plan draws as a flight of steps; an `arch` at each plan item of an arched structure row of the
                 hand-in (design_shell.arched: a tube's ribs), at the row's size, named its row; each entry's surface the scene's surface library's for its kind
                 (surface-library@<place>, read as an `after`: design_shell.PART_KINDS), else none and
                 `surface_missing` says why (the scene builder names it on the mesh, never paints another way)
    lights       one at each plan item of a glowing row (its row kind, score/stages/row_kinds.py, or its concept
                 showing it glow, `{home}/design/light/<place>.json`, reading.concept_light): over the item's
                 middle, as high on it as the library's lamp for the row's mount says, its numbers that lamp's
                 (data/library/lamps.json, tools/props/scene/lamps.py), reaching by how high it hangs; a row the
                 concept shows glowing in the colour it shows there, its strength times its brightness there; an
                 item outlining the whole room held on a wall (score/review/holders) on that wall's face instead
    objects      one at each plan item of each prop or shell row of the batch's hand-in (several where the item
                 counts several or a run the plan draws once), `<row>_<n>`, on its spot at its shape's base, turned
                 along its item, waiting on the bake's model of its row's take (`bake`, `<first row>_1`), which the
                 assembly lays (assembly/made_waiting.py); a terrain row's too: ground-join lays its piece where its
                 object stands (terrain/join.py laid_middles), and the assembly and the settle leave out each row
                 ground-join joined (made_waiting.joined_rows: the ground lays it); a row the plan's shell lays itself (route `plan`) is named
                 on a shell piece of its part instead (an opening on the lintel over its item's cut); one at the
                 floor on a deck lying on the floor (airlock's porch deck) stands on it; each carries what holds it (`on`, from the place's relations,
                 score/review/holders: its opening, its wall, its holder's objects), which the assembly lays it by
    environment  inside or not, and the sky at the place's site at its scene time from the physics (overhead.py: each
                 light over the horizon, every other body, every backdrop), which the light layer draws
                 (score/stages/light/sky.py); the record draws no sky and holds no air the design does not give
    views        one from inside each doorway looking across, one from each of the plan's person spots (an inside
                 place's only where the eye stands inside its outline: the others in `views_left_out`, with why); an
                 open place's spot at its floor stands on the terrain row's made ground under it (`terrain`, the one
                 thing made that the record reads: wreck's eyes stood under its ground, 2026-10-30)
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
from score.review import holders, overhead
from score.review.plan_checks import WALLS_ITEM
from score.stages import row_kinds
from score.stages.earth_seed import design_shell
from score.stages.scene_record import concept_light, far
from score.stages.scene_record import plan as place_plan
import score.stages.shapes_first.floor_fit as floor_fit

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
# A view stands this far inside its doorway (every view sees far.VIEW_FOV wide).
VIEW_IN = 1.0
AIM_HEIGHT = 1.0
# What a door may lead to that is no place.
NOT_PLACES = ("outside", "sealed")
# The routes whose rows' models the record lays at their plan items (prepare's groups.ROUTES): people are the cast's.
LAID_ROUTES = ("prop", "shell")
# The part of the place each piece of the shell is (design_shell.part_kind), as a reading's row says its part: a row
# the plan lays itself (route `plan`) is named on a piece of its part, an opening on the piece over its cut (shell).
SHELL_PARTS = {"deck": "floor", "wall": "wall", "roof": "roof"}
# An item's way (x across) in plan metres by its facing (None as north): turned east or west it lies across.
FACING_WAY = {None: (1.0, 0.0), "N": (1.0, 0.0), "S": (-1.0, 0.0), "E": (0.0, 1.0), "W": (0.0, -1.0)}


def files(place):
    """The design files the writer reads: the place's kept plan and every other (its holder's `holds`, its siblings'
    frames), its scene inventory, its concept's light once read, its sky inputs (scene_sky.keep's), the row-kind
    rules, the library's lamp, the environment's eye height (place.json `shared`), the batch's hand-in (prepare's
    handin.py: each row's route and the take that makes its model) and its relations once derived (relations_file)."""
    return {"inventory": "{home}/design/inventory/{place}.json", "plans": "{home}/design/plans",
            "sky": "{home}/design/sky/{place}.json", "row kinds": "{data}/checks/row-kinds.json",
            "lamp library": "{data}/library/lamps.json", "places": "{data}/definitions/place.json",
            "hand-in": "{home}/design/props/{place}.json", **concept_light.concept_light_input(place),
            **design_shell.relations_file(place)}


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
    points, floor = in_frame(design, piece.get("points") or [piece["centre"]])
    entry = {"name": name if number == 0 else f"{name}_{number + 1}", "builder": piece["builder"], "points": points,
             "plain": "shell", "from": said}
    if piece["builder"] == "dome":
        del entry["points"]
        entry.update(centre=points[0], radius=round(piece["radius"], 4), base=round(floor + piece["base"], 4),
                     rise=round(piece["rise"], 4), layer=2)
    elif piece["builder"] == "gable":
        entry.update(eave=round(floor + piece["eave"], 4), top=round(floor + piece["top"], 4), layer=2)
    else:
        entry.update(low=round(floor + piece["low"], 4), high=round(floor + piece["high"], 4))
        if name.startswith("roof"):
            entry["layer"] = 2
    return entry


def cut_piece(design, middle):
    """The name of the shell piece over the cut an opening at plan point `middle` makes in its wall (its lintel, else
    the wall's foot under it: design_shell.walls' pieces, in its spans' order), else None: no wall is cut there."""
    outline, openings, eave = design_shell.outline_of(design), design_shell.openings_of(design), \
        design_shell.lowest_eave(design)
    for index, start in enumerate(outline):
        end = outline[(index + 1) % len(outline)]
        length = math.dist(start, end)
        entry = design_shell.written_wall(design, start, end)
        thick = float(entry.get("thick") or design_shell.THICK)
        at = design_shell.on_edge([{"at": middle, "wide": 0.0, "sill": 0.0, "head": 0.0}], start, end, thick) \
            if length >= 1e-6 else []
        if not at:
            continue
        cuts = design_shell.on_edge(openings, start, end, thick)
        spans = design_shell.spans(length, cuts, -DECK_BELOW - design_shell.SLAB,
                                   design_shell.wall_height(design, entry, eave))
        over = [number for number, (begin, finish, *_) in enumerate(spans)
                if (begin, finish) in {cut[:2] for cut in cuts} and begin <= at[0][0] <= finish]
        if over:
            return f"wall_{index + 1}" if over[-1] == 0 else f"wall_{index + 1}_{over[-1] + 1}"
    return None


def opening_pieces(design, row_id):
    """The shell pieces over the cuts the row's plan items make (cut_piece), in item order."""
    tied = design.get("rows") or {}
    found = [cut_piece(design, [float(item[1]) + float(item[3]) / 2, float(item[2]) + float(item[4]) / 2])
             for item in design.get("items") or [] if row_id in (tied.get(item[0]) or [])]
    return [name for name in found if name]


def shell(design, place, library, rows=None):
    """The room shell's entries (design_shell.pieces) stood in the place's frame, each painted from the scene's
    library by its part's kind; each of the shell's own rows (`rows`: {part: [row id]}) named (`row`, its score:row)
    on the first piece of its part no other row names, an opening's on the piece over the cut its plan item makes
    (opening_pieces; none where no wall is cut at it: hangar's floor hatch named no lintel, 2026-10-30)."""
    found = [painted(shell_entry(name, number, piece, design, said), design_shell.part_kind(name), place, library)
             for name, parts, said in design_shell.pieces(design) for number, piece in enumerate(parts)]
    by_name = {entry["name"]: entry for entry in found}
    for row_id in (rows or {}).get("opening", []):
        for name in opening_pieces(design, row_id):
            by_name[name].setdefault("row", row_id)
    free = {part: list(ids) for part, ids in (rows or {}).items() if part != "opening"}
    for entry in found:
        if "row" in entry:
            continue
        ids = free.get(SHELL_PARTS.get(entry["name"].split("_")[0]))
        if ids:
            entry["row"] = ids.pop(0)
    return found


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


def structure(plan, design, library=None, rows=None):
    """The record's structure: an inside place's shell where its base does not lay it (its own rows, `rows`, named on
    its pieces), and the plan's stairs, each painted from the scene's surface library (`library`: its materials.json
    content, None while not made)."""
    shelled = shell(design, plan["place"], library, rows) if inside(design) and not design_shell.laid_for(design) \
        else []
    return shelled + [painted(stair(number, entry, design), "stair", plan["place"], library)
                      for number, entry in enumerate(design.get("stairs") or [], 1)
                      if len(entry.get("points") or []) >= 3]


def arch_entry(row, item, shape, design, number):
    """An arched row's band at its plan item (design_shell.arches): standing on the item's middle at its shape's base,
    spanning the row's wide along the item's longer side, rising its tall, its deep both its thickness and its depth."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    span, band, rise = (float(value) for value in row["size"])
    way = np.array([1.0, 0.0]) if wide >= deep else np.array([0.0, 1.0])
    middle = np.array([x + wide / 2, y + deep / 2])
    feet, floor = in_frame(design, [middle - way * span / 2, middle + way * span / 2])
    return {"name": f"{row['id']}_{number}", "builder": "arch", "feet": feet,
            "low": round(floor + float(shape.get("base") or 0.0), 4), "rise": rise, "thick": band, "deep": band,
            "plain": "shell", "row": row["id"],
            "from": f"plan item {item[0]!r}, inventory row {row['id']}: an arch {span:g} m across and {rise:g} m "
                    f"high, {band:g} m thick (earth_seed/design_shell.arched)"}


def arch_entries(design, place, library, handin):
    """The arched rows' bands (arch_entry) at their plan items, each painted as a wall of the shell it carries."""
    return [painted(arch_entry(row, item, shape, design, number), "wall", place, library)
            for number, (row, item, shape) in enumerate(design_shell.arches(design, handin.get("rows", [])), 1)]


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


# A lamp held on its wall stands this far out from the wall's face into the room, metres: off the face, never in it.
LAMP_OUT = 0.1


def wall_lamp_spot(relation):
    """(plan spot, face ends) of a lamp on its wall relation (score/review/holders `wall`): its spot's nearest point
    on the wall's face, LAMP_OUT out from it into the room."""
    wall = relation["wall"]
    start, end = np.asarray(wall["from"], float), np.asarray(wall["to"], float)
    run = (end - start) / max(float(np.linalg.norm(end - start)), 1e-9)
    out = np.array([-run[1], run[0]]) * relation["side"]
    face = out * float(wall.get("thick") or 0.0) / 2
    along = float(np.clip((np.asarray(relation["spot"], float) - start) @ run, 0.0, float((end - start) @ run)))
    return start + face + run * along + out * LAMP_OUT, [start + face, end + face]


def item_lamp(item, row, rows, design, library, path, glow=None, relation=None):
    """The light of a glowing row's plan item: over its middle, as high on it as the library's lamp for the row's
    mount puts it, reaching by how high that is over the floor; an item outlining the whole room (holders.outlines_room:
    its middle says nothing of where it is) held on a wall (`relation`) on that wall's face at the relation's spot
    (wall_lamp_spot), as high on its shape, else on the wall's height (the place's ceiling), as its mount puts it;
    where its concept shows it glowing (`glow`, the concept's light), the colour its light is there and its strength
    that lamp's times its brightness there."""
    name, x, y, wide, deep = item[0], *[float(value) for value in item[1:5]]
    shape = (design.get("shapes") or {}).get(name) or {}
    walled = relation is not None and relation.get("how") == "wall" and holders.outlines_room(item, design)
    base, tall = float(shape.get("base") or 0.0), float(shape.get("tall") or (walled and ceiling(design)) or 0.0)
    mounts, words = library.mounts(path), library.mount_words(path)
    share = float(mounts[library.mount_of(row, rows, words)]["high"])
    high = base + tall * share
    light = library.light_at(row, high, rows, mounts, words)
    energy, colour, attenuation = game_lamp()
    plan_spot, face = wall_lamp_spot(relation) if walled else ([x + wide / 2, y + deep / 2], None)
    (spot,), floor = in_frame(design, [plan_spot], high)
    why = f"its concept shows its {glow['glowing'] or 'light'} glowing" if glow else \
        f"row kind {row['row_kind']}, it glows"
    return {"type": "omni", "at": [spot[0], floor, spot[1]], "colour": glow["colour"] if glow else colour,
            "energy": round(energy * light["strength"] * (float(glow["brightness"]) if glow else 1.0), 4),
            "range": light["reach"], "attenuation": attenuation, "shadows": light["shadows"],
            "from": f"plan item {name!r}, inventory row {row['id']} ({why}): the library's lamp "
                    f"(data/library/lamps.json) for its mount, {high:.2f} m over the floor"
                    + (f", on its wall ({relation['why']})" if walled else ""),
            **({"against": in_frame(design, face)[0]} if walled else {})}


def lights(design, inputs, relations=None):
    """A light at each plan item of the scene's glowing rows: those whose row kind glows (row_kinds.rows_that) and
    those its concept shows glowing (`concept light`: an engine's core, a screen, a light strip; owner, 2026-10-25:
    "look at the concept, the engines themself should be a source of light"), in the colour and brightness the concept
    shows; a row of the sky (anchored `sky`: its stars, a planet) is the physics' (the light layer's sky), no lamp.
    An item outlining the whole room has its lamp on the wall its relation (`relations`, score/review/holders) holds it
    on (item_lamp)."""
    inventory = read(inputs["inventory"])
    glowing = {row["id"]: row for row in row_kinds.rows_that(inventory, "glows", row_kinds.table(inputs["row kinds"]))}
    shown = {row: glow for row, glow in (read(inputs["concept light"])["rows"] if "concept light" in inputs
                                         else {}).items() if glow["glows"]}
    glowing |= {row["id"]: {**row, "row_kind": glowing.get(row["id"], {}).get("row_kind")}
                for row in inventory["rows"] if row["id"] in shown and row.get("anchor") != "sky"}
    rows_of, library, holding = design.get("rows") or {}, library_lamps(), relations_of(relations)
    found = []
    for item in design.get("items") or []:
        if len(item) > 6 and item[6] == "zone":
            continue
        for row_id in rows_of.get(item[0]) or []:
            if row_id in glowing:
                found.append(item_lamp(item, glowing[row_id], inventory["rows"], design, library,
                                       inputs["lamp library"], shown.get(row_id), holding.get((item[0], row_id))))
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


def views(plan, eye_height, ground=None):
    """One view inside each doorway looking across the inside's middle (the doorway's mirror through it), one from
    each standing spot to the middle at its own level or to the plan item it looks at on the floor; each eye at
    standing height over its level (the plan row's plan.json: its `doorways` and `standing`), a spot at the floor
    over the made ground under it where `ground` (ground_under) has one there."""
    found, middle = [], middle_of(plan)
    for door in plan.get("doorways", []):
        at = np.asarray(door["middle"], dtype=float)
        eye = at + np.asarray(door["inward"], dtype=float) * VIEW_IN
        aim = 2 * middle - at[[0, 2]]
        found.append({"name": f"from-{door['name']}", "eye": [round(eye[0], 3), round(at[1] + eye_height, 3),
                                                             round(eye[2], 3)],
                      "aim": [round(aim[0], 3), round(at[1] + AIM_HEIGHT, 3), round(aim[1], 3)], "fov": far.VIEW_FOV,
                      "from": f"plan {door['name']} ({door['wide']:g} m wide, to {door['to']}), looking across"})
    for number, spot in enumerate(plan["standing"], 1):
        aim = item_middle(plan, spot["looks_at"]) if spot["looks_at"] else middle
        aim_level = plan["floor_height"] if spot["looks_at"] else spot["level"]
        stands = spot_ground(spot, plan["floor_height"], ground)
        found.append({"name": f"spot-{number}",
                      "eye": [round(spot["at"][0], 3), round(stands + eye_height, 3), round(spot["at"][1], 3)],
                      "aim": [round(aim[0], 3), round(aim_level + AIM_HEIGHT, 3), round(aim[1], 3)],
                      "fov": far.VIEW_FOV, "from": f"plan standing spot {number}, looking to " +
                                              (f"plan item {spot['looks_at']!r}" if spot["looks_at"] else "the middle")})
    return found


def spot_ground(spot, floor_height, ground):
    """What a standing spot stands on: the made ground under it where the spot is at the floor and `ground` has one
    there (wreck's spot-3 and spot-6 eyes stood 2.6 and 4.3 m under its ground, their views black, 2026-10-30), else
    its level (a deck)."""
    under = ground(*spot["at"]) if ground and spot["level"] <= floor_height else None
    return spot["level"] if under is None else under


def ground_under(inputs, place):
    """(x, z) -> the height of the place's made ground there (the terrain row's places/<place>.usdc, as the assembly
    lays it, its water left out), None off it; None for a place it makes none for."""
    import trimesh

    import score.stages.cast.measure as measure  # this form: the code version hashes measure.py alone
    made = sorted(pathlib.Path(inputs["terrain"]).glob(f"*/places/{place}.usdc")) if "terrain" in inputs else []
    solid = [tris for name, tris in (measure.solids(made[0], place) if made else {}).items()
             if not name.startswith(measure.WATER)]
    if not solid:
        return None
    tris = np.concatenate(solid)
    mesh = trimesh.Trimesh(vertices=tris.reshape(-1, 3), faces=np.arange(len(tris) * 3).reshape(-1, 3), process=False)
    top = float(tris[..., 1].max()) + 1.0

    def height(x, z):
        hits = mesh.ray.intersects_location([[x, top, z]], [[0.0, -1.0, 0.0]], multiple_hits=False)[0]
        return round(float(hits[0][1]), 4) if len(hits) else None
    return height


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


def sibling(place, design, holder, name, plans, why=None):
    """A place the holder's plan holds beside this one, stood in this place's frame where the holder holds it."""
    holds = {hold["place"]: hold for hold in holder.get("holds") or []}
    other = read(pathlib.Path(plans) / f"{name}.json")
    return stood(place, design, holds[place], name, other, holds[name],
                 why or f"a door of {place} leads to {name}: where its holder's plan holds both (holds)")


def stood(place, design, hold, name, other, other_hold, why):
    """Another place stood in this place's frame, both plans laid unturned on the holder's plan: this one in `hold`,
    the other in `other_hold` (the holder itself at its own plan's corner)."""
    here, floor = origin_on_holder(design, hold)
    there, other_floor = origin_on_holder(other, other_hold)
    _, east, south = place_plan.frame_of(design)
    offset = there - here
    at = east * offset[0] + south * offset[1]
    return {"name": name, "stage": name, "at": [round(float(at[0]), 4), round(floor - other_floor, 4),
                                                round(float(at[2]), 4)],
            "rotation": quaternion(axes_in(design, other)), "from": why}


def places_of(place, plan, design, plans, handin=None):
    """Each place a door or opening of this one leads to that its holder's plan holds beside it, and each place of
    its scene a backdrop row is shown from (the hand-in's rows' `shown`, prepare/groups.shown_from): the holder
    itself, or a place it holds beside this one."""
    holder_name, holder = holder_of(place, plans)
    if holder is None:
        return []
    held = {hold["place"] for hold in holder.get("holds") or []}
    found = [sibling(place, design, holder, name, plans) for name in leads_of(plan, design)
             if name in held and name != place and (pathlib.Path(plans) / f"{name}.json").is_file()]
    return found + shown_places(place, design, holder_name, holder, plans, handin or {}, {entry["name"]
                                                                                          for entry in found})


def shown_places(place, design, holder_name, holder, plans, handin, stood_already):
    """The places of the scene the hand-in's backdrop rows are shown from (`shown`), not stood already: its holder
    at its own plan's corner, a place the holder holds beside this one where it holds it."""
    held = {hold["place"]: hold for hold in holder.get("holds") or []}
    rows = {}
    for row in handin.get("rows", []):
        if row.get("shown"):
            rows.setdefault(row["shown"]["place"], []).append(row["id"])
    found = []
    for name, ids in sorted(rows.items()):
        why = f"{place} shows {', '.join(ids)} beyond it, made in {name} (its backdrop rows' `shown`)"
        if name in stood_already or name == place:
            continue
        if name == holder_name:
            found.append(stood(place, design, held[place], name, holder, {"x": 0.0, "y": 0.0}, why))
        elif name in held and (pathlib.Path(plans) / f"{name}.json").is_file():
            found.append(sibling(place, design, holder, name, plans, why))
    return found


# --- the design's objects -----------------------------------------------------------------------------------------

def models_of(handin):
    """{row id: the model the bake makes for it}: each handed take's, `<its first row>_1` (prepare's handin.py
    surface_record names it so); a row of no handed take has none."""
    return {row: f"{first}_1" for first, entry in handin.get("objects", {}).items() for row in entry["rows"]}


def plan_rows(handin):
    """{shell part: [row id]} of the rows the plan's shell lays itself (route `plan`), in the hand-in's order."""
    found = {}
    for row in handin.get("rows", []):
        if row.get("route") == "plan":
            found.setdefault(row.get("part"), []).append(row["id"])
    return found


def item_path(item, shape):
    """The path an item's pieces stand along, in plan metres: a polygon's outline round its box, closed; else its
    box's long middle line."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    if shape.get("shape") == "polygon" and len(shape.get("points") or []) >= 3:
        points = [[x + float(across) * wide, y + float(along) * deep] for across, along in shape["points"]]
        return np.asarray(points + points[:1])
    if wide >= deep:
        return np.asarray([[x, y + deep / 2], [x + wide, y + deep / 2]])
    return np.asarray([[x + wide / 2, y], [x + wide / 2, y + deep]])


def along(path, share):
    """The plan point `share` of the way along a path and the way the path runs there (a unit plan vector)."""
    legs = np.diff(path, axis=0)
    lengths = np.linalg.norm(legs, axis=1)
    reach = share * lengths.sum()
    for start, leg, length in zip(path, legs, lengths):
        if length > 0 and reach <= length:
            return start + leg * reach / length, leg / length
        reach -= length
    last = int(np.flatnonzero(lengths)[-1])
    return path[-1], legs[last] / lengths[last]


def spots_of(item, shape, pieces):
    """[(plan point, x way)] of an item's pieces: one over its box's middle turned by its facing; several evenly along
    its path (item_path), each its long side along it."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    if pieces == 1:
        return [(np.array([x + wide / 2, y + deep / 2]), np.asarray(FACING_WAY.get(item[5], FACING_WAY[None])))]
    path = item_path(item, shape)
    return [along(path, (number + 0.5) / pieces) for number in range(pieces)]


def yaw_turn(design, way, size):
    """The turn [x, y, z, w] about up that lays a model's long side (its x, else its z where it is deeper than wide:
    `size` [wide, deep, tall]) along a plan way, in the place's frame."""
    _, east, south = place_plan.frame_of(design)
    seen = east * way[0] + south * way[1]
    deeper = isinstance(size, list) and len(size) == 3 and float(size[1]) > float(size[0])
    angle = math.atan2(seen[0], seen[2]) if deeper else math.atan2(-seen[2], seen[0])
    return [0.0, round(math.sin(angle / 2), 6), 0.0, round(math.cos(angle / 2), 6)]


def outward(item, wide, deep):
    """The plan way out of a `wide` by `deep` plan across the edge an item touches (floor_fit.at_edge), and that edge's
    line ([axis, at]); at a corner, the edge the item runs furthest along."""
    x, y, across, along_edge = (float(value) for value in item[1:5])
    edges = [(along_edge, (-1.0, 0.0), (0, 0.0), x <= floor_fit.ROUNDING),
             (across, (0.0, -1.0), (1, 0.0), y <= floor_fit.ROUNDING),
             (along_edge, (1.0, 0.0), (0, wide), x + across >= wide - floor_fit.ROUNDING),
             (across, (0.0, 1.0), (1, deep), y + along_edge >= deep - floor_fit.ROUNDING)]
    _, way, line, _ = max((edge for edge in edges if edge[3]), key=lambda edge: edge[0])
    return np.asarray(way), line


def past_edge_spot(item, design, spot, size):
    """(plan point, x way) of a piece of a row the plan lays only against its edge (floor_fit.past_edge: a building
    round a square, its face the item): its face on the edge's line, its body (its narrower side across: yaw_turn lays
    the longer along the edge) out past it, off the floor, facing in."""
    way, (axis, at) = outward(item, float(design["w"]), float(design["d"]))
    depth = min(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else 0.0
    point = np.array(spot, dtype=float)
    point[axis] = at + way[axis] * depth / 2
    return point, np.array([way[1], -way[0]])  # facing in (-way), as FACING_WAY turns a facing into its x way


def pieces_of(row, items):
    """How many pieces an item of the row lays: its shape's count; the row's own count on its only item (a run the
    plan draws once, laid as the pieces prepare's groups.run_pieces makes it of)."""
    counts = [int(shape.get("count") or 1) for _, shape in items]
    if len(items) == 1:
        counts = [max(counts[0], int(row.get("count") or 1))]
    return counts


def sized(row):
    return isinstance(row.get("size"), list) and len(row["size"]) == 3 and all(
        isinstance(side, (int, float)) and side > 0 for side in row["size"])


def waits(row, model, by_id):
    """Why an object of the row waits on its model: the bake's model to come, or why the batch makes none."""
    if model is None:
        return f"no take of the batch makes a model of row {row['id']} (prepare's hand-in hands none)"
    first = by_id.get(model.removesuffix("_1"), row)
    if not sized(first):
        return f"its model {model} is never baked: row {first['id']} has no size (an input gap of the batch)"
    return f"its model {model} comes from the surface line's bake"


def plan_way(design, way):
    """A plan way [x, y] as a unit place way [x, z]."""
    _, east, south = place_plan.frame_of(design)
    seen = east * float(way[0]) + south * float(way[1])
    seen = seen / max(float(np.linalg.norm(seen)), 1e-9)
    return [round(float(seen[0]), 6), round(float(seen[2]), 6)]


def wall_face(design, wall, side):
    """A plan wall's face on its `side` (+1: its line's left as one walks it on the plan, x east, y south) in the
    place's frame: its two ends [[x, z], [x, z]] on the floor and the way out of it into the side's room."""
    start, end = np.asarray(wall["from"], float), np.asarray(wall["to"], float)
    run = (end - start) / max(float(np.linalg.norm(end - start)), 1e-9)
    out = np.array([-run[1], run[0]]) * side
    reach = out * float(wall.get("thick") or 0.0) / 2
    ends, _ = in_frame(design, [start + reach, end + reach])
    return ends, plan_way(design, out)


FACE_WAYS = {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def related(design, relation, spot, way, base, size, piece=0):
    """(spot, x way, base, the record's `on`) of an object, the `piece`-th of its item, laid by its plan item's relation
    (score/review/holders; `pieces` one a piece): in its opening at the opening's middle and sill, along its wall;
    against a wall's face, along it, at the relation's spot (the concept's, for an item the plan writer left on the
    walls item); past the plan's edge, its face on the edge's line and its body out past it, facing in (a street's
    facade); on, within or against its holder as it was (at its piece's spot where the relation gives `spots`: street's
    three restaurant doors spread their width and room apart), its holder's objects named after (holder_names); on
    the floor at the relation's spot where it gives one (a stair at the plan's stair); a ramp at its spot, run up its
    way, its `on` the level's edge, the way up and the level's top in the place's frame. None `on` on the floor, the
    ceiling or past an edge."""
    if "pieces" in relation:
        relation = relation["pieces"][min(piece, len(relation["pieces"]) - 1)]
    how = relation["how"]
    if how == "in":
        opening, wall = relation["opening"], relation.get("wall")
        along = np.subtract(wall["to"], wall["from"]) if wall else np.asarray(way, float)
        (middle,), floor = in_frame(design, [opening["at"]], float(opening["sill"]))
        return (np.asarray(opening["at"], float), along / max(float(np.linalg.norm(along)), 1e-9),
                float(opening["sill"]),
                {"how": "in", "middle": [middle[0], floor, middle[1]], "along": plan_way(design, along),
                 "wide": float(opening["wide"]), "tall": round(float(opening["head"]) - float(opening["sill"]), 4),
                 "why": relation["why"]})
    if how == "wall":
        wall = relation["wall"]
        ends, out = wall_face(design, wall, relation["side"])
        along = np.subtract(wall["to"], wall["from"])
        return (np.asarray(relation["spot"], float), along / max(float(np.linalg.norm(along)), 1e-9), base,
                {"how": "wall", "span": ends, "out": out, "why": relation["why"]})
    if how in ("top", "within", "face"):
        found = {"how": how, "holder item": relation["holder"], "why": relation["why"],
                 **({"holder row": relation["holder row"]} if relation.get("holder row") else {}),
                 **({"hangs": True} if relation.get("hangs") else {})}  # hung on its holder's back (fitting.on_back)
        if relation.get("spots"):
            spot = np.asarray(relation["spots"][min(piece, len(relation["spots"]) - 1)], float)
        if how == "face":
            found["out"] = plan_way(design, FACE_WAYS[relation["face"]])
            recess = relation.get("recess")
            if recess:  # its recess's room beside it, which the assembly keeps within the face too
                room_way = (recess.get("room_ways") or [recess.get("room_way") or [0.0, 0.0]])[
                    min(piece, len(recess.get("room_ways") or [0]) - 1)]
                found["room"] = float(recess["room"])
                found["room_way"] = plan_way(design, room_way) if any(room_way) else [0.0, 0.0]
        return spot, way, base, found
    if how == "ramp":
        ends, floor = in_frame(design, relation["edge"], float(relation["height"]))
        return (np.asarray(relation["spot"], float), np.asarray(relation["way"], float), base,
                {"how": "ramp", "edge": ends, "up": plan_way(design, relation["way"]), "top": floor,
                 "why": relation["why"]})
    if how == "edge":
        out = np.asarray(FACE_WAYS[relation["edge"]])
        depth = min(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else 0.0
        return np.asarray(relation["spot"], float) + out * depth / 2, np.array([out[1], -out[0]]), base, None
    if relation.get("spot"):
        return np.asarray(relation["spot"], float), np.asarray(relation.get("way") or way, float), base, None
    return spot, way, base, None


def arch_names(design, handin):
    """{plan item: [the arch entry laid at it]} of the arched rows' bands (arch_entries' names)."""
    found = {}
    for number, (row, item, _) in enumerate(design_shell.arches(design, handin.get("rows", [])), 1):
        found.setdefault(item[0], []).append(f"{row['id']}_{number}")
    return found


def holder_names(found, laid, arched=None):
    """Each object's `on` naming its holder's objects (those laid at its holder item, `laid` {item: [names]}, of its
    holder row where it names one), else the arch the record lays there (`arched`, under Structure: a tube's rib);
    one whose holder item laid neither keeps no `on` and says so."""
    rows = {entry["name"]: entry["row"] for entry in found}
    for entry in found:
        on = entry.get("on")
        if on and "holder item" in on:
            names = [name for name in laid.get(on["holder item"]) or []
                     if rows.get(name) == on.get("holder row", rows.get(name))]
            if not names and (arched or {}).get(on["holder item"]):
                names, on["holder scope"] = arched[on["holder item"]], "Structure"
            if names:
                on["holder"] = names
            else:
                entry.pop("on")
                entry["unheld"] = f"its holder item {on['holder item']!r} lays no object"
    return found


PLACING = ("in", "wall", "edge", "top", "within", "face", "ramp")  # relations that give an object its place


def marks(item, row, relation, unheld):
    """What the assembly's `held` gate reads of an object beside its `on`: `fills` for a door or window row (it
    stands in an opening), `unheld` with why where its relations name nothing holding it, `unplaced` where the plan
    writer left it on the walls item and no relation places it (it would stand at the room's middle)."""
    found = {"fills": True} if design_shell.fills_opening(row) else {}
    if unheld:
        found["unheld"] = unheld
    placed = relation and (relation["how"] in PLACING or relation.get("spot") or relation.get("pieces"))
    if item[0] == WALLS_ITEM and not placed:
        found["unplaced"] = "the plan writer left it on the walls item and no relation places it"
    return found


def relations_of(relations):
    """{(plan item, row): relation} of the place's relations file (score/review/holders), {} with none."""
    return {(entry["item"], entry["row"]): entry for entry in (relations or {}).get("relations", [])}


def deck_height(design, spot):
    """The height of the highest deck lying on the floor (a plan level whose slab reaches down to it: nothing stands
    under it) whose outline holds a plan spot, else 0: a thing at the floor there stands on that deck (airlock's porch
    deck at 0.2 m, its sandbags laid inside its slab, 2026-10-30); a higher level may have things under it, so a thing
    at the floor under it stays there."""
    return max([0.0] + [float(level["height"]) for level in design.get("levels") or []
                        if len(level.get("points") or []) >= 3 and
                        0.0 < float(level.get("height") or 0.0) <= design_shell.SLAB + DECK_BELOW and
                        design_shell.inside(spot, level["points"])])


def design_objects(design, handin, relations=None):
    """Every object of the design: one at each plan item (more where the item counts several, or a run the plan
    draws once) for each prop or shell row the item names, `<row>_<n>` the n-th of its row, standing on its plan spot
    as high as its shape's base, turned along its item, waiting on the bake's model of its row (made_waiting lays it
    once baked; one the bake never makes stays named on the stage's root). A row marked `far` is laid far off by
    far_objects alone, never at an item its plan laid it at too (the street's distant floodlights, laid at its end). A
    row on the ground the plan lays only against its edge (floor_fit.past_edge) stands past it (past_edge_spot), never
    centred on its edge strip over the floor (2026-10-26: the square's 30 m buildings on 2 to 7 m strips). An item's
    relation (`relations`, score/review/holders: in an opening, against a wall, on, within or against a holder) is
    carried as the object's `on`, which the assembly lays it by at its built size (assembly/made_waiting.fitted)."""
    by_id = {row["id"]: row for row in handin.get("rows", [])}
    models, shapes, tied = models_of(handin), design.get("shapes") or {}, design.get("rows") or {}
    items = {}
    for item in design.get("items") or []:
        if len(item) > 6 and item[6] != "item":
            continue
        for row_id in tied.get(item[0]) or []:
            if row_id in by_id and by_id[row_id].get("route", "prop") in LAID_ROUTES and not by_id[row_id].get("far"):
                items.setdefault(row_id, []).append((item, shapes.get(item[0]) or {}))
    found, edged, holding, laid_at = [], floor_fit.past_edge(design, handin), relations_of(relations), {}
    unheld = {(entry["item"], entry["row"]): entry["why"] for entry in (relations or {}).get("unheld", [])}
    for row_id, laid in items.items():
        row, model = by_id[row_id], models.get(row_id)
        size = by_id.get(model.removesuffix("_1"), row).get("size") if model else row.get("size")
        number = 0
        for (item, shape), pieces in zip(laid, pieces_of(row, laid)):
            base = float(shape.get("base") or 0.0)
            relation, on = holding.get((item[0], row_id)), None
            marked = marks(item, row, relation, unheld.get((item[0], row_id)))
            for piece, (spot, way) in enumerate(spots_of(item, shape, pieces)):
                if row_id in edged:
                    spot, way = past_edge_spot(item, design, spot, size)
                height = base or deck_height(design, spot)
                if relation:
                    spot, way, height, on = related(design, relation, spot, way, height, size, piece)
                number += 1
                (point,), floor = in_frame(design, [spot], height)
                found.append({"name": f"{row_id}_{number}", "row": row_id, "bake": model, "kind": "object",
                              "at": [point[0], floor, point[1]], "rotation": yaw_turn(design, way, size),
                              "waiting": waits(row, model, by_id),
                              "from": f"plan item {item[0]!r}, inventory row {row_id}: piece {number} of the row, "
                                      f"{height:g} m over the floor", **({"on": dict(on)} if on else {}), **marked})
                laid_at.setdefault(item[0], []).append(found[-1]["name"])
    return holder_names(found, laid_at, arch_names(design, handin))


def far_objects(design, handin, inventory_path):
    """Every far object of the design (a prop row prepare marks `far`, groups.far_made: a thing the place shows far
    off that no place of its scene makes): its pieces (`far`: how many, along how long a line) laid square to its
    bearing at its far spot (far.spot: where its concept box is seen, at its true distance), each turned along that
    line, waiting on its take's bake model like every object; and [{row, why}] of those no spot is found for."""
    by_id, models = {row["id"]: row for row in handin.get("rows", [])}, models_of(handin)
    rows = [row for row in handin.get("rows", []) if row.get("far") and row.get("route") == "prop"]
    inventory = read(inventory_path) if rows else {}
    found, unplaced = [], []
    for row in rows:
        placed = far.spot(design, inventory, row)
        if placed is None:
            unplaced.append({"row": row["id"], "why": "no far spot: the plan fixes fit no projection of the concept, "
                                                      "or the row has no box or no read tall"})
            continue
        model = models.get(row["id"])
        size = by_id.get(model.removesuffix("_1"), row).get("size") if model else row.get("size")
        pieces, length = int(row["far"]["pieces"]), float(row["far"]["length"])
        way = np.asarray(placed["way"])
        for number in range(1, pieces + 1):
            spot = np.asarray(placed["at"]) + way * length * ((number - 0.5) / pieces - 0.5)
            (point,), floor = in_frame(design, [spot])
            found.append({"name": f"{row['id']}_{number}", "row": row["id"], "bake": model, "kind": "object",
                          "at": [point[0], floor, point[1]], "rotation": yaw_turn(design, way, size),
                          "waiting": waits(row, model, by_id),
                          "from": f"far off, {placed['distance']:g} m from the plan's middle where its concept box is "
                                  f"seen (far.spot): piece {number} of {pieces} along {length:g} m"})
    return found, unplaced


# --- the record ---------------------------------------------------------------------------------------------------

def ceiling(design):
    """The highest roof's top, else the walls' tallest, over the floor; None for a place with neither."""
    heights = [float(roof.get("top") or roof.get("eave") or 0.0) for roof in design.get("roofs") or []] + \
        [float(wall.get("tall") or 0.0) for wall in design.get("walls") or []]
    return max(heights) if heights and max(heights) > 0 else None


def relations_input(inputs, place):
    """The place's relations as design_shell.relations_read gives them, against its kept plan."""
    return design_shell.relations_read(inputs, pathlib.Path(inputs["plans"]) / f"{place}.json")


def record_of(plan, design, inputs):
    """The place's scene record from its design (module docstring)."""
    place = plan["place"]
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    handin = read(inputs["hand-in"])
    relations, stale = relations_input(inputs, place)
    design = design_shell.cut_for(design, handin.get("rows", []), relations)
    far_laid = far_objects(design, handin, inputs.get("inventory"))
    record = {"place": place,
              "about": f"{plan['title']}, written by SCORE's scene-record stage from its design: its locked plan, "
                       "its scene inventory's row kinds, the library's lamp and the environment concept's physics at "
                       "its site. Frame: the plan's (x east, z south, y up over its floor).",
              "floor": plan["floor"], "inside": inside(design),
              "structure": structure(plan, design, library_of(inputs), plan_rows(handin)) +
              arch_entries(design, plan["place"], library_of(inputs), handin),
              "objects": design_objects(design, handin, relations) + far_laid[0],
              "lights": lights(design, inputs, relations), "environment": environment(design, read(inputs["sky"])),
              "doorways": plan.get("doorways", []), "places": places_of(place, plan, design, inputs["plans"], handin)}
    ground = None if record["inside"] else ground_under(inputs, place)
    record["views"], left_out = views_inside(views(plan if record["inside"] else dict(plan, doorways=[]), eye, ground),
                                             design, record["inside"])
    if left_out:
        record["views_left_out"] = left_out
    if far_laid[1]:
        record["far_unplaced"] = far_laid[1]
    if stale:
        record["relations_left_out"] = stale
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
