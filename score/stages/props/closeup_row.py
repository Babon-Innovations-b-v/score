"""The prop route's first rows: the objects' inputs (free) and their close-ups (paid, Nano Banana Pro).

props-inputs@<place> writes rows.json, one row per object of the place's prop data in the close-up stage's form
(tools/props/closeup/stage.py: id, scene, words, size, concept picture, box), with the close-up already drawn where
the data names one, its route, take and the model layer that handed it (the shared loop's hand-in, #41). Its gate,
`boxed or drawn`, is the close-up stage's own box gate (stage.gate_problems): every object without a drawn close-up
needs a box the gate passes, so nothing is drawn of the wrong thing.

closeup@<place> draws every missing close-up with Nano Banana Pro through tools/props/closeup/pro.py, a take's
close-ups as one Batch API job at half price (google_batch prices each answer): the first take, then up to three
retries, each worded more strictly and the later ones on their own seeds, for each picture the check rejected (the
stage's PRO_TAKES, owner 2026-10-24 and 2026-10-25); the step bought again for a gap draws up to four new takes on the
ladder after them (stage.take_at, owner 2026-10-25: "a place needs every object"). Every picture stays in Google's cache, keyed by its request, and
the check judges it apart: a take cached before is read back free and judged again first, so a picture that passes is
kept and only the rows none passed are drawn again (coordinator, 2026-10-25). A drawn close-up is taken as it is,
set on the stage's grey. Its gate, `close-up`, is the shape check's measured half (check.measured_faults: plain
border, one object filling the frame, the proportions of the object's own size, stage.object_size), free and
re-measured on the stored pictures, so Pixal3D is never
paid for a close-up that fails it. An object every Pro take failed keeps none (in a free-only run, every cached take: its
next, a paid retry on the priced list, is named in the run's log only, its gap worded as a paid run's): its prop route
failed there, a batch gap (batch-gaps.json, score/stages/batch_gaps.py) the rows after it leave out. The judge's half
(a model on rented cards) is not run here.
"""
import dataclasses
import io
import json
import os
import shutil

from PIL import Image

import score.stages.batch_gaps as batch_gaps
import score.stages.props.prop_data as prop_data  # the module, not the package: the table stays out of the code
from score.stages.surfaces.surface_gates import verdict

