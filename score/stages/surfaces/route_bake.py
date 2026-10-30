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
import shutil
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
CLOSEUP = "bake close-up"  # the listing's: a Pixal3D take's close-up as Pixal3D cut it out (stood_square)
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


def own_parts(short, out, take, method):
    """The take's own parts as its job reads them, beside the output: a parts folder holding its parts.json record and
    its parts files alone, so its job (its content, the kept job it finds: tools/cloud/kept.py) moves with its own
    take, never with another take of the place or the parts output's new folder (#36, 2026-10-30: one retaken take
    baked every take of its place again)."""
    folder = out / f".bake-{take}-parts"
    shutil.copytree(short["parts"] / take, folder / take)
    (folder / "parts.json").write_text(json.dumps({"takes": {take: method["takes"][take]}}))
    return folder


def job_files(short, out, records, heads, method):
    """Each take's part records, claimed rows, job head (`heads`: {take: the head with its models}) and own parts
    (own_parts) written beside the output: {take: (records, claimed, head, parts)}."""
    found = {}
    for take, head in heads.items():
        found[take] = (*(out / f".bake-{take}-{what}.json" for what in ("records", "claimed", "head")),
                       own_parts(short, out, take, method))
        found[take][0].write_text(json.dumps(records[take]))
        found[take][1].write_text(json.dumps({take: place_line.claimed_rows(take, short)}))
        found[take][2].write_text(json.dumps(head))
    return found


def made_of(out, take):
    """The folder a take's job bakes its models into and brings back, its own: a folder two jobs share comes back with
    either's copy, so a kept take was baked again beside any retaken take of its machine (#36, 2026-10-30).
    make_bake gathers each into made/ after the jobs (gathered)."""
    return out / f".bake-{take}-made"


def gathered(folder, made):
    """Every file a take's job baked into its own folder moved into the row's made/, where its readers find it."""
    made.mkdir(exist_ok=True)
    for path in sorted(folder.rglob("*")) if folder.is_dir() else ():
        if path.is_file():
            (made / path.relative_to(folder)).parent.mkdir(parents=True, exist_ok=True)
            path.replace(made / path.relative_to(folder))


