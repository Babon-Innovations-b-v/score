"""The motion row's moving rows whose objects only their `score:row` names (tagged_rows: the sea, laid by the terrain as
one water sheet, /square/Outside/water), each moved by its rule's library recipe (a body of water's ripple: ripple.py's
RECIPE), set on the motion row by the stage table (motion@square, 2026-11-10: the sea stood with
no object, and no writer made its ripple). Kept apart from the motion package, which other makers' code versions
hash: only the table's motion row reads this file, so its key moves and the motion output moves only at a place with
such a row (the square's sea, the stairwell's water).

    made(make)                     the make, then each row it left with no object whose rule a recipe makes, its
                                   objects found by their tags or names on the build with the made ground: its ripple
                                   keyed into layers/motion.usda and recorded in RECORD; moves.json stays as motion
                                   wrote it (the sound row reads it)
    judge_designed(output, ...)    shown_rows' `designed`, with a row RECORD moves by its objects no longer missing
    covered(judge)                 a `covered` gate, and every object of a row a recipe moves (by its score:row or
                                   its name) moved by it in the layer
"""
import functools
import json
import pathlib

import numpy as np

from score import checks
from score.stages import layer_base, row_kinds
from score.stages import motion
from score.stages.motion import from_design, ripple, shown_rows, tagged_rows

RECORD = "ripples.json"
# The moves a recipe makes of a moving row's rule (data/checks/row-kinds.json `motion.move`).
RECIPES = {"ripple": ripple.NAME}


def made(make):
    """A make that, once the motion make has run, keys the ripple of each row it left with no object (ripple_rows)."""
    @functools.wraps(make)
    def making(inputs, out, seed, params):
        make(inputs, out, seed, params)
        ripple_rows(inputs, out)
    return making


def ripple_rows(inputs, out):
    """The ripple of each row the made record left with no object whose rule a recipe makes, keyed into its layer and
    recorded in RECORD; nothing where there is none."""
    record = json.loads((pathlib.Path(out) / motion.RECORD).read_text())
    rows = recipe_rows(inputs, record)
    if not rows:
        return
    with tagged_rows.grounded(inputs) as source:
        stage, place = layer_base.opened(source), motion.place_of(inputs)
        found = [(row, path) for row in rows for path in sorted({*tagged_rows.objects(stage, place, row["id"]),
                                                                  *row_kinds.objects_of(stage, place, row["id"])})]
        made = rippled(inputs, out, stage, found, float(record["seconds"]))
    if made:
        (pathlib.Path(out) / RECORD).write_text(json.dumps({"place": place, "ripples": made}, indent=1))


def recipe_rows(inputs, record):
    """The rows the record names missing (no object of theirs by name) and leaves out by no gap, whose rule a library
    recipe makes (RECIPES)."""
    missing = {shown_rows.row_of(line) for line in record.get("missing", [])} - set(record.get("left_out", {}))
    kinds = row_kinds.table(inputs["row kinds"])
    return [row for row in row_kinds.rows_that(motion.read_json(inputs["design"]), "moves", kinds)
            if row["id"] in missing and from_design.rule_of(row, kinds)["move"] in RECIPES]


def rippled(inputs, out, stage, found, seconds):
    """Each tagged object's ripple keyed into the output's motion layer: [its RECORD entry]; none on a place whose
    body is unknown (no sky inputs: no pull to give its waves their lengths)."""
    from pxr import Sdf, UsdGeom
    body = motion.body_of(inputs)
    if body is None or not found:
        return []
    settings = ripple.RECIPE
    layer = Sdf.Layer.FindOrOpen(str(pathlib.Path(out) / motion.game_motion.LAYER))
    made = []
    for row, path in found:
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
        edges = ripple.longest_edges(points, mesh.GetFaceVertexIndicesAttr().Get())
        middle = (points.min(axis=0) + points.max(axis=0)) / 2.0
        waves = ripple.waves(settings, body["gravity"], seconds, -middle[[0, 2]])
        why = (f"{row['id']} ({row['row_kind']}, its rule's move {ripple.NAME}): the library's {ripple.NAME} "
               f"({ripple.LIBRARY}), {len(waves)} deep-water waves on {body['name']}'s pull of "
               f"{float(body['gravity']):g} m/s/s, its {path.rsplit('/', 1)[-1]} named by its score:row")
        ripple.write(layer, path, ripple.keyed(points, edges, waves, seconds, layer.timeCodesPerSecond, settings), why)
        made.append({"name": path.rsplit("/", 1)[-1], "prim": path, "row": row["id"], "recipe": ripple.NAME,
                     "library": ripple.LIBRARY, "seconds": seconds, "step": float(settings["step"]),
                     "waves": [{name: wave[name] for name in ("period", "height", "length", "heading")}
                               for wave in waves],
                     "carried": round(float(np.mean([ripple.carried(edges, wave["length"], settings).mean()
                                                     for wave in waves])), 4),
                     "from": why})
    layer.Save()
    return made


