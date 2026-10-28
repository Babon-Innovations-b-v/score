"""The body's feet on the scene's ground: the colliders' surface points (`surface`), the lowest one's height over the
ground (`lowest_over`) and the points the ground pushes with their push directions (`pushes`: within GAP of the drawn
triangle under them or into it, a friction pyramid under SLIDE_MOST, else sliding). Nothing here moves the body: it
stands where the fit to SOMA puts it (#70)."""
import mujoco
import numpy as np

from ground import heights_over, standing
from model import TO_OWN

# The ground pushes only a foot point touching it: within GAP of its drawn triangle or into it (MuJoCo's contact: a
# geom meets the ground within its margin, MyoFullBody's foot colliders' 1 mm, and rests 0.1 to 0.4 mm into it under
# the body's weight with MuJoCo's default solref and solimp, as MyoSuite, MuscleMimic and KINESIS leave them).
GAP = 0.005  # metres
SLIDE_MOST = 1.2  # m/s
FRICTION = 0.5


def surface(model, data, geoms):
    """Points round each collider (MuJoCo's frame): its surface sampled in 26 directions (a capsule's at both ends)."""
    directions = np.array([[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z], float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    found = []
    for geom in geoms:
        size, kind = model.geom_size[geom], model.geom_type[geom]
        if kind == mujoco.mjtGeom.mjGEOM_CAPSULE:
            local = np.concatenate([directions * size[0] + [0, 0, size[1]], directions * size[0] - [0, 0, size[1]]])
        elif kind == mujoco.mjtGeom.mjGEOM_BOX:
            local = np.sign(directions) * size
        elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
            local = directions * size[0]
        else:  # an ellipsoid
            local = directions * size
        found.append(local @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom])
    return np.concatenate(found)


def lowest_over(model, data, geoms, ground):
    """The lowest of `geoms`' collider points over the ground (metres); None when none is over any of it."""
    heights = heights_over(surface(model, data, geoms) @ TO_OWN.T, ground)
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def pushes(model, data, ground, up, colliders):
    """The points the ground pushes ([(body, point's Jacobian, the directions it may push along)], MuJoCo's frame):
    the colliders' surface points (`surface`) within GAP of the drawn ground under them, or into it, each pushed along
    its triangle's normal (`up`, the person's frame) with Coulomb's friction: a point slower than SLIDE_MOST sticks (a
    friction pyramid, FRICTION), a faster one slides (the normal and FRICTION of it against its slip)."""
    found, along = [], np.zeros((3, model.nv))
    points = [surface(model, data, [geom]) for geom in colliders]
    owners = np.concatenate([np.full(len(mine), model.geom_bodyid[geom]) for geom, mine in zip(colliders, points)])
    points = np.concatenate(points)
    own = points @ TO_OWN.T
    heights, triangles = standing(own, ground)
    for point in np.flatnonzero(own[:, 1] - np.nan_to_num(heights, nan=np.inf) <= GAP):
        mujoco.mj_jac(model, data, along, None, points[point], owners[point])
        normal = TO_OWN.T @ up[triangles[point]]
        moving = along @ data.qvel
        slip = moving - (moving @ normal) * normal
        if np.linalg.norm(moving) > SLIDE_MOST and np.linalg.norm(slip) > 0:
            edges = [normal - FRICTION * slip / np.linalg.norm(slip)]
        else:
            first = np.cross(normal, [1.0, 0.0, 0.0] if abs(normal[0]) < 0.9 else [0.0, 1.0, 0.0])
            first /= np.linalg.norm(first)
            second = np.cross(normal, first)
            edges = [normal + FRICTION * first, normal - FRICTION * first, normal + FRICTION * second,
                     normal - FRICTION * second]
        found.append((owners[point], along.copy(), edges))
    return found
