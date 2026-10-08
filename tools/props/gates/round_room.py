"""The early room checks for a rounded kit room (modules batch one, 2026-10-07: the habitat and the airlock), what
greybox.py and placement.py are for the hub's twelve walls: on the room's real meshes, before any picture is paid for.

    ~/.farm-factory-props/env/bin/python tools/props/gates/round_room.py <room> <layout.json> --models <folder> \
        [--report <out.json>] [--boxes]

    leaks     rays cast from standing points at eye height across the room's floor, every way up and round: the
              share that reach the shell's outer skin without meeting anything drawn; a ray leaving through a
              doorway the game shuts with a node of its own (the airlock's doors) is not a leak
    envelope  every piece's mesh against the shell's outer skin: pieces poking out, and by how much
    doorways  pieces standing in a doorway's way in (a door's width, a metre into the room)
    crowding  solid pieces overlapping each other

The skin and the doorways are the room's numbers (its inventory's `room.layout`, the shell's own outline from
room_kit.py); pieces are placed as the game places them (room.py).
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "scene"))
import room  # noqa: E402
import room_kit  # noqa: E402

SHELL_WALL = 0.3
ROOF_THICK = 0.25
POKE_TOLERANCE = 0.03
RAYS_A_POINT = 96
EYE = 1.6
GRID = 1.5
WAY_IN = 1.0
DOORWAY = room_kit.DOORWAY
DOOR_LEAF_TOP = 2.7  # the airlock door leaf's top (airlock.tscn): it shuts the doorway and the strip of shell over it


def skin(layout):
    """The shell's outer solid: its walls' outside faces from under the floor to the eaves and its dome's top."""
    points = []
    for inset, high in ((-SHELL_WALL, -0.3), (-SHELL_WALL, layout["wall"])):
        points += [(x, high, z) for x, z in room_kit.outline(layout["inside"], layout["corner"], inset)]
    for inset, high, under in room_kit.roof_profile(layout):
        points += [(x, high - under[1] * (ROOF_THICK + 0.05), z)
                   for x, z in room_kit.outline(layout["inside"], layout["corner"], inset - under[0] * (ROOF_THICK + 0.05))]
    return trimesh.convex.convex_hull(np.array(points))


def doorway_rays(layout, shut_by_game, origins, directions, travel):
    """Which rays leave through a doorway the game shuts with a node of its own."""
    found = np.zeros(len(directions), dtype=bool)
    for name in shut_by_game:
        side = room_kit.side_named(layout, name)
        middle = (side["start"] + side["end"]) / 2
        along = (side["end"] - side["start"]) / np.linalg.norm(side["end"] - side["start"])
        outward = np.array([side["outward"][0], 0.0, side["outward"][1]])
        # where each ray crosses the wall's inside face: through the doorway there, it meets the game's door
        toward = directions @ outward
        reach = ((np.array([middle[0], 0.0, middle[1]]) - origins) @ outward) / np.where(toward > 1e-6, toward, np.inf)
        at = origins + directions * reach[:, None]
        across = (at[:, [0, 2]] - middle) @ along
        found |= (toward > 1e-6) & (reach <= travel) & (np.abs(across) < DOORWAY[0] / 2) & (at[:, 1] < DOOR_LEAF_TOP)
    return found


def standing_points(layout, solids):
    """Eye-height points on a grid over the floor, clear of the walls (inside the rounded corners too: a corner
    rounded wider than the clearance left a point behind its panels, the workshop's, 2026-10-07) and of every solid
    piece."""
    half = np.asarray(layout["inside"]) / 2 - 0.6
    found = []
    for x in np.arange(-half[0], half[0] + 1e-6, GRID):
        for z in np.arange(-half[1], half[1] + 1e-6, GRID):
            point = np.array([x, EYE, z])
            if not in_rounded(layout, x, z, 0.6):
                continue
            if not any(mesh.bounds[0][0] - 0.2 < x < mesh.bounds[1][0] + 0.2
                       and mesh.bounds[0][2] - 0.2 < z < mesh.bounds[1][2] + 0.2 for mesh in solids):
                found.append(point)
    return np.array(found)


def in_rounded(layout, x, z, inset):
    """Whether a place on the floor stands inside the room's rounded outline pushed in by `inset`."""
    half = np.asarray(layout["inside"]) / 2 - inset
    reach = max(layout["corner"] - inset, 0.0)
    corner = half - reach
    out = np.maximum(np.abs([x, z]) - corner, 0.0)
    return bool(np.all(np.abs([x, z]) <= half + 1e-9) and np.linalg.norm(out) <= reach + 1e-9)


def directions():
    """RAYS_A_POINT ways out, evenly over the upper half and round the level (a Fibonacci spiral)."""
    index = np.arange(RAYS_A_POINT) + 0.5
    up = index / RAYS_A_POINT * 1.1 - 0.1  # a little below level too
    turn = np.pi * (1 + 5 ** 0.5) * index
    flat = np.sqrt(np.maximum(0.0, 1 - up ** 2))
    return np.stack([flat * np.cos(turn), up, flat * np.sin(turn)], 1)


