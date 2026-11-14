"""The body on the scene's ground: the colliders' surface points (`surface`), the person's drawn skin riding the
body's bones (`Skin`: SOMA's mesh, linear blend over the segments each bone carries), its lowest point's height over
the ground, the whole skin's and each part's (`lowests`) and the skin points the ground pushes with their push directions and where (`pushes`: within GAP of
the drawn triangle under them or into it, or of a back along its normal, a friction pyramid under SLIDE_MOST, else
sliding). Nothing here moves the
body: it stands where the fit to SOMA puts it (#70)."""
import mujoco
import numpy as np

from ground import body_floor, body_reach, body_top, heights_over, leaning, standing
from model import TO_OWN, own_pose

# The ground pushes only a skin point touching it: within GAP of its drawn triangle or into it, the same 5 mm the
# stage's `lands` gate takes a landed foot within (`_gates.LANDED`).
GAP = 0.005  # metres
# A foot the video shows standing (the job's seen stance: on LabValidation GEM-X's static contact or the stage's own
# stance on the clip, tools/labval `_soma.seen_stance`) is pushed from its own lowest skin point, up to STANCE_HIGH over
# its ground: the video's feet stand a few millimetres to centimetres off the floor where its legs' lengths and the
# foot's shape miss (#98, 2026-11-07: the deepest squat's right sole 18 to 28 mm up while GEM-X held it static, so only
# the left foot was pushed and only its calf worked). A foot higher than that, or not seen standing, is pushed only
# within GAP as any skin is; nothing moves the body. STANCE_HIGH tuned on LabValidation's subjects 2 to 5 (36 trials,
# against their plates; never on the reference's angles): 30 mm per-foot vertical force RMSE 28.5/28.1% of the weight,
# 50 mm 28.1/26.7, 80 mm no better (24 trials); GAP 10 mm and the balance's SHARE_COST 0.1 no better.
STANCE_HIGH = 0.05  # metres
REGISTERED_FRAMES = 60  # frames spread over a clip that lay each segment's skin on SOMA's (`Skin.registered`)
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
        self.credit = None  # frames x points: how far over its ground each point is pushed from (`credited`)

    def registered(self, carried, soma):
        """This skin with each segment's riding moved by the one rigid turn and shift that best lays the segment's
        skin, as the fitted path carries it, on SOMA's own over the clip (Kabsch: the least squares over the points the
        segment carries most, on REGISTERED_FRAMES frames spread over the clip): `carried` each segment's frame
        riding its bone (frames x segments x 4 x 4, `model.posed_path`), `soma` SOMA's segment frames standing where
        `binds` stands each one (frames x segments x 4 x 4). The fit follows SOMA's markers, not its joints: carried
        from MyoFullBody's ankle, a foot's skin stood 5 to 11 mm over SOMA's on the median, turned 4 to 6 degrees
        (#98, 2026-11-07, LabValidation's subjects 2, 3 and 5), so the ground missed feet SOMA stood on."""
        frames = np.unique(np.linspace(0, len(carried) - 1, min(REGISTERED_FRAMES, len(carried))).astype(int))
        riding = np.array(self.riding)
        for segment in range(len(self.bodies)):
            mine = np.flatnonzero(self.weights.argmax(axis=1) == segment)
            if len(mine) < 3:
                continue
            local = self.points[mine] @ self.unbound[segment, :3, :3].T + self.unbound[segment, :3, 3]
            seen = np.linalg.inv(carried[frames, segment]) @ soma[frames, segment]  # SOMA's frame in the carried one
            wanted = (np.einsum("fij,pj->fpi", seen[:, :3, :3], local) + seen[:, None, :3, 3]).reshape(-1, 3)
            given = np.tile(local, (len(frames), 1))
            riding[segment] = riding[segment] @ kabsch(given, wanted)
        found = Skin(self.points, self.weights, np.linalg.inv(self.unbound), self.bodies, riding)
        found.credit = self.credit
        return found

    def credited(self, lowest, stance, feet):
        """This skin's `credit` set: on each frame a foot is seen standing (`stance`, frames x feet) and its lowest
        point stands within STANCE_HIGH over its ground (`lowest`, frames x feet, m, nan where none), each point it
        carries most (`feet`, each foot's bodies) is pushed from that height, as if the ground stood at its sole."""
        credit = np.zeros((len(stance), len(self.points)))
        for foot, bodies in enumerate(feet):
            mine = np.isin(self.owners, list(bodies))
            lifted = np.where(np.asarray(stance)[:, foot] & (np.nan_to_num(lowest[:, foot], nan=np.inf) <= STANCE_HIGH),
                              np.clip(np.nan_to_num(lowest[:, foot]), 0.0, STANCE_HIGH), 0.0)
            credit[:, mine] = lifted[:, None]
        self.credit = credit

    def credit_of(self, count):
        """Each of `count` states' credit (states x points): a state is a frame of the clip, or of a whole copy of it
        stacked; none when the skin has no credit."""
        if self.credit is None:
            return np.zeros((count, len(self.points)))
        if count % len(self.credit):
            raise ValueError(f"{count} states: not whole copies of the clip's {len(self.credit)} frames")
        return self.credit[np.arange(count) % len(self.credit)]

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


