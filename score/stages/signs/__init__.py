"""A shop's lightbox sign built in code (2099 #161, the street's tea restaurant 未来茶餐厅: TRELLIS.2 draws no
characters, and its sign read "未来余食厅" in a dull texture that never lit): a dark metal casing, a glowing face inset
in it, and the words standing proud of the face as raised letters, each set in the library's face
(text_decals.FONTS, SIL OFL) and cut into runs of a raster's rows, so they read sharp from the street with no picture.
Every part is a palette variant of its library recipe (car.painted), the face and letters glowing.

    sign_parts(text, size, look)    the parts of a sign of `size` (across, tall, deep; y up, its face towards +z, its
                                    foot on y 0, centred across and in depth): casing, face, letters
    build(text, size, palette)      (trimesh.Scene, record): the parts painted from the palette
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
FINISHES = {"casing": ("painted_metal", "gunmetal_steel"), "face": ("glowing", "sign_lightbox_cream"),
            "letters": ("glowing", "sign_lettering_red")}


def ink(text, look):
    """The words' ink as a boolean raster ROWS tall (True where a letter is), cropped to its ink."""
    from PIL import Image
    from score.stages.surfaces import text_decals
    line = text_decals.set_line(text, look)
    wide = max(1, round(line.width * ROWS / line.height))
    return np.asarray(line.resize((wide, ROWS), Image.LANCZOS)) >= 128


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


def sign_parts(text, size, look="bold sans"):
    """[(part, mesh)]: the casing, the face inset by BORDER standing FACE_PROUD out of it, and the letters standing
    LETTER_PROUD out of the face, the words centred on it as large as TEXT_TALL and TEXT_WIDE let them."""
    import trimesh
    across, tall, deep = (float(value) for value in size)
    front = deep / 2.0
    casing = box((-across / 2, 0.0, -deep / 2), (across / 2, tall, front))
    face_low, face_high = np.array([-across / 2 + BORDER, BORDER]), np.array([across / 2 - BORDER, tall - BORDER])
    face = box((*face_low, front), (*face_high, front + FACE_PROUD))
    raster = ink(text, look)
    span = face_high - face_low
    cell = min(span[1] * TEXT_TALL / raster.shape[0], span[0] * TEXT_WIDE / raster.shape[1])
    middle = (face_low + face_high) / 2.0
    left, top = middle[0] - raster.shape[1] * cell / 2.0, middle[1] + raster.shape[0] * cell / 2.0
    face_front = front + FACE_PROUD
    letters = trimesh.util.concatenate([
        box((left + first * cell, top - (row + 1) * cell, face_front),
            (left + past * cell, top - row * cell, face_front + LETTER_PROUD)) for row, first, past in runs(raster)])
    return [("casing", casing), ("face", face), ("letters", letters)]


def build(text, size, palette, look="bold sans"):
    """(trimesh.Scene, record) of the sign: each part a node of its own name in its palette variant (FINISHES), the
    record naming its text, size and parts as car.painted reads them."""
    import trimesh
    scene = trimesh.Scene()
    record = {"rule": "lightbox", "text": text, "look": look, "size": [float(value) for value in size], "parts": []}
    for name, mesh in sign_parts(text, size, look):
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        recipe, variant = FINISHES[name]
        record["parts"].append({"name": name, "finish": recipe, "variant": variant})
    car.painted(scene, record, palette)
    material = scene.geometry["face"].visual.material
    material.emissiveFactor = [value * FACE_GLOW for value in material.emissiveFactor]
    record["face_glow"] = FACE_GLOW
    return scene, record
