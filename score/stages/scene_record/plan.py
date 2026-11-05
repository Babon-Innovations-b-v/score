"""plan@<place>: the place's dimensioned plan (his kept plan, {home}/design/plans/<place>.json) brought into the store in metres and the
place's own frame (contract `place-plan` v2: v1 had no shell, frame, block, levels or shows), beside what its concept was read into.

    shell     what holds the place's walls (the plan's `shell`): `domed` (the record's room_walls, deck and dome; the
              default), `kit` (the kit's own pieces are the walls and floors: the Earth's rooms and open places) or
              `outdoor` (a place on a body's open ground with no walls of the record's: the wreck, the old station,
              the camp grounds, and the camp, whose kit holds its domes; the plan's w and d are its site, and its
              `lamps`, `decals`, `beams` and `blocks` are a lamp row's light, what is painted on the ground, a column
              of light up from a row and a plain box standing outside the kit, its footing or ramp)
    walls     the room's inside wide and deep, its corners' radius, its walls' height and its dome's rise (read off the
              plan's words) and run (the inventory's room layout, which the plan does not draw); a kit shell's ceiling
              and floor to floor (its storey) from the plan's words; a faceted room's facets, apothem, turn and pit
              (`shape: faceted`, its doors by bearing), a walkway tube's radius, axis, length and glass bands
              (`shape: tube`, its doors its `near` and `far` ends), a flat-roofed room's door opening in its roof
              (`shape: flat`, the inventory's room layout's `opening`: the hangar)
    floor     the plan's inside as the place frame's box round it, and its floor's height
    block     the building a kit room stands in (the plan's `block`, in the place's frame), else None
    doors     each plan door: its side, its middle in the place's frame (on its sill: a door's fifth number is the
              sill's level), its wall's outward normal, its wide and tall, what it is, and where it leads (the plan's
              `leads`, by side or by `<side>@<level>`: a place, `outside` or `sealed`, with why), cut or shut, and
              the leaf the record stands in it (`leaf`: its inventory row and its name, the airlock's outer door)
    doorways  each opening of the written plan a person walks through (a door, a gate, an open doorway) in the place's
              frame: its middle on its sill, the way into the place, its wide, sill and head and where it leads
    items     each plan item's box in the place's frame, its facing and kind, and the inventory rows that make it
    zones     the plan's keep-clear zones; standing: the plan's person spots (on its floor, looking to its middle;
              the cast's); elements: the concept's elements; shows: the places seen from it that no
              made ground seats (the far city), each with why; objects: the plan items a released world model
              makes; aims: where a spot lamp row aims (a plan item)

The plan's own frame is metres from its north-west corner (x east, y south). The place's frame is its kit's: a domed
room's middle on its floor (x east, z south); a plan with a `frame` stands where its `anchor` says (a plan point and
the place point it is), turned so its `toward` plan point falls the way of its place point (the Earth's places share
one frame, the street's; the square's and the launch's plans are drawn down the balcony's view).

Gate `mapped`: every plan item names inventory rows that exist (a zone names none, nor a plot the writer lays, nor an
item a library model makes: its model must be a library reference, tools/library/library_files.py; any other name is a gap), every concept element names rows that
exist, a plan door, a plan object, a plan decal, a plan item (a plot) or its drop, every door says where it leads and why, a sealed door is
one the inventory's room layout shuts with a leaf, and every outdoor lamp and beam stands on a row that exists. How far a row's laid spot (the inventory's, else the kit's pieces of it)
lies from its item's box is measured and shown, never judged here: the layout is the inventory's.

Gate `held` (the audit of 2026-11-04: holds and door leads never reconciled, plans sized apart from their holders): the
plan's frame anchors, person spots and items lie inside its own box; a plan holding places holds each the size and
middle of its own item for the hold's row (rooms several to one item inside it), no two holds overlap, no place held
once is led to by more doors than it has leading back, and every door of a held place to a held sibling meets one of
the sibling's leading back on the holder's plan (`levels`: a place stands as high as a sibling's door to it says).

A place may be held several times (#72: the base's seven tubes, one tube scene stood on each link): each such hold
names its `instance` (`tube#3`), what each of the place's doorways leads to there (`leads`: {its own lead: this
instance's}, the tube's hub and greenhouse ends the habitat's and the hub's) and its `turn` (0, 90, 180 or 270 degrees
clockwise on the holder's plan; any hold may turn); a plan that stretches (`shape: tube`, its run along its d: tube.json's
"stood and stretched") takes its hold's length along its run. The gate judges each instance by itself: its doors and
leads, its size and middle against its own item, its overlaps.
"""
import json
import math
import pathlib
import re
import sys

import numpy as np

from score import checks, contracts

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/library"))
import library_files  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
SIDES = {"N": "north", "S": "south", "E": "east", "W": "west"}
LEADS = ("outside", "sealed")
SHELLS = ("domed", "kit", "outdoor")
# Plan items that name no rows: a keep-clear zone, a growing plot the writer lays as plain plates (writer.plots), and
# a flat roof's door opening the writer leaves in its roof (writer.flat_shell).
UNROWED = ("zone", "plot", "roof_door")
# The openings of a written plan a person walks through (a window is none).
DOORWAYS = ("door", "gate", "opening")
# A row's laid spot this far outside its item's box is shown as off the plan (metres).
SPOT_MARGIN = 0.6
WALLS = re.compile(r"walls (\d+(?:\.\d+)?) m")
RISE = re.compile(r"rising (?:about )?(\d+(?:\.\d+)?) m")
SIZE = re.compile(r"(\d+(?:\.\d+)?) x (\d+(?:\.\d+)?) m")
CEILING = re.compile(r"ceiling (\d+(?:\.\d+)?) m")
STOREY = re.compile(r"floor to floor (\d+(?:\.\d+)?) m")


