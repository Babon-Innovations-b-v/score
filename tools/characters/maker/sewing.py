"""The plain pieces of draping a GarmentCode garment in Blender, with nothing but numpy: GarmentCode's measurements
sized to a body, the seams between the panels cut apart, the sewn cloth put back in the box mesh's point order, and
the cloth written in GarmentCode's simulation output format (`<name>_sim.obj`, which `people/drape.py` reads).

A sewing record (`<name>_sewing.npz`, written by `garment.py`) holds:
    points      every panel's points in centimetres, where GarmentCode laid the panel round the body
    faces       the panels' triangles, as indices into points
    box_index   for each point, the box mesh point it is; a seam's point has a copy in each panel it joins
    panel       for each point, the number of its panel; panel_names names them
"""
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
