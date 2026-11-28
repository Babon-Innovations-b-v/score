"""A shop's lightbox sign built in code (2099 #161, the street's tea restaurant 未来茶餐厅: TRELLIS.2 draws no
characters, and its sign read "未来余食厅" in a dull texture that never lit): a dark metal casing, a glowing face inset
in it, and the words standing proud of the face as raised letters, each set in the library's face
(text_decals.FONTS, SIL OFL) and cut into runs of a raster's rows, so they read sharp from the street with no picture.
Every part is a palette variant of its library recipe (car.painted), the face and letters glowing.

    mark_ink(mark)                  an attitude marker's symbol (MARKS) as a ROWS-square ink raster
    sign_parts(text, size, look, vertical, relief, mark)  the parts of a sign of `size` (across, tall, deep; y up, its face towards
                                    +z, its foot on y 0, centred across and in depth): casing, face, letters; a
                                    vertical sign's characters stacked top to bottom, as a Hong Kong blade sign's
    build(text, size, palette, look, finishes, vertical, relief)  (trimesh.Scene, record): the parts painted from the palette,
                                    FINISHES unless `finishes` names others (a neon blade: a dark face, glowing letters)
"""
import numpy as np

from score.stages.props.moving_parts import car

BORDER = 0.06  # metres of casing round the face
FACE_PROUD = 0.006  # metres the face stands out of the casing's front
LETTER_PROUD = 0.018  # metres the letters stand out of the face
TEXT_TALL = 0.68  # share of the face's height the words' ink fills (at most; a long line is held to the face's width)
TEXT_WIDE = 0.92  # share of the face's width the words may fill
ROWS = 96  # raster rows a line of words is cut into: a row is a run's height
# The share of its glowing colour the face gives off: a lightbox's tubes shine through a diffusing face, dimmer than
# a bare lamp, so its red words stand out of it. At a whole glow the street's face (sign-cream) drew white at the
# night's exposure and its words read pink in its bloom (2099 #161, round 3).
FACE_GLOW = 0.3
# The share of its colour a glowing face reflects: a diffuser is lit from behind, so the street's lamps over it must not
# light it as a cream wall (at its whole colour the sign under its 18.8 W lamp drew a white slab, round 3).
FACE_BASE = 0.35
# The share of their colour a lightbox's letters give off: red film over the tubes, deeper than the face, so the words
# read red, not salmon in the face's bloom (round 3). A neon sign's letters (a glowing finish over a face that does not
# glow) give off their whole colour.
LETTER_GLOW = 0.45
GAP = 0.12  # share of a character's height between a vertical sign's characters
FINISHES = {"casing": ("painted_metal", "gunmetal_steel"), "face": ("glowing", "sign_lightbox_cream"),
            "letters": ("glowing", "sign_lettering_red")}
# A street lamp's square head is a lightbox with no words on a pole (2099 #161 round 5: the concept's HK lamp; a
# Victorian lantern stood there). Its head gives off LAMP_GLOW of its colour, so it reads lit, not a white bloom blob.
LAMP_FINISHES = {"pole": ("painted_metal", "gunmetal_steel"), "cap": ("painted_metal", "gunmetal_steel"),
                 "head": ("glowing", "lamp_head_glow")}
LAMP_GLOW = 0.35
POLE_WIDE = 0.12  # metres across the pole's square section
# An attitude marker's symbol, set left of a label's words (2099 #257, the SAS grid's buttons): KSP's navball marks as
# the game's ball draws them (2099 game/cockpit/instruments/BallMarks.Drawn), each a list of strokes in a unit square
# (x right, y up, -0.55 to 0.55), plus a circle's (middle, radius) where a mark has one. A label of a mode the ball
# shows no mark for takes the nearest sign: STABILITY the fixed nose's wings, OFF a power sign, the speed box's
# ORBIT / SURFACE an orbit round a world.
_LEAN = 0.5 ** 0.5
_CORNERS = [(_LEAN, _LEAN), (-_LEAN, _LEAN), (_LEAN, -_LEAN), (-_LEAN, -_LEAN)]
_FINS = [(np.cos(np.radians(angle)), np.sin(np.radians(angle))) for angle in (90.0, 210.0, 330.0)]
MARKS = {
    "prograde": {"circles": [(0.0, 0.0, 0.3)], "strokes": [((0.0, 0.3), (0.0, 0.55)), ((-0.3, 0.0), (-0.55, 0.0)),
                                                         ((0.3, 0.0), (0.55, 0.0))]},
    "retrograde": {"circles": [(0.0, 0.0, 0.3)], "strokes": [((-0.21, -0.21), (0.21, 0.21)), ((-0.21, 0.21), (0.21, -0.21)),
                                                           ((0.0, 0.3), (0.0, 0.55)), ((-0.3, 0.0), (-0.55, 0.0)),
                                                           ((0.3, 0.0), (0.55, 0.0))]},
    "normal": {"strokes": [((0.0, 0.38), (-0.36, -0.24)), ((-0.36, -0.24), (0.36, -0.24)), ((0.36, -0.24), (0.0, 0.38))]},
    "anti_normal": {"strokes": [((0.0, -0.38), (-0.36, 0.24)), ((-0.36, 0.24), (0.36, 0.24)), ((0.36, 0.24), (0.0, -0.38)),
                                ((0.0, -0.05), (0.0, 0.05))]},
    "radial_in": {"circles": [(0.0, 0.0, 0.3)], "strokes": [((x * 0.05, y * 0.05), (x * 0.24, y * 0.24)) for x, y in _CORNERS]},
    "radial_out": {"circles": [(0.0, 0.0, 0.25)], "strokes": [((x * 0.25, y * 0.25), (x * 0.5, y * 0.5)) for x, y in _CORNERS]},
    "burn": {"circles": [(0.0, 0.0, 0.28)],
             "strokes": [stroke for x, y in _FINS for side in (1.0, -1.0) for stroke in
                         [((x * 0.28 - y * 0.12 * side, y * 0.28 + x * 0.12 * side), (x * 0.5, y * 0.5))]]},
    "stability": {"circles": [(0.0, 0.0, 0.06)], "strokes": [((-0.5, 0.0), (-0.18, 0.0)), ((-0.18, 0.0), (0.0, -0.18)),
                                                           ((0.0, -0.18), (0.18, 0.0)), ((0.18, 0.0), (0.5, 0.0))]},
    "off": {"arcs": [(0.0, -0.04, 0.36, 130.0, 410.0)], "strokes": [((0.0, 0.5), (0.0, 0.05))]},
    "frame": {"ellipses": [(0.0, 0.0, 0.52, 0.24)], "circles": [(0.0, 0.0, 0.12)]},
}
MARK_STROKE = 0.08  # a mark's line width, of its square


