"""A rough model's take through the cloud batch: tools/cloud/batch.py's own command (its plan and price, the
clearance at every rent point, the machines, the ledger line, the finish), run in the prop environment:

    $PROPS_PYTHON score/stages/rough_model/_cloud.py <list.txt> --who "<session>" \
        --inventory data/inventory/<scene>.json

with one check of it replaced. The batch builds only the scenes' rows (from_the_inventory: every model's name on an
approved inventory's row); a rough model is the place's whole concept, on no row, so it keeps the rest of that check:
the inventory approved by the owner. batch.py is loaded from its file and left as it is:
the pixal row declares it, so an edit there would move that paid row's key.
"""
import importlib.util
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
BATCH = REPO / "tools/cloud/batch.py"


def load_batch():
    """batch.py as a module from its file, its own folder on the path first (it imports its siblings, capacity and
    provider, as a script run there would; its other folders it adds itself)."""
    if str(BATCH.parent) not in sys.path:
        sys.path.insert(0, str(BATCH.parent))
    spec = importlib.util.spec_from_file_location("batch", BATCH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def concept_check(batch):
    """batch.from_the_inventory without its rows: each inventory approved (batch.built_from: a designed place's
    hand-in by the creator's lock, else page A's approval). Fault (2026-10-22 benchmark): the page A check alone
    refused the greenhouse's hand-in for page A's row shape."""
    def approved(models, paths):
        for path in paths:
            batch.built_from(path)
    return approved


if __name__ == "__main__":
    loaded = load_batch()
    loaded.from_the_inventory = concept_check(loaded)
    loaded.main()
