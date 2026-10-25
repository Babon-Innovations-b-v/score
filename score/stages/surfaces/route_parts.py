"""The finish route's parts row, `surfaces-parts` (free, on this PC's processor): the method's interface (PARTS in
__init__.py) written from the route's split, so the framework's rows (paint, bake, check) and every reader of the
parts (the likeness, the machines) take it as they took the finish-map method's.

Its finishes are the list's. Each finish's surface is checked against its colour in the close-up before the bake,
free (finish_parts.checked_finishes, the same check the finish-map method ran; the paper's "a finish's surface must
lie within dE 32 of its colour there"): its colour is read where the close-up shows it (`close_up_colours`: the
model cast through the close-up's own camera, each pixel taking the finish of the face under it), never the raw
model's texture, whose colours carry the picture's baked light. A take with no own close-up or camera, or whose cast
does not fit the close-up's outline (CLOSE_UP_FIT), is measured on its views' texture instead (`seen_colours`), named
so in its record (`colour_from`), as a stand-in close-up is. A finish off its listed surface takes the nearest
surface of its family that fits, or one of the scene's own shell surfaces (palette_library.shell_surfaces: the variants
its surface library gives the shell laid from its locked plan); one no surface fits is marked off its colour with a
proposed surface, and the paint's gate "colour against the close-up" fails it by name. The bake check holds each
baked part against the same close-up colour (bake_check.close_up_faults, its `measured_lab`). Each part takes its finish's
checked surface (finish_parts.part_rows), and the list's settings where its finish kept the surface the list named
(route_settings.applied: the bake paints and bakes the surface with them).

Output: parts.json (per take its method, parts (each with its finish's `settings` or None), finishes with the list's
settings and the check's measure; the takes left out and why), <take>/parts.npy (one part per face of the raw take,
the paint's face order), <take>/colours.npy (NaN: the paint joins parts on their surface alone). Gate "parts": every
take the split split has its parts.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import palette_library  # noqa: E402
import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import route_settings  # noqa: E402
import route_split  # noqa: E402
import surface_gates as gates  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402

METHOD = "finish-route"
# The close-up's camera is Pixal3D's (transforms.json beside its input picture: its distance and camera_angle_x),
# looking at the model's front (+Z, route_cast's front) in the model file's own frame. Measured 2026-10-25 on six raw
# takes of the earlier runs: the cast's outline met the close-up's own (its alpha) at IoU 0.93 to 0.975 on five and
# 0.685 on one; under CLOSE_UP_FIT the cast is not trusted to say which finish a pixel shows.
CLOSE_UP_FIT = 0.85
CLOSE_UP_SIDE = 512  # the cast's pixels across at most (the close-up's own, sampled)
EDGE = 2  # a pixel counts when those EDGE away on every side show its finish too, so no border mixes two finishes


def seen_colours(views, finish_of, count):
    """Each finish's median CIELAB colour over the pixels of its faces in every view of the model's texture, or None
    where no view shows it."""
    faces = dict(np.load(views / "faces.npz"))
    colours = dict(np.load(views / "colours.npz"))
    found = []
    for number in range(count):
        pixels = np.concatenate([colours[view][(faces[view] >= 0) & (finish_of[np.maximum(faces[view], 0)] == number)]
                                 for view in faces])
        found.append(np.median(cast.lab_of(pixels), axis=0) if len(pixels) else None)
    return found


def close_up_camera(camera_file):
    """(distance, horizontal field of view in radians) of the close-up's camera (Pixal3D's transforms.json)."""
    found = json.loads(pathlib.Path(camera_file).read_text())
    distance = float(np.linalg.norm(np.array(found["frames"][0]["transform_matrix"], dtype=float)[:3, 3]))
    return distance, float(found["camera_angle_x"])


def close_up_cast(model, camera, size):
    """(the face under each sampled pixel, -1 off the model; the pixels' rows; their columns) of a close-up `size`
    (width, height) seen by `camera` (close_up_camera), `model` a route_cast.Model (its faces normalised by its
    frame)."""
    distance, field = camera
    width, height = size
    step = max(1, -(-max(width, height) // CLOSE_UP_SIDE))
    columns, rows = np.meshgrid(np.arange(0, width, step), np.arange(0, height, step))
    focal = width / 2 / np.tan(field / 2)
    ways = np.stack([(columns + 0.5 - width / 2) / focal, -(rows + 0.5 - height / 2) / focal,
                     -np.ones(columns.shape)], axis=-1).reshape(-1, 3)
    ways /= np.linalg.norm(ways, axis=1, keepdims=True)
    middle, side = model.frame
    eye = (np.array([0.0, 0.0, distance]) - middle) / side
    hit_faces, hit_rays = model.mesh.ray.intersects_id(np.repeat(eye[None], len(ways), axis=0), ways,
                                                       multiple_hits=False)
    faces = np.full(len(ways), -1, dtype=np.int64)
    faces[hit_rays] = hit_faces
    return faces.reshape(columns.shape), rows, columns


def inner(finish_map):
    """The pixels whose neighbours EDGE away on every side show the same finish (-1: none)."""
    kept = finish_map >= 0
    for axis in (0, 1):
        for shift in (EDGE, -EDGE):
            kept &= np.roll(finish_map, shift, axis=axis) == finish_map
    return kept


def close_up_colours(model, camera_file, close_up, finish_of, count):
    """(each finish's median CIELAB colour in the close-up where it shows it (inner pixels the cast and the close-up's
    alpha share), None where it shows none; the cast's fit: its outline's IoU with the close-up's)."""
    from PIL import Image
    picture = np.asarray(Image.open(close_up).convert("RGBA"))
    faces, rows, columns = close_up_cast(model, close_up_camera(camera_file), (picture.shape[1], picture.shape[0]))
    sampled = picture[rows, columns]
    shown, hit = sampled[..., 3] > 127, faces >= 0
    fit = float((shown & hit).sum() / max((shown | hit).sum(), 1))
    finish_map = np.where(shown & hit, finish_of[np.maximum(faces, 0)], -1)
    kept = inner(finish_map)
    found = []
    for number in range(count):
        pixels = sampled[kept & (finish_map == number)][:, :3]
        found.append(np.median(cast.lab_of(pixels), axis=0) if len(pixels) else None)
    return found, round(fit, 3)


def finish_colours(folders, finish_of, count):
    """(each finish's colour, where it was read): the close-up's (close_up_colours) when the take has its own
    close-up and camera and the cast fits it, else its views' texture (seen_colours), with why."""
    if folders.get("close_up") and folders.get("camera"):
        found, fit = close_up_colours(cast.loaded(folders["model"]), folders["camera"], folders["close_up"],
                                      finish_of, count)
        if fit >= CLOSE_UP_FIT:
            return found, f"close-up (outline fit {fit})"
        why = f"views: the close-up's cast fits its outline at IoU {fit}, under {CLOSE_UP_FIT}"
    else:
        why = "views: no own close-up or camera"
    return seen_colours(folders["views"], finish_of, count), why


def part_finish(mesh, part_of, finish_of, part):
    """The finish a part takes, as finish_parts.part_rows chose it: the finish over most of its area."""
    members = part_of == part
    return int(np.bincount(finish_of[members], weights=mesh.area_faces[members]).argmax())


def parts_take(folders, entry, finishes, surfaces):
    """One take's parts into folders["out"]: parts.npy and colours.npy; its parts.json record. `surfaces`: the take's
    library surfaces (palette_library.take_surfaces) and the scene's shell surfaces (palette_library.shell_surfaces)."""
    finish_of = np.load(folders["split"] / "finish.npy").astype(int)
    part_of = np.load(folders["split"] / "parts.npy").astype(int)
    mesh = route_split.model_of(folders["views"])
    every, kit = surfaces
    colours, colour_from = finish_colours(folders, finish_of, len(finishes))
    checked = finish_parts.checked_finishes(entry, finishes, colours, every, kit)
    folders["out"].mkdir(parents=True)
    np.save(folders["out"] / "parts.npy", part_of.astype(np.int32))
    np.save(folders["out"] / "colours.npy", np.full((len(mesh.faces), 3), np.nan, dtype=np.float32))
    rows = finish_parts.part_rows(mesh, part_of, finish_of, checked)
    for row in rows:
        row["settings"] = route_settings.applied(checked[part_finish(mesh, part_of, finish_of, row["part"])])
    return {"method": METHOD, "parts": rows, "judge_unknown": [], "finishes": checked, "colour_from": colour_from,
            "measures": {"parts": len(rows), "off colour": sum(entry["by"] == "off its colour" for entry in checked)}}


def make_parts(inputs, out, seed, params):
    """Every split take's parts; parts.json, with the takes the split made gaps (or the list left out) as left
    out."""
    views, listed = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-list"])
    split = pathlib.Path(inputs["finish-route-split"])
    _, takes = route_data.takes_written(out, inputs, params)
    palette = palette_library.read(inputs)
    kit = palette_library.shell_surfaces(palette)
    split_takes = json.loads((split / "split.json").read_text())
    named = {take: entry["name"] for entry in batch_gaps.of(inputs) for take in entry["objects"]}
    found, left = {}, {}
    for take in takes:
        record = split_takes.get(take)
        if record is None or record["fault"]:
            left[take] = record["fault"] if record else named.get(take, "not split: no finish list")
            continue
        finishes = json.loads((listed / f"{take}.json").read_text())["finishes"]
        folders = {"views": views / take, "split": split / take, "out": out / take, "model": inputs.get(f"model {take}"),
                   "close_up": inputs.get(f"close-up {take}"), "camera": inputs.get(f"camera {take}")}
        found[take] = parts_take(folders, takes[take], finishes, (palette_library.take_surfaces(takes[take], palette), kit))
    (out / "parts.json").write_text(json.dumps({"takes": found, "left_out": left}, indent=1))


def judge_parts(output, inputs, evidence):
    """Every take the split split has its parts; the takes left out (gaps named by the rows before) and the
    finishes off their colour as measures."""
    found = json.loads((output / "parts.json").read_text())
    split = json.loads((pathlib.Path(inputs["finish-route-split"]) / "split.json").read_text())
    failing = [f"{take}: no parts" for take, record in split.items()
               if not record["fault"] and take not in found["takes"]]
    return gates.verdict("parts", failing, len(found["takes"]) + len(found["left_out"]), "takes", {
        "left_out": len(found["left_out"]),
        "off colour": sum(record["measures"]["off colour"] for record in found["takes"].values())})
