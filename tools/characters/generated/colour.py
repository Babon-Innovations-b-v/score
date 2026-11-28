"""A generated model's paint toned toward its photo, garment by garment (#223).

TRELLIS.2 paints its own guess of the albedo, and on a glossy or dark garment the guess drifts far from the photo it
was made from (measured on the first round, 2026-11-26, sRGB means of matched regions, photo against paint): a
sage puffer jacket (131, 137, 123) painted grey-green (65, 72, 68), brown ankle boots (89, 51, 41) painted black
(14, 3, 0), a navy turtleneck (20, 21, 35) painted neutral grey (34, 33, 33), white wool (229, 219, 206) painted
(168, 156, 140). Its metalness is 0 everywhere and the import reads the maps rightly (base colour sRGB, metal-rough
non-colour); the drift is the paint's.

Every texel gets the height of the model point nearest it in UV (`toned_texture`), and the paint is clustered
(PAINT_CLUSTERS) on CIELAB plus height (HEIGHT_LAB Lab units over the whole height), so a garment the paint drew in
nearly the colour of its neighbour (the boots painted as black as the trousers) is still a cluster of its own. The
model seen from the front (its vertices splatted onto a grid, the front-most kept) is laid on the photo's cut-out
person by their boxes. The photo's colours are clustered too (PHOTO_CLUSTERS); its clusters of one hue (within
GARMENT_AB in a and b) and near lightness (within GARMENT_L), every two of them (complete linkage), are one colour
garment, the lit and shaded side of a coat or a plaid's dark and light lines (`photo_garments`), and each connected
piece of one is a photo garment (`photo_regions`: brown boots and a coat's brown shade lie apart on the body).

A paint cluster's garment is the photo garment most of its front pixels land on (`garments`); paint clusters alike
in paint (within PAINT_SAME) whose garments are of one colour are joined (`merged`: a coat painted one colour, lit
above and shaded below in the photo, gets one move, not a band at the shade's edge). A garment's photo colour is
read where its front pixels land, only off the photo garments that take at least LANDED_SHARE of them (a misaligned
edge's other garment left out); its texels are moved so its median and spread (1.4826 x the median absolute
deviation, each Lab channel, the ratio held in SPREAD_RANGE) become the photo's: one move for the whole garment, so
the folds, shading and seams the paint drew are kept. A texel takes each cluster's move by its share in that
cluster (SOFT_LAB, nearly hard: a softer share let the boots' move tint the trousers above them); a cluster seen on
fewer than MIN_PIXELS front pixels, or landing mostly on the photo's specks, keeps its paint. The model's own paint
stays its own (a generated model keeps its own paint: data/checks/library-exceptions.json); only its colour is
brought back to its photo's. Run it on the raw model, before the head swap, the hair and still_rig's grade.

A texel the front sees (its surface facing it, `seen_places`) on a garment's place takes only that garment's
clusters (`seen_allowed`), never the kept body's by colour alone (2026-11-28: the older woman's cream scarf, shaded by
her neck and down its edges, fell in her grey hair's cluster by colour and height and kept its paint, grey-brown
streaks on a scarf lifted to L 84 round them). A place is a photo garment's piece (inside or under the photo's body
zone, two places: grey hair and a white scarf can be one colour piece), and its clusters are those of the garments
landing on at least LANDED_SHARE of its front pixels (`place_clusters`); a place the kept body lands on says nothing,
so a place only ever gives a texel a garment's move, never takes one away. A texel whose colour is like none of its
place's clusters (`alike`: the front is laid on the photo by the boxes, an edge may land on its neighbour), and one the
front does not see, is clustered as before.

Garments only: the person's body (skin, hair, beard, brows, lips, eyes) keeps its paint. A paint cluster landing
mostly on the photo's body (`body_zone`: its skin pieces, the head, the hands) has no garment (`bodily`), and a
garment whose paint clusters differ past a photo garment's limits is split before its move (`split`: the hollow head's
dark back seen through a face is never moved with its skin by one median).

Run: `python -m tools.characters.generated.colour <model.glb> <cut-out photo.png> <out.glb> <report.json>` (under
a minute, under 2 GB).
"""
import argparse
import io
import json
import pathlib

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage
from scipy.cluster.vq import kmeans2
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import squareform
from scipy.spatial import cKDTree
from skimage.color import lab2rgb, rgb2lab

