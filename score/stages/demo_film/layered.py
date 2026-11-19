"""A place's film drawn in layers (owner, 2026-11-19: "render a place's background once and the people on top", and
"for the layered datasets story, cheap rendering is gonna be important"): the place without its people drawn once a
frame of each shot, each walker and each peel layer (the peeled walker's player model, SOMA body and sim body with
its GRF arrows and muscle colours) drawn on its own over it with its shadows and light on the place (Blender's shadow
catcher, blender/layered.py), and the film composited from them (blender/compose.py). Every layer's frames are kept
in the SCORE store, each frame under a key of what it shows (its layer's own content, the place's, the camera, the
size and samples, the drawing code), so a frame made once is never made again, and a changed walker changes only its
own layers' keys: fixing it draws only them, and the film is composed again from the kept rest.

    python -m score.stages.demo_film.layered preview <scene folder> <folder> --rows <rows.json> [--walker <name>]
    python -m score.stages.demo_film.layered draw <scene folder> <folder> --rows <rows.json> [--walker <name>]
        [--size 1920 1080] [--review] [--views <shot>/<view> ...] [--redraw <layer> ...] [--local]
        [--on processor|card|cloud] [--slices 8] [--minutes 120]
    python -m score.stages.demo_film.layered match <scene folder> <folder> --rows <rows.json> --views <shot>/<view> ...
        [--size 480 270] [--review]

The film is the place's walk-through (the scene's film/path.json, shot `walk`) and its walker peel (peel.walker_job,
shot `peel`), as the demo's place films are cut. A layer is `background`, `walker:<name>` (each walker under the
stage's Characters, its names the walkers layer's characters.json), `soma:<walker>` and `sim:<walker>` (the peeled
walker's SOMA surface and sim body; its player model is its walker layer). A picture is the background and the layers
it shows: a walk-through frame every walker; a peel pass the walkers but the peeled one, and the pass's own layer of
it (dressed: its walker layer, mesh: soma, sim: sim); the peel's opening every walker on the concept's view.

`preview` is the standard look every film passes before its final (owner, 2026-11-19): the whole film at
PREVIEW_SIZE and the review's samples, every PREVIEW_EVERY film frame (4 a second) drawn in layers on this machine's
processor (free), composed and joined as the film joins them, laid out as contact sheets (`sheets/<n>.jpg`, SHEET
frames each, their film time on each), and checked: no black frame, no frame the same as the one before, a walker in
some walk-through frame, and the peeled walker's layer in view on every frame from its close-up on. Its record,
`<folder>/preview/preview.json`, names the film's key (every camera of both shots, the peel's passes and every
layer's key) and its verdict. `draw` without `--review` is a final: refused unless that record passed for the same
film key. `draw` keeps each frame on disk and in the store, draws only the frames neither holds (`--redraw` a layer:
its frames drawn again whatever is kept), on this machine's processor (`processor`, free), its card through the card
queue (`card`), or written as blender_cloud jobs over `--slices` (`cloud`: run them with tools/cloud/blender_cloud.py
--detach, then `draw` again, which keeps what they drew and composes), and composes `<folder>/film.mp4`. `match`
draws the same frames whole (blender_views.py, walker_peel.py, as the films were drawn before) and measures the
composite against them (TOLERANCE), the layering's proof on a place: `<folder>/match/match.json`.

The store is the framework's (Store.default()); each frame's EXR a blob there and its record `film-layers/<key>.json`
beside the objects, both pushed to the store bucket (score/store/offload: the SCORE store's bucket) and read back
from it where this machine does not hold them; `--local` keeps them in this machine's store alone (a trial).
"""
import argparse
import json
import pathlib
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw

from score.store import Store, file_hash, text_hash, tree_listing

REPO = pathlib.Path(__file__).resolve().parents[3]
BLENDER_FOLDER = REPO / "score/stages/demo_film/blender"
LAYERED_SCRIPT = BLENDER_FOLDER / "layered.py"
WALKER_SCRIPT = BLENDER_FOLDER / "walker_peel.py"
COMPOSE_SCRIPT = BLENDER_FOLDER / "compose.py"
VIEWS_SCRIPT = REPO / "score/stages/place_build/blender_views.py"
# What draws a frame: a change to the place's drawing is a new key for every frame, to the peel's drawing only for
# the peel's layers.
PLACE_CODE = (LAYERED_SCRIPT, VIEWS_SCRIPT, REPO / "tools/blender/inside/usd_views.py")
PEEL_CODE = (WALKER_SCRIPT, BLENDER_FOLDER / "body_peel.py")
BACKGROUND = "background"
WALK, PEEL = "walk", "peel"
INDEX = "film-layers"  # the store's records of kept frames: film-layers/<key>.json
WALKERS = "layers/walkers"  # the scene's walkers layer: its people, kept out of the place's own key
PASS_LAYER = {"dressed": "walker", "mesh": "soma", "sim": "sim"}
RATE = 24
PREVIEW_SIZE = (480, 270)
FINAL_SIZE = (1920, 1080)
PREVIEW_EVERY = 6  # film frames between a preview's frames: 4 a second
SHEET = (6, 4)  # a contact sheet's frames across and down: 6 s of film
TILE = (320, 180)
BLACK = 8.0  # a frame whose mean is under this (of 255) is black
STILL = 0.5  # a frame whose mean difference from the one before is under this (of 255) did not move
SEEN = 0.002  # the share of the picture a walker's layer covers to be in view
# The composite against a whole render of the same frames, 8-bit levels over every pixel and channel (the proof's
# limits: Cycles' own noise between two renders at the review's samples, each layer denoised on its own).
TOLERANCE = {"mean": 2.0, "p99": 24.0}
PROCESSOR_THREADS = "12"
PROCESSOR_MEMORY = "12G"


