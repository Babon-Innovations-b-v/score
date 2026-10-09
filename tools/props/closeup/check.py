"""The close-up shape check: whether a close-up may go to the 3D step, decided without a person.

Two halves. The measurements are cheap and run here on the picture alone: a plain background all round its
border (a room, a floor or a cut-off object breaks it), the object filling a sensible share of the frame, one
object rather than several, and its outline's proportions against the inventory row's box. The judge is a
vision-language model on a rented card (../cloud/judge.py, Qwen3.8-27B in FP8, Apache-2.0) that sees the concept's
crop beside the close-up and answers set questions: one object, a clean background, the whole object, the same
object as in the crop, parts missing or added, proportions. Each question is asked with three seeds and the majority decides. A close-up passes only when both halves pass.

The rule was tuned on the 40 close-ups of the open-model check (job openpics, 2026-10-08, four models on the
lab's ten objects, each scored by hand): a pass of a picture scored wrong costs a bad 3D model, a fail of a good
one only a Nano Banana Pro picture, so the rule leans to failing.
"""
import json
import math
import re

import numpy as np
from PIL import Image
from scipy import ndimage

# The judge's question. Image 1 is the concept's crop, image 2 the close-up.
QUESTION = """You check a picture made for a 3D model maker.
Image 1 is a crop of a concept painting of a room; the object to check is in it, among other things.
Image 2 is a new picture that should show that one object alone, clean, for a 3D model to be built from it.
The object: {words}.
Its size: {wide:.2f} m wide, {deep:.2f} m deep and {tall:.2f} m tall.

Image 2 passes only if a 3D model built from it would have the right shape. Look hard at image 2 and decide:
1. one_object: image 2 shows exactly one object: no second copy, no other objects (things standing on it, in
   front of it or beside it count as other objects).
2. clean: the background is plain and empty: no room, wall, floor, shelf, scenery or miniature scene, and nothing
   drawn beside the object: no dimension lines, arrows, measurements, captions or other text.
3. whole: the whole object is in the frame, nothing cut off by the edge.
4. same_object: it is the same object as in image 1, not a different kind of object or a generic one.
5. missing_parts: main parts the object has in image 1 that image 2 lacks (a jointed arm, a second unit, legs).
6. added_parts: parts image 2 adds that the object in image 1 does not have (for example armrests, dividers, a
   stand, a hood or top panel, extra boxes, objects standing on it). Stickers, labels, notes and wear do not count.
   Where image 1 and the words disagree about the shape, image 1 wins.
7. proportions: the object's proportions in image 2 match the size given (width : depth : height) within about a
   quarter, allowing for the view.

After your thinking, answer with one JSON object and nothing after it:
{{"one_object": true, "clean": true, "whole": true, "same_object": true, "missing_parts": [], "added_parts": [],
"proportions": true, "shape_score": 8, "verdict": "pass"}}
shape_score is 1 to 10, 10 meaning the same shape as the object in image 1; verdict is "pass" or "fail"."""

# The measurements' limits.
SIDE = 256                 # the picture is measured at this size
RING = 0.03                # the border ring, as a share of the side
NEAR = 18.0                # a pixel this close to the background colour (0-255 RGB distance) is background
FAR = 30.0                 # a pixel this far from it is object
BORDER_CLEAN = 0.75        # share of the ring that must be background (a long cast shadow may reach the edge)
SPECK = 0.01               # parts smaller than this share of the object are specks
FILL_MIN = 0.45            # the object's longer side, as a share of the frame's
ONE_PIECE = 0.7           # share of the object's pixels in its largest part (a dropped shadow apart from it is allowed)
PROPORTION_LIMIT = 0.5     # |ln(seen height:width / expected)| at most this
# The view the close-ups are drawn from: turned about 35 degrees, a little from above (the close-up wording).
TURN_DEGREES = 35.0
LOOK_DOWN_DEGREES = 15.0
# The judge is asked each question with these seeds, and a close-up passes its half when most answers pass: one
# answer alone gave a different verdict for the same picture between runs (the lab desk, 2026-10-08).
SEEDS = (7, 8, 9)
# The judge's limits: the shape score a pass needs, and the judge's own questions that must all be yes.
SCORE_MIN = 7
MUST_BE_TRUE = ("one_object", "clean", "whole", "same_object", "proportions")


def question(words, size):
    """The judge's question for one close-up, from its inventory row's words and size (wide, deep, tall)."""
    wide, deep, tall = size
    return QUESTION.format(words=words, wide=wide, deep=deep, tall=tall)


def answer_of(text):
    """The judge's JSON answer from its whole reply (the last object in it), or None when it gave none."""
    found = None
    for match in re.finditer(r"\{[^{}]*\}", text, flags=re.S):
        try:
            found = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    return found


