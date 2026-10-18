"""The visual check's pictures: each finding marked on the picture it was found on (its cells tinted and outlined,
its words under it), and a contact sheet of every place judged.

    marks.marked(image, item, path)            # one finding's picture
    marks.sheet(rows, path)       # rows: [(place, answer, [marked pictures, else a plain one], reason)]
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SIDE = (640, 360)
TEXT_BAND = 44
TINT = {"blocking plane": (230, 60, 40), "untextured": (240, 170, 20), "little seen": (60, 140, 240),
        "neighbour inside": (200, 40, 200)}
ANSWER_COLOUR = {"fail": (190, 50, 40), "pass": (40, 140, 70), "unknown": (130, 130, 130)}
BACKGROUND = (238, 236, 230)
INK = (29, 32, 38)
THUMB = (320, 180)
MOST_A_ROW = 4
NAME_WIDTH = 150


def cells_mask(cells, size):
    """A finding's cells as a picture-sized mask."""
    grid = Image.fromarray((np.asarray(cells, dtype=np.uint8) * 255))
    return np.asarray(grid.resize(size, Image.NEAREST)) > 0


def tinted(image, mask, colour):
    """The picture with the mask tinted in a colour and outlined."""
    pixels = np.asarray(image.convert("RGB").resize(SIDE, Image.LANCZOS), dtype=float)
    pixels[mask] = pixels[mask] * 0.55 + np.asarray(colour) * 0.45
    edge = mask & ~ndimage.binary_erosion(mask, iterations=2)
    pixels[edge] = colour
    return Image.fromarray(pixels.astype(np.uint8))


def wrapped(text, width):
    """The text cut into lines of at most `width` characters, at words."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def marked(image, item, path):
    """One finding's picture: its cells marked, its rule, picture and sentence written under it; the path."""
    colour = TINT[item["rule"]]
    shown = tinted(image, cells_mask(item["cells"], SIDE), colour)
    canvas = Image.new("RGB", (SIDE[0], SIDE[1] + TEXT_BAND), BACKGROUND)
    canvas.paste(shown, (0, 0))
    pen = ImageDraw.Draw(canvas)
    small = ImageFont.load_default(size=11)
    pen.rectangle((0, SIDE[1], 8, SIDE[1] + TEXT_BAND), fill=colour)
    words = [f"{item['rule']} ({item['name']})", *wrapped(item["sentence"], 100)][:3]
    for number, line in enumerate(words):
        pen.text((14, SIDE[1] + 3 + number * 13), line, fill=INK, font=small)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path


def sheet(rows, path):
    """A contact sheet: a row a place, its name, answer and reason, then up to MOST_A_ROW pictures; the path."""
    row_height = THUMB[1] + 30
    canvas = Image.new("RGB", (NAME_WIDTH + MOST_A_ROW * (THUMB[0] + 6), 10 + row_height * len(rows)), BACKGROUND)
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=14)
    small = ImageFont.load_default(size=11)
    for number, (place, answer, pictures, note) in enumerate(rows):
        top = 10 + number * row_height
        pen.text((8, top + 4), place, fill=INK, font=font)
        pen.text((8, top + 24), answer, fill=ANSWER_COLOUR[answer], font=font)
        for line, text in enumerate(wrapped(note, 22)[:8]):
            pen.text((8, top + 46 + line * 13), text, fill=INK, font=small)
        for column, picture in enumerate(pictures[:MOST_A_ROW]):
            thumb = Image.open(picture).convert("RGB")
            thumb.thumbnail((THUMB[0], THUMB[1] + 30))
            canvas.paste(thumb, (NAME_WIDTH + column * (THUMB[0] + 6), top))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path
