"""The kit layout of a vehicle bay, the garage or the hangar (job place, 2026-10-07): room_kit.py's rounded room with
what a bay needs on top of it.

    python3 tools/props/scene/bay_kit.py <room> <out.json>             # the room
    python3 tools/props/scene/bay_kit.py <room> <out.json> --leaf      # one leaf of its big door, in the leaf's frame

The room's numbers are its inventory's `room.layout`, as room_kit.py reads them, plus:
- `bands`: the tops of the wall's bands of panels from the floor up (the lowest band is the lower panels, every other
  the upper ones), for walls taller than the two bands room_kit lays: the hangar's walls are 13 m;
- `big_door`: the wall the big door is in and its opening (`wide`, `high`): a doorway wider and taller than a tube
  hatch's, the wall's panels standing beside it and above it, its frame round it; its leaves are the game's moving
  node, drawn from a kit of their own (`--leaf`);
- `roof`: "flat" for a flat roof at the wall's top, lined with plates outside the roof door's `opening` (wide across,
  long along, centred on the floor); its leaves are the game's moving node too. A domed room (the garage) keeps
  room_kit's dome.
- `posts`: how far apart the posts standing up the walls are (the hangar's walls are framed), and `rails`: the bridge
  crane's two rails along the long walls, at a height (`high`), with its bridge of two girders on them where it is
  `parked` (along), `gauge` metres apart, the trolley's row standing on them.

Frame and pieces as room_kit.py's: the room's middle on its floor, x east, z south, y up; every piece a kind of the
inventory (`<room>_<id>`), its origin, axes and laid size. The route (tools/props/library/route.py) makes the models.
A leaf's frame: its middle on its foot (a wall leaf) or its middle (a roof leaf), its front toward -z, which is into
the room.
"""
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hub_kit  # noqa: E402
import room_kit  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
# How far apart the plates of a flat roof and a door leaf are laid, at most.
ROOF_PLATE = 2.4
LEAF_PLATE = 1.25
# A leaf's ribs: how far apart, how wide and how far they stand out of its plates.
LEAF_RIB_EVERY = 2.0
# How high a frame's header stands over the opening it is round, and how wide its posts are, as the hub's door kit.
FRAME_POSTS = room_kit.FRAME_POSTS
FRAME_HEADER = room_kit.FRAME_HEADER
# A tube hatch's doorway and frame top, over which a tall wall's panels carry on up.
DOORWAY = room_kit.DOORWAY
HATCH_TOP = DOORWAY[1] + FRAME_HEADER


def wall_runs(side, layout):
    """A wall's runs of panels as (middle along the wall, length, foot, top): beside a tube hatch's or the big door's
    doorway from the floor, over it from its frame's top; the whole wall when it has no doorway."""
    length = float(np.linalg.norm(side["end"] - side["start"]))
    top = layout["wall"]
    big = layout.get("big_door", {})
    if side["main"] and big.get("wall") == side["name"]:
        gap, high = big["wide"] + FRAME_POSTS, big["high"] + FRAME_HEADER
    elif side["main"] and side["name"] in layout["doors"]:
        gap, high = DOORWAY[0] + FRAME_POSTS, HATCH_TOP
    else:
        return [(0.0, length, 0.0, top)]
    beside = (length - gap) / 2
    runs = [(-length / 2 + beside / 2, beside, 0.0, top), (length / 2 - beside / 2, beside, 0.0, top)]
    if top - high > 0.05:
        runs.append((0.0, gap, high, top))
    return runs


def band_spans(bands, foot, top):
    """The bands of a run from `foot` to `top`, as (kind, bottom, height): the lowest band's lower panels, then the
    upper panels, cut where the run starts and ends."""
    found = []
    bottom = 0.0
    for index, band_top in enumerate(bands):
        low, high = max(bottom, foot), min(band_top, top)
        if high - low > 0.05:
            found.append(("wall_lower_plain" if index == 0 else "wall_upper_plain", low, high - low))
        bottom = band_top
    return found