def ink(text, look, vertical=False):
    """The words' ink as a boolean raster (True where a letter is), cropped to its ink: one line ROWS tall, or for a
    vertical sign each character ROWS tall, centred across, stacked top to bottom GAP of a character apart."""
    from PIL import Image
    from score.stages.surfaces import text_decals
    if not vertical:
        line = text_decals.set_line(text, look)
        wide = max(1, round(line.width * ROWS / line.height))
        return np.asarray(line.resize((wide, ROWS), Image.LANCZOS)) >= 128
    characters = [ink(character, look) for character in text if not character.isspace()]
    wide = max(character.shape[1] for character in characters)
    gap = np.zeros((round(ROWS * GAP), wide), dtype=bool)
    stacked = []
    for number, character in enumerate(characters):
        left = (wide - character.shape[1]) // 2
        stacked += [gap] * bool(number) + [np.pad(character, ((0, 0), (left, wide - character.shape[1] - left)))]
    return np.vstack(stacked)


def mark_ink(mark):
    """An attitude marker's symbol (MARKS[mark]) as a ROWS-square boolean raster, True where its lines are; y up in the
    symbol is up in the raster."""
    from PIL import Image, ImageDraw
    shape = MARKS[mark]
    picture = Image.new("L", (ROWS, ROWS), 0)
    draw = ImageDraw.Draw(picture)
    width = max(1, round(MARK_STROKE * ROWS))

    def at(x, y):
        return ((x + 0.55) / 1.1 * (ROWS - 1), (0.55 - y) / 1.1 * (ROWS - 1))

    def scaled(radius):
        return radius / 1.1 * (ROWS - 1)

    for start, end in shape.get("strokes", []):
        draw.line([at(*start), at(*end)], fill=255, width=width)
    for x, y, radius in shape.get("circles", []):
        (middle_x, middle_y), reach = at(x, y), scaled(radius)
        draw.ellipse([middle_x - reach, middle_y - reach, middle_x + reach, middle_y + reach], outline=255, width=width)
    for x, y, across, tall in shape.get("ellipses", []):
        (middle_x, middle_y) = at(x, y)
        draw.ellipse([middle_x - scaled(across), middle_y - scaled(tall), middle_x + scaled(across),
                      middle_y + scaled(tall)], outline=255, width=width)
    for x, y, radius, start, end in shape.get("arcs", []):
        (middle_x, middle_y), reach = at(x, y), scaled(radius)
        draw.arc([middle_x - reach, middle_y - reach, middle_x + reach, middle_y + reach], start, end, fill=255,
                 width=width)
    return np.asarray(picture) >= 128


def runs(raster):
    """Each row's runs of ink as (row, first column, past the last column), rows counted from the top."""
    found = []
    for row, cells in enumerate(raster):
        edges = np.flatnonzero(np.diff(np.concatenate([[0], cells.astype(np.int8), [0]])))
        found.extend((row, int(first), int(past)) for first, past in zip(edges[0::2], edges[1::2]))
    return found


def box(low, high):
    """An axis-aligned box from `low` to `high`."""
    import trimesh
    low, high = np.asarray(low, float), np.asarray(high, float)
    return trimesh.creation.box(extents=high - low,
                                transform=trimesh.transformations.translation_matrix((low + high) / 2.0))


