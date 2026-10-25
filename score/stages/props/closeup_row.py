"""The prop route's first rows: the objects' inputs (free) and their close-ups (paid, Nano Banana Pro).

props-inputs@<place> writes rows.json, one row per object of the place's prop data in the close-up stage's form
(tools/props/closeup/stage.py: id, scene, words, size, concept picture, box), with the close-up already drawn where
the data names one, its route, take and the model layer that handed it (the shared loop's hand-in, #41). Its gate,
`boxed or drawn`, is the close-up stage's own box gate (stage.gate_problems): every object without a drawn close-up
needs a box the gate passes, so nothing is drawn of the wrong thing.

closeup@<place> draws every missing close-up with Nano Banana Pro through tools/props/closeup/pro.py, a take's
close-ups as one Batch API job at half price (google_batch prices each answer): the first take, then up to three
retries, each worded more strictly and the later ones on their own seeds, for each picture the check rejected (the
stage's PRO_TAKES, owner 2026-10-24 and 2026-10-25). Every picture stays in Google's cache, keyed by its request, and
the check judges it apart: a take cached before is read back free and judged again first, so a picture that passes is
kept and only the rows none passed are drawn again (coordinator, 2026-10-25). A drawn close-up is taken as it is,
set on the stage's grey. Its gate, `close-up`, is the shape check's measured half (check.measured_faults: plain
border, one object filling the frame, the proportions of the object's own size, stage.object_size), free and
re-measured on the stored pictures, so Pixal3D is never
paid for a close-up that fails it. An object every Pro take failed keeps none: its prop route failed there, a batch
gap (batch-gaps.json, score/stages/batch_gaps.py) the rows after it leave out. The judge's half (a model on rented
cards) is not run here.
"""
import dataclasses
import json
import shutil

from PIL import Image

import score.stages.batch_gaps as batch_gaps
import score.stages.props.prop_data as prop_data  # the module, not the package: the table stays out of the code
from score.stages.surfaces.surface_gates import verdict

GREY = (205, 205, 205)
# pro.DOLLARS_A_PICTURE, written here: pro is imported only inside the rows' functions (prop_data.tools). Google's
# 2K price at the Batch API's half, as pro.draw asks (owner, 2026-10-24).
DOLLARS_A_PICTURE = 0.067
# Up to four Pro pictures an object (stage.PRO_TAKES), counted one dollar a euro (google_spend); the hub's 51 boxed
# objects.
EUROS = round(51 * 4 * DOLLARS_A_PICTURE, 2)

def closeup_tools():
    """The close-up stage (tools/props/closeup/stage.py) and its shape check, imported under prop_data.tools."""
    with prop_data.tools("props/closeup", "props", "cloud"):
        import check
        import stage
    return stage, check


def layer_of(entry):
    """The model layer that handed a prop data object to the shared loop (score/stages/shapes_first): its `layer`,
    else "objects", the layer every prop data file was first written for."""
    return entry.get("layer", "objects")


def inventory_rows(inventory, wanted):
    """The close-up stage's rows of `wanted` objects: name, size, its reading's own size where it has one (the
    close-up is asked for and checked at it, stage.object_size), concept view and box from the inventory (the view's
    picture is filled in by make_inputs, from the row's declared file)."""
    return [{"id": row["id"], "scene": inventory["scene"], "words": row["name"], "size": row["size"],
             "read_size": row.get("read_size"), "view": row.get("view"), "box": row.get("box")}
            for row in inventory["rows"] if row["id"] in wanted]


def make_inputs(inputs, out, seed, params):
    """rows.json: every object of the place's prop data (those the runner's object filter keeps, prop_data.kept) as a
    close-up row, its drawn close-up where named; the rows after it work on these rows alone."""
    objects = prop_data.kept(prop_data.record_at(inputs["props"])["objects"], params)
    rows = inventory_rows(json.loads(inputs["inventory"].read_text()), objects)
    for row in rows:
        row["concept"] = str(inputs[f"view {row['view']}"]) if row["view"] else None
        entry = objects[row["id"]]
        # only an object whose prop data names a close-up has one drawn: an object named like one of the row's tools
        # (the square's `stage` took "close-up stage", the tool's folder, 2026-10-24) has none
        named = inputs.get(f"close-up {row['id']}") if entry.get("closeup") else None
        row["drawn"] = str(named) if named else None
        row.update(route=entry["route"], take=entry.get("take"), layer=layer_of(entry),
                   failures=entry.get("failures", {}))
    missing = sorted(set(objects) - {row["id"] for row in rows})
    (out / "rows.json").write_text(json.dumps({"rows": rows, "not_in_inventory": missing}, indent=1))


def inputs_faults(folder):
    return [] if (folder / "rows.json").exists() else ["no rows.json"]


