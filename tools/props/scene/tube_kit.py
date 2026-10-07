"""The kit layout of a walkway tube (modules batch one, 2026-10-07): the made pieces of one bay and of one end, which
the game lays along any tube's way (TubeKit: bay after bay between the two ends, each bay stretched to share the length
evenly, the far end turned to face back in).

    python3 tools/props/scene/tube_kit.py <out.json>

The tube's numbers are the network's (TubeWay: its section RADIUS round an axis AXIS_HIGH over the deck, so the deck
is 2.3 m wide where the hull meets it) and LinkTube's (a hoop every BAY metres, the glass band from GLASS_FROM to
GLASS_TO degrees off the crown each side, the collar at each end). Frame of a bay and of an end: x across the tube to
the right looking along it, y up from the deck, z along the tube (an end's z runs from the doorway into the tube).

The pieces, as the picked concept (K12) shows the tube: a deck plate; the hull's crown plate and its two foot plates
under the glass; a rail along each edge of each glass band (the glass itself is the tube's, LinkTube's); a hoop at the
bay's start; a handrail each side at the glass's foot; three pipe runs low on the left and a cable run high on the
right; the strip lamp along the crown; a welded patch on the crown every PATCH_EVERY bays. At each end: the collar
ring, a sign plate on its crown facing into the tube, and a dust strip on the deck.
"""
import json
import math
import pathlib
import sys

import numpy as np

RADIUS = 1.6  # TubeWay.RADIUS
AXIS_HIGH = 1.1  # TubeWay.AXIS_HEIGHT
BAY = 1.3  # LinkTube.HOOP_EVERY
GLASS_FROM, GLASS_TO = 38.0, 104.0  # LinkTube.GLASS_FROM, GLASS_TO
SHELL_WALL = 0.3  # ModuleShell.WALL
HULL_IN = 1.58  # the kit's hull plates' outer face, under the shell's
FOOT_END = math.degrees(math.acos(-AXIS_HIGH / RADIUS))  # where the arch meets the deck
DECK_HALF = math.sqrt(RADIUS ** 2 - AXIS_HIGH ** 2)
PATCH_EVERY = 3
ROOM = "tube"


def piece(kind, origin, x, z, size, **extra):
    """A piece in its kind's frame: its x and z axes given (y = z cross x), its origin at its foot's middle."""
    x, z = np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64)
    y = np.cross(z, x)
    found = {"kind": f"{ROOM}_{kind}", "at": [round(float(value), 4) for value in origin],
             "x": [round(float(value), 5) for value in x], "y": [round(float(value), 5) for value in y],
             "z": [round(float(value), 5) for value in z], "size": [round(float(value), 4) for value in size],
             "layer": 1}
    found.update(extra)
    return found


def arc_box(radius, deep, start, end):
    """An arc band's box in the section (as pieces.arc_points draws it): its foot's middle (x, y over the deck) and its
    width and height."""
    angles = np.radians(np.linspace(start, end, 64))
    points = np.concatenate([np.stack([r * np.sin(angles), AXIS_HIGH + r * np.cos(angles)], 1)
                             for r in (radius, radius - deep)])
    low, high = points.min(axis=0), points.max(axis=0)
    return np.array([(low[0] + high[0]) / 2, low[1]]), high - low


def along(kind, arc, length, middle_z, part, **extra):
    """A band of the section (`arc`: radius, depth, start, end degrees off the crown) running `length` along the
    tube, its middle `middle_z` along it."""
    foot, size = arc_box(*arc)
    return piece(kind, (foot[0], foot[1], middle_z), (1, 0, 0), (0, 0, 1), (size[0], size[1], length), arc=list(arc),
                 tube_part=part, **extra)


def run_along(kind, x, y, length, middle_z, size, facing_right, part):
    """A pipe or cable run along the tube at (x, y), its front toward the tube's middle."""
    z = (-1, 0, 0) if facing_right else (1, 0, 0)
    xs = (0, 0, 1) if facing_right else (0, 0, -1)
    return piece(kind, (x, y - size[1] / 2, middle_z), xs, z, (length, size[1], size[2]), tube_part=part)


