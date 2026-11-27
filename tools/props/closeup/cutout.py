"""A drawn close-up cut out of its plain ground: a matting model's soft alpha made into a clean cut-out, with no model
here (the alpha comes from whichever matte ran: BiRefNet-general on the 2099 prologue, 2026-11-27).

A matte alone fails a close-up three ways (the prologue's 36 close-up gaps, 2026-11-27): it tears holes in the pale
parts of a pale object on a pale ground, it keeps the green of a green ground seen through glass, and it leaves
specks and a green fringe. So the cut-out here:

- fits the drawn ground's own colour at every pixel (`fitted_ground`: the sure-ground pixels spread by a wide blur, so
  the ground's vignette and glow are followed), and puts back the textured pixels near the matte's object that differ
  from it (an edge the matte tore off a pale part);
- fills every hole inside the object's outer outline, except a hole that is the ground seen through a gap: as smooth
  as the ground and near its colour there, or one the matte is sure is ground and near its colour;
- on a green ground takes a pixel near the ground's green inside the outline as a gap, and neutralises the green left
  on the object (spill on a rim; seen through tinted glass);
- for a glazed object (`glazed`) keeps every hole inside the outline as a pane, coloured a neutral glass grey (its
  finish is the library's glass recipe later), since clear glass drawn on a plain ground shows only that ground;
- drops parts smaller than SPECK of the largest.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

EDGE = 10              # px: textured pixels this near the matte's object may join it
KEY = 22.0             # RGB distance from the fitted ground beyond which a textured pixel is object
SMOOTH = 1.3           # grey standard deviation over 3 x 3 below which a pixel is as smooth as the drawn ground
GAP_NEAR = 22.0        # a smooth pixel this near the fitted ground is ground-like
GAP_AREA = 60          # px: a hole smaller than this is never a gap
GAP_SHARE = 0.6        # a hole is a gap when this share of its inside is ground-like ...
SURE_GAP = 0.05        # ... or when the matte's median alpha over it is under this,
SURE_GAP_NEAR = 45.0   # its median distance from the fitted ground under this,
SURE_GAP_SMOOTH = 2.5  # and its median 3 x 3 grey deviation under this
SPECK = 0.02           # a part smaller than this share of the largest is a speck
GREEN_LEAD = 40        # on a green ground a pixel whose green leads red and blue by this much is green
GREEN_NEAR = 70.0      # and green this near the fitted ground's green is the ground itself
GLASS = np.array([150.0, 162.0, 168.0])  # a pane's neutral glass grey
SURE_RING = 25         # px round the matte's object that are never taken as sure ground
GROUND_STEP = 4        # the ground is fitted on every GROUND_STEP-th pixel
GROUND_BLUR = 12       # the fit's blur, in those steps (48 px)
NO_GLASS = ("no glass", "not glazed", "unglazed")


def glazed(material, what):
    """A row whose holes are glass panes: its material is glass, or its words name glass or glazing and do not deny it."""
    words = f"{material} {what}".lower()
    return ("glass" in material.lower() or "glaz" in words or "glass" in words) and not any(
        denial in words for denial in NO_GLASS)


def spread(values, weight, blur):
    """`values` (H x W x 3, zero where unknown) spread over the picture by a normalised blur of width `blur`."""
    summed = np.stack([ndimage.gaussian_filter(values[..., channel], blur, mode="nearest") for channel in range(3)], -1)
    return summed, ndimage.gaussian_filter(weight, blur, mode="nearest")


def fitted_ground(pixels, sure):
    """The drawn ground's colour at every pixel, from the sure-ground pixels; wider blurs fill what lies far from any."""
    height, width = sure.shape
    weight = sure[::GROUND_STEP, ::GROUND_STEP].astype(np.float32)
    values = pixels[::GROUND_STEP, ::GROUND_STEP] * weight[..., None]
    blur = GROUND_BLUR
    summed, norm = spread(values, weight, blur)
    known = norm > 1e-3
    while not known.all() and blur < 64 * GROUND_BLUR:
        blur *= 2
        wide_summed, wide_norm = spread(values, weight, blur)
        fill = ~known & (wide_norm > 1e-6)
        summed[fill], norm[fill] = wide_summed[fill], wide_norm[fill]
        known |= fill
    ground = summed / np.maximum(norm, 1e-9)[..., None]
    return np.kron(ground, np.ones((GROUND_STEP, GROUND_STEP, 1)))[:height, :width]


