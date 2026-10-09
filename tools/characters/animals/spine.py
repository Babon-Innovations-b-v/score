"""The fish's spine rig, worked out in plain numpy (job characters-full, 2026-10-09): no rigger knows a fish, and a
fish swims by one travelling bend down its body, so a chain of bones along the body's long axis is the whole rig.

    axes = body_axes(points)                      # its long axis (head first), its height and its width
    joints = spine_joints(points, axes, count)    # count + 1 points from the snout to the tail's tip
    weights = spine_weights(points, joints)       # (points, count): each point split between two bones

A point is weighted by where it lies along the spine alone, so a fin follows the spine bone it sits beside, and the
weights change smoothly from one bone to the next (no crease where two meet). Blender (rig_fish.py) and the tests
use the same functions.
"""
import numpy as np

# How much of each end is measured to tell the head from the tail: the head end is the thicker one (a tang's tail is
# a thin stalk and a flat fin).
END_SHARE = 0.2


def horizontal_axis(points, up=(0.0, 0.0, 1.0)):
    """The cloud's centre and its longest direction across `up` (the model stands as it was drawn, so its length is
    level), as a unit vector of unknown sign."""
    points = np.asarray(points, np.float64)
    up = np.asarray(up, np.float64)
    centre = points.mean(axis=0)
    flat = (points - centre) - np.outer((points - centre) @ up, up)
    _, _, directions = np.linalg.svd(flat, full_matrices=False)
    return centre, directions[0]


def thickness_at_ends(points, centre, along, across):
    """The mean distance from the body's middle plane across it, in the first and the last END_SHARE of its length."""
    position = (points - centre) @ along
    low, high = position.min(), position.max()
    reach = (high - low) * END_SHARE
    width = np.abs((points - centre) @ across)
    return width[position <= low + reach].mean(), width[position >= high - reach].mean()


def body_axes(points, up=(0.0, 0.0, 1.0)):
    """The body's long axis pointing to the head, its up and its width axis, as unit vectors. The long axis is the
    longest level direction; the head end is the thicker one."""
    points = np.asarray(points, np.float64)
    up = np.asarray(up, np.float64)
    centre, along = horizontal_axis(points, up)
    width = np.cross(along, up)
    back, front = thickness_at_ends(points, centre, along, width)
    if back > front:
        along, width = -along, -width
    return {"centre": centre, "along": along, "up": up, "width": width}


def spine_joints(points, axes, count):
    """`count` + 1 points on the long axis through the centre, evenly spaced from the snout to the tail's tip."""
    points = np.asarray(points, np.float64)
    position = (points - axes["centre"]) @ axes["along"]
    front, back = position.max(), position.min()
    steps = np.linspace(front, back, count + 1)
    return axes["centre"] + steps[:, None] * axes["along"][None, :]


def spine_weights(points, joints):
    """Each point's weight on each of the len(joints) - 1 bones: split between the two bones whose middles it lies
    between, by how far along it lies; points past the first or last middle go wholly to that bone."""
    points = np.asarray(points, np.float64)
    joints = np.asarray(joints, np.float64)
    count = len(joints) - 1
    start, finish = joints[0], joints[-1]
    length = np.linalg.norm(finish - start)
    direction = (finish - start) / length
    place = np.clip((points - start) @ direction / length * count - 0.5, 0.0, count - 1)
    lower = np.floor(place).astype(int)
    upper = np.minimum(lower + 1, count - 1)
    share = place - lower
    weights = np.zeros((len(points), count))
    rows = np.arange(len(points))
    weights[rows, lower] += 1.0 - share
    weights[rows, upper] += share
    return weights
