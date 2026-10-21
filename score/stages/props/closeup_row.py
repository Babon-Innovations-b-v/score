"""The prop route's first rows: the objects' inputs (free) and their close-ups (paid, Nano Banana Pro).

props-inputs@<place> writes rows.json, one row per object of the place's prop data in the close-up stage's form
(tools/props/closeup/stage.py: id, scene, words, size, concept picture, box), with the close-up already drawn where
the data names one, its route, take and the model layer that handed it (the shared loop's hand-in, #41). Its gate,
`boxed or drawn`, is the close-up stage's own box gate (stage.gate_problems): every object without a drawn close-up
needs a box the gate passes, so nothing is drawn of the wrong thing.

closeup@<place> draws every missing close-up with Nano Banana Pro through tools/props/closeup/pro.py (google_spend
prices each call): first from the crop alone, then, for what still fails, with the whole concept beside (the stage's
PRO_TAKES). A drawn close-up is taken as it is, set on the stage's grey. Its gate, `close-up`, is the shape check's
measured half (check.measured_faults: plain border, one object filling the frame, the row's proportions), free and
re-measured on the stored pictures, so Pixal3D is never paid for a close-up that fails it. An object every Pro take
failed keeps none: its prop route failed there, a batch gap (batch-gaps.json, score/stages/batch_gaps.py) the rows
after it leave out. The judge's half (a model on rented cards) is not run here.
"""
import dataclasses
import json
import shutil

from PIL import Image

import score.stages.batch_gaps as batch_gaps
import score.stages.props.prop_data as prop_data  # the module, not the package: the table stays out of the code
from score.stages.surfaces.surface_gates import verdict

GREY = (205, 205, 205)
# pro.DOLLARS_A_PICTURE, written here: pro is imported only inside the rows' functions (prop_data.tools).
DOLLARS_A_PICTURE = 0.134
# Up to two Pro pictures an object (PRO_TAKES), counted one dollar a euro (google_spend); the hub's 51 boxed objects.
EUROS = round(51 * 2 * DOLLARS_A_PICTURE, 2)


def closeup_tools():
    """The close-up stage (tools/props/closeup/stage.py) and its shape check, imported under prop_data.tools."""
    with prop_data.tools("props/closeup", "props", "props/cloud"):
        import check
        import stage
    return stage, check


def layer_of(entry):
    """The model layer that handed a prop data object to the shared loop (score/stages/shapes_first): its `layer`,
    else "objects", the layer every prop data file was first written for."""
    return entry.get("layer", "objects")


def inventory_rows(inventory, wanted):
    """The close-up stage's rows of `wanted` objects: name, size, concept view and box from the inventory (the view's
    picture is filled in by make_inputs, from the row's declared file)."""
    return [{"id": row["id"], "scene": inventory["scene"], "words": row["name"], "size": row["size"],
             "view": row.get("view"), "box": row.get("box")}
            for row in inventory["rows"] if row["id"] in wanted]


def make_inputs(inputs, out, seed, params):
    """rows.json: every object of the place's prop data as a close-up row, its drawn close-up where named."""
    record = prop_data.record_at(inputs["props"])
    rows = inventory_rows(json.loads(inputs["inventory"].read_text()), record["objects"])
    for row in rows:
        row["concept"] = str(inputs[f"view {row['view']}"]) if row["view"] else None
        named = inputs.get(f"close-up {row['id']}")
        row["drawn"] = str(named) if named else None
        entry = record["objects"][row["id"]]
        row.update(route=entry["route"], take=entry.get("take"), layer=layer_of(entry),
                   failures=entry.get("failures", {}))
    missing = sorted(set(record["objects"]) - {row["id"] for row in rows})
    (out / "rows.json").write_text(json.dumps({"rows": rows, "not_in_inventory": missing}, indent=1))


def inputs_faults(folder):
    return [] if (folder / "rows.json").exists() else ["no rows.json"]


def designed_inventory(inputs):
    """A designed place's hand-in as the box gate reads it (its views' pictures the declared files), else None: the
    gate reads the scene's own inventory file."""
    found = json.loads(inputs["inventory"].read_text())
    if "objects" not in found:
        return None
    views = [{**view, "picture": str(inputs[f"view {view['id']}"])} for view in found["plan"]["views"]]
    return {**found, "plan": {**found["plan"], "views": views}}


