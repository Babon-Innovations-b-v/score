"""One person's lids sheet (#223): the close-up photo's eyes, then the generated head before its lids, lashes and
brows are made (`blender_eyes.py`'s "after" pictures) and after (`blender_lids.py`'s): the eyes in a 9 cm frame, the
face from the front and from three quarters, beside the photo.

    python -m tools.characters.generated.lids_sheet <name> <before renders> <after renders> <close-up photo> \
        <eyes stats.json> <lids stats.json> <out.jpg>
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw

from tools.characters.generated import eyes_sheet

ROWS = [[("photo", "close-up photo (the reference)"), ("before-eyes", "before: eyes, 9 cm frame"),
         ("after-eyes", "after: eyes, 9 cm frame")],
        [("photo-face", "close-up photo"), ("before-face", "before: face"), ("after-face", "after: face"),
         ("before-three_quarter", "before: three quarters"), ("after-three_quarter", "after: three quarters")]]


def pictures_of(before, after, photo_path, eye_stats):
    """The sheet's pictures by key: the photo's eyes and whole, the renders before and after."""
    pictures = {"photo": eyes_sheet.photo_eyes(photo_path, eye_stats),
                "photo-face": Image.open(photo_path).convert("RGB")}
    for key in ("eyes", "face", "three_quarter"):
        pictures[f"before-{key}"] = Image.open(pathlib.Path(before) / f"after-{key}.png").convert("RGB")
        pictures[f"after-{key}"] = Image.open(pathlib.Path(after) / f"after-{key}.png").convert("RGB")
    return pictures


def sheet(name, before, after, photo_path, eye_stats_path, lid_stats_path, out):
    """The sheet written to `out` (jpg) with its title line."""
    eye_stats = json.loads(pathlib.Path(eye_stats_path).read_text())
    lid_stats = json.loads(pathlib.Path(lid_stats_path).read_text())
    typeface = eyes_sheet.font()
    pictures = pictures_of(before, after, photo_path, eye_stats)
    rows = [eyes_sheet.row_image([(pictures[key], label) for key, label in row], typeface) for row in ROWS]
    tall = lid_stats["opening_height_mm"]
    title = (f"{name}: lids reshaped to the photo's opening (tall {tall['model']} -> {tall['photo']} mm), thin "
             f"margins, {lid_stats['lashes']} strand lashes, painted brows regrown as {lid_stats['brow_hairs']} "
             f"hairs (photo's brow), the eyeball eyes.py's")
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
    print(f"sheet: {sheet(*sys.argv[1:8])}")