from tools.characters.generated import labels
from tools.props import glb_file

PAINT_CLUSTERS = 16
PHOTO_CLUSTERS = 12
HEIGHT_LAB = 60.0  # the model's whole height counts as this many Lab units in the paint's clusters
GRID_PIXELS = 600  # the front view's height in pixels
SPREAD_RANGE = (0.67, 1.5)
SOFT_LAB = 1.5  # a texel's share in each cluster falls as exp(-(d^2 - d_min^2) / (2 SOFT_LAB^2))
MIN_PIXELS = 150
LANDED_SHARE = 0.2
PAINT_SAME = 6.0  # Lab units: paint clusters this alike, sent to photo garments of one colour, are one garment
PIECE_PIXELS = 30  # a photo garment's connected piece smaller than this is a speck, no garment
GARMENT_AB = 8.0  # photo clusters whose centres lie this close in a and b ...
GARMENT_L = 30.0  # ... and this close in lightness are one garment
SAMPLES = 60000  # front pixels each clustering is fitted on
ALPHA_CUT = 127
BAND_ROWS = 128  # texture rows toned at once
FACE_LEAST = 0.005  # the face is the highest photo skin piece with at least this share of the person's pixels
HAND_SHARE = 0.4  # a skin piece under the head is a hand when no larger than this share of the head's largest
BODY_SHARE = 0.5  # a paint cluster with this share of its front pixels on the photo's body is the body's: kept
SEEN_DEPTH = 0.004  # share of the model's height a point may lie behind its front cell's front-most and be seen
SEEN_FACING = 0.25  # ... and its surface must face the front this squarely (|normal z|; the sheet is wound either way)


def parts_of(document, views):
    """The model's textured primitives, each its own: (points, per-vertex UV with v up from the picture's bottom,
    base colour image index). Read off the file's own primitives, never through trimesh's `force="mesh"`, which packs
    a swapped head's and body's pictures into one atlas with its own UVs (round 2, 2026-11-26: that atlas, written
    over the body's picture, scrambled the whole paint)."""
    if any(key in node for node in document["nodes"] for key in ("matrix", "translation", "rotation", "scale")):
        raise ValueError("a node with its own transform is not handled")
    parts = []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            material = document["materials"][primitive["material"]] if "material" in primitive else {}
            base = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
            if base is None:
                continue
            attributes = primitive["attributes"]
            points = glb_file.accessor_array(document, views, attributes["POSITION"]).astype(float)
            uv = glb_file.accessor_array(document, views, attributes[f"TEXCOORD_{base.get('texCoord', 0)}"])
            uv = np.column_stack([uv[:, 0], 1.0 - uv[:, 1]]).astype(float)
            parts.append((points, uv, document["textures"][base["index"]]["source"]))
    return parts


def faces_of(document, views):
    """Each textured primitive's triangles (rows of its own point indices), in `parts_of`'s order."""
    faces = []
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            material = document["materials"][primitive["material"]] if "material" in primitive else {}
            if material.get("pbrMetallicRoughness", {}).get("baseColorTexture") is None:
                continue
            if "indices" in primitive:
                faces.append(glb_file.accessor_array(document, views, primitive["indices"]).astype(np.int64)
                             .reshape(-1, 3))
            else:
                count = document["accessors"][primitive["attributes"]["POSITION"]]["count"]
                faces.append(np.arange(count - count % 3, dtype=np.int64).reshape(-1, 3))
    return faces