def kabsch(given, wanted):
    """The rigid motion (4 x 4) that best takes the points `given` onto `wanted` (n x 3 each), least squares
    (Kabsch 1976, its reflection kept out)."""
    middle_given, middle_wanted = given.mean(axis=0), wanted.mean(axis=0)
    left, _, right = np.linalg.svd((wanted - middle_wanted).T @ (given - middle_given))
    turn = left @ np.diag([1.0, 1.0, np.sign(np.linalg.det(left @ right))]) @ right
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = turn, middle_wanted - turn @ middle_given
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


def on_ground_all(model, states, ground, skin):
    """`pushes_all`'s and `touching_all`'s skin of every state (`states`: `batched.Card.evaluate`'s xpos and xmat)
    carried and stood on its ground: the weights' (point, segment) pairs, their shares and bodies, each pair's point
    as its segment carries it (states x pairs x 3) and each skin point's (states x points x 3, the person's frame),
    and each point's ground height and triangle (states x points, nan and -1 where none is)."""
    count = len(states["xpos"])
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
    reach = np.repeat([body_reach(mine) for mine in own], own.shape[1])  # each state's own reach, point by point
    floor = np.repeat([body_floor(mine) for mine in own], own.shape[1])  # ... and floor
    top = np.repeat([body_top(mine) for mine in own], own.shape[1])  # ... and top
    every_height, every_triangle = (values.reshape(count, -1)
                                    for values in standing(own.reshape(-1, 3), ground, reach, floor, top))
    return points, segments, shares, bodies, carried, own, every_height, every_triangle


def backs_all(own, ground):
    """Every state's skin points' backs (`ground.leaning`'s distance, triangle, normal and foot, states x points),
    within GAP, each state's own body's middle (its skin's median) the side a back pushes to and its `body_floor` the
    height a point leans over (`own`: on_ground_all's skin, states x points x 3)."""
    count, many = own.shape[:2]
    middles = np.repeat(np.median(own, axis=1), many, axis=0)
    floors = np.repeat([body_floor(mine) for mine in own], many)
    return [values.reshape(count, many, *values.shape[1:])
            for values in leaning(own.reshape(-1, 3), ground, middles, GAP, floors)]


def leaned(leans, state, triangles):
    """The points of `state` a back pushes (`leaning`'s `leans`, every state's): those within GAP of one that is not
    the triangle their ground is (`triangles`, the state's, `standing`'s: a point on a steep slope it stands on is
    pushed once)."""
    distance, triangle = leans[0][state], leans[1][state]
    return np.flatnonzero(np.isfinite(distance) & (triangle != triangles))


