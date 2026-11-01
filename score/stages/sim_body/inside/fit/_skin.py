"""Bones inside SOMA's skin (#70's judgement, the audit's item 2): every EVERY-th frame, each bone mesh's vertices
(at most VERTS a mesh) tested against SOMA's skin posed on that frame (linear blend, as SOMA skins it) by the
generalised winding number (inside at 0.5 or more: warp's BVH winding query on the CPU, the rule main's harness
measures with), the share outside kept per region (REGIONS, the hand's parts (HAND) one region). The stage's record
and level 1's score (evaluation._measure) both measure through this one module. Level 1's least squares reads the
depth outside instead (`marks_kernel`: each point's distance to the skin's closest point when outside, 0 inside), smooth
where the share is a step (#70, 2026-10-30): the share stays the judged measure. Levels 2 and 3 hold the bones inside
too (#70, 2026-11-01, the owner: "we just know bones need to be inside the skin"): each kept bone vertex's depth outside
the frame's posed skin (`PosedSkins`, MuJoCo's frame) times `skin_cost` is the residual of both solves, as its offset
off the skin's closest point (`apart_kernel`: the same winding query, the closest point on the face it finds in
float64), whose Jacobian in the point is the projector off the closest feature (the face's normal, an edge's plane, a
corner's every axis): so a solve sees the skin's bend at its edges and corners, where a depth row's own Gauss-Newton
square misses it. Nothing here moves SOMA."""
import mujoco
import numpy as np
import warp

from model import TO_OWN

EVERY = 10  # frames between the skin measures
VERTS = 80  # bone vertices kept per mesh
REGIONS = {"shoulder": ("clavicle", "scapula", "humerus"), "forearm": ("ulna", "radius"),
           "fingers": ("ph_", "thumb"), "metacarpals": ("mc",),
           "carpals": ("lunate", "scaphoid", "pisiform", "triquetrum", "capitate", "trapezium", "trapezoid", "hamate"),
           "pelvis": ("pelvis", "sacrum"), "spine": ("lumbar", "thorax", "torso", "cervical", "neck", "rib"),
           "head": ("head", "skull", "jaw", "mandible"), "thigh": ("femur", "patella"), "shin": ("tibia", "fibula"),
           "foot": ("talus", "calcn", "toes")}
HAND = ("fingers", "metacarpals", "carpals")  # the hand's parts, scored together as "hand"
POCKET_REACH = 0.03  # m: a face whose outward normal meets the skin again this near is a pocket's wall
POCKET_SEGMENT = "Head"  # the segment whose pockets a closed face covers (lips, eyelids and eyes, nostrils, ears)
# The bones-in-skin goal of level 3 against the turns' 1 (`_frames.weights`): its rows sum to SKIN_GOAL times the
# mean over the kept bone vertices of their squared depth outside (m), each goal over its own count as OpenSim weighs
# its goals. Chosen from measurement (#70, 2026-11-01), never set to pass a score: on mean's 15 clips with the skin rows
# in level 3 only, bones outside 11.45 % (none) -> 9.57 / 6.95 / 4.88 % at 1e2 / 1e3 / 1e4, the turns 4.662 ->
# 4.61 / 4.603 / 4.735 deg: 1e3 the largest goal whose turns are no worse; env1's seated and standing astronauts read
# fewer bones outside at it too (fit/CLAUDE.md). Level 2 holds no skin rows: its polish did not settle with them.
SKIN_GOAL = 1.0e3
# A frame whose posed skin lies inside itself over FOLD_MOST of its area (a deep squat's or a kneel's skin folding into
# itself, which no skeleton can follow) is left out of the skin rows of levels 1 and 3 and out of the bones-outside
# share, and reported apart (the owner, 2026-11-01). A skin vertex lies inside itself when the point FOLD_IN in from it
# along its normal winds 1.5 or more. On the mean body's 15 clips (every 10th frame, main's fit, 2026-11-01) 81 of 281
# frames folded over 0.5 % held 79 % of the bones' squared depth outside, 24.8 % of their bone vertices outside
# against 16.0 % on the rest.
FOLD_MOST = 0.005
FOLD_IN = 0.001  # m

warp.config.quiet = True


