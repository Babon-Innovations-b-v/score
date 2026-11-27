"""A generated person's detailed head put on its whole body: the head-and-shoulders model (made from a head close-up)
fitted onto the whole clothed body's soft head, both cut at one level line low on the neck or inside the collar, the
head's cut edge laid onto the body's, and the head's paint blended into the body's across a band above the cut.
Everything of the body below the cut stays as it was.

Inside Blender (CPU):
    blender -b --python head_swap.py -- <body.glb> <head.glb> <cut depth> <out.glb> <out transform.json> [<hood>]

<cut depth>: the cut's depth under the body's crown, in the body's heights (a head, crown to chin, is about 0.13;
about 0.15 to 0.17 lands low on the neck or inside a collar). <hood>: when the body's own hood or high collar rises
round the neck above the cut, the depth under the crown (body heights) from which down the body keeps everything round
the neck but the neck itself and the throat: its hood stays, the head model's is dropped.

The transform JSON holds the head-to-body similarity (scale, rotation, translation) in the glTF frame of the two files,
so anything made on the head model (hair strands, eyes) follows onto the body with the same matrix; the cut's level,
the band and the fit's residual sit beside it. Only the head's vertices within the band above the cut are moved (to
close the seam); everything above the band is the head model under the transform alone.

The fitting, falloff and rasterising pieces are plain numpy (importable without Blender); `main` runs in Blender.
"""
import json
import math
import pathlib
import sys

import numpy as np

ICP_ROUNDS = 40
ICP_KEPT = 0.7  # the share of pairs (the closest) each round fits; the rest are where the two faces truly differ
FIT_POINTS = 8000  # points each side of the fit (a random draw, fixed seed)
START_SCALES = np.arange(0.16, 0.38, 0.02)  # the head model's scales onto the body scanned (its bust ~0.9 high)
SCAN_ROUNDS = 25  # rigid rounds at each scanned scale
# Sizes in the body's heights (the whole body is one person standing, crown to sole).
HEAD_SPAN = 0.13  # crown to chin: the fit's part of both models
TARGET_SPAN = 0.16  # the body's head and neck, for the swap's axis
SNAP_REACH = 0.012  # a head cut-edge point is laid onto the body's cut edge only within this distance (2 cm)
BAND = 0.02  # the shape's band above the cut (3.4 cm): the head's cut edge laid on the body's eases out across it
PAINT_BAND = 0.035  # the paint's band above the cut (6 cm): the head's paint blends from the body's across it
NORMAL_AGREE = 0.3  # two surfaces face the same way when their normals' dot is over this (a neck and a collar's
# inside do not)
NORMAL_REACH = 0.004  # within this of the cut (7 mm) the two sides' shading normals are averaged: no shading line
KEEP_RADIUS = 0.12  # the swap holds only within this of the head's axis (20 cm: never the shoulders' outer parts)
HOOD_SLAB = 0.012  # with a hood kept: the neck's parting from the hood read on this slab above the cut (2 cm)
HOOD_ANGLES = 18  # and per this many directions round the axis (20 degrees each)
NECK_RANGE = (0.025, 0.09)  # the parting looked for between these radii from the axis (4 to 15 cm)
FRONT_HALF_ANGLE = 40.0  # with a hood kept: the front (chin, throat) within this many degrees of -y stays the head's
# down to the cut even where no ring parts it from the collar (its faces need not turn outward: the chin's underside)
NECK_FALLBACK = 0.048  # the neck's reach (8 cm) where a hood lies against it with no empty ring between; with a hood
# kept, nothing of the head's under the hood's depth lies farther out, front included: the stairwell woman's open
# puffer collar stood 9 to 13 cm out within 40 to 80 degrees of the front, the head model's copy of it was kept there
# and drawn over the body's as torn shards and black holes (whole person round 5, 2026-11-27)
HOOD_GAP = 0.003  # an empty ring at least this wide (5 mm) parts them; narrower, nothing is round the neck there
TEXEL_SLACK = 0.02  # barycentric slack so a triangle's edge texels are painted too (no unblended rim)
# The chin over the cut (`chin_over_cut`), in body heights: read on slices 4 mm high of the face's middle column (2.7 cm
# wide), up to 13 cm over the cut; the chin is the lowest slice standing 2.5 cm forward of the throat (the woman of
# 2026-11-27: throat 0.015, chin 0.051, 3 cm over the cut)
CHIN_SLICE = 0.0025
CHIN_COLUMN = 0.008
CHIN_REACH = 0.08
CHIN_STEP = 0.015


