"""The "lies on its surface" check (G6 of the robust route, round two, 2026-10-06; the owner: "the random stuff
sticking out of the roof is still there"): every piece hung on a wall or a roof face sits flush on its host plane,
turned to it, and stays inside its host face.

    ~/.farm-factory-props/env/bin/python tools/props/gates/surface.py <layout.json>

    roof gear   kinds named ceiling_*: the host is the roof face under the piece's foot; the foot (y 0) must lie on
                the face's underside, the piece's height (y) must point straight into the room, and its whole foot
                must stay inside that face; in a rounded room the host is the laid roof plate the piece hangs from,
                by its foot or, standing up to the roof, by its head
    wall gear   pieces hung on a wall (group `hangs`, standing upright, within WALL_REACH of their wall): the back
                must sit on the wall within its lining's depth, face straight out of it, and stay inside the wall's
                width; the walls are the room's own (shell.py)
    floor gear  pieces set into the floor (`set_in`: a mat, a grating, a machine bay's plate): a plate, no thicker
                than SET_IN_THICKEST (the garage's and the hangar's bay plates were laid 4.6 and 7.2 m thick, their
                rows' depth and height swapped, and the review cameras framed them from under the floor)

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
import shell  # noqa: E402
from room import hub_kit  # noqa: E402

FLUSH = 0.03
TURN_DEGREES = 5.0
LINING_DEEPEST = 0.3  # the deepest lining (0.12) and a pipe bracket (0.15) stand gear this far off
# How far in from its wall's face a hung piece's origin may stand and still be judged as hung on it: the hub's walkway
# ends 3.9 m out, 0.6 m in from its walls.
WALL_REACH = 0.6
# How far past a roof plate's edge a point still lies under it: the plates lap, and a dome's corner steps meet at a
# slant.
PLATE_EDGE = 0.03
# The thickest a piece set into the floor may be: the deck's gratings are 0.054 m, a mat 0.02.
SET_IN_THICKEST = 0.1
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


def corners(laid):
    """A piece's four foot corners (y 0), front and back. As measured so far they reach a quarter of its width each
    way (side is +-0.5 and halved again), not a half; kept so the findings stay the same (#3)."""
    origin, x, z = np.array(laid["at"]), np.array(laid["x"]), np.array(laid["z"])
    wide, _, deep = laid["size"]
    return [origin + x * side * wide / 2 + z * end * deep for side in (-0.5, 0.5) for end in (-0.5, 0.5)]


def turn_from(axis, normal):
    """Degrees between a piece's axis and its host's normal, either way along it."""
    return math.degrees(math.acos(min(1.0, abs(float(np.array(axis) @ normal)))))


def seat_faults(foot, plane, axis, host):
    """A roof-hung piece's foot off its host plane (a point on it, its normal into the room), or its `axis` turned
    from it."""
    point, into_room = plane
    found = []
    gap = abs(float((foot - point) @ into_room))
    if gap > FLUSH:
        found.append(f"foot {gap:.2f} m off the {host}")
    turn = turn_from(axis, into_room)
    if turn > TURN_DEGREES:
        found.append(f"turned {turn:.0f} degrees from the {host}")
    return found


def roof_faults(laid):
    """What is wrong with a roof-hung piece's seat: a list of plain findings."""
    bearing = facet_of(laid["at"])
    found = seat_faults(np.array(laid["at"]), roof_plane(bearing), laid["y"], "roof face")
    if not all(inside_face(corner, bearing) for corner in corners(laid)):
        found.append("reaches past its roof face")
    return found


def wall_faults(laid, wall):
    """What is wrong with a wall-hung piece's seat on its wall (shell.walls)."""
    back = np.array(laid["at"]) + np.array(laid["z"]) * laid["size"][2] / 2
    found = []
    depth = float((wall["middle"] - back) @ wall["normal"])
    if not -FLUSH <= depth <= LINING_DEEPEST:
        found.append(f"back {depth:.2f} m off the wall")
    turn = turn_from(laid["z"], wall["normal"])
    if turn > TURN_DEGREES:
        found.append(f"turned {turn:.0f} degrees from the wall")
    reach = wall["half"] + wall["over"]
    if not all(abs(float((corner - wall["middle"]) @ wall["along"])) <= reach for corner in corners(laid)):
        found.append("reaches past its wall")
    return found


def plate_face(plate):
    """A roof plate's face into the room: (a point on it, its normal into the room)."""
    return np.array(plate["at"]) - np.array(plate["z"]) * plate["size"][2] / 2, -np.array(plate["z"])


def over_plate(point, plate):
    """Whether a point, seen square to a roof plate, lies over it: within its height and its width at that height (a
    plate is laid as a trapezoid, `taper` its head's width over its foot's)."""
    face, _ = plate_face(plate)
    offset = np.asarray(point) - face
    wide, tall, _ = plate["size"]
    along = float(offset @ np.array(plate["y"]))
    if not -PLATE_EDGE <= along <= tall + PLATE_EDGE:
        return False
    share = min(max(along / tall, 0.0), 1.0)
    half = wide / 2 * (1 + (plate.get("taper", 1.0) - 1) * share)
    return abs(float(offset @ np.array(plate["x"]))) <= half + PLATE_EDGE


def plate_over(point, plates):
    """The roof plate a point hangs from: the nearest of those it lies square under; None when it lies under none."""
    under = [plate for plate in plates if over_plate(point, plate)]
    if not under:
        return None
    return min(under, key=lambda plate: abs(float((np.asarray(point) - plate_face(plate)[0]) @ plate_face(plate)[1])))


def plate_faults(laid, plates):
    """What is wrong with a roof-hung piece's seat in a rounded room: its host is the roof plate its foot hangs from
    (shell.roof_plates), as roof_faults judges the hub's roof face. The piece hangs by the end of its height that
    faces the roof: its foot when its height points down into the room (the hub's way), its head when it points up
    (room_kit lays a roof row standing, its head at the roof)."""
    foot = np.array(laid["at"])
    if laid["y"][1] > 0:
        foot = foot + np.array(laid["y"]) * laid["size"][1]
    host = plate_over(foot, plates)
    if host is None:
        return ["hangs under no roof plate"]
    found = seat_faults(foot, plate_face(host), laid["y"], "roof plate")
    if not all(plate_over(corner, plates) for corner in corners(laid)):
        found.append("reaches past the roof's plates")
    return found


def floor_faults(laid):
    """What is wrong with a piece set into the floor: its thickness (its z, square to the floor) past a plate's."""
    thick = laid["size"][2]
    if thick > SET_IN_THICKEST:
        return [f"set into the floor {thick:.2f} m thick, past a plate's {SET_IN_THICKEST} m (its size's sides swapped?)"]
    return []


def is_wall_gear(laid, about, wall):
    """A piece hung on a wall: group `hangs`, standing upright, out past the walkway (within WALL_REACH of its wall's
    face), on the floor's level; a door's own parts (frames lining the opening, leaves and hinges swung open) and
    corner posts have hosts of their own, and a floor rise's face (`rise`: a wall panel's model standing on the floor
    as a step's or a ledge's side, greenhouse_kit.rise_faces) stands on the floor, hung on no wall."""
    reach = float((wall["middle"] - np.array(laid["at"])) @ wall["normal"])
    own_host = any(word in laid["kind"] for word in NOT_ON_ONE_WALL)
    return about.get("group") == "hangs" and abs(laid["y"][1]) > 0.99 and reach < WALL_REACH and \
        laid["at"][1] >= 0.0 and laid.get("layer", 1) == 1 and not own_host and "rise" not in laid


def faults(layout):
    """Every hung piece off its surface: (index, kind, findings). A glowing part split from a piece (`part`: a
    screen's content, a lamp's lens) sits on its host's front and is judged with its host."""
    walls = shell.walls(layout)
    plates = shell.roof_plates(layout)
    found = []
    for index, laid in enumerate(layout["pieces"]):
        if "part" in laid:
            continue
        about = layout["kinds"].get(laid["kind"], {})
        wall = shell.wall_of(walls, laid["at"])
        if laid.get("set_in"):
            problems = floor_faults(laid)
        elif "ceiling_" in laid["kind"]:
            problems = roof_faults(laid) if shell.is_hub(layout) else plate_faults(laid, plates)
        elif is_wall_gear(laid, about, wall):
            problems = wall_faults(laid, wall)
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
