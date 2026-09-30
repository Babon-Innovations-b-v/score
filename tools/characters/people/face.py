"""The face's own parts, laid on the head: solid brows and dark iris discs.

The drawing's brows are thick, straight and dark, angled down toward the nose. Each is laid out
in a front view as a tapered strip (the inner end lower and thicker), cast back onto the skin and
built as a slab: its top BROW_PROUD off the skin, its rim bevelled down to under half that, walls
running SINK into the skin so no gap shows. An iris is a disc cast onto the eye (the MakeHuman
eye, CC0, seated on this head and kept in the look), IRIS_PROUD off it, with the same walls.
The mouth and the nose are lines painted on the skin (`paint.py`), not parts.
"""
import fit
import numpy as np
import trimesh
from person import WHO

# The brow strip in a front view, on his left (x > 0); the right is mirrored. Along the brow:
# x, the strip's centre height, its full height.
BROW = np.array([[0.011, 1.6570, 0.0100],
                 [0.022, 1.6590, 0.0098],
                 [0.034, 1.6610, 0.0088],
                 [0.045, 1.6620, 0.0072],
                 [0.054, 1.6615, 0.0050]])
# Moved onto this head, and each brow's height scaled by BROW_WEIGHT (the look's, 1 for take C).
BROW = np.column_stack([fit.head_xy(BROW[:, :2]), BROW[:, 2] * fit.head_scale()[1] * WHO["brow_weight"]])
# Raised by the look's `brow_lift` (m): above a glasses rim, and higher on the women (#112).
BROW[:, 1] += WHO["brow_lift"]
BROW_STEPS, BROW_ACROSS = 12, 5
BROW_PROUD = 0.0022
BROW_RIM_SHARE = 0.45
EYE_CENTRES = fit.head_xy(np.array([[0.031, 1.6485], [-0.031, 1.6485]]))
IRIS_RADIUS = 0.0044
IRIS_PROUD = 0.0006
IRIS_RINGS, IRIS_SPOKES = 4, 16
SINK = 0.001


def cast_front(mesh, front_view):
    """Where rays straight back along -z through each (x, y) first meet the mesh, with the
    face's normal there turned to face the front."""
    origins = np.column_stack([front_view, np.full(len(front_view), 0.5)])
    directions = np.tile([0.0, 0.0, -1.0], (len(front_view), 1))
    locations, ray, face = mesh.ray.intersects_location(origins, directions, multiple_hits=True)
    hits = np.full((len(front_view), 3), np.nan)
    normals = np.full((len(front_view), 3), np.nan)
    for location, index, triangle in zip(locations, ray, face):
        if np.isnan(hits[index, 2]) or location[2] > hits[index, 2]:
            hits[index] = location
            normals[index] = mesh.face_normals[triangle]
    if np.isnan(hits).any():
        raise SystemExit(f"{int(np.isnan(hits).any(axis=1).sum())} face rays missed")
    normals[normals[:, 2] < 0] *= -1
    return hits, normals


def facing_the_front(points, faces):
    """The shell with its triangles turned, if need be, so that on the whole they face the front
    (+z), which is the side anyone sees. It is not closed where its walls sink into the skin, so
    trimesh's repair alone can leave it inside out, as it did the right brow."""
    shell = trimesh.Trimesh(points, np.array(faces), process=False)
    trimesh.repair.fix_normals(shell)
    if (shell.face_normals[:, 2] * shell.area_faces).sum() < 0:
        shell.invert()
    return np.asarray(shell.vertices), np.asarray(shell.faces)


def slab(mesh, front_view, rows, columns):
    """A brow slab over a rows x columns grid of front-view points."""
    hits, normals = cast_front(mesh, front_view)
    height = np.full(rows * columns, BROW_PROUD)
    ring = np.zeros((rows, columns), dtype=bool)
    ring[[0, -1], :] = True
    ring[:, [0, -1]] = True
    height[ring.ravel()] = BROW_PROUD * BROW_RIM_SHARE
    points = np.vstack([hits + normals * height[:, None], hits - normals * SINK])
    faces = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            corner = row * columns + column
            faces += [[corner, corner + 1, corner + columns + 1],
                      [corner, corner + columns + 1, corner + columns]]
    rim = ([column for column in range(columns)]
           + [row * columns + columns - 1 for row in range(1, rows)]
           + [(rows - 1) * columns + column for column in range(columns - 2, -1, -1)]
           + [row * columns for row in range(rows - 2, 0, -1)])
    offset = rows * columns
    for index in range(len(rim)):
        here, there = rim[index], rim[(index + 1) % len(rim)]
        faces += [[here, there + offset, there], [here, here + offset, there + offset]]
    return facing_the_front(points, faces)


