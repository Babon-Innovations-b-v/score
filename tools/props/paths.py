"""Where the prop tool chain lives.

The models and the image-to-3dlab runtime are large and are not in the repo. They are built once per
box by the bootstrap chapter of the bible; this file is the single place that says where they
landed, so moving them is one edit.
"""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]

# Overridable so a second box, or a test, can point somewhere else.
HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
# The plain-Python side's interpreter: PROPS_PYTHON, else this repo's own environment (`make env`, pyproject.toml),
# else the older per-box prop environment under HOME.
VENV_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON") or next(
    (path for path in (REPO / ".venv/bin/python", HOME / "env/bin/python") if path.exists()), REPO / ".venv/bin/python"))
PICTURE_MODEL = HOME / "flux2-klein"
# The locked route's runtime (#55): a checkout of the vendored image-to-3dlab with its own Python
# and the Pixal3D build, and the Blender its finishing step drives. See workflow/bootstrap.
IMAGE_TO_3DLAB = HOME / "image-to-3dlab"
BLENDER = HOME / "blender" / "blender"

# Everything the chain makes: reference pictures and the review page (pixal.py's models go in
# WORK/pixal).
WORK = pathlib.Path(os.environ.get("PROPS_WORK", HOME / "work"))
PICTURES = WORK / "pictures"
PAGES = WORK / "pages"


def make_directories():
    for path in (PICTURES, PAGES):
        path.mkdir(parents=True, exist_ok=True)


def scene_folder(scene):
    """Where everything made for one scene lands (WORK/scene/<scene>), made if it is not there."""
    path = WORK / "scene" / scene
    path.mkdir(parents=True, exist_ok=True)
    return path
