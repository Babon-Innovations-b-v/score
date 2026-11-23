"""The cockpit kit (the capsule lock, owner 2026-11-23: "messy meshes, no panels, ugly walls, way to big for the
cockpit"): a small craft's inside built in code at its real size, every piece one mesh `geo` of named parts for the
place's palette, as the dome shell algorithm's blocks are, so nothing inside the cockpit is a picture-made mesh.

    write(path, kind, sizes)    the piece of `kind` (KINDS) with its `sizes` written as a USD file at `path`; its parts

Every piece is built facing +z (its front toward the one looking at it, its back on z = 0, x to that one's right, y
up) and written turned half round y, so laid in a wall's frame (dome_shell blocks: the room at -z) its front faces
the room, and a word on it reads left to right from inside. A floor piece (a seat, the console) is laid with its own
turn. `FLAT_KINDS` are written as built (the ceiling's cushions, facing down).

The pieces, each with its sizes in metres (KINDS has their builders):
- `lining`: a wall's quilted cushions, rows of rounded pillows (a stagger every other row) over a seam backing, round
  holes left for portholes and a hatch (`holes` [[u, v, r]] as the room sees the wall), `clear` a stretch of the wall
  left bare (`[u0, u1]`), the wall narrowing from `wide` at its foot to `top_wide` at `high`.
- `bench`: the low cushion ring's piece of one side, its plan narrowing from the wall to the room.
- `ceiling`: the ceiling's cushions inside a ten-sided outline `apothem` from the middle, facing down.
- `panel`: a plate with rounded corners, a raised bezel, a label strip with its word in modelled letters, and its
  `items` ({kind, at [u, v], ...}: the hardware below) laid on it.
- the hardware, each its own piece or an item of a panel: `toggle` (a 2 cm bat toggle, `guard` a red flip cover),
  `lamp` (`colour` red, green, amber, white), `gauge` (a 6 cm round needle gauge), `bars` (a bar meter), `readout`
  (a small lit number window), `screen` (`graphic` tower, orbit, attitude, landing, lines), `keypad`, `button`,
  `rotary`, `wheel`, `slider`, `beacon`, `words` (lettering alone).
- `rim`: a porthole's bolted ring and its sleeve through the lining; `console`, `switch_box`, `seat`, `throttle`,
  `stick`, `lamp_fixture`.
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
FLAT_KINDS = ("ceiling",)

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


def bars(count=3, wide=0.05, high=0.09, levels=(0.7, 0.45, 0.85), colour="green", **_):
    """A bar meter: `count` lit columns of segments in a dark window, each lit to its level."""
    found = box("dark", (-wide / 2, -high / 2, 0.0), (wide / 2, high / 2, 0.004), 0.001)
    pitch = wide / count
    segments = 9
    for column in range(count):
        middle = -wide / 2 + pitch * (column + 0.5)
        lit = int(round(levels[column % len(levels)] * segments))
        for step in range(lit):
            bottom = -high / 2 + 0.004 + step * (high - 0.008) / segments
            found += box(LAMP_PARTS[colour], (middle - pitch * 0.3, bottom, 0.0037),
                         (middle + pitch * 0.3, bottom + (high - 0.008) / segments * 0.72, 0.0048), 0.0002)
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
        for x in (-0.32, -0.18):
            lines.append([(x * wide, -0.42 * high), (x * wide, 0.36 * high)])
        for step in range(7):
            y = -0.42 * high + step * 0.12 * high
            lines.append([(-0.32 * wide, y), (-0.18 * wide, y + 0.12 * high)])
        body = [(0.0, -0.38), (0.0, 0.18), (0.05, 0.32), (0.1, 0.18), (0.1, -0.38), (0.0, -0.38)]
        lines.append([(x * wide, y * high) for x, y in body])
        for fin in ([(0.0, -0.22), (-0.05, -0.38)], [(0.1, -0.22), (0.15, -0.38)]):
            lines.append([(x * wide, y * high) for x, y in fin])
        for step in range(4):
            y = (0.3 - step * 0.14) * high
            lines.append([(0.25 * wide, y), (0.42 * wide, y)])
    elif kind == "orbit":
        lines.append(circle_path(0.38 * wide, 0.26 * high, (0.0, -0.02 * high), 48, -10))
        lines.append(circle_path(0.06 * high, 0.06 * high, (-0.05 * wide, -0.04 * high), 20))
        lines.append(circle_path(0.012 * high, 0.012 * high, (0.3 * wide, 0.13 * high), 8))
        lines.append([(-0.45 * wide, 0.38 * high), (-0.15 * wide, 0.38 * high)])
        lines.append([(0.2 * wide, -0.38 * high), (0.44 * wide, -0.38 * high)])
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
    found += frame_ring("metal", rounded_rectangle(wide + 2 * border, high + 2 * border, 0.012),
                        rounded_rectangle(wide + 0.004, high + 0.004, 0.006), 0.0115, 0.017)
    found += box("glass_dark", (-wide / 2, -high / 2, 0.011), (wide / 2, high / 2, 0.0135), 0.0005)
    found += moved(graphic(sizes.get("graphic", graphic_kind), wide * 0.9, high * 0.9, LAMP_PARTS[colour]),
                   offset=(0.0, 0.0, 0.0136))
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
         "keypad": keypad, "button": button, "rotary": rotary, "wheel": wheel, "slider": slider, "beacon": beacon,
         "words": words}


def laid_items(items, height):
    """A panel's `items` ({kind, at [u, v], ...}) built and laid on its plate at `height`."""
    found = []
    for item in items:
        sizes = {key: value for key, value in item.items() if key not in ("kind", "at")}
        built = ITEMS[item["kind"]](**sizes)
        found += moved(built, offset=(item["at"][0], item["at"][1], height - 0.0003))
    return found


