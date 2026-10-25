"""likeness@<place>: every object of the place's prop data, made by either route, held to its close-up and to the
model checks as they exist; the row that decides each object's route.

A prop object's model is its take's bake (surfaces-bake, after the surface line's split, library paint and the bake
that makes it solid; it runs only once surfaces-check, the paint's check, passed); a code object's, or a prop object
moved to `fallback` after failing, is its code build. Each is scored against its close-up (closeup@<place>) and its
checks written to likeness.json; an object that fails any goes to code (prop route), or to a new builder (code).

The gates, each failing an object by name:
- `outline`: likeness.OUTLINE_LEAST on the best of eight ways round (likeness.py, set on the hub's accepted models).
- `likeness`: DINOv2 on the best way's silhouette, at the least likeness likeness-calibration@<place> set on the
  place's accepted models; its evidence, the pairs' scores, is gathered on a rented machine (similar.py, paid). A
  designed place (its hand-in an approved design's, prepare/handin.py) names no accepted models, so no calibration
  applies to it: its scores are measured and shown, never judged, and `outline` holds its likeness (#10; the accepted
  set the least was first set on went with the old disk, so a calibration for it is the owner's to name).
- `close-up parts present`: a prop model's parts (surfaces-parts) own every finish its close-up's list names; a code
  build is unknown (nothing measures its parts: the fittings' parts check went with the code fallback, 2026-10-22).
- `thin and in proportion`: tools/props/gates/model.py's check (thinnest wall, spread against the row's size).
- `lean`: tools/props/library/straight.py on a generated model of a kind that stands square, as it exists: code
  builds are not held to it. No rule names such a kind since the old kinds' details (data/library/details.json)
  retired with the old models (owner, 2026-10-21), so no model is held to it until one does.
Whether a model is closed is written as a measure only: 3 of the hub's 9 accepted generated models and 27 of its 83
accepted code builds are not (2026-10-12), so no gate as it exists fails an open model.
An object a batch gap names (score/stages/batch_gaps.py: a paid step of its take failed in the batch) still fails each
gate by name; the table moves those faults to complete, which lists the gaps from this output's batch-gaps.json (the
gaps of every row it read, each with its hand-in object and inventory rows).
"""
import dataclasses
import json
import pathlib

import numpy as np
from PIL import Image

from score import checks
import score.stages.batch_gaps as batch_gaps
import score.stages.props.calibration_row as calibration_row
import score.stages.props.likeness as likeness
import score.stages.props.prop_data as prop_data
from score.stages.surfaces.prop_env import PROPS_HOME
from score.stages.surfaces.surface_gates import guarded, unknown, verdict

# DINOv2 on a processor machine for a few hundred pairs (similar.py), rounded up.
LIKENESS_EUROS = 1.0


def files(place):
    """prop_data.likeness_files with each prop object's take's Pixal3D input (its close-up as Pixal3D cut it out,
    object_record) that is there: a take the batch made no model of has none, and its gate names the object (a batch
    gap the table moves). Here, not in prop_data.py, whose edits move the paid prop rows' code versions."""
    record = prop_data.record_at(prop_data.path_of(place)) if prop_data.applies(place) else {"objects": {}}
    return {**prop_data.likeness_files(place),
            **{f"pixal input {row}": "{home}/work/pixal/" + f"{entry['take']}.svviews/input.png"
               for row, entry in record["objects"].items() if entry["route"] == "prop"
               and (PROPS_HOME / "work/pixal" / f"{entry['take']}.svviews/input.png").exists()}}


def route_of(row, record):
    """Where an object's model comes from: "code" for a code object or a prop object moved to the fallback."""
    return "code" if record["objects"][row]["route"] == "code" or row in record.get("fallback", {}) else "prop"


def baked_models(bake):
    """{take: baked .gltf} from a surfaces-bake output (the first model baked of each take)."""
    found = {}
    for model, entry in sorted(json.loads((bake / "baked.json").read_text()).items()):
        found.setdefault(entry["parts"], bake / "made" / f"{model}.gltf")
    return found


def model_of(row, record, inputs, baked):
    """An object's model file, or None when its route made none."""
    if route_of(row, record) == "code":
        return inputs.get(f"code build {row}")
    return baked.get(record["objects"][row]["take"])


