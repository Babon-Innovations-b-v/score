"""The cockpit kit (the capsule lock, owner 2026-11-23: "messy meshes, no panels, ugly walls, way to big for the
cockpit"): a small craft's inside built in code at its real size, every piece one mesh `geo` of named parts for the
place's palette, as the dome shell algorithm's blocks are, so nothing inside the cockpit is a picture-made mesh.

    write(path, kind, sizes)    the piece of `kind` (KINDS) with its `sizes` written as a USD file at `path`; its parts

Every piece is built facing +z (its front toward the one looking at it, its back on z = 0, x to that one's right, y
up) and written turned half round y, so laid with a wall's turn (Cone.turn) its front faces the room and a word on it
reads left to right from inside. A floor piece (a seat, the console) is laid with its own turn. `FLAT_KINDS` (the
capsule's own body) are built in the capsule's frame (y up the cone's axis, the floor's top at y = 0, the room's
front +z) and written as built.

The capsule's body, each a closed piece over its cone (Cone: `radius`, `slope`, `hull`, `lining`, ... as CONE):
- `hull`: the smooth pressure hull, its round `holes` [[theta, y, r]] (portholes, hatch) open for their sleeves and
  the cut-away (`cut` [theta, half theta, y, half y, power]) its "main" body's gap and its "plug" (`which`).
- `lining`: the quilted vinyl lining from the floor to the ceiling, one piece: courses of flat full pads with thin
  seams, a bolster along the floor, eased flat round each hole (`fades`) and under each panel (`flats`, flat_spot);
  holes and cut-away as the hull's.
- `ceiling` (its lamps' spots flat), `floor` (the round plate, the walked ground), `skirt` (the service ring under
  the hull, its pipes), `nose`, `lip` (the cut-away's rounded rim), `through_wall` (a porthole's or the hatch's
  sleeve, flanges hugging the lining and the hull, bolts, glass), `hatch_leaf`, `gantry` (the railed walkway).
- `panel`: a plate with rounded corners, a raised bezel, a label strip with its word in modelled letters, and its
  `items` ({kind, at [u, v], ...}: the hardware below) laid on it.
- the hardware, each its own piece or an item of a panel: `toggle` (a 2 cm bat toggle, `guard` a red flip cover),
  `lamp` (`colour` red, green, amber, white), `gauge` (a 6 cm round needle gauge), `bars` (a bar meter, up or
  `across`), `readout` (a small lit number window), `screen` (`graphic` tower, orbit, attitude, landing, lines),
  `scope` (a round scope), `keypad`, `button`, `rotary`, `wheel`, `slider`, `beacon`, `words` (lettering alone).
- `console`, `switch_box`, `seat`, `throttle`, `stick`, `lamp_fixture`.
"""
import math

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade, Vt

from score.stages.place_build import dome_shell

SEGMENTS = 32  # points round a turned piece
SEAM = 0.007  # metres between two cushions (the stitched seam the backing shows)
PLATE = 0.012  # a panel plate's thickness
BEZEL = 0.006  # how far a panel's bezel stands over its plate
LETTER_ROWS = 7  # the lettering's dot rows (a 5 x 7 face)
LINE = 0.0025  # a screen graphic's line width
FLAT_KINDS = ("hull", "lining", "ceiling", "floor", "skirt", "nose", "lip", "through_wall", "tread", "gantry")

