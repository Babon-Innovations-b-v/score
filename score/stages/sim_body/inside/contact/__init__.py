"""The body on the scene's ground: the colliders' surface points (`surface`), the person's drawn skin riding the
body's bones (`Skin`: SOMA's mesh, linear blend over the segments each bone carries), its lowest point's height over
the ground, the whole skin's and each part's (`lowests`) and the skin points the ground pushes with their push directions and where (`pushes`: within GAP of
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


class Chains:
    """Which dofs move each body (bodies x dofs, MuJoCo's `mj_jac` chain: the dofs of the body and its ancestors) and
    each body's tree root, made once for a model."""

    def __init__(self, model):
        self.moves = np.zeros((model.nbody, model.nv), dtype=bool)
        for body in range(model.nbody):
            dof = model.body_dofadr[body] + model.body_dofnum[body] - 1 if model.body_dofnum[body] else -1
            walk = body
            while dof < 0 and walk > 0:  # a body with no dofs of its own moves with its nearest ancestor's
                walk = model.body_parentid[walk]
                dof = model.body_dofadr[walk] + model.body_dofnum[walk] - 1 if model.body_dofnum[walk] else -1
            while dof >= 0:
                self.moves[body, dof] = True
                dof = model.dof_parentid[dof]
        self.roots = np.asarray(model.body_rootid)


def pushes_all(model, states, ground, up, skin, chains):
    """`pushes` of every state at once (`states`: `batched.Card.evaluate`'s dict of each state's xpos, xmat, cdof,
    subtree_com and qvel), the skin carried, its ground under it (every state's points in one `standing`, each with
    its state's reach) and every touching point's Jacobian for all states together (`mj_jac`'s sum over the point's
    body's dofs, `Chains`): a list of each state's pushes, the same tuples, and each skin point's height over its
    ground (states x points, nan where it has none: `lowests`')."""
    count = len(states["qvel"])
    if not len(skin.points):  # no skin: nothing to push
        return [[] for _ in range(count)], np.zeros((count, 0))
    weights = skin.weights
    points, segments = np.nonzero(weights)
    shares = weights[points, segments]
    bodies = np.asarray(skin.bodies)[segments]
    turns = TO_OWN @ states["xmat"].reshape(count, -1, 3, 3)  # each body's frame in the person's frame
    places = states["xpos"].reshape(count, -1, 3) @ TO_OWN.T
    poses = np.zeros((count, len(skin.bodies), 4, 4))
    poses[:, :, :3, :3] = turns[:, skin.bodies]
    poses[:, :, :3, 3] = places[:, skin.bodies]
    poses[:, :, 3, 3] = 1.0
    moves = poses @ skin.riding @ skin.unbound  # states x segments x 4 x 4
    carried = moves[:, segments]  # states x pairs x 4 x 4
    carried = np.einsum("fpij,pj->fpi", carried[..., :3, :3], skin.points[points]) + carried[..., :3, 3]
    own = np.zeros((count, len(skin.points), 3))
    for axis in range(3):
        own[:, :, axis] = np.array([np.bincount(points, shares * carried[state, :, axis], len(skin.points))
                                    for state in range(count)])
    cdof = states["cdof"].reshape(count, model.nv, 6)
    com = states["subtree_com"].reshape(count, -1, 3)
    reach = np.repeat([body_reach(mine) for mine in own], own.shape[1])  # each state's own reach, point by point
    every_height, every_triangle = (values.reshape(count, -1) for values in standing(own.reshape(-1, 3), ground, reach))
    found = []
    for state in range(count):
        mine, heights, triangles = own[state], every_height[state], every_triangle[state]
        over = mine[:, 1] - np.nan_to_num(heights, nan=np.inf)
        touching = np.flatnonzero(over <= GAP)
        pairs = np.flatnonzero(np.isin(points, touching))
        at = carried[state, pairs] @ TO_OWN  # MuJoCo's frame (TO_OWN.T applied to each point)
        offset = at - com[state, chains.roots[bodies[pairs]]]
        motion = np.cross(cdof[state, None, :, :3], offset[:, None, :]) + cdof[state, None, :, 3:]  # pairs x nv x 3
        motion *= chains.moves[bodies[pairs]][:, :, None]
        local = np.searchsorted(touching, points[pairs])  # each pair's touching point
        jacobians = np.zeros((len(touching), 3, model.nv))
        np.add.at(jacobians, local, shares[pairs, None, None] * np.swapaxes(motion, 1, 2))
        found.append([pushed(skin, point, jacobians[number], up[triangles[point]], states["qvel"][state], over[point],
                             [mine[point, 0], heights[point], mine[point, 2]])
                      for number, point in enumerate(touching)])
    return found, own[:, :, 1] - every_height


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


def lowest_of(heights):
    """The least of some heights (metres); None when none is over any ground (all nan, or none at all)."""
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def lowests(model, data, skin, ground, parts):
    """The lowest of the skin's points over the ground within the body's reach (metres), and of each part's points
    ({part: its points' indices}); None where none is over any of it. The skin is placed and its heights found once
    for all of them (#70: a point's height is its own, so a part's are the whole skin's at its points)."""
    placed = skin.placed(model, data)
    heights = heights_over(placed, ground, body_reach(placed))
    return lowest_of(heights), {part: lowest_of(heights[points]) if len(points) else None
                              for part, points in parts.items()}


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
        found.append(pushed(skin, point, skin.jacobian(model, data, carried, point), up[triangles[point]], data.qvel,
                            over[point], [own[point, 0], heights[point], own[point, 2]]))
    return found


def pushed(skin, point, along, up, qvel, over, under):
    """One touching skin point's push (`pushes`' tuple): its Jacobian `along` (3 x nv, MuJoCo's frame), its
    triangle's upward normal `up` (the person's frame), the body's speeds `qvel`, its height `over` its ground and the
    ground's point `under` it (the person's frame)."""
    normal = TO_OWN.T @ up
    moving = along @ qvel
    slip = moving - (moving @ normal) * normal
    if np.linalg.norm(moving) > SLIDE_MOST and np.linalg.norm(slip) > 0:
        edges = [normal - FRICTION * slip / np.linalg.norm(slip)]
    else:
        first = np.cross(normal, [1.0, 0.0, 0.0] if abs(normal[0]) < 0.9 else [0.0, 1.0, 0.0])
        first /= np.linalg.norm(first)
        second = np.cross(normal, first)
        edges = [normal + FRICTION * first, normal - FRICTION * first, normal + FRICTION * second,
                 normal - FRICTION * second]
    return skin.owners[point], along, [closeness(over) * edge for edge in edges], TO_OWN.T @ np.asarray(under, float)