class Refused(RuntimeError):
    """A film the layering cannot draw or compose as asked."""


# --- keys -------------------------------------------------------------------------------------------------------

def code_key(files):
    return text_hash(json.dumps([file_hash(path) for path in files]))


def walkers_of(scene):
    """The scene's walkers ({name: look}), from its walkers layer's characters.json; none without one."""
    found = pathlib.Path(scene) / WALKERS / "characters.json"
    return {name: entry["look"] for name, entry in json.loads(found.read_text())["looks"].items()} \
        if found.exists() else {}


def place_files(listing):
    """The scene's files the place is drawn from ({path: sha256}): its stages, assets, layers and records, never its
    walkers layer, its reviews or its film's outputs."""
    return {name: sha for name, sha in listing.items()
            if not name.startswith(WALKERS + "/") and (name.startswith(("layers/", "assets/")) or
                                                       ("/" not in name and name.endswith((".usda", ".usdc", ".usd")))
                                                       or name in ("palette.json", "place.json"))}


def walker_block(text, name):
    """A walker's own lines in the walkers layer (its `def SkelRoot "<name>"` to the next walker's)."""
    start = text.find(f'def SkelRoot "{name}"')
    if start < 0:
        raise Refused(f"the walkers layer holds no walker {name}")
    end = text.find("def SkelRoot ", start + 1)
    return text[start:end if end >= 0 else len(text)]


def scene_keys(scene, walkers, code):
    """{"background": the place's key, "walker:<name>": each walker's}: the place's from its own files and the code;
    a walker's from the place's, its own lines in the walkers layer and its look's files there."""
    listing = tree_listing(scene)
    place = text_hash(json.dumps({"files": place_files(listing), "code": code}, sort_keys=True))
    keys = {BACKGROUND: place}
    layer = pathlib.Path(scene) / WALKERS / "layers" / "characters.usda"
    text = layer.read_text() if layer.exists() else ""
    for name, look in walkers.items():
        stem = look.replace("/", "-")
        files = {path: sha for path, sha in listing.items()
                 if path.startswith(WALKERS + "/assets/") and pathlib.Path(path).name.startswith(stem)}
        keys[f"walker:{name}"] = text_hash(json.dumps({"place": place, "lines": text_hash(walker_block(text, name)),
                                                      "files": files}, sort_keys=True))
    return keys


def arrays_hash(path):
    """An .npz's arrays' own bytes hashed (the file holds the time it was written)."""
    held = np.load(path)
    return text_hash(json.dumps({name: text_hash(held[name].tobytes().hex()) for name in sorted(held.files)}))


def peel_keys(job, walker_key, sim_layer):
    """{"soma:<walker>", "sim:<walker>"}: the peeled walker's, its job's arrays, its sim body layer and the job's
    arrows and muscles."""
    person = job["people"][0]
    shared = {"walker": walker_key, "arrays": arrays_hash(person["arrays"]), "arrows": job["arrows"],
              "muscles": job["muscles"]}
    return {f"soma:{job['walker']}": text_hash(json.dumps(dict(shared, layer="soma"), sort_keys=True)),
            f"sim:{job['walker']}": text_hash(json.dumps(dict(shared, layer="sim", timed=file_hash(person["sim_layer"]),
                                                              sim=file_hash(sim_layer)), sort_keys=True))}


def camera_of(view):
    """What a view's camera and moment are, for a key: the view less its name and drawing marks."""
    return {name: value for name, value in view.items() if name not in ("name", "layers", "look_only")}


def frame_key(layer_key, view, size, review):
    return text_hash(json.dumps({"layer": layer_key, "camera": camera_of(view), "size": list(size),
                                 "review": bool(review)}, sort_keys=True))