def pushes_all(model, states, ground, up, skin, chains):
    """`pushes` of every state at once (`states`: `batched.Card.evaluate`'s dict of each state's xpos, xmat, cdof,
    subtree_com and qvel), the skin carried, its ground under it (every state's points in one `standing`, each with
    its state's reach) and every touching point's Jacobian for all states together (`mj_jac`'s sum over the point's
    body's dofs, `Chains`): a list of each state's pushes, the same tuples, and each skin point's height over its
    ground (states x points, nan where it has none: `lowests`')."""
    count = len(states["qvel"])
    if not len(skin.points):  # no skin: nothing to push
        return [[] for _ in range(count)], np.zeros((count, 0))
    points, segments, shares, bodies, carried, own, every_height, every_triangle = on_ground_all(model, states, ground,
                                                                                                skin)
    leans = backs_all(own, ground)
    cdof = states["cdof"].reshape(count, model.nv, 6)
    com = states["subtree_com"].reshape(count, -1, 3)
    credit = skin.credit_of(count)
    found = []
    for state in range(count):
        mine, heights, triangles = own[state], every_height[state], every_triangle[state]
        over = mine[:, 1] - np.nan_to_num(heights, nan=np.inf) - credit[state]
        touching, backed = np.flatnonzero(over <= GAP), leaned(leans, state, triangles)
        every = np.union1d(touching, backed)
        pairs = np.flatnonzero(np.isin(points, every))
        at = carried[state, pairs] @ TO_OWN  # MuJoCo's frame (TO_OWN.T applied to each point)
        offset = at - com[state, chains.roots[bodies[pairs]]]
        motion = np.cross(cdof[state, None, :, :3], offset[:, None, :]) + cdof[state, None, :, 3:]  # pairs x nv x 3
        motion *= chains.moves[bodies[pairs]][:, :, None]
        local = np.searchsorted(every, points[pairs])  # each pair's touching point
        jacobians = np.zeros((len(every), 3, model.nv))
        np.add.at(jacobians, local, shares[pairs, None, None] * np.swapaxes(motion, 1, 2))
        on = np.searchsorted(every, touching)
        found.append([pushed(skin, point, jacobians[number], up[triangles[point]], states["qvel"][state], over[point],
                             [mine[point, 0], heights[point], mine[point, 2]])
                      for number, point in zip(on, touching)]
                     + [pushed(skin, point, jacobians[number], leans[2][state, point], states["qvel"][state],
                               leans[0][state, point], leans[3][state, point])
                        for number, point in zip(np.searchsorted(every, backed), backed)])
    return found, own[:, :, 1] - every_height


def touching_all(model, states, ground, up, skin):
    """Each state's touching skin points as the balance of the pelvis reads them (`states`: `batched.Card.evaluate`'s
    xpos, xmat, cvel and subtree_com, and qvel), `pushes_all`'s points without their Jacobians: [(each point's place
    blended over its segments, MuJoCo's frame (points x 3), its weights' sum (points), its push directions
    (`pyramids`, points x 4 x 3) and how many it has)] a state. A push e at the point gives the root the wrench
    (sum e, place x e - sum origin x e); a point's speed is its segments' points' on their bodies (MuJoCo's cvel:
    the body's turn and the speed at its tree's centre of mass), blended, as `pushes`' Jacobian times the speeds."""
    count = len(states["xpos"])
    if not len(skin.points):  # no skin: nothing to push
        return [(np.zeros((0, 3)), np.zeros(0), np.zeros((0, 4, 3)), np.zeros(0, int)) for _ in range(count)]
    points, _, shares, bodies, carried, own, every_height, every_triangle = on_ground_all(model, states, ground, skin)
    leans = backs_all(own, ground)
    summed = np.bincount(points, shares, len(skin.points))
    cvel = states["cvel"].reshape(count, -1, 6)
    com = states["subtree_com"].reshape(count, -1, 3)
    roots = np.asarray(model.body_rootid)[bodies]
    credit = skin.credit_of(count)
    found = []
    for state in range(count):
        over = own[state, :, 1] - np.nan_to_num(every_height[state], nan=np.inf) - credit[state]
        touching, backed = np.flatnonzero(over <= GAP), leaned(leans, state, every_triangle[state])
        every = np.concatenate([touching, backed])  # a point a back and its ground push is pushed by both
        pairs = np.flatnonzero(np.isin(points, every))
        at = carried[state, pairs] @ TO_OWN  # MuJoCo's frame
        speed = cvel[state, bodies[pairs]]
        speed = speed[:, 3:] + np.cross(speed[:, :3], at - com[state, roots[pairs]])
        unique = np.unique(every)
        local = np.searchsorted(unique, points[pairs])
        moving = np.zeros((len(unique), 3))
        np.add.at(moving, local, shares[pairs, None] * speed)
        moving = moving[np.searchsorted(unique, every)]
        ups = np.concatenate([up[every_triangle[state, touching]], leans[2][state, backed]])
        edges, counts = pyramids(ups, moving, np.concatenate([over[touching], leans[0][state, backed]]))
        found.append((own[state, every] @ TO_OWN, summed[every], edges, counts))
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


def lowest_of(heights):
    """The least of some heights (metres); None when none is over any ground (all nan, or none at all)."""
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def lowests(model, data, skin, ground, parts):
    """The lowest of the skin's points over the ground within the body's reach (metres), and of each part's points
    ({part: its points' indices}); None where none is over any of it. The skin is placed and its heights found once
    for all of them (#70: a point's height is its own, so a part's are the whole skin's at its points)."""
    placed = skin.placed(model, data)
    heights = heights_over(placed, ground, body_reach(placed), body_floor(placed), body_top(placed))
    return lowest_of(heights), {part: lowest_of(heights[points]) if len(points) else None
                              for part, points in parts.items()}


