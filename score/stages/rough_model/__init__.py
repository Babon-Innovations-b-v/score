"""rough-model@<place>: the place's rough model (CONTEXT.md "rough model", shapes first): its concept put through the
prop pipeline whole, Pixal3D in a cloud batch (tools/props/cloud/batch.py's own command, through _cloud.py), one 3D
model that gives the place's plan its proportions and shape; never shipped. Paid, cleared by the runner like any paid
row. A row of every place with a plan (scene_record.written, as plan@<place>), outside shells and inside places alike.

    reads   plan@<place> (place-plan v2), and the concept picture the place's plan names (files `concept`): the
            creator's pick, which the plan was read from
    makes   rough.glb (the take's finished model, <take>-final.glb as the batch brings it back into WORK/pixal, in
            Pixal3D's own size, Y up) and rough.json {place, take, concept (its file's name), concept_sha256,
            model_sha256}
    gates   made     rough.glb is a binary glTF with triangles; its extent measured in its own mesh frame (wide, high,
                     deep), measures only: no proportion threshold is measured yet
            concept  the model was made from the concept this node read (its sha256 as rough.json names it)


The take is named for the place and its concept's hash (take_name), so a new concept is a new take, and a take the
batch already brought back is not made again (the batch refuses to overwrite one); one brought back raw whose finish
failed is finished here, as the batch finishes every take (pixal.py --finish-only).
"""
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess

from score import contracts
import score.stages.props.prop_data as prop_data  # the module, not the package: the table stays out of the code
import score.stages.scene_record.plan as plan_row
from score.stages.rough_model import _cloud
from score.stages.surfaces.prop_env import PROPS_PYTHON
from score.stages.surfaces.surface_gates import guarded, verdict

REPO = pathlib.Path(__file__).resolve().parents[3]
CLOUD = pathlib.Path(__file__).resolve().parent / "_cloud.py"
TOOLS = {"batch": "{repo}/tools/props/cloud/batch.py", "pixal": "{repo}/tools/props/pixal.py",
         "rough cloud": "{repo}/score/stages/rough_model/_cloud.py"}
# The row's estimate, for its clearance only and never shown as a price (compute.run_price keeps it as guess_euros):
# no rough-model run is measured. The four one-model Pixal3D batches in paper/evidence/cloud/ledger.jsonl
# (2026-10-09) cost EUR 0.26 to 1.42 each, rounded up. Pixal's measured per-model unit (data/costs/per-unit.json) is
# not carried over: it is measured over batches of many models that share one set-up, and a rough model is a batch of
# one.
EUROS = 1.5
MODEL, RECORD = "rough.glb", "rough.json"
GLB_MAGIC, JSON_CHUNK = b"glTF", 0x4E4F534A
TRIANGLES = 4  # a glTF primitive's mode for triangles, its default


def files(place):
    """The concept picture and the inventory the place's plan row reads (scene_record.plan.files: the batch builds
    only from an approved inventory) and the tools the make runs; no style: Pixal3D is worded by nothing."""
    read = plan_row.files(place)
    return {**({"concept": read["concept"]} if "concept" in read else {}), "inventory": read["inventory"], **TOOLS}


def plan_record(inputs):
    return json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())


def concept_of(inputs, place):
    """The place's concept picture, as its plan names it; refused with none."""
    if "concept" not in inputs:
        raise ValueError(f"{place}: no concept picture: its plan names none")
    return pathlib.Path(inputs["concept"])


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def take_name(place, concept_hash):
    """The take's name: the place's, with its concept's hash, so a new concept is a new take."""
    return f"{place}-rough-{concept_hash[:12]}"


def take_files(take):
    """(raw model, finished model) of a take in WORK/pixal, where the batch brings it back."""
    with prop_data.tools("props"):
        from paths import WORK
    return WORK / "pixal" / f"{take}.glb", WORK / "pixal" / f"{take}-final.glb"


