"""The prop benchmark's render and route runner (#163, design on #162): each NVIDIA SimReady asset of the set drawn
as the prop route's close-up, then made again by today's two routes from that picture and its row alone, every
step's output kept as a run-store object whose blobs go to the SCORE store bucket.

    PROPS_HOME=~/.score-this-pc SCORE_CLOUD=local SCORE_FREE_ONLY=1 .venv/bin/python tools/props/bench/run/bench.py \
        render <set.json> --library <scratch score_lib checkout> [--run <id>] [--only <id> ...]
    ... bench.py route <set.json> --library <...> --run <id> --branch A|B [--only <id> ...]
    ... bench.py measure <set.json> --library <...> --run <id> [--only <id> ...] [--previous <run>]
    ... bench.py index --run <id>        # the run's index stored as an object; its hash

**The set** (data/checks/prop-bench-set.json, the truth step's): {"objects": [{"address", "kind", "split"}]} (or a
list, or {"assets": [...]}; an "id" and "version" in place of the address, `simready_` added when missing). A pictured
case (#159: the 2099 cockpit cases, `picture`, no NVIDIA model) has its "id" and no address: its `render` is its
close-up as kept in the store (`picture.closeup`), its row its words and target size, and its `measures` hold each
made model to that close-up and size alone (measures.pictured at PICTURED_BARS: the close-up's silhouette through the
camera fitted on it, close_up_fit), as are the 2099 session's own makes of it (`made_before`, branch `old`).

**The material class** both routes are given (sim.py's classes, NVIDIA's table in data/physics/surface_classes.json;
`make --material`, the class of whatever no finish names) is what a placing agent reads off the words: the first class a word of the entry's id names (CLASS_WORDS),
else its kind's (KIND_CLASS); never the truth's own physics material.

**The render** (free, this PC's card through the card queue: place_build/render.queued). The entry is fetched by
score_lib's own command into job scratch (never the library's cache), its true box read by pxr (metres, Z up), and
closeup.py draws it in the close-up style (tools/props/closeup: turned TURN_DEGREES, looking down LOOK_DOWN_DEGREES,
straight above with its edges square to the frame for a row that lies flat, check.lies_flat), the whole box inside
MARGIN of a SIZE px square frame at a vertical FOV, its materials by their own maps, under soft studio light. Kept:
`closeup.png` (on the light grey BACKDROP with its caught shadow: Pixal3D's input, it cuts it out itself), `rgba.png`
(the true alpha: the cut-out's truth and TRELLIS.2's input), `row.json` (what the route is given: the entry's words
and its true size, wide deep tall) and Blender's `report.json`. A box Blender drew off the pxr box by more than
BOX_TOLERANCE of its diagonal fails the render (a unit or up-axis slip).

**The routes**, each step a kept output in order; a step that fails is the asset's gap on that branch, its reason
kept, and the branch's later steps are not run for it (one try each: no step is run again inside a run).
- A, the Pixal3D take route: `raw` (tools/cloud/batch.py through score/stages/props/pixal_row.run_batch, the take on
  this PC's card under SCORE_CLOUD=local; its list line as pixal_row writes one, its faces place_route.faces_for),
  `finished` (pixal.py --finish-only through pixal_row.finish_all, flat rows laid on their face), then the checks
  on the finished model: `straight` (straight.py), `gate` (the model gate at the row's size) and `physics` (the
  physics layer's rule for a made object: drawn area times its one material's sheet and density, its friction its
  class's row, its collider the convex hull). The finish route (views, list, split, parts, bake) and the solid copy cut to size are not run yet (NOT_RUN):
  they are a place's surface line, and the list is a paid Gemini call.
- B, place_build `make` (TRELLIS.2 on this PC's card), given the RGBA render, the row's size and `--no-take-in`, in a
  scratch place folder: `raw` (trellis.glb), `final` (set at the size, its paint graded), `sim` (CoACD hulls and
  mass), then `straight` and `gate` on the final model, and `finish` (finish.py, #168): the final model through the
  library finish method (views, list, split, parts) on the benchmark place's surface library, read once a run; its
  list is Claude's (EUR 0), as on a place's line. A `finish` gap leaves the checks standing. Then `physics`
  (weighed_step, #161's rules through sim.py): each finish part's class its surface's, each of make's hulls the class
  of the faces inside it, a real-world mass a part (Claude's answer, EUR 0) held to NVIDIA's bulk density band.
  And `look` (#182, look_step): the finish drawn as the bake paints it, each slot's recipe mixed by its texel mask on
  the final model's own UVs, through the card queue (look.py). Then `parts` (parts_step, #177): its moving parts
  (maker/parts.py) seen in the close-up (Claude, EUR 0), cut through the finish's fitted camera and jointed, each its
  share of the physics step's masses and its class.
Nothing is taken into score_lib, and the library read is a scratch checkout (--library), never the shared one.

**The measures** (`measure`, free, this PC's processor): each branch's made model (A's finished final.glb, B's final
model) read in the truth's frame (glTF's Y up turned to Z up), its mass, colliders and friction from its physics step
(each branch's `physics`), held to its truth (tools/props/bench/truth) by tools/props/bench/measures (B's faces in their
finish parts and each part's family against its truth finish's, `family`, where its finish step is kept; its moving
parts and joints against NVIDIA's, where its parts step is kept; its look held by eye to NVIDIA's render and to the
`--previous` run's look of the asset by the picture judge, tools/props/bench/judge, #184), the kind's
other set assets laid like it for the rank: kept as the branch's `measures` step, measures.json {truth, made, found,
judged}, `found` whole so a later bar re-judges it. An overlap target's withdrawn models (the old models of score_lib it
replaced) are measured the same way at the size they were laid at, branch `old`, one step each (its address).

The run's index (<PROPS_HOME>/bench/<run>/index.json, rewritten whole after every step) names each output's hash; a
step already in it is not run again, so a run stopped part way goes on where it stopped.
"""
import argparse
import concurrent.futures
import datetime
import functools
import json
import math
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import threading
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
for _folder in ("tools/library", "tools/props", "tools/props/closeup", "tools/props/library", "tools/props/gates"):
    sys.path.insert(0, str(REPO / _folder))
sys.path.insert(0, str(REPO))

import check  # noqa: E402  (tools/props/closeup: the close-up style)
import finish  # noqa: E402  (branch B's finish: the library finish method)

SCRIPT = HERE / "closeup.py"
LOOK = HERE / "look.py"  # the finish's look drawn by its texel masks (look_step, #182)
LOOK_SMALL = 360  # the look's small copy, a page's
# A pixel of the mesh alone in plain white (look.py's bare.png) darker than this display luminance (0 to 1) faces away
# from every light: its normal is turned into the body or it lies in a fold (#159: the printer box's holes are 0.0047
# of its silhouette at 0.1 and 0.0052 at 0.2; tc4r's clean made models 0.00001 at most at either).
LOOK_DARK = 0.1
PLACE = "bench163"  # the benchmark's place name: its takes, its inventory's scene, its scratch place folder
SIZE = 2048  # the close-up's pixels square (#162: Pro draws at 2K)
FOV = 30.0  # vertical degrees, as tools/usd/compare.py draws
MARGIN = 0.08  # the share of the half frame kept clear round the box
SAMPLES = 128
BACKDROP = (214, 214, 214)  # the light grey even backdrop
BOX_TOLERANCE = 0.01
CARD_GB = 6
MEMORY_GB = 8
RENDER_SECONDS = 1800
RENDERS_AT_ONCE = 2  # close-ups drawn side by side (the card queue gives each its share; card_turn's two slots)
NOT_RUN = {"finish-route": "a place's surface line (views, list, split, parts, bake); its list is a paid Gemini call",
           "solid": "the bake's solid copy cut to size runs inside the finish route's bake"}


# A word of an entry's id that names its material class (at a word start), first match wins.
CLASS_WORDS = (("wood", "wood"), ("plywood", "wood"), ("cardboard", "cardboard"), ("paper", "paper"),
               ("fabric", "fabric"), ("textile", "fabric"), ("rug", "fabric"), ("rubber", "rubber"),
               ("hose", "rubber"), ("glass", "glass"), ("mirror", "glass"), ("plastic", "plastic"),
               ("fiberglass", "plastic"), ("steel", "metal"), ("aluminium", "metal"), ("metal", "metal"))
