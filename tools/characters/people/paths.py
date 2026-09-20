"""Where the crew body tool chain lives.

The body model, the motion model and the clips they made are large and are not in the repo. They
are built once per box by the bootstrap chapter of the bible; this file is the single place that
says where they landed, so moving them is one edit. It mirrors `tools/props/paths.py`, which does
the same job for the prop chain.
"""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]

# Overridable so a second box, or a test, can point somewhere else.
HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
VENV_PYTHON = HOME / "env" / "bin" / "python"

# Everything the chain makes: the clips the motion model wrote, and the body built from them.
WORK = pathlib.Path(os.environ.get("MOTION_WORK", HOME / "work"))
MOTIONS = WORK / "motions"
BODIES = WORK / "bodies"

# Where the finished body lands in the game.
PEOPLE_MODEL = REPO / "game" / "people" / "person_model"


def ready():
    """What is missing, so a run can say so instead of failing halfway."""
    missing = []
    if not VENV_PYTHON.exists():
        missing.append(f"python environment: {VENV_PYTHON}")
    if not MOTIONS.exists():
        missing.append(f"generated clips: {MOTIONS}")
    return missing


def make_directories():
    for path in (MOTIONS, BODIES):
        path.mkdir(parents=True, exist_ok=True)
