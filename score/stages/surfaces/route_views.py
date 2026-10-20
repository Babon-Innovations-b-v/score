"""The finish route's views row (free, on this PC's processor, no Blender): each take's raw model rendered from every
angle it needs in one go, and its colour regions, ready for the one finish list ask.

The angles (`covering_views`, the free coverage check before the render): the BASE views (the close-up's front, the
back, both sides, the top, the bottom), then from CANDIDATES the one that sees the most area no chosen view sees,
again, until every face is seen, no candidate sees one more, or MOST_VIEWS. A face no view can see (inside the model)
is counted (`unseen_faces`, `unseen_share`); the split gives it its nearest seen face's finish.

Each view: the face under each pixel and its colour from the model's own texture (route_cast). The texture is only
measured, never painted: every finish is a library surface. Its regions: every seen pixel's CIELAB colour in k-means'
groups (at most REGIONS, fitted on SAMPLE pixels with the node's seed; colours only split, they name nothing), the
same groups in every view, so the list's answer labels each region of each view with a finish.

Output per take: <take>/model.npz (the welded, normalised vertices and faces every later row reads, so the face ids
agree), <take>/faces.npz, colours.npz and regions.npz (one array a view), <take>/<view>.png (the texture, shaded by
angle), <take>/regions-<view>.png (each region in its label colour, finish_ask.LABELS), <take>/close-up.png (the take's
own close-up, else the stand-in: the front view unshaded, route_data.STAND_IN). views.json: per take its model, its
views' angles, its faces and how many the paint's loading finds, the share of its area seen, its regions (CIELAB,
sRGB, share of the seen pixels) and its close-up's source.
Gate "views cast": every take has its raw model, loaded with the faces the paint loads, every view sees it and the
views together see SEEN_LEAST of its area.
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

SEEN_LEAST = 0.5  # a take whose views together see under this share of its area fails: the cast missed the model
MOST_VIEWS = 16  # the base views and the coverage check's extras together
REGIONS = len(finish_ask.LABELS)  # one label colour a region in the list's pictures
SAMPLE = 60000  # the pixels k-means is fitted on, drawn with the node's seed


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


def colour_regions(colours, faces, seed):
    """(the regions' CIELAB centres, each view's region per pixel, -1 off the model): every seen pixel's colour in
    k-means' groups, fitted on SAMPLE of them; groups no pixel falls in are dropped."""
    from scipy.cluster.vq import kmeans2, vq
    seen = {view: cast.lab_of(colours[view][faces[view] >= 0]) for view in faces}
    every = np.concatenate(list(seen.values()))
    draw = np.random.default_rng(seed).choice(len(every), min(SAMPLE, len(every)), replace=False)
    distinct = len(np.unique(every[draw].round(1), axis=0))  # fewer colours than REGIONS: one region each
    centres, _ = kmeans2(every[draw], min(REGIONS, distinct), seed=seed, minit="++")
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


def view_record(model, faces, angles, close_up):
    """A take's record: its views' angles, its faces, the share of its area some view sees, its unseen faces, its
    empty views, its close-up's source."""
    seen = np.unique(np.concatenate([found[found >= 0] for found in faces.values()]))
    area = model.mesh.area_faces
    return {"views": angles, "faces": len(model.mesh.faces), "seen_share": round(float(area[seen].sum() / area.sum()), 3),
            "unseen_faces": len(model.mesh.faces) - len(seen),
            "unseen_share": round(float(1 - area[seen].sum() / area.sum()), 4),
            "views_empty": [view for view, found in faces.items() if not (found >= 0).any()],
            "close_up": "own" if close_up is not None else route_data.STAND_IN}


def view_take(model_file, close_up, folder, seed):
    """One take's views and regions into `folder`; its record (view_record, its regions, the paint's face count)."""
    model = cast.loaded(model_file)
    angles, casts = covering_views(model.mesh)
    faces = {view: found for view, (found, _) in casts.items()}
    colours = {view: cast.texture_colours(model, found, points) for view, (found, points) in casts.items()}
    centres, regions = colour_regions(colours, faces, seed)
    views_saved(folder, model, (angles, faces, colours), regions)
    close_up_written(folder, close_up, faces, colours)
    return {**view_record(model, faces, angles, close_up), "paint_faces": paint_faces(model_file),
            "regions": region_records(centres, colours, regions)}


def make_views(inputs, out, seed, params):
    """Every take's views; views.json records each, or that it has no raw model."""
    _, takes = route_data.takes_written(out, inputs, params)
    found = {}
    for take in takes:
        model_file = inputs.get(f"model {take}")
        if model_file is None:
            found[take] = {"model": None}
            continue
        record = view_take(model_file, inputs.get(f"close-up {take}"), out / take, seed)
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
    if record["seen_share"] < SEEN_LEAST:
        return [f"{take}: the views see {record['seen_share']:.0%} of its area"]
    return []


def judge_views(output, inputs, evidence):
    """Every take has its raw model with the paint's faces, every view sees it and the views together see SEEN_LEAST of
    its area; the views a take needed and its unseen faces as measures."""
    found = json.loads((output / "views.json").read_text())
    failing = [fault for take, record in found.items() for fault in take_faults(take, record)]
    if not found:
        place = json.loads((output / "takes.json").read_text())["place"]
        failing.append(f"{place}: no take to work on (the object filter keeps none of its takes)")
    cast_takes = [record for record in found.values() if record.get("model")]
    stand_ins = sum(record.get("close_up") == route_data.STAND_IN for record in cast_takes)
    return gates.verdict("views cast", failing, max(len(found), 1), "takes not cast",
                         {"stand_in_close_ups": stand_ins,
                          "views_most": max((len(record["views"]) for record in cast_takes), default=0),
                          "unseen_faces": sum(record["unseen_faces"] for record in cast_takes)})