def files(place):
    """Every kept plan (a door leads to another place's door): the place's own plan, its scene inventory and its
    picked concept are the design's, which the table adds where they are kept (stages.creator_plan); a place with none
    of them blocks on its missing plan by name."""
    return {"plans": "{home}/design/plans", "plan": "{home}/design/plans/{place}.json",
            "inventory": "{home}/design/inventory/{place}.json"}


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def heights(plan, layout):
    """The walls' height and the dome's rise from the plan's words, its run from the inventory's room layout; a kit
    shell's ceiling and floor to floor from its words (none named: 0, an open place); an outdoor place has none."""
    if plan.get("shell") == "outdoor":
        ceiling = CEILING.search(plan["height"])
        return {"high": float(ceiling.group(1)) if ceiling else 0.0, "rise": 0.0, "run": 0.0}
    if plan.get("shell") == "kit":
        ceiling, storey = CEILING.search(plan["height"]), STOREY.search(plan["height"])
        return {"high": float(ceiling.group(1)) if ceiling else 0.0, "storey": float(storey.group(1)) if storey else 0.0,
                "rise": 0.0, "run": 0.0}
    walls, rise = WALLS.search(plan["height"]), RISE.search(plan["height"])
    if walls is None:
        raise ValueError(f"{plan['title']}: the plan's height names no walls' height ({plan['height']!r})")
    return {"high": float(walls.group(1)), "rise": float(rise.group(1)) if rise else 0.0,
            "run": float(layout.get("run", 0.0))}


