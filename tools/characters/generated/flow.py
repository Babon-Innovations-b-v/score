"""The generated hair's own flow (`flow_field`): the way its strands run at each place of its volume, read off the
shell TRELLIS.2 made, so a sleek bob grows straight and sleek and waves follow the shell's waves (round 1 combed the
strands by hair.py's generic comb and wave, and a bob came out a straggly mop, loose waves tight ringlets,
2026-11-26).

The shell carries the flow twice. Its geometry is grooved along the strands: over each hair triangle's neighbours
(NORMAL_ROUNDS rounds over `labels.adjacency`) the normals spread most across the grooves and least along them, so the
way along is the normals' tensor's least axis (`grooves`). Its paint is streaked along the strands: the texture's
lightness changes least along a streak, the least axis of its structure tensor (PAINT_SIGMA texels, `streaks`),
carried from the picture onto the triangle by its UV-to-space map. Each way counts by how clearly it points (its
coherence), as an orientation tensor (a way and its reverse are one). The triangles' tensors are spread into the
volume, normalised, over FLOW_SIGMA_M near the shell and SPREAD_SIGMA_M deeper in, and read as the main axis with its
coherence. The field is an orientation only: a strand takes its sign from its own last step, or from the comb at its
root (`strands.py`)."""
import numpy as np
from scipy import ndimage

from tools.characters.generated import labels, volume
from tools.characters.whole import hair

NORMAL_ROUNDS = 2  # rounds of neighbours the normals' spread is read over (some 6 to 10 mm)
GROOVE_FLOOR = 0.002  # the normals' spread under which a surface is smooth, not grooved (radians squared)
PAINT_SIGMA = (1.0, 4.0)  # texels: the lightness's derivative's and its structure tensor's Gaussian
PAINT_FLOOR = 2e-5  # a structure tensor's size under which the paint is plain (lightness 0..1, squared)
FLOW_SIGMA_M = 0.005
SPREAD_SIGMA_M = 0.015
NEAR_MASS = 0.05  # the near spread's weight (a share of its median on the shell) under which the deeper is read


def tensor_axes(tensors):
    """The eigenvalues (ascending) and eigenvectors (columns) of symmetric 3 x 3 tensors."""
    return np.linalg.eigh(tensors)


def grooves(points, faces, hair_faces):
    """The hair triangles' groove way (unit, along the least spread of their neighbours' normals) and its coherence
    (0 on a smooth or evenly curved surface, towards 1 along a clear groove)."""
    normals = volume.face_normals(points, faces[hair_faces])
    neighbours = labels.adjacency(points, faces[hair_faces])
    tensors = (normals[:, :, None] * normals[:, None, :]).reshape(-1, 9)
    degree = np.ones(len(normals))
    for _ in range(NORMAL_ROUNDS):
        tensors = tensors + neighbours @ tensors
        degree = degree + neighbours @ degree
    values, vectors = tensor_axes((tensors / degree[:, None]).reshape(-1, 3, 3))
    spread_across, spread_along = values[:, 1], values[:, 0]
    coherence = (spread_across - spread_along) / (spread_across + spread_along + GROOVE_FLOOR)
    return vectors[:, :, 0], np.clip(coherence, 0.0, 1.0)


def paint_tensor(texture):
    """The texture's lightness structure tensor (Jxx, Jxy, Jyy over columns and rows), PAINT_SIGMA."""
    lightness = (np.asarray(texture, float) / 255.0) @ np.array([0.2126, 0.7152, 0.0722])
    along_columns = ndimage.gaussian_filter(lightness, PAINT_SIGMA[0], order=(0, 1))
    along_rows = ndimage.gaussian_filter(lightness, PAINT_SIGMA[0], order=(1, 0))
    return [ndimage.gaussian_filter(product, PAINT_SIGMA[1]) for product in
            (along_columns * along_columns, along_columns * along_rows, along_rows * along_rows)]


