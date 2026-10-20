"""The scene inventory rows a place's stage has nothing made for, and where each one's box goes. No position is
ever made up: a box stands only where the inventory, the kit or the made parent says.

    inventory = rows.inventory(data, place)          # the place's scene inventory, or None
    missing = rows.missing(stage, place, inventory)   # the rows the completion gate's own rule finds unmade
    boxes = rows.boxes(stage, place, inventory, kit, missing)   # one a row's object, parents before children

Which rows are missing is tools/usd/complete.py's rule (`unlaid_rows`: not laid, not dropped, not held back), over
the rows of the place's own objects on its accepted stage (none when it has none; never a shown place's, under
/<place>/Places). A row's objects are named as export.object_names names them (`<row>_<n>`, the n-th of its row) and
placed by the first rule that applies:

    spot      a floor or ceiling spot: the inventory's x and z, else the kit's pieces of the row (plan.row_spots);
              the foot at the spot's y, else on the floor at 0 (a ceiling row with no y has no height: unplaced),
              turned about up by `facing` as export.turn_in_seat turns it (a kit piece by its own axes); on a place
              with ground, stood as export.stand_on stands it: on the ground under its spot, lifted by that y and
              turned with its seat
    wall      a wall spot (`wall`, `across`, `bottom`): room_kit.on_side over the inventory's room
    on        a row anchored `on:<parent>`: every object at the middle of the parent's top (the inventory gives no
              layout on it); on the made parent's world box, or nested under the parent's own box when the parent is
              missing too
    unplaced  anything else: no transform, no box in space
"""
import json
import math
import pathlib
import sys

import numpy as np

from score.stages.complete.gaps import layer
from score.stages.scene_record import plan as plans

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on the path by the complete stage's import
import complete  # noqa: E402
import ground as grounds  # noqa: E402

SPOT, WALL, ON, UNPLACED = "spot", "wall", "on", "unplaced"


def inventory(data, place):
    """The place's scene inventory (its plan's `inventory` name, the prologue's rooms', else the place's own), or
    None when it has none."""
    plan = pathlib.Path(data) / "plans" / f"{place}.json"
    name = json.loads(plan.read_text()).get("inventory", place) if plan.exists() else place
    path = pathlib.Path(data) / "inventory" / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def made_objects(stage, place):
    """{row: [prim path]} of the place's own made objects (score:row) on the stage, never a shown place's (its
    children under /<place>/Places are not walked); {} with no stage."""
    found = {}
    if stage is None:
        return found
    shown = f"/{place}/Places"
    walk = iter(stage.Traverse())
    for prim in walk:
        if str(prim.GetPath()) == shown:
            walk.PruneChildren()
        elif prim.HasAttribute("score:row"):
            found.setdefault(prim.GetAttribute("score:row").Get(), []).append(str(prim.GetPath()))
    return found


def missing(stage, place, written):
    """The inventory's rows with nothing of the place's own made for them on the stage (every row, with no stage),
    in its order."""
    if written is None:
        return []
    unlaid = {fault["row"] for fault in complete.unlaid_rows(written, set(made_objects(stage, place)))}
    return [row for row in written["rows"] if row["id"] in unlaid]


def parent_of(row):
    """The row a row stands on (`on:<row>`), or None."""
    anchor = str(row.get("anchor", ""))
    return anchor.split(":", 1)[1] if anchor.startswith("on:") else None


def turned(facing):
    """The axes (x, y, z) of a thing turned `facing` degrees about up, as export.turn_in_seat turns it."""
    angle = math.radians(-float(facing))
    return [[math.cos(angle), 0.0, -math.sin(angle)], [0.0, 1.0, 0.0], [math.sin(angle), 0.0, math.cos(angle)]]


def foot_height(row, given):
    """Where a spot's foot stands: its own y, else 0 on the floor; None when nothing says."""
    if given is not None:
        return float(given)
    return 0.0 if row.get("anchor") == "floor" else None


def kit_pieces(row, kit):
    """The kit's pieces of a row (a kind `<room>_<row>`, its parts left out), as plan.row_spots reads them."""
    kind = f"{kit.get('room')}_{row['id']}"
    return [piece for piece in kit.get("pieces", []) if "part" not in piece and piece["kind"] == kind]


def stood(across, height, along, axes, ground):
    """A spot's frame {origin, axes}: at (across, height, along) on a flat place; on a place with ground, as
    export.stand_on stands it: on the ground under (across, along) lifted by `height`, its own axes turned with the
    seat after (as the transform ops apply them)."""
    if ground is None:
        return {"origin": [across, height, along], "axes": axes}
    position, seat_turn = ground.standing(float(across), float(along), float(height))
    return {"origin": [float(value) for value in position],
            "axes": (np.asarray(axes, dtype=float) @ np.asarray(seat_turn, dtype=float)).tolist()}


