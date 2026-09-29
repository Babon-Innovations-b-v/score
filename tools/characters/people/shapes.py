"""Small clean shapes for the outfits' hard parts, built as numbers rather than generated.

Every builder works in the body's frame: y up, +z the body's front, +x its left. Those returning a
trimesh.Trimesh return it closed and wound outward.
"""
import numpy as np
import trimesh


def _outward(mesh):
    """Merge coincident points and wind every triangle outward."""
    mesh = trimesh.Trimesh(mesh.vertices, mesh.faces, process=True)
    trimesh.repair.fix_normals(mesh)
    return mesh


def _grid(count):
    """count+1 values over [-1, 1], closer together near the ends so rounded edges get points."""
    return np.sin(np.linspace(-1.0, 1.0, count + 1) * np.pi / 2)


def rounded_box(half, radius, count=10):
    """A box with rounded edges and corners, centred at the origin, axis aligned."""
    half = np.asarray(half, dtype=float)
    steps = _grid(count)
    vertices, faces = [], []
    for axis in range(3):
        others = [other for other in range(3) if other != axis]
        for sign in (-1.0, 1.0):
            first, second = np.meshgrid(steps, steps, indexing="ij")
            patch = np.zeros((count + 1, count + 1, 3))
            patch[..., axis] = sign
            patch[..., others[0]] = first
            patch[..., others[1]] = second
            base = sum(len(block) for block in vertices)
            vertices.append(patch.reshape(-1, 3))
            index = np.arange((count + 1) ** 2).reshape(count + 1, count + 1) + base
            corner = index[:-1, :-1].ravel()
            right = index[1:, :-1].ravel()
            up = index[:-1, 1:].ravel()
            both = index[1:, 1:].ravel()
            faces += [np.stack([corner, right, both], 1), np.stack([corner, both, up], 1)]
    cube = np.concatenate(vertices) * half
    inner = np.clip(cube, -(half - radius), half - radius)
    offset = cube - inner
    length = np.linalg.norm(offset, axis=1, keepdims=True)
    points = inner + radius * offset / np.maximum(length, 1e-12)
    return _outward(trimesh.Trimesh(points, np.concatenate(faces), process=False))


def placed(mesh, origin, axes):
    """A copy of `mesh` with its local x, y, z along the columns of `axes`, moved to `origin`."""
    points = mesh.vertices @ np.asarray(axes, dtype=float).T + origin
    return _outward(trimesh.Trimesh(points, mesh.faces.copy(), process=False))


def frame(first, second):
    """Right-handed axes (as columns): `first` exactly, `second` made square to it."""
    first = np.asarray(first, dtype=float)
    first = first / np.linalg.norm(first)
    second = np.asarray(second, dtype=float) - first * np.dot(second, first)
    second /= np.linalg.norm(second)
    return np.stack([first, second, np.cross(first, second)], axis=1)


def loft(origin, across, up_axis, radii, profile, count=48):
    """A closed ring swept round an ellipse.

    `across` and the axis square to it and to `up_axis` carry the ellipse's two radii; `profile`
    is a function of the angle giving a closed polygon of (outward from the ellipse, along
    `up_axis`) offsets, the same number of points at every angle.
    """
    up_axis = np.asarray(up_axis, dtype=float) / np.linalg.norm(up_axis)
    across = np.asarray(across, dtype=float) - up_axis * np.dot(across, up_axis)
    across /= np.linalg.norm(across)
    other = np.cross(up_axis, across)
    angles = np.linspace(0.0, 2 * np.pi, count, endpoint=False)
    rings = []
    for angle in angles:
        shape = np.asarray(profile(angle), dtype=float)
        cosine, sine = np.cos(angle), np.sin(angle)
        rings.append(origin + np.outer(radii[0] + shape[:, 0], across * cosine)
                     + np.outer(radii[1] + shape[:, 0], other * sine)
                     + np.outer(shape[:, 1], up_axis))
    points = np.concatenate(rings)
    size = len(rings[0])
    faces = []
    for step in range(count):
        following = (step + 1) % count
        for corner in range(size):
            nxt = (corner + 1) % size
            here, there = step * size, following * size
            faces.append([here + corner, there + corner, there + nxt])
            faces.append([here + corner, there + nxt, here + nxt])
    return _outward(trimesh.Trimesh(points, np.array(faces), process=False))


def rounded_rectangle(inside, outside, low, high, corner):
    """A closed profile for `loft`: a rectangle from `inside` to `outside` (outward) and `low`
    to `high` (along the axis), its four corners cut round by `corner`."""
    points = []
    centres = [(outside - corner, high - corner), (inside + corner, high - corner),
               (inside + corner, low + corner), (outside - corner, low + corner)]
    starts = [0.0, 0.5 * np.pi, np.pi, 1.5 * np.pi]
    for (across, along), start in zip(centres, starts):
        for step in np.linspace(start, start + 0.5 * np.pi, 3):
            points.append((across + corner * np.cos(step), along + corner * np.sin(step)))
    return np.array(points)


