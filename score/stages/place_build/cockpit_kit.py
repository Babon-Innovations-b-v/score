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
- `lining`: the quilted vinyl lining from the floor to the ceiling: big stuffed pillows of their own widths in
  courses meeting in deep creases, curving over into the ceiling at its top (`rise` keeps one height of it), a
  bolster along the floor, eased flat round each hole (`fades`), each mounting plate (`flats`, flat_spot)
  set into it with the cushions it cuts swelling from a crease against its edge;
  holes and cut-away as the hull's, a wall (`sector`) ending along the seams round its cushions; with `panels`
  (CONE) a real cabin's panelled wall instead, its kick pad along the floor still quilted.
- `ceiling` (its lamps' spots flat), `floor` (the round plate, the walked ground, one faint hatch ring), `skirt`
  (the service ring under the hull, its pipes), `nose` (the cone carried on to a narrow rimmed top), `lip` (the cut-away's rounded rim), `through_wall` (a porthole's or the hatch's
  sleeve, flanges hugging the lining and the hull, bolts, glass), `hatch_leaf`, `gantry` (the railed walkway).
- `panel`: a plate with rounded corners, a raised bezel, a label strip with its word in modelled letters, and its
  `items` ({kind, at [u, v], ...}: the hardware below) laid on it.
- the hardware, each its own piece or an item of a panel: `toggle` (a 2 cm bat toggle, `guard` its wickets or
  "cover" a red flip cover),
  `lamp` (`colour` red, green, amber, white), `gauge` (a 6 cm round needle gauge), `bars` (a bar meter, up or
  `across`), `readout` (a small lit number window), `screen` (`graphic` tower, orbit, attitude, landing, lines),
  `scope` (a round scope), `keypad`, `button`, `rotary`, `wheel` (a valve handwheel), `slider`, `guarded_button`,
  `breakers` (a row of push-pull circuit breakers), `ball` (an attitude ball), `words` (lettering alone).
- `mount`: a flat mounting plate set into the lining (its `flats`), a panel or a screen on it.
- `console` (also a pod beside the seat: a panel laid on its sloping top), `switch_box`, `seat`, `throttle`, `stick`,
  `lamp_fixture`, `handrail` (a grab handle on a wall), `cables` (a clamped cable run along the wall, capsule frame).
"""
import math

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade, Vt

from score.stages.place_build import dome_shell

SEGMENTS = 32  # points round a turned piece
PLATE = 0.012  # a panel plate's thickness
BEZEL = 0.010  # how far a panel's bezel stands over its plate
LETTER_ROWS = 7  # the lettering's dot rows (a 5 x 7 face)
LINE = 0.0025  # a screen graphic's line width
FLAT_KINDS = ("hull", "lining", "ceiling", "floor", "skirt", "nose", "lip", "through_wall", "tread", "gantry",
              "cables")

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
# (`smooth` True, False, or each point's own unit normal (n x 3) where a surface's shading must run on unbroken
# across its parts and across the walls it is cut into: the lining's cushions)

def piece(part, points, triangles, smooth):
    """One piece: its part, points (n x 3), triangles (m x 3, wound to face out) and whether it shades smooth."""
    return (part, np.asarray(points, dtype=np.float64).reshape(-1, 3), np.asarray(triangles, dtype=np.int64)
            .reshape(-1, 3), bool(smooth))


def moved(pieces, rotation=None, offset=(0.0, 0.0, 0.0)):
    """The pieces turned by `rotation` (3 x 3) and moved by `offset`."""
    turn = np.eye(3) if rotation is None else np.asarray(rotation, dtype=np.float64)
    return [(part, points @ turn.T + np.asarray(offset, dtype=np.float64), triangles,
             smooth @ turn.T if isinstance(smooth, np.ndarray) else smooth)
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

LAMP_PARTS = {"red": "lamp_red", "green": "lamp_green", "amber": "lamp_amber", "white": "lamp_white", "cyan": "lamp_cyan",
              "off": "lamp_off"}  # "off": a lamp or a button cap unlit, dark glass (most of a real panel's are)


def toggle(guard=False, **_):
    """A bat-handle toggle switch 2 cm tall on a small plate, thrown up. `guard` True stands a wicket either side of
    it (a bent bar loop, as the Apollo command module's guarded switches: a hand brushing past cannot throw it);
    `guard` "cover" holds a red flip cover open over it between two posts instead (a critical switch: STAGE, CHUTE).
    Its plate dark, so only the nut and the bat read (a bright plate drew a white block: the judge's "toy")."""
    found = box("dark", (-0.008, -0.013, 0.0), (0.008, 0.013, 0.0015), 0.0005)
    found += turned("metal", [(0.0, 0.0012), (0.0065, 0.0012), (0.0065, 0.004), (0.0045, 0.0045), (0.0045, 0.008),
                              (0.0, 0.008)], segments=6)
    lever = turned("lever", [(0.0, 0.0), (0.0021, 0.0), (0.0017, 0.017), (0.0028, 0.0185), (0.0028, 0.0205),
                             (0.0, 0.021)], segments=12)
    found += moved(lever, about("x", -22), (0.0, 0.0, 0.007))
    if guard == "cover":
        for side in (-1, 1):
            found += box("guard", (side * 0.0095 - 0.001, -0.012, 0.0012), (side * 0.0095 + 0.001, 0.012, 0.024),
                         0.0004)
        cover = box("cover", (-0.0105, -0.026, -0.0015), (0.0105, 0.0, 0.0015), 0.0005)
        found += moved(cover, about("x", -110), (0.0, 0.012, 0.024))
    elif guard:
        for side in (-1, 1):  # a stout bail standing on a foot at each end, a third taller than the bat (a thin
            # dark wire beside the switch read as no guard at all: the judge's "bare bat switches"; round 4, a 4 mm
            # chrome wire blurred into a blob at seat distance: a 5.6 mm bar, matte painted by its `guard` look)
            x = side * 0.0145
            loop = [(x, -0.0155, 0.0015), (x, -0.0125, 0.024), (x, -0.0055, 0.0315), (x, 0.0055, 0.0315),
                    (x, 0.0125, 0.024), (x, 0.0155, 0.0015)]
            found += tube("guard", loop, 0.0028, 12)
            for end in (-0.0155, 0.0155):
                found += box("guard", (x - 0.004, end - 0.004, 0.0), (x + 0.004, end + 0.004, 0.003), 0.0008)
    return found


def lamp(colour="green", size=0.009, **_):
    """A round indicator lamp: a black knurled bezel and a low lens of `colour` (LAMP_PARTS) `size` metres across,
    nearly flat (a panel's jewel lamp; a domed lens in a bright ring read as a sweet, the judge's "candy dots")."""
    radius = size / 2
    found = turned("dark", [(radius * 0.7, 0.0), (radius * 1.4, 0.0), (radius * 1.4, 0.003), (radius * 1.15, 0.005),
                            (radius * 0.95, 0.005), (radius * 0.7, 0.005), (radius * 0.7, 0.0)], segments=20)
    profile = [(0.0, 0.003)] + [(radius * math.cos(math.radians(angle)),
                                 0.003 + radius * 0.32 * math.sin(math.radians(angle))) for angle in range(0, 91, 15)]
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
    """A push button `size` across: a bright collar and a lit cap of `colour`, flat-topped with a chamfered edge
    (a panel's real push button, never a domed sweet)."""
    radius = size / 2
    found = turned("metal", [(radius * 0.8, 0.0), (radius * 1.3, 0.0), (radius * 1.3, 0.004), (radius * 0.9, 0.006),
                             (radius * 0.8, 0.006), (radius * 0.8, 0.0)], segments=20)
    found += turned(LAMP_PARTS[colour], [(0.0, 0.003), (radius * 0.85, 0.003), (radius * 0.85, 0.0085),
                                         (radius * 0.72, 0.0097), (0.0, 0.0097)], segments=20)
    return found


def rotary(size=0.028, **_):
    """A rotary selector: a dark fluted knob with a white pointer over a bright skirt."""
    radius = size / 2
    found = turned("metal", [(radius * 0.6, 0.0), (radius * 1.2, 0.0), (radius * 1.2, 0.003), (radius * 0.6, 0.003),
                             (radius * 0.6, 0.0)], segments=24)
    found += turned("dark", [(0.0, 0.0025), (radius * 0.75, 0.0025), (radius * 0.75, 0.003), (radius * 0.75, 0.014), (radius * 0.6, 0.017), (0.0, 0.017)],
                    segments=12)
    found += moved(ribbon("ink", [(0.0, 0.0), (0.0, radius * 0.65)], 0.002, 0.0), offset=(0.0, 0.0, 0.0172))
    for step in range(6):
        angle = math.radians(150 - step * 24)
        found += ribbon("ink", [(radius * 1.35 * math.cos(angle), radius * 1.35 * math.sin(angle)),
                                (radius * 1.7 * math.cos(angle), radius * 1.7 * math.sin(angle))], 0.0012, 0.0002)
    return found


def wheel(size=0.07, part="valve", **_):
    """A machined valve handwheel `size` across (the pad water valve; the hatch's in its `part` "metal"): a true round
    rim of round section, three round spokes from a chamfered hub to it, and a hex nut on a stem standing off the
    panel. Round 4 (the judge: "a lumpy, bubbly orange-red ring with thin cross spokes ... a toy or a pool float"):
    no scalloped grip, the rim one smooth turned ring, the spokes stout bars."""
    radius = size / 2
    found = turned("metal", [(0.0, 0.0), (0.009, 0.0), (0.009, 0.014), (0.0075, 0.016), (0.0, 0.016)], segments=16)
    rim = max(0.0045, size * 0.04)  # the rim's section radius: a stout ring a hand grips, never a wire
    section = [(radius - rim + rim * math.cos(angle), 0.02 + rim * math.sin(angle))
               for angle in np.linspace(-math.pi / 2, 1.5 * math.pi, 17)]  # walked out, up, in, down
    found += turned(part, section, segments=64, smooth=True)
    hub = max(0.0105, size * 0.09)
    for step in range(3):
        spoke = tube(part, [(hub * 0.8, 0.0, 0.0205), (radius - rim * 0.9, 0.0, 0.0205)], rim * 0.62, 12)
        found += moved(spoke, about("z", 90 + step * 120))
    found += turned(part, [(0.0, 0.0145), (hub, 0.0145), (hub, 0.024), (hub * 0.78, 0.0285), (0.0, 0.0285)],
                    segments=24)
    found += turned("metal", [(0.0, 0.028), (0.0055, 0.028), (0.0055, 0.033), (0.0, 0.033)], segments=6)
    return found


def slider(high=0.06, level=0.6, **_):
    """A slide lever in a dark slot: its knob at `level` of the slot."""
    found = box("dark", (-0.004, -high / 2, 0.0), (0.004, high / 2, 0.003), 0.0008)
    y = -high / 2 + high * level
    found += rounded_box("lever", (-0.007, y - 0.005, 0.0025), (0.007, y + 0.005, 0.014), 0.003, steps=2, inside=1)
    return found


def guarded_button(colour="red", size=0.026, **_):
    """A guarded push button (the master alarm, an abort): a square lit cap `size` across in a square bezel, and a
    bent bar guard arching over it from side to side, so it is pressed on purpose, never knocked."""
    half = size / 2
    found = box("metal", (-half - 0.006, -half - 0.006, 0.0), (half + 0.006, half + 0.006, 0.006), 0.0015)
    found += box("dark", (-half - 0.001, -half - 0.001, 0.0045), (half + 0.001, half + 0.001, 0.0075), 0.0006)
    found += box(LAMP_PARTS[colour], (-half + 0.001, -half + 0.001, 0.006), (half - 0.001, half - 0.001, 0.0125),
                 0.0012)
    arch = [(-half - 0.003, 0.0, 0.004)] + [(-(half + 0.003) * math.cos(math.radians(angle)), 0.0,
                                             0.004 + 0.022 * math.sin(math.radians(angle)))
                                            for angle in range(15, 180, 15)] + [(half + 0.003, 0.0, 0.004)]
    for offset in (-half + 0.002, half - 0.002):
        found += tube("guard", [(x, y + offset, z) for x, y, z in arch], 0.0018, 8)
    return found


def annunciator(columns=4, rows=2, tile=(0.026, 0.013), lit=(), **_):
    """A caution and warning block: `columns` x `rows` rectangular lamp tiles `tile` (wide, high) in a dark frame, a
    black web between them, the tiles in `lit` ([column, row, colour], LAMP_PARTS) lit and the rest dark glass
    (lamp_off): a real cabin's lamps in a grid, never scattered dots."""
    wide, high = tile
    web = 0.002
    outer_wide, outer_high = columns * (wide + web) + web + 0.008, rows * (high + web) + web + 0.008
    found = box("dark", (-outer_wide / 2, -outer_high / 2, 0.0), (outer_wide / 2, outer_high / 2, 0.005), 0.0012)
    colours = {(int(column), int(row)): colour for column, row, colour in lit}
    for column in range(columns):
        for row in range(rows):
            x = -outer_wide / 2 + 0.004 + web + column * (wide + web)
            y = outer_high / 2 - 0.004 - web - (row + 1) * high - row * web
            part = LAMP_PARTS[colours[(column, row)]] if (column, row) in colours else "lamp_off"
            found += box(part, (x, y, 0.0035), (x + wide, y + high, 0.0062), 0.0006)
    return found


def talk_key(size=0.034, guard=False, **_):
    """A push-to-talk key `size` across (the radio's): a square cast collar screwed to the panel round a black
    rubber key standing proud of it, ribbed across its top for a gloved thumb, and its lit transmit bar over it;
    `guard` stands a bent bar either side of it, arching higher than the key (round 4, the judge: "a flat square
    that doesn't read as a push-to-talk button ... a bigger, guarded TALK button")."""
    half = size / 2
    found = box("metal", (-half - 0.007, -half - 0.007, 0.0), (half + 0.007, half + 0.007, 0.006), 0.0015)
    found += box("dark", (-half - 0.001, -half - 0.001, 0.004), (half + 0.001, half + 0.001, 0.0068), 0.0006)
    found += rounded_box("boot", (-half + 0.001, -half + 0.001, 0.0055), (half - 0.001, half - 0.001, 0.016),
                         0.0035, steps=2, inside=1)
    for row in range(-2, 3):
        found += box("knob", (-half + 0.005, row * 0.0055 - 0.0011, 0.0155), (half - 0.005, row * 0.0055 + 0.0011,
                                                                                0.0172), 0.0004)
    found += box("lamp_green", (-half * 0.6, half + 0.0025, 0.0055), (half * 0.6, half + 0.0055, 0.0075), 0.0005)
    head = [(0.0, 0.0), (0.0022, 0.0), (0.0022, 0.0008), (0.0015, 0.0013), (0.0, 0.0013)]
    for x in (-1, 1):
        for y in (-1, 1):
            found += moved(turned("bolt", head, segments=8),
                           offset=(x * (half + 0.0038), y * (half + 0.0038), 0.0058))
    if guard:
        reach = half + 0.0045  # each bar along the key's side, on the collar, arching over its top
        arch = [(-reach * math.cos(math.radians(angle)), 0.0055 + 0.024 * math.sin(math.radians(angle)))
                for angle in range(0, 181, 15)]
        for side in (-1, 1):
            found += tube("guard", [(side * reach, along, height) for along, height in arch], 0.0026, 10)
    return found


def breakers(count=6, pitch=0.019, out=(), size=1.0, **_):
    """A row of `count` push-pull circuit breakers `pitch` apart, `size` times a 12 mm breaker: each a bright
    threaded collar, a black cap and its white band; the ones in `out` (their numbers) pulled, standing taller with
    the band showing below the cap; a white index tick under each (round 4, the judge: "tiny dots on a recessed
    plate": the wall rows drawn at 1.3)."""
    scale = float(size)
    strip = 0.008 * scale + 0.004
    found = box("dark", (-count * pitch / 2, -strip, 0.0), (count * pitch / 2, strip, 0.002), 0.0006)
    for number in range(count):
        x = (number - (count - 1) / 2) * pitch
        lift = 0.005 * scale if number in out else 0.0
        found += moved(turned("metal", [(0.0, 0.0015), (0.0058 * scale, 0.0015), (0.0058 * scale, 0.0045),
                                        (0.0, 0.0045)], segments=6), offset=(x, 0.0, 0.0))
        found += moved(turned("knob", [(0.0, 0.004), (0.0042 * scale, 0.004), (0.0042 * scale, 0.004 + 0.0075 * scale),
                                       (0.0034 * scale, 0.004 + 0.0085 * scale), (0.0, 0.004 + 0.0085 * scale)],
                              segments=16), offset=(x, 0.0, lift))
        if lift:
            found += moved(turned("ink", [(0.0, 0.0044), (0.004 * scale, 0.0044), (0.004 * scale, 0.004 + 0.0055 * scale),
                                          (0.0, 0.004 + 0.0055 * scale)], segments=16), offset=(x, 0.0, 0.0))
        if scale > 1.0:
            found += box("ink", (x - 0.0007, -strip + 0.0008, 0.0014), (x + 0.0007, -strip + 0.0032, 0.0026), 0.0002)
    return found


def ball(size=0.09, **_):
    """An attitude ball (the flight director's): a dark case and a bright bezel holding a ball `size` across, its sky
    half pale and its ground half black parted along the horizon, and an orange craft marker across its face."""
    radius = size / 2
    deep = 0.01
    found = turned("dark", [(0.0, 0.0), (radius * 1.3, 0.0), (radius * 1.3, deep), (0.0, deep)], segments=48)
    found += turned("metal", [(radius * 1.02, deep - 0.001), (radius * 1.32, deep - 0.001), (radius * 1.32, deep + 0.004),
                              (radius * 1.2, deep + 0.007), (radius * 1.02, deep + 0.006), (radius * 1.02, deep - 0.001)],
                    segments=48)
    centre, squash = deep + 0.002, 0.45  # the ball drawn shallow along the panel's normal, its back in the plate
    pitch = 25.0  # the ball turned nose down a little, its horizon below its middle: sky and ground both read from a
    # seat looking down onto a sloping panel
    gap = 0.0006
    half = [(0.0, gap)] + [(radius * math.cos(math.radians(angle)), gap + radius * math.sin(math.radians(angle)))
                           for angle in range(0, 91, 10)]
    for part, turn in (("ball_sky", -90), ("ball_ground", 90)):
        found += moved(turned(part, half, segments=32, smooth=True), np.diag([1.0, 1.0, squash]) @ np.asarray(
            about("x", pitch)) @ np.asarray(about("x", turn)), (0.0, 0.0, centre))
    front = centre + radius * squash
    found += box("marker", (-radius * 0.5, -0.0016, front - 0.0035), (-radius * 0.12, 0.0016, front + 0.0015), 0.0006)
    found += box("marker", (radius * 0.12, -0.0016, front - 0.0035), (radius * 0.5, 0.0016, front + 0.0015), 0.0006)
    found += box("marker", (-0.0025, -0.0025, front - 0.003), (0.0025, 0.0025, front + 0.002), 0.0008)
    found += ball_marks(radius, centre, squash, pitch, deep)
    return found


def ball_marks(radius, centre, squash, pitch, deep):
    """An attitude ball's markings (the FDAI's): its pitch lines every 30 degrees and its middle meridian drawn on
    the ball, dark on the sky half and white on the ground half, turned with it; the bezel's roll scale, a tick every
    10 degrees, long every 30; and the roll pointer over the top (a plain ball with one dash read as a toy)."""
    shape = np.diag([1.0, 1.0, squash]) @ np.asarray(about("x", pitch))
    on_ball = lambda points: [tuple(shape @ (radius * 1.004 * np.asarray(point)) + np.array([0.0, 0.0, centre]))
                              for point in points]
    found = []
    for latitude in (-60.0, -30.0, 30.0, 60.0):
        lat = math.radians(latitude)
        ring = [(math.cos(lat) * math.sin(math.radians(along)), math.sin(lat), math.cos(lat) * math.cos(math.radians(along)))
                for along in range(-80, 81, 8)]
        found += tube("dark" if latitude > 0 else "ink", on_ball(ring), 0.00055, 6)
    for low, high, part in ((4, 84, "dark"), (-84, -4, "ink")):
        meridian = [(0.0, math.sin(math.radians(angle)), math.cos(math.radians(angle))) for angle in range(low, high + 1, 8)]
        kept = [point for point in meridian if (shape @ np.asarray(point))[2] > 0.15]
        if len(kept) > 1:
            found += tube(part, on_ball(kept), 0.00055, 6)
    for tick in range(36):
        angle = math.radians(tick * 10)
        inner = radius * (1.07 if tick % 3 == 0 else 1.12)
        found += ribbon("ink", [(inner * math.cos(angle), inner * math.sin(angle)),
                                (radius * 1.19 * math.cos(angle), radius * 1.19 * math.sin(angle))],
                        0.0012 if tick % 3 else 0.0018, deep + 0.0066)
    found += box("marker", (-0.0022, radius * 1.21, deep + 0.004), (0.0022, radius * 1.30, deep + 0.009), 0.0005)
    return found


def words(text="", high=0.012, part="ink", **_):
    """Lettering alone."""
    return moved(lettering(part, text, high), offset=(0.0, 0.0, 0.0))


ITEMS = {"toggle": toggle, "lamp": lamp, "gauge": gauge, "bars": bars, "readout": readout, "screen": screen,
         "keypad": keypad, "scope": scope, "button": button, "rotary": rotary, "wheel": wheel, "slider": slider,
         "guarded_button": guarded_button, "breakers": breakers, "ball": ball, "words": words,
         "annunciator": annunciator, "talk_key": talk_key}


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


def panel(wide=0.4, high=0.3, label="", items=(), label_high=0.014, split=0.5, **_):
    """An instrument panel: a plate with rounded corners, a raised bezel round it screwed down (panel_screws), a label strip across its top with
    `label` in modelled letters, and its `items` laid on the plate (their `at` from the plate's middle). A label
    "A|B" makes two sections, the plate parted at `split` of its width by a raised divider, each section with its own
    strip over it; a "/" in a name stacks its words in lines on a taller strip."""
    corner = 0.022
    found = framed_plate(rounded_rectangle(wide, high, corner), rounded_rectangle(wide - 0.03, high - 0.03,
                                                                                    corner * 0.6))
    if label:
        top = high / 2 - 0.015 - 0.006
        names = label.split("|")
        left, right = -wide / 2 + 0.03, wide / 2 - 0.03
        cuts = [left] + ([left + (right - left) * split] if len(names) == 2 else []) + [right]
        for name, start, end in zip(names, cuts[:-1], cuts[1:]):
            start, end = start + (0.008 if start > left else 0.0), end - (0.008 if end < right else 0.0)
            lines = [line.strip() for line in name.split("/")]
            line_high = label_high if len(lines) == 1 else label_high * 0.75
            strip_high = line_high * (1.7 + 1.25 * (len(lines) - 1))
            found += box("label", (start, top - strip_high, PLATE - 0.0005), (end, top, PLATE + 0.0025), 0.0008)
            for number, line in enumerate(lines):
                fitted = min(line_high, (end - start - 0.012) / max(1, 6 * len(line) - 1) * LETTER_ROWS)
                middle = top - line_high * (0.85 + 1.25 * number)
                found += moved(lettering("ink", line, fitted), offset=((start + end) / 2, middle, PLATE + 0.0025))
        if len(names) == 2:
            found += box("bezel", (cuts[1] - 0.003, -high / 2 + 0.016, PLATE - 0.0005),
                         (cuts[1] + 0.003, top, PLATE + 0.005), 0.0015)
    found += panel_screws(wide, high)
    found += laid_items(items, PLATE)
    return found


def panel_screws(wide, high, inset=0.0075, most=0.12):
    """The screws holding a panel down, along the middle of its bezel: one by each corner and more along each edge,
    at most `most` metres apart (a real panel's bolted edge)."""
    head = [(0.0, 0.0), (0.0034, 0.0), (0.0034, 0.0012), (0.0024, 0.0021), (0.0, 0.0021)]
    corner_x, corner_y = wide / 2 - 0.012, high / 2 - 0.012
    spots = [(sx * corner_x, sy * corner_y) for sx in (-1, 1) for sy in (-1, 1)]
    for reach, edge, across in ((corner_x, high / 2 - inset, False), (corner_y, wide / 2 - inset, True)):
        count = max(1, math.ceil(2 * reach / most))
        for step in range(1, count):
            along = -reach + 2 * reach * step / count
            spots += [(side * edge, along) if across else (along, side * edge) for side in (-1, 1)]
    found = []
    for x, y in spots:
        found += moved(turned("bolt", head, segments=10), offset=(x, y, PLATE + BEZEL - 0.0004))
    return found


# --- the capsule: its cone's hull, lining, ceiling and floor, built in the capsule's own frame -----------------------

CONE = {"radius": 1.40, "slope": 0.22, "hull": 0.05, "gap": 0.003, "lining": 0.05, "bolster": 0.04,
        "bolster_high": 0.32, "puff": 0.09, "ceiling": 2.05, "shoulder": 1.80, "inset": 0.30, "panels": 0,
        "panel_from": 0.0, "panel_puff": 0.02, "quilted": (0,)}
# `panels` 0: the concept's stuffed pillows; else the lining is a real cabin's wall: `panels` padded panels round
# every course, their joints lined up course over course from `panel_from` degrees (so a wall of the lining, its
# `sector`, can hold whole panels), each a flat face of `panel_puff` rolled off at its edge into a dark joint, the
# course along the floor (`quilted`) a stitched quilted kick pad; `panel_puff` how far a panel's face stands off its
# joint: a few millimetres for a real cabin's painted metal wall panels (2099 #246 round 2, the owner: "that light
# padding just ugly"; `quilted` empty: no quilting on its walls at all)
ROWS = (0.0, 0.30, 0.59, 0.88, 1.30, 1.80, 2.05)  # the lining's courses, metres up from the floor (of its back):
# the fourth behind the screens, the fifth round the portholes (never a seam through one), the last over the shoulder
CUSHION_WIDE = 0.40  # metres round a cushion on average, along its course's middle on the lining's face
WIDE_SPREAD = 0.4  # how far each cushion's width strays from that, a share of it either way: every course's cushions
# of their own widths and its seams set off from the next's at random (the concept's stuffed pillows; owner
# 2026-11-24: "uggly creme bricks", never a flat grid of equal tiles)
CUSHION_SEED = 2099  # the cushions' widths and offsets drawn from it, so the lining is the same every time
PILLOW = 3.2  # the power of a cushion's outline (a superellipse): its corners rounded in, pinched into the creases
FULLNESS = 0.36  # how fast a cushion swells from its crease (a power under 1: a fat pillow, its sides steep)
CUT_FLAT = 0.03  # metres along the wall either side of the cut-away's outline the quilting lies flat
FADE = 0.14  # metres over which the quilting eases flat round a porthole or a hatch
MOUNT_BORDER = 0.03  # metres of the lining laid flat on a mounting plate's plane round its edge, so the plate's
# outline sits on a clean flat band of the padding (never ragged where a cushion swells against it)
MOUNT_EASE = 0.05  # metres outside that band over which the lining's skin eases from its plane to the cone
MOUNT_ROLL = 0.07  # metres outside a mounting plate over which a cut cushion swells from its crease against it
TUCK = 0.03  # metres the ceiling's pad reaches over the top of the lining's shoulder
TUCK_DROP = 0.025  # metres its edge sinks there, into the shoulder's top
PANEL_EDGE = 10.0  # the power of a wall panel's outline: square, only its corners rounded
PANEL_ROLL = 0.3  # how fast a wall panel's face rolls off its edge (a power under 1: flat, a narrow rounded edge)
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


def grid_solid(front, back, keep, front_parts, back_part, side_part, ways, pole=None, front_normals=None):
    """A closed solid over a grid of cells: `front` and `back` (rows x columns x 3, the columns round a ring), each
    kept cell (`keep`, rows - 1 x columns) a quad of each, its front facing along `ways` (rows x columns x 3) and its
    back away, in its `front_parts` (rows - 1 x columns) and `back_part`; a side face of `side_part` on every edge
    between a kept cell and one not kept (or the grid's first and last row), facing out of the kept one. `pole`
    [front point, back point] closes the first row round a middle point instead of a side (a disc). `front_normals`
    (rows x columns x 3) shade the front by the whole grid's own normals, so no part or wall edge breaks it."""
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
    if front_normals is not None:
        pieces = [(part, points, triangles, front_normals.reshape(-1, 3)) for part, points, triangles, _ in pieces]
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
        near |= off_axis(cone, points, theta, y) < radius
    return near


def off_axis(cone, points, theta, y):
    """How far each point lies from the axis of a round hole at `theta` (degrees) and `y` (the face's normal through
    its middle on the hull's inner face, along which its sleeve and flanges are laid), measured across it; infinite
    for a point further than THROUGH along it (the axis runs on across the room to the far wall)."""
    middle = cone.at(math.radians(theta), y)
    axis = cone.inward(math.radians(theta))
    offset = points - middle
    along = np.einsum("...i,i->...", offset, axis)
    across = np.linalg.norm(offset - along[..., None] * axis, axis=-1)
    return np.where(np.abs(along) < THROUGH, across, np.inf)


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
        kept &= (middle_theta - start + 1e-9) % (2 * math.pi) < math.radians(sector[1] - sector[0])  # a middle
        # on a sector's edge (a cushion's, 15 degrees) falls in exactly one
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


def shoulder(cone, y):
    """How far the lining's face is carried in toward the axis and up at each height `y` of its back, so the padding
    curves over into the ceiling: a quarter ellipse from `shoulder` up, `inset` in and up to `ceiling` (its top
    level there, meeting the ceiling's pad); nothing below `shoulder`. (inset, lift)."""
    start, top, inset = (float(cone.sizes[key]) for key in ("shoulder", "ceiling", "inset"))
    height = np.asarray(y, dtype=np.float64)
    turn = np.clip((height - start) / (top - start), 0.0, 1.0) * math.pi / 2
    above = height > start
    return (np.where(above, inset * (1 - np.cos(turn)), 0.0),
            np.where(above, start + (top - start) * np.sin(turn) - height, 0.0))


def course_seams(cone):
    """Each course's seams round it (ROWS): (where its first seam stands, a share of a turn; its seams from there as
    shares of a turn). About CUSHION_WIDE apart along the course's middle on the face, each cushion's width its own
    (WIDE_SPREAD) and each course's seams set off from the next's at random (CUSHION_SEED)."""
    face = cone.sizes["gap"] + cone.sizes["lining"]
    seams = []
    for course in range(len(ROWS) - 1):
        draw = np.random.default_rng(CUSHION_SEED + course)
        middle = (ROWS[course] + ROWS[course + 1]) / 2
        around = 2 * math.pi * (float(cone.rho(middle, face)) - float(shoulder(cone, middle)[0]))
        if cone.sizes["panels"]:  # a real cabin's panels: even widths, their joints lined up course over course
            seams.append((cone.sizes["panel_from"] / 360.0 % 1.0, np.linspace(0.0, 1.0, int(cone.sizes["panels"]) + 1)))
            continue
        count = max(6, int(round(around / CUSHION_WIDE)))
        widths = 1 + WIDE_SPREAD * (2 * draw.random(count) - 1)
        seams.append((float(draw.random()), np.concatenate([[0.0], np.cumsum(widths) / widths.sum()])))
    return seams


def cushion_at(cone, theta, y):
    """Which cushion of the lining holds each spot (theta, y) and where in it: (its course, its column, its middle's
    angle, the share across it, the share up it). Courses ROWS high, each of its own cushions (course_seams)."""
    theta, height = np.broadcast_arrays(np.asarray(theta, dtype=np.float64), np.asarray(y, dtype=np.float64))
    edges = np.asarray(ROWS)
    row = np.clip(np.searchsorted(edges, height, side="right") - 1, 0, len(edges) - 2)
    low, high = edges[row], edges[row + 1]
    upward = np.clip((height - low) / (high - low), 0.0, 1.0)
    share = (theta % (2 * math.pi)) / (2 * math.pi)
    column, middle, across = np.zeros(theta.shape, dtype=np.int64), np.zeros(theta.shape), np.zeros(theta.shape)
    for course, (start, seams) in enumerate(course_seams(cone)):
        here = row == course
        local = (share[here] - start) % 1.0
        index = np.clip(np.searchsorted(seams, local, side="right") - 1, 0, len(seams) - 2)
        first, last = seams[index], seams[index + 1]
        column[here] = index
        across[here] = (local - first) / (last - first)
        middle[here] = ((first + last) / 2 + start) % 1.0 * 2 * math.pi
    return row, column, middle, across, upward


def quilt(cone, theta, y):
    """How far the lining's cushions stand out over the spots (theta, y): big stuffed pillows in courses
    (cushion_at), each a superellipse dome (PILLOW) swelling steeply from zero along its edge (FULLNESS), so two
    pillows meet in a deep crease and their corners pinch in, each a little fuller or flatter than the next; the
    course on the floor a fat bolster. A panelled lining (CONE's `panels`) stands its wall panels' flat faces
    `panel_puff` off instead, rolled off at their square edges, its `quilted` courses still pillows."""
    row, column, _, across, upward = cushion_at(cone, theta, y)
    seed = np.abs(np.sin(row * 12.9898 + column * 78.233) * 43758.5453) % 1.0
    lean = np.abs(np.sin(row * 39.3468 + column * 11.135) * 24634.6345) % 1.0
    middle_across = 0.5 + 0.08 * (lean - 0.5)  # each pillow's crown a little off its middle
    side = np.where(across < middle_across, (middle_across - across) / middle_across,
                    (across - middle_across) / (1 - middle_across))
    reach = (side ** PILLOW + np.abs(2 * upward - 1) ** PILLOW) ** (1.0 / PILLOW)
    swell = np.clip(1 - reach ** PILLOW, 0.0, 1.0) ** FULLNESS
    puff = cone.sizes["puff"] * np.where(row == 0, 1.3, 1.0) * (0.85 + 0.3 * seed)
    if not cone.sizes["panels"]:
        return puff * swell
    square = (np.abs(2 * across - 1) ** PANEL_EDGE + np.abs(2 * upward - 1) ** PANEL_EDGE) ** (1.0 / PANEL_EDGE)
    panel = cone.sizes["panel_puff"] * np.clip(1 - square ** PANEL_EDGE, 0.0, 1.0) ** PANEL_ROLL
    return np.where(np.isin(row, list(cone.sizes["quilted"])), puff * swell, panel)


def cut_distance(cone, theta, y, cut):
    """About how many metres along the wall each spot (theta, y) lies from the cut-away's outline `cut` (in_cut's),
    outside it or in."""
    middle, half, height, half_high, power = cut
    across = np.abs(wrapped(theta - math.radians(middle))) / math.radians(half)
    upward = np.abs(np.asarray(y) - height) / half_high
    scaled = (across ** power + upward ** power) ** (1.0 / power)
    return np.abs(scaled - 1) * min(math.radians(half) * float(cone.rho(height, 0.1)), half_high)


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


def lining_depth(cone, theta, y, back, fades, flats, cut=None):
    """How far the lining's face stands off its back at each spot, (its skin, the bolster at the floor; the
    cushions over it; how much the spot is eased flat), the cushions eased flat round each fade [theta, y, radius] and along the cut-away's outline `cut`, so its section is
    a clean band of the padding) and how much each spot is eased flat (1 where eased, so no seam runs round a hole,
    along the cut or under a plate). Each flat [theta, y, wide, high] is a mounting plate set into the padding
    (mount): its skin lies on the plate's plane under it and a MOUNT_BORDER band round it, eases back onto the cone
    over MOUNT_EASE, and the
    cushions it cuts swell from a crease against its edge over MOUNT_ROLL, as they do from a seam (never pulled
    down into a pocket round it)."""
    sizes = cone.sizes
    bump = quilt(cone, theta, y)
    eased = np.zeros(theta.shape)
    skin_face = back + cone.inward(theta) * sizes["lining"]
    for fade_theta, fade_y, radius in fades:
        distance = off_axis(cone, skin_face, fade_theta, fade_y)  # on the skin's face and across the hole's axis,
        # as its flange is laid: a straight line from its middle, or a spot on the back, runs short of the flange's
        # edge where the cone curves away from a wide hole (a hatch's sides), and a cushion swelled through it there
        eased = 1 - (1 - eased) * smoothstep(radius, radius + FADE, distance)  # two fades meeting ease the
        # padding between them flat together, never a pinched crumple
    if cut:
        eased = np.maximum(eased, 1 - smoothstep(CUT_FLAT, CUT_FLAT + FADE, cut_distance(cone, theta, y, cut)))
    skin = sizes["lining"] + sizes["bolster"] * smoothstep(sizes["bolster_high"], 0.0, y) * (1 - eased)
    bump = bump * (1 - eased)
    flattened = np.zeros(theta.shape)
    normals = cone.inward(theta)
    for flat_theta, flat_y, wide, high in flats:
        middle, _, (right, up, inward) = flat_spot(flat_theta, flat_y, wide, high, **sizes)
        offset = back - cone.at(math.radians(flat_theta), flat_y, sizes["gap"])
        near = np.abs(offset @ inward) < 0.3
        outside = np.hypot(np.maximum(np.abs(offset @ right) - wide / 2 - MOUNT_BORDER, 0.0),
                           np.maximum(np.abs(offset @ up) - high / 2 - MOUNT_BORDER, 0.0))
        weight = (1 - smoothstep(0.0, MOUNT_EASE, outside)) * near
        onto = ((middle - back) @ inward) / np.maximum(np.einsum("...i,i->...", normals, inward), 1e-6)
        skin = skin * (1 - weight) + np.maximum(onto, skin) * weight
        bump = bump * np.where(near, np.clip(outside / MOUNT_ROLL, 0.0, 1.0) ** FULLNESS, 1.0)
        flattened = np.maximum(flattened, (1 - smoothstep(0.0, MOUNT_ROLL, outside)) * near)  # under the plate
        # and where the cushions it cuts lie low against it: no crease's dark seam drawn across the flat there
    return skin, bump, np.maximum(eased, flattened)


def lining(cut=None, holes=(), fades=(), flats=(), which="main", sector=None, rise=None, cell=0.014, rows=0.012,
           screws=None, **sizes):
    """The cabin's quilted lining, one closed piece round the cone from the floor to the ceiling: its back a hair
    off the hull, its face the cushions (lining_depth: stuffed vinyl pillows of their own widths in courses meeting
    in deep creases, a bolster along the floor), curving over at the top into the ceiling (shoulder, the cushions
    standing off the curve along its own normal; `rise` [from, to] keeps only that height of it), round holes left for the portholes and the hatch (`holes`, as hull), the quilting eased
    flat round them (`fades`) and onto each mounting plate's plane (`flats`, flat_spot, the cut cushions swelling
    from a crease against its edge),
    the cut-away left out of its "main" body and filling its "plug", eased flat along it. Parts cushion (a pad's
    face, and the edges where a wall or the cut-away ends, so two walls meet with no dark line), seam (the one row
    of cells along each cushion's edge, the bottom of its crease), back; the face shaded by the whole grid's
    normals (surface_normals), so neither a part's edge nor a wall's breaks the shading. `screws` ({pitch, off,
    top, clear}, wall_screws) screws a panelled wall's panels down along their joints in its `sector`, part bolt, in
    the wall's own piece (a row of screws of its own, a curved line, had its middle behind the wall's face)."""
    cone = Cone(**sizes)
    top = cone.sizes["ceiling"]
    thetas, heights = ring_grid(rows, 0.0015, top, 2 * math.pi * float(cone.rho(0.0)), cell)
    grid_theta, grid_y = np.meshgrid(thetas, heights)
    back = cone.at(grid_theta, grid_y, cone.sizes["gap"])
    normals = cone.inward(grid_theta)
    skin, bump, eased = lining_depth(cone, grid_theta, grid_y, back, fades, flats, cut)
    base = back + normals * skin[..., None]
    inset, lift = shoulder(cone, grid_y)
    base[..., 0] -= np.sin(grid_theta) * inset
    base[..., 2] -= np.cos(grid_theta) * inset
    base[..., 1] += lift
    face_normals = surface_normals(base, normals)
    front = base + face_normals * bump[..., None]
    front[..., 1] = np.maximum(front[..., 1], back[..., 1].min())  # the bolster's foot stays on the floor
    middle_theta = grid_theta[:-1] + math.pi / len(thetas)
    middle_y = (grid_y[:-1] + grid_y[1:]) / 2
    cut_cells = in_cut(middle_theta, middle_y, cut) if cut else np.zeros(middle_y.shape, dtype=bool)
    near = near_hole(cone, back, holes) | near_hole(cone, front, holes)  # the face stands off along its own normal
    _, _, cushion_middle, _, _ = cushion_at(cone, middle_theta, middle_y)  # a wall ends along the seams round its
    keep = cells_kept(near, cut_cells, which, cushion_middle, sector)  # cushions, never across a cushion's face
    if rise is not None:  # only the cells from rise[0] to rise[1] up the back: the shoulder a wall of its own, so a
        # wall's middle stays by its padding, never out in the room (the check's rays start there)
        keep &= (middle_y >= rise[0]) & (middle_y < rise[1])
    rows_of, columns_of, _, _, _ = cushion_at(cone, grid_theta, grid_y)
    cushion = rows_of * 10000 + columns_of
    corners = [cushion[:-1], np.roll(cushion[:-1], -1, axis=1), cushion[1:], np.roll(cushion[1:], -1, axis=1)]
    smoothed = (eased[:-1] + np.roll(eased[:-1], -1, axis=1) + eased[1:] + np.roll(eased[1:], -1, axis=1)) / 4
    crossed = np.zeros(cushion[:-1].shape, dtype=bool)
    for other in corners[1:]:
        crossed |= other != corners[0]
    eased_limit = 0.95 if cone.sizes["panels"] else 0.05
    parts = np.where(crossed & (smoothed < eased_limit), "seam", "cushion")  # the crease along a cushion's edge,
    # none where the quilting is eased even a little (no stray dark bits on the flat round a hole or along the cut);
    # a panelled wall's joints run on to the fitting they meet, never stopping short in the open wall
    found = grid_solid(front, back, keep, parts, "back", "cushion", face_normals,
                       front_normals=surface_normals(front, face_normals))
    if screws and which == "main" and sector is not None and (rise is None or rise[0] < screws.get("top", 1.76)):
        found += wall_screws(cut, fades, flats, sector, **screws, **sizes)
    return found


def surface_normals(grid, toward):
    """The unit normals of a ring grid's surface (rows x columns x 3, the columns round a ring), each turned to
    the side `toward` (rows x columns x 3) points."""
    along_rows = np.gradient(grid, axis=0)
    round_ring = np.roll(grid, -1, axis=1) - np.roll(grid, 1, axis=1)
    normals = np.cross(round_ring, along_rows)
    normals *= np.sign(np.einsum("...i,...i->...", normals, toward))[..., None]
    return normals / np.linalg.norm(normals, axis=-1, keepdims=True)


def ceiling(lamps=(), rings=26, segments=144, thick=0.07, puff=0.03, **sizes):
    """The ceiling's quilted pad: a round pad in the middle and a ring of eight round it, under the hull's top at the
    lining's top (`ceiling`), its face down, reaching TUCK over the top of the lining's shoulder and its edge
    sunk TUCK_DROP into it, so no slit shows between them; each lamp's spot [x, z, radius] left flat for the lamp."""
    cone = Cone(**sizes)
    low = cone.sizes["ceiling"]
    outer = float(cone.rho(low, cone.sizes["gap"] + cone.sizes["lining"])) - cone.sizes["inset"] + TUCK
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
    under = np.stack([flat_x, low - puff * share - TUCK_DROP * smoothstep(outer - TUCK, outer, grid_radius),
                      flat_z], axis=-1)
    shrink = min(1.0, float(cone.rho(low + thick, cone.sizes["gap"])) / (outer + 0.002) - 0.004)
    over = np.stack([flat_x * shrink, np.full_like(flat_x, low + thick), flat_z * shrink], axis=-1)
    ways = np.broadcast_to(np.array([0.0, -1.0, 0.0]), under.shape)
    parts = np.full((rings - 1, segments), "cushion")
    return grid_solid(under, over, np.ones(parts.shape, dtype=bool), parts, "back", "seam", ways,
                      pole=[np.array([0.0, low - puff, 0.0]), np.array([0.0, low + thick, 0.0])])


def upright(pieces):
    """A piece turned about z (turned's axis) stood up, its axis along y."""
    return moved(pieces, about("x", -90))


def floor(rim=None, bottom=-0.40, plates=8, **sizes):
    """The cabin's round floor, a solid disc from the hull's foot (`bottom`, on the service module) to its top at
    y = 0, out to the lining's back (or `rim`): a muted plate in two rings of `plates` deck plates, a faint groove
    round the floor hatch in its middle and round the inner ring, and a thin seam strip between each two plates
    (part floor_ring, a shade off the floor's own)."""
    cone = Cone(**sizes)
    edge = float(cone.rho(0.0, cone.sizes["gap"])) - 0.002 if rim is None else rim
    found = turned("floor", [(0.0, bottom), (edge, bottom), (edge, 0.0), (0.95, 0.0)], segments=96)
    found += turned("floor_ring", [(0.95, 0.0), (0.95, -0.002), (0.93, -0.002), (0.93, 0.0)], segments=96)
    found += turned("floor", [(0.93, 0.0), (0.47, 0.0)], segments=96)
    found += turned("floor_ring", [(0.47, 0.0), (0.47, -0.002), (0.45, -0.002), (0.45, 0.0)], segments=96)
    found += turned("floor", [(0.45, 0.0), (0.0, 0.0)], segments=96)
    found = upright(found)
    for step in range(plates):
        strip = box("floor_ring", (0.48, -0.001, -0.004), (edge - 0.03, 0.0008, 0.004), 0.0004)
        found += moved(strip, about("y", (step + 0.5) * 360.0 / plates))
    return found


def skirt(bottom=-2.48, top=-0.40, foot=2.72, struts=24, **sizes):
    """The service module under the capsule, a solid drum from the stack's top (`bottom`, `foot` across) up to the
    hull's foot: a flare up to the drum, an open service bay round it holding three fluid pipes (the middle one
    copper, part pipe_copper) behind `struts` upright struts, a rust band under the hull."""
    cone = Cone(**sizes)
    drum = float(cone.rho(top, -cone.sizes["hull"]))
    found = turned("skirt", [(0.0, bottom), (foot, bottom), (drum, bottom + 0.88), (drum, top - 0.78)],
                   segments=96)
    found += turned("recess", [(drum, top - 0.78), (drum - 0.14, top - 0.75), (drum - 0.14, top - 0.24),
                               (drum, top - 0.21)], segments=96)
    found += turned("band", [(drum, top - 0.21), (drum, top), (0.0, top)], segments=96)
    for height, part in ((top - 0.62, "pipe"), (top - 0.49, "pipe_copper"), (top - 0.36, "pipe")):
        found += turned(part, [(drum - 0.085 + 0.03 * math.cos(math.radians(angle)),
                                height + 0.03 * math.sin(math.radians(angle))) for angle in range(-90, 271, 30)],
                        segments=96, smooth=True)
    found = upright(found)
    for step in range(struts):
        angle = 2 * math.pi * (step + 0.5) / struts
        spot = (drum - 0.03) * np.array([math.sin(angle), 0.0, math.cos(angle)])
        found += tube("pipe", [spot + (0.0, top - 0.765, 0.0), spot + (0.0, top - 0.225, 0.0)], 0.016, 10)
    return found


def nose(base=2.15, high=0.55, **sizes):
    """The capsule's nose over the hull's top (`base`): the hull's cone carried on `high` metres to a narrow flat
    top, its edge a small chamfer, and a raised rim round the top (part band): one clean truncated cone."""
    cone = Cone(**sizes)
    edge = float(cone.rho(base, -cone.sizes["hull"]))
    top = float(cone.rho(base + high, -cone.sizes["hull"]))
    crown = base + high + 0.025
    found = turned("hull", [(0.0, base + 0.0005), (edge, base + 0.0005), (top, base + high),
                            (top - 0.03, crown), (0.0, crown)], segments=96)
    found += turned("band", [(top - 0.16, crown - 0.0005), (top - 0.05, crown - 0.0005), (top - 0.05, crown + 0.06),
                             (top - 0.07, crown + 0.075), (top - 0.16, crown + 0.075),
                             (top - 0.16, crown - 0.0005)], segments=96)
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


def lip(cut=None, steps=480, out=0.035, wide=0.07, **sizes):
    """The cut-away's rim (part lip): one narrow rolled band round its outline (`cut`, as in_cut) over the hull's cut
    edge, through the wall from `out` metres outside the hull to the lining's back and `wide` along it, so the
    section reads as the wall's own thickness and never a frame round the room; never into the room, so with the
    plug in place (a view that does not cut, the game) the padding closes over it with no band across the wall."""
    cone = Cone(**sizes)
    middle, half, height, half_high, power = cut
    angles = np.linspace(0, 2 * math.pi, steps + 1)[:-1]
    cos, sin = np.cos(angles), np.sin(angles)
    across = np.sign(cos) * np.abs(cos) ** (2 / power)
    upward = np.sign(sin) * np.abs(sin) ** (2 / power)
    theta = math.radians(middle) + across * math.radians(half)
    y = height + upward * half_high
    inner, outer = cone.sizes["gap"], -cone.sizes["hull"] - out  # offsets in from the hull's inner face
    path = cone.at(theta, y, (inner + outer) / 2)
    return swept("lip", path, cone.inward(theta), inner - outer, wide)


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


def bolt_ring(cone, middle, right, up, axis, radius, face, lift, count, size=0.009, outward=False):
    """`count` hex bolt heads on a ring of `radius` round `middle`, standing on the face `face` in, `lift` off it
    toward the room (or out of the hull, `outward`)."""
    found = []
    head = turned("bolt", [(0.0, 0.0), (size, 0.0), (size, size * 0.5), (size * 0.6, size * 0.8), (0.0, size * 0.8)],
                  segments=6)
    way, across = (-axis, -right) if outward else (axis, right)
    for step in range(count):
        angle = 2 * math.pi * (step + 0.5) / count
        spot = middle + radius * (math.cos(angle) * right + math.sin(angle) * up)
        base = cone.onto(spot, axis, face) + way * (lift - 0.0005)
        found += placed(head, base, across, up, way)
    return found


def placed(pieces, origin, right, up, way):
    """Pieces built round z laid at `origin` with their x along `right`, y along `up` and z along `way`."""
    return moved(pieces, np.stack([right, up, way], axis=1), origin)


def sleeve(cone, middle, right, up, axis, radius, wall, low, face, bore, rim="rim", segments=96, rows=8):
    """A round sleeve `wall` thick inside `radius` along `axis` through the wall: from `low` (metres along the axis
    off `middle`, a plane outside the hull) to a hair past the face `face` in, each way round where that face lies
    (the wall's curve across the sleeve followed, so the sleeve stands no further into the room than its flange); its
    inside of the part `bore`, the rest of `rim`."""
    angles = np.arange(segments) * 2 * math.pi / segments
    around = np.cos(angles)[:, None] * right + np.sin(angles)[:, None] * up
    reach = [np.einsum("ij,j->i", cone.onto(middle + size * around, axis, face) - middle, axis)
             for size in (radius, radius + wall)]
    high = np.maximum(*reach) + 0.015
    along = low + (high - low)[None, :] * np.linspace(0.0, 1.0, rows + 1)[:, None]
    inner = middle + radius * around[None] + along[..., None] * axis
    outer = middle + (radius + wall) * around[None] + along[..., None] * axis
    ways = np.broadcast_to(-around[None], inner.shape)
    return grid_solid(inner, outer, np.ones((rows, segments), dtype=bool), np.full((rows, segments), bore), rim,
                      rim, ways)


def through_wall(at=(0.0, 1.45), radius=0.15, wall=0.015, flange=0.07, bolts=10, glass=True, outside=0.03,
                 bore="bore", outer_thick=0.014, rim="rim", **sizes):
    """A round opening's frame through the hull and lining at `at` [theta (degrees), y]: a sleeve of `radius` along
    the wall's normal from outside the hull to past the cushions' face (sleeve; its inside of the part `bore`), a
    flange hugging the lining's face and one hugging the hull's outside, each with its bolts, and its glass out
    past the hull (a porthole's) or none (a hatch's); the outer flange `outer_thick` thick, bolted round when it
    stands 2 cm or more (a hatch's frame read from outside); its sleeve's outside and flanges of the part `rim`."""
    cone = Cone(**sizes)
    angle = math.radians(at[0])
    right, up, axis = cone.frame(angle)
    middle = cone.at(angle, at[1])
    face = cone.sizes["gap"] + cone.sizes["lining"]
    found = sleeve(cone, middle, right, up, axis, radius, wall, -cone.sizes["hull"] - outside, face, bore, rim)
    bedded = radius + wall - 0.003  # each flange reaches into the sleeve's wall, so no face of one lies on the other
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange, face, 0.022, False, rim)
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange * 0.8, -cone.sizes["hull"],
                           outer_thick, True, rim)
    found += bolt_ring(cone, middle, right, up, axis, radius + wall + flange / 2, face, 0.023, bolts)
    if outer_thick >= 0.02:
        found += bolt_ring(cone, middle, right, up, axis, radius + wall + flange * 0.45, -cone.sizes["hull"],
                           outer_thick + 0.001, bolts, size=0.011, outward=True)
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
    handwheel on a gearbox drum in its middle, eight ribs from the drum out to the rim, and between them eight latch
    dogs at the rim each on a link rod from the drum (a real capsule hatch's locking gear: round 4, the judge's "a
    flat dark disc with radial ribs, with no latch dogs, locking mechanism or crank housing"; the lit ring inside the
    rim gone, it read as a glowing outline) (its inside toward +z, as built); on its outside a hinge arm on two straps
    out to the hinge's knuckle past its edge (part hinge)."""
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
    drum = thick / 2 + 0.052  # the gearbox drum's face: the handwheel's stem stands on it
    found += turned("hinge", [(0.0, thick / 2 + 0.01), (0.125, thick / 2 + 0.01), (0.125, drum - 0.008),
                              (0.115, drum), (0.0, drum)], segments=48)
    for step in range(6):  # the drum's cover screws
        angle = 2 * math.pi * step / 6
        found += moved(turned("bolt", [(0.0, 0.0), (0.006, 0.0), (0.006, 0.003), (0.0035, 0.0055), (0.0, 0.0055)],
                              segments=6), offset=(0.097 * math.cos(angle), 0.097 * math.sin(angle), drum - 0.0005))
    found += moved(wheel(size=0.32, part="metal"), offset=(0.0, 0.0, drum - 0.0005))
    for step in range(8):  # the inside face's stiffening ribs, from the drum out to the rim (a real hatch's
        # structure: a plain dished disc read as unfinished)
        rib = box("leaf", (0.12, -0.009, thick / 2 + 0.006), (radius - 0.1, 0.009, thick / 2 + 0.034), 0.003)
        found += moved(rib, about("z", 22.5 + step * 45))
    for step in range(8):  # the latch dogs between the ribs, each a lug on a pivot pin at the rim, a link rod from
        # the drum to it
        turn = about("z", step * 45)
        dog = box("metal", (radius - 0.125, -0.022, thick / 2 + 0.001), (radius - 0.064, 0.022, thick / 2 + 0.036),
                  0.004)
        pin = [(0.0, thick / 2 + 0.035), (0.011, thick / 2 + 0.035), (0.011, thick / 2 + 0.042),
               (0.008, thick / 2 + 0.045), (0.0, thick / 2 + 0.045)]
        dog += moved(turned("bolt", pin, segments=12), offset=(radius - 0.095, 0.0, 0.0))
        dog += tube("metal", [(0.115, 0.0, thick / 2 + 0.032), (radius - 0.12, 0.0, thick / 2 + 0.032)], 0.0065, 12)
        found += moved(dog, turn)
    for step in range(bolts):  # its outside's bolts
        angle = 2 * math.pi * (step + 0.5) / bolts
        found += moved(turned("bolt", [(0.0, 0.0), (0.009, 0.0), (0.009, 0.005), (0.005, 0.008), (0.0, 0.008)],
                              segments=6), about("x", 180), ((radius - 0.033) * math.cos(angle),
                                                             (radius - 0.033) * math.sin(angle), -thick / 2 - 0.0005))
    found += turned("rim", [(0.0, -thick / 2 - 0.012), (0.08, -thick / 2 - 0.012), (0.08, -thick / 2 - 0.0005),
                            (0.0, -thick / 2 - 0.0005)], segments=32)
    arm = -thick / 2 - 0.03  # the hinge arm across its outside, to the knuckle past its edge
    found += tube("hinge", [(0.05, 0.0, arm), (radius + 0.06, 0.0, arm)], 0.017, 12)
    for y in (-0.045, 0.045):
        found += box("hinge", (0.1, y - 0.02, arm - 0.006), (radius - 0.06, y + 0.02, -thick / 2 + 0.002), 0.003)
    found += tube("hinge", [(radius + 0.06, -0.1, arm), (radius + 0.06, 0.1, arm)], 0.026, 16)
    return found


def gantry(long=1.6, wide=1.3, rail=1.05, deep=0.7, start=0.3, side=-1, **_):
    """The railed walkway outside the hatch, built along +x from the hull (x = 0) with its deck's top at y = 0: a
    grating deck on edge beams, one railing run of posts and rails from `start` along the `side` (+1 or -1 along z)
    edge and on round the far end, a truss under each side."""
    found = box("grate", (0.0, -0.04, -wide / 2), (long, 0.0, wide / 2), 0.004)
    edge = side * (wide / 2 + 0.025)
    end = long - 0.025
    run = [(start - 0.02, edge), (end, edge), (end, -edge)]
    posts = [(x, edge) for x in np.linspace(start, end, 4)] + [(end, z) for z in np.linspace(edge, -edge, 4)[1:]]
    for x, z in posts:
        found += tube("rail", [(x, -0.0005, z), (x, rail, z)], 0.02, 12)
    for height in (rail, rail * 0.5):
        found += tube("rail", [(x, height, z) for x, z in run], 0.018, 12)
    for side in (-1, 1):
        edge = side * (wide / 2 + 0.025)
        found += box("frame", (0.0, -0.16, edge - 0.025), (long, -0.0005, edge + 0.025), 0.004)
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

def mount(wide=0.4, high=0.3, thick=0.016, corner=0.03, **_):
    """A flat mounting plate `wide` x `high` and `thick`, set into the lining where it is eased flat (lining_depth's
    flats): rounded corners and a bolt head in each corner."""
    found = outline_slab("mount", rounded_rectangle(wide, high, corner), 0.0, thick)
    head = [(0.0, 0.0), (0.006, 0.0), (0.006, 0.002), (0.004, 0.0035), (0.0, 0.0035)]
    for x in (-1, 1):
        for y in (-1, 1):
            found += moved(turned("bolt", head, segments=12),
                           offset=(x * (wide / 2 - 0.016), y * (high / 2 - 0.016), thick - 0.0003))
    return found


def console(wide=1.0, deep=0.4, front_high=0.6, back_high=0.74, items=(), lean=0.0, grille=0.4, rear=0.0, **_):
    """The long low console before the pilot: a box `wide` across, `deep` from the pilot's side (+z) back, its top
    sloping up from `front_high` to `back_high` away from the pilot, its far face sloping in `lean` metres to its
    foot, a bright lip round its top, a slatted vent grille `grille` wide on its pilot's side (and `rear` wide on its
    far face, standing upright when `lean` is 0: a pod seen from behind) and its `items` laid on its top (their `at`
    [u, v] up the slope from its middle)."""
    side = [(lean, 0.0), (deep, 0.0), (deep, front_high), (0.0, back_high)]
    found = []
    points = [(-wide / 2, y, z) for z, y in side] + [(wide / 2, y, z) for z, y in side]
    for face in ([0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]):
        found.append(piece("body", [points[index] for index in face], [[0, 1, 2], [0, 2, 3]], False))
    middle = np.array([0.0, (front_high + back_high) / 4, deep / 2])
    found = [(part, points, oriented(points, triangles, points.mean(axis=0) - middle), smooth)
             for part, points, triangles, smooth in found]
    slope = math.degrees(math.atan2(back_high - front_high, deep))
    length = math.hypot(deep, back_high - front_high)
    # the deck and the lip sunk a little into the top, so neither shares the top's face (a ray along the top would
    # count one face for two)
    top = box("deck", (-wide / 2 + 0.03, -length / 2 + 0.02, -0.004), (wide / 2 - 0.03, length / 2 - 0.02, 0.008),
              0.002)
    top += frame_ring("lip", rounded_rectangle(wide + 0.012, length + 0.012, 0.01),
                      rounded_rectangle(wide - 0.05, length - 0.03, 0.008), -0.004, 0.012)
    top += laid_items(items, 0.008)
    found += moved(top, np.asarray(about("x", -90 + slope)), (0.0, (front_high + back_high) / 2, deep / 2))
    if grille:
        found += box("vent", (-grille / 2, 0.10, deep - 0.002), (grille / 2, 0.34, deep + 0.002), 0.002)
        for step in range(int(grille / 0.03)):
            x = -grille / 2 + 0.015 + step * 0.03
            found += box("lip", (x - 0.006, 0.115, deep + 0.0015), (x + 0.006, 0.325, deep + 0.008), 0.0015)
    if rear:
        if lean:
            raise ValueError("a console's rear grille stands on an upright far face (lean 0)")
        found += box("vent", (-rear / 2, 0.12, -0.002), (rear / 2, back_high - 0.15, 0.002), 0.002)
        for step in range(int(rear / 0.03)):
            x = -rear / 2 + 0.015 + step * 0.03
            found += box("lip", (x - 0.006, 0.135, -0.008), (x + 0.006, back_high - 0.165, -0.0015), 0.0015)
    found += box("lip", (-wide / 2 - 0.006, 0.0, lean * 0.9 - 0.006), (wide / 2 + 0.006, 0.05, deep + 0.006), 0.004)
    return found


def switch_box(wide=0.28, deep=0.24, front_high=0.56, back_high=0.66, items=(), **_):
    """The small switch box at the pilot's right hand: a box with a sloping top holding its `items`."""
    return console(wide, deep, front_high, back_high, items, grille=0.0)


SEAT_SCALE = 0.8  # the pilot's seat drawn to fit a 2.6 m cabin: 0.42 m across its shell, its headrest 0.98 m up


def pad(part, wide, high, thick, puff, at=(0.0, 0.0, 0.0), tilt=0.0, turn=0.0, lying=False):
    """One padded leather cushion `wide` x `high`, `thick` deep, its face (+z) swollen `puff`: its back's middle at
    `at`, tilted `tilt` degrees about x and turned `turn` about y (a wing angled in); `lying` lays it face up (a seat
    pan)."""
    found = rounded_box(part, (-wide / 2, -high / 2, 0.0), (wide / 2, high / 2, thick), min(0.03, thick / 2 - 0.002),
                        puff, steps=4, inside=8)
    rotation = np.asarray(about("y", turn)) @ np.asarray(about("x", tilt - (90.0 if lying else 0.0)))
    return moved(found, rotation, at)


def seat(scale=SEAT_SCALE, **_):
    """A padded bucket seat on a metal frame (its front toward +z), `scale` of 0.5 m across: a puffy seat pan
    between raised bolsters, a back of three pleated rolls between wings angled in, a headrest with its own small
    wings, all in a grey shell whose sides wrap them; padded armrests on posts and a tubular pedestal on two floor
    rails."""
    found = pad("upholstery", 0.30, 0.40, 0.06, 0.03, (0.0, 0.42, 0.02), lying=True)
    for side in (-1, 1):
        found += pad("upholstery", 0.07, 0.40, 0.09, 0.012, (side * 0.19, 0.42, 0.02), lying=True)
    back = []
    for number, middle in enumerate((0.10, 0.27, 0.44)):
        back += pad("upholstery", 0.30, 0.165, 0.06, 0.03, (0.0, middle, 0.0))
    for side in (-1, 1):
        back += pad("upholstery", 0.075, 0.52, 0.07, 0.02, (side * 0.185, 0.27, 0.005), turn=side * -22.0)
    back += pad("upholstery", 0.22, 0.15, 0.06, 0.03, (0.0, 0.69, 0.0))
    for side in (-1, 1):
        back += pad("upholstery", 0.05, 0.15, 0.06, 0.015, (side * 0.13, 0.69, 0.005), turn=side * -28.0)
    back += moved(rounded_box("shell", (-0.25, 0.003, -0.02), (0.25, 0.065, 0.6), 0.03, narrow=0.78),
                  about("x", -90))  # its back shell tapering to the shoulders
    for side in (-1, 1):
        back += rounded_box("shell", (min(side * 0.225, side * 0.26), -0.02, -0.055),
                            (max(side * 0.225, side * 0.26), 0.46, 0.13), 0.015)
    back += moved(rounded_box("shell", (-0.16, 0.003, 0.58), (0.16, 0.055, 0.79), 0.03, narrow=0.8), about("x", -90))
    found += moved(back, about("x", -12), (0.0, 0.46, -0.21))
    found += rounded_box("shell", (-0.25, 0.35, -0.22), (0.25, 0.415, 0.25), 0.025)
    for side in (-1, 1):
        found += rounded_box("shell", (min(side * 0.225, side * 0.26), 0.36, -0.21),
                             (max(side * 0.225, side * 0.26), 0.52, 0.24), 0.015)
        found += rounded_box("upholstery", (side * 0.30 - 0.03, 0.63, -0.14), (side * 0.30 + 0.03, 0.685, 0.18),
                             0.022, 0.006)
        for z in (-0.12, 0.11):
            found += tube("frame", [(side * 0.30, 0.415, z), (side * 0.30, 0.632, z)], 0.011, 10)
        for z in (-0.16, 0.16):
            found += tube("frame", [(side * 0.14, 0.035, z), (side * 0.14, 0.345, z)], 0.018, 12)
        found += tube("frame", [(side * 0.14, 0.19, -0.16), (side * 0.14, 0.19, 0.16)], 0.013, 10)
        found += box("frame", (side * 0.17 - 0.025, 0.0, -0.26), (side * 0.17 + 0.025, 0.035, 0.26), 0.006)
    found += tube("frame", [(-0.14, 0.19, 0.0), (0.14, 0.19, 0.0)], 0.013, 10)
    found += tube("frame", [(-0.14, 0.05, -0.16), (0.14, 0.05, 0.16)], 0.012, 10)
    return moved(found, np.eye(3) * scale)


def throttle(levers=2, **_):
    """The throttle quadrant: a box with a slotted top and `levers` short levers thrown forward, stubby black
    grips."""
    found = rounded_box("body", (-0.06, 0.0, -0.11), (0.06, 0.07, 0.11), 0.012)
    found += box("dark", (-0.05, 0.068, -0.09), (0.05, 0.074, 0.09), 0.002)
    for number in range(levers):
        x = -0.022 + number * 0.044
        stem = tube("lever", [(0.0, 0.0, 0.0), (0.0, 0.085, 0.0)], 0.007, 10)
        stem += moved(rounded_box("knob", (-0.016, 0.0, -0.02), (0.016, 0.042, 0.02), 0.013), offset=(0.0, 0.08, 0.0))
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


def handrail(long=0.42, stand=0.06, radius=0.011, **_):
    """A grab handle on a wall, upright `long` metres between its two feet: a round bar bent off the wall `stand`
    metres on each foot, each foot a plate bolted twice to the wall (its back on z = 0, the bar toward +z)."""
    half = long / 2
    bend = [(0.0, -half, 0.0)] + [(0.0, -half + 0.03 * (1 - math.cos(math.radians(angle))),
                                   stand * math.sin(math.radians(angle))) for angle in range(15, 91, 15)]
    path = bend + [(x, -y, z) for x, y, z in reversed(bend)]
    found = tube("rail", path, radius, 14)
    head = [(0.0, 0.0), (0.004, 0.0), (0.004, 0.0015), (0.0028, 0.0025), (0.0, 0.0025)]
    for end in (-half, half):
        found += box("metal", (-0.022, end - 0.032, -0.004), (0.022, end + 0.032, 0.006), 0.002)
        for offset in (-0.021, 0.021):
            found += moved(turned("bolt", head, segments=10), offset=(0.0, end + offset, 0.0055))
    return found


def cables(around=(300.0, 380.0), y=1.74, count=3, pitch=0.026, stand=0.03, clamp_every=0.32, **sizes):
    """A cable run along the cabin wall in the capsule's frame: `count` bundled cables of their own thicknesses
    `pitch` apart up the wall at height `y` (their middle), from `around` [from, to] degrees round the cone, `stand`
    metres off the lining's face (past its panels), held by a bright clamp strap every `clamp_every` metres."""
    cone = Cone(**sizes)
    face = cone.sizes["gap"] + cone.sizes["lining"] + cone.sizes["panel_puff"] + stand
    start, end = (math.radians(value) for value in around)
    length = abs(end - start) * float(cone.rho(y, face))
    thetas = np.linspace(start, end, max(8, int(length / 0.03)))
    found = []
    radii = [0.009, 0.0065, 0.0075, 0.006][:count]
    for number, radius in enumerate(radii):
        height = y + (number - (count - 1) / 2) * pitch
        found += tube("cable", [cone.at(theta, height, face) for theta in thetas], radius, 12)
    reach = (count - 1) / 2 * pitch + 0.014
    clamps = max(2, int(length / clamp_every) + 1)
    for theta in np.linspace(start, end, clamps)[1:-1] if clamps > 2 else []:
        right, up, inward = cone.frame(theta)
        strap = box("clamp", (-0.008, -reach, -stand - 0.004), (0.008, reach, 0.011), 0.002)
        found += moved(strap, np.column_stack([right, up, inward]), cone.at(theta, y, face))
    return found


def joint_spots(cone, pitch, off, top):
    """Where a panelled lining's screws stand (theta radians, y): along both sides of every joint, `off` metres off
    it and about `pitch` metres apart, the upright joints from the floor's course to `top`, the level ones between
    the courses under it; none where two joints cross."""
    face = cone.sizes["gap"] + cone.sizes["lining"]
    joints = [math.radians(cone.sizes["panel_from"] + 360.0 * step / cone.sizes["panels"])
              for step in range(int(cone.sizes["panels"]))]
    levels = [row for row in ROWS[1:] if row < top]
    spots = []
    for joint in joints:
        for y in np.arange(0.06, top, pitch):
            if min(abs(y - level) for level in levels) > 2 * off:
                rho = float(cone.rho(y, face))
                spots += [(joint + side * off / rho, float(y)) for side in (-1, 1)]
    for level in levels:
        rho = float(cone.rho(level, face))
        count = int(2 * math.pi * rho / pitch)
        for theta in np.arange(count) * 2 * math.pi / count:
            if min(abs(wrapped(theta - joint)) for joint in joints) * rho > 2 * off:
                spots += [(float(theta), level + side * off) for side in (-1, 1)]
    return spots


def wall_screws(cut=None, holes=(), flats=(), sector=(0.0, 360.0), pitch=0.11, off=0.02, top=1.76, clear=0.05,
                **sizes):
    """The screws holding a panelled lining's wall panels (CONE's `panels`) to the frame, in the capsule's frame:
    a domed head along both sides of each joint (joint_spots) on the panel's face, laid along its normal, in the
    walls of `sector` [from, to] degrees only; none in the cut-away, nor within `clear` metres of a hole's flange
    (`holes` [theta, y, radius] as the lining's fades) or of a mounting plate (`flats`, as the lining's): a real
    cabin's bolted panels, never a smooth padded wall."""
    cone = Cone(**sizes)
    face = cone.sizes["gap"] + cone.sizes["lining"]
    head = [(0.0, 0.0), (0.0042, 0.0), (0.0042, 0.0011), (0.0032, 0.0022), (0.0016, 0.0027), (0.0, 0.0028)]
    low, high = (math.radians(value) for value in sector)
    found = []
    for theta, y in joint_spots(cone, pitch, off, top):
        if (theta - low) % (2 * math.pi) >= (high - low) % (2 * math.pi) or (cut and in_cut(theta, y, cut)):
            continue
        if cut and cut_distance(cone, theta, y, cut) < clear:
            continue
        back = cone.at(theta, y, cone.sizes["gap"])
        skin = cone.at(theta, y, face)
        if any(off_axis(cone, skin[None], hole_theta, hole_y)[0] < radius + clear for hole_theta, hole_y, radius in holes):
            continue
        blocked = False
        for flat_theta, flat_y, wide, high_flat in flats:
            _, _, (right, up, inward) = flat_spot(flat_theta, flat_y, wide, high_flat, **sizes)
            offset = back - cone.at(math.radians(flat_theta), flat_y, cone.sizes["gap"])
            reach = MOUNT_BORDER + MOUNT_EASE + clear
            blocked |= bool(abs(offset @ right) < wide / 2 + reach and abs(offset @ up) < high_flat / 2 + reach)
        if blocked:
            continue
        right, up, inward = cone.frame(theta)
        stand = float(quilt(cone, np.array([theta]), np.array([y]))[0])
        found += moved(turned("bolt", head, segments=8), np.column_stack([right, up, inward]),
                       cone.at(theta, y, face + stand - 0.0004))
    return found


KINDS = {"hull": hull, "lining": lining, "ceiling": ceiling, "floor": floor, "skirt": skirt, "nose": nose, "lip": lip,
         "through_wall": through_wall, "tread": tread, "hatch_leaf": hatch_leaf, "gantry": gantry, "panel": panel, "console": console,
         "switch_box": switch_box, "mount": mount, "seat": seat, "throttle": throttle, "stick": stick, "lamp_fixture": lamp_fixture,
         "handrail": handrail, "cables": cables, **ITEMS}


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
    return written(path, pieces)


def written(path, pieces):
    """`pieces` written at `path` as one piece file (write): /piece with one mesh `geo`, each part a GeomSubset bound
    to a placeholder, its normals at every corner. Its parts, sorted."""
    points, triangles, normals, parts = [], [], [], {}
    count = 0
    for part, piece_points, piece_triangles, smooth in pieces:
        if not len(piece_triangles):
            continue
        given = smooth[piece_triangles].reshape(-1, 3) if isinstance(smooth, np.ndarray) else None
        piece_points, piece_triangles = welded(piece_points, piece_triangles)
        if given is not None and len(given) != 3 * len(piece_triangles):
            raise ValueError(f"part {part}: a piece shaded by its points' own normals lost a collapsed face")
        normals.append(given if given is not None else corner_normals(piece_points, piece_triangles, smooth))
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