# Each kind's class when no word names one: what most of its things are made of.
KIND_CLASS = {"box": "cardboard", "crate": "plastic", "shelf / rack": "metal", "cabinet / locker": "metal",
              "desk / table / bench": "wood", "chair / stool": "plastic", "monitor / keyboard": "plastic",
              "lamp body": "metal", "bin": "plastic", "ladder": "metal", "sign (flat)": "plastic",
              "toolbox / tool cart": "metal", "fridge / stove / sink": "metal", "hose / pipe (slender)": "rubber",
              "tray (flat)": "plastic", "overlap": "plastic"}


class StepFailed(RuntimeError):
    """A step that made nothing it could keep: the asset's gap on its branch."""


# --- the set and the row ---------------------------------------------------------------------------------------------

def read_set(path):
    """The set's rows, each with its address."""
    found = json.loads(pathlib.Path(path).read_text())
    rows = (found.get("objects") or found.get("assets")) if isinstance(found, dict) else found
    listed = []
    for row in rows:
        if row.get("picture"):
            listed.append({**row, "address": None})
            continue
        if "address" not in row:
            entry = row["id"] if row["id"].startswith("simready_") else f"simready_{row['id']}"
            row = {**row, "address": f"model/{entry}@{row['version']}"}
        listed.append({**row, "id": row["address"].split("/", 1)[1].split("@")[0]})
    return listed


def size_of(low, high, up_axis):
    """(wide, deep, tall) metres of a box in its stage's axes."""
    sides = [float(high[axis] - low[axis]) for axis in range(3)]
    return [sides[0], sides[2], sides[1]] if up_axis.upper() == "Y" else sides


def material_for(row):
    """The material class the routes are given for a set row (module docstring): the set's own `material` when it
    names one, else the first CLASS_WORDS word at a word start of its id, else its kind's KIND_CLASS."""
    if row.get("material"):
        return row["material"]
    words = row["id"].removeprefix("simready_").split("_")
    for word, material in CLASS_WORDS:
        if any(part.startswith(word) for part in words):
            return material
    return KIND_CLASS.get(row.get("kind"), "plastic")


def words_of(record):
    """What the route is told the object is: the entry's title and its description."""
    return " ".join([record.get("title", ""), *record.get("tags", {}).get("description", [])]).strip()


# --- the framing -----------------------------------------------------------------------------------------------------

def view_of(low, high, size):
    """The close-up's camera on a Z-up box: turned TURN_DEGREES from its front (-y) about z and looking down
    LOOK_DOWN_DEGREES, or straight down with +y up for a row that lies flat; at the least distance that holds every
    corner inside MARGIN of the square frame. {"eye", "aim", "up", "fov"}."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    centre = (low + high) / 2
    down = math.radians(check.look_down(size))
    turn = 0.0 if check.lies_flat(size) else math.radians(check.TURN_DEGREES)
    back = np.array([math.sin(turn) * math.cos(down), -math.cos(turn) * math.cos(down), math.sin(down)])
    up = np.array([0.0, 1.0, 0.0]) if check.lies_flat(size) else np.array([0.0, 0.0, 1.0])
    right = np.cross(up, back)
    right /= np.linalg.norm(right)
    true_up = np.cross(back, right)
    reach = math.tan(math.radians(FOV) / 2) * (1 - MARGIN)
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    offsets = corners - centre
    distance = max(max(abs(offset @ right), abs(offset @ true_up)) / reach + offset @ back for offset in offsets)
    return {"eye": (centre + back * distance).tolist(), "aim": centre.tolist(), "up": up.tolist(), "fov": FOV}


# --- the render ------------------------------------------------------------------------------------------------------

def library_values(library):
    """The library's settings for its own command, its root the scratch checkout; refused for the shared checkout."""
    import library_files
    library = pathlib.Path(library).resolve()
    shared = library_files.default_root()
    if shared is not None and library == pathlib.Path(shared).resolve():
        raise SystemExit(f"{library} is the shared score_lib checkout: give a scratch one (git worktree add --detach)")
    if not (library / "entries").is_dir():
        raise SystemExit(f"{library}: no score_lib checkout")
    values = {**library_files.defaults(), **os.environ, "SCORE_LIB_ROOT": str(library)}
    return library_files.blob_store(values)


def fetched(address, values, into):
    """The entry fetched by the library's own command into `into` (job scratch); its record and its root USD."""
    import library_files
    words = shlex.split(values.get("SCORE_LIB_COMMAND") or library_files.DEFAULT_COMMAND) + [
        "--root", values["SCORE_LIB_ROOT"], "fetch", address, "--into", str(into)]
    done = subprocess.run(words, env=values, cwd=values["SCORE_LIB_ROOT"], capture_output=True, text=True,
                          timeout=library_files.TIMEOUT)
    if done.returncode:
        raise StepFailed(f"score-lib fetch {address} exited {done.returncode}: {done.stderr.strip()[-300:]}")
    kind, rest = address.split("/", 1)
    entry, version = rest.split("@")
    record = json.loads((pathlib.Path(values["SCORE_LIB_ROOT"]) / "entries" / kind / entry / version /
                         "entry.json").read_text())
    return record, pathlib.Path(into) / "score_lib" / kind / entry / version / record["usd"]["root"]


def true_box(root):
    """The asset's drawn box (render and default purposes) in metres, in its stage's axes; and its up axis."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(root))
    metres = UsdGeom.GetStageMetersPerUnit(stage)
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        stage.GetPseudoRoot()).ComputeAlignedRange()
    return ([value * metres for value in found.GetMin()], [value * metres for value in found.GetMax()],
            str(UsdGeom.GetStageUpAxis(stage)))


def blender_box(low, high, up_axis):
    """The box as Blender's importer lays it: a Y-up stage turned onto Z up, (x, y, z) -> (x, -z, y)."""
    if up_axis.upper() != "Y":
        return list(low), list(high)
    return [low[0], -high[2], low[1]], [high[0], -low[2], high[1]]


def queued_blender(job_name, arguments, log, script=SCRIPT):
    """`script` (closeup.py, else look.py) run on this PC's card through the card queue (place_build/render.queued);
    its exit."""
    from score.stages.place_build import render
    command = render.queued(job_name, script, arguments, seconds=RENDER_SECONDS, card_gb=str(CARD_GB),
                            memory_gb=MEMORY_GB)
    with open(log, "w") as out:
        return subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, cwd=REPO).returncode


def on_backdrop(shadow, out):
    """The render with its caught shadow laid on the light grey BACKDROP (its alpha over it), opaque RGB."""
    from PIL import Image
    pixels = np.asarray(Image.open(shadow).convert("RGBA"), dtype=np.float64) / 255
    alpha = pixels[..., 3:]
    laid = pixels[..., :3] * alpha + np.array(BACKDROP) / 255 * (1 - alpha)
    Image.fromarray(np.round(laid * 255).astype(np.uint8), "RGB").save(out)