def walls(room, layout, kinds):
    """Every wall's panels band by band round its doorways, its skirting where it meets the floor and its cornice."""
    found = []
    bands = layout.get("bands", [room_kit.LOWER, layout["wall"]])
    for side in room_kit.sides(layout):
        for middle, run, foot, top in wall_runs(side, layout):
            count = max(1, round(run / room_kit.PANEL))
            wide = run / count
            for kind, bottom, high in band_spans(bands, foot, top):
                lap = room_kit.BAND_LAP if kind == "wall_lower_plain" else 0.0
                deep = room_kit.size_of(kinds, kind)[2]
                for index in range(count):
                    across = middle - run / 2 + wide * (index + 0.5)
                    found.append(room_kit.on_side(room, kind, side, across, bottom,
                                                  (wide + room_kit.LAP, high + lap, deep)))
            if foot == 0.0:
                skirting = room_kit.size_of(kinds, "wall_skirting")
                found.append(room_kit.on_side(room, "wall_skirting", side, middle, 0.0, (run, skirting[1], skirting[2]),
                                              out=room_kit.size_of(kinds, "wall_lower_plain")[2]))
        length = float(np.linalg.norm(side["end"] - side["start"]))
        cornice = room_kit.size_of(kinds, "wall_cornice")
        found.append(room_kit.on_side(room, "wall_cornice", side, 0.0, layout["wall"] - cornice[1],
                                      (length + room_kit.LAP, cornice[1], cornice[2])))
    return found


def big_doorways(layout):
    """The big door's opening for the door check (gates/doors.py), which the kit lays no leaf in (its leaves are the
    game's moving node, shut whenever the room holds air): its middle on the floor in the wall, its outward normal,
    its width and height."""
    big = layout.get("big_door")
    if not big:
        return []
    side = room_kit.side_named(layout, big["wall"])
    middle = (side["start"] + side["end"]) / 2 + side["outward"] * room_kit.SHELL_WALL / 2
    return [{"at": [round(float(middle[0]), 4), 0.0, round(float(middle[1]), 4)],
             "normal": [round(float(side["outward"][0]), 5), 0.0, round(float(side["outward"][1]), 5)],
             "wide": big["wide"] + FRAME_POSTS, "tall": big["high"], "deep": room_kit.SHELL_WALL + 0.2}]


def big_door_frame(room, layout, kinds):
    """The big door's frame round its opening: a post either side of it and a header across its top, of the posts'
    plain steel (the CODE-BUILT LIMIT: code builds plain plates, pipes and trims only)."""
    big = layout.get("big_door")
    if not big:
        return []
    side = room_kit.side_named(layout, big["wall"])
    post = room_kit.size_of(kinds, "wall_corner_post")
    behind = room_kit.size_of(kinds, "wall_lower_plain")[2]
    found = [room_kit.on_side(room, "wall_corner_post", side, sign * (big["wide"] / 2 + post[0] / 2), 0.0,
                              (post[0], big["high"] + post[0], post[2]), out=behind) for sign in (-1, 1)]
    found.append(room_kit.on_side(room, "wall_corner_post", side, 0.0, big["high"],
                                  (big["wide"], post[0], post[2]), out=behind))
    return found


def breaks(half, reach, opening):
    """Where a flat roof's cells are cut along one axis: its walls, where the rounded corners end and the opening's
    edges, in order."""
    found = {-half, half, -(half - reach), half - reach}
    if opening:
        found |= {-opening / 2, opening / 2}
    return sorted(found)


def in_corner(low, high, half, reach):
    """Whether a cell lies in one of the rounded corners' squares (which the fans line instead)."""
    middle = (np.asarray(low) + np.asarray(high)) / 2
    return bool(np.all(np.abs(middle) > half - reach))


def flat_roof(room, layout, kinds):
    """A flat roof lined with plates under it at the wall's top: the room's cross in cells cut at the corners and the
    roof door's opening (left open), each cell in plates about ROOF_PLATE across, and each rounded corner a fan of
    triangles to its middle, as room_kit lines the floor."""
    found = []
    deep = room_kit.size_of(kinds, "roof_face_panel")[2]
    high = layout["wall"]
    half = np.asarray(layout["inside"], dtype=np.float64) / 2
    reach = layout["corner"]
    opening = layout.get("opening", [0.0, 0.0])
    across_cuts = breaks(half[0], reach, opening[0])
    along_cuts = breaks(half[1], reach, opening[1])
    # Front down into the room (z up), height along +z (south): x runs west so the frame is right-handed (a mirrored
    # frame draws its faces inside out).
    down = (np.array([-1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0]))
    for low_x, high_x in zip(across_cuts, across_cuts[1:]):
        for low_z, high_z in zip(along_cuts, along_cuts[1:]):
            low, high_corner = (low_x, low_z), (high_x, high_z)
            if in_corner(low, high_corner, half, reach):
                continue
            middle = (np.asarray(low) + np.asarray(high_corner)) / 2
            if np.all(np.abs(middle) < np.asarray(opening) / 2):
                continue
            size = np.asarray(high_corner) - np.asarray(low)
            counts = [max(1, round(value / ROOF_PLATE)) for value in size]
            cell = size / counts
            for across in range(counts[0]):
                for along in range(counts[1]):
                    corner = np.asarray(low) + cell * np.array([across, along])
                    origin = np.array([corner[0] + cell[0] / 2, high - deep / 2, corner[1]])
                    laid = room_kit.piece(room, "roof_face_panel", origin, down, (cell[0], cell[1], deep),
                                          room_kit.ROOF_LAYER)
                    laid["taper"] = 1.0
                    found.append(laid)
    for signs in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        middle = np.array(signs) * (half - reach)
        for step in range(room_kit.CORNER_STEPS):
            angles = [math.pi / 2 * step / room_kit.CORNER_STEPS, math.pi / 2 * (step + 1) / room_kit.CORNER_STEPS]
            ends = [middle + np.array(signs) * np.array([math.sin(angle), math.cos(angle)]) * reach for angle in angles]
            chord_middle = (ends[0] + ends[1]) / 2
            toward = middle - chord_middle
            tall = float(np.linalg.norm(toward))
            toward /= tall
            y = np.array([toward[0], 0.0, toward[1]])
            z = np.array([0.0, 1.0, 0.0])  # its front down into the room
            laid = room_kit.piece(room, "roof_face_panel", np.array([chord_middle[0], high - deep / 2, chord_middle[1]]),
                                  (np.cross(y, z), y, z), (float(np.linalg.norm(ends[1] - ends[0])), tall, deep),
                                  room_kit.ROOF_LAYER)
            laid["taper"] = 0.0
            found.append(laid)
    return found