def frame_of(plan):
    """The plan's frame in the place's: its north-west corner on its floor, and its east and south as place vectors.
    No `frame`: a domed room's middle on its floor, unturned."""
    frame = plan.get("frame")
    if frame is None:
        return np.array([-plan["w"] / 2, 0.0, -plan["d"] / 2]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
    turn = 0.0
    if frame.get("toward"):
        plan_way = np.subtract(frame["toward"]["plan"], frame["anchor"]["plan"])
        place_way = np.subtract(np.asarray(frame["toward"]["place"])[[0, 2]],
                                np.asarray(frame["anchor"]["place"])[[0, 2]])
        turn = math.atan2(place_way[1], place_way[0]) - math.atan2(plan_way[1], plan_way[0])
    east = np.array([math.cos(turn), 0.0, math.sin(turn)])
    south = np.array([-math.sin(turn), 0.0, math.cos(turn)])
    anchor_x, anchor_y = frame["anchor"]["plan"]
    return np.asarray(frame["anchor"]["place"], dtype=float) - east * anchor_x - south * anchor_y, east, south


def placed(plan, x, y, level=0.0):
    """A plan point (metres from its north-west corner, x east, y south), `level` metres up, in the place's frame."""
    corner, east, south = frame_of(plan)
    return np.round(corner + east * x + south * y + np.array([0.0, level, 0.0]), 4)


def door_middle(plan, side, at, level=0.0):
    """A plan door's middle on its sill in the place's frame (`at` is metres along its wall from the plan's
    north-west corner)."""
    x, y = {"N": (at, 0.0), "S": (at, plan["d"]), "W": (0.0, at), "E": (plan["w"], at)}[side]
    return placed(plan, x, y, level).tolist()


def outward(plan, side):
    """A plan wall's outward normal in the place's frame."""
    _, east, south = frame_of(plan)
    return np.round({"N": -south, "S": south, "E": east, "W": -east}[side], 6).tolist()


def lead_of(plan, side, level, at):
    """A door's lead: the plan's `leads` by `<side>:<along>` (a wall with doors to two places, `at` along it: the
    walkway's to the galley and the quarters), else by `<side>@<level>` (a wall with doors at several levels), else
    by side."""
    leads = plan.get("leads", {})
    return leads.get(f"{side}:{float(at):g}") or leads.get(f"{side}@{level:g}", leads.get(side, {}))


def leaf_tall(inventory, kind):
    """A door's height from the leaf that shuts it: the inventory row `<kind>_leaf` (its size's third, up)."""
    for row in inventory["rows"]:
        if row["id"] == f"{kind}_leaf":
            return float(row["size"][2])
    return None


def doors_of(plan, inventory):
    """Each plan door in the place's frame, with where it leads (plan `leads`) and whether it is cut (it leads to a
    place or outside) or shut."""
    layout = inventory.get("room", {}).get("layout", {})
    found = []
    for side, at, wide, what, *level in plan["doors"]:
        level = float(level[0]) if level else 0.0
        lead = lead_of(plan, side, level, at)
        sized = SIZE.search(what)
        kind = layout.get("doors", {}).get(SIDES[side])
        tall = float(sized.group(2)) if sized else leaf_tall(inventory, kind) if kind else None
        found.append({"side": SIDES[side], "plan_side": side, "name": f"{side}@{level:g}" if level else side,
                      "middle": door_middle(plan, side, at, level), "normal": outward(plan, side), "level": level,
                      "at": at, "wide": float(wide), "tall": tall, "what": what, "leads": lead.get("to"),
                      "joins": lead.get("joins"), "joins_door": lead.get("door"),
                      "leaf": lead.get("leaf"), "why": lead.get("why"), "cut": lead.get("to") not in (None, "sealed")})
    return found


def bearing_normal(bearing):
    """The way out of a wall facing `bearing` degrees (0 north, -z; 90 east, +x), on the floor."""
    turn = math.radians(bearing)
    return [round(math.sin(turn), 6), 0.0, round(-math.cos(turn), 6)]


def facet_doors_of(plan):
    """Each door of a faceted room (`[bearing, wide, what]`) in the place's frame: in the middle of the facet facing
    its bearing, on the plan's apothem, with where it leads; its height from its words."""
    found = []
    for bearing, wide, what in plan["doors"]:
        side = str(bearing)
        lead = plan.get("leads", {}).get(side, {})
        sized = SIZE.search(what)
        normal = bearing_normal(bearing)
        found.append({"side": f"bearing {bearing}", "plan_side": side, "name": side, "level": 0.0, "bearing": float(bearing), "normal": normal,
                      "middle": [round(value * plan["apothem"], 4) for value in normal], "wide": float(wide),
                      "tall": float(sized.group(2)) if sized else None, "what": what, "leads": lead.get("to"),
                      "joins": None, "joins_door": None, "why": lead.get("why"),
                      "cut": lead.get("to") not in (None, "sealed")})
    return found


def corner_of(plan):
    """The radius of the room's corners: the plan's `corner`, else 0 for a written plan (score/review/plan_writing),
    whose `outline` draws every corner and curve as its own points, so no corner is rounded past them. A plan with
    neither says nothing of its corners, and is refused by name."""
    if "corner" in plan:
        return float(plan["corner"])
    if plan.get("outline"):
        return 0.0
    raise ValueError(f"{plan['title']}: the plan gives no corner and no outline")


def walls_of(plan, layout):
    """The room's walls: a capsule's inside wide and deep with its corners (a flat roof's: with its door opening),
    or a faceted room's facets, apothem, turn and sunken pit; with the walls' height, the roof's rise and run."""
    if plan.get("shape") == "faceted":
        return {"shape": "faceted", "facets": int(plan["facets"]), "apothem": float(plan["apothem"]),
                "turn": float(plan["turn"]), "pit_radius": float(plan["pit"]["radius"]),
                "pit_floor": float(plan["pit"]["floor"]), "wide": 2 * float(plan["apothem"]),
                "deep": 2 * float(plan["apothem"]), **heights(plan, layout)}
    capsule = {"wide": float(plan["w"]), "deep": float(plan["d"]), "corner": corner_of(plan),
               **heights(plan, layout)}
    if plan.get("shape") == "flat":
        return {**capsule, "shape": "flat", **({"opening": [float(value) for value in layout["opening"]]}
                                                 if layout.get("opening") else {})}
    return capsule


def tube_doors_of(plan):
    """A walkway tube's two open ends (`near`, its frame's z 0, and `far`, its length along), each with where it
    leads; their height from their words."""
    found = []
    for end, wide, what in plan["doors"]:
        lead = plan.get("leads", {}).get(end, {})
        sized = SIZE.search(what)
        far = end == "far"
        found.append({"side": f"{end} end", "plan_side": end, "name": end, "level": 0.0, "normal": [0.0, 0.0, 1.0 if far else -1.0],
                      "middle": [0.0, 0.0, float(plan["length"]) if far else 0.0], "wide": float(wide),
                      "tall": float(sized.group(2)) if sized else None, "what": what, "leads": lead.get("to"),
                      "joins": None, "joins_door": None, "why": lead.get("why"),
                      "cut": lead.get("to") not in (None, "sealed")})
    return found


def tube_walls_of(plan):
    """A walkway tube's section and run: its hull's radius, its axis over the deck, its length, its glass bands'
    bearings round the axis (0 the crown) and its deck's width where the hull meets it."""
    radius, axis = float(plan["radius"]), float(plan["axis"])
    deck = round(2 * math.sqrt(radius ** 2 - axis ** 2), 4)
    return {"shape": "tube", "radius": radius, "axis": axis, "length": float(plan["length"]),
            "glass": [float(value) for value in plan["glass"]], "deck": deck, "wide": deck,
            "deep": float(plan["length"]),
            "high": round(axis + radius, 4), "rise": 0.0, "run": 0.0}


def box_of(plan, x, y, wide, deep):
    """A plan box (x, y, wide, deep) as the place frame's box round it: x0, z0, x1, z1."""
    corners = np.array([placed(plan, x + across, y + along) for across in (0.0, wide) for along in (0.0, deep)])
    return [*corners[:, [0, 2]].min(axis=0).round(4).tolist(), *corners[:, [0, 2]].max(axis=0).round(4).tolist()]


def items_of(plan):
    """Each plan item: its box (x0, z0, x1, z1) in the place's frame, its facing, kind and rows."""
    rows = plan.get("rows", {})
    return [{"name": name, "box": box_of(plan, x, y, wide, deep), "facing": facing, "kind": kind,
             "rows": rows.get(name)}
            for name, x, y, wide, deep, facing, kind in plan["items"]]


def standing_of(plan):
    """Each person spot (the plan's `people`, [x, y, facing, row]: the cast's spots) in the place's frame: [x, z] on
    its floor, its level, and the plan item it looks at (none: the middle)."""
    found = []
    for x, y, *_ in plan.get("people", []):
        spot = placed(plan, x, y)
        found.append({"at": [float(spot[0]), float(spot[2])], "level": float(spot[1]), "looks_at": None})
    return found


def doorways_of(plan):
    """Each opening of the plan a person walks through (`openings` of kind door, gate or opening) in the place's frame:
    its middle on its sill, the way into the place (its wall's normal toward the outline's middle), its wide, sill,
    head and where it leads (`to`)."""
    outline = np.asarray(plan.get("outline") or [[0, 0], [plan["w"], 0], [plan["w"], plan["d"]], [0, plan["d"]]],
                         dtype=float)
    centre = outline.mean(axis=0)
    _, east, south = frame_of(plan)
    found = []
    for number, opening in enumerate(plan.get("openings") or [], 1):
        if opening.get("kind") not in DOORWAYS:
            continue
        turn = math.radians(float(opening.get("angle") or 0.0))
        normal = np.array([-math.sin(turn), math.cos(turn)])
        at = np.asarray(opening["at"], dtype=float)
        if normal @ (centre - at) < 0:
            normal = -normal
        sill = float(opening.get("sill") or 0.0)
        found.append({"name": f"{opening['kind']}-{number}", "middle": placed(plan, *at, sill).tolist(),
                      "inward": np.round(east * normal[0] + south * normal[1], 6).tolist(),
                      "wide": float(opening["wide"]), "sill": sill, "head": opening.get("head"),
                      "to": opening.get("to")})
    return found


def floor_of(plan):
    """The plan's inside as the place frame's box round it, [[x0, z0], [x1, z1]], and its floor's height."""
    box = box_of(plan, 0.0, 0.0, plan["w"], plan["d"])
    return [box[:2], box[2:]], float(frame_of(plan)[0][1])


def shaped(plan, inventory, layout):
    """The plan's walls and doors by its shape: a walkway tube's, a faceted room's or a capsule's."""
    if plan.get("shape") == "tube":
        return tube_walls_of(plan), tube_doors_of(plan)
    if plan.get("shape") == "faceted":
        return walls_of(plan, layout), facet_doors_of(plan)
    return walls_of(plan, layout), doors_of(plan, inventory)


def make(inputs, out, seed, params):
    """plan.json: the plan in the place's frame, with its doors' leads, its items' rows and the concept's elements."""
    plan, inventory = read(inputs["plan"]), read(inputs["inventory"])
    layout = inventory.get("room", {}).get("layout", {})
    shell = plan.get("shell", "domed")
    if shell not in SHELLS:
        raise ValueError(f"{plan['title']}: shell {shell!r} is none of {SHELLS}")
    floor, floor_height = floor_of(plan)
    walls, doors = shaped(plan, inventory, layout)
    record = {"place": pathlib.Path(inputs["kit"]).stem, "title": plan["title"], "shell": shell,
              "inside": (bool(layout.get("wall")) or plan.get("shape") == "tube") if shell == "domed"
              else bool(plan.get("inside")),
              "walls": walls, "glass": bool(layout.get("glass_dome")),
              "floor": floor, "floor_height": floor_height, "block": plan.get("block"),
              "doors": doors, "doorways": doorways_of(plan), "items": items_of(plan), "standing": standing_of(plan),
              "elements": plan.get("elements", []), "shows": plan.get("shows", {}), "objects": plan.get("objects", {}),
              "aims": plan.get("aims", {}), "removes": plan.get("removes", []), "far_ground": plan.get("far_ground"),
              # Each door leaf a lead stands open (`moves`: its kit piece's node, by how far, why).
              "moves": [{**move, "door": side} for side, lead in sorted(plan.get("leads", {}).items())
                        for move in lead.get("moves", [])],
              **({key: plan.get(key, []) for key in ("lamps", "decals", "beams", "blocks")}
                 if shell == "outdoor" else {}),
              "concept": plan.get("concept", {}), "notes": plan.get("notes", []),
              "open": layout.get("open", []), "big_door": layout.get("big_door")}
    (out / "plan.json").write_text(json.dumps(record, indent=1))


def plan_faults(folder):
    path = pathlib.Path(folder) / "plan.json"
    if not path.exists():
        return ["no plan.json"]
    record = json.loads(path.read_text())
    return [f"plan.json lacks {key}" for key in ("place", "walls", "doors", "items", "standing") if key not in record]


PLACE_PLAN = contracts.Contract("place-plan", 2, plan_faults, {"length": "metre", "up axis": "Y"})


# --- held places: where the holder's plan holds them and where their doors meet -------------------------------------

# A door to a held sibling meets a door of the sibling leading back within these (metres: along the floor, in height;
# the audit of 2026-11-04: the base's airlock door opened 21.8 m from the hub's, the flat stood 9 m under its door).
DOORS_MET = 0.3
LEVEL_MET = 0.1
# A hold the size of its holder's item for its row within this share, its middle within HOLD_MIDDLE (metres).
HOLD_SIZED = 0.1
HOLD_MIDDLE = 0.5
# Metres a plan point, a box or a hold may stand past what holds it before it is out.
EDGE = 0.05
# A passage's words (score/review/holders' PASSAGE_WORDS, not imported: holders keys two other stages): a tunnel or
# tube drawn past the plan's edge stands outside it by design.
PASSAGE_WORDS = {"tunnel", "tunnels", "tube", "tubes", "corridor", "corridors"}


def doors_to(plan, name):
    """The plan's doorways (openings a person walks through) leading to `name`."""
    return [opening for opening in plan.get("openings") or []
            if opening.get("kind") in DOORWAYS and opening.get("to") == name]


TURNS = (0, 90, 180, 270)
INSTANCE = "#"  # an instance's name: its place, this mark, its number (tube#3)


def name_of(hold):
    """The name a hold stands under on its holder: its `instance`, else its place."""
    return hold.get("instance") or hold["place"]


def place_of(name):
    """The place an instance's name (`tube#3`) or a place's name stands for."""
    return str(name).partition(INSTANCE)[0]


def turn_of(hold):
    """A hold's turn in degrees clockwise on its holder's plan (TURNS), 0 when it names none; refused otherwise."""
    turn = float(hold.get("turn") or 0)
    if turn not in TURNS:
        raise ValueError(f"{name_of(hold)}'s hold turns {turn:g} degrees, none of {TURNS}")
    return int(turn)


def stretches(plan):
    """Whether a plan is stood stretched to its hold's length along its run (its d): a walkway tube (`shape: tube`,
    tube.json: "every other tube is this stage stood and stretched")."""
    return plan.get("shape") == "tube"


def stretch_of(hold, plan):
    """How many times its own d a stretching plan's run is laid in `hold` (its length along the hold's turned run), 1
    for any other plan or a hold with no box (the holder itself)."""
    if not stretches(plan) or "w" not in hold:
        return 1.0
    return float(hold["w"] if turn_of(hold) in (90, 270) else hold["d"]) / float(plan["d"])


def laid_size(hold, plan):
    """(w, d) a plan covers on its holder's plan laid in `hold`: stretched along its run, turned."""
    wide, deep = float(plan["w"]), float(plan["d"]) * stretch_of(hold, plan)
    return (deep, wide) if turn_of(hold) in (90, 270) else (wide, deep)


def on_holder(hold, plan, point):
    """A point of a held place's plan on its holder's plan: its plan stretched along its run (`stretch_of`), turned by
    the hold's turn and laid in its hold, middle on middle (the scene tree's child_matrix); the holder itself is held
    at its own corner (no w or d)."""
    stretch = stretch_of(hold, plan)
    wide, deep = laid_size(hold, plan)
    across = float(point[0]) - float(plan["w"]) / 2
    along = (float(point[1]) - float(plan["d"]) / 2) * stretch
    turn = math.radians(turn_of(hold))
    cos, sin = round(math.cos(turn)), round(math.sin(turn))
    middle = np.array([hold["x"] + hold.get("w", wide) / 2, hold["y"] + hold.get("d", deep) / 2])
    return middle + np.array([cos * across - sin * along, sin * across + cos * along])


def as_held(hold, plan):
    """`plan` as its hold stands it: each doorway leading where the hold's `leads` say this instance's lead (a tube's
    ends the two places it joins), the rest as its own plan says."""
    renamed = hold.get("leads") or {}
    if not renamed:
        return plan
    return {**plan, "openings": [{**opening, "to": renamed.get(opening.get("to"), opening.get("to"))}
                                 for opening in plan.get("openings") or []]}


def paired(plan, hold, name, other, other_hold, other_name):
    """Each door of `plan` (place `name`, held at `hold`) leading to `other_name`, with the door of `other` leading back
    nearest it on the holder's plan and that door's spot there (None, None: no door leads back), nearest first."""
    back = [(door, on_holder(other_hold, other, door["at"])) for door in doors_to(other, name)]
    found = []
    for door in doors_to(plan, other_name):
        spot = on_holder(hold, plan, door["at"])
        nearest, there = min(back, key=lambda entry: float(np.linalg.norm(entry[1] - spot)), default=(None, None))
        found.append({"door": door, "spot": spot, "back": nearest, "there": there,
                      "gap": None if there is None else float(np.linalg.norm(there - spot))})
    return sorted(found, key=lambda pair: math.inf if pair["gap"] is None else pair["gap"])


def held_plans(holder, plans):
    """{held name (`name_of`): (its hold, its kept plan as the hold stands it)} of each place the holder's plan holds
    that has a plan in `plans`, each instance its own."""
    found = {}
    for hold in holder.get("holds") or []:
        path = pathlib.Path(plans) / f"{hold['place']}.json"
        if path.is_file():
            found[name_of(hold)] = (hold, as_held(hold, read(path)))
    return found


def hold_of(holder, place):
    """`place`'s own hold on the holder's plan: the one holding it once, else its instance that renames none of its
    leads (the one its own plan's leads say: tube.json's west tube), else its first; None when it holds none."""
    holds = [hold for hold in holder.get("holds") or [] if hold["place"] == place]
    own = [hold for hold in holds if not hold.get("instance") or not any(
        old != new for old, new in (hold.get("leads") or {}).items())]
    return (own or holds or [None])[0]


def sill(door):
    return float(door.get("sill") or 0.0)


def levels(holder, plans):
    """{held place: its floor's height over its holder's floor} of the places the holder's plan holds (levels_of)."""
    return levels_of(held_plans(holder, plans))


def levels_of(held):
    """{held place: its floor's height over its holder's floor} ({place: (its hold, its plan)}): on the holder's floor,
    unless a held sibling's door leading to it stands higher than its own door leading back (the stairwell's flat
    door 9 m up: the flat 9 m up), by the pair that meets nearest along the floor; never under the holder's floor."""
    found = {}
    for name, (hold, plan) in held.items():
        raised = [sill(pair["door"]) - sill(pair["back"])
                  for other, (other_hold, other_plan) in sorted(held.items()) if other != name
                  for pair in paired(other_plan, other_hold, other, plan, hold, name)[:1] if pair["back"]]
        found[name] = round(max([0.0, *raised]), 4)
    return found


# --- the gate ---------------------------------------------------------------------------------------------------

def row_spots(inventory, kit):
    """Each inventory row's laid spots (x, z) in the place's frame: the inventory's own, else the kit's pieces of it
    (a kind `<room>_<row>`, its parts left out); a row laid along a wall has none."""
    laid = {}
    for piece in kit.get("pieces", []):
        if "part" not in piece:
            laid.setdefault(piece["kind"], []).append((piece["at"][0], piece["at"][2]))
    return {row["id"]: [(spot["x"], spot["z"]) for spot in row.get("at", []) if "x" in spot]
            or laid.get(f"{kit.get('room')}_{row['id']}", []) for row in inventory["rows"]}


def item_faults(item, ids, made):
    """Why a plan item is not mapped: no rows named and no library model making it (`made`, the plan's object), a
    row the inventory lacks, or a model that is a gap, no library reference (unless the plan marks it `waiting` on
    its model, which the record carries)."""
    found = []
    if made is not None and library_files.parsed(made["model"]) is None and not made.get("waiting"):
        found.append(f"plan item {item['name']!r}: model {made['model']} is a gap, not in the library")
    if item["rows"] is None and made is None:
        return found + [f"plan item {item['name']!r} names no inventory rows and no drop"]
    if not item["rows"] and item["kind"] not in UNROWED and made is None:
        return found + [f"plan item {item['name']!r} names no rows (only a zone, a plot the writer lays, or an item a "
                        "released model makes, may)"]
    return found + [f"plan item {item['name']!r}: row {row} is not in the inventory"
                    for row in item["rows"] or [] if row not in ids]


def element_faults(element, ids, doors, made, decals=(), items=()):
    """Why a concept element is not mapped: no rows, door, object, decal, plan item (one the writer lays: a plot) or
    drop; a row the inventory lacks; a door the plan lacks; an object (a plan item a released model makes), a decal
    or an item the plan lacks."""
    if not any(element.get(key) for key in ("rows", "door", "object", "decal", "item", "drop")):
        return [f"concept element {element['element']!r} names no rows, door, object, decal, plan item or drop"]
    if element.get("object") and element["object"] not in made:
        return [f"concept element {element['element']!r}: object {element['object']!r} is no plan object"]
    if element.get("decal") and element["decal"] not in decals:
        return [f"concept element {element['element']!r}: decal {element['decal']} is not on the plan"]
    if element.get("item") and element["item"] not in items:
        return [f"concept element {element['element']!r}: plan item {element['item']!r} is not on the plan"]
    found = [f"concept element {element['element']!r}: row {row} is not in the inventory"
             for row in element.get("rows", []) if row not in ids]
    if element.get("door") and element["door"] not in doors:
        found.append(f"concept element {element['element']!r}: door {element['door']} is not on the plan")
    return found


def door_faults(door, places, record, ids=None):
    """Why a door's lead is not said: none, no why, a place the world lacks, a sealed door the layout leaves open, a
    cut door with no height, or a leaf whose row the inventory lacks. A cut door may hold a leaf: it opens (a motion),
    and the doorway leads on."""
    name = f"door {door['name']} ({door['what']})"
    if not door["leads"] or not door["why"]:
        return [f"{name} says nowhere it leads, or not why"]
    found = []
    if door["leads"] not in LEADS and door["leads"] not in places:
        found.append(f"{name} leads to {door['leads']}, which is no place of the world")
    if door["joins"] and door["joins"] not in places:
        found.append(f"{name} joins {door['joins']}, which is no place of the world")
    is_big = (record.get("big_door") or {}).get("wall") == door["side"]
    if not door["cut"] and (is_big or door["side"] in record["open"]):
        found.append(f"{name} is sealed but the room layout leaves it open (no leaf shuts it)")
    if door["cut"] and door["tall"] is None:
        found.append(f"{name} has no height: neither its words nor a leaf row give one")
    if door.get("leaf") and ids is not None and door["leaf"]["row"] not in ids:
        found.append(f"{name}: its leaf's row {door['leaf']['row']} is not in the inventory")
    return found


def lit_faults(record, ids):
    """Why an outdoor plan's lamp or beam is not mapped: the row it stands on is not in the inventory."""
    return [f"{kind[:-1]} {entry['name']!r}: row {entry['row']} is not in the inventory"
            for kind in ("lamps", "beams") for entry in record.get(kind, [])
            if entry["row"] not in ids and not entry.get("place")]  # another place's row: its kit, the writer's


def off_plan(record, inventory, kit):
    """Each mapped row's laid spot farther than SPOT_MARGIN outside the nearest item naming it: shown, not judged."""
    spots, found = row_spots(inventory, kit), []
    boxes = {}
    for item in record["items"]:
        for row in item["rows"] or []:
            boxes.setdefault(row, []).append(item)
    for row, items in boxes.items():
        for x, z in spots.get(row, []):
            gap, item = min((max(low_x - x, x - high_x, low_z - z, z - high_z, 0.0), item["name"])
                            for item in items for low_x, low_z, high_x, high_z in [item["box"]])
            if gap > SPOT_MARGIN:
                found.append(f"{row} at ({x:.2f}, {z:.2f}) lies {gap:.2f} m off plan item {item!r}")
    return found


def judge_mapped(output, inputs, evidence):
    """Fail on a plan item, concept element or door that is not mapped (module docstring)."""
    record = read(pathlib.Path(output) / "plan.json")
    inventory = read(inputs["inventory"])
    ids = {row["id"] for row in inventory["rows"]}
    places = {path.stem for path in pathlib.Path(inputs["plans"]).glob("*.json")}
    doors = {door["plan_side"] for door in record["doors"]} | {door["name"] for door in record["doors"]}
    faults = [fault for item in record["items"]
              for fault in item_faults(item, ids, record["objects"].get(item["name"]))]
    if not record["elements"]:
        faults.append("the plan holds no concept elements")
    decals = {decal["name"] for decal in record.get("decals", [])}
    faults += [fault for element in record["elements"]
               for fault in element_faults(element, ids, doors, record["objects"], decals,
                                           {item["name"] for item in record["items"]})]
    faults += [fault for door in record["doors"] for fault in door_faults(door, places, record, ids)]
    faults += lit_faults(record, ids)
    shown = off_plan(record, inventory, read(inputs["kit"]))
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"every plan item, concept element and door is mapped ({len(record['items'])} items, "
         f"{len(record['elements'])} elements, {len(record['doors'])} doors)")
    return checks.Verdict("mapped", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "rows off their item": len(shown)}, {"faults": "lower"},
                          tuple(faults + [f"shown, not judged: {line}" for line in shown]))