def film_key(shots, keys):
    """The film's key: every view's camera of both shots, the peel's passes and every layer's key; never its size or
    samples (a preview and its final share it)."""
    return text_hash(json.dumps({"shots": {shot: {"views": [dict(camera_of(view), name=view["name"])
                                                            for view in made["views"]],
                                                  "pictures": made["pictures"]} for shot, made in shots.items()},
                                 "keys": keys}, sort_keys=True))


# --- the shots and their pictures --------------------------------------------------------------------------------

def walk_shot(scene, walkers):
    """The walk-through: its views (the scene's film path) and its pictures, each a frame of every walker."""
    views = json.loads((pathlib.Path(scene) / "film" / "path.json").read_text())["views"]
    layers = [f"walker:{name}" for name in walkers]
    return {"views": views, "pictures": [{"out": f"{WALK}/{view['name']}.png", "view": view["name"],
                                          "layers": layers} for view in views]}


def peel_shot(listing, job, walkers):
    """The walker peel: its views (peel.walker_job's) and its pictures, one a pass a frame draws (`<pass>/<frame>`)
    and the opening's (`opening/<frame>`)."""
    walker = job["walker"]
    others = [f"walker:{name}" for name in walkers if name != walker]
    pictures = []
    for view in listing["views"]:
        frame = int(view["name"][1:5])
        if view["name"].startswith("o"):
            pictures.append({"out": f"{PEEL}/opening/{frame:04d}.png", "view": view["name"],
                             "layers": [*others, f"walker:{walker}"], "frame": frame})
            continue
        for name in job["draws"][frame]:
            pictures.append({"out": f"{PEEL}/{name}/{frame:04d}.png", "view": view["name"], "frame": frame,
                             "layers": [*others, f"{PASS_LAYER[name]}:{walker}"]})
    return {"views": listing["views"], "pictures": pictures}


def sampled(shots, every):
    """The shots kept to every `every`-th film frame (a walk-through view's index, a peel's film frame)."""
    if every <= 1:
        return shots
    walk = shots[WALK]
    names = {view["name"] for index, view in enumerate(walk["views"]) if index % every == 0}
    kept = {WALK: {"views": [view for view in walk["views"] if view["name"] in names],
                   "pictures": [picture for picture in walk["pictures"] if picture["view"] in names]}}
    peel = shots[PEEL]
    pictures = [picture for picture in peel["pictures"] if picture["frame"] % every == 0]
    used = {picture["view"] for picture in pictures}
    kept[PEEL] = {"views": [view for view in peel["views"] if view["name"] in used], "pictures": pictures}
    return kept


def picked(shots, wanted):
    """The shots kept to the named views (`<shot>/<view>`), all where none are named."""
    if not wanted:
        return shots
    names = {tuple(name.split("/", 1)) for name in wanted}
    unknown = sorted(f"{shot}/{view}" for shot, view in names
                     if shot not in shots or view not in {made["name"] for made in shots[shot]["views"]})
    if unknown:
        raise Refused(f"no view {', '.join(unknown)} in the film")
    return {shot: {"views": [view for view in made["views"] if (shot, view["name"]) in names],
                   "pictures": [picture for picture in made["pictures"] if (shot, picture["view"]) in names]}
            for shot, made in shots.items()}


def needed(shots, keys, size, review):
    """{(shot, view, layer): frame key} of every layer frame the pictures want, the background's included."""
    found = {}
    for shot, made in shots.items():
        views = {view["name"]: view for view in made["views"]}
        for picture in made["pictures"]:
            for layer in [BACKGROUND, *picture["layers"]]:
                found[(shot, picture["view"], layer)] = frame_key(keys[layer], views[picture["view"]], size, review)
    return found


def frame_path(folder, shot, view, layer, suffix):
    return pathlib.Path(folder) / "layers" / shot / layer.replace(":", "-") / f"{view}{suffix}"


# --- the store ---------------------------------------------------------------------------------------------------

