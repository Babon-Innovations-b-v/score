"""The sim body's run (score/stages/sim_body/inside/sim_body.py) handed LabValidation trials as the stage hands it a
cast: one job.json a trial (its person's rig, segments, targets, mass), the lab's floor a flat square at y = 0
under the clip's path, and a measure folder (tools/cloud/sim_measure: scripts/go.sh, its done markers) that runs every
trial's job once on a rented card."""
import json
import pathlib

import numpy as np

from score.stages import sim_body
from tools.labval._files import G

GO = """#!/usr/bin/env bash
# LabValidation sim body runs (tools/labval): every trials/<trial>/job.json run once, done when its out.json is there.
# PY, REPO and LANES come from the machine (tools/cloud/sim_measure/on_machine.py); no path is written here.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${REPO}" OMP_NUM_THREADS=4
for trial in "${HERE}"/trials/*/; do [ -f "${trial}out.json" ] || printf '%s\\n' "${trial}"; done | \\
  xargs -r -P "${LANES}" -I{} sh -c 'systemd-run --user --scope --quiet "${PY}" \\
    "${REPO}/tools/cloud/backends/card_queue.py" run --job labval-sim-body --priority sim-body -- \\
    "${PY}" "${REPO}/score/stages/sim_body/inside/sim_body.py" "$1job.json" "$1out.json" > "$1run.log" 2>&1 \\
    || echo "failed: $1 (its run.log)"' _ {}
"""


def floor_under(worlds):
    """The lab's floor under a clip (2 x 3 x 3 triangles, y = 0, the person's frame): a square over its segments'
    span across the ground grown by sim_body.REACH."""
    path = np.asarray(worlds)[:, :, [0, 2], 3].reshape(-1, 2)
    (low_x, low_z), (high_x, high_z) = path.min(axis=0) - sim_body.REACH, path.max(axis=0) + sim_body.REACH
    corners = np.array([[low_x, 0.0, low_z], [high_x, 0.0, low_z], [high_x, 0.0, high_z], [low_x, 0.0, high_z]])
    return np.array([corners[[0, 1, 2]], corners[[0, 2, 3]]])


def written_person(name, rig, worlds, segments, kg, folder):
    """One person of a job (inside/sim_body.py's `people` entry) with its targets npz written into `folder`: the
    subject's stated mass (LabValidation's sessionMetadata), its SOMA body's own standing height (the stage's
    `standing_height`: the run's body is the SOMA body's), and each foot's seen stance where the rig has one
    (`_soma.person`'s `stance`), and what the clip rests on beside the floor (its `supports`: a chair, a box) in
    its ground."""
    targets = pathlib.Path(folder) / "targets.npz"
    seen = {"stance": np.asarray(rig["stance"], dtype=bool)} if "stance" in rig else {}
    ground = np.concatenate([floor_under(worlds), np.reshape(rig.get("supports", ()), (-1, 3, 3))])
    np.savez_compressed(targets, world=worlds, ground=ground, points=rig["points"], faces=rig["faces"],
                        weights=rig["weights"], **seen)
    return {"name": name, "kg": float(kg), "height": sim_body.standing_height(rig),
            "rig": {"names": [str(joint) for joint in rig["names"]], "parents": np.asarray(rig["parents"]).tolist(),
                    "bind": np.asarray(rig["bind"]).tolist()}, "segments": list(segments), "targets": str(targets)}


def job_of(people, model):
    """A run's job.json: the stage's rate, Earth's gravity, the fetched model and the stage's own limits and caps."""
    return {"rate": sim_body.RATE, "gravity": G, "model": str(model), "people": people,
            "residual": {"force": sim_body.RESIDUAL_FORCE, "moment": sim_body.RESIDUAL_MOMENT},
            "adjust": {"move most m": sim_body.MOVE_MOST, "turn most deg": sim_body.FOLLOWED,
                       "follows deg": sim_body.FOLLOWED}}


def write_go(folder):
    """The measure folder's scripts/go.sh (GO), executable."""
    script = pathlib.Path(folder) / "scripts" / "go.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(GO)
    script.chmod(0o755)
    return script


def write_trial(folder, trial, person, model, record):
    """trials/<trial>/job.json (one person: the trial's subject) and record.json (the adapter's record) under the
    measure folder."""
    mine = pathlib.Path(folder) / "trials" / trial
    (mine / "job.json").write_text(json.dumps(job_of([person], model)))
    (mine / "record.json").write_text(json.dumps(record, indent=1))
    return mine
