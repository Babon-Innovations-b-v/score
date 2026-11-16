"""A made model's own paint graded toward its place's palette (owner 2026-11-16: one shared material library a place,
"if u take a bunch of random scans, everything will look very inconsistent"): the colours its surface shows are
gathered into a few groups (k-means in CIELAB over points spread evenly on the surface, so each group weighs by the area
it paints); each group moves GRADE of the way to its nearest palette token, every texel by its groups' soft shares, so
the paint's own detail (its wear, its print, its shading) stays and only its colours come into the place's family.
A group of at least MISMATCH_SHARE of the surface still further than MISMATCH_DELTA from every token is a mismatch:
its prop is repainted from the library (`surface`), never graded harder.

    graded(rgb, samples, tokens) -> (graded rgb, [{"share", "from", "token", "delta_e", ...}])
"""
import numpy as np
from scipy.cluster.vq import kmeans2

GROUPS = 6
GRADE = 0.6
SOFTNESS = 8.0  # delta E: how widely a texel shares between its nearest groups (no seams between groups)
MISMATCH_SHARE = 0.15
MISMATCH_DELTA = 30.0
WHITE = np.array([0.95047, 1.0, 1.08883])  # D65
TO_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                   [0.0193339, 0.1191920, 0.9503041]])


def linear(srgb):
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def encoded(light):
    light = np.clip(light, 0.0, 1.0)
    return np.where(light <= 0.0031308, light * 12.92, 1.055 * light ** (1 / 2.4) - 0.055)


def lab(srgb):
    """sRGB in 0..1 (..., 3) as CIELAB (..., 3)."""
    xyz = (linear(srgb) @ TO_XYZ.T) / WHITE
    curve = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * curve[..., 1] - 16, 500 * (curve[..., 0] - curve[..., 1]),
                     200 * (curve[..., 1] - curve[..., 2])], -1)


def srgb(colours):
    """CIELAB (..., 3) as sRGB in 0..1."""
    middle = (colours[..., 0] + 16) / 116
    curve = np.stack([middle + colours[..., 1] / 500, middle, middle - colours[..., 2] / 200], -1)
    xyz = np.where(curve ** 3 > 216 / 24389, curve ** 3, (116 * curve - 16) / (24389 / 27)) * WHITE
    return encoded(xyz @ np.linalg.inv(TO_XYZ).T)


def hex_lab(text):
    text = text.lstrip("#")
    return lab(np.array([int(text[at:at + 2], 16) / 255 for at in (0, 2, 4)]))


def groups(samples):
    """The surface's colour groups: their centres (CIELAB) and each one's share of the samples."""
    count = min(GROUPS, len(np.unique(np.round(samples), axis=0)))
    centres, owner = kmeans2(samples, count, minit="++", seed=7)
    shares = np.bincount(owner, minlength=count) / len(samples)
    kept = shares > 0
    return centres[kept], shares[kept]


def graded(rgb, samples, tokens):
    """`rgb` (h, w, 3 in 0..1, the base colour picture) graded toward `tokens` ({name: "#rrggbb"}); `samples` the
    picture's colours at points spread evenly over the surface (n, 3 in 0..1). The graded picture and each group's
    move."""
    names = sorted(tokens)
    palette = np.array([hex_lab(tokens[name]) for name in names])
    centres, shares = groups(lab(samples))
    gaps = np.linalg.norm(centres[:, None] - palette[None], axis=-1)
    nearest = gaps.argmin(1)
    moves = GRADE * (palette[nearest] - centres)
    colours = lab(rgb.reshape(-1, 3))
    weights = np.exp(-(np.linalg.norm(colours[:, None] - centres[None], axis=-1) / SOFTNESS) ** 2)
    weights /= np.maximum(weights.sum(1, keepdims=True), 1e-12)
    # a texel far from every group (none of the surface shows it: the atlas' padding) moves with its nearest one
    far = weights.sum(1) == 0
    weights[far, np.linalg.norm(colours[far, None] - centres[None], axis=-1).argmin(1)] = 1.0
    moved = srgb(colours + weights @ moves).reshape(rgb.shape)
    report = [{"share": round(float(share), 3), "from": "#" + "".join(f"{round(value * 255):02x}" for value in
                                                                         srgb(centre)),
               "token": names[index], "delta_e": round(float(gaps[number, index]), 1),
               "mismatch": bool(share >= MISMATCH_SHARE and gaps[number, index] > MISMATCH_DELTA)}
              for number, (centre, share, index) in enumerate(zip(centres, shares, nearest))]
    return moved, sorted(report, key=lambda group: -group["share"])
