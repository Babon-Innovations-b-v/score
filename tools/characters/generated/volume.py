"""The generated hair's own shape as a volume the strands fill (`hair_volume`): every place inside the model's surface,
whose nearest piece of that surface is hair, and outside the head's skin and new scalp (`../generated/scalp.py`).

Read on a VOXEL_M grid round the hair: inside the model where the air cannot reach past its surface and the new
scalp's (`solid_inside`: the model is a thin two-sided sheet, wound either way, its head hollow and open through the
eyes or a bust's cut, so the scalp walls the hair off from the head's inside), or under the outermost hair as seen from
the head's middle (`seen_from`), never inside the head's skin as seen from there; inside the head's skin and scalp by the side of their
nearest sample (SAMPLE_M apart), each sample's normal turned outward by the model's own inside (`outward_by`: the
place ORIENT_M off it along its normal must lie outside). Its depth (the distance to the volume's edge, the outer
shell or the scalp, smoothed over DEPTH_SMOOTH voxels) gives the strands their layer and its gradient the surface
they flow along; its half thickness is the deepest depth within THICK_REACH_M (the middle of the shell there)."""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

VOXEL_M = 0.002
MARGIN_M = 0.01
SAMPLE_M = 0.0008
DEPTH_SMOOTH = 1.0
THICK_REACH_M = 0.03
ORIENT_M = 0.003
SEAL_VOXELS = 1
DIRECTIONS = 6  # the icosphere's subdivisions the outermost hair is read along
FLOOR_M = 0.004 + MARGIN_M  # the grid's bottom this far over the model's lowest: inside a bust's open cut, so the air
# under it cannot run up through the neck into the head (a bust read hollow, its hair a 2 mm skin, 2026-11-26)
FEWEST_VOXELS = 500  # a piece of the volume smaller than this is a speck of paint, not hair


def surface_samples(points, faces, rng):
    """Places on the triangles about SAMPLE_M apart: (places, the triangle each lies on)."""
    corners = points[faces]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2.0
    count = int(area.sum() / SAMPLE_M ** 2)
    picked = rng.choice(len(faces), size=count, p=area / area.sum())
    weights = rng.dirichlet(np.ones(3), count)
    return np.einsum("pc,pcd->pd", weights, corners[picked]), picked


def face_normals(points, faces):
    """Each triangle's unit normal by its winding."""
    corners = points[faces]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return normal / np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)


def inside_of(places, samples, normals):
    """Whether each place lies behind its nearest sample's surface (inside), and that sample's index."""
    _, nearest = cKDTree(samples).query(places, workers=-1)
    return np.einsum("pi,pi->p", places - samples[nearest], normals[nearest]) < 0.0, nearest


def solid_inside(samples, low, shape):
    """The model as a solid on the grid: every voxel the outside air cannot reach. A generated model is a thin
    two-sided sheet (its head hollow), so inside is what its surface (the voxels its `samples` touch, grown by
    SEAL_VOXELS to seal pinholes) closes off from the air at the grid's top and sides; the bottom is left out, as the
    grid cuts the body there."""
    wall = np.zeros(shape, dtype=bool)
    at = np.clip(np.round((samples - low) / VOXEL_M).astype(int), 0, np.asarray(shape) - 1)
    wall[at[:, 0], at[:, 1], at[:, 2]] = True
    wall = ndimage.binary_dilation(wall, iterations=SEAL_VOXELS)
    pieces, _ = ndimage.label(~wall)
    border = np.zeros(shape, dtype=bool)
    border[[0, -1], :, :] = True
    border[:, -1, :] = True
    border[:, :, [0, -1]] = True
    outside = np.isin(pieces, np.unique(pieces[border & ~wall]))
    return ~outside


def outward_by(places, normals, inside, low):
    """The normals turned so the place ORIENT_M along each lies outside (`inside`, a voxel grid from `low`)."""
    probe = np.round((places + normals * ORIENT_M - low) / VOXEL_M).astype(int)
    probe = np.clip(probe, 0, np.asarray(inside.shape) - 1)
    flip = inside[probe[:, 0], probe[:, 1], probe[:, 2]]
    return np.where(flip[:, None], -normals, normals)


def grid_of(low, high):
    """The voxel grid round [low, high]: (its first corner, its shape, every voxel's middle as (n, 3))."""
    low, high = low - MARGIN_M, high + MARGIN_M
    shape = np.ceil((high - low) / VOXEL_M).astype(int) + 1
    axes = [low[axis] + VOXEL_M * np.arange(shape[axis]) for axis in range(3)]
    middles = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    return low, shape, middles