def picture_of(document, views, image):
    """An image of the file as RGBA uint8."""
    return np.asarray(Image.open(io.BytesIO(views[document["images"][image]["bufferView"]])).convert("RGBA"))


def texel_colours(texture, uv):
    """The texture's RGB (0 to 1) at each UV (glTF's v up from the picture's bottom)."""
    height, width = texture.shape[:2]
    cols = np.clip(np.round(uv[:, 0] * (width - 1)).astype(int), 0, width - 1)
    rows = np.clip(np.round((1.0 - uv[:, 1]) * (height - 1)).astype(int), 0, height - 1)
    return texture[rows, cols, :3] / 255.0


def heights_of(points):
    """Each point's height over the model's, 0 at its feet and 1 at its top (glTF: y up)."""
    return (points[:, 1] - points[:, 1].min()) / np.ptp(points[:, 1])


def features(lab, height):
    """The clusters' space: Lab and the height in HEIGHT_LAB units."""
    return np.column_stack([lab, height * HEIGHT_LAB])


def front_cells(points, pixels):
    """Each point's cell in the front view (glTF: y up, looking along -z) over the points' box, `pixels` rows high:
    (rows down, columns, the grid's width)."""
    low, high = points[:, :2].min(0), points[:, :2].max(0)
    step = (high[1] - low[1]) / pixels
    width = int(np.ceil((high[0] - low[0]) / step)) + 1
    cols = np.clip(((points[:, 0] - low[0]) / step).astype(int), 0, width - 1)
    rows = np.clip(((high[1] - points[:, 1]) / step).astype(int), 0, pixels - 1)
    return rows, cols, width


def front_view(points, values, pixels):
    """The points seen from the front (glTF: y up, looking along -z), each grid cell holding the front-most point's
    `values` row; (image rows down, seen mask). The grid spans the points' box, `pixels` rows high."""
    rows, cols, width = front_cells(points, pixels)
    cell = rows * width + cols
    order = np.lexsort((-points[:, 2], cell))  # by cell, the front-most (largest z) first
    first = order[np.r_[True, cell[order][1:] != cell[order][:-1]]]
    image = np.zeros((pixels * width, values.shape[1]))
    seen = np.zeros(pixels * width, bool)
    image[cell[first]], seen[cell[first]] = values[first], True
    return image.reshape(pixels, width, -1), seen.reshape(pixels, width)


def view_box(seen):
    """The rows and columns `seen` covers: (row slice, column slice)."""
    rows, cols = np.nonzero(seen)
    return slice(rows.min(), rows.max() + 1), slice(cols.min(), cols.max() + 1)


def photo_on(photo_rgba, shape):
    """The photo's cut-out person (alpha over ALPHA_CUT) cropped to its box and resampled onto a grid of `shape`
    (nearest); (rgb 0 to 1, person mask)."""
    alpha = photo_rgba[..., 3] > ALPHA_CUT
    rows, cols = np.nonzero(alpha)
    top, bottom, left, right = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    pick_rows = (top + (np.arange(shape[0]) + 0.5) * (bottom - top) / shape[0]).astype(int)
    pick_cols = (left + (np.arange(shape[1]) + 0.5) * (right - left) / shape[1]).astype(int)
    grid = np.ix_(pick_rows, pick_cols)
    return photo_rgba[..., :3][grid] / 255.0, alpha[grid]


def nearest(values, centres):
    """Each row's squared distance to every centre (rows x centres)."""
    return ((values[:, None, :] - centres[None]) ** 2).sum(-1)


def clustered(values, count):
    """k-means (SAMPLES rows fitted, every row labelled): (centres, labels)."""
    rng = np.random.default_rng(7)
    fitted = values[rng.choice(len(values), min(SAMPLES, len(values)), replace=False)]
    centres, _ = kmeans2(fitted, min(count, len(np.unique(fitted, axis=0))), minit="++", seed=7)
    return centres, nearest(values, centres).argmin(1)