def door_faults_held(held, level):
    """Each door of a held place to a held sibling that meets no door of the sibling leading back on the holder's
    plan: none leads back, the nearest is more than DOORS_MET away, or stands at another height (LEVEL_MET)."""
    found = []
    for name, (hold, plan) in sorted(held.items()):
        for other, (other_hold, other_plan) in sorted(held.items()):
            if other == name:
                continue
            for pair in paired(plan, hold, name, other_plan, other_hold, other):
                said = f"{name}'s door to {other} at {pair['door']['at']}"
                if pair["back"] is None:
                    found.append(f"{said}: no door of {other} leads back to {name}")
                elif pair["gap"] > DOORS_MET:
                    found.append(f"{said} opens {pair['gap']:.1f} m from {other}'s nearest door back "
                                 f"({pair['back']['at']}) where the holder holds both")
                elif abs(level[name] + sill(pair["door"]) - level[other] - sill(pair["back"])) > LEVEL_MET:
                    found.append(f"{said} stands {level[name] + sill(pair['door']):.2f} m up, {other}'s door back "
                                 f"{level[other] + sill(pair['back']):.2f} m")
    return found


def once_faults(held):
    """Each held place more doors of its held siblings lead to than it has doors leading back: held once, it cannot
    meet them all (the base's one tube for six)."""
    found = []
    for name, (_, plan) in sorted(held.items()):
        leading = sum(len(doors_to(other_plan, name)) for other, (_, other_plan) in held.items() if other != name)
        back = sum(len(doors_to(plan, other)) for other in held if other != name)
        if leading > back:
            found.append(f"{name} is held once, but {leading} doors of its siblings lead to it and {back} of its own "
                         "lead back")
    return found


