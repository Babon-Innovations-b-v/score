"""Runs inside Blender on a rented processor machine (tools/props/cloud/blender_cloud.py, the surface stage's paint,
../place_line.py make_paint): hands one take's paint to Blender's own Python, outside Blender, with the prop
environment's packages at their pinned versions (installed once a machine into SITE), and says its peak memory.

    blender -b --python paint_take.py -- <listing>    (the listing: the paint's inputs, the take, its part records)

The paint is place_line.py's `paint-take` step, from the repository at its own path (an input of the job), with
PROPS_HOME at this PC's so the take's models are found where they were sent, and FARM_LOCAL_MODELS=1, the cloud
runners' mark that lets a heavy step run (tools/props/local_models.py).
"""
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys

PYTHON = "/root/blender/5.0/python/bin/python3.11"
SITE = pathlib.Path("/root/paint-site")
# The prop environment's versions (~/.farm-factory-props/env, 2026-10-12): what the paint ran with on the PC.
PINS = ("numpy==2.4.6", "scipy==1.17.1", "trimesh==5.1.0", "pillow==12.3.0", "networkx==3.6.1", "rtree==1.4.1",
        "embreex==4.4.0")


def install():
    """The pinned packages into SITE, once a machine (a mark named for the pins)."""
    mark = SITE / f".pins-{hashlib.sha256(' '.join(PINS).encode()).hexdigest()[:12]}"
    if mark.exists():
        return
    subprocess.run([PYTHON, "-m", "pip", "install", "--quiet", "--target", str(SITE), *PINS], check=True)
    mark.write_text(" ".join(PINS))


def measured(command, environment):
    """Run a command to its end; its exit code (minus the signal that killed it) and its peak memory in GB."""
    process = subprocess.Popen(command, env=environment)
    _, status, usage = os.wait4(process.pid, 0)
    return os.waitstatus_to_exitcode(status), usage.ru_maxrss / 1e6


def main():
    listing = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
    named = json.loads(listing.read_text())
    install()
    repo = pathlib.Path(named["paint repo"])  # a trial's data may lie outside the repository
    environment = dict(os.environ, PYTHONPATH=str(SITE), PROPS_HOME=named["props home"], FARM_LOCAL_MODELS="1")
    code, peak = measured([PYTHON, str(repo / "score/stages/surfaces/place_line.py"), "paint-take", str(listing),
                           str(listing.parent)], environment)
    killed = f", killed by {signal.Signals(-code).name}" if code < 0 else ""
    print(f"paint {named['paint take']}: exit code {code}{killed}, peak memory {peak:.2f} GB", flush=True)
    if code:
        raise RuntimeError(f"the paint of {named['paint take']} failed")


if __name__ == "__main__":
    main()
