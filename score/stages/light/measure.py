"""The light stage's measures on pictures (sRGB PNG, 0 to 255): each fault the stage fixes, measured the same way on
the place's look, on its look with the judged lamps off where a lamp's light is judged, and on its concept, never
judged by eye.

    where(view, size, point) -> (x, y, depth, focal)   usd_views.py's camera: eye, aim, up, fov across the picture
    head(picture, x, y, radius)    a floodlight's head: its halo and how far the gaps between its lamps fill
    beam(before, after, points)    how much a lamp's beam brightens the air along its axis, after against before
    body(picture, x, y, radius, toward, usable)   a sky body's disc: how much of it shows, its sunward and far halves
    sky_of(picture, sky_pixels(picture))   a day sky's colour and its rise toward the horizon
    veil(before, after)            how much lighter the picture's lower part got: lamps' haze laid over the whole place
"""
import math

import numpy as np
from PIL import Image

# The sky's pixels in the frame before: the top share of the picture, within this many levels of its commonest colour.
SKY_ROWS = 0.45
SKY_NEAR = 14


def picture(path):
    """A picture's luminance-ready RGB as floats."""
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)


def lightness(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def where(view, size, point):
    """Where a point of the stage falls in a view's picture: (x, y) in pixels, its depth along the view and the
    camera's focal length in pixels."""
    eye, aim, up = (np.asarray(view[key], dtype=np.float64) for key in ("eye", "aim", "up"))
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    upward = np.cross(right, forward)
    offset = np.asarray(point, dtype=np.float64) - eye
    depth = float(offset @ forward)
    focal = size[0] / 2 / math.tan(math.radians(view["fov"]) / 2)
    if depth <= 0:
        return None, None, depth, focal
    return size[0] / 2 + focal * (offset @ right) / depth, size[1] / 2 - focal * (offset @ upward) / depth, depth, focal


def ring(shape, x, y, inner, outer):
    """The pixels between two radii round (x, y)."""
    rows, columns = np.mgrid[0:shape[0], 0:shape[1]]
    distance = np.hypot(columns - x, rows - y)
    return (distance >= inner) & (distance < outer)


def head(rgb, x, y, radius):
    """A floodlight head of `radius` pixels (half its bank's width) at (x, y): `halo`, how much brighter the air just
    round the bank is than the air further out (0 to 1 of white), and `fill`, the darkest tenth of the bank's square
    against its brightest tenth (a grid of lit panes in a dark frame is low; lamps that glow into each other high),
    and `peak`, its brightest pixel (0 to 1): a lamp seen from behind shows no lit face at all."""
    light = lightness(rgb)
    near = ring(light.shape, x, y, radius * 1.3, radius * 2.5)
    far = ring(light.shape, x, y, radius * 4.0, radius * 5.0)
    if near.sum() < 20 or far.sum() < 20:
        return None
    low, high = int(max(0, y - radius * 0.8)), int(min(light.shape[0], y + radius * 0.8))
    left, right = int(max(0, x - radius * 0.8)), int(min(light.shape[1], x + radius * 0.8))
    bank = light[low:high, left:right]
    if bank.size < 9:
        return None
    return {"halo": round(float((light[near].mean() - light[far].mean()) / 255.0), 4),
            "fill": round(float(np.percentile(bank, 10) / max(np.percentile(bank, 90), 1.0)), 4),
            "peak": round(float(bank.max() / 255.0), 4), "radius_px": round(float(radius), 1)}


# The picture's lower share, where the place's ground and people are, for the veil.
VEIL_ROWS = 0.4


def veil(before, after):
    """How much lighter (0 to 1 of white) the lower VEIL_ROWS of the picture is after than before: a lamp's haze
    meant to show round the lamp, laid over the whole place instead, washes it out."""
    low = int(before.shape[0] * (1.0 - VEIL_ROWS))
    return round(float((lightness(after[low:]).mean() - lightness(before[low:]).mean()) / 255.0), 4)


def beam(before, after, points, radius):
    """How much brighter the air is after than before (0 to 1 of white) round points along a lamp's axis."""
    gains = []
    for x, y in points:
        inside = ring(before.shape[:2], x, y, 0.0, radius)
        if inside.sum() >= 9:
            gains.append(float((lightness(after)[inside] - lightness(before)[inside]).mean() / 255.0))
    return round(float(np.mean(gains)), 4) if gains else None


# A sky body's pixel shows it when it stands this many levels (0 to 255) off the sky just round its disc.
SHOWN_LEVELS = 8.0


def body(rgb, x, y, radius, toward, usable):
    """A sky body's disc of `radius` pixels at (x, y), on its `usable` pixels (a mask: those the place's lamps do not
    light): `shown`, the share standing SHOWN_LEVELS off the median of the ring just outside it, and the mean
    lightness of the half its sun lights (`sunward`, the side `toward` points to in the picture) and the other
    (`away`), each None where that half has no pixel; None when the disc has under 9 usable pixels."""
    rows, columns = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]]
    distance = np.hypot(columns - x, rows - y)
    inside = (distance < radius * 0.92) & usable
    if inside.sum() < 9:
        return None
    light = lightness(rgb)
    around = (distance >= radius * 1.1) & (distance < radius * 1.6)
    background = float(np.median(light[around])) if around.any() else 0.0
    side = (columns - x) * toward[0] + (rows - y) * toward[1]
    halves = {name: inside & part for name, part in (("sunward", side > 0), ("away", side < 0))}
    shown = float((np.abs(light[inside] - background) > SHOWN_LEVELS).mean())
    return {"px": int(inside.sum()), "shown": round(shown, 4),
            **{name: round(float(light[mask].mean()), 2) if mask.any() else None for name, mask in halves.items()}}


def sky_pixels(before):
    """The sky's pixels: the picture's top SKY_ROWS within SKY_NEAR levels of the commonest colour there."""
    top = before[: int(before.shape[0] * SKY_ROWS)]
    codes = (top.astype(np.int64) // 4) @ np.array([4096, 64, 1])
    common = np.bincount(codes.ravel()).argmax()
    colour = np.array([common // 4096, (common // 64) % 64, common % 64]) * 4 + 2
    near = np.abs(top - colour).max(axis=-1) <= SKY_NEAR
    mask = np.zeros(before.shape[:2], dtype=bool)
    mask[: top.shape[0]] = near
    return mask


def sky_of(rgb, mask):
    """A sky's mean colour on its pixels, and how much lighter its lowest tenth of rows is than its highest tenth."""
    rows = np.nonzero(mask.any(axis=1))[0]
    if len(rows) < 10 or mask.sum() < 500:
        return None
    tenth = max(1, len(rows) // 10)
    high, low = mask.copy(), mask.copy()
    high[rows[tenth]:] = False
    low[: rows[-tenth]] = False
    light = lightness(rgb)
    return {"mean_rgb": [round(float(value), 1) for value in rgb[mask].mean(axis=0)],
            "rise_to_horizon": round(float((light[low].mean() - light[high].mean()) / 255.0), 4),
            "blue_to_red": round(float(rgb[mask][:, 2].mean() / max(rgb[mask][:, 0].mean(), 1.0)), 4)}


def colour_gap(first, second):
    """The mean of the three channels' differences, in levels."""
    return round(float(np.abs(np.subtract(first, second)).mean()), 1)
