"""What every painter shares: a part's picture is painted texel by texel from where that texel sits
on the model.

Each texel is traced back to its triangle, and the point and the normal there decide its colour.
No picture is stretched onto the model, so an edge between two colours lands exactly where the
rule puts it, however the part was unwrapped.
"""
import io

import numpy as np
from PIL import Image
from scipy import ndimage

# Pictures are painted at this many times their saved size across, then averaged down, so an
# edge between two colours is smooth rather than a stair.
SUPERSAMPLE = 2


def smooth_normals(points, faces):
    """Area-weighted point normals."""
    corner = points[faces]
    face_normal = np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0])
    normals = np.zeros_like(points)
    for column in range(3):
        np.add.at(normals, faces[:, column], face_normal)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(length, 1e-12)


def split_on_seams(faces, corner_uv):
    """One point for each (point, texture coordinate) pair: the new faces, each new point's
    source point, and its texture coordinate."""
    keys = np.concatenate([faces.reshape(-1, 1).astype(np.float64),
                           np.round(corner_uv.reshape(-1, 2), 6)], axis=1)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    return inverse.reshape(-1, 3), unique[:, 0].astype(np.int64), unique[:, 1:]


def rasterise(uv, faces, size):
    """For a size x size picture (row 0 at the top, v running up): each texel's triangle (-1 off
    the part) and its three barycentric weights."""
    owner = np.full((size, size), -1, dtype=np.int64)
    shares = np.zeros((size, size, 3))
    pixel = np.stack([uv[:, 0] * size - 0.5, (1.0 - uv[:, 1]) * size - 0.5], axis=1)
    for index, corners_of in enumerate(faces):
        corners = pixel[corners_of]
        low = np.clip(np.floor(corners.min(axis=0)).astype(int), 0, size - 1)
        high = np.clip(np.ceil(corners.max(axis=0)).astype(int), 0, size - 1)
        columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
        spots = np.stack([columns.ravel(), rows.ravel()], axis=1).astype(np.float64)
        first, second = corners[1] - corners[0], corners[2] - corners[0]
        area = first[0] * second[1] - first[1] * second[0]
        if abs(area) < 1e-12:
            continue
        offset = spots - corners[0]
        share_one = (offset[:, 0] * second[1] - offset[:, 1] * second[0]) / area
        share_two = (first[0] * offset[:, 1] - first[1] * offset[:, 0]) / area
        share_zero = 1.0 - share_one - share_two
        inside = (share_zero >= -1e-6) & (share_one >= -1e-6) & (share_two >= -1e-6)
        texel_rows, texel_columns = spots[inside, 1].astype(int), spots[inside, 0].astype(int)
        owner[texel_rows, texel_columns] = index
        shares[texel_rows, texel_columns] = np.stack(
            [share_zero[inside], share_one[inside], share_two[inside]], axis=1)
    return owner, shares


def at_texels(values, faces, owner, shares):
    """A per-point quantity interpolated to every texel on the part (zeros off it)."""
    on = owner >= 0
    out = np.zeros(owner.shape + values.shape[1:])
    triangle = faces[owner[on]]
    weights = shares[on]
    out[on] = sum(values[triangle[:, corner]] * (weights[:, corner:corner + 1] if values.ndim > 1
                                                 else weights[:, corner])
                  for corner in range(3))
    return out


def bleed(picture, on, rounds=16):
    """The painted colours spread out past each island's edge, so filtering never reaches the
    empty space between islands."""
    picture = picture.astype(np.float64).copy()
    filled = on.copy()
    for _ in range(rounds):
        grown = ndimage.binary_dilation(filled) & ~filled
        if not grown.any():
            break
        total = np.zeros_like(picture)
        count = np.zeros(filled.shape)
        for row_step in (-1, 0, 1):
            for column_step in (-1, 0, 1):
                total += np.roll(np.roll(picture * filled[..., None], row_step, 0), column_step, 1)
                count += np.roll(np.roll(filled.astype(float), row_step, 0), column_step, 1)
        picture[grown] = total[grown] / np.maximum(count[grown], 1)[:, None]
        filled |= grown
    return picture


def finished(picture, on):
    """The supersampled picture bled past its islands, then averaged down to its saved size, as
    bytes (0 to 255)."""
    picture = bleed(picture, on)
    size = picture.shape[0] // SUPERSAMPLE
    picture = picture.reshape(size, SUPERSAMPLE, size, SUPERSAMPLE, 3).mean(axis=(1, 3))
    return np.clip(np.round(picture), 0, 255).astype(np.uint8)


def flat_picture(colour, size=8):
    """A small picture in one colour, for a part painted all over alike."""
    return np.tile(np.array(colour, dtype=np.uint8), (size, size, 1))


def png_bytes(picture):
    """A picture as the PNG bytes that go in the body file."""
    out = io.BytesIO()
    Image.fromarray(picture).save(out, format="PNG")
    return out.getvalue()
