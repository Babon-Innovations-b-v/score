"""The real makers and free checks of prop_batch.run: each paid step one batch over every prop still in it, through
the runners and the ledgered clients that already make these outputs, so the batch is paid and recorded as they are.

    close-up      Nano Banana Pro from this PC (../closeup/stage.py's Pro takes through pro.draw, google_spend's
                  ledger and cache: a drawn close-up is never drawn again); a kept close-up is not asked at all
    image-to-3d   batch.py: one Pixal3D batch over every prop's new take, on the cheapest card that holds it (L4
                  first, capacity.KIND_ORDER) and as many takes to a card as it runs at once (RUNS_PER_24GB), each
                  finished here with pixal.py --finish-only as the batch does; a take already made is not asked again
    finish-pick   finish_ask.finish_list from this PC (Gemini 3.1 Pro through google_spend, cached by its input)
    bake          library_bake.py: one bake batch over every prop, a make_chunky job each, its entry and specs from
                  the place's surface data as the surface line's bake builds them (place_line.bake_entries)

Limit, one machine per step: the owner's shape is one rented machine for a prop's whole route, but the steps cannot
share one with the runners as they are. Pixal3D runs on batch.py's own set-up (the lab's image) while the bake runs
Blender 5.0.1 from library_setup.sh; the finish (pixal.py --finish-only) stays on this PC until a byte-for-byte match
up there is measured (cloud overlay); the finish pick, a Google ask, sits between the model and the bake on this PC;
and a Pixal3D card is not parked for another kind (pixal is not in park.CLEANUPS). So each step is one warm batch for
all its props, never one rent per place, and a bake card is parked for the next claim of its kind as park.py does.

Limit, parts: the bake (make_chunky) bakes a prop's labelled parts folder (<library surface>.ply), which only the
surface line's maps, SegviGen and paint make today, from the take they were made on. A re-made take needs its parts
written again (a code body over the kept detail: route work, branch prop-route), so a prop names its `parts` folder
and the first free check stops a prop that names none before anything is paid for it.

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
for folder in (REPO, HERE.parent, HERE, HERE.parent / "library", HERE.parent / "closeup", HERE.parent / "scene",
               HERE.parent / "gates", REPO / "score/stages/surfaces"):
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
    from the prop's take, by place_line.bake_entries."""
    import place_line
    job, chunky = place_line.bake_entries(bake_inputs(prop["place"]),
                                          {prop["name"]: prop_batch.resolved(prop.get("parts") or "")})
    if not chunky:
        raise KeyError(f"{prop['place']}'s surface data bakes no model from {prop['name']}")
    return job, chunky[0]


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
    """Nano Banana Pro's close-up of each prop as the close-up stage draws one (the crop alone, then with the room for
    what still fails its measured shape check), the first that passes copied to out/closeups/<name>.png."""
    import check
    import stage
    folder = pathlib.Path(out) / "closeups" / "pro"
    rows = {prop["name"]: closeup_row(prop) for prop in props}
    stage.make_crops(list(rows.values()), folder)
    failed, made = {row["id"] for row in rows.values()}, {}
    for take in stage.PRO_TAKES:
        stage.draw_with_pro(list(rows.values()), folder, failed, take)
        for name, row in rows.items():
            picture = folder / take / f"{row['id']}.png"
            if name not in made and picture.exists() and not check.measured_faults(check.measure(picture, row["size"])):
                shutil.copyfile(picture, drawn_closeup({"name": name}, out))
                made[name] = {"caller": "pro", "picture": str(drawn_closeup({"name": name}, out))}
        failed = {row["id"] for name, row in rows.items() if name not in made}
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
    """(ok, why): a prop that makes the bake names the parts folder it bakes."""
    if not prop_batch.makes_step(prop, prop_batch.STEPS[-1]) or prop.get("parts"):
        return True, ""
    return False, ("names no parts for its bake: a re-made take needs its parts written again (a code body over the "
                   "kept detail, route work), or today's maps, SegviGen and paint")


def check_inputs(prop):
    """Before the close-up: the box gate on the prop's row, and its parts named."""
    import stage
    problems = stage.gate_problems([closeup_row(prop)])
    if problems:
        return False, "; ".join(problems)
    return parts_named(prop)


def check_closeup(prop, out):
    """Before image-to-3d: the close-up is there and passes its measured shape check at the row's size."""
    import check
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
    """Before the bake: the parts folder holds parts, each a library surface the bake knows."""
    import place_line
    folder = prop_batch.resolved(prop.get("parts") or "")
    if not prop.get("parts") or not list(folder.glob("*.ply")):
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