def render_asset(row, values, scratch, out, draw=queued_blender):
    """One asset drawn as its close-up into `out` (module docstring); its row."""
    scratch.mkdir(parents=True, exist_ok=True)
    record, root = fetched(row["address"], values, scratch / "entry")
    low, high, up_axis = true_box(root)
    low, high = blender_box(low, high, up_axis)
    size = size_of(low, high, "Z")
    job = {"size": SIZE, "samples": SAMPLES, "camera": view_of(low, high, size), "floor": low[2]}
    (scratch / "job.json").write_text(json.dumps(job, indent=1))
    code = draw(f"bench-{row['id']}", [str(root), str(scratch / "job.json"), str(scratch / "drawn")],
                scratch / "blender.log")
    drawn = scratch / "drawn"
    if code or not (drawn / "rgba.png").is_file() or not (drawn / "shadow.png").is_file():
        lines = (scratch / "blender.log").read_text(errors="replace").splitlines() \
            if (scratch / "blender.log").is_file() else []
        said = [line for line in lines if "Error" in line or "error:" in line] or lines[-6:]
        raise StepFailed(f"the close-up render exited {code}: {' | '.join(said[-6:])}")
    report = json.loads((drawn / "report.json").read_text())
    diagonal = float(np.linalg.norm(np.subtract(high, low)))
    slip = float(np.abs(np.subtract(report["box"], [low, high])).max())
    if slip > BOX_TOLERANCE * diagonal:
        raise StepFailed(f"Blender drew the box {report['box']}, the true box is {[low, high]}: off {slip:.4f} m")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(drawn / "rgba.png", out / "rgba.png")
    on_backdrop(drawn / "shadow.png", out / "closeup.png")
    shutil.copyfile(drawn / "report.json", out / "report.json")
    given = {"id": row["id"], "address": row["address"], "words": words_of(record),
             "size": [round(side, 4) for side in size], "lies_flat": check.lies_flat(size), "camera": job["camera"]}
    (out / "row.json").write_text(json.dumps(given, indent=1))
    return given


def pictured_render(row, kept, out):
    """A pictured case's close-up (its `picture.closeup` store output, closeup.png) kept as its render: rgba.png (the
    picture as cut out), closeup.png (on the light grey BACKDROP) and row.json (its words and target size); its row."""
    picture = row["picture"]
    folder = kept.store.checkout(picture["closeup"])
    out.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    with Image.open(folder / "closeup.png") as found:
        found.convert("RGBA").save(out / "rgba.png")
    on_backdrop(out / "rgba.png", out / "closeup.png")
    size = [float(side) for side in picture["size"]]
    given = {"id": row["id"], "address": None, "words": picture["words"], "size": size,
             "lies_flat": check.lies_flat(size), "camera": None, "picture": picture["closeup"]}
    (out / "row.json").write_text(json.dumps(given, indent=1))
    return given


# --- keeping outputs -------------------------------------------------------------------------------------------------

class Kept:
    """The run's outputs: each step's folder put in the run store, its blobs sent to the store bucket at once, and the
    run's index (its path) naming each by hash."""

    def __init__(self, store, bucket, index):
        self.store, self.bucket, self.index_path = store, bucket, pathlib.Path(index)
        self.index = json.loads(self.index_path.read_text()) if self.index_path.is_file() else {"assets": {}}
        self.lock = threading.Lock()

    def entry(self, asset, branch, step):
        return self.index["assets"].get(asset, {}).get(branch, {}).get(step)

    def write(self, asset, branch, step, entry):
        with self.lock:  # steps of several assets side by side
            self.index["assets"].setdefault(asset, {}).setdefault(branch, {})[step] = entry
            partial = self.index_path.with_name(self.index_path.name + ".partial")
            partial.write_text(json.dumps(self.index, indent=1, sort_keys=True))
            partial.replace(self.index_path)

    def keep(self, asset, branch, step, folder, seconds):
        """The step's folder stored, its blobs in the bucket; its output's hash."""
        from score.store import offload
        output = self.store.put_tree(folder)
        for sha in sorted(set(self.store.listing(output).values())):
            offload.push(self.store.objects.path(f"blobs/{sha}"), sha, self.bucket)
        self.write(asset, branch, step, {"output": output, "seconds": round(seconds, 1)})
        return output

    def gap(self, asset, branch, step, why):
        self.write(asset, branch, step, {"gap": str(why)[-1500:]})


def run_steps(kept, asset, branch, steps, scratch):
    """Each (step, make) in order for one asset on one branch, `make(folder)` writing the step's files into a fresh
    folder of job scratch; the first that fails is the branch's gap, the ones after it not run. A step the index
    already holds is not run again."""
    for step, make in steps:
        found = kept.entry(asset, branch, step)
        if found and "gap" in found:
            return
        if found:
            continue
        folder = scratch / branch / step
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        began = time.time()
        try:
            make(folder)
            if not any(path.is_file() for path in folder.rglob("*")):
                raise StepFailed("the step wrote nothing")
        except (Exception, SystemExit) as why:  # the step's gap, its reason kept: never run again in the run
            kept.gap(asset, branch, step, f"{type(why).__name__}: {why}")
            return
        kept.keep(asset, branch, step, folder, time.time() - began)


def checked_out(kept, asset, branch, step, into):
    """A kept step's folder read back from the store into `into`."""
    found = kept.entry(asset, branch, step)
    if not found or "output" not in found:
        raise StepFailed(f"{asset}: no {branch} {step} kept")
    source = kept.store.checkout(found["output"])
    shutil.copytree(source, into, dirs_exist_ok=True)
    return into


# --- the checks every branch's model takes ---------------------------------------------------------------------------

def mesh_of(path):
    """A model's mesh as the model gate reads one (gates/model.raw_model): one mesh, its vertices welded across UV
    seams. Unwelded, a made model's seams split it into thousands of pieces and the gate's piece count took 40 GB on
    TRELLIS.2's crate (2026-11-23)."""
    import trimesh
    mesh = trimesh.load(str(path), force="mesh", skip_materials=True)
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    return mesh


def straight_step(model):
    def make(folder):
        import straight
        (folder / "straight.json").write_text(json.dumps(straight.straightness(mesh_of(model)), indent=1))
    return make


def gate_step(model, row):
    """The model gate at the row's size (its frame y up: wide, tall, deep)."""
    def make(folder):
        import model as model_gate
        wide, deep, tall = row["size"]
        found = model_gate.check(row["id"], mesh_of(model), [wide, tall, deep])
        (folder / "gate.json").write_text(json.dumps(found, indent=1))
    return make


def physics_step(model, row, material):
    """The physics layer's rule for a made object (tools/usd/physics.py write_masses): the drawn area times the
    layer's material's sheet and density (data/physics/materials.json's one row, steel, as every place's physics
    design gives every model: score/stages/physics/design.py); its friction and restitution its class's row; its
    collider the convex hull (the export's hull guide)."""
    def make(folder):
        from score.stages.place_build.maker import sim
        spec = sim.material(material)
        layer = json.loads((REPO / "data/physics/materials.json").read_text())["materials"]["steel"]
        mesh = mesh_of(model)
        hull = mesh.convex_hull
        hull.export(str(folder / "hull.glb"))
        found = {"material": material, "area_m2": round(float(mesh.area), 5),
                 "mass_kg": round(float(mesh.area * layer["sheet"] * layer["density"]), 4),
                 "hull_m3": round(float(hull.volume), 6), "static": spec["static"], "dynamic": spec["dynamic"],
                 "restitution": spec["restitution"]}
        (folder / "physics.json").write_text(json.dumps(found, indent=1))
    return make


# --- branch A: the Pixal3D take route --------------------------------------------------------------------------------

def take_of(asset):
    return f"{PLACE}-{asset}"


def faces_of(row):
    """The triangles the route cuts this row's model to (place_route.faces_for at its kit size)."""
    import place_route
    return place_route.faces_for(row["id"], place_route.kit_size(row["size"]))


def inventory_for(rows, run_folder):
    """The benchmark's inventory batch.py builds from: one generate row a set asset, its true size; approved as the
    owner's benchmark set (#163, the design he resolved on #162)."""
    path = run_folder / f"{PLACE}.json"
    found = {"scene": PLACE, "place": PLACE, "plan": {"views": [{"id": "render", "picture": "the set's close-ups"}]},
             "approved": "2026-11-23, the prop benchmark's set: #163 (design #162)", "migrated": "",
             "room": {"shell": "", "light": "", "backdrop": "", "wall_fill": []},
             "rows": [{"id": row["id"], "view": "render", "box": None, "unseen": "a benchmark asset, drawn alone",
                       "name": row["words"][:80] or row["id"], "kind": "generate", "anchor": "floor",
                       "size": row["size"], "count": 1, "thing": f"prop:{row['id']}"} for row in rows]}
    path.write_text(json.dumps(found, indent=1))
    return path