def robust(lab):
    """Each Lab channel's median and spread (1.4826 x its median absolute deviation, never under 0.5)."""
    median = np.median(lab, 0)
    return median, np.maximum(1.4826 * np.median(np.abs(lab - median), 0), 0.5)


def landed(photo_labels):
    """Which of the photo pixels a garment lands on are its own: those of the photo garments taking at least
    LANDED_SHARE of them (the largest one when none does)."""
    counts = np.bincount(photo_labels)
    return np.isin(photo_labels, np.flatnonzero(counts >= min(LANDED_SHARE * len(photo_labels), counts.max())))


def photo_garments(centres):
    """Each photo cluster's garment: complete linkage, so every two clusters of a garment lie within GARMENT_AB in a
    and b and GARMENT_L in lightness (a chain of near greys never joins a white shirt to a grey jacket)."""
    if len(centres) < 2:
        return np.zeros(len(centres), int)
    chroma = np.linalg.norm(centres[:, None, 1:] - centres[None, :, 1:], axis=-1) / GARMENT_AB
    lightness = np.abs(centres[:, None, 0] - centres[None, :, 0]) / GARMENT_L
    apart = np.maximum(chroma, lightness)
    np.fill_diagonal(apart, 0.0)
    return fcluster(linkage(squareform(apart, checks=False), "complete"), 1.0, "distance") - 1


def photo_regions(colour_garment, person):
    """The photo's garments as places: each colour garment's connected pieces (8-connected) of at least PIECE_PIXELS
    pixels numbered, -1 elsewhere (so brown boots and a coat's brown shade, apart on the body, are not one)."""
    regions = np.full(person.shape, -1)
    count = 0
    for garment in np.unique(colour_garment[person]):
        pieces, found = ndimage.label((colour_garment == garment) & person, structure=np.ones((3, 3)))
        sizes = np.bincount(pieces.ravel(), minlength=found + 1)
        for piece in np.flatnonzero(sizes[1:] >= PIECE_PIXELS) + 1:
            regions[pieces == piece] = count
            count += 1
    return regions


def skin_pieces(regions, photo_lab):
    """The photo's skin: its garment pieces (`photo_regions`) whose median colour is a skin's (`labels.skin_like`);
    {piece: its pixels' mask}."""
    pieces = {}
    for piece in np.unique(regions[regions >= 0]):
        mask = regions == piece
        if labels.skin_like(np.median(photo_lab[mask], 0)[None])[0]:
            pieces[piece] = mask
    return pieces


def body_zone(regions, photo_lab):
    """Where the photo shows the person's own body, never a garment. The face is the skin piece (`skin_pieces`) of at
    least FACE_LEAST of the person's pixels lying highest (by its middle row); the head's skin is every skin piece
    reaching over the face's middle row, and the head's bottom their lowest row (the chin, or the neck's shaded
    side). The body is the head's skin, every piece of any colour whose middle row lies over the head's bottom (the
    hair, a beard, brows, lips and eyes) down to that row (grey hair and a white scarf can be one colour piece), and
    the hands: skin pieces under the head of at most HAND_SHARE of the head's
    largest skin piece, clear of the picture's bottom row (a skin-hued coat is larger, and a bust's cut runs through
    its clothes). A hood or a hat over the head lies in it too and keeps its paint."""
    pieces = skin_pieces(regions, photo_lab)
    zone = np.zeros(regions.shape, bool)
    least = FACE_LEAST * (regions >= 0).sum()
    faces = {piece: np.nonzero(mask)[0] for piece, mask in pieces.items() if mask.sum() >= least}
    if not faces:
        return zone
    middle = min(rows.mean() for rows in faces.values())
    head = [piece for piece, mask in pieces.items() if np.nonzero(mask)[0].min() <= middle]
    bottom = max(np.nonzero(pieces[piece])[0].max() for piece in head)
    hand_most = HAND_SHARE * max(int(pieces[piece].sum()) for piece in head)
    for piece in np.unique(regions[regions >= 0]):
        mask = regions == piece
        hand = piece in pieces and mask.sum() <= hand_most and not mask[-1].any()
        if piece in head or hand:
            zone |= mask
        elif np.nonzero(mask)[0].mean() <= bottom:
            zone[:bottom + 1] |= mask[:bottom + 1]
    return zone