def expected_proportion(size):
    """Height over width the object's outline should show from the close-up view, from its box."""
    wide, deep, tall = size
    turn, down = math.radians(TURN_DEGREES), math.radians(LOOK_DOWN_DEGREES)
    seen_wide = wide * math.cos(turn) + deep * math.sin(turn)
    seen_tall = tall * math.cos(down) + (wide * math.sin(turn) + deep * math.cos(turn)) * math.sin(down)
    return seen_tall / seen_wide


def background_fit(pixels, ring):
    """The background as a smooth surface fitted to the border ring (studio light falls off towards the corners),
    per pixel: a quadratic in x and y per colour channel, by least squares over the ring."""
    height, width = pixels.shape[:2]
    rows, columns = np.mgrid[0:height, 0:width]
    x, y = columns / width - 0.5, rows / height - 0.5
    terms = np.stack([np.ones_like(x), x, y, x * x, y * y, x * y], axis=-1)
    in_ring = np.zeros((height, width), dtype=bool)
    in_ring[:ring], in_ring[-ring:], in_ring[:, :ring], in_ring[:, -ring:] = True, True, True, True
    weights, *_ = np.linalg.lstsq(terms[in_ring], pixels[in_ring], rcond=None)
    return terms @ weights, in_ring


def object_mask(picture):
    """Per pixel, how far it is from the fitted background, and which pixels are the border ring."""
    pixels = np.asarray(picture, dtype=float)
    ring = max(1, round(RING * min(pixels.shape[:2])))
    background, in_ring = background_fit(pixels, ring)
    return np.linalg.norm(pixels - background, axis=2), in_ring


def measure(path, size):
    """The cheap measurements of one close-up: its border's cleanliness, the object's share of the frame, the share
    of it in one piece and how far its outline's proportions are from the row's box."""
    picture = Image.open(path).convert("RGB")
    picture.thumbnail((SIDE, SIDE))
    distance, in_ring = object_mask(picture)
    border_clean = float(np.mean(distance[in_ring] < NEAR))
    solid = ndimage.binary_closing(distance > FAR, iterations=2)
    labels, count = ndimage.label(solid)
    sizes = ndimage.sum(solid, labels, range(1, count + 1)) if count else np.array([])
    total = sizes.sum()
    kept = [index + 1 for index, area in enumerate(sizes) if area >= SPECK * total]
    if not kept:
        return {"border_clean": border_clean, "fill": 0.0, "one_piece": 0.0, "proportion_error": None}
    rows, columns = np.nonzero(np.isin(labels, kept))
    height, width = rows.max() - rows.min() + 1, columns.max() - columns.min() + 1
    seen = height / width
    return {"border_clean": border_clean,
            "fill": float(max(height / distance.shape[0], width / distance.shape[1])),
            "one_piece": float(max(sizes) / sum(sizes[index - 1] for index in kept)),
            "proportion_error": abs(math.log(seen / expected_proportion(size)))}


def measured_faults(measures):
    """What the measurements fault in a close-up, as short words; none when it passes them."""
    faults = []
    if measures["border_clean"] < BORDER_CLEAN:
        faults.append("background not plain to the edge")
    if measures["fill"] < FILL_MIN:
        faults.append("object small in the frame")
    if measures["one_piece"] < ONE_PIECE:
        faults.append("more than one object")
    if measures["proportion_error"] is None or measures["proportion_error"] > PROPORTION_LIMIT:
        faults.append("proportions off the row's box")
    return faults


def judged_faults(answer):
    """What the judge faults in a close-up, as short words; none when it passes it."""
    if answer is None:
        return ["the judge gave no answer"]
    faults = [f"judge: not {name.replace('_', ' ')}" for name in MUST_BE_TRUE if answer.get(name) is not True]
    faults += [f"judge: adds {part}" for part in answer.get("added_parts") or []]
    faults += [f"judge: lacks {part}" for part in answer.get("missing_parts") or []]
    if not isinstance(answer.get("shape_score"), (int, float)) or answer["shape_score"] < SCORE_MIN:
        faults.append(f"judge: shape score {answer.get('shape_score')}")
    if answer.get("verdict") != "pass":
        faults.append("judge: fail")
    return faults


def voted_faults(answers):
    """The judge's faults on a close-up asked several times: none when most of the answers pass it, else the faults of
    the first answer that failed it and how many passed."""
    failing = [found for found in (judged_faults(answer) for answer in answers) if found]
    if len(failing) * 2 < len(answers):
        return []
    return failing[0] + [f"judge: {len(answers) - len(failing)} of {len(answers)} answers passed"]


def faults(measures, answers):
    """Every fault the check finds in a close-up, from its measurements and the judge's answers; it passes when there
    are none."""
    return measured_faults(measures) + voted_faults(answers)
