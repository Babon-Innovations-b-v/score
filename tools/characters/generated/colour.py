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


def model_of(path):
    """The glb's one mesh: (points, per-vertex UV, base colour texture as RGBA uint8)."""
    mesh = trimesh.load(str(path), force="mesh", process=False)
    texture = np.asarray(mesh.visual.material.baseColorTexture.convert("RGBA"))
    return np.asarray(mesh.vertices, float), np.asarray(mesh.visual.uv, float), texture


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


def front_view(points, values, pixels):
    """The points seen from the front (glTF: y up, looking along -z), each grid cell holding the front-most point's
    `values` row; (image rows down, seen mask). The grid spans the points' box, `pixels` rows high."""
    low, high = points[:, :2].min(0), points[:, :2].max(0)
    step = (high[1] - low[1]) / pixels
    width = int(np.ceil((high[0] - low[0]) / step)) + 1
    cols = np.clip(((points[:, 0] - low[0]) / step).astype(int), 0, width - 1)
    rows = np.clip(((high[1] - points[:, 1]) / step).astype(int), 0, pixels - 1)
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
    return np.where(chosen >= 0, components, -1)


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


def toned_lab(lab, height, centres, table):
    """Each Lab colour moved by every cluster's move, weighted by its soft share in that cluster."""
    distance = nearest(features(lab, height), centres)
    weight = np.exp(-(distance - distance.min(1, keepdims=True)) / (2.0 * SOFT_LAB ** 2))
    weight /= weight.sum(1, keepdims=True)
    out = np.zeros_like(lab)
    for cluster, move in enumerate(table):
        start, ratio, end = move if move is not None else (np.zeros(3), np.ones(3), np.zeros(3))
        out += weight[:, cluster:cluster + 1] * ((lab - start) * ratio + end)
    return out


def toned_texture(texture, points, uv, centres, table):
    """The texture's RGB toned in Lab, its alpha kept; toned BAND_ROWS rows at a time to keep memory small."""
    out = texture.copy()
    tree_heights = heights_of(points)
    tree = cKDTree(uv)
    height, width = texture.shape[:2]
    for top in range(0, height, BAND_ROWS):
        band = texture[top:top + BAND_ROWS, :, :3] / 255.0
        grid_v, grid_u = np.mgrid[top:top + band.shape[0], 0:width]
        queries = np.column_stack([grid_u.ravel() / (width - 1), 1.0 - grid_v.ravel() / (height - 1)])
        heights = tree_heights[tree.query(queries)[1]]
        lab = rgb2lab(band).reshape(-1, 3)
        rgb = lab2rgb(toned_lab(lab, heights, centres, table).reshape(band.shape))
        out[top:top + band.shape[0], :, :3] = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    return out


def fitted(points, uv, texture, photo_rgba):
    """The colour fit: (paint cluster centres, per-cluster moves, report rows)."""
    values = np.column_stack([texel_colours(texture, uv), heights_of(points)])
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
    photo_labels = photo_regions(colour_garment, person)[both]
    chosen = merged(garments(paint_labels, photo_labels, len(centres)), centres, paint_labels, photo_lab,
                    photo_labels)
    table = moves(paint_lab, paint_labels, photo_lab, photo_labels, chosen)
    report = [{"cluster": cluster, "garment": int(chosen[cluster]),
               "height": round(float(centres[cluster, 3] / HEIGHT_LAB), 3),
               "pixels": int((paint_labels == cluster).sum()),
               "paint_srgb": srgb255(move[0]) if move is not None else srgb255(centres[cluster, :3]),
               "photo_srgb": srgb255(move[2]) if move is not None else None}
              for cluster, move in enumerate(table)]
    return centres, table, report


def srgb255(lab):
    """A Lab colour as sRGB 0 to 255."""
    return (np.clip(lab2rgb(np.asarray(lab, float)[None, None])[0, 0], 0, 1) * 255).round().astype(int).tolist()


def written(model, texture, out):
    """The glb again with its base colour image replaced by `texture` (PNG); every other byte's meaning kept."""
    document, views = glb_file.read(model)
    material = document["materials"][0]["pbrMetallicRoughness"]
    image = document["images"][document["textures"][material["baseColorTexture"]["index"]]["source"]]
    buffer = io.BytesIO()
    Image.fromarray(texture).save(buffer, format="PNG")
    views[image["bufferView"]] = buffer.getvalue()
    image["mimeType"] = "image/png"
    glb_file.write(document, views, out)


def toned(model, photo_path, out, report_path):
    """The model's paint toned toward its photo, written to `out`; the fit written to `report_path`."""
    points, uv, texture = model_of(model)
    photo = np.asarray(Image.open(photo_path).convert("RGBA"))
    centres, table, report = fitted(points, uv, texture, photo)
    written(model, toned_texture(texture, points, uv, centres, table), out)
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
