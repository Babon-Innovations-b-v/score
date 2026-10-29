"""Bones inside SOMA's skin (#70's judgement, the audit's item 2): every EVERY-th frame, each bone mesh's vertices
(at most VERTS a mesh) tested against SOMA's skin posed on that frame (linear blend, as SOMA skins it) by the
generalised winding number (inside at 0.5 or more: warp's BVH winding query on the CPU, the rule main's harness
measures with), the share outside kept per region (REGIONS, the hand's parts one region). Nothing here moves SOMA."""
import mujoco
import numpy as np
import warp

from model import TO_OWN

EVERY = 10  # frames between the skin measures
VERTS = 80  # bone vertices kept per mesh
REGIONS = {"shoulder": ("clavicle", "scapula", "humerus"), "forearm": ("ulna", "radius"),
           "hand": ("ph_", "thumb", "mc", "lunate", "scaphoid", "pisiform", "triquetrum", "capitate", "trapezium",
                    "trapezoid", "hamate"),
           "pelvis": ("pelvis", "sacrum"), "spine": ("lumbar", "thorax", "torso", "cervical", "neck", "rib"),
           "head": ("head", "skull", "jaw", "mandible"), "thigh": ("femur", "patella"), "shin": ("tibia", "fibula"),
           "foot": ("talus", "calcn", "toes")}

warp.config.quiet = True


@warp.kernel
def _signs(mesh: warp.uint64, points: warp.array(dtype=warp.vec3), out: warp.array(dtype=float)):
    index = warp.tid()
    out[index] = warp.mesh_query_point_sign_winding_number(mesh, points[index], 1.0e6, 2.0, 0.5).sign


def region(body):
    """The region a body's bone belongs to, "other" when none."""
    return next((label for label, parts in REGIONS.items() if any(part in body for part in parts)), "other")


def bone_meshes(model):
    """[(geom, vertex indices kept)] of every bone mesh, with each geom's region."""
    found = []
    for geom in range(model.ngeom):
        if model.geom_type[geom] == mujoco.mjtGeom.mjGEOM_MESH:
            count = int(model.mesh_vertnum[model.geom_dataid[geom]])
            kept = np.linspace(0, count - 1, VERTS).astype(int) if count > VERTS else np.arange(count)
            found.append((geom, kept, region(model.body(model.geom_bodyid[geom]).name)))
    return found


def bone_points(model, data, meshes):
    """The kept bone vertices in the person's frame (Y up) and each one's region."""
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


def outside(points, verts, faces):
    """Whether each point lies outside the closed mesh (verts, faces) by the winding number."""
    mesh = warp.Mesh(points=warp.array(np.asarray(verts, dtype=np.float32), dtype=warp.vec3, device="cpu"),
                     indices=warp.array(np.asarray(faces, dtype=np.int32).ravel(), dtype=int, device="cpu"))
    out = warp.zeros(len(points), dtype=float, device="cpu")
    warp.launch(_signs, dim=len(points), device="cpu",
                inputs=[mesh.id, warp.array(np.asarray(points, dtype=np.float32), dtype=warp.vec3, device="cpu"), out])
    return out.numpy() >= 0


def bones_outside(model, path, worlds, segments, rig):
    """{"all": %, region: %} of the bone vertices outside SOMA's posed skin, over every EVERY-th frame."""
    data, meshes, shares = mujoco.MjData(model), bone_meshes(model), {}
    for qpos, world in list(zip(path, worlds))[::EVERY]:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        points, labels = bone_points(model, data, meshes)
        out = outside(points, skin(rig, segments, world), rig["faces"])
        shares.setdefault("all", []).append(float(out.mean()))
        for label in set(labels):
            shares.setdefault(label, []).append(float(out[labels == label].mean()))
    return {label: round(100 * float(np.mean(found)), 2) for label, found in shares.items()}
