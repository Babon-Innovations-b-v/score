"""The finish route's texels (#159): each texel of the model's own texture given its finish and part, so a finish's
border follows the texture's own colour edge at picture detail, not the model's triangles.

The split gives each face one finish (route_split), and the look drawn face by face shows every triangle along a
border: TRELLIS.2's small uneven triangles made the desk top's front edge chewed, specks on its legs and a sawtooth on
the toaster's side (tc3s, 2026-11-23), where run 1's own painted picture had smooth edges. Here, free, on this PC's
processor, from what the views row measured of the texture (`texels.npz`: the face under each texel and its colour
region, the regions the list labelled):

- `face_texels`: each texel's face, the faces' UV triangles filled into each picture (PIL), a texel no face covers -1.
- `region_weights`: how often the list labelled each region with each finish over the views (the close-up's front and
  the laid close-up FRONT_VOTE), so a texel's colour names the finish its region was labelled.
- `carriers`: per face and finish, the part of the nearest face of that finish within REACH border steps along the
  surface (-1 none): the coarser of a view's pixel and a face, what a face's finish is settled by. A texel may take
  only a finish that lies that near its face: the colour moves a border to the texture's edge, never paints a finish
  where the split put none (a dark shading spot in the middle of a white top stays white).
- `texel_parts`: each texel the part of the finish its region weighs most among those near its face (its face's own on
  a tie, or when its region names none of them).
- `without_specks`: each speck given the part round it. An island is the texels of one part joined across texel edges
  and, over the UV seams, across the faces they lie on (`islands`); a speck is one under SPECK_PIXELS of the views'
  pixels that is not its finish's largest island (a finish whose one area is small, the toaster's red light, keeps it).
- `filled`: each texel no face covers given the part of the nearest covered one, so a picture read between texels at a
  chart's border reads its own part, not the empty texel's.

The faces keep their parts (parts.npy): physics, the measures and every reader of the parts take a part a face; only
the look reads the texels (`<take>/texels.npz` in the split and the parts rows, one uint16 part map a picture, as
`piece<k>` of the model's pieces in their file order).
"""
import numpy as np

# How far along the surface, in border steps (border_step), a texel may reach for the finish its colour names. On tc3s
# the share of the seen area whose texels' colour named another finish than the one they took, at 0, 1, 2, 3, 4, 6 and
# 8 steps: the desk 0.87, 0.45, 0.15, 0.08, 0.05, 0.04 and 0.04%; the toaster 3.27, 2.56, 1.38, 1.22, 1.02, 0.49 and
# 0.23%. Drawn, the desk's front edge kept three white notches at three steps and was as clean as TRELLIS.2's own
# picture at six; the toaster looked the same at three and six. Further, its colours name finishes a hand's width off
# (its body's shading bands), which the views outvoted: no border the triangles moved.
REACH = 6
# An island smaller than a 2 x 2 block of the views' pixels (route_cast.SIDE across the bounding sphere) is a speck
# unless it is its finish's largest: no view showed it as a thing apart, so the list never judged it. On tc3s at REACH,
# the desk's 138 islands under it (the flecks on its legs and top edge, 0.009% of its area) and the toaster's 80
# (0.010%) went; every island of four pixels and more stayed: the toaster's red light (9.1 and 19.6 pixels), its dial
# marks, the desk's grommet (68 and more).
SPECK_PIXELS = 4.0
NO_PART = np.iinfo(np.uint16).max


def face_texels(corner_uv, faces, shape):
    """Each texel's face (-1 where no face covers it) of one picture of `shape` (rows, columns): `faces` (their ids)
    laid by their corners' UVs (n x 3 x 2, glTF's: v up), filled in face order, the texel read as route_cast reads
    it (column u x width, row (1 - v) x height)."""
    from PIL import Image, ImageDraw
    height, width = shape
    picture = Image.new("I", (width, height), -1)
    draw = ImageDraw.Draw(picture)
    corners = np.stack([corner_uv[..., 0] * width, (1.0 - corner_uv[..., 1]) * height], axis=-1)
    for face, points in zip(faces.tolist(), corners.tolist()):
        draw.polygon([tuple(point) for point in points], fill=face)
    return np.asarray(picture, dtype=np.int64).reshape(height, width)


def region_weights(labels, region_count, count, front_vote, front_views):
    """(region x finish) how strongly the list labelled each region with each finish: one a view, `front_vote` for the
    views `front_views` names."""
    found = np.zeros((region_count, count))
    for view, labelled in labels.items():
        for region, finish in labelled.items():
            found[int(region), int(finish)] += front_vote if view in front_views else 1.0
    return found


