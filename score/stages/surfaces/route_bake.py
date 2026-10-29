"""The finish route's bake, `surfaces-bake` (paid): each take painted and baked in one job on the warm card the bake
rents (owner's lead, 2026-10-20, #18): nothing heavy runs on this PC, whose prop environment is capped at 14 GB
(crane-r1's paint peaked at 34.8 GB on a rented machine, 2026-10-12). One job a take (its one model, or each model
the place bakes from it, so a take is painted once) through blender_cloud.py on the bake's card classes
(place_line.CLASSES), every job once: a job that fails is its take's batch gap (batch-gaps.json,
score/stages/batch_gaps.py), left out of the paint and named in the gate, whose fault the table moves to complete;
only a call that brought no take back (a set-up fault) stops the row.

Here, free, before anything is rented: each part's library surface from the parts row (place_line.method_surfaces,
its proposals into the finish registry), with the list's settings where the part has them (route_settings: the
variant's spec in the list's token colour, roughness and metal, under its settings name), and the job's specs from
today's library (a surface no library holds, or a spec naming a picture that is not there, stops the row before it
rents). Up there (inside/paint_bake.py): the take painted as the rented paint painted it (place_line.paint_take),
its models' make_chunky entries written over its labelled take (`bake_job_step`, bake_job.entry_of), then
make_chunky on the card.

Output: made/ (the baked models), labelled/<take>/ and painted.json (the paint's, which surfaces-paint takes over),
baked.json (each model's entry), specs.json (every spec the bake baked, by name: the check reads the settings'
surfaces from it), elsewhere.json (place_line.claims). Gate "baked": every take of the parts baked, every claim baked
by its place.
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import palette_library  # noqa: E402
import place_line  # noqa: E402
import prop_env  # noqa: E402
import route_settings  # noqa: E402
import surface_gates as gates  # noqa: E402

SCRIPT = "score/stages/surfaces/inside/paint_bake.py"
# A job's minutes on the card: the rented paint's (place_line.PAINT_MINUTES, measured on processor machines) and a
# model's bake (library_bake.MINUTES_EACH["chunky"], measured on an L4) for each model of the take.
PAINT_MINUTES, MODEL_MINUTES = place_line.PAINT_MINUTES, 1.5
HEAD, CHUNKY = "bake head", "bake chunky job"  # the listing's: the job's head with the take's models; its job
# What of the repository the job reads besides the paint's: the bake's library code (tools/library: route.py's
# library_files), ProcFunc and infinigen2 (library_bake.SHIPPED).
BAKE_REPO = ("tools/library", "vendor/procfunc/src", "vendor/infinigen2")


def named_records(records):
    """A take's part records with each part that has the list's settings painted as its settings' surface."""
    return [dict(record, surface=route_settings.settings_name(record["surface"], record["settings"]))
            if record.get("settings") and record.get("surface") else record for record in records]


def baked_specs(palette, specs, records):
    """The job's specs: its own (decals, screens) and every surface the records name, from today's library as the
    scene palette gives it (palette_library.specs: each variant in its own token, dirtied in its dirt token), a
    surface with settings as its variant's spec with them (route_settings.set_spec). A surface in no library, or a
    spec naming a picture not there, stops the bake here."""
    every = palette_library.specs(palette)
    colours = palette_library.library_tokens(palette)
    found = {**specs, **{name: every[name] for name in specs if name in every}}
    unknown = []
    for record in (record for take in records.values() for record in take if record.get("surface")):
        if record.get("settings") and record.get("judge") in every:
            found[record["surface"]] = route_settings.set_spec(every[record["judge"]], record["settings"], colours)
        elif record["surface"] in every:
            found[record["surface"]] = every[record["surface"]]
        elif record["surface"] not in specs:
            unknown.append(record["surface"])
    if unknown:
        raise RuntimeError(f"surfaces in no library: {sorted(set(unknown))}")
    missing = sorted(name for name, spec in found.items() if "image" in spec and not pathlib.Path(spec["image"]).exists())
    if missing:
        raise RuntimeError(f"specs whose picture is not there: {missing}")
    return found


