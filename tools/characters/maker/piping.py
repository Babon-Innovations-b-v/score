"""The prop route's piping: thin strips down the outside of each sleeve and each trouser leg, where the close-up shows
them (the player's work suit: red from below the shoulder panel to the cuff, and from the belt to the hem), cut into
the garment's own triangles along two lines PIPING_WIDTH apart, so a strip is sharp and as thin as the cloth's print
rather than a run of whole triangles. SAM 2.1 found the piping on the player's upper arms only, as patches, and never
on his legs (2026-10-10). Plain numpy.

The line down a limb is the shipped work suit's (people/paint.py `outer_line`): on the limb's chain of joints, the
side facing away from the body in a front view; a point's place across it is its offset from that line round the
limb. Only triangles whose corners all lie on that outer half, close to the chain and within its run are cut.
"""
import numpy as np

# The piping's width: about a centimetre on the close-up's sleeves and trouser legs at the figure's scale.
PIPING_WIDTH = 0.009
# How far from its limb's chain a garment point may lie to be on that limb (the trouser legs' widest).
LIMB_REACH = 0.11
# Where each run starts and stops along its chain, in metres from the chain's first joint: a sleeve's under the
# shoulder panel to its cuff, a trouser leg's from under the belt to its hem.
ARM_RUN = (0.06, None)
LEG_RUN = (0.04, None)
CHAINS = (("Arm", "ForeArm", "Hand"), ("Leg", "Shin", "Foot"))


def along_chain(points, places):
    """Each point's distance along a chain of joint places from its first, the chain's direction there and the
    nearest place on it (people/paint.py's along_chain), and its distance from the chain."""
    best = np.full(len(points), np.inf)
    along, axis_out, foot_out = np.zeros(len(points)), np.zeros((len(points), 3)), np.zeros((len(points), 3))
    start = 0.0
    for first, second in zip(places[:-1], places[1:]):
        length = np.linalg.norm(second - first)
        axis = (second - first) / length
        reach = np.clip((points - first) @ axis, 0, length)
        foot = first + reach[:, None] * axis
        distance = np.linalg.norm(points - foot, axis=1)
        closer = distance < best
        best[closer] = distance[closer]
        along[closer] = start + reach[closer]
        axis_out[closer] = axis
        foot_out[closer] = foot[closer]
        start += length
    return along, axis_out, foot_out, best


def across_outer_line(points, places, side_sign, run):
    """Each point's offset across the line down the outside of the limb (signed, metres), and whether it is on the
    limb's outer half within `run` (start, end metres along its chain; None: to the chain's last joint)."""
    along, axis, foot, distance = along_chain(points, places)
    lateral = np.array([side_sign, 0.0, 0.0])
    outward = lateral - (axis @ lateral)[:, None] * axis
    outward /= np.maximum(np.linalg.norm(outward, axis=1, keepdims=True), 1e-12)
    radial = points - foot
    across = (radial * np.cross(axis, outward)).sum(1)
    end = run[1] if run[1] is not None else np.inf
    usable = ((radial * outward).sum(1) > 0) & (distance < LIMB_REACH) & (along >= run[0]) & (along <= end) & \
        (along < np.sum(np.linalg.norm(np.diff(places, axis=0), axis=1)) - 1e-6)
    return across, usable


def split_at(points, faces, weights, field, level, cut):
    """The triangles marked in `cut` that `field` crosses `level` in, split along it (one new point an edge, shared
    by the triangles on either side, its place, weights and field interpolated): (points, faces, weights, field, cut)
    with the new triangles keeping their triangle's mark."""
    above = field > level
    crossing = cut & (above[faces].sum(1) % 3 != 0)
    made = {}
    new_points, new_weights, new_field = [points], [weights], [field]
    total = len(points)

    def on_edge(first, second):
        nonlocal total
        key = (min(first, second), max(first, second))
        if key not in made:
            share = (level - field[key[0]]) / (field[key[1]] - field[key[0]])
            new_points.append(points[key[0]] + share * (points[key[1]] - points[key[0]]))
            new_weights.append(weights[key[0]] + share * (weights[key[1]] - weights[key[0]]))
            new_field.append(level)
            made[key] = total
            total += 1
        return made[key]

    kept_faces, kept_cut = [faces[~crossing]], [cut[~crossing]]
    for corners in faces[crossing]:
        lone = next(slot for slot in range(3) if above[corners[slot]] != above[corners[(slot + 1) % 3]]
                    and above[corners[slot]] != above[corners[(slot + 2) % 3]])
        alone, first, second = corners[lone], corners[(lone + 1) % 3], corners[(lone + 2) % 3]
        to_first, to_second = on_edge(alone, first), on_edge(alone, second)
        kept_faces.append(np.array([[alone, to_first, to_second], [to_first, first, second],
                                    [to_first, second, to_second]]))
        kept_cut.append(np.ones(3, bool))
    return (np.vstack([points] + [np.atleast_2d(point) for point in new_points[1:]]),
            np.concatenate(kept_faces).astype(int),
            np.vstack([weights] + [np.atleast_2d(weight) for weight in new_weights[1:]]),
            np.concatenate([field, np.array(new_field[1:], float)]), np.concatenate(kept_cut))


def cut_piping(points, faces, weights, joint_places):
    """A garment piece with its piping cut in: (points, faces, weights, each face's piping flag). `joint_places` maps
    joint names to their bind places. A face is piping where its middle lies on a limb's outer half within its run and
    within half PIPING_WIDTH of the line (the cuts put its corners on the strip's edges)."""
    limbs = [(np.array([joint_places[side + name] for name in chain]), sign, run)
             for side, sign in (("Left", 1.0), ("Right", -1.0)) for chain, run in zip(CHAINS, (ARM_RUN, LEG_RUN))]
    for places, sign, run in limbs:
        across, usable = across_outer_line(points, places, sign, run)
        cut = usable[faces].all(1)
        field = np.where(usable, across, 0.0)
        for level in (-PIPING_WIDTH / 2, PIPING_WIDTH / 2):
            points, faces, weights, field, cut = split_at(points, faces, weights, field, level, cut)
    strip = np.zeros(len(faces), bool)
    middles = points[faces].mean(1)
    for places, sign, run in limbs:
        across, usable = across_outer_line(middles, places, sign, run)
        strip |= usable & (np.abs(across) < PIPING_WIDTH / 2)
    return points, faces, weights, strip
