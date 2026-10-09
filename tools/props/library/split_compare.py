"""Which part splitter gives a generated model the parts its finishes need (job parts-test, 2026-10-09): PartCrafter's
split laid onto the Pixal3D model (labels.py), against splitters run on our own Pixal3D model in the cloud
(../cloud/meshparts.py): SegviGen with no guidance, SegviGen guided by the clean close-up's finish regions painted as
its part-colour map, and GeoSAM2 seeded with the same regions. Painting stays parts plus the surface library; nothing
here keeps a model's picture colours.

    python tools/props/library/split_compare.py inputs <run folder> <take> [<take> ...]
    python tools/props/library/split_compare.py labels <run folder>
    python tools/props/library/split_compare.py scores <run folder>

`inputs` writes, per take, what the cloud runner sends up (<run>/<take>/up/: the raw model, the guide map, GeoSAM2's
copy of the model and the close-up's regions on the full model's faces for its seed); `labels` lays every method's split onto the raw model's faces (<take>/parts_<method>.npy,
one part per welded face); `scores` scores each split three ways against the close-up (scores.json):

- finishes: of the finishes the close-up shows (its SAM 2.1 regions, each with the material the judge named for it,
  labels.json of the repaint; regions with one material are one finish), the share that get parts of their own: at
  least OWN_COVER of the finish's seen area lies in parts at least OWN_PURITY of whose seen area is that finish;
- needless cuts: the share of the model's area on a smooth surface (labels.smooth_regions) that lies in a part other
  than the surface's largest one while showing the same finish (or no finish the close-up saw);
- regions: the split rendered flat from the close-up's camera and compared with the close-up's regions pixel by
  pixel: how whole each region stays (the share of it in its main part) and how pure each part is (the share of it
  in its main finish), their harmonic mean.

The split of a method on our model is cleaned as PartCrafter's is when laid: smoothed over the surface
(labels.smoothed_parts), then islands of a part under CRUMB of the model's area join the part they border most
(labels.without_crumbs at a finer size than painting's, so a tape patch survives).
"""
import argparse
import json
import pathlib
import shutil
import sys

import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import labels  # noqa: E402
import regions  # noqa: E402
from paths import WORK  # noqa: E402

LABELS = WORK / "labels"
METHODS = ("partcrafter", "segvigen", "segvigen_guided", "geosam2_guided")
# Guide colours: SegviGen's first part colour (its data_toolkit/assets/full_seg_w_2d_map/colors.json), then each next
# the colour of a 6-step RGB grid farthest from those taken, none darker than DARKEST in every channel (the guide is
# laid on black). Its own palette holds near twins ((127, 246, 192) and (133, 248, 196)) that cannot be told apart.
FIRST_COLOUR = (127, 246, 192)
PALETTE_SIZE = 64
DARKEST = 102
# SegviGen's voxel grid side over the model's longest side.
GRID = 512
# Voxel colours become parts as SegviGen's split.py groups them: quantised to QUANT, colours within MERGE one part, a
# part of fewer than COLOUR_LEAST voxels dropped. Guided or not: given the guide's colours, SegviGen still paints its
# parts in colours of its own (the chair's seventeen guide colours came back as eleven others, 2026-10-09), so a part
# is never matched to a guide colour.
QUANT = 16
COLOUR_LEAST = 500
MERGE = 32.0
# GeoSAM2's first view looks along +X of the model it is given; the close-up's camera looks at the raw model from its
# -Z side (labels.VIEW_TURN), so the model is turned a quarter about up: x' = z, z' = -x.
GEOSAM2_TURN = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
# GeoSAM2 gets the model cut to this many faces: its label completion walks the faces in Python 64 times, and on the
# full million-face chair it had not finished after 9 minutes (2026-10-09). Its labels come back to every face of
# ours by the nearest face; the seed is laid from the full model's faces.
GEOSAM2_FACES = 150_000
CRUMB = 0.002
OWN_COVER = 0.6
OWN_PURITY = 0.7
# A finish under FINISH_LEAST of the seen area is not counted.
FINISH_LEAST = 0.01


def picture(take):
    """The take's clean close-up (RGBA)."""
    return Image.open(labels.PIXAL / f"{take}.svviews" / "input.png").convert("RGBA")


def raw_model(take):
    """The take's raw Pixal3D model, welded as labels.py welds it (its faces in the file's order)."""
    return labels.welded(trimesh.load(labels.PIXAL / f"{take}.glb", force="mesh", process=False))


def pixel_regions(take, masks_folder):
    """Each pixel's finish region of the close-up (regions.region_map over its SAM 2.1 masks), -1 off the object."""
    inside = np.asarray(picture(take))[..., 3] > 127
    return regions.region_map(regions.masks_of(masks_folder / f"{take}.npz"), inside)