def bay():
    """One bay's pieces, from z 0 to BAY."""
    middle = BAY / 2
    found = [piece("ring_floor_plate", (0.0, -0.02, 0.0), (1, 0, 0), (0, -1, 0), (2 * DECK_HALF, BAY, 0.04),
                   taper=1.0, tube_part="bay")]
    found.append(along("hull_plate", (HULL_IN, 0.04, -GLASS_FROM + 2, GLASS_FROM - 2), BAY, middle, "bay"))
    for side in (-1, 1):
        found.append(along("hull_plate", (HULL_IN, 0.04, side * (GLASS_TO + 2), side * FOOT_END), BAY, middle,
                           "bay"))
        for edge in (GLASS_FROM, GLASS_TO):
            found.append(along("hull_plate", (HULL_IN, 0.08, side * (edge - 2), side * (edge + 2)), BAY, middle,
                               "bay", material="dark_panel"))
        rail_y = 0.95
        rail_x = side * (math.sqrt(RADIUS ** 2 - (rail_y - AXIS_HIGH) ** 2) - 0.16)
        found.append(run_along("pipe_straight", rail_x, rail_y, BAY, middle, (BAY, 0.06, 0.06), side > 0, "bay"))
    for high in (0.25, 0.4, 0.55):
        x = -(math.sqrt(HULL_IN ** 2 - (high - AXIS_HIGH) ** 2) - 0.12)
        found.append(run_along("pipe_straight", x, high, BAY, middle, (BAY, 0.1, 0.1), False, "bay"))
    found.append(cable_run(middle))
    found.append(along("hoop", (HULL_IN, 0.12, -FOOT_END + 1, FOOT_END - 1), 0.09, 0.045, "bay"))
    lamp = (1.2, 0.12, 0.1)
    crown = AXIS_HIGH + HULL_IN - 0.04
    found.append(piece("crown_strip_lamp", (-lamp[1] / 2, crown - lamp[2] / 2, middle), (0, 0, 1), (0, 1, 0), lamp,
                       tube_part="bay"))
    found.append(patch(middle))
    return found


def cable_run(middle):
    """The cable run high on the right, on the crown plate 30 degrees off the crown, its front to the tube's axis."""
    angle = math.radians(30.0)
    size = (BAY, 0.12, 0.08)
    out = np.array([math.sin(angle), math.cos(angle), 0.0])
    reach = HULL_IN - 0.04 - size[2] / 2
    middle_point = np.array([0.0, AXIS_HIGH, middle]) + out * reach
    x = np.array([0.0, 0.0, -1.0])
    y = np.cross(out, x)
    origin = middle_point - y * size[1] / 2
    return piece("cable_bundle", origin, x, out, size, tube_part="bay")


def patch(middle):
    """A welded patch on the crown plate, 15 degrees left of the crown, on every PATCH_EVERY-th bay."""
    angle = math.radians(-15.0)
    size = (0.7, 0.5, 0.04)
    out = np.array([math.sin(angle), math.cos(angle), 0.0])
    middle_point = np.array([0.0, AXIS_HIGH, middle]) + out * (HULL_IN - 0.04 - size[2] / 2)
    x = np.array([0.0, 0.0, 1.0])
    y = np.cross(out, x)
    return piece("hull_patch", middle_point - y * size[1] / 2, x, out, size, tube_part="bay", every=PATCH_EVERY)


def end():
    """One end's pieces, z from its doorway into the tube: the collar ring round the doorway's mouth (LinkTube's
    collar: the shell's half wall and most of the collar's thickness in), a sign plate on the collar facing in, and a
    dust strip on the deck inside it."""
    collar = 0.16
    collar_z = SHELL_WALL / 2 + collar * 0.7
    found = [along("hoop", (RADIUS + 0.02, 0.2, -FOOT_END + 0.5, FOOT_END - 0.5), collar, collar_z, "end",
                   material="painted_panel")]
    sign = (0.4, 0.16, 0.02)
    found.append(piece("sign_plate", (0.0, AXIS_HIGH + RADIUS + 0.02 - 0.2 + 0.02, collar_z + collar / 2 + sign[2] / 2),
                       (-1, 0, 0), (0, 0, -1), sign, tube_part="end"))
    mat = (2.0, 0.5, 0.02)
    found.append(piece("end_mat", (0.0, mat[2] / 2, collar_z + 0.15), (1, 0, 0), (0, -1, 0), mat, tube_part="end"))
    return found


KINDS = {"ring_floor_plate": {"group": "floors"}, "end_mat": {"group": "floors"},
         "crown_strip_lamp": {"group": "hangs", "light": {"strength": 0.15, "reach": 3.5, "high": 0.5}},
         "hull_plate": {}, "hoop": {}, "pipe_straight": {"group": "hangs"},
         "cable_bundle": {"group": "hangs"}, "hull_patch": {"group": "hangs"}, "sign_plate": {"group": "hangs"}}


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    pieces = bay() + end()
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    pathlib.Path(sys.argv[1]).write_text(json.dumps(
        {"room": ROOM, "frame": "a bay's or an end's: x across the tube to the right, y up from the deck, z along it",
         "bay": BAY, "counts": counts, "kinds": {f"{ROOM}_{kind}": about for kind, about in KINDS.items()},
         "pieces": pieces}, indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")


if __name__ == "__main__":
    main()