def card_job(short, out, take, files):
    """One take's cloud job file: its listing (what its paint and bake read of the make's inputs: the place's world
    files and the take's own parts; the take, its part records, claimed rows and job head) and every file it reads at
    its own path; its labelled take, its baked models and their entries come back."""
    listing = out / f".bake-{take}.json"
    records, claimed, head, parts = files
    world = {name: path for name, path in short.items()
             if name.startswith("inventory ") or name in ("surfaces", "resting rules", "relations", "stance rules")}
    pixal = prop_env.PROPS_HOME / "work/pixal"
    closeup = [path for path in [pixal / f"{take}.svviews" / "input.png"] if path.exists()]
    listing.write_text(json.dumps({**{name: str(path) for name, path in world.items()}, "surfaces-parts": str(parts),
                                   place_line.TAKE: take,
                                   place_line.RECORDS: str(records), place_line.CLAIMED: str(claimed),
                                   place_line.HOME: str(prop_env.PROPS_HOME), place_line.CODE: str(place_line.REPO),
                                   HEAD: str(head), CHUNKY: str(out / f".bake-{take}-chunky.json"),
                                   **{CLOSEUP: str(path) for path in closeup}}))
    models = sorted({pixal / f"{take}.glb", pixal / f"{take}-final.glb", *pixal.glob(f"{take}-[0-9]*.glb")})
    mark = [path for path in [pixal / f"{take}.svviews" / "code.json"] if path.exists()]  # a code build's (bake_job)
    read = [listing, records, claimed, head, parts, *world.values(), *models, *mark, *closeup,
            *(place_line.REPO / folder for folder in (*place_line.PAINT_REPO, *BAKE_REPO))]
    job = out / f".bake-{take}-job.json"
    job.write_text(json.dumps({"script": SCRIPT, "args": [str(listing)], "inputs": [str(path) for path in read],
                               "outputs": [str(out / "labelled" / take), str(made_of(out, take)),
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
    head = job_head(data, short, records)  # every take's specs: specs.json's
    models = {model: take for model, take in data["bake"]["models"].items() if take in method["takes"]}
    heads = {take: dict(job_head(data, short, {take: records[take]}),  # a job's head: its own take's specs alone
                        models=sorted(model for model, its in models.items() if its == take))
             for take in sorted(set(models.values()))}
    files = job_files(short, out, records, heads, method)
    jobs = [card_job(short, out, take, files[take]) for take in heads]
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(place_line.REPO / "tools/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", f"surfaces-bake-{data['place']}", "--classes", place_line.CLASSES],
                          cwd=place_line.REPO, capture_output=True, text=True)
    (out / "bake.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    unbaked = sorted(take for take in heads if not (out / "labelled" / take / "labels.json").exists()
                     or not (out / "entries" / f"{take}.json").exists())
    if done.returncode and len(unbaked) == len(heads):
        raise RuntimeError(f"blender_cloud.py paint and bake failed: {done.stderr[-3000:]}")
    for take in heads:
        gathered(made_of(out, take), out / "made")
    for path in out.glob(".bake-*"):
        shutil.rmtree(path) if path.is_dir() else path.unlink()
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
    origin across and deep) at the model's built `size`: on the face its `axis` and `side` name, the door's `wide`
    with its `room` beside it on its `room_side` (a swing's hinge side, a slide's way; both sides at 0), its middle
    `along` the face kept within the face's span less RECESS_BACK at each end (shrunk to that where wider), so a side
    wall stands beside it, as the assembly keeps a door within its holder's (fitting.on_holder), from its `base` to its
    top within the model's height, `depth` deep into the model but never past RECESS_BACK of its far side. Kept flush
    with the span's end, base's garage door recess (its `along` -7.695 past the module's half width 5.371) cut its
    module's W side wall away too (#72, 2026-10-29)."""
    wide, tall, deep = (float(side) for side in size)
    axis, across = (0, 2) if recess["axis"] == "x" else (2, 0)
    half, span = (wide if axis == 0 else deep) / 2, (deep if axis == 0 else wide)
    room, room_side = float(recess.get("room") or 0.0), float(recess.get("room_side", 1.0))
    inside = span - 2 * RECESS_BACK  # the span less a side wall at each end
    opening = min(inside, float(recess["wide"]) + room * (1.0 if room_side else 2.0))  # its room beside it, or both
    middle = float(recess["along"]) + room_side * room / 2
    middle = min(max(middle, -inside / 2 + opening / 2), inside / 2 - opening / 2)
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
                                                                         dict(recess, along=along, room_side=side))}
                                                   for along, side in zip(recess.get("pieces") or [recess["along"]],
                                                                          recess.get("room_sides")
                                                                          or [recess.get("room_side", 1.0)])]
    return found


def take_rows(inputs):
    """Every row of the hand-ins among the inputs."""
    return [row for name, path in inputs.items() if name.startswith("inventory ") and pathlib.Path(path).exists()
            for row in json.loads(pathlib.Path(path).read_text()).get("rows", [])]


def labelled_mesh(labelled):
    """(vertices, triangles) of the labelled take's parts, in the finished model's glTF frame."""
    import numpy as np
    import trimesh
    meshes = [trimesh.load(path, force="mesh", process=False) for path in sorted(pathlib.Path(labelled).glob("*.ply"))]
    starts = np.cumsum([0, *(len(mesh.vertices) for mesh in meshes)])
    return (np.vstack([mesh.vertices for mesh in meshes]),
            np.vstack([mesh.faces + start for mesh, start in zip(meshes, starts)]))


def labelled_points(labelled):
    """The labelled take's vertices (its parts, in the finished model's glTF frame)."""
    return labelled_mesh(labelled)[0]


def fitted(points, size):
    """Points fitted to the model's built `size` along each axis, about their box's middle, as make_chunky fits it."""
    low, high = points.min(axis=0), points.max(axis=0)
    return (points - (low + high) / 2) / (high - low).clip(1e-9) * [float(side) for side in size]