def bodily(paint_labels, on_body, count):
    """Which paint clusters are the person's body (skin, hair, beard, brows, lips, eyes): at least BODY_SHARE of their
    front pixels land on the photo's body (`body_zone`). The skin step repaints the face from the photo and the hair
    is regrown, so the body is never toned (round 1, 2026-11-26: a bearded man's skin, hair and beard joined into one
    garment and moved to his photo's skin, the ears and neck cream)."""
    return np.array([on_body[paint_labels == cluster].mean() >= BODY_SHARE if (paint_labels == cluster).any()
                     else False for cluster in range(count)])


def garments(paint_labels, photo_labels, count):
    """Each paint cluster's garment: the photo garment most of its front pixels land on; -1 (its paint kept) when it
    has fewer than MIN_PIXELS front pixels or most land on specks (`photo_regions`' -1)."""
    chosen = np.full(count, -1)
    for cluster in range(count):
        members = paint_labels == cluster
        if members.sum() >= MIN_PIXELS:
            chosen[cluster] = np.bincount(photo_labels[members] + 1).argmax() - 1
    return chosen


def photo_target(members, photo_lab, photo_labels):
    """The photo's Lab where `members` land, off its own garments (`landed`; specks left out): (median, spread)."""
    members = members & (photo_labels >= 0)
    return robust(photo_lab[members][landed(photo_labels[members])])


def alike(first, second):
    """Whether two Lab colours are of one colour garment: within GARMENT_AB in a and b and GARMENT_L in lightness."""
    return np.linalg.norm(first[1:] - second[1:]) < GARMENT_AB and abs(first[0] - second[0]) < GARMENT_L


def merged(chosen, centres, paint_labels, photo_lab, photo_labels):
    """`chosen` with paint clusters joined into one garment when their paint is alike (within PAINT_SAME, height
    aside) and the photo where they land is of one colour: a coat painted one colour whose photo is lit above and
    shaded below gets one move, not a band at the shade's edge; boots painted as black as the trousers but landing
    on brown stay apart."""
    used = np.flatnonzero(chosen >= 0)
    targets = {garment: photo_target(np.isin(paint_labels, np.flatnonzero(chosen == garment)), photo_lab,
                                     photo_labels)[0] for garment in np.unique(chosen[used])}
    joined = np.zeros((len(chosen), len(chosen)), bool)
    for first in used:
        for second in used:
            joined[first, second] = (np.linalg.norm(centres[first, :3] - centres[second, :3]) < PAINT_SAME
                                     and alike(targets[chosen[first]], targets[chosen[second]]))
    joined |= chosen[:, None] == chosen[None, :]
    components = connected_components(joined, directed=False)[1]
    return np.where(chosen >= 0, split(components, centres), -1)


def split(components, centres):
    """Each garment split into groups whose paint is of one colour (`photo_garments`' complete linkage on the paint
    clusters' Lab): clusters landing on one photo garment whose paint differs past GARMENT_AB or GARMENT_L (a skin
    painted light beside paint seen dark through the hollow head) are never moved by one median."""
    out = np.zeros_like(components)
    count = 0
    for garment in np.unique(components):
        members = np.flatnonzero(components == garment)
        groups = photo_garments(centres[members, :3])
        out[members] = groups + count
        count += groups.max() + 1
    return out


