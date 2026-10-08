"""Paint a generated (chunky) piece by its parts: which library material each face of the model is (job paint,
2026-10-08: "shouldn't the painting be done by parts? that's why we did the part segmentation", the owner).

    ~/.farm-factory-props/env/bin/python tools/props/library/labels.py <take> <out folder> --place hub \
        [--parts <folder of part_XX.glb>] [--kind hub_chair] [--without lamp_lens,screen]

The part is the painting unit. A part splitter's parts (`--parts`: PartCrafter via cloud/parts.py, made from the same
clean picture) are laid onto Pixal3D's raw model (register.py) and every face of the model is given exactly one part:
the part nearest it (a vote of its PART_VOTES nearest part points within PART_REACH; the splitter's specks left out),
then smoothed over the model's own surface, the vote flowing freely over smooth surface and hardly across a crease; a
smooth region of the model one part clearly holds is that part's whole (by_regions), so part edges settle on the
model's creases; an island of a part under PART_CRUMB of the model's area joins the part round it. Pixal3D's file is
welded first (its blocks' seams repeat every vertex). Without a splitter the whole model is one part (a sack, a
drift, a quilt).

Every part is ONE library material, from the kind's allowed materials (`data/library/details.json` `materials`, else
the place's) by the part's colour in the clean picture: the median of its lit seen faces (the lighter LIT_SHARE of
them, so shade never picks a darker material). No face ever leaves its part's material: per-face colour votes split
one painted desk into four materials by light and shade, and a split by chroma left the greenhouse chair's seat in
blue and black blotches (2026-10-07/08). A detail smaller than a part (a label, a screw) is a decal or a part of its
own, never a patch of paint. A part the camera hardly saw takes the material of the part it borders most.

How well the parts registered is measured and written down (`registration`: the median gap against the model's size,
the share of the model a part clearly holds, how much of it lies near any part); a split that does not register is
reported and the model painted as one part, never in blotches. The result is checked by patchy.py (written into labels.json as `patchy`) and moved onto the
finished model (raw to upright, register.py), cut to the finished model's box (the raw model's floaters go) and
written as one .ply per material (what the bake paints from), plus parts/part_XX.ply, one per part (a door, a lid, a
wheel: the moving pieces come from the same split), and labels.json; a sample of it is stored in the repository
(stored_parts.py, data/parts/<take>.npz).
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
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import glb_file  # noqa: E402
import library  # noqa: E402
import patchy  # noqa: E402
import register  # noqa: E402
import stored_parts  # noqa: E402
from paths import REPO, WORK  # noqa: E402

PIXAL = WORK / "pixal"
DETAILS = REPO / "data/library/details.json"
DEPTH_SLACK = 0.01
SAMPLED = 20000
# Part points a part gets at least, however small its area (the rest are shared out by area).
PART_FLOOR = 300
# Library materials a part of an object is never: the floor's deck paint.
NOT_ON_OBJECTS = ("deck",)
# Lightness, then the two colour axes: hue and chroma count more than lightness (the three-piece test).
WEIGHTS = np.array([0.5, 1.5, 1.5])
# A face takes the part most of its PART_VOTES nearest part points belong to (nearer points weigh more).
PART_VOTES = 8
# Smoothing: SMOOTH_ROUNDS rounds of each face taking its neighbours' weighted majority, a neighbour across a fold of
# CREASE_DEGREES weighing exp(-1) as much as one on flat surface.
SMOOTH_ROUNDS = 12
CREASE_DEGREES = 25.0
# Smooth regions: faces joined across folds under REGION_DEGREES; a region of at least REGION_LEAST of the model's
# area is one part's (the welded raw chair: 12 regions over 1% held 93% of its area at 15 degrees).
REGION_DEGREES = 15.0
REGION_LEAST = 0.002
REGION_CLEAR = 0.7
# A splitter part holding at least this share of an unclear smooth region is merged with the others holding it.
MERGE_SHARE = 0.2
# An island of one part (its faces joined across shared edges) under this share of the model's area joins its
# neighbours' part: patchy.py's stray island, so a part never leaves a blotch (a separate piece keeps its own).
PART_CRUMB = patchy.STRAY_ISLAND
# A material's lightness as a clean studio picture shows it (anchors_of).
PHOTO_FLOOR = 25.0
PHOTO_SPAN = 0.6
# A part's colour: the median of the lighter LIT_SHARE of its seen faces; under SEEN_LEAST seen faces it borrows.
LIT_SHARE = 0.3
SEEN_LEAST = 30
# A splitter's part keeps its pieces of at least PART_PIECE_LEAST of its area; a part under PART_LEAST of the whole goes.
PART_PIECE_LEAST = 0.1
PART_LEAST = 0.005
# A part point votes for a face only within PART_REACH of the model's diagonal.
PART_REACH = 0.03
# Registration: a split is registered when its median gap is within GAP_LIMIT of the model's diagonal and at least
# CLEAR_LEAST of the model's area lies in smooth regions one part clearly holds (by_regions). Two generators never
# make the same shape (the median gap ran 0.7 to 2.5% of the diagonal on splits that read right), so how much of the
# model lies near a part (`covered`, within COVER_REACH) is reported, not judged; a split that does not register
# paints the model as one part. Set on the first 17 splits (job paint, 2026-10-08): the monitor's, the one that
# read wrong, held 9% clear; the rest 87 to 98%.
GAP_LIMIT = 0.03
CLEAR_LEAST = 0.6
COVER_REACH = 0.02
BODY_LEAST = 0.005
# The registration's fit starts from this many of the best quarter turns (register.aligned).
REGISTER_TRIES = 6
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


def welded(mesh):
    """The raw model with its vertices joined where they coincide, its faces in their order: Pixal3D's file repeats
    every vertex along its blocks' seams, so unwelded the chair was 21,000 separate pieces and nothing could spread
    over its surface."""
    rounded = np.round(mesh.vertices, patchy.WELD_DIGITS)
    _, first, inverse = np.unique(rounded, axis=0, return_index=True, return_inverse=True)
    return trimesh.Trimesh(mesh.vertices[first], inverse.reshape(-1)[mesh.faces], process=False)


def part_points(folder):
    """A splitter's part_XX.glb files as surface points, shared out by area (at least PART_FLOOR a part), and the part
    each point belongs to. A part's crumbs (its pieces under PART_PIECE_LEAST of its area) and parts under
    PART_LEAST of the whole are left out: PartCrafter scatters specks round a model, and a speck is the nearest part
    to the faces its model left out (the sample store's sides went to specks floating over its top)."""
    parts = [trimesh.load(path, force="mesh", skip_materials=True) for path in sorted(folder.glob("part_*.glb"))]
    if not parts:
        raise SystemExit(f"{folder}: no part_XX.glb")
    parts = [without_specks(part) for part in parts]
    total = sum(part.area for part in parts)
    parts = [part for part in parts if part.area >= PART_LEAST * total]
    areas = np.array([part.area for part in parts])
    counts = np.maximum(PART_FLOOR, (SAMPLED * areas / areas.sum()).astype(int))
    points = np.vstack([part.sample(count, seed=number) for number, (part, count) in enumerate(zip(parts, counts))])
    return points, np.repeat(np.arange(len(parts)), counts)


def without_specks(part):
    """A splitter's part without its pieces under PART_PIECE_LEAST of its area (a part is a few hundred thousand faces
    at most, so it may be split here)."""
    pieces = part.split(only_watertight=False)
    if len(pieces) <= 1:
        return part
    kept = [piece for piece in pieces if piece.area >= PART_PIECE_LEAST * part.area]
    return trimesh.util.concatenate(kept) if kept else part


def registration(mesh, moved, gap):
    """How well the moved part points lie on the model: the median gap and the covered share of the model's surface
    (its pieces of at least BODY_LEAST of its area: a raw model carries thousands of crumbs), against its diagonal,
    and whether the split is usable."""
    diagonal = float(np.linalg.norm(mesh.bounds[1] - mesh.bounds[0]))
    body = patchy.components(len(mesh.faces), mesh.face_adjacency)
    main = (np.bincount(body, weights=mesh.area_faces) >= BODY_LEAST * mesh.area)[body]
    reach, _ = cKDTree(moved).query(mesh.triangles_center[main])
    covered = float(mesh.area_faces[main][reach < COVER_REACH * diagonal].sum() / mesh.area_faces[main].sum())
    gap_share = gap / diagonal
    return {"gap_share": round(gap_share, 4), "covered": round(covered, 3),
            "registered": bool(gap_share <= GAP_LIMIT)}


def neighbour_matrix(mesh):
    """The faces' edge neighbours as a sparse matrix, each pair weighed by how flat the fold between them is."""
    pairs = mesh.face_adjacency
    weight = np.exp(-np.degrees(mesh.face_adjacency_angles) / CREASE_DEGREES)
    count = len(mesh.faces)
    return sparse.coo_matrix((np.r_[weight, weight], (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                             shape=(count, count)).tocsr()


def nearest_parts(mesh, moved, owner, count):
    """Each face's part by a distance-weighted vote of its PART_VOTES nearest part points, as per-part scores."""
    distance, index = cKDTree(moved).query(mesh.triangles_center, k=PART_VOTES)
    reach = PART_REACH * np.linalg.norm(mesh.bounds[1] - mesh.bounds[0])
    # A face no part point comes near gets no vote: its part spreads to it from its surface's explained faces.
    weight = np.where(distance < reach, 1.0 / np.maximum(distance, 1e-6), 0.0)
    scores = np.zeros((len(mesh.faces), count))
    for column in range(PART_VOTES):
        np.add.at(scores, (np.arange(len(mesh.faces)), owner[index[:, column]]), weight[:, column])
    return scores / np.maximum(scores.sum(1, keepdims=True), 1e-12)


def smoothed_parts(scores, neighbours):
    """The part scores spread over the surface (SMOOTH_ROUNDS), mostly within smooth regions, then each face's best."""
    current = scores
    for _ in range(SMOOTH_ROUNDS):
        spread = neighbours @ current
        current = 0.5 * scores + spread / np.maximum(spread.sum(1, keepdims=True), 1e-12)
    return current.argmax(1)


def smooth_regions(mesh):
    """Each face's smooth region: faces joined across folds under REGION_DEGREES."""
    pairs = mesh.face_adjacency
    return patchy.components(len(mesh.faces), pairs[np.degrees(mesh.face_adjacency_angles) < REGION_DEGREES])


def by_regions(mesh, scores, smoothed):
    """The model's smooth regions (faces joined across folds under REGION_DEGREES) of at least REGION_LEAST of its
    area each take, whole, the part their faces' scores favour most by area; the rest keep the smoothed vote. A part
    splitter's model is not the Pixal3D model, so its part edges land near, not on, the model's own; a smooth region
    of the model is one surface of one part (a seat's top, a door's face). A region whose favourite part holds under
    REGION_CLEAR of its votes runs over a part edge the model rounds off (the hab lander's whole hull was one region)
    and keeps the smoothed vote too."""
    region = smooth_regions(mesh)
    area = np.bincount(region, weights=mesh.area_faces)
    totals = np.zeros((len(area), scores.shape[1]))
    np.add.at(totals, region, scores * mesh.area_faces[:, None])
    clear = totals.max(1) >= REGION_CLEAR * totals.sum(1)
    large = ((area >= REGION_LEAST * mesh.area) & clear)[region]
    return np.where(large, totals.argmax(1)[region], smoothed), float(area[clear].sum() / mesh.area)


def without_crumbs(mesh, part_of):
    """Every island of a part under PART_CRUMB of the model's area taken into the part it borders most."""
    pairs = mesh.face_adjacency
    for _ in range(3):
        island = patchy.islands(part_of, pairs)
        island_area = np.bincount(island, weights=mesh.area_faces)
        small = island_area < PART_CRUMB * mesh.area
        if not small[island].any():
            break
        across = (island[pairs[:, 0]] != island[pairs[:, 1]])
        votes = {}
        for this, that in ((pairs[across, 0], pairs[across, 1]), (pairs[across, 1], pairs[across, 0])):
            lone = small[island[this]]
            for crumb, part in zip(island[this[lone]], part_of[that[lone]]):
                votes.setdefault(crumb, {}).setdefault(part, 0)
                votes[crumb][part] += 1
        moved = np.array([max(votes[crumb], key=votes[crumb].get) if crumb in votes else -1
                          for crumb in range(len(island_area))])
        change = small[island] & (moved[island] >= 0)
        part_of = np.where(change, moved[island], part_of)
    return part_of


def split_on_model(folder, mesh, finished, to_finished):
    """A splitter's part points laid on the raw model: fitted two ways onto the finished model (`finished`, its
    points), which stands upright as the splitter's model does, then carried back to the raw model by the inverse of
    `to_finished`. The raw model leans by the picture's elevation, so no quarter turn starts near it, and a one-way
    fit there shrank a desk's split to 0.6 of its size (job repaint, 2026-10-08). (points, owner, gap on the raw)."""
    points, owner = part_points(folder)
    matrix, _ = register.aligned(points, finished, tries=REGISTER_TRIES, two_way=True)
    matrix = np.linalg.inv(to_finished) @ matrix
    moved = points @ matrix[:3, :3].T + matrix[:3, 3]
    gap = float(np.median(cKDTree(mesh.sample(SAMPLED, seed=0)).query(moved)[0]))
    return moved, owner, gap


def merged_parts(mesh, scores):
    """Each splitter part's group: parts that share a smooth region of the model no part clearly holds (each holding
    at least MERGE_SHARE of its votes) are one group. A splitter asked for eight parts cuts one smooth surface into
    several (an access cover's flat face into five); that surface is one part of the model."""
    region = smooth_regions(mesh)
    area = np.bincount(region, weights=mesh.area_faces)
    totals = np.zeros((len(area), scores.shape[1]))
    np.add.at(totals, region, scores * mesh.area_faces[:, None])
    shares = totals / np.maximum(totals.sum(1, keepdims=True), 1e-12)
    unclear = (area >= REGION_LEAST * mesh.area) & (shares.max(1) < REGION_CLEAR)
    held = shares[unclear] >= MERGE_SHARE
    links = sparse.csr_matrix(held.T.astype(float) @ held.astype(float)) + sparse.eye(scores.shape[1])
    return connected_components(links, directed=False)[1]


def part_faces(mesh, moved, owner):
    """Every face's part from part points laid on the model, and the share of the model parts clearly hold."""
    count = int(owner.max()) + 1
    scores = nearest_parts(mesh, moved, owner, count)
    part_of, clear = by_regions(mesh, scores, smoothed_parts(scores, neighbour_matrix(mesh)))
    part_of = without_crumbs(mesh, part_of)
    _, part_of = np.unique(part_of, return_inverse=True)  # parts that won no face are gone
    return part_of.reshape(-1), clear, scores


def parts_on_model(folder, mesh, finished, to_finished):
    """Every face's part from a splitter's parts laid onto the model, and the registration report. A split whose parts
    do not clearly hold CLEAR_LEAST of the model is tried again with the parts that share its unclear surfaces merged
    (merged_parts) before it is reported as not registered."""
    moved, owner, gap = split_on_model(folder, mesh, finished, to_finished)
    part_of, clear, scores = part_faces(mesh, moved, owner)
    report = dict(registration(mesh, moved, gap), splitter_parts=int(owner.max()) + 1, clear=round(clear, 3))
    if clear < CLEAR_LEAST:
        group = merged_parts(mesh, scores)
        part_of, clear, _ = part_faces(mesh, moved, group[owner])
        report.update(merged_to=int(group.max()) + 1, clear=round(clear, 3))
    report["registered"] = bool(report["registered"] and clear >= CLEAR_LEAST)
    return part_of, report


def anchors_of(materials):
    """The materials' names and their colours as a clean studio picture shows them: the token's Lab colour with its
    lightness drawn into the picture's range (PHOTO_FLOOR + PHOTO_SPAN * L*): studio light lifts black rubber to a
    dark grey and keeps a white hull under paper white."""
    names = list(materials)
    anchors = lab(np.array([srgb(np.array(materials[name]["colour"])) for name in names]))
    anchors[:, 0] = PHOTO_FLOOR + PHOTO_SPAN * anchors[:, 0]
    return names, anchors


def weighted(colours, anchor):
    """Distance in Lab with hue and chroma weighed over lightness (WEIGHTS)."""
    return np.sqrt((((colours - anchor) ** 2) * WEIGHTS).sum(-1))


def part_colour(colours):
    """A part's colour from its seen faces' colours: the median of the lighter LIT_SHARE of them (shade only darkens)."""
    lightness = colours[:, 0]
    lit = colours[lightness >= np.quantile(lightness, 1 - LIT_SHARE)]
    return np.median(lit, axis=0)


def borders(mesh, part_of, count):
    """How many shared edges each pair of parts has."""
    pairs = mesh.face_adjacency
    first, second = part_of[pairs[:, 0]], part_of[pairs[:, 1]]
    across = first != second
    found = np.zeros((count, count))
    np.add.at(found, (first[across], second[across]), 1)
    return found + found.T


def paint_parts(mesh, colours, part_of, materials):
    """One library material per part: the allowed material nearest the part's colour (part_colour); a part with
    under SEEN_LEAST seen faces takes the material of the seen part it borders most. Per part its material's index,
    seen faces and colour; the material names."""
    names, anchors = anchors_of(materials)
    seen = ~np.isnan(colours[:, 0])
    count = int(part_of.max()) + 1
    chosen = np.full(count, -1)
    about = []
    for part in range(count):
        members = (part_of == part) & seen
        colour = part_colour(colours[members]) if members.sum() >= SEEN_LEAST else None
        if colour is not None:
            chosen[part] = int(np.argmin([weighted(colour, anchor) for anchor in anchors]))
        about.append({"seen_faces": int(members.sum()),
                      "colour": None if colour is None else [round(float(value), 1) for value in colour]})
    if (chosen < 0).all():  # the camera saw no part well: the whole model's colour for all
        chosen[:] = int(np.argmin([weighted(part_colour(colours[seen]), anchor) for anchor in anchors]))
    shared = borders(mesh, part_of, count)
    for part in np.nonzero(chosen < 0)[0]:
        known = np.nonzero(chosen >= 0)[0]
        chosen[part] = chosen[known[np.argmax(shared[part, known])]]
        about[part]["borrowed"] = True
    for part in range(count):
        about[part]["material"] = names[chosen[part]]
    return chosen, about, names


def allowed_materials(place, kind, without):
    """The materials a piece may take: its kind's own list (details.json `materials`) or the place's, less those an
    object never is and those named in `without`."""
    every = library.resolved(place)
    own = json.loads(DETAILS.read_text()).get(kind, {}).get("materials") if kind else None
    if own:
        missing = [name for name in own if name not in every]
        if missing:
            raise SystemExit(f"{kind}: details.json names materials {place} does not have: {', '.join(missing)}")
        return {name: every[name] for name in own}
    left_out = NOT_ON_OBJECTS + tuple(without)
    return {name: spec for name, spec in every.items() if name not in left_out}


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


def write_parts(mesh, labels, order, part_of, final_bounds, out):
    """The model (already on its finished model) cut to that box: one .ply per material and parts/part_XX.ply per
    part; the material shares and the faces kept."""
    middles = mesh.triangles_center
    inside = np.all((middles >= final_bounds[0] - 0.02) & (middles <= final_bounds[1] + 0.02), axis=1)
    shares = {}
    for index, name in enumerate(order):
        chosen = inside & (labels == index)
        if not chosen.any():
            continue
        mesh.submesh([np.nonzero(chosen)[0]], append=True).export(out / f"{name}.ply")
        shares[name] = round(float(mesh.area_faces[chosen].sum() / mesh.area_faces[inside].sum()), 3)
    (out / "parts").mkdir(exist_ok=True)
    for part in np.unique(part_of[inside]):
        mesh.submesh([np.nonzero(inside & (part_of == part))[0]], append=True).export(out / "parts" / f"part_{part:02d}.ply")
    return shares, inside


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("take")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--place", default="hub")
    parser.add_argument("--parts", type=pathlib.Path)
    parser.add_argument("--kind", help="the kind (its details.json `materials` are the ones allowed)")
    parser.add_argument("--without", default="", help="library materials this piece has none of, by comma (a "
                        "locker's paper notes read as a lamp lens, 2026-10-07)")
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)
    for old in list(arguments.out.glob("*.ply")) + list(arguments.out.glob("parts/*.ply")):
        old.unlink()  # a material or part the new labels no longer have must not reach the bake
    materials = allowed_materials(arguments.place, arguments.kind,
                                  [name for name in arguments.without.split(",") if name])
    np.random.seed(0)  # with the samples' own seeds (trimesh draws from its own generator, not numpy's global
    # one): the same take labels the same way every run; unseeded, the torn ship's aft section registered on one
    # run and not the next (2026-10-08)
    mesh = welded(trimesh.load(PIXAL / f"{arguments.take}.glb", force="mesh", process=False))
    colours = face_colours(mesh, arguments.take)
    report = {"take": arguments.take, "kind": arguments.kind, "allowed": list(materials),
              "seen_share": round(float((~np.isnan(colours[:, 0])).mean()), 3)}
    final = trimesh.load(PIXAL / f"{arguments.take}-final.glb", force="mesh")
    matrix, gap = onto_finished(mesh.sample(SAMPLED, seed=1), final.sample(SAMPLED, seed=2),
                                finish_turn(arguments.take))
    if arguments.parts:
        part_of, report["registration"] = parts_on_model(arguments.parts, mesh, final.sample(SAMPLED, seed=3), matrix)
        report.update(way="parts", parts_folder=str(arguments.parts))
        if not report["registration"]["registered"]:  # reported, and painted whole rather than in blotches
            part_of = np.zeros(len(mesh.faces), dtype=int)
            report["way"] = "whole: its split did not register"
    else:
        part_of = np.zeros(len(mesh.faces), dtype=int)
        report.update(way="whole")
    chosen, about, names = paint_parts(mesh, colours, part_of, materials)
    order = sorted({names[index] for index in chosen})
    labels = np.array([order.index(names[index]) for index in chosen])[part_of]
    report["upright_gap"] = round(gap, 4)
    mesh.apply_transform(matrix)
    report["shares"], inside = write_parts(mesh, labels, order, part_of, final.bounds, arguments.out)
    report["faces_kept"] = int(inside.sum())
    areas = mesh.area_faces
    for part, entry in enumerate(about):
        entry["share"] = round(float(areas[inside & (part_of == part)].sum() / areas[inside].sum()), 3)
    report["parts"] = about
    kept, kept_labels, _, kept_parts = patchy.labelled_parts(arguments.out)
    report["patchy"] = patchy.score(kept, kept_labels, kept_parts)
    (arguments.out / "labels.json").write_text(json.dumps(report, indent=1))
    stored_parts.write(arguments.out, arguments.take)
    print(json.dumps({key: report[key] for key in ("take", "way", "shares", "patchy") + (
        ("registration",) if "registration" in report else ())}))


if __name__ == "__main__":
    main()