def batch_made(rows, closeups, inventory, logs):
    """Every take with no raw model made in one tools/cloud/batch.py call (pixal_row.run_batch: the card filled as its
    capacity says, never one take after another); the reason when the call failed as a whole, else None."""
    from score.stages.props import pixal_row
    lines = [f"{take_of(row['id'])} {closeups[row['id']]} --faces {faces_of(row)} "
             f"--seed {pixal_row.seed_of(take_of(row['id']))}"
             for row in rows if not pixal_row.raw_made(take_of(row["id"]))]
    if not lines:
        return None
    (logs / "list.txt").write_text("\n".join(lines) + "\n")
    try:
        pixal_row.run_batch(logs / "list.txt", PLACE, inventory, logs)
    except RuntimeError as why:
        return str(why)
    return None


def finishes_made(rows, closeups, logs):
    """Every raw take with no finish finished in one call (pixal_row.finish_all: pixal.py --finish-only, its jobs side
    by side); the reason when the call failed as a whole, else None."""
    from score.stages.props import pixal_row
    jobs = [pixal_row.finish_job(take_of(row["id"]), closeups[row["id"]], faces_of(row), row["lies_flat"])
            for row in rows if pixal_row.raw_made(take_of(row["id"]))
            and not pixal_row.finished(take_of(row["id"]), faces_of(row))]
    if not jobs:
        return None
    try:
        pixal_row.finish_all(jobs, PLACE, logs)
    except RuntimeError as why:
        return str(why)
    return None


def raw_take(row, failed):
    def make(folder):
        from score.stages.props import pixal_row
        take = take_of(row["id"])
        if not pixal_row.raw_made(take):
            raise StepFailed(failed or f"Pixal3D brought no raw model back for {take} (the run's batch.log)")
        raw, _, views = pixal_row.take_files(take)
        shutil.copyfile(raw, folder / "raw.glb")
        shutil.copytree(views, folder / "raw.svviews")
    return make


def finished_take(row, failed):
    def make(folder):
        from score.stages.props import pixal_row
        take, faces = take_of(row["id"]), faces_of(row)
        if not pixal_row.finished(take, faces):
            raise StepFailed(failed or f"the finish brought no model back for {take} (the run's finish.log)")
        shutil.copyfile(pixal_row.take_files(take)[1], folder / "final.glb")
        shutil.copyfile(pixal_row.slimmed(take, faces), folder / f"finished-{faces}.glb")
    return make


def kept_output(kept, asset, branch, step):
    return "output" in (kept.entry(asset, branch, step) or {})


def branch_a(kept, rows, closeups, material, inventory, scratch, logs):
    """The Pixal3D take route for every asset (module docstring): the takes in one batch, the finishes in one call,
    each asset's steps kept in order, its take's files then cleared from WORK."""
    waiting = [row for row in rows if not kept.entry(row["id"], "A", "raw")]
    failed = batch_made(waiting, closeups, inventory, logs) if waiting else None
    for row in waiting:
        run_steps(kept, row["id"], "A", [("raw", raw_take(row, failed))], scratch[row["id"]])
    unfinished = [row for row in rows if kept_output(kept, row["id"], "A", "raw")
                  and not kept.entry(row["id"], "A", "finished")]
    for row in unfinished:  # a raw take kept by an earlier invocation is put back where the finish reads it
        restored_take(kept, row, scratch[row["id"]])
    failed = finishes_made(unfinished, closeups, logs) if unfinished else None
    for row in rows:
        asset = row["id"]
        run_steps(kept, asset, "A", [("finished", finished_take(row, failed))], scratch[asset])
        if kept_output(kept, asset, "A", "finished"):
            model = checked_out(kept, asset, "A", "finished", scratch[asset] / "A" / "kept-final") / "final.glb"
            run_steps(kept, asset, "A", [("straight", straight_step(model)), ("gate", gate_step(model, row)),
                                         ("physics", physics_step(model, row, material[asset]))], scratch[asset])
        for step, why in NOT_RUN.items():
            if not kept.entry(asset, "A", step):
                kept.gap(asset, "A", step, f"not run yet: {why}")
        cleared_take(take_of(asset), faces_of(row))


def restored_take(kept, row, scratch):
    """A kept raw take's model and camera folder put back into WORK/pixal when they are not there."""
    from score.stages.props import pixal_row
    take = take_of(row["id"])
    if pixal_row.raw_made(take):
        return
    folder = checked_out(kept, row["id"], "A", "raw", scratch / "A" / "kept-raw")
    raw, _, views = pixal_row.take_files(take)
    shutil.copyfile(folder / "raw.glb", raw)
    shutil.copytree(folder / "raw.svviews", views, dirs_exist_ok=True)


def cleared_take(take, faces):
    """A benchmark take's files removed from WORK/pixal once kept (job scratch: the store holds them)."""
    from score.stages.props import pixal_row
    raw, final, views = pixal_row.take_files(take)
    for path in (raw, final, pixal_row.slimmed(take, faces)):
        path.unlink(missing_ok=True)
    shutil.rmtree(views, ignore_errors=True)
    shutil.rmtree(raw.with_name(f"{take}-{faces}"), ignore_errors=True)


# --- branch B: place_build make --------------------------------------------------------------------------------------

def scratch_place(scratch):
    """A place folder of the benchmark's own in job scratch: its record and no palette (nothing graded toward one)."""
    folder = scratch / "place"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "place.json").write_text(json.dumps({"place": PLACE}, indent=1))
    return folder


def made_steps(row, rgba, material, place):
    """`make` (TRELLIS.2, set at the row's size, sim-ready, nothing taken in) with its files split into the raw, final
    and sim steps; a raw model kept by an earlier invocation is put back where make reads it, so TRELLIS.2 runs once."""
    from score.stages.place_build import maker
    work = place / "made" / maker.entry_id(row["id"], PLACE)

    def made():
        if not (work / f"{work.name}.json").is_file():
            maker.make(place, row["id"], str(rgba), material, size=row["size"], take_in=False)
        return work

    def raw(folder):
        shutil.copyfile(made() / "trellis.glb", folder / "raw.glb")
        shutil.copyfile(work / "trellis.json", folder / "trellis.json")

    def final(folder):
        shutil.copyfile(made() / f"{work.name}-final.glb", folder / "final.glb")

    def sim(folder):
        shutil.copyfile(made() / f"{work.name}-hulls.glb", folder / "hulls.glb")
        shutil.copyfile(work / f"{work.name}.json", folder / "made.json")
    return work, [("raw", raw), ("final", final), ("sim", sim)]


def branch_b(kept, row, material, rgba, scratch, library):
    """place_build make's steps for one asset, then the checks on its final model and its finish; `library()` gives
    the benchmark place's surface library (finish.bench_library), read once a run."""
    work, steps = made_steps(row, rgba, material, scratch_place(scratch))
    if kept_output(kept, row["id"], "B", "raw"):
        folder = checked_out(kept, row["id"], "B", "raw", scratch / "B" / "kept-raw")
        work.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder / "raw.glb", work / "trellis.glb")
        shutil.copyfile(folder / "trellis.json", work / "trellis.json")
    run_steps(kept, row["id"], "B", steps, scratch)
    if kept_output(kept, row["id"], "B", "final"):
        model = checked_out(kept, row["id"], "B", "final", scratch / "B" / "kept-final") / "final.glb"
        run_steps(kept, row["id"], "B", [("straight", straight_step(model)), ("gate", gate_step(model, row))],
                  scratch)
        run_steps(kept, row["id"], "B", [("finish", finish_step(model, rgba, row, library))],
                  scratch)
        if kept_output(kept, row["id"], "B", "finish"):
            parted = checked_out(kept, row["id"], "B", "finish", scratch / "B" / "look-finish")
            camera = finish.look_view(json.loads((rgba.parent / "row.json").read_text())["camera"], parted)
            run_steps(kept, row["id"], "B", [("look", look_step(model, parted, row, camera))], scratch)
    if not kept.entry(row["id"], "B", "physics") and all(kept_output(kept, row["id"], "B", step)
                                                         for step in ("final", "sim", "finish")):
        folders = {step: checked_out(kept, row["id"], "B", step, scratch / "B" / f"weighed-{step}")
                   for step in ("final", "sim", "finish")}
        run_steps(kept, row["id"], "B", [("physics", weighed_step(folders, row, material, rgba))], scratch)
    if not kept.entry(row["id"], "B", "parts") and all(kept_output(kept, row["id"], "B", step)
                                                       for step in ("final", "finish", "physics")):
        folders = {step: checked_out(kept, row["id"], "B", step, scratch / "B" / f"parted-{step}")
                   for step in ("final", "finish", "physics")}
        run_steps(kept, row["id"], "B", [("parts", parts_step(folders, row, rgba))], scratch)


