"""The "lies on its surface" check (G6 of the robust route, round two, 2026-10-06; the owner: "the random stuff
sticking out of the roof is still there"): every piece hung on a wall or a roof face sits flush on its host plane,
turned to it, and stays inside its host face.

    ~/.farm-factory-props/env/bin/python tools/props/gates/surface.py <layout.json>

    roof gear   kinds named ceiling_*: the host is the roof face under the piece's foot; the foot (y 0) must lie on
                the face's underside, the piece's height (y) must point straight into the room, and its whole foot
                must stay inside that face
    wall gear   pieces hung on a wall (group `hangs`, standing upright, out past the walkway): the back must sit on
                the wall within its lining's depth, face straight out of it, and stay inside the wall's width

The envelope test cannot see a tray laid the wrong way inside the room; this can (the hub kit's trays lay radially
at the corners, sticking out across the lattice).
"""
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import room  # noqa: E402
from room import hub_kit  # noqa: E402

FLUSH = 0.03
TURN_DEGREES = 5.0
LINING_DEEPEST = 0.3  # the deepest lining (0.12) and a pipe bracket (0.15) stand gear this far off
WALKWAY_OUT = 3.9
# Hung pieces whose host is not one wall: a door's own parts, and the posts standing in a corner between two walls.
NOT_ON_ONE_WALL = ("hatch_", "airlock_", "door_strip", "grab_bar", "corner_post")


def facet_of(point):
    """The wall (and roof face) a point stands over: its bearing, a multiple of 30."""
    return (round(float(room.bearing_of(np.array([point]))[0]) / 30) * 30) % 360


def roof_plane(bearing):
    """A roof face's underside as (a point on it, its normal into the room)."""
    normal, along = hub_kit.bearing_vectors(bearing)
    foot = normal * hub_kit.APOTHEM + np.array([0.0, hub_kit.WALL_HIGH, 0.0])
    up_slope = np.array([0.0, hub_kit.RISE, 0.0]) - normal * hub_kit.APOTHEM
    into_room = np.cross(up_slope / np.linalg.norm(up_slope), along)
    return foot, into_room if into_room[1] < 0 else -into_room


def inside_face(point, bearing):
    """Whether a point lies over its face: within the facet's width at that height on the roof (the face narrows to
    the apex), across the wall's width on a wall."""
    normal, along = hub_kit.bearing_vectors(bearing)
    reach = float(point @ normal)
    half = hub_kit.FACET_WIDE / 2 * max(0.0, reach / hub_kit.APOTHEM) if point[1] > hub_kit.WALL_HIGH else \
        hub_kit.FACET_WIDE / 2
    return abs(float(point @ along)) <= half + 0.01


def corners(laid, depth):
    """A piece's four foot corners (y 0) at `depth` along its z (-0.5 front, 0.5 back)."""
    origin, x, z = np.array(laid["at"]), np.array(laid["x"]), np.array(laid["z"])
    wide, _, deep = laid["size"]
    return [origin + x * side * wide / 2 + z * depth * deep for side in (-0.5, 0.5) for depth in (-0.5, 0.5)][:4]


def roof_faults(laid):
    """What is wrong with a roof-hung piece's seat: a list of plain findings."""
    bearing = facet_of(laid["at"])
    point, into_room = roof_plane(bearing)
    found = []
    gap = abs(float((np.array(laid["at"]) - point) @ into_room))
    if gap > FLUSH:
        found.append(f"foot {gap:.2f} m off the roof face")
    turn = math.degrees(math.acos(min(1.0, abs(float(np.array(laid["y"]) @ into_room)))))
    if turn > TURN_DEGREES:
        found.append(f"turned {turn:.0f} degrees from the roof face")
    if not all(inside_face(corner, bearing) for corner in corners(laid, 0.0)):
        found.append("reaches past its roof face")
    return found


def wall_faults(laid):
    """What is wrong with a wall-hung piece's seat."""
    bearing = facet_of(laid["at"])
    normal, _ = hub_kit.bearing_vectors(bearing)
    back = np.array(laid["at"]) + np.array(laid["z"]) * laid["size"][2] / 2
    found = []
    depth = hub_kit.APOTHEM - float(back @ normal)
    if not -FLUSH <= depth <= LINING_DEEPEST:
        found.append(f"back {depth:.2f} m off the wall")
    turn = math.degrees(math.acos(min(1.0, abs(float(np.array(laid["z"]) @ normal)))))
    if turn > TURN_DEGREES:
        found.append(f"turned {turn:.0f} degrees from the wall")
    if not all(inside_face(corner, bearing) for corner in corners(laid, 0.5)):
        found.append("reaches past its wall")
    return found


def is_wall_gear(laid, about):
    """A piece hung on a wall: group `hangs`, standing upright, out past the walkway, on the ring's floor; a door's
    own parts (frames lining the opening, leaves and hinges swung open) and corner posts have hosts of their own."""
    reach = math.hypot(laid["at"][0], laid["at"][2])
    own_host = any(word in laid["kind"] for word in NOT_ON_ONE_WALL)
    return about.get("group") == "hangs" and abs(laid["y"][1]) > 0.99 and reach > WALKWAY_OUT and \
        laid["at"][1] >= 0.0 and laid.get("layer", 1) == 1 and not own_host


def faults(layout):
    """Every hung piece off its surface: (index, kind, findings)."""
    found = []
    for index, laid in enumerate(layout["pieces"]):
        about = layout["kinds"].get(laid["kind"], {})
        if "ceiling_" in laid["kind"]:
            problems = roof_faults(laid)
        elif is_wall_gear(laid, about):
            problems = wall_faults(laid)
        else:
            continue
        if problems:
            found.append((index, laid["kind"], problems))
    return found


def main():
    layout = json.loads(pathlib.Path(sys.argv[1]).read_text())
    found = faults(layout)
    for index, kind, problems in found:
        print(index, kind, "; ".join(problems))
    print(len(found), "pieces off their surface")


if __name__ == "__main__":
    main()
