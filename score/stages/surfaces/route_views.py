"""The finish route's views row (free, on this PC's processor, no Blender): each take's model ray cast from every
side and the close-up's direction (route_cast.VIEWS), the face under each pixel and its colour from the model's own
texture. The texture is only measured, never painted: every finish is a library surface.

Output per take: <take>/model.npz (the welded, normalised vertices and faces every later row reads, so the face ids
agree), <take>/faces.npz and <take>/colours.npz (one array a view), <take>/<view>.png (the texture, shaded by angle),
<take>/close-up.png (the take's own close-up, else the stand-in: the front view unshaded, route_data.STAND_IN).
views.json: per take its model's source, its close-up's, the faces and the share of the model's area seen.
Gate "views cast": every take has a model and every view sees it; a take with no model is named.
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402

SEEN_LEAST = 0.5  # a take whose views together see under this share of its area fails: the cast missed the model


def view_take(model_file, close_up, folder):
    """One take's views into `folder`; its record (faces, seen share, close-up source)."""
    model = cast.loaded(model_file)
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "model.npz", vertices=model.mesh.vertices.astype(np.float32),
                        faces=model.mesh.faces.astype(np.int32))
    faces, colours = {}, {}
    for view in cast.VIEWS:
        faces[view], points = cast.cast(model.mesh, view)
        colours[view] = cast.texture_colours(model, faces[view], points)
        cast.picture(colours[view], faces[view], cast.shading(model.mesh, faces[view], view)).save(folder / f"{view}.png")
    np.savez_compressed(folder / "faces.npz", **{view: found.astype(np.int32) for view, found in faces.items()})
    np.savez_compressed(folder / "colours.npz", **colours)
    if close_up is not None:
        shutil.copyfile(close_up, folder / "close-up.png")
    else:
        cast.picture(colours[cast.FRONT], faces[cast.FRONT]).save(folder / "close-up.png")
    seen = np.unique(np.concatenate([found[found >= 0] for found in faces.values()]))
    area = model.mesh.area_faces
    return {"faces": len(model.mesh.faces), "seen_share": round(float(area[seen].sum() / area.sum()), 3),
            "views_empty": [view for view, found in faces.items() if not (found >= 0).any()],
            "close_up": "own" if close_up is not None else route_data.STAND_IN}


def make_views(inputs, out, seed, params):
    """Every take's views; views.json records each, or that it has no model."""
    _, takes = route_data.takes_written(out, inputs, params)
    found = {}
    for take in takes:
        model_file = inputs.get(f"model {take}")
        if model_file is None:
            found[take] = {"model": None}
            continue
        record = view_take(model_file, inputs.get(f"close-up {take}"), out / take)
        found[take] = {"model": pathlib.Path(model_file).name, **record}
    (out / "views.json").write_text(json.dumps(found, indent=1))


def views_faults(folder):
    return [] if (folder / "views.json").exists() and (folder / "takes.json").exists() else ["no views.json"]


def judge_views(output, inputs, evidence):
    """Every take has a model, every view sees it and the views together see SEEN_LEAST of its area."""
    found = json.loads((output / "views.json").read_text())
    failing = []
    for take, record in found.items():
        if record.get("model") is None:
            failing.append(f"{take}: no model here (no raw take, and no released model of it on this machine)")
        elif record["views_empty"]:
            failing.append(f"{take}: views seeing nothing: {', '.join(record['views_empty'])}")
        elif record["seen_share"] < SEEN_LEAST:
            failing.append(f"{take}: the views see {record['seen_share']:.0%} of its area")
    if not found:
        place = json.loads((output / "takes.json").read_text())["place"]
        failing.append(f"{place}: no take to work on (the object filter keeps none of its takes)")
    stand_ins = sum(record.get("close_up") == route_data.STAND_IN for record in found.values())
    return gates.verdict("views cast", failing, max(len(found), 1), "takes not cast",
                         {"stand_in_close_ups": stand_ins})