def moves(paint_lab, paint_labels, photo_lab, photo_labels, chosen):
    """Per paint cluster, its garment's (from median, spread ratio, to median), one move for all the garment's
    clusters, so the shading the paint drew across it is kept; None for a cluster with no garment."""
    table = []
    for garment in chosen:
        if garment < 0:
            table.append(None)
            continue
        members = np.isin(paint_labels, np.flatnonzero(chosen == garment))
        paint_median, paint_spread = robust(paint_lab[members])
        photo_median, photo_spread = photo_target(members, photo_lab, photo_labels)
        table.append((paint_median, np.clip(photo_spread / paint_spread, *SPREAD_RANGE), photo_median))
    return table


def photo_places(regions, zone):
    """The photo's places: each garment piece (`photo_regions`) split into its part inside the body zone and its part
    outside (grey hair and a white scarf can be one colour piece); -1 off them."""
    return np.where(regions >= 0, 2 * regions + zone, -1)


def place_clusters(pixel_places, paint_labels, chosen, count):
    """Per place (rows up to the largest place), the paint clusters a texel on it may take: those of the garments'
    moves (`chosen`) landing on at least LANDED_SHARE of its front pixels (the largest when none does). A place says
    nothing (no row) when the kept body (-1: every cluster with no move) is among them or it has fewer than MIN_PIXELS
    front pixels: a place only ever gives a texel a garment's move, never takes one away (taken away, the stairwell
    woman's puffer cuffs on the photo's hands and its collar top under the photo's hair kept their dark grey)."""
    allowed = np.zeros((max(int(pixel_places.max()) + 1, 1), count), bool)
    groups = chosen[paint_labels]
    for place in np.unique(pixel_places[pixel_places >= 0]):
        members = groups[pixel_places == place]
        if len(members) < MIN_PIXELS:
            continue
        found, counts = np.unique(members, return_counts=True)
        worn = found[counts >= min(LANDED_SHARE * len(members), counts.max())]
        if -1 not in worn:
            allowed[place] = np.isin(chosen, worn)
    return allowed


def seen_places(points, normals, frame, place_grid):
    """Each point's place (`photo_places` on the front view's cropped grid) when the front sees it (within
    SEEN_DEPTH of the model's height behind its cell's front-most point, its surface facing the front by SEEN_FACING:
    the top of a puffer's collar behind the shoulders, seen edge on over them, landed on the photo's hair hanging
    there and kept its grey), else -1. `frame` is the front view's (pixels, row slice, column slice)."""
    pixels, rows, cols = frame
    row, col, width = front_cells(points, pixels)
    cell = row * width + col
    front = np.full(cell.max() + 1, -np.inf)
    np.maximum.at(front, cell, points[:, 2])
    facing = np.abs(normals[:, 2]) >= SEEN_FACING
    seen = facing & (points[:, 2] >= front[cell] - SEEN_DEPTH * np.ptp(points[:, 1]))
    row, col = row - rows.start, col - cols.start
    inside = seen & (row >= 0) & (row < place_grid.shape[0]) & (col >= 0) & (col < place_grid.shape[1])
    places = np.full(len(points), -1)
    places[inside] = place_grid[row[inside], col[inside]]
    return places


def seen_allowed(points, normals, frame, place_grid, allowed):
    """The clusters each point may take (points x clusters): a point the front sees on a place with clusters
    (`seen_places`, `place_clusters`) its place's, every cluster elsewhere. A point the front does not see is clustered
    by colour and height alone (2026-11-28, tried: reached along the surface from the seen points, the stairwell
    woman's puffer collar under her hair took the hair's place and kept its grey, the older woman's coat by her hands
    the hands')."""
    places = seen_places(points, normals, frame, place_grid)
    known = (places >= 0) & allowed[np.maximum(places, 0)].any(1)
    return np.where(known[:, None], allowed[np.maximum(places, 0)], True)


