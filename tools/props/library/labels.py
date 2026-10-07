"""Part labels for a generated (chunky) piece: which library material each face of the model is (job robust-exp,
2026-10-06; the robust route: the model gives shape only, the picture only votes which library material a part is,
and its colours never replace the library's: since round four they come back only as a detail layer over it).

    ~/.farm-factory-props/env/bin/python tools/props/library/labels.py <take> <out folder> --place hub \
        [--parts <folder of part_XX.glb>] [--without lamp_lens,screen]

Pixal3D's raw model is pixel-aligned with the picture it was made from (WORK/pixal/<take>.svviews: the cut-out
picture and its camera), so each face seen from that camera takes the picture's colour where it lands (a depth test
keeps hidden faces out). The model is taken as parts: a part splitter's (`--parts`, PartCrafter via cloud/parts.py,
laid onto the model by register.py) or, without one, the whole model as one part. A part takes the place's library
material nearest its median seen colour, hue and chroma weighed over lightness; a seen face whose colour is plainly
another material's (a steel tool on a wooden board) takes that one (by_part). Per-face votes are gone: they split one
painted desk into four materials by light and shade, which baked as dark blotches (2026-10-07).

The model is then moved onto its finished model (register.py, raw to upright), cut to the finished model's box (the
raw model's floaters go) and written as one .ply per material, with labels.json (shares, seen share, groups, parts).
Beside them the finished model itself is written as picture.obj with its texture: the picture's own pixels, which the
bake lays over the library surfaces as their detail (labels, notes, rust, the tools' own colours), its faces split
into those the picture's camera saw and those it did not.
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

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import glb_file  # noqa: E402
import library  # noqa: E402
import register  # noqa: E402
from paths import WORK  # noqa: E402

PIXAL = WORK / "pixal"
DEPTH_SLACK = 0.01
VOTES = 3
SAMPLED = 20000
# Library materials a part of an object is never: the floor's deck paint.
NOT_ON_OBJECTS = ("deck",)
# Lightness, then the two colour axes: hue and chroma count more than lightness (the three-piece test).
WEIGHTS = np.array([0.5, 1.5, 1.5])
# A seen face leaves its part's material for another when the other is nearer than SPLIT_MARGIN of the part's own and
# the face differs from the part's median in chromaticity (a* and b* over L*) by SPLIT_CHROMATICITY (a steel tool on a
# wooden board), or is lighter by SPLIT_LIGHTER (a pale desk top inside a dark part). Shade only darkens and scales a*
# and b* down with L*, so it splits neither way: split by lightness or plain chroma, the desk's shaded knee-hole and
# the tools' shadows on the board came out as dark material, baked as black patches (2026-10-07).
SPLIT_CHROMATICITY = 0.2
SPLIT_LIGHTER = 30.0
# Chromaticity is read only on faces at least this light: in deep shade a* and b* are noise over a small L*.
SPLIT_LIT = 30.0
SPLIT_MARGIN = 0.7
UNSEEN_NEIGHBOURS = 50
# A finished model's face counts as seen by the picture's camera when a seen raw face lies within this.
SEEN_REACH = 0.01
# How far a turned finished model's box may miss its final model's and still be the finish's turn (metres).
FINISH_MISS = 0.01


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


def splitter_parts(folder, mesh):
    """Each face's part from a splitter's part_XX.glb files laid onto the model; the gap left by the fit."""
    parts = [trimesh.load(path, force="mesh", skip_materials=True) for path in sorted(folder.glob("part_*.glb"))]
    points = np.vstack([part.sample(SAMPLED // len(parts)) for part in parts])
    owner = np.repeat(np.arange(len(parts)), SAMPLED // len(parts))
    matrix, gap = register.aligned(points, mesh.sample(SAMPLED))
    moved = points @ matrix[:3, :3].T + matrix[:3, 3]
    _, nearest = cKDTree(moved).query(mesh.triangles_center)
    return owner[nearest], len(parts), gap


def face_colours(mesh, take):
    """Each seen face's colour in the picture, in Lab (NaN where the camera does not see it)."""
    views = PIXAL / f"{take}.svviews"
    rgba = np.asarray(Image.open(views / "input.png").convert("RGBA"), dtype=np.float64) / 255
    colours = lab(median_filter(rgba[..., :3], size=(5, 5, 1)))
    seen, row, column = seen_faces(mesh, json.loads((views / "transforms.json").read_text()), rgba.shape[:2])
    seen &= rgba[row, column, 3] > 0.5
    found = np.full((len(mesh.faces), 3), np.nan)
    found[seen] = colours[row[seen], column[seen]]
    return found


