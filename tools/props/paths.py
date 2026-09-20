"""Where the prop tool chain lives.

The models and the TRELLIS checkout are large and are not in the repo. They are built once per
box by the bootstrap chapter of the bible; this file is the single place that says where they
landed, so moving them is one edit.
"""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]

# Overridable so a second box, or a test, can point somewhere else.
HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
VENV_PYTHON = HOME / "env" / "bin" / "python"
TRELLIS = HOME / "trellis"
PICTURE_MODEL = HOME / "flux2-klein"

# Everything the chain makes: reference pictures, meshes, reports and the review page.
WORK = pathlib.Path(os.environ.get("PROPS_WORK", HOME / "work"))
PICTURES = WORK / "pictures"
MESHES = WORK / "meshes"
PAGES = WORK / "pages"


def ready():
    """What is missing, so a run can say so instead of failing halfway."""
    missing = []
    for label, path in (("python environment", VENV_PYTHON),
                        ("TRELLIS checkout", TRELLIS),
                        ("picture model", PICTURE_MODEL)):
        if not path.exists():
            missing.append(f"{label}: {path}")
    return missing


def make_directories():
    for path in (PICTURES, MESHES, PAGES):
        path.mkdir(parents=True, exist_ok=True)
