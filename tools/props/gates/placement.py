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
import greybox  # noqa: E402
from room import hub_kit  # noqa: E402

MARGIN = 0.05
LINES_AN_OPENING = ("hatch_frame", "hatch_wall_surround", "porthole_panel", "backer", "hatch_hinge", "hatch_leaf",
                    "hatch_wheel", "hatch_window",
                    "skirting", "cornice", "floor_plate", "tread_mat")


def footprint(laid, normal, along):
    """The piece's laid box seen straight through the wall: (across low, across high, up low, up high, out)."""
    corners = []
    origin = np.array(laid["at"])
    for x in (-0.5, 0.5):
        for y in (0.0, 1.0):
            for z in (-0.5, 0.5):
                corners.append(origin + np.array(laid["x"]) * x * laid["size"][0]
                               + np.array(laid["y"]) * y * laid["size"][1] + np.array(laid["z"]) * z * laid["size"][2])
    corners = np.array(corners)
    across = corners @ along
    return across.min(), across.max(), corners[:, 1].min(), corners[:, 1].max(), float((corners @ normal).max())


def clashes(layout):
    """Every piece in front of an opening: (index, kind, opening)."""
    found = []
    for index, laid in enumerate(layout["pieces"]):
        if any(word in laid["kind"] for word in LINES_AN_OPENING):
            continue
        if abs(laid["z"][1]) > 0.7:
            continue  # a floor or roof piece faces up or down, never into a doorway
        own_bearing = float(np.degrees(np.arctan2(laid["at"][0], -laid["at"][2])) % 360)
        for bearing, kind, numbers in greybox.openings():
            if abs((own_bearing - bearing + 180) % 360 - 180) > 12:
                continue  # judged only against its own wall's openings
            normal, along = hub_kit.bearing_vectors(bearing)
            low, high, bottom, top, out = footprint(laid, normal, along)
            if out < hub_kit.APOTHEM - 0.6:
                continue
            if kind == "doorway":
                box = (-numbers[0] / 2, numbers[0] / 2, 0.0, numbers[1])
            else:
                box = (-numbers[1], numbers[1], numbers[0] - numbers[1], numbers[0] + numbers[1])
            if low < box[1] + MARGIN and high > box[0] - MARGIN and bottom < box[3] + MARGIN and top > box[2] - MARGIN:
                found.append((index, laid["kind"], f"{kind} {bearing}"))
    return found


def main():
    layout = json.loads(pathlib.Path(sys.argv[1]).read_text())
    found = clashes(layout)
    for entry in found:
        print(*entry)
    print(len(found), "pieces in front of an opening")


if __name__ == "__main__":
    main()
