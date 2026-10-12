"""Runs inside Blender on a rented processor machine (tools/props/cloud/blender_cloud.py; the people stage's body
rows, prop_person.py `checks` with `cloud=True`): a built person's checks side by side, each in Blender's own Python
outside Blender with the prop environment's packages at their pinned versions (installed once a machine), as the
surface stage's paint runs (score/stages/surfaces/inside/paint_take.py). On the PC the two body-through-cloth counts
took about an hour a body each (2026-10-10), too long for every look of a world side by side.

    blender -b --python body_checks.py -- <listing>

The listing names the repository, PROPS_HOME, and each check's command line (a script of tools/characters/maker by
its path and its arguments); every record lands where its command says, which blender_cloud.py brings back.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

PYTHON = "/root/blender/5.0/python/bin/python3.11"
SITE = pathlib.Path("/root/paint-site")
# The prop environment's versions, as the surface stage's paint pins them.
PINS = ("numpy==2.4.6", "scipy==1.17.1", "trimesh==5.1.0", "pillow==12.3.0", "networkx==3.6.1", "rtree==1.4.1",
        "embreex==4.4.0")


def install():
    """The pinned packages into SITE, once a machine (a mark named for the pins)."""
    mark = SITE / f".pins-{hashlib.sha256(' '.join(PINS).encode()).hexdigest()[:12]}"
    if mark.exists():
        return
    subprocess.run([PYTHON, "-m", "pip", "install", "--quiet", "--target", str(SITE), *PINS], check=True)
    mark.write_text(" ".join(PINS))


def main():
    listing = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    install()
    environment = dict(os.environ, PYTHONPATH=str(SITE), PROPS_HOME=listing["props home"], FARM_LOCAL_MODELS="1")
    for group in ("first", "checks", "then"):
        running = [(name, subprocess.Popen([PYTHON, *command], env=environment, cwd=listing["repo"]))
                   for name, command in listing.get(group, {}).items()]
        failed = [name for name, process in running if process.wait()]
        print(f"body checks ({group}): {len(running) - len(failed)} of {len(running)} ended well", flush=True)
        if failed:
            raise RuntimeError(f"body checks failed: {failed}")


if __name__ == "__main__":
    main()