def streaks(points, faces, uv, texture, hair_faces):
    """The hair triangles' paint streak way (unit, in space) and its coherence: the texture's structure tensor read at
    each triangle's middle, its least axis carried by the triangle's UV-to-space map."""
    height, width = texture.shape[:2]
    jxx, jxy, jyy = paint_tensor(texture)
    corners, corner_uv = points[faces[hair_faces]], uv[faces[hair_faces]]
    middle = corner_uv.mean(axis=1)
    column = np.clip(((middle[:, 0] % 1.0) * (width - 1)).astype(int), 0, width - 1)
    row = np.clip(((1.0 - middle[:, 1] % 1.0) * (height - 1)).astype(int), 0, height - 1)
    xx, xy, yy = jxx[row, column], jxy[row, column], jyy[row, column]
    spread = np.sqrt((xx - yy) ** 2 + 4.0 * xy ** 2)
    coherence = spread / (xx + yy + PAINT_FLOOR)
    across = 0.5 * np.arctan2(2.0 * xy, xx - yy)  # the lightness's steepest way (columns, rows)
    along_image = np.stack([-np.sin(across), np.cos(across)], axis=1)
    along_uv = np.stack([along_image[:, 0] / (width - 1), -along_image[:, 1] / (height - 1)], axis=1)
    edges = np.stack([corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]], axis=2)  # (n, 3, 2)
    uv_edges = np.stack([corner_uv[:, 1] - corner_uv[:, 0], corner_uv[:, 2] - corner_uv[:, 0]], axis=2)  # (n, 2, 2)
    determinant = np.linalg.det(uv_edges)
    usable = np.abs(determinant) > 1e-12
    inverse = np.zeros_like(uv_edges)
    inverse[usable] = np.linalg.inv(uv_edges[usable])
    mapped = np.einsum("nij,njk,nk->ni", edges, inverse, along_uv)
    way = hair.tangent(mapped, volume.face_normals(points, faces[hair_faces]))
    return way, np.where(usable, np.clip(coherence, 0.0, 1.0), 0.0)


def splatted(places, tensors, space):
    """The tensors summed into the volume's grid at their places: (6 component grids, weight grid)."""
    at = np.round((places - space["low"]) / volume.VOXEL_M).astype(int)
    shape = tuple(space["shape"])
    inside = ((at >= 0) & (at < np.asarray(shape))).all(axis=1)
    flat = np.ravel_multi_index(tuple(at[inside].T), shape)
    grids = []
    for row, column in ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)):
        grids.append(np.bincount(flat, tensors[inside, row, column], np.prod(shape)).reshape(shape))
    weight = np.bincount(flat, np.trace(tensors[inside], axis1=1, axis2=2), np.prod(shape)).reshape(shape)
    return grids, weight


def spread(grids, weight, sigma_m):
    """The splatted tensors smoothed over `sigma_m` and normalised by their weight: (6 grids, the smoothed weight)."""
    sigma = sigma_m / volume.VOXEL_M
    mass = ndimage.gaussian_filter(weight, sigma)
    return [ndimage.gaussian_filter(grid, sigma) / np.maximum(mass, 1e-9) for grid in grids], mass


def flow_field(points, faces, uv, texture, hair_faces, space):
    """The flow on the volume's grid: {axis (x, y, z, 3) unit, coherent (x, y, z) 0..1}."""
    groove_way, groove_clear = grooves(points, faces, hair_faces)
    streak_way, streak_clear = streaks(points, faces, uv, texture, hair_faces)
    tensors = (groove_clear[:, None, None] * groove_way[:, :, None] * groove_way[:, None, :]
               + streak_clear[:, None, None] * streak_way[:, :, None] * streak_way[:, None, :])
    places = points[faces[hair_faces]].mean(axis=1)
    grids, weight = splatted(places, tensors, space)
    near, near_mass = spread(grids, weight, FLOW_SIGMA_M)
    deep, _ = spread(grids, weight, SPREAD_SIGMA_M)
    use_near = near_mass > NEAR_MASS * float(np.median(near_mass[weight > 0]))
    read = np.argwhere(space["filled"] > 0.5)
    components = [np.where(use_near, near_grid, deep_grid)[tuple(read.T)] for near_grid, deep_grid in zip(near, deep)]
    xx, xy, xz, yy, yz, zz = components
    tensor = np.stack([np.stack([xx, xy, xz], -1), np.stack([xy, yy, yz], -1), np.stack([xz, yz, zz], -1)], -2)
    values, vectors = tensor_axes(tensor)
    axis = np.zeros(tuple(space["shape"]) + (3,), np.float32)
    coherent = np.zeros(tuple(space["shape"]), np.float32)
    axis[tuple(read.T)] = vectors[:, :, 2]
    coherent[tuple(read.T)] = np.clip((values[:, 2] - values[:, 1]) / np.maximum(values.sum(axis=1), 1e-12), 0, 1)
    return {"axis": axis, "coherent": coherent}


def read_axis(field, space, places):
    """The flow's axis and coherence at the places (the nearest voxel's; 0 outside the grid)."""
    at = np.round((places - space["low"]) / volume.VOXEL_M).astype(int)
    shape = np.asarray(space["shape"])
    inside = ((at >= 0) & (at < shape)).all(axis=1)
    at = np.clip(at, 0, shape - 1)
    axis = field["axis"][tuple(at.T)] * inside[:, None]
    return axis.astype(float), field["coherent"][tuple(at.T)] * inside