def parts_step(folders, row, picture):
    """The final model's moving parts (score/stages/place_build/maker/parts.py, #177): the pieces Claude sees move in
    the route's picture (`picture`, the RGBA close-up; EUR 0), cut through the finish step's fitted camera and jointed,
    each part's mass its share of the physics step's finish groups by area and its class theirs of most area:
    parts.json, face_parts.npy (each final face's part, -1 the body) and parted.glb (its part nodes)."""
    def make(folder):
        from PIL import Image
        import score.stages.surfaces  # noqa: F401  (the stage first: its modules import one another through it)
        import route_cast
        from score.stages.place_build.maker import parts
        model = folders["final"] / "final.glb"
        side = gltf_side(model)
        vertices = side["vertices"] @ Y_UP.T  # back to the model file's own frame, glTF's Y up
        camera = route_cast.close_up_camera(folders["finish"] / "camera.json")
        with Image.open(picture) as shown:
            size = shown.size
        listed = parts.asked(row["words"], row["size"], picture)
        face_part, left_out = parts.cut(vertices, side["faces"], listed, camera, size)
        found = parts.record(listed, face_part, parts.jointed(vertices, side["faces"], face_part, listed, camera, size),
                             left_out)
        part_of, _ = finish.face_finishes(folders["finish"], row["id"])
        weighed = json.loads((folders["physics"] / "physics.json").read_text())["parts"]
        group_of = {number: index for index, group in enumerate(weighed) for number in group["finish_parts"]}
        face_group = np.array([group_of[part] for part in np.asarray(part_of).tolist()])
        corners = vertices[side["faces"]]
        areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2
        indices = [part["index"] for part in found["parts"]]
        counted = np.array([indices.index(value) if value in indices else -1 for value in face_part.tolist()])
        kg, found["body"]["kg"] = parts.part_masses(counted, face_group, [group["kg"] for group in weighed], areas,
                                                    len(indices))
        classes, found["body"]["class"] = parts.part_classes(counted, [weighed[group]["class"] for group in
                                                                       face_group], areas, len(indices))
        for number, (part, mass, name) in enumerate(zip(found["parts"], kg, classes)):
            part.update(index=number, kg=round(mass, 4), **{"class": name})
        (folder / "parts.json").write_text(json.dumps(found, indent=1))
        np.save(folder / "face_parts.npy", counted)
        parts.written(model, counted, found, folder / "parted.glb")
    return make


def weighed_step(folders, row, material, picture):
    """make's physics on its finished model (sim.py, #161's rules): each finish part's class its library surface's
    (`material` where the surface names none), each of make's hulls the class of the faces inside it, and a
    real-world mass a part seen in the route's picture (`picture`, the RGBA close-up), the parts of one words and class
    asked as one; physics.json and the hulls as hull.glb."""
    def make(folder):
        from score.stages.place_build.maker import sim
        side = gltf_side(folders["final"] / "final.glb")
        part_of, surfaces = finish.face_finishes(folders["finish"], row["id"])
        if len(part_of) != len(side["faces"]):
            raise StepFailed(f"the finish's parts name {len(part_of)} faces, the model has {len(side['faces'])}")
        records = finish.records(sorted({address for address in surfaces.values() if address.startswith("surface/")}))
        listed = json.loads((folders["finish"] / "surfaces-parts" / "parts.json").read_text())["takes"][row["id"]]
        groups, group_of = [], {}
        for part in listed["parts"]:
            name = sim.surface_class(records.get(surfaces[part["part"]], {})) or material
            key = (part["words"], name)
            if key not in group_of:
                group_of[key] = len(groups)
                groups.append({"words": part["words"], "class": name, "share": 0.0, "finish_parts": []})
            groups[group_of[key]]["share"] += part["share"]
            groups[group_of[key]]["finish_parts"].append(part["part"])
        class_of = {number: group["class"] for group in groups for number in group["finish_parts"]}
        hulls = [(piece["vertices"], piece["faces"]) for piece in colliders_of(folders["sim"] / "hulls.glb")]
        classes = sim.hull_classes(side["vertices"], side["faces"], [class_of[part] for part in part_of], hulls)
        masses = sim.weighed(row["words"], row["size"], groups, picture)
        parts = [{**group, "kg": round(kg, 4)} for group, kg in zip(groups, masses)]
        found = sim.physical(hulls, classes, parts, row["size"])
        (folder / "physics.json").write_text(json.dumps(found, indent=1))
        shutil.copyfile(folders["sim"] / "hulls.glb", folder / "hull.glb")
    return make


def look_step(model, parted, row, camera, draw=queued_blender, ask=None):
    """The finish's look as the bake paints it (#182, finish.look_job): the made model whole, each slot's recipe mixed
    by its texel mask on the model's own UVs, drawn by look.py through the card queue from the close-up's `camera`;
    look.png, its job and masks, a LOOK_SMALL side copy for a page, and each text mark read back where it was drawn
    (finish.marks_read, `ask` a test's: marks.json, read.json; #185)."""
    def make(folder):
        from PIL import Image
        job = finish.look_job(parted, row["id"], model, camera, folder)
        code = draw(f"bench-look-{row['id']}", [str(job)], folder / "blender.log", LOOK)
        if code or not (folder / "look.png").is_file():
            lines = (folder / "blender.log").read_text(errors="replace").splitlines()
            raise StepFailed(f"look.py exited {code}: {' | '.join(lines[-6:])}")
        with Image.open(folder / "look.png") as drawn:
            drawn.resize((LOOK_SMALL, LOOK_SMALL), Image.LANCZOS).save(folder / f"look-{LOOK_SMALL}.png")
        (folder / "holes.json").write_text(json.dumps({"holes": look_holes(folder / "look.png",
                                                                             folder / "bare.png")}))
        finish.marks_read(folder, ask)
    return make


def look_holes(look, bare):
    """The share of the model's own silhouette (the mesh alone, `bare`'s opaque pixels) that the `look` shows as a
    hole: the background there (the look transparent), or the mesh alone black (LOOK_DARK) in plain white, its
    normals turned away from every light (#159: the printer box's front)."""
    from PIL import Image
    with Image.open(look) as drawn, Image.open(bare) as alone:
        looked = np.asarray(drawn.convert("RGBA"), dtype=np.float64) / 255
        plain = np.asarray(alone.convert("RGBA"), dtype=np.float64) / 255
    inside = plain[..., 3] >= 0.5
    dark = plain[..., :3] @ np.array([0.2126, 0.7152, 0.0722]) < LOOK_DARK
    holes = inside & ((looked[..., 3] < 0.5) | dark)
    return round(float(holes.sum() / max(int(inside.sum()), 1)), 5)


def finish_step(model, close_up, row, library):
    """The made model through the library finish method (finish.py: views, list, split, parts) on the benchmark
    place's surface library; its rows' outputs kept whole."""
    def make(folder):
        finish.finished(model, close_up, row, library(), folder)
    return make


# --- the measures: each made model held to its truth (tools/props/bench/measures) ------------------------------------

# Row vectors from a Y-up frame (glTF's, a Y-up stage's: x across, y up, z toward the viewer) to the measures' Z up.
PAINT_POINTS = 200000  # surface points a made model's own paint is read at, for its heading (measures._heading)
Y_UP = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
# Each branch's model and physics: (the step and file of its model, the step of its physics).
MEASURED = {"A": (("finished", "final.glb"), "physics"), "B": (("final", "final.glb"), "physics")}
# Each branch's finish step, whose parts give its model's faces their finish groups (finish.face_finishes).
FINISHED = {"B": "finish"}
# Each branch's moving parts step (#177), whose parts and joints the measures hold to NVIDIA's (parted).
PARTED = {"B": "parts"}
# Each branch's look step (#182), whose picture the picture judge holds to NVIDIA's render (judged_look, #184)
# and whose holes (look_holes) the measures judge as `look.holes` (#159).
# Its text marks read back (read.json, #185) the measures hold to the close-up's words as `look.read`.
LOOKED = {"B": "look"}
JOINT_TYPES = {"hinge": "revolute", "spin": "revolute", "slide": "prismatic"}