def panel(wide=0.4, high=0.3, label="", items=(), label_high=0.02, **_):
    """An instrument panel: a plate with rounded corners, a raised bezel round it, a label strip across its top with
    `label` in modelled letters, and its `items` laid on the plate (their `at` from the plate's middle)."""
    corner = 0.022
    found = outline_slab("plate", rounded_rectangle(wide, high, corner), 0.0, PLATE)
    found += frame_ring("bezel", rounded_rectangle(wide, high, corner),
                        rounded_rectangle(wide - 0.024, high - 0.024, corner * 0.6), PLATE - 0.0005, PLATE + BEZEL)
    if label:
        strip_high = label_high * 1.7
        top = high / 2 - 0.012 - 0.006
        found += box("label", (-wide / 2 + 0.03, top - strip_high, PLATE - 0.0005), (wide / 2 - 0.03, top, PLATE + 0.0025),
                     0.0008)
        found += moved(lettering("ink", label, label_high), offset=(0.0, top - strip_high / 2, PLATE + 0.0025))
    found += laid_items(items, PLATE)
    return found


# --- the room: cushions, rims, furniture ----------------------------------------------------------------------------

def overlaps_hole(low_u, low_v, high_u, high_v, holes, margin):
    """Whether the rectangle comes within `margin` of any round hole [u, v, r]."""
    for u, v, radius in holes:
        nearest_u, nearest_v = min(max(u, low_u), high_u), min(max(v, low_v), high_v)
        if math.hypot(u - nearest_u, v - nearest_v) < radius + margin:
            return True
    return False