def laid_faults(held):
    """Each hold another size than its place's plan laid in it (`laid_size`: turned, a tube stretched along its run),
    off by more than EDGE: the scene tree would stand it past its hold (the hangar's 32 x 64 m plan held unturned in
    a box drawn wide)."""
    found = []
    for name, (hold, plan) in sorted(held.items()):
        wide, deep = laid_size(hold, plan)
        if abs(wide - hold["w"]) > EDGE or abs(deep - hold["d"]) > EDGE:
            found.append(f"{name}'s hold is {hold['w']:g} x {hold['d']:g} m, its plan laid in it "
                         f"{wide:g} x {deep:g} m (turned {turn_of(hold)})")
    return found


def unnamed_faults(held):
    """Each door of a held place leading to a place the holder holds only as instances by the place's own name: it
    meets no one of them (the hub's four doors to `tube` once the base held a tube on each link)."""
    instances = {}
    for name, (hold, _) in held.items():
        if hold.get("instance"):
            instances.setdefault(hold["place"], []).append(name)
    found = []
    for name, (_, plan) in sorted(held.items()):
        for opening in plan.get("openings") or []:
            to = opening.get("to")
            if opening.get("kind") in DOORWAYS and to in instances and to not in held:
                found.append(f"{name}'s door to {to} at {opening['at']} names no instance of it "
                             f"({', '.join(sorted(instances[to]))})")
    return found