class Kept:
    """The layers' frames in the SCORE store: each frame's EXR a blob, its record `film-layers/<key>.json`; with a
    bucket (score/store/offload's), both pushed to it, and read from it where this machine holds neither."""

    def __init__(self, store, bucket=None):
        self.store, self.bucket = store, bucket

    def record_key(self, key):
        return f"{INDEX}/{key}.json"

    def find(self, key):
        """The frame's record ({key, border or empty, blob}), or None where neither the store nor its bucket holds it."""
        if self.store.objects.exists(self.record_key(key)):
            return json.loads(self.store.objects.read_bytes(self.record_key(key)))
        if self.bucket is None or self.bucket.answer(self.record_key(key)) is None:
            return None
        with tempfile.TemporaryDirectory() as spare:
            self.bucket.fetch(self.record_key(key), pathlib.Path(spare) / "record.json")
            record = json.loads((pathlib.Path(spare) / "record.json").read_text())
        self.store.objects.write_bytes(self.record_key(key), json.dumps(record).encode())
        return record

    def keep(self, key, exr, record):
        """A drawn frame kept: its EXR (none for an empty layer) as a blob, its record beside, the bucket's too."""
        if exr is not None:
            record = dict(record, blob=file_hash(exr))
            self.store.put_blob(exr, record["blob"])
        data = json.dumps(record).encode()
        if not self.store.objects.exists(self.record_key(key)):
            self.store.objects.write_bytes(self.record_key(key), data)
        if self.bucket is not None:
            from score.store import offload
            if exr is not None:
                offload.push(self.store.objects.path(f"blobs/{record['blob']}"), record["blob"], self.bucket)
            with tempfile.TemporaryDirectory() as spare:
                path = pathlib.Path(spare) / "record.json"
                path.write_bytes(data)
                self.bucket.put_new(path, self.record_key(key), text_hash(data.decode()))
        return record

    def place(self, record, exr):
        """A kept frame on disk at `exr` (a read-only link to its blob, fetched from the bucket where it is not
        here)."""
        if self.bucket is not None and not self.store.objects.exists(f"blobs/{record['blob']}"):
            from score.store import offload
            offload.OPENER["bucket"] = self.bucket
            offload.fetched(self.store.objects.root, record["blob"])
        self.store.place_blob(record["blob"], exr)


def on_disk(folder, at, key):
    """The drawn frame's record on disk when its sidecar names this key, else None."""
    shot, view, layer = at
    sidecar = frame_path(folder, shot, view, layer, ".json")
    if not sidecar.exists():
        return None
    record = json.loads(sidecar.read_text())
    return record if record.get("key") == key else None


def gathered(folder, wanted, kept, redraw=()):
    """The wanted frames on disk: each drawn one kept in the store, each the store holds placed; the ones neither
    holds (and every frame of a `redraw` layer not drawn since) returned to draw, their stale files gone."""
    missing = {}
    for at, key in wanted.items():
        record = on_disk(folder, at, key)
        exr = frame_path(folder, *at, ".exr")
        if record is not None and (record.get("empty") or exr.exists()):
            if at[2] not in redraw:
                kept.keep(key, None if record.get("empty") else exr, record)
                continue
        found = None if at[2] in redraw else kept.find(key)
        exr.unlink(missing_ok=True)
        frame_path(folder, *at, ".json").unlink(missing_ok=True)
        if found is None:
            missing[at] = key
            continue
        if not found.get("empty"):
            kept.place(found, exr)
        exr.parent.mkdir(parents=True, exist_ok=True)
        frame_path(folder, *at, ".json").write_text(json.dumps({name: found[name] for name in found if name != "blob"}))
    return missing


# --- drawing -----------------------------------------------------------------------------------------------------

def to_draw(shot, made, missing):
    """The shot's views that have frames to draw, each naming its layers ({layer: frame key})."""
    layers = {}
    for (named, view, layer), key in missing.items():
        if named == shot:
            layers.setdefault(view, {})[layer] = key
    return [dict(view, layers=layers[view["name"]]) for view in made["views"] if view["name"] in layers]


def listings(folder, scene, shots, missing, size, review, peel_folder):
    """The Blender jobs drawing the missing frames: [(name, script, arguments)], each listing written."""
    from score.stages import place_build
    usda = str(place_build.scene_path(scene).resolve())
    jobs = []
    walk = to_draw(WALK, shots[WALK], missing)
    if walk:
        listed = pathlib.Path(folder) / "layers" / "walk.json"
        listed.parent.mkdir(parents=True, exist_ok=True)
        listed.write_text(json.dumps({"size": list(size), "review": review, "views": walk,
                                      "layered": str(pathlib.Path(folder) / "layers" / WALK)}, indent=1))
        jobs.append(("walk", LAYERED_SCRIPT, [usda, str(listed), str(pathlib.Path(folder) / "layers" / "walk-out")]))
    peel = to_draw(PEEL, shots[PEEL], missing)
    if peel:
        job = json.loads((peel_folder / "job.json").read_text())
        layered_job = peel_folder / "job-layered.json"
        layered_job.write_text(json.dumps(dict(job, layered={"out": str(pathlib.Path(folder) / "layers" / PEEL)}),
                                          indent=1))
        listed = pathlib.Path(folder) / "layers" / "peel.json"
        listed.write_text(json.dumps({"size": list(size), "review": review, "views": peel,
                                      "peel": str(layered_job)}, indent=1))
        jobs.append(("peel", WALKER_SCRIPT, [usda, str(listed), str(pathlib.Path(folder) / "layers" / "peel-out")]))
    return jobs


