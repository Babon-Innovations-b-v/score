"""The surface stage's paid Blender row, in a module of its own so a change to the free steps does not rent again: the
turntable of each raw model (inside/turntable.py on rented cards, tools/props/cloud/blender_cloud.py inside the
runner's clearance), its own texture drawn unlit from the close-up's camera and turntable_views.MAP_VIEWS, with the
face under every pixel. The finish-map method draws a finish map of each view and lays it on the faces the view
sees.

Row (place grain, surfaces-turntable@<place>).
"""
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS = REPO / "tools/props"
for folder in (PROPS, PROPS / "library", PROPS / "cloud", pathlib.Path(__file__).resolve().parent):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the prop tools must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from surface_gates import verdict  # noqa: E402

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", PROPS_HOME / "env/bin/python"))
# One processor class, the runner's default: inside/turntable.py renders on the processor (cycles_fixed).
CLASSES = "cpu-32c-128gb"
TAKES_A_JOB = 2  # turntable takes per Blender job, so a batch's jobs run side by side on cards of their own
MINUTES_A_TAKE = 5
# From the ledger's measured runs of the same kind (rounds 1 to 4): a turntable of six takes cost well under a euro;
# set up per machine.
TURNTABLE_EUROS = 3.0
TEXT_CHUNKS = {b"tEXt", b"iTXt", b"zTXt", b"tIME"}
FILES = {"turntable script": "{repo}/score/stages/surfaces/inside/turntable.py",
         "blender runner": "{repo}/tools/props/cloud/blender_cloud.py"}


def inputs_folder(inputs):
    """The input of the row named ...-inputs (surfaces-inputs, the trial's fm-inputs)."""
    return next(pathlib.Path(path) for name, path in inputs.items() if name.endswith("-inputs"))


def run_tool(arguments, log):
    """A cloud runner in the prop environment (the clearance's ticket in the environment), its output kept in
    `log`; fails when it does."""
    done = subprocess.run([str(PROPS_PYTHON), *map(str, arguments)], cwd=REPO, capture_output=True, text=True)
    log.write_text(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"{pathlib.Path(arguments[0]).name} failed: {done.stderr[-2000:]}")


def without_text(path):
    """Rewrite a PNG without its text and time chunks, every other chunk byte for byte: Blender writes the date and
    Cycles' render times into each picture, so two renders of the same pixels were different files and re-keyed every
    row after the turntable (2026-10-12)."""
    data = path.read_bytes()
    kept, at = [data[:8]], 8
    while at < len(data):
        length, kind = struct.unpack(">I4s", data[at:at + 8])
        end = at + 12 + length
        if kind not in TEXT_CHUNKS:
            kept.append(data[at:end])
        at = end
    path.write_bytes(b"".join(kept))


def make_turntable(inputs, out, seed, params):
    """The turntable on rented cards, TAKES_A_JOB takes a Blender job; the face maps then kept compressed."""
    import numpy as np
    job = json.loads((inputs_folder(inputs) / "multiview" / "job.json").read_text())
    renders = out / "renders"
    scratch = out / ".jobs"
    scratch.mkdir(parents=True)
    paths = []
    for start in range(0, len(job["takes"]), TAKES_A_JOB):
        share = job["takes"][start:start + TAKES_A_JOB]
        spec = scratch / f"turntable-{start // TAKES_A_JOB}.json"
        spec.write_text(json.dumps({"out": str(renders), "takes": share}, indent=1))
        blender = scratch / f"blender-{start // TAKES_A_JOB}.json"
        blender.write_text(json.dumps({
            "script": "score/stages/surfaces/inside/turntable.py", "args": [str(spec)],
            "inputs": [str(spec), *[entry["model"] for entry in share]],
            "outputs": [str(renders / entry["take"]) for entry in share],
            "minutes": MINUTES_A_TAKE * len(share) + 5}, indent=1))
        paths.append(blender)
    run_tool([PROPS / "cloud/blender_cloud.py", *paths, "--who", "surfaces", "--classes", CLASSES],
             out / "turntable.log")
    shutil.rmtree(scratch)
    for path in renders.glob("*/*.png"):
        without_text(path)
    for path in renders.glob("*/*-id.npy"):
        np.savez_compressed(path.with_suffix(".npz"), ids=np.load(path))
        path.unlink()


def turntable_faults(folder):
    takes = [path.name for path in (folder / "renders").iterdir()] if (folder / "renders").is_dir() else []
    empty = [take for take in takes if not list((folder / "renders" / take).glob("*-id.npz"))]
    return ([] if takes else ["no renders"]) + ([f"no face maps for {empty}"] if empty else [])


def judge_turntable(output, inputs, evidence):
    """Pass when every take came back with all its views (colour, metal and roughness, face map) and faces.npy."""
    job = json.loads((inputs_folder(inputs) / "multiview" / "job.json").read_text())
    failing = []
    for entry in job["takes"]:
        folder = output / "renders" / entry["take"]
        missing = [view["name"] for view in entry["views"]
                   if not all((folder / f"{view['name']}{suffix}").exists() for suffix in (".png", "-mr.png",
                                                                                             "-id.npz"))]
        if missing or not (folder / "faces.npy").exists():
            failing.append(f"{entry['take']}: missing {missing[:4] or 'faces.npy'}")
    return verdict("turntable", failing, len(job["takes"]), "takes missing views")