def ripples_of(output):
    """The output's RECORD entries, [] where it made none."""
    path = pathlib.Path(output) / RECORD
    return json.loads(path.read_text())["ripples"] if path.is_file() else []


def judge_designed(output, inputs, evidence):
    """shown_rows.judge_designed, with each missing row whose tagged objects RECORD ripples named as moved there."""
    verdict = shown_rows.judge_designed(output, inputs, evidence)
    rippled_rows = {entry["row"] for entry in ripples_of(output)}
    there = sorted({shown_rows.row_of(line) for line in verdict.findings} & rippled_rows)
    if not there:
        return verdict
    faults = tuple(line for line in verdict.findings if shown_rows.row_of(line) not in rippled_rows)
    reason = (f"{len(faults)} moving things stand on nothing of the inventory" if faults else
              f"{verdict.measures['named']} moving and standing things are each an object of an inventory row") + \
        f" ({', '.join(there)}: its objects named by their score:row, moved by the library's recipe)"
    return checks.Verdict("designed", checks.FAIL if faults else checks.PASS, reason,
                          {**verdict.measures, "missing": len(faults)}, verdict.better, faults)


def keyed_points(layer, path):
    """The distinct keys of a sheet's points in the output's motion layer: how many keys, and the most any point
    rises or falls between them (metres)."""
    from pxr import Sdf
    attribute = Sdf.Path(path).AppendProperty("points")
    times = layer.ListTimeSamplesForPath(attribute) if layer.GetAttributeAtPath(attribute) else []
    if len(times) < 2:
        return len(times), 0.0
    heights = np.stack([np.asarray(layer.QueryTimeSample(attribute, time), dtype=float)[:, 1] for time in times])
    return len(times), float((heights.max(axis=0) - heights.min(axis=0)).max())


def unrippled(output, inputs, stage, place):
    """The objects of every row whose rule a library recipe makes (RECIPES), by their score:row or their names on the
    build with the made ground, and the faults of those the layer does not move: one RECORD names no ripple of, or
    whose ripple keys its points still."""
    from pxr import Sdf
    kinds = row_kinds.table(inputs["row kinds"])
    rows = [row for row in row_kinds.rows_that(motion.read_json(inputs["design"]), "moves", kinds)
            if from_design.rule_of(row, kinds)["move"] in RECIPES]
    wanted = [(row["id"], path) for row in rows
              for path in sorted({*tagged_rows.objects(stage, place, row["id"]),
                                  *row_kinds.objects_of(stage, place, row["id"])})]
    entries = {entry["prim"]: entry for entry in ripples_of(output)}
    layer = Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / motion.game_motion.LAYER))
    faults = []
    for row, path in wanted:
        keys, reach = keyed_points(layer, path) if path in entries else (0, 0.0)
        if path not in entries:
            faults.append(f"{path} ({row}): its row's rule is a library recipe's, and no recipe moves it")
        elif reach <= 0.0:
            faults.append(f"{path} ({row}): its {entries[path]['recipe']} keys its points still ({keys} keys)")
    return wanted, faults


def covered(judge):
    """A `covered` gate (`judge`, judged on its own build) with, on the build with the made ground, every object of a
    row a library recipe moves held to be moved by it in the layer (unrippled)."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        return with_ripples(judge(output, inputs, evidence), output, inputs)
    return judged


def with_ripples(verdict, output, inputs):
    """A `covered` verdict with the faults of the recipe rows' objects the layer leaves still (unrippled)."""
    with tagged_rows.grounded(inputs) as source:
        wanted, faults = unrippled(output, inputs, layer_base.opened(source), motion.place_of(inputs))
    if not wanted:
        return verdict
    missing = (verdict.findings if verdict.answer == checks.FAIL else ()) + tuple(faults)
    reason = verdict.reason + (f"; {len(faults)} of {len(wanted)} objects of a recipe's rows stand unmoved"
                               if faults else f"; the {len(wanted)} objects of a recipe's rows move by it")
    return checks.Verdict("covered", checks.FAIL if missing else checks.PASS, reason,
                          {**verdict.measures, "tagged": len(wanted), "tagged moved": len(wanted) - len(faults)},
                          verdict.better, tuple(missing) or verdict.findings)
