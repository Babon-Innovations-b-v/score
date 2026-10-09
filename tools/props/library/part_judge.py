"""Which library material each part of a generated model is, asked of a vision-language judge (job repaint,
2026-10-08: picked by colour, 60 of 86 rebaked models came out one material, the telephone all rubber and the lab
desk all bare steel, because most parts photograph as the same grey).

For each part the camera saw, labels.py `--ask <folder>` writes the clean close-up with that part outlined and the
rest dimmed (<folder>/<take>-part<NN>.png) and a question naming the object and the kind's allowed materials; the
questions of every take go to ../cloud/judge.py (Qwen3.8-27B, open, on a rented card, seeded sampling) in one run;
labels.py `--answers <folder>` then paints each part with the material the judge named. The picture's colour picks
only where the judge gave no usable answer. No model runs here: numpy and the picture.
"""
import colorsys
import json
import pathlib
import re

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
LIBRARY = HERE.parents[2] / "data/library/materials.json"
QUESTIONS = "questions.json"
# The outline's colour and width (pixels), and how dark the rest of the picture is drawn.
OUTLINE = (255, 0, 200)
OUTLINE_WIDTH = 4
DIM = 0.35
# A part's pixels: its seen faces' pixels, closed over gaps of this many pixels (the faces are points in the picture).
CLOSE_PIXELS = 6

QUESTION = """You help paint a 3D model of an object made from this picture.
The object: {object}.
In the picture one part of the object (or several pieces with the same finish) is outlined in magenta; everything
outside it is dimmed.
Decide what that outlined part is (for example a seat cushion, a metal frame, a handset, a cord, a drawer front),
then which one of these materials it is made of:
{materials}
Choose by what the part is and how such a part is made, not only by its colour in the picture.

After your thinking, answer with one JSON object and nothing after it:
{{"part": "what the outlined part is, in a few words", "material": "one code from the list, such as M1"}}"""


def colour_words(linear):
    """A colour (linear RGB) in plain words: "dark brown", "light grey", "white" (the judge reads words better than
    numbers; two vinyls of one family differ only by colour, and the chair's brown seat was named the blue one)."""
    red, green, blue = [value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055 for value in linear]
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    if lightness > 0.9:
        return "white"
    if lightness < 0.08:
        return "black"
    shade = "dark " if lightness < 0.3 else "light " if lightness > 0.65 else ""
    if saturation < 0.15:
        return shade + "grey"
    names = ((0.04, "red"), (0.11, "orange"), (0.18, "yellow"), (0.45, "green"), (0.72, "blue"), (0.92, "purple"),
             (1.01, "red"))
    name = next(word for limit, word in names if hue < limit)
    if name in ("orange", "red") and lightness < 0.4:
        name = "brown"
    if name == "yellow" and saturation < 0.5:
        name = "gold"
    return shade + name


def code(index):
    """The code a material goes by in a question: M1, M2, ..."""
    return f"M{index + 1}"


def material_lines(materials):
    """Each allowed material as a line for the question: its code, what its library family is and its colour here
    (`materials`: name to the place's spec). The library's own names are left out: the judge named a brown seat
    "vinyl_seat" (dark blue) over "vinyl_brown" for the word seat (job repaint, 2026-10-08)."""
    families = json.loads(LIBRARY.read_text())["families"]
    family_of = {variant: entry for entry in families.values() for variant in entry["variants"]}
    lines = []
    for index, (name, spec) in enumerate(materials.items()):
        about = family_of.get(name, {}).get("is", name.replace("_", " ")).split(":")[0].strip()
        colour = f", {colour_words(spec['colour'])}" if "colour" in spec else ""
        lines.append(f"- {code(index)}: {about}{colour}")
    return "\n".join(lines)


def question(object_words, materials):
    return QUESTION.format(object=object_words, materials=material_lines(materials))


def part_pixels(part_of, seen, row, column, shape):
    """Each pixel's part (-1 where no seen face lands): the part of the seen face on it."""
    height, width = shape
    found = np.full(height * width, -1)
    found[row[seen] * width + column[seen]] = part_of[seen]
    return found.reshape(height, width)


def outlined(picture, mask):
    """The picture with `mask` kept bright and outlined, the rest dimmed (RGB)."""
    rgb = np.asarray(picture.convert("RGBA"), dtype=np.float64)
    alpha = rgb[..., 3:] / 255
    rgb = rgb[..., :3] * alpha + 255 * (1 - alpha)  # the cut-out on white, as the picture was made
    kept = ndimage.binary_closing(mask, iterations=CLOSE_PIXELS)
    shown = np.where(kept[..., None], rgb, rgb * DIM + 255 * (1 - DIM) * 0.5)
    edge = ndimage.binary_dilation(kept, iterations=OUTLINE_WIDTH) & ~kept
    shown[edge] = OUTLINE
    return Image.fromarray(shown.clip(0, 255).astype(np.uint8))


def write_questions(folder, take, picture, pixels, parts, object_words, materials):
    """The outlined picture of each part in `parts` and its question, added to <folder>/questions.json (a take's
    old questions replaced); the question names."""
    folder.mkdir(parents=True, exist_ok=True)
    listing = folder / QUESTIONS
    jobs = [job for job in (json.loads(listing.read_text()) if listing.exists() else [])
            if not job["name"].startswith(f"{take}-part")]
    asked = []
    for part in parts:
        name = f"{take}-part{part:02d}"
        outlined(picture, pixels == part).save(folder / f"{name}.png")
        jobs.append({"name": name, "text": question(object_words, materials), "images": [str(folder / f"{name}.png")]})
        asked.append(name)
    listing.write_text(json.dumps(jobs, indent=1))
    return asked


def answer_of(text):
    """The judge's JSON answer from its whole reply (the last object in it), or None when it gave none."""
    found = None
    for match in re.finditer(r"\{[^{}]*\}", text, flags=re.S):
        try:
            found = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    return found


def judged(folder, take, count, names):
    """Each part's material as the judge answered it ({part: (material, what the part is)}), for the parts whose
    answer gives the code of one of `names` (in the order the question listed them)."""
    found = {}
    for part in range(count):
        path = pathlib.Path(folder) / f"{take}-part{part:02d}.txt"
        answer = answer_of(path.read_text()) if path.exists() else None
        codes = {code(index): name for index, name in enumerate(names)}
        if answer and str(answer.get("material", "")).strip().upper() in codes:
            found[part] = (codes[str(answer["material"]).strip().upper()], str(answer.get("part", "")))
    return found
