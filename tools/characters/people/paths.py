"""Where the people tools' files live outside the repo.

The clips the motion model made and each look's settings are large or the creator's own and are not in the repo;
this file is the single place that says where they lie, so moving them is one edit. A maker's chain on a rented card
points each at its make folder (../maker/chain.py's environment). It mirrors `tools/props/paths.py`, which does the
same job for the prop chain.
"""
import os
import pathlib

# Overridable so a second box, or a test, can point somewhere else.
HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))

# Everything the chain makes: the clips the motion model wrote among it.
WORK = pathlib.Path(os.environ.get("MOTION_WORK", HOME / "work"))
MOTIONS = WORK / "motions"
# Who this run makes, and its look's settings (`person.json`, read by person.py).
PERSON = os.environ.get("MOTION_PERSON", "take_c")
LOOK = pathlib.Path(os.environ.get("MOTION_LOOK", HOME / "look" / PERSON))