def finishes_missing(take, parts):
    """The finishes a take's close-up lists that no part of its model owns."""
    entry = parts["takes"].get(take)
    if entry is None:
        return None
    owned = {row["words"] for row in entry["parts"]}
    return [finish["finish"] for finish in entry["finishes"] if finish["finish"] not in owned]


def model_checks(path, size, kind, square):
    """model.py's check at the row's size (x wide, y tall, z deep), straight.py's for a square generated kind, and
    whether the mesh is closed."""
    import trimesh
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
        import straight
    points, triangles = likeness.gltf_mesh(path)
    mesh = trimesh.Trimesh(points, triangles, process=True)
    found = {"model_check": model_gate.check(kind, mesh, [size[0], size[2], size[1]]),
             "closed": bool(mesh.is_watertight)}
    if square:
        found["straight"] = straight.straightness(mesh)
    return found


def shading(pixels):
    """A close-up's backdrop colour at every pixel: a quadratic in x and y fitted to its border's pixels."""
    tall, wide = pixels.shape[:2]
    down, across = np.mgrid[0:tall, 0:wide] / max(tall, wide)
    terms = np.stack([np.ones_like(across), across, down, across * across, across * down, down * down], axis=-1)
    border = np.zeros((tall, wide), dtype=bool)
    border[0], border[-1], border[:, 0], border[:, -1] = True, True, True, True
    return terms @ np.linalg.lstsq(terms[border], pixels[border], rcond=None)[0]


def cut_out(closeup, folder):
    """The close-up with its object as alpha, which likeness.closeup_object reads before compare.closeup_mask: the
    mask taken on the close-up with its backdrop's shading levelled out. compare.closeup_mask's one border colour
    took a studio backdrop's darker corner for the object (engineroom's power core, 2026-10-15: border 176 to 229
    grey, the corner joined the core's foot and its outline fell from 0.76 to 0.46). A close-up already cut out is
    kept. A prop object's take's Pixal3D input, the same close-up as Pixal3D cut it out, is taken before this
    (object_record): on the galley's fold-down seat, 2026-10-15, white cushions on a white backdrop, this mask kept
    11% of the picture, the frame without its cushions, and the outline fell to 0.26."""
    picture = Image.open(closeup)
    if picture.mode == "RGBA" and np.asarray(picture)[..., 3].min() < 128:
        return closeup
    pixels = np.asarray(picture.convert("RGB"), dtype=np.float64)
    level = Image.fromarray(np.clip(pixels - shading(pixels) + 128, 0, 255).astype(np.uint8))
    mask = likeness.candidate().closeup_mask(level)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / closeup.name
    Image.fromarray(np.dstack([pixels.astype(np.uint8), np.where(mask, 255, 0).astype(np.uint8)])).save(path)
    return path


def pixal_cut(path, folder, row):
    """A prop object's close-up as its take's Pixal3D input cut it out, its object made one piece with its holes filled
    as compare.closeup_mask makes every other cut (a rack's open frame stays one silhouette: storage's cargo rack, cut
    so, passed at 0.68; its open lattice measured 0.43 on bars a pixel apart)."""
    from scipy import ndimage
    picture = np.asarray(Image.open(path).convert("RGBA"))
    labels, count = ndimage.label(picture[..., 3] > 127)
    if count == 0:
        raise ValueError(f"{path}: Pixal3D's cut-out holds no object")
    largest = np.argmax(ndimage.sum(np.ones_like(labels), labels, index=range(1, count + 1))) + 1
    mask = ndimage.binary_fill_holes(labels == largest)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{row}.png"
    Image.fromarray(np.dstack([picture[..., :3], np.where(mask, 255, 0).astype(np.uint8)])).save(out)
    return out