def overlap_faults(holder):
    """Each two holds of the holder's plan whose boxes overlap (more than EDGE both ways)."""
    holds = holder.get("holds") or []
    found = []
    for number, one in enumerate(holds):
        for two in holds[number + 1:]:
            across = min(one["x"] + one["w"], two["x"] + two["w"]) - max(one["x"], two["x"])
            along = min(one["y"] + one["d"], two["y"] + two["d"]) - max(one["y"], two["y"])
            if across > EDGE and along > EDGE:
                found.append(f"the holds of {name_of(one)} and {name_of(two)} overlap by {across:.1f} x {along:.1f} m")
    return found


def within(box, outer):
    """Whether a box (x, y, w, d) lies inside another, EDGE allowed."""
    return box[0] >= outer[0] - EDGE and box[1] >= outer[1] - EDGE and \
        box[0] + box[2] <= outer[0] + outer[2] + EDGE and box[1] + box[3] <= outer[1] + outer[3] + EDGE


def hold_faults(holder):
    """Each hold that disagrees with the holder's own item for its row: no item of the row; one place a row holds
    another size (HOLD_SIZED) or middle (HOLD_MIDDLE) than its nearest item; rooms several to an item (the ship's in
    its hull) outside it. An instance is one place to one item, its own nearest (the base's tubes, one a link)."""
    rows = holder.get("rows") or {}
    holds = holder.get("holds") or []
    found = []
    for hold in holds:
        if not hold.get("row"):
            continue
        items = [[float(value) for value in item[1:5]] for item in holder.get("items") or []
                 if hold["row"] in (rows.get(item[0]) or [])]
        box = [hold["x"], hold["y"], hold["w"], hold["d"]]
        if not items:
            found.append(f"{name_of(hold)} is held in row {hold['row']}, which no item of the plan draws")
            continue
        nearest = min(items, key=lambda item: math.dist((item[0] + item[2] / 2, item[1] + item[3] / 2),
                                                        (box[0] + box[2] / 2, box[1] + box[3] / 2)))
        sharing = sum(1 for other in holds if other.get("row") == hold["row"])
        if sharing > len(items) and not hold.get("instance"):
            if not within(box, nearest):
                found.append(f"{name_of(hold)}'s hold {box} stands outside its {hold['row']} item {nearest}")
            continue
        middle = math.dist((nearest[0] + nearest[2] / 2, nearest[1] + nearest[3] / 2),
                           (box[0] + box[2] / 2, box[1] + box[3] / 2))
        sized = all(abs(own - its) <= HOLD_SIZED * its for own, its in ((box[2], nearest[2]), (box[3], nearest[3])))
        if not sized or middle > HOLD_MIDDLE:
            found.append(f"{name_of(hold)}'s hold is {box[2]:.1f} x {box[3]:.1f} m, its {hold['row']} item "
                         f"{nearest[2]:.1f} x {nearest[3]:.1f} m, their middles {middle:.1f} m apart")
    return found