def lining(wide=1.3, top_wide=None, low=0.0, high=1.7, rows=4, columns=4, depth=0.12, puff=0.03, holes=(),
           clear=None, under=(), under_depth=0.09, seed=0, **_):
    """A wall's quilted lining: `rows` of rounded pillows from `low` to `high` (`columns` a row, every other row
    staggered half a pillow), `depth` thick and swollen `puff` at their middles, over a seam backing; the wall `wide`
    at its foot narrowing to `top_wide` at `high`; no pillow within a seam of a round hole (`holes` [[u, v, r]]: a
    porthole's, a hatch's; a pillow over its edge cut round it) nor over the bare stretch `clear`
    [u0, u1] (a pillow over its edge cut back to it); a pillow behind a panel (`under` [[u0, v0, u1, v1]]) only `under_depth` thick and barely swollen, so
    the panel sits on it set into its neighbours."""
    random = np.random.default_rng(seed)
    top_wide = wide if top_wide is None else top_wide
    pitch = (high - low) / rows
    found = []

    def half_at(v):
        return (wide + (top_wide - wide) * (v - low) / max(high - low, 1e-9)) / 2

    for row in range(rows):
        bottom, top = low + row * pitch, low + (row + 1) * pitch
        half = min(half_at(bottom), half_at(top))
        cell = 2 * half / columns
        shift = cell / 2 if row % 2 else 0.0
        edges = sorted({-half, half, *[-half + shift + cell * step for step in range(columns + 1)
                                       if -half < -half + shift + cell * step < half]})
        for low_u, high_u in zip(edges[:-1], edges[1:]):
            if high_u - low_u < 0.04:
                continue
            for u0, v0, u1, v1 in split_round(*trimmed(low_u, bottom, high_u, top, clear), holes):
                if u1 - u0 < 0.05 or v1 - v0 < 0.05 or any(
                        math.hypot((u0 + u1) / 2 - hu, (v0 + v1) / 2 - hv) < hr + 0.01 for hu, hv, hr in holes):
                    continue
                thick = depth * (1 + random.uniform(-0.08, 0.08))
                swell = puff * random.uniform(0.75, 1.2)
                if any(u1 > a0 - 0.01 and u0 < a1 + 0.01 and v1 > b0 - 0.01 and v0 < b1 + 0.01
                       for a0, b0, a1, b1 in under):
                    thick, swell = under_depth, 0.006
                near = overlaps_hole(u0, v0, u1, v1, holes, 0.004)
                pillow = rounded_box("cushion", (u0 + SEAM / 2, v0 + SEAM / 2, 0.004),
                                     (u1 - SEAM / 2, v1 - SEAM / 2, thick), min(0.045, (u1 - u0) / 3, (v1 - v0) / 3),
                                     swell, inside=14 if near else 6)
                found += [(part, warped_out(points, holes, (u0, v0, u1, v1)), triangles, smooth)
                          for part, points, triangles, smooth in pillow]
    found += backing(wide, top_wide, low, high, holes, clear)
    return found


def trimmed(low_u, low_v, high_u, high_v, clear):
    """A pillow's rectangle cut back to the side of the bare stretch `clear` [u0, u1] it mostly lies on (an empty
    width when it lies within it)."""
    if clear is None or high_u <= clear[0] or low_u >= clear[1]:
        return low_u, low_v, high_u, high_v
    left, right = max(0.0, clear[0] - low_u), max(0.0, high_u - clear[1])
    return (low_u, low_v, clear[0], high_v) if left >= right else (clear[1], low_v, high_u, high_v)


def split_round(low_u, low_v, high_u, high_v, holes):
    """A pillow's rectangle split at the middle of each round hole inside it, so every piece has the hole's middle
    outside it or on its corner (`warped_out` then bends each away from the hole)."""
    pieces = [(low_u, low_v, high_u, high_v)]
    for hole_u, hole_v, _ in holes:
        split = []
        for u0, v0, u1, v1 in pieces:
            us = [u0, hole_u, u1] if u0 < hole_u < u1 else [u0, u1]
            vs = [v0, hole_v, v1] if v0 < hole_v < v1 else [v0, v1]
            split += [(us[i], vs[j], us[i + 1], vs[j + 1]) for i in range(len(us) - 1) for j in range(len(vs) - 1)]
        pieces = split
    return pieces