def carriers(mesh, part_of, finish_of, count, reach):
    """(face x finish) the part of the face of that finish nearest each face along the surface (face middles joined
    across shared edges), -1 where none lies within `reach`; a face's own finish carries its own part."""
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra
    pairs = mesh.face_adjacency
    middles = mesh.triangles_center
    length = np.linalg.norm(middles[pairs[:, 0]] - middles[pairs[:, 1]], axis=1) + 1e-12
    faces = len(part_of)
    ends = (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])
    graph = sparse.coo_matrix((np.r_[length, length], ends), shape=(faces, faces)).tocsr()
    found = np.full((faces, count), -1, dtype=np.int64)
    for finish in range(count):
        sources = np.flatnonzero(finish_of == finish)
        if not len(sources):
            continue
        distance, _, source = dijkstra(graph, directed=False, indices=sources, min_only=True, limit=reach,
                                       return_predecessors=True)
        reached = np.isfinite(distance) & (source >= 0)
        found[reached, finish] = part_of[source[reached]]
    return found


def view_pixel(mesh):
    """The side of one pixel of the views row's casts (route_cast.rays frames the bounding sphere at route_cast.SIDE),
    in the model's own units."""
    import route_cast as cast
    return 2.0 * float(np.linalg.norm(mesh.vertices, axis=1).max()) * cast.MARGIN / cast.SIDE


def border_step(mesh):
    """The coarser of what settles a face's finish: one pixel of the views (every face under it takes its region) or
    the median distance between neighbouring faces' middles (a face takes one finish whole), in the model's units."""
    pairs = mesh.face_adjacency
    middles = mesh.triangles_center
    return max(view_pixel(mesh), float(np.median(np.linalg.norm(middles[pairs[:, 0]] - middles[pairs[:, 1]], axis=1))))


def texel_parts(face_of, region_of, weights, carried, finish_of):
    """Each texel's part (-1 where no face covers it): the finish its region weighs most among those `carried` near its
    face, its face's own on a tie or where its region names none of them."""
    covered = face_of >= 0
    faces, regions = face_of[covered], region_of[covered]
    near = carried[faces]
    score = np.where(near >= 0, weights[np.maximum(regions, 0)], -1.0)
    score[regions < 0] = -1.0
    own = finish_of[faces]
    score[np.arange(len(faces)), own] = np.maximum(score[np.arange(len(faces)), own], 0.0) + 0.5
    found = np.full(face_of.shape, -1, dtype=np.int64)
    found[covered] = near[np.arange(len(faces)), score.argmax(1)]
    return found


def texel_areas(maps, areas):
    """{piece: each texel's share of the model's area}: its face's area over the texels its face covers, in every
    picture."""
    counts = np.zeros(len(areas))
    for face_of in maps.values():
        np.add.at(counts, face_of[face_of >= 0], 1.0)
    share = areas / max(areas.sum(), 1e-12) / np.maximum(counts, 1.0)
    return {piece: np.where(face_of >= 0, share[np.maximum(face_of, 0)], 0.0) for piece, face_of in maps.items()}


