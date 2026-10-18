"""The pictures an output's records point at: each record that names a picture on the store's machine (an absolute
path to an image that is there), cut to the record's `box` of pixels when it has one, named by the record: one cell
per record."""
import pathlib

from PIL import Image, ImageDraw, ImageFont

CELL = 180
LABEL = 16
COLUMNS = 4
MOST = 16
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
BACKGROUND = (238, 236, 230)
INK = (29, 32, 38)


def records(document):
    """The records a document holds: a list of dicts, the dicts of its first list of dicts, or its dict values."""
    if isinstance(document, list):
        return [item for item in document if isinstance(item, dict)]
    if not isinstance(document, dict):
        return []
    listed = next((value for value in document.values() if isinstance(value, list) and value
                   and isinstance(value[0], dict)), None)
    if listed:
        return [item for item in listed if isinstance(item, dict)]
    return [{"id": key, **value} for key, value in document.items() if isinstance(value, dict)]


def picture_path(record):
    """The first absolute path to an image on this machine that the record names; None."""
    for value in record.values():
        if isinstance(value, str) and value.startswith("/") and pathlib.Path(value).suffix.lower() in IMAGES:
            if pathlib.Path(value).is_file():
                return pathlib.Path(value)
    return None


def pixel_box(record):
    """The record's `box` of pixels (left, top, right, bottom) when it is one; None."""
    found = record.get("box")
    if isinstance(found, list) and len(found) == 4 and all(isinstance(value, int) for value in found) \
            and found[2] > found[0] and found[3] > found[1]:
        return tuple(found)
    return None


def pointed(document):
    """[(name, picture path, box or None)] of the records that name a picture that is there."""
    found = []
    for number, record in enumerate(records(document)):
        path = picture_path(record)
        if path:
            name = next((record[field] for field in ("id", "name", "take") if isinstance(record.get(field), str)),
                        str(number))
            found.append((name, path, pixel_box(record)))
    return found


def cut(path, box):
    """The picture, cut to the box when there is one, fitted into a cell."""
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    if box:
        image = image.crop(box)
    image.thumbnail((CELL - 8, CELL - 8))
    return image


def picture(found, destination):
    """The sheet of pointed-at pictures, each named; the path."""
    shown = found[:MOST]
    rows = -(-len(shown) // COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * CELL, rows * (CELL + LABEL)), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=11)
    for number, (name, path, box) in enumerate(shown):
        left, top = (number % COLUMNS) * CELL, (number // COLUMNS) * (CELL + LABEL)
        image = cut(path, box)
        sheet.paste(image, (left + (CELL - image.width) // 2, top + (CELL - image.height) // 2))
        pen.text((left + 4, top + CELL), str(name)[:26], fill=INK, font=small)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