def object_record(row, record, inputs, baked, parts, rows, square, cuts):
    """One object's route, model, outline (at the look-down its close-up was drawn at, for the size it was drawn at:
    tools/props/closeup/stage.py object_size), checks and missing parts; `rows`: the inventory's rows by id."""
    route = route_of(row, record)
    place = record["place"]
    found = {"route": route, "model": None}
    model = model_of(row, record, inputs, baked)
    closeup = inputs["closeup"] / "closeups" / f"{row}.png"
    if model is None or not pathlib.Path(model).exists() or not closeup.exists():
        return {**found, "missing": "no model" if closeup.exists() else "no close-up"}
    cut = inputs.get(f"pixal input {row}") if route == "prop" else None
    closeup = pixal_cut(cut, cuts, row) if cut is not None and pathlib.Path(cut).exists() else cut_out(closeup, cuts)
    kind = f"{place}_{row}"
    drawn = rows[row].get("read_size") or rows[row]["size"]
    found.update(model=str(model), closeup=str(closeup), **likeness.best_way(model, closeup, drawn),
                 **model_checks(model, rows[row]["size"], kind, route == "prop" and kind in square))
    # a code build's parts: None, unknown (nothing measures them since the code fallback's parts check went)
    found["parts_missing"] = finishes_missing(record["objects"][row]["take"], parts) if route == "prop" else None
    return found


def make_likeness(inputs, out, seed, params):
    """likeness.json (every object's record) and pairs.json (each best way's silhouette pair, for DINOv2)."""
    record = prop_data.record_at(inputs["props"])
    rows = {row["id"]: row for row in json.loads(inputs["inventory"].read_text())["rows"]}
    square = set()  # no rule names a kind that stands square since the old kinds' details retired (2026-10-21)
    prop = "surfaces-bake" in inputs
    baked = baked_models(inputs["surfaces-bake"]) if prop else {}
    parts = json.loads((inputs["surfaces-parts"] / "parts.json").read_text()) if prop else {"takes": {}}
    found = {row: object_record(row, record, inputs, baked, parts, rows, square, out / "cut")
             for row in sorted(prop_data.kept(record["objects"], params))}
    pairs = {row: likeness.write_pair(entry["model"], entry["closeup"], entry["way"], out / "pairs", row,
                                      entry["look_down"])
             for row, entry in found.items() if "way" in entry}
    (out / "likeness.json").write_text(json.dumps({"objects": found}, indent=1))
    (out / "pairs.json").write_text(json.dumps(pairs, indent=1))
    batch_gaps.write(out, [with_rows(entry, record) for entry in batch_gaps.of(inputs)])


def with_rows(entry, record):
    """A batch gap carried on with every object of the hand-in record its takes or rows name, and the inventory rows
    that object stands for, so the gates that name rows (this one's, complete's) find it."""
    named = set(entry["objects"])
    rows = [(row, *item.get("rows", ())) for row, item in record["objects"].items()
            if row in named or item.get("take") in named]
    return {**entry, "objects": sorted(named.union(*rows))}


def likeness_faults(folder):
    return [] if (folder / "likeness.json").exists() else ["no likeness.json"]


def objects(output):
    return json.loads((output / "likeness.json").read_text())["objects"]


# --- each object's faults by check: None when the check cannot tell ------------------------------------------------

def outline_faults(row, entry):
    if entry["outline"] < likeness.OUTLINE_LEAST:
        return [f"outline {entry['outline']:.3f} under {likeness.OUTLINE_LEAST}"]
    return []


def parts_faults(row, entry):
    missing = entry["parts_missing"]
    return None if missing is None else [f"misses {', '.join(missing)}"] if missing else []


def model_faults(row, entry):
    found = entry["model_check"]
    return [] if found["pass"] else [f"thinnest {found['thinnest']} m, spread {found['spread']}"]


def lean_faults(row, entry):
    return [] if "straight" not in entry or entry["straight"]["pass"] else ["leans or warps"]


def scored(scores, least):
    """DINOv2's faults on each object from its scores ({row: likeness}) at `least`; None for one not scored or no
    least."""
    def faults(row, entry):
        if least is None or row not in scores:
            return None
        return [f"likeness {scores[row]:.3f} under {least}"] if scores[row] < least else []
    return faults


FREE = {"outline": outline_faults, "close-up parts present": parts_faults, "thin and in proportion": model_faults,
        "lean": lean_faults}


