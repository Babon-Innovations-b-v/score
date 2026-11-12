"""A flag's cloth as a grid the simulation moves, and the rig that carries the flag's own mesh on it (the motion row's
flag cloth, cloth.py). Plain numpy: no USD, no Newton.

The flag's mesh stays as it is built; only how it moves is made. Its cloth (the parts whose library surface is made
with a recipe the cloth table holds) is laid flat as a grid of `spacing` metres in its own frame: from its pole's
upright line (the middle of its parts that are not cloth: the pole) along the cloth to its free edge (`along`), up
its pole (`up`, the model's own up) and across (`normal`). Only the grid's cells the cloth covers are kept; its
column on the pole's line is pinned. Every `every`-th node each way is a joint, each carrying its turn from the grid's
own slope there; each cloth point rides the four joints of the joint cell it lies in (bilinear shares, a missing
corner dropped), and every point of the pole, and of the cloth within half a cell of the pole's line (its sleeve), the
pole's own joint, which never moves.

    cloth_points(faces, subsets, ...)     the points of the cloth's faces, and the rest
    frame_of(points, cloth, rigid)        the flag's own frame: origin on the pole's line, along, up, normal
    triangles_of(faces, subsets, cloth)   the cloth's faces as triangles
    grid_of(local, triangles, spacing)    the grid nodes, faces and pinned column over the cloth (in the frame)
    joints_of(grid, every)                the grid nodes that are joints
    weights_of(local, cloth, grid, ...)   each point's four joints and shares
    turns_of(positions, grid, joints)     each joint's frame (frames x joints x 4 x 4) from the grid's slope there
    looped(positions, frames, seam)       a run made to loop: its first `seam` frames blended into those after its end
"""
import numpy as np

UP = np.array([0.0, 1.0, 0.0])


def cloth_points(faces, subsets, cloth, count):
    """(the points of the faces of the `cloth` subsets, every other of the mesh's `count` points), each sorted.
    `faces` is each face's point indices, `subsets` {name: face indices}."""
    chosen = [face for name in cloth for face in subsets[name]]
    inside = np.unique(np.concatenate([np.asarray(faces[face]) for face in chosen])) if chosen else \
        np.zeros(0, dtype=np.int64)
    return inside, np.setdiff1d(np.arange(count), inside)


def frame_of(points, cloth, rigid):
    """The flag's own frame as a 4 x 4 (its columns along, up, normal and origin, in the model's space): the origin
    on the pole's upright line (the middle of the rigid points across, at the model's floor), `along` the cloth's
    widest way across the up axis, turned from the pole toward the cloth, `normal` along x up."""
    points = np.asarray(points, dtype=np.float64)
    pole = points[rigid].mean(axis=0)
    origin = np.array([pole[0], 0.0, pole[2]])
    flat = points[cloth][:, [0, 2]] - origin[[0, 2]]
    _, _, axes = np.linalg.svd(flat - flat.mean(axis=0), full_matrices=False)
    along = np.array([axes[0][0], 0.0, axes[0][1]])
    if along[[0, 2]] @ flat.mean(axis=0) < 0.0:
        along = -along
    along /= np.linalg.norm(along)
    normal = np.cross(along, UP)
    found = np.eye(4)
    found[:3, 0], found[:3, 1], found[:3, 2], found[:3, 3] = along, UP, normal, origin
    return found


def local_of(points, frame):
    """Points of the model in the flag's own frame ([along, up, normal])."""
    return (np.asarray(points, dtype=np.float64) - frame[:3, 3]) @ frame[:3, :3]


def triangles_of(faces, subsets, cloth):
    """The cloth's faces as triangles (fans), point indices k x 3."""
    found = []
    for face in (faces[number] for name in cloth for number in subsets[name]):
        found += [(face[0], face[corner], face[corner + 1]) for corner in range(1, len(face) - 1)]
    return np.asarray(found, dtype=np.int64).reshape(-1, 3)


