"""likeness@<place>: every object of the place's prop data, made by either route, held to its close-up and to the
model checks as they exist; the row that decides each object's route.

A prop object's model is its take's bake (surfaces-bake, after the surface line's split, library paint and the bake
that makes it solid; it runs only once surfaces-check, the paint's check, passed); a code object's, or a prop object
moved to `fallback` after failing, is its code build. Each is scored against its close-up (closeup@<place>) and its
checks written to likeness.json; an object that fails any goes to code (prop route), or to a new builder (code).

The gates, each failing an object by name:
- `outline`: likeness.OUTLINE_LEAST on the best of eight ways round (likeness.py, set on the hub's accepted models).
- `likeness`: DINOv2 on the best way's silhouette, at the least likeness likeness-calibration@<place> set on the
  place's accepted models; its evidence, the pairs' scores, is gathered on a rented machine (similar.py, paid).
- `close-up parts present`: a prop model's parts (surfaces-parts) own every finish its close-up's list names; a code
  build's fitting shows every part its close-up has (sorter.missing_parts, fittings.json); a plain kind (sorter.PLAIN)
  has no parts to show; any other code build is unknown (nothing measured its parts).
- `thin and in proportion`: tools/props/gates/model.py's check (thinnest wall, spread against the row's size).
- `lean`: tools/props/library/straight.py on a generated model of a kind that stands square (details.json `square`),
  as it exists: code builds are not held to it.
Whether a model is closed is written as a measure only: 3 of the hub's 9 accepted generated models and 27 of its 83
accepted code builds are not (2026-10-12), so no gate as it exists fails an open model.
"""
import dataclasses
import json
import pathlib

import score.stages.props.calibration_row as calibration_row
import score.stages.props.likeness as likeness
import score.stages.props.prop_data as prop_data
from score.stages.surfaces.surface_gates import guarded, unknown, verdict

# DINOv2 on a processor machine for a few hundred pairs (similar.py), rounded up.
LIKENESS_EUROS = 1.0


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


def code_parts_missing(place, row):
    """A code build's parts its close-up shows and it does not ([] for a plain kind); None when nothing measured."""
    with prop_data.tools("props/library"):
        import sorter
    if sorter.own_name(f"{place}_{row}") in sorter.PLAIN:
        return []
    entry = sorter.fittings().get(row)
    return None if entry is None else sorter.missing_parts(entry)


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


def object_record(row, record, inputs, baked, parts, sizes, square):
    """One object's route, model, outline, checks and missing parts."""
    route = route_of(row, record)
    place = record["place"]
    found = {"route": route, "model": None}
    model = model_of(row, record, inputs, baked)
    closeup = inputs["closeup"] / "closeups" / f"{row}.png"
    if model is None or not pathlib.Path(model).exists() or not closeup.exists():
        return {**found, "missing": "no model" if closeup.exists() else "no close-up"}
    kind = f"{place}_{row}"
    found.update(model=str(model), **likeness.best_way(model, closeup),
                 **model_checks(model, sizes[row], kind, route == "prop" and kind in square))
    found["parts_missing"] = (finishes_missing(record["objects"][row]["take"], parts) if route == "prop"
                              else code_parts_missing(place, row))
    return found


def make_likeness(inputs, out, seed, params):
    """likeness.json (every object's record) and pairs.json (each best way's silhouette pair, for DINOv2)."""
    record = prop_data.record_at(inputs["props"])
    sizes = {row["id"]: row["size"] for row in json.loads(inputs["inventory"].read_text())["rows"]}
    details = json.loads(inputs["details"].read_text())
    square = {kind for kind, entry in details.items() if isinstance(entry, dict) and entry.get("square")}
    prop = "surfaces-bake" in inputs
    baked = baked_models(inputs["surfaces-bake"]) if prop else {}
    parts = json.loads((inputs["surfaces-parts"] / "parts.json").read_text()) if prop else {"takes": {}}
    found = {row: object_record(row, record, inputs, baked, parts, sizes, square) for row in sorted(record["objects"])}
    pairs = {row: likeness.write_pair(entry["model"], inputs["closeup"] / "closeups" / f"{row}.png", entry["way"],
                                      out / "pairs", row)
             for row, entry in found.items() if "way" in entry}
    (out / "likeness.json").write_text(json.dumps({"objects": found}, indent=1))
    (out / "pairs.json").write_text(json.dumps(pairs, indent=1))


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
    if least is None:
        return unknown("likeness", "DINOv2's least likeness is not set: no accepted calibration of the place's "
                                   "accepted models (likeness-calibration)")
    found = objects(output)
    return judged("likeness", found,
                  object_faults(found, scored(json.loads(pathlib.Path(evidence).read_text()), least)))


def gather_likeness(output, inputs, folder):
    """DINOv2's score of every pair on a rented machine (similar.py): the evidence file."""
    with prop_data.tools("props/cloud", "props"):
        import similar
        similar.likeness(json.loads((output / "pairs.json").read_text()), folder / "likeness.json",
                         "score likeness")
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


