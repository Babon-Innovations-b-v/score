"""Which library material each part of a generated model is, asked of a vision-language judge (job repaint,
2026-10-08: picked by colour, 60 of 86 rebaked models came out one material, the telephone all rubber and the lab
desk all bare steel, because most parts photograph as the same grey).

For each part the camera saw, labels.py `--ask <folder>` writes the clean close-up with that part outlined and the
rest dimmed (<folder>/<take>-part<NN>.png) and a question naming the object and the kind's allowed materials; the
questions of every take go to ../cloud/judge.py (Qwen3.8-27B, open, on a rented card, seeded sampling) in one run;
labels.py `--answers <folder>` then paints each part with the material the judge named. The picture's colour picks
only where the judge gave no usable answer. No model runs here: numpy and the picture.
"""
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
In the picture one part of the object is outlined in magenta; everything outside that part is dimmed.
Decide what that outlined part is (for example a seat cushion, a metal frame, a handset, a cord, a drawer front),
then which one of these materials it is made of:
{materials}
Choose by what the part is and how such a part is made, not only by its colour in the picture.

After your thinking, answer with one JSON object and nothing after it:
{{"part": "what the outlined part is, in a few words", "material": "one name from the list"}}"""


def material_lines(names):
    """Each allowed material as a line for the question: its name and what its library family is."""
    families = json.loads(LIBRARY.read_text())["families"]
    family_of = {variant: entry for entry in families.values() for variant in entry["variants"]}
    lines = []
    for name in names:
        about = family_of.get(name, {}).get("is", "")
        lines.append(f"- {name}: {about.split(':')[0].strip()}" if about else f"- {name}")
    return "\n".join(lines)


def question(object_words, names):
    return QUESTION.format(object=object_words, materials=material_lines(names))


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


def write_questions(folder, take, picture, pixels, parts, object_words, names):
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
        jobs.append({"name": name, "text": question(object_words, names), "images": [str(folder / f"{name}.png")]})
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
    answer names one of `names`."""
    found = {}
    for part in range(count):
        path = pathlib.Path(folder) / f"{take}-part{part:02d}.txt"
        answer = answer_of(path.read_text()) if path.exists() else None
        if answer and answer.get("material") in names:
            found[part] = (answer["material"], str(answer.get("part", "")))
    return found
