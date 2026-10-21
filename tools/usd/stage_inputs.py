"""What a stage was made from, by content: a file's and a made model's hash, the inputs record written beside a stage
(inputs.json) and the inventory it names. Kept apart from complete.py, the completion gate, so the exporter, the scene
record and the pick lock hash this small module, not the gate's checks (triage, settle, reach): an edit to a check
moves no export's or terrain's code version.
"""
import datetime
import hashlib
import json
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
INVENTORIES = REPO / "data/inventory"
# A designed place's scene inventory: its locked concept's reading, kept where the plan stage reads it (plans.keep).
DESIGN = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "design/inventory"
INPUTS = "inputs.json"


def inventory_path(place):
    """The place's scene inventory: its design's, else data/inventory's (the people line's)."""
    designed = DESIGN / f"{place}.json"
    return designed if designed.exists() else INVENTORIES / f"{place}.json"


def inventory_pattern(place):
    """inventory_path as a stage's file pattern ({home} or {data})."""
    folder = "{home}/design/inventory/" if (DESIGN / f"{place}.json").exists() else "{data}/inventory/"
    return folder + f"{place}.json"


def now():
    """This moment, in UTC, as text."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def file_hash(path):
    """A file's content as a sha256 hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def model_hash(gltf):
    """A made model's content as a sha256 hex digest: its .gltf and every buffer file it names (a .glb holds its own)."""
    gltf = pathlib.Path(gltf)
    digest = hashlib.sha256(gltf.read_bytes())
    if gltf.suffix == ".glb":
        return digest.hexdigest()
    for buffer in json.loads(gltf.read_text()).get("buffers", []):
        if buffer.get("uri") and not buffer["uri"].startswith("data:"):
            digest.update(file_hash(gltf.parent / buffer["uri"]).encode())
    return digest.hexdigest()


def input_name(path):
    """How an input is named in a stage's inputs record: its path in the repository, or its full path outside it."""
    resolved = pathlib.Path(path).resolve()
    return str(resolved.relative_to(REPO)) if resolved.is_relative_to(REPO) else str(resolved)


def record_inputs(out, inventory, inputs, models, hashes=None):
    """Write what a stage was exported from beside it (inputs.json): the inventory it was laid from, each input file
    by its content, and each made model (.gltf) by its content, file and time, for the gate to tell when the stage is
    older than they are. `models` is {model: its .gltf}, `hashes` their model_hash when already worked out; inputs that do
    not exist are left out."""
    hashes = hashes or {}
    written = {"at": now(), "inventory": input_name(inventory),
               "inputs": {input_name(path): file_hash(path) for path in [inventory, *inputs] if pathlib.Path(path).exists()},
               "models": {model: {"file": str(pathlib.Path(gltf).resolve()), "sha256": hashes.get(model) or model_hash(gltf),
                                  "mtime": pathlib.Path(gltf).stat().st_mtime_ns}
                          for model, gltf in sorted(models.items())}}
    (pathlib.Path(out) / INPUTS).write_text(json.dumps(written, indent=1) + "\n")
    return written


def recorded_inventory(place, stage):
    """The inventory a stage was laid from, as its inputs record names it; else the place's own."""
    record = pathlib.Path(stage).parent / INPUTS
    if record.exists():
        return REPO / json.loads(record.read_text())["inventory"]
    return inventory_path(place)
