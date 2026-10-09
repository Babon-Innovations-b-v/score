"""The hair shell's grid: a height field over the scalp, laid on directions from a centre inside the head. Columns go
round the head (azimuth 0 at the front, + to the person's left), rows run from the crown to the hairline, whose polar
angle is a table per azimuth, so the hairline is a clean grid row; one more ring tucks 3 mm under the skin there, so
the edge never shows a gap. Moved here from round three's hair_shell.py (#100), the parts generated hair uses.

Points are metres, y up, facing +z, like the people tools' parts.
"""
import numpy as np

# Take C's shell centre; a person's is moved with their eyes (hair_fit.centre_for).
TAKE_C_CENTRE = np.array([0.0, 1.655, -0.012])
TUCK = 0.003
# Hairline polar angle (degrees from straight up) by |azimuth| (degrees from the front): level across the front to a
# squared temple corner, a short sideburn in front of the ear, clear of the ear's top, low at the nape.
HAIRLINE = np.array([[0, 61], [25, 63], [40, 65], [52, 70], [58, 80], [63, 93], [70, 100], [80, 103], [86, 101],
                     [92, 89], [100, 84], [112, 87], [124, 98], [145, 107], [165, 112], [180, 114]])
# The part side (the person's right) sits a few degrees higher at the front: a slight recess.
PART_RECESS = 4.0


def smoothstep(low, high, value):
    share = np.clip((value - low) / (high - low), 0.0, 1.0)
    return share * share * (3 - 2 * share)


def hairline(azimuth_degrees):
    """The hairline's polar angle (radians) at each azimuth."""
    polar = np.interp(np.abs(azimuth_degrees), HAIRLINE[:, 0], HAIRLINE[:, 1])
    recess = PART_RECESS * np.exp(-((azimuth_degrees + 35) / 18) ** 2)
    return np.radians(polar - recess)


def directions(rows, columns):
    """Unit directions on the grid, (rows + 1, columns, 3); row 0 is the crown."""
    azimuth = np.linspace(-np.pi, np.pi, columns, endpoint=False)
    edge = hairline(np.degrees(azimuth))
    for _ in range(3):
        edge = (np.roll(edge, 1) + 2 * edge + np.roll(edge, -1)) / 4
    share = np.linspace(0.0, 1.0, rows + 1)[:, None]
    polar = share * edge[None, :]
    return np.stack([np.sin(polar) * np.sin(azimuth), np.cos(polar), np.sin(polar) * np.cos(azimuth)], axis=2)


def scalp_radius(head, dirs, centre):
    """The distance from the centre to the nearest head surface along each direction."""
    flat = dirs.reshape(-1, 3)
    locations, ray, _ = head.ray.intersects_location(np.tile(centre, (len(flat), 1)), flat, multiple_hits=True)
    radius = np.full(len(flat), np.inf)
    np.minimum.at(radius, ray, np.linalg.norm(locations - centre, axis=1))
    if np.isinf(radius).any():
        raise SystemExit(f"{int(np.isinf(radius).sum())} scalp rays missed the head")
    return radius.reshape(dirs.shape[:2])


def smooth_grid(field, passes):
    """Each grid value averaged with its neighbours round the row and along the column."""
    for _ in range(passes):
        around = np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
        up = np.vstack([field[:1], field[:-1]])
        down = np.vstack([field[1:], field[-1:]])
        field = (4 * field + around + up + down) / 8
    field[0] = field[0].mean()
    return field


def taper(field, dirs, front_edge):
    """The sides and back thinned toward the hairline (short and tidy); the front edge keeps `front_edge` of its
    height, so a swept top ends in a clean edge over the forehead."""
    share = np.linspace(0.0, 1.0, field.shape[0])[:, None]
    frontness = smoothstep(0.55, 0.85, dirs[..., 2][-1])[None, :]
    edge_share = frontness * front_edge + (1 - frontness) * 0.15
    return field * (1.0 - smoothstep(0.8, 1.0, share) * (1.0 - edge_share))


def mesh(points_grid, tuck_ring):
    """Points and faces for a crown fan, the grid rows, and the tuck ring below the last row."""
    rows, columns = points_grid.shape[:2]
    crown = points_grid[0].mean(axis=0)
    points = np.vstack([crown[None], points_grid[1:].reshape(-1, 3), tuck_ring])

    def index(row, column):
        return 0 if row == 0 else 1 + (row - 1) * columns + column % columns
    faces = [[0, index(1, column + 1), index(1, column)] for column in range(columns)]
    for row in range(1, rows - 1):
        for column in range(columns):
            first, second = index(row, column), index(row, column + 1)
            third, fourth = index(row + 1, column + 1), index(row + 1, column)
            faces += [[first, second, third], [first, third, fourth]]
    tuck_start = 1 + (rows - 1) * columns
    for column in range(columns):
        first, second = index(rows - 1, column), index(rows - 1, column + 1)
        third, fourth = tuck_start + (column + 1) % columns, tuck_start + column
        faces += [[first, second, third], [first, third, fourth]]
    return points, np.array(faces)