def side_of(vertices, faces, face_material=None):
    """A side as the measures read one: metres, Z up, its box (low, high)."""
    vertices = np.asarray(vertices, dtype=float)
    return {"vertices": vertices, "faces": np.asarray(faces, dtype=np.int64), "face_material": face_material,
            "box": [vertices.min(0).tolist(), vertices.max(0).tolist()]}


def gltf_meshes(path):
    """A glTF or glb file's meshes placed in the world by its nodes, each turned from glTF's Y up to Z up."""
    import trimesh
    scene = trimesh.load(str(path), force="scene")
    return [(np.asarray(mesh.vertices, dtype=float) @ Y_UP, np.asarray(mesh.faces), mesh)
            for mesh in scene.dump(concatenate=False) if len(mesh.faces)]


def gltf_side(path):
    """A glTF or glb model as a side: its meshes joined, each triangle's material an index by its material's name."""
    vertices, faces, materials, names, offset = [], [], [], {}, 0
    for points, triangles, mesh in gltf_meshes(path):
        name = getattr(getattr(mesh.visual, "material", None), "name", None) or ""
        vertices.append(points)
        faces.append(triangles + offset)
        materials.append(np.full(len(triangles), names.setdefault(name, len(names)), dtype=np.int32))
        offset += len(points)
    return side_of(np.concatenate(vertices), np.concatenate(faces), np.concatenate(materials))


def painted(path, count=PAINT_POINTS):
    """{"points", "colour"}: `count` points on a glTF or glb model's surface (Z up, as gltf_side lays it), each with
    the linear base colour its own material paints there (its texture at the point's UV times its factor), for the
    heading (measures._heading); None for a model with no base colour at all."""
    import trimesh
    meshes = gltf_meshes(path)
    areas = np.array([float(mesh.area) for _, _, mesh in meshes])
    if not len(meshes) or areas.sum() <= 0:
        return None
    points, colours, painted_any = [], [], False
    for (vertices, faces, mesh), share in zip(meshes, areas / areas.sum()):
        material = getattr(mesh.visual, "material", None)
        factor = np.asarray(getattr(material, "baseColorFactor", None) if material is not None and
                            getattr(material, "baseColorFactor", None) is not None else [255, 255, 255, 255],
                            dtype=float)[:3]
        factor = factor / 255.0 if factor.max() > 1.0 else factor
        picture = getattr(material, "baseColorTexture", None)
        uv = getattr(mesh.visual, "uv", None)
        painted_any |= picture is not None or getattr(material, "baseColorFactor", None) is not None
        sampled, face = trimesh.sample.sample_surface(trimesh.Trimesh(vertices, faces, process=False),
                                                      max(1, round(count * share)), seed=7)
        colour = np.ones((len(sampled), 3))
        if picture is not None and uv is not None:
            weights = trimesh.triangles.points_to_barycentric(vertices[faces[face]], sampled)
            where = np.einsum("ij,ijk->ik", weights, np.asarray(uv)[faces[face]])
            texels = np.asarray(picture.convert("RGB"), dtype=float) / 255.0
            height, width = texels.shape[:2]
            rows = np.clip(np.round((1 - where[:, 1] % 1.0) * (height - 1)), 0, height - 1).astype(int)
            columns = np.clip(np.round((where[:, 0] % 1.0) * (width - 1)), 0, width - 1).astype(int)
            shade = texels[rows, columns]
            colour = np.where(shade <= 0.04045, shade / 12.92, ((shade + 0.055) / 1.055) ** 2.4)
        points.append(sampled)
        colours.append(colour * factor)
    return {"points": np.concatenate(points), "colour": np.concatenate(colours)} if painted_any else None


def usd_side(path):
    """A USD model as a side (the truth reader's mesh walk, its stage turned to Z up when it is Y up): each triangle's
    material its bound material's index."""
    from pxr import Usd, UsdGeom
    from tools.props.bench.truth import _read
    stage = Usd.Stage.Open(str(path))
    turn = np.eye(4) * UsdGeom.GetStageMetersPerUnit(stage)
    if str(UsdGeom.GetStageUpAxis(stage)).upper() == "Y":
        turn[:3, :3] = turn[:3, :3] @ Y_UP
    turn[3, 3] = 1.0
    vertices, faces, face_material, materials, offset = [], [], [], [], 0
    for prim in Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies()):
        if not _read.shown(prim):
            continue
        points, matrix = _read.placed_points(prim, turn)
        triangles, polygon, _ = _read.triangles(prim, matrix)
        count = len(UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get() or [])
        vertices.append(points)
        faces.append(triangles + offset)
        face_material.append(_read.polygon_materials(prim, count, materials)[polygon])
        offset += len(points)
    if not vertices:
        raise StepFailed(f"{path}: no drawn mesh")
    return side_of(np.concatenate(vertices), np.concatenate(faces), np.concatenate(face_material))


def colliders_of(path):
    """A collider file's hulls, each {vertices, faces}, Z up."""
    return [{"vertices": points, "faces": triangles} for points, triangles, _ in gltf_meshes(path)]


def parted(folder):
    """{"face_part", "joints"} of a parts step's folder (parts_step) in the measures' frame: each final face's moving
    part, an index into `joints` (-1 the still body), and each part's joint {type revolute or prismatic, axis (its
    way, signed), pivot, limits}, turned from glTF's Y up to Z up."""
    found = json.loads((folder / "parts.json").read_text())
    joints = [{"type": JOINT_TYPES[part["joint"]], "limits": part["limits"],
               "axis": (part["sign"] * np.eye(3)["xyz".index(part["axis"])] @ Y_UP).tolist(),
               "pivot": (np.asarray(part["pivot"], dtype=float) @ Y_UP).tolist()} for part in found["parts"]]
    return {"face_part": np.load(folder / "face_parts.npy"), "joints": joints}


def made_side(model, physics, finished=None, take=None, parts=None):
    """A branch's made model as a side, its mass, colliders and friction from its physics step's folder (physics.json
    and hull.glb: A's the physics layer's, B's make's physics on its finished model); each face's material its finish
    part, with `surfaces` {part: library address} and `looks` {part: its look as set, finish.part_looks}, from its
    finish step's folder (finish.face_finishes) when it has one, else left out. A part list whose faces are not the
    model's (another face count) fails."""
    side = {**gltf_side(model), "face_material": None, "painted": painted(model)}
    if finished is not None:
        part_of, surfaces = finish.face_finishes(finished, take)
        if len(part_of) != len(side["faces"]):
            raise StepFailed(f"the finish's parts name {len(part_of)} faces, the model has {len(side['faces'])}")
        side.update(face_material=np.asarray(part_of, dtype=np.int32), surfaces=surfaces,
                    looks=finish.part_looks(finished, take))
    if parts is not None:
        side.update(parted(parts))
        if len(side["face_part"]) != len(side["faces"]):
            raise StepFailed(f"the parts name {len(side['face_part'])} faces, the model has {len(side['faces'])}")
    found, hulls = json.loads((physics / "physics.json").read_text()), physics / "hull.glb"
    return {**side, "mass": found.get("mass_kg"), "colliders": colliders_of(hulls), "friction": found.get("static")}


def old_side(address):
    """A withdrawn model of score_lib as a side, at the size it was laid at: its USD root (the record's, else its one
    USD file) when it has one, else its glTF; its own physics is not read."""
    kind, path = old_model(address)
    return usd_side(path) if kind == "usd" else gltf_side(path)


