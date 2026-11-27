"""The generated hair's own shape as a volume the strands fill (`hair_volume`): every place inside the model's surface,
whose nearest piece of that surface is hair, and outside the head's skin and new scalp (`../generated/scalp.py`).

Read on a VOXEL_M grid round the hair: inside the model where the air cannot reach past its surface and the new
scalp's (`solid_inside`: the model is a thin two-sided sheet, wound either way, its head hollow and open through the
eyes or a bust's cut, so the scalp walls the hair off from the head's inside), or under the outermost hair as seen from
the head's middle (`seen_from`), never inside the head's skin as seen from there; inside the head's skin and scalp by the side of their
nearest sample (SAMPLE_M apart), each sample's normal turned outward by the model's own inside (`outward_by`: the
place ORIENT_M off it along its normal must lie outside). Its depth (the distance to the volume's edge, the outer
shell or the scalp, smoothed over DEPTH_SMOOTH voxels) and its gradient say where the volume's edge is (a strand
leaving it slides along it, `../generated/strands.py`). Its layer (`layered`) runs from 0 on the scalp's side to 1
on its outer surface, read along rays from the head's middle (LAYER_DIRECTIONS): the hair's span along each ray is the
volume's thickness there, and the layer's gradient the way across the shell (round 1 held each strand at a share of
the depth from the nearer edge, so no strand ever lay in the shell's outer half: the regrown hair sat inside the
shell, short of its outline and its ends, 2026-11-26)."""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

VOXEL_M = 0.002
MARGIN_M = 0.01
SAMPLE_M = 0.0008
DEPTH_SMOOTH = 1.0
LAYER_DIRECTIONS = 6  # the icosphere's subdivisions the layer is read along (some 1.2 degrees apart)
LAYER_SMOOTH = 1.5  # voxels the layer is smoothed over within the volume
ORIENT_M = 0.003
SEAL_VOXELS = 1
SHELL_VOXELS = 1
RADIAL_COS = 0.5
SKIN_NEAR_M = 0.012
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


def radially(places, normals, start):
    """The normals that face `start` or away from it (RADIAL_COS) turned away from it; the rest kept."""
    away = places - start
    away /= np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-9)
    facing = np.einsum("pi,pi->p", normals, away)
    return np.where((np.abs(facing) > RADIAL_COS)[:, None], normals * np.sign(facing)[:, None], normals)


def outward_by(places, normals, inside, low):
    """The normals turned so the place ORIENT_M along each lies outside (`inside`, a voxel grid from `low`)."""
    probe = np.round((places + normals * ORIENT_M - low) / VOXEL_M).astype(int)
    probe = np.clip(probe, 0, np.asarray(inside.shape) - 1)
    flip = inside[probe[:, 0], probe[:, 1], probe[:, 2]]
    return np.where(flip[:, None], -normals, normals)


