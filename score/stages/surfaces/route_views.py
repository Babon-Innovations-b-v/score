"""The finish route's views row (free, on this PC's processor, no Blender): each take's raw model rendered from every
angle it needs in one go, and its colour regions, ready for the one finish list ask.

The angles (`covering_views`, the free coverage check before the render): the BASE views (the close-up's front, the
back, both sides, the top, the bottom), then from CANDIDATES the one that sees the most area no chosen view sees,
again, until every face is seen, no candidate sees one more, or MOST_VIEWS. A face no view can see (inside the model)
is counted (`unseen_faces`, `unseen_share`); the split gives it its nearest seen face's finish.

Each view: the face under each pixel and its colour from the model's own texture (route_cast). The texture is only
measured, never painted: every finish is a library surface. The take's own close-up, where it has its camera and the
cast fits its outline (route_cast.CLOSE_UP_FIT), is laid on the model through that camera (laid_close_up), one more
view of the regions, CLOSE_UP: a small part it shows (a red label, a decal, a screen's glow) the raw texture often
lacks. Its regions: every seen pixel's CIELAB colour, the views' and the laid close-up's, in groups of distinct colour
(colour_regions: FINE k-means groups fitted on SAMPLE pixels with the node's seed, a group for each far colour they
miss, the nearest merged down to REGIONS; colours only split, they name nothing), the same groups in every view, so
the list's answer labels each region of each view with a finish. A region holds one piece group (piece_groups: the
model's main piece or the rest, where the rest shows PIECE_SHARE), so one colour on two pieces is two regions (#174),
and one SAM 3 mask of the close-up where the take has them (its input `masks <take>`, a folder: mask_faces, laid
through the close-up's camera), so a panel bounded by an edge is a region even where its colour lies inside its
body's (#207).

Output per take: <take>/model.npz (the welded, normalised vertices and faces every later row reads, so the face ids
agree), <take>/faces.npz, colours.npz and regions.npz (one array a view), <take>/<view>.png (the texture, shaded by
angle), <take>/regions-<view>.png (each region in its label colour, finish_ask.LABELS), <take>/close-up.png (the take's
own close-up, else the stand-in: the front view unshaded, route_data.STAND_IN); where the close-up is laid,
<take>/close-up.npz (its face per pixel and colours) and regions-close-up.png, its regions in regions.npz.
<take>/texels.npz, where the model has a picture: each picture's texels, the face covering each and its colour's
region (texel_regions), which the split gives each its finish (route_texels), and where the close-up is laid the
region it shows each texel in (close_up_texels).
views.json: per take its model, its views' angles, its faces and how many the paint's loading finds, the share of its
area seen, its regions (CIELAB, sRGB, share of the seen pixels; where the close-up is laid, each one's colour there,
close_up_shown, which the list reads its colour from), its close-up's source and whether it was laid.
Gate "views cast": every take has its raw model, loaded with the faces the paint loads, every view sees it and the
views together see SEEN_LEAST of the area any angle sees (both measured at MEASURE_SIDE). A take a batch gap names
(score/stages/batch_gaps.py: its close-up or its Pixal3D job failed in the batch) is left out, and its gap carried on
in this output's batch-gaps.json.
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_ask  # noqa: E402
import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402
from score import checks  # noqa: E402

SEEN_LEAST = 0.5  # a take whose views together see under this share of its area fails: the cast missed the model
MOST_VIEWS = 16  # the base views and the coverage check's extras together
# The most side the seen shares are measured at (measure_side), the angles cast finer: at cast.SIDE a raw Pixal3D
# person (1.8 m tall, a million faces of about 1.4 mm) has several faces under each 4.7 mm pixel and most are never
# hit, so the share read 29% for astronaut-made-s1 (2026-10-22); at this side a pixel is about a face.
MEASURE_SIDE = 1536
# Measured there, every angle (BASE and CANDIDATES) together saw 49.5% of that take: the rest lies inside the raw
# model, out of every view, so the gate holds the views to SEEN_LEAST of the area any angle sees (`reachable_share`),
# never of area no cast can reach.
REGIONS = len(finish_ask.LABELS)  # one label colour a region in the list's pictures
SAMPLE = 60000  # the pixels k-means is fitted on, drawn with the node's seed
# k-means over all seen pixels spent its REGIONS groups on the texture's shading and rust: greenhouse desk's eight
# were seven greys from L* 21 to 62 and one paper yellow, so its close-up's red DANGER label, blue decal and teal
# screens had no region and no part (likeness@greenhouse, 2026-10-29). The pixels are first grouped finer (FINE),
# each far colour given a group (ACCENT_DE, ACCENT_LEAST), and the nearest groups merged down to REGIONS.
FINE = 4 * REGIONS
ACCENT_DE = 15.0  # CIE76: a pixel this far from every fine group's centre is a colour none of them holds
ACCENT_LEAST = 40  # the fewest pixels (every view and the close-up together) a group of its own needs
# Two groups each holding MAJOR_SHARE of the pixels whose hues lie MAJOR_CHROMA apart (CIE a*b* distance, so shading
# steps of one colour, which differ in L*, never count) are two materials and merge last (merged_centres, #202):
# tc6's heat gun's slate blue body (texture L* 30, a*b* -1.3 -9.4, 40% of its pixels) and dark grey cap and battery
# (L* 23, -0.2 -4.3, 51%), 8.6 apart, merged into one region before the laid close-up's shading steps of each did
# (14 apart in L*), and the list drew the battery the body's blue. Measured on all 33 of tc6's takes: only the heat
# gun's regions and the surgical chair's (its two textured whites, a*b* 4.5 apart, kept apart for a 0.2% group of
# L* 78) change.
MAJOR_SHARE = 0.1
MAJOR_CHROMA = 4.0
# A colour spanning the model's main piece and its other pieces is two regions (#174): TRELLIS.2's desk made its
# board and its legs separate pieces, but colour alone grouped the board's underside with the legs (sRGB 182 against
# 179) and the list could only label the whole region, as frame metal in all 16 views. Each pixel is of the main piece
# (the model's largest connected piece and every piece lying mostly inside its box: a shell's inner wall) or of the
# rest (piece_groups), and a region never holds both (colour_regions); only where the rest shows PIECE_SHARE of the
# seen pixels (on that desk 11%, its legs and feet), so a model of one piece and its crumbs groups as before.
PIECE_SHARE = 0.05
CLOSE_UP = "close-up"  # the close-up's own pixels laid on the model through its camera, a view of the regions
# How far, in the close-up's pixels at its depth, a texel may lie from the face the close-up shows there and still be
# the one it shows (close_up_texels): a texel's face is often not the one cast at its pixel's middle where faces are
# finer than the cast.
SEEN_DEPTH = 3.0
# A region's colour in the laid close-up (close_up_shown) is read from at least this many of its pixels: fewer are a
# few edge pixels of a part the close-up hardly shows.
SHOWN_LEAST = 25
EDGE = 2  # a close-up pixel is kept only when those EDGE away on every side lie on the model in the cast and alpha
# SAM 3's masks of the close-up (#207, the input `masks <take>`, mask_faces): tc6's humidifier's control window, a
# mid-grey panel (sRGB 95 to 115) on a ribbed grey body whose rib light and shadow span 76 to 155, fell by colour alone
# in regions holding rib pixels. Each mask laid through the close-up's camera is a group of its own, so its faces are
# regions no other part's pixels join. A face is a mask's when MASK_SHARE of its laid pixels lie under it (the
# smallest such mask, so a panel inside a door's mask keeps its own); a mask showing under SHOWN_LEAST laid pixels, or
# over MASK_MOST of the laid model, is none (a speck, or the whole body), nor one whose overlap with a kept one is
# MASK_SAME of the two together (the same panel under two words). At most MASKS_MOST are kept, the largest first, so the piece groups and every
# mask keep a region of the REGIONS.
MASK_SHARE = 0.5
MASK_MOST = 0.5
MASK_SAME = 0.8
MASKS_MOST = REGIONS - 2


def seen_area(mesh, found):
    """The model's area under the pixels of `found` (a view's face per pixel)."""
    return float(mesh.area_faces[np.unique(found[found >= 0])].sum())


def covering_views(mesh):
    """({view: angles}, {view: (face per pixel, point per pixel)}): BASE's views, then the candidate that sees the
    most area no chosen view sees, again, until none sees more or MOST_VIEWS are chosen."""
    angles = dict(cast.BASE)
    casts = {view: cast.cast(mesh, angles[view]) for view in angles}
    seen = np.zeros(len(mesh.faces), dtype=bool)
    for faces, _ in casts.values():
        seen[faces[faces >= 0]] = True
    candidates = {view: cast.cast(mesh, turn) for view, turn in cast.CANDIDATES.items()}
    while candidates and len(angles) < MOST_VIEWS and not seen.all():
        gains = {view: seen_area(mesh, np.where(seen[np.maximum(found, 0)], -1, found))
                 for view, (found, _) in candidates.items()}
        best = max(gains, key=gains.get)
        if gains[best] <= 0:
            break
        angles[best], casts[best] = cast.CANDIDATES[best], candidates.pop(best)
        seen[casts[best][0][casts[best][0] >= 0]] = True
    return angles, casts


def fine_centres(every, seed):
    """FINE k-means centres fitted on SAMPLE of `every` (CIELAB pixels), and a centre for each group of ACCENT_LEAST
    or more pixels further than ACCENT_DE from all of them (accent_centres)."""
    from scipy.cluster.vq import kmeans2
    draw = np.random.default_rng(seed).choice(len(every), min(SAMPLE, len(every)), replace=False)
    distinct = len(np.unique(every[draw].round(1), axis=0))  # fewer colours than FINE: one centre each
    centres, _ = kmeans2(every[draw], min(FINE, distinct), seed=seed, minit="++")
    return np.concatenate([centres, accent_centres(every, centres, seed)])


def accent_centres(every, centres, seed):
    """A centre for each group of ACCENT_LEAST or more of `every`'s pixels that lie further than ACCENT_DE from every
    one of `centres`: a small saturated area (a red label, a screen's glow) is too few pixels of the sample to draw a
    centre of its own."""
    from scipy.cluster.vq import kmeans2, vq
    far = every[vq(every, centres)[1] > ACCENT_DE]
    if len(far) < ACCENT_LEAST:
        return np.zeros((0, 3))
    draw = np.random.default_rng(seed).choice(len(far), min(SAMPLE, len(far)), replace=False)
    groups, _ = kmeans2(far[draw], min(REGIONS, len(np.unique(far[draw].round(1), axis=0))), seed=seed, minit="++")
    counts = np.bincount(vq(far, groups)[0], minlength=len(groups))
    return groups[counts >= ACCENT_LEAST]


def merged_centres(every, centres, groups):
    """(`centres` and their piece groups) with the groups of fewer than ACCENT_LEAST of `every`'s pixels dropped
    (their pixels go to the nearest group left), then the two nearest merged (weighed by their pixels) until REGIONS
    are left: shading steps of one colour lie close and merge first, a colour far from the rest keeps its own region
    however small, two of other piece groups (`groups`: each pixel's and each centre's, colour_regions) only when no
    other two groups are left, and two materials (two_materials) last of all, so the one colour on two pieces merges
    before a piece loses one of its materials (#174)."""
    every_group, centre_groups = groups
    counts = np.bincount(assigned(every, every_group, centres, centre_groups), minlength=len(centres)).astype(float)
    kept = counts >= min(ACCENT_LEAST, counts.max())
    centres, counts, centre_groups = centres[kept], counts[kept], centre_groups[kept]
    while len(centres) > REGIONS:
        apart = np.linalg.norm(centres[:, None] - centres[None], axis=-1) + np.diag(np.full(len(centres), np.inf))
        last = (apart + 1e3 * (centre_groups[:, None] != centre_groups[None])  # 1000: past any two CIELAB colours'
                + 2e3 * two_materials(centres, counts))  # distance; two materials after every piece group merge
        first, second = np.unravel_index(last.argmin(), apart.shape)
        centres[first] = (centres[first] * counts[first] + centres[second] * counts[second]) \
            / (counts[first] + counts[second])
        counts[first] += counts[second]
        centres, counts = np.delete(centres, second, axis=0), np.delete(counts, second)
        centre_groups = np.delete(centre_groups, second)
    return centres, centre_groups


def two_materials(centres, counts):
    """Whether each two groups are two materials (MAJOR_SHARE and MAJOR_CHROMA): each holds MAJOR_SHARE of the
    pixels and their hues lie MAJOR_CHROMA apart."""
    major = counts >= MAJOR_SHARE * counts.sum()
    hue = np.linalg.norm(centres[:, None, 1:] - centres[None, :, 1:], axis=-1)
    return major[:, None] & major[None] & (hue >= MAJOR_CHROMA)


def colour_regions(colours, faces, seed, groups=None, masked=None):
    """(the regions' CIELAB centres, each view's region per pixel, -1 off the model, each region's group):
    every seen pixel's colour in at most REGIONS groups of distinct colour (fine_centres merged, merged_centres), a
    region of one piece group only where `groups` (piece_groups, per face) gives the rest PIECE_SHARE of the seen
    pixels, else one group, and of one close-up mask where `masked` (mask_faces, per face, 0 under none) names one
    (each group its piece's and mask's together, masked_groups); groups no pixel falls in are dropped."""
    seen = {view: cast.lab_of(colours[view][faces[view] >= 0]) for view in faces}
    every = np.concatenate(list(seen.values()))
    if groups is None:
        of = {view: np.zeros(len(lab), dtype=int) for view, lab in seen.items()}
    else:
        of = {view: np.asarray(groups)[faces[view][faces[view] >= 0]].astype(int) for view in faces}
    every_group = np.concatenate(list(of.values()))
    if (every_group > 0).mean() < PIECE_SHARE:
        of = {view: np.zeros_like(group) for view, group in of.items()}
    if masked is not None:
        of = {view: masked_groups(group, np.asarray(masked)[faces[view][faces[view] >= 0]], masked)
              for view, group in of.items()}
    every_group = np.concatenate(list(of.values()))
    fitted = [(fine_centres(every[every_group == group], seed + group), group) for group in np.unique(every_group)]
    centres = np.concatenate([found for found, _ in fitted])
    centre_groups = np.concatenate([np.full(len(found), group) for found, group in fitted])
    centres, centre_groups = merged_centres(every, centres, (every_group, centre_groups))
    used = np.unique(assigned(every, every_group, centres, centre_groups))
    centres, centre_groups = centres[used], centre_groups[used]
    per_pixel = {}
    for view, lab in seen.items():
        label = np.full(faces[view].shape, -1)
        label[faces[view] >= 0] = assigned(lab, of[view], centres, centre_groups)
        per_pixel[view] = label
    return centres, per_pixel, centre_groups


def piece_groups(mesh):
    """Each face's piece group: 0 on the model's largest connected piece and every piece whose faces' centres lie at
    least half inside that piece's box (a shell's inner wall), 1 on the rest (PIECE_SHARE's note)."""
    import trimesh
    piece = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(mesh.faces))
    counts = np.bincount(piece)
    centres = mesh.triangles_center
    main = centres[piece == counts.argmax()]
    inside = ((centres >= main.min(0)) & (centres <= main.max(0))).all(1)
    return (np.bincount(piece, weights=inside)[piece] / counts[piece] < 0.5).astype(int)


def masked_groups(pieces, masks, masked):
    """Each of `pieces` (piece groups) and its mask in `masks` (one of `masked`'s, mask_faces: 0 under none) as one
    group, `piece * span + mask`, span one past `masked`'s most, so the main piece under no mask stays group 0."""
    return np.asarray(pieces) * (int(np.max(masked, initial=0)) + 1) + np.asarray(masks)


def mask_faces(face_count, laid, masks):
    """Each face's close-up mask (#207): one more than the number among the kept masks (MASK_MOST, SHOWN_LEAST,
    MASK_SAME, MASKS_MOST; the largest first) of the smallest under which MASK_SHARE of the face's laid pixels lie, 0
    under none or not laid. `laid`: the face under each close-up pixel kept (kept_close_up), `masks`: SAM 3's of the
    close-up on the same grid (close_up_masks), bool (count, rows, columns)."""
    on = laid >= 0
    seen = np.bincount(laid[on], minlength=face_count)
    shown = [int((mask & on).sum()) for mask in masks]
    kept = []
    for index in sorted(range(len(masks)), key=lambda number: -shown[number]):
        if len(kept) == MASKS_MOST or not SHOWN_LEAST <= shown[index] <= MASK_MOST * on.sum():
            continue
        if any((masks[index] & masks[other] & on).sum() > MASK_SAME * ((masks[index] | masks[other]) & on).sum()
               for other in kept):
            continue
        kept.append(index)
    found = np.zeros(face_count, dtype=int)
    for number, index in enumerate(kept):  # largest first: a smaller mask a face lies under takes it after
        under = np.bincount(laid[on & masks[index]], minlength=face_count)
        found[(seen > 0) & (under >= MASK_SHARE * seen)] = number + 1
    return found


def close_up_masks(folder, close_up):
    """SAM 3's masks of the take's close-up (#207, its input `masks <take>`: a folder of them, one picture each, white
    on black at the close-up's own size), by name, read on the grid route_cast.close_up_cast samples the close-up on
    (every step-th pixel, at most route_cast.CLOSE_UP_SIDE across): bool (count, rows, columns). A mask of another
    size is refused: it is not a mask of this close-up."""
    from PIL import Image
    with Image.open(close_up) as picture:
        width, height = picture.size
    step = max(1, -(-max(width, height) // cast.CLOSE_UP_SIDE))
    found = []
    for path in sorted(pathlib.Path(folder).glob("*.png")):
        with Image.open(path) as mask:
            if mask.size != (width, height):
                raise ValueError(f"{path.name}: a mask of {mask.size[0]}x{mask.size[1]}, the close-up is "
                                 f"{width}x{height}: not a mask of this close-up")
            found.append(np.asarray(mask.convert("L"))[::step, ::step] > 127)
    return np.array(found, dtype=bool).reshape(len(found), -(-height // step), -(-width // step))


def assigned(lab, lab_groups, centres, centre_groups):
    """Each CIELAB pixel's nearest centre among its own piece group's (all of them where its group has none)."""
    from scipy.cluster.vq import vq
    found = np.zeros(len(lab), dtype=int)
    for group in np.unique(lab_groups):
        mine, own = lab_groups == group, np.flatnonzero(centre_groups == group)
        own = own if len(own) else np.arange(len(centres))
        found[mine] = own[vq(lab[mine], centres[own])[0]]
    return found


def region_records(centres, colours, per_pixel, shown=None):
    """Each region's CIELAB centre, median sRGB 0-255 over its pixels in every view and share of the seen pixels;
    with `shown` (close_up_shown, where the close-up is laid) its `close_up_srgb` too."""
    seen = sum(int((label >= 0).sum()) for label in per_pixel.values())
    found = []
    for region, centre in enumerate(centres):
        pixels = np.concatenate([colours[view][per_pixel[view] == region] for view in colours])
        found.append({"region": region, "lab": [round(float(value), 1) for value in centre],
                      "srgb": np.median(pixels, axis=0).round().astype(int).tolist(),
                      "share": round(len(pixels) / max(seen, 1), 4),
                      **({"close_up_srgb": shown[region]} if shown is not None else {})})
    return found


def close_up_shown(faces, per_pixel, laid, count):
    """Each of the `count` regions' median sRGB 0-255 in the laid close-up (`laid`: its face and colour per pixel) over
    the faces the texture's views give that region (each face the region of most of its pixels there), None where
    the close-up shows under SHOWN_LEAST pixels of them. The texture is TRELLIS.2's copy of the close-up and drifts from
    it in hue, saturation and value: tc5r's hospital chair seat textured royal blue (chroma 46) where the close-up shows
    teal (23), its vending cabinet textured L* 18 where the close-up shows 42, and the list took each token off the
    texture (#198)."""
    laid_faces, laid_colours = laid
    textured = [view for view in faces if view != CLOSE_UP]
    face_ids = np.concatenate([faces[view][per_pixel[view] >= 0] for view in textured])
    labels = np.concatenate([per_pixel[view][per_pixel[view] >= 0] for view in textured])
    votes = np.zeros((int(max(face_ids.max(initial=-1), laid_faces.max(initial=-1))) + 1, count), dtype=np.int64)
    np.add.at(votes, (face_ids, labels), 1)
    face_region = np.where(votes.any(1), votes.argmax(1), -1)
    on = laid_faces >= 0
    region_seen = face_region[laid_faces[on]]
    pixels = laid_colours[on]
    found = []
    for region in range(count):
        held = pixels[region_seen == region]
        found.append(np.median(held, axis=0).round().astype(int).tolist() if len(held) >= SHOWN_LEAST else None)
    return found


def views_saved(folder, model, cast_views, regions):
    """model.npz, faces.npz, colours.npz, regions.npz and each view's pictures (the texture and the regions, shaded
    by angle) into `folder`; cast_views is (angles, faces, colours)."""
    angles, faces, colours = cast_views
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "model.npz", vertices=model.mesh.vertices.astype(np.float32),
                        faces=model.mesh.faces.astype(np.int32))
    palette = np.array(finish_ask.LABELS, dtype=np.uint8)
    for view in faces:
        shade = cast.shading(model.mesh, faces[view], angles[view])
        cast.picture(colours[view], faces[view], shade).save(folder / f"{view}.png")
        painted = np.where((regions[view] >= 0)[..., None], palette[np.maximum(regions[view], 0)], 0)
        cast.picture(painted, faces[view], shade).save(folder / f"regions-{view}.png")
    np.savez_compressed(folder / "faces.npz", **{view: found.astype(np.int32) for view, found in faces.items()})
    np.savez_compressed(folder / "colours.npz", **colours)
    np.savez_compressed(folder / "regions.npz", **{view: label.astype(np.int16) for view, label in regions.items()})


def texel_regions(model, centres, groups):
    """{face<k>, region<k>}: each texel of the model's piece k's colour picture, the face covering it (-1 none) and the
    region of its colour among its face's piece group's (route_texels.face_texels; -1 off the faces; `groups`: each
    face's group and each region's, colour_regions), for every piece with a picture and UVs: the texels the split
    gives each its finish (route_texels)."""
    import route_texels
    face_groups, region_groups = groups
    found = {}
    for piece, picture in enumerate(model.pictures):
        mine = np.flatnonzero(model.piece_of == piece)
        if picture is None or not len(mine) or np.isnan(model.corner_uv[mine]).any():
            continue
        face_of = route_texels.face_texels(model.corner_uv[mine], mine, picture.shape[:2])
        covered = face_of >= 0
        colours = np.clip(picture[covered] * model.factors[piece][:3], 0, 255)
        region_of = np.full(face_of.shape, -1, dtype=np.int8)
        region_of[covered] = assigned(cast.lab_of(colours), face_groups[face_of[covered]], centres, region_groups)
        found[f"face{piece}"], found[f"region{piece}"] = face_of.astype(np.int32), region_of
    return found


def texel_points(model, face_of):
    """(the texels of a picture (`face_of`, the face covering each, -1 none) a face covers, as a mask; each one's point
    on its face, in the model's normalised frame, NaN where its face's UVs have no area): read back from its place in
    the picture (UV) to its face's corners."""
    tall, wide = face_of.shape
    covered = face_of >= 0
    rows, columns = np.nonzero(covered)
    faces = face_of[covered]
    uv = np.c_[(columns + 0.5) / wide, 1.0 - (rows + 0.5) / tall]
    corners = model.corner_uv[faces]
    first, second, to = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0], uv - corners[:, 0]
    across = first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]
    flat = np.abs(across) < 1e-12
    across = np.where(flat, 1.0, across)
    along = (to[:, 0] * second[:, 1] - to[:, 1] * second[:, 0]) / across
    upward = (first[:, 0] * to[:, 1] - first[:, 1] * to[:, 0]) / across
    ends = model.mesh.vertices[model.mesh.faces[faces]]
    points = ends[:, 0] + along[:, None] * (ends[:, 1] - ends[:, 0]) + upward[:, None] * (ends[:, 2] - ends[:, 0])
    points[flat] = np.nan
    return covered, points


def close_up_texels(model, own, laid_faces, laid_regions, texels):
    """{closeup<k>}: each texel of piece k the region the laid close-up shows it in, -1 where it does not see it (off
    the cast, or a surface in front nearer than SEEN_DEPTH of the close-up's pixels): read at the texel's own point on
    its face through the close-up's camera (`own`: the close-up and its camera file), so a part the texture lacks is
    drawn at the texels' detail, not the faces' (#159 round 8: the readout window's lit digits came out as shards of
    the coarse window faces under them)."""
    from PIL import Image
    with Image.open(own[0]) as picture:
        wide, tall = picture.size
    eye, right, up, field = cast.close_up_camera(own[1])
    focal = wide / 2 / np.tan(field / 2)
    ahead = np.cross(up, right)
    step = max(1, -(-max(wide, tall) // cast.CLOSE_UP_SIDE))
    middle, side = model.frame
    centres = model.mesh.triangles_center * side + middle
    found = {}
    for name in [name for name in texels if name.startswith("face")]:
        face_of = texels[name]
        covered, points = texel_points(model, face_of)
        relative = points * side + middle - eye
        depth = relative @ ahead
        safe = np.where(depth > 0, depth, np.nan)
        row = np.floor((tall / 2 - focal * (relative @ up) / safe) / step)
        column = np.floor((wide / 2 + focal * (relative @ right) / safe) / step)
        inside = (row >= 0) & (row < laid_faces.shape[0]) & (column >= 0) & (column < laid_faces.shape[1])
        row, column = np.where(inside, row, 0).astype(int), np.where(inside, column, 0).astype(int)
        shown = laid_faces[row, column]
        nearest = (centres[np.maximum(shown, 0)] - eye) @ ahead
        seen = inside & (shown >= 0) & ((shown == face_of[covered])
                                        | (np.abs(nearest - depth) <= SEEN_DEPTH * step * safe / focal))
        region = np.full(face_of.shape, -1, dtype=np.int8)
        region[covered] = np.where(seen, laid_regions[row, column], -1)
        found[f"closeup{name[len('face'):]}"] = region
    return found


def close_up_written(folder, close_up, faces, colours):
    """close-up.png: the take's own close-up copied, else the stand-in (its own texture from the front)."""
    if close_up is not None:
        shutil.copyfile(close_up, folder / "close-up.png")
    else:
        cast.picture(colours[cast.FRONT], faces[cast.FRONT]).save(folder / "close-up.png")


def paint_faces(model_file):
    """The faces the paint finds in the raw model (split_compare.raw_model loads it as one mesh, its faces in order)."""
    import trimesh
    return len(trimesh.load(str(model_file), force="mesh", process=False).faces)


def measure_side(mesh):
    """The side the seen shares are measured at: a pixel a third of the model's median face across, at least
    cast.SIDE, at most MEASURE_SIDE (cast.rays frames the bounding sphere)."""
    reach = float(np.linalg.norm(mesh.vertices, axis=1).max()) * cast.MARGIN
    edge = float(np.sqrt(2 * np.median(mesh.area_faces)))
    return int(min(MEASURE_SIDE, max(cast.SIDE, np.ceil(6 * reach / edge))))


def seen_share(mesh, faces):
    """The share of the model's area under some pixel of `faces` (views' faces per pixel)."""
    seen = np.unique(np.concatenate([found[found >= 0] for found in faces]))
    return float(mesh.area_faces[seen].sum() / mesh.area_faces.sum())


def view_record(model, faces, angles, close_up):
    """A take's record: its views' angles, its faces, the share of its area some view sees, its unseen faces, its
    empty views, its close-up's source."""
    seen = np.unique(np.concatenate([found[found >= 0] for found in faces.values()]))
    area = model.mesh.area_faces
    return {"views": angles, "faces": len(model.mesh.faces), "seen_share": round(seen_share(model.mesh, faces.values()), 3),
            "unseen_faces": len(model.mesh.faces) - len(seen),
            "unseen_share": round(float(1 - area[seen].sum() / area.sum()), 4),
            "views_empty": [view for view, found in faces.items() if not (found >= 0).any()],
            "close_up": "own" if close_up is not None else route_data.STAND_IN}


def kept_close_up(model, close_up, camera_file):
    """(the face under each close-up pixel kept, -1 elsewhere; the pixels' colours, sRGB 0-255; the cast's fit) of
    the take's own close-up through its own camera (route_cast.close_up_pixels): a pixel is kept where it and those
    EDGE away on every side lie on the model in both the cast and the close-up's alpha, so no border pixel mixes the
    model with the backdrop."""
    faces, sampled, both, fit = cast.close_up_pixels(model, camera_file, close_up)
    kept = both.copy()
    for axis in (0, 1):
        for shift in (EDGE, -EDGE):
            kept &= np.roll(both, shift, axis=axis)
    return np.where(kept, faces, -1), np.ascontiguousarray(sampled[..., :3]), fit


def close_up_saved(folder, laid, regions):
    """close-up.npz (the laid close-up's face per pixel and colours) and regions-close-up.png (its regions in their
    label colours, unshaded: the close-up carries its own light)."""
    faces, colours = laid
    np.savez_compressed(folder / "close-up.npz", faces=faces.astype(np.int32), colours=colours)
    palette = np.array(finish_ask.LABELS, dtype=np.uint8)
    cast.picture(np.where((regions >= 0)[..., None], palette[np.maximum(regions, 0)], 0), faces).save(
        folder / f"regions-{CLOSE_UP}.png")


def laid_close_up(model, close_up, camera_file):
    """(the laid close-up (faces, colours) or None, its record): laid when the take has its own close-up and camera
    and the cast fits the close-up's outline at route_cast.CLOSE_UP_FIT."""
    if close_up is None or camera_file is None:
        return None, {"laid": False, "why": "no own close-up or camera"}
    faces, colours, fit = kept_close_up(model, close_up, camera_file)
    if fit < cast.CLOSE_UP_FIT:
        return None, {"laid": False, "fit": fit, "why": f"its cast fits the close-up's outline at IoU {fit}, under "
                                                       f"{cast.CLOSE_UP_FIT}"}
    return (faces, colours), {"laid": True, "fit": fit}


def view_take(model_file, close_up, camera_file, folder, seed, masks=None):
    """One take's views and regions into `folder`, the close-up laid on the model one more view of the regions
    (laid_close_up) where it fits, there each of its SAM 3 masks (`masks`, a folder: close_up_masks) a group of faces
    (mask_faces); its record (view_record, its regions, the paint's face count, the laid close-up, the masks)."""
    model = cast.loaded(model_file)
    angles, casts = covering_views(model.mesh)
    faces = {view: found for view, (found, _) in casts.items()}
    colours = {view: cast.texture_colours(model, found, points) for view, (found, points) in casts.items()}
    laid, laid_record = laid_close_up(model, close_up, camera_file)
    every_faces, every_colours = dict(faces), dict(colours)
    if laid is not None:
        every_faces[CLOSE_UP], every_colours[CLOSE_UP] = laid
    groups = piece_groups(model.mesh)
    masked = None if laid is None or masks is None else mask_faces(len(model.mesh.faces), laid[0],
                                                                     close_up_masks(masks, close_up))
    centres, regions, region_groups = colour_regions(every_colours, every_faces, seed, groups, masked)
    span = 1 if masked is None else int(masked.max(initial=0)) + 1
    if not (region_groups // span).any():  # one piece group (PIECE_SHARE): every face of it
        groups = np.zeros_like(groups)
    if masked is not None:
        groups = masked_groups(groups, masked, masked)
    views_saved(folder, model, (angles, faces, colours), regions)
    texels = texel_regions(model, centres, (groups, region_groups))
    if texels and laid is not None:
        texels.update(close_up_texels(model, (close_up, camera_file), laid[0], regions[CLOSE_UP], texels))
    if texels:  # a model with no picture (a colour factor alone) has no texels
        np.savez_compressed(folder / "texels.npz", **texels)
    if laid is not None:
        close_up_saved(folder, laid, regions[CLOSE_UP])
    close_up_written(folder, close_up, faces, colours)
    side = measure_side(model.mesh)
    measured = {view: cast.cast(model.mesh, turn, side)[0] for view, turn in {**cast.BASE, **cast.CANDIDATES}.items()}
    return {**view_record(model, {view: measured[view] for view in angles}, angles, close_up),
            "reachable_share": round(seen_share(model.mesh, measured.values()), 3),
            "paint_faces": paint_faces(model_file),
            "regions": region_records(centres, every_colours, regions,
                                      None if laid is None else close_up_shown(every_faces, regions, laid,
                                                                               len(centres))),
            "close_up_laid": laid_record,
            "masks": None if masked is None else {"given": len(list(pathlib.Path(masks).glob("*.png"))),
                                                  "kept": int(masked.max(initial=0)),
                                                  "faces": int((masked > 0).sum())}}


def files(place):
    """route_data.shape_files and each own close-up's camera (`camera <take>`, as route_data.parts_files names them),
    the close-up laid on the model through it (laid_close_up). The table sets it (score/stages `close_up_laid`), so
    no row that imports route_data moves."""
    cameras = {name: path for name, path in route_data.parts_files(place).items() if name.startswith("camera ")}
    return {**route_data.shape_files(place), **cameras}


def make_views(inputs, out, seed, params):
    """Every take's views; views.json records each, or that it has no raw model. A take a batch gap of the prop route
    names (its close-up or its Pixal3D job failed) is left out, its gap carried on in batch-gaps.json."""
    _, takes = route_data.takes_written(out, inputs, params)
    carried = batch_gaps.of(inputs)
    batch_gaps.write(out, carried)
    found = {}
    for take in [take for take in takes if take not in batch_gaps.objects(carried)]:
        model_file = inputs.get(f"model {take}")
        if model_file is None:
            found[take] = {"model": None}
            continue
        record = view_take(model_file, inputs.get(f"close-up {take}"), inputs.get(f"camera {take}"), out / take,
                           seed, inputs.get(f"masks {take}"))
        found[take] = {"model": pathlib.Path(model_file).name, **record}
    (out / "views.json").write_text(json.dumps(found, indent=1))


def views_faults(folder):
    return [] if (folder / "views.json").exists() and (folder / "takes.json").exists() else ["no views.json"]


def take_faults(take, record):
    """What stops one take's views: no raw model, faces other than the paint's, a view seeing nothing, too little
    seen."""
    if record.get("model") is None:
        return [f"{take}: no raw take here (the paint lays the raw take on its finished model)"]
    if record["paint_faces"] != record["faces"]:
        return [f"{take}: {record['faces']} faces cast, the paint loads {record['paint_faces']}: the parts would not "
                "land on its faces"]
    if record["views_empty"]:
        return [f"{take}: views seeing nothing: {', '.join(record['views_empty'])}"]
    reachable = record.get("reachable_share", 1.0)
    if record["seen_share"] < SEEN_LEAST * reachable:
        return [f"{take}: the views see {record['seen_share']:.0%} of its area, of {reachable:.0%} any angle sees"]
    return []


def all_gapped(output):
    """The names of the batch gaps this output carries when they leave out every take the row worked on (takes.json),
    else []: a row with none of its takes to cast has nothing to fail, its gaps carried on."""
    written = json.loads((output / "takes.json").read_text())["takes"]
    carried = batch_gaps.read([output])
    left_out = batch_gaps.objects(carried)
    if not written or not all(take in left_out for take in written):
        return []
    return [entry["name"] for entry in carried if set(entry["objects"]) & set(written)]


def judge_views(output, inputs, evidence):
    """Every take has its raw model with the paint's faces, every view sees it and the views together see SEEN_LEAST of
    the area any angle sees; the views a take needed and its unseen faces as measures."""
    found = json.loads((output / "views.json").read_text())
    failing = [fault for take, record in found.items() for fault in take_faults(take, record)]
    gapped = all_gapped(output)
    if not found and gapped:
        return checks.Verdict("views cast", checks.PASS, f"every take left out by its batch gap, carried on: "
                              f"{'; '.join(gapped)}", {"failing": 0, "left_out": len(gapped)}, {"failing": "lower"})
    if not found:
        place = json.loads((output / "takes.json").read_text())["place"]
        failing.append(f"{place}: no take to work on (the object filter keeps none of its takes)")
    cast_takes = [record for record in found.values() if record.get("model")]
    stand_ins = sum(record.get("close_up") == route_data.STAND_IN for record in cast_takes)
    return gates.verdict("views cast", failing, max(len(found), 1), "takes not cast",
                         {"stand_in_close_ups": stand_ins,
                          "views_most": max((len(record["views"]) for record in cast_takes), default=0),
                          "unseen_faces": sum(record["unseen_faces"] for record in cast_takes)})