def job_head(data, short, records):
    """The place's bake job's top-level fields (bake_job.job_head) at its scene palette's wear and dirt
    (palette_library.read, read from its design) with baked_specs, as the place walks it."""
    import bake_job
    palette = palette_library.read(short)
    head = bake_job.job_head(palette_library.wear(palette), palette_library.specs(palette))
    head["specs"] = place_line.unwalked(baked_specs(palette, head["specs"], records), data)
    return head


def job_files(short, out, records, heads):
    """Each take's part records, claimed rows and job head (`heads`: {take: the head with its models}) written beside
    the output: {take: (records, claimed, head)}."""
    found = {}
    for take, head in heads.items():
        found[take] = tuple(out / f".bake-{take}-{what}.json" for what in ("records", "claimed", "head"))
        found[take][0].write_text(json.dumps(records[take]))
        found[take][1].write_text(json.dumps({take: place_line.claimed_rows(take, short)}))
        found[take][2].write_text(json.dumps(head))
    return found


def card_job(inputs, short, out, take, files):
    """One take's cloud job file: its listing (the make's inputs, the take, its part records, claimed rows and job
    head) and every file it reads at its own path; its labelled take, its baked models and their entries come back."""
    listing = out / f".bake-{take}.json"
    records, claimed, head = files
    listing.write_text(json.dumps({**{name: str(path) for name, path in inputs.items()}, place_line.TAKE: take,
                                   place_line.RECORDS: str(records), place_line.CLAIMED: str(claimed),
                                   place_line.HOME: str(prop_env.PROPS_HOME), place_line.CODE: str(place_line.REPO),
                                   HEAD: str(head), CHUNKY: str(out / f".bake-{take}-chunky.json")}))
    pixal = prop_env.PROPS_HOME / "work/pixal"
    models = sorted({pixal / f"{take}.glb", pixal / f"{take}-final.glb", *pixal.glob(f"{take}-[0-9]*.glb")})
    world = [path for name, path in short.items()
             if name.startswith("inventory ") or name in ("surfaces", "resting rules", "relations")]
    mark = [path for path in [pixal / f"{take}.svviews" / "code.json"] if path.exists()]  # a code build's (bake_job)
    read = [listing, records, claimed, head, short["parts"] / "parts.json", short["parts"] / take, *world, *models, *mark,
            *(place_line.REPO / folder for folder in (*place_line.PAINT_REPO, *BAKE_REPO))]
    job = out / f".bake-{take}-job.json"
    job.write_text(json.dumps({"script": SCRIPT, "args": [str(listing)], "inputs": [str(path) for path in read],
                               "outputs": [str(out / "labelled" / take), str(out / "made"),
                                           str(out / "entries" / f"{take}.json")],
                               "minutes": PAINT_MINUTES + MODEL_MINUTES * len(json.loads(head.read_text())["models"])},
                              indent=1))
    return job


