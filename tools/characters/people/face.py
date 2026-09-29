"""The face's own parts, laid on the head: solid brows and dark iris discs.

The drawing's brows are thick, straight and dark, angled down toward the nose. Each is laid out
in a front view as a tapered strip (the inner end lower and thicker), cast back onto the skin and
built as a slab: its top BROW_PROUD off the skin, its rim bevelled down to under half that, walls
running SINK into the skin so no gap shows. An iris is a disc cast onto the eye (the MakeHuman
eye, CC0, seated on this head and kept in the look), IRIS_PROUD off it, with the same walls.
The mouth and the nose are lines painted on the skin (`paint.py`), not parts.
"""
import numpy as np
import trimesh

# The brow strip in a front view, on his left (x > 0); the right is mirrored. Along the brow:
# x, the strip's centre height, its full height.
BROW = np.array([[0.011, 1.6570, 0.0100],
                 [0.022, 1.6590, 0.0098],
                 [0.034, 1.6610, 0.0088],
                 [0.045, 1.6620, 0.0072],
                 [0.054, 1.6615, 0.0050]])
BROW_STEPS, BROW_ACROSS = 12, 5
BROW_PROUD = 0.0022
BROW_RIM_SHARE = 0.45
EYE_CENTRES = np.array([[0.031, 1.6485], [-0.031, 1.6485]])
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


def the_head_surface(head_points, head_faces, eye_points, eye_faces):
    return trimesh.Trimesh(np.vstack([head_points, eye_points]),
                           np.vstack([head_faces, eye_faces + len(head_points)]), process=False)


def brows(surface):
    """Both brows as one mesh: points, faces."""
    return joined([slab(surface, *brow_grid(side)) for side in (1.0, -1.0)])


def irises(surface):
    """Both irises as one mesh: points, faces."""
    return joined([disc(surface, centre) for centre in EYE_CENTRES])