def region_finishes(take, count):
    """Each region's finish: the material the repaint painted it with (its labels.json), as an index into the
    take's finish names; and the names."""
    painted = json.loads((LABELS / take / "labels.json").read_text())["regions"]
    if len(painted) != count:
        raise SystemExit(f"{take}: {count} regions here, {len(painted)} in its labels.json")
    names = sorted({entry["material"] for entry in painted})
    return np.array([names.index(entry["material"]) for entry in painted]), names


def face_regions(mesh, take, pixels):
    """Each face's close-up region where the camera sees it, -1 elsewhere."""
    view = labels.picture_view(mesh, take)
    _, seen, row, column = view
    found = np.full(len(mesh.faces), -1)
    found[seen] = pixels[row[seen], column[seen]]
    return found


def guide_map(pixels):
    """The close-up's regions painted in SegviGen's part colours on a clear background (RGBA)."""
    colours = np.array([palette_colour(number) for number in range(int(pixels.max()) + 1)], dtype=np.uint8)
    painted = np.zeros((*pixels.shape, 4), dtype=np.uint8)
    inside = pixels >= 0
    painted[inside, :3] = colours[pixels[inside]]
    painted[inside, 3] = 255
    return Image.fromarray(painted)


def guide_palette(count=PALETTE_SIZE):
    """`count` guide colours, each the grid colour farthest from those before it (FIRST_COLOUR first)."""
    steps = np.arange(0, 256, 51, dtype=float)
    grid = np.stack(np.meshgrid(steps, steps, steps, indexing="ij"), -1).reshape(-1, 3)
    grid = grid[grid.max(1) >= DARKEST]
    chosen = [np.array(FIRST_COLOUR, dtype=float)]
    while len(chosen) < count:
        distance = np.linalg.norm(grid[:, None] - np.array(chosen)[None], axis=2).min(1)
        chosen.append(grid[distance.argmax()])
    return np.array(chosen, dtype=np.uint8)


PALETTE = guide_palette()


def palette_colour(number):
    """The guide colour of region `number`."""
    if number >= len(PALETTE):
        raise SystemExit(f"region {number}: more regions than the {len(PALETTE)} guide colours")
    return tuple(int(channel) for channel in PALETTE[number])


def geosam2_frame(mesh):
    """The raw model's frame for GeoSAM2: its box centred, its longest side 1, turned so its close-up side faces
    GeoSAM2's first view; (centre, scale)."""
    low, high = mesh.bounds
    return (low + high) / 2, 1.0 / float((high - low).max())


def to_geosam2(points, centre, scale):
    return ((points - centre) * scale) @ GEOSAM2_TURN.T


def write_inputs(run, take, masks_folder, seeds_folder=None):
    """The take's uploads (<run>/<take>/up/) and the close-up's regions on its faces (<run>/<take>/view.npz). With
    `seeds_folder` the guide and the seeds are its finish seeds (<take>.npy, one finish per pixel: SAM 3 asked for
    each finish by name, the judge confirming each) instead of SAM 2.1's regions, which cut a close-up by look; the
    regions stay in view.npz for the scores."""
    folder = run / take / "up"
    folder.mkdir(parents=True, exist_ok=True)
    mesh = raw_model(take)
    pixels = pixel_regions(take, masks_folder)
    seeds = np.load(seeds_folder / f"{take}.npy") if seeds_folder else pixels
    on_faces = face_regions(mesh, take, seeds)
    shutil.copyfile(labels.PIXAL / f"{take}.glb", folder / "raw.glb")
    guide_map(seeds).save(folder / "map.png")
    centre, scale = geosam2_frame(mesh)
    turned = trimesh.Trimesh(to_geosam2(mesh.vertices, centre, scale), mesh.faces, process=False)
    turned.simplify_quadric_decimation(face_count=GEOSAM2_FACES).export(folder / "mesh.glb")
    np.savez_compressed(folder / "seed_points.npz", middles=to_geosam2(mesh.triangles_center, centre, scale)
                        .astype(np.float32), regions=(on_faces + 1).astype(np.int32))  # 0: no region seen there
    np.savez_compressed(run / take / "view.npz", pixels=pixels, on_faces=face_regions(mesh, take, pixels),
                        centre=centre, scale=scale)
    return {"take": take, "faces": len(mesh.faces), "regions": int(pixels.max()) + 1,
            "seen_faces": int((on_faces >= 0).sum())}


# Laying each method's split onto the raw model.