def judge_inputs(output, inputs, evidence):
    """Every object is an inventory row, and has a drawn close-up or a box the close-up stage's box gate passes."""
    found = json.loads((output / "rows.json").read_text())
    failing = [f"{row}: on no inventory row" for row in found["not_in_inventory"]]
    to_draw = [row for row in found["rows"] if not row["drawn"]]
    failing += [f"{row['id']}: no close-up and no box" for row in to_draw if not row["box"]]
    stage, _ = closeup_tools()
    with prop_data.tools("props/scene"):  # the box gate puts its folder on the path when it runs
        failing += stage.gate_problems([row for row in to_draw if row["box"]], designed_inventory(inputs))
    return verdict("boxed or drawn", failing, len(found["rows"]) + len(found["not_in_inventory"]), "objects")


def taken_as_drawn(row, out):
    """A drawn close-up into closeups/<id>.png, on the stage's grey where it was cut out."""
    picture = Image.open(row["drawn"])
    if picture.mode == "RGBA":
        picture = Image.alpha_composite(Image.new("RGBA", picture.size, GREY + (255,)), picture)
    picture.convert("RGB").save(out / "closeups" / f"{row['id']}.png")


def measured(path, row):
    """The shape check's measured faults of one close-up at its row's size; a row with no measured size (the people
    line's looks, #41) is named, never measured against a made-up box."""
    if row["size"] is None:
        return ["no measured size: its proportions held to none"]
    _, check = closeup_tools()
    return check.measured_faults(check.measure(path, row["size"]))


def draw_missing(rows, out):
    """Pro's close-ups of the rows with none: each take of PRO_TAKES for what the takes before it failed; {id: take
    record}."""
    stage, _ = closeup_tools()
    stage.make_crops(rows, out)
    failed, found = {row["id"] for row in rows}, {}
    for take in stage.PRO_TAKES:
        if not failed:
            break
        with prop_data.tools("props/closeup", "props", "props/cloud"):  # Pro's key is read through secret_store
            stage.draw_with_pro(rows, out, failed, take)
        for row in rows:
            if row["id"] in failed:
                picture = out / take / f"{row['id']}.png"
                faults = measured(picture, row) if picture.exists() else [f"Pro gave no {take} picture"]
                found.setdefault(row["id"], {})[take] = faults
        failed = {row_id for row_id in failed if found[row_id][take]}
    return found


def make_closeups(inputs, out, seed, params):
    """closeups/<id>.png for every object (drawn ones as they are, the rest by Pro) and closeups.json."""
    rows = json.loads((inputs["props-inputs"] / "rows.json").read_text())["rows"]
    (out / "closeups").mkdir(parents=True)
    for row in rows:
        if row["drawn"]:
            taken_as_drawn(row, out)
    takes = draw_missing([row for row in rows if not row["drawn"]], out)
    record = {}
    for row in rows:
        tried = takes.get(row["id"], {})
        passed = next((take for take, faults in tried.items() if not faults), None)
        if passed:
            shutil.copy(out / passed / f"{row['id']}.png", out / "closeups" / f"{row['id']}.png")
        record[row["id"]] = {"size": row["size"], "drawn_by": "given" if row["drawn"] else passed,
                             "takes": tried, "pro_pictures": sum((out / take / f"{row['id']}.png").exists()
                                                                 for take in tried)}
    batch_gaps.write(out, [batch_gaps.gap(f"{row['id']}: no close-up passed", "closeup", "close-up",
                                          (row["id"], row.get("take")),
                                          [f"{take}: {', '.join(faults)}"
                                           for take, faults in record[row["id"]]["takes"].items()],
                                          "every Pro take failed the shape check's measured half")
                           for row in rows if not row["drawn"] and not record[row["id"]]["drawn_by"]])
    pictures = sum(entry["pro_pictures"] for entry in record.values())
    (out / "closeups.json").write_text(json.dumps({"objects": record, "pro_pictures": pictures,
                                                   "pro_dollars": round(pictures * DOLLARS_A_PICTURE, 3)},
                                                  indent=1))


def closeups_faults(folder):
    return [] if (folder / "closeups.json").exists() else ["no closeups.json"]


def judge_closeups(output, inputs, evidence):
    """Every close-up kept passes the shape check's measured half, measured again here. An object every Pro take
    failed has none kept: its prop route failed at its close-up, it goes to code (the likeness row finds no model for
    it, compare.py drops its take), and it is named here, never failed: one such object must not stop the others."""
    found = json.loads((output / "closeups.json").read_text())["objects"]
    failing, handed = [], []
    for row, entry in sorted(found.items()):
        picture = output / "closeups" / f"{row}.png"
        if not picture.exists():
            handed.append(f"{row}: no close-up passed, to code")
            continue
        failing += [f"{row}: {fault}" for fault in measured(picture, entry)]
    found_verdict = verdict("close-up", failing, len(found), "close-ups faulted", {"to code": len(handed)})
    return dataclasses.replace(found_verdict, findings=(*found_verdict.findings, *handed[:40]))