def hits_along(points, faces, start, directions, outermost):
    """Along each direction from `start`, the distance to the outermost (or the first) surface it meets: 0 (or inf)
    where it meets none."""
    import trimesh  # noqa: PLC0415 (its ray caster only here)
    mesh = trimesh.Trimesh(points, faces, process=False)
    where, ray, _ = mesh.ray.intersects_location(np.repeat(start[None], len(directions), axis=0), directions,
                                                multiple_hits=True)
    distance = np.linalg.norm(where - start, axis=1)
    found = np.zeros(len(directions)) if outermost else np.full(len(directions), np.inf)
    (np.maximum if outermost else np.minimum).at(found, ray, distance)
    return found


def seen_from(middles, hair_mesh, body_mesh, start):
    """Each place seen from `start` (the head's middle) along its direction: (under the hair: past the head's
    outermost skin, scalp or neck and nearer than the outermost hair surface; inside the head: nearer than that skin;
    a direction meeting no skin, down through the neck, is neither).
    The room between the scalp and a long head's dome of hair is open to the air at its rim, round the ears and the
    neck, so the air's reach alone leaves it empty; and the head is open down its neck, so its inside is read here."""
    import trimesh  # noqa: PLC0415
    directions = np.asarray(trimesh.creation.icosphere(subdivisions=DIRECTIONS).vertices)
    outermost = hits_along(*hair_mesh, start, directions, True)
    skin = hits_along(*body_mesh, start, directions, True)
    away = middles - start
    distance = np.linalg.norm(away, axis=1)
    _, nearest = cKDTree(directions).query(away / np.maximum(distance, 1e-9)[:, None], workers=-1)
    seen = skin[nearest] > 0.0
    return (distance < outermost[nearest]) & (distance > skin[nearest]) & seen, distance < skin[nearest]


def hair_volume(model, hair, body, rng, start):
    """The hair's volume: {low, shape, filled, depth (m), gradient (unit, into the volume), half (m)}. `model` is
    (points, triangles) and `body` (points, triangles, normals) whose triangles `the first body[3]` of them are the
    model's own (their normals turned outward here); `hair` labels the model's triangles; `start` is the head's
    middle the hair is seen from (`scalp.origin`)."""
    points, faces = model
    hair_places = points[faces[hair]].reshape(-1, 3)
    floor = hair_places.min(axis=0)
    floor[1] = max(floor[1], points[faces].reshape(-1, 3)[:, 1].min() + FLOOR_M)
    low, shape, middles = grid_of(floor, hair_places.max(axis=0))
    model_samples, model_on = surface_samples(points, faces, rng)
    body_samples, body_on = surface_samples(body[0], body[1], rng)
    inside_model = solid_inside(np.vstack([model_samples, body_samples]), low, shape)
    _, nearest = cKDTree(model_samples).query(middles, workers=-1)
    body_normals = body[2][body_on]
    from_model = body_on < body[3]
    body_normals[from_model] = outward_by(body_samples[from_model], body_normals[from_model], inside_model, low)
    inside_body, _ = inside_of(middles, body_samples, body_normals)
    under, in_head = seen_from(middles, (points, faces[hair]), body[:2], start)
    filled = (inside_model | under.reshape(shape)) & (hair[model_on[nearest]] & ~inside_body & ~in_head).reshape(shape)
    pieces, count = ndimage.label(filled)
    sizes = ndimage.sum(filled, pieces, index=np.arange(1, count + 1))
    filled = np.isin(pieces, 1 + np.flatnonzero(sizes >= FEWEST_VOXELS))
    depth = ndimage.gaussian_filter(ndimage.distance_transform_edt(filled) * VOXEL_M, DEPTH_SMOOTH)
    gradient = np.stack(np.gradient(depth, VOXEL_M), axis=-1)
    gradient /= np.maximum(np.linalg.norm(gradient, axis=-1, keepdims=True), 1e-9)
    reach = 2 * int(THICK_REACH_M / VOXEL_M) + 1
    half = ndimage.maximum_filter(depth, size=reach)
    return {"low": low, "shape": shape, "filled": filled.astype(np.float32), "depth": depth.astype(np.float32),
            "gradient": gradient.astype(np.float32), "half": half.astype(np.float32)}


def read(volume, name, places):
    """The volume's field `name` read at the places (trilinear; 0 outside the grid)."""
    at = ((places - volume["low"]) / VOXEL_M).T
    field = volume[name]
    if field.ndim == 3:
        return ndimage.map_coordinates(field, at, order=1, mode="constant", cval=0.0)
    return np.stack([ndimage.map_coordinates(field[..., axis], at, order=1, mode="constant", cval=0.0)
                     for axis in range(field.shape[-1])], axis=1)
