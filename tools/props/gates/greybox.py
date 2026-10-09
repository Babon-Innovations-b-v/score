"""The greybox gate (G2 of the robust route, job robust-exp 2026-10-06): checks on a kit room's real meshes that cost
nothing and run before any picture or model is paid for.

    ~/.farm-factory-props/env/bin/python tools/props/gates/greybox.py <layout.json> --models <folder> ... \
        [--sector 255,315] [--report <out.json>]

    leaks     rays cast from standing points inside the room outward through a sector of its walls and roof: the
              share that reach the shell's outer skin without meeting anything drawn (the hub's shell draws
              nothing; a route that seals the room lays a backer of its own); rays that leave through a real
              opening (a doorway, the porthole) are not leaks
    openings  rays straight out through each real opening of the shell in the sector: the share something blocks
    envelope  every piece's mesh against the shell's outer skin: pieces poking out, and by how much
    budget    the sector's pieces, triangles and lamps

A layout is HubKit's (data/kit/hub.json); pieces are placed as the game places them (room.py). `--models` names
the folders of .glb or .gltf models the pieces are drawn with (a route's made pieces, a scene package's objects).
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
import room  # noqa: E402
from room import hub_kit  # noqa: E402

RAYS_A_POINT = 96
POKE_TOLERANCE = 0.03
BLOCKED_WITHIN = 0.8


def openings():
    """The hub shell's real openings: (bearing, kind, numbers) -- doorways (wide, tall) and the porthole (high,
    radius), from the shell's own constants."""
    found = [(bearing, "doorway", hub_kit.DOORWAY) for bearing in hub_kit.DOORS]
    found.append((hub_kit.PORTHOLE[0], "porthole", (hub_kit.PORTHOLE[1], 0.3)))
    return found


def in_hole(points, along, kind, numbers):
    """Which points on an opening's wall plane lie inside the opening: a doorway's rectangle or the porthole's circle."""
    across, high = points @ along, points[:, 1]
    if kind == "doorway":
        return (np.abs(across) <= numbers[0] / 2) & (high >= 0.0) & (high <= numbers[1])
    return np.hypot(across, high - numbers[0]) <= numbers[1]


def in_opening(points, every_opening):
    """Which points (on or near the wall's outside) lie in one of the openings, seen straight through the wall."""
    inside = np.zeros(len(points), dtype=bool)
    for bearing, kind, numbers in every_opening:
        normal, along = hub_kit.bearing_vectors(bearing)
        inside |= (points @ normal > hub_kit.APOTHEM - 0.05) & in_hole(points, along, kind, numbers)
    return inside


def through_opening(origins, vectors, every_opening):
    """Which rays pass out through an opening: where each crosses the inside face of an opening's wall, it is inside
    the opening (a ray leaving at a slant through the porthole's tunnel ends off its axis outside)."""
    inside = np.zeros(len(origins), dtype=bool)
    for bearing, kind, numbers in every_opening:
        normal, along = hub_kit.bearing_vectors(bearing)
        outward = vectors @ normal
        travel = np.where(outward > 1e-6, (hub_kit.APOTHEM - origins @ normal) / np.maximum(outward, 1e-6), -1.0)
        inside |= (travel > 0) & in_hole(origins + vectors * travel[:, None], along, kind, numbers)
    return inside


def standing_points(sector):
    """Points a person's eye or hand could be at in front of the sector's walls: three rings, five heights."""
    found = []
    for radius in (2.8, 3.4, 4.0):
        for bearing in np.arange(sector[0], sector[1] + 0.1, 5.0):
            normal, _ = hub_kit.bearing_vectors(bearing)
            for high in (0.4, 1.0, 1.6, 2.2, 2.8):
                found.append(normal * radius + np.array([0.0, high, 0.0]))
    return np.array(found)


def directions(count, seed):
    rng = np.random.default_rng(seed)
    found = rng.normal(size=(count, 3))
    return found / np.linalg.norm(found, axis=1, keepdims=True)


def first_hits(mesh, origins, rays):
    """Distance along each ray to the first surface of `mesh` (inf where none)."""
    distance = np.full(len(origins), np.inf)
    if mesh is None or len(mesh.faces) == 0:
        return distance
    where, ray_index, _ = mesh.ray.intersects_location(origins, rays, multiple_hits=False)
    distance[ray_index] = np.linalg.norm(where - origins[ray_index], axis=1)
    return distance