@warp.kernel
def marks_kernel(meshes: warp.array(dtype=warp.uint64), points: warp.array2d(dtype=warp.vec3),
           signs: warp.array2d(dtype=float), depths: warp.array2d(dtype=float)):
    """Per (skin frame, point): the winding sign (outside at 0 or more) and the depth outside (m, 0 inside); the card's
    measure launches this same kernel."""
    shot, point = warp.tid()
    found = warp.mesh_query_point_sign_winding_number(meshes[shot], points[shot, point], 1.0e6, 2.0, 0.5)
    closest = warp.mesh_eval_position(meshes[shot], found.face, found.u, found.v)
    signs[shot, point] = found.sign
    depths[shot, point] = warp.where(found.sign >= 0.0, warp.length(points[shot, point] - closest), 0.0)


@warp.func
def _away(direction: warp.vec3d):
    """The projector off a feature along `direction` (an edge's): I - e e^T."""
    unit = warp.normalize(direction)
    return warp.identity(n=3, dtype=warp.float64) - warp.outer(unit, unit)


@warp.func
def closest_on_triangle(point: warp.vec3d, first: warp.vec3d, second: warp.vec3d, third: warp.vec3d):
    """The triangle's closest point to `point` in float64 (Ericson, Real-Time Collision Detection, 5.1.5) and the
    Hessian of half the squared distance to it there: the projector off the closest feature's span (n n^T on the face,
    I - e e^T on an edge, I at a corner)."""
    along = second - first
    across = third - first
    off = point - first
    d1 = warp.dot(along, off)
    d2 = warp.dot(across, off)
    found = first
    bend = warp.identity(n=3, dtype=warp.float64)
    if d1 > warp.float64(0.0) or d2 > warp.float64(0.0):
        off_second = point - second
        d3 = warp.dot(along, off_second)
        d4 = warp.dot(across, off_second)
        off_third = point - third
        d5 = warp.dot(along, off_third)
        d6 = warp.dot(across, off_third)
        vc = d1 * d4 - d3 * d2
        vb = d5 * d2 - d1 * d6
        va = d3 * d6 - d5 * d4
        if d3 >= warp.float64(0.0) and d4 <= d3:
            found = second
        elif vc <= warp.float64(0.0) and d1 >= warp.float64(0.0) and d3 <= warp.float64(0.0):
            found = first + along * (d1 / (d1 - d3))
            bend = _away(along)
        elif d6 >= warp.float64(0.0) and d5 <= d6:
            found = third
        elif vb <= warp.float64(0.0) and d2 >= warp.float64(0.0) and d6 <= warp.float64(0.0):
            found = first + across * (d2 / (d2 - d6))
            bend = _away(across)
        elif va <= warp.float64(0.0) and d4 - d3 >= warp.float64(0.0) and d5 - d6 >= warp.float64(0.0):
            found = second + (third - second) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))
            bend = _away(third - second)
        else:
            scale = warp.float64(1.0) / (va + vb + vc)
            found = first + along * (vb * scale) + across * (vc * scale)
            normal = warp.normalize(warp.cross(along, across))
            bend = warp.outer(normal, normal)
    return found, bend


@warp.func
def apart_of(mesh: warp.uint64, verts: warp.array(dtype=warp.vec3d), first_vert: int,
             faces: warp.array(dtype=warp.int32), ring_starts: warp.array(dtype=warp.int32),
             ring_faces: warp.array(dtype=warp.int32), point: warp.vec3d):
    """A point's offset off its skin (zero inside by the winding number, `marks_kernel`'s query on the float32 mesh)
    and the offset's Jacobian in the point (`closest_on_triangle`'s projector, zero inside). The closest point is the
    nearest, in float64, of the face the query finds and every face touching its corners (`rings`: the faces at vertex
    v are `ring_faces[ring_starts[v]:ring_starts[v + 1]]`; `verts` the mesh's float64 points from `first_vert`): the
    query's float32 face flips between near neighbours, so the depth to its face alone jumped there (mean's sampled
    frames, 2026-11-01: a lumbar inside-joint column 2.95e-4 off its central difference at a 1e-6 step, 1.4e-8 with
    the ring). What stays is the depth's kink where a point crosses the skin: a residual max(0, d), whose square, the
    cost, is smooth."""
    near = warp.vec3(warp.float32(point[0]), warp.float32(point[1]), warp.float32(point[2]))
    found = warp.mesh_query_point_sign_winding_number(mesh, near, 1.0e6, 2.0, 0.5)
    offset = warp.vec3d()
    bend = warp.mat33d()
    if found.sign >= 0.0:
        best = warp.float64(1.0e30)
        for corner in range(3):
            vert = faces[3 * found.face + corner]
            for slot in range(ring_starts[vert], ring_starts[vert + 1]):
                face = ring_faces[slot]
                closest, projector = closest_on_triangle(point, verts[first_vert + faces[3 * face]],
                                                         verts[first_vert + faces[3 * face + 1]],
                                                         verts[first_vert + faces[3 * face + 2]])
                apart = point - closest
                length = warp.dot(apart, apart)
                if length < best:
                    best = length
                    offset = apart
                    bend = projector
    return offset, bend