def circle(radius, count=10):
    """A closed circular profile for `loft`."""
    angles = np.linspace(0.0, 2 * np.pi, count, endpoint=False)
    return np.stack([radius * np.cos(angles), radius * np.sin(angles)], axis=1)


def spherical_cap(centre, radius, axis, half_angle, rings=9, count=40):
    """The part of a sphere within `half_angle` of `axis`: an open, single surface."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    helper = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    first = np.cross(axis, helper)
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)
    points = [centre + axis * radius]
    for ring in range(1, rings + 1):
        polar = half_angle * ring / rings
        for step in range(count):
            around = 2 * np.pi * step / count
            direction = (axis * np.cos(polar)
                         + np.sin(polar) * (first * np.cos(around) + second * np.sin(around)))
            points.append(centre + direction * radius)
    faces = [[0, 1 + step, 1 + (step + 1) % count] for step in range(count)]
    for ring in range(1, rings):
        inner, outer = 1 + (ring - 1) * count, 1 + ring * count
        for step in range(count):
            nxt = (step + 1) % count
            faces.append([inner + step, outer + step, outer + nxt])
            faces.append([inner + step, outer + nxt, inner + nxt])
    mesh = trimesh.Trimesh(np.array(points), np.array(faces), process=False)
    if np.dot(mesh.face_normals.mean(axis=0), axis) < 0:
        mesh.invert()
    return mesh


def joined(meshes):
    """Several closed pieces as one mesh (they may overlap; nothing is cut)."""
    return trimesh.util.concatenate(list(meshes))


def ring_band(angles, centre, rings, closed):
    """A thick band round a vertical axis at `centre`: `rings` lists (radius, height) per angle,
    inner rings bottom to top then outer rings top to bottom; each ring is joined to the next and
    the last to the first. An open band (`closed` false) gets its two ends capped. Points, faces."""
    points = []
    for radius, height in rings:
        height = np.broadcast_to(height, angles.shape)
        points.append(np.stack([centre[0] + radius * np.sin(angles), height,
                                centre[2] + radius * np.cos(angles)], axis=1))
    points = np.concatenate(points)
    count, layers = len(angles), len(rings)
    faces = []
    spans = count if closed else count - 1
    for layer in range(layers):
        following = (layer + 1) % layers
        for index in range(spans):
            other = (index + 1) % count
            faces += [[layer * count + index, layer * count + other, following * count + other],
                      [layer * count + index, following * count + other, following * count + index]]
    if not closed:
        for end in (0, count - 1):
            cap = [layer * count + end for layer in range(layers)]
            for index in range(1, layers - 1):
                faces.append([cap[0], cap[index], cap[index + 1]] if end
                             else [cap[0], cap[index + 1], cap[index]])
    return points, np.array(faces)


def _rectangle(width, height):
    return np.array([[-width / 2, -height / 2], [width / 2, -height / 2],
                     [width / 2, height / 2], [-width / 2, height / 2]])


def picture_frame(outer, inner, bevel, thickness):
    """A rectangular frame with its front edges chamfered: back face at z=0, front at
    z=thickness. Points, faces."""
    layers = [
        np.column_stack([_rectangle(*outer), np.zeros(4)]),
        np.column_stack([_rectangle(*outer), np.full(4, thickness - bevel)]),
        np.column_stack([_rectangle(outer[0] - 2 * bevel, outer[1] - 2 * bevel), np.full(4, thickness)]),
        np.column_stack([_rectangle(inner[0] + 2 * bevel, inner[1] + 2 * bevel), np.full(4, thickness)]),
        np.column_stack([_rectangle(*inner), np.full(4, thickness - bevel)]),
        np.column_stack([_rectangle(*inner), np.zeros(4)]),
    ]
    points = np.concatenate(layers)
    faces = []
    for layer in range(6):
        following = (layer + 1) % 6
        for corner in range(4):
            other = (corner + 1) % 4
            faces += [[layer * 4 + corner, layer * 4 + other, following * 4 + other],
                      [layer * 4 + corner, following * 4 + other, following * 4 + corner]]
    return points, np.array(faces)


def square_box(size, centre):
    """An axis-aligned box of `size` round `centre`, with sharp corners. Points, faces."""
    corners = np.array([[x_side, y_side, z_side] for x_side in (-0.5, 0.5)
                        for y_side in (-0.5, 0.5) for z_side in (-0.5, 0.5)])
    faces = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                      [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return corners * size + centre, faces