def texture(pixels):
    """The grey standard deviation over each pixel's 3 x 3 neighbourhood."""
    grey = pixels.mean(axis=2)
    return np.sqrt(np.maximum(ndimage.uniform_filter(grey ** 2, 3) - ndimage.uniform_filter(grey, 3) ** 2, 0))


def without_specks(mask):
    """`mask` with its parts smaller than SPECK of the largest dropped."""
    labels, count = ndimage.label(mask)
    if count <= 1:
        return mask
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    return np.isin(labels, np.flatnonzero(sizes >= SPECK * sizes.max()) + 1)


def is_gap(part, ground_like, soft, distance, local):
    """Whether one hole inside the outline (`part`, a mask over its bounding region's arrays) is ground seen through."""
    inner = ndimage.binary_erosion(part, iterations=1)
    inside = inner if inner.sum() >= 20 else part
    if ground_like[inside].mean() >= GAP_SHARE:
        return True
    return (np.median(soft[part]) < SURE_GAP and np.median(distance[part]) < SURE_GAP_NEAR
            and np.median(local[part]) < SURE_GAP_SMOOTH)


def opened(solid, candidates, ground_like, soft, distance, local):
    """`solid` with every hole among `candidates` that is a gap made clear."""
    out = solid.copy()
    labels, _ = ndimage.label(candidates)
    for index, region in enumerate(ndimage.find_objects(labels), start=1):
        part = labels[region] == index
        if part.sum() >= GAP_AREA and is_gap(part, ground_like[region], soft[region], distance[region], local[region]):
            out[region][part] = False
    return out


def green_gaps_opened(solid, ground_like):
    """`solid` with every large patch of the ground's own green inside it made clear."""
    labels, count = ndimage.label(solid & ground_like)
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
    return solid & ~np.isin(labels, np.flatnonzero(sizes >= GAP_AREA) + 1)


def recoloured(pixels, solid, ground_like, green, glass):
    """The object's colours: green spill neutralised (towards glass grey where it is green through glass) on a green
    ground; a glazed object's ground-like panes glass grey on a plain one."""
    rgb = pixels.copy()
    if green:
        lead = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
        rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]) + 4)
        share = np.clip(lead / 180.0, 0, 1)[..., None]
        rgb = rgb * (1 - share) + GLASS * share
    elif glass:
        share = (ground_like & solid)[..., None].astype(np.float32)
        rgb = rgb * (1 - share) + GLASS * share
    return rgb.clip(0, 255).astype(np.uint8)


def cut(picture, soft, ground="white", glass=False):
    """The close-up `picture` (drawn on a plain `ground`: "white" for light grey, or "green") cut out as RGBA, from the
    matte's soft alpha `soft` (0..1, the picture's size); `glass` for a glazed object (`glazed`)."""
    pixels = np.asarray(picture.convert("RGB"), dtype=np.float32)
    green = ground == "green"
    sure = ~ndimage.binary_dilation(soft > 0.5, iterations=SURE_RING) & (soft < 0.05)
    distance = np.linalg.norm(pixels - fitted_ground(pixels, sure), axis=2)
    local = texture(pixels)
    if green:
        lead = pixels[..., 1] - np.maximum(pixels[..., 0], pixels[..., 2])
        ground_like = (distance < GREEN_NEAR) & (lead > GREEN_LEAD)
        keyed = lead <= GREEN_LEAD
    else:
        ground_like = (local < SMOOTH) & (distance < GAP_NEAR)
        keyed = (distance > KEY) & (local >= SMOOTH)
    body = soft > 0.5
    body |= ndimage.binary_dilation(body, iterations=EDGE) & keyed
    body = without_specks(ndimage.binary_closing(body, iterations=2))
    solid = ndimage.binary_fill_holes(body)
    if not glass:
        candidates = solid & ((soft < 0.5) | ground_like) if green else solid & (soft < 0.5)
        solid = opened(solid, candidates, ground_like, soft, distance, local)
        if green:
            solid = green_gaps_opened(solid, ground_like)
    solid = without_specks(ndimage.binary_opening(solid, iterations=1))
    alpha = ndimage.gaussian_filter(solid.astype(np.float32), 0.8)
    rgb = recoloured(pixels, solid, ground_like, green, glass)
    return Image.fromarray(np.dstack([rgb, (alpha * 255).round().astype(np.uint8)]), "RGBA")
