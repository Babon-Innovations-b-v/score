"""One person's eyes sheet (#223): the close-up photo's eyes, then the generated head before and after its eyes are made
real (`blender_eyes.py`'s pictures): the eyes close up and the face, and the face from three quarters after.

    python -m tools.characters.generated.eyes_sheet <name> <renders folder> <close-up photo> <stats.json> <out.jpg>
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROW_HEIGHT = 700
GAP = 10
LABEL = 44
PHOTO_CROP = (4.2, 1.6)  # the photo's eyes cropped this many pupil distances wide, and tall, round their middle
ROWS = [[("photo", "close-up photo (the reference)"), ("before-eyes", "before: eyes, 9 cm frame"),
         ("after-eyes", "after: eyes, 9 cm frame")],
        [("before-face", "before: face"), ("after-face", "after: face"),
         ("after-three_quarter", "after: three quarters")]]


def photo_eyes(photo_path, stats):
    """The photo cropped round its eyes (where eyes.py found them)."""
    photo = Image.open(photo_path).convert("RGB")
    pupils = np.array(stats["photo_pupils_px"])
    middle, apart = pupils.mean(axis=0), np.linalg.norm(pupils[1] - pupils[0])
    half = np.array(PHOTO_CROP) * apart / 2.0
    return photo.crop(tuple(int(value) for value in (*(middle - half), *(middle + half))))


def font():
    """The sheet's label font."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except OSError:
        return ImageFont.load_default()


def row_image(pictures, typeface):
    """One row of labelled pictures, each scaled to ROW_HEIGHT."""
    panels = [(picture.resize((round(picture.width * ROW_HEIGHT / picture.height), ROW_HEIGHT), Image.LANCZOS), label)
              for picture, label in pictures]
    row = Image.new("RGB", (sum(panel.width for panel, _ in panels) + GAP * (len(panels) - 1), ROW_HEIGHT + LABEL),
                    "white")
    draw = ImageDraw.Draw(row)
    left = 0
    for panel, label in panels:
        row.paste(panel, (left, LABEL))
        draw.text((left + 6, 8), label, fill="black", font=typeface)
        left += panel.width + GAP
    return row


def sheet(name, renders, photo_path, stats_path, out):
    """The sheet written to `out` (jpg) with its title line."""
    stats = json.loads(pathlib.Path(stats_path).read_text())
    typeface = font()
    pictures = {"photo": photo_eyes(photo_path, stats)}
    pictures.update({key: Image.open(pathlib.Path(renders) / f"{key}.png").convert("RGB")
                     for row in ROWS for key, _ in row if key != "photo"})
    rows = [row_image([(pictures[key], label) for key, label in row], typeface) for row in ROWS]
    title = (f"{name}: TRELLIS.2 head, painted eyes replaced by the face module's eyeball "
             f"({stats['eye_diameter_mm']} mm, "
             f"cornea, tear film, library eye finishes), iris toned to the photo's (linear "
             f"{', '.join(f'{value:.3f}' for value in stats['iris_linear'])}), lids the model's own")
    width = max(row.width for row in rows)
    page = Image.new("RGB", (width, LABEL + sum(row.height + GAP for row in rows)), "white")
    ImageDraw.Draw(page).text((6, 8), title, fill="black", font=typeface)
    top = LABEL
    for row in rows:
        page.paste(row, (0, top))
        top += row.height + GAP
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    page.save(out, quality=90)
    return out


if __name__ == "__main__":
    print(f"sheet: {sheet(*sys.argv[1:6])}")