def object_faults(found, faults_of):
    """{row: faults, or None when the check cannot tell}; an object with no model faults on every check."""
    return {row: ([entry["missing"]] if "missing" in entry else faults_of(row, entry)) for row, entry in found.items()}


def judged(name, found, faults):
    """The check's verdict: fail naming each object's faults, else unknown naming what it could not tell, else pass."""
    failing = [f"{row}: {fault} ({found[row]['route']} route)" for row, listed in sorted(faults.items()) if listed
               for fault in listed]
    untold = sorted(row for row, listed in faults.items() if listed is None)
    if untold and not failing:
        return unknown(name, f"cannot tell for {', '.join(untold)}")
    return verdict(name, failing + [f"{row}: cannot tell" for row in untold], len(found), "faults")


def free_judge(name):
    """The judge of one free check (FREE)."""
    def judge(output, inputs, evidence):
        found = objects(output)
        return judged(name, found, object_faults(found, FREE[name]))
    return judge


def judge_likeness(output, inputs, evidence):
    """Each best way's DINOv2 likeness ({row: score}, the gathered evidence) at least the calibration's least."""
    least = calibration_row.least(inputs.get("likeness-calibration"))
    if least is None and designed(inputs):
        return measured_only(json.loads(pathlib.Path(evidence).read_text()))
    if least is None:
        return unknown("likeness", "DINOv2's least likeness is not set: no accepted calibration of the place's "
                                   "accepted models (likeness-calibration)")
    found = objects(output)
    return judged("likeness", found,
                  object_faults(found, scored(json.loads(pathlib.Path(evidence).read_text()), least)))


def designed(inputs):
    """Whether the row's prop data is an approved design's hand-in (prepare/handin.py), which names no accepted
    models to calibrate on."""
    return "props" in inputs and bool(prop_data.record_at(inputs["props"]).get("approved"))


def measured_only(scores):
    """A designed place's likeness verdict: DINOv2's scores ({row: likeness}) measured and shown, not judged (module
    docstring)."""
    least = min(scores.values()) if scores else -1.0
    return checks.Verdict("likeness", checks.PASS,
                          f"measured, not judged: a designed place has no calibration of accepted models; DINOv2 "
                          f"scored {len(scores)} objects (least {least:.3f}), outline holds its likeness",
                          {"scored": len(scores), "least scored": round(least, 4)}, {},
                          tuple(f"{row}: likeness {score:.3f}" for row, score in sorted(scores.items())[:40]))


def stored_pairs(output):
    """pairs.json's pairs, each picture read from the output's own pairs/ folder: the paths it holds point into the
    folder the make ran in, removed once the output was stored (likeness@campgrounds, 2026-10-15: no likeness came
    back, the cairn's model picture missing)."""
    pairs = json.loads((output / "pairs.json").read_text())
    return {row: [str(output / "pairs" / pathlib.Path(picture).name) for picture in pair]
            for row, pair in pairs.items()}


def gather_likeness(output, inputs, folder):
    """DINOv2's score of every pair on a rented machine (similar.py): the evidence file."""
    with prop_data.tools("cloud", "props"):
        import similar
        similar.likeness(stored_pairs(output), folder / "likeness.json", "score likeness")
    return folder / "likeness.json"


def routes(output, scores=None, least=None):
    """{row: "prop" | "code" | "builder" | "unknown"}: where each object stands after its checks (DINOv2's scores at
    `least` included). A prop object that passed every check stays prop; one that failed any goes to code; a code
    object that failed needs a new builder; one a check could not tell for is unknown."""
    found = objects(output)
    per_check = [object_faults(found, faults_of) for faults_of in (*FREE.values(), scored(scores or {}, least))]
    found_routes = {}
    for row, entry in found.items():
        told = [faults[row] for faults in per_check]
        if any(told):
            found_routes[row] = {"prop": "code", "code": "builder"}[entry["route"]]
        else:
            found_routes[row] = "unknown" if None in told else entry["route"]
    return found_routes


CHECKS = (*(guarded(name, free_judge(name)) for name in FREE),
          dataclasses.replace(guarded("likeness", judge_likeness), evidence="DINOv2 scores (similar.py)"))
GATHERERS = {"likeness": (gather_likeness, LIKENESS_EUROS)}


