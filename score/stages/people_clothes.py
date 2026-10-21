"""What a person row of a picked design wears (owner, 2026-10-13: the concept decides the clothes), read off the design
alone in the people rows' refresh (people_rows.refreshed_place): of the library's fabrics, those whose name
shares a word with the row's name as read (words_of), the nearest by CIE76 dE to the row's measured
torso, used only within WITHIN of it. The torso is measured on the locked concept: each figure's torso (rows 30-60%
and columns 30-70% of its SAM 3 box), its median colour, and the median over the row's figures. Lightness never
chooses on its own: the concepts are dim, warm-lit rooms, so only a fabric the words name is a candidate.

    {"words", "named": [fabric, ...], "torso_lab": [L, a, b] | null, "figures", "surface": fabric | null,
     "de": dE | null, "why"}

A row whose words name no fabric, or whose named fabrics all lie further than WITHIN from its torso, wears its look's
own paint (`surface` null, `why` says which); a fabric is never added to the library here (a library edit re-keys
every place's paint).
"""
import re
import sys

import numpy as np

from score.stages import people_rows

# The furthest a named fabric may lie from the measured torso and still be worn (CIE76 dE; the rule of 2026-10-13).
WITHIN = 32.0
TORSO_ROWS = (0.30, 0.60)
TORSO_COLUMNS = (0.30, 0.70)


def labels():
    """tools/props/library/labels.py (the library's colour conversions)."""
    folder = str(people_rows.REPO / "tools/props/library")
    if folder not in sys.path:
        sys.path.append(folder)
    import labels as found
    return found


def fabrics():
    """{fabric: its CIELAB} of every library fabric, each in its own token (the people place's own list of materials
    in place.json was retired, 2026-10-21)."""
    found = labels()
    import library
    return {name: [float(value) for value in found.lab(found.srgb(np.array(spec["colour"], dtype=float))[None])[0]]
            for name, spec in library.by_library(people_rows.LINE).items() if spec.get("family") == "fabric"}


def words_of(row):
    """The row's name as read, lower case, word by word. Its `where` is left out: it names a spot, not the clothes
    (the wreck's "standing near centre light" named suit_light_blue)."""
    return set(re.findall(r"[a-z]+", (row.get("name") or "").lower()))


def named(row, lab_of):
    """The fabrics whose name shares a word with the row's words."""
    words = words_of(row)
    return sorted(name for name in lab_of if words & set(name.split("_")))


def torso(picture, box):
    """The median sRGB (0..1) of one figure's torso in the concept (`picture` H x W x 3, 0..255), or None when the
    box holds no pixel there."""
    left, top, right, bottom = box
    rows = slice(int(top + TORSO_ROWS[0] * (bottom - top)), int(top + TORSO_ROWS[1] * (bottom - top)))
    columns = slice(int(left + TORSO_COLUMNS[0] * (right - left)), int(left + TORSO_COLUMNS[1] * (right - left)))
    pixels = picture[rows, columns].reshape(-1, 3)
    return np.median(pixels, axis=0) / 255.0 if len(pixels) else None


def torso_lab(row, picture):
    """(the median CIELAB over the row's figures' torsos, how many figures) or (None, 0) with no box or picture."""
    boxes = row.get("boxes") or ([row["box"]] if row.get("box") else [])
    figures = [found for found in (torso(picture, box) for box in boxes) if found is not None] \
        if picture is not None else []
    if not figures:
        return None, 0
    return [round(float(value), 1) for value in np.median(labels().lab(np.array(figures)), axis=0)], len(figures)


def worn(row, picture, lab_of):
    """The row's dress record (the module's docstring) from its words, its boxes and the concept (`picture` H x W x 3,
    0..255, or None when the store keeps none); `lab_of` {fabric: CIELAB}."""
    candidates = named(row, lab_of)
    measured, figures = torso_lab(row, picture)
    record = {"words": row.get("name") or "", "named": candidates, "torso_lab": measured, "figures": figures, "surface": None,
              "de": None}
    if not candidates:
        return {**record, "why": "the words name no library fabric of the people place: the look's own paint"}
    if measured is None:
        return {**record, "why": "no torso measured (no SAM 3 box or no concept picture): the look's own paint"}
    distances = {name: float(np.linalg.norm(np.array(lab_of[name]) - measured)) for name in candidates}
    nearest = min(distances, key=distances.get)
    if distances[nearest] > WITHIN:
        return {**record, "de": round(distances[nearest], 1),
                "why": f"{nearest}, the nearest fabric the words name, lies dE {distances[nearest]:.1f} from the "
                       f"torso, over {WITHIN:g}: the look's own paint"}
    return {**record, "surface": nearest, "de": round(distances[nearest], 1),
            "why": f"the words name {', '.join(candidates)}; {nearest} the nearest to the torso"}
