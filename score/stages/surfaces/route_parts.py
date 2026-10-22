"""The finish route's parts row, `surfaces-parts` (free, on this PC's processor): the method's interface (PARTS in
__init__.py) written from the route's split, so the framework's rows (paint, bake, check) and every reader of the
parts (the likeness, the machines) take it as they took the finish-map method's.

Its finishes are the split's (route_split.FINISHES: the list's, each off what the views show given the palette token
nearest them). Each finish's surface is checked against its colour before the bake, free (finish_parts.checked_finishes, the same
check the finish-map method ran): its colour here is the median CIELAB of the model's own texture over its faces'
pixels in every view (route_views), never painted, only measured. A finish off its listed surface takes the nearest
surface of its family that fits, or one of the scene's own shell surfaces (palette_library.shell_surfaces: the variants
its surface library gives the shell laid from its locked plan); one no surface fits is marked off its colour with a
proposed surface, and the paint's gate "colour against the close-up" fails it by name. Each part takes its finish's
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
    checked = finish_parts.checked_finishes(entry, finishes, seen_colours(folders["views"], finish_of, len(finishes)),
                                            every, kit)
    folders["out"].mkdir(parents=True)
    np.save(folders["out"] / "parts.npy", part_of.astype(np.int32))
    np.save(folders["out"] / "colours.npy", np.full((len(mesh.faces), 3), np.nan, dtype=np.float32))
    rows = finish_parts.part_rows(mesh, part_of, finish_of, checked)
    for row in rows:
        row["settings"] = route_settings.applied(checked[part_finish(mesh, part_of, finish_of, row["part"])])
    return {"method": METHOD, "parts": rows, "judge_unknown": [], "finishes": checked,
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
        judged = split / take / route_split.FINISHES  # the split's, recoloured; the list's for one split before it
        finishes = (json.loads(judged.read_text()) if judged.exists()
                    else json.loads((listed / f"{take}.json").read_text())["finishes"])
        found[take] = parts_take({"views": views / take, "split": split / take, "out": out / take}, takes[take],
                                 finishes, (palette_library.take_surfaces(takes[take], palette), kit))
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
