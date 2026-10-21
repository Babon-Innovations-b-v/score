"""The real makers and free checks of prop_batch.run: each paid step one batch over every prop still in it, through
the runners and the ledgered clients that already make these outputs, so the batch is paid and recorded as they are.

    close-up      Nano Banana Pro from this PC (../closeup/stage.py's one Pro take a prop, its wording chosen free
                  first, through pro.draw, google_spend's ledger and cache: a drawn close-up is never drawn again);
                  a kept close-up is not asked at all
    image-to-3d   batch.py: one Pixal3D batch over every prop's new take, on the cheapest card that holds it (L4
                  first, capacity.KIND_ORDER) and as many takes to a card as it runs at once (RUNS_PER_24GB), each
                  finished here with pixal.py --finish-only as the batch does; a take already made is not asked again
    finish-pick   finish_ask.finish_list from this PC (Gemini 3.1 Pro through google_spend, cached by its input)
    bake          library_bake.py: one bake batch over every prop, a make_chunky job each, its entry and specs from
                  the place's surface data as the surface line's bake builds them (place_line.bake_entries)

Limit, one machine per step: the owner's shape is one rented machine for a prop's whole route, but the steps cannot
share one with the runners as they are. Pixal3D runs on batch.py's own set-up (the lab's image) while the bake runs
Blender 5.0.1 from library_setup.sh; the finish (pixal.py --finish-only) stays on this PC until a byte-for-byte match
up there is measured (cloud overlay); and the finish pick, a Google ask, sits between the model and the bake on this
PC. So each step is one warm batch for all its props, never one rent per place, and each step's card (Pixal3D's and
the bake's) is parked for the next claim of its kind as park.py does.

Parts: the bake (make_chunky) bakes a prop's labelled parts folder (<library surface>.ply). A prop that names its
`parts` bakes that folder. A bodied prop (`body`: its take in bodies.BODIES) has its re-made take's parts written,
free, before its bake (../library/body_parts.py): each face of the new raw model takes the surface of the nearest face
of the accepted take (the place's accepted surfaces-paint output), so the body brings its own parts from code and
the kept details keep their finishes; the surface line's maps, SegviGen and paint are not made again. A prop with
neither stops at the first free check before anything is paid for it.

Checks, free, before each paid step: the box gate and the parts named (before the close-up), the close-up's measured
shape check (before image-to-3d), the new raw model's proportions against the accepted take's (gates/model.py's
spread, before the finish pick), every part a library surface the bake knows (before the bake).
"""
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
for folder in (REPO, HERE.parent, HERE, HERE.parent / "library", HERE.parent / "library/inside", HERE.parent / "closeup",
               HERE.parent / "scene", HERE.parent / "gates", REPO / "score/stages/surfaces"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the prop tools must not shadow the framework's

import prop_batch  # noqa: E402
import surface_data  # noqa: E402
from paths import HOME, VENV_PYTHON, WORK  # noqa: E402

LEDGER = HOME / "cloud" / "ledger.jsonl"
TAKE_FILES = (".glb", "-final.glb", ".svviews")


# --- the prop's data -------------------------------------------------------------------------------------------------

def surface_entry(prop):
    """The prop's take in its place's surface data: its kind, object words and library places."""
    return surface_data.takes(prop["place"])[prop["name"]]


def bake_inputs(place):
    """The surface line's bake files of a place, as paths ({home}, {data} and {repo} filled in)."""
    return {name: prop_batch.resolved(pattern) for name, pattern in surface_data.bake_files(place).items()}


def bake_entry(prop):
    """(the place's bake job, the prop's make_chunky entry with its parts folder): the model the place's data bakes
    from the prop's take, by place_line.bake_entries, sized over the prop's sizing folder (sizing_folder)."""
    import place_line
    job, chunky = place_line.bake_entries(bake_inputs(prop["place"]), {prop["name"]: sizing_folder(prop)})
    if not chunky:
        raise KeyError(f"{prop['place']}'s surface data bakes no model from {prop['name']}")
    return job, dict(chunky[0], parts=str(parts_folder(prop) or ""))


def sizing_folder(prop):
    """The labelled folder a prop's entry is turned over (bake_job.measured_turn): the prop's own `parts`,
    else a bodied prop's accepted labelled take (its re-made take's parts are written at this entry's size, so they
    are not there yet), else None (a prop with neither stops at its first free check)."""
    if prop.get("parts"):
        return prop_batch.resolved(prop["parts"])
    return accepted_labelled(prop) if prop.get("body") else None


def parts_folder(prop):
    """The parts folder a prop's bake reads: its own `parts`, else a bodied prop's re-made take's written parts
    (WORK/body-parts/<take>), else None."""
    if prop.get("parts"):
        return prop_batch.resolved(prop["parts"])
    return WORK / "body-parts" / prop["take"] if prop.get("body") else None


def accepted_labelled(prop):
    """The accepted labelled take of a bodied prop: its place's accepted surfaces-paint output, checked out."""
    from score.store import Store
    store = Store.default()
    return store.checkout(store.accepted(f"surfaces-paint@{prop['place']}")) / "labelled" / prop["body"]


def write_body_parts(prop):
    """A bodied prop's re-made take's parts (body_parts.write, free, no model loaded), at its bake entry's laid size
    and turn; (ok, why)."""
    import body_parts
    _, entry = bake_entry(prop)
    try:
        body_parts.write(prop["take"], accepted_labelled(prop), prop["body"], entry["size"], entry["base"],
                         parts_folder(prop))
    except SystemExit as refusal:
        return False, str(refusal)
    return True, ""


def take_made(take):
    """Whether the new take's raw model, finished model and camera folder are all here."""
    return all((WORK / "pixal" / f"{take}{suffix}").exists() for suffix in TAKE_FILES)


def drawn_closeup(prop, out):
    return pathlib.Path(out) / "closeups" / f"{prop['name']}.png"


def picture_of(prop, out):
    """The close-up the later steps use: the one this batch drew, else the prop's kept one."""
    drawn = drawn_closeup(prop, out)
    return drawn if drawn.exists() else prop_batch.resolved(prop["picture"])


def inventory_path(prop):
    return REPO / "data/inventory" / f"{prop['place']}.json"


def closeup_row(prop):
    """The close-up stage's row of the prop (its words, size, scene, box and concept view), from its place's approved
    inventory."""
    import inventory as inventories
    import stage
    rows = [row for row in stage.rows_from_inventory(inventories.approved_inventory(inventory_path(prop)))
            if row["id"] == prop["row"]]
    if not rows:
        raise KeyError(f"no generated row {prop['row']} with a box in {inventory_path(prop)}")
    return dict(rows[0], concept=str(WORK / rows[0]["concept"].removeprefix("WORK/")))


# --- the ledger ------------------------------------------------------------------------------------------------------

def batch_ids(kind):
    return {row.get("batch") for row in prop_batch.read_lines(LEDGER) if row.get("kind") == kind}


def new_batch(kind, before):
    """The one ledger batch of `kind` written since `before`, or None when there is none or several (another session's
    batch of the kind ended meanwhile: measured_costs then leaves this step's euros unsplit rather than guess)."""
    found = sorted(batch_ids(kind) - before)
    return found[0] if len(found) == 1 else None


def run_tool(command, log, call):
    """A runner's command from the repo, its output into `log`; its exit code."""
    done = call([str(part) for part in command], cwd=REPO, capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(done.stdout[-20000:] + done.stderr[-20000:])
    return done.returncode


def came_back(code, made, log, what):
    """A batch that failed and brought nothing back raises with its log; one that brought some back lets the props
    with no output fail by name in the manifest."""
    if code and not made:
        raise RuntimeError(f"{what} failed (exit {code}) and made nothing; its log is {log}")
    return made


# --- the makers ------------------------------------------------------------------------------------------------------

def make_closeups(props, out):
    """Nano Banana Pro's close-up of each prop as the close-up stage draws one: one take a prop, its wording chosen free
    first (stage.pro_wording: the crop alone, or with the room when the crop is small), copied to
    out/closeups/<name>.png when it passes its measured shape check. One that fails is a gap, not drawn again (a
    batch runs every job once)."""
    import check
    import stage
    folder = pathlib.Path(out) / "closeups" / "pro"
    rows = {prop["name"]: closeup_row(prop) for prop in props}
    stage.make_crops(list(rows.values()), folder)
    take, made = stage.PRO_TAKES[0], {}
    stage.draw_with_pro(list(rows.values()), folder, {row["id"] for row in rows.values()}, take)
    for name, row in rows.items():
        picture = folder / take / f"{row['id']}.png"
        if picture.exists() and not check.measured_faults(check.measure(picture, row["size"])):
            shutil.copyfile(picture, drawn_closeup({"name": name}, out))
            made[name] = {"caller": "pro", "picture": str(drawn_closeup({"name": name}, out)),
                          "pro_wording": row["pro_wording"]}
    return made


def batch_line(prop, out):
    """One line of batch.py's list: the new take, its close-up, the faces its bake entry asks and its seed."""
    _, entry = bake_entry(prop)
    return f"{prop['take']} {picture_of(prop, out)} --faces {entry['faces']} --seed {prop['seed']}"


def make_models(props, out, who, call=subprocess.run):
    """Every prop's new take through one batch.py batch (a take already here is not made again); {name: {batch,
    take}} for each take that came back finished."""
    todo = [prop for prop in props if not take_made(prop["take"])]
    code, log, batch = 0, pathlib.Path(out) / "logs" / "image-to-3d.log", None
    if todo:
        listing = pathlib.Path(out) / "image-to-3d.txt"
        listing.parent.mkdir(parents=True, exist_ok=True)
        listing.write_text("".join(batch_line(prop, out) + "\n" for prop in todo))
        before = batch_ids("pixal")
        inventories = sorted({inventory_path(prop) for prop in todo})
        code = run_tool([VENV_PYTHON, HERE / "batch.py", listing, "--who", who, "--inventory", *inventories], log,
                        call)
        batch = new_batch("pixal", before)
    made = {prop["name"]: {"batch": batch if prop in todo else None, "take": prop["take"]}
            for prop in props if take_made(prop["take"])}
    return came_back(code, made, log, "the Pixal3D batch")


def make_finish_picks(props, out):
    """Each prop's finish list of its close-up (finish_ask.finish_list, Gemini 3.1 Pro, cached by its input), each
    finish one of the take's allowed library surfaces, as out/finishes/<name>.json."""
    import finish_ask
    import labels
    from PIL import Image
    made = {}
    for prop in props:
        entry = surface_entry(prop)
        finishes = finish_ask.finish_list(Image.open(picture_of(prop, out)).convert("RGBA"), entry["object"],
                                          labels.allowed_materials(entry["library_places"][0], entry["kind"], []))
        path = pathlib.Path(out) / "finishes" / f"{prop['name']}.json"
        prop_batch.write_json(path, {"take": prop["take"], "finishes": finishes})
        made[prop["name"]] = {"caller": "finishmap-list", "finishes": str(path)}
    return made


def bake_job(prop, out):
    """The prop's make_chunky job, as the surface line's bake writes one: the place's job with its entry alone, the
    specs from today's library in the place's tokens, unwalked where nobody walks."""
    import place_line
    job, entry = bake_entry(prop)
    data = json.loads(bake_inputs(prop["place"])["surfaces"].read_text())
    specs = place_line.unwalked(place_line.baking_specs(data["library"], job["specs"], [pathlib.Path(entry["parts"])]),
                                data)
    one = dict(job, specs=specs, chunky=[entry], out=str(pathlib.Path(out) / "made"), report=f"report-{entry['name']}.json")
    for key in ("kit", "pieces", "code", "was"):
        one.pop(key, None)
    path = pathlib.Path(out) / "bake-jobs" / f"{prop['name']}.json"
    prop_batch.write_json(path, one)
    return path, entry["name"]


def make_bakes(props, out, who, call=subprocess.run):
    """Every prop's bake through one library_bake.py batch; {name: {batch, model}} for each baked model."""
    import place_line
    jobs = {prop["name"]: bake_job(prop, out) for prop in props}
    log = pathlib.Path(out) / "logs" / "bake.log"
    before = batch_ids("library")
    code = run_tool([VENV_PYTHON, HERE / "library_bake.py", *(path for path, _ in jobs.values()), "--who", who,
                     "--classes", place_line.CLASSES], log, call)
    batch = new_batch("library", before)
    made = {name: {"batch": batch, "model": str(pathlib.Path(out) / "made" / f"{model}.gltf")}
            for name, (_, model) in jobs.items() if (pathlib.Path(out) / "made" / f"{model}.gltf").exists()}
    return came_back(code, made, log, "the bake batch")


def makers_for(out, who):
    """prop_batch.run's makers, by step."""
    return {"closeup": lambda props: make_closeups(props, out),
            "image-to-3d": lambda props: make_models(props, out, who),
            "finish-pick": lambda props: make_finish_picks(props, out),
            "bake": lambda props: make_bakes(props, out, who)}


# --- the free checks -------------------------------------------------------------------------------------------------

def parts_named(prop):
    """(ok, why): a prop that makes the bake names the parts folder it bakes, or a body with a builder
    (bodies.BODIES) its parts are written for. Fault (trial, 2026-10-19): eight trial props named a body no builder
    makes, passed this check and would have paid Pixal3D before check_parts refused them."""
    import bodies
    if not prop_batch.makes_step(prop, prop_batch.STEPS[-1]) or prop.get("parts") or prop.get("body") in bodies.BODIES:
        return True, ""
    if prop.get("body"):
        return False, f"names the body {prop['body']}, which no builder makes (bodies.BODIES)"
    return False, ("names no parts and no body for its bake: a re-made take needs a code body (bodies.BODIES) or "
                   "today's maps, SegviGen and paint")


def check_inputs(prop):
    """Before the close-up: the box gate on the prop's row, and its parts named."""
    import stage
    problems = stage.gate_problems([closeup_row(prop)])
    if problems:
        return False, "; ".join(problems)
    return parts_named(prop)


def check_closeup(prop, out):
    """Before image-to-3d: its parts named (parts_named: a prop that kept its close-up stops here, before its first
    paid step), and the close-up is there and passes its measured shape check at the row's size."""
    import check
    named, why = parts_named(prop)
    if not named:
        return False, why
    picture = picture_of(prop, out)
    if not picture.is_file():
        return False, f"no close-up at {picture}"
    faults = check.measured_faults(check.measure(picture, closeup_row(prop)["size"]))
    return (False, "; ".join(faults)) if faults else (True, "")


def check_raw_model(prop):
    """Before the finish pick: the new raw model keeps the proportions of the prop's accepted take, made from the same
    close-up (gates/model.py's spread, both in Pixal3D's own frame). Against the laid size it cannot be judged here:
    the bake's kit-frame turn is make_chunky's, and the accepted takes measured 0.2 to 3.6 that way."""
    import model as model_gate
    import trimesh

    def extents(take):
        return trimesh.load(WORK / "pixal" / f"{take}.glb", force="mesh", skip_materials=True).extents

    spread = model_gate.spread(extents(prop["take"]), extents(prop["name"]))
    if spread > model_gate.SPREAD_LIMIT:
        return False, f"spread {spread:.3f} against the accepted take {prop['name']}, over {model_gate.SPREAD_LIMIT}"
    return True, ""


def check_parts(prop):
    """Before the bake: a bodied prop's parts written first (write_body_parts, free); then the parts folder holds
    parts, each a library surface the bake knows."""
    import place_line
    if prop.get("body") and not prop.get("parts"):
        ok, why = write_body_parts(prop)
        if not ok:
            return False, why
    folder = parts_folder(prop)
    if folder is None or not list(folder.glob("*.ply")):
        return False, f"no parts at {folder}"
    data = json.loads(bake_inputs(prop["place"])["surfaces"].read_text())
    job, _ = bake_entry(prop)
    try:
        place_line.baking_specs(data["library"], job["specs"], [folder])
    except RuntimeError as fault:
        return False, str(fault)
    return True, ""


def checks_for(out):
    """prop_batch.run's free checks, by step."""
    return {"closeup": check_inputs, "image-to-3d": lambda prop: check_closeup(prop, out),
            "finish-pick": check_raw_model, "bake": check_parts}
