"""The grain check: a rendered picture that ships is clean, not sparkling with specks (the owner, 2026-10-20: the
Library's Camp picture full of fireflies and grain, a light look mixed from the passes' noisy lamp groups).

    found = grain.specks(path)               # specks per mille of the picture's flat area, None with too little
    verdict = grain.verdict(name, paths)     # fail naming each grainy picture, else pass

Free and local (numpy, scipy, Pillow). A speck is a pixel more than SPECK_LEVELS of 255 off the median of its 3 x 3
neighbours; it is counted only on the flat area, where the picture's 5 x 5 median slopes less than FLAT_LEVELS a pixel
(edges, prints and fine shapes are left out), and a picture is grainy above GRAINY_PER_MILLE. The threshold is
picked, not measured against the owner's eye on a set of pictures, so every verdict says it is unmeasured.
"""
import pathlib

import numpy as np
from PIL import Image
from scipy import ndimage

from score import checks

SPECK_LEVELS = 6
FLAT_LEVELS = 2.0
LEAST_FLAT = 1000  # flat pixels needed to judge a picture at all
# Picked 2026-10-20 on the library's place, layer, character and algorithm pictures: the clean card renders (crops
# look 0.2, physics frame 1.1, effects look 1.3, film concept 1.5, terrain look 2.8 per mille: the launch's lit city and
# stars) under it, every light look the owner called grainy (camp 85) and the faint ones (greenhouse 4.8) over it.
GRAINY_PER_MILLE = 3.0
THRESHOLD = f"over {GRAINY_PER_MILLE:g} specks per mille of the flat area (threshold picked, unmeasured)"


def specks(path):
    """Specks per mille of the picture's flat area (its see-through pixels left out), or None when it has fewer than
    LEAST_FLAT flat pixels."""
    picture = Image.open(path)
    shown = np.asarray(picture.convert("RGBA"))[..., 3] > 0
    luminance = np.asarray(picture.convert("L"), dtype=np.float64)
    smooth = ndimage.median_filter(luminance, 5)
    slope = np.hypot(ndimage.sobel(smooth, 0), ndimage.sobel(smooth, 1)) / 8.0
    flat = ndimage.binary_erosion((slope < FLAT_LEVELS) & shown, iterations=2)
    if flat.sum() < LEAST_FLAT:
        return None
    off = np.abs(luminance - ndimage.median_filter(luminance, 3))
    return float((off[flat] > SPECK_LEVELS).mean() * 1000.0)


def verdict(name, paths, root=None):
    """The check `name` over the pictures: fail naming each grainy one (its path from `root`), else pass; unknown
    with no picture to judge."""
    paths = sorted(paths)
    measured = {path: specks(path) for path in paths}
    judged = {path: found for path, found in measured.items() if found is not None}
    if not judged:
        return checks.Verdict(name, checks.UNKNOWN, f"no picture with a flat area to judge ({len(paths)} found)")
    shown = {path: pathlib.Path(path).relative_to(root) if root else pathlib.Path(path).name for path in judged}
    grainy = tuple(f"grainy picture {shown[path]}: {found:.1f} specks per mille" for path, found in judged.items()
                   if found > GRAINY_PER_MILLE)
    worst = max(judged.values())
    measures = {"grainy": len(grainy), "pictures": len(judged), "worst_per_mille": round(worst, 2)}
    better = {"grainy": "lower", "worst_per_mille": "lower"}
    if grainy:
        return checks.Verdict(name, checks.FAIL, f"{len(grainy)} of {len(judged)} {THRESHOLD}: "
                              + "; ".join(grainy[:3]), measures, better, grainy)
    return checks.Verdict(name, checks.PASS, f"{len(judged)} clean, worst {worst:.1f} specks per mille "
                                             f"({THRESHOLD.removeprefix('over ')})", measures, better)
