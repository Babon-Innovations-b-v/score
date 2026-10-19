"""The scene inventory rows a place's stage has nothing made for, and where each one's box goes. No position is
ever made up: a box stands only where the inventory, the kit or the made parent says.

    inventory = rows.inventory(data, place)          # the place's scene inventory, or None
    missing = rows.missing(stage, inventory)          # the rows the completion gate's own rule finds unmade
    boxes = rows.boxes(stage, place, inventory, kit, missing)   # one a row's object, parents before children

Which rows are missing is tools/usd/complete.py's rule (`unlaid_rows`: not laid, not dropped, not held back), over
the laid rows of the place's accepted stage (none when it has none). A row's objects are named as
export.object_names names them (`<row>_<n>`, the n-th of its row) and placed by the first rule that applies:

    spot      a floor or ceiling spot: the inventory's x and z, else the kit's pieces of the row (plan.row_spots);
              the foot at the spot's y, else on the floor at 0 (a ceiling row with no y has no height: unplaced),
              turned about up by `facing` as export.turn_in_seat turns it (a kit piece by its own axes)
    wall      a wall spot (`wall`, `across`, `bottom`): room_kit.on_side over the inventory's room
    on        a row anchored `on:<parent>`: on the parent's top, its objects spread along x; on the made parent's
              world box, or nested under the parent's own box when the parent is missing too
    unplaced  anything else: no transform, no box in space
"""
import json
import math
import pathlib
import sys

from score.stages.scene_record import plan as plans

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on the path by the complete stage's import
import complete  # noqa: E402

SPOT, WALL, ON, UNPLACED = "spot", "wall", "on", "unplaced"
PLACED = (SPOT, WALL, ON, UNPLACED)


def inventory(data, place):
    """The place's scene inventory (its plan's `inventory` name, the prologue's rooms', else the place's own), or
    None when it has none."""
    plan = pathlib.Path(data) / "plans" / f"{place}.json"
    name = json.loads(plan.read_text()).get("inventory", place) if plan.exists() else place
    path = pathlib.Path(data) / "inventory" / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def missing(stage, written):
    """The inventory's rows with nothing made for them on the stage (every row, with no stage), in its order."""
    if written is None:
        return []
    laid = complete.laid_rows(stage) if stage is not None else set()
    unlaid = {fault["row"] for fault in complete.unlaid_rows(written, laid)}
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


def floor_spots(row, kit, spots):
    """The row's floor or ceiling spots as frames {origin, axes}, or None for one with no height; `spots` its (x, z)
    from plan.row_spots, in the same order as the inventory's or the kit's own."""
    given = [spot for spot in row.get("at", []) if "x" in spot]
    if given:
        return [None if foot_height(row, spot.get("y")) is None else
                {"origin": [x, foot_height(row, spot.get("y")), z], "axes": turned(spot.get("facing", 0.0))}
                for (x, z), spot in zip(spots, given)]
    return [{"origin": [x, float(piece["at"][1]), z], "axes": [piece["x"], piece["y"], piece["z"]]}
            for (x, z), piece in zip(spots, kit_pieces(row, kit))]


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


def frames(row, kit, room, spots):
    """[(placed, frame or None)] for each object of a row that does not stand on another: its spots, then its wall
    spots; its count unplaced when it has neither."""
    found = [(SPOT, frame) for frame in floor_spots(row, kit, spots.get(row["id"], []))]
    found += [(WALL, frame) for frame in wall_spots(row, room)]
    if not found:
        return [(UNPLACED, None)] * max(1, int(row.get("count", 1)))
    return [(placed if frame else UNPLACED, frame) for placed, frame in found]


def parent_top(stage, place, parent):
    """The made parent's world box top as (middle x, top y, middle z), from its first object; None when it has
    no object on the stage."""
    from pxr import Usd, UsdGeom
    if stage is None:
        return None
    made = sorted(str(prim.GetPath()) for prim in stage.Traverse()
                  if prim.HasAttribute("score:row") and prim.GetAttribute("score:row").Get() == parent)
    if not made:
        return None
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    box = cache.ComputeWorldBound(stage.GetPrimAtPath(made[0])).ComputeAlignedRange()
    if box.IsEmpty():
        return None
    low, high = box.GetMin(), box.GetMax()
    return [(low[0] + high[0]) / 2, high[1], (low[2] + high[2]) / 2]


def spread(count, wide, index):
    """The along-x offset of the index-th of `count` objects side by side, `wide` each, centred."""
    return (index - (count - 1) / 2) * wide


def on_frames(row, top, nested):
    """The objects of a row standing on its parent: on the made parent's top (`top`), on the missing parent's own
    box (`nested`: (its path, its height), its frame its own), or unplaced."""
    count = max(1, int(row.get("count", 1)))
    wide = float(row["size"][0])
    if top is not None:
        return [(ON, {"origin": [top[0] + spread(count, wide, index), top[1], top[2]], "axes": turned(0.0)}, None)
                for index in range(count)]
    if nested is not None and nested[1] is not None:
        return [(ON, {"origin": [spread(count, wide, index), nested[1], 0.0], "axes": turned(0.0)}, nested[0])
                for index in range(count)]
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
    """One missing object: its prim path (under the Holes scope, or nested under its missing parent's box), its
    row, size, how it is placed and its frame."""
    name = f"{row['id']}_{number}"
    return {"path": f"{under or f'/{place}/Holes'}/{name}", "name": name, "row": row, "placed": placed,
            "frame": frame}


def boxes(stage, place, written, kit, rows):
    """Every object of the missing rows as a box, parents before children."""
    spots = plans.row_spots(written, kit) if written else {}
    room = dict(written.get("room", {}), name=kit.get("room", "")) if written else {}
    missing_ids = {row["id"] for row in rows}
    first = {}  # a missing parent's first box: (its path, its height), or its path and None when it is unplaced
    found = []
    for row in ordered(rows):
        parent = parent_of(row)
        if parent and parent != row["id"]:
            nested = first.get(parent) if parent in missing_ids else None
            top = None if parent in missing_ids else parent_top(stage, place, parent)
            laid = on_frames(row, top, nested)
        else:
            laid = [(placed, frame, None) for placed, frame in frames(row, kit, room, spots)]
        for number, (placed, frame, under) in enumerate(laid, start=1):
            found.append(box(place, row, number, placed, frame, under))
        own = found[-len(laid)]
        first[row["id"]] = (own["path"], float(row["size"][2]) if own["placed"] != UNPLACED else None)
    return found

