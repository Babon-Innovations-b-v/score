"""Bones inside SOMA's skin (#70's judgement, the audit's item 2): every EVERY-th frame, each bone mesh's vertices
(at most VERTS a mesh) tested against SOMA's skin posed on that frame (linear blend, as SOMA skins it) by the
generalised winding number (inside at 0.5 or more: warp's BVH winding query on the CPU, the rule main's harness
measures with), the share outside kept per region (REGIONS, the hand's parts (HAND) one region). The stage's record
and level 1's score (evaluation._measure) both measure through this one module. Level 1's least squares reads the
depth outside instead (`marks_kernel`: each point's distance to the skin's closest point when outside, 0 inside), smooth
where the share is a step (#70, 2026-10-30): the share stays the judged measure. Nothing here moves SOMA."""
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


def bones_outside(model, path, worlds, segments, rig):
    """{"all": %, region: %} of the bone vertices outside SOMA's posed skin, over every EVERY-th frame."""
    data, meshes, shares = mujoco.MjData(model), bone_meshes(model), {}
    for qpos, world in list(zip(path, worlds))[::EVERY]:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        points, bones = bone_points(model, data, meshes)
        labels = np.array([scored(region(bone)) for bone in bones])
        out = outside(points, skin(rig, segments, world), envelope(rig))
        shares.setdefault("all", []).append(float(out.mean()))
        for label in set(labels):
            shares.setdefault(label, []).append(float(out[labels == label].mean()))
    return {label: round(100 * float(np.mean(found)), 2) for label, found in shares.items()}