def make_bake(inputs, out, seed, params):
    """Every take the place bakes painted and baked on rented cards, one job a take (blender_cloud.py); the parts'
    proposals go into the finish registry here first. painted.json, baked.json, specs.json, elsewhere.json."""
    from registry import Registry
    from score.store import Store
    short = prop_env.short(inputs)
    data = place_line.data_of(short)
    method = json.loads((short["parts"] / "parts.json").read_text())
    registry = Registry(Store.default())
    records = {take: named_records(place_line.method_surfaces(take, data["takes"][take]["place"], record["parts"],
                                                              registry))
               for take, record in method["takes"].items()}
    head = job_head(data, short, records)
    models = {model: take for model, take in data["bake"]["models"].items() if take in method["takes"]}
    heads = {take: dict(head, models=sorted(model for model, its in models.items() if its == take))
             for take in sorted(set(models.values()))}
    files = job_files(short, out, records, heads)
    jobs = [card_job(inputs, short, out, take, files[take]) for take in heads]
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(place_line.REPO / "tools/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", f"surfaces-bake-{data['place']}", "--classes", place_line.CLASSES],
                          cwd=place_line.REPO, capture_output=True, text=True)
    (out / "bake.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    unbaked = sorted(take for take in heads if not (out / "labelled" / take / "labels.json").exists()
                     or not (out / "entries" / f"{take}.json").exists())
    if done.returncode and len(unbaked) == len(heads):
        raise RuntimeError(f"blender_cloud.py paint and bake failed: {done.stderr[-3000:]}")
    for path in out.glob(".bake-*"):
        path.unlink()
    import score.stages.batch_gaps as batch_gaps  # here: the bake job runs this module in the prop environment
    batch_gaps.write(out, [batch_gaps.gap(f"{take}: not baked", "surfaces-bake", "baked", (take,),
                                          [f"{take}: its paint and bake job brought nothing back (bake.log)"],
                                          "the take's bake job ran once in the batch and failed") for take in unbaked])
    heads = {take: head for take, head in heads.items() if take not in unbaked}
    painted = {take: json.loads((out / "labelled" / take / "labels.json").read_text()) for take in heads}
    left = {**method["left_out"], **{take: f"{take}: not baked" for take in unbaked}}
    (out / "painted.json").write_text(json.dumps({"takes": painted, "left_out": left}, indent=1))
    entries = {model: entry for take in heads
               for model, entry in json.loads((out / "entries" / f"{take}.json").read_text()).items()}
    (out / "baked.json").write_text(json.dumps({model: dict(entry, parts=pathlib.Path(entry["parts"]).name)
                                                for model, entry in entries.items()}, indent=1))
    (out / "specs.json").write_text(json.dumps(head["specs"], indent=1))
    (out / "elsewhere.json").write_text(json.dumps(place_line.claims(short), indent=1))


def stands(labelled):
    """Whether the paint levelled the take's feet (library_bake.stands: its labels.json `feet` not skipped), so
    make_chunky levels its cut-down copy's too."""
    labels = labelled / "labels.json"
    return labels.exists() and "skipped" not in json.loads(labels.read_text()).get("feet", {"skipped": "no report"})


# A recess stays this far out past its face (so the cut opens it cleanly) and leaves at least this much of its
# model behind it: a recess with a back, never a tunnel through.
RECESS_OUT, RECESS_BACK = 0.05, 0.05


def recess_box(size, recess):
    """A recess's box [low, high] in its model's kit frame (x across, y up from its foot, z deep, its middle at the
    origin across and deep) at the model's built `size`: on the face its `axis` and `side` name, its middle `along` the
    face kept within the face's span (shrunk to the span where wider) as the assembly keeps a door within its
    holder's (fitting.on_holder), from its `base` to its top within the model's height, `depth` deep into the model but
    never past RECESS_BACK of its far side."""
    wide, tall, deep = (float(side) for side in size)
    axis, across = (0, 2) if recess["axis"] == "x" else (2, 0)
    half, span = (wide if axis == 0 else deep) / 2, (deep if axis == 0 else wide)
    opening = min(span, float(recess["wide"]) + float(recess.get("room") or 0.0))
    middle = float(recess["along"]) + float(recess.get("room") or 0.0) / 2
    middle = min(max(middle, -span / 2 + opening / 2), span / 2 - opening / 2)
    depth = min(float(recess["depth"]), 2 * half - RECESS_BACK)
    side = float(recess["side"])
    low, high = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    low[across], high[across] = middle - opening / 2, middle + opening / 2
    low[1] = min(max(float(recess["base"]), 0.0), tall)
    high[1] = min(tall, low[1] + float(recess["tall"]))
    face, inner = side * half + side * RECESS_OUT, side * half - side * depth
    low[axis], high[axis] = min(face, inner), max(face, inner)
    return [[round(value, 4) for value in low], [round(value, 4) for value in high]]


