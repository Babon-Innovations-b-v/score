"""The mesh arithmetic every measure stands on: welded corners, face areas and normals, points drawn on a surface."""
import numpy as np
import trimesh

WELD = 1e-6  # corners nearer than this share of the box's diagonal are one corner (a seam's split copies)


def diagonal(vertices):
    """The length of the points' box's diagonal."""
    return float(np.linalg.norm(vertices.max(0) - vertices.min(0)))


def welded(vertices, faces):
    """(corners, faces) with the corners at one place made one: a texture seam's copies are not an open edge."""
    step = max(diagonal(vertices), 1e-9) * WELD
    keys = np.round(vertices / step).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return vertices[first], inverse.reshape(-1)[faces]


def crossed(vertices, faces):
    """Each face's edge cross product: its normal times twice its area."""
    corners = vertices[faces]
    return np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])


def areas(vertices, faces):
    """Each face's area."""
    return np.linalg.norm(crossed(vertices, faces), axis=1) / 2


def normals(vertices, faces):
    """Each face's unit normal (zero for a face with no area)."""
    across = crossed(vertices, faces)
    length = np.linalg.norm(across, axis=1, keepdims=True)
    return np.divide(across, length, out=np.zeros_like(across), where=length > 0)


def sampled(vertices, faces, count, seed=0):
    """(points, the face each lies on): `count` points drawn on the surface by area, the same for the same seed."""
    weight = areas(vertices, faces)
    draw = np.random.default_rng(seed)
    picked = draw.choice(len(faces), count, p=weight / weight.sum())
    first, second = draw.random(count), draw.random(count)
    folded = first + second > 1
    first[folded], second[folded] = 1 - first[folded], 1 - second[folded]
    corners = vertices[faces[picked]]
    points = corners[:, 0] + first[:, None] * (corners[:, 1] - corners[:, 0]) \
        + second[:, None] * (corners[:, 2] - corners[:, 0])
    return points, picked


# Points drawn on the whole surface for each one kept on its outside: NVIDIA's fridge is about 80% inside surface.
OVERDRAW = 8
# A ray starts this share of the box's diagonal off its point, clear of the point's own face.
LIFT = 1e-4
WAYS_OUT = np.vstack([np.eye(3), -np.eye(3)])  # the six axis ways, besides the face's own normal either way


def outside(vertices, faces, count, seed=0):
    """Up to `count` points drawn on the surface that can be seen from outside it: a ray from the point along its
    face's normal (either way, so a face wound either way counts) or along an axis leaves the model without striking
    it. A closed cabinet's liner and shelves are not seen; an open rack's shelves are, along its open sides."""
    points, picked = sampled(vertices, faces, count * OVERDRAW, seed=seed)
    facing = normals(vertices, faces)[picked]
    rays = trimesh.Trimesh(vertices, faces, process=False).ray
    lift = diagonal(vertices) * LIFT
    seen = np.zeros(len(points), dtype=bool)
    for way in [facing, -facing] + [np.broadcast_to(axis, points.shape) for axis in WAYS_OUT]:
        open_ones = np.flatnonzero(~seen)
        if not len(open_ones):
            break
        struck = rays.intersects_any(points[open_ones] + way[open_ones] * lift, way[open_ones])
        seen[open_ones[~struck]] = True
    return points[seen][:count]


def moved(vertices, matrix):
    """The points under a 4x4 matrix (column vectors)."""
    return vertices @ matrix[:3, :3].T + matrix[:3, 3]