def outlines(points, triangles, poses, size, closeup, row):
    """Each pose's (3 by 3, kit frame) best outline against the close-up (take_outline.best) of the take fitted to
    its `size`, at the look-down its row's close-up was drawn at (its `read_size` or `size`)."""
    import take_outline
    target = take_outline.cut(closeup)
    down = take_outline.look_down((row or {}).get("read_size") or (row or {}).get("size"))
    return [take_outline.best(fitted(points @ pose.T, size), triangles, target, down) for pose in poses]


def stood_square(entries, labelled, take, inputs, built=False):
    """`entries` with each model whose take stands tumbled in its turn (tumble.tumbled, #36) turned to stand square
    (tumble.square_turn, its box's proportions the row's), its `stood` saying so with the turn it was made in
    (`made`); a row the guard list keeps (tumble.keeps_pose: a person, a code build (`built`), lying, leaning,
    hanging, no up) keeps its pose, `stood` saying why. A Pixal3D take (its close-up among the inputs, CLOSEUP) is
    turned only when its turned pose's outline against its close-up is at least its made pose's (outlines), else kept
    as made, `stood` saying why with both (#36, 2026-10-30: lab's desk_divider outlined 0.467 as made, 0.296 turned).
    The bake measures each again as baked (squared_again)."""
    import numpy as np
    import tumble
    rules, rows = tumble.rules_of(inputs), take_rows(inputs)
    points, triangles = labelled_mesh(labelled)
    found = {}
    for model, entry in entries.items():
        base = np.array(entry["base"], float).reshape(3, 3)
        laid = points @ base.T
        row = tumble.take_row(take, model, rows)
        kept = tumble.keeps_pose(row, rules, rows, built)
        degrees, loose = tumble.measure(laid)
        if kept or not tumble.tumbled(laid):
            found[model] = dict(entry, **({"stood": {"kept": kept, "degrees": degrees}} if kept else {}))
            continue
        turn = tumble.square_turn(laid, entry["size"]) @ base
        after, _ = tumble.measure(points @ turn.T)
        stood = {"degrees": degrees, "loose": loose, "after": after, "made": entry["base"]}
        if CLOSEUP in inputs:
            made, turned = outlines(points, triangles, (base, turn), entry["size"], inputs[CLOSEUP], row)
            stood["outline"] = {"made": made, "turned": turned}
            if turned < made:
                found[model] = dict(entry, stood=dict(stood, kept=f"turned square its outline against its close-up "
                                                                   f"was {turned}, under its made pose's {made}: kept "
                                                                   "as made"))
                continue
        found[model] = dict(entry, base=[round(float(value), 6) for value in turn.reshape(-1)], stood=stood)
    return found


# How many times the bake measures a take's cut-down copy as it bakes (fitted to its size, remeshed, its feet
# levelled: make_chunky --shapes) with surfaces-check's own measure (tumble.measure on the made mesh), turning it again
# while it still stands off square: habitat's stove stood 7.1 degrees on its labelled take, 10.7 fitted to its size
# and 12.6 baked; stairwell's extinguisher 25.5 degrees but loose 1.17 on its take, 1.28 baked (#36, 2026-10-29). A
# turned take still more than tumble.DEGREES off after the last takes back the turn it was made in, `stood` saying
# why, so a turn never leaves it worse (hangar's pipe valves, turned from 32.8 to 12.4 degrees on their unsteady
# box, went from likeness 0.461 to 0.363).
SQUARE_ROUNDS = 3