def bar(room, kind, start, end, size, layer=1):
    """A straight trim from one point to another (a post, a rail, a rib), its length along its x, `size` its other two
    sides (tall up, deep along its z)."""
    start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
    along = end - start
    length = float(np.linalg.norm(along))
    along /= length
    helper = np.array([0.0, 1.0, 0.0]) if abs(along[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    z = np.cross(along, helper)
    z /= np.linalg.norm(z)
    y = np.cross(z, along)
    tall, deep = size
    origin = (start + end) / 2 - y * tall / 2
    return room_kit.piece(room, kind, origin, (along, y, z), (length, tall, deep), layer)


def posts(room, layout, kinds):
    """Posts standing up the long straight walls every `posts` metres, clear of the doorways, on the panels."""
    every = layout.get("posts")
    if not every:
        return []
    post = room_kit.size_of(kinds, "wall_corner_post")
    found = []
    for side in room_kit.sides(layout):
        if not side["main"]:
            continue
        length = float(np.linalg.norm(side["end"] - side["start"]))
        count = int(length // every)
        doorway = 0.0
        if side["name"] in layout["doors"]:
            doorway = DOORWAY[0] + FRAME_POSTS
        if layout.get("big_door", {}).get("wall") == side["name"]:
            doorway = layout["big_door"]["wide"] + FRAME_POSTS
        for index in range(count + 1):
            across = -length / 2 + length * index / max(count, 1)
            if abs(across) < doorway / 2 + post[0] or abs(across) > length / 2 - 0.05:
                continue
            behind = room_kit.size_of(kinds, "wall_upper_plain")[2]
            found.append(room_kit.on_side(room, "wall_corner_post", side, across, 0.0,
                                          (post[0], layout["wall"], post[2]), out=behind))
    return found


def rails(room, layout, kinds):
    """The bridge crane's two rails along the long walls (east and west) at their height, standing off the posts, and
    the crane's bridge across the room between them where the inventory parks it (`rails.parked`, along): two girders
    lying on the rails' tops, `rails.gauge` metres apart middle to middle, for the trolley's wheels to run on."""
    spec = layout.get("rails")
    if not spec:
        return []
    rib = room_kit.size_of(kinds, "lattice_ring_rib")
    half = np.asarray(layout["inside"], dtype=np.float64) / 2
    reach = layout["corner"]
    standoff = room_kit.size_of(kinds, "wall_upper_plain")[2] + room_kit.size_of(kinds, "wall_corner_post")[2] + rib[2] / 2
    found = []
    for sign in (-1, 1):
        x = sign * (half[0] - standoff)
        found.append(bar(room, "lattice_ring_rib", (x, spec["high"], -(half[1] - reach)), (x, spec["high"], half[1] - reach),
                         (rib[1], rib[2]), room_kit.ROOF_LAYER))
    span = half[0] - standoff
    girder = (rib[1] * 1.6, rib[2] * 1.6)
    middle = spec["high"] + rib[1] / 2 + girder[0] / 2
    for sign in (-1, 1):
        along = spec.get("parked", 0.0) + sign * spec["gauge"] / 2
        found.append(bar(room, "lattice_ring_rib", (-span, middle, along), (span, middle, along), girder,
                         room_kit.ROOF_LAYER))
    return found


def beam(room, layout, kinds):
    """One overhead beam from point to point (the garage's hoist rail over the lift), on the roof's layer."""
    spec = layout.get("rail")
    if not spec:
        return []
    rib = room_kit.size_of(kinds, "lattice_ring_rib")
    return [bar(room, "lattice_ring_rib", spec["from"], spec["to"], (rib[1], rib[2]), room_kit.ROOF_LAYER)]


def laid_out(room, inventory):
    """Every piece of the room: room_kit's floor, hatches and rows, with a bay's walls, big door, roof and frame."""
    layout = inventory["room"]["layout"]
    kinds = {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}
    found = walls(room, layout, kinds) + room_kit.floor(room, layout, kinds) + room_kit.doors(room, layout, kinds)
    found += big_door_frame(room, layout, kinds)
    if layout.get("roof") == "flat":
        found += flat_roof(room, layout, kinds)
    elif layout.get("rise"):
        found += room_kit.roof(room, layout, kinds)
    found += posts(room, layout, kinds) + rails(room, layout, kinds) + beam(room, layout, kinds)
    found += room_kit.placed_rows(room, layout, kinds, inventory) + room_kit.flat_rows(room, inventory, kinds)
    found += room_kit.pipe_brackets(room, kinds, found) + room_kit.under_floor(room, kinds, found)
    found = hub_kit.split_at_fittings(found)
    # A machine bay's plate is wider than the deck plates it is set into: those wholly under it are left out.
    return [laid for laid in room_kit.cut_openings(room, found + room_kit.children(room, found))
            if not room_kit.covered(laid)]


def leaf(inventory):
    """One leaf of the big door in its own frame: plates over its face and ribs across it, its front into the room.
    A wall leaf stands on its foot's middle; a roof leaf lies on its middle, its front down. Its pieces are kinds of
    the leaf's own kit (`leaf.kit`, a name with no underscore, so each kind keeps its plain builder's name: the game
    draws the leaf from that kit, moving with the door)."""
    layout = inventory["room"]["layout"]
    kinds = {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}
    spec = layout["leaf"]
    room = spec["kit"]
    wide, long = spec["size"]
    deep = room_kit.size_of(kinds, "wall_upper_plain")[2]
    rib = room_kit.size_of(kinds, "lattice_ring_rib")
    lying = spec.get("lies") == "roof"
    if lying:
        # x across the leaf (west, so the frame is right-handed), y along it (its length), z up: its front, -z,
        # faces down into the room.
        axes = (np.array([-1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0]))
    else:
        axes = (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    x_axis, y_axis, z_axis = axes
    counts = [max(1, round(wide / LEAF_PLATE)), max(1, round(long / LEAF_PLATE))]
    cell = (wide / counts[0], long / counts[1])
    start = -long / 2 if lying else 0.0
    found = []
    for across in range(counts[0]):
        for along in range(counts[1]):
            middle = x_axis * (-wide / 2 + cell[0] * (across + 0.5)) + y_axis * (start + cell[1] * along)
            laid = room_kit.piece(room, "wall_upper_plain", middle, axes, (cell[0] + room_kit.LAP, cell[1], deep))
            found.append(laid)
    ribs = max(2, round(long / LEAF_RIB_EVERY) + 1)
    face = -z_axis * (deep / 2 + rib[2] / 2)
    for index in range(ribs):
        along = start + (long - rib[1]) * index / (ribs - 1)
        middle = y_axis * along + face
        found.append(room_kit.piece(room, "lattice_ring_rib", middle - x_axis * 0.0, axes, (wide, rib[1], rib[2])))
    return found


def leaf_kinds(inventory):
    """A leaf kit's kinds, as the room's kinds table has them: plates and ribs, both hanging from the door."""
    kit = inventory["room"]["layout"]["leaf"]["kit"]
    return {f"{kit}_{own}": {"group": "hangs"} for own in ("wall_upper_plain", "lattice_ring_rib")}


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    room = sys.argv[1]
    inventory = json.loads((REPO / f"data/inventory/{room}.json").read_text())
    is_leaf = sys.argv[3:] == ["--leaf"]
    pieces = leaf(inventory) if is_leaf else laid_out(room, inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    frame = ("the leaf's own: its middle on its foot (a roof leaf: its middle), x across, front -z into the room"
             if is_leaf else "the room's own: its middle on its floor, x east, z south, y up")
    pathlib.Path(sys.argv[2]).write_text(json.dumps(
        {"room": inventory["room"]["layout"]["leaf"]["kit"] if is_leaf else room, "frame": frame, "counts": counts,
         "kinds": leaf_kinds(inventory) if is_leaf else room_kit.kinds_table(room, inventory), "pieces": pieces,
         "doorways": [] if is_leaf else big_doorways(inventory["room"]["layout"])}, indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")


if __name__ == "__main__":
    main()
