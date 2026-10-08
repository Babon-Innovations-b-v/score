"""The placement gate's opening check (G6 of the robust route, job robust-exp 2026-10-06): no piece may stand in front
of one of the shell's real openings. The hub kit laid a conduit box over the porthole's spot because its wall gear
only kept clear of furniture (the hub kit log, 2026-10-06).

    ~/.farm-factory-props/env/bin/python tools/props/gates/placement.py <layout.json>

A piece clashes when its laid box, seen straight through its wall, overlaps an opening (a doorway, the porthole)
grown by a margin. Pieces that line an opening (its frame, the wall surround round a doorway, the porthole's own
panel, a backer) are its own and are not judged.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shell  # noqa: E402

MARGIN = 0.05
LINES_AN_OPENING = ("hatch_frame", "hatch_wall_surround", "porthole_panel", "backer", "hatch_hinge", "hatch_leaf",
                    "hatch_wheel", "hatch_window",
                    "skirting", "cornice", "floor_plate", "tread_mat", "door_frame")
# The wall's own lining (its panels and posts) runs up to an opening's edge and laps under its frame: a rounded room's
# panels reach room_kit.LAP / 2 past the end of their run, and a bay's big door is framed with the posts' kind. They may
# reach this far into an opening, never further.
LINES_ITS_EDGE = ("wall_lower", "wall_upper", "wall_corner_post")
EDGE_LAP = 0.025


def footprint(laid, opening):
    """The piece's laid box seen straight through an opening's wall: (across low, across high, up low, up high, out),
    across from the opening's middle and out from the wall's inside face."""
    corners = []
    origin = np.array(laid["at"])
    for x in (-0.5, 0.5):
        for y in (0.0, 1.0):
            for z in (-0.5, 0.5):
                corners.append(origin + np.array(laid["x"]) * x * laid["size"][0]
                               + np.array(laid["y"]) * y * laid["size"][1] + np.array(laid["z"]) * z * laid["size"][2])
    corners = np.array(corners) - opening["middle"]
    across = corners @ opening["along"]
    return across.min(), across.max(), corners[:, 1].min(), corners[:, 1].max(), float((corners @ opening["normal"]).max())


def bearing(vector):
    """A direction's bearing on the floor, in degrees clockwise from north (-z)."""
    return float(np.degrees(np.arctan2(vector[0], -vector[2])) % 360)


def in_front(laid, opening):
    """Whether a piece's box, seen straight through the opening's wall, overlaps the opening grown by MARGIN (the
    wall's own lining: shrunk by EDGE_LAP)."""
    low, high, bottom, top, out = footprint(laid, opening)
    if out < -0.6:
        return False
    box = opening["box"]
    grow = -EDGE_LAP if any(word in laid["kind"] for word in LINES_ITS_EDGE) else MARGIN
    return low < box[1] + grow and high > box[0] - grow and bottom < box[3] + grow and top > box[2] - grow


def clashes(layout):
    """Every piece in front of an opening: (index, kind, opening)."""
    every_opening = shell.openings(layout)
    found = []
    for index, laid in enumerate(layout["pieces"]):
        if any(word in laid["kind"] for word in LINES_AN_OPENING):
            continue
        if abs(laid["z"][1]) > 0.7:
            continue  # a floor or roof piece faces up or down, never into a doorway
        # Its wall is the one its back looks toward, not the one nearest its middle: a piece at a wall's end lies
        # nearly half a facet off the wall's middle (an elbow beside the airlock's doorway slipped the check that way).
        own_bearing = bearing(laid["z"])
        for opening in every_opening:
            if abs((own_bearing - bearing(opening["normal"]) + 180) % 360 - 180) > 12:
                continue  # judged only against its own wall's openings
            if in_front(laid, opening):
                found.append((index, laid["kind"], opening["name"]))
    return found


def main():
    layout = json.loads(pathlib.Path(sys.argv[1]).read_text())
    found = clashes(layout)
    for entry in found:
        print(*entry)
    print(len(found), "pieces in front of an opening")


if __name__ == "__main__":
    main()