def similarity(source, target, scale=None):
    """The least-squares similarity (scale, rotation 3x3, translation) taking `source` points onto `target` (Umeyama);
    with `scale` given, the best turn and shift at that scale."""
    source_middle, target_middle = source.mean(0), target.mean(0)
    source_centred, target_centred = source - source_middle, target - target_middle
    covariance = target_centred.T @ source_centred / len(source)
    left, singular, right = np.linalg.svd(covariance)
    sign = np.eye(3)
    sign[2, 2] = np.sign(np.linalg.det(left @ right)) or 1.0
    rotation = left @ sign @ right
    if scale is None:
        scale = float(np.trace(np.diag(singular) @ sign) / source_centred.var(0).sum())
    translation = target_middle - scale * rotation @ source_middle
    return scale, rotation, translation


def moved(points, scale, rotation, translation):
    """`points` under the similarity."""
    return scale * points @ rotation.T + translation


def trimmed_icp(source, target, start, nearest, held_of=None, rounds=ICP_ROUNDS, kept=ICP_KEPT, free_scale=True):
    """The similarity taking `source` points onto `target` points from `start` (scale, rotation, translation),
    matched both ways each round (each source point to its nearest target point and each target point to its nearest
    source point, so a free scale neither shrinks nor swells), each way fitting only its `kept` closest pairs; the
    start's scale held unless `free_scale`.
    `nearest(points)` gives a function answering queries' nearest indices among `points`; `held_of(placed)` picks the
    source points taking part where the fit has put them (all when None). Returns (scale, rotation, translation, rms of
    the kept pairs)."""
    scale, rotation, translation = start
    to_target = nearest(target)
    rms = math.inf
    for _ in range(rounds):
        placed = moved(source, scale, rotation, translation)
        held = np.ones(len(source), bool) if held_of is None else held_of(placed)
        taking, placed = source[held], placed[held]
        forward = to_target(placed)
        forward_gaps = np.linalg.norm(target[forward] - placed, axis=1)
        forward_kept = forward_gaps <= np.quantile(forward_gaps, kept)
        backward = nearest(placed)(target)
        backward_gaps = np.linalg.norm(placed[backward] - target, axis=1)
        backward_kept = backward_gaps <= np.quantile(backward_gaps, kept)
        scale, rotation, translation = similarity(
            np.vstack([taking[forward_kept], taking[backward[backward_kept]]]),
            np.vstack([target[forward[forward_kept]], target[backward_kept]]), None if free_scale else scale)
        rms = float(np.sqrt((np.concatenate([forward_gaps[forward_kept], backward_gaps[backward_kept]]) ** 2).mean()))
    return scale, rotation, translation, rms


def lowest(scales, misses):
    """The scale of least miss: the vertex of the parabola through the lowest miss and its neighbours (the lowest
    scale itself at either end of the scan)."""
    best = int(np.argmin(misses))
    if best in (0, len(scales) - 1):
        return float(scales[best])
    curve = np.polyfit(scales[best - 1:best + 2], misses[best - 1:best + 2], 2)
    return float(-curve[1] / (2 * curve[0])) if curve[0] > 0 else float(scales[best])