def processor_command(script, arguments):
    """Blender on this machine's processor (Cycles, FARM_CYCLES_CPU), PROCESSOR_THREADS, in a memory-capped scope."""
    from score.stages.place_build import render as place_render
    linked = ":".join(filter(None, [place_render.libraries(), "/usr/lib/wsl/lib"]))
    return ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={PROCESSOR_MEMORY}", "-p",
            "MemorySwapMax=0", "--setenv=FARM_CYCLES_CPU=1", f"--setenv=LD_LIBRARY_PATH={linked}",
            str(place_render.BLENDER), "-b", "-t", PROCESSOR_THREADS, "-setaudio", "None", "--python-exit-code", "1",
            "--python", str(script), "--", *arguments]


def ran(command, log):
    """A Blender command run, its output to `log`; refused naming the log's tail when it fails."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as out:
        done = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, cwd=REPO, stdin=subprocess.DEVNULL)
    if done.returncode:
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise Refused(f"exit {done.returncode}, log {log}: {tail}")


def drawn_here(folder, jobs, on):
    """The jobs drawn on this machine: its processor, or its card through the card queue."""
    from score.stages.place_build import render as place_render
    for name, script, arguments in jobs:
        command = processor_command(script, arguments) if on == "processor" else \
            place_render.queued(f"layered-{name}", script, arguments)
        ran(command, pathlib.Path(folder) / "layers" / f"{name}.log")


def cloud_jobs(folder, scene, jobs, inputs, slices, minutes):
    """The jobs dealt into `slices` blender_cloud jobs each (their views split, each its own listing, the layers'
    folders their outputs): the job files written."""
    made = []
    for name, script, arguments in jobs:
        listing = json.loads(pathlib.Path(arguments[1]).read_text())
        out = listing.get("layered") or json.loads(pathlib.Path(listing["peel"]).read_text())["layered"]["out"]
        for index in range(slices):
            part = listing["views"][index::slices]
            if not part:
                continue
            piece = pathlib.Path(folder) / "cloud" / f"{name}-{index:02d}"
            piece.mkdir(parents=True, exist_ok=True)
            (piece / "views.json").write_text(json.dumps(dict(listing, views=part), indent=1))
            job = {"script": str(script.relative_to(REPO)),
                   "args": [arguments[0], str(piece / "views.json"), str(piece / "look")],
                   "inputs": [str(pathlib.Path(scene).resolve()), str(piece / "views.json"), *inputs],
                   "code": ["score/stages/place_build", "tools/props/library", "vendor/procfunc/src",
                            "vendor/infinigen2"],
                   "outputs": [out, str(piece / "look")], "minutes": minutes}
            (piece / "job.json").write_text(json.dumps(job, indent=1))
            made.append(str(piece / "job.json"))
    return made


def composed(folder, shots):
    """Every picture composed (compose.py on this machine's processor, the look its background's record names):
    <folder>/frames/<picture>.png, and its layers' shares in view ({picture: {layer: share}})."""
    pictures = []
    for shot, made in shots.items():
        for picture in made["pictures"]:
            layers = [frame_path(folder, shot, picture["view"], layer, ".exr") for layer in picture["layers"]]
            pictures.append({"out": str(pathlib.Path(folder) / "frames" / picture["out"]),
                             "background": str(frame_path(folder, shot, picture["view"], BACKGROUND, ".exr")),
                             "layers": [str(path) for path in layers if path.exists()],
                             "names": [layer for layer, path in zip(picture["layers"], layers) if path.exists()]})
    if not pictures:
        return {}
    look = json.loads(pathlib.Path(pictures[0]["background"]).with_suffix(".json").read_text())["look"]
    listing = pathlib.Path(folder) / "frames" / "compose.json"
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(json.dumps({"look": look, "pictures": pictures}, indent=1))
    ran(processor_command(COMPOSE_SCRIPT, [str(listing)]), pathlib.Path(folder) / "frames" / "compose.log")
    return json.loads((pathlib.Path(folder) / "frames" / "shares.json").read_text())


# --- the film ----------------------------------------------------------------------------------------------------

def film_shots(scene, folder, inputs, walker, size, review):
    """The film's shots at `size` (the walk-through, and the walker peel's job written into <folder>/peel), every
    layer's key, the peel's folder and job."""
    from score.stages import sim_body
    from score.stages.demo_film import peel, peel_rows
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    walker = walker or peel_rows.walker(inputs, cast)
    walkers = walkers_of(scene)
    if walker not in walkers:
        raise Refused(f"the peeled walker {walker} is none of the scene's walkers ({', '.join(walkers) or 'none'})")
    peel_folder = pathlib.Path(folder) / "peel"
    peel_folder.mkdir(parents=True, exist_ok=True)
    listed = peel.walker_job(peel_folder, scene, cast, pathlib.Path(inputs["sim-body"]),
                             peel_rows.people_of(inputs, clothed=False), walker, size, review)
    listing, job = json.loads(listed.read_text()), json.loads((peel_folder / "job.json").read_text())
    keys = scene_keys(scene, walkers, code_key(PLACE_CODE))
    keys.update(peel_keys(job, text_hash(keys[f"walker:{walker}"] + code_key(PEEL_CODE)),
                          pathlib.Path(inputs["sim-body"]) / sim_body.LAYER))
    return {WALK: walk_shot(scene, walkers), PEEL: peel_shot(listing, job, walkers)}, keys, peel_folder, job


