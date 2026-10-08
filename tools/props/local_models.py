"""No model runs on this PC: every model step goes to the cloud.

The owner's rule (2026-10-03): "My GPU is only for game tests; do all model stuff in batches in
the cloud." The same day WSL went down twice from running out of memory, six model processes of
6 to 7 GB each loaded at once by three sessions. So every step that loads a model (a picture, a
cut-out, depth, Pixal3D) asks here first, and on this PC it is refused with the cloud command
that does the same work. A rented machine runs the same scripts with FARM_LOCAL_MODELS=1 set by
the runner; on this PC that setting is for an emergency only, and is the owner's call.
"""
import os
import sys

ALLOW = "FARM_LOCAL_MODELS"


def allowed():
    """Whether this machine may load a model: only a rented one, or an emergency here."""
    return os.environ.get(ALLOW) == "1"


def refuse_here(what, cloud):
    """Stop before `what` loads a model on this PC, naming the cloud command that does it."""
    if allowed():
        return
    print(f"refused: {what} loads a model, and no model runs on this PC (owner, 2026-10-03: the "
          f"graphics card is for game tests only).\n"
          f"Run it in the cloud instead: {cloud}\n"
          f"Emergency only, with the owner's word: {ALLOW}=1", file=sys.stderr, flush=True)
    raise SystemExit(3)
