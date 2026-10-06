"""Part labels for a generated (chunky) piece: which library material each face of the model is (job robust-exp,
2026-10-06; the robust route: the model gives shape only, the picture only votes which library material a part is,
and its colours are never baked in).

    ~/.farm-factory-props/env/bin/python tools/props/library/labels.py <take> <out folder> --place hub \
        [--parts <folder of part_XX.glb>]

Pixal3D's raw model is pixel-aligned with the picture it was made from (WORK/pixal/<take>.svviews: the cut-out
picture and its camera), so each face seen from that camera takes the picture's colour where it lands (a depth test
keeps hidden faces out). The picture's colours are grouped (k-means in Lab) and each group goes to the nearest of the
place's library materials by its token colour, hue and chroma weighed over lightness, as the three-piece test did.

Two ways to turn those votes into parts:
    picture (default)  each face keeps its own vote; unseen faces take their nearest seen face's; a few rounds of
                       majority vote over neighbouring faces remove speckle
    --parts            a part splitter's parts (PartCrafter, cloud/parts.py) are laid onto the model (register.py) and
                       each face joins its nearest part; a whole part takes the area-weighted majority of its seen
                       faces' votes, so grime across a body cannot split it

The model is then moved onto its finished model (register.py, raw to upright), cut to the finished model's box (the
raw model's floaters go) and written as one .ply per material, with labels.json (shares, seen share, groups, parts).
No model runs here: numpy and the picture.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy import sparse
from scipy.ndimage import median_filter
from scipy.spatial import cKDTree
from sklearn.cluster import KMeans

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import library  # noqa: E402
import register  # noqa: E402
from paths import WORK  # noqa: E402

PIXAL = WORK / "pixal"
GROUPS = 6
DEPTH_SLACK = 0.01
VOTES = 3
SAMPLED = 20000
# Library materials a part of an object is never: the floor's deck paint.
NOT_ON_OBJECTS = ("deck",)
# Lightness, then the two colour axes: hue and chroma count more than lightness (the three-piece test).
WEIGHTS = np.array([0.5, 1.5, 1.5])


def lab(rgb):
    """sRGB (0..1) to CIE Lab."""
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.9505, 1.0, 1.089])
    bent = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * bent[..., 1] - 16, 500 * (bent[..., 0] - bent[..., 1]), 200 * (bent[..., 1] - bent[..., 2])],
                    -1)


def srgb(linear):
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)


def picture_groups(rgba):
    """Per pixel of the picture's object: its colour group (-1 off the object), and each group's middle in Lab."""
    alpha = rgba[..., 3] > 0.5
    colours = lab(median_filter(rgba[..., :3], size=(5, 5, 1)))
    fitted = KMeans(n_clusters=GROUPS, n_init=4, random_state=0).fit(colours[alpha])
    groups = -np.ones(alpha.shape, dtype=int)
    groups[alpha] = fitted.labels_
    return groups, fitted.cluster_centers_


def group_materials(centres, materials):
    """Each colour group's library material: the nearest token colour, hue and chroma weighed over lightness."""
    names = list(materials)
    anchors = lab(np.array([srgb(np.array(materials[name]["colour"])) for name in names]))
    return [names[int(np.argmin((((anchors - centre) ** 2) * WEIGHTS).sum(-1)))] for centre in centres]


def seen_faces(mesh, camera, shape):
    """Which faces the picture's camera sees, and the pixel each lands on (a depth test on face middles)."""
    height, width = shape
    middles = mesh.triangles_center
    focal = 1 / np.tan(camera["camera_angle_x"] / 2)
    distance = -camera["frames"][0]["transform_matrix"][1][3]
    depth = distance - middles[:, 2]
    column = np.clip(((0.5 + 0.5 * middles[:, 0] * focal / depth) * width).astype(int), 0, width - 1)
    row = np.clip(((0.5 - 0.5 * middles[:, 1] * focal / depth) * height).astype(int), 0, height - 1)
    pixel = row * width + column
    nearest = np.full(height * width, np.inf)
    np.minimum.at(nearest, pixel, depth)
    facing = (mesh.face_normals @ np.array([0.0, 0.0, 1.0])) > 0.05
    return (depth <= nearest[pixel] + DEPTH_SLACK) & facing, row, column


def picture_votes(mesh, take, materials):
    """Each seen face's material index (-1 unseen), the material names in index order and the colour groups' names."""
    views = PIXAL / f"{take}.svviews"
    rgba = np.asarray(Image.open(views / "input.png").convert("RGBA"), dtype=np.float64) / 255
    groups, centres = picture_groups(rgba)
    names = group_materials(centres, materials)
    seen, row, column = seen_faces(mesh, json.loads((views / "transforms.json").read_text()), groups.shape)
    seen &= groups[row, column] >= 0
    order = sorted(set(names))
    by_group = np.array([order.index(name) for name in names])
    votes = -np.ones(len(mesh.faces), dtype=int)
    votes[seen] = by_group[groups[row[seen], column[seen]]]
    return votes, order, names


