"""The engine adapter: Blender, headless, in the cloud; every run cleared by the compute adapter first.

    spec = engines.blender_job(script, arguments, outputs, code, minutes, euros)  # a job for the blender image
    compute.submit(runner, node, job_store, run, job, spec)                   # the container path (SCORE_CLOUD=k8s)
    engines.blender_on_machines(runner, node, script, arguments, inputs, outputs, classes, minutes,
                                euros)                                       # the default

Both paths are tools/cloud's and tools/props/cloud's as they are (the blender image's command line as
tools/cloud/images/warm.py writes it; blender_cloud.run_elsewhere for a rented machine), wrapped, not rewritten. No
game engine yet: one comes when Godot is built (#2).
"""
import pathlib
import sys

from score.adapters import compute

REPO = pathlib.Path(__file__).resolve().parents[3]
BLENDER = "/opt/blender/blender"


def blender_job(script, arguments, outputs, code, minutes, euros):
    """A job spec running one Blender script headless in the pinned blender image, with its estimate in euros."""
    return {"kind": "blender", "image": compute.job_contract.image("blender"), "code": code, "minutes": minutes,
            "euros": euros,
            "command": [BLENDER, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python", str(script), "--",
                        *(str(argument) for argument in arguments)],
            "outputs": outputs}


def machine_runner():
    """tools/props/cloud/blender_cloud.py, the machine path's Blender runner."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import blender_cloud
    return blender_cloud


def blender_on_machines(runner, node, script, arguments, inputs, outputs, classes, minutes, euros):
    """Run one Blender script on a rented machine for a node cleared at its estimate in euros, its outputs back where
    they belong."""
    ticket = compute.clearance(runner, node, euros)
    machine_runner().run_elsewhere(script, arguments, inputs, outputs, classes, f"{node} {ticket['key'][:12]}",
                                   minutes)