def old_model(address):
    """("usd", its USD root) of a model of score_lib (the record's root, else its one USD file), else ("gltf", its
    glTF), its files fetched."""
    import library_files
    from score import library
    kind, rest = address.split("/", 1)
    entry_id, version = rest.split("@")
    record = library.entry(library.root_from_environment(), kind, entry_id, int(version))
    files = {name: library_files.resolve(library_files.reference(address, name))
             for name, info in record["files"].items() if info.get("role") in ("usd", "gltf", "texture")}
    stages = [name for name, info in record["files"].items() if info.get("role") == "usd"]
    root = (record.get("usd") or {}).get("root") or (stages[0] if len(stages) == 1 else None)
    if root in files:
        return "usd", files[root]
    named = [name for name in files if name.endswith((".gltf", ".glb"))]
    if not named:
        raise StepFailed(f"{address}: no USD root and no glTF among its files")
    return "gltf", files[named[0]]


def seen_faces(model, looked, side):
    """Each of the side's faces' pixels in its kept look (finish.look_faces), the measures' `face_seen`; a look cast
    on another face count fails."""
    seen = finish.look_faces(model, looked)
    if len(seen) != len(side["faces"]):
        raise StepFailed(f"the look's faces are {len(seen)}, the model has {len(side['faces'])}")
    return seen


def look_found(looked):
    """The look group of measures.json from a kept look step's folder `looked`: its holes (holes.json) and its text
    marks read back (read.json, measures.text_read, #185), each where the step wrote it."""
    from tools.props.bench import measures
    found = json.loads((looked / "holes.json").read_text()) if (looked / "holes.json").exists() else {}
    read = measures.text_read(json.loads((looked / "read.json").read_text())) \
        if (looked / "read.json").exists() else None
    return {**found, **(read or {})}


def written_measures(folder, truth, side, others, made, picture=None, looked=None):
    """measures.json: what was measured, every measure (measures.measured, the picture judge's group `picture` where
    given, and the look's holes and text marks read back from its look step's folder `looked` where it has them,
    look_found) and its judgement at today's bars."""
    from tools.props.bench import calibrate, measures
    found = measures.measured(truth, side, others=others)
    if picture is not None:
        found["picture"] = picture
    look = look_found(looked) if looked is not None else {}
    if look:
        found["look"] = look
    if side.get("surfaces") is not None and "finish" in found:
        named = [entry["surface"] for entry in measures.by_finish(truth)["materials"]]
        found["family"] = finish.same_family(found["finish"]["pairs"], side["surfaces"], named)
    record = {"truth": truth["address"], "made": made, "found": found, "judged": measures.judged(found)}
    (folder / "measures.json").write_text(json.dumps(calibrate.plain(record), indent=1))


def judged_look(kept, asset, branch, previous, scratch):
    """The branch's kept look held by the picture judge (tools/props/bench/judge, #184) to NVIDIA's render (a pictured
    case's: its close-up, #159) and to the same asset's look in the `previous` run (a Kept, where it kept one): the
    measure group "picture", or None where the branch keeps no look."""
    from tools.props.bench import judge
    step = LOOKED.get(branch)
    if not step or not kept_output(kept, asset, branch, step):
        return None
    look = checked_out(kept, asset, branch, step, scratch / branch / f"judged-{step}") / "look.png"  # never over
    # measure_step's own copy: the store's files are read-only, so a second copy into one folder was refused (#186)
    given = checked_out(kept, asset, "input", "render", scratch / "input-judged")
    before = None
    if previous is not None and kept_output(previous, asset, branch, step):
        before = checked_out(previous, asset, branch, step, scratch / branch / f"previous-{step}") / "look.png"
    row = json.loads((given / "row.json").read_text())
    return judge.looked(row["words"], look, given / "rgba.png", before, pictured=bool(row.get("picture")))


def measure_step(kept, asset, branch, truth, others, scratch, previous=None):
    """The branch's made model and its physics read back from the store and measured against the truth; its look
    judged against NVIDIA's render and the `previous` run's look (judged_look)."""
    def make(folder):
        (step, name), physics = MEASURED[branch]
        model = checked_out(kept, asset, branch, step, scratch / branch / f"kept-{step}") / name
        held = checked_out(kept, asset, branch, physics, scratch / branch / f"kept-{physics}")
        finishing = FINISHED.get(branch)
        finished_parts = checked_out(kept, asset, branch, finishing, scratch / branch / f"kept-{finishing}") \
            if finishing and kept_output(kept, asset, branch, finishing) else None
        moving = PARTED.get(branch)
        cut = checked_out(kept, asset, branch, moving, scratch / branch / f"kept-{moving}") \
            if moving and kept_output(kept, asset, branch, moving) else None
        look = LOOKED.get(branch)
        looked = checked_out(kept, asset, branch, look, scratch / branch / f"kept-{look}") \
            if look and kept_output(kept, asset, branch, look) else None
        side = made_side(model, held, finished_parts, asset, cut)
        if looked is not None:
            side["face_seen"] = seen_faces(model, looked, side)
        if looked is not None and finished_parts is not None:  # each part's drawn pattern beside NVIDIA's (#186)
            rendered = checked_out(kept, asset, "input", "render", scratch / branch / "kept-render")
            patterns = finish.drawn_patterns(model, finished_parts, looked, rendered / "rgba.png", asset)
            side["looks"] = {part: {**look, **patterns.get(part, {})} for part, look in side["looks"].items()}
        written_measures(folder, truth, side, others, f"{branch} {step}",
                         judged_look(kept, asset, branch, previous, scratch), looked)
    return make


def old_step(address, truth, others):
    def make(folder):
        written_measures(folder, truth, old_side(address), others, address)
    return make


def pictured_side(model, finished=None, take=None):
    """A made model of a pictured case as a side (measures.pictured's): its glTF faces in their glTF materials, or,
    with its finish step's folder, in its finish parts with each part's class (`classes`), surface recipe
    (`families`) and the text of each decal the finish printed on it (`decals`). A part list whose faces are not the
    model's fails."""
    side = gltf_side(model)
    if finished is None:
        return side
    part_of, surfaces = finish.face_finishes(finished, take)
    if len(part_of) != len(side["faces"]):
        raise StepFailed(f"the finish's parts name {len(part_of)} faces, the model has {len(side['faces'])}")
    looks = finish.part_looks(finished, take)
    placed = json.loads((finished / "surfaces-parts" / "parts.json").read_text())["takes"][take].get("decals", [])
    return {**side, "face_material": np.asarray(part_of, dtype=np.int32), "surfaces": surfaces, "looks": looks,
            "classes": {part: look["class"] for part, look in looks.items()},
            "families": {part: finish.family_of(address) for part, address in surfaces.items()},
            "decals": [decal["text"] for decal in placed if decal.get("text")]}


def pictured_measures(folder, row, given, model, side, made, looked=None, judged=None):
    """measures.json of a pictured case's made model: the camera fitted from its outline on the close-up (camera.json
    beside it, its fit the silhouette), every pictured measure (and its look's from its look step's folder `looked`,
    look_found; the picture judge's group `picture`, `judged`, where given) and its judgement at PICTURED_BARS."""
    from tools.props.bench import calibrate, measures
    picture = row["picture"]
    fitted = json.loads(finish.fitted_camera(model, given / "rgba.png", {**row, "size": picture["size"]},
                                             folder).read_text())["fitted"]
    found = measures.pictured(picture["size"], side, fitted["fit"], picture)
    if judged is not None:
        found["picture"] = judged
    look = look_found(looked) if looked is not None else {}
    if look:
        found["look"] = look
    record = {"truth": {"closeup": picture["closeup"], "size": picture["size"], "size_from": picture["size_from"]},
              "made": made, "found": found, "judged": measures.judged(found, measures.PICTURED_BARS)}
    (folder / "measures.json").write_text(json.dumps(calibrate.plain(record), indent=1))


