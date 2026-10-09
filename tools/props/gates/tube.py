"""The early checks for a walkway tube's kit (modules batch one, 2026-10-07): one bay's made pieces as the game lays
them, before any game run.

    ~/.farm-factory-props/env/bin/python tools/props/gates/tube.py <layout.json> --models <folder> [--report <out.json>]

    leaks     rays from eye height in the bay's middle, every way round the section: the share that reach the tube's
              hull (RADIUS round its axis) without meeting a piece, outside the two glass bands (the tube's own glass)
    envelope  pieces reaching out of the hull or under the deck, and by how much

Frame: tube_kit.py's (x across, y up from the deck, z along the tube); a bay runs from z 0 to its length.
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
import tube_kit  # noqa: E402

RAYS = 360
POKE_TOLERANCE = 0.03


def leaks(pieces, bay):
    drawn = trimesh.util.concatenate([mesh for _, _, mesh in pieces])
    caster = drawn.ray  # embree when the prop environment has it (embreex): the rooms run to millions of faces
    angles = np.radians(np.linspace(-180.0, 180.0, RAYS, endpoint=False))
    origin = np.array([0.0, 1.6, bay / 2])
    rays = np.stack([np.sin(angles), np.cos(angles), np.zeros_like(angles)], 1)
    origins = np.repeat(origin[None], len(rays), axis=0)
    hits, hit_rays, _ = caster.intersects_location(origins, rays, multiple_hits=False)
    met = np.full(len(rays), np.inf)
    met[hit_rays] = np.linalg.norm(hits - origins[hit_rays], axis=1)
    # where each ray meets the hull's circle, or the deck
    found = []
    for index, direction in enumerate(rays):
        to_hull = _to_circle(origin, direction)
        to_deck = (0.0 - origin[1]) / direction[1] if direction[1] < -1e-6 else np.inf
        reach = min(to_hull, to_deck)
        point = origin + direction * reach
        crown = abs(math.degrees(math.atan2(point[0], point[1] - tube_kit.AXIS_HIGH)))
        glass = tube_kit.GLASS_FROM <= crown <= tube_kit.GLASS_TO
        if met[index] > reach + 0.01 and not glass:
            found.append(round(math.degrees(angles[index]), 1))
    return {"rays": RAYS, "leak_share": round(len(found) / RAYS, 4), "leaks_at_degrees": found[:30]}


def _to_circle(origin, direction):
    """How far along a ray in the section from `origin` the hull's circle is (the far root of the quadratic)."""
    start = origin[:2] - np.array([0.0, tube_kit.AXIS_HIGH])
    flat = direction[:2]
    linear = 2 * start @ flat
    constant = start @ start - tube_kit.RADIUS ** 2
    return (-linear + math.sqrt(linear * linear - 4 * (flat @ flat) * constant)) / (2 * (flat @ flat))


def envelope(pieces):
    found = []
    for index, kind, mesh in pieces:
        out = np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1] - tube_kit.AXIS_HIGH) - (tube_kit.RADIUS + 0.04)
        under = -mesh.vertices[:, 1] - 0.05
        worst = float(max(out.max(), under.max()))
        if worst > POKE_TOLERANCE and not kind.endswith("_hoop"):
            found.append({"piece": index, "kind": kind, "out": round(worst, 3)})
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("layout", type=pathlib.Path)
    parser.add_argument("--models", type=pathlib.Path, action="append", default=[])
    parser.add_argument("--report", type=pathlib.Path)
    options = parser.parse_args()
    kit = json.loads(options.layout.read_text())
    bay_only = dict(kit, pieces=[laid for laid in kit["pieces"] if laid.get("tube_part", "bay") == "bay"])
    resolve = room.models_in(*options.models)
    pieces = room.placed(bay_only, resolve)
    report = {"pieces": len(pieces), "of": len(bay_only["pieces"]), "leaks": leaks(pieces, kit.get("bay", tube_kit.BAY)),
              "envelope": envelope(room.placed(kit, resolve))}
    if options.report:
        options.report.write_text(json.dumps(report, indent=1))
    print("pieces", report["pieces"], "of", report["of"], "| leak share", report["leaks"]["leak_share"],
          "| poking out", len(report["envelope"]))


if __name__ == "__main__":
    main()