def timeline(shots):
    """{(shot, view or frame): seconds into the film}: the walk-through's frames, then the peel's."""
    walk = {(WALK, view["name"]): index / RATE for index, view in enumerate(shots[WALK]["views"])}
    start = len(shots[WALK]["views"]) / RATE
    frames = {picture["frame"] for picture in shots[PEEL]["pictures"]}
    return {**walk, **{(PEEL, frame): start + frame / RATE for frame in frames}}


def preview_passed(folder, key):
    """Refused unless the film's preview (<folder>/preview/preview.json) passed for this very film."""
    record = pathlib.Path(folder) / "preview" / "preview.json"
    if not record.exists():
        raise Refused(f"no preview of this film in {record.parent}: run the preview before its final")
    made = json.loads(record.read_text())
    if made["film"] != key:
        raise Refused(f"{record} previewed another film (a camera, a pass or a layer changed since): preview again")
    if not made["passed"]:
        raise Refused(f"{record} failed: {'; '.join(made['faults'])}")


def draw(scene, folder, inputs, walker=None, size=FINAL_SIZE, review=False, every=1, views=(), on="processor",
         kept=None, slices=8, minutes=120.0, redraw=()):
    """The film drawn in layers into `folder` (module docstring): {"film" key, "shots", "times", "shares", "job",
    "peel" joined frames' folder, "drawn" frames drawn now, "kept" frames the store held, "film.mp4" when whole};
    with `on` cloud and frames to draw, {"film", "jobs", "missing"} and nothing composed."""
    from score.stages.demo_film import peel
    folder = pathlib.Path(folder)
    shots, keys, peel_folder, job = film_shots(scene, folder, inputs, walker, size, review)
    key = film_key(shots, keys)
    if not review:
        preview_passed(folder, key)
    times = timeline(shots)
    shots = picked(sampled(shots, every), views)
    wanted = needed(shots, keys, size, review)
    kept = kept or Kept(Store.default())
    missing = gathered(folder, wanted, kept, redraw)
    if missing:
        jobs = listings(folder, scene, shots, missing, size, review, peel_folder)
        if on == "cloud":
            inputs_of = [str(peel_folder), str(pathlib.Path(inputs["sim-body"]).resolve())]
            return {"film": key, "jobs": cloud_jobs(folder, scene, jobs, inputs_of, slices, minutes),
                    "missing": len(missing)}
        drawn_here(folder, jobs, on)
        left = gathered(folder, missing, kept)
        if left:
            raise Refused(f"{len(left)} frames were not drawn, the first {'/'.join(next(iter(left)))}")
    shares = composed(folder, shots)
    frames = sorted({picture["frame"] for picture in shots[PEEL]["pictures"]})
    joined = peel.joined(folder / "frames" / PEEL, len(job["draws"]), dissolve=True, ends=job["ends"],
                         cut_in=job.get("cut_in"), frames=frames) if frames else None
    made = {"film": key, "shots": shots, "times": times, "shares": shares, "job": job, "peel": joined,
            "drawn": len(missing), "kept": len(wanted) - len(missing)}
    if every == 1 and not views:
        made["film.mp4"] = str(encoded(folder, shots, joined))
    return made


def film_frames(folder, shots, joined):
    """The film's frames in order: the walk-through's, then the peel's joined ones."""
    walk = [pathlib.Path(folder) / "frames" / WALK / f"{view['name']}.png" for view in shots[WALK]["views"]]
    peel = [joined / f"{frame:04d}.png" for frame in sorted({picture["frame"] for picture in shots[PEEL]["pictures"]})]
    return walk + peel


def encoded(folder, shots, joined):
    """<folder>/film.mp4: the film's frames, H.264 at RATE (no sound: the film's cut lays its own)."""
    listing = pathlib.Path(folder) / "film.txt"
    listing.write_text("".join(f"file '{path}'\nduration {1 / RATE}\n" for path in film_frames(folder, shots, joined)))
    out = pathlib.Path(folder) / "film.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-r",
                    str(RATE), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(out)], check=True)
    return out


# --- the preview -------------------------------------------------------------------------------------------------

