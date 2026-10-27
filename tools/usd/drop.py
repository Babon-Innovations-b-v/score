"""The settle's drop (settle.py's drop job, run): each loose object let fall onto the stage's real ground in Newton,
MuJoCo's solver on Newton's own contacts, in the physics trial's own pinned Python
(score/stages/physics/inside/newton_env.sh), on a rented card or this PC. The script it runs is
score/stages/settling/inside/settle_drop.py; its record is what settle.rest_poses reads.

    found = drop.simulate(stage_path, loose, folder, cloud=True, ignore=..., start=..., under=..., cache=DROPS)

Kept out of settle.py, which sits in the code of about 90 rows (triage imports settle): an edit there moves them all,
while this file is read by the settle stage and the assembly's drop run alone.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
INSIDE = REPO / "score/stages/settling/inside/settle_drop.py"
# The trial script whose USD-to-triangle helpers the drop borrows, and the Python both run in (pinned, built once
# where it runs).
TRIAL = REPO / "score/stages/physics/inside/physics_trial.py"
ENV = REPO / "score/stages/physics/inside/newton_env.sh"
LOCAL_ENV = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "envs/newton_env"
# A drop takes the physics trial's card and nothing else (#21: one class decided before the batch; PRD #55: Newton's
# contacts and solve on a card). None in stock: the drop waits for a machine of the run's warm pool, or for stock (no
# stock never makes a gap: owner, 2026-10-23).
DROP_CLASSES = ("gpu-24gb",)
MINUTES = 30


def simulate(stage_path, loose, folder, cloud=False, ignore=(), start=None, under=None, cache=None):
    """The Newton run: how each loose object moved from as laid to at rest (stage frame, column vectors), how fast it
    still moved at the end, and the static objects it started inside; `ignore` are objects left out of the statics
    (settle.part_objects, held_on_loose, fixtures_on_loose), `start` the motions that stand objects upright before
    their drop (settle.upright_starts) and `under` what each is stacked on (settle.stacked_under). With a `cache`
    folder, a cloud drop of the very same job on the very same stage with the same drop script and Python is not paid
    for twice (drop_key)."""
    folder.mkdir(parents=True, exist_ok=True)
    job, out = folder / "settle-job.json", folder / "settled.json"
    job.write_text(json.dumps({"loose": sorted(loose), "lift": loose, "ignore": sorted(ignore),
                               "start": {name: [list(map(float, row)) for row in motion]
                                         for name, motion in (start or {}).items()},
                               "under": under or {}}, indent=1))
    if out.exists():
        out.unlink()
    if cloud:  # a rented card (tools/cloud/blender_cloud.py runs the script in the env's Python), not this PC
        kept = pathlib.Path(cache) / drop_key(stage_path, job) / "settled.json" if cache else None
        if kept is not None and kept.exists():
            out.write_bytes(kept.read_bytes())
            return json.loads(out.read_text())
        sys.path.insert(0, str(REPO / "tools/cloud"))
        import blender_cloud
        with blender_cloud.Machine(DROP_CLASSES, "settle") as machine:
            machine.run(INSIDE, [stage_path, job, out], [stage_path.parent, job], [out], MINUTES, env=ENV)
        if kept is not None:
            kept.parent.mkdir(parents=True, exist_ok=True)
            kept.write_bytes(out.read_bytes())
        return json.loads(out.read_text())
    subprocess.run(["bash", str(ENV), str(LOCAL_ENV)], check=True)
    command = [str(LOCAL_ENV / "bin/python"), str(INSIDE), str(stage_path), str(job), str(out)]
    if subprocess.run(command, stdout=subprocess.DEVNULL).returncode != 0 or not out.exists():
        raise RuntimeError(f"the settle drop failed; run it by hand to see its output: {command}")
    return json.loads(out.read_text())


def drop_key(stage_path, job):
    """A drop's identity: the hash of its job, the drop script, the trial script it borrows from, its Python's pins
    and every file of the stage's folder."""
    digest = hashlib.sha256(b"".join(pathlib.Path(path).read_bytes() for path in (job, INSIDE, TRIAL, ENV)))
    folder = pathlib.Path(stage_path).parent
    for path in sorted(item for item in folder.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(folder)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