def measure_pictured(row, kept, scratch, previous=None):
    """A pictured case's made models (each branch's, its finish parts where kept; the 2099 session's own makes,
    branch `old`) held to its kept close-up and target size, each kept look by eye to the close-up and the `previous`
    run's look (judged_look); its close-up not kept is its gap on branch `truth`."""
    asset = row["id"]
    if not kept_output(kept, asset, "input", "render"):
        kept.gap(asset, "truth", "read", "StepFailed: no close-up kept (run render first)")
        return
    _, given = given_row(kept, asset, scratch)

    def branch_step(branch):
        def make(folder):
            (step, name), _ = MEASURED[branch]
            model = checked_out(kept, asset, branch, step, scratch / branch / f"kept-{step}") / name
            done = FINISHED.get(branch)
            parted = checked_out(kept, asset, branch, done, scratch / branch / f"kept-{done}") \
                if done and kept_output(kept, asset, branch, done) else None
            look = LOOKED.get(branch)
            looked = checked_out(kept, asset, branch, look, scratch / branch / f"kept-{look}") \
                if look and kept_output(kept, asset, branch, look) else None
            side = pictured_side(model, parted, asset)
            if looked is not None:
                side["face_seen"] = seen_faces(model, looked, side)
            pictured_measures(folder, row, given, model, side, f"{branch} {step}", looked,
                              judged_look(kept, asset, branch, previous, scratch))
        return make

    def old_step_of(address):
        def make(folder):
            kind, model = old_model(address)
            if kind != "gltf":
                raise StepFailed(f"{address}: a USD model; its outline is fitted on glTF alone")
            pictured_measures(folder, row, given, model, gltf_side(model), address)
        return make

    for branch in MEASURED:
        if kept_output(kept, asset, branch, MEASURED[branch][0][0]):
            run_steps(kept, asset, branch, [("measures", branch_step(branch))], scratch)
    for address in row.get("made_before") or []:
        run_steps(kept, asset, "old", [(address.split("/", 1)[1], old_step_of(address))], scratch)


def measure_all(rows, every, kept, run, previous=None):
    """Each asset's made models (both branches, and the withdrawn ones an overlap target replaced) measured against
    its truth; `every` (the whole set) gives the kind's other assets, laid like it for the rank; each look judged
    against the `previous` run's (a Kept) where given. Kept as the
    `measures` step of A and B, and as branch `old`, one step a withdrawn model; a truth that cannot be read is the
    asset's gap on branch `truth`. A pictured case is held to its close-up and target size (measure_pictured)."""
    from tools.props.bench import truth as bench_truth
    for row in rows:
        scratch = job_scratch(run, f"{row['id']}-measures")
        try:
            if row.get("picture"):
                measure_pictured(row, kept, scratch, previous)
                continue
            try:
                truth = bench_truth.read(row["address"])
                others = [{**bench_truth.read(mate["address"]), "id": mate["address"]} for mate in every
                          if mate["kind"] == row["kind"] and mate["address"] != row["address"]]
            except Exception as why:  # the asset's gap, its reason kept; the other assets are still measured
                kept.gap(row["id"], "truth", "read", f"{type(why).__name__}: {why}")
                continue
            for branch in MEASURED:
                if kept_output(kept, row["id"], branch, MEASURED[branch][0][0]):
                    run_steps(kept, row["id"], branch,
                              [("measures", measure_step(kept, row["id"], branch, truth, others, scratch, previous))],
                              scratch)
            for address in row.get("withdrawn") or []:
                run_steps(kept, row["id"], "old", [(address.split("/", 1)[1], old_step(address, truth, others))],
                          scratch)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


# --- the commands ----------------------------------------------------------------------------------------------------

def props_home():
    return pathlib.Path(os.environ.get("PROPS_HOME") or pathlib.Path.home() / ".score-this-pc")


def run_folder(run):
    folder = props_home() / "bench" / run
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def job_scratch(run, asset):
    """This asset's job scratch, emptied when its job ends."""
    folder = props_home() / "tmp" / f"{PLACE}-{run}" / asset
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    return folder


def opened_kept(run):
    from score.store import Store, offload
    offload.install()
    return Kept(Store.default(), offload.open_bucket(), run_folder(run) / "index.json")


def chosen(rows, only):
    return [row for row in rows if not only or row["id"] in only or row["id"].removeprefix("simready_") in only]


def render_one(row, values, kept, run, draw=queued_blender):
    """One asset's close-up kept as its `render` step (branch "input"), its scratch emptied after."""
    scratch = job_scratch(run, row["id"])
    try:
        if row.get("picture"):
            run_steps(kept, row["id"], "input", [("render", lambda folder: pictured_render(row, kept, folder))],
                      scratch)
            return
        run_steps(kept, row["id"], "input", [("render", lambda folder: render_asset(row, values, scratch / "work",
                                                                                     folder, draw))], scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def render_all(rows, values, kept, run, draw=queued_blender):
    """Every asset's close-up, RENDERS_AT_ONCE side by side."""
    with concurrent.futures.ThreadPoolExecutor(RENDERS_AT_ONCE) as pool:
        for done in [pool.submit(render_one, row, values, kept, run, draw) for row in rows]:
            done.result()


def given_row(kept, asset, scratch):
    """The asset's kept close-up folder (closeup.png, rgba.png, row.json) read back into scratch; its row."""
    folder = checked_out(kept, asset, "input", "render", scratch / "input")
    return json.loads((folder / "row.json").read_text()), folder


def route_all(rows, kept, run, branch):
    """Each asset made again by one branch from its kept close-up and row alone."""
    if os.environ.get("SCORE_CLOUD") != "local":
        raise SystemExit("the benchmark's routes run on this PC's card only: set SCORE_CLOUD=local and "
                         "SCORE_FREE_ONLY=1")
    rendered = [row for row in rows if kept_output(kept, row["id"], "input", "render")]
    scratch = {row["id"]: job_scratch(run, f"{row['id']}-{branch}") for row in rendered}
    try:
        given = {row["id"]: given_row(kept, row["id"], scratch[row["id"]]) for row in rendered}
        found = [given[row["id"]][0] for row in rendered]
        material = {row["id"]: material_for(row) for row in rendered}
        if branch == "A":
            closeups = {asset: folder / "closeup.png" for asset, (_, folder) in given.items()}
            branch_a(kept, found, closeups, material, inventory_for(found, run_folder(run)), scratch, run_folder(run))
        else:
            library = functools.cache(lambda: finish.bench_library(os.environ["SCORE_LIB_ROOT"]))
            for row in found:
                branch_b(kept, row, material[row["id"]], given[row["id"]][1] / "rgba.png", scratch[row["id"]],
                         library)
    finally:
        shutil.rmtree(props_home() / "tmp" / f"{PLACE}-{run}", ignore_errors=True)


def stored_index(kept):
    """The run's folder (its index, its inventory, the batch's list and logs) stored as an object, its blobs in the
    bucket; its hash."""
    output = kept.store.put_tree(kept.index_path.parent)
    from score.store import offload
    for sha in set(kept.store.listing(output).values()):
        offload.push(kept.store.objects.path(f"blobs/{sha}"), sha, kept.bucket)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("render", "route", "measure", "index"))
    parser.add_argument("set", nargs="?")
    parser.add_argument("--library", help="a scratch score_lib checkout (git worktree add --detach)")
    parser.add_argument("--run", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--branch", choices=("A", "B"))
    parser.add_argument("--only", action="append", help="this asset's id alone (repeat)")
    parser.add_argument("--previous", help="measure: the previous round's run, whose looks the picture judge holds "
                                           "each look to (#184)")
    options = parser.parse_args()
    kept = opened_kept(options.run)
    if options.command != "index":
        if not options.set or not options.library:
            raise SystemExit("render, route and measure need the set file and --library")
        values = library_values(options.library)
        os.environ["SCORE_LIB_ROOT"] = values["SCORE_LIB_ROOT"]  # every library read of the steps: the scratch one
        every = read_set(options.set)
        rows = chosen(every, options.only)
        kept.index.setdefault("set", str(options.set))
        if options.command == "render":
            render_all(rows, values, kept, options.run)
        elif options.command == "measure":
            measure_all(rows, every, kept, options.run, opened_kept(options.previous) if options.previous else None)
        elif not options.branch:
            raise SystemExit("route needs --branch A or B")
        else:
            route_all(rows, kept, options.run, options.branch)
    print(json.dumps({"run": options.run, "index": str(kept.index_path), "stored": stored_index(kept)}))


if __name__ == "__main__":
    main()
