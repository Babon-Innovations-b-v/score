"""Draw the library's printed pictures: screen content, labels, keypad prints and stencils (data/library/pictures),
from the `pictures` of data/library/materials.json. Simplified Chinese in Noto Sans SC Bold (game/ui/fonts, SIL OFL),
colours from palette tokens only.

    ~/.farm-factory-props/env/bin/python tools/props/library/printed.py

A screen's picture is its content on a clear ground, so the glass shows between and only the content glows; a label
is a whole plate. Every string is checked against the typeface's GB2312 cut by the sign test's rule (signs, #121):
use words from the signs already approved (舱 for modules, 门禁 for access control).
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402

FONT = library.REPO / "game/ui/fonts/noto_sans_sc/NotoSansSC-Bold.ttf"
SIZES = {"status": (1024, 640), "readout": (1024, 512), "label": (1024, 256), "keypad": (512, 640),
         "stencil": (512, 256), "notice": (1024, 768)}


def srgb(token):
    """A token's colour as 8-bit sRGB with full alpha."""
    hex_colour = next(entry["value"] for entry in json.loads(library.TOKENS.read_text())["color"]["tokens"]
                      if entry["name"] == token)
    hex_colour = hex_colour["ops"] if isinstance(hex_colour, dict) else hex_colour
    return tuple(int(hex_colour.lstrip("#")[at:at + 2], 16) for at in (0, 2, 4)) + (255,)


def font(size):
    return ImageFont.truetype(str(FONT), size)


def centred(draw, box, text, size, fill):
    face = font(size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=face)
    draw.text(((box[0] + box[2] - (right - left)) / 2 - left, (box[1] + box[3] - (bottom - top)) / 2 - top), text,
              font=face, fill=fill)


def status(spec, size):
    """A status screen: a title bar and rows of name, value and a bar, in the screen's ink, on clear ground."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    faint = ink[:3] + (90,)
    width, height = size
    draw.rectangle((24, 24, width - 24, 120), outline=ink, width=4)
    centred(draw, (24, 24, width - 24, 120), spec["title"], 64, ink)
    row_height = (height - 160) // len(spec["rows"])
    for at, (name, value) in enumerate(spec["rows"]):
        top = 150 + at * row_height
        draw.text((48, top), name, font=font(52), fill=ink)
        draw.text((width // 2 - 40, top), value, font=font(52), fill=ink)
        draw.rectangle((48, top + row_height - 26, width - 48, top + row_height - 14), fill=faint)
        draw.rectangle((48, top + row_height - 26, 48 + (width - 96) * (0.55 + 0.1 * at), top + row_height - 14),
                       fill=ink)
    return picture


def readout(spec, size):
    """A readout: a small title and one big value."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    width, height = size
    centred(draw, (0, 20, width, 150), spec["title"], 80, ink)
    draw.line((60, 165, width - 60, 165), fill=ink, width=5)
    centred(draw, (0, 190, width, height - 30), spec["value"], 170, ink)
    return picture


def label(spec, size):
    """A label plate: the whole picture is the plate, the text in ink with a rule round it."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    width, height = size
    draw.rounded_rectangle((14, 14, width - 14, height - 14), radius=14, outline=ink, width=8)
    centred(draw, (0, 0, width, height), spec["text"], int(height * 0.5), ink)
    return picture


def keypad(spec, size):
    """A keypad's print: twelve key outlines and their figures on clear ground."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    width, height = size
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    cell_w, cell_h = width / 3, height / 4
    for at, key in enumerate(keys):
        column, row = at % 3, at // 3
        box = (column * cell_w + 14, row * cell_h + 14, (column + 1) * cell_w - 14, (row + 1) * cell_h - 14)
        draw.rounded_rectangle(box, radius=12, outline=ink, width=6)
        centred(draw, box, key, int(cell_h * 0.45), ink)
    return picture


def stencil(spec, size):
    """Stencilled figures on clear ground, in ink."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    centred(ImageDraw.Draw(picture), (0, 0) + size, spec["text"], int(size[1] * 0.75), srgb(spec["ink"]))
    return picture


def notice(spec, size):
    """A notice board's sheets: white sheets side by side, each a title and lines of small print in ink, on the
    board's own colour (the plate's)."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    faint = ink[:3] + (150,)
    width, height = size
    sheets = spec["sheets"]
    sheet_w = (width - 40 * (len(sheets) + 1)) / len(sheets)
    for at, (title, lines) in enumerate(sheets):
        left = 40 + at * (sheet_w + 40)
        top = 60 + (at % 2) * 40
        box = (left, top, left + sheet_w, height - 60 - ((at + 1) % 2) * 40)
        draw.rectangle(box, fill=(246, 244, 236, 255))
        centred(draw, (box[0], box[1] + 20, box[2], box[1] + 110), title, 56, ink)
        for line in range(lines):
            y = box[1] + 150 + line * 70
            end = box[2] - 30 - (line * 37 % 90)
            draw.rectangle((box[0] + 30, y, end, y + 14), fill=faint)
        draw.ellipse(((box[0] + box[2]) / 2 - 12, box[1] - 4, (box[0] + box[2]) / 2 + 12, box[1] + 20), fill=ink)
    return picture


STYLES = {"status": status, "notice": notice, "readout": readout, "label": label, "keypad": keypad, "stencil": stencil}


def main():
    library.PICTURES.mkdir(parents=True, exist_ok=True)
    for name, spec in library.theme_library()["pictures"].items():
        STYLES[spec["style"]](spec, SIZES[spec["style"]]).save(library.PICTURES / f"{name}.png")
        print(name)


if __name__ == "__main__":
    main()
