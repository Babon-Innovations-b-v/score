"""Check a place's cast before its characters go into the stage: every character is a distinct person, and every walk
stays clear of the other people and of the place's objects.

    .venv/bin/python tools/characters/cast_check.py <place> --stage <the place's stage .usda>

Two rules, both the owner's (2026-10-09, after the hub showed two of the same crew member and one walked into the
other):

- **Nobody twice.** A person is their look (cast.look_of): a named body (`nev`, `oona`, the leader) is one person,
  and a kit mix is its build with its face and hair. Two characters with the same look are the same person, whatever
  they wear, and a place never shows the same person twice. The crowd (one cheap distant body copied many times as a
  PointInstancer, seen only from far away) is not checked: it is a crowd, not people one tells apart.
- **Walks stay clear.** Each walk is followed along its `path` at the cast's pace; at every step the walker's middle
  stays CLEARANCE metres from every other character where that one is at the same moment (standing still, or along
  its own walk), and BODY_RADIUS plus MARGIN metres from the footprint of every object the stage holds between a
  walker's knee and head (the room's pieces, its gameplay objects and its structure; what lies under a knee, the
  floor and its plates, or over a head, is stepped on or under).

It prints each fault and exits non-zero when there is one, so a cast that fails is never written into a stage.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cast  # noqa: E402

# A walker's body as a disc round its middle, in metres, and the room it keeps beyond that from what it passes.
BODY_RADIUS = 0.25
MARGIN = 0.15
# How far apart two people's middles stay: both bodies and the margin.
CLEARANCE = 2 * BODY_RADIUS + MARGIN
# The heights over a walker's feet an object must reach into to stand in its way: over the knee, under the head.
KNEE = 0.3
HEAD = 1.7
# How finely a walk is followed, in seconds.
STEP_SECONDS = 0.05
# The stage's scopes whose prims are things a walker could walk into, each prim one thing.
OBJECT_SCOPES = ("Objects", "Fixtures", "Structure")


def repeated_people(cast_record):
    """Faults: every person who is in the cast more than once, with the names they appear under."""
    seen = {}
    for character in cast.characters_of(cast_record):
        seen.setdefault(cast.look_of(character["character"], character.get("worn")), []).append(character["name"])
    return [f"{' and '.join(names)} are the same person ({', '.join(who)})"
            for who, names in seen.items() if len(names) > 1]


def walk_length(path):
    """A walk's length in metres along its points."""
    return sum(math.dist(start, end) for start, end in zip(path, path[1:]))


def where_at(character, seconds):
    """Where a character's middle is (x, z) after `seconds`: its spot, or along its walk at its pace, stopped at the
    walk's end."""
    path = character.get("path")
    if not path:
        return np.array([character["at"][0], character["at"][2]], dtype=float)
    left = seconds * float(character["pace"])
    for start, end in zip(path, path[1:]):
        length = math.dist(start, end)
        if left <= length and length > 0.0:
            share = left / length
            return np.array([start[0] + (end[0] - start[0]) * share, start[2] + (end[2] - start[2]) * share])
        left -= length
    return np.array([path[-1][0], path[-1][2]], dtype=float)


def walk_seconds(character):
    """How long a character's walk takes at its pace (nothing for one standing)."""
    return walk_length(character["path"]) / float(character["pace"]) if character.get("path") else 0.0


def clash_with_people(walker, others):
    """Faults: the first moment the walker comes closer than CLEARANCE to each of the others."""
    faults = []
    steps = int(walk_seconds(walker) / STEP_SECONDS) + 1
    for other in others:
        for step in range(steps + 1):
            seconds = step * STEP_SECONDS
            gap = float(np.linalg.norm(where_at(walker, seconds) - where_at(other, seconds)))
            if gap < CLEARANCE:
                faults.append(f"{walker['name']} walks {gap:.2f} m from {other['name']} after {seconds:.2f} s "
                              f"(people keep {CLEARANCE:.2f} m apart)")
                break
    return faults


