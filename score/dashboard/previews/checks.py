"""A surface check pictured: for each checked model, each surface it wears as a pair of patches, the library's colour
over the colour its bake came out in (both CIE Lab in the output), the difference written under them, a large one
marked. A model's surfaces are shown largest share first."""
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PATCH = 30
NAME_WIDTH = 150
ROW = PATCH * 2 + 18
MOST_MODELS = 10
MOST_SURFACES = 8
FAR = 10.0  # a colour difference (delta E) the eye reads as another colour
BACKGROUND = (238, 236, 230)
INK = (29, 32, 38)
GREY = (120, 120, 120)
WARN = (180, 88, 58)
WHITE = np.array([95.047, 100.0, 108.883])


def lab_rgb(lab):
    """(r, g, b) 0-255 of a CIE Lab colour (D65), clipped into sRGB."""
    lightness, green_red, blue_yellow = (float(value) for value in lab)
    middle = (lightness + 16) / 116
    parts = np.array([middle + green_red / 500, middle, middle - blue_yellow / 200])
    linear = np.where(parts ** 3 > 0.008856, parts ** 3, (parts - 16 / 116) / 7.787) * WHITE / 100
    rgb = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]]) @ linear
    rgb = np.where(rgb > 0.0031308, 1.055 * np.clip(rgb, 0, None) ** (1 / 2.4) - 0.055, 12.92 * rgb)
    return tuple(int(value) for value in np.clip(rgb * 255, 0, 255).round())


def checked(document):
    """[(model, [(surface, library lab, baked lab, delta E)])] of a check document: every model whose `surfaces` hold
    both a library and a baked colour; empty for any other document."""
    if not isinstance(document, dict):
        return []
    found = []
    for model, record in document.items():
        surfaces = record.get("surfaces") if isinstance(record, dict) else None
        if not isinstance(surfaces, dict):
            continue
        pairs = [(surface, facts["surface_lab"], facts["baked_lab"], facts.get("delta_e"), facts.get("share", 0))
                 for surface, facts in surfaces.items()
                 if isinstance(facts, dict) and facts.get("surface_lab") and facts.get("baked_lab")]
        pairs.sort(key=lambda pair: -(pair[4] or 0))
        if pairs:
            found.append((model, [pair[:4] for pair in pairs]))
    return found


def picture(models, destination):
    """The sheet of checked models, a row each; the path."""
    shown = models[:MOST_MODELS]
    sheet = Image.new("RGB", (NAME_WIDTH + MOST_SURFACES * (PATCH + 8), 20 + ROW * len(shown)), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=10)
    pen.text((6, 4), f"surface check: {len(models)} models, library colour over baked colour", fill=INK, font=small)
    for number, (model, pairs) in enumerate(shown):
        top = 20 + number * ROW
        pen.text((6, top + PATCH - 6), str(model)[:24], fill=INK, font=small)
        for column, (surface, library, baked, difference) in enumerate(pairs[:MOST_SURFACES]):
            left = NAME_WIDTH + column * (PATCH + 8)
            far = difference is not None and difference > FAR
            pen.rectangle([left, top, left + PATCH, top + PATCH], fill=lab_rgb(library))
            pen.rectangle([left, top + PATCH, left + PATCH, top + 2 * PATCH], fill=lab_rgb(baked),
                          outline=WARN if far else None, width=2)
            words = "" if difference is None else f"{difference:.0f}"
            pen.text((left + 2, top + 2 * PATCH + 2), words, fill=WARN if far else GREY, font=small)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
