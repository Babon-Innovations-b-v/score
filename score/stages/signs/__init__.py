"""A shop's lightbox sign built in code (2099 #161, the street's tea restaurant 未来茶餐厅: TRELLIS.2 draws no
characters, and its sign read "未来余食厅" in a dull texture that never lit): a dark metal casing, a glowing face inset
in it, and the words standing proud of the face as raised letters, each set in the library's face
(text_decals.FONTS, SIL OFL) and cut into runs of a raster's rows, so they read sharp from the street with no picture.
Every part is a palette variant of its library recipe (car.painted), the face and letters glowing.

    sign_parts(text, size, look, vertical)  the parts of a sign of `size` (across, tall, deep; y up, its face towards
                                    +z, its foot on y 0, centred across and in depth): casing, face, letters; a
                                    vertical sign's characters stacked top to bottom, as a Hong Kong blade sign's
    build(text, size, palette, look, finishes, vertical)  (trimesh.Scene, record): the parts painted from the palette,
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


def sign_parts(text, size, look="bold sans", vertical=False):
    """[(part, mesh)]: the casing, the face inset by BORDER standing FACE_PROUD out of it, and the letters standing
    LETTER_PROUD out of the face, the words centred on it as large as TEXT_TALL and TEXT_WIDE let them."""
    import trimesh
    across, tall, deep = (float(value) for value in size)
    front = deep / 2.0
    casing = box((-across / 2, 0.0, -deep / 2), (across / 2, tall, front))
    face_low, face_high = np.array([-across / 2 + BORDER, BORDER]), np.array([across / 2 - BORDER, tall - BORDER])
    face = box((*face_low, front), (*face_high, front + FACE_PROUD))
    raster = ink(text, look, vertical)
    span = face_high - face_low
    cell = min(span[1] * TEXT_TALL / raster.shape[0], span[0] * TEXT_WIDE / raster.shape[1])
    middle = (face_low + face_high) / 2.0
    left, top = middle[0] - raster.shape[1] * cell / 2.0, middle[1] + raster.shape[0] * cell / 2.0
    face_front = front + FACE_PROUD
    letters = trimesh.util.concatenate([
        box((left + first * cell, top - (row + 1) * cell, face_front),
            (left + past * cell, top - row * cell, face_front + LETTER_PROUD)) for row, first, past in runs(raster)])
    return [("casing", casing), ("face", face), ("letters", letters)]


def build(text, size, palette, look="bold sans", finishes=None, vertical=False):
    """(trimesh.Scene, record) of the sign: each part a node of its own name in its palette variant (FINISHES, or
    `finishes` {part: (recipe, variant)} over them), the record naming its text, size and parts as car.painted reads
    them. A glowing face gives off FACE_GLOW and reflects FACE_BASE of its colour, its letters then LETTER_GLOW."""
    import trimesh
    chosen = dict(FINISHES, **(finishes or {}))
    scene = trimesh.Scene()
    record = {"rule": "lightbox", "text": text, "look": look, "size": [float(value) for value in size],
              "vertical": bool(vertical), "parts": []}
    for name, mesh in sign_parts(text, size, look, vertical):
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
