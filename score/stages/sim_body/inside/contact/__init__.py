"""The body on the scene's ground: the colliders' surface points (`surface`), the person's drawn skin riding the
body's bones (`Skin`: SOMA's mesh, linear blend over the segments each bone carries), its lowest point's height over
the ground (`lowest_over`) and the skin points the ground pushes with their push directions and where (`pushes`: within GAP of
the drawn triangle under them or into it, a friction pyramid under SLIDE_MOST, else sliding). Nothing here moves the
body: it stands where the fit to SOMA puts it (#70)."""
import mujoco
import numpy as np

from ground import body_reach, heights_over, standing
from model import TO_OWN, own_pose

# The ground pushes only a skin point touching it: within GAP of its drawn triangle or into it, the same 5 mm the
# stage's `lands` gate takes a landed foot within (`_gates.LANDED`).
GAP = 0.005  # metres
SLIDE_MOST = 1.2  # m/s
FRICTION = 0.5


class Skin:
    """The person's drawn surface, SOMA's skin, carried by the body's bones: each segment rides its bone
    (`riding`), and each skin point is the linear blend of the segments its weights name, so a seat, a bed or a ledge
    it touches carries it as a floor carries a foot (2026-11-01: MyoFullBody's colliders stood 16 to 27 mm inside a
    seated astronaut's skin, which sat 10 mm into its floor, so nothing carried his weight)."""

    def __init__(self, points, weights, binds, bodies, riding):
        """`points` the skin at its bind (v x 3, the person's frame), `weights` each point's share per segment (v x
        segments), `binds` each segment's frame at the bind standing where `riding` stands it, its group's start
        (segments x 4 x 4: `landmarks.at_starts`), `bodies` the body each segment rides and `riding` its frame on
        that body (segments x 4 x 4)."""
        self.points, self.weights = np.asarray(points, float), np.asarray(weights, float)
        self.unbound = np.linalg.inv(np.asarray(binds, float))
        self.bodies, self.riding = list(bodies), np.asarray(riding, float)
        self.owners = np.asarray(self.bodies)[self.weights.argmax(axis=1)]  # the body a point's force is booked on

    def by_segment(self, model, data):
        """Each skin point as each segment alone carries it now (v x segments x 3, the person's frame)."""
        moves = np.array([own_pose(model, data, body) for body in self.bodies]) @ self.riding @ self.unbound
        return np.einsum("sij,vj->vsi", moves[:, :3, :3], self.points) + moves[None, :, :3, 3]

    def placed(self, model, data):
        """The skin now (v x 3, the person's frame)."""
        return np.einsum("vs,vsi->vi", self.weights, self.by_segment(model, data))

    def jacobian(self, model, data, carried, point):
        """A skin point's Jacobian (3 x nv, MuJoCo's frame): its segments' points' Jacobians on their bodies,
        blended by its weights; `carried` is `by_segment`'s."""
        found, along = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        for segment in np.flatnonzero(self.weights[point]):
            mujoco.mj_jac(model, data, along, None, TO_OWN.T @ carried[point, segment], self.bodies[segment])
            found += self.weights[point, segment] * along
        return found


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


def lowest_over(model, data, skin, ground, points=None):
    """The lowest of the skin's points (`points`, else all) over the ground within the body's reach (metres); None
    when none is over any of it."""
    placed = skin.placed(model, data)
    heights = heights_over(placed if points is None else placed[points], ground, body_reach(placed))
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def closeness(over):
    """How near a skin point `over` metres above its ground is (0 at GAP, 1 on or into it): the length of its push
    directions, so the solve's cost of its push grows as it nears GAP (a push of x newtons along them costs x over its
    closeness) and a point coming within GAP takes its share of the load from nothing, never all at once (2026-11-05,
    #70: points crossing GAP whole moved a foot's centre of pressure 3 to 6 cm a frame)."""
    return float(np.clip((GAP - over) / GAP, 0.0, 1.0))


def pushes(model, data, ground, up, skin):
    """The points the ground pushes ([(body, point's Jacobian, the directions it may push along, each `closeness`
    long, the ground's point under it)], MuJoCo's frame):
    the skin's points within GAP of the drawn ground under them (within the body's reach, `body_reach`: a roof over
    its head is never pushing ground), or into it, each pushed along its triangle's normal (`up`, the person's frame)
    with Coulomb's friction: a point slower than SLIDE_MOST sticks (a friction pyramid, FRICTION), a faster one slides
    (the normal and FRICTION of it against its slip); booked on the body its heaviest segment rides, acting at the
    ground straight under the point (its height there, `standing`: a seat's top under a seated body's skin). Each
    point's directions are as long as it is near (`closeness`), so a point's push fades to nothing at GAP."""
    found = []
    carried = skin.by_segment(model, data)
    own = np.einsum("vs,vsi->vi", skin.weights, carried)
    heights, triangles = standing(own, ground, body_reach(own))
    over = own[:, 1] - np.nan_to_num(heights, nan=np.inf)
    for point in np.flatnonzero(over <= GAP):
        along = skin.jacobian(model, data, carried, point)
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
        under = TO_OWN.T @ np.array([own[point, 0], heights[point], own[point, 2]])
        found.append((skin.owners[point], along, [closeness(over[point]) * edge for edge in edges], under))
    return found