def smoothed(labels, mesh):
    """A few rounds of majority vote over each face's neighbours, so lone faces take their surroundings' material."""
    pairs = mesh.face_adjacency
    count = len(labels)
    neighbours = sparse.coo_matrix((np.ones(len(pairs) * 2), (np.r_[pairs[:, 0], pairs[:, 1]],
                                                               np.r_[pairs[:, 1], pairs[:, 0]])),
                                   shape=(count, count)).tocsr()
    kinds = labels.max() + 1
    for _ in range(VOTES):
        votes = neighbours @ np.eye(kinds)[labels] + np.eye(kinds)[labels]
        labels = votes.argmax(1)
    return labels


def by_face(mesh, votes):
    """The picture way: seen faces keep their vote, unseen ones take the nearest seen face's, then smoothing."""
    seen = votes >= 0
    middles = mesh.triangles_center
    labels = votes.copy()
    _, nearest = cKDTree(middles[seen]).query(middles[~seen])
    labels[~seen] = votes[seen][nearest]
    return smoothed(labels, mesh)


def splitter_parts(folder, mesh):
    """Each face's part from a splitter's part_XX.glb files laid onto the model; the gap left by the fit."""
    parts = [trimesh.load(path, force="mesh", skip_materials=True) for path in sorted(folder.glob("part_*.glb"))]
    points = np.vstack([part.sample(SAMPLED // len(parts)) for part in parts])
    owner = np.repeat(np.arange(len(parts)), SAMPLED // len(parts))
    matrix, gap = register.aligned(points, mesh.sample(SAMPLED))
    moved = points @ matrix[:3, :3].T + matrix[:3, 3]
    _, nearest = cKDTree(moved).query(mesh.triangles_center)
    return owner[nearest], len(parts), gap


def by_part(mesh, votes, part_of):
    """The splitter way: every face of a part takes the area-weighted majority of the part's seen votes."""
    labels = np.zeros(len(mesh.faces), dtype=int)
    areas = mesh.area_faces
    for part in np.unique(part_of):
        members = part_of == part
        seen = members & (votes >= 0)
        if seen.any():
            labels[members] = np.bincount(votes[seen], weights=areas[seen]).argmax()
        else:
            labels[members] = np.bincount(votes[votes >= 0], weights=areas[votes >= 0]).argmax()
    return labels


def write_parts(mesh, labels, order, matrix, final_bounds, out):
    """The model moved onto its finished model, cut to that box, one .ply per material; the face shares."""
    mesh.apply_transform(matrix)
    middles = mesh.triangles_center
    inside = np.all((middles >= final_bounds[0] - 0.02) & (middles <= final_bounds[1] + 0.02), axis=1)
    shares = {}
    for index, name in enumerate(order):
        chosen = inside & (labels == index)
        if not chosen.any():
            continue
        mesh.submesh([np.nonzero(chosen)[0]], append=True).export(out / f"{name}.ply")
        shares[name] = round(float(mesh.area_faces[chosen].sum() / mesh.area_faces[inside].sum()), 3)
    return shares, int(inside.sum())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("take")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--place", default="hub")
    parser.add_argument("--parts", type=pathlib.Path)
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)
    materials = {name: spec for name, spec in library.resolved(arguments.place).items() if name not in NOT_ON_OBJECTS}
    mesh = trimesh.load(PIXAL / f"{arguments.take}.glb", force="mesh", process=False)
    votes, order, names = picture_votes(mesh, arguments.take, materials)
    report = {"take": arguments.take, "seen_share": round(float((votes >= 0).mean()), 3), "groups": names}
    if arguments.parts:
        part_of, count, gap = splitter_parts(arguments.parts, mesh)
        labels = by_part(mesh, votes, part_of)
        report.update(way="parts", parts=count, parts_gap=round(gap, 4))
    else:
        labels = by_face(mesh, votes)
        report.update(way="picture")
    final = trimesh.load(PIXAL / f"{arguments.take}-final.glb", force="mesh")
    matrix, gap = register.aligned(mesh.sample(SAMPLED), final.sample(SAMPLED))
    report["upright_gap"] = round(gap, 4)
    report["shares"], report["faces_kept"] = write_parts(mesh, labels, order, matrix, final.bounds, arguments.out)
    (arguments.out / "labels.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