def preview_faults(made, walkers):
    """What a preview's frames show wrong (module docstring): black or unmoved frames, no walker in the walk-through,
    the peeled walker out of view from its close-up on."""
    from score.stages.demo_film import peel
    faults, before = [], None
    folder = pathlib.Path(made["peel"]).parents[2] if made["peel"] else None
    job, shares = made["job"], made["shares"]
    ordered = [((WALK, view["name"]), pathlib.Path(made["frames"][WALK]) / f"{view['name']}.png")
               for view in made["shots"][WALK]["views"]]
    ordered += [((PEEL, frame), pathlib.Path(made["peel"]) / f"{frame:04d}.png")
                for frame in sorted({picture["frame"] for picture in made["shots"][PEEL]["pictures"]})]
    for at, path in ordered:
        picture = np.asarray(Image.open(path).convert("RGB"), dtype=float)
        when = made["times"][at]
        if picture.mean() < BLACK:
            faults.append(f"black at {when:.2f} s")
        if before is not None and before[0] == at[0] and np.abs(picture - before[1]).mean() < STILL:
            faults.append(f"unmoved at {when:.2f} s")
        before = (at[0], picture)
    walk_seen = [share for picture in made["shots"][WALK]["pictures"]
                 for share in shares.get(str(pathlib.Path(made["frames"][WALK]) / f"{picture['view']}.png"), {}).values()]
    if walkers and not any(share >= SEEN for share in walk_seen):
        faults.append("no walker in view in the walk-through")
    close = round((peel.OPENING_SECONDS + job["approach_seconds"]) * RATE)
    for frame in sorted({picture["frame"] for picture in made["shots"][PEEL]["pictures"]}):
        if frame < close:
            continue
        shown = peel.PASSES[peel.stage_of(frame, len(job["draws"]), job["ends"], peel.DISSOLVE_SECONDS)[0]]
        layer = f"{PASS_LAYER[shown]}:{job['walker']}"
        share = shares.get(str(folder / "frames" / PEEL / shown / f"{frame:04d}.png"), {}).get(layer, 0.0)
        if share < SEEN:
            faults.append(f"{job['walker']} ({shown}) out of view at {made['times'][(PEEL, frame)]:.2f} s")
    return faults


