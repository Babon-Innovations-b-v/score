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


def bones_outside(model, path, worlds, segments, rig):
    """{"all": %, region: %} of the bone vertices outside SOMA's posed skin, over every EVERY-th frame."""
    data, meshes, shares = mujoco.MjData(model), bone_meshes(model), {}
    for qpos, world in list(zip(path, worlds))[::EVERY]:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        points, bones = bone_points(model, data, meshes)
        labels = np.array([scored(region(bone)) for bone in bones])
        out = outside(points, skin(rig, segments, world), rig["faces"])
        shares.setdefault("all", []).append(float(out.mean()))
        for label in set(labels):
            shares.setdefault(label, []).append(float(out[labels == label].mean()))
    return {label: round(100 * float(np.mean(found)), 2) for label, found in shares.items()}