def dispatch(take, picture, place, inventory, out):
    """The take made by the cloud batch (_cloud.py), its log in the output folder."""
    (out / "list.txt").write_text(f"{take} {picture}\n")
    done = subprocess.run([str(PROPS_PYTHON), str(CLOUD), str(out / "list.txt"), "--who", f"score rough-model {place}",
                           "--inventory", str(inventory)], cwd=REPO, capture_output=True, text=True)
    (out / "batch.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"the rough model's Pixal3D batch failed (exit {done.returncode}); its log is batch.log")


def finish(take, picture, out):
    """A take brought back raw whose finish never ran or failed, finished here as the batch finishes every take:
    pixal.py --finish-only (Blender and the processor, no model) in the batch's interpreter, under one of the PC's
    finish slots the batches share (batch.finish_slot), its log in the output folder."""
    batch = _cloud.load_batch()
    with batch.finish_slot(), (out / "finish.log").open("a") as log:
        done = subprocess.run([str(batch.VENV_PYTHON), str(REPO / "tools/props/pixal.py"), str(picture), take,
                               "--who", "score rough-model", "--finish-only"], cwd=REPO, stdout=log,
                              stderr=subprocess.STDOUT)
    if done.returncode:
        raise RuntimeError(f"the finish of {take} failed (exit {done.returncode}); its log is finish.log")


def make(inputs, out, seed, params):
    """rough.glb, the place's concept made into one model by the cloud batch where its take is not made yet, and
    rough.json."""
    place = plan_record(inputs)["place"]
    picture = concept_of(inputs, place)
    concept_hash = sha256(picture)
    take = take_name(place, concept_hash)
    raw, final = take_files(take)
    if not raw.exists():
        dispatch(take, picture, place, inputs["inventory"], out)
    if not final.exists():
        finish(take, picture, out)
    shutil.copyfile(final, out / MODEL)
    (out / RECORD).write_text(json.dumps({"place": place, "take": take, "concept": picture.name,
                                          "concept_sha256": concept_hash, "model_sha256": sha256(out / MODEL)},
                                         indent=1))


def faults(folder):
    return [f"no {name}" for name in (MODEL, RECORD) if not (folder / name).exists()]


# Y up as the finish stands it (glb_file.py); no length unit: Pixal3D's model has a size of its own, not metres.
CONTRACT = contracts.Contract("rough-model", 1, faults, {"up axis": "Y"})


def glb_json(path):
    """A binary glTF's JSON chunk; ValueError for a file that is not one."""
    data = pathlib.Path(path).read_bytes()
    if len(data) < 20 or data[:4] != GLB_MAGIC:
        raise ValueError(f"{path.name} is not a binary glTF")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != JSON_CHUNK:
        raise ValueError(f"{path.name}: its first chunk is not its JSON")
    return json.loads(data[20:20 + length])


def triangles(gltf):
    """The triangles of every triangle primitive: its indices' count over three, else its positions'."""
    accessors = gltf.get("accessors", [])
    return sum(accessors[primitive.get("indices", primitive["attributes"]["POSITION"])]["count"] // 3
               for mesh in gltf.get("meshes", []) for primitive in mesh["primitives"]
               if primitive.get("mode", TRIANGLES) == TRIANGLES)


def extent(gltf):
    """(wide, high, deep) of every primitive's positions together, in the mesh frame (node transforms not applied)."""
    accessors = gltf.get("accessors", [])
    bounds = [accessors[primitive["attributes"]["POSITION"]] for mesh in gltf.get("meshes", [])
              for primitive in mesh["primitives"]]
    low = [min(bound["min"][axis] for bound in bounds) for axis in range(3)]
    high = [max(bound["max"][axis] for bound in bounds) for axis in range(3)]
    return tuple(round(high[axis] - low[axis], 4) for axis in range(3))


def judge_made(output, inputs, evidence):
    """rough.glb is a binary glTF with triangles; its extent measured."""
    try:
        gltf = glb_json(output / MODEL)
    except ValueError as wrong:
        return verdict("made", [str(wrong)], 1, "models")
    count = triangles(gltf)
    if not count:
        return verdict("made", [f"{MODEL} has no triangles"], 1, "models")
    wide, high, deep = extent(gltf)
    return verdict("made", [], 1, "models", {"triangles": count, "wide": wide, "high": high, "deep": deep})


def judge_concept(output, inputs, evidence):
    """The model was made from the concept this node read: rough.json names its sha256."""
    record = json.loads((output / RECORD).read_text())
    read = sha256(concept_of(inputs, record["place"]))
    failing = [] if record["concept_sha256"] == read else [
        f"made from a concept of sha256 {record['concept_sha256'][:12]}, the node read {read[:12]}"]
    return verdict("concept", failing, 1, "models")


CHECKS = (guarded("made", judge_made), guarded("concept", judge_concept))
# The plan the rough model is made beside (scene_record.plan.PLACE_PLAN), as this row was written for it.
AFTER = {"plan": ("place-plan", 2)}