def warped_out(points, holes, cell, past=0.01):
    """A pillow's points bent away from each round hole [u, v, r] it overlaps: along each way out of the hole's middle,
    the stretch of the pillow's rectangle `cell` from where the way enters it to where it leaves is drawn onto the
    stretch from `past` beyond the hole's edge to where it leaves, so the pillow stays whole and closed and hugs the
    porthole's rim."""
    points = points.copy()
    low, high = np.array(cell[:2]) - 1e-6, np.array(cell[2:]) + 1e-6
    for hole_u, hole_v, radius in holes:
        centre = np.array([hole_u, hole_v])
        offset = points[:, :2] - centre
        distance = np.maximum(np.linalg.norm(offset, axis=1), 1e-9)
        way = offset / distance[:, None]
        safe = np.where(np.abs(way) < 1e-12, 1e-12, way)
        first, second = (low - centre) / safe, (high - centre) / safe
        enters = np.maximum(np.minimum(first, second).max(axis=1), 0.0)
        leaves = np.maximum(first, second).min(axis=1)
        start = np.minimum(np.maximum(enters, radius + past), leaves - 0.005)
        moved = enters < start
        share = (distance - enters) / np.maximum(leaves - enters, 1e-9)
        reach = np.where(moved, start + share * (leaves - start), distance)
        points[:, :2] = centre + way * reach[:, None]
    return points


def backing(wide, top_wide, low, high, holes, clear, cell=0.02):
    """The seam backing behind a lining's pillows: one sheet facing the room, a cell left out inside each hole and
    the bare stretch."""
    points, triangles = [], []
    for v in np.arange(low, high - 1e-9, cell):
        v1 = min(v + cell, high)
        half = (wide + (top_wide - wide) * (v - low) / max(high - low, 1e-9)) / 2
        for u in np.arange(-half, half - 1e-9, cell):
            u1 = min(u + cell, half)
            if any(math.hypot((u + u1) / 2 - hu, (v + v1) / 2 - hv) < hr for hu, hv, hr in holes):
                continue
            if clear is not None and u1 > clear[0] and u < clear[1]:
                continue
            first = len(points)
            points += [(u, v, 0.003), (u1, v, 0.003), (u1, v1, 0.003), (u, v1, 0.003)]
            triangles += [[first, first + 1, first + 2], [first, first + 2, first + 3]]
    return [piece("seam", points, triangles, False)] if points else []


def bench(wide=1.3, front=0.95, high=0.44, back=0.07, deep=0.58, seed=0, **_):
    """One side's piece of the low cushion ring: a fat cushion from `back` to `deep` off the wall, `high` tall, its
    plan `wide` at the wall and `front` at the room, on a seam plinth."""
    found = rounded_box("cushion", (-wide / 2 + SEAM, 0.0, back), (wide / 2 - SEAM, high, deep), 0.07, 0.025,
                        narrow=front / wide)
    found += rounded_box("cushion", (-wide / 2 + SEAM, high - 0.004, back), (wide / 2 - SEAM, high + 0.12,
                                                                                back + 0.16), 0.05, 0.02)
    return found


