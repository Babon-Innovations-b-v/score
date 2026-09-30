"""Where the crew body tool chain lives.

The body model, the motion model and the clips they made are large and are not in the repo. They
are built once per box by the bootstrap chapter of the bible; this file is the single place that
says where they landed, so moving them is one edit. It mirrors `tools/props/paths.py`, which does
the same job for the prop chain.
"""
import os
import pathlib

# Overridable so a second box, or a test, can point somewhere else.
HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
VENV_PYTHON = HOME / "env" / "bin" / "python"

# Everything the chain makes: the clips the motion model wrote, the body built from them, and what
# dressing the body makes on the way (thinned cloth, texture coordinates, the painted pictures).
WORK = pathlib.Path(os.environ.get("MOTION_WORK", HOME / "work"))
MOTIONS = WORK / "motions"
BODIES = WORK / "bodies"
DRESSING = WORK / "dressing"

# Everybody the game draws as a body of their own (#112), each a look and a built file: take C,
# the player's first astronaut; Nev, the botanist; Oona, Bram and Sefa, the first expedition.
PEOPLE = ("take_c", "nev", "oona", "bram", "sefa")
# Who this run builds; one run builds one person, because every module reads its look on import.
PERSON = os.environ.get("MOTION_PERSON", PEOPLE[0])

# What one person's look is made from, kept outside the repo because the tools that made it are
# (#100): the body's build as SAM 3D Body read it off the owner's drawing, the two drapes
# GarmentCode simulated, the boots and the hair Hi3DGen made, the MakeHuman eyes seated on the
# head, the face drawn over the head, and, for everybody after take C, where their joints sit
# (`joints.json`) and what sets them apart (`person.json`). Nothing here is remade by a build;
# the build reads it.
LOOK = pathlib.Path(os.environ.get("MOTION_LOOK", HOME / "look" / PERSON))
IDENTITY = LOOK / "identity.npz"
WORK_DRAPE = LOOK / "work_drape"
SPACE_DRAPE = LOOK / "space_drape"
WORK_BOOT = LOOK / "work_boot.npz"
SPACE_BOOT = LOOK / "space_boot.npz"
HAIR = LOOK / "hair.npz"
EYES = LOOK / "eyes.npz"
FACE = LOOK / "face"

# The prop chain's Blender, which unwraps and thins the crew's parts too.
BLENDER = pathlib.Path(os.environ.get(
    "PROPS_BLENDER", pathlib.Path.home() / ".farm-factory-props" / "blender" / "blender"))


def ready():
    """What is missing, so a run can say so instead of failing halfway."""
    missing = []
    for what, path in (("python environment", VENV_PYTHON), ("generated clips", MOTIONS),
                       ("the crew's look", LOOK), ("Blender", BLENDER)):
        if not path.exists():
            missing.append(f"{what}: {path}")
    return missing