def weighted(colours, anchor):
    """Distance in Lab with hue and chroma weighed over lightness (WEIGHTS)."""
    return np.sqrt((((colours - anchor) ** 2) * WEIGHTS).sum(-1))


def chromaticity(colours):
    """Lab colours' a* and b* over L*: what shade leaves alone."""
    return colours[..., 1:] / np.maximum(colours[..., :1], 1.0)


def never_darker(chosen, colours, seen, anchors):
    """No seen face keeps a material darker than itself by more than SPLIT_LIGHTER: studio light does not make dark
    paint read pale, so such a face took its material from a part it does not belong to (a PartCrafter part reaching
    over the comms desk's top, 2026-10-07). It takes the nearest material no darker than that."""
    faces = np.nonzero(seen)[0]
    lightness = colours[faces, 0]
    wrong = lightness - anchors[chosen[faces], 0] > SPLIT_LIGHTER
    for face, colour in zip(faces[wrong], colours[faces[wrong]]):
        allowed = anchors[:, 0] >= colour[0] - SPLIT_LIGHTER
        distances = np.where(allowed, weighted(colour, anchors), np.inf)
        if np.isfinite(distances).any():
            chosen[face] = int(np.argmin(distances))
    return chosen


def by_part(mesh, colours, part_of, materials):
    """Every face of a part takes the library material nearest the part's median picture colour (a majority of
    per-face votes let shaded faces outvote lit ones: the comms desk came out 98% dark pipe steel, 2026-10-07), except
    a seen face whose colour is plainly another material's (SPLIT_CHROMATICITY, SPLIT_LIGHTER, SPLIT_MARGIN): the steel tools on a wooden
    board. A face the camera does not see takes the most common material of its UNSEEN_NEIGHBOURS nearest seen faces:
    a part splitter's parts only roughly fit the model (a tool's part reached round the toolboard's back), and a single
    nearest face carried a shaded edge's dark over a wall panel's whole unseen body (2026-10-07). A few rounds of neighbour majority
    then clear speckle. The labels and the material names in index order."""
    names = list(materials)
    anchors = lab(np.array([srgb(np.array(materials[name]["colour"])) for name in names]))
    seen_anywhere = ~np.isnan(colours[:, 0])
    whole = np.median(colours[seen_anywhere], axis=0)
    chosen = np.zeros(len(part_of), dtype=int)
    for part in np.unique(part_of):
        members = part_of == part
        seen = members & seen_anywhere
        middle = np.median(colours[seen], axis=0) if seen.sum() >= 20 else whole
        own = int(np.argmin([weighted(middle, anchor) for anchor in anchors]))
        chosen[members] = own
        distances = np.stack([weighted(colours[seen], anchor) for anchor in anchors], -1)
        nearest = distances.argmin(-1)
        coloured = (np.linalg.norm(chromaticity(colours[seen]) - chromaticity(middle), axis=-1) > SPLIT_CHROMATICITY) & \
            (colours[seen][:, 0] > SPLIT_LIT)
        apart = coloured | (colours[seen][:, 0] - middle[0] > SPLIT_LIGHTER)
        other = apart & (distances[np.arange(len(nearest)), nearest] < SPLIT_MARGIN * distances[:, own])
        chosen[np.nonzero(seen)[0][other]] = nearest[other]
    chosen = never_darker(chosen, colours, seen_anywhere, anchors)
    middles = mesh.triangles_center
    _, closest = cKDTree(middles[seen_anywhere]).query(middles[~seen_anywhere], k=UNSEEN_NEIGHBOURS)
    neighbours = chosen[seen_anywhere][closest]
    chosen[~seen_anywhere] = np.array([np.bincount(row).argmax() for row in neighbours])
    chosen = smoothed(chosen, mesh)
    order = sorted({names[index] for index in np.unique(chosen)})
    return np.array([order.index(names[index]) for index in chosen]), order


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