def recessed(entries, relations):
    """`entries` with each recess the place's relations name (score/review/holders `recess`: a moving door's room in
    its holder model) as a cut of its holder's entry ({"recess": [low, high]}, make_chunky.opened), at its built size."""
    found = {model: dict(entry, cuts=list(entry.get("cuts") or [])) for model, entry in entries.items()}
    for relation in (relations or {}).get("relations", []):
        for piece in relation.get("pieces") or [relation]:
            recess = piece.get("recess") or relation.get("recess")
            if recess and recess["model"] in found:
                found[recess["model"]]["cuts"] += [{"recess": recess_box(found[recess["model"]]["size"],
                                                                         dict(recess, along=along))}
                                                   for along in recess.get("pieces") or [recess["along"]]]
    return found


def bake_files(place):
    """The bake row's files (surface_data.bake_files) and the place's relations once derived (score/review/holders):
    the recesses its moving doors need in their holder models (recessed). Here, not in surface_data.py or bake_job.py,
    whose code the people line's paid rows hash too."""
    import surface_data
    found = surface_data.DESIGN.parent / "relations" / f"{place}.json"
    return {**surface_data.bake_files(place),
            **({"relations": "{home}/design/relations/" + f"{place}.json"} if found.is_file() else {})}


def bake_job_step(inputs, out):
    """On the rented card, after the paint (inside/paint_bake.py hands it here): the take's models' make_chunky
    entries over its labelled take (bake_job.entry_of), kept in entries/<take>.json, and its make_chunky job (the head
    with them)."""
    import bake_job
    data = place_line.data_of(inputs)
    take = inputs[place_line.TAKE].name
    labelled = out / "labelled" / take
    head = json.loads(inputs[HEAD].read_text())
    built = bake_job.code_built(take, inputs[place_line.HOME])
    box = bake_job.drawn_box(take, [path for name, path in inputs.items() if name.startswith("inventory ")])
    entries = {model: dict(bake_job.entry_of(model, data["bake"].get("entries", {}).get(model), labelled, built, box),
                           name=model, parts=str(labelled), regions=[])
               for model in head.pop("models")}
    relations = json.loads(inputs["relations"].read_text()) if "relations" in inputs else None
    entries = recessed(entries, relations)
    (out / "entries").mkdir(exist_ok=True)
    (out / "entries" / f"{take}.json").write_text(json.dumps(entries, indent=1))
    chunky = [dict(entry, stands=stands(labelled)) for entry in entries.values()]
    inputs[CHUNKY].write_text(json.dumps(dict(head, chunky=chunky, out=str(out / "made"), report=f"report-{take}.json"),
                                         indent=1))


def bake_faults(folder):
    return place_line.bake_faults(folder) or ([] if (folder / "painted.json").exists() else ["no painted.json"])


def judge_baked(output, inputs, evidence):
    """Every take of the parts came back painted and baked, and every model the place lays that another place claims
    is baked by that place (place_line.judge_baked's, its paint in this output)."""
    baked = json.loads((output / "baked.json").read_text())
    takes = json.loads((prop_env.short(inputs)["parts"] / "parts.json").read_text())["takes"]
    failing = [f"{take}: not baked (no model of the place's data takes it)" for take in takes
               if take not in {entry["parts"] for entry in baked.values()}]
    claimed = json.loads((output / "elsewhere.json").read_text())
    failing += [f"{model}: claimed by {claim['place']}, which does not bake {claim['take']}"
                for model, claim in claimed.items() if claim["baked_as"] is None]
    return gates.verdict("baked", failing, len(takes) + len(claimed), "models not baked here or by their claim")


STEPS = {"bake-job": bake_job_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
