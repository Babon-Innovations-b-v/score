"""scene-record@<place>: the place's scene record written by SCORE from its design alone (the owner, 2026-10-21: every
stage builds from the creator's design; nothing old is read): its locked plan (the plan row's plan.json, and the kept
plan itself for what the plan row does not carry: its outline, walls, openings, levels, stairs, roofs, items' shapes
and the places its holder's plan holds), its scene inventory (the row kinds: which rows glow), the library's lamp,
and its sky inputs (`{home}/design/sky/<place>.json`: the environment concept's physics, its site and scene time,
worked out by score/review/overhead.py). Contract `scene-record` v1 is today's record schema, so tools/usd/scene.py
builds it unchanged; it lands as record/<place>.json in the output.

    inside       the plan encloses the place (walls or roofs drawn) on no ground of its own (no terrain spots)
    structure    an inside place's room shell from its plan (earth_seed/design_shell.pieces: each level's deck, the
                 outline's walls with every opening cut, the roofs), stood in the place's frame as builders' `slab`,
                 `gable`, `dome` and `tube_arc` (a vault) entries, each wall on its written line; none where
                 the place's base already lays it (design_shell.laid_for: a room whose plan says its kit holds its walls); and each stair or ramp the
                 plan draws as a flight of steps; an `arch` at each plan item of an arched structure row of the
                 hand-in (design_shell.arched: a tube's ribs), at the row's size, named its row; each entry's surface the scene's surface library's for its kind
                 (surface-library@<place>, read as an `after`: design_shell.PART_KINDS), else none and
                 `surface_missing` says why (the scene builder names it on the mesh, never paints another way); the
                 shell's own structural rows' pieces (design_shell.row_pieces: pillars, beams, pads, grates) for
                 every enclosed place, its base's shell or its own; and its wall kit (score/stages/wall_kit, #128:
                 frames round every opening, the panels, padded sections, dado and facades its code rows name) as
                 `slab` and `specks` entries tracing to the library's wall kit algorithm by their `from`
    lights       at each plan item of a glowing row (its row kind, score/stages/row_kinds.py, or its concept
                 showing it glow, `{home}/design/light/<place>.json`, reading.concept_light) as many as its pieces,
                 and at least the things its reading counts over the row's items (lamp_count): over the item's
                 middle, several along it, as high on it as the library's lamp for the row's mount says, its numbers
                 that lamp's (data/library/lamps.json, tools/props/scene/lamps.py), reaching by how high it hangs; a
                 row the concept shows glowing in the colour it shows there, its strength times its brightness there
                 and times its glowing part's share (lamps.json `glowing`: a screen or an indicator a faint emitter);
                 an item outlining the whole room held on a wall (score/review/holders) on that wall's face instead,
                 several spread along it
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
    views        first the concept's view (`concept_view`, #128: high, CONCEPT_PITCH down at the floor's middle the
                 way the concept looks, as far back in the room's free space as it stands clear; the film's first
                 camera, `held` at its height), then one from inside each doorway looking across, one from each of
                 the plan's person spots (an inside
                 place's only where the eye stands inside its outline: the others in `views_left_out`, with why); an
                 open place's spot at its floor stands on the terrain row's made ground under it (`terrain`, the one
                 thing made that the record reads: wreck's eyes stood under its ground, 2026-10-30); an eye at the
                 floor where a person would stand in a wall, a floor thing or another person moved to the nearest
                 free floor, its aim by the same offset (review/standing.py, `clear_of`); a look meeting a wall or
                 floor thing within CLEAR_LOOK turned to the nearest clear way, else left out with why (`looked`;
                 flat's spot-2 faced its wardrobe from 0.45 m, 2026-10-31)
    doorways     the plan's doorways in the place's frame (the plan row's), which ground-fit judges
    places       each other place its holder's plan holds that a door or opening of this place leads to, stood where
                 its door leading back meets this place's door to it (else where the holder's plan holds it, `holds`),
                 as high as a sibling's door to it says (place_plan.levels), turned as its own plan's frame is

Every entry's `from` names the plan element, inventory row or physics it was made from. Nothing of a game, a kit, a
filed definition or an old record is read.
"""
import json
import math
import pathlib
import sys

import numpy as np

from score import contracts
from score.review import holders, overhead, plan_checks, standing
from score.review.plan_checks import WALLS_ITEM
from score.stages import row_kinds, wall_kit
from score.stages.earth_seed import design_shell
from score.stages.scene_record import concept_light, far
from score.stages.scene_record import plan as place_plan
import score.stages.shapes_first.floor_fit as floor_fit

REPO = pathlib.Path(__file__).resolve().parents[3]
# The shell's backing: a wall the plan does not write stands this far behind its outline's edge, its deck this far
# under the floor (design_shell's, which lays the same shell in a kit room's base).
BACKING = design_shell.BACKING
DECK_BELOW = design_shell.DECK_BELOW
# A part's surface is the scene's surface library's for its kind (design_shell.PART_KINDS), else none and named
# missing (`surface_missing`, which tools/usd/scene.py marks the mesh with).
LIBRARY_ROW = "surface-library"
# A ramp is laid as a flight of steps this high each (metres), fine enough to walk as a slope.
RAMP_STEP = 0.05
# A box flight's waist: metres of slab under each step's riser foot (flight_steps), so a flight is treads on a stepped
# slab with room under it, never solid columns down to its foot (#128: the street's 15 steps up to 3 m read as brown
# columns, 2026-11-15).
STAIR_WAIST = 0.15
# A view stands this far inside its doorway (every view sees far.VIEW_FOV wide).
VIEW_IN = 1.0
AIM_HEIGHT = 1.0
# A view's look must run this far clear of walls and floor things: a view is judged by its whole picture's mean
# luminance (stages/light/mix.py), and a surface nearer than a doorway eye stands in from its door fills most of its
# far.VIEW_FOV picture (1.7 m across at 1 m), so it reads that surface, not the room (flat's spot-2, 0.45 m off its
# wardrobe, read 0.026 against the concept's 0.263, 2026-10-31).
CLEAR_LOOK = VIEW_IN
# A blocked look turns by this many degrees a try, either way, nearest the aim first, up to all the way round.
TURN_STEP = 15
# A view looking within this many degrees of straight up or down has no up of the world's (its picture's sideways
# is their cross product: round 33's spot-1 at shiplock looked straight down and every measure was NaN), so it is
# given the floor's long axis as its up (`upright`).
STEEP = 10.0
# The concept's view, the record's first (#128 cause 6: the film opened at a door or a spot, a 1.6 m eye in a bunk,
# outside a wall, a shelf at arm's length or facing the empty side): every concept is drawn "high three-quarter ... 35
# to 45 degrees down" (score/review/concepts.py INSIDE_VIEW, OUTSIDE_VIEW). An inside place's eye stands
# CONCEPT_UNDER under its walls' top (its cutaway's eye stands outside the walls; ours stays in the room, high,
# looking down across it); an open place's rises CONCEPT_PITCH as it steps back. It looks at the floor's middle along
# the way the concept looks (far.heading), from as far back as it stands clear, stepped back CONCEPT_STEP at a time:
# CONCEPT_ROOM round it clear of walls and of anything less than CONCEPT_OVER under the eye, its look clear for
# CONCEPT_LOOK; a room too tight for the first clearance tries the next (quarters' bunks, 4.5 m across).
CONCEPT_PITCH = 40.0
CONCEPT_ROOM = (1.0, 0.75, 0.5)
CONCEPT_OVER = 0.3
CONCEPT_LOOK = 1.5
CONCEPT_UNDER = 0.4
CONCEPT_STEP = 0.25
# Anchors whose thing hangs off a wall or the ceiling: its column is solid to the eye (garage's shelf, 0.7 m off it).
HUNG_ANCHORS = ("wall", "ceiling", "roof")
# The day sky's picture (sky_dome): its brightness and colour balance in red, green and blue, and the picture's width
# in texels. Fitted 2026-11-10 on campgrounds' light passes (10 views, the sky where the render met no surface, put
# through their own AgX table) against its concept's sky (mean [231.7, 195.5, 159.2], blue to red 0.687), the one
# Mars concept that shows its sky: the gain of 2026-10-11 (11.76, 7.56, 5.04, fitted on the camp's old concept K05)
# read pale grey through AgX, gap 22.8 levels and blue to red 0.845 (median); this one 9.1 and 0.708, and 11.8 and
# 0.722 in a CPU preview render of the dome. The dome lights nothing (usd_views.sky_domes), so it moves the sky alone.
SKY_GAIN = (38.58, 7.55, 4.36)
SKY_WIDTH = 1024
# What a door may lead to that is no place.
NOT_PLACES = ("outside", "sealed")
# The routes whose rows' models the record lays at their plan items (prepare's groups.ROUTES): people are the cast's.
LAID_ROUTES = ("prop", "shell")
# The last word of a row's id that names the flight the plan draws for it, by the flight's kind: a ramp (the lander's
# ramp), else a stair (the greenhouse's stairs); never a thing named for one (a stair railing, a step ladder).
FLIGHT_NOUNS = {"ramp": frozenset(("ramp", "ramps")),
                "stair": frozenset(("stair", "stairs", "staircase", "staircases", "steps"))}
# The part of the place each piece of the shell is (design_shell.part_kind), as a reading's row says its part: a row
# the plan lays itself (route `plan`) is named on a piece of its part, an opening on the piece over its cut (shell).
SHELL_PARTS = {"deck": "floor", "wall": "wall", "roof": "roof"}
# The words of an opening row's id that name a roof's opening and a floor's (open_cuts); any other is a wall's.
ROOF_WORDS = frozenset(("roof", "ceiling", "skylight"))
FLOOR_WORDS = frozenset(("floor", "hatch"))
# An item's way (x across) in plan metres by its facing (None as north): turned east or west it lies across.
FACING_WAY = {None: (1.0, 0.0), "N": (1.0, 0.0), "S": (-1.0, 0.0), "E": (0.0, 1.0), "W": (0.0, -1.0)}
# A plan polygon (or a row's ground size) at most this wide across for its length is a band, long one way.
BAND_SHARE = 0.5
# A row's ground size, or a plan box, at most this wide across for its length is longer one way (writer.item_way).
ELONGATED = 0.8