def brow_grid(side):
    """One brow's strip as front-view points, rows across the brow, columns along it."""
    along = np.linspace(BROW[0, 0], BROW[-1, 0], BROW_STEPS)
    centre = np.interp(along, BROW[:, 0], BROW[:, 1])
    height = np.interp(along, BROW[:, 0], BROW[:, 2])
    across = np.linspace(-0.5, 0.5, BROW_ACROSS)
    grid = np.array([[x_along * side, middle + tall * share] for share in across
                     for x_along, middle, tall in zip(along, centre, height)])
    return grid, BROW_ACROSS, BROW_STEPS


def disc(mesh, centre):
    """An iris: a fan of rings, its top IRIS_PROUD off the eye, walls down into it."""
    grid = np.array([[centre[0] + radius * np.cos(angle), centre[1] + radius * np.sin(angle)]
                     for radius in np.linspace(0.0005, IRIS_RADIUS, IRIS_RINGS)
                     for angle in np.linspace(0, 2 * np.pi, IRIS_SPOKES, endpoint=False)])
    rings, spokes = IRIS_RINGS, IRIS_SPOKES
    hits, normals = cast_front(mesh, grid)
    middle_hit, middle_normal = cast_front(mesh, np.array([centre]))
    top = np.vstack([middle_hit + middle_normal * IRIS_PROUD, hits + normals * IRIS_PROUD])
    base = hits[-spokes:] - normals[-spokes:] * SINK
    faces = [[0, 1 + spoke, 1 + (spoke + 1) % spokes] for spoke in range(spokes)]
    for ring in range(rings - 1):
        for spoke in range(spokes):
            inner = 1 + ring * spokes + spoke
            beside = 1 + ring * spokes + (spoke + 1) % spokes
            faces += [[inner, inner + spokes, beside + spokes], [inner, beside + spokes, beside]]
    outer = 1 + (rings - 1) * spokes
    low = 1 + rings * spokes
    for spoke in range(spokes):
        here, there = outer + spoke, outer + (spoke + 1) % spokes
        faces += [[here, low + spoke, low + (spoke + 1) % spokes],
                  [here, low + (spoke + 1) % spokes, there]]
    return facing_the_front(np.vstack([top, base]), faces)


def joined(pieces):
    points, faces, count = [], [], 0
    for piece_points, piece_faces in pieces:
        points.append(piece_points)
        faces.append(piece_faces + count)
        count += len(piece_points)
    return np.vstack(points), np.vstack(faces)


# Lips pressed shut for a painted mouth (#112): the head's points round the mouth, in take C's
# head measures moved with the eyes (half width, drop under the eyes from and to, how far in from
# the front of the face), are smoothed this many rounds, fading out towards the box's edge.
LIPS = (0.030, 0.052, 0.094, 0.030)
LIPS_ROUNDS = 8


def lips_shut(points, faces):
    """The head's points with the crease between the lips smoothed away: a fitted head's mouth is
    a little open, and its outline drawn round the lips read as a second, grim mouth beside the
    painted line."""
    eye = fit.eye(1.0)
    scale = fit.head_scale()
    across = np.abs(points[:, 0]) / scale[0]
    drop = (eye[1] - points[:, 1]) / scale[1]
    half, top, bottom, depth = LIPS
    inside = (across < half) & (drop > top) & (drop < bottom) & (points[:, 2] > eye[2] - depth)
    middle = (top + bottom) / 2
    fade = np.clip(1.0 - np.maximum(across / half, np.abs(drop - middle) / ((bottom - top) / 2)), 0.0, 1.0)
    weight = np.where(inside, np.clip(fade * 2.0, 0.0, 1.0), 0.0)[:, None]
    mesh = trimesh.Trimesh(points, faces, process=False)
    smoothed = trimesh.smoothing.filter_laplacian(mesh.copy(), lamb=0.6, iterations=LIPS_ROUNDS,
                                                volume_constraint=False).vertices
    return points * (1.0 - weight) + np.asarray(smoothed) * weight


def the_head_surface(head_points, head_faces, eye_points, eye_faces):
    return trimesh.Trimesh(np.vstack([head_points, eye_points]),
                           np.vstack([head_faces, eye_faces + len(head_points)]), process=False)


def brows(surface):
    """Both brows as one mesh: points, faces."""
    return joined([slab(surface, *brow_grid(side)) for side in (1.0, -1.0)])


def irises(surface):
    """Both irises as one mesh: points, faces."""
    return joined([disc(surface, centre) for centre in EYE_CENTRES])


# Thin round glasses (#112, Nev): two round rims before the eyes, a bridge arched over the nose
# and two arms back to the ears, each a thin tube, all rigid on the head. Measured on the head:
# the rims stand RIM_CLEAR in front of the face under them.
RIM_RADIUS = 0.0172
RIM_TUBE = 0.0011
RIM_CLEAR = 0.006
RIM_LIFT = 0.001
ARM_TUBE = 0.0010
TUBE_SIDES = 8


