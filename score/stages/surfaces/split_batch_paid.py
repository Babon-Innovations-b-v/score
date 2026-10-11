"""The paid rows of the g-texture method (turntable, unlit, regions, the judge, finish-masks), in a module of their own
that imports nothing of split_batch.py, so their code version is theirs alone: a change to the free steps (the
inputs, the asks, the prompts, the split and its gate) does not rent and pay for these again. Each make runs a cloud
runner of tools/props/cloud in the prop environment inside the runner's clearance (SCORE_SPEND_TICKET). The judge
(both judge rows, split-judge and surfaces-judge) asks Gemini 3.1 Pro through tools/props/cloud/gemini_judge.py:
temperature 0, the answer an enum of the question's codes plus "unknown", one ask each, each request asked once
(google_spend's cache, by its input's hash) and priced on the Google ledger.
"""
import json
import os
import pathlib
import shutil
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
WORK = PROPS_HOME / "work"
CLASSES = "gpu-24gb,gpu-48gb,gpu-80gb"
TAKES_A_JOB = 2  # turntable takes per Blender job, so a batch's jobs run side by side on cards of their own
MINUTES_A_TAKE = 5
NO_VERDICT_MOST = 0.02  # the judge's replies with no verdict at most this share
ASK_ROUNDS = 3  # the asker runs at most this many times while asks are left (a request the API lost)
# Estimates (EUR) for the runner's clearance, from the ledger's measured runs of the same kinds (rounds 1 to 4): a
# turntable of six takes, the unlit copies and SAM 2.1 of six pictures, SAM 3 over 102 views each cost well under a
# euro; set up per machine. The judge: $8.20 per 1,000 asks measured (judge-decision.txt); a place's asks (a few
# hundred) stay under JUDGE_EUROS.
TURNTABLE_EUROS, UNLIT_EUROS, REGIONS_EUROS, MASKS_EUROS, JUDGE_EUROS = 3.0, 1.5, 1.5, 3.0, 3.0


def inp(inputs, step):
    """The input of the row named ...-<step> (split-inputs, surfaces-seed-inputs, surfaces-asks)."""
    return next(pathlib.Path(path) for name, path in inputs.items() if name.endswith(f"-{step}"))


def takes_of(folder):
    return json.loads((pathlib.Path(folder) / "flat" / "takes.json").read_text())


def run_tool(arguments, log):
    """A cloud runner in the prop environment (the clearance's ticket in the environment), its output kept in
    `log`; fails when it does."""
    done = subprocess.run([str(PROPS_PYTHON), *map(str, arguments)], cwd=REPO, capture_output=True, text=True)
    log.write_text(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"{pathlib.Path(arguments[0]).name} failed: {done.stderr[-2000:]}")


# --- turntable ------------------------------------------------------------------------------------------------------

def make_turntable(inputs, out, seed, params):
    """The turntable on rented cards, TAKES_A_JOB takes a Blender job; the face maps then kept compressed."""
    import numpy as np
    job = json.loads((pathlib.Path(inp(inputs, "inputs")) / "multiview" / "job.json").read_text())
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
    for path in renders.glob("*/*-id.npy"):
        np.savez_compressed(path.with_suffix(".npz"), ids=np.load(path))
        path.unlink()


def turntable_faults(folder):
    takes = [path.name for path in (folder / "renders").iterdir()] if (folder / "renders").is_dir() else []
    empty = [take for take in takes if not list((folder / "renders" / take).glob("*-id.npz"))]
    return ([] if takes else ["no renders"]) + ([f"no face maps for {empty}"] if empty else [])


def judge_turntable(output, inputs, evidence):
    """Pass when every take came back with all its views (colour, metal and roughness, face map) and faces.npy."""
    job = json.loads((pathlib.Path(inp(inputs, "inputs")) / "multiview" / "job.json").read_text())
    failing = []
    for entry in job["takes"]:
        folder = output / "renders" / entry["take"]
        missing = [view["name"] for view in entry["views"]
                   if not all((folder / f"{view['name']}{suffix}").exists() for suffix in (".png", "-mr.png",
                                                                                             "-id.npz"))]
        if missing or not (folder / "faces.npy").exists():
            failing.append(f"{entry['take']}: missing {missing[:4] or 'faces.npy'}")
    return verdict("turntable", failing, len(job["takes"]), "takes missing views")


# --- unlit ----------------------------------------------------------------------------------------------------------

