"""The character maker's animal route: one animal from its spec to a rigged, animated character, every model step and
every Blender run on rented machines (job characters-full, 2026-10-09).

    import route
    route.make(spec, folder, who="<session>", dry_run=False)

`spec` is a character spec (data/characters/makes/<name>.json, read by ../maker/spec.py) with "kind": "animal", its
"picture" (a side-on close-up), "body" ("fish" or "quadruped"), "length_m" and "clips"; `folder` is where the make
lands (~/.farm-factory-motion/made/<name>/). The steps, each skipped when its output is already there:

1. mesh    Pixal3D from the picture (../../props/cloud/batch.py --characters), finished as every batch model is
2. rig     a quadruped through UniRig on a card (../../props/cloud/unirig.py); a fish gets a spine made in Blender
3. clips   blender_rig.py on one held cloud machine: stood, scaled, rigged, its clips keyed, <name>.glb and lods/
4. review  blender_review.py on the same machine: review/turntable/ and review/<clip>/ frames, and a GIF of each
5. usd     usd/<name>.usdc through ../skel_usd.py (plain Python)

make.json records each step: what ran, how long it took, and the cloud runs it caused (machines, card types, minutes,
euros) as the ledger has them.
"""
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "props"))
sys.path.insert(0, str(HERE.parent.parent / "props" / "cloud"))

from paths import WORK  # noqa: E402

CLOUD_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
CLOUD = HERE.parent.parent / "props" / "cloud"
# The review renders want a card (Cycles), else a 32-core processor machine when no card is in stock; the rig job
# runs on the same machine first.
CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb", "cpu-32c-128gb", "cpu-32c-64gb")
# The lighter copies: a share of the triangles for the middle distance, a count for the far one (a school of fish,
# a street's dogs).
LODS = {"fish": [["lod1", 0.15], ["lod2", 400]], "quadruped": [["lod1", 0.15], ["lod2", 1500]]}
BLENDER_MINUTES = {"rig": 5, "review": 20}


def model_path(spec):
    """Where the batch leaves the animal's finished model."""
    return WORK / "pixal" / f"{spec['name']}-final.glb"


def run(command):
    """A runner as its own process; raises when it fails."""
    done = subprocess.run([str(part) for part in command])
    if done.returncode:
        raise RuntimeError(f"{command[1]} failed with {done.returncode}")


def mesh(spec, folder, who, dry_run):
    """Step 1: the finished model from the picture (batch.py --characters)."""
    spec_file = folder / "work" / "spec.json"
    spec_file.write_text(json.dumps(spec, indent=1))
    command = [CLOUD_PYTHON, CLOUD / "batch.py", "--characters", spec_file, "--who", who, "--max-cards", "1"]
    run(command + (["--dry-run"] if dry_run else []))
    return model_path(spec)


def unirig(model, folder, who, dry_run):
    """Step 2 for a quadruped: the model with UniRig's skeleton and skin weights."""
    out = folder / "work" / "unirig"
    run([CLOUD_PYTHON, CLOUD / "unirig.py", model, "--out", out, "--who", who] + (["--dry-run"] if dry_run else []))
    return out / f"{model.stem}-unirig.glb"


def rig_job(spec, folder, model):
    """blender_rig.py's job for the animal, written beside the make."""
    body = spec.get("body", "quadruped")
    job = {"name": spec["name"], "body": body, "model": str(model), "rig": "spine" if body == "fish" else "unirig",
           "length_m": spec["length_m"], "clips": spec["clips"], "out": str(folder), "lods": LODS[body]}
    path = folder / "work" / "rig-job.json"
    path.write_text(json.dumps(job, indent=1))
    return path


def gifs(review, clips):
    """A looping GIF of the turntable and of each clip from its frames, at the frames' own pace."""
    from PIL import Image
    for name, seconds in [("turntable", 0.25)] + [(clip, 2 / 30) for clip in clips]:
        frames = [Image.open(path).convert("RGB") for path in sorted((review / name).glob("*.png"))]
        if frames:
            frames[0].save(review / f"{name}.gif", save_all=True, append_images=frames[1:],
                           duration=int(seconds * 1000), loop=0)


def blender_steps(spec, folder, model, who):
    """Steps 3 and 4 on one held cloud machine: the rig and clips, then the review frames from the exported file."""
    import blender_cloud
    job = rig_job(spec, folder, model)
    made = folder / f"{spec['name']}.glb"
    review = folder / "review"
    with blender_cloud.Machine(CLASSES, who, minutes=sum(BLENDER_MINUTES.values())) as machine:
        machine.run(HERE / "blender_rig.py", [job], [job, model],
                    [made, folder / "lods", folder / "rig.json"], BLENDER_MINUTES["rig"])
        machine.run(HERE / "blender_review.py", [made, review, *spec["clips"]], [made], [review],
                    BLENDER_MINUTES["review"])
    gifs(review, spec["clips"])
    return made


def usd(made, folder):
    """Step 5: the UsdSkel asset, every mesh of the file worn."""
    import skel_usd
    return skel_usd.convert(made, folder / "usd", worn=None)


def cloud_runs(name, who, since):
    """The ledger's runs for this make since `since` (a UTC time stamp): the batch that made its model, the UniRig
    run that named it and the Blender machine asked for under `who`."""
    import ledger
    runs = []
    for entry in ledger.entries():
        if entry.get("started", "") < since:
            continue
        models = entry.get("models")
        named = models if isinstance(models, list) else []
        ours = name in entry.get("job_seconds", {}) or any(model.startswith(name) for model in named)
        if ours or entry.get("who") == who:
            runs.append({"kind": entry.get("kind"), "batch": entry.get("batch"), "wall_minutes": entry.get("wall_minutes"),
                         "euros": entry.get("euros"),
                         "machines": [{"type": row["type"], "minutes": round(row["minutes"], 2), "euros": row["euros"]}
                                      for row in entry.get("machines", [])]})
    return runs


def step(record, label, work):
    """Run one step, recording how long it took (or that it failed, and why) in `record`."""
    began = time.time()
    try:
        result = work()
    except Exception as failed:
        record["steps"].append({"step": label, "failed": str(failed), "minutes": (time.time() - began) / 60})
        raise
    record["steps"].append({"step": label, "minutes": round((time.time() - began) / 60, 2)})
    return result


def make(spec, folder, who, dry_run=False):
    """Make the animal of `spec` into `folder`: its glTF with skin and clips, lods/, usd/, review/ and make.json.
    With `dry_run` the cloud steps are only priced. Returns the make's record."""
    folder = pathlib.Path(folder)
    (folder / "work").mkdir(parents=True, exist_ok=True)
    who = f"{who} ({spec['name']})"
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {"name": spec["name"], "kind": "animal", "body": spec.get("body"), "started": since, "steps": []}
    try:
        model = model_path(spec)
        if not model.exists() or dry_run:
            model = step(record, "mesh: Pixal3D (cloud), finished as a batch finishes", lambda: mesh(spec, folder, who,
                                                                                                   dry_run))
        if spec.get("body", "quadruped") != "fish":
            model = step(record, "rig: UniRig (cloud)", lambda: unirig(model, folder, who, dry_run))
        if dry_run:
            return record
        made = step(record, "clips and review: Blender (cloud)", lambda: blender_steps(spec, folder, model, who))
        step(record, "usd: UsdSkel", lambda: usd(made, folder))
    finally:
        record["cloud"] = cloud_runs(spec["name"], who, since)
        record["euros"] = round(sum(entry["euros"] or 0 for entry in record["cloud"]), 2)
        (folder / "make.json").write_text(json.dumps(record, indent=1))
    return record