FONT = {
    "A": (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    "C": (" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "),
    "D": ("#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"),
    "H": ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "I": (" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "J": ("  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "#   #", "##  #", "# # #", "#  ##", "#   #", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "),
    "X": ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    "Y": ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    "0": (" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": ("  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    ".": ("     ", "     ", "     ", "     ", "     ", "     ", "  #  "),
}


# --- shapes: each a (part, points, triangles, smooth) piece ----------------------------------------------------------

def piece(part, points, triangles, smooth):
    """One piece: its part, points (n x 3), triangles (m x 3, wound to face out) and whether it shades smooth."""
    return (part, np.asarray(points, dtype=np.float64).reshape(-1, 3), np.asarray(triangles, dtype=np.int64)
            .reshape(-1, 3), bool(smooth))


def moved(pieces, rotation=None, offset=(0.0, 0.0, 0.0)):
    """The pieces turned by `rotation` (3 x 3) and moved by `offset`."""
    turn = np.eye(3) if rotation is None else np.asarray(rotation, dtype=np.float64)
    return [(part, points @ turn.T + np.asarray(offset, dtype=np.float64), triangles, smooth)
            for part, points, triangles, smooth in pieces]


def about(axis, degrees):
    """The rotation of `degrees` about the x, y or z axis."""
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    return {"x": [[1, 0, 0], [0, cos, -sin], [0, sin, cos]], "y": [[cos, 0, sin], [0, 1, 0], [-sin, 0, cos]],
            "z": [[cos, -sin, 0], [sin, cos, 0], [0, 0, 1]]}[axis]


def box(part, low, high, bevel=0.002):
    """A closed box from `low` to `high`, its edges chamfered `bevel` (dome_shell.chamfered_box), shaded flat."""
    points, triangles = dome_shell.chamfered_box(low, high, bevel)
    return [piece(part, points, triangles, False)]


def oriented(points, triangles, outward):
    """The triangles wound so the first faces along `outward`."""
    first = points[triangles[0]]
    normal = np.cross(first[1] - first[0], first[2] - first[0])
    return triangles if np.dot(normal, outward) >= 0 else triangles[:, ::-1]


def edge_coordinates(low, high, radius, steps, inside):
    """Along one axis, the grid lines of a rounded box's face: `steps` round each rounded edge (spaced so they fall
    evenly round its arc) and `inside` across its flat middle."""
    inner_low, inner_high = low + radius, high - radius
    arc = radius * np.tan(np.linspace(0.0, math.pi / 4, steps + 1))
    middle = np.linspace(inner_low, inner_high, inside + 1)
    return np.unique(np.round(np.concatenate([inner_low - arc[::-1], middle, inner_high + arc]), 9))


def rounded_box(part, low, high, radius, puff=0.0, steps=3, inside=6, narrow=None):
    """A closed box from `low` to `high` with every edge rounded `radius` (a pillow, a cushion, a key), its front
    (+z) face swollen `puff` metres at its middle, shaded smooth; `narrow` [front half width share] draws its x in
    toward its front (a wedge of the bench ring, wider at the wall than at the room)."""
    low, high = np.asarray(low, dtype=np.float64), np.asarray(high, dtype=np.float64)
    radius = min(float(radius), float((high - low).min()) / 2 - 1e-5)
    inner_low, inner_high = low + radius, high - radius
    lines = [edge_coordinates(low[axis], high[axis], radius, steps, inside) for axis in range(3)]
    points, triangles = [], []
    for axis in range(3):
        across, up = [other for other in range(3) if other != axis]
        for side in (-1, 1):
            first = len(points)
            grid_a, grid_b = np.meshgrid(lines[across], lines[up], indexing="ij")
            face = np.zeros(grid_a.shape + (3,))
            face[..., across], face[..., up] = grid_a, grid_b
            face[..., axis] = high[axis] if side > 0 else low[axis]
            points += face.reshape(-1, 3).tolist()
            rows, cols = grid_a.shape
            index = np.arange(rows * cols).reshape(rows, cols) + first
            quads = np.stack([index[:-1, :-1], index[1:, :-1], index[1:, 1:], index[:-1, 1:]], axis=-1).reshape(-1, 4)
            outward = np.zeros(3)
            outward[axis] = side
            corners = np.asarray(points)
            made = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
            triangles += oriented(corners, made, outward).tolist()
    points = np.asarray(points)
    clamped = np.clip(points, inner_low, inner_high)
    offset = points - clamped
    length = np.linalg.norm(offset, axis=1, keepdims=True)
    points = clamped + offset / np.maximum(length, 1e-12) * radius
    if puff:
        half = (high - low) / 2
        middle = (high + low) / 2
        share = np.clip(1 - ((points[:, :2] - middle[:2]) / half[:2]) ** 2, 0, 1) ** 0.6
        front = np.clip((points[:, 2] - middle[2]) / half[2], 0, 1)
        points[:, 2] += puff * share[:, 0] * share[:, 1] * front
    if narrow is not None:
        depth = np.clip((points[:, 2] - low[2]) / (high[2] - low[2]), 0, 1)
        middle_x = (high[0] + low[0]) / 2
        points[:, 0] = middle_x + (points[:, 0] - middle_x) * (1 - (1 - float(narrow)) * depth)
    return [piece(part, points, triangles, True)]


def turned(part, profile, segments=SEGMENTS, smooth=False, sweep=360.0):
    """A piece turned about z from `profile` [(radius, z)] (a ring of SEGMENTS round each point; a point of radius 0
    a pole), the profile walked up its outside and in across its top, so each face looks to the profile's right
    ((dz, -dr): out, up, in, down); each step of the profile its own band, shaded smooth round and flat across unless
    `smooth`."""
    angles = np.radians(np.linspace(0.0, sweep, segments + 1)[:-1] if sweep >= 360 else
                        np.linspace(0.0, sweep, segments + 1))
    closed = sweep >= 360
    count = len(angles)
    bands = [profile] if smooth else [profile[number:number + 2] for number in range(len(profile) - 1)]
    pieces = []
    for band in bands:
        points = [(radius * math.cos(angle), radius * math.sin(angle), height)
                  for radius, height in band for angle in angles]
        triangles = []
        for ring in range(len(band) - 1):
            for step in range(count if closed else count - 1):
                here, there = ring * count + step, ring * count + (step + 1) % count
                below, beyond = here + count, there + count
                triangles += [[here, there, beyond], [here, beyond, below]]
        points = np.asarray(points)
        triangles = np.asarray(triangles)
        fixed = []
        for triangle in triangles:
            ring = min(triangle) // count
            (radius_a, height_a), (radius_b, height_b) = band[ring], band[ring + 1]
            corners = points[triangle]
            centre = corners.mean(axis=0)
            radial = np.array([centre[0], centre[1], 0.0])
            radial /= max(np.linalg.norm(radial), 1e-12)
            expected = (height_b - height_a) * radial + np.array([0.0, 0.0, radius_a - radius_b])
            normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
            fixed.append(triangle[::-1] if np.dot(normal, expected) < 0 else triangle)
        triangles = np.asarray(fixed)
        pieces.append(piece(part, points, triangles, True))
    return pieces


def outline_slab(part, outline, low, high):
    """A closed slab of the plan `outline` [(x, y)] (convex, counter-clockwise) from z `low` to `high`: its faces
    flat, its sides smooth round its corners."""
    outline = np.asarray(outline, dtype=np.float64)
    count = len(outline)
    centre = outline.mean(axis=0)
    top = [(centre[0], centre[1], high)] + [(x, y, high) for x, y in outline]
    bottom = [(centre[0], centre[1], low)] + [(x, y, low) for x, y in outline]
    fan = [[0, 1 + step, 1 + (step + 1) % count] for step in range(count)]
    side = [(x, y, low) for x, y in outline] + [(x, y, high) for x, y in outline]
    walls = []
    for step in range(count):
        here, there = step, (step + 1) % count
        walls += [[here, there, there + count], [here, there + count, here + count]]
    return [piece(part, top, fan, False), piece(part, bottom, [face[::-1] for face in fan], False),
            piece(part, side, walls, True)]


def rounded_rectangle(wide, high, corner, steps=6):
    """The counter-clockwise plan of a rectangle `wide` x `high` round its middle, its corners rounded `corner`."""
    corner = min(corner, wide / 2 - 1e-4, high / 2 - 1e-4)
    found = []
    for centre_x, centre_y, start in ((wide / 2 - corner, -high / 2 + corner, -90), (wide / 2 - corner,
                                      high / 2 - corner, 0), (-wide / 2 + corner, high / 2 - corner, 90),
                                      (-wide / 2 + corner, -high / 2 + corner, 180)):
        for step in range(steps + 1):
            angle = math.radians(start + 90 * step / steps)
            found.append((centre_x + corner * math.cos(angle), centre_y + corner * math.sin(angle)))
    return found


def frame_ring(part, outer, inner, low, high):
    """A closed ring between the plans `outer` and `inner` (each counter-clockwise, as many points) from z `low` to
    `high`: a bezel round a plate or a screen."""
    outer, inner = np.asarray(outer, dtype=np.float64), np.asarray(inner, dtype=np.float64)
    count = len(outer)
    points = ([(x, y, high) for x, y in outer] + [(x, y, high) for x, y in inner] + [(x, y, low) for x, y in outer]
              + [(x, y, low) for x, y in inner])
    top, bottom = [], []
    for step in range(count):
        here, there = step, (step + 1) % count
        top += [[here, there, count + there], [here, count + there, count + here]]
        bottom += [[2 * count + here, 3 * count + there, 2 * count + there],
                   [2 * count + here, 3 * count + here, 3 * count + there]]
    outer_side = [(x, y, low) for x, y in outer] + [(x, y, high) for x, y in outer]
    inner_side = [(x, y, low) for x, y in inner] + [(x, y, high) for x, y in inner]
    walls_out, walls_in = [], []
    for step in range(count):
        here, there = step, (step + 1) % count
        walls_out += [[here, there, there + count], [here, there + count, here + count]]
        walls_in += [[here, there + count, there], [here, here + count, there + count]]
    return [piece(part, points, top + bottom, False), piece(part, outer_side, walls_out, True),
            piece(part, inner_side, walls_in, True)]


def tube(part, path, radius, segments=12):
    """A round bar of `radius` along the polyline `path` [(x, y, z)], its ends closed, shaded smooth round."""
    path = np.asarray(path, dtype=np.float64)
    tangents = np.gradient(path, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    helper = np.array([0.0, 1.0, 0.0]) if abs(tangents[0][1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    side = np.cross(tangents[0], helper)
    points = []
    for point, tangent in zip(path, tangents):
        side = side - np.dot(side, tangent) * tangent
        side /= np.linalg.norm(side)
        other = np.cross(tangent, side)
        points += [point + radius * (math.cos(angle) * side + math.sin(angle) * other)
                   for angle in np.linspace(0, 2 * math.pi, segments + 1)[:-1]]
    points = np.asarray(points)
    triangles = []
    for ring in range(len(path) - 1):
        for step in range(segments):
            here, there = ring * segments + step, ring * segments + (step + 1) % segments
            triangles += [[here, there, there + segments], [here, there + segments, here + segments]]
    fixed = []
    for triangle in triangles:
        corners = points[triangle]
        normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        ring = triangle[0] // segments
        fixed.append(triangle[::-1] if np.dot(normal, corners.mean(axis=0) - path[ring]) < 0 else triangle)
    pieces = [piece(part, points, fixed, True)]
    for end, sign in ((0, -1.0), (len(path) - 1, 1.0)):
        ring = points[end * segments:(end + 1) * segments]
        cap_points = np.vstack([ring, path[end][None]])
        cap = np.array([[segments, step, (step + 1) % segments] for step in range(segments)])
        pieces.append(piece(part, cap_points, oriented(cap_points, cap, sign * tangents[end]), False))
    return pieces


def ribbon(part, path, width, height, thick=0.0007):
    """A thin line `width` wide along the 2-D `path` [(x, y)], lying on z = `height` (sunk a little into what is
    under it) and `thick` proud of it, each stretch a closed slab (a screen's graphic, a dial's tick)."""
    found = []
    low, high = height - 0.0003, height + thick
    for start, end in zip(path[:-1], path[1:]):
        start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
        along = end - start
        length = np.linalg.norm(along)
        if length < 1e-9:
            continue
        across = np.array([-along[1], along[0]]) / length * width / 2
        extend = along / length * width / 2
        corners = [start - across - extend, end - across + extend, end + across + extend, start + across - extend]
        points = [(x, y, low) for x, y in corners] + [(x, y, high) for x, y in corners]
        middle = np.mean(points, axis=0)
        for face in ([0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
            quad = np.asarray([points[index] for index in face])
            found.append(piece(part, quad, oriented(quad, np.array([[0, 1, 2], [0, 2, 3]]),
                                                    quad.mean(axis=0) - middle), False))
    return found


def lettering(part, text, high, depth=0.0012, align="middle"):
    """`text` in modelled letters `high` metres tall (FONT's 5 x 7 face, each lit run of dots one box), standing
    `depth` over z = 0, centred on x = 0 (or starting there, `align` left), its middle at y = 0."""
    dot = high / LETTER_ROWS
    advance = 6 * dot
    wide = len(text) * advance - dot
    start = -wide / 2 if align == "middle" else 0.0
    found = []
    for number, letter in enumerate(text.upper()):
        rows = FONT.get(letter)
        if rows is None:
            continue
        left = start + number * advance
        for row, line in enumerate(rows):
            column = 0
            while column < len(line):
                if line[column] != "#":
                    column += 1
                    continue
                end = column
                while end < len(line) and line[end] == "#":
                    end += 1
                top = high / 2 - row * dot
                inset = dot * 0.04  # rows never share a face (a ray through a shared face is read once, not twice)
                found += box(part, (left + column * dot, top - dot + inset, -0.0003), (left + end * dot, top - inset,
                                                                                         depth), 0.0002)
                column = end
    return found


def circle_path(radius_x, radius_y, centre=(0.0, 0.0), steps=40, start=0.0, sweep=360.0):
    """The points of an ellipse's arc."""
    return [(centre[0] + radius_x * math.cos(math.radians(start + sweep * step / steps)),
             centre[1] + radius_y * math.sin(math.radians(start + sweep * step / steps))) for step in range(steps + 1)]


# --- hardware: each built at its own spot, its back on z = 0 --------------------------------------------------------

LAMP_PARTS = {"red": "lamp_red", "green": "lamp_green", "amber": "lamp_amber", "white": "lamp_white", "cyan": "lamp_cyan"}


def toggle(guard=False, **_):
    """A bat-handle toggle switch 2 cm tall on a small plate, thrown up, with a red flip cover held open over it
    when `guard`."""
    found = box("metal", (-0.008, -0.013, 0.0), (0.008, 0.013, 0.0015), 0.0005)
    found += turned("metal", [(0.0, 0.0012), (0.0065, 0.0012), (0.0065, 0.004), (0.0045, 0.0045), (0.0045, 0.008),
                              (0.0, 0.008)], segments=6)
    lever = turned("lever", [(0.0, 0.0), (0.0021, 0.0), (0.0017, 0.017), (0.0028, 0.0185), (0.0028, 0.0205),
                             (0.0, 0.021)], segments=12)
    found += moved(lever, about("x", -22), (0.0, 0.0, 0.007))
    if guard:
        for side in (-1, 1):
            found += box("guard", (side * 0.0095 - 0.001, -0.012, 0.0012), (side * 0.0095 + 0.001, 0.012, 0.024),
                         0.0004)
        cover = box("guard", (-0.0105, -0.026, -0.0015), (0.0105, 0.0, 0.0015), 0.0005)
        found += moved(cover, about("x", -110), (0.0, 0.012, 0.024))
    return found


def lamp(colour="green", size=0.009, **_):
    """A round indicator lamp: a bright ring and a domed lens of `colour` (LAMP_PARTS) `size` metres across."""
    radius = size / 2
    found = turned("metal", [(radius * 0.7, 0.0), (radius * 1.35, 0.0), (radius * 1.35, 0.002), (radius * 1.1, 0.004),
                             (radius * 0.95, 0.004), (radius * 0.7, 0.004), (radius * 0.7, 0.0)], segments=20)
    profile = [(0.0, 0.003)] + [(radius * math.cos(math.radians(angle)),
                                 0.003 + radius * 0.75 * math.sin(math.radians(angle))) for angle in range(0, 91, 15)]
    found += turned(LAMP_PARTS[colour], profile, segments=20, smooth=True)
    return found


def gauge(size=0.06, sweep=240.0, reading=0.35, **_):
    """A round needle gauge `size` across: a dark case, a bright bezel, a white dial with its ticks and a black
    needle at `reading` of its sweep."""
    radius = size / 2
    found = turned("dark", [(0.0, 0.0), (radius * 0.98, 0.0), (radius, 0.012), (0.0, 0.012)], segments=40)
    found += turned("metal", [(radius * 0.86, 0.0115), (radius * 1.04, 0.0115), (radius * 1.06, 0.016),
                              (radius * 0.98, 0.019), (radius * 0.86, 0.017), (radius * 0.86, 0.0115)], segments=40)
    found += turned("dial", [(0.0, 0.0118), (radius * 0.87, 0.0118), (radius * 0.87, 0.0129), (0.0, 0.0129)],
                    segments=40)
    start = 90 + sweep / 2
    for tick in range(11):
        angle = math.radians(start - sweep * tick / 10)
        inner = radius * (0.62 if tick % 5 == 0 else 0.7)
        found += ribbon("ink", [(inner * math.cos(angle), inner * math.sin(angle)),
                                (radius * 0.8 * math.cos(angle), radius * 0.8 * math.sin(angle))], 0.0019, 0.013)
    angle = math.radians(start - sweep * reading)
    found += ribbon("ink", [(-0.12 * radius * math.cos(angle), -0.12 * radius * math.sin(angle)),
                               (radius * 0.74 * math.cos(angle), radius * 0.74 * math.sin(angle))], 0.003, 0.0134)
    found += turned("ink", [(0.0, 0.0122), (radius * 0.1, 0.0122), (radius * 0.1, 0.0145), (0.0, 0.0145)], segments=12)
    return found


def bars(count=3, wide=0.05, high=0.09, levels=(0.7, 0.45, 0.85), colour="green", across=False, segments=9, **_):
    """A bar meter: `count` lit columns of `segments` in a dark window, each lit to its level (rows lit from the left
    when `across`)."""
    found = box("dark", (-wide / 2, -high / 2, 0.0), (wide / 2, high / 2, 0.004), 0.001)
    long, short = (wide, high) if across else (high, wide)
    pitch = short / count
    for column in range(count):
        middle = -short / 2 + pitch * (column + 0.5)
        lit = int(round(levels[column % len(levels)] * segments))
        for step in range(lit):
            start = -long / 2 + 0.004 + step * (long - 0.008) / segments
            end = start + (long - 0.008) / segments * 0.72
            low, high_end = (start, middle - pitch * 0.3), (end, middle + pitch * 0.3)
            if not across:
                low, high_end = (middle - pitch * 0.3, start), (middle + pitch * 0.3, end)
            found += box(LAMP_PARTS[colour], (low[0], low[1], 0.0037), (high_end[0], high_end[1], 0.0048), 0.0002)
    return found


def readout(wide=0.07, high=0.026, digits="2830", colour="green", **_):
    """A small lit number window: a dark recess in a bright frame and its digits lit."""
    found = frame_ring("metal", rounded_rectangle(wide + 0.008, high + 0.008, 0.003),
                       rounded_rectangle(wide, high, 0.002), 0.0, 0.004)
    found += box("dark", (-wide / 2 - 0.001, -high / 2 - 0.001, 0.0003), (wide / 2 + 0.001, high / 2 + 0.001, 0.002), 0.0003)
    found += moved(lettering(LAMP_PARTS[colour], digits, high * 0.6, 0.0006), offset=(0.0, 0.0, 0.002))
    return found


GRAPHICS = ("tower", "orbit", "attitude", "landing", "lines")


def graphic(kind, wide, high, part):
    """A screen's line drawing (GRAPHICS) fitted to `wide` x `high`, as ribbons on z = 0."""
    lines = []
    if kind == "tower":
        left, right, foot, head = -0.36, -0.2, -0.42, 0.40
        lines += [[(left * wide, foot * high), (left * wide, head * high)],
                  [(right * wide, foot * high), (right * wide, head * high)]]
        for step in range(8):
            low = foot + step * (head - foot) / 8
            up = low + (head - foot) / 8
            lines.append([(left * wide, low * high), (right * wide, low * high)])
            lines.append([(left * wide, low * high), (right * wide, up * high)])
            lines.append([(right * wide, low * high), (left * wide, up * high)])
        lines.append([(left * wide, head * high), (right * wide, head * high)])
        for arm in (0.22, -0.05):
            lines.append([(right * wide, arm * high), (-0.04 * wide, arm * high), (-0.04 * wide, (arm - 0.05) * high)])
        body = [(-0.02, -0.42), (-0.02, 0.18), (0.03, 0.34), (0.08, 0.18), (0.08, -0.42), (-0.02, -0.42)]
        lines.append([(x * wide, y * high) for x, y in body])
        for step in range(5):
            y = (0.34 - step * 0.16) * high
            lines.append([(0.18 * wide, y), ((0.3 + 0.08 * (step % 3)) * wide, y)])
            lines.append([(0.18 * wide, y - 0.05 * high), (0.44 * wide, y - 0.05 * high)])
    elif kind == "orbit":
        lines.append(circle_path(0.34 * wide, 0.24 * high, (-0.06 * wide, -0.04 * high), 48, -10))
        lines.append(circle_path(0.07 * high, 0.07 * high, (-0.1 * wide, -0.06 * high), 20))
        lines.append(circle_path(0.014 * high, 0.014 * high, (0.22 * wide, 0.14 * high), 8))
        lines.append([(-0.46 * wide, -0.44 * high), (0.46 * wide, -0.44 * high)])
        for step in range(4):
            y = (0.3 - step * 0.12) * high
            lines.append([(0.33 * wide, y), (0.46 * wide, y)])
    elif kind == "attitude":
        for share in (0.38, 0.24):
            lines.append(circle_path(share * high, share * high, (0.0, 0.0), 40))
        lines.append([(-0.45 * high, 0.0), (0.45 * high, 0.0)])
        lines.append([(0.0, -0.45 * high), (0.0, 0.45 * high)])
        lines.append([(-0.2 * high, 0.08 * high), (0.0, 0.02 * high), (0.2 * high, 0.08 * high)])
    elif kind == "landing":
        for step in range(5):
            lines.append([(-0.45 * wide, (-0.4 + step * 0.2) * high), (0.45 * wide, (-0.4 + step * 0.2) * high)])
        lines.append([(-0.45 * wide + step * 0.09 * wide, -0.3 * high + 0.12 * high * math.sin(step * 0.7))
                      for step in range(11)])
    else:
        for step in range(4):
            y = (0.3 - step * 0.2) * high
            lines.append([(-0.4 * wide, y), ((0.1 + 0.08 * (step % 3)) * wide, y)])
    found = []
    for line in lines:
        for start, end in zip(line[:-1], line[1:]):
            found += ribbon(part, [start, end], LINE, 0.0001 * (len(found) % 4))  # strokes that overlap never share a face
    return found


def screen(wide=0.2, high=0.15, graphic_kind="lines", colour="green", **sizes):
    """A screen in a bezel with rounded corners: a dark glass face and its `graphic_kind` drawing lit in
    `colour`."""
    border = 0.014
    found = outline_slab("frame", rounded_rectangle(wide + 2 * border, high + 2 * border, 0.012), 0.0, 0.012)
    found += frame_ring("metal", rounded_rectangle(wide + 2 * border - 0.003, high + 2 * border - 0.003, 0.011),
                        rounded_rectangle(wide + 0.004, high + 0.004, 0.006), 0.0105, 0.017)
    found += box("glass_dark", (-wide / 2, -high / 2, 0.011), (wide / 2, high / 2, 0.0135), 0.0005)
    found += moved(graphic(sizes.get("graphic", graphic_kind), wide * 0.9, high * 0.9, LAMP_PARTS[colour]),
                   offset=(0.0, 0.0, 0.0136))
    if sizes.get("title"):
        found += moved(lettering(LAMP_PARTS[colour], sizes["title"], high * 0.07, 0.0006, align="left"),
                       offset=(-wide * 0.45, high * 0.42, 0.0136))
    return found


def scope(size=0.11, colour="cyan", **_):
    """A round scope `size` across: a bright ring round a dark face with its rings, cross and the craft's mark lit."""
    radius = size / 2
    found = turned("metal", [(radius * 0.9, 0.0), (radius * 1.12, 0.0), (radius * 1.12, 0.008), (radius * 1.0, 0.011),
                             (radius * 0.9, 0.011), (radius * 0.9, 0.0)], segments=48)
    found += turned("glass_dark", [(0.0, 0.0), (radius * 0.91, 0.0), (radius * 0.91, 0.006), (0.0, 0.006)], segments=48)
    lines = [circle_path(radius * share, radius * share, (0.0, 0.0), 40) for share in (0.75, 0.45)]
    lines += [[(-radius * 0.85, 0.0), (radius * 0.85, 0.0)], [(0.0, -radius * 0.85), (0.0, radius * 0.85)],
              [(-radius * 0.35, radius * 0.1), (0.0, 0.0), (radius * 0.35, radius * 0.1)]]
    for line in lines:
        for start, end in zip(line[:-1], line[1:]):
            found += moved(ribbon(LAMP_PARTS[colour], [start, end], LINE, 0.0), offset=(0.0, 0.0, 0.0062))
    return found


def keypad(columns=3, rows=4, key=0.013, gap=0.004, **_):
    """A keypad: a dark tray and its keys, rounded, in rows."""
    wide, high = columns * (key + gap) + gap, rows * (key + gap) + gap
    found = box("dark", (-wide / 2, -high / 2, 0.0), (wide / 2, high / 2, 0.004), 0.001)
    for column in range(columns):
        for row in range(rows):
            x = -wide / 2 + gap + column * (key + gap)
            y = -high / 2 + gap + row * (key + gap)
            found += rounded_box("key", (x, y, 0.0035), (x + key, y + key, 0.010), 0.002, steps=2, inside=1)
    return found


def button(colour="red", size=0.016, **_):
    """A push button `size` across: a bright collar and a lit cap of `colour`."""
    radius = size / 2
    found = turned("metal", [(radius * 0.8, 0.0), (radius * 1.3, 0.0), (radius * 1.3, 0.004), (radius * 0.9, 0.006),
                             (radius * 0.8, 0.006), (radius * 0.8, 0.0)], segments=20)
    found += turned(LAMP_PARTS[colour], [(0.0, 0.003), (radius * 0.85, 0.003), (radius * 0.85, 0.009), (radius * 0.6, 0.011),
                                         (0.0, 0.011)], segments=20, smooth=True)
    return found


def rotary(size=0.028, **_):
    """A rotary selector: a dark fluted knob with a white pointer over a bright skirt."""
    radius = size / 2
    found = turned("metal", [(radius * 0.6, 0.0), (radius * 1.2, 0.0), (radius * 1.2, 0.003), (radius * 0.6, 0.003),
                             (radius * 0.6, 0.0)], segments=24)
    found += turned("dark", [(0.0, 0.0025), (radius * 0.75, 0.0025), (radius * 0.75, 0.003), (radius * 0.75, 0.014), (radius * 0.6, 0.017), (0.0, 0.017)],
                    segments=12)
    found += moved(ribbon("dial", [(0.0, 0.0), (0.0, radius * 0.65)], 0.002, 0.0), offset=(0.0, 0.0, 0.0172))
    for step in range(6):
        angle = math.radians(150 - step * 24)
        found += ribbon("ink", [(radius * 1.35 * math.cos(angle), radius * 1.35 * math.sin(angle)),
                                (radius * 1.7 * math.cos(angle), radius * 1.7 * math.sin(angle))], 0.0012, 0.0002)
    return found


def wheel(size=0.07, **_):
    """A small handwheel `size` across on a boss, three spokes (the pad water valve)."""
    radius = size / 2
    found = turned("dark", [(0.0, 0.0), (0.008, 0.0), (0.008, 0.018), (0.0, 0.018)], segments=16)
    found += tube("metal", [(radius * math.cos(angle), radius * math.sin(angle), 0.02)
                            for angle in np.linspace(0, 2 * math.pi, 41)], 0.0035, 10)
    for step in range(3):
        angle = math.radians(90 + step * 120)
        found += tube("metal", [(0.0, 0.0, 0.018), (radius * math.cos(angle), radius * math.sin(angle), 0.02)],
                      0.0025, 8)
    return found


def slider(high=0.06, level=0.6, **_):
    """A slide lever in a dark slot: its knob at `level` of the slot."""
    found = box("dark", (-0.004, -high / 2, 0.0), (0.004, high / 2, 0.003), 0.0008)
    y = -high / 2 + high * level
    found += rounded_box("lever", (-0.007, y - 0.005, 0.0025), (0.007, y + 0.005, 0.014), 0.003, steps=2, inside=1)
    return found


def beacon(**_):
    """The master alarm: a red dome on a bright base inside a wire cage."""
    found = turned("metal", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.008), (0.024, 0.012), (0.0, 0.012)], segments=24)
    found += turned("glow", [(0.0, 0.012)] + [(0.021 * math.cos(math.radians(angle)), 0.012 + 0.03 * math.sin(math.radians(angle)))
                             for angle in range(0, 91, 10)], segments=24, smooth=True)
    for step in range(4):
        angle = math.radians(45 + step * 90)
        found += tube("metal", [(0.024 * math.cos(angle) * math.cos(math.radians(tilt)),
                                 0.024 * math.sin(angle) * math.cos(math.radians(tilt)),
                                 0.012 + 0.034 * math.sin(math.radians(tilt))) for tilt in range(0, 91, 15)], 0.0012, 6)
    return found


def words(text="", high=0.012, part="ink", **_):
    """Lettering alone."""
    return moved(lettering(part, text, high), offset=(0.0, 0.0, 0.0))


ITEMS = {"toggle": toggle, "lamp": lamp, "gauge": gauge, "bars": bars, "readout": readout, "screen": screen,
         "keypad": keypad, "scope": scope, "button": button, "rotary": rotary, "wheel": wheel, "slider": slider, "beacon": beacon,
         "words": words}


def laid_items(items, height):
    """A panel's `items` ({kind, at [u, v], ...}) built and laid on its plate at `height`."""
    found = []
    for item in items:
        sizes = {key: value for key, value in item.items() if key not in ("kind", "at")}
        built = ITEMS[item["kind"]](**sizes)
        found += moved(built, offset=(item["at"][0], item["at"][1], height - 0.0003))
    return found


def framed_plate(outer, inner):
    """A panel's plate and its raised bezel as one closed body: the plate PLATE thick inside the `inner` outline, the
    bezel BEZEL over it between `inner` and `outer` (each counter-clockwise, as many points), so its middle lies in
    the plate (a bezel alone, a ring, has its middle in its hole, where the panel's own wired parts sit)."""
    outer, inner = np.asarray(outer, dtype=np.float64), np.asarray(inner, dtype=np.float64)
    count = len(outer)
    rings = [(outer, 0.0), (outer, PLATE + BEZEL), (inner, PLATE + BEZEL), (inner, PLATE)]
    points = [(x, y, z) for outline, z in rings for x, y in outline]
    middle_top, middle_bottom = len(points), len(points) + 1
    points += [(*inner.mean(axis=0), PLATE), (*outer.mean(axis=0), 0.0)]
    points = np.asarray(points)
    bands = []
    for ring in range(len(rings) - 1):
        for step in range(count):
            here, there = ring * count + step, ring * count + (step + 1) % count
            bands += [[here, there, there + count], [here, there + count, here + count]]
    top = [[middle_top, 3 * count + step, 3 * count + (step + 1) % count] for step in range(count)]
    bottom = [[middle_bottom, (step + 1) % count, step] for step in range(count)]
    triangles = np.asarray(bands + top + bottom)
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    across = corners.mean(axis=1)[:, :2] - outer.mean(axis=0)
    zero, flat = np.zeros((count * 2, 2)), np.zeros((count, 2))
    ways = np.vstack([np.column_stack([across[:count * 2], zero[:, 0]]),  # the bezel's outer wall: out
                      np.column_stack([zero, np.ones(count * 2)]),  # its top: up
                      np.column_stack([-across[count * 4:count * 6], zero[:, 0]]),  # its inner wall: in
                      np.column_stack([flat, np.ones(count)]), np.column_stack([flat, -np.ones(count)])])
    flip = np.einsum("ij,ij->i", normals, ways) < 0
    triangles[flip] = triangles[flip][:, ::-1]
    plate = np.zeros(len(triangles), dtype=bool)
    plate[len(bands):] = True  # the faces across: the plate's top and its back
    return [piece("bezel", points, triangles[~plate], False), piece("plate", points, triangles[plate], False)]


def panel(wide=0.4, high=0.3, label="", items=(), label_high=0.02, **_):
    """An instrument panel: a plate with rounded corners, a raised bezel round it, a label strip across its top with
    `label` in modelled letters, and its `items` laid on the plate (their `at` from the plate's middle)."""
    corner = 0.022
    found = framed_plate(rounded_rectangle(wide, high, corner), rounded_rectangle(wide - 0.024, high - 0.024,
                                                                                    corner * 0.6))
    if label:
        strip_high = label_high * 1.7
        top = high / 2 - 0.012 - 0.006
        found += box("label", (-wide / 2 + 0.03, top - strip_high, PLATE - 0.0005), (wide / 2 - 0.03, top, PLATE + 0.0025),
                     0.0008)
        found += moved(lettering("ink", label, label_high), offset=(0.0, top - strip_high / 2, PLATE + 0.0025))
    found += laid_items(items, PLATE)
    return found


# --- the capsule: its cone's hull, lining, ceiling and floor, built in the capsule's own frame -----------------------

CONE = {"radius": 1.40, "slope": 0.18, "hull": 0.05, "gap": 0.003, "lining": 0.05, "bolster": 0.05,
        "bolster_high": 0.55, "puff": 0.045, "ceiling": 2.05}
ROWS = (0.0, 0.42, 0.75, 1.08, 1.41, 1.74, 2.05)  # the lining's courses, metres up from the floor
WIDTHS = (0.55, 0.42, 0.42, 0.40, 0.38, 0.36)  # each course's cushion width
FADE = 0.06  # metres over which the quilting eases flat round a porthole, a hatch or a panel
THROUGH = 0.5  # metres along a hole's axis off the hull's inner face within which the wall is cut for it


class Cone:
    """The capsule's cone: its hull's inner face `radius` metres from the axis (y) at the floor (y = 0), drawn in
    `slope` metres a metre up. Every face of the hull and lining is this cone `offset` metres in (along its normal,
    toward the room): a cone too. An angle `theta` runs from +z toward +x (the room's front and its left)."""

    def __init__(self, **sizes):
        self.sizes = {**CONE, **{key: value for key, value in sizes.items() if key in CONE}}
        self.radius, self.slope = float(self.sizes["radius"]), float(self.sizes["slope"])
        self.cos = 1.0 / math.sqrt(1.0 + self.slope ** 2)
        self.sin = self.slope * self.cos

    def rho(self, y, offset=0.0):
        """The face's distance from the axis at height `y`."""
        return self.radius - self.slope * np.asarray(y, dtype=np.float64) - offset / self.cos

    def at(self, theta, y, offset=0.0):
        """The points of the face `offset` in at `theta` (radians) and height `y`."""
        theta, y = np.broadcast_arrays(np.asarray(theta, dtype=np.float64), np.asarray(y, dtype=np.float64))
        rho = self.rho(y, offset)
        return np.stack([rho * np.sin(theta), y, rho * np.cos(theta)], axis=-1)

    def inward(self, theta):
        """The faces' normal toward the room at `theta`."""
        theta = np.asarray(theta, dtype=np.float64)
        return np.stack([-np.sin(theta) * self.cos, np.full_like(theta, -self.sin), -np.cos(theta) * self.cos],
                        axis=-1)

    def frame(self, theta):
        """At `theta`, as one in the room looking at the wall sees it: (right, up the wall, toward the room); a piece
        laid there turns [-slope_degrees, theta degrees, 0] (`turn`)."""
        theta = float(theta)
        right = np.array([-math.cos(theta), 0.0, math.sin(theta)])
        up = np.array([-self.sin * math.sin(theta), self.cos, -self.sin * math.cos(theta)])
        return right, up, self.inward(theta)

    def turn(self, theta):
        """The turn (rotateXYZ degrees) laying a piece's front (its -z, as written) toward the room at `theta`."""
        return [round(-math.degrees(math.atan(self.slope)), 6), round(math.degrees(float(theta)), 6), 0.0]

    def onto(self, points, way, offset=0.0):
        """Where the line from each of `points` along `way` meets the face `offset` in (its nearer crossing)."""
        points = np.asarray(points, dtype=np.float64)
        way = np.asarray(way, dtype=np.float64) / np.linalg.norm(way)
        top = self.radius - offset / self.cos
        reach = top - self.slope * points[..., 1]
        rise = -self.slope * way[1]
        square = way[0] ** 2 + way[2] ** 2 - rise ** 2
        linear = 2 * (points[..., 0] * way[0] + points[..., 2] * way[2] - reach * rise)
        constant = points[..., 0] ** 2 + points[..., 2] ** 2 - reach ** 2
        root = np.sqrt(np.maximum(linear ** 2 - 4 * square * constant, 0.0))
        near, far = (-linear - root) / (2 * square), (-linear + root) / (2 * square)
        along = np.where(np.abs(near) < np.abs(far), near, far)
        return points + along[..., None] * way


def smoothstep(low, high, value):
    """0 at `low`, 1 at `high`, eased between."""
    share = np.clip((np.asarray(value, dtype=np.float64) - low) / (high - low), 0.0, 1.0)
    return share * share * (3 - 2 * share)


def facing(points, triangles, ways):
    """The triangles wound so each faces along its `ways` row (one way a triangle)."""
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    flip = np.einsum("ij,ij->i", normals, ways) < 0
    triangles = triangles.copy()
    triangles[flip] = triangles[flip][:, ::-1]
    return triangles


def grid_solid(front, back, keep, front_parts, back_part, side_part, ways, pole=None):
    """A closed solid over a grid of cells: `front` and `back` (rows x columns x 3, the columns round a ring), each
    kept cell (`keep`, rows - 1 x columns) a quad of each, its front facing along `ways` (rows x columns x 3) and its
    back away, in its `front_parts` (rows - 1 x columns) and `back_part`; a side face of `side_part` on every edge
    between a kept cell and one not kept (or the grid's first and last row), facing out of the kept one. `pole`
    [front point, back point] closes the first row round a middle point instead of a side (a disc)."""
    rows, columns = front.shape[:2]
    count = rows * columns
    index = np.arange(count).reshape(rows, columns)
    following = np.roll(index, -1, axis=1)
    flat_front, flat_back, flat_ways = front.reshape(-1, 3), back.reshape(-1, 3), ways.reshape(-1, 3)
    cell_rows, cell_columns = np.nonzero(keep)
    quads = np.stack([index[cell_rows, cell_columns], following[cell_rows, cell_columns],
                      following[cell_rows + 1, cell_columns], index[cell_rows + 1, cell_columns]], axis=-1)
    triangles = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    triangle_ways = flat_ways[triangles].mean(axis=1)
    parts = np.concatenate([front_parts[cell_rows, cell_columns]] * 2)
    front_faces = facing(flat_front, triangles, triangle_ways)
    pieces = [piece(str(part), flat_front, front_faces[parts == part], True) for part in np.unique(parts)]
    back_faces = [facing(flat_back, triangles, -triangle_ways)]
    if pole is not None:
        middle_front, middle_back = np.vstack([flat_front, pole[0]]), np.vstack([flat_back, pole[1]])
        fan = np.stack([np.full(columns, count), index[0], following[0]], axis=-1)
        fan_ways = flat_ways[index[0]]
        pieces.append(piece(str(front_parts[0, 0]), middle_front, facing(middle_front, fan, fan_ways), True))
        pieces.append(piece(back_part, middle_back, facing(middle_back, fan, -fan_ways), True))
    pieces.append(piece(back_part, flat_back, np.concatenate(back_faces), True))
    edge = np.zeros((1, columns), dtype=bool)
    padded = np.vstack([np.ones((1, columns), dtype=bool) if pole is not None else edge, keep, edge])
    centres = (front[:-1] + np.roll(front[:-1], -1, axis=1) + front[1:] + np.roll(front[1:], -1, axis=1)) / 4
    level_rows, level_columns = np.nonzero(padded[:-1] != padded[1:])
    if pole is not None:
        keep_first = level_rows > 0
        level_rows, level_columns = level_rows[keep_first], level_columns[keep_first]
    above = padded[level_rows + 1, level_columns]
    starts = index[level_rows, level_columns]
    ends = following[level_rows, level_columns]
    kept_rows = np.where(above, level_rows, level_rows - 1)
    kept_centres = centres[kept_rows, level_columns]
    left = np.roll(keep, 1, axis=1)
    upright_rows, upright_columns = np.nonzero(left != keep)
    kept_columns = np.where(keep[upright_rows, upright_columns], upright_columns, (upright_columns - 1) % columns)
    starts = np.concatenate([starts, index[upright_rows, upright_columns]])
    ends = np.concatenate([ends, index[upright_rows + 1, upright_columns]])
    kept_centres = np.vstack([kept_centres, centres[upright_rows, kept_columns]])
    if len(starts):
        sides = np.stack([starts, ends, ends + count, starts + count], axis=-1)
        both = np.vstack([flat_front, flat_back])
        outward = (flat_front[starts] + flat_front[ends]) / 2 - kept_centres
        side_faces = np.concatenate([sides[:, [0, 1, 2]], sides[:, [0, 2, 3]]])
        pieces.append(piece(side_part, both, facing(both, side_faces, np.vstack([outward, outward])), False))
    return pieces


def wrapped(angle):
    """An angle (radians) brought within half a turn of 0."""
    return (np.asarray(angle, dtype=np.float64) + math.pi) % (2 * math.pi) - math.pi


def in_cut(theta, y, cut):
    """Whether each spot lies inside the cut-away's outline `cut` [theta, half theta (degrees), y, half y, power]: a
    rounded rectangle on the cone (a superellipse in angle and height), the concept's open side."""
    middle, half, height, half_high, power = cut
    across = np.abs(wrapped(theta - math.radians(middle))) / math.radians(half)
    upward = np.abs(np.asarray(y) - height) / half_high
    return across ** power + upward ** power < 1.0


def near_hole(cone, points, holes):
    """Whether each point lies within a round hole [theta (degrees), y, radius] of the cone: nearer than the radius
    to the hole's axis (the face's normal through its middle on the hull's inner face) and within THROUGH of the
    wall along it (the axis runs on across the room to the far wall, which keeps its cells)."""
    near = np.zeros(points.shape[:-1], dtype=bool)
    for theta, y, radius in holes:
        middle = cone.at(math.radians(theta), y)
        axis = cone.inward(math.radians(theta))
        offset = points - middle
        along = np.einsum("...i,i->...", offset, axis)
        across = offset - along[..., None] * axis
        near |= (np.linalg.norm(across, axis=-1) < radius) & (np.abs(along) < THROUGH)
    return near


def cells_kept(near, cut_cells, which, middle_theta, sector):
    """The cells of a grid kept for `which` piece: its "main" body (outside the cut-away; only its `sector` [from,
    to] degrees round when given, so each sector is a wall of its own whose middle lies by it) or the "plug" filling
    the cut-away (the camera's alone); a cell with a corner in a hole is in neither."""
    corner = near[:-1] | np.roll(near[:-1], -1, axis=1) | near[1:] | np.roll(near[1:], -1, axis=1)
    if which not in ("main", "plug"):
        raise ValueError(f"a capsule piece is its main body or its plug, not {which!r}")
    kept = ~corner & (cut_cells if which == "plug" else ~cut_cells)
    if sector is not None:
        start = math.radians(sector[0])
        kept &= (middle_theta - start) % (2 * math.pi) < math.radians(sector[1] - sector[0])
    return kept


def ring_grid(rows, bottom, top, circumference, cell):
    """A ring grid's angles and heights: as many columns as `cell` metres fit round `circumference`, and rows `rows`
    apart from `bottom` to `top`."""
    columns = max(12, int(round(circumference / cell)))
    heights = np.linspace(bottom, top, max(2, int(round((top - bottom) / rows)) + 1))
    return np.arange(columns) * 2 * math.pi / columns, heights


def hull(cut=None, holes=(), which="main", sector=None, bottom=-0.40, top=2.15, cell=0.025, band=-0.18, **sizes):
    """The capsule's pressure hull from `bottom` to `top`: a smooth cone `hull` metres thick, its round holes
    (`holes` [[theta, y, radius]]: the portholes, the hatch) left open for their sleeves, the cut-away (`cut`, as
    in_cut) left out of its "main" body and filling its "plug"; below `band` its rim (part band)."""
    cone = Cone(**sizes)
    thetas, heights = ring_grid(cell, bottom, top, 2 * math.pi * float(cone.rho(bottom)), cell)
    grid_theta, grid_y = np.meshgrid(thetas, heights)
    inner = cone.at(grid_theta, grid_y)
    outer = cone.at(grid_theta, grid_y, -cone.sizes["hull"])
    middle_theta = grid_theta[:-1] + math.pi / len(thetas)
    middle_y = (grid_y[:-1] + grid_y[1:]) / 2
    cut_cells = in_cut(middle_theta, middle_y, cut) if cut else np.zeros(middle_y.shape, dtype=bool)
    near = near_hole(cone, inner, holes) | near_hole(cone, outer, holes)
    keep = cells_kept(near, cut_cells, which, middle_theta, sector)
    parts = np.where(middle_y < band, "band", "hull")
    return grid_solid(inner, outer, keep, parts, "hull", "edge", cone.inward(grid_theta))


def quilt(cone, theta, y):
    """The lining's cushions over the spots (theta, y): (how far each stands out, the share of its cushion's puff
    there). Courses of rounded pads, ROWS high and about WIDTHS wide, each course offset from the one under it, a
    pad's face flat and full and falling to a thin seam at its edges, its seams wandering a little; the course on
    the floor a fat bolster."""
    edges = np.asarray(ROWS)
    wander = (0.010 * np.sin(3 * theta + 1.7) + 0.006 * np.sin(7 * theta + 0.4)) * smoothstep(0.05, 0.2, y)
    shifted = y + wander
    row = np.clip(np.searchsorted(edges, shifted, side="right") - 1, 0, len(edges) - 2)
    low, high = edges[row], edges[row + 1]
    upward = np.clip((shifted - low) / (high - low), 0.0, 1.0)
    middles = (edges[:-1] + edges[1:]) / 2
    counts = np.maximum(np.round(2 * math.pi * cone.rho(middles, 0.1) / np.asarray(WIDTHS)), 3)
    shifts = np.array([(0.5 * (number % 2) + 0.13 * number) % 1.0 for number in range(len(counts))])
    position = (theta % (2 * math.pi)) / (2 * math.pi) * counts[row] + shifts[row]
    column = np.floor(position)
    across = position - column
    seed = np.abs(np.sin(row * 12.9898 + (column % counts[row]) * 78.233) * 43758.5453) % 1.0
    share_across = np.clip(1 - np.abs(2 * across - 1) ** 3.5, 0, 1) ** 0.65
    share_up = np.where(row == 0, np.clip(1 - np.abs(2 * upward - 1) ** 2.5, 0, 1) ** 0.6,
                        np.clip(1 - np.abs(2 * upward - 1) ** 3, 0, 1) ** 0.65)
    share = share_across * share_up
    puff = cone.sizes["puff"] * np.where(row == 0, 1.7, 1.0) * (0.85 + 0.3 * seed)
    return puff * share, share


def flat_spot(theta, y, wide, high, **sizes):
    """Where a flat piece `wide` x `high` (a panel) lies on the lining at `theta` (degrees) and height `y`, the
    quilting under it eased onto its plane: (its back's middle, its turn, (right, up, inward)). The plane stands off
    the lining's face by the wall's curve across the piece, so its edges rest on the face and nothing sinks in."""
    cone = Cone(**sizes)
    angle = math.radians(theta)
    right, up, inward = cone.frame(angle)
    face = cone.sizes["gap"] + cone.sizes["lining"]
    rho = float(cone.rho(y, face))
    reach = wide / 2 + 0.02
    sag = rho - math.sqrt(max(rho ** 2 - reach ** 2, 1e-9))
    middle = cone.at(angle, y, face) + inward * (sag + 0.003)
    return middle, cone.turn(angle), (right, up, inward)


def lining_depth(cone, theta, y, back, fades, flats):
    """How far the lining's face stands off its back at each spot: its skin, the bolster at the floor and the
    cushions, eased flat round each fade [theta, y, radius] and onto each flat's plane [theta, y, wide, high]."""
    sizes = cone.sizes
    bump, share = quilt(cone, theta, y)
    soft = sizes["bolster"] * smoothstep(sizes["bolster_high"], 0.0, y) + bump
    eased = np.zeros(theta.shape)
    for fade_theta, fade_y, radius in fades:
        distance = np.linalg.norm(back - cone.at(math.radians(fade_theta), fade_y, sizes["gap"]), axis=-1)
        eased = np.maximum(eased, 1 - smoothstep(radius, radius + FADE, distance))
    depth = sizes["lining"] + soft * (1 - eased)
    flattened = np.zeros(theta.shape)
    normals = cone.inward(theta)
    for flat_theta, flat_y, wide, high in flats:
        middle, _, (right, up, inward) = flat_spot(flat_theta, flat_y, wide, high, **sizes)
        offset = back - cone.at(math.radians(flat_theta), flat_y, sizes["gap"])
        outside = np.hypot(np.maximum(np.abs(offset @ right) - wide / 2, 0.0),
                           np.maximum(np.abs(offset @ up) - high / 2, 0.0))
        weight = (1 - smoothstep(0.01, 0.01 + FADE, outside)) * (np.abs(offset @ inward) < 0.3)
        onto = ((middle - back) @ inward) / np.maximum(np.einsum("...i,i->...", normals, inward), 1e-6)
        depth = depth * (1 - weight) + onto * weight
        flattened = np.maximum(flattened, weight)
    return depth, share * (1 - np.maximum(eased, flattened)) + np.maximum(eased, flattened)


def lining(cut=None, holes=(), fades=(), flats=(), which="main", sector=None, cell=0.02, rows=0.016, **sizes):
    """The cabin's quilted lining, one closed piece round the cone from the floor to the ceiling: its back a hair
    off the hull, its face the cushions (lining_depth: worn vinyl pads in courses, thin seams, a bolster along the
    floor), round holes left for the portholes and the hatch (`holes`, as hull), the quilting eased flat round them
    (`fades`) and under each panel (`flats`, flat_spot), the cut-away left out of its "main" body and filling its
    "plug". Parts cushion and seam (the faces down in a seam), back."""
    cone = Cone(**sizes)
    top = cone.sizes["ceiling"]
    thetas, heights = ring_grid(rows, 0.0015, top, 2 * math.pi * float(cone.rho(0.0)), cell)
    grid_theta, grid_y = np.meshgrid(thetas, heights)
    back = cone.at(grid_theta, grid_y, cone.sizes["gap"])
    normals = cone.inward(grid_theta)
    depth, _ = lining_depth(cone, grid_theta, grid_y, back, fades, flats)
    front = back + normals * depth[..., None]
    front[..., 1] = np.maximum(front[..., 1], back[..., 1].min())  # the bolster's foot stays on the floor
    middle_theta = grid_theta[:-1] + math.pi / len(thetas)
    middle_y = (grid_y[:-1] + grid_y[1:]) / 2
    cut_cells = in_cut(middle_theta, middle_y, cut) if cut else np.zeros(middle_y.shape, dtype=bool)
    near = near_hole(cone, back, holes) | near_hole(cone, front, holes)  # the face stands off along its own normal
    keep = cells_kept(near, cut_cells, which, middle_theta, sector)
    parts = np.full(keep.shape, "cushion")  # the seams are the pads' own grooves, never a patch of another look
    return grid_solid(front, back, keep, parts, "back", "seam", normals)


def ceiling(lamps=(), rings=26, segments=144, thick=0.07, puff=0.03, **sizes):
    """The ceiling's quilted pad: a round pad in the middle and a ring of eight round it, under the hull's top at the
    lining's top (`ceiling`), its face down; each lamp's spot [x, z, radius] left flat for the lamp."""
    cone = Cone(**sizes)
    low = cone.sizes["ceiling"]
    outer = float(cone.rho(low, cone.sizes["gap"])) - 0.002
    radii = np.linspace(outer / rings, outer, rings)
    angles = np.arange(segments) * 2 * math.pi / segments
    grid_radius, grid_angle = np.meshgrid(radii, angles, indexing="ij")
    middle = 0.3
    centre = np.clip(1 - (grid_radius / middle) ** 4, 0, 1) ** 0.5
    across = np.clip((grid_radius - middle) / (outer - middle), 0, 1)
    around = (grid_angle / (2 * math.pi) * 8 + 0.06) % 1.0
    ring = (np.clip(1 - np.abs(2 * across - 1) ** 4, 0, 1) ** 0.55
            * np.clip(1 - np.abs(2 * around - 1) ** 5, 0, 1) ** 0.55)
    share = np.where(grid_radius < middle, centre, ring)
    flat_x, flat_z = grid_radius * np.sin(grid_angle), grid_radius * np.cos(grid_angle)
    for x, z, radius in lamps:
        share = share * smoothstep(radius, radius + FADE, np.hypot(flat_x - x, flat_z - z))
    under = np.stack([flat_x, low - puff * share, flat_z], axis=-1)
    shrink = float(cone.rho(low + thick, cone.sizes["gap"])) / (outer + 0.002) - 0.004
    over = np.stack([flat_x * shrink, np.full_like(flat_x, low + thick), flat_z * shrink], axis=-1)
    ways = np.broadcast_to(np.array([0.0, -1.0, 0.0]), under.shape)
    parts = np.full((rings - 1, segments), "cushion")
    return grid_solid(under, over, np.ones(parts.shape, dtype=bool), parts, "back", "seam", ways,
                      pole=[np.array([0.0, low - puff, 0.0]), np.array([0.0, low + thick, 0.0])])


def upright(pieces):
    """A piece turned about z (turned's axis) stood up, its axis along y."""
    return moved(pieces, about("x", -90))


def floor(rim=None, bottom=-0.40, **sizes):
    """The cabin's round floor, a solid disc from the hull's foot (`bottom`, on the service module) to its top at
    y = 0, out to the lining's back (or `rim`): a muted plate, two thin grooves round its middle disc."""
    cone = Cone(**sizes)
    edge = float(cone.rho(0.0, cone.sizes["gap"])) - 0.002 if rim is None else rim
    found = turned("floor", [(0.0, bottom), (edge, bottom), (edge, 0.0), (1.06, 0.0)], segments=96)
    found += turned("groove", [(1.06, 0.0), (1.06, -0.004), (1.04, -0.004), (1.04, 0.0)], segments=96)
    found += turned("floor", [(1.04, 0.0), (0.62, 0.0)], segments=96)
    found += turned("groove", [(0.62, 0.0), (0.62, -0.004), (0.60, -0.004), (0.60, 0.0)], segments=96)
    found += turned("floor", [(0.60, 0.0), (0.0, 0.0)], segments=96)
    return upright(found)


def skirt(bottom=-2.48, top=-0.40, foot=2.72, **sizes):
    """The service module under the capsule, a solid drum from the stack's top (`bottom`, `foot` across) up to the
    hull's foot: a flare up to the drum, a recess holding three fluid pipes round it, a rust band under the hull."""
    cone = Cone(**sizes)
    drum = float(cone.rho(top, -cone.sizes["hull"]))
    found = turned("skirt", [(0.0, bottom), (foot, bottom), (drum, bottom + 0.88), (drum, top - 0.78)],
                   segments=96)
    found += turned("recess", [(drum, top - 0.78), (drum - 0.12, top - 0.75), (drum - 0.12, top - 0.24),
                               (drum, top - 0.21)], segments=96)
    found += turned("band", [(drum, top - 0.21), (drum, top), (0.0, top)], segments=96)
    for height in (top - 0.62, top - 0.49, top - 0.36):
        found += turned("pipe", [(drum - 0.065 + 0.03 * math.cos(math.radians(angle)),
                                  height + 0.03 * math.sin(math.radians(angle))) for angle in range(-90, 271, 30)],
                        segments=96, smooth=True)
    return upright(found)


def nose(base=2.15, **sizes):
    """The capsule's nose over the hull's top (`base`): a rounded shoulder to a flat crown and its docking ring."""
    cone = Cone(**sizes)
    edge = float(cone.rho(base, -cone.sizes["hull"]))
    found = turned("hull", [(0.0, base + 0.0005), (edge, base + 0.0005), (edge - 0.03, base + 0.1),
                            (edge - 0.12, base + 0.2), (edge - 0.28, base + 0.26), (0.52, base + 0.27),
                            (0.0, base + 0.27)], segments=96, smooth=True)
    found += turned("band", [(0.42, base + 0.2695), (0.5, base + 0.2695), (0.5, base + 0.33), (0.47, base + 0.345),
                             (0.42, base + 0.345), (0.42, base + 0.2695)], segments=96)
    return upright(found)


def swept(part, path, normals, deep, wide, segments=20):
    """A closed band of an oval section (`deep` along `normals`, `wide` across them) swept round the closed `path`
    (n x 3, its first point not repeated): the cut-away's rounded lip."""
    path, normals = np.asarray(path, dtype=np.float64), np.asarray(normals, dtype=np.float64)
    tangents = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    normals = normals - np.einsum("ij,ij->i", normals, tangents)[:, None] * tangents
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    sides = np.cross(tangents, normals)
    angles = np.linspace(0, 2 * math.pi, segments + 1)[:-1]
    points = (path[:, None] + deep / 2 * np.cos(angles)[None, :, None] * normals[:, None]
              + wide / 2 * np.sin(angles)[None, :, None] * sides[:, None]).reshape(-1, 3)
    count = len(path)
    index = np.arange(count * segments).reshape(count, segments)
    following = np.roll(index, -1, axis=0)
    beside = np.roll(index, -1, axis=1)
    quads = np.stack([index, beside, np.roll(beside, -1, axis=0), following], axis=-1).reshape(-1, 4)
    triangles = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    centres = np.repeat(path, segments, axis=0)
    ways = points[triangles].mean(axis=1) - centres[triangles[:, 0]]
    return [piece(part, points, facing(points, triangles, ways), True)]


def lip(cut=None, steps=480, deep=0.24, wide=0.10, **sizes):
    """The cut-away's rim: one rounded band round its outline (`cut`, as in_cut) over the hull's and the lining's cut
    edges, from outside the hull to past the cushions' face."""
    cone = Cone(**sizes)
    middle, half, height, half_high, power = cut
    angles = np.linspace(0, 2 * math.pi, steps + 1)[:-1]
    cos, sin = np.cos(angles), np.sin(angles)
    across = np.sign(cos) * np.abs(cos) ** (2 / power)
    upward = np.sign(sin) * np.abs(sin) ** (2 / power)
    theta = math.radians(middle) + across * math.radians(half)
    y = height + upward * half_high
    depth = (cone.sizes["gap"] + cone.sizes["lining"] + cone.sizes["puff"] - cone.sizes["hull"]) / 2
    path = cone.at(theta, y, depth)
    return swept("band", path, cone.inward(theta), deep, wide)


def collar_flange(cone, middle, right, up, axis, inner, outer, face, thick, outward, part, segments=72, rings=4):
    """A flat ring hugging a face of the cone round a hole: from radius `inner` to `outer` round `middle` in the
    plane (right, up), its back on the face `face` in, `thick` thick toward the room (or out, `outward`)."""
    angles = np.arange(segments) * 2 * math.pi / segments
    radii = np.linspace(inner, outer, rings + 1)
    grid_radius, grid_angle = np.meshgrid(radii, angles, indexing="ij")
    spots = (middle + grid_radius[..., None] * (np.cos(grid_angle)[..., None] * right
                                                + np.sin(grid_angle)[..., None] * up))
    way = -axis if outward else axis
    base = cone.onto(spots, axis, face) + way * 0.001
    top = base + way * thick
    ways = np.broadcast_to(way, top.shape)
    return grid_solid(top, base, np.ones((rings, segments), dtype=bool), np.full((rings, segments), part), part,
                      part, ways)


def bolt_ring(cone, middle, right, up, axis, radius, face, lift, count, size=0.009):
    """`count` hex bolt heads on a ring of `radius` round `middle`, standing on the face `face` in, `lift` off it."""
    found = []
    head = turned("bolt", [(0.0, 0.0), (size, 0.0), (size, size * 0.5), (size * 0.6, size * 0.8), (0.0, size * 0.8)],
                  segments=6)
    for step in range(count):
        angle = 2 * math.pi * (step + 0.5) / count
        spot = middle + radius * (math.cos(angle) * right + math.sin(angle) * up)
        base = cone.onto(spot, axis, face) + axis * (lift - 0.0005)
        found += placed(head, base, right, up, axis)
    return found


def placed(pieces, origin, right, up, way):
    """Pieces built round z laid at `origin` with their x along `right`, y along `up` and z along `way`."""
    return moved(pieces, np.stack([right, up, way], axis=1), origin)


def sleeve(cone, middle, right, up, axis, radius, wall, low, face, bore, segments=96, rows=8):
    """A round sleeve `wall` thick inside `radius` along `axis` through the wall: from `low` (metres along the axis
    off `middle`, a plane outside the hull) to a hair past the face `face` in, each way round where that face lies
    (the wall's curve across the sleeve followed, so the sleeve stands no further into the room than its flange); its
    inside of the part `bore`."""
    angles = np.arange(segments) * 2 * math.pi / segments
    around = np.cos(angles)[:, None] * right + np.sin(angles)[:, None] * up
    reach = [np.einsum("ij,j->i", cone.onto(middle + size * around, axis, face) - middle, axis)
             for size in (radius, radius + wall)]
    high = np.maximum(*reach) + 0.015
    along = low + (high - low)[None, :] * np.linspace(0.0, 1.0, rows + 1)[:, None]
    inner = middle + radius * around[None] + along[..., None] * axis
    outer = middle + (radius + wall) * around[None] + along[..., None] * axis
    ways = np.broadcast_to(-around[None], inner.shape)
    return grid_solid(inner, outer, np.ones((rows, segments), dtype=bool), np.full((rows, segments), bore), "rim",
                      "rim", ways)


def through_wall(at=(0.0, 1.45), radius=0.15, wall=0.015, flange=0.07, bolts=10, glass=True, outside=0.03,
                 bore="bore", **sizes):
    """A round opening's frame through the hull and lining at `at` [theta (degrees), y]: a sleeve of `radius` along
    the wall's normal from outside the hull to past the cushions' face (sleeve; its inside of the part `bore`), a
    flange hugging the lining's face and one hugging the hull's outside, each with its bolts, and its glass out
    past the hull (a porthole's) or none (a hatch's)."""
    cone = Cone(**sizes)
    angle = math.radians(at[0])
    right, up, axis = cone.frame(angle)
    middle = cone.at(angle, at[1])
    face = cone.sizes["gap"] + cone.sizes["lining"]
    found = sleeve(cone, middle, right, up, axis, radius, wall, -cone.sizes["hull"] - outside, face, bore)
    bedded = radius + wall - 0.003  # each flange reaches into the sleeve's wall, so no face of one lies on the other
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange, face, 0.022, False, "rim")
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange * 0.8, -cone.sizes["hull"],
                           0.014, True, "rim")
    found += bolt_ring(cone, middle, right, up, axis, radius + wall + flange / 2, face, 0.023, bolts)
    if glass:
        pane = -cone.sizes["hull"] - outside / 2  # outside the hull, past where the hull and lining read their rays
        found += placed(turned("glass", [(0.0, pane - 0.002), (radius + 0.001, pane - 0.002),
                                         (radius + 0.001, pane + 0.002), (0.0, pane + 0.002)], segments=96),
                        middle, right, up, axis)
    return found


def tread(at=(0.0, 0.8), radius=0.63, rise=0.215, start=0.0, end=0.3, **sizes):
    """The step filling a hatch sleeve's trough (of `radius`, at `at` as through_wall) to a flat tread `rise` over
    its bottom, from `start` to `end` metres along the wall's normal off the hull's inner face: the walked way
    through the hatch, as wide as the sleeve's chord there."""
    cone = Cone(**sizes)
    angle = math.radians(at[0])
    right, up, axis = cone.frame(angle)
    inside = radius - 0.001
    chord = -inside + rise
    beta = math.asin(-chord / inside)
    arc = [(inside * math.cos(turn), inside * math.sin(turn)) for turn in np.linspace(math.pi + beta,
                                                                                       2 * math.pi - beta, 24)]
    return placed(outline_slab("tread", arc, start, end), cone.at(angle, at[1]), right, up, axis)


def hatch_leaf(radius=0.6, thick=0.05, bolts=16, **_):
    """The round hatch's door: a dished disc `radius` across, a raised rim on its inside face, bolts round it and a
    handwheel in its middle (its inside toward +z, as built)."""
    found = turned("leaf", [(0.0, -thick / 2), (radius, -thick / 2), (radius, thick / 2), (radius - 0.06, thick / 2),
                            (radius - 0.09, thick / 2 + 0.012), (0.0, thick / 2 + 0.02)], segments=96)
    found += turned("rim", [(radius - 0.059, thick / 2 + 0.0005), (radius - 0.005, thick / 2 + 0.0005),
                            (radius - 0.005, thick / 2 + 0.012), (radius - 0.025, thick / 2 + 0.02),
                            (radius - 0.059, thick / 2 + 0.02), (radius - 0.059, thick / 2 + 0.0005)], segments=96)
    for step in range(bolts):
        angle = 2 * math.pi * (step + 0.5) / bolts
        found += moved(turned("bolt", [(0.0, 0.0), (0.009, 0.0), (0.009, 0.005), (0.005, 0.008), (0.0, 0.008)],
                              segments=6), offset=((radius - 0.033) * math.cos(angle),
                                                   (radius - 0.033) * math.sin(angle), thick / 2 + 0.0205))
    found += moved(wheel(size=0.32), offset=(0.0, 0.0, thick / 2 + 0.0205))
    for step in range(bolts):  # its outside's bolts
        angle = 2 * math.pi * (step + 0.5) / bolts
        found += moved(turned("bolt", [(0.0, 0.0), (0.009, 0.0), (0.009, 0.005), (0.005, 0.008), (0.0, 0.008)],
                              segments=6), about("x", 180), ((radius - 0.033) * math.cos(angle),
                                                             (radius - 0.033) * math.sin(angle), -thick / 2 - 0.0005))
    found += turned("rim", [(0.0, -thick / 2 - 0.012), (0.08, -thick / 2 - 0.012), (0.08, -thick / 2 - 0.0005),
                            (0.0, -thick / 2 - 0.0005)], segments=32)
    return found


def gantry(long=1.6, wide=1.3, rail=1.05, deep=0.7, start=0.3, **_):
    """The railed walkway outside the hatch, built along +x from the hull (x = 0) with its deck's top at y = 0: a
    grating deck on edge beams, a railing of posts and rails along both sides from `start`, a truss under each
    side."""
    found = box("grate", (0.0, -0.04, -wide / 2), (long, 0.0, wide / 2), 0.004)
    for side in (-1, 1):
        edge = side * (wide / 2 + 0.025)
        found += box("frame", (0.0, -0.16, edge - 0.025), (long, -0.0005, edge + 0.025), 0.004)
        posts = np.linspace(start, long - 0.04, 4)
        for x in posts:
            found += tube("rail", [(x, -0.0005, edge), (x, rail, edge)], 0.02, 12)
        for height in (rail, rail * 0.5):
            found += tube("rail", [(start - 0.02, height, edge), (long - 0.02, height, edge)], 0.018, 12)
        chord = -deep
        found += tube("rail", [(0.05, chord, edge), (long - 0.1, chord, edge)], 0.03, 12)
        verticals = np.linspace(0.05, long - 0.1, 4)
        for x in verticals:
            found += tube("rail", [(x, chord, edge), (x, -0.16, edge)], 0.022, 12)
        for start_x, end_x in zip(verticals[:-1], verticals[1:]):
            found += tube("rail", [(start_x + 0.02, chord + 0.03, edge), (end_x - 0.02, -0.19, edge)], 0.016, 10)
    for x in np.linspace(0.05, long - 0.1, 4):
        found += tube("rail", [(x, -deep, -wide / 2 - 0.025), (x, -deep, wide / 2 + 0.025)], 0.02, 10)
    return found


# --- the furniture --------------------------------------------------------------------------------------------------

def console(wide=1.0, deep=0.4, front_high=0.6, back_high=0.74, items=(), **_):
    """The long low console before the pilot: a box `wide` across, `deep` from the pilot's side (+z) back, its top
    sloping up from `front_high` to `back_high` away from the pilot, a bright lip round its top, vents on its front
    and its `items` laid on its top (their `at` [u, v] up the slope from its middle)."""
    side = [(0.0, 0.0), (deep, 0.0), (deep, front_high), (0.0, back_high)]
    found = []
    points = [(-wide / 2, y, z) for z, y in side] + [(wide / 2, y, z) for z, y in side]
    for face in ([0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]):
        found.append(piece("body", [points[index] for index in face], [[0, 1, 2], [0, 2, 3]], False))
    middle = np.array([0.0, (front_high + back_high) / 4, deep / 2])
    found = [(part, points, oriented(points, triangles, points.mean(axis=0) - middle), smooth)
             for part, points, triangles, smooth in found]
    slope = math.degrees(math.atan2(back_high - front_high, deep))
    length = math.hypot(deep, back_high - front_high)
    top = box("deck", (-wide / 2 + 0.03, -length / 2 + 0.02, 0.0), (wide / 2 - 0.03, length / 2 - 0.02, 0.008),
              0.002)
    top += frame_ring("lip", rounded_rectangle(wide + 0.012, length + 0.012, 0.01),
                      rounded_rectangle(wide - 0.05, length - 0.03, 0.008), 0.0, 0.012)
    top += laid_items(items, 0.008)
    found += moved(top, np.asarray(about("x", -90 + slope)), (0.0, (front_high + back_high) / 2, deep / 2))
    for step in range(9):
        x = -0.2 + step * 0.05
        found += box("vent", (x - 0.012, 0.12, deep - 0.002), (x + 0.012, 0.32, deep + 0.004), 0.002)
    found += box("lip", (-wide / 2 - 0.006, 0.0, -0.006), (wide / 2 + 0.006, 0.05, deep + 0.006), 0.004)
    return found


def switch_box(wide=0.28, deep=0.24, front_high=0.56, back_high=0.66, items=(), **_):
    """The small switch box at the pilot's right hand: a box with a sloping top holding its `items`."""
    found = console(wide, deep, front_high, back_high, items)
    return [entry for entry in found if entry[0] != "vent"]


def seat(**_):
    """A compact padded bucket seat on a metal frame (its front toward +z), 0.6 m across: a seat pan and a back
    between raised side bolsters, a headrest, all in a grey shell whose wings wrap them; armrests on posts and a
    pedestal of tubes on a floor plate."""
    found = rounded_box("upholstery", (-0.17, 0.42, -0.18), (0.17, 0.5, 0.22), 0.035, 0.018)
    for side in (-1, 1):
        found += rounded_box("upholstery", (min(side * 0.15, side * 0.23), 0.43, -0.18),
                             (max(side * 0.15, side * 0.23), 0.56, 0.21), 0.028, 0.01)
    back = rounded_box("upholstery", (-0.16, 0.0, 0.0), (0.16, 0.56, 0.08), 0.04, 0.02)
    for side in (-1, 1):
        back += rounded_box("upholstery", (min(side * 0.14, side * 0.22), 0.02, 0.0),
                            (max(side * 0.14, side * 0.22), 0.54, 0.15), 0.028, 0.01)
    back += rounded_box("upholstery", (-0.11, 0.62, 0.0), (0.11, 0.79, 0.08), 0.04, 0.015)
    back += rounded_box("shell", (-0.235, -0.02, -0.06), (0.235, 0.6, -0.003), 0.03)
    for side in (-1, 1):
        back += rounded_box("shell", (min(side * 0.215, side * 0.25), -0.02, -0.055),
                            (max(side * 0.215, side * 0.25), 0.58, 0.17), 0.015)
    back += rounded_box("shell", (-0.13, 0.58, -0.05), (0.13, 0.82, -0.003), 0.025)
    found += moved(back, about("x", -12), (0.0, 0.46, -0.21))
    found += rounded_box("shell", (-0.24, 0.35, -0.22), (0.24, 0.415, 0.25), 0.025)
    for side in (-1, 1):
        found += rounded_box("shell", (min(side * 0.215, side * 0.25), 0.36, -0.21),
                             (max(side * 0.215, side * 0.25), 0.55, 0.24), 0.015)
        found += rounded_box("upholstery", (side * 0.28 - 0.025, 0.63, -0.14), (side * 0.28 + 0.025, 0.675, 0.18),
                             0.018, 0.004)
        for z in (-0.14, 0.11):
            found += tube("frame", [(side * 0.28, 0.415, z), (side * 0.28, 0.63, z)], 0.011, 10)
        for z in (-0.16, 0.16):
            found += tube("frame", [(side * 0.14, 0.035, z), (side * 0.14, 0.345, z)], 0.018, 12)
        found += tube("frame", [(side * 0.14, 0.19, -0.16), (side * 0.14, 0.19, 0.16)], 0.013, 10)
    found += tube("frame", [(-0.14, 0.19, 0.0), (0.14, 0.19, 0.0)], 0.013, 10)
    found += box("frame", (-0.21, 0.0, -0.23), (0.21, 0.035, 0.23), 0.006)
    return found


def throttle(levers=2, **_):
    """The throttle quadrant: a box with a slotted top and `levers` levers thrown forward, black knobs."""
    found = rounded_box("body", (-0.06, 0.0, -0.11), (0.06, 0.07, 0.11), 0.012)
    found += box("dark", (-0.05, 0.068, -0.09), (0.05, 0.074, 0.09), 0.002)
    for number in range(levers):
        x = -0.022 + number * 0.044
        stem = tube("lever", [(0.0, 0.0, 0.0), (0.0, 0.16, 0.0)], 0.006, 10)
        stem += moved(rounded_box("knob", (-0.014, 0.0, -0.016), (0.014, 0.05, 0.016), 0.012), offset=(0.0, 0.16, 0.0))
        found += moved(stem, about("x", -14 - 10 * number), (x, 0.06, 0.0))
    return found


def stick(**_):
    """The control stick: a rubber boot on a bright collar, a shaft and a black grip with a red button on top."""
    found = turned("metal", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.012), (0.04, 0.016), (0.0, 0.016)], segments=24)
    found += turned("boot", [(0.0, 0.015), (0.04, 0.015), (0.044, 0.024), (0.032, 0.034), (0.036, 0.044), (0.024, 0.056),
                             (0.027, 0.066), (0.012, 0.08), (0.0, 0.08)], segments=24, smooth=True)
    found += turned("metal", [(0.0, 0.075), (0.009, 0.075), (0.009, 0.2), (0.0, 0.2)], segments=16)
    found += turned("knob", [(0.0, 0.18), (0.017, 0.18), (0.021, 0.22), (0.022, 0.27), (0.018, 0.3), (0.0, 0.305)],
                    segments=24, smooth=True)
    found += moved(button("red", 0.014), offset=(0.0, 0.0, 0.3))
    return moved(found, [[1, 0, 0], [0, 0, 1], [0, -1, 0]])


def lamp_fixture(size=0.2, **_):
    """A round ceiling lamp `size` across: a bright ring and a white glowing lens (facing +z)."""
    radius = size / 2
    found = turned("metal", [(0.0, 0.0), (radius, 0.0), (radius, 0.012), (radius * 0.85, 0.018), (0.0, 0.018)],
                   segments=40)
    found += turned("lamp_white", [(0.0, 0.016), (radius * 0.85, 0.016), (radius * 0.6, 0.026), (0.0, 0.03)], segments=40,
                    smooth=True)
    return found


KINDS = {"hull": hull, "lining": lining, "ceiling": ceiling, "floor": floor, "skirt": skirt, "nose": nose, "lip": lip,
         "through_wall": through_wall, "tread": tread, "hatch_leaf": hatch_leaf, "gantry": gantry, "panel": panel, "console": console,
         "switch_box": switch_box, "seat": seat, "throttle": throttle, "stick": stick, "lamp_fixture": lamp_fixture,
         **ITEMS}


# --- writing --------------------------------------------------------------------------------------------------------

def welded(points, triangles):
    """The piece's points merged where they coincide and only those its triangles use, and its triangles over
    them, each one collapsed to a line or a point (a turned piece's fan at its pole) left out: a reader drops such a
    face and every part's face numbers after it slip."""
    keys = np.round(points, 7)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    triangles = inverse.reshape(-1)[triangles]
    triangles = triangles[(triangles[:, 0] != triangles[:, 1]) & (triangles[:, 1] != triangles[:, 2])
                          & (triangles[:, 0] != triangles[:, 2])]
    used, compact = np.unique(triangles, return_inverse=True)
    return unique[used], compact.reshape(triangles.shape)


def corner_normals(points, triangles, smooth):
    """Each triangle corner's normal: the area-weighted mean of the faces round its point when `smooth`, else its
    face's own."""
    corners = points[triangles]
    faces = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    if not smooth:
        unit = faces / np.maximum(np.linalg.norm(faces, axis=1, keepdims=True), 1e-15)
        return np.repeat(unit, 3, axis=0)
    summed = np.zeros_like(points)
    for corner in range(3):
        np.add.at(summed, triangles[:, corner], faces)
    unit = summed / np.maximum(np.linalg.norm(summed, axis=1, keepdims=True), 1e-15)
    return unit[triangles].reshape(-1, 3)


def write(path, kind, sizes):
    """The piece of `kind` (KINDS) with its `sizes` written at `path`: /piece with one mesh `geo`, each part a
    GeomSubset bound to a placeholder (dome_shell.placeholder, the library's surface goes over it), its normals at
    every corner; turned half round y unless a FLAT_KINDS piece. Its parts, sorted."""
    if kind not in KINDS:
        raise ValueError(f"no cockpit piece {kind!r} (pieces are {', '.join(sorted(KINDS))})")
    pieces = KINDS[kind](**sizes)
    if kind not in FLAT_KINDS:
        pieces = moved(pieces, about("y", 180))
    points, triangles, normals, parts = [], [], [], {}
    count = 0
    for part, piece_points, piece_triangles, smooth in pieces:
        if not len(piece_triangles):
            continue
        piece_points, piece_triangles = welded(piece_points, piece_triangles)
        normals.append(corner_normals(piece_points, piece_triangles, smooth))
        first = sum(len(found) for found in triangles)
        triangles.append(piece_triangles + count)
        points.append(piece_points)
        count += len(piece_points)
        parts.setdefault(part, []).extend(range(first, first + len(piece_triangles)))
    points, triangles, normals = np.vstack(points), np.vstack(triangles), np.vstack(normals)
    points, triangles = welded(points, triangles)  # one point where pieces meet (their normals stay each its own,
    # per corner), so the check reads a closed piece of many parts as one body with its own middle
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/piece")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, "/piece/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(triangles)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(triangles.reshape(-1).tolist()))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals.astype(np.float32)))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    low, high = points.min(axis=0), points.max(axis=0)
    mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*low.tolist()), Gf.Vec3f(*high.tolist())]))
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    for part, part_faces in sorted(parts.items()):
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, part, UsdGeom.Tokens.face, part_faces, "materialBind",
                                                 UsdGeom.Tokens.nonOverlapping)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(dome_shell.placeholder(stage, f"/piece/Looks/{part}"))
    stage.GetRootLayer().Save()
    return sorted(parts)