def covered_cells(flat, triangles, spacing, shape):
    """Which grid cells (columns x rows) the cloth covers: the middle of the cell inside one of its triangles laid
    flat (`flat`: points x 2, along and up off the grid's corner), or a point of it in the cell."""
    covered = np.zeros(shape, dtype=bool)
    cells = np.minimum((flat[np.unique(triangles.ravel())] / spacing).astype(int), np.asarray(shape) - 1)
    covered[cells[:, 0], cells[:, 1]] = True
    for corners in flat[triangles]:
        low = np.maximum(np.floor(corners.min(axis=0) / spacing - 0.5).astype(int), 0)
        high = np.minimum(np.ceil(corners.max(axis=0) / spacing - 0.5).astype(int), np.asarray(shape) - 1)
        if (high < low).any():
            continue
        columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1), indexing="ij")
        middles = (np.stack([columns.ravel(), rows.ravel()], axis=1) + 0.5) * spacing
        first, second = corners[1] - corners[0], corners[2] - corners[0]
        area = first[0] * second[1] - first[1] * second[0]
        if abs(area) < 1e-15:
            continue
        offset = middles - corners[0]
        share_b = (offset[:, 0] * second[1] - offset[:, 1] * second[0]) / area
        share_c = (first[0] * offset[:, 1] - first[1] * offset[:, 0]) / area
        inside = (share_b >= 0.0) & (share_c >= 0.0) & (share_b + share_c <= 1.0)
        covered[columns.ravel()[inside], rows.ravel()[inside]] = True
    return covered


def grid_of(local, triangles, spacing):
    """The grid over the cloth (`triangles` of `local`, the points in the flag's frame): {"index": (column, row) of
    each node, "number": each (column, row)'s node or -1, "points": nodes x 3 at rest (flat, normal 0), "faces": two
    triangles a covered cell, "pinned": the nodes of column 0 (on the pole's line), "low": the grid's lowest up,
    "spacing"}."""
    used_points = np.unique(triangles.ravel())
    along, up = np.maximum(local[used_points, 0], 0.0), local[used_points, 1]
    low = float(up.min())
    columns, rows = int(np.floor(along.max() / spacing)) + 1, int(np.floor((up.max() - low) / spacing)) + 1
    flat = np.stack([np.maximum(local[:, 0], 0.0), local[:, 1] - low], axis=1)
    covered = covered_cells(flat, triangles, spacing, (columns, rows))
    used = np.zeros((columns + 1, rows + 1), dtype=bool)
    for step_a in (0, 1):
        for step_u in (0, 1):
            used[step_a:columns + step_a, step_u:rows + step_u] |= covered
    index = np.argwhere(used)
    number = -np.ones(used.shape, dtype=np.int64)
    number[index[:, 0], index[:, 1]] = np.arange(len(index))
    faces = []
    for column, row in np.argwhere(covered):
        a, b = number[column, row], number[column + 1, row]
        c, d = number[column + 1, row + 1], number[column, row + 1]
        faces += [(a, b, c), (a, c, d)]
    points = np.stack([index[:, 0] * spacing, low + index[:, 1] * spacing, np.zeros(len(index))], axis=1)
    return {"index": index, "number": number, "points": points, "faces": np.asarray(faces, dtype=np.int64),
            "pinned": index[:, 0] == 0, "low": low, "spacing": float(spacing)}


def joints_of(grid, every):
    """The grid nodes that are joints: each `every`-th column and row of the grid, and the last of each, where a
    node stands."""
    index = grid["index"]
    last = index.max(axis=0)
    on = [(index[:, axis] % every == 0) | (index[:, axis] == last[axis]) for axis in (0, 1)]
    return np.flatnonzero(on[0] & on[1])


def lines_of(grid, joints):
    """The sorted joint columns and rows of the grid."""
    index = grid["index"][joints]
    return np.unique(index[:, 0]), np.unique(index[:, 1])