def leaks(drawn, skin, sector, seed=7):
    """Rays out through the sector: (escaped share, rays counted)."""
    points = standing_points(sector)
    rays = directions(RAYS_A_POINT, seed)
    origins = np.repeat(points, len(rays), axis=0)
    vectors = np.tile(rays, (len(points), 1))
    to_skin = first_hits(skin, origins, vectors)
    exits = origins + vectors * to_skin[:, None]
    bearings = room.bearing_of(exits)
    counted = (bearings >= sector[0]) & (bearings <= sector[1]) & np.isfinite(to_skin)
    counted &= ~in_opening(exits, openings()) & ~through_opening(origins, vectors, openings())
    counted &= exits[:, 1] >= 0.0  # the walls and the roof; the floor and the pit are a check of their own
    origins, vectors, to_skin = origins[counted], vectors[counted], to_skin[counted]
    to_drawn = first_hits(drawn, origins, vectors)
    escaped = to_drawn > to_skin
    return float(escaped.mean()) if len(escaped) else 0.0, int(len(escaped))


def opening_blocked(drawn, sector):
    """For each real opening in the sector, the share of straight rays out through it that something blocks."""
    found = {}
    for bearing, kind, numbers in openings():
        if not sector[0] <= bearing <= sector[1]:
            continue
        normal, along = hub_kit.bearing_vectors(bearing)
        samples = []
        for across in np.linspace(-0.45, 0.45, 9):
            for up in np.linspace(0.05, 0.95, 9):
                if kind == "doorway":
                    samples.append(normal * (hub_kit.APOTHEM - BLOCKED_WITHIN / 2) + along * across * numbers[0]
                                   + np.array([0.0, up * numbers[1], 0.0]))
                elif math.hypot(across, up - 0.5) <= 0.45:
                    samples.append(normal * (hub_kit.APOTHEM - BLOCKED_WITHIN / 2) + along * across * 2 * numbers[1]
                                   + np.array([0.0, numbers[0] + (up - 0.5) * 2 * numbers[1], 0.0]))
        origins = np.array(samples)
        hits = first_hits(drawn, origins, np.tile(normal, (len(origins), 1)))
        found[f"{kind} {bearing}"] = float((hits < BLOCKED_WITHIN).mean())
    return found


def envelope(pieces, skin):
    """Pieces whose mesh pokes out of the shell's outer skin by more than POKE_TOLERANCE: (index, kind, metres)."""
    found = []
    for index, kind, mesh in pieces:
        points = mesh.vertices
        if len(points) > 4000:
            points = points[np.random.default_rng(0).choice(len(points), 4000, replace=False)]
        outside = ~skin.contains(points)
        if not outside.any():
            continue
        poke = float(np.max(-trimesh.proximity.signed_distance(skin, points[outside])))
        if poke > POKE_TOLERANCE:
            found.append((index, kind, round(poke, 3)))
    return found


def in_sector(layout, sector):
    """Indices of the pieces laid in the sector (by their origin's bearing), out of the pit."""
    chosen = set()
    for index, laid in enumerate(layout["pieces"]):
        at = np.array([laid["at"]])
        if sector[0] <= room.bearing_of(at)[0] < sector[1] and laid["at"][1] > -0.1 and \
                math.hypot(laid["at"][0], laid["at"][2]) >= 2.6:
            chosen.add(index)
    return chosen


def budget(layout, pieces, chosen):
    lamps = sum(1 for index in chosen if "light" in layout["kinds"].get(layout["pieces"][index]["kind"], {}))
    triangles = sum(len(mesh.faces) for index, _, mesh in pieces if index in chosen)
    return {"pieces": len(chosen), "kinds": len({layout["pieces"][index]["kind"] for index in chosen}),
            "triangles": int(triangles), "lamps": lamps}


def gate(layout, resolve, sector):
    """Every check on one layout: the report."""
    skin = room.outer_skin()
    pieces = room.placed(layout, resolve)
    drawn = trimesh.util.concatenate([mesh for _, _, mesh in pieces])
    chosen = in_sector(layout, sector)
    escaped, rays = leaks(drawn, skin, sector)
    return {"leak_share": round(escaped, 4), "rays": rays, "openings_blocked": opening_blocked(drawn, sector),
            "envelope": envelope([piece for piece in pieces if piece[0] in chosen], skin),
            "budget": budget(layout, pieces, chosen)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("layout", type=pathlib.Path)
    parser.add_argument("--models", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--sector", default="255,315")
    parser.add_argument("--report", type=pathlib.Path)
    arguments = parser.parse_args()
    layout = json.loads(arguments.layout.read_text())
    resolve = room.models_in(*arguments.models)
    sector = tuple(float(value) for value in arguments.sector.split(","))
    report = gate(layout, resolve, sector)
    text = json.dumps(report, indent=1)
    print(text)
    if arguments.report:
        arguments.report.write_text(text)


if __name__ == "__main__":
    main()