def files(place):
    """The design files the writer reads: the place's kept plan and every other (its holder's `holds`, its siblings'
    frames), its scene inventory, its concept's light once read, its sky inputs (scene_sky.keep's), the real bodies'
    dusty air (data/physics/dust.json, its day sky outside), the row-kind
    rules, the library's lamp, the environment's eye height (place.json `shared`), the batch's hand-in (prepare's
    handin.py: each row's route and the take that makes its model) and its relations once derived (relations_file)."""
    return {"inventory": "{home}/design/inventory/{place}.json", "plans": "{home}/design/plans",
            "sky": "{home}/design/sky/{place}.json", "dust": "{data}/physics/dust.json",
            "row kinds": "{data}/checks/row-kinds.json",
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
    elif piece["builder"] == "vault":  # builders' tube_arc runs along z from 0: turned a quarter about up to run east
        arc = design_shell.piece_arc(dict(piece, points=entry.pop("points"), eave=floor + piece["eave"],
                                          top=floor + piece["top"]))
        entry.update(builder="tube_arc", radius=round(arc["radius"], 4), axis_high=round(arc["axis_high"], 4),
                     start=round(arc["from"], 4), end=round(arc["to"], 4), length=round(arc["length"], 4),
                     placed_at=[round(arc["start"][0], 4), 0.0, round(arc["start"][1], 4)],
                     placed_turn=[0.0, math.sqrt(0.5), 0.0, math.sqrt(0.5)] if arc["along"][0]
                     else [0.0, 0.0, 0.0, 1.0],
                     layer=2)
    elif piece["builder"] == "gable":
        entry.update(eave=round(floor + piece["eave"], 4), top=round(floor + piece["top"], 4), layer=2)
    elif piece["builder"] == "quad":  # a shed roof's face: its corners stood in the place's frame
        del entry["points"]
        corners, _ = in_frame(design, [[corner[0], corner[2]] for corner in piece["corners"]])
        entry.update(corners=[[x, round(floor + corner[1], 4), z] for (x, z), corner in zip(corners, piece["corners"])],
                     layer=2)
    else:
        entry.update(low=round(floor + piece["low"], 4), high=round(floor + piece["high"], 4))
        if name.startswith("roof"):
            entry["layer"] = 2
    return entry


def cut_piece(design, middle):
    """The name of the shell piece over the cut an opening at plan point `middle` makes in its wall (its lintel, else
    the wall's foot under it: design_shell.walls' pieces, in its spans' order), else None: no wall is cut there."""
    openings, eave = design_shell.openings_of(design), design_shell.lowest_eave(design)
    for name, start, end, thick, entry, inner in design_shell.wall_lines(design):
        length = math.dist(start, end)
        at = design_shell.on_edge([{"at": middle, "wide": 0.0, "sill": 0.0, "head": 0.0}], start, end, thick)
        if not at:
            continue
        cuts = design_shell.on_edge(openings, start, end, thick)
        high = design_shell.wall_height(design, entry, eave, (start, end), inner)
        spans = design_shell.inner_spans(length, cuts, high) if inner else \
            design_shell.spans(length, cuts, -DECK_BELOW - design_shell.SLAB, high)
        over = [number for number, (begin, finish, *_) in enumerate(spans)
                if (begin, finish) in {cut[:2] for cut in cuts} and begin <= at[0][0] <= finish]
        if over:
            return name if over[-1] == 0 else f"{name}_{over[-1] + 1}"
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
    (opening_pieces; none where no wall is cut at it: hangar's floor hatch named no lintel, 2026-10-30), else at a cut
    its words fit (name_open_cuts)."""
    found = [painted(shell_entry(name, number, piece, design, said),
                     "glass" if piece.get("glass") else design_shell.part_kind(name), place, library)
             for name, parts, said in design_shell.pieces(design) for number, piece in enumerate(parts)]
    by_name = {entry["name"]: entry for entry in found}
    for row_id in (rows or {}).get("opening", []):
        for name in opening_pieces(design, row_id):
            by_name[name].setdefault("row", row_id)
    # an opening row its plan item cuts no wall for named on its cut first, before a free row takes that piece (the
    # hangar's roof panels took roof_1, its roof opening left on none, 2026-11-06); a floor hatch's flight is named
    # in `structure`, once the flights are laid
    name_open_cuts(design, found, (rows or {}).get("opening", []))
    free = {part: list(ids) for part, ids in (rows or {}).items() if part != "opening"}
    for entry in found:
        if "row" in entry:
            continue
        ids = free.get(SHELL_PARTS.get(entry["name"].split("_")[0]))
        if ids:
            entry["row"] = ids.pop(0)
    return found


def stair(number, entry, design):
    """A stair or ramp the plan draws as a flight of steps along its footprint the way it says (`angle`: degrees from
    east, clockwise as y runs south), from its `from` height to its `to`: its `foot` the lower end, wherever the
    plan's `from` lies, since the builder (tools/usd/builders.py stairs) lays steps up from its foot (the stairwell's
    flights of 3 m to 1.5 m stood as flat blocks 1.5 m tall, their treads underneath, 2026-11-04)."""
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
    if high < low:
        (foot, low), (top, high) = (top, high), (foot, low)
    return {"name": f"{entry.get('kind', 'stair')}_{number}", "builder": "stairs",
            "foot": [foot[0], round(floor + low, 4), foot[1]], "top": [top[0], round(floor + high, 4), top[1]],
            "wide": round(float(side.max() - side.min()), 4), "steps": max(1, steps),
            "from": f"the plan's {entry.get('kind', 'stair')} {number}: from {low:g} m to {high:g} m, "
                    f"{max(1, steps)} steps up its footprint at {float(entry.get('angle') or 0.0):g} degrees"}


def flight_steps(flight):
    """A box flight (stair: its foot, top, wide and steps in the place's frame) as one `slab` a step: its tread at its
    rise, down its riser and STAIR_WAIST under that, never below the flight's foot, so the flight stands as steps on a
    stepped slab with room under it, never a row of solid columns down to its foot (#128). tools/usd/builders.py's
    `stairs` is left as it is (an edit there moves 83 paid rows' keys); this lays builders' `slab`, as the wall kit
    does. The first step keeps the flight's name (`<kind>_<n>`: the plan-matched gate's, a hatch's), the others
    `<kind>_<n>_<step>`."""
    foot, top = np.asarray(flight["foot"], float), np.asarray(flight["top"], float)
    run = top[[0, 2]] - foot[[0, 2]]
    way = run / max(float(np.linalg.norm(run)), 1e-9)
    side = np.array([-way[1], way[0]]) * float(flight["wide"]) / 2
    steps = int(flight["steps"])
    rise = (float(top[1]) - float(foot[1])) / steps
    found = []
    for step in range(steps):
        near, far = foot[[0, 2]] + run * step / steps, foot[[0, 2]] + run * (step + 1) / steps
        high = float(foot[1]) + rise * (step + 1)
        low = max(float(foot[1]), high - rise - STAIR_WAIST)
        found.append({"name": flight["name"] if step == 0 else f"{flight['name']}_{step + 1}", "builder": "slab",
                      "points": [[round(float(x), 4), round(float(z), 4)]
                                 for x, z in (near - side, far - side, far + side, near + side)],
                      "low": round(low, 4), "high": round(high, 4),
                      "from": f"{flight['from']}: step {step + 1}, its tread on a {STAIR_WAIST:g} m waist"})
    return found


def structure(plan, design, library=None, rows=None, handin=None):
    """The record's structure: an inside place's shell where its base does not lay it (its own rows, `rows`, named on
    its pieces), and the plan's stairs, each a slab a step (flight_steps), but each the take of a row of the hand-in
    lays (flight_takes: never a box flight beside a take), each painted from the scene's surface library (`library`: its materials.json content, None
    while not made)."""
    shelled = shell(design, plan["place"], library, rows) if inside(design) and not design_shell.laid_for(design) \
        else []
    taken = flight_takes(design, handin or {})
    flights = [painted(step, "stair", plan["place"], library) for number, entry in flights_of(design)
               if number not in taken for step in flight_steps(stair(number, entry, design))]
    if shelled:
        name_open_cuts(design, shelled + flights, (rows or {}).get("opening", []))
    return shelled + flights


def flights_of(design):
    """[(number, flight)] of each stair or ramp the plan draws (a footprint of three points or more), numbered as the
    record names them (`<kind>_<number>`, counting every drawn entry)."""
    return [(number, entry) for number, entry in enumerate(design.get("stairs") or [], 1)
            if len(entry.get("points") or []) >= 3]


def flight_kind(row):
    """The kind of flight (FLIGHT_NOUNS: ramp, stair) a row is by the last word of its id, else None."""
    last = str(row.get("id") or "").lower().split("_")[-1]
    return next((kind for kind, nouns in FLIGHT_NOUNS.items() if last in nouns), None)


def flight_middle(entry):
    """A flight's footprint's middle, in plan metres."""
    return np.asarray(entry["points"], float).mean(axis=0)


def row_distance(design, row_id, entry):
    """Metres from a flight's middle to the nearest middle of a plan item of its own laying the row (the walls item
    none), inf with none."""
    items, tied = {item[0]: item for item in design.get("items") or []}, design.get("rows") or {}
    middles = [np.array([float(items[name][1]) + float(items[name][3]) / 2,
                         float(items[name][2]) + float(items[name][4]) / 2])
               for name, ids in tied.items() if row_id in (ids or []) and name in items and name != WALLS_ITEM]
    return min((float(np.linalg.norm(middle - flight_middle(entry))) for middle in middles), default=math.inf)


def flight_takes(design, handin):
    """{flight number: row id} of each flight the plan draws that a row of its kind (flight_kind) with a take
    (models_of: the place's own baked model) lays, there in place of a box flight (2026-11-15, #128: the greenhouse's
    baked stairs and the airlock's baked ramp stood unused while box flights were laid, and the engine room and the
    camp grounds laid a box ramp beside their ramp's take). Each kind's rows and flights are paired nearest first (a
    row's distance its nearest plan item's to the flight, row_distance; a row on no item last), one flight a row; a
    flight left over takes its nearest row of its kind again (the greenhouse's one stairs row on its three flights).
    A flight no row with a take of its kind names stays a flight of steps."""
    models = models_of(handin)
    rows = [row for row in handin.get("rows", []) if row["id"] in models and flight_kind(row)
            and row.get("route", "prop") in LAID_ROUTES and not row.get("far")]
    found = {}
    for kind in FLIGHT_NOUNS:
        ranked = sorted((row_distance(design, row["id"], entry), index, number, row["id"])
                        for number, entry in flights_of(design) if (entry.get("kind") == "ramp") == (kind == "ramp")
                        for index, row in enumerate(rows) if flight_kind(row) == kind)
        paired = set()
        for _, _, number, row_id in ranked:
            if number not in found and row_id not in paired:
                found[number] = row_id
                paired.add(row_id)
        for _, _, number, row_id in ranked:
            if not own_item(design, row_id):  # one laid at its own item stands for one flight alone
                found.setdefault(number, row_id)
    return found


def own_item(design, row_id):
    """Whether the plan gives a row an item of its own (one laying it alone, never the walls item): the engine room's
    RAMP 1, the garage's DOOR RAMP 1; never one it shares (the camp grounds' lander ramp on its lander's item)."""
    return any(ids == [row_id] for name, ids in (design.get("rows") or {}).items() if name != WALLS_ITEM)


def flown_rows(design, handin):
    """{flight number: row id} of the flights a take is laid at in place of a box flight (flight_takes) whose row has
    no plan item of its own (own_item): one with its own item is laid there by its relation (a ramp pitched up to its
    level), its flight left unbuilt."""
    return {number: row_id for number, row_id in flight_takes(design, handin).items() if not own_item(design, row_id)}


def flights_named(design, handin, found):
    """Name each flight a take laid at its row's own item stands for (flight_takes less flown_rows) on that row's
    first object in `found` (`flight`, as the plan-matched gate counts it laid): the engine room's ramp at its RAMP 1,
    no box ramp beside it."""
    flown = flown_rows(design, handin)
    drawn = dict(flights_of(design))
    for number, row_id in sorted(flight_takes(design, handin).items()):
        laid = next((entry for entry in found if entry["row"] == row_id and "flight" not in entry), None)
        if number not in flown and laid is not None:
            laid["flight"] = f"{drawn[number].get('kind', 'stair')}_{number}"


def flight_objects(design, handin):
    """The objects of the takes laid at the plan's flights (flown_rows): one at each flight its row lays, `<row>_<n>`,
    over its footprint's middle at its low end's height, its long side along its way up, waiting on its row's model,
    `flight` naming the flight it stands for (`<kind>_<number>`, as the plan-matched gate counts it laid); a flight
    whose row is laid at an item of its own is named on that item's first piece (flights_named)."""
    by_id, models, drawn = {row["id"]: row for row in handin.get("rows", [])}, models_of(handin), dict(flights_of(design))
    found, counts = [], {}
    for number, row_id in sorted(flown_rows(design, handin).items()):
        entry, row, model = drawn[number], by_id[row_id], models[row_id]
        size = by_id.get(model.removesuffix("_1"), row).get("size")
        turn = math.radians(float(entry.get("angle") or 0.0))
        low, high = float(entry["from"]), float(entry["to"])
        way = np.array([math.cos(turn), math.sin(turn)]) * (1.0 if high >= low else -1.0)  # its way up
        (point,), floor = in_frame(design, [flight_middle(entry)], min(low, high))
        counts[row_id] = counts.get(row_id, 0) + 1
        name = f"{entry.get('kind', 'stair')}_{number}"
        laid = {"name": f"{row_id}_{counts[row_id]}", "row": row_id, "bake": model, "kind": "object",
                "at": [point[0], floor, point[1]], "rotation": yaw_turn(design, way, size),
                "waiting": waits(row, model, by_id), "flight": name,
                "from": f"the plan's {name.replace('_', ' ')}, inventory row {row_id}: its take laid in place "
                        f"of a box flight, from {min(low, high):g} m up its footprint"}
        if entry.get("kind") == "ramp":
            laid["on"] = flight_ramp(design, entry, way, name)
        found.append(laid)
    return found


def flight_ramp(design, entry, way, name):
    """The `on` (how "ramp", as related lays a ramp up to its level) of a ramp take laid at the plan's flight: the
    flight's high end's edge across its footprint, its way up and its high end's height, in the place's frame, which
    the assembly pitches the take by onto the deck there (fitting.ramp_rest), else, named its `flight`, up to that high
    end itself (fitting.ramp_end), so it reaches what the flight reaches
    (#128: the camp grounds' lander ramp lay flat on its footprint, short of the hatch, 2026-11-15)."""
    points = np.asarray(entry["points"], float)
    across = np.array([-way[1], way[0]])
    along, side = points @ way, points @ across
    edge = [way * along.max() + across * side.min(), way * along.max() + across * side.max()]
    ends, top = in_frame(design, edge, max(float(entry["from"]), float(entry["to"])))
    return {"how": "ramp", "edge": ends, "up": plan_way(design, way), "top": top, "flight": name,
            "why": f"up the plan's {name.replace('_', ' ')} to its high end at "
                   f"{max(float(entry['from']), float(entry['to'])):g} m"}


def open_cuts(design, words):
    """The names of the shell's pieces at the openings it cuts that an opening row of these words (its id's) may be
    named on, in order: a roof's (roof, ceiling, skylight) the first piece of each roof cut round its openings; a
    floor's (floor, hatch) each flight going down through a hatch its deck is cut over (design_shell.hatches); any
    other the lintel over each of the plan's own wall openings (cut_piece)."""
    if words & ROOF_WORDS:
        return [f"roof_{number}" for number, entry in enumerate(
            [entry for entry in design.get("roofs") or [] if len(entry.get("points") or []) >= 3], 1)
            if design_shell.roof_holes(entry)]
    if words & FLOOR_WORDS:
        levels = [level for level in design.get("levels") or [] if len(level.get("points") or []) >= 3] or \
            [{"height": 0.0, "points": design_shell.outline_of(design)}]
        return [f"{entry.get('kind', 'stair')}_{index + 1}" for level in levels
                for index, _ in design_shell.hatches(design, level)
                for entry in [(design.get("stairs") or [])[index]]]
    return [name for name in (cut_piece(design, opening["at"]) for opening in design_shell.openings_of(design))
            if name]


def name_open_cuts(design, entries, row_ids):
    """Name each opening row no plan item of its own cuts a wall for (shell's opening_pieces left it unnamed) on the
    first free piece at an opening the shell cuts that its words fit (open_cuts): the lab's corridor openings on the
    lintels over its doors, the hangar's floor hatch on the flight down through its deck's hatch (2026-11-05); a row
    no such piece fits stays unnamed, for the plan-matched gate (gates.unbuilt_rows) to fail."""
    by_name = {entry["name"]: entry for entry in entries}
    named = {entry.get("row") for entry in entries}
    for row_id in row_ids:
        if row_id in named:
            continue
        words = {word.removesuffix("s") for word in row_id.lower().split("_")}
        free = [name for name in open_cuts(design, words) if name in by_name and "row" not in by_name[name]]
        if free:
            by_name[free[0]]["row"] = row_id
            named.add(row_id)


def row_entries(design, place, library, handin):
    """The pieces the shell builds of its own structural rows (design_shell.row_pieces: pillars along the walls, beams
    under the roof, pads and grates at their plan items), each named its row, painted from the scene's library as its
    part kind; none for a place the plan does not enclose. A room whose base lays its shell (design_shell.laid_for)
    gets them here too: its base lays only the deck, walls and roof (2026-11-15, #128: no beam, pillar or grate of a
    kit room was built)."""
    if not inside(design):
        return []
    rows = [row for row in handin.get("rows", []) if row.get("route") == "plan"]
    return [dict(painted(shell_entry(name, 0, piece, design, said), kind, place, library), row=row_id)
            for row_id, name, piece, said, kind in design_shell.row_pieces(design, rows)]


def kit_part(design, part):
    """One solid of a wall kit piece (plan metres, heights over the floor) as a `slab` stood in the place's frame."""
    points, floor = in_frame(design, part["points"])
    return {"builder": "slab", "points": points, "low": round(floor + part["low"], 4),
            "high": round(floor + part["high"], 4)}


def kit_specks(design, specks):
    """A wall kit piece's rivet heads ([x, y, height] in plan metres) as builders' `specks` numbers in the place's
    frame."""
    points, floor = in_frame(design, [spot[:2] for spot in specks])
    return {"builder": "specks", "points": [[point[0], round(floor + spot[2], 4), point[1]]
                                            for point, spot in zip(points, specks)], "across": wall_kit.RIVET}


def kit_entries(design, place, library, handin):
    """The wall kit (score/stages/wall_kit: frames round every opening, and the panels, padded sections, dado,
    facades and ceiling panels, hung under the roof's underside here, roof_under, of the code rows the plan's shell
    lays, route `plan`) of an enclosed place: each solid of a piece a `slab`
    entry, its rivets one `specks` entry, named kit_<piece>[_<n>], painted with the scene library variant its words
    choose (wall_kit.surface), else none and why. Its `from` ends with the wall kit's code that made it, by which the
    library check traces it to the wall kit algorithm entry. No `row`: a thin slab with a row is a raised floor pad
    to the assembly (assembly/on_pads.py), so the rows stay named on the shell's pieces as before."""
    if not inside(design):
        return []
    rows = [row for row in handin.get("rows", []) if row.get("route") == "plan"]
    found = []
    for piece in wall_kit.pieces(design, rows, lambda spot: roof_under(design, spot)):
        surface = wall_kit.surface(piece, library)
        laid = [kit_part(design, part) for part in piece.parts] + \
            ([kit_specks(design, piece.specks)] if piece.specks else [])
        for number, numbers in enumerate(laid, 1):
            entry = {"name": f"kit_{piece.name}" if len(laid) == 1 else f"kit_{piece.name}_{number}", **numbers,
                     "plain": piece.plain, "from": piece.said, "surface": surface}
            if surface is None:
                entry["surface_missing"] = design_shell.missing_why(place, "wall", library)
            found.append(entry)
    return found


def arch_entry(row, item, shape, design, number):
    """An arched row's band at its plan item (design_shell.arches): standing on the item's middle at its shape's base,
    spanning the row's wide along the item's longer side, rising its tall, its deep both its thickness and its depth;
    in a walkway tube its hull's hoop (tube_rib)."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    span, band, rise = (float(value) for value in row["size"])
    middle = np.array([x + wide / 2, y + deep / 2])
    if design_shell.tube_of(design) and design_shell.tube_run(design) is not None:
        return tube_rib(row, item, design, number, middle, band)
    way = np.array([1.0, 0.0]) if wide >= deep else np.array([0.0, 1.0])
    feet, floor = in_frame(design, [middle - way * span / 2, middle + way * span / 2])
    return {"name": f"{row['id']}_{number}", "builder": "arch", "feet": feet,
            "low": round(floor + float(shape.get("base") or 0.0), 4), "rise": rise, "thick": band, "deep": band,
            "plain": "shell", "row": row["id"],
            "from": f"plan item {item[0]!r}, inventory row {row['id']}: an arch {span:g} m across and {rise:g} m "
                    f"high, {band:g} m thick (earth_seed/design_shell.arched)"}


def tube_rib(row, item, design, number, middle, band):
    """A walkway tube's rib (design_shell.tube_of) at its plan item: a hoop round the hull's circle on the inside of
    it, its section `band` across, standing square to the tube's run at the item's place along it, its middle on the
    tube's axis (builders' `torus`, turned up; its foot under the deck hidden by it). The tube's ribs stood as arches
    as tall as they were wide, off its round hull (2026-11-15)."""
    tube, run = design_shell.tube_of(design), design_shell.tube_run(design)
    outline = np.asarray(design_shell.outline_of(design), float)
    across = int(run[0] > run[1])  # the plan axis across the run: the tube's axis stands at its middle
    middle = middle.copy()
    middle[across] = (outline[:, across].min() + outline[:, across].max()) / 2
    (spot, ahead), floor = in_frame(design, [middle, middle + run])
    axis_high = floor + float(design_shell.lowest_eave(design) or 0.0) + tube["axis"]
    along_z = abs(ahead[1] - spot[1]) >= abs(ahead[0] - spot[0])
    half = round(math.sqrt(0.5), 6)
    return {"name": f"{row['id']}_{number}", "builder": "torus", "inner": round(tube["radius"] - band, 4),
            "outer": round(tube["radius"], 4), "height": 0.0,
            "placed_at": [spot[0], round(axis_high, 4), spot[1]],
            "placed_turn": [half, 0.0, 0.0, half] if along_z else [0.0, 0.0, half, half],
            "plain": "shell", "row": row["id"],
            "from": f"plan item {item[0]!r}, inventory row {row['id']}: a hoop round its walkway tube's hull, "
                    f"{tube['radius']:g} m round its axis {tube['axis']:g} m over the deck, {band:g} m thick "
                    "(earth_seed/design_shell.arched, tube_of)"}


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


def wall_lamp_spot(relation, pieces=1, piece=0):
    """(plan spot, face ends) of a lamp on its wall relation (score/review/holders `wall`), LAMP_OUT out from the
    wall's face into the room: one lamp at its spot's nearest point on the face; the `piece`-th of several spread
    evenly along the face, each the middle of its own share of it (2026-11-04: a row of three wall lamps stood as
    one, on one spot)."""
    wall = relation["wall"]
    start, end = np.asarray(wall["from"], float), np.asarray(wall["to"], float)
    length = float(np.linalg.norm(end - start))
    run = (end - start) / max(length, 1e-9)
    out = np.array([-run[1], run[0]]) * relation["side"]
    face = out * float(wall.get("thick") or 0.0) / 2
    along = float(np.clip((np.asarray(relation["spot"], float) - start) @ run, 0.0, float((end - start) @ run))) \
        if pieces == 1 else length * (piece + 0.5) / pieces
    return start + face + run * along + out * LAMP_OUT, [start + face, end + face]


# Glowing parts that show light rather than throw it which lamps.json's `emitter` words do not name yet: a keypad's
# backlit keys (2026-11-10: shiplock's door keypad was read as a whole lamp, its three cyan lamps gave 50-80% of the
# room's light and failed its colour check). Kept here, not in lamps.json, which is in about 91 paid rows' keys.
CONTROL_FACES = {"keypad", "keypads", "touchpad", "touchpads", "touchscreen", "touchscreens"}
# A warning light or beacon is a signal, made to be seen rather than to light a room, as an indicator is (2026-11-10:
# garage's four amber warning bulbs and docking_airlock's red door warning lights threw room light as lamps, at
# about 3100 K and in red, and both rooms read warmer than their concepts).
SIGNAL_LIGHTS = {"warning", "beacon", "beacons"}


def glow_share(row, glow, path):
    """(share, kind) of the library's lamp a glowing part throws as room light (data/library/lamps.json `glowing`):
    a faint emitter (a screen, an indicator, a keyboard, a keypad, a flame, a warning light: its `emitter` words,
    CONTROL_FACES or SIGNAL_LIGHTS in what glows, else in the row's noun or name) its `emitter` share, any other
    glowing part (a lamp, a strip, a grow light) a light source at 1 (2026-11-04: screens and indicator lamps threw
    room light as lamps did, and the lab came out green and red)."""
    entry = json.loads(pathlib.Path(path).read_text()).get("glowing") or {}
    emitter = entry.get("emitter")
    if not emitter:
        return 1.0, "source"
    said = set(row_kinds.words(" ".join(str(text) for text in (
        (glow or {}).get("glowing") or "", row.get("noun") or "", row.get("name") or "", row.get("id") or ""
    ))).split())
    return (float(emitter["share"]), "emitter") if said & (set(emitter["words"]) | CONTROL_FACES | SIGNAL_LIGHTS) \
        else (1.0, "source")


def lamp_count(row, laid):
    """How many lamps each plan item of a glowing row lays (`laid`, [(item, shape)]): as many as its pieces
    (pieces_of: its shape's count, and at least the row's counted things, its reading's `count`, over all its items;
    2026-11-04: 23 glowing rows in 13 places laid one lamp for a row read as up to 13, garage's three ceiling lamps
    one)."""
    return pieces_of(row, laid)


def lamp_high(item, row, design, mount, share, relation=None):
    """Metres over the floor a glowing row's lamp at its plan item shines from: `share` (its library mount's `high`)
    up its shape's height from its base; where its shape gives no height (a code or structure row's item, the walls
    item), up the row's own height from where it is mounted: the height its wall relation gives it, else, on the
    ceiling mount, its top under the ceiling, else the height its words give a wall thing (holders.mount_height: high
    on its wall, above the bed); else up the ceiling from the floor (#128: hangar's wall lamps and quarters' string and
    wall lights shone from the floor, 0 m over it, their shapes giving no height)."""
    shape = (design.get("shapes") or {}).get(item[0]) or {}
    base = float(shape.get("base") or 0.0)
    if shape.get("tall"):
        return base + float(shape["tall"]) * share
    own = float(row["size"][2]) if sized(row) else 0.0
    held = relation.get("height") if relation and relation.get("how") == "wall" else None
    top = ceiling(design)
    if held is not None:
        return float(held) + own * share
    if mount == "ceiling" and top:
        return max(base, top - own) + own * share
    said = holders.mount_height(item, row, design)
    if said is not None:
        return said[0] + own * share
    return base + (top or 0.0) * share


def item_lamps(item, row, rows, design, library, path, glow=None, relation=None, pieces=1):
    """The lights of a glowing row's plan item, `pieces` of them (lamp_count): one over its middle, several evenly
    along its path (spots_of; an item outlining the whole room along its box's long middle line, never round the room's
    outline), each as high on it as the library's lamp for the row's mount puts it, reaching by how high that is over
    the floor; an item outlining the whole room (holders.outlines_room: its middle says nothing of where it is) held on
    a wall (`relation`) on that wall's face (wall_lamp_spot: at the relation's spot, several spread along the face), as
    high on its shape, else on the wall's height (the place's ceiling), as its mount puts it; where its concept shows it
    glowing (`glow`, the concept's light), the colour its light is there and its strength that lamp's times its
    brightness there; each times its glowing part's share (glow_share: a screen is no lamp)."""
    name, x, y, wide, deep = item[0], *[float(value) for value in item[1:5]]
    shape = (design.get("shapes") or {}).get(name) or {}
    room = holders.outlines_room(item, design)
    walled = relation is not None and relation.get("how") == "wall" and room
    mounts, words = library.mounts(path), library.mount_words(path)
    mount = library.mount_of(row, rows, words)
    high = lamp_high(item, row, design, mount, float(mounts[mount]["high"]), relation)
    light = library.light_at(row, high, rows, mounts, words)
    energy, colour, attenuation = game_lamp()
    part, kind = glow_share(row, glow, path)
    why = f"its concept shows its {glow['glowing'] or 'light'} glowing" if glow else \
        f"row kind {row['row_kind']}, it glows"
    spots = [wall_lamp_spot(relation, pieces, piece) for piece in range(pieces)] if walled else \
        [(spot, None) for spot, _ in spots_of(item, {} if room else shape, pieces, row)]
    found = []
    for number, (plan_spot, face) in enumerate(spots, 1):
        (spot,), floor = in_frame(design, [plan_spot], high)
        found.append({"type": "omni", "at": [spot[0], floor, spot[1]], "row": row["id"],
                      "colour": glow["colour"] if glow else colour,
                      "energy": round(energy * light["strength"] * part *
                                      (float(glow["brightness"]) if glow else 1.0), 4),
                      "range": light["reach"], "attenuation": attenuation, "shadows": light["shadows"],
                      "from": f"plan item {name!r}, inventory row {row['id']} ({why}): the library's lamp "
                              f"(data/library/lamps.json) for its mount, {high:.2f} m over the floor"
                              + (f", lamp {number} of {pieces} at the item" if pieces > 1 else "")
                              + (f", a faint {kind} at {part:g} of a lamp" if kind == "emitter" else "")
                              + (f", on its wall ({relation['why']})" if walled else ""),
                      **({"against": in_frame(design, face)[0]} if walled else {})})
    return found


def glowing_rows(inputs):
    """({row id: inventory row}, {row id: its concept's glow}) of the scene's glowing rows: those whose row kind glows
    (row_kinds.rows_that) and those its concept shows glowing, a row of the sky (anchored `sky`) left to the
    physics."""
    inventory = read(inputs["inventory"])
    glowing = {row["id"]: row for row in row_kinds.rows_that(inventory, "glows", row_kinds.table(inputs["row kinds"]))}
    shown = {row: glow for row, glow in (read(inputs["concept light"])["rows"] if "concept light" in inputs
                                         else {}).items() if glow["glows"]}
    glowing |= {row["id"]: {**row, "row_kind": glowing.get(row["id"], {}).get("row_kind")}
                for row in inventory["rows"] if row["id"] in shown and row.get("anchor") != "sky"}
    return glowing, shown


def lights(design, inputs, relations=None):
    """Lights at the plan items of the scene's glowing rows (glowing_rows): those whose row kind glows and those its
    concept shows glowing (an engine's core, a screen, a light strip; owner, 2026-10-25: "look at the concept, the
    engines themself should be a source of light"), in the colour and brightness the concept shows; a row of the sky
    (anchored `sky`: its stars, a planet) is the physics' (the light layer's sky), no lamp. Each item lays as many as
    lamp_count gives it, so a row lays at least the things its reading counts; an item outlining the whole room has
    its lamps on the wall its relation (`relations`, score/review/holders) holds it on (item_lamps)."""
    inventory = read(inputs["inventory"])
    glowing, shown = glowing_rows(inputs)
    rows_of, library, holding = item_rows(design), library_lamps(), relations_of(relations)
    shapes, laid = design.get("shapes") or {}, {}
    for item in design.get("items") or []:
        if len(item) > 6 and item[6] == "zone":
            continue
        for row_id in rows_of.get(item[0]) or []:
            if row_id in glowing:
                laid.setdefault(row_id, []).append((item, shapes.get(item[0]) or {}))
    found = []
    for row_id, items in laid.items():
        for (item, _), pieces in zip(items, lamp_count(counted(glowing[row_id], design), items)):
            found += item_lamps(item, glowing[row_id], inventory["rows"], design, library, inputs["lamp library"],
                                shown.get(row_id), holding.get((item[0], row_id)), pieces)
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


def sky_dome(design, kept, dust):
    """The day sky's air over a place on a real body with dusty air (`dust`, data/physics/dust.json: its entry by the
    site body's reference), as tools/usd/mars_sky.py scatters it (scene.write_sky_dome, the light layer draws it while
    a sun is up); None on a body without dust (2026-11-02: the sky_dome entries left with the old records, eb01c402,
    and every outdoor Mars place's sky was black: campgrounds' 192.8 levels off its concept's). An inside place
    carries it too: its views see the sky through its glass and openings (2026-11-04: camp's glass domes showed black
    starry space in a Mars afternoon, its sun 9.8 degrees up), and a shell with none hides it."""
    on = kept["site"].get("on")
    body = next((body for body in kept["setting"].get("bodies") or [] if body.get("body") == on), None)
    found = (dust.get("bodies") or {}).get(body.get("reference") or body.get("body")) if body else None
    if not found:
        return None
    return {**{key: value for key, value in found.items() if key != "cited"}, "gain": list(SKY_GAIN),
            "width": SKY_WIDTH,
            "from": f"{body['name']}'s dusty air (data/physics/dust.json: {dust['sources'][found['cited']]}); its "
                    f"gain {list(SKY_GAIN)} fitted on campgrounds' rendered sky against its concept's sky "
                    f"(2026-11-10, colour gap 9.1 levels)"}


def environment(design, kept, dust=None):
    """Inside or not, and the place's sky from the physics at its site at its scene time (sky_seen), with its day
    sky's dusty air where it stands outside on a dusty body (sky_dome, from `dust`, data/physics/dust.json)."""
    site = kept["site"]
    found = {"inside": inside(design), "site": site, "time": kept["time"], "sky": sky_seen(kept),
             "from": f"the environment concept's physics (score/review/overhead.py) at the place's site on "
                     f"{site.get('on')} at its scene time {kept['time']}; its sky is drawn by the light layer"}
    dome = sky_dome(design, kept, dust or {})
    return found if dome is None else {**found, "sky_dome": dome}


# --- views --------------------------------------------------------------------------------------------------------

def middle_of(plan):
    """The plan's inside's middle on its floor, in the place's frame (x, z)."""
    (low_x, low_z), (high_x, high_z) = plan["floor"]
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def item_middle(plan, name):
    low_x, low_z, high_x, high_z = next(item["box"] for item in plan["items"] if item["name"] == name)
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def views(plan, eye_height, ground=None, clear=None, sight=None):
    """One view inside each doorway looking across the inside's middle (the doorway's mirror through it), one from
    each standing spot to the middle at its own level or to the plan item it looks at on the floor; each eye at
    standing height over its level (the plan row's plan.json: its `doorways` and `standing`), a spot at the floor
    over the made ground under it where `ground` (ground_under) has one there. An eye at the floor where a person
    would stand in a wall, a thing or another person moves by `clear`'s offset (`clear_of`), its aim with it; a look
    `sight` (`sight_of`) finds blocked within CLEAR_LOOK turns to the nearest clear way (`looked`)."""
    found, middle = [], middle_of(plan)
    for door in plan.get("doorways", []):
        at = np.asarray(door["middle"], dtype=float)
        eye = at + np.asarray(door["inward"], dtype=float) * VIEW_IN
        aim = 2 * middle - at[[0, 2]]
        offset = clear(eye[[0, 2]]) if clear and at[1] <= plan["floor_height"] else None
        if offset is not None:
            eye, aim = eye + [offset[0], 0.0, offset[1]], aim + offset
        found.append({"name": f"from-{door['name']}", "eye": [round(eye[0], 3), round(at[1] + eye_height, 3),
                                                             round(eye[2], 3)],
                      "aim": [round(aim[0], 3), round(at[1] + AIM_HEIGHT, 3), round(aim[1], 3)], "fov": far.VIEW_FOV,
                      "from": f"plan {door['name']} ({door['wide']:g} m wide, to {door['to']}), looking across"})
        found[-1] = looked(found[-1], sight, min(float(at[1]), plan["floor_height"]))
    for number, spot in enumerate(plan["standing"], 1):
        aim = item_middle(plan, spot["looks_at"]) if spot["looks_at"] else middle
        aim_level = plan["floor_height"] if spot["looks_at"] else spot["level"]
        offset = clear(np.asarray(spot["at"], dtype=float)) if clear and spot["level"] <= plan["floor_height"] \
            else None
        at = np.asarray(spot["at"], dtype=float) + (offset if offset is not None else 0.0)
        aim = np.asarray(aim, dtype=float) + (offset if offset is not None else 0.0)
        stands = spot_ground({**spot, "at": at.tolist()}, plan["floor_height"], ground)
        found.append({"name": f"spot-{number}",
                      "eye": [round(at[0], 3), round(stands + eye_height, 3), round(at[1], 3)],
                      "aim": [round(aim[0], 3), round(aim_level + AIM_HEIGHT, 3), round(aim[1], 3)],
                      "fov": far.VIEW_FOV, "from": f"plan standing spot {number}, looking to " +
                                              (f"plan item {spot['looks_at']!r}" if spot["looks_at"] else "the middle")})
        found[-1] = looked(found[-1], sight, stands if spot["level"] <= plan["floor_height"] else plan["floor_height"])
    return [upright(view, plan["floor"]) for view in found]


def concept_tops(design, inventory):
    """(grid, tops): plan_checks.Grid cells of the design and how high over its floor the solid in each reaches: a
    wall all the way, a thing on the floor its shape's tall, one on another thing a metre over that, one hung off a wall
    or the ceiling all the way; people, things seen far off, an item outlining the room (holders.outlines_room:
    engineroom's wall panels, its middle says nothing) and a walkway tube's ribs (hoops round its hull, its axis
    clear: the tube's eight ribs held its eye 2 m from its middle, 2026-11-16) none."""
    grid = plan_checks.Grid(design)
    tops = np.zeros(grid.shape)
    anchored, left_out = plan_checks.anchors(inventory), plan_checks.people(inventory) | plan_checks.afar(inventory)
    if design_shell.tube_of(design) and design_shell.tube_run(design) is not None:
        left_out |= {row["id"] for row in (inventory or {}).get("rows") or [] if design_shell.arched(row)}
    for item, row, shape in plan_checks.placed_items(design):
        if row in left_out or holders.outlines_room(item, design):
            continue
        anchor = anchored.get(row, "floor")
        tall = float((shape or {}).get("tall") or 1.0)
        top = tall if anchor in plan_checks.FLOOR_ANCHORS else np.inf if anchor in HUNG_ANCHORS else tall + 1.0
        covered = grid.covered(plan_checks.polygon_of(item, shape))
        tops[covered] = np.maximum(tops[covered], top)
    for wall in design.get("walls", []):
        tops[grid.covered(plan_checks.wall_polygon(wall))] = np.inf
    return grid, tops


def concept_view(design, inventory, eye_height, enclosed, ground=None, sight=None):
    """The concept's view (CONCEPT_PITCH above): its eye stepped back from the floor's middle against the way the
    concept looks (far.heading's away; looking north, the painting's near side at the plan's bottom, where no
    projection fits), at least a person's eye over what it stands on, to the furthest step that stays inside the
    outline and clear by the first of CONCEPT_ROOM that leaves one. In a walkway tube (design_shell.tube_of) the eye
    stands on its axis line, looking along its run (the end the concept's way leans to) from no nearer its end than
    the clearance, under its hull's crown (the tube's eye stood 2.8 m up over its 2.7 m crown, in its end doorway,
    2026-11-16). `held`: the film stands at this eye (tools/review/demo.py), never lowered to a walker's. None where no
    step stands clear."""
    ways = far.heading(design, inventory)
    away = ways[0] if ways is not None else np.array([0.0, -1.0])
    said = "the way the concept looks (its plan fixes' projection)" if ways is not None else \
        "north (no projection of the concept fits: its near side is the plan's bottom)"
    grid, tops = concept_tops(design, inventory)
    outline = np.asarray(plan_checks.outline_of(design), dtype=float)
    middle = outline.mean(axis=0) if design.get("outline") else far.middle_of(design)
    floor = float(place_plan.placed(design, *middle)[1])
    ceiling_top = max((float(wall.get("tall") or 0.0) for wall in design.get("walls") or []), default=0.0) or \
        ceiling(design)
    high = floor + ceiling_top - CONCEPT_UNDER if enclosed and ceiling_top else None
    tube, run, reach = design_shell.tube_of(design), design_shell.tube_run(design), np.inf
    if tube is not None and run is not None and high is not None:
        away = run if float(away @ run) >= 0 else -run
        said = f"along the tube's run, {said}"
        crown = float(design_shell.lowest_eave(design) or 0.0) + tube["axis"] + tube["radius"]
        high = min(high, floor + crown - CONCEPT_UNDER)
        reach = float(np.ptp(outline @ run)) / 2
    roofs = [(np.asarray(roof["points"], dtype=float), float(roof.get("eave") or roof.get("top") or ceiling_top))
             for roof in design.get("roofs") or [] if len(roof.get("points") or []) >= 3]
    target = place_plan.placed(design, *middle)
    if ground:
        target[1] = ground(target[0], target[2]) or target[1]
    best = None
    for room in CONCEPT_ROOM:
        for back in np.arange(CONCEPT_STEP, float(np.hypot(design["w"], design["d"])), CONCEPT_STEP):
            spot = middle - away * back
            if back > reach - room or not plan_checks.inside(spot[None, :], outline)[0]:
                break
            eye = place_plan.placed(design, *spot)
            stands = (ground(eye[0], eye[2]) if ground else None) or floor
            rise = target[1] + back * math.tan(math.radians(CONCEPT_PITCH)) if high is None else \
                min([high] + [floor + eave - CONCEPT_UNDER for points, eave in roofs
                              if plan_checks.inside(spot[None, :], points)[0]])
            eye[1] = max(rise, stands + eye_height)
            near = np.linalg.norm(grid.centres - spot, axis=1).reshape(grid.shape) <= room
            if not (stands + tops[near] > eye[1] - CONCEPT_OVER).any() and \
                    not (sight and sight(eye, target, stands, CONCEPT_LOOK) is not None):
                best = (back, eye, room)
        if best is not None:
            break
    if best is None:
        return None
    back, eye, room = best
    view = {"name": "concept", "eye": [round(float(value), 3) for value in eye],
            "aim": [round(float(value), 3) for value in target], "fov": far.VIEW_FOV, "held": True,
            "from": f"the concept's view: down at the floor's middle, looking {said}, {back:g} m back in the room's "
                    f"free space, clear by {room:g} m"}
    return upright(view, [[min(eye[0], target[0]) - 1, min(eye[2], target[2]) - 1],
                          [max(eye[0], target[0]) + 1, max(eye[2], target[2]) + 1]])


def looked(view, sight, base):
    """The view as it is when `sight` finds its look clear for CLEAR_LOOK; else turned about its eye to the nearest
    way TURN_STEP by TURN_STEP that is, said in its `from`; else marked `blind` with why (views_kept leaves it out)."""
    if sight is None:
        return view
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    hit = sight(eye, aim, base)
    if hit is None:
        return view
    for turn in [side * step for step in range(TURN_STEP, 181, TURN_STEP) for side in (1, -1)]:
        cos, sin = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        way = aim[[0, 2]] - eye[[0, 2]]
        turned = eye[[0, 2]] + [way[0] * cos - way[1] * sin, way[0] * sin + way[1] * cos]
        new_aim = np.array([turned[0], aim[1], turned[1]])
        if sight(eye, new_aim, base) is None:
            return dict(view, aim=[round(float(value), 3) for value in new_aim],
                        **{"from": f"{view['from']}, turned {turn:+d} degrees off a wall or thing {hit:.2f} m ahead"})
    return dict(view, blind=f"a wall or thing stands within {CLEAR_LOOK:g} m of its eye every way it turns "
                            f"({hit:.2f} m ahead): it would see one surface, not the room")


def sight_of(design, inventory):
    """(eye, aim, base[, reach]) -> how far along the look from `eye` toward `aim` (place frame) its first wall or
    floor thing (plan_checks.blocking, as tall as its shape; its doorways open) stands, within `reach` (CLEAR_LOOK),
    or None when none does; `base` is the height the things stand on."""
    grid = plan_checks.Grid(design)
    tops = np.zeros(grid.shape)
    for item, _, shape in plan_checks.blocking(design, inventory):
        covered = grid.covered(plan_checks.polygon_of(item, shape))
        tops[covered] = np.maximum(tops[covered], float((shape or {}).get("tall") or 1.0))
    for wall in design.get("walls", []):
        tops[grid.covered(plan_checks.wall_polygon(wall))] = np.inf
    for opening in design.get("openings", []):
        if opening.get("kind") in ("door", "opening", "gate"):
            tops[grid.covered(plan_checks.opening_polygon(opening))] = 0.0
    corner, east, south = place_plan.frame_of(design)

    def first_hit(eye, aim, base, reach=CLEAR_LOOK):
        look = (aim - eye) / max(float(np.linalg.norm(aim - eye)), 1e-9)
        for along in np.arange(0.0, reach, grid.size / 2):
            point = eye + look * along
            across = point[[0, 2]] - corner[[0, 2]]
            spot = np.array([float(across @ east[[0, 2]]), float(across @ south[[0, 2]])])
            cell = np.floor((spot - grid.low) / grid.size).astype(int)[::-1]  # off the grid nothing stands
            if (cell >= 0).all() and (cell < grid.shape).all() and point[1] - base < tops[tuple(cell)]:
                return float(along)
        return None
    return first_hit


def upright(view, floor):
    """The view, with an `up` along the floor's long axis (x when the floor is as wide as it is deep) when it looks
    within STEEP of straight up or down; else as it is, its up the world's."""
    look = np.subtract(view["aim"], view["eye"], dtype=float)
    if abs(look[1]) < np.linalg.norm(look) * math.cos(math.radians(STEEP)):
        return view
    (low_x, low_z), (high_x, high_z) = floor
    return dict(view, up=[1.0, 0.0, 0.0] if high_x - low_x >= high_z - low_z else [0.0, 0.0, 1.0])


def clear_of(design, inventory):
    """(x, z) -> the offset [dx, dz] in the place's frame that takes an eye there to the nearest floor inside the
    design's outline where a person stands in no wall, floor thing or person spot but the one it stands on
    (review.standing; wreck's spot-5, 2026-10-30), or None where it stands in none (or no floor is free)."""
    grid = plan_checks.Grid(design)
    outline = grid.covered(plan_checks.outline_of(design))
    walls_things = standing.blocked(design, inventory, grid, None)
    people = list(zip(design.get("people", []), standing.footprints(design, inventory)))
    size = standing.footprints({"people": [[0.0, 0.0]]}, inventory)[0]
    corner, east, south = place_plan.frame_of(design)

    def offset(point):
        across = np.asarray(point, dtype=float) - corner[[0, 2]]
        spot = [float(across @ east[[0, 2]]), float(across @ south[[0, 2]])]
        others = [(other, other_size) for other, other_size in people if math.dist(other[:2], spot) > 0.01]
        if not standing.stands_in(spot, size, walls_things, grid, others):
            return None
        free = standing.nearest_free(spot, size, walls_things, grid, outline, others)
        return None if free is None else (east[[0, 2]] * (free[0] - spot[0]) + south[[0, 2]] * (free[1] - spot[1]))
    return offset


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
    """(kept, left out) of the views: one `looked` marked blind, and an inside place's one whose eye stands outside
    its plan's outline (it sees its walls from behind), are left out with why."""
    outline = in_frame(design, design_shell.outline_of(design))[0] if enclosed else None
    kept, left = [], []
    for view in found:
        why = view.get("blind") or (None if outline is None or inside_polygon([view["eye"][0], view["eye"][2]], outline)
                                    else "its eye stands outside the plan's outline: it would see the walls from behind")
        if why:
            left.append({"name": view["name"], "eye": view["eye"], "from": view["from"], "why": why})
        else:
            kept.append(view)
    return kept, left


# --- places -------------------------------------------------------------------------------------------------------

def holder_of(place, plans):
    """(holder's name, its plan) of the plan that holds the place (`holds`), else (None, None)."""
    for path in sorted(pathlib.Path(plans).glob("*.json")):
        held = read(path)
        if any(hold.get("place") == place for hold in held.get("holds") or []):
            return path.stem, held
    return None, None


def leads_of(plan, design, hold=None):
    """Every place a door (the plan row's `leads`) or an opening (the kept plan's `to`) of the place leads to, each
    door's lead where its `hold` leads it (place_plan.as_held)."""
    renamed = (hold or {}).get("leads") or {}
    found = {renamed.get(door["leads"], door["leads"]) for door in plan["doors"]} | {
        opening.get("to") for opening in design.get("openings") or []}
    return sorted(name for name in found if name and name not in NOT_PLACES)


def held_design(place, design, holder):
    """(the place's plan as its own hold on its holder stands it, the name that hold stands under): its doorways
    leading where its hold leads them (place_plan.as_held: the base's airlock door to the hub, led to tube#3), and the
    name its neighbours' doors lead back to (the tube's own hold, tube#4, the one the greenhouse's and the hub's doors
    lead to; 2026-11-06: the tube's two ends met no door back, the airlock's none)."""
    own = place_plan.hold_of(holder, place)
    return (place_plan.as_held(own, design), place_plan.name_of(own)) if own else (design, place)


def origin_on_holder(design, hold):
    """The place's frame origin as a point of its holder's plan (its own plan laid in its hold, middle on middle:
    place_plan.on_holder) and its plan's floor in its frame."""
    corner, east, south = place_plan.frame_of(design)
    return place_plan.on_holder(hold, design, (-float(corner @ east), -float(corner @ south))), float(corner[1])


def unturned(hold, way):
    """A way [x, y] on the holder's plan as a way on the place's own plan, its hold's turn undone."""
    cos, sin = place_plan.turning(hold)
    return np.array([cos * way[0] + sin * way[1], -sin * way[0] + cos * way[1]])


def axes_in(design, other, hold=None, other_hold=None):
    """The other place's frame axes (rows: across, up, along) in this place's frame, both plans laid on their
    holder's plan as their holds turn them (none: unturned)."""
    _, east, south = place_plan.frame_of(design)
    _, other_east, other_south = place_plan.frame_of(other)
    found = []
    for axis in np.eye(3):
        way = [float(axis @ other_east), float(axis @ other_south)]  # on the other's plan
        on_holder = unturned({"turn": -place_plan.turn_of(other_hold or {}) % 360}, way)
        own = unturned(hold or {}, on_holder)
        found.append(east * own[0] + south * own[1] + np.array([0.0, axis[1], 0.0]))
    return np.array(found)


def stretched(other, other_hold):
    """A stretched place's scale in its own frame (scene.write_places' `scale`): its run (its plan's south) the
    hold's length over its own; None when it is laid at its own length."""
    stretch = place_plan.stretch_of(other_hold, other)
    if abs(stretch - 1.0) < 1e-6:
        return None
    _, _, south = place_plan.frame_of(other)
    return [round(1.0 + (stretch - 1.0) * abs(float(value)), 6) for value in south]


def quaternion(axes):
    """A turn (rows: the turned x, y, z axes, row vectors) as [x, y, z, w], as scene.turn reads `rotation`."""
    from pxr import Gf
    quat = Gf.Matrix3d(*np.asarray(axes, dtype=float).ravel().tolist()).ExtractRotation().GetQuat()
    return [round(value, 6) for value in (*quat.GetImaginary(), quat.GetReal())]


def sibling(place, design, holder, name, plans, why=None):
    """A place the holder's plan holds beside this one (`name`: a place, or an instance of one held several times),
    stood in this place's frame where its door leading back meets this place's door to it, else where the holder
    holds it; each at its floor's height (place_plan.levels)."""
    holds = {place_plan.name_of(hold): hold for hold in holder.get("holds") or []}
    own = place_plan.hold_of(holder, place)
    other = place_plan.as_held(holds[name], read(pathlib.Path(plans) / f"{holds[name]['place']}.json"))
    level = place_plan.levels(holder, plans)
    return stood(place, design, own, name, other, holds[name],
                 why or f"a door of {place} leads to {name}: where its door back meets it, both as high as the "
                        "holder's plan stands them (holds, levels)", level.get(place_plan.name_of(own), 0.0),
                 level.get(name, 0.0))


def stood(place, design, hold, name, other, other_hold, why, level=0.0, other_level=0.0):
    """Another place stood in this place's frame, both plans laid on the holder's plan as their holds lay them
    (place_plan.on_holder: turned, a tube stretched), this one in `hold` with its floor `level` over the holder's,
    the other in `other_hold` at `other_level` (the holder itself at its own plan's corner, at 0): moved along the
    floor so the nearest door of it leading back meets this place's door to it (place_plan.paired: the base's airlock
    opened 21.8 m off the hub's door, 2026-11-04), the hold the first guess. An instance (`tube#3`) stands its
    place's stage, stretched as its hold says (`scale`)."""
    there, other_floor = origin_on_holder(other, other_hold)
    _, floor = origin_on_holder(design, hold)
    met = [pair for pair in place_plan.paired(design, hold, place_plan.name_of(hold), other, other_hold, name)
           if pair["back"]]
    if met:  # from this place's door, along the holder's plan to the other's origin as its door back meets it
        there = there + met[0]["spot"] - met[0]["there"]
        own = np.asarray(met[0]["door"]["at"], float) + unturned(hold, there - met[0]["spot"])
    else:
        here, _ = origin_on_holder(design, hold)
        corner, east, south = place_plan.frame_of(design)
        own = np.array([-float(corner @ east), -float(corner @ south)]) + unturned(hold, there - here)
    at = place_plan.placed(design, *own)
    scale = stretched(other, other_hold)
    return {"name": name.replace(place_plan.INSTANCE, "_"), "stage": other_hold.get("place", name),
            **({"instance": name} if other_hold.get("instance") else {}),
            "at": [round(float(at[0]), 4), round(floor - other_floor + other_level - level, 4), round(float(at[2]), 4)],
            "rotation": quaternion(axes_in(design, other, hold, other_hold)), **({"scale": scale} if scale else {}),
            "from": why}


def places_of(place, plan, design, plans, handin=None):
    """Each place a door or opening of this one leads to that its holder's plan holds beside it, and each place of
    its scene a backdrop row is shown from (the hand-in's rows' `shown`, prepare/groups.shown_from): the holder
    itself, or a place it holds beside this one."""
    holder_name, holder = holder_of(place, plans)
    if holder is None:
        return []
    held = {place_plan.name_of(hold): hold["place"] for hold in holder.get("holds") or []}
    led, _ = held_design(place, design, holder)
    found = [sibling(place, led, holder, name, plans)
             for name in leads_of(plan, led, place_plan.hold_of(holder, place))
             if name in held and name != place and (pathlib.Path(plans) / f"{held[name]}.json").is_file()]
    return found + shown_places(place, design, holder_name, holder, plans, handin or {}, {entry["name"]
                                                                                          for entry in found})


def shown_places(place, design, holder_name, holder, plans, handin, stood_already):
    """The places of the scene the hand-in's backdrop rows are shown from (`shown`), not stood already: its holder
    at its own plan's corner, a place the holder holds beside this one where it holds it."""
    held = {place_plan.name_of(hold): hold for hold in holder.get("holds") or []}
    rows = {}
    for row in handin.get("rows", []):
        if row.get("shown"):
            rows.setdefault(row["shown"]["place"], []).append(row["id"])
    found = []
    for name, ids in sorted(rows.items()):
        why = f"{place} shows {', '.join(ids)} beyond it, made in {name} (its backdrop rows' `shown`)"
        if name in stood_already or name == place:
            continue
        own = place_plan.hold_of(holder, place)
        if name == holder_name:
            found.append(stood(place, design, own, name, holder, {"x": 0.0, "y": 0.0}, why,
                               place_plan.levels(holder, plans).get(place_plan.name_of(own), 0.0)))
        elif name in held and (pathlib.Path(plans) / f"{name}.json").is_file():
            found.append(sibling(place, design, holder, name, plans, why))
    return found


# --- the design's objects -----------------------------------------------------------------------------------------

def models_of(handin):
    """{row id: the model the bake makes for it}: each handed take's, `<its first row>_1` (prepare's handin.py
    surface_record names it so); a row of no handed take has none."""
    return {row: f"{first}_1" for first, entry in handin.get("objects", {}).items() for row in entry["rows"]}


def item_rows(design):
    """{plan item: the rows it lays}: each item's rows in the plan, but the walls item (WALLS_ITEM: the rows the plan
    places nowhere) none the plan also places on an item of its own, which lays it there (2026-11-06: a plan's fixes
    gave a walls row its own item and left it on the walls item too, and the record laid camp's airlock door, its dome
    windows and flat's balcony doors twice). Only an item design_objects lays at (kind `item`, as holders.items_of
    reads them) places a row so: a door-kind item is the shell's opening, its door row laid in it from the walls item
    by its relation (#128, 2026-11-16: workshop's doorway, on its DOORWAY 1 of kind door, was taken off the walls
    item and laid nowhere, and plan-matched counted it 0)."""
    tied = design.get("rows") or {}
    placed = {row for item in design.get("items") or [] if item[0] != WALLS_ITEM and
              (len(item) <= 6 or item[6] == "item") for row in tied.get(item[0]) or []}
    return {name: [row for row in rows if name != WALLS_ITEM or row not in placed] for name, rows in tied.items()}


def plan_rows(handin):
    """{shell part: [row id]} of the rows the plan's shell lays itself (route `plan`), in the hand-in's order; a
    structure row (the plan names it its own shell, groups.plan_structure) anchored on a part of the shell (a floor,
    wall or roof, SHELL_PARTS) is that part's, so its piece names it (2026-11-15 re-reading: the hub's roof windows,
    read as structure on its roof, were built by no piece of its glass dome)."""
    found = {}
    for row in handin.get("rows", []):
        if row.get("route") == "plan":
            part = row.get("part")
            if part == "structure" and row.get("anchor") in SHELL_PARTS.values():
                part = row["anchor"]
            found.setdefault(part, []).append(row["id"])
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


def spots_of(item, shape, pieces, row):
    """[(plan point, x way)] of an item's pieces: one over its box's middle turned by its facing (`item_way`); several
    evenly along its path (item_path), each its long side along it, spread across the box in lanes where it holds
    more than one of them side by side (area_lanes)."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    if pieces == 1:
        band = band_way(item, shape, row)
        return [(np.array([x + wide / 2, y + deep / 2]), item_way(item, row) if band is None else band)]
    path = item_path(item, shape)
    lanes = area_lanes(item, shape, pieces, row)
    if lanes == 1:
        return [along(path, (number + 0.5) / pieces) for number in range(pieces)]
    short = min(wide, deep)
    across = np.array([0.0, 1.0]) if wide >= deep else np.array([1.0, 0.0])
    found = []
    for number in range(pieces):
        point, way = along(path, (number + 0.5) / pieces)
        found.append((point + across * short * ((number % lanes + 0.5) / lanes - 0.5), way))
    return found


def area_lanes(item, shape, pieces, row):
    """How many lanes across its box an item's `pieces` are spread over: 1 for a polygon's outline, a row with no read
    size or a box holding one of them across (a run: a pipe, a row of crates along a wall); else as many as its
    short side holds side by side, at most as the pieces would stand on a grid the box's shape (each piece the next
    lane in turn, so two stand on its diagonal: #128, hangar's crates and garage's boxes stood in one line down the
    middle of the area the concept shows them scattered over)."""
    if pieces < 2 or (shape.get("shape") == "polygon" and len(shape.get("points") or []) >= 3) or not sized(row):
        return 1
    wide, deep = float(item[3]), float(item[4])
    fits = int(min(wide, deep) // min(float(row["size"][0]), float(row["size"][1])))
    if fits < 2:
        return 1
    return int(min(fits, pieces, max(2, round(math.sqrt(pieces * min(wide, deep) / max(wide, deep))))))


def band_way(item, shape, row):
    """The plan way a long row's one piece lays its long side along where its item's polygon is a band (its outline's
    long axis, at most BAND_SHARE as wide across), signed toward its facing's way; None otherwise. Base's connecting
    tubes, each drawn a diagonal band from its hub to a module on a square box, were laid north to south beside both
    (assembly@base, 2026-11-15)."""
    size = row["size"] if sized(row) else None
    if shape.get("shape") != "polygon" or len(shape.get("points") or []) < 3 or not size \
            or min(size[0], size[1]) > BAND_SHARE * max(size[0], size[1]):
        return None
    x, y, wide, deep = (float(value) for value in item[1:5])
    points = np.array([[x + float(across) * wide, y + float(along) * deep] for across, along in shape["points"]])
    _, axes = np.linalg.eigh(np.cov((points - points.mean(axis=0)).T))
    long_way, cross_way = axes[:, 1], axes[:, 0]
    length, across = (float(np.ptp(points @ way)) for way in (long_way, cross_way))
    if length <= 0 or across > BAND_SHARE * length:
        return None
    facing = np.asarray(FACING_WAY.get(item[5], FACING_WAY[None]), float)
    return long_way if float(long_way @ facing) >= 0 else -long_way


def item_way(item, row):
    """The plan way one piece at an item lays its long side along (yaw_turn): its facing's (FACING_WAY), turned a
    quarter onto its box's long side where its row and its box are both long on the ground (thin_straight.slender on
    their ground sides) and the facing lays the row across the box: the walkway's two 12 m ceiling ducts, each on a
    0.14 by 12 m box along the hall facing S, were laid across the hall (#36, 2026-10-31). With no facing, a row
    longer one way than the other (ELONGATED) on a box so too lies along the box: galley's 2 by 0.8 m dining table on
    its 1.1 by 2.4 m box was laid across it (the still of 2026-11-15)."""
    import score.stages.props.thin_straight as thin_straight
    way = np.asarray(FACING_WAY.get(item[5], FACING_WAY[None]), float)
    wide, deep = float(item[3]), float(item[4])
    size = row["size"] if sized(row) else None
    long = (lambda across, along: thin_straight.slender((across, along, 0.0))) if item[5] is not None else (
        lambda across, along: min(across, along) <= ELONGATED * max(across, along))
    if (size and long(float(size[0]), float(size[1])) and long(wide, deep)
            and (abs(way[0]) > abs(way[1])) != (wide > deep)):
        return np.array([-way[1], way[0]])
    return way


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
    """How many pieces an item of the row lays: its shape's count, and at least the row's own count across its items,
    what they fall short of laid one more an item in turn from the first (a run the plan draws once laid as the pieces
    prepare's groups.run_pieces makes it of). 2026-11-04: the lab's 10 pipes on 6 items laid 6, its 3 desk dividers on
    2 items laid 2."""
    counts = [int(shape.get("count") or 1) for _, shape in items]
    short = int(row.get("count") or 1) - sum(counts)
    for turn in range(max(short, 0)):
        counts[turn % len(counts)] += 1
    return counts


def counted(row, design):
    """`row` with the count the scene record lays at least (pieces_of): its own, or the number its plan's `dropped`
    says it lays where the place's floor holds no more (plan_fixes.surplus_dropped: the engine room's 4 railings of the
    8 its concept's boxes count, 2026-11-09), so no piece taken off is laid again on the items left."""
    laid = [entry["laid"] for entry in design.get("dropped") or [] if isinstance(entry, dict)
            and entry.get("item") == row["id"] and isinstance(entry.get("laid"), int)]
    return {**row, "count": min(laid)} if laid else row


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
    first, last = holders.corner_trims(design, start, end)
    ends, _ = in_frame(design, [start + run * first + reach, end - run * last + reach])
    return ends, plan_way(design, out)


FACE_WAYS = {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def related(design, relation, spot, way, base, size, piece=0):
    """(spot, x way, base, the record's `on`) of an object, the `piece`-th of its item, laid by its plan item's relation
    (score/review/holders; `pieces` one a piece): in its opening at the opening's middle and sill, along its wall;
    against a wall's face, along it, at the relation's spot (the concept's, for an item the plan writer left on the
    walls item); past the plan's edge, its face on the edge's line and its body out past it, facing in (a street's
    facade); on, within or against its holder as it was (at its piece's spot where the relation gives `spots`: street's
    three restaurant doors spread their width and room apart), its holder's objects named after (holder_names); on
    the floor at the relation's spot where it gives one (a stair at the plan's stair, a railing round its engine),
    at its `height` where it gives one (on what stands under it, never over nothing); hung between its two holders
    (`hung`) where its plan lays it, its `on` how "between" them, which the assembly hangs it from once both are laid
    (assembly/hung_between: the square's lantern strings between its buildings); a ramp at its spot, run up its
    way, its `on` the level's edge, the way up and the level's top in the place's frame. None `on` on the floor, the
    ceiling or past an edge. A piece's wall is the plan wall its chord lies on (piece_wall), so the assembly fits it
    on that wall's face, never shrunk to its chord."""
    if "pieces" in relation:
        relation = relation["pieces"][min(piece, len(relation["pieces"]) - 1)]
        if relation["how"] == "wall":
            relation = {**relation, "wall": piece_wall(design, relation["wall"])}
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
    if how == "wall":  # its front (FACING_WAY's) out into the room: its x way the run's, turned by the side it is on
        wall = relation["wall"]
        ends, out = wall_face(design, wall, relation["side"])
        along = np.subtract(wall["to"], wall["from"]) * -float(relation["side"])
        return (np.asarray(relation["spot"], float), along / max(float(np.linalg.norm(along)), 1e-9),
                float(relation.get("height", base)), {"how": "wall", "span": ends, "out": out, "why": relation["why"]})
    if how in ("top", "within", "face"):
        found = {"how": how, "holder item": relation["holder"], "why": relation["why"],
                 **({"holder row": relation["holder row"]} if relation.get("holder row") else {}),
                 **({"hangs": True} if relation.get("hangs") else {}),  # hung on its holder's back (fitting.on_back)
                 **({"under": True} if relation.get("under") else {})}  # at its holder's foot (fitting.on_holder)
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
    if how == "hung" and len(relation.get("holders") or []) == 2:  # between its two holders (assembly/hung_between)
        return spot, way, float(relation.get("height", base)), {
            "how": "between", "holder items": list(relation["holders"]),
            "holder rows": list(relation.get("holder rows") or []), "why": relation["why"]}
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
        spot, way = np.asarray(relation["spot"], float), np.asarray(relation.get("way") or way, float)
    base = float(relation.get("height", base))  # what stands under it (holders.stood_under, around_holders)
    if how == "ceiling" and relation.get("to roof") and isinstance(size, list) and len(size) == 3:
        base = roof_under(design, spot) - float(size[2]) - ROOF_CLEAR  # its top at the roof's underside over it
    return spot, way, base, None


# A wall piece's chord lies on a plan wall when it runs within this many degrees of the wall's line and its middle
# within the wall's half thickness and CHORD_ON metres of it, between its ends (piece_wall).
CHORD_TURN = 1.0
CHORD_ON = 0.02


def piece_wall(design, chord):
    """The plan wall (holders.walls_of) a wall piece's chord lies on, run the chord's way, with its own thickness; the
    chord itself where it lies on none (a chord across a round wall's facets). The holders give each piece of a row a
    face only its made length long (holders.wall_pieces); the bake lays a model by its own shape (bake_job.fit_within),
    so a model longer than that chord was shrunk to it: airlock's two 2.5 m valved pipes laid 0.7 m tall at 28% on
    3.2 m of free wall, workshop's monitors and pipes so (#128 5b, the stills of 2026-11-15)."""
    start, end = np.asarray(chord["from"], float), np.asarray(chord["to"], float)
    length = float(np.linalg.norm(end - start))
    if length < 1e-9:
        return chord
    run, middle = (end - start) / length, (start + end) / 2
    for wall in holders.walls_of(design):
        first, last = np.asarray(wall["from"], float), np.asarray(wall["to"], float)
        span = float(np.linalg.norm(last - first))
        if span < 1e-9:
            continue
        way = (last - first) / span
        if abs(float(run[0] * way[1] - run[1] * way[0])) > math.sin(math.radians(CHORD_TURN)):
            continue
        reach = float(wall.get("thick") or 0.0) / 2 + CHORD_ON
        along = float((middle - first) @ way)
        if abs(float(way[0] * (middle - first)[1] - way[1] * (middle - first)[0])) > reach or not 0.0 <= along <= span:
            continue
        if float(run @ way) < 0:
            first, last = last, first
        return {"from": [round(float(value), 4) for value in first], "to": [round(float(value), 4) for value in last],
                "thick": wall.get("thick", chord.get("thick"))}
    return chord


# A thing hung from the roof stands this far under its underside, metres: against it, never in it.
ROOF_CLEAR = 0.01


def roof_under(design, spot):
    """The underside of the place's roof over a plan spot, metres over the floor, as design_shell builds it: a slab's
    or a gable's (closed on its eave) at its eave, a shed's on its slope, a dome's on its sphere's cap, a vault's on
    its arc; the lowest of
    those over the spot; the walls' height (the place's ceiling) under none."""
    found = []
    for name, laid, _ in design_shell.pieces(design):
        for piece in laid if name.startswith("roof") else []:
            if piece["builder"] == "dome":
                reach = float(np.linalg.norm(np.subtract(spot, piece["centre"])))
                sphere = (float(piece["radius"]) ** 2 + float(piece["rise"]) ** 2) / (2 * float(piece["rise"]))
                if reach <= float(piece["radius"]):
                    found.append(float(piece["base"]) + math.sqrt(max(sphere ** 2 - reach ** 2, 0.0)) -
                                 (sphere - float(piece["rise"])))
            elif design_shell.inside(spot, piece["points"]):
                if piece["builder"] == "quad":
                    found.append(design_shell.shed_high(piece, spot))
                elif piece["builder"] == "vault":
                    arc = design_shell.piece_arc(piece)
                    across = abs(float(np.subtract(spot, arc["start"]) @ [arc["along"][1], -arc["along"][0]]))
                    found.append(arc["axis_high"] + math.sqrt(max(arc["radius"] ** 2 - across ** 2, 0.0)))
                else:
                    found.append(float(piece.get("low", piece.get("eave", 0.0))))
    return min(found) if found else float(ceiling(design) or design_shell.STOREY)


def arch_names(design, handin):
    """{plan item: [the arch entry laid at it]} of the arched rows' bands (arch_entries' names)."""
    found = {}
    for number, (row, item, _) in enumerate(design_shell.arches(design, handin.get("rows", [])), 1):
        found.setdefault(item[0], []).append(f"{row['id']}_{number}")
    return found


def holder_names(found, laid, arched=None):
    """Each object's `on` naming its holder's objects (those laid at its holder item, `laid` {item: [names]}, of its
    holder row where it names one), else the arch the record lays there (`arched`, under Structure: a tube's rib), one
    hung between two holder items (`holder items`) the first object of each; one whose holder item laid neither
    keeps no `on` and says so."""
    rows = {entry["name"]: entry["row"] for entry in found}
    for entry in found:
        if "beside" in entry:  # a seat before its holder (holders' `beside`): its holder's objects named
            entry["beside"]["holder"] = [name for name in laid.get(entry["beside"]["holder item"]) or []
                                         if rows.get(name) == entry["beside"]["holder row"]]
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
        if on and "holder items" in on:  # hung between two holders: each one's object
            names = [[name for name in laid.get(item) or [] if rows.get(name) == row]
                     for item, row in zip(on["holder items"], on["holder rows"])]
            if all(names):
                on["holder"] = [of_item[0] for of_item in names]
            else:
                entry.pop("on")
                entry["unheld"] = f"of the holder items {' and '.join(on['holder items'])} it hangs between, " \
                                  "one lays no object"
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
    at the floor under it stays there. A spot in a pit sunk in the floor (design_shell.pits, levels_of: the hub's
    2.33 m pit 0.9 m down) stands on the pit's floor (#128: the hub's cables and monitors in its pit stood over it on
    nothing), never a piece at an item outlining the room (design_objects)."""
    levels = design_shell.levels_of(design, design_shell.outline_of(design))
    sunk = [float(levels[low]["height"]) for low in design_shell.pits(levels)
            if design_shell.inside(spot, levels[low]["points"])]
    if sunk:
        return min(sunk)
    return max([0.0] + [float(level["height"]) for level in design.get("levels") or []
                        if len(level.get("points") or []) >= 3 and
                        0.0 < float(level.get("height") or 0.0) <= design_shell.SLAB + DECK_BELOW and
                        design_shell.inside(spot, level["points"])])


def floor_lift(design, spot, base):
    """The height a piece with its shape's `base` stands at on a plan spot: its base, lifted onto the highest level
    lying on the floor (a deck at most a slab and its gap high, the ground under the place too) whose outline holds
    the spot where its base is below that level's top (settle@airlock, checkout 67: its sandbags' -0.2 m ground base
    laid them inside the 0 m floor and 0.1 m locker decks, buried with their faces flush), else its base."""
    return max([base] + [float(level.get("height") or 0.0) for level in design.get("levels") or []
                         if len(level.get("points") or []) >= 3 and
                         float(level.get("height") or 0.0) <= design_shell.SLAB + DECK_BELOW and
                         design_shell.inside(spot, level["points"])])


def design_objects(design, handin, relations=None):
    """Every object of the design: one at each plan item (more where the item counts several, or a run the plan
    draws once) for each prop or shell row the item names, `<row>_<n>` the n-th of its row, standing on its plan spot
    as high as its shape's base, turned along its item (a long row along the band its polygon draws, band_way; a
    passage against its wall run out through it, never along it: workshop's glass tunnels), waiting on the bake's model of its row (made_waiting lays it
    once baked; one the bake never makes stays named on the stage's root). A row marked `far` is laid far off by
    far_objects alone, never at an item its plan laid it at too (the street's distant floodlights, laid at its end). A
    row on the ground the plan lays only against its edge (floor_fit.past_edge) stands past it (past_edge_spot), never
    centred on its edge strip over the floor (2026-10-26: the square's 30 m buildings on 2 to 7 m strips). An item's
    relation (`relations`, score/review/holders: in an opening, against a wall, on, within or against a holder) is
    carried as the object's `on`, which the assembly lays it by at its built size (assembly/made_waiting.fitted), one
    against a holder much thinner than it marked `below`, hung under it (thin_holder: a lantern on its string), and
    how it rests there as its `rests` (leaning, attached: holders.rests), which the settle leans it or holds it by."""
    by_id = {row["id"]: row for row in handin.get("rows", [])}
    models, shapes, tied = models_of(handin), design.get("shapes") or {}, item_rows(design)
    flown = set(flown_rows(design, handin).values())  # laid at the plan's flights alone (flight_objects)
    items = {}
    for item in design.get("items") or []:
        if len(item) > 6 and item[6] != "item":
            continue
        for row_id in tied.get(item[0]) or []:
            if row_id in by_id and by_id[row_id].get("route", "prop") in LAID_ROUTES and not by_id[row_id].get("far") \
                    and row_id not in flown:
                items.setdefault(row_id, []).append((item, shapes.get(item[0]) or {}))
    found, edged, holding, laid_at = [], floor_fit.past_edge(design, handin), relations_of(relations), {}
    unheld = {(entry["item"], entry["row"]): entry["why"] for entry in (relations or {}).get("unheld", [])}
    for row_id, laid in items.items():
        row, model = by_id[row_id], models.get(row_id)
        size = by_id.get(model.removesuffix("_1"), row).get("size") if model else row.get("size")
        number = 0
        for (item, shape), pieces in zip(laid, pieces_of(counted(row, design), laid)):
            base = float(shape.get("base") or 0.0)
            relation, on = holding.get((item[0], row_id)), None
            marked = marks(item, row, relation, unheld.get((item[0], row_id)))
            for piece, (spot, way) in enumerate(spots_of(item, shape, pieces, row)):
                if row_id in edged:
                    spot, way = past_edge_spot(item, design, spot, size)
                height = floor_lift(design, spot, base) if base else deck_height(design, spot)
                if holders.outlines_room(item, design):
                    height = max(0.0, height)  # its middle says nothing of where it is: never down a pit there
                if relation:
                    spot, way, height, on = related(design, relation, spot, way, height, size, piece)
                if on and on["how"] == "wall" and plan_checks.connector(row):
                    way = np.array([-way[1], way[0]])  # a passage runs out through its wall, never along it
                if on and on["how"] == "face" and thin_holder(size, row_size(by_id, models, on.get("holder row"))):
                    on = {**on, "below": True}  # hung under it (fitting.hung_under), never against its side
                number += 1
                (point,), floor = in_frame(design, [spot], height)
                found.append({"name": f"{row_id}_{number}", "row": row_id, "bake": model, "kind": "object",
                              "at": [point[0], floor, point[1]], "rotation": yaw_turn(design, way, size),
                              "waiting": waits(row, model, by_id),
                              "from": f"plan item {item[0]!r}, inventory row {row_id}: piece {number} of the row, "
                                      f"{height:g} m over the floor", **({"on": dict(on)} if on else {}), **marked,
                              **({"beside": {"holder item": relation["beside"], "holder row": relation["holder row"]}}
                                 if relation and relation.get("beside") else {}),
                              **({"under roof": True} if relation and relation.get("to roof") and sized(
                                  {"size": size}) else {}),
                              **({"rests": relation["rests"]} if relation and relation.get("rests") else {})})
                laid_at.setdefault(item[0], []).append(found[-1]["name"])
    flights_named(design, handin, found)
    found += flight_objects(design, handin)
    hung_along(found)
    return holder_names(found, laid_at, arch_names(design, handin))


def hung_along(found):
    """Each object of `found` hung `below` a thin holder (thin_holder) given its `along`, (k + 0.5) / n: the share of
    the way along its holder's run it hangs at (fitting.hung_under), the k-th of the n the record hangs under the same
    holder item, in its order, so they hang spread along it. Street's lanterns stand 13 to 20 m from their string on
    the plan, so where on the string each hangs is the record's to say (2026-11-11)."""
    under = {}
    for entry in found:
        if (entry.get("on") or {}).get("below"):
            under.setdefault(entry["on"]["holder item"], []).append(entry["on"])
    for hung in under.values():
        for number, on in enumerate(hung):
            on["along"] = round((number + 0.5) / len(hung), 4)


# A holder whose height and narrower side across the floor are each at most this share of the smallest side of a thing
# laid against it is much thinner than the thing, which hangs under it (thin_holder).
THIN_SHARE = 0.25


def row_size(by_id, models, row_id):
    """A hand-in row's size as its objects are laid at: its model's row's (`models`, models_of), else its own; None
    for a row the hand-in has not."""
    row, model = by_id.get(row_id), models.get(row_id)
    if row is None:
        return None
    return by_id.get(model.removesuffix("_1"), row).get("size") if model else row.get("size")


def thin_holder(size, holder_size):
    """Whether a holder of `holder_size` ([across, deep, tall]) is much thinner than a thing of `size` laid against its
    side: its height and its narrower side across the floor each at most THIN_SHARE of the thing's smallest side (a
    0.4 m lantern on its 1 cm string). Such a thing hangs under it at its own size; laid against the string's side,
    street's red paper lanterns were shrunk to 16% and 2% of their size to fit its 1 cm height (2026-11-11)."""
    if not (sized({"size": size}) and sized({"size": holder_size})):
        return False
    thick = max(float(holder_size[2]), min(float(holder_size[0]), float(holder_size[1])))
    return thick <= THIN_SHARE * min(float(side) for side in size)


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
    design = design_shell.glazed(design_shell.cut_for(design, handin.get("rows", []), relations),
                                 handin.get("rows", []))
    far_laid = far_objects(design, handin, inputs.get("inventory"))
    own = row_entries(design, place, library_of(inputs), handin)
    record = {"place": place,
              "about": f"{plan['title']}, written by SCORE's scene-record stage from its design: its locked plan, "
                       "its scene inventory's row kinds, the library's lamp and the environment concept's physics at "
                       "its site. Frame: the plan's (x east, z south, y up over its floor).",
              "floor": plan["floor"], "inside": inside(design),
              "structure": structure(plan, design, library_of(inputs), {
                  part: [row_id for row_id in ids if row_id not in {entry["row"] for entry in own}]
                  for part, ids in plan_rows(handin).items()}, handin) +
              arch_entries(design, plan["place"], library_of(inputs), handin) + own +
              kit_entries(design, place, library_of(inputs), handin),
              "objects": design_objects(design, handin, relations) + far_laid[0],
              "lights": lights(design, inputs, relations), "environment": environment(design, read(inputs["sky"]), read(inputs["dust"])),
              "doorways": plan.get("doorways", []), "places": places_of(place, plan, design, inputs["plans"], handin)}
    ground = None if record["inside"] else ground_under(inputs, place)
    inventory = pathlib.Path(inputs.get("inventory") or "")
    rows = read(inventory) if inventory.is_file() else {}
    sight = sight_of(design, rows)
    concept = concept_view(design, rows, eye, record["inside"], ground, sight)
    record["views"], left_out = views_inside(
        ([concept] if concept else []) + views(plan if record["inside"] else dict(plan, doorways=[]), eye, ground,
                                               clear_of(design, rows), sight), design, record["inside"])
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
