"""A shop's lightbox sign is built with its words raised on its glowing face (2099 #161, the street's 未来茶餐厅): its
casing fills its size with its foot on y 0, its face sits inside the casing's border and stands just out of its front,
its letters stand out of the face within the face's bounds, centred on it, their runs covering the words' ink, and each
part takes its palette variant: the casing painted metal, the face and the letters glowing in their own colours.

Breaks (each applied once, seen red, reverted), in score/stages/signs/__init__.py:
    sign_parts' `face_front = front + FACE_PROUD` -> `face_front = front` (the letters sink into the face)
    `top - (row + 1) * cell` -> `top + (row + 1) * cell` (the words drawn upside down, out of the face)
    runs' `zip(edges[0::2], edges[1::2])` -> `zip(edges[1::2], edges[0::2])` (every run empty or reversed)
    FINISHES' letters `"sign_lettering_red"` -> `"sign_lightbox_cream"` (the words the face's colour: unreadable)
    build's `value * FACE_GLOW` -> `value` (the face glows whole: white, its words pink in its bloom)
    build's `base[:3] * FACE_BASE / 255.0` -> `base[:3] / 255.0` (the face reflects the street's lamps as a cream wall)
    build's `value * LETTER_GLOW` -> `value` (the words glow brighter than the face: salmon in its bloom)
    ink's `[gap] * bool(number) + [...]` -> `[...]` and `np.vstack` -> `np.hstack` (a vertical sign set as one line)
    build's `if chosen["face"][0] == "glowing":` -> `if True:` (a neon blade's letters dimmed as a lightbox's)
    lamp_parts' `under = tall - head - BORDER` -> `under = tall - head` (the lamp's cap above its height)
    build_lamp's `value * LAMP_GLOW` -> `value` (the lamp's head a white bloom blob)
    sign_parts' `border, ... = BORDER * relief, ...` -> `= BORDER, ...` (a 3 cm label plate's face turned inside out)
    sign_parts' `raster = np.hstack([mark_ink(mark), ...])` dropped (a SAS label's marker symbol missing)
    mark_ink's `(0.55 - y)` -> `(y + 0.55)` (every marker drawn upside down: NORMAL's triangle points down)
    MARKS' "anti_normal" strokes swapped for "normal"'s (two buttons carry one symbol)
"""
import numpy as np

from score.stages import signs as lightbox

PALETTE = {"tokens": {"steel-gunmetal": "#3a3f45", "sign-cream": "#f4ead2", "sign-red-text": "#c8382a"},
           "families": {"steel": {"variants": {"gunmetal_steel": {"token": "steel-gunmetal", "roughness": 0.45,
                                                                  "metal": 0.0}}},
                        "plastic": {"variants": {"sign_lightbox_cream": {"token": "sign-cream", "roughness": 0.3},
                                                 "sign_lettering_red": {"token": "sign-red-text", "roughness": 0.3},
                                                 "lamp_head_glow": {"token": "sign-cream", "roughness": 0.3}}}}}


