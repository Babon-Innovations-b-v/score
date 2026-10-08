"""A kit room's shell as the surface and placement checks judge it (job world1-finish2, 2026-10-09: both checks were
shaped for the hub, so on the garage and the hangar they measured every piece against the hub's twelve walls and its
openings and gave hundreds of false findings): its walls as the hosts wall gear hangs on, and its real openings.

    import shell
    walls = shell.walls(layout)        # [{"name", "middle", "normal", "along", "half", "over"}]
    wall = shell.wall_of(walls, point)  # the wall a point stands nearest
    openings = shell.openings(layout)  # [{"name", "middle", "normal", "along", "box"}]

Two shells are known. The hub's is faceted, from its own constants (hub_kit.py: twelve walls APOTHEM out, the
doorways and the porthole). A rounded room's (the modules room_kit.py lays, and the bays bay_kit.py lays on it) is
from its inventory's numbers (`room.layout`): the walls are its outline's straight runs and corner steps, the openings
its door spots' doorways and its big door. Any other place has no shell these checks know, and they stop on it.

A wall's `middle` is the middle of its inside face on the floor, `normal` its outward normal, `along` its direction
along the wall, `half` its half width and `over` how far a piece may reach past its ends (a rounded room's panels lap
LAP past each end of their run). An opening's `box` is (across low, across high, bottom, top) in its wall's frame,
across from its middle.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools/props/scene"))
import hub_kit  # noqa: E402
import room_kit  # noqa: E402

sys.path.insert(0, str(HERE))
import greybox  # noqa: E402

INVENTORIES = REPO / "data/inventory"
HUB_OVER = 0.01


def rounded_numbers(layout):
    """A rounded room's numbers (its inventory's `room.layout`); None for the hub or a place with no rounded room."""
    path = INVENTORIES / f"{layout.get('room', '')}.json"
    if layout.get("room") == "hub" or not path.exists():
        return None
    numbers = json.loads(path.read_text()).get("room", {}).get("layout")
    return numbers if isinstance(numbers, dict) and "inside" in numbers else None


def is_hub(layout):
    return layout.get("room") == "hub"


def in_room_frame(layout):
    """Whether every piece is a kind of the room itself, laid in its frame (a door leaf's kit is in the leaf's own)."""
    return all(laid["kind"].startswith(f"{layout.get('room')}_") for laid in layout["pieces"])


def known(layout):
    """Stop on a place whose shell these checks do not know, rather than judge it against another room's."""
    if not in_room_frame(layout) or (not is_hub(layout) and rounded_numbers(layout) is None):
        raise SystemExit(f"no shell known for {layout.get('room')!r} in this layout's frame: the hub and the rounded "
                         "rooms are judged in their own")


def flat_to_room(point):
    """An (x, z) point or direction as one in the room's frame on the floor."""
    return np.array([point[0], 0.0, point[1]], dtype=np.float64)


def hub_walls():
    """The hub's twelve walls, each a facet APOTHEM out."""
    found = []
    for bearing in range(0, 360, 30):
        normal, along = hub_kit.bearing_vectors(bearing)
        found.append({"name": str(bearing), "middle": normal * hub_kit.APOTHEM, "normal": normal, "along": along,
                      "half": hub_kit.FACET_WIDE / 2, "over": HUB_OVER})
    return found


def rounded_walls(numbers):
    """A rounded room's walls: every straight run and corner step of its outline (room_kit.sides)."""
    found = []
    for side in room_kit.sides(numbers):
        run = side["end"] - side["start"]
        length = float(np.linalg.norm(run))
        found.append({"name": side["name"], "middle": flat_to_room((side["start"] + side["end"]) / 2),
                      "normal": flat_to_room(side["outward"]), "along": flat_to_room(run / length),
                      "half": length / 2, "over": room_kit.LAP / 2 + HUB_OVER})
    return found


def walls(layout):
    known(layout)
    return hub_walls() if is_hub(layout) else rounded_walls(rounded_numbers(layout))


def wall_of(every_wall, point):
    """The wall a point stands nearest, by its distance to each wall's inside face within the wall's width."""
    point = np.array([point[0], 0.0, point[2]], dtype=np.float64)

    def distance(wall):
        offset = point - wall["middle"]
        past = max(0.0, abs(float(offset @ wall["along"])) - wall["half"])
        return float(np.hypot(float(offset @ wall["normal"]), past))
    return min(every_wall, key=distance)


def hub_openings():
    """The hub's doorways and its porthole (greybox.openings: the shell's own constants) as boxes, named by bearing; the
    porthole's box is the square round its circle."""
    openings = []
    for bearing, kind, numbers in greybox.openings():
        if kind == "doorway":
            box = (-numbers[0] / 2, numbers[0] / 2, 0.0, numbers[1])
        else:
            box = (-numbers[1], numbers[1], numbers[0] - numbers[1], numbers[0] + numbers[1])
        normal, along = hub_kit.bearing_vectors(bearing)
        openings.append({"name": f"{kind} {bearing}", "middle": normal * hub_kit.APOTHEM, "normal": normal,
                         "along": along, "box": box})
    return openings


def rounded_openings(numbers):
    """A rounded room's doorways at its door spots (room_kit.DOORWAY) and its big door, each in its wall's middle."""
    spots = [(name, "doorway", room_kit.DOORWAY) for name in numbers["doors"]]
    big = numbers.get("big_door")
    if big:
        spots.append((big["wall"], "big door", (big["wide"], big["high"])))
    openings = []
    for name, kind, (wide, tall) in spots:
        side = room_kit.side_named(numbers, name)
        run = side["end"] - side["start"]
        openings.append({"name": f"{kind} {name}", "middle": flat_to_room((side["start"] + side["end"]) / 2),
                         "normal": flat_to_room(side["outward"]), "along": flat_to_room(run / np.linalg.norm(run)),
                         "box": (-wide / 2, wide / 2, 0.0, tall)})
    return openings


def openings(layout):
    known(layout)
    return hub_openings() if is_hub(layout) else rounded_openings(rounded_numbers(layout))


def roof_plates(layout):
    """A rounded room's roof plates as laid (its dome's or its flat roof's), the hosts its roof gear hangs from."""
    return [laid for laid in layout["pieces"] if laid["kind"] == f"{layout['room']}_roof_face_panel"]