def inside_faults(plan, name):
    """Each frame anchor, person spot or item box of the plan outside its own box (w by d, EDGE allowed)."""
    outer = [0.0, 0.0, float(plan["w"]), float(plan["d"])]
    found = []
    for key in ("anchor", "toward"):
        point = ((plan.get("frame") or {}).get(key) or {}).get("plan")
        if point is not None and not within([*point, 0.0, 0.0], outer):
            found.append(f"{name}'s frame {key} {point} lies outside its {outer[2]} x {outer[3]} m plan")
    for number, spot in enumerate(plan.get("people") or [], 1):
        if not within([float(spot[0]), float(spot[1]), 0.0, 0.0], outer):
            found.append(f"{name}'s person spot {number} {spot[:2]} lies outside its {outer[2]} x {outer[3]} m plan")
    for item in plan.get("items") or []:
        if not set(re.findall(r"[a-z]+", str(item[0]).lower())) & PASSAGE_WORDS and not item_inside(item, outer):
            found.append(f"{name}'s item {item[0]!r} {item[1:5]} lies outside its {outer[2]} x {outer[3]} m plan")
    return found


def item_inside(item, outer):
    """Whether a plan item stands in the plan's box: its middle inside, reaching past the box by at most half its
    thinner side (a door or a pipe drawn centred on the wall line), EDGE allowed."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    if not within([x + wide / 2, y + deep / 2, 0.0, 0.0], outer):
        return False
    reach = min(wide, deep) / 2
    return within([x + reach, y + reach, max(wide - 2 * reach, 0.0), max(deep - 2 * reach, 0.0)], outer)


def judge_held(output, inputs, evidence):
    """Fail on a plan that does not hold what it says where it says (module docstring): its frame anchors, person
    spots and items outside its own box; and, holding places, a hold another size or spot than its item, two holds
    overlapping, a place held once that several doors lead to, a hold another size than its plan laid in it, a door
    naming a place held only as instances, a door to a held sibling meeting none leading back (each instance by
    itself)."""
    place = read(pathlib.Path(output) / "plan.json")["place"]
    design = read(pathlib.Path(inputs["plans"]) / f"{place}.json")
    held = held_plans(design, inputs["plans"])
    faults = inside_faults(design, place) + hold_faults(design) + overlap_faults(design) + once_faults(held) + \
        laid_faults(held) + unnamed_faults(held) + door_faults_held(held, levels_of(held))
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"its plan holds its things inside it and its {len(held)} held places where their doors meet" if held
         else "its plan holds its things inside it")
    return checks.Verdict("held", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "held places": len(held)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("mapped", judge_mapped), checks.Check("held", judge_held))
