"""The paint of the faces cloth.py paints over (`cloth.painted_over`: the body's own old hair round a swapped head's
neck, now the collar's, the hood's or the neck's), in plain numpy (importable without Blender;
`blender_cloth.painted_over` runs it on the shell). The faces keep their own texture places; their own texels are
painted again, each with the garment's paint at the nearest point of its kind's surface not painted over (that
triangle's texture place there, read bilinearly), so the garment's paint runs on across them texel by texel.

One donor face's flat paint per face drew b_hoodie_man's hood inside as light and dark shards (2026-11-28: 22658 of
its 51378 pixels in the front close-up); each corner its own nearest donor's texture place streaked it across the
atlas' seams; each corner laid on the nearest surface of one island per face read the charts' dark edges (the atlas
holds 43698 islands over 342k faces: the stairwell woman's collar top drew at light 0.24 against the jacket's 0.48).
Only donor paint clear of them and like the kind's own is read (`CLEAR_M`, `kind_like`): the old hair's triangles are
finer than its texels, so the collar's own texels round it hold the hair's dark: read as they are, the stairwell
woman's sage collar top took paint at a median 0.27 sRGB against the collar's 0.45.
"""
import numpy as np

LIKE_SPREADS = 3.0  # a donor's paint further than this many of its kind's spreads from the kind's median is not read
SPREAD_LEAST = 0.03  # the spread (sRGB, 0 to 1) is never read tighter than this
CLEAR_M = 0.01  # a donor triangle's middle this near the faces painted over wears their paint too: never read
TEXEL_REACH = 1.0  # texels painted round a triangle (a bilinear read reaches one texel out)


def barycentric(points, triangles):
    """Each point's weights on its triangle's three corners (the point on or near it; clamped inside, summing to 1;
    a degenerate triangle's a third each)."""
    first, second, along = (triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0],
                            points - triangles[:, 0])
    d00, d01, d11 = (np.einsum("nd,nd->n", *pair) for pair in ((first, first), (first, second), (second, second)))
    d20, d21 = np.einsum("nd,nd->n", along, first), np.einsum("nd,nd->n", along, second)
    denominator = d00 * d11 - d01 * d01
    flat = np.abs(denominator) < 1e-30
    safe = np.where(flat, 1.0, denominator)
    second_weight, third_weight = (d11 * d20 - d01 * d21) / safe, (d00 * d21 - d01 * d20) / safe
    weights = np.clip(np.column_stack([1.0 - second_weight - third_weight, second_weight, third_weight]), 0.0, None)
    weights = weights / np.maximum(weights.sum(1, keepdims=True), 1e-30)
    weights[flat] = 1.0 / 3.0
    return weights


def texels(places, size):
    """The texels a bilinear read of each triangle of texture places (n, 3, 2; u right, v up, 0 to 1) on a picture of
    `size` (width, height) takes paint from: those whose middles lie within TEXEL_REACH texels of it (most of the
    old hair's triangles are smaller than a texel: only those holding a texel's middle left 15675 faces with 20005
    texels, and the rest wore the old hair's paint round them); (rows from the bottom, columns, each one's triangle,
    its weights on the corners at the triangle's point nearest it)."""
    width, height = size
    pixels = places * np.array([width, height]) - 0.5
    found = [[], [], [], []]
    for number, corners in enumerate(pixels):
        low = np.floor(corners.min(0) - TEXEL_REACH).astype(int)
        high = np.ceil(corners.max(0) + TEXEL_REACH).astype(int)
        columns, rows = np.meshgrid(np.arange(max(low[0], 0), min(high[0], width - 1) + 1),
                                    np.arange(max(low[1], 0), min(high[1], height - 1) + 1))
        if not columns.size:
            continue
        middles = np.column_stack([columns.ravel(), rows.ravel()]).astype(float)
        weights = barycentric(middles, np.repeat(corners[None], len(middles), axis=0))
        near = np.linalg.norm(weights @ corners - middles, axis=1) <= TEXEL_REACH
        found[0].append(rows.ravel()[near])
        found[1].append(columns.ravel()[near])
        found[2].append(np.full(near.sum(), number))
        found[3].append(weights[near])
    if not found[0]:
        return np.zeros(0, int), np.zeros(0, int), np.zeros(0, int), np.zeros((0, 3))
    return tuple(np.concatenate(part) for part in found)


def bilinear(picture, places):
    """The picture (rows from the bottom) read bilinearly at texture places (u right, v up, 0 to 1), edges held."""
    height, width = picture.shape[:2]
    pixels = places * np.array([width, height]) - 0.5
    low = np.floor(pixels).astype(int)
    share = pixels - low
    found = 0.0
    for down, across in ((0, 0), (0, 1), (1, 0), (1, 1)):
        column = np.clip(low[:, 0] + across, 0, width - 1)
        row = np.clip(low[:, 1] + down, 0, height - 1)
        weight = (share[:, 0] if across else 1 - share[:, 0]) * (share[:, 1] if down else 1 - share[:, 1])
        found = found + picture[row, column] * weight[:, None]
    return found


def kind_like(paint):
    """Which paints (n, channels; the first three sRGB) lie within LIKE_SPREADS spreads of their median (the spread:
    the median distance from it, at least SPREAD_LEAST)."""
    distance = np.linalg.norm(paint[:, :3] - np.median(paint[:, :3], axis=0), axis=1)
    return distance <= LIKE_SPREADS * max(SPREAD_LEAST, float(np.median(distance)))


def repainted(picture, places, points, triangles, triangle_places, nearest, read):
    """`picture` (rows from the bottom, h x w x channels) with the texels of the faces at `places` (n, 3, 2) and
    `points` (n, 3, 3) painted with the donor surface's paint at their nearest points: `nearest(points)` gives
    (closest points, indices) on the donor `triangles` (m, 3, 3), whose corners' places are `triangle_places`
    (m, 3, 2), and `read(texture places, donor triangles)` their paint; (the picture, how many texels)."""
    rows, columns, face, weights = texels(places, (picture.shape[1], picture.shape[0]))
    if not len(rows):
        return picture, 0
    located, triangle = nearest(np.einsum("nc,ncd->nd", weights, points[face]))
    found = np.einsum("nc,nck->nk", barycentric(located, triangles[triangle]), triangle_places[triangle])
    painted = picture.copy()
    painted[rows, columns] = read(found, triangle)
    return painted, len(rows)
