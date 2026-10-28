"""The body's feet on the scene's ground: the colliders' surface points (`surface`), the lowest one's height over the
ground (`lowest_over`), the foot segments standing in each frame of the clip (`stances`, Kovar et al. 2002), the
foot points the fit holds on and out of the ground (`on_ground`) and a planted foot's slip (`unslipped`), the path
moved once so it stands on the ground (`grounded`), and the points the ground pushes with their push directions
(`pushes`: within GAP of the drawn triangle under them or into it, a friction pyramid under SLIDE_MOST, else
sliding)."""
import mujoco
import numpy as np

from bone_groups import FEET
from ground import heights_over, standing
from model import TO_OWN

# A foot segment (FEET) stands on its ground in a frame when its SOMA joint moves slower than STILL and stands within
# LOW of its calibration height over its ground (Kovar, Schreiner and Gleicher 2002, "Footskate cleanup for motion
# capture editing": contacts found by the joint's height and speed, then held by the fit).
STILL = 0.5  # m/s
LOW = 0.02  # metres
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


def stances(standing_frame, segments, worlds, ground, rate):
    """The foot segments standing on the ground, frame by frame ([{segment}]): its SOMA joint slower than STILL and
    no more than LOW higher over its ground than it stands in the calibration frame (`standing_frame`, segments x 4 x
    4) over the rig's floor (Kovar et al. 2002)."""
    found = [set() for _ in worlds]
    for number, segment in enumerate(segments):
        if segment.endswith(FEET):
            places = worlds[:, number, :3, 3]
            speed = np.linalg.norm(np.gradient(places, 1.0 / rate, axis=0), axis=1)
            low = heights_over(places, ground) <= standing_frame[number][1, 3] + LOW
            for frame in np.flatnonzero(low & (speed < STILL)):
                found[frame].add(segment)
    return found


def on_ground(model, data, ground, feet, planted):
    """The foot points the fit holds now ([(point, its body, how far it must rise)], MuJoCo's frame): each planted
    body's lowest collider point onto the ground, and every point of `feet` ({body: geoms}) under the ground or within
    GAP over it out of it (one that is over it rises by 0 but stays in the fit, so the fit's next step cannot put it
    back in: the one-sided bound's active set)."""
    found = []
    for body, geoms in feet.items():
        points = surface(model, data, geoms)
        heights = heights_over(points @ TO_OWN.T, ground)
        if np.isnan(heights).all():
            continue
        rise = {point: max(-heights[point], 0.0) for point in np.flatnonzero(heights < GAP)}
        if body in planted:
            rise[int(np.nanargmin(heights))] = -heights[int(np.nanargmin(heights))]
        found += [(points[point], body, rise[point]) for point in sorted(rise)]
    return found


def unslipped(model, data, before, ground, feet, planted):
    """Each planted body's lowest collider point now and how far it moved across the ground since the frame `before`
    ([(point, its body, its slip: MuJoCo's x and y)]): the material point in contact stands still, so a foot standing
    on its ground rolls on it but never slides (Kovar, Schreiner and Gleicher 2002 hold a planted foot's place; a held
    height alone let the rig walk's toe slide 6 cm in a frame at heel-off, 1.8 m/s, 2026-10-28)."""
    found = []
    for body in planted:
        points = surface(model, data, feet[body])
        heights = heights_over(points @ TO_OWN.T, ground)
        if np.isnan(heights).all():
            continue
        point = points[int(np.nanargmin(heights))]
        local = data.xmat[body].reshape(3, 3).T @ (point - data.xpos[body])
        then = before.xpos[body] + before.xmat[body].reshape(3, 3) @ local
        found.append((point, body, (point - then)[:2]))
    return found


def grounded(model, path, colliders, ground, name):
    """The path moved once up or down so its lowest collider point stands on its ground at the median frame, and that
    move (m). A walk always has a foot on its ground, so each frame's lowest point should be on it; the median frame's
    is (the frame 0 rule left the Kimodo walker's feet standing 2 to 3 cm over it once its legs followed the clip, and
    MuscleMimic's lowest over all frames lifted it 2.3 cm, with frames carried by nothing, 2026-10-27)."""
    data, lowest = mujoco.MjData(model), []
    for qpos in path:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        lowest.append(lowest_over(model, data, colliders, ground))
    lowest = [over for over in lowest if over is not None]
    if not lowest:
        raise SystemExit(f"{name}: no ground under its body in any frame")
    over = float(np.median(lowest))
    moved = path.copy()
    moved[:, 2] -= over  # MuJoCo's up
    return moved, -over


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
