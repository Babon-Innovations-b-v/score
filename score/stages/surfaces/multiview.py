"""The g-texture method's split (the surface test of 2026-10-11, round 4's best): our own model split by its finishes
over several views, with its texture, instead of GeoSAM2's geometry seeded on one view (known-problems (c): GeoSAM2
drops colour and is seeded on view 0 only, so smooth surfaces get cut). split_batch.py runs it as stage rows
(cameras, prompts, split).

1. A turntable of the textured raw model (inside/turntable.py on a rented card): the close-up's own camera (view c)
   and VIEWS round it, each with its unlit base colour, metal and roughness and the face under each pixel.
2. SAM 3 per finish (tools/props/cloud/finish_masks.py, each view a picture of its own): the finishes are the surfaces
   the judge named for the unlit close-up's regions; each is asked for by a noun phrase (what the judge called its largest
   region) and an exemplar box, that finish's faces as this view shows them (the close-up's regions carried onto the
   model, so the box follows the finish round the turntable).
3. A vote per face: every view that shows a face votes, by SAM 3's score, for the finishes whose masks cover its
   pixel; where SAM 3 takes several finishes for one class (classes), the face's texture colour, gloss and thickness
   pick among them against each finish's exemplar from its seed region's core, smoothed over the surface
   (within_class, round 3); a face the close-up itself shows keeps its own region's finish. The finishes are spread
   over the surface (labels.smoothed_parts), crumbs join their neighbours, and each connected patch of one finish is
   a part (<work>/multiview/<take>/parts.npy, one part per welded face).
The parts then go to the judge like any split's (paint.py), and neighbours merge only where the judge names one
surface and their unlit colours agree (MERGE_COLOUR).
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PROPS = HERE.parents[2] / "tools/props"  # the prop tool chain this stage reads (labels, the judge, the cloud)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROPS))
sys.path.insert(0, str(PROPS / "library"))

# The turntable: azimuths (degrees, 0 the close-up's side) at a low and a high elevation.
LOW, LOW_TURNS = 15.0, range(0, 360, 30)
HIGH, HIGH_TURNS = 55.0, range(45, 360, 90)
SIDE = 1024
# The camera stands far enough that the model's farthest point from the middle fits with this margin.
FIT_MARGIN = 1.08
# A finish's exemplar box in a view: the largest patch of its seed faces' pixels, kept when it holds BOX_LEAST of the
# object's pixels there (else the finish is asked by its phrase alone).
BOX_LEAST = 0.002
# A face takes a finish when its share of the votes of the views showing it reaches VOTE_LEAST.
VOTE_LEAST = 0.3
# SAM 3 asked by words cannot tell gold foil from silver foil (attributes are its weakest prompt): a finish whose mask
# covers another finish's seed faces at least CLASS_COVER as well as that finish's own mask does is the same class to
# it, and within a class each face takes the finish whose seed faces' texture colour is nearest its own
# (labels.weighted). Its masks covered a finish's own seed faces 19 to 53% of the time on the lander and power unit.
CLASS_COVER = 0.5
# Round 3: within a class, each face's finish is decided by what its texture and shape say, against each finish's
# exemplar taken from its seed region's core, never its border (shading and the neighbour's foil bleed in there: the
# lander's silver seed faces read b* p90 23.7, gold's): CORE_RINGS edge rings in, the middle CORE_LIGHTNESS
# quantiles of its L*, and of two hue groups HUE_APART apart (a*, b*) the larger; under CORE_LEAST coloured core
# faces the whole region is used. The features (FEATURES) are the texture's colour, metalness and roughness and the
# solid's thickness; each finish's exemplar is their median and spread over its core (the spread never under
# SPREAD_FLOOR), and a face scores each finish by how likely its features are under that exemplar (independent
# Gaussians), smoothed over its neighbours. The desk chair's steel reads metal 0.99 and its vinyl 0.07, where the
# colours of chair-b's steel and vinyl overlap; chair-b's base is 4.5 cm through, its seat and back 10 to 11 cm.
CORE_RINGS = 3
CORE_LIGHTNESS = (0.2, 0.8)
HUE_APART = 8.0
CORE_LEAST = 50
HUE_ROUNDS = 10
SPREAD_FLOOR = np.array([2.0, 1.0, 1.0, 0.05, 0.05, 0.1])


def views_of(take, mesh):
    """The close-up's camera (view c) and the turntable's, in the raw model's glTF frame: labels.seen_faces looks at
    the model turned half round (VIEW_TURN) from +z, so the close-up camera stands at -z looking +z."""
    import labels
    camera = json.loads((labels.PIXAL / f"{take}.svviews" / "transforms.json").read_text())
    from PIL import Image
    width, height = Image.open(labels.PIXAL / f"{take}.svviews" / "input.png").size
    distance = -camera["frames"][0]["transform_matrix"][1][3]
    fov = camera["camera_angle_x"]
    reach = float(np.linalg.norm(mesh.vertices, axis=1).max())
    orbit = max(distance, FIT_MARGIN * reach / np.sin(fov / 2))
    found = [{"name": "c", "position": [0.0, 0.0, -distance], "target": [0.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0],
              "fov_x": fov, "width": width, "height": height}]
    for elevation, turns in ((LOW, LOW_TURNS), (HIGH, HIGH_TURNS)):
        for turn in turns:
            azimuth, rise = np.radians(turn), np.radians(elevation)
            direction = [np.sin(azimuth) * np.cos(rise), np.sin(rise), -np.cos(azimuth) * np.cos(rise)]
            found.append({"name": f"t{int(elevation):02d}-{turn:03d}",
                          "position": [float(orbit * value) for value in direction], "target": [0.0, 0.0, 0.0],
                          "up": [0.0, 1.0, 0.0], "fov_x": fov, "width": SIDE, "height": SIDE})
    return found


def cameras(work, takes):
    """<work>/multiview/job.json for inside/turntable.py; the job's path."""
    import labels
    import split_compare
    folder = work / "multiview"
    folder.mkdir(parents=True, exist_ok=True)
    job = {"out": str(folder / "renders"), "takes": [
        {"take": take, "model": str(labels.PIXAL / f"{take}.glb"),
         "views": views_of(take, split_compare.raw_model(take))}
        for take in takes]}
    path = folder / "job.json"
    path.write_text(json.dumps(job, indent=1))
    return path