def leaks(layout, pieces, outer, shut_by_game, solids):
    drawn = trimesh.util.concatenate([mesh for _, _, mesh in pieces])
    caster = drawn.ray  # embree when the prop environment has it (embreex): the rooms run to millions of faces
    out_caster = outer.ray
    points = standing_points(layout, solids)
    ways = directions()
    origins = np.repeat(points, len(ways), axis=0)
    rays = np.tile(ways, (len(points), 1))
    exits, exit_rays, _ = out_caster.intersects_location(origins, rays, multiple_hits=False)
    travel = np.full(len(rays), np.inf)
    travel[exit_rays] = np.linalg.norm(exits - origins[exit_rays], axis=1)
    hits, hit_rays, _ = caster.intersects_location(origins, rays, multiple_hits=False)
    met = np.full(len(rays), np.inf)
    met[hit_rays] = np.linalg.norm(hits - origins[hit_rays], axis=1)
    leaking = (met > travel + 0.01) & ~doorway_rays(layout, shut_by_game, origins, rays, travel)
    where = origins[leaking] + rays[leaking] * np.minimum(travel[leaking], 30)[:, None]
    return {"points": int(len(points)), "rays": int(len(rays)), "leak_share": round(float(leaking.mean()), 4),
            "leaks_at": [[round(float(value), 2) for value in point] for point in where[:20]]}


def envelope(pieces, outer):
    found = []
    for index, kind, mesh in pieces:
        inside = outer.contains(mesh.vertices)
        if inside.all():
            continue
        distance = trimesh.proximity.signed_distance(outer, mesh.vertices[~inside])
        worst = float(-distance.min()) if len(distance) else 0.0
        if worst > POKE_TOLERANCE:
            found.append({"piece": index, "kind": kind, "out": round(worst, 3)})
    return found


def in_doorways(layout, pieces, doors):
    found = []
    for name in doors:
        side = room_kit.side_named(layout, name)
        middle = (side["start"] + side["end"]) / 2
        along = (side["end"] - side["start"]) / np.linalg.norm(side["end"] - side["start"])
        for index, kind, mesh in pieces:
            if "_hatch_" in kind or kind.endswith(("_door_frame", "_tread_mat", "_floor_grating")):
                continue  # the door's own parts and what lies before it
            flat = mesh.vertices[:, [0, 2]] - middle
            across, inward = flat @ along, -(flat @ side["outward"])
            inside = (np.abs(across) < DOORWAY[0] / 2 - 0.05) & (inward > 0.35) & (inward < WAY_IN) & \
                     (mesh.vertices[:, 1] > 0.05) & (mesh.vertices[:, 1] < DOORWAY[1] - 0.1)
            if inside.mean() > 0.02:
                found.append({"door": name, "piece": index, "kind": kind})
    return found


def crowding(solid_pieces):
    found = []
    for first in range(len(solid_pieces)):
        for second in range(first + 1, len(solid_pieces)):
            (index_a, kind_a, a), (index_b, kind_b, b) = solid_pieces[first], solid_pieces[second]
            low = np.maximum(a.bounds[0], b.bounds[0])
            high = np.minimum(a.bounds[1], b.bounds[1])
            if np.all(high - low > 0.02):
                found.append({"pieces": [index_a, index_b], "kinds": [kind_a, kind_b],
                              "overlap": [round(float(value), 3) for value in high - low]})
    return found


def unit_box(name, about):
    """A unit box standing on its foot's middle: a piece as its laid box."""
    box = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    box.apply_translation((0.0, 0.5, 0.0))
    return box


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("layout", type=pathlib.Path)
    parser.add_argument("--models", type=pathlib.Path, action="append", default=[])
    parser.add_argument("--report", type=pathlib.Path)
    parser.add_argument("--boxes", action="store_true", help="every piece its laid box: the layout's own check, before "
                                                             "any model is made")
    options = parser.parse_args()
    inventory = json.loads((room.REPO / f"data/inventory/{options.room}.json").read_text())
    layout = inventory["room"]["layout"]
    kit = json.loads(options.layout.read_text())
    pieces = room.placed(kit, unit_box if options.boxes else room.models_in(*options.models))
    solid_kinds = {kind for kind, about in kit["kinds"].items() if about.get("solid")}
    # What stands on the roof outside (the airlock's beacon) is not judged against the skin.
    outside = {kind for kind, about in kit["kinds"].items() if about.get("outside")}
    # A solid piece's glowing part (its screen, its lamp's lens) is its own, never a second piece crowding it.
    solids = [(index, kind, mesh) for index, kind, mesh in pieces
              if kind in solid_kinds and "part" not in kit["pieces"][index]]
    outer = skin(layout)
    # A doorway the game shuts with a node of its own, or an open one a tube joins (the workshop's west, to the
    # corridor): a ray through it leaves into the next room, not out through a gap.
    shut_by_game = [name for name, kind in layout["doors"].items() if kind != "hatch" or name in layout.get("open", [])]
    report = {"room": options.room, "pieces": len(pieces), "of": len(kit["pieces"]),
              "leaks": leaks(layout, pieces, outer, shut_by_game, [mesh for _, _, mesh in solids]),
              "envelope": envelope([piece for piece in pieces if piece[1] not in outside], outer),
              "doorways": in_doorways(layout, pieces, layout["doors"]),
              "crowding": crowding(solids)}
    text = json.dumps(report, indent=1)
    if options.report:
        options.report.write_text(text)
    print("pieces", report["pieces"], "of", report["of"], "| leak share", report["leaks"]["leak_share"],
          "| poking out", len(report["envelope"]), "| in doorways", len(report["doorways"]),
          "| crowding", len(report["crowding"]))


if __name__ == "__main__":
    main()