def sign_parts(text, size, look="bold sans", vertical=False, relief=1.0, mark=None):
    """[(part, mesh)]: the casing, the face inset by BORDER standing FACE_PROUD out of it, and the letters standing
    LETTER_PROUD out of the face, the words centred on it as large as TEXT_TALL and TEXT_WIDE let them; `relief` scales
    the border and both reliefs, so a label plate a few centimetres tall keeps a face (at a whole BORDER it has none);
    `mark` (a MARKS name) sets that symbol a line tall left of the words, a third of a line apart, raised as they are."""
    import trimesh
    across, tall, deep = (float(value) for value in size)
    border, face_proud, letter_proud = BORDER * relief, FACE_PROUD * relief, LETTER_PROUD * relief
    front = deep / 2.0
    casing = box((-across / 2, 0.0, -deep / 2), (across / 2, tall, front))
    face_low, face_high = np.array([-across / 2 + border, border]), np.array([across / 2 - border, tall - border])
    face = box((*face_low, front), (*face_high, front + face_proud))
    raster = ink(text, look, vertical)
    if mark is not None:
        raster = np.hstack([mark_ink(mark), np.zeros((ROWS, ROWS // 3), dtype=bool), raster])
    span = face_high - face_low
    cell = min(span[1] * TEXT_TALL / raster.shape[0], span[0] * TEXT_WIDE / raster.shape[1])
    middle = (face_low + face_high) / 2.0
    left, top = middle[0] - raster.shape[1] * cell / 2.0, middle[1] + raster.shape[0] * cell / 2.0
    face_front = front + face_proud
    letters = trimesh.util.concatenate([
        box((left + first * cell, top - (row + 1) * cell, face_front),
            (left + past * cell, top - row * cell, face_front + letter_proud)) for row, first, past in runs(raster)])
    return [("casing", casing), ("face", face), ("letters", letters)]


def build(text, size, palette, look="bold sans", finishes=None, vertical=False, relief=1.0, mark=None):
    """(trimesh.Scene, record) of the sign: each part a node of its own name in its palette variant (FINISHES, or
    `finishes` {part: (recipe, variant)} over them), the record naming its text, size and parts as car.painted reads
    them, its `relief` and its `mark` (sign_parts). A glowing face gives off FACE_GLOW and reflects FACE_BASE of its colour, its letters then LETTER_GLOW."""
    import trimesh
    chosen = dict(FINISHES, **(finishes or {}))
    scene = trimesh.Scene()
    record = {"rule": "lightbox", "text": text, "look": look, "size": [float(value) for value in size],
              "vertical": bool(vertical), "relief": float(relief), "parts": []}
    if mark is not None:
        record["mark"] = mark
    for name, mesh in sign_parts(text, size, look, vertical, relief, mark):
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        recipe, variant = chosen[name]
        record["parts"].append({"name": name, "finish": recipe, "variant": variant})
    car.painted(scene, record, palette)
    if chosen["face"][0] == "glowing":
        face = scene.geometry["face"].visual.material
        face.emissiveFactor = [value * FACE_GLOW for value in face.emissiveFactor]
        base = np.asarray(face.baseColorFactor, dtype=float)
        face.baseColorFactor = [*(base[:3] * FACE_BASE / 255.0), base[3] / 255.0]
        letters = scene.geometry["letters"].visual.material
        letters.emissiveFactor = [value * LETTER_GLOW for value in letters.emissiveFactor]
        record.update(face_glow=FACE_GLOW, face_base=FACE_BASE, letter_glow=LETTER_GLOW)
    return scene, record


def lamp_parts(tall, head):
    """[(part, mesh)] of a square lamp `tall` metres to its cap: a pole up to the head, the head a cube `head` across,
    and a cap BORDER thick and BORDER wider than the head on top of it."""
    under = tall - head - BORDER
    pole = box((-POLE_WIDE / 2, 0.0, -POLE_WIDE / 2), (POLE_WIDE / 2, under, POLE_WIDE / 2))
    lantern = box((-head / 2, under, -head / 2), (head / 2, under + head, head / 2))
    reach = head / 2 + BORDER / 2
    cap = box((-reach, under + head, -reach), (reach, tall, reach))
    return [("pole", pole), ("head", lantern), ("cap", cap)]


def build_lamp(tall, head, palette):
    """(trimesh.Scene, record) of a square lamp: each part a node of its own name in its LAMP_FINISHES variant, the
    head giving off LAMP_GLOW of its glow and reflecting FACE_BASE of its colour."""
    import trimesh
    scene = trimesh.Scene()
    record = {"rule": "lightbox lamp", "size": [head, float(tall), head], "parts": []}
    for name, mesh in lamp_parts(float(tall), float(head)):
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        recipe, variant = LAMP_FINISHES[name]
        record["parts"].append({"name": name, "finish": recipe, "variant": variant})
    car.painted(scene, record, palette)
    glow = scene.geometry["head"].visual.material
    glow.emissiveFactor = [value * LAMP_GLOW for value in glow.emissiveFactor]
    base = np.asarray(glow.baseColorFactor, dtype=float)
    glow.baseColorFactor = [*(base[:3] * FACE_BASE / 255.0), base[3] / 255.0]
    record.update(head_glow=LAMP_GLOW, head_base=FACE_BASE)
    return scene, record