def toned_lab(lab, height, centres, table, allowed=None):
    """Each Lab colour moved by every cluster's move, weighted by its soft share in that cluster; only among the
    clusters it is `allowed` (colours x clusters, `seen_allowed`) when its colour is like one of them (`alike`:
    within GARMENT_AB in a and b and GARMENT_L in lightness), else among all (the front is laid on the photo by the
    boxes, so a neck can land on a turtleneck)."""
    distance = nearest(features(lab, height), centres)
    if allowed is not None:
        chroma = np.linalg.norm(lab[:, None, 1:] - centres[None, :, 1:3], axis=-1)
        like = (chroma < GARMENT_AB) & (np.abs(lab[:, None, 0] - centres[None, :, 0]) < GARMENT_L)
        fits = (allowed & like).any(1)
        distance = np.where(allowed | ~fits[:, None], distance, np.inf)
    weight = np.exp(-(distance - distance.min(1, keepdims=True)) / (2.0 * SOFT_LAB ** 2))
    weight /= weight.sum(1, keepdims=True)
    out = np.zeros_like(lab)
    for cluster, move in enumerate(table):
        start, ratio, end = move if move is not None else (np.zeros(3), np.ones(3), np.zeros(3))
        out += weight[:, cluster:cluster + 1] * ((lab - start) * ratio + end)
    return out


def toned_texture(texture, heights, uv, centres, table, allowed=None):
    """The texture's RGB toned in Lab, its alpha kept; toned BAND_ROWS rows at a time to keep memory small. `heights`
    are the UV points' heights over the whole model (`heights_of` of all its parts), `allowed` the clusters each UV
    point may take (`seen_allowed`; None: every cluster everywhere)."""
    out = texture.copy()
    tree_heights = heights
    tree = cKDTree(uv)
    height, width = texture.shape[:2]
    for top in range(0, height, BAND_ROWS):
        band = texture[top:top + BAND_ROWS, :, :3] / 255.0
        grid_v, grid_u = np.mgrid[top:top + band.shape[0], 0:width]
        queries = np.column_stack([grid_u.ravel() / (width - 1), 1.0 - grid_v.ravel() / (height - 1)])
        found = tree.query(queries)[1]
        lab = rgb2lab(band).reshape(-1, 3)
        own = None if allowed is None else allowed[found]
        rgb = lab2rgb(toned_lab(lab, tree_heights[found], centres, table, own).reshape(band.shape))
        out[top:top + band.shape[0], :, :3] = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    return out


def fitted(points, colours, photo_rgba):
    """The colour fit from the model's points and their paint (RGB 0 to 1): (paint cluster centres, per-cluster moves,
    report rows, places: the front view's frame, its photo places and each place's clusters, for `seen_allowed`)."""
    values = np.column_stack([colours, heights_of(points)])
    view, seen = front_view(points, values, GRID_PIXELS)
    rows, cols = view_box(seen)
    view, seen = view[rows, cols], seen[rows, cols]
    photo, person = photo_on(photo_rgba, seen.shape)
    both = seen & person
    paint_lab, photo_lab = rgb2lab(view[both][:, :3]), rgb2lab(photo[both])
    centres, paint_labels = clustered(features(paint_lab, view[both][:, 3]), PAINT_CLUSTERS)
    photo_centres, photo_clusters = clustered(rgb2lab(photo[person]), PHOTO_CLUSTERS)
    colour_garment = np.full(person.shape, -1)
    colour_garment[person] = photo_garments(photo_centres)[photo_clusters]
    regions = photo_regions(colour_garment, person)
    photo_labels = regions[both]
    photo_grid = np.zeros(person.shape + (3,))
    photo_grid[person] = rgb2lab(photo[person])
    zone = body_zone(regions, photo_grid) & person
    body = bodily(paint_labels, zone[both], len(centres))
    chosen = np.where(body, -1, garments(paint_labels, photo_labels, len(centres)))
    chosen = merged(chosen, centres, paint_labels, photo_lab, photo_labels)
    table = moves(paint_lab, paint_labels, photo_lab, photo_labels, chosen)
    report = [{"cluster": cluster, "garment": int(chosen[cluster]), "body": bool(body[cluster]),
               "height": round(float(centres[cluster, 3] / HEIGHT_LAB), 3),
               "pixels": int((paint_labels == cluster).sum()),
               "paint_srgb": srgb255(move[0]) if move is not None else srgb255(centres[cluster, :3]),
               "photo_srgb": srgb255(move[2]) if move is not None else None}
              for cluster, move in enumerate(table)]
    place_grid = photo_places(regions, zone)
    clusters = place_clusters(place_grid[both], paint_labels, chosen, len(centres))
    places = ((GRID_PIXELS, rows, cols), place_grid, clusters)
    return centres, table, report, places