def chin_over_cut(heights, forward, across):
    """The chin's height over the cut (body heights): of the face's middle column (within CHIN_COLUMN either side), the
    lowest CHIN_SLICE whose front stands CHIN_STEP forward of the throat's (the column's lowest slice over the cut).
    `heights` over the cut and `forward`, `across` in body heights per point (forward toward the face). Refused when
    no slice stands out (no face over the cut)."""
    heights, forward = np.asarray(heights, float), np.asarray(forward, float)
    column = (np.abs(np.asarray(across, float)) < CHIN_COLUMN) & (heights >= 0.0) & (heights < CHIN_REACH)
    slices = np.floor(heights[column] / CHIN_SLICE).astype(int)
    if not len(slices):
        raise ValueError("no head points over the cut in the face's middle column")
    fronts = np.full(slices.max() + 1, -np.inf)
    np.maximum.at(fronts, slices, forward[column])
    throat = fronts[slices.min()]
    standing = np.flatnonzero(fronts > throat + CHIN_STEP)
    if not len(standing):
        raise ValueError("no chin stands forward of the throat over the cut")
    return float(standing[0] * CHIN_SLICE)


def eased(height, band):
    """The seam's weight at `height` above the cut: 1 at the cut, easing (smoothstep) to 0 at `band`, 0 above."""
    share = np.clip(1.0 - np.asarray(height, float) / band, 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def texels_of(triangle_uv, size, slack=TEXEL_SLACK):
    """The texel centres inside one UV triangle on a `size` x `size` texture: (columns, rows, barycentrics (n, 3))."""
    corners = np.asarray(triangle_uv, float) * size - 0.5
    low = np.floor(corners.min(0)).astype(int)
    high = np.ceil(corners.max(0)).astype(int)
    low, high = np.clip(low, 0, size - 1), np.clip(high, 0, size - 1)
    columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
    columns, rows = columns.ravel(), rows.ravel()
    edge_one, edge_two = corners[1] - corners[0], corners[2] - corners[0]
    area = edge_one[0] * edge_two[1] - edge_one[1] * edge_two[0]
    if abs(area) < 1e-12:
        return columns[:0], rows[:0], np.zeros((0, 3))
    offset_x, offset_y = columns - corners[0, 0], rows - corners[0, 1]
    second = (offset_x * edge_two[1] - offset_y * edge_two[0]) / area
    third = (edge_one[0] * offset_y - edge_one[1] * offset_x) / area
    weights = np.stack([1.0 - second - third, second, third], axis=1)
    inside = (weights >= -slack).all(1)
    return columns[inside], rows[inside], weights[inside]


def barycentric(points, corners):
    """Each point's barycentric weights (n, 3) in its triangle `corners` (n, 3, 3), the point projected onto it."""
    edge_one, edge_two = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    offset = points - corners[:, 0]
    dot_11 = (edge_one * edge_one).sum(1)
    dot_12 = (edge_one * edge_two).sum(1)
    dot_22 = (edge_two * edge_two).sum(1)
    dot_o1 = (offset * edge_one).sum(1)
    dot_o2 = (offset * edge_two).sum(1)
    denominator = np.where(np.abs(dot_11 * dot_22 - dot_12 ** 2) < 1e-20, 1e-20, dot_11 * dot_22 - dot_12 ** 2)
    second = (dot_22 * dot_o1 - dot_12 * dot_o2) / denominator
    third = (dot_11 * dot_o2 - dot_12 * dot_o1) / denominator
    return np.clip(np.stack([1.0 - second - third, second, third], axis=1), 0.0, 1.0)


def bilinear(image, uv):
    """`image` (h, w, c) read at the UVs (n, 2) (Blender's: v up, row 0 at the bottom), bilinear, wrapping clamped."""
    height, width = image.shape[:2]
    x = np.clip(uv[:, 0] * width - 0.5, 0, width - 1.001)
    y = np.clip(uv[:, 1] * height - 0.5, 0, height - 1.001)
    left, bottom = x.astype(int), y.astype(int)
    across, up = (x - left)[:, None], (y - bottom)[:, None]
    return (image[bottom, left] * (1 - across) * (1 - up) + image[bottom, left + 1] * across * (1 - up)
            + image[bottom + 1, left] * (1 - across) * up + image[bottom + 1, left + 1] * across * up)


def gltf_matrix(blender_matrix):
    """A 4x4 transform between Blender's frame (z up) written in the glTF frame (y up) of the files it moves."""
    to_blender = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
    return np.linalg.inv(to_blender) @ blender_matrix @ to_blender


# ---- Blender from here on -------------------------------------------------------------------------------------------


def imported(path, name):
    """The glb's one mesh as a new object called `name`, its transform applied (world coordinates in its data)."""
    import bpy
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [item for item in bpy.data.objects if item not in before]
    meshes = [item for item in new if item.type == "MESH"]
    if len(meshes) != 1:
        raise SystemExit(f"{path}: expected one mesh, found {len(meshes)}")
    mesh = meshes[0]
    mesh.data.transform(mesh.matrix_world)
    mesh.parent = None
    mesh.matrix_world.identity()
    for item in new:
        if item is not mesh:
            bpy.data.objects.remove(item)
    mesh.name = name
    return mesh


def vertices_of(mesh):
    """The mesh's vertex positions (n, 3)."""
    positions = np.zeros(len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("co", positions)
    return positions.reshape(-1, 3)


def normals_of(mesh):
    """The mesh's vertex normals (n, 3)."""
    normals = np.zeros(len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("normal", normals)
    return normals.reshape(-1, 3)


def nearest_on(points):
    """A function answering each query point's nearest index among `points` (a KD tree)."""
    from mathutils import kdtree
    tree = kdtree.KDTree(len(points))
    for number, point in enumerate(points):
        tree.insert(point, number)
    tree.balance()

    def answer(queries):
        return np.array([tree.find(query)[1] for query in queries], int)
    return answer


def fitted(body, head):
    """The head's similarity onto the body's head: the head model's head (what the fit puts above the body's chin)
    matched both ways onto the body's head, hair and all. A free scale slides slowly along a long valley, so the scale
    is scanned instead: at each, the best turn and shift (stood crown on crown, centred, then a rigid two-way ICP) and
    its miss; the least miss's scale (a parabola through its neighbours) fitted once more. Returns (scale, rotation,
    translation, rms, crown, middle x, body height)."""
    rng = np.random.default_rng(0)
    body_points, head_points = vertices_of(body), vertices_of(head)
    height = float(np.ptp(body_points[:, 2]))
    crown = float(body_points[:, 2].max())
    chin = crown - HEAD_SPAN * height
    target = body_points[body_points[:, 2] > chin]
    target = target[rng.choice(len(target), min(FIT_POINTS, len(target)), replace=False)]
    source = head_points[rng.choice(len(head_points), min(5 * FIT_POINTS, len(head_points)), replace=False)]
    head_crown = float(head_points[:, 2].max())
    middle = np.median(target, axis=0)

    def held_of(placed):
        held = np.zeros(len(placed), bool)
        above = np.where(placed[:, 2] > chin)[0]
        held[rng.permutation(above)[:FIT_POINTS]] = True
        return held

    def fit_at(scale, rounds):
        upper = source[source[:, 2] > head_crown - HEAD_SPAN * height / scale]
        shift = np.array([middle[0] - scale * np.median(upper[:, 0]), middle[1] - scale * np.median(upper[:, 1]),
                          crown - scale * head_crown])
        return trimmed_icp(source, target, (scale, np.eye(3), shift), nearest_on, held_of, rounds, free_scale=False)

    misses = np.array([fit_at(scale, SCAN_ROUNDS)[3] for scale in START_SCALES])
    print("FIT scan " + " ".join(f"{scale:.2f}:{miss:.5f}" for scale, miss in zip(START_SCALES, misses)), flush=True)
    best = fit_at(lowest(START_SCALES, misses), ICP_ROUNDS)
    print(f"FIT scale {best[0]:.4f}, rms {best[3]:.5f}", flush=True)
    return (*best, crown, float(middle[0]), height)


def split_at(mesh, level):
    """The mesh's faces cut along the level plane z = `level` (no faces removed yet)."""
    import bmesh
    from mathutils import Vector
    built = bmesh.new()
    built.from_mesh(mesh.data)
    bmesh.ops.bisect_plane(built, geom=built.verts[:] + built.edges[:] + built.faces[:], dist=1e-7,
                           plane_co=Vector((0, 0, level)), plane_no=Vector((0, 0, 1)))
    return built


def dropped(built, mesh, keep):
    """The faces `keep` (centre, normal -> bool) refuses deleted, loose vertices too, the cut's split faces made
    triangles again; written back to `mesh`."""
    import bmesh
    gone = [face for face in built.faces if not keep(face.calc_center_median(), face.normal)]
    bmesh.ops.delete(built, geom=gone, context="FACES")
    loose = [vertex for vertex in built.verts if not vertex.link_faces]
    bmesh.ops.delete(built, geom=loose, context="VERTS")
    bmesh.ops.triangulate(built, faces=[face for face in built.faces if len(face.verts) > 3])
    built.to_mesh(mesh.data)
    built.free()
    mesh.data.update()


def cut_edge(mesh, level):
    """The mesh's open-edge vertices lying on the cut: (indices, positions)."""
    import bmesh
    built = bmesh.new()
    built.from_mesh(mesh.data)
    found = [vertex.index for vertex in built.verts if vertex.is_boundary and abs(vertex.co.z - level) < 1e-5]
    built.free()
    points = vertices_of(mesh)
    return np.array(found, int), points[found]


def cut_segments(mesh, level):
    """The body's open edges along the cut, as (start points, end points, unit normals: their ends' mean)."""
    import bmesh
    built = bmesh.new()
    built.from_mesh(mesh.data)
    built.normal_update()
    pairs = [(tuple(edge.verts[0].co), tuple(edge.verts[1].co), tuple(edge.verts[0].normal + edge.verts[1].normal))
             for edge in built.edges
             if edge.is_boundary and all(abs(vertex.co.z - level) < 1e-5 for vertex in edge.verts)]
    built.free()
    pairs = np.array(pairs, float).reshape(-1, 3, 3)
    normals = pairs[:, 2] / np.maximum(np.linalg.norm(pairs[:, 2], axis=1, keepdims=True), 1e-9)
    return pairs[:, 0], pairs[:, 1], normals


def onto_segments(points, normals, starts, ends, segment_normals):
    """Each point's closest point on the segments facing its way (normals agreeing by NORMAL_AGREE: a neck's edge is
    never laid on a collar's inside), brute force in chunks (the cut holds a few thousand); a point no segment faces
    gets its own place."""
    found = np.zeros_like(points)
    along = ends - starts
    length = np.maximum((along * along).sum(1), 1e-20)
    for first in range(0, len(points), 256):
        chunk = points[first:first + 256]
        share = np.clip(((chunk[:, None] - starts[None]) * along[None]).sum(2) / length[None], 0.0, 1.0)
        closest = starts[None] + share[..., None] * along[None]
        gaps = ((closest - chunk[:, None]) ** 2).sum(2)
        facing = normals[first:first + 256] @ segment_normals.T > NORMAL_AGREE
        gaps[~facing] = np.inf
        pick = np.argmin(gaps, 1)
        chosen = closest[np.arange(len(chunk)), pick]
        found[first:first + 256] = np.where(facing.any(1)[:, None], chosen, chunk)
    return found


def seam_closed(head, body, level, reach, band):
    """The head's cut edge laid onto the body's (each edge point within `reach` of a body cut edge facing its way
    moved onto it), the move eased out over `band` above the cut. Returns the share of the head's edge laid."""
    edge_indices, edge_points = cut_edge(head, level)
    targets = onto_segments(edge_points, normals_of(head)[edge_indices], *cut_segments(body, level))
    shifts = targets - edge_points
    gaps = np.linalg.norm(shifts, axis=1)
    laid = (gaps < reach) & (gaps > 0)
    shifts[~laid] = 0.0
    points = vertices_of(head)
    near = np.where(points[:, 2] < level + band)[0]
    owner = nearest_on(edge_points)
    points[near] += shifts[owner(points[near])] * eased(points[near, 2] - level, band)[:, None]
    points[edge_indices] = edge_points + shifts
    head.data.vertices.foreach_set("co", points.ravel())
    head.data.update()
    return float(laid.mean())


def image_array(image):
    """The image's pixels (h, w, 4) floats as stored (row 0 at the bottom)."""
    pixels = np.zeros(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(image.size[1], image.size[0], 4)


def textures_of(mesh):
    """{role: image} of the mesh's one material: its base colour and metal-roughness images."""
    found = {}
    for node in mesh.data.materials[0].node_tree.nodes:
        if node.type != "TEX_IMAGE":
            continue
        linked = [link.to_socket.name for link in node.outputs["Color"].links]
        found["base" if "Base Color" in linked else "metal_rough"] = node.image
    return found


class Surface:
    """The uncut body's surface: the closest point's UV for any query point (a BVH over its triangles)."""

    def __init__(self, mesh):
        from mathutils.bvhtree import BVHTree
        self.points = vertices_of(mesh)
        corners = np.zeros(len(mesh.data.loops), int)
        mesh.data.loops.foreach_get("vertex_index", corners)
        self.triangles = corners.reshape(-1, 3)
        uv = np.zeros(len(mesh.data.loops) * 2)
        mesh.data.uv_layers.active.data.foreach_get("uv", uv)
        self.uv = uv.reshape(-1, 3, 2)
        self.tree = BVHTree.FromPolygons(self.points.tolist(), self.triangles.tolist(), all_triangles=True)

    def uv_at(self, queries, normals, reach):
        """The UV (n, 2) of the body's surface at each query: where the line along the query's normal first meets a
        body face facing its way (within `reach` either side), else its closest surface point."""
        from mathutils import Vector
        located, faces = np.zeros_like(queries), np.zeros(len(queries), int)
        for number, (query, normal) in enumerate(zip(queries, normals)):
            hits = []
            for way in (1.0, -1.0):
                start = Vector(query - way * normal * 1e-5)
                location, face_normal, face, distance = self.tree.ray_cast(start, Vector(way * normal), reach)
                if location is not None and face_normal.dot(Vector(normal)) > NORMAL_AGREE:
                    hits.append((distance, location, face))
            if hits:
                _, location, face = min(hits, key=lambda hit: hit[0])
            else:
                location, _, face, _ = self.tree.find_nearest(query)
            located[number], faces[number] = location, face
        weights = barycentric(located, self.points[self.triangles[faces]])
        return (self.uv[faces] * weights[..., None]).sum(1)


def paint_blended(head, body_surface, body_images, level, band, reach, out_folder, name):
    """The head's texels on the band above the cut blended toward the body's paint at the same place (all body at the
    cut, all head at the band's top), base colour and metal-roughness alike, saved as new images; the body's paint read
    along each texel's normal within `reach`. Returns texels painted."""
    import bpy
    points, normals = vertices_of(head), normals_of(head)
    corners = np.zeros(len(head.data.loops), int)
    head.data.loops.foreach_get("vertex_index", corners)
    triangles = corners.reshape(-1, 3)
    uv = np.zeros(len(head.data.loops) * 2)
    head.data.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 3, 2)
    images = textures_of(head)
    size = images["base"].size[0]
    in_band = np.where((points[triangles, 2] < level + band).any(1))[0]
    columns, rows, places, facing = [], [], [], []
    for triangle in in_band:
        column, row, weights = texels_of(uv[triangle], size)
        columns.append(column)
        rows.append(row)
        places.append(weights @ points[triangles[triangle]])
        facing.append(weights @ normals[triangles[triangle]])
    columns, rows, places = np.concatenate(columns), np.concatenate(rows), np.concatenate(places)
    facing = np.concatenate(facing)
    facing /= np.maximum(np.linalg.norm(facing, axis=1, keepdims=True), 1e-9)
    weight = eased(places[:, 2] - level, band)[:, None]
    body_uv = body_surface.uv_at(places, facing, reach)
    for role, image in images.items():
        pixels = image_array(image)
        theirs = bilinear(body_images[role], body_uv)
        pixels[rows, columns, :3] = pixels[rows, columns, :3] * (1 - weight) + theirs[:, :3] * weight
        blended = bpy.data.images.new(f"{name}_head_{role}", size, size, alpha=True)
        blended.colorspace_settings.name = image.colorspace_settings.name
        blended.pixels.foreach_set(pixels.ravel())
        blended.filepath_raw = str(pathlib.Path(out_folder) / f"{name}_head_{role}.png")
        blended.file_format = "PNG"
        blended.save()
        for material in head.data.materials:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image == image:
                    node.image = blended
    return len(rows)


def shaded_across(mesh, level, reach):
    """The joined mesh's shading normals near the cut made one smooth field across it: each vertex within `reach` of
    the cut takes the mean normal of every vertex (either side) within `reach` of it facing its way, eased back to its own over the
    reach, so the two sides' differing normals draw no line."""
    points, normals = vertices_of(mesh), normals_of(mesh)
    seam_distance = np.abs(points[:, 2] - level)
    near = np.where(seam_distance < reach)[0]
    from mathutils import kdtree
    tree = kdtree.KDTree(len(near))
    for number, index in enumerate(near):
        tree.insert(points[index], number)
    tree.balance()
    shaded = normals.copy()
    for index in near:
        found = [number for _, number, _ in tree.find_range(points[index], reach)
                 if normals[near[number]] @ normals[index] > NORMAL_AGREE]
        mean = normals[near[found]].mean(0)
        share = 1.0 - seam_distance[index] / reach
        blended = normals[index] * (1 - share) + mean / max(np.linalg.norm(mean), 1e-9) * share
        shaded[index] = blended / max(np.linalg.norm(blended), 1e-9)
    mesh.data.normals_split_custom_set_from_vertices(shaded.tolist())
    mesh.data.update()


def transform_record(fit, level, band, laid, texels):
    """The head-to-body transform (Blender and glTF frames) and the cut, as the JSON record."""
    scale, rotation, translation, rms = fit
    matrix = np.eye(4)
    matrix[:3, :3] = scale * rotation
    matrix[:3, 3] = translation
    return {
        "head_to_body_gltf": gltf_matrix(matrix).round(8).tolist(),
        "head_to_body_blender": matrix.round(8).tolist(),
        "scale": round(float(scale), 6),
        "note": ("apply head_to_body_gltf (4x4, column vectors) to points in the head glb's frame to place them in "
                 "the body glb's frame; the head's vertices within the band above the cut were also eased to close "
                 "the seam, everything higher follows the matrix alone"),
        "cut_level_gltf_y": round(level, 6),
        "band": round(band, 6),
        "head_fit_rms": round(float(rms), 6),
        "head_edge_laid_share": round(laid, 4),
        "texels_blended": int(texels),
    }


def neck_gaps(points, axis, level, height):
    """Where a hood or high collar parts from the neck, per direction round the axis (HOOD_ANGLES bins), read on the
    slab just above the cut (HOOD_SLAB high, where both are plain): the middle of the widest empty ring between
    NECK_RANGE's radii (over HOOD_GAP wide); where the hood lies against the neck with no such ring but reaches out
    past two thirds of the range, NECK_FALLBACK; else infinity (nothing round the neck that way). (HOOD_ANGLES,) radii."""
    slab = points[(points[:, 2] > level) & (points[:, 2] < level + HOOD_SLAB * height)]
    across = slab[:, :2] - np.asarray(axis)
    radius = np.hypot(across[:, 0], across[:, 1])
    which = direction_bin(across)
    gaps = np.full(HOOD_ANGLES, np.inf)
    for bin_number in range(HOOD_ANGLES):
        ring = np.sort(radius[which == bin_number])
        ring = ring[(ring > NECK_RANGE[0] * height) & (ring < NECK_RANGE[1] * height)]
        if len(ring) < 2:
            continue
        widths = np.diff(ring)
        widest = int(np.argmax(widths))
        if widths[widest] > HOOD_GAP * height:
            gaps[bin_number] = (ring[widest] + ring[widest + 1]) / 2.0
        elif ring[-1] > NECK_RANGE[1] * height * 0.65:
            gaps[bin_number] = NECK_FALLBACK * height
    return gaps


def direction_bin(across):
    """Each (x, y) offset's direction bin round the axis (0 at the back, the front, -y, in the middle)."""
    angle = np.degrees(np.arctan2(across[..., 0], -across[..., 1]))
    return np.clip(((angle + 180.0) / 360.0 * HOOD_ANGLES).astype(int), 0, HOOD_ANGLES - 1)


def kept_region(level, crown, height, axis, hood, body_points):
    """The test (face centre, normal -> bool) of what the head model gives above the cut: within KEEP_RADIUS of the
    head's axis; with `hood` (a depth under the crown, body heights), under that depth only what lies inside the empty
    ring parting the neck from the body's hood or high collar (`neck_gaps`) and within the neck's reach
    (NECK_FALLBACK), so that hood stays the body's. Given a face's normal (the head's faces), only faces turned outward
    count (a neck is, a hood's inside is not), the front (chin and throat, within FRONT_HALF_ANGLE of -y) excepted;
    the body loses all inside the ring."""
    top = crown - hood * height if hood is not None else None
    gaps = neck_gaps(body_points, axis, level, height) if hood is not None else None

    def kept(centre, normal=None):
        across = np.array([centre.x - axis[0], centre.y - axis[1]])
        radius = math.hypot(*across)
        if centre.z < level or radius > KEEP_RADIUS * height:
            return False
        if top is None or centre.z > top:
            return True
        if radius > min(gaps[direction_bin(across)], NECK_FALLBACK * height):
            return False
        front = abs(math.degrees(math.atan2(across[0], -across[1]))) < FRONT_HALF_ANGLE
        return front or normal is None or normal.x * across[0] + normal.y * across[1] > 0
    return kept


def main():
    import bpy
    from mathutils import Matrix
    arguments = sys.argv[sys.argv.index("--") + 1:]
    body_path, head_path, cut_depth, out_glb, out_json = arguments[:5]
    hood = float(arguments[5]) if len(arguments) > 5 else None
    name = pathlib.Path(out_glb).stem
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = imported(body_path, "body")
    head = imported(head_path, "head")
    *fit, crown, middle_x, height = fitted(body, head)
    matrix = np.eye(4)
    matrix[:3, :3] = fit[0] * fit[1]
    matrix[:3, 3] = fit[2]
    head.data.transform(Matrix(matrix.tolist()))
    head.data.update()
    level = float(crown - float(cut_depth) * height)
    band = BAND * height
    points = vertices_of(body)
    head_part = points[points[:, 2] > crown - TARGET_SPAN * height]
    kept = kept_region(level, crown, height, (middle_x, float(np.median(head_part[:, 1]))), hood, points)
    body_surface = Surface(body)
    body_images = {role: image_array(image) for role, image in textures_of(body).items()}
    dropped(split_at(body, level), body, lambda centre, normal: not kept(centre))
    dropped(split_at(head, level), head, kept)
    laid = seam_closed(head, body, level, SNAP_REACH * height, band)
    texels = paint_blended(head, body_surface, body_images, level, PAINT_BAND * height, SNAP_REACH * height,
                           pathlib.Path(out_glb).parent, name)
    print(f"SEAM level {level:.4f}, band {band:.4f}, head edge laid {laid:.3f}, texels blended {texels}", flush=True)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = name
    shaded_across(body, level, NORMAL_REACH * height)
    bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_selection=True, export_yup=True)
    record = transform_record(fit, level, band, laid, texels)
    record.update({"body": str(body_path), "head": str(head_path), "cut_depth_under_crown": float(cut_depth),
                   "hood_depth_under_crown": hood, "body_height_units": round(height, 6)})
    pathlib.Path(out_json).write_text(json.dumps(record, indent=1))
    print("HEAD SWAP DONE", out_glb, flush=True)


if __name__ == "__main__":
    main()
