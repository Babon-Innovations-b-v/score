"""Draw the library's printed pictures: screen content, labels, keypad prints and stencils (data/library/pictures),
from the `pictures` of data/library/materials.json. English in Barlow Condensed Bold (data/fonts, SIL OFL), the
game's own display face: every label and screen on the base reads in English (the owner, 2026-10-06, after the hub's
in-game test). Colours from palette tokens only.

    ~/.farm-factory-props/env/bin/python tools/props/library/printed.py [name ...]     # all, or only these

A screen's picture is its content on a clear ground, so the glass shows between and only the content glows; a label
is a whole plate. A line is set as big as its box allows and shrunk until it fits across it.
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402

FONT = library.REPO / "data/fonts/barlow_condensed/BarlowCondensed-Bold.ttf"
# The margin a line keeps from its box's sides, in pixels.
MARGIN = 36
SIZES = {"status": (1024, 640), "readout": (1024, 512), "label": (1024, 256), "keypad": (512, 640),
         "stencil": (512, 256), "notice": (1024, 768), "lens": (256, 32), "sheet": (768, 1024),
         "plan": (1024, 704), "note": (512, 512)}


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
    while right - left > box[2] - box[0] - 2 * MARGIN and size > 8:
        size -= 2
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


def lens(spec, size):
    """A lamp's lens, lit: the token's colour across it, fading a little toward its ends (a strip lamp's tube)."""
    picture = Image.new("RGBA", size, srgb(spec["ink"]))
    draw = ImageDraw.Draw(picture)
    width, height = size
    for column in range(width // 8):
        fade = 1.0 - 0.35 * (1.0 - column / (width // 8))
        shade = tuple(int(value * fade) for value in srgb(spec["ink"])[:3]) + (255,)
        draw.line((column, 0, column, height), fill=shade)
        draw.line((width - 1 - column, 0, width - 1 - column, height), fill=shade)
    return picture


def sheet(spec, size):
    """One pinned sheet: a title and lines of small print (a table's rules when `table`) in ink on clear ground,
    the paper the plate's own colour."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    faint = ink[:3] + (150,)
    width, height = size
    centred(draw, (0, 40, width, 170), spec["title"], 96, ink)
    draw.line((60, 190, width - 60, 190), fill=ink, width=6)
    rows = spec["lines"]
    step = (height - 260) / rows
    for line in range(rows):
        y = 240 + line * step
        if spec.get("table"):
            draw.line((60, y + step - 10, width - 60, y + step - 10), fill=faint, width=3)
            draw.rectangle((80, y + 10, 80 + (width - 160) * (0.25 + (line * 13 % 20) / 100), y + 28), fill=faint)
            draw.rectangle((width / 2 + 20, y + 10, width / 2 + 20 + (width / 2 - 100) * (0.4 + (line * 7 % 30) / 100),
                            y + 28), fill=faint)
        else:
            draw.rectangle((80, y + 10, width - 80 - (line * 37 % 140), y + 28), fill=faint)
    return picture


def plan(spec, size):
    """A plan sheet: a title and a simple floor plan (a ring of rooms round a hub) in ink lines."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    width, height = size
    centred(draw, (0, 20, width, 120), spec["title"], 72, ink)
    middle = (width / 2, height / 2 + 50)
    radius = min(width, height) * 0.28
    draw.ellipse((middle[0] - radius, middle[1] - radius, middle[0] + radius, middle[1] + radius), outline=ink,
                 width=6)
    draw.ellipse((middle[0] - radius / 2, middle[1] - radius / 2, middle[0] + radius / 2, middle[1] + radius / 2),
                 outline=ink, width=4)
    for left, top, right, bottom in ((40, middle[1] - 50, middle[0] - radius, middle[1] + 50),
                                     (middle[0] + radius, middle[1] - 50, width - 40, middle[1] + 50),
                                     (middle[0] - 50, 130, middle[0] + 50, middle[1] - radius)):
        draw.rectangle((left, top, right, bottom), outline=ink, width=5)
    return picture


def note(spec, size):
    """A sticky note: a few short words in ink, on the plate's own colour."""
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    width, height = size
    rows = spec["lines"]
    for at, text in enumerate(rows):
        top = 40 + at * (height - 80) / len(rows)
        centred(draw, (0, top, width, top + (height - 80) / len(rows)), text, 110, srgb(spec["ink"]))
    return picture


# Earth's print (the prologue build, 2026-10-07): every word on Earth is Mandarin (the bible's sign system), set in the
# game's own Chinese faces, cut to GB2312 (data/fonts, SIL OFL).
HANZI_FONTS = {"sans": "noto_sans_sc/NotoSansSC-Bold.ttf", "black": "noto_sans_sc/NotoSansSC-Black.ttf",
               "serif": "noto_serif_sc/NotoSerifSC-Bold.ttf", "qingke": "zcool_qingke_huangyou/ZCOOLQingKeHuangYou-Regular.ttf"}
HANZI_SIZES = {"banner": (2048, 512), "couplet": (256, 1536), "poster": (768, 1024), "square": (512, 512),
               "plate": (1024, 384), "sheets": (1024, 768), "calendar": (768, 1024)}


def hanzi_font(spec, size):
    return ImageFont.truetype(str(library.REPO / "data/fonts" / HANZI_FONTS[spec.get("font", "sans")]), size)


def hanzi_line(draw, box, text, spec, fill, size):
    """One line of Chinese as big as its box allows, centred in it."""
    face = hanzi_font(spec, size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=face)
    while (right - left > box[2] - box[0] - 2 * MARGIN or bottom - top > box[3] - box[1] - MARGIN) and size > 8:
        size -= 4
        face = hanzi_font(spec, size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=face)
    draw.text(((box[0] + box[2] - (right - left)) / 2 - left, (box[1] + box[3] - (bottom - top)) / 2 - top), text,
              font=face, fill=fill)


def hanzi(spec, size):
    """Chinese words in ink on clear ground: lines across (`lines`), or one column read downward (`column`, a couplet
    or a banner down a pole); a `rule` draws a border inside the edge, as a plaque's or a poster's."""
    size = HANZI_SIZES[spec.get("shape", "plate")]
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    width, height = size
    if spec.get("rule"):
        draw.rectangle((20, 20, width - 20, height - 20), outline=ink, width=10)
    if "column" in spec:
        step = (height - 2 * MARGIN) / len(spec["column"])
        for at, character in enumerate(spec["column"]):
            top = MARGIN + at * step
            hanzi_line(draw, (0, top, width, top + step), character, spec, ink, int(min(width, step) * 0.8))
        return picture
    lines = spec["lines"]
    step = (height - 2 * MARGIN) / len(lines)
    for at, text in enumerate(lines):
        top = MARGIN + at * step
        hanzi_line(draw, (0, top, width, top + step), text, spec, ink, int(step * 0.8))
    return picture


def hanzi_sheets(spec, size):
    """A notice board's sheets in Chinese: sheets side by side, a title and lines of small print each, on clear
    ground between them (the board's colour)."""
    size = HANZI_SIZES["sheets"]
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
        draw.rectangle(box, fill=(240, 236, 222, 255))
        hanzi_line(draw, (box[0], box[1] + 20, box[2], box[1] + 120), title, spec, ink, 64)
        for line in range(lines):
            y = box[1] + 160 + line * 60
            draw.rectangle((box[0] + 30, y, box[2] - 30 - (line * 37 % 90), y + 14), fill=faint)
    return picture


def calendar(spec, size):
    """A wall calendar's page: a picture panel over a grid of day numbers, the month in Chinese, and no year (the game
    shows the year once, on its first screen)."""
    size = HANZI_SIZES["calendar"]
    picture = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = srgb(spec["ink"])
    accent = srgb(spec["accent"])
    width, height = size
    draw.rectangle((40, 40, width - 40, height * 0.45), fill=srgb(spec["panel"]))
    hanzi_line(draw, (40, height * 0.46, width - 40, height * 0.58), spec["month"], spec, accent, 90)
    for day in range(31):
        column, row = (day + 3) % 7, (day + 3) // 7
        box = (60 + column * (width - 120) / 7, height * 0.6 + row * 70, 60 + (column + 1) * (width - 120) / 7,
               height * 0.6 + row * 70 + 64)
        face = font(48)
        left, top, right, bottom = draw.textbbox((0, 0), str(day + 1), font=face)
        draw.text(((box[0] + box[2] - (right - left)) / 2 - left, (box[1] + box[3] - (bottom - top)) / 2 - top),
                  str(day + 1), font=face, fill=accent if column in (0, 6) else ink)
    return picture


STYLES = {"status": status, "notice": notice, "readout": readout, "label": label, "keypad": keypad, "stencil": stencil,
          "lens": lens, "sheet": sheet, "plan": plan, "note": note, "hanzi": hanzi, "hanzi_sheets": hanzi_sheets,
          "calendar": calendar}


def main():
    library.PICTURES.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:]
    for name, spec in library.theme_library()["pictures"].items():
        if (wanted and name not in wanted) or spec["style"] not in STYLES:  # a "drawn" picture has a tool of its own
            continue
        STYLES[spec["style"]](spec, SIZES.get(spec["style"])).save(library.PICTURES / f"{name}.png")
        print(name)


if __name__ == "__main__":
    main()