GREY = (205, 205, 205)
# pro.DOLLARS_A_PICTURE, written here: pro is imported only inside the rows' functions (prop_data.tools). Google's
# 2K price at the Batch API's half, as pro.draw asks (owner, 2026-10-24).
DOLLARS_A_PICTURE = 0.067
# A place's row at its most: every object drawing all of Pro's takes (stage.PRO_TAKES: the first and up to three
# retries), counted one dollar a euro (google_spend), for a place of OBJECTS_GUESS objects. A guess: a reading has no
# cap on its rows and no spread of objects a place across environments is measured yet; prepare prices each Buy from
# its own rows (estimate.per_model), never from this.
OBJECTS_GUESS = 50
EUROS = round(OBJECTS_GUESS * 4 * DOLLARS_A_PICTURE, 2)

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
    picture is filled in by make_inputs, from the row's declared file), and `far` on a row laid far off (prepare's
    groups.far_made: its close-up is drawn from its crop alone, stage.pro_wording)."""
    return [{"id": row["id"], "scene": inventory["scene"], "words": row["name"], "size": row["size"],
             "read_size": row.get("read_size"), "view": row.get("view"), "box": row.get("box"),
             **({"far": row["far"]} if row.get("far") else {})}
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


def same_row(row, then):
    """Whether a row is the one props-inputs handed before (`then`), all but its concept's path (a make's frozen home)
    and the wording chosen on it here."""
    def plain(entry):
        return {key: value for key, value in entry.items() if key not in ("concept", "pro_wording")}
    return then is not None and plain(row) == plain(then)


def reused_pictures(rows, out, store=None):
    """Each row's take whose request google_spend's cache misses but the accepted closeup@<scene> output answered: its
    row the same as props-inputs handed it then (same_row) and the request rebuilt from that output's crop the same
    body, digest for digest, as today's. Its picture goes into out/<take>/ as the cache would give it, free: the answer
    this request got, kept in the store (batch 2, 2026-10-30: four accepted pictures whose answers were never cached)."""
    from score.store import Store

    stage, _ = closeup_tools()
    store = store or Store.default()
    for scene in sorted({row["scene"] for row in rows}):
        accept = store.current_accept(f"closeup@{scene}")
        record = accept and store.record(f"closeup@{scene}", accept["key"])
        if not record or "props-inputs" not in record.get("after", {}):
            continue
        then = {row["id"]: row for row in store.read_file(record["after"]["props-inputs"], "rows.json")["rows"]}
        listing = store.listing(accept["output"])
        kept = store.read_file(accept["output"], "closeups.json")["objects"]
        for row in rows:
            if row["scene"] == scene and same_row(row, then.get(row["id"])):
                reuse_row(row, out, kept.get(row["id"], {}).get("takes", {}), listing, store, stage)


def reuse_row(row, out, takes, listing, store, stage):
    """reused_pictures for one row: each take of the accepted output's whose rebuilt request is today's."""
    crop = listing.get(f"crops/{row['id']}.jpg")
    for take in takes:
        picture = listing.get(f"{take}/{row['id']}.png")
        if not crop or not picture or stage.cached(row, out, take):
            continue
        text, today_crop, concept, seed = stage.pro_ask(row, out, take)
        then_crop = Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{crop}")))
        today, then = (stage.pro.google_spend.cache_path(stage.pro.MODEL, stage.pro.request_body(text, image, concept,
                                                                                               seed))
                       for image in (today_crop, then_crop))
        if today == then:
            (out / take).mkdir(parents=True, exist_ok=True)
            (out / take / f"{row['id']}.png").write_bytes(store.objects.read_bytes(f"blobs/{picture}"))


def draw_missing(rows, out, store=None):
    """Pro's close-ups of the rows with none: first every take on the ladder whose request google_spend's cache holds
    (free: a picture drawn before, kept or rejected, judged again by today's check), then up to len(PRO_TAKES) new
    takes for each row no picture passed yet, each row at its next take (stage.take_at: a gap's step bought again
    draws new takes, never only its rejected ones read back; one Pro gave no picture is a gap, not asked again; in a
    run that may spend nothing, runs_free_only, no new take: its row is a gap, make_closeups); a take the cache misses
    that the accepted output answered for the same request is read back from there (reused_pictures); {id: take
    record}, its takes in ladder order."""
    stage, _ = closeup_tools()
    stage.make_crops(rows, out)
    stage.with_pro_wordings(rows)
    found = {}
    with prop_data.tools("props/closeup", "props", "cloud"):  # Pro's key is read through secret_store
        reused_pictures(rows, out, store)
        index = 0
        while wanted := {row["id"] for row in rows if stage.cached(row, out, stage.take_at(index))
                         or (out / stage.take_at(index) / f"{row['id']}.png").exists()}:
            judged_take(rows, out, stage.take_at(index), wanted, found)
            index += 1
        for _ in [] if runs_free_only() else stage.PRO_TAKES:
            for take, wanted in next_takes(rows, found, stage).items():
                judged_take(rows, out, take, wanted, found)
    return {row: dict(sorted(tried.items(), key=lambda item: stage.take_index(item[0]))) for row, tried in found.items()}


def runs_free_only():
    """Whether this process may spend nothing (tools/cloud/ledger.py FREE_ONLY, this PC's free-only run)."""
    with prop_data.tools("cloud"):
        import ledger
    return os.environ.get(ledger.FREE_ONLY) == "1"


def say_unpaid(rows, takes, stage):
    """In a free-only run, each row no cached take passed named in the run's log as a paid retry on the priced list,
    with its next take; the log only, so the output (its gaps worded as a paid run's) stays the same in every mode
    and nothing after it re-keys (batch 2, 2026-10-30)."""
    for take, wanted in sorted(next_takes(rows, takes, stage).items()):
        for row in sorted(wanted):
            print(f"{row}: no cached Pro take passed and this run spends nothing: paid retry on the priced list, its "
                  f"next take {take} (USD {DOLLARS_A_PICTURE})", flush=True)


def next_takes(rows, found, stage):
    """{take: {id}} of each row still open at its next take on the ladder (the one after its takes tried)."""
    wanted = {}
    for row in rows:
        tried = found.get(row["id"], {})
        take = stage.take_at(len(tried))
        if still_open(tried, take):
            wanted.setdefault(take, set()).add(row["id"])
    return wanted


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
    undrawn = [row for row in rows if not row["drawn"]]
    takes = draw_missing(undrawn, out)
    if runs_free_only():
        say_unpaid(undrawn, takes, closeup_tools()[0])
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