def closeness(over):
    """How near each skin point `over` metres above its ground is (one height or an array of them; 0 at GAP, 1 on or
    into it): the length of its push directions, so the solve's cost of its push grows as it nears GAP (a push of x
    newtons along them costs x over its closeness) and a point coming within GAP takes its share of the load from
    nothing, never all at once (2026-11-05, #70: points crossing GAP whole moved a foot's centre of pressure 3 to 6 cm
    a frame)."""
    return np.clip((GAP - np.asarray(over, float)) / GAP, 0.0, 1.0)


def pushes(model, data, ground, up, skin, frame=0):
    """The points the ground pushes ([(body, point's Jacobian, the directions it may push along, each `closeness`
    long, the ground's point under it)], MuJoCo's frame):
    the skin's points within GAP of the drawn ground under them (within the body's reach, `body_reach`: a roof over
    its head is never pushing ground), or into it, each pushed along its triangle's normal (`up`, the person's frame)
    with Coulomb's friction: a point slower than SLIDE_MOST sticks (a friction pyramid, FRICTION), a faster one slides
    (the normal and FRICTION of it against its slip); booked on the body its heaviest segment rides, acting at the
    ground straight under the point (its height there, `standing`: a seat's top under a seated body's skin). Each
    point's directions are as long as it is near (`closeness`), so a point's push fades to nothing at GAP; a point of a
    foot seen standing is measured from its credit on `frame` (`Skin.credited`). A point within GAP of a back (a steep
    triangle, `ground.leaning`: a seat's back, a wall), in front of it or in it, over a knee above the body's lowest
    point (`body_floor`: a riser the toe meets is no back), is pushed along its normal towards
    the body's middle (the median of its skin) as a floor pushes, from the foot of the point on it, once more where
    its ground is not that triangle: a seated pilot leans on his seat's back."""
    found = []
    carried = skin.by_segment(model, data)
    own = np.einsum("vs,vsi->vi", skin.weights, carried)
    heights, triangles = standing(own, ground, body_reach(own), body_floor(own), body_top(own))
    over = own[:, 1] - np.nan_to_num(heights, nan=np.inf)
    if skin.credit is not None:
        over = over - skin.credit[frame % len(skin.credit)]
    for point in np.flatnonzero(over <= GAP):
        found.append(pushed(skin, point, skin.jacobian(model, data, carried, point), up[triangles[point]], data.qvel,
                            over[point], [own[point, 0], heights[point], own[point, 2]]))
    leans = [values[None] for values in leaning(own, ground, np.median(own, axis=0), GAP, body_floor(own))]
    for point in leaned(leans, 0, triangles):
        found.append(pushed(skin, point, skin.jacobian(model, data, carried, point), leans[2][0, point], data.qvel,
                            leans[0][0, point], leans[3][0, point]))
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


def pyramids(ups, moving, overs):
    """Each touching point's push directions (points x 4 x 3, MuJoCo's frame) and how many of them it has (points),
    `pushed`'s rule for many points at once (the contact test holds the two equal): along its triangle's upward
    normal (`ups`, the person's frame) with Coulomb's friction, a point slower than SLIDE_MOST (`moving`, its speed,
    MuJoCo's frame) a friction pyramid (four), a faster one the normal and FRICTION of it against its slip (one, the
    first), each as long as the point is near (`closeness` of its height `overs`)."""
    normals = ups @ TO_OWN  # TO_OWN.T applied to each normal
    slip = moving - np.einsum("ij,ij->i", moving, normals)[:, None] * normals
    slips = np.linalg.norm(slip, axis=1)
    sliding = (np.linalg.norm(moving, axis=1) > SLIDE_MOST) & (slips > 0)
    side = np.where(np.abs(normals[:, :1]) < 0.9, [[1.0, 0.0, 0.0]], [[0.0, 1.0, 0.0]])
    first = np.cross(normals, side)
    first /= np.linalg.norm(first, axis=1, keepdims=True)
    second = np.cross(normals, first)
    edges = np.stack([normals + FRICTION * first, normals - FRICTION * first, normals + FRICTION * second,
                      normals - FRICTION * second], axis=1)
    edges[sliding, 0] = normals[sliding] - FRICTION * slip[sliding] / slips[sliding, None]
    return edges * closeness(overs)[:, None, None], np.where(sliding, 1, 4)
