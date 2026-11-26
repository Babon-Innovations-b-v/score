"""One person's skin sheet (#223): the close-up photo beside the generated head before and after its face is
re-painted from the photo and its skin made skin (`blender_skin.py`'s pictures): the face from the front and three
quarters, the eyes in a 9 cm frame and the cheek and nose close up, each row led by the photo cropped the same way.

    python -m tools.characters.generated.skin_sheet <name> <renders folder> <close-up photo> <skin stats.json> \
        <out.jpg>
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

from tools.characters.generated import eyes_sheet

ROWS = [[("photo-face", "close-up photo"), ("before-face", "before: face"), ("after-face", "after: face"),
         ("before-three_quarter", "before: three quarters"), ("after-three_quarter", "after: three quarters")],
        [("photo-eyes", "close-up photo"), ("before-eyes", "before: eyes, 9 cm frame"),
         ("after-eyes", "after: eyes, 9 cm frame")],
        [("photo-close", "close-up photo"), ("before-close", "before: cheek and nose, 6 cm frame"),
         ("after-close", "after: cheek and nose, 6 cm frame")]]


def cropped(photo, middle, size):
    """The photo cropped to `size` (width, height; pixels) round `middle` (column, row)."""
    half = np.asarray(size) / 2.0
    corners = (*(np.asarray(middle) - half), *(np.asarray(middle) + half))
    return photo.crop(tuple(int(round(value)) for value in corners))


def photo_crops(photo_path, stats, frames):
    """The photo cropped as each row's renders frame the head (`frames`, blender_skin.py's frames.json): the face
    (portrait, its middle under the pupils), the eyes (landscape, round the pupils) and the cheek and nose (landscape,
    round the close-up's point)."""
    photo = Image.open(photo_path).convert("RGB")
    scale = stats["photo_px_per_m"]
    pupils = np.mean(stats["photo_pupils_px"], axis=0)
    face, eyes, close = (frames[key] * scale for key in ("face", "eyes", "close"))
    wide = 1.0 / frames["portrait"]
    face_middle = pupils + [0.0, frames["face_drop"] * scale]
    return {"photo-face": cropped(photo, face_middle, (face * frames["portrait"], face)),
            "photo-eyes": cropped(photo, pupils, (eyes * wide, eyes)),
            "photo-close": cropped(photo, stats["close_photo_px"], (close * wide, close))}


def sheet(name, renders, photo_path, stats_path, out):
    """The sheet written to `out` (jpg) with its title line."""
    stats = json.loads(pathlib.Path(stats_path).read_text())
    typeface = eyes_sheet.font()
    frames = json.loads((pathlib.Path(renders) / "frames.json").read_text())
    pictures = photo_crops(photo_path, stats, frames)
    pictures.update({key: Image.open(pathlib.Path(renders) / f"{key}.png").convert("RGB")
                     for row in ROWS for key, _ in row if not key.startswith("photo")})
    rows = [eyes_sheet.row_image([(pictures[key], label) for key, label in row], typeface) for row in ROWS]
    title = (f"{name}: TRELLIS.2 head with real eyes; after: the face re-painted from the close-up photo (4K, "
             f"{stats['texture_mm_per_px']} mm a pixel, registered at detail correlation "
             f"{stats['detail_correlation_before']} -> {stats['detail_correlation_after']}, its light flattened) in "
             f"score_lib's skin (random-walk skin light, oil coat, scanned pores, glossier T-zone)")
    width = max(row.width for row in rows)
    page = Image.new("RGB", (width, eyes_sheet.LABEL + sum(row.height + eyes_sheet.GAP for row in rows)), "white")
    ImageDraw.Draw(page).text((6, 8), title, fill="black", font=typeface)
    top = eyes_sheet.LABEL
    for row in rows:
        page.paste(row, (0, top))
        top += row.height + eyes_sheet.GAP
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    page.save(out, quality=90)
    return out


if __name__ == "__main__":
    print(f"sheet: {sheet(*sys.argv[1:6])}")