def designed_inventory(inputs):
    """A designed place's hand-in, or a line no place owns (the people line, its rows drawn from the designs that map
    them, #26), as the box gate reads it (its views' pictures the declared files), else None: the gate reads the
    scene's own inventory file."""
    found = json.loads(inputs["inventory"].read_text())
    if "objects" not in found and not found.get("no_place"):
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


def taken_or_why(row, out):
    """taken_as_drawn, or why the drawn close-up could not be taken (missing, a folder, no picture): one object's
    failure, a batch gap, never the whole row's."""
    try:
        taken_as_drawn(row, out)
    except OSError as error:  # PIL's UnidentifiedImageError is one too
        return f"{row['drawn']}: {type(error).__name__}: {error}"
    return None


def measured(path, row):
    """The shape check's measured faults of one close-up at its object's own size (stage.object_size: its reading's,
    else the row's); a person's (a row of the people layer: drawn in the rig's A-pose, no box's outline) by its
    framing and its arms clear of the body (check.person_faults); any other row with no measured size is named, never
    measured against a made-up box."""
    stage, check = closeup_tools()
    if row.get("layer") == "people":
        return check.person_faults(path)
    if stage.object_size(row) is None:
        return ["no measured size: its proportions held to none"]
    return check.measured_faults(check.measure(path, stage.object_size(row)))


def draw_missing(rows, out):
    """Pro's close-ups of the rows with none: first every take whose request google_spend's cache holds (free: a
    picture drawn before, kept or rejected, judged again by today's check), then each take of PRO_TAKES in turn for
    the rows no picture passed yet (one Pro gave no picture is a gap, not asked again); {id: take record}."""
    stage, _ = closeup_tools()
    stage.make_crops(rows, out)
    stage.with_pro_wordings(rows)
    found = {}
    with prop_data.tools("props/closeup", "props", "cloud"):  # Pro's key is read through secret_store
        for take in stage.PRO_TAKES:
            judged_take(rows, out, take, {row["id"] for row in rows if stage.cached(row, out, take)}, found)
        for take in stage.PRO_TAKES:
            judged_take(rows, out, take, {row["id"] for row in rows if still_open(found.get(row["id"], {}), take)},
                        found)
    return {row: {take: tried[take] for take in stage.PRO_TAKES if take in tried} for row, tried in found.items()}


def still_open(tried, take):
    """Whether a row is drawn at `take`: no take of it passed, none came back without a picture, and `take` untried."""
    return take not in tried and all(faults and not faults[0].startswith("Pro gave no") for faults in tried.values())


def judged_take(rows, out, take, wanted, found):
    """The `wanted` rows' pictures of `take` drawn (pro.draw: a cached one read back free) and measured into `found`
    ({id: {take: faults}})."""
    stage, _ = closeup_tools()
    if not wanted:
        return
    stage.draw_with_pro(rows, out, wanted, take)
    for row in rows:
        if row["id"] in wanted:
            picture = out / take / f"{row['id']}.png"
            found.setdefault(row["id"], {})[take] = measured(picture, row) if picture.exists() else [
                f"Pro gave no {take} picture"]


def make_closeups(inputs, out, seed, params):
    """closeups/<id>.png for every object (drawn ones as they are, the rest by Pro) and closeups.json."""
    rows = json.loads((inputs["props-inputs"] / "rows.json").read_text())["rows"]
    (out / "closeups").mkdir(parents=True)
    unreadable = {row["id"]: taken_or_why(row, out) for row in rows if row["drawn"]}
    unreadable = {row: why for row, why in unreadable.items() if why}
    takes = draw_missing([row for row in rows if not row["drawn"]], out)
    record = {}
    for row in rows:
        tried = takes.get(row["id"], {})
        passed = next((take for take, faults in tried.items() if not faults), None)
        if passed:
            shutil.copy(out / passed / f"{row['id']}.png", out / "closeups" / f"{row['id']}.png")
        record[row["id"]] = {"size": row["size"], "read_size": row.get("read_size"), "layer": row.get("layer"),
                             "drawn_by": "given" if row["drawn"] else passed,
                             "takes": tried, "pro_pictures": sum((out / take / f"{row['id']}.png").exists()
                                                                 for take in tried)}
    batch_gaps.write(out, [batch_gaps.gap(f"{row['id']}: no close-up passed", "closeup", "close-up",
                                          (row["id"], row.get("take")),
                                          [f"{take}: {', '.join(faults)}"
                                           for take, faults in record[row["id"]]["takes"].items()],
                                          "every Pro take failed the shape check's measured half")
                           for row in rows if not row["drawn"] and not record[row["id"]]["drawn_by"]] +
                     [batch_gaps.gap(f"{row['id']}: its drawn close-up could not be read", "closeup", "close-up",
                                     (row["id"], row.get("take")), [unreadable[row["id"]]],
                                     "the close-up its prop data names is no picture that opens")
                      for row in rows if row["id"] in unreadable])
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