def shell_voxels(samples, low, shape):
    """The voxels the hair's own surface passes through, grown by SHELL_VOXELS: a bob's hanging ends and a lock's thin
    sheet, open to the air or beside the neck where no ray from the head's middle meets skin, are hair too (round 2's
    first volume left a bob's lowest 4 cm out, its outer surface 40% covered, 2026-11-26)."""
    shell = np.zeros(shape, dtype=bool)
    at = np.round((samples - low) / VOXEL_M).astype(int)
    at = at[((at >= 0) & (at < np.asarray(shape))).all(axis=1)]
    shell[at[:, 0], at[:, 1], at[:, 2]] = True
    return ndimage.binary_dilation(shell, iterations=SHELL_VOXELS)


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
    """The hair's volume: {low, shape, filled, depth (m), gradient (unit, into the volume), layer (0 inner to 1
    outer), across (unit, outward through the layers), thick (m), under (m: the distance to the air outside the hair,
    never the head), outward (unit: towards that air)}. `model` is (points, triangles) and
    `body` (points, triangles, normals, n, rays) whose first n triangles are the model's own (their normals turned
    outward here) and whose `rays` triangles (skin, scalp and neck, never clothes: a coat further along a ray put a
    bob's hanging ends inside the head) the head is read along; `hair` labels the model's triangles; `start` is the
    head's middle the hair is seen from (`scalp.origin`)."""
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
    near_hair = hair[model_on[nearest]].reshape(shape)
    # a skin normal is turned away from the model's inside less its hair (a bob lying on the jaw put the jaw's
    # normals into the head and the bob's ends inside it, 2026-11-26), and one facing the head's middle or away from
    # it (RADIAL_COS) simply away from it: the air a bob closes off beside the cheeks turned the cheeks' normals in
    body_normals[from_model] = radially(body_samples[from_model], outward_by(
        body_samples[from_model], body_normals[from_model], inside_model & ~near_hair, low), start)
    skin = body[4][body_on]
    inside_body, nearest_skin = inside_of(middles, body_samples[skin], body_normals[skin])
    # only near the skin: further in, the rays from the head's middle say what is inside (`seen_from`); further out a
    # far ear's or collar's normal put a bob's outer side inside the head (2026-11-26)
    inside_body &= np.linalg.norm(middles - body_samples[skin][nearest_skin], axis=1) < SKIN_NEAR_M
    under, in_head = seen_from(middles, (points, faces[hair]), (body[0], body[1][body[4]]), start)
    outside_head = (~inside_body & ~in_head).reshape(shape)
    filled = (inside_model | under.reshape(shape)) & near_hair & outside_head
    filled |= shell_voxels(model_samples[hair[model_on]], low, shape) & outside_head
    pieces, count = ndimage.label(filled)
    sizes = ndimage.sum(filled, pieces, index=np.arange(1, count + 1))
    filled = np.isin(pieces, 1 + np.flatnonzero(sizes >= FEWEST_VOXELS))
    depth = ndimage.gaussian_filter(ndimage.distance_transform_edt(filled) * VOXEL_M, DEPTH_SMOOTH)
    gradient = np.stack(np.gradient(depth, VOXEL_M), axis=-1)
    gradient /= np.maximum(np.linalg.norm(gradient, axis=-1, keepdims=True), 1e-9)
    layer, thick = layered(filled, low, start)
    under = ndimage.gaussian_filter(ndimage.distance_transform_edt(filled | ~outside_head) * VOXEL_M, DEPTH_SMOOTH)
    outward = -np.stack(np.gradient(under, VOXEL_M), axis=-1)
    outward /= np.maximum(np.linalg.norm(outward, axis=-1, keepdims=True), 1e-9)
    across = np.stack(np.gradient(layer, VOXEL_M), axis=-1)
    across /= np.maximum(np.linalg.norm(across, axis=-1, keepdims=True), 1e-9)
    return {"low": low, "shape": shape, "filled": filled.astype(np.float32), "depth": depth.astype(np.float32),
            "gradient": gradient.astype(np.float32), "layer": layer.astype(np.float32),
            "across": across.astype(np.float32), "thick": thick.astype(np.float32), "under": under.astype(np.float32),
            "outward": outward.astype(np.float32)}


def layered(filled, low, start):
    """Each voxel's layer in the hair (0 on its inner side, 1 on its outer surface, along the ray from `start`) and
    the hair's thickness along that ray (m), both smoothed over LAYER_SMOOTH voxels within the volume and carried
    a few voxels out of it (a strand a step outside still reads them)."""
    import trimesh  # noqa: PLC0415
    inside = np.argwhere(filled)
    away = low + inside * VOXEL_M - start
    distance = np.linalg.norm(away, axis=1)
    directions = np.asarray(trimesh.creation.icosphere(subdivisions=LAYER_DIRECTIONS).vertices)
    ray = cKDTree(directions).query(away / np.maximum(distance, 1e-9)[:, None], workers=-1)[1]
    nearest, farthest = np.full(len(directions), np.inf), np.zeros(len(directions))
    np.minimum.at(nearest, ray, distance)
    np.maximum.at(farthest, ray, distance)
    span = np.maximum(farthest[ray] - nearest[ray], VOXEL_M)
    fields = []
    for values in ((distance - nearest[ray]) / span, span):
        grid = np.zeros(filled.shape)
        grid[tuple(inside.T)] = values
        fields.append(spread_in(grid, filled))
    return fields


def spread_in(grid, filled):
    """A field held on the volume's voxels smoothed over LAYER_SMOOTH voxels within it (normalised, so the edge does
    not fade) and carried out of it to the nearest voxel's value."""
    weight = ndimage.gaussian_filter(filled.astype(float), LAYER_SMOOTH)
    smooth = ndimage.gaussian_filter(grid * filled, LAYER_SMOOTH) / np.maximum(weight, 1e-6)
    nearest = ndimage.distance_transform_edt(~filled.astype(bool), return_distances=False, return_indices=True)
    return np.where(filled > 0, smooth, smooth[tuple(nearest)])


def read(volume, name, places):
    """The volume's field `name` read at the places (trilinear; 0 outside the grid)."""
    at = ((places - volume["low"]) / VOXEL_M).T
    field = volume[name]
    if field.ndim == 3:
        return ndimage.map_coordinates(field, at, order=1, mode="constant", cval=0.0)
    return np.stack([ndimage.map_coordinates(field[..., axis], at, order=1, mode="constant", cval=0.0)
                     for axis in range(field.shape[-1])], axis=1)