def weights_of(local, cloth, grid, joints, influences=4):
    """(joint indices, shares), points x `influences` each: a joint's index counts from 1 (0 is the pole's own
    joint). A cloth point past half a cell from the pole's line rides the four joints of the joint cell it lies in,
    by bilinear shares, a missing corner dropped and the rest made whole again (none: its nearest joint); every other
    point rides the pole's joint alone."""
    spacing = grid["spacing"]
    columns, rows = lines_of(grid, joints)
    joint_at = {tuple(grid["index"][node]): number + 1 for number, node in enumerate(joints)}
    indices = np.zeros((len(local), influences), dtype=np.int64)
    shares = np.zeros((len(local), influences))
    shares[:, 0] = 1.0
    for point in cloth:
        along, up = local[point, 0] / spacing, (local[point, 1] - grid["low"]) / spacing
        if along < 0.5:
            continue
        low_a = columns[max(np.searchsorted(columns, along, side="right") - 1, 0)]
        high_a = columns[min(np.searchsorted(columns, along, side="right"), len(columns) - 1)]
        low_u = rows[max(np.searchsorted(rows, up, side="right") - 1, 0)]
        high_u = rows[min(np.searchsorted(rows, up, side="right"), len(rows) - 1)]
        across = 0.0 if high_a == low_a else float(np.clip((along - low_a) / (high_a - low_a), 0.0, 1.0))
        upward = 0.0 if high_u == low_u else float(np.clip((up - low_u) / (high_u - low_u), 0.0, 1.0))
        found = {}
        for (column, part_a) in ((low_a, 1.0 - across), (high_a, across)):
            for (row, part_u) in ((low_u, 1.0 - upward), (high_u, upward)):
                if (int(column), int(row)) in joint_at and part_a * part_u > 0.0:
                    joint = joint_at[(int(column), int(row))]
                    found[joint] = found.get(joint, 0.0) + part_a * part_u
        if not found:
            nodes = grid["index"][joints]
            nearest = int(np.argmin(np.hypot(nodes[:, 0] - along, nodes[:, 1] - up)))
            found = {nearest + 1: 1.0}
        total = sum(found.values())
        for slot, (joint, share) in enumerate(sorted(found.items())):
            indices[point, slot], shares[point, slot] = joint, share / total
    return indices, shares


def neighbour(grid, node, axis, step):
    """The grid node `step` from `node` along `axis` (0 along, 1 up), or the node itself where there is none."""
    index = grid["index"][node].copy()
    index[axis] += step
    shape = grid["number"].shape
    if not (0 <= index[0] < shape[0] and 0 <= index[1] < shape[1]):
        return node
    found = grid["number"][index[0], index[1]]
    return node if found < 0 else int(found)


def turns_of(positions, grid, joints):
    """Each joint's frame in the flag's frame at each of `positions` (frames x nodes x 3): frames x joints x 4 x 4,
    its origin the node, its x the grid's slope along there, its z the cloth's normal (along x up), its y z x x."""
    positions = np.asarray(positions, dtype=np.float64)
    found = np.zeros((len(positions), len(joints), 4, 4))
    found[:, :, 3, 3] = 1.0
    for number, node in enumerate(joints):
        ahead, behind = neighbour(grid, node, 0, 1), neighbour(grid, node, 0, -1)
        above, below = neighbour(grid, node, 1, 1), neighbour(grid, node, 1, -1)
        along = positions[:, ahead] - positions[:, behind]
        up = positions[:, above] - positions[:, below]
        along /= np.maximum(np.linalg.norm(along, axis=1), 1e-12)[:, None]
        normal = np.cross(along, up)
        normal /= np.maximum(np.linalg.norm(normal, axis=1), 1e-12)[:, None]
        found[:, number, :3, 0] = along
        found[:, number, :3, 1] = np.cross(normal, along)
        found[:, number, :3, 2] = normal
        found[:, number, :3, 3] = positions[:, node]
    return found


def looped(positions, frames, seam):
    """`frames` frames of a run that loops: its frames from `seam` on as they are, its first `seam` frames blended
    from those `frames` later (all of them at its first frame) into its own (all of them at frame `seam`), so its
    last frame leads into its first as any frame into the next. `positions` holds at least frames + seam."""
    positions = np.asarray(positions, dtype=np.float64)
    if len(positions) < frames + seam:
        raise ValueError(f"a loop of {frames} frames with a {seam}-frame seam needs {frames + seam} frames, "
                         f"not {len(positions)}")
    found = positions[:frames].copy()
    for frame in range(seam):
        share = frame / seam
        found[frame] = positions[frame + frames] * (1.0 - share) + positions[frame] * share
    return found

