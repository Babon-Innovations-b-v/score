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
CREW = ("take_c", "nev", "oona", "bram", "sefa")
# The crew kit's builds (#112): every part a seed mixes into a generated crew member, the next
# astronaut or a body at the square's edge, one file per build (`kit.py`).
KIT_BUILDS = ("kit_m_slim", "kit_m_avg", "kit_m_broad", "kit_w_slim", "kit_w_avg", "kit_w_broad")
# The prologue's people (`prologue.py`): the leader on his podium, on a build of his own, and on
# launch day the guard, the driver and the two technicians, each on a kit build.
PROLOGUE = ("leader", "guard", "driver", "tech_man", "tech_woman")
PEOPLE = CREW + KIT_BUILDS + PROLOGUE
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
# Plain clothes (the prologue's people and the crowd's edge, #112): a jacket, a knee-length coat
# and trousers, each a GarmentCode drape on the build.
JACKET_DRAPE = LOOK / "jacket_drape"
COAT_DRAPE = LOOK / "coat_drape"
TROUSERS_DRAPE = LOOK / "trousers_drape"
# What every crew kit build shares (#112): the body SAM 3D Body read off each face's picture
# (`face_bodies/`), each face's drawing (`faces/`) and each hairstyle, made on take C's head
# (`hair/`).
KIT = HOME / "look" / "kit"
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