def islands(parts, faces, mesh):
    """(each texel's island over every picture, flat in `parts`' piece order; -1 off the faces): texels of one part
    joined across texel edges, and two such pieces of one part joined where they lie on the same or edge-neighbouring
    faces (a UV seam cuts one island in two pictures' places)."""
    from scipy import sparse
    from scipy.ndimage import label
    flat_parts = np.concatenate([parts[piece].ravel() for piece in parts])
    flat_faces = np.concatenate([faces[piece].ravel() for piece in parts])
    patch = np.full(len(flat_parts), -1, dtype=np.int64)
    offset, start = 0, 0
    for piece in parts:
        size = parts[piece].size
        for part in np.unique(parts[piece][parts[piece] >= 0]):
            found, number = label(parts[piece] == part)
            mine = found.ravel() > 0
            patch[start:start + size][mine] = found.ravel()[mine] - 1 + offset
            offset += number
        start += size
    covered = patch >= 0
    if not covered.any():
        return patch
    on = sparse.coo_matrix((np.ones(int(covered.sum())), (patch[covered], flat_faces[covered])),
                           shape=(offset, len(mesh.faces))).tocsr()
    on.data[:] = 1.0
    pairs = mesh.face_adjacency
    near = sparse.identity(len(mesh.faces), format="csr") + sparse.coo_matrix(
        (np.ones(2 * len(pairs)), (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
        shape=(len(mesh.faces), len(mesh.faces))).tocsr()
    touching = (on @ near @ on.T).tocoo()
    part_of_patch = np.zeros(offset, dtype=np.int64)
    part_of_patch[patch[covered]] = flat_parts[covered]
    same = part_of_patch[touching.row] == part_of_patch[touching.col]
    graph = sparse.coo_matrix((np.ones(int(same.sum())), (touching.row[same], touching.col[same])),
                              shape=(offset, offset))
    joined = sparse.csgraph.connected_components(graph, directed=False)[1]
    return np.where(covered, joined[np.maximum(patch, 0)], -1)


def speck_islands(island, flat_parts, flat_area, finish_of_part, least):
    """Whether each island is a speck: under `least` (a share of the area) and not its finish's largest island."""
    count = int(island.max()) + 1
    covered = island >= 0
    area = np.bincount(island[covered], weights=flat_area[covered], minlength=count)
    part = np.zeros(count, dtype=np.int64)
    part[island[covered]] = flat_parts[covered]
    finish = finish_of_part[part]
    largest = np.zeros(int(finish.max()) + 1)
    np.maximum.at(largest, finish, area)
    return (area < least) & (area < largest[finish])


def without_specks(parts, faces, mesh, areas, finish_of_part, least):
    """({piece: part per texel} with each speck given the part its bordering texels hold most, round by round until
    none is left or none borders another part; the share of the area moved). Only texels of larger islands vote, so two
    specks never swap."""
    pieces = list(parts)
    shapes = [parts[piece].shape for piece in pieces]
    flat = np.concatenate([parts[piece].ravel() for piece in pieces])
    flat_area = np.concatenate([areas[piece].ravel() for piece in pieces])
    starts = np.cumsum([0] + [int(np.prod(shape)) for shape in shapes])
    moved = 0.0
    while True:  # each round gives at least one speck a larger island's part, so it ends
        current = {piece: flat[starts[index]:starts[index + 1]].reshape(shapes[index])
                   for index, piece in enumerate(pieces)}
        island = islands(current, faces, mesh)
        if not (island >= 0).any():
            return current, moved
        speck = speck_islands(island, flat, flat_area, finish_of_part, least)
        covered = island >= 0
        island_area = np.bincount(island[covered], weights=flat_area[covered], minlength=len(speck))
        voters, given_parts = [], []
        for index, (rows, columns) in enumerate(shapes):
            grid = island[starts[index]:starts[index + 1]].reshape(rows, columns)
            here = flat[starts[index]:starts[index + 1]].reshape(rows, columns)
            for one, other in neighbour_slices():
                mine, theirs = grid[one].ravel(), grid[other].ravel()
                voting = (mine >= 0) & (theirs >= 0) & (mine != theirs)
                voting &= speck[np.maximum(mine, 0)] & (island_area[np.maximum(theirs, 0)]
                                                       > island_area[np.maximum(mine, 0)])
                voters.append(mine[voting])
                given_parts.append(here[other].ravel()[voting])
        voters, given_parts = np.concatenate(voters), np.concatenate(given_parts)
        if not len(voters):
            return current, moved
        pairs, tally = np.unique(np.stack([voters, given_parts], axis=1), axis=0, return_counts=True)
        order = np.lexsort((tally, pairs[:, 0]))  # per speck, its most voted part last
        last = order[np.r_[pairs[order[1:], 0] != pairs[order[:-1], 0], True]]
        given = np.full(len(speck), -1, dtype=np.int64)
        given[pairs[last, 0]] = pairs[last, 1]
        change = covered & (given[np.maximum(island, 0)] >= 0)
        moved += float(flat_area[change].sum())
        flat = np.where(change, given[np.maximum(island, 0)], flat)


def neighbour_slices():
    """(this texel, its neighbour) slice pairs of a picture: the right, left, lower and upper neighbours."""
    ahead, behind = (slice(None), slice(1, None)), (slice(None), slice(None, -1))
    below, above = (slice(1, None), slice(None)), (slice(None, -1), slice(None))
    return ((ahead, behind), (behind, ahead), (below, above), (above, below))


def filled(parts):
    """The part map with each texel no face covers given the part of the nearest covered texel (all NO_PART when
    none is covered), as uint16."""
    from scipy.ndimage import distance_transform_edt
    empty = parts < 0
    if empty.all():
        return np.full(parts.shape, NO_PART, dtype=np.uint16)
    _, (rows, columns) = distance_transform_edt(empty, return_indices=True)
    return parts[rows, columns].astype(np.uint16)


def take_texels(mesh, texels, regions, split):
    """({piece: part per texel, uint16}, its record) of one take: `texels` the views row's (each picture's face and
    region per texel), `regions` (region x finish weights: region_weights), `split` (part per face, finish per face).
    The record: the share of the area whose texels took another face's part (`moved`) and the specks' (`specks`)."""
    part_of, finish_of = split
    faces = {piece: texels[f"face{piece}"] for piece in pieces_of(texels)}
    carried = carriers(mesh, part_of, finish_of, regions.shape[1], REACH * border_step(mesh))
    parts = {piece: texel_parts(faces[piece], texels[f"region{piece}"], regions, carried, finish_of)
             for piece in faces}
    areas = texel_areas(faces, mesh.area_faces)
    moved = sum(float(areas[piece][(parts[piece] >= 0) & (parts[piece] != part_of[np.maximum(faces[piece], 0)])].sum())
                for piece in faces)
    finish_of_part = np.zeros(int(part_of.max()) + 1, dtype=np.int64)
    finish_of_part[part_of] = finish_of
    least = SPECK_PIXELS * view_pixel(mesh) ** 2 / mesh.area
    parts, specks = without_specks(parts, faces, mesh, areas, finish_of_part, least)
    return ({piece: filled(found) for piece, found in parts.items()},
            {"moved": round(moved, 4), "specks": round(specks, 5)})


def pieces_of(texels):
    """The piece numbers the views row measured a picture of, in order."""
    return sorted(int(name[len("face"):]) for name in texels if name.startswith("face"))