def squared_again(entries, shapes, measured):
    """(`entries` after a measuring of their cut-down copies as baked, the models to bake and measure again):
    `shapes` {model: its copy's points in the kit frame (x across, y up)} of the models measured, `measured` how many
    times they have been. A copy standing square (not tumble.tumbled, and within tumble.DEGREES where the bake turned
    it) is done; one off square is turned again by its copy (tumble.square_turn, before its turn) until SQUARE_ROUNDS,
    after which a turned one still more than tumble.DEGREES off takes back the turn it was made in (`made`), `stood`
    saying why, and a never turned one stays as it was made. Each measure is kept in `stood`'s `baked`."""
    import numpy as np
    import tumble
    found, again = dict(entries), []
    for model, points in shapes.items():
        entry = found[model]
        stood = dict(entry.get("stood") or {})
        made = stood.get("made", entry["base"])
        degrees, loose = tumble.measure(points)
        stood["baked"] = [*stood.get("baked", []), [degrees, loose]]
        turned = entry["base"] != made
        square = not (degrees > tumble.DEGREES and loose > tumble.LOOSE) and (not turned or degrees <= tumble.DEGREES)
        if square:
            found[model] = dict(entry, stood=stood)
        elif measured < SQUARE_ROUNDS:
            turn = tumble.square_turn(points, entry["size"]) @ np.array(entry["base"], float).reshape(3, 3)
            found[model] = dict(entry, base=[round(float(value), 6) for value in turn.reshape(-1)],
                                stood=dict(stood, made=made))
            again.append(model)
        elif turned:
            found[model] = dict(entry, base=made, stood=dict(
                stood, kept=f"its turn left it {degrees} degrees off its frame as baked: kept as made"))
        else:
            found[model] = dict(entry, stood=stood)
    return found, again


def square_again_step(inputs, out):
    """On the rented card, after make_chunky --shapes wrote the pending models' cut-down copies (the `square` of the
    take's make_chunky job): squared_again over them, its entries and its job written again with the models still to
    measure."""
    import numpy as np
    take = inputs[place_line.TAKE].name
    job = json.loads(inputs[CHUNKY].read_text())
    square = job["square"]
    folder = pathlib.Path(square["folder"])
    shapes = {model: np.load(folder / f"{model}.npy") for model in square["pending"]
              if (folder / f"{model}.npy").exists()}
    written = out / "entries" / f"{take}.json"
    entries, again = squared_again(json.loads(written.read_text()), shapes, square["round"] + 1)
    written.write_text(json.dumps(entries, indent=1))
    job["chunky"] = [dict(entry, base=entries[entry["name"]]["base"], stood=entries[entry["name"]].get("stood"))
                     for entry in job["chunky"]]
    job["square"] = dict(square, round=square["round"] + 1, pending=again)
    inputs[CHUNKY].write_text(json.dumps(job, indent=1))


def bake_files(place):
    """The bake row's files (surface_data.bake_files), the pose rules it stands takes square by (stood_square:
    stance.json's lying classes, the resting rules' ground debris) and the place's relations once derived
    (score/review/holders): the recesses its moving doors need in their holder models (recessed). Here, not in surface_data.py or bake_job.py,
    whose code the people line's paid rows hash too."""
    import surface_data
    found = surface_data.DESIGN.parent / "relations" / f"{place}.json"
    return {**surface_data.bake_files(place), "stance rules": "{data}/checks/stance.json",
            "close-up view": "{repo}/tools/props/closeup/check.py",  # take_outline's look-down, loaded by its path
            "resting rules": "{data}/checks/resting.json",
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
    guard = bake_job.drawn_guard(take, [path for name, path in inputs.items() if name.startswith("inventory ")],
                                 inputs)
    entries = {model: dict(bake_job.entry_of(model, data["bake"].get("entries", {}).get(model), labelled, built,
                                             *guard), name=model, parts=str(labelled), regions=[])
               for model in head.pop("models")}
    relations = json.loads(inputs["relations"].read_text()) if "relations" in inputs else None
    entries = recessed(stood_square(entries, labelled, take, inputs, built), relations)
    (out / "entries").mkdir(exist_ok=True)
    (out / "entries" / f"{take}.json").write_text(json.dumps(entries, indent=1))
    chunky = [dict(entry, stands=stands(labelled)) for entry in entries.values()]
    square = {"round": 0, "folder": str(out / "shapes" / take),
              "pending": [model for model, entry in entries.items() if not (entry.get("stood") or {}).get("kept")]}
    inputs[CHUNKY].write_text(json.dumps(dict(head, chunky=chunky, out=str(made_of(out, take)),
                                              report=f"report-{take}.json", square=square), indent=1))


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


STEPS = {"bake-job": bake_job_step, "square-again": square_again_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