def ceiling(apothem=1.0, cell=0.3, depth=0.09, puff=0.025, seed=0, **_):
    """The ceiling's cushions: a grid of pillows `cell` square inside a ten-sided outline `apothem` from the middle
    (its sides facing 0, 36, ... degrees round y), hanging `depth` under y = 0 and facing down."""
    random = np.random.default_rng(seed)
    normals = [(math.sin(math.radians(step * 36)), math.cos(math.radians(step * 36))) for step in range(10)]
    found = []
    count = int(math.ceil(apothem / cell)) + 1
    for column in range(-count, count):
        for row in range(-count, count):
            x0, z0 = column * cell + SEAM / 2, row * cell + SEAM / 2
            x1, z1 = x0 + cell - SEAM, z0 + cell - SEAM
            corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
            reach = max(max(nx * x + nz * z for x, z in corners) for nx, nz in normals)
            if reach > apothem + 0.12 or max(nx * (x0 + x1) / 2 + nz * (z0 + z1) / 2 for nx, nz in normals) > apothem:
                continue
            thick = depth * random.uniform(0.9, 1.1)
            pillow = rounded_box("cushion", (x0, z0, 0.0), (x1, z1, thick), 0.04, puff * random.uniform(0.8, 1.2))
            found += moved(pillow, [[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    return found


def rim(radius=0.215, sleeve=0.14, bolts=12, **_):
    """A porthole's ring round a hole of `radius`: a bright bolted flange over the lining and a sleeve `sleeve` deep
    back through it to the hull."""
    outer = radius + 0.055
    found = turned("rim", [(radius - 0.012, 0.03), (radius - 0.012, 0.0), (outer, 0.0), (outer, 0.022),
                           (outer - 0.015, 0.038), (radius + 0.008, 0.038), (radius - 0.012, 0.03)], segments=64)
    found += turned("rim", [(radius - 0.012, -sleeve), (radius - 0.004, -sleeve), (radius - 0.004, 0.001),
                            (radius - 0.012, 0.001), (radius - 0.012, -sleeve)], segments=64)
    for step in range(bolts):
        angle = 2 * math.pi * step / bolts
        bolt = turned("metal", [(0.0, 0.038), (0.007, 0.038), (0.007, 0.043), (0.004, 0.046), (0.0, 0.046)],
                      segments=6)
        found += moved(bolt, offset=((radius + 0.032) * math.cos(angle), (radius + 0.032) * math.sin(angle), -0.008))
    return found


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
    """A padded bucket seat on a frame: seat pan, back and headrest cushions in a grey shell with side bolsters,
    armrests on posts and a pedestal of tubes to a floor plate (the seat's front toward +z)."""
    found = rounded_box("upholstery", (-0.24, 0.40, -0.22), (0.24, 0.50, 0.26), 0.04, 0.02)
    back = rounded_box("upholstery", (-0.22, 0.0, 0.0), (0.22, 0.6, 0.09), 0.045, 0.02)
    back += rounded_box("shell", (-0.26, -0.02, -0.06), (0.26, 0.64, 0.02), 0.03)
    for side in (-1, 1):
        back += rounded_box("upholstery", (side * 0.27 - 0.045, 0.02, -0.02), (side * 0.27 + 0.045, 0.46, 0.12), 0.035,
                            0.01)
    back += rounded_box("upholstery", (-0.13, 0.66, -0.01), (0.13, 0.84, 0.08), 0.04, 0.015)
    back += rounded_box("shell", (-0.15, 0.64, -0.05), (0.15, 0.86, 0.0), 0.02)
    found += moved(back, about("x", -14), (0.0, 0.46, -0.24))
    found += rounded_box("shell", (-0.27, 0.34, -0.25), (0.27, 0.41, 0.28), 0.025)
    for side in (-1, 1):
        found += rounded_box("upholstery", (side * 0.3 - 0.035, 0.62, -0.16), (side * 0.3 + 0.035, 0.67, 0.2), 0.02,
                             0.005)
        found += tube("frame", [(side * 0.3, 0.41, 0.1), (side * 0.3, 0.62, 0.1)], 0.012, 10)
        found += tube("frame", [(side * 0.3, 0.41, -0.18), (side * 0.3, 0.62, -0.18)], 0.012, 10)
        for z in (-0.18, 0.18):
            found += tube("frame", [(side * 0.17, 0.035, z), (side * 0.17, 0.34, z)], 0.02, 12)
        found += tube("frame", [(side * 0.17, 0.2, -0.18), (side * 0.17, 0.2, 0.18)], 0.014, 10)
    found += box("frame", (-0.24, 0.0, -0.26), (0.24, 0.035, 0.26), 0.006)
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


KINDS = {"lining": lining, "bench": bench, "ceiling": ceiling, "panel": panel, "rim": rim, "console": console,
         "switch_box": switch_box, "seat": seat, "throttle": throttle, "stick": stick, "lamp_fixture": lamp_fixture,
         **ITEMS}


# --- writing --------------------------------------------------------------------------------------------------------

def welded(points, triangles):
    """The piece's points merged where they coincide, and its triangles over them."""
    keys = np.round(points, 7)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    return unique, inverse.reshape(-1)[triangles]


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
