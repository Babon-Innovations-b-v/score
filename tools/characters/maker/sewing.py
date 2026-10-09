"""The plain pieces of draping a GarmentCode garment (in Newton, `newton_drape.py`, or Blender, `cloth_drape.py`), with
nothing but numpy: GarmentCode's measurements sized to a body, the seams between the panels cut apart, the sewn cloth
put back in the box mesh's point order, the welded cloth's rest shapes taken from the flat panels, the bending edges,
the points GarmentCode holds while it drapes, and the cloth written in GarmentCode's simulation output format
(`<name>_sim.obj`, which `people/drape.py` reads).

A sewing record (`<name>_sewing.npz`, written by `garment.py`) holds:
    points      every panel's points in centimetres, where GarmentCode laid the panel round the body
    faces       the panels' triangles, as indices into points
    box_index   for each point, the box mesh point it is; a seam's point has a copy in each panel it joins
    panel       for each point, the number of its panel; panel_names names them
"""
import pathlib

import numpy as np

# Measurements GarmentCode keeps as they are, angles of the body rather than lengths.
ANGLES = ("arm_pose_angle", "hip_inclination", "shoulder_incl")
# Girths and widths that follow a girth measured on both bodies rather than the height.
FOLLOWS = {"bust": "bust", "waist": "waist", "hips": "hips", "leg_circ": "leg_circ", "wrist": "wrist",
           "underbust": "bust", "back_width": "bust", "waist_back_width": "waist", "hip_back_width": "hips",
           "arm_length": "arm_length", "shoulder_w": "shoulder_w"}


def sized_measurements(base, theirs, ours):
    """GarmentCode's measurements of its reference body (`base`, centimetres) carried to ours: what both bodies were
    measured by (`theirs`, `ours`, the same way) scales its own number, every other length scales with the height,
    and the arms' angle moves by the difference measured (GarmentCode's angle is for its own A pose)."""
    sized = {}
    for key, value in base.items():
        if key == "arm_pose_angle":
            sized[key] = value + (ours["arm_pose_angle"] - theirs["arm_pose_angle"])
        elif key in ANGLES:
            sized[key] = value
        elif key in FOLLOWS:
            sized[key] = value * ours[FOLLOWS[key]] / theirs[FOLLOWS[key]]
        else:
            sized[key] = value * ours["height"] / theirs["height"]
    return {key: round(float(value), 4) for key, value in sized.items()}


def seams(box_index):
    """The sewing threads: every copy of a box mesh point tied to the first copy, as pairs of point indices."""
    first = {}
    pairs = []
    for point, box in enumerate(np.asarray(box_index).tolist()):
        if box in first:
            pairs.append((first[box], point))
        else:
            first[box] = point
    return np.array(pairs, dtype=np.int64).reshape(-1, 2)


def merged(points, box_index, count):
    """The box mesh's points from the panels' points: each the middle of its copies."""
    box_index = np.asarray(box_index)
    total = np.zeros((count, 3))
    np.add.at(total, box_index, points)
    copies = np.bincount(box_index, minlength=count)
    if (copies == 0).any():
        raise ValueError(f"{int((copies == 0).sum())} box mesh points have no panel point")
    return total / copies[:, None]


def seam_gaps(points, box_index):
    """How far each thread is still open: the distance between each copy and its first copy."""
    pairs = seams(box_index)
    return np.linalg.norm(points[pairs[:, 0]] - points[pairs[:, 1]], axis=1)


def read_obj(path):
    """An OBJ file's points and triangles (the first index of each corner; polygons fanned)."""
    points, faces = [], []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("v "):
            points.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            faces.extend([corners[0], corners[index], corners[index + 1]] for index in range(1, len(corners) - 1))
    return np.array(points, dtype=float), np.array(faces, dtype=np.int64)


def box_point_count(box_obj_text):
    """How many points the box mesh file has."""
    return sum(1 for line in box_obj_text.splitlines() if line.startswith("v "))


def sim_obj(box_obj_text, positions):
    """GarmentCode's simulated cloth file: the box mesh file with its points moved to the sewn positions
    (centimetres), everything else (texture coordinates, faces) kept, as GarmentCode's own save_frame writes it."""
    lines, index = [], 0
    for line in box_obj_text.splitlines():
        if line.startswith("v "):
            if index >= len(positions):
                raise ValueError(f"the box mesh has more points than the {len(positions)} given")
            lines.append(f"v {positions[index][0]} {positions[index][1]} {positions[index][2]}")
            index += 1
        else:
            lines.append(line)
    if index != len(positions):
        raise ValueError(f"the box mesh has {index} points, {len(positions)} given")
    return "\n".join(lines) + "\n"


def barycentric(points, corners):
    """Each point's barycentric weights in each triangle (points x triangles x 3), the point taken onto the
    triangle's plane."""
    first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
    along_one, along_two = second - first, third - first
    offset = points[:, None, :] - first[None]
    one_one = (along_one * along_one).sum(axis=1)
    one_two = (along_one * along_two).sum(axis=1)
    two_two = (along_two * along_two).sum(axis=1)
    off_one = (offset * along_one[None]).sum(axis=2)
    off_two = (offset * along_two[None]).sum(axis=2)
    area = one_one * two_two - one_two ** 2
    weight_two = (two_two * off_one - one_two * off_two) / area
    weight_three = (one_one * off_two - one_two * off_one) / area
    return np.stack([1.0 - weight_two - weight_three, weight_two, weight_three], axis=2)


