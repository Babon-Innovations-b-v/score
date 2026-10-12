"""Heavy steps that load no model (the surface stage's paint) run on a rented machine, never on this PC.

The owner, 2026-10-12: heavy steps run in the cloud, measurements included (the paint of twelve takes in one process
passed the PC's 14 GB cap that day). A cloud runner or job image sets local_models.ALLOW (FARM_LOCAL_MODELS=1) on the
machines it rents; a heavy step calls `refuse_here` first. Model steps keep local_models.refuse_here, which names
their own cloud command. A module of its own: local_models.py is in many paid rows' code versions.
"""
import local_models


def refuse_here(what):
    """Stop `what` unless this is a machine a cloud runner marked."""
    if not local_models.allowed():
        raise SystemExit(f"refused: {what} runs on a cloud machine; submit it as a batch")