def floor_spots(row, kit, spots, ground):
    """The row's floor or ceiling spots as frames {origin, axes}, or None for one with no height; `spots` its (x, z)
    from plan.row_spots, in the same order as the inventory's or the kit's own; `ground` the place's, or None."""
    given = [spot for spot in row.get("at", []) if "x" in spot]
    if given:
        return [None if foot_height(row, spot.get("y")) is None else
                stood(across, foot_height(row, spot.get("y")), along, turned(spot.get("facing", 0.0)), ground)
                for (across, along), spot in zip(spots, given)]
    return [stood(across, float(piece["at"][1]), along, [piece["x"], piece["y"], piece["z"]], ground)
            for (across, along), piece in zip(spots, kit_pieces(row, kit))]


def wall_spots(row, room):
    """The row's wall spots as frames {origin, axes} against the room's walls (room_kit.on_side), or None for a
    spot on a wall the room's layout does not have (a faceted or outdoor place's)."""
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import room_kit
    layout = room.get("layout", {})
    walls = {side["name"]: side for side in room_kit.sides(layout)} if "inside" in layout and "corner" in layout else {}
    wide, deep, tall = row["size"]
    found = []
    for spot in row.get("at", []):
        if "wall" not in spot:
            continue
        side = walls.get(spot["wall"])
        laid = side and room_kit.on_side(room.get("name", ""), row["id"], side, float(spot["across"]),
                                         float(spot["bottom"]), (wide, tall, deep), out=float(spot.get("out", 0.0)))
        found.append({"origin": laid["at"], "axes": [laid["x"], laid["y"], laid["z"]]} if laid else None)
    return found


def frames(row, kit, room, spots, ground):
    """[(placed, frame or None)] for each object of a row that does not stand on another: its spots, then its wall
    spots; its count unplaced when it has neither."""
    found = [(SPOT, frame) for frame in floor_spots(row, kit, spots.get(row["id"], []), ground)]
    found += [(WALL, frame) for frame in wall_spots(row, room)]
    if not found:
        return [(UNPLACED, None)] * max(1, int(row.get("count", 1)))
    return [(placed if frame else UNPLACED, frame) for placed, frame in found]


def parent_top(stage, made, parent):
    """The made parent's world box top as (middle x, top y, middle z), from its first object; None when the place
    has no object of it (`made`: made_objects) or its box is empty."""
    paths = sorted(made.get(parent, []))
    if not paths:
        return None
    low, high = layer.bounds(stage, paths[0], layer.SEEN)
    if low is None:
        return None
    return [(low[0] + high[0]) / 2, high[1], (low[2] + high[2]) / 2]


def on_frames(row, top, nested):
    """The objects of a row standing on its parent, each at the middle of its top: the made parent's (`top`), the
    missing parent's own box (`nested`: (its path, its height), its frame its own), or unplaced."""
    count = max(1, int(row.get("count", 1)))
    if top is not None:
        return [(ON, {"origin": list(top), "axes": turned(0.0)}, None)] * count
    if nested is not None and nested[1] is not None:
        return [(ON, {"origin": [0.0, nested[1], 0.0], "axes": turned(0.0)}, nested[0])] * count
    return [(UNPLACED, None, nested[0] if nested else None)] * count


def ordered(rows):
    """The missing rows with each parent before the rows on it."""
    ids = {row["id"] for row in rows}
    done, found = set(), []
    while len(found) < len(rows):
        ready = [row for row in rows if row["id"] not in done
                 and (parent_of(row) not in ids or parent_of(row) in done or parent_of(row) == row["id"])]
        if not ready:
            raise ValueError(f"rows standing on each other in a ring: {sorted(ids - done)}")
        found += ready
        done |= {row["id"] for row in ready}
    return found


def box(place, row, number, placed, frame, under):
    """One missing object: its prim path (under the Gaps scope, or nested under its missing parent's box), its
    row, size, how it is placed and its frame."""
    name = f"{row['id']}_{number}"
    return {"path": f"{under or f'/{place}/Gaps'}/{name}", "name": name, "row": row, "placed": placed,
            "frame": frame}


def boxes(stage, place, written, kit, rows):
    """Every object of the missing rows as a box, parents before children."""
    spots = plans.row_spots(written, kit) if written else {}
    room = dict(written.get("room", {}), name=kit.get("room", "")) if written else {}
    ground = grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))
    made = made_objects(stage, place)
    missing_ids = {row["id"] for row in rows}
    first = {}  # a missing parent's first box: (its path, its height), or its path and None when it is unplaced
    found = []
    for row in ordered(rows):
        parent = parent_of(row)
        if parent and parent != row["id"]:
            nested = first.get(parent) if parent in missing_ids else None
            top = None if parent in missing_ids else parent_top(stage, made, parent)
            laid = on_frames(row, top, nested)
        else:
            laid = [(placed, frame, None) for placed, frame in frames(row, kit, room, spots, ground)]
        for number, (placed, frame, under) in enumerate(laid, start=1):
            found.append(box(place, row, number, placed, frame, under))
        own = found[-len(laid)]
        first[row["id"]] = (own["path"], float(row["size"][2]) if own["placed"] != UNPLACED else None)
    return found