def box_gap(point, box):
    """How far a point (x, z) is from a footprint box (x low, z low, x high, z high); 0 inside it."""
    low_x, low_z, high_x, high_z = box
    return math.hypot(max(low_x - point[0], 0.0, point[0] - high_x), max(low_z - point[1], 0.0, point[1] - high_z))


def clash_with_things(walker, things):
    """Faults: each thing (name, footprint box, bottom, top) in the walker's way, closer than BODY_RADIUS + MARGIN
    to its middle somewhere along its walk, reaching between its knee and head."""
    feet = float(walker["path"][0][1])
    keep = BODY_RADIUS + MARGIN
    steps = int(walk_seconds(walker) / STEP_SECONDS) + 1
    spots = [where_at(walker, step * STEP_SECONDS) for step in range(steps + 1)]
    faults = []
    for name, box, bottom, top in things:
        if top < feet + KNEE or bottom > feet + HEAD:
            continue
        gap = min(box_gap(spot, box) for spot in spots)
        if gap < keep:
            faults.append(f"{walker['name']} walks {gap:.2f} m from {name} (keeps {keep:.2f} m clear)")
    return faults


def walk_faults(cast_record, things):
    """Faults: every walk of the cast that passes through a person or a thing."""
    characters = cast.characters_of(cast_record)
    faults = []
    for walker in (character for character in characters if character.get("path")):
        others = [character for character in characters if character is not walker]
        faults += clash_with_people(walker, others)
        faults += clash_with_things(walker, things)
    return faults


def mesh_boxes(prim, cache):
    """The world boxes of a prim's meshes, each (x low, y low, z low, x high, y high, z high)."""
    boxes = []
    for part in Usd.PrimRange(prim):
        if part.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(part).ComputeVisibility() != UsdGeom.Tokens.invisible:
            extent = cache.ComputeWorldBound(part).ComputeAlignedRange()
            if not extent.IsEmpty():
                boxes.append((*extent.GetMin(), *extent.GetMax()))
    return boxes


def stage_things(stage_path, place):
    """The things a walker could walk into on a place's stage: each prim of its objects, gameplay objects and
    structure, as (name, footprint box, bottom, top). A structure piece (a room's walls, one mesh round the whole
    room) is taken a mesh at a time, its box only if it is not one that holds the whole floor."""
    stage = Usd.Stage.Open(str(stage_path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    things = []
    for scope in OBJECT_SCOPES:
        holder = stage.GetPrimAtPath(f"/{place}/{scope}")
        if not holder:
            continue
        for prim in holder.GetChildren():
            for box in mesh_boxes(prim, cache):
                things.append((f"{scope}/{prim.GetName()}", (box[0], box[2], box[3], box[5]), box[1], box[4]))
    return things


def wrapping(thing, cast_record):
    """Whether a thing's footprint holds every spot of the cast (a room's shell, its whole deck): one stands inside
    it, not in its way."""
    _, box, _, _ = thing
    spots = [character["at"] for character in cast.characters_of(cast_record)]
    spots += [point for character in cast.characters_of(cast_record) for point in (character.get("path") or [])]
    return all(box[0] <= spot[0] <= box[2] and box[1] <= spot[2] <= box[3] for spot in spots)


def check(cast_record, things):
    """Every fault of a cast against the things of its stage."""
    standing_in = [thing for thing in things if not wrapping(thing, cast_record)]
    return repeated_people(cast_record) + walk_faults(cast_record, standing_in)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("--stage", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    cast_record = json.loads((cast.CASTS / f"{arguments.place}.json").read_text())
    faults = check(cast_record, stage_things(arguments.stage, arguments.place))
    for fault in faults:
        print(fault)
    print(f"{arguments.place}: {len(faults)} fault(s)")
    sys.exit(1 if faults else 0)


if __name__ == "__main__":
    main()
