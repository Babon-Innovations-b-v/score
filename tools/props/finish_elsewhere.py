"""Inside Blender on a rented machine (tools/cloud/blender_cloud.py run_elsewhere): a raw Pixal3D take finished
as pixal.py --finish-only finishes it, there rather than on the owner's PC (no Blender, no bake, no model there; the
pixal row's takes, score/stages/props/pixal_row.py, as score/stages/rough_model/_finish.py does the rough model's).

    blender -b --python finish_elsewhere.py -- <repo> <work> <picture> <take> [pixal.py options ...]

<repo> and <work> are the PC's own paths, sent up at the same places with the raw take (<work>/pixal/<take>.glb and
its camera folder): pixal.py runs from <repo>/tools/props in a Python with the finish's pins (the lab's own
requirements.lock versions, xatlas the repo's uv.lock's), standing in for the lab's Python, and this Blender as its
Blender, both found where paths.py looks under a home of their own. It writes <work>/pixal/<take>-final.glb. Standard
library only: Blender's own Python runs this file.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

import bpy

PINS = ("numpy==1.26.4", "scipy==1.17.1", "trimesh==5.1.0", "pillow==12.3.0", "rtree==1.4.1",
        "fast-simplification==0.2.0", "networkx==3.7", "xatlas==0.0.11")
VENV = pathlib.Path("/root/finish-venv")
UV = pathlib.Path("/root/uv/uv")
# The home paths.py reads (PROPS_HOME): image-to-3dlab/.venv and blender/blender, linked to this machine's.
HOME = pathlib.Path("/root/finish-home")


def environment():
    """The finish's Python with its pins, made once a machine (a mark named for the pins, so a parked machine keeps
    it while they stand)."""
    mark = VENV / f".pins-{hashlib.sha256(' '.join(PINS).encode()).hexdigest()[:16]}"
    if mark.exists():
        return
    if not UV.exists():
        subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh", shell=True,
                       check=True)
    subprocess.run([str(UV), "venv", "--clear", "--quiet", "--python", "3.12", str(VENV)], check=True)
    subprocess.run([str(UV), "pip", "install", "--quiet", "--python", str(VENV / "bin/python"), *PINS], check=True)
    mark.touch()


def home():
    """PROPS_HOME for pixal.py: the lab's Python and Blender where paths.py looks for them."""
    for link, target in ((HOME / "image-to-3dlab/.venv", VENV), (HOME / "blender/blender",
                                                                   pathlib.Path(bpy.app.binary_path))):
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(target)
    return HOME


def main():
    repo, work, picture, take, *options = sys.argv[sys.argv.index("--") + 1:]
    environment()
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONHOME", "PYTHONPATH")}
    env.update(PROPS_HOME=str(home()), PROPS_WORK=work)
    subprocess.run([str(VENV / "bin/python"), str(pathlib.Path(repo) / "tools/props/pixal.py"), picture, take,
                    "--who", "score pixal (cloud finish)", "--finish-only", *options], env=env, check=True)


main()