def test_a_lightbox_sign_carries_its_words_raised_on_its_glowing_face():
    size = (3.0, 1.0, 0.36)
    scene, record = lightbox.build("未来茶餐厅", size, PALETTE)
    parts = {name: scene.geometry[name] for name in ("casing", "face", "letters")}
    casing, face, letters = (parts[name].bounds for name in ("casing", "face", "letters"))
    assert np.allclose(casing, [[-1.5, 0.0, -0.18], [1.5, 1.0, 0.18]])
    assert np.allclose(face[:, :2], [[-1.5 + lightbox.BORDER, lightbox.BORDER], [1.5 - lightbox.BORDER, 1.0 - lightbox.BORDER]])
    assert np.isclose(face[0, 2], 0.18) and np.isclose(face[1, 2], 0.18 + lightbox.FACE_PROUD)
    assert np.isclose(letters[0, 2], face[1, 2]) and np.isclose(letters[1, 2], face[1, 2] + lightbox.LETTER_PROUD)
    assert np.all(letters[0, :2] >= face[0, :2] - 1e-9) and np.all(letters[1, :2] <= face[1, :2] + 1e-9)
    assert np.allclose((letters[0, :2] + letters[1, :2]) / 2.0, (face[0, :2] + face[1, :2]) / 2.0, atol=0.02)
    raster = lightbox.ink("未来茶餐厅", "bold sans")
    covered = np.zeros_like(raster)
    for row, first, past in lightbox.runs(raster):
        assert past > first
        covered[row, first:past] = True
    assert np.array_equal(covered, raster) and raster.mean() > 0.2, "the runs are the words' ink"
    cell = (letters[1, 0] - letters[0, 0]) / raster.shape[1]
    centres = parts["letters"].triangles_center
    centres = centres[np.isclose(centres[:, 2], letters[1, 2])]  # the letters' fronts
    for row in (0, raster.shape[0] // 2, raster.shape[0] - 1):  # each raster row's ink at its own height, top down
        band = centres[np.abs(centres[:, 1] - (letters[1, 1] - (row + 0.5) * cell)) < cell * 0.49]
        columns = np.unique(np.clip(((band[:, 0] - letters[0, 0]) / cell).astype(int), 0, raster.shape[1] - 1))
        assert set(columns) <= set(np.flatnonzero(raster[row])) and len(columns), row
    finishes = {part["name"]: (part["finish"], part["variant"]) for part in record["parts"]}
    assert finishes == {"casing": ("painted_metal", "gunmetal_steel"), "face": ("glowing", "sign_lightbox_cream"),
                        "letters": ("glowing", "sign_lettering_red")}
    face_glow, letter_glow = (np.asarray(scene.geometry[name].visual.material.emissiveFactor) for name in ("face", "letters"))
    face_colour = np.asarray(scene.geometry["face"].visual.material.baseColorFactor[:3]) / 255.0
    assert np.allclose(face_glow, face_colour / lightbox.FACE_BASE * lightbox.FACE_GLOW, atol=0.01) \
        and 0.0 < lightbox.FACE_GLOW < 1.0 and 0.0 < lightbox.FACE_BASE < 1.0, \
        "the face glows its cream through a diffuser and reflects only part of it"
    assert letter_glow[0] > 2 * letter_glow[1] and letter_glow.sum() < face_glow.sum(), \
        "the letters glow red, deeper than the face, so they read red on it"
    assert not np.any(scene.geometry["casing"].visual.material.emissiveFactor)
    blade, blade_record = lightbox.build("未来酒店", (0.8, 2.8, 0.2), PALETTE, vertical=True,
                                         finishes={"face": ("painted_metal", "gunmetal_steel"),
                                                   "letters": ("glowing", "sign_lettering_red")})
    tall = lightbox.ink("未来酒店", "bold sans", vertical=True)
    one = lightbox.ink("未", "bold sans")
    assert tall.shape[0] == 4 * one.shape[0] + 3 * round(lightbox.ROWS * lightbox.GAP) and tall.shape[1] < 2 * one.shape[1], \
        "a vertical sign's characters stack top to bottom, a gap between each"
    blade_letters = blade.geometry["letters"].bounds
    assert blade_letters[1, 1] - blade_letters[0, 1] > 2 * (blade_letters[1, 0] - blade_letters[0, 0])
    assert not np.any(blade.geometry["face"].visual.material.emissiveFactor) and np.allclose(
        blade.geometry["letters"].visual.material.emissiveFactor, lightbox.car.linear("#c8382a"), atol=0.01), \
        "a neon blade: a dark face, its letters glowing their whole colour"
    label, label_record = lightbox.build("TALK", (0.1, 0.03, 0.005), PALETTE, relief=0.05,
                                         finishes={"face": ("painted_metal", "gunmetal_steel")})
    label_face, label_letters = label.geometry["face"].bounds, label.geometry["letters"].bounds
    assert label_record["relief"] == 0.05 and np.allclose(label_face[:, :2], [[-0.05 + 0.003, 0.003], [0.05 - 0.003, 0.027]]) \
        and np.all(label_letters[0, :2] >= label_face[0, :2] - 1e-9) and np.all(label_letters[1, :2] <= label_face[1, :2] + 1e-9) \
        and np.isclose(label_letters[1, 2] - label_letters[0, 2], lightbox.LETTER_PROUD * 0.05), \
        "a small label plate keeps a face inside its border, its letters on it, both reliefs scaled"
    lamp, lamp_record = lightbox.build_lamp(3.0, 0.42, PALETTE)
    assert np.allclose(lamp.bounds, [[-0.21 - lightbox.BORDER / 2, 0.0, -0.21 - lightbox.BORDER / 2],
                                     [0.21 + lightbox.BORDER / 2, 3.0, 0.21 + lightbox.BORDER / 2]]), \
        "a square lamp stands on y 0 to its height, its cap the widest part"
    head = lamp.geometry["head"]
    assert np.isclose(head.bounds[1, 1], lamp.geometry["cap"].bounds[0, 1]) \
        and np.isclose(head.bounds[0, 1], lamp.geometry["pole"].bounds[1, 1]), "the head sits on the pole under the cap"
    assert np.allclose(head.visual.material.emissiveFactor,
                       np.asarray(head.visual.material.baseColorFactor[:3]) / 255.0 / lightbox.FACE_BASE * lightbox.LAMP_GLOW,
                       atol=0.01) and not np.any(lamp.geometry["pole"].visual.material.emissiveFactor), \
        "the lamp's head glows part of its colour, its pole does not"
    marked, marked_record = lightbox.build("NORMAL", (0.08, 0.022, 0.005), PALETTE, relief=0.03, mark="normal")
    plain = lightbox.build("NORMAL", (0.08, 0.022, 0.005), PALETTE, relief=0.03)[0]
    symbol = lightbox.mark_ink("normal")
    marked_letters = marked.geometry["letters"].bounds
    assert marked_record["mark"] == "normal" and symbol.shape == (lightbox.ROWS, lightbox.ROWS) \
        and len(marked.geometry["letters"].faces) == len(plain.geometry["letters"].faces) + 12 * len(lightbox.runs(symbol)) \
        and np.all(marked_letters[0, :2] >= marked.geometry["face"].bounds[0, :2] - 1e-9), \
        "a SAS label carries its marker's symbol raised left of its words"
    inked = np.flatnonzero(symbol.any(axis=1))
    top, bottom = symbol[inked[0] + 2], symbol[inked[-1] - 2]
    assert top.sum() < bottom.sum() / 3, "NORMAL's triangle points up, as the ball draws it"
    drawn = {name: lightbox.mark_ink(name).tobytes() for name in lightbox.MARKS}
    assert len(set(drawn.values())) == len(lightbox.MARKS) == 10 \
        and all(0.02 < lightbox.mark_ink(name).mean() < 0.4 for name in lightbox.MARKS), \
        "each of the ten SAS buttons' symbols is its own, drawn in lines"