def renders(work, take):
    return work / "multiview" / "renders" / take


def poly_faces(work, take, mesh):
    """Each Blender polygon's welded face (the nearest face middle), cached as <work>/multiview/<take>/poly_face.npy."""
    from scipy.spatial import cKDTree
    path = work / "multiview" / take / "poly_face.npy"
    if path.exists():
        return np.load(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    middles = np.load(renders(work, take) / "faces.npy")
    distance, found = cKDTree(mesh.triangles_center).query(middles)
    if np.median(distance) > 1e-4:
        raise SystemExit(f"{take}: Blender's polygons lie {np.median(distance):.5f} from the welded faces (median)")
    np.save(path, found.astype(np.int32))
    return found


def face_map(work, take, view, mesh):
    """Each pixel's welded face in a turntable view, -1 off the model."""
    ids = np.load(renders(work, take) / f"{view}-id.npy")
    poly = poly_faces(work, take, mesh)
    return np.where(ids >= 0, poly[np.maximum(ids, 0)], -1)


def view_names(work, take):
    return sorted(path.name[:-len("-id.npy")] for path in renders(work, take).glob("*-id.npy"))


def camera_of(work, take, view):
    """A turntable view's camera as the job gave it to inside/turntable.py."""
    job = json.loads((work / "multiview" / "job.json").read_text())
    entry = next(entry for entry in job["takes"] if entry["take"] == take)
    return next(camera for camera in entry["views"] if camera["name"] == view)


def projected(mesh, camera):
    """Each face middle's pixel (row, column) and depth through a turntable camera (glTF frame, fov across the
    width)."""
    position, target, up = (np.array(camera[key], dtype=float) for key in ("position", "target", "up"))
    forward = (target - position) / np.linalg.norm(target - position)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    offset = mesh.triangles_center - position
    depth = offset @ forward
    scale = 0.5 * camera["width"] / np.tan(camera["fov_x"] / 2)
    column = np.clip((0.5 * camera["width"] + scale * (offset @ right) / depth).astype(int), 0, camera["width"] - 1)
    row = np.clip((0.5 * camera["height"] - scale * (offset @ true_up) / depth).astype(int), 0, camera["height"] - 1)
    return row, column, depth


def seen_in_view(work, take, view, mesh):
    """Which faces a turntable view sees and the pixel each lands on: a face is seen when its middle lies no more than
    labels.DEPTH_SLACK behind the face Blender drew at that pixel (the face map), so faces smaller than a pixel count
    too (one face per pixel centre saw about 40% of each model's area from 17 views)."""
    import labels
    faces = face_map(work, take, view, mesh)
    row, column, depth = projected(mesh, camera_of(work, take, view))
    drawn = faces[row, column]
    front_depth = np.where(drawn >= 0, depth[np.maximum(drawn, 0)], -np.inf)
    seen = (drawn >= 0) & (depth > 0) & (depth <= front_depth + labels.DEPTH_SLACK)
    return seen, row, column


def turntable_view(work, take, view, mesh):
    """A turntable view as labels.picture_view gives a picture's: (picture, seen, row, column) with the face map as a
    fifth item."""
    from PIL import Image
    picture = Image.open(renders(work, take) / f"{view}.png").convert("RGBA")
    seen, row, column = seen_in_view(work, take, view, mesh)
    return picture, seen, row, column, face_map(work, take, view, mesh)


def close_up_overlap(work, take):
    """View c's drawn outline against the close-up's (intersection over union): the turntable's camera check."""
    from PIL import Image
    import labels
    drawn = np.load(renders(work, take) / "c-id.npy") >= 0
    close = np.asarray(Image.open(labels.PIXAL / f"{take}.svviews" / "input.png").convert("RGBA"))[..., 3] > 127
    return float((drawn & close).sum() / (drawn | close).sum())


def finishes_of(work, answers, take, materials):
    """The unlit close-up's finishes: per surface the judge named (else the allowed surface nearest the region's
    colour), its regions, its phrase (what the judge called its largest judged region) and its share of the picture."""
    from PIL import Image
    import labels
    import part_judge
    import regions
    import measure
    asked = measure.region_pixels(work, "unlit", take)
    names = list(materials)
    colours = labels.picture_lab(Image.open(measure.picture_path(work, "unlit", take)).convert("RGBA"))
    asked_answers = part_judge.judged(answers, f"R-unlit~{take}", int(asked.max()) + 1, names)
    # A region holding a coloured and a neutral finish (gold tape on a grey panel, gold and silver foil in one SAM
    # mask) is split in two by the unlit copy's chroma, as labels.py's split route splits the lit one; the half whose
    # colour family is the answered surface's keeps the judge's answer.
    pixels, origin = regions.split_by_colour(asked, colours)
    centres = regions.medians(pixels, colours)
    judged = labels.inherited_answers(asked_answers, origin, centres, labels.anchors_of(materials)[1], names)
    count = int(pixels.max()) + 1
    paint_of, _ = labels.region_materials(centres, regions.vivid(pixels, colours), judged, materials)
    sizes = np.bincount(pixels[pixels >= 0], minlength=count)
    found = {}
    for region in np.argsort(-sizes):
        surface = names[paint_of[region]]
        entry = found.setdefault(surface, {"regions": [], "phrase": None, "share": 0.0})
        entry["regions"].append(int(region))
        entry["share"] += float(sizes[region] / sizes.sum())
        if entry["phrase"] is None and region in judged and judged[region][1].strip():
            entry["phrase"] = judged[region][1].strip()
    for surface, entry in found.items():
        entry["phrase"] = entry["phrase"] or surface.replace("_", " ")
    return pixels, found


def exemplar_box(mask, object_pixels):
    """The box [x0, y0, x1, y1] round the largest patch of `mask`, or None when it is under BOX_LEAST."""
    from scipy import ndimage
    pieces, count = ndimage.label(ndimage.binary_opening(mask, iterations=1))
    if not count:
        return None
    sizes = np.bincount(pieces.ravel())[1:]
    largest = int(sizes.argmax()) + 1
    if sizes[largest - 1] < BOX_LEAST * max(object_pixels, 1):
        return None
    rows, columns = np.nonzero(pieces == largest)
    return [int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1]


def prompts(work, answers, take, entry):
    """SAM 3's pictures for one take: each turntable view on white (<work>/multiview/sam3/<take>~<view>.png) with its
    finishes' phrases and exemplar boxes (.json); the finishes, written to <work>/multiview/<take>/finishes.json."""
    from PIL import Image
    import measure
    import split_compare
    mesh = split_compare.raw_model(take)
    materials = measure.materials_of(entry)
    pixels, finishes = finishes_of(work, answers, take, materials)
    np.save(work / "multiview" / take / "finish_pixels.npy", pixels.astype(np.int32))
    face_region = split_compare.face_regions(mesh, take, pixels)
    codes = {f"S{number}": surface for number, surface in enumerate(finishes)}
    region_code = np.full(int(pixels.max()) + 1, -1)
    for number, surface in enumerate(finishes):
        region_code[finishes[surface]["regions"]] = number
    seed = np.where(face_region >= 0, region_code[np.maximum(face_region, 0)], -1)
    out = work / "multiview" / "sam3"
    out.mkdir(parents=True, exist_ok=True)
    for view in view_names(work, take):
        faces = face_map(work, take, view, mesh)
        drawn = Image.open(renders(work, take) / f"{view}.png").convert("RGBA")
        white = Image.new("RGBA", drawn.size, (255, 255, 255, 255))
        Image.alpha_composite(white, drawn).convert("RGB").save(out / f"{take}~{view}.png")
        on_seed = np.where(faces >= 0, seed[np.maximum(faces, 0)], -1)
        boxes = {code: box for code, box in ((code, exemplar_box(on_seed == number, (faces >= 0).sum()))
                                             for number, code in enumerate(codes)) if box}
        asked = {"phrases": {code: finishes[surface]["phrase"] for code, surface in codes.items()}, "boxes": boxes}
        (out / f"{take}~{view}.json").write_text(json.dumps(asked))
    record = {"codes": codes, "finishes": finishes, "overlap_c": round(close_up_overlap(work, take), 4)}
    (work / "multiview" / take / "finishes.json").write_text(json.dumps(record, indent=1))
    return record


def votes_of(work, take, mesh, count):
    """Per face and finish code, SAM 3's score-weighted share of the views that see the face (seen_in_view) with its
    pixel inside that finish's mask; how many views saw each face; and each face's mean texture colour over them (Lab,
    NaN where none did)."""
    from PIL import Image
    import labels
    votes = np.zeros((len(mesh.faces), count))
    shown = np.zeros(len(mesh.faces))
    colour = np.zeros((len(mesh.faces), 3))
    for view in view_names(work, take):
        seen, row, column = seen_in_view(work, take, view, mesh)
        shown[seen] += 1.0
        rgb = np.asarray(Image.open(renders(work, take) / f"{view}.png").convert("RGB"), dtype=np.float64) / 255
        colour[seen] += labels.lab(rgb[row[seen], column[seen]])
        stored = np.load(work / "multiview" / "sam3" / "masks" / f"{take}~{view}.npz")
        height, width = stored["shape"]
        for number in range(count):
            key = f"mask_S{number}"
            if key not in stored:
                continue
            mask = np.unpackbits(stored[key], axis=-1)[..., :width].astype(bool).reshape(height, width)
            hit = seen & mask[row, column]
            votes[hit, number] += float(stored[f"score_S{number}"])
    colour = np.where(shown[:, None] > 0, colour / np.maximum(shown, 1.0)[:, None], np.nan)
    return votes / np.maximum(shown, 1.0)[:, None], shown, colour


def texture_colours(work, take, mesh):
    """Each face's mean texture colour (Lab) over the turntable views that see it, NaN where none does (votes_of's
    colour without SAM 3's masks)."""
    from PIL import Image
    import labels
    colour = np.zeros((len(mesh.faces), 3))
    shown = np.zeros(len(mesh.faces))
    for view in view_names(work, take):
        seen, row, column = seen_in_view(work, take, view, mesh)
        shown[seen] += 1.0
        rgb = np.asarray(Image.open(renders(work, take) / f"{view}.png").convert("RGB"), dtype=np.float64) / 255
        colour[seen] += labels.lab(rgb[row[seen], column[seen]])
    return np.where(shown[:, None] > 0, colour / np.maximum(shown, 1.0)[:, None], np.nan)


def metal_rough(work, take, mesh):
    """Each face's texture metalness and roughness (0 to 1), averaged over the turntable views that see it
    (<view>-mr.png: red metal, green roughness), NaN where none does."""
    from PIL import Image
    total = np.zeros((len(mesh.faces), 2))
    shown = np.zeros(len(mesh.faces))
    for view in view_names(work, take):
        seen, row, column = seen_in_view(work, take, view, mesh)
        picture = np.asarray(Image.open(renders(work, take) / f"{view}-mr.png").convert("RGB"), dtype=np.float64) / 255
        total[seen] += picture[row[seen], column[seen], :2]
        shown[seen] += 1.0
    found = np.where(shown[:, None] > 0, total / np.maximum(shown, 1.0)[:, None], np.nan)
    return found[:, 0], found[:, 1]


def thickness(mesh):
    """Each face's thickness through the solid: the distance from its middle, along its inward normal, to the second
    surface the ray meets (the raw models' walls are double, about 2 mm apart, so the first is the wall's inside);
    NaN where there is none."""
    start = mesh.triangles_center - mesh.face_normals * 1e-6 * mesh.scale
    where, rays, _ = mesh.ray.intersects_location(start, -mesh.face_normals, multiple_hits=True)
    distance = np.linalg.norm(where - start[rays], axis=1)
    order = np.lexsort((distance, rays))
    rays, distance = rays[order], distance[order]
    first = np.r_[True, rays[1:] != rays[:-1]]
    rank = np.arange(len(rays)) - np.maximum.accumulate(np.where(first, np.arange(len(rays)), 0))
    found = np.full(len(mesh.faces), np.nan)
    found[rays[rank == 1]] = distance[rank == 1]
    return found


def face_features(work, take, mesh, colour, folder):
    """Each face's FEATURES (NaN where unknown), cached as <folder>/features.npy."""
    path = folder / "features.npy"
    if path.exists():
        return np.load(path)
    metal, rough = metal_rough(work, take, mesh)
    with np.errstate(divide="ignore", invalid="ignore"):
        found = np.column_stack([colour, metal, rough, np.log(thickness(mesh))])
    found[~np.isfinite(found)] = np.nan
    np.save(path, found.astype(np.float32))
    return found


def spread_votes(mesh, scores):
    """The votes spread over the surface as labels.smoothed_parts spreads part scores; each face's best finish, a
    face no vote reached taking the nearest reached face's."""
    from scipy.spatial import cKDTree
    import labels
    neighbours = labels.neighbour_matrix(mesh)
    current = scores
    for _ in range(labels.SMOOTH_ROUNDS):
        spread = neighbours @ current
        current = 0.5 * scores + spread / np.maximum(spread.sum(1, keepdims=True), 1e-12)
    reached = current.max(1) > 0
    best = current.argmax(1)
    if not reached.all():
        best[~reached] = best[reached][cKDTree(mesh.triangles_center[reached]).query(
            mesh.triangles_center[~reached])[1]]
    return best


def without_crumbs(mesh, finish):
    """labels.without_crumbs at the split's crumb size (split_compare.CRUMB): a finish's island under it joins the
    finish it borders most."""
    import labels
    import split_compare
    saved = labels.PART_CRUMB
    labels.PART_CRUMB = split_compare.CRUMB
    try:
        return labels.without_crumbs(mesh, finish)
    finally:
        labels.PART_CRUMB = saved


def parts_of(mesh, finish):
    """Each connected patch of one finish a part; a patch under split_compare.CRUMB of the model's area that borders
    nothing (a loose piece of the raw model) joins the part of the nearest face in a patch that is not one."""
    from scipy.spatial import cKDTree
    import patchy
    import split_compare
    islands = patchy.islands(finish, mesh.face_adjacency)
    sizes = np.bincount(islands, weights=mesh.area_faces)
    big = (sizes >= split_compare.CRUMB * mesh.area)[islands]
    if not big.all():
        islands[~big] = islands[big][cKDTree(mesh.triangles_center[big]).query(mesh.triangles_center[~big])[1]]
    return np.unique(islands, return_inverse=True)[1].reshape(-1)


def seed_codes(work, take, mesh, record):
    """Each face's finish code from the unlit close-up's finish regions (prompts' finish_pixels.npy) where view c sees
    it (-1 elsewhere)."""
    import split_compare
    pixels = np.load(work / "multiview" / take / "finish_pixels.npy")
    region_code = np.full(int(pixels.max()) + 1, -1)
    for number, surface in enumerate(record["finishes"]):
        region_code[record["finishes"][surface]["regions"]] = number
    face_region = split_compare.face_regions(mesh, take, pixels)
    return np.where(face_region >= 0, region_code[np.maximum(face_region, 0)], -1)


def classes(votes, seeds, count):
    """Finishes SAM 3 takes for one class: i and j join when i's votes (VOTE_LEAST) cover j's seed faces at least
    CLASS_COVER as well as j's own do, or j's cover i's so; each finish's class number."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    cover = np.zeros((count, count))
    for second in range(count):
        members = seeds == second
        if members.any():
            cover[:, second] = (votes[members] >= VOTE_LEAST).mean(0)
    own = np.diag(cover)
    links = (cover >= CLASS_COVER * own[None, :]) & (own[None, :] > 0)
    np.fill_diagonal(links, False)
    return connected_components(sparse.csr_matrix(links | links.T), directed=False)[1]


def core_faces(mesh, members, rings):
    """`members` (faces) less every face within `rings` edge rings of a face outside it: the region's core."""
    pairs = mesh.face_adjacency
    core = members.copy()
    for _ in range(rings):
        outside = ~core
        border = np.zeros(len(core), dtype=bool)
        border[pairs[:, 0][outside[pairs[:, 1]]]] = True
        border[pairs[:, 1][outside[pairs[:, 0]]]] = True
        core &= ~border
    return core


def main_hue(colours):
    """Which of the colours (Lab) lie in the larger of two hue groups (two-means on a*, b*) when the groups' centres
    lie HUE_APART or more apart, else all of them: a seed region holding its neighbour's foil keeps its own."""
    hue = colours[:, 1:]
    spread = hue - hue.mean(0)
    axis = np.linalg.svd(spread, full_matrices=False)[2][0]
    along = spread @ axis
    every = np.ones(len(colours), dtype=bool)
    if len(colours) < 2 or np.ptp(along) == 0:
        return every
    centres = np.stack([hue[along <= np.median(along)].mean(0), hue[along > np.median(along)].mean(0)])
    for _ in range(HUE_ROUNDS):
        group = np.linalg.norm(hue[:, None] - centres[None], axis=2).argmin(1)
        if (group == group[0]).all():
            return every
        centres = np.stack([hue[group == number].mean(0) for number in (0, 1)])
    if np.linalg.norm(centres[0] - centres[1]) < HUE_APART:
        return every
    return group == np.bincount(group, minlength=2).argmax()


def exemplar_faces(mesh, colour, members):
    """The faces a finish's exemplar is taken from, of its seed faces `members`: their core (CORE_RINGS in from the
    border, or all of them when the core keeps under CORE_LEAST coloured faces), the middle CORE_LIGHTNESS of its
    L* (shade and highlight out), then its main hue (main_hue)."""
    coloured = members & ~np.isnan(colour[:, 0])
    core = core_faces(mesh, members, CORE_RINGS) & coloured
    kept = core if core.sum() >= CORE_LEAST else coloured
    if kept.sum() < 2:
        return kept
    low, high = np.quantile(colour[kept, 0], CORE_LIGHTNESS)
    middle = kept & (colour[:, 0] >= low) & (colour[:, 0] <= high)
    if middle.sum() >= 2:
        kept = middle
    found = np.zeros(len(members), dtype=bool)
    found[np.nonzero(kept)[0][main_hue(colour[kept])]] = True
    return found


def exemplar(features, faces):
    """A finish's exemplar over `faces`: per feature the median and the spread (1.4826 times the median absolute
    deviation, never under SPREAD_FLOOR); NaN where no face has the feature."""
    import warnings
    chosen = features[faces]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a feature no chosen face has: its median is NaN
        centre = np.nanmedian(chosen, axis=0)
        spread = 1.4826 * np.nanmedian(np.abs(chosen - centre), axis=0)
    return centre, np.fmax(spread, SPREAD_FLOOR[:chosen.shape[1]])


def likelihoods(features, centres, spreads):
    """Each face's probability of each exemplar (independent Gaussians over the features both know; a face with no
    known feature gets zeros)."""
    log = np.zeros((len(features), len(centres)))
    known = np.zeros(len(features), dtype=bool)
    for number, (centre, spread) in enumerate(zip(centres, spreads)):
        usable = ~np.isnan(centre)
        values = features[:, usable]
        terms = -0.5 * ((values - centre[usable]) / spread[usable]) ** 2 - np.log(spread[usable])
        log[:, number] = np.nansum(terms, axis=1)
        known |= (~np.isnan(values)).any(1)
    log -= log.max(1, keepdims=True)
    found = np.exp(log)
    found /= found.sum(1, keepdims=True)
    found[~known] = 0.0
    return found


def within_class(mesh, finish, features, seeds, class_of, count):
    """Each face's finish chosen again within its finish's class (classes) by what its texture and shape say: per
    face each member finish's likelihood (likelihoods) under its exemplar (exemplar over exemplar_faces), spread
    over the surface as labels.smoothed_parts spreads part scores (a lone fleck of the neighbour's colour does not
    win its face; a face with nothing known takes its neighbours'), then the best."""
    import labels
    colour = features[:, :3]
    exemplars = [exemplar(features, exemplar_faces(mesh, colour, seeds == number)) for number in range(count)]
    found = finish.copy()
    neighbours = labels.neighbour_matrix(mesh)
    for group in np.unique(class_of):
        members = [number for number in range(count)
                   if class_of[number] == group and not np.isnan(exemplars[number][0][0])]
        if len(members) < 2:
            continue
        inside = np.isin(finish, members)
        scores = np.zeros((len(finish), len(members)))
        scores[inside] = likelihoods(features[inside], [exemplars[number][0] for number in members],
                                     [exemplars[number][1] for number in members])
        current = scores
        for _ in range(labels.SMOOTH_ROUNDS):
            spread = neighbours @ current
            current = 0.5 * scores + spread / np.maximum(spread.sum(1, keepdims=True), 1e-12)
        reached = inside & (current.max(1) > 0)
        found[reached] = np.array(members)[current[reached].argmax(1)]
    return found


def split(work, take, out, colour_only=False):
    """The texture-aware split: SAM 3's winning finish per face where the views decide it and the close-up's own
    regions where view c sees them, spread over the rest; then within each class (finishes SAM 3 takes for one
    thing: gold and silver foil, a chair's vinyl and steel) every face takes the finish its features make likeliest,
    smoothed (within_class; with `colour_only` its texture colour alone); crumbs join their neighbours and each
    connected patch of one finish is a part (<work>/<out>/<take>/parts.npy)."""
    import split_compare
    mesh = split_compare.raw_model(take)
    record = json.loads((work / "multiview" / take / "finishes.json").read_text())
    count = len(record["codes"])
    votes, shown, colour = votes_of(work, take, mesh, count)
    seeds = seed_codes(work, take, mesh, record)
    decided = votes.max(1) >= VOTE_LEAST
    chosen = votes.argmax(1)
    seeded = seeds >= 0
    chosen[seeded] = seeds[seeded]
    decided |= seeded
    scores = np.zeros_like(votes)
    scores[np.nonzero(decided)[0], chosen[decided]] = 1.0
    class_of = classes(votes, seeds, count)
    folder = work / out / take
    folder.mkdir(parents=True, exist_ok=True)
    features = colour if colour_only else face_features(work, take, mesh, colour, folder)
    finish = within_class(mesh, spread_votes(mesh, scores), features, seeds, class_of, count)
    finish[seeded] = seeds[seeded]
    finish = without_crumbs(mesh, finish)
    part_of = parts_of(mesh, finish)
    np.save(folder / "parts.npy", part_of.astype(np.int32))
    np.save(folder / "finish.npy", finish.astype(np.int16))
    np.save(folder / "colour.npy", colour.astype(np.float32))
    areas = mesh.area_faces
    report = {"take": take, "parts": int(part_of.max()) + 1,
              "shown_share": round(float(areas[shown > 0].sum() / areas.sum()), 3),
              "decided_share": round(float(areas[decided].sum() / areas.sum()), 3),
              "classes": {record["codes"][f"S{number}"]: int(class_of[number]) for number in range(count)},
              "finish_shares": {record["codes"][f"S{number}"]: round(float(areas[finish == number].sum() / areas.sum()),
                                                                     3) for number in range(count)}}
    (folder / "split.json").write_text(json.dumps(report, indent=1))
    return report