def srgb255(lab):
    """A Lab colour as sRGB 0 to 255."""
    return (np.clip(lab2rgb(np.asarray(lab, float)[None, None])[0, 0], 0, 1) * 255).round().astype(int).tolist()


def written(document, views, pictures, out):
    """The glb again with each toned image (index: RGBA picture) replaced, as PNG at its own size; every other byte's
    meaning kept."""
    for image, texture in pictures.items():
        buffer = io.BytesIO()
        Image.fromarray(texture).save(buffer, format="PNG")
        views[document["images"][image]["bufferView"]] = buffer.getvalue()
        document["images"][image]["mimeType"] = "image/png"
    glb_file.write(document, views, out)


def toned_pictures(textures, parts, centres, table, allowed):
    """Each base colour image (index: RGBA picture) toned through its own primitives' UVs, the points' heights and
    clusters (`allowed`, `seen_allowed`) taken over the whole model."""
    heights = heights_of(np.vstack([part[0] for part in parts]))
    starts = np.cumsum([0] + [len(part[0]) for part in parts])
    pictures = {}
    for image, texture in textures.items():
        members = [index for index, part in enumerate(parts) if part[2] == image]
        uv = np.vstack([parts[index][1] for index in members])
        own_heights = np.concatenate([heights[starts[index]:starts[index + 1]] for index in members])
        own_allowed = np.vstack([allowed[starts[index]:starts[index + 1]] for index in members])
        pictures[image] = toned_texture(texture, own_heights, uv, centres, table, own_allowed)
    return pictures


def toned(model, photo_path, out, report_path):
    """The model's paint toned toward its photo, written to `out`; the fit written to `report_path`. The fit reads
    every textured primitive together (a swapped head beside its body); each image is written back in place."""
    document, views = glb_file.read(model)
    parts = parts_of(document, views)
    textures = {image: picture_of(document, views, image) for image in sorted({part[2] for part in parts})}
    points = np.vstack([part[0] for part in parts])
    colours = np.vstack([texel_colours(textures[image], uv) for _, uv, image in parts])
    photo = np.asarray(Image.open(photo_path).convert("RGBA"))
    centres, table, report, (frame, place_grid, clusters) = fitted(points, colours, photo)
    starts = np.cumsum([0] + [len(part[0]) for part in parts])
    faces = np.vstack([own + start for own, start in zip(faces_of(document, views), starts)])
    normals = trimesh.Trimesh(points, faces, process=False).vertex_normals
    allowed = seen_allowed(points, normals, frame, place_grid, clusters)
    written(document, views, toned_pictures(textures, parts, centres, table, allowed), out)
    pathlib.Path(report_path).write_text(json.dumps({"model": str(model), "photo": str(photo_path),
                                                     "clusters": report}, indent=1))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("model", type=pathlib.Path)
    parser.add_argument("photo", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("report", type=pathlib.Path)
    options = parser.parse_args()
    for row in toned(options.model, options.photo, options.out, options.report):
        print(row, flush=True)
    print(f"COLOUR DONE {options.out}", flush=True)


if __name__ == "__main__":
    main()