def rings(faces, count):
    """Each of `count` vertices' faces (`faces` faces x 3) as (starts count + 1, faces), int32: `apart_of`'s rings."""
    faces = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    order = np.argsort(faces.ravel(), kind="stable")
    starts = np.searchsorted(faces.ravel()[order], np.arange(count + 1))
    return starts.astype(np.int32), (order // 3).astype(np.int32)


@warp.kernel
def apart_kernel(meshes: warp.array(dtype=warp.uint64), first_verts: warp.array(dtype=warp.int32),
                 kept: warp.array(dtype=warp.int32), verts: warp.array(dtype=warp.vec3d),
                 faces: warp.array(dtype=warp.int32),
                 ring_starts: warp.array(dtype=warp.int32), ring_faces: warp.array(dtype=warp.int32),
                 mesh_of: warp.array(dtype=warp.int32), points: warp.array(dtype=warp.vec3d),
                 apart: warp.array(dtype=warp.vec3d), bends: warp.array(dtype=warp.mat33d)):
    """Per point: its offset off its skin (`apart_of`; `mesh_of` its mesh), its length the depth, and that offset's
    Jacobian in the point (the projector off the closest feature); zero on a skin not `kept` (`unfolded`)."""
    point = warp.tid()
    mesh = mesh_of[point]
    if kept[mesh] != 0:
        offset, bend = apart_of(meshes[mesh], verts, first_verts[mesh], faces, ring_starts, ring_faces,
                                points[point])
        apart[point] = offset
        bends[point] = bend


def region(body):
    """The region a body's bone belongs to (the hand's parts each their own), "other" when none."""
    return next((label for label, parts in REGIONS.items() if any(part in body for part in parts)), "other")


def scored(part):
    """The region a part is scored in: the hand's parts as "hand"."""
    return "hand" if part in HAND else part


def bone_meshes(model):
    """[(geom, vertex indices kept, its body's name)] of every bone mesh."""
    found = []
    for geom in range(model.ngeom):
        if model.geom_type[geom] == mujoco.mjtGeom.mjGEOM_MESH:
            count = int(model.mesh_vertnum[model.geom_dataid[geom]])
            kept = np.linspace(0, count - 1, VERTS).astype(int) if count > VERTS else np.arange(count)
            found.append((geom, kept, model.body(model.geom_bodyid[geom]).name))
    return found


def bone_points(model, data, meshes):
    """The kept bone vertices in the person's frame (Y up) and each one's body name."""
    points, labels = [], []
    for geom, kept, label in meshes:
        start = model.mesh_vertadr[model.geom_dataid[geom]]
        verts = model.mesh_vert[start + kept]
        points.append((verts @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom]) @ TO_OWN.T)
        labels += [label] * len(kept)
    return np.concatenate(points), np.array(labels)


def skin(rig, segments, world):
    """SOMA's mesh posed on one frame (`world` segments x 4 x 4), linear blend over the segments' weights."""
    names = [str(joint) for joint in rig["names"]]
    joints = [names.index(segment) for segment in segments]
    weights = np.asarray(rig["weights"], dtype=float)[:, joints]
    moves = world @ np.linalg.inv(np.asarray(rig["bind"], dtype=float)[joints])
    points = np.asarray(rig["points"], dtype=float)
    moved = np.einsum("sij,vj->vsi", moves[:, :3, :3], points) + moves[None, :, :3, 3]
    return np.einsum("vs,vsi->vi", weights, moved)