def carried(fine, coarse, sewn):
    """The fine panels' points carried onto where the coarse panels were sewn: each fine point at its place in the
    coarse triangle of its own panel that holds it (or comes nearest to holding it, at a panel's edge), in the laid
    panels, then at that place in the same triangle sewn.

    `fine` and `coarse` are sewing records of one pattern at two spacings (the panels laid the same way), `sewn` the
    coarse points after sewing. A fine drape started from it needs only to settle, not to be sewn round the body."""
    result = np.empty_like(fine["points"], dtype=float)
    coarse_face_panel = coarse["panel"][coarse["faces"][:, 0]]
    for number in np.unique(fine["panel"]):
        mine = np.where(fine["panel"] == number)[0]
        faces = coarse["faces"][coarse_face_panel == number]
        weights = barycentric(fine["points"][mine], coarse["points"][faces])
        best = weights.min(axis=2).argmax(axis=1)
        chosen = weights[np.arange(len(mine)), best]
        result[mine] = (chosen[:, :, None] * sewn[faces[best]]).sum(axis=1)
    return result


def arm_of(panel):
    """The arm a panel dresses, as people/drape.py's limb_of reads a panel's name, or None."""
    if panel.startswith("pant_") or not ("sleeve" in panel or "cuff" in panel):
        return None
    return "left_arm" if "left" in panel else "right_arm"


def uncovered(points, faces, on_limb, shoulder, elbow, span, step=0.01):
    """The shares of the upper arm, from shoulder to elbow, within `span` (from, to) that no triangle of the limb's
    cloth (any corner on it, as people/space_suit.py cuts its bands) reaches across: an empty list when the sleeve
    covers the whole span, as every band the space suits lay round the upper arm needs."""
    axis = np.asarray(elbow, dtype=float) - np.asarray(shoulder, dtype=float)
    length = np.linalg.norm(axis)
    along = (np.asarray(points) - shoulder) @ (axis / length) / length
    kept = np.asarray(faces)[np.asarray(on_limb)[faces].any(axis=1)]
    low, high = along[kept].min(axis=1), along[kept].max(axis=1)
    shares = np.round(np.arange(span[0], span[1] + step / 2, step), 4)
    return [float(share) for share in shares if not ((low <= share) & (high >= share)).any()]


# ---- the welded cloth (newton_drape.py) -------------------------------------------------------------------------

def welded_faces(record):
    """The panels' triangles as the box mesh's: each corner the box mesh point its panel point is."""
    return np.asarray(record["box_index"])[np.asarray(record["faces"])]


def rest_areas(record):
    """Each triangle's area in its own flat panel (the record's units squared)."""
    corners = np.asarray(record["points"], dtype=float)[np.asarray(record["faces"])]
    return 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)


def point_masses(record, count, density):
    """Each box mesh point's mass: a third of each of its triangles' flat area times `density` (mass per area)."""
    masses = np.zeros(count)
    np.add.at(masses, welded_faces(record), (rest_areas(record) * density / 3.0)[:, None])
    return masses


def bending_edges(faces):
    """Every edge of a triangle mesh as Newton's bending elements take it: (the corner opposite it in its first
    triangle, the corner opposite it in its second or -1 at a border, its start, its end), its first triangle running
    from start to end; the first triangle of each edge; and how many edges join two triangles running the same way
    along them or more than two triangles (a mesh not oriented alike there), whose bending is left out."""
    faces = np.asarray(faces)
    halves = {}
    for number, (first, second, third) in enumerate(faces.tolist()):
        for start, end, opposite in ((first, second, third), (second, third, first), (third, first, second)):
            halves.setdefault((min(start, end), max(start, end)), []).append((start, end, opposite, number))
    edges, owners, odd = [], [], 0
    for shared in halves.values():
        start, end, opposite, owner = shared[0]
        if len(shared) == 1:
            edges.append((opposite, -1, start, end))
        elif len(shared) == 2 and shared[1][0] == end and shared[1][1] == start:
            edges.append((opposite, shared[1][2], start, end))
        else:
            odd += 1
            edges.append((opposite, -1, start, end))
        owners.append(owner)
    return np.array(edges, dtype=np.int64).reshape(-1, 4), np.array(owners, dtype=np.int64), odd


def rest_edge_lengths(record, edges, owners):
    """Each edge's length in the flat panel of the triangle it was read from (`bending_edges`), in the record's
    units: a seam's edge is as long as the pattern makes it, not as GarmentCode's box mesh stretched it."""
    copies = np.asarray(record["faces"])[owners]
    welded = np.asarray(record["box_index"])[copies]
    points = np.asarray(record["points"], dtype=float)

    def copy_of(corner):
        column = np.argmax(welded == np.asarray(corner)[:, None], axis=1)
        return copies[np.arange(len(copies)), column]

    return np.linalg.norm(points[copy_of(edges[:, 2])] - points[copy_of(edges[:, 3])], axis=1)


def attachments(labels, body):
    """The points GarmentCode's Warp run held while the garment draped (its garment.py, MIT): the waist points
    ('lower_interface') at the body's waist level along y, and each collar at half the neck's width less a centimetre
    along x. `labels` is the box mesh's vertex labels, `body` GarmentCode's measurements (centimetres); a list of
    (points, axis, value in centimetres)."""
    held = []
    if labels.get("lower_interface"):
        level = body.get("_waist_level", body["height"] - body["head_l"] - body["waist_line"])
        held.append((np.asarray(labels["lower_interface"], dtype=np.int64), 1, float(level)))
    neck = (body["neck_w"] - 2.0) / 2.0
    for label, value in (("right_collar", -neck), ("left_collar", neck)):
        if labels.get(label):
            held.append((np.asarray(labels[label], dtype=np.int64), 0, float(value)))
    return held
