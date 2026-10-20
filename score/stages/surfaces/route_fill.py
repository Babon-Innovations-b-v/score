"""The finish route's fill row (free, on this PC's processor): each part takes its finish's library surface with
the list's settings, and the model is drawn again from every view in those surfaces' palette colours. The drawing is
flat library colour only, shaded by angle: no wear, bump or pattern (that needs the bake, in the cloud). The settings
are this row's output; a tweak is the recheck row's output; no materials.json variant is ever edited.

The free colour check: each finish's colour where its faces show the model's own texture (the median of their
pixels over every view, CIELAB) against its token's colour, within finish_parts.COLOUR_DELTA_E (CIE76, set on round
4's six models); glass, glow, lamp light and print keep their own colour (finish_parts.OWN_COLOUR, owner #8).

Output per take: <take>/finish.npy (finish per face), <take>/filled-<view>.png; fill.json per take: each finish's
surface, settings, sRGB colour, seen and filled CIELAB and their distance. Gate "every part filled": every listed
take's faces each have a library surface with settings.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402


def finish_per_face(groups, finishes, count):
    """Each face's finish (index into `finishes`) from its colour group (`count` groups, some perhaps holding no
    face after the vote); -1 for a group no finish holds."""
    finish_of_group = np.full(count, -1)
    for number, entry in enumerate(finishes):
        finish_of_group[entry["groups"]] = number
    return finish_of_group[groups]


def token_srgb(token):
    """A palette token's colour, sRGB 0-255."""
    import labels
    import library
    linear = np.asarray(library.token_colours()[token], dtype=float)
    return np.clip(labels.srgb(linear) * 255, 0, 255).round().astype(np.uint8)


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


def colour_record(entry, seen, families):
    """One finish's colour check: its seen and filled CIELAB, their distance, and whether it is judged by its own
    colour (glass, glow, light, print)."""
    srgb = token_srgb(entry["settings"]["token"])
    filled = cast.lab_of(srgb[None])[0]
    own = families.get(entry["surface"]) in finish_parts.OWN_COLOUR
    apart = None if seen is None else round(float(np.linalg.norm(filled - seen)), 1)
    return {"srgb": srgb.tolist(), "filled_lab": [round(float(value), 1) for value in filled],
            "seen_lab": None if seen is None else [round(float(value), 1) for value in seen], "delta_e": apart,
            "own_colour": own,
            "colour_fits": own or apart is None or apart <= finish_parts.COLOUR_DELTA_E}


def drawn(views, finish_of, finishes, out, name):
    """The filled model from every view into `out` (<name>-<view>.png): each face its finish's colour."""
    import route_split
    mesh = route_split.model_of(views)
    faces = dict(np.load(views / "faces.npz"))
    colours = np.array([entry["srgb"] for entry in finishes] + [[0, 0, 0]], dtype=np.uint8)
    for view, found in faces.items():
        cast.picture(cast.face_painted(colours[finish_of], found), found,
                     cast.shading(mesh, found, view)).save(out / f"{name}-{view}.png")


def filled(views, finish_of, finishes, families):
    """The finishes with their colour check (colour_record)."""
    seen = seen_colours(views, finish_of, len(finishes))
    return [{**entry, **colour_record(entry, colour, families)} for entry, colour in zip(finishes, seen)]


def fill_take(folders, finishes, families, count):
    """One take filled into folders["out"]: finish.npy, its pictures; its finishes with their colour check."""
    finish_of = finish_per_face(np.load(folders["split"] / "groups.npy").astype(int), finishes, count)
    folders["out"].mkdir(parents=True)
    np.save(folders["out"] / "finish.npy", finish_of.astype(np.int16))
    found = filled(folders["views"], finish_of, finishes, families)
    drawn(folders["views"], finish_of, found, folders["out"], "filled")
    return found


def make_fill(inputs, out, seed, params):
    """Every listed take filled; fill.json."""
    views, split = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-split"])
    listed = pathlib.Path(inputs["finish-route-list"])
    _, takes = route_data.takes_written(out, inputs, params)
    found = {}
    for take, record in json.loads((split / "groups.json").read_text()).items():
        finishes = json.loads((listed / f"{take}.json").read_text())["finishes"]
        families = {name: spec.get("family") for name, spec in finish_parts.take_surfaces(takes[take]).items()}
        found[take] = fill_take({"views": views / take, "split": split / take, "out": out / take}, finishes, families,
                                len(record["groups"]))
    (out / "fill.json").write_text(json.dumps(found, indent=1))


def fill_faults(folder):
    return [] if (folder / "fill.json").exists() else ["no fill.json"]


def judge_fill(output, inputs, evidence):
    """Every listed take filled, every face one finish with a library surface and settings; the finishes off their
    seen colour as a measure (the recheck row judges them)."""
    found = json.loads((output / "fill.json").read_text())
    failing = [f"{take}: faces with no finish" for take in found if (np.load(output / take / "finish.npy") < 0).any()]
    failing += [f"{take}: {entry['finish']}: no surface or settings" for take, finishes in found.items()
                for entry in finishes if not entry.get("surface") or not entry.get("settings")]
    off = sum(not entry["colour_fits"] for finishes in found.values() for entry in finishes)
    return gates.verdict("every part filled", failing, len(found), "takes not filled", {"off_colour": off})