def marks(points, verts, faces):
    """(whether each point lies outside the closed mesh (verts, faces) by the winding number, its depth outside in m)."""
    mesh = warp.Mesh(points=warp.array(np.asarray(verts, dtype=np.float32), dtype=warp.vec3, device="cpu"),
                     indices=warp.array(np.asarray(faces, dtype=np.int32).ravel(), dtype=int, device="cpu"),
                     support_winding_number=True)
    signs, depths = (warp.zeros((1, len(points)), dtype=float, device="cpu") for _ in range(2))
    warp.launch(marks_kernel, dim=signs.shape, device="cpu",
                inputs=[warp.array([mesh.id], dtype=warp.uint64, device="cpu"),
                        warp.array(np.asarray(points, dtype=np.float32)[None], dtype=warp.vec3, device="cpu"),
                        signs, depths])
    return signs.numpy()[0] >= 0, depths.numpy()[0].astype(float)


def depth_mm(depths):
    """Level 1's skin residual of one region: the root mean square of its points' depths outside (m given, mm out)."""
    return 1000 * float(np.sqrt(np.mean(np.square(depths))))


def outside(points, verts, faces):
    """Whether each point lies outside the closed mesh (verts, faces) by the winding number."""
    return marks(points, verts, faces)[0]


def pockets(rig):
    """The head's pockets in SOMA's mesh at its bind ([vertex indices] each): connected faces whose outward normal meets
    the mesh again within POCKET_REACH (a pocket's walls face each other), most of whose vertices ride POCKET_SEGMENT
    by their largest skin weight. On the template (2026-11-01): the mouth (a slit 46 mm wide, 13 mm deep), each eye
    socket (26 x 19 x 22 mm), nostril and ear; the webs between fingers and toes face each other too, but no head."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    points, faces = np.asarray(rig["points"], dtype=np.float64), np.asarray(rig["faces"], dtype=np.int32)
    first, second, third = (points[faces[:, corner]] for corner in range(3))
    normals = np.cross(second - first, third - first)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    middles = (first + second + third) / 3
    mesh = warp.Mesh(points=warp.array(points.astype(np.float32), dtype=warp.vec3, device="cpu"),
                     indices=warp.array(faces.ravel(), dtype=int, device="cpu"))
    hits = warp.zeros(len(faces), dtype=float, device="cpu")
    warp.launch(_pocket_rays, dim=len(faces), device="cpu",
                inputs=[mesh.id, warp.array((middles + 1e-4 * normals).astype(np.float32), dtype=warp.vec3, device="cpu"),
                        warp.array(normals.astype(np.float32), dtype=warp.vec3, device="cpu"), hits])
    walls = np.flatnonzero(hits.numpy() < POCKET_REACH)
    shared = coo_matrix((np.ones(3 * len(walls)), (np.repeat(walls, 3), faces[walls].ravel())),
                        shape=(len(faces), len(points))).tocsr()
    touching = (shared @ shared.T).tocoo()
    _, label = connected_components(touching, directed=False)
    head = [str(name) for name in rig["names"]].index(POCKET_SEGMENT)
    riders = np.argmax(np.asarray(rig["weights"]), axis=1) == head
    found = []
    for part in np.unique(label[walls]):
        verts = np.unique(faces[walls[label[walls] == part]])
        if len(verts) >= 4 and riders[verts].mean() > 0.5:
            found.append(verts)
    return found


@warp.kernel
def _pocket_rays(mesh: warp.uint64, starts: warp.array(dtype=warp.vec3), directions: warp.array(dtype=warp.vec3),
                 hits: warp.array(dtype=float)):
    face = warp.tid()
    found = warp.mesh_query_ray(mesh, starts[face], directions[face], 1.0)
    hits[face] = warp.where(found.result, found.t, 1.0e6)


ENVELOPES = {}  # {the rig's points and faces' digest: the faces with the head's pockets closed}


def envelope(rig):
    """SOMA's faces with each of the head's `pockets` closed by its convex hull as a shell of its own (its faces after
    the skin's, outward, over the pocket's own vertices, so it moves with them; the skin's face indices unchanged): the
    winding number in a closed pocket is then 1, inside, as under a closed face (lips, eyelids and eyes, nostrils,
    ears), and a point's depth outside is to the face's skin or the pocket's lid. The inside test's faces
    (owner, 2026-11-01: the teeth read outside in every frame; 49 of a frame's 827 outside jaw and skull vertices sat in
    the mouth's slit, 22 in the eye sockets, the other 756 out of the face itself)."""
    import hashlib
    from scipy.spatial import ConvexHull
    faces = np.asarray(rig["faces"], dtype=np.int32)
    key = hashlib.sha1(np.ascontiguousarray(rig["points"], dtype=np.float64).tobytes() + faces.tobytes()).hexdigest()
    if key not in ENVELOPES:
        points, lids = np.asarray(rig["points"], dtype=np.float64), [faces]
        for verts in pockets(rig):
            hull = ConvexHull(points[verts])
            shell = verts[hull.simplices]
            outward = np.einsum("ij,ij->i", np.cross(points[shell[:, 1]] - points[shell[:, 0]],
                                                     points[shell[:, 2]] - points[shell[:, 0]]), hull.equations[:, :3])
            shell[outward < 0] = shell[outward < 0][:, [0, 2, 1]]
            lids.append(shell)
        ENVELOPES[key] = np.concatenate(lids).astype(np.int32)
    return ENVELOPES[key]


@warp.kernel
def _doubled(mesh: warp.uint64, points: warp.array(dtype=warp.vec3), found: warp.array(dtype=float)):
    """1 where a point winds 1.5 or more (inside the skin twice), else 0."""
    point = warp.tid()
    query = warp.mesh_query_point_sign_winding_number(mesh, points[point], 1.0e6, 2.0, 1.5)
    found[point] = warp.where(query.sign < 0.0, 1.0, 0.0)


def folded(verts, faces):
    """The share of a posed skin's area (`verts`, its own `faces`, no pockets closed) lying inside itself: each vertex
    by its area (a third of its faces'), inside itself when the point FOLD_IN in along its normal winds 1.5 or more."""
    verts, faces = np.asarray(verts, dtype=np.float64), np.asarray(faces, dtype=np.int32)
    normals = np.zeros_like(verts)
    crossed = np.cross(verts[faces[:, 1]] - verts[faces[:, 0]], verts[faces[:, 2]] - verts[faces[:, 0]])
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    area = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(area, 1e-30)[:, None]
    mesh = warp.Mesh(points=warp.array(verts.astype(np.float32), dtype=warp.vec3, device="cpu"),
                     indices=warp.array(faces.ravel(), dtype=int, device="cpu"), support_winding_number=True)
    found = warp.zeros(len(verts), dtype=float, device="cpu")
    warp.launch(_doubled, dim=len(verts), device="cpu",
                inputs=[mesh.id, warp.array((verts - FOLD_IN * normals).astype(np.float32), dtype=warp.vec3,
                                            device="cpu"), found])
    return float(area[found.numpy() > 0].sum() / area.sum())


def unfolded(verts, faces):
    """Whether a posed skin is kept in the skin rows and the share: it lies inside itself over at most FOLD_MOST of its
    area (`folded`)."""
    return folded(verts, faces) <= FOLD_MOST


def bones_outside(model, path, worlds, segments, rig):
    """({"all": %, region: %} of the bone vertices outside SOMA's posed skin over every EVERY-th frame whose skin is
    `unfolded`, {"frames": the folded ones' count, "all": their own %}) (`FOLD_MOST`)."""
    data, meshes, shares, apart = mujoco.MjData(model), bone_meshes(model), {}, []
    for qpos, world in list(zip(path, worlds))[::EVERY]:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        points, bones = bone_points(model, data, meshes)
        labels = np.array([scored(region(bone)) for bone in bones])
        posed = skin(rig, segments, world)
        out = outside(points, posed, envelope(rig))
        if not unfolded(posed, rig["faces"]):
            apart.append(float(out.mean()))
            continue
        shares.setdefault("all", []).append(float(out.mean()))
        for label in set(labels):
            shares.setdefault(label, []).append(float(out[labels == label].mean()))
    return ({label: round(100 * float(np.mean(found)), 2) for label, found in shares.items()},
            {"frames": len(apart), "all": round(100 * float(np.mean(apart)), 2) if apart else 0.0})


class PosedSkins:
    """SOMA's skin posed on each frame in MuJoCo's frame (`verts` frames x points x 3, float32), its `faces` and which
    frames are `kept` (`unfolded`; all when not given): the target level 3 holds the bones inside, a frame not
    kept giving no rows. Indexed by frames like an array; `joined` puts several end to end."""

    def __init__(self, verts, faces, kept=None):
        self.verts = np.asarray(verts, dtype=np.float32)
        self.faces = np.asarray(faces, dtype=np.int32)
        self.kept = np.ones(len(self.verts), dtype=bool) if kept is None else np.asarray(kept, dtype=bool)

    def __len__(self):
        return len(self.verts)

    def __getitem__(self, frames):
        return PosedSkins(self.verts[frames], self.faces, self.kept[frames])

    @staticmethod
    def joined(parts):
        """`parts` end to end, refused when their faces differ (one person's mesh)."""
        parts = list(parts)
        if any(not np.array_equal(part.faces, parts[0].faces) for part in parts):
            raise ValueError("posed skins of different meshes")
        return PosedSkins(np.concatenate([part.verts for part in parts]), parts[0].faces,
                          np.concatenate([part.kept for part in parts]))


def posed_skins(rig, segments, worlds):
    """SOMA's skin on every frame of `worlds` (`skin`, linear blend) in MuJoCo's frame, each kept when `unfolded`."""
    own = np.stack([skin(rig, segments, world) for world in np.asarray(worlds, dtype=float)])
    return PosedSkins(own @ TO_OWN, envelope(rig), [unfolded(posed, rig["faces"]) for posed in own])


def bone_bodies(model):
    """Every kept bone vertex (`bone_meshes`' order) as (its body's id, its place in the body's frame): points x 3."""
    bodies, places = [], []
    for geom, kept, _ in bone_meshes(model):
        start = model.mesh_vertadr[model.geom_dataid[geom]]
        turn = np.zeros(9)
        mujoco.mju_quat2Mat(turn, model.geom_quat[geom])
        places.append(model.mesh_vert[start + kept].astype(float) @ turn.reshape(3, 3).T + model.geom_pos[geom])
        bodies += [int(model.geom_bodyid[geom])] * len(kept)
    return np.array(bodies, dtype=int), (np.concatenate(places) if places else np.zeros((0, 3)))


def skin_cost(count):
    """One bone vertex's residual weight: SKIN_GOAL over the `count` kept vertices, as a cost multiplies a depth."""
    return float(np.sqrt(SKIN_GOAL / max(count, 1)))


def card_device():
    """The card when Warp sees one, else the CPU."""
    return "cuda:0" if warp.is_cuda_available() else "cpu"


class SkinMeshes:
    """A `PosedSkins`' frames as Warp meshes (exact winding numbers) on `device`, with their float64 points (`verts`,
    each frame's from `first_verts`) for `apart`."""

    def __init__(self, skins, device):
        self.device = device
        faces = warp.array(skins.faces.ravel(), dtype=int, device=device)
        self.meshes = [warp.Mesh(points=warp.array(verts, dtype=warp.vec3, device=device), indices=faces,
                                 support_winding_number=True) for verts in skins.verts]
        self.ids = warp.array(np.array([mesh.id for mesh in self.meshes], dtype=np.uint64), dtype=warp.uint64,
                              device=device)
        count = skins.verts.shape[1] if len(skins) else 0
        self.first_verts = warp.array(np.arange(len(skins), dtype=np.int32) * count, dtype=warp.int32, device=device)
        self.verts = warp.array(skins.verts.reshape(-1, 3).astype(np.float64), dtype=warp.vec3d, device=device)
        self.faces = warp.array(skins.faces.ravel(), dtype=warp.int32, device=device)
        self.kept = warp.array(skins.kept.astype(np.int32), dtype=warp.int32, device=device)
        starts, ringed = rings(skins.faces, count)
        self.ring_starts = warp.array(starts, dtype=warp.int32, device=device)
        self.ring_faces = warp.array(ringed, dtype=warp.int32, device=device)

    def apart(self, points, frames):
        """Each point's offset off its frame's skin and that offset's Jacobian in the point (`apart_kernel`; points
        n x 3 in MuJoCo's frame, `frames` n: its mesh's index), float64: (n x 3, n x 3 x 3)."""
        found = warp.zeros(len(points), dtype=warp.vec3d, device=self.device)
        bends = warp.zeros(len(points), dtype=warp.mat33d, device=self.device)
        warp.launch(apart_kernel, dim=len(points), device=self.device,
                    inputs=[self.ids, self.first_verts, self.kept, self.verts, self.faces, self.ring_starts,
                            self.ring_faces,
                            warp.array(np.asarray(frames, dtype=np.int32), dtype=warp.int32, device=self.device),
                            warp.array(np.asarray(points, dtype=np.float64), dtype=warp.vec3d, device=self.device),
                            found, bends])
        return found.numpy().astype(float), bends.numpy().astype(float)