def tube(path, radius, closed=False):
    """A round tube along a polyline of points: points, faces."""
    path = np.asarray(path, dtype=float)
    count = len(path)
    tangents = np.gradient(path, axis=0) if not closed else (np.roll(path, -1, 0) - np.roll(path, 1, 0))
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    helper = np.array([0.0, 1.0, 0.0])
    rings = []
    for point, tangent in zip(path, tangents):
        side = np.cross(tangent, helper)
        if np.linalg.norm(side) < 1e-6:
            side = np.cross(tangent, [1.0, 0.0, 0.0])
        side /= np.linalg.norm(side)
        up = np.cross(side, tangent)
        angles = np.linspace(0, 2 * np.pi, TUBE_SIDES, endpoint=False)
        rings.append(point + radius * (np.outer(np.cos(angles), side) + np.outer(np.sin(angles), up)))
    points = np.vstack(rings)
    faces = []
    for ring in range(count if closed else count - 1):
        following = (ring + 1) % count
        for step in range(TUBE_SIDES):
            here, beside = ring * TUBE_SIDES + step, ring * TUBE_SIDES + (step + 1) % TUBE_SIDES
            ahead_beside = following * TUBE_SIDES + (step + 1) % TUBE_SIDES
            ahead = following * TUBE_SIDES + step
            faces += [[here, beside, ahead_beside], [here, ahead_beside, ahead]]
    if not closed:
        for end, flip in ((0, True), (count - 1, False)):
            centre = len(points)
            points = np.vstack([points, path[end]])
            for step in range(TUBE_SIDES):
                here, beside = end * TUBE_SIDES + step, end * TUBE_SIDES + (step + 1) % TUBE_SIDES
                faces.append([centre, beside, here] if flip else [centre, here, beside])
    mesh = trimesh.Trimesh(points, np.array(faces), process=False)
    trimesh.repair.fix_normals(mesh)
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def front_depth(surface, front_view):
    hits, _ = cast_front(surface, np.asarray(front_view))
    return hits[:, 2]


def glasses(surface):
    """Both rims, the bridge and the arms, as one mesh: points, faces."""
    radius = RIM_RADIUS * fit.head_scale()[0]
    angles = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    pieces = []
    rim_z = []
    for centre in EYE_CENTRES:
        ring = np.column_stack([centre[0] + radius * np.cos(angles), centre[1] + RIM_LIFT + radius * np.sin(angles)])
        inside = np.column_stack([centre[0] + 0.7 * radius * np.cos(angles), centre[1] + 0.7 * radius * np.sin(angles)])
        depth = max(front_depth(surface, ring).max(), front_depth(surface, inside).max()) + RIM_CLEAR
        rim_z.append(depth)
        pieces.append(tube(np.column_stack([ring, np.full(len(ring), depth)]), RIM_TUBE, closed=True))
    depth = max(rim_z)
    left, right = EYE_CENTRES[0], EYE_CENTRES[1]
    height = (left[1] + right[1]) / 2 + RIM_LIFT + 0.25 * radius
    inner = left[0] - radius
    bridge_x = np.linspace(-inner, inner, 9)
    arch = height + 0.004 * np.cos(bridge_x / inner * np.pi / 2)
    bridge_z = np.maximum(front_depth(surface, np.column_stack([bridge_x, arch])) + 0.004, depth - 0.004)
    pieces.append(tube(np.column_stack([bridge_x, arch, bridge_z]), RIM_TUBE))
    points = surface.vertices
    band = points[np.abs(points[:, 1] - height) < 0.012]
    ear_z = fit.THEIRS["Head"][2] - 0.012
    for centre, side in ((left, 1.0), (right, -1.0)):
        start = np.array([centre[0] + side * radius, centre[1] + RIM_LIFT + 0.3 * radius, rim_z[0] if side > 0 else rim_z[1]])
        near = band[np.abs(band[:, 2] - (start[2] - 0.03)) < 0.02]
        wide = np.abs(near[:, 0]).max() + 0.005
        back = band[np.abs(band[:, 2] - ear_z) < 0.015]
        wide_back = np.abs(back[:, 0]).max() + 0.004
        path = [start,
                [side * (wide - 0.002), start[1], start[2] - 0.012],
                [side * wide, start[1] - 0.001, start[2] - 0.03],
                [side * wide_back, start[1] - 0.004, ear_z + 0.01],
                [side * (wide_back - 0.003), start[1] - 0.016, ear_z - 0.012]]
        pieces.append(tube(np.array(path), ARM_TUBE))
    return joined(pieces)