def make_unlit(inputs, out, seed, params):
    """The close-ups' unlit copies (delight.py, into WORK/unlit as split-<take>.png), each laid on its close-up's matte
    as seg-unlit/<take>.png."""
    import numpy as np
    from PIL import Image
    folder = pathlib.Path(inp(inputs, "inputs"))
    takes = list(takes_of(folder))
    named = out / ".named"
    named.mkdir(parents=True)
    pictures = []
    for take in takes:
        target = named / f"split-{take}.png"
        shutil.copy2(folder / "unlit-in" / f"{take}.png", target)
        pictures.append(target)
    if [path for path in pictures if not (WORK / "unlit" / path.name).exists()]:
        run_tool([PROPS / "cloud/delight.py", *pictures], out / "unlit.log")
    (out / "seg-unlit").mkdir()
    for take in takes:
        unlit = np.asarray(Image.open(WORK / "unlit" / f"split-{take}.png").convert("RGB"))
        matte = np.asarray(Image.open(WORK / "pixal" / f"{take}.svviews" / "input.png").convert("RGBA"))[..., 3:]
        Image.fromarray(np.concatenate([unlit, matte], axis=-1), "RGBA").save(out / "seg-unlit" / f"{take}.png")
    shutil.rmtree(named)


def unlit_faults(folder):
    return [] if (folder / "seg-unlit").is_dir() and list((folder / "seg-unlit").glob("*.png")) else ["no seg-unlit"]


def judge_unlit(output, inputs, evidence):
    """Pass when every take has its unlit copy at its close-up's size."""
    from PIL import Image
    failing = []
    for take in takes_of(inp(inputs, "inputs")):
        path = output / "seg-unlit" / f"{take}.png"
        close = Image.open(WORK / "pixal" / f"{take}.svviews" / "input.png").size
        if not path.exists() or Image.open(path).size != close:
            failing.append(take)
    return verdict("unlit", failing, len(takes_of(inp(inputs, "inputs"))), "takes without an unlit copy")


# --- regions --------------------------------------------------------------------------------------------------------

def make_regions(inputs, out, seed, params):
    """SAM 2.1's regions of every unlit copy (segment.py), into seg-unlit/masks/<take>.npz beside the pictures."""
    shutil.copytree(pathlib.Path(inp(inputs, "unlit")) / "seg-unlit", out / "seg-unlit")
    for path in (out / "seg-unlit").glob("*.png"):
        path.chmod(0o644)
    run_tool([PROPS / "cloud/segment.py", out / "seg-unlit", "--who", "surfaces"], out / "regions.log")


def regions_faults(folder):
    return [] if (folder / "seg-unlit" / "masks").is_dir() else ["no seg-unlit/masks"]


def judge_regions(output, inputs, evidence):
    """Pass when every take's unlit copy has its masks."""
    takes = takes_of(inp(inputs, "inputs"))
    failing = [take for take in takes if not (output / "seg-unlit" / "masks" / f"{take}.npz").exists()]
    return verdict("regions", failing, len(takes), "takes without masks")


# --- judge ----------------------------------------------------------------------------------------------------------

def make_judge(inputs, out, seed, params):
    """The asks answered by the judge (gemini_judge, the models adapter's gemini-judge) into <out>/answers; a request
    the API lost is asked again."""
    import gemini_judge
    folder = inp(inputs, "asks")
    asks = json.loads((folder / "asks.json").read_text())
    answers = out / "answers"
    answers.mkdir()
    listing = out / ".asks-here.json"
    listing.write_text(json.dumps([dict(job, images=[str(folder / image) for image in job["images"]])
                                   for job in asks]))
    try:
        for _ in range(ASK_ROUNDS):
            if not gemini_judge.to_ask(listing, answers):
                break
            gemini_judge.ask(listing, answers)
    finally:
        listing.unlink()


def answers_faults(folder):
    return [] if (folder / "answers").is_dir() else ["no answers/"]


def judge_answered(output, inputs, evidence):
    """Fail on any ask without a reply, or more than NO_VERDICT_MOST of the replies without a verdict."""
    import part_judge
    asks = json.loads((pathlib.Path(inp(inputs, "asks")) / "asks.json").read_text())
    replies = {job["name"]: output / "answers" / f"{job['name']}.txt" for job in asks}
    missing = [name for name, path in replies.items() if not path.exists()]
    empty = [name for name, path in replies.items() if path.exists() and part_judge.answer_of(path.read_text()) is None]
    failing = missing + (empty if len(empty) > NO_VERDICT_MOST * len(asks) else [])
    return verdict("judge", failing, len(asks), "asks without a reply or a verdict")


# --- finish-masks ---------------------------------------------------------------------------------------------------

def make_masks(inputs, out, seed, params):
    """SAM 3 per finish over every view (finish_masks.py), the masks into sam3/masks/."""
    shutil.copytree(pathlib.Path(inp(inputs, "prompts")) / "sam3", out / "sam3")
    for path in (out / "sam3").iterdir():
        path.chmod(0o644)
    run_tool([PROPS / "cloud/finish_masks.py", out / "sam3", "--who", "surfaces"], out / "masks.log")


def masks_faults(folder):
    return [] if (folder / "sam3" / "masks").is_dir() else ["no sam3/masks"]


def judge_masks(output, inputs, evidence):
    """Pass when every view picture has its masks."""
    pictures = sorted((output / "sam3").glob("*.png"))
    failing = [path.stem for path in pictures if not (output / "sam3" / "masks" / f"{path.stem}.npz").exists()]
    return verdict("masks", failing, len(pictures), "views without masks")
