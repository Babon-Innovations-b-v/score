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
the list's answer labels each region of each view with a finish.

Output per take: <take>/model.npz (the welded, normalised vertices and faces every later row reads, so the face ids
agree), <take>/faces.npz, colours.npz and regions.npz (one array a view), <take>/<view>.png (the texture, shaded by
angle), <take>/regions-<view>.png (each region in its label colour, finish_ask.LABELS), <take>/close-up.png (the take's
own close-up, else the stand-in: the front view unshaded, route_data.STAND_IN); where the close-up is laid,
<take>/close-up.npz (its face per pixel and colours) and regions-close-up.png, its regions in regions.npz.
views.json: per take its model, its views' angles, its faces and how many the paint's loading finds, the share of its
area seen, its regions (CIELAB, sRGB, share of the seen pixels), its close-up's source and whether it was laid.
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
CLOSE_UP = "close-up"  # the close-up's own pixels laid on the model through its camera, a view of the regions
EDGE = 2  # a close-up pixel is kept only when those EDGE away on every side lie on the model in the cast and alpha


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


def merged_centres(every, centres):
    """`centres` with the groups of fewer than ACCENT_LEAST of `every`'s pixels dropped (their pixels go to the
    nearest group left), then the two nearest merged (weighed by their pixels) until REGIONS are left: shading steps
    of one colour lie close and merge first, a colour far from the rest keeps its own region however small."""
    from scipy.cluster.vq import vq
    counts = np.bincount(vq(every, centres)[0], minlength=len(centres)).astype(float)
    kept = counts >= min(ACCENT_LEAST, counts.max())
    centres, counts = centres[kept], counts[kept]
    while len(centres) > REGIONS:
        apart = np.linalg.norm(centres[:, None] - centres[None], axis=-1) + np.diag(np.full(len(centres), np.inf))
        first, second = np.unravel_index(apart.argmin(), apart.shape)
        centres[first] = (centres[first] * counts[first] + centres[second] * counts[second]) \
            / (counts[first] + counts[second])
        counts[first] += counts[second]
        centres, counts = np.delete(centres, second, axis=0), np.delete(counts, second)
    return centres


def colour_regions(colours, faces, seed):
    """(the regions' CIELAB centres, each view's region per pixel, -1 off the model): every seen pixel's colour in
    at most REGIONS groups of distinct colour (fine_centres merged, merged_centres); groups no pixel falls in are
    dropped."""
    from scipy.cluster.vq import vq
    seen = {view: cast.lab_of(colours[view][faces[view] >= 0]) for view in faces}
    every = np.concatenate(list(seen.values()))
    centres = merged_centres(every, fine_centres(every, seed))
    centres = centres[np.unique(vq(every, centres)[0])]
    per_pixel = {}
    for view, lab in seen.items():
        label = np.full(faces[view].shape, -1)
        label[faces[view] >= 0] = vq(lab, centres)[0]
        per_pixel[view] = label
    return centres, per_pixel


def region_records(centres, colours, per_pixel):
    """Each region's CIELAB centre, median sRGB 0-255 over its pixels in every view and share of the seen pixels."""
    seen = sum(int((label >= 0).sum()) for label in per_pixel.values())
    found = []
    for region, centre in enumerate(centres):
        pixels = np.concatenate([colours[view][per_pixel[view] == region] for view in colours])
        found.append({"region": region, "lab": [round(float(value), 1) for value in centre],
                      "srgb": np.median(pixels, axis=0).round().astype(int).tolist(),
                      "share": round(len(pixels) / max(seen, 1), 4)})
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


def view_take(model_file, close_up, camera_file, folder, seed):
    """One take's views and regions into `folder`, the close-up laid on the model one more view of the regions
    (laid_close_up) where it fits; its record (view_record, its regions, the paint's face count, the laid close-up)."""
    model = cast.loaded(model_file)
    angles, casts = covering_views(model.mesh)
    faces = {view: found for view, (found, _) in casts.items()}
    colours = {view: cast.texture_colours(model, found, points) for view, (found, points) in casts.items()}
    laid, laid_record = laid_close_up(model, close_up, camera_file)
    every_faces, every_colours = dict(faces), dict(colours)
    if laid is not None:
        every_faces[CLOSE_UP], every_colours[CLOSE_UP] = laid
    centres, regions = colour_regions(every_colours, every_faces, seed)
    views_saved(folder, model, (angles, faces, colours), regions)
    if laid is not None:
        close_up_saved(folder, laid, regions[CLOSE_UP])
    close_up_written(folder, close_up, faces, colours)
    side = measure_side(model.mesh)
    measured = {view: cast.cast(model.mesh, turn, side)[0] for view, turn in {**cast.BASE, **cast.CANDIDATES}.items()}
    return {**view_record(model, {view: measured[view] for view in angles}, angles, close_up),
            "reachable_share": round(seen_share(model.mesh, measured.values()), 3),
            "paint_faces": paint_faces(model_file),
            "regions": region_records(centres, every_colours, regions), "close_up_laid": laid_record}


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
                           seed)
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