def finish_turn(take):
    """The turn pixal.py's finish gave the take (stand_and_pad: glb_file.upright_turn, then glb_file.level_turn, on the
    finished model's own positions, in the raw model's frame), replayed exactly: of the take's finished files and the
    finish's options, the one whose turned box matches the final model's. A fit by registration instead turned the comms
    desk's parts 6 cm off and, on a near-symmetric piece, landed end for end at random (2026-10-07)."""
    final = trimesh.load(PIXAL / f"{take}-final.glb", force="mesh")
    best = None
    for path in sorted(PIXAL.glob(f"{take}-[0-9]*.glb")):
        for long, feet in ((False, False), (True, False), (False, True), (True, True)):
            document, views = glb_file.read(path)
            points = glb_file.positions(document, views)
            turn = glb_file.upright_turn(points, long=long, feet=feet)
            glb_file.turned(document, views, turn)
            whole = glb_file.level_turn(*glb_file.faces(document, views)) @ turn
            moved = points @ whole.T
            miss = float(np.abs(np.array([moved.min(0), moved.max(0)]) - final.bounds).max())
            if best is None or miss < best[1]:
                best = (whole, miss)
    if best is None or best[1] > FINISH_MISS:
        raise SystemExit(f"{take}: no finish turn matches its final model "
                         f"({'no finished file' if best is None else f'missed by {best[1]:.4f} m'})")
    return best[0]


def onto_finished(points, target, turn):
    """The raw model's points laid onto its finished model: the finish's own turn (finish_turn), refined by
    register.aligned without quarter turns. The 4 x 4 matrix and the median gap in metres."""
    start = np.eye(4)
    start[:3, :3] = turn
    refined, gap = register.aligned(points @ turn.T, target, turns=False)
    return refined @ start, gap


def write_picture(final, out, seen_points):
    """The finished model with the picture's own pixels on it (Pixal3D's Pixel Match), in the parts' frame, as
    picture.obj with its texture beside it: the bake lays its labels, notes, rust and colours over the library
    surfaces (round four, 2026-10-07: dropping the picture took the room's detail with it). Its faces come in two
    materials, `seen` and `unseen` by the picture's camera (`seen_points`, the seen raw faces' middles on the finished
    model): where the camera never looked, Pixal3D guessed, and its guesses drew comb-like streaks down the locker's
    side, so the bake lays no detail there. The texture's size and the seen share."""
    material = getattr(final.visual, "material", None)
    image = getattr(material, "baseColorTexture", None) or getattr(material, "image", None)
    if image is None:
        raise SystemExit("the finished model carries no picture to lay over the library (a Pixal3D take before "
                         "Pixel Match?)")
    reach, _ = cKDTree(seen_points).query(final.triangles_center)
    seen = reach < SEEN_REACH
    halves = []
    for name, faces in (("seen", seen), ("unseen", ~seen)):
        if faces.any():
            half = final.submesh([np.nonzero(faces)[0]], append=True)
            half.visual.material = trimesh.visual.material.SimpleMaterial(name=name, image=image)
            halves.append(half)
    trimesh.Scene(halves).export(out / "picture.obj")
    return list(image.size), round(float(final.area_faces[seen].sum() / final.area), 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("take")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--place", default="hub")
    parser.add_argument("--parts", type=pathlib.Path)
    parser.add_argument("--without", default="", help="library materials this piece has none of, by comma (a "
                        "locker's paper notes read as a lamp lens, 2026-10-07)")
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)
    left_out = NOT_ON_OBJECTS + tuple(name for name in arguments.without.split(",") if name)
    materials = {name: spec for name, spec in library.resolved(arguments.place).items() if name not in left_out}
    np.random.seed(0)  # the samples registration reads: the same take labels the same way every run
    mesh = trimesh.load(PIXAL / f"{arguments.take}.glb", force="mesh", process=False)
    colours = face_colours(mesh, arguments.take)
    report = {"take": arguments.take, "seen_share": round(float((~np.isnan(colours[:, 0])).mean()), 3)}
    if arguments.parts:
        part_of, count, gap = splitter_parts(arguments.parts, mesh)
        report.update(way="parts", parts=count, parts_gap=round(gap, 4))
    else:
        part_of = np.zeros(len(mesh.faces), dtype=int)
        report.update(way="whole")
    labels, order = by_part(mesh, colours, part_of, materials)
    final = trimesh.load(PIXAL / f"{arguments.take}-final.glb", force="mesh")
    matrix, gap = onto_finished(mesh.sample(SAMPLED), final.sample(SAMPLED), finish_turn(arguments.take))
    report["upright_gap"] = round(gap, 4)
    middles = mesh.triangles_center @ matrix[:3, :3].T + matrix[:3, 3]
    seen_points = middles[~np.isnan(colours[:, 0])]
    report["shares"], report["faces_kept"] = write_parts(mesh, labels, order, matrix, final.bounds, arguments.out)
    report["picture"], report["picture_seen_share"] = write_picture(final, arguments.out, seen_points)
    (arguments.out / "labels.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
