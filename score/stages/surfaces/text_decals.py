"""Text decals (#171, owner on #164, 2026-11-23: "TRELLIS isnt able to do text and numbers tho"): a printed mark of
words or numbers, or a plain printed line, is never a route's texture and never a library picture. The finish list reads
its words, its typeface's look and its ink from the close-up (finish_ask.marks_of); the parts row places it at its cast
size (route_parts.decal_placements) and draws it here, set in the library's own face of that look (data/fonts, SIL OFL,
the faces the library's `printed` recipe sets its labels in), as a one-ink decal: white through its transparency, the
bake printing it in its palette token's ink (recipes.decal_layer), as a single-ink library decal is.

    FONTS                          {look: the library face set for it}
    drawn(placement)               the decal's picture (RGBA), its words filling its measured box
"""
import pathlib

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
# The looks a text mark is read as, each the library face set for it. score_lib holds no font yet, nor does the
# library hold a stencil or a monospaced face: the list is offered these looks alone.
FONTS = {"sans": "data/fonts/noto_sans_sc/NotoSansSC-Regular.otf",
         "bold sans": "data/fonts/noto_sans_sc/NotoSansSC-Bold.ttf",
         "condensed": "data/fonts/barlow_condensed/BarlowCondensed-SemiBold.ttf",
         "serif": "data/fonts/noto_serif_sc/NotoSerifSC-Bold.ttf"}
DRAWN = ("text", "rule")  # the mark shapes drawn here; a "picture" mark is a library decal or a gap
PX_PER_M = 3000  # #161 rule 7: a part with print is baked at about 3,000 px a metre
MOST_PX = 4096
SET_PX = 512  # the size a line is set at before it is fitted to its box


def pixels(size_m):
    """(width, height) in pixels of a decal `size_m` metres at PX_PER_M, its longer side at most MOST_PX."""
    scale = min(PX_PER_M, MOST_PX / max(max(size_m), 1e-6))
    return max(1, round(size_m[0] * scale)), max(1, round(size_m[1] * scale))


def set_line(text, look):
    """The words set in the look's face at SET_PX, cropped to their ink (an alpha picture)."""
    from PIL import Image, ImageDraw, ImageFont
    face = ImageFont.truetype(str(REPO / FONTS[look]), SET_PX)
    left, top, right, bottom = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=face)
    line = Image.new("L", (right - left + 2, bottom - top + 2), 0)
    ImageDraw.Draw(line).text((1 - left, 1 - top), text, font=face, fill=255)
    return line.crop(line.getbbox())


def drawn(placement):
    """A drawn mark's picture (RGBA, white through its transparency) at its placement's size: a text mark's words set
    in its look's face, scaled whole to fit inside the box and centred in it (a face is never stretched); a rule the
    whole box."""
    from PIL import Image
    wide, tall = pixels(placement["size"])
    alpha = Image.new("L", (wide, tall), 0)
    if placement["shape"] == "rule":
        alpha.paste(255, (0, 0, wide, tall))
    else:
        line = set_line(placement["text"], placement["look"])
        scale = min(wide / line.width, tall / line.height)
        fitted = line.resize((max(1, round(line.width * scale)), max(1, round(line.height * scale))), Image.LANCZOS)
        alpha.paste(fitted, ((wide - fitted.width) // 2, (tall - fitted.height) // 2))
    picture = np.zeros((tall, wide, 4), dtype=np.uint8)
    picture[..., :3] = 255
    picture[..., 3] = np.asarray(alpha)
    return Image.fromarray(picture)
