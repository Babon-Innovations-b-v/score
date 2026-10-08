"""The kit layout of a walkway tube (modules batch one, 2026-10-07): the made pieces of one bay and of one end, which
the game lays along any tube's way (TubeKit: bay after bay between the two ends, each bay stretched to share the length
evenly, the far end turned to face back in).

    python3 tools/props/scene/tube_kit.py <out.json>

The tube's numbers are the network's (TubeWay: its section RADIUS round an axis AXIS_HIGH over the deck, so the deck
is 2.3 m wide where the hull meets it) and LinkTube's (a hoop every BAY metres, the glass band from GLASS_FROM to
GLASS_TO degrees off the crown each side, the collar at each end). Frame of a bay and of an end: x across the tube to
the right looking along it, y up from the deck, z along the tube (an end's z runs from the doorway into the tube).

The pieces, as the picked concept (K12) shows the tube (read crop by crop for the concept-density rule, 2026-10-08): a
deck plate; the hull's crown plate and its two foot plates under the glass; a rail along each edge of each glass band
(the glass itself is the tube's, LinkTube's); a hoop at the bay's start; a handrail each side just under the glass on
bent brackets; three pipe runs low on the left and a bundle of three high on the right beside the cable run, every
pipe on its own clamp bracket, the run's axis PIPE_AXIS off the hull (pieces.PIPE_AXIS); a second cable run high on the
left; the strip lamp along the crown; a welded patch on the crown and a taped one low on the right every PATCH_EVERY
bays; and every INSTRUMENTS_EVERY bays a small readout screen, a junction box and a placard high on the left. At each
end: the collar ring, two sign plates on it either side of the crown facing into the tube, and a dust strip on the
deck.
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
# The hull plates' inner face (HULL_IN less their depth), what a fitting on the hull stands on.
HULL_FACE = HULL_IN - 0.04
# A pipe run's axis off the hull (pieces.PIPE_AXIS): where its clamp brackets (pieces.pipe_bracket) hold it.
PIPE_AXIS = 0.08
# The pipe runs by their angle off the crown (degrees, + to the right): three low on the left at the heights the old
# layout had them, three high on the right beside the cable run.
LOW_PIPE_HEIGHTS = (0.25, 0.4, 0.55)
HIGH_PIPES = (12.0, 18.5, 25.0)
CABLE_RIGHT, CABLE_LEFT = 31.0, -33.0
# The handrails: just under each glass band's foot (GLASS_TO), their axis RAIL_OFF off the hull, on a bent bracket
# near the bay's start (the concept's J hooks by each hoop).
RAIL_ANGLE = GLASS_TO + 3.0
RAIL = (BAY, 0.06, 0.06)
RAIL_OFF = 0.10
RAIL_BRACKET = (0.04, 0.07, RAIL_OFF + 0.031)
BRACKETS_AT = 0.65  # along the bay: the pipes' clamps, clear of the hoop and the rail brackets
RAIL_BRACKETS_AT = 0.08
# The instruments high on the left (a small readout, a junction box and a placard), on every INSTRUMENTS_EVERY-th bay,
# a multiple of PATCH_EVERY so they never share a bay with the crown patch (TubeKit lays a piece on bays where
# index % every == every // 2).
INSTRUMENTS_EVERY = 6
INSTRUMENTS_ANGLE = -25.0
LOW_PATCH_ANGLE = 118.0


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
        angle = side * RAIL_ANGLE
        found.append(on_hull("pipe_straight", angle, RAIL, middle, HULL_FACE - RAIL_OFF))
        found.append(on_hull("rail_bracket", angle, RAIL_BRACKET, RAIL_BRACKETS_AT,
                             HULL_FACE - RAIL_BRACKET[2] / 2))
    pipe = (BAY, 0.1, 0.1)
    bracket = (0.12, 0.1, 0.15)  # the hub's pipe bracket row (wide, tall, deep)
    low = [-math.degrees(math.acos((high - AXIS_HIGH) / (HULL_FACE - PIPE_AXIS))) for high in LOW_PIPE_HEIGHTS]
    for angle in low + list(HIGH_PIPES):
        found.append(on_hull("pipe_straight", angle, pipe, middle, HULL_FACE - PIPE_AXIS))
        found.append(on_hull("pipe_bracket", angle, bracket, BRACKETS_AT, HULL_FACE - bracket[2] / 2))
    cable = (BAY, 0.12, 0.08)
    for angle in (CABLE_RIGHT, CABLE_LEFT):
        found.append(on_hull("cable_bundle", angle, cable, middle, HULL_FACE - cable[2] / 2))
    found.append(along("hoop", (HULL_IN, 0.12, -FOOT_END + 1, FOOT_END - 1), 0.09, 0.045, "bay"))
    lamp = (1.2, 0.12, 0.1)
    crown = AXIS_HIGH + HULL_IN - 0.04
    found.append(piece("crown_strip_lamp", (-lamp[1] / 2, crown - lamp[2] / 2, middle), (0, 0, 1), (0, 1, 0), lamp,
                       tube_part="bay"))
    patch = (0.7, 0.5, 0.04)
    found.append(on_hull("hull_patch", -15.0, patch, middle, HULL_FACE - patch[2] / 2, every=PATCH_EVERY))
    found.append(on_hull("hull_patch", LOW_PATCH_ANGLE, (0.5, 0.4, 0.04), 0.45, HULL_FACE - 0.02, every=PATCH_EVERY))
    readout, box, placard = (0.3, 0.25, 0.06), (0.2, 0.2, 0.1), (0.24, 0.1, 0.02)
    found.append(on_hull("small_readout", INSTRUMENTS_ANGLE, readout, 0.3, HULL_FACE - readout[2] / 2,
                         every=INSTRUMENTS_EVERY))
    found.append(on_hull("sign_plate", INSTRUMENTS_ANGLE, placard, 0.68, HULL_FACE - placard[2] / 2,
                         every=INSTRUMENTS_EVERY, label="label_cable_run"))
    found.append(on_hull("conduit_box", INSTRUMENTS_ANGLE, box, 1.0, HULL_FACE - box[2] / 2,
                         every=INSTRUMENTS_EVERY))
    return found


def on_hull(kind, angle, size, along_z, reach, **extra):
    """A piece on the hull at `angle` degrees off the crown (+ to the right), `along_z` along the bay, its middle
    `reach` from the tube's axis, its back to the hull and its front to the axis. Its x runs along the tube, turned so
    its y (the piece's up) runs up the hull's side: a wall piece low on a side stands upright."""
    radians = math.radians(angle)
    out = np.array([math.sin(radians), math.cos(radians), 0.0])
    x = np.array([0.0, 0.0, 1.0 if angle < 0 else -1.0])
    y = np.cross(out, x)
    middle = np.array([0.0, AXIS_HIGH, along_z]) + out * reach
    return piece(kind, middle - y * size[1] / 2, x, out, size, tube_part="bay", **extra)


def end():
    """One end's pieces, z from its doorway into the tube: the collar ring round the doorway's mouth (LinkTube's
    collar: the shell's half wall and most of the collar's thickness in), a sign plate on the collar facing in, and a
    dust strip on the deck inside it."""
    collar = 0.16
    collar_z = SHELL_WALL / 2 + collar * 0.7
    found = [along("hoop", (RADIUS + 0.02, 0.2, -FOOT_END + 0.5, FOOT_END - 0.5), collar, collar_z, "end",
                   material="painted_panel")]
    sign = (0.4, 0.16, 0.02)
    # Two signs on the collar's band either side of the crown lamp (the concept's pair over the far hatch).
    band = RADIUS + 0.02 - 0.15  # inside the collar's 0.2 m band, the sign's corners too
    for angle in (-17.0, 17.0):
        radians = math.radians(angle)
        found.append(piece("sign_plate", (band * math.sin(radians), AXIS_HIGH + band * math.cos(radians) - sign[1] / 2,
                                          collar_z + collar / 2 + sign[2] / 2), (-1, 0, 0), (0, 0, -1), sign,
                           tube_part="end"))
    mat = (2.0, 0.5, 0.02)
    found.append(piece("end_mat", (0.0, mat[2] / 2, collar_z + 0.15), (1, 0, 0), (0, -1, 0), mat, tube_part="end"))
    return found


KINDS = {"ring_floor_plate": {"group": "floors"}, "end_mat": {"group": "floors"},
         "crown_strip_lamp": {"group": "hangs", "light": {"strength": 0.15, "reach": 3.5, "high": 0.5}},
         "hull_plate": {}, "hoop": {}, "pipe_straight": {"group": "hangs"},
         "cable_bundle": {"group": "hangs"}, "hull_patch": {"group": "hangs"}, "sign_plate": {"group": "hangs"},
         "pipe_bracket": {"group": "hangs"}, "rail_bracket": {"group": "hangs"}, "small_readout": {"group": "hangs"},
         "conduit_box": {"group": "hangs"}}


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
