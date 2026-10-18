"""The people route's head (owner, 2026-10-18, score #10): the made mesh's head is split, its hair kept and its face
dropped, and the face is the old SOMA-X head with the person's drawn face (`work/bodies/<person>.glb`'s skin_head,
eyes, irises and eyebrows, people/skin.py's head), laid on the made skeleton. Plain numpy and scipy.

- **The split.** The made body's parts already name the hair and the face (`hair`, `skin_head`, from the parts
  judge); the hair is kept as made, riding the head joint, and every `skin_head` surface is left out.
- **The old head, run on down the neck.** The old head was cut under its own collar (1.47 m on the player); the made
  collar sits lower, so the head is taken again from SOMA-X's average body laid on the made bind (the made rig's
  `source_points`, the same body the old head was cut from): every point above the cut within NECK_REACH of the neck's
  line, or hanging from the neck and head joints. Points the old head has keep its texture place; the new neck points
  take the old head's nearest bottom-border point's, and the picture's lowest band is painted plain skin
  (`painted_neck`: the old drawing drew its collar line there, which showed on the throat);
  the old head's own points and texture seams are kept as they are, the neck appended under them.
- **The hair on the old head.** The made hair was made on the made skull, which sits smaller and further forward than
  the old one; it is laid onto the old head by the turn and shift that best lay the made face above the neck on the
  old head (`rigid_fit`), grown about the head's middle until no more than a tenth of the old scalp it may cover
  shows through (`hair_scale`), and any old scalp point still in or through the hair is drawn in
  under it, HAIR_GAP inside its first surface on the line from the head's middle (`under_hair`), so the hair rides
  the same head and the hairline cannot open.
- **The neck seam.** The cut is SEAM_BELOW under the made collar line (the made face's lower border, by direction
  round the neck: its lowest), the owner's 2 cm. The neck keeps SOMA-X's own weights (Neck1, Neck2, Head). Every head
  point under the collar line at its own direction round the neck is a tuck (listed last, the material's
  `tuck_from`), which pokes.py's tucks gate holds to 5 mm.
"""
import numpy as np
from scipy.spatial import cKDTree

NECK_REACH = 0.08
SEAM_BELOW = 0.02
HEAD_JOINTS = ("Neck1", "Neck2", "Head", "HeadEnd")
DIRECTIONS = 24
SAME_PLACE = 0.001
ICP_ROUNDS = 30
HAIR_GAP = 0.003
HAIR_SCALES = tuple(np.round(np.arange(1.0, 1.31, 0.01), 2))
HAIR_THROUGH = 0.1
PAINT_BAND = 0.02
# Texels the painted band reaches past its triangles, so a bilinear sample at its edge stays plain skin.
PAINT_MARGIN = 4


def border_points(faces):
    """The points on edges used by one triangle."""
    pairs = np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    unique, counts = np.unique(pairs, axis=0, return_counts=True)
    return np.unique(unique[counts == 1])


def around(points, centre):
    """Each point's direction round the neck's vertical line through `centre`, as one of DIRECTIONS bins."""
    turn = np.arctan2(points[:, 2] - centre[2], points[:, 0] - centre[0])
    return ((turn + np.pi) / (2 * np.pi) * DIRECTIONS).astype(int) % DIRECTIONS


def collar_line(face_points, centre, below):
    """The made collar line by direction round the neck (DIRECTIONS heights): the face's border points under
    `below` (the jaw), each bin's lowest, an empty bin the mean of its two nearest filled ones."""
    low = face_points[face_points[:, 1] < below]
    bins = around(low, centre)
    line = np.full(DIRECTIONS, np.nan)
    for number in np.unique(bins):
        line[number] = low[bins == number, 1].min()
    filled = np.flatnonzero(~np.isnan(line))
    for number in np.flatnonzero(np.isnan(line)):
        gaps = (filled - number) % DIRECTIONS
        after, before = filled[gaps.argmin()], filled[((number - filled) % DIRECTIONS).argmin()]
        line[number] = 0.5 * (line[after] + line[before])
    return line


def head_piece(points, faces, weights, names, centre, cut):
    """SOMA-X's head and neck above `cut`: (points, faces, weights, each kept point's number in the body)."""
    head = np.isin(np.asarray(names)[weights.argmax(1)], HEAD_JOINTS)
    near = np.hypot(points[:, 0] - centre[0], points[:, 2] - centre[2]) < NECK_REACH
    kept = (head | near) & (points[:, 1] > cut)
    faces = faces[kept[faces].all(1)]
    used, renumbered = np.unique(faces, return_inverse=True)
    return points[used], renumbered.reshape(-1, 3), weights[used], used


class Extension:
    """The SOMA-X piece's triangles the old head lacks, to append to the old head: each triangle with three points of
    its own (`points`, `weights`, `faces` numbered from the old head's point count) all wearing one texture place,
    the old head's bottom-border point nearest the triangle's middle, in the band `painted_neck` paints plain skin.
    Shared points wore their own border places, and a triangle across the old drawing's seam down the throat drew a
    streak across the whole picture. `found`: how many piece points the old head has at the same place."""

    def __init__(self, piece_points, piece_faces, piece_weights, old_points, old_faces, old_uv, old_weights):
        distance, nearest = cKDTree(old_points).query(piece_points)
        same = distance < SAME_PLACE
        self.found = int(same.sum())
        new = piece_faces[~same[piece_faces].all(1)]
        places = np.where(same[:, None], old_points[nearest], piece_points)
        weights = np.where(same[:, None], old_weights[nearest], piece_weights)
        self.points = places[new].reshape(-1, 3)
        self.weights = weights[new].reshape(-1, weights.shape[1])
        self.faces = len(old_points) + np.arange(len(self.points)).reshape(-1, 3)
        border = border_points(old_faces)
        bottom = border[old_points[border, 1] <= np.median(old_points[border, 1])]
        middles = places[new].mean(1)
        self.uv = np.repeat(old_uv[bottom[cKDTree(old_points[bottom]).query(middles)[1]]], 3, axis=0)