def sheets(made, out):
    """Contact sheets of the preview's frames (SHEET a sheet, each its film time), <out>/<n>.jpg."""
    out.mkdir(parents=True, exist_ok=True)
    tiles = [(made["times"][(WALK, view["name"])], pathlib.Path(made["frames"][WALK]) / f"{view['name']}.png")
             for view in made["shots"][WALK]["views"]]
    tiles += [(made["times"][(PEEL, frame)], pathlib.Path(made["peel"]) / f"{frame:04d}.png")
              for frame in sorted({picture["frame"] for picture in made["shots"][PEEL]["pictures"]})]
    across, down = SHEET
    written = []
    for number, first in enumerate(range(0, len(tiles), across * down)):
        sheet = Image.new("RGB", (across * TILE[0], down * TILE[1]), (17, 19, 23))
        for place, (when, path) in enumerate(tiles[first:first + across * down]):
            tile = Image.open(path).convert("RGB").resize(TILE)
            ImageDraw.Draw(tile).text((6, 4), f"{when:6.2f} s", fill=(255, 255, 255))
            sheet.paste(tile, ((place % across) * TILE[0], (place // across) * TILE[1]))
        sheet.save(out / f"{number:02d}.jpg", quality=88)
        written.append(str(out / f"{number:02d}.jpg"))
    return written


def preview(scene, folder, inputs, walker=None, kept=None):
    """The film's preview (module docstring) into <folder>/preview: its record."""
    out = pathlib.Path(folder) / "preview"
    made = draw(scene, out, inputs, walker, PREVIEW_SIZE, review=True, every=PREVIEW_EVERY, kept=kept)
    made["frames"] = {WALK: str(out / "frames" / WALK)}
    faults = preview_faults(made, walkers_of(scene))
    record = {"film": made["film"], "passed": not faults, "faults": faults, "sheets": sheets(made, out / "sheets"),
              "frames": sum(len(shot["views"]) for shot in made["shots"].values()), "size": list(PREVIEW_SIZE),
              "every": PREVIEW_EVERY, "drawn": made["drawn"], "kept": made["kept"]}
    (out / "preview.json").write_text(json.dumps(record, indent=1))
    return record


# --- the proof ---------------------------------------------------------------------------------------------------

def whole(folder, scene, made, size, review):
    """The same frames drawn whole, as the films were drawn before layering: the walk-through by blender_views.py,
    the peel by walker_peel.py, into <folder>/match/{walk,peel}."""
    from score.stages import place_build
    usda = str(place_build.scene_path(scene).resolve())
    out = pathlib.Path(folder) / "match"
    out.mkdir(parents=True, exist_ok=True)
    walk = made["shots"][WALK]["views"]
    if walk:
        listed = out / "walk.json"
        listed.write_text(json.dumps({"size": list(size), "review": review, "views": walk}, indent=1))
        ran(processor_command(VIEWS_SCRIPT, [usda, str(listed), str(out / WALK)]), out / "walk.log")
    peel = made["shots"][PEEL]["views"]
    if peel:
        job = out / "peel-job.json"
        job.write_text(json.dumps(dict(made["job"], out=str(out / PEEL)), indent=1))
        listed = out / "peel.json"
        listed.write_text(json.dumps({"size": list(size), "review": review, "views": peel, "peel": str(job)}, indent=1))
        ran(processor_command(WALKER_SCRIPT, [usda, str(listed), str(out / "peel-out")]), out / "peel.log")
    return out


def measured(composite, drawn):
    """The composite against the whole render, in 8-bit levels over every pixel and channel."""
    difference = np.abs(np.asarray(Image.open(composite).convert("RGB"), dtype=float) -
                        np.asarray(Image.open(drawn).convert("RGB"), dtype=float))
    return {"mean": round(float(difference.mean()), 3), "p99": round(float(np.percentile(difference, 99)), 1),
            "max": round(float(difference.max()), 1), "over_16": round(float((difference.max(axis=2) > 16).mean()), 5)}


def match(scene, folder, inputs, views, walker=None, size=PREVIEW_SIZE, review=True, kept=None):
    """The composite of the named views against the same frames drawn whole: <folder>/match/match.json."""
    made = draw(scene, folder, inputs, walker, size, review, views=views, kept=kept)
    out = whole(folder, scene, made, size, review)
    pictures = {}
    for shot, shot_made in made["shots"].items():
        for picture in shot_made["pictures"]:
            name = picture["out"].split("/", 1)[1]
            drawn = out / WALK / f"{picture['view']}-look.png" if shot == WALK else out / PEEL / name
            pictures[picture["out"]] = measured(pathlib.Path(folder) / "frames" / picture["out"], drawn)
    worst = {measure: max(found[measure] for found in pictures.values()) for measure in ("mean", "p99", "max")}
    record = {"tolerance": TOLERANCE, "worst": worst, "pictures": pictures, "size": list(size), "review": review,
              "within": all(worst[measure] <= limit for measure, limit in TOLERANCE.items())}
    (out / "match.json").write_text(json.dumps(record, indent=1))
    return record


def kept_of(local):
    """The frames' store: this machine's (`local`), else with the store bucket."""
    if local:
        return Kept(Store.default())
    from score.store import offload
    return Kept(Store.default(), offload.open_bucket())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("preview", "draw", "match"))
    parser.add_argument("scene", type=pathlib.Path)
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--rows", type=pathlib.Path, required=True, help="{row: output folder} the sim body ran from")
    parser.add_argument("--walker", help="the walker peeled (else close_walker's)")
    parser.add_argument("--size", type=int, nargs=2)
    parser.add_argument("--review", action="store_true", help="at the review's samples (a look, never a final)")
    parser.add_argument("--views", nargs="*", default=(), help="only these views, <shot>/<view> (walk/f0100)")
    parser.add_argument("--redraw", nargs="*", default=(), help="these layers' frames drawn again (walker:<name>)")
    parser.add_argument("--on", choices=("processor", "card", "cloud"), default="processor")
    parser.add_argument("--slices", type=int, default=8)
    parser.add_argument("--minutes", type=float, default=120.0)
    parser.add_argument("--local", action="store_true", help="keep the frames in this machine's store alone")
    arguments = parser.parse_args()
    inputs = json.loads(arguments.rows.read_text())
    kept = kept_of(arguments.local)
    if arguments.command == "preview":
        made = preview(arguments.scene, arguments.folder, inputs, arguments.walker, kept)
        print(json.dumps({key: made[key] for key in ("passed", "faults", "sheets", "drawn", "kept")}))
        return
    if arguments.command == "match":
        made = match(arguments.scene, arguments.folder, inputs, arguments.views, arguments.walker,
                     tuple(arguments.size or PREVIEW_SIZE), True if arguments.review or not arguments.size
                     else arguments.review, kept)
        print(json.dumps({"within": made["within"], "worst": made["worst"], "tolerance": made["tolerance"]}))
        return
    made = draw(arguments.scene, arguments.folder, inputs, arguments.walker, tuple(arguments.size or FINAL_SIZE),
                arguments.review, views=arguments.views, on=arguments.on, kept=kept, slices=arguments.slices,
                minutes=arguments.minutes, redraw=tuple(arguments.redraw))
    print(json.dumps({key: made[key] for key in ("film", "jobs", "missing", "drawn", "kept", "film.mp4")
                      if key in made}))


if __name__ == "__main__":
    main()