def grouped_colours(colours):
    """Colours grouped into parts: quantised, each quantised colour (most common first) joining the first group whose
    colour lies within MERGE, else starting one; groups of fewer than COLOUR_LEAST voxels dropped (the largest always
    kept), every colour then taking its nearest group's."""
    quantised = np.clip(((colours + QUANT / 2) // QUANT) * QUANT, 0, 255)
    unique, counts = np.unique(quantised, axis=0, return_counts=True)
    seeds, totals = [], []
    for index in np.argsort(-counts):
        near = [number for number, seed in enumerate(seeds) if np.linalg.norm(unique[index] - seed) <= MERGE]
        if near:
            totals[near[0]] += counts[index]
        else:
            seeds.append(unique[index])
            totals.append(counts[index])
    kept = [seed for seed, total in zip(seeds, totals) if total >= COLOUR_LEAST] or seeds[:1]
    return cKDTree(np.array(kept)).query(colours)[1]


def voxel_parts_on_faces(mesh, coords, voxel_part, centre, scale):
    """Each face's part from SegviGen's voxels: each vertex takes its nearest voxel's part, each face the part most
    of its vertices have (the paper's own transfer, written here: its repository's exporter remeshes)."""
    middles = (coords.astype(float) + 0.5) / GRID - 0.5
    normalised = (mesh.vertices - centre) * scale
    nearest = cKDTree(middles).query(normalised)[1]
    corner = voxel_part[nearest][mesh.faces]
    agree = corner[:, 1] == corner[:, 2]
    return np.where(agree, corner[:, 1], corner[:, 0])


def face_parts_by_nearest(mesh, centre, scale, their_middles, their_labels):
    """Each face's part from GeoSAM2's per-face labels on its own copy of the model: the label of the nearest of its
    faces (label 0, faces it left unlabelled, is not taken)."""
    labelled = their_labels > 0
    mine = to_geosam2(mesh.triangles_center, centre, scale)
    return their_labels[labelled][cKDTree(their_middles[labelled]).query(mine)[1]]


def cleaned(mesh, part_of):
    """The split smoothed over the model's surface as PartCrafter's is (labels.smoothed_parts: each face's part the
    weighted vote of its neighbours, hardly across a crease), then its crumbs (islands under CRUMB of the area) joined
    to their neighbours, numbered from 0. Unsmoothed, SegviGen's guided split speckled the chair's unseen back."""
    _, part_of = np.unique(np.asarray(part_of), return_inverse=True)
    votes = np.zeros((len(part_of), int(part_of.max()) + 1))
    votes[np.arange(len(part_of)), part_of.reshape(-1)] = 1.0
    part_of = labels.smoothed_parts(votes, labels.neighbour_matrix(mesh))
    saved = labels.PART_CRUMB
    labels.PART_CRUMB = CRUMB
    try:
        part_of = labels.without_crumbs(mesh, part_of)
    finally:
        labels.PART_CRUMB = saved
    return np.unique(part_of, return_inverse=True)[1].reshape(-1)


def partcrafter_parts(mesh, take):
    """PartCrafter's split as the repaint lays it (labels.parts_on_model, parts merged where they share an unclear
    surface), and its registration report."""
    report = json.loads((LABELS / take / "labels.json").read_text())
    np.random.seed(0)
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    matrix, _ = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                     labels.finish_turn(take))
    return labels.parts_on_model(pathlib.Path(report["parts_folder"]), mesh, final.sample(labels.SAMPLED, seed=3),
                                 matrix)


def segvigen_parts(mesh, folder, mode):
    """SegviGen's split (`mode` auto or guided) from its voxels (<take>/down/segvigen_<mode>.npz)."""
    stored = np.load(folder / "down" / f"segvigen_{mode}.npz")
    voxel_part = grouped_colours(stored["colours"].astype(float))
    return voxel_parts_on_faces(mesh, stored["coords"], voxel_part, stored["centre"], stored["scale"])


def geosam2_parts(mesh, folder, view):
    """GeoSAM2's split from its per-face labels (<take>/down/geosam2.npz)."""
    stored = np.load(folder / "down" / "geosam2.npz")
    return face_parts_by_nearest(mesh, view["centre"], view["scale"], stored["middles"], stored["labels"])


def lay_all(run, take):
    """Every method's split of the take on its raw model's faces, written as <take>/parts_<method>.npy."""
    folder = run / take
    mesh = raw_model(take)
    view = dict(np.load(folder / "view.npz"))
    notes = json.loads((folder / "laid.json").read_text()) if (folder / "laid.json").exists() else {}
    if not (folder / "parts_partcrafter.npy").exists():
        part_of, notes["partcrafter"] = partcrafter_parts(mesh, take)
        np.save(folder / "parts_partcrafter.npy", part_of.astype(np.int32))
    for method, make in (("segvigen", lambda: segvigen_parts(mesh, folder, "auto")),
                         ("segvigen_guided", lambda: segvigen_parts(mesh, folder, "guided")),
                         ("geosam2_guided", lambda: geosam2_parts(mesh, folder, view))):
        try:
            np.save(folder / f"parts_{method}.npy", cleaned(mesh, make()).astype(np.int32))
            notes.pop(method, None)
        except FileNotFoundError as missing:
            notes[method] = f"no output: {missing.filename}"
    (folder / "laid.json").write_text(json.dumps(notes, indent=1, default=str))
    return notes


# Scores.

def finishes_owned(areas, finish, part_of):
    """The finishes (seen faces' finish indices, -1 unseen) that get parts of their own, and those that do not; each
    finish under FINISH_LEAST of the seen area is left out."""
    seen = finish >= 0
    total = areas[seen].sum()
    parts = int(part_of.max()) + 1
    count = int(finish.max()) + 1
    table = np.zeros((parts, count))
    np.add.at(table, (part_of[seen], finish[seen]), areas[seen])
    purity = table / np.maximum(table.sum(1, keepdims=True), 1e-12)
    owned, missed = [], []
    for number in range(count):
        size = table[:, number].sum()
        if size < FINISH_LEAST * total:
            continue
        held = table[purity[:, number] >= OWN_PURITY, number].sum()
        (owned if held >= OWN_COVER * size else missed).append(number)
    return owned, missed


def needless_cuts(mesh, finish, part_of):
    """The share of the model's area on smooth surfaces lying outside the surface's largest part while showing the
    same finish as it (or none the close-up saw); and how many smooth surfaces are cut so."""
    areas = mesh.area_faces
    surface = labels.smooth_regions(mesh)
    big = np.bincount(surface, weights=areas) >= labels.REGION_LEAST * areas.sum()
    part_finish = main_finish(areas, finish, part_of)
    wasted, cut = 0.0, 0
    for number in np.nonzero(big)[0]:
        members = surface == number
        pieces = np.bincount(part_of[members], weights=areas[members])
        largest = int(pieces.argmax())
        piece_finish = main_finish(areas[members], finish[members], part_of[members], part_finish)
        needless = [piece for piece in np.nonzero(pieces)[0] if piece != largest
                    and (piece_finish[piece] < 0 or piece_finish[piece] == piece_finish[largest])]
        share = pieces[needless].sum() if needless else 0.0
        wasted += share
        cut += int(share > 0.1 * pieces.sum())
    return float(wasted / areas.sum()), cut


def main_finish(areas, finish, part_of, fallback=None):
    """Each part's finish by most seen area, -1 where none of it was seen (or `fallback`'s where given)."""
    parts = int(part_of.max()) + 1
    found = np.full(parts, -1) if fallback is None else np.array(fallback[:parts]) if len(fallback) >= parts \
        else np.r_[fallback, np.full(parts - len(fallback), -1)]
    seen = finish >= 0
    if not seen.any():
        return found
    table = np.zeros((parts, int(finish.max()) + 1))
    np.add.at(table, (part_of[seen], finish[seen]), areas[seen])
    has = table.sum(1) > 0
    found[has] = table[has].argmax(1)
    return found


def region_agreement(rendered, pixels, region_finish):
    """The split rendered from the close-up's camera (`rendered`, each pixel's part, -1 off the model) against the
    close-up's regions: how whole each region stays, how pure each part is in finish, their harmonic mean."""
    both = (rendered >= 0) & (pixels >= 0)
    part, region = rendered[both], pixels[both]
    table = np.zeros((int(part.max()) + 1, int(region.max()) + 1))
    np.add.at(table, (part, region), 1)
    whole = float(table.max(0).sum() / table.sum())
    finish_table = np.zeros((table.shape[0], int(region_finish.max()) + 1))
    np.add.at(finish_table.T, region_finish, table.T)
    pure = float(finish_table.max(1).sum() / finish_table.sum())
    return {"whole": round(whole, 3), "pure": round(pure, 3), "agreement": round(2 * whole * pure / (whole + pure), 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("inputs", "labels"))
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("takes", nargs="*")
    parser.add_argument("--masks", type=pathlib.Path, help="the folder of segment.py's masks (<take>.npz)")
    parser.add_argument("--seeds", type=pathlib.Path, help="inputs: a folder of finish seed maps (<take>.npy)")
    arguments = parser.parse_args()
    arguments.run.mkdir(parents=True, exist_ok=True)
    if arguments.step == "inputs":
        for take in arguments.takes:
            print(json.dumps(write_inputs(arguments.run, take, arguments.masks, arguments.seeds)), flush=True)
    else:
        for take in arguments.takes or sorted(path.parent.name for path in arguments.run.glob("*/view.npz")):
            print(take, json.dumps(lay_all(arguments.run, take), default=str), flush=True)


if __name__ == "__main__":
    main()