def painted_neck(picture, points, faces, uv, band=PAINT_BAND):
    """The old head's picture with its lowest `band` painted plain skin (the median colour at the head's texture
    places): the old drawing draws a line where its own collar met the neck, which the made collar, cut lower in
    front, shows on the throat. Painting the picture, not moving texture places, keeps every triangle sampling inside
    its own part of the picture (moved places drew streaks across the drawing)."""
    from PIL import Image, ImageDraw
    rows, columns = picture.shape[:2]
    skin = np.median(picture[np.clip((uv[:, 1] * rows).astype(int), 0, rows - 1),
                             np.clip((uv[:, 0] * columns).astype(int), 0, columns - 1), :3], 0)
    colour = tuple(int(value) for value in skin)
    low = points[:, 1] < points[:, 1].min() + band
    image = Image.fromarray(picture[:, :, :3].copy())
    draw = ImageDraw.Draw(image)
    for face in faces[low[faces].any(1)]:
        corners = [(float(u * columns), float(v * rows)) for u, v in uv[face]]
        draw.polygon(corners, fill=colour, outline=colour, width=PAINT_MARGIN)
    return np.asarray(image)


def laid_on(points, weights, old_bind, new_bind):
    """Points moved from one skeleton's bind onto another's by their own weights (dense, per joint)."""
    moves = new_bind @ np.linalg.inv(old_bind)
    blended = np.einsum("pj,jab->pab", weights, moves)
    return np.einsum("pab,pb->pa", blended[:, :3, :3], points) + blended[:, :3, 3]


def tuck_order(points, line, centre):
    """The head's points reordered visible first, those under the collar line last: (order, tuck_from)."""
    under = points[:, 1] < line[around(points, centre)]
    order = np.r_[np.flatnonzero(~under), np.flatnonzero(under)]
    return order, int((~under).sum())


def reordered(order, faces):
    """Triangles renumbered after their points were put in `order`."""
    new_number = np.empty(len(order), int)
    new_number[order] = np.arange(len(order))
    return new_number[faces]


def rigid_fit(source, target, rounds=ICP_ROUNDS):
    """The turn and shift that best lay `source` points on `target` points (iterative closest points with Umeyama's
    least-squares fit each round, its scale held at one: let free, it shrank the made face to 0.81 of its size onto
    the larger old head, iterative closest points' known pull): a 4x4 matrix."""
    tree = cKDTree(target)
    matrix = np.eye(4)
    moved = source.copy()
    for _ in range(rounds):
        matched = target[tree.query(moved)[1]]
        step = umeyama(moved, matched)
        moved = moved @ step[:3, :3].T + step[:3, 3]
        matrix = step @ matrix
    return matrix


def umeyama(source, target):
    """The least-squares turn and shift from paired points (Umeyama 1991, scale one): a 4x4 matrix."""
    source_mean, target_mean = source.mean(0), target.mean(0)
    centred_source, centred_target = source - source_mean, target - target_mean
    left, _, right = np.linalg.svd(centred_target.T @ centred_source / len(source))
    sign = np.eye(3)
    sign[2, 2] = np.sign(np.linalg.det(left @ right)) or 1.0
    turn = left @ sign @ right
    matrix = np.eye(4)
    matrix[:3, :3] = turn
    matrix[:3, 3] = target_mean - turn @ source_mean
    return matrix


def under_hair(points, hair_points, hair_faces, centre, covered):
    """Head points the hair may cover (`covered`) that lie in or through the hair, drawn in towards `centre` to
    HAIR_GAP inside the hair's first surface on the line from the centre: the scalp stays under the hair. Also how
    many moved."""
    import trimesh
    hair = trimesh.Trimesh(hair_points, hair_faces, process=False)
    asked = np.flatnonzero(covered)
    moving, first = through_hair(points[asked], hair, centre)
    directions = points[asked[moving]] - centre
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    moved = points.copy()
    moved[asked[moving]] = centre + directions * (first[moving] - HAIR_GAP)[:, None]
    return moved, int(moving.sum())


def scalp(points, centre, brow_top, ear_level):
    """Which head points the hair may cover: above the ears, and in front only above the brows."""
    behind = points[:, 2] < centre[2]
    return (points[:, 1] > ear_level) & (behind | (points[:, 1] > brow_top))


def through_hair(points, hair, centre):
    """Which points lie at or past HAIR_GAP inside the hair's first surface on the line from `centre`, and that
    surface's distance from the centre on each point's line (inf where the line misses the hair)."""
    directions = points - centre
    reach = np.linalg.norm(directions, axis=1)
    directions = directions / reach[:, None]
    places, rays, _ = hair.ray.intersects_location(np.repeat(centre[None], len(points), 0), directions,
                                                  multiple_hits=True)
    first = np.full(len(points), np.inf)
    np.minimum.at(first, rays, np.linalg.norm(places - centre, axis=1))
    return reach > first - HAIR_GAP, first


def hair_scale(scalp_points, hair_points, hair_faces, centre):
    """The least scale of the hair about the head's middle (of HAIR_SCALES) under which no more than HAIR_THROUGH of
    the scalp it may cover shows through it: the made skull is smaller than the old one."""
    import trimesh
    for scale in HAIR_SCALES:
        hair = trimesh.Trimesh(centre + (hair_points - centre) * scale, hair_faces, process=False)
        showing, _ = through_hair(scalp_points, hair, centre)
        if showing.mean() <= HAIR_THROUGH:
            return scale
    return HAIR_SCALES[-1]
