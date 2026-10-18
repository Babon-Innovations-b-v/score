"""Where a processor machine is in stock, for library_bake.py's --processor. All that is left of the retired Infinigen
patch runner (Pixal3D's nature props won, 2026-10-06). It stays here: moving it into library_bake.py would move that
file's paid rows.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402


def offers(machine_class):
    """Where a processor machine of `machine_class` is in stock (not short), best stocked first: provider.Offer."""
    found = [offer for offer in batch.offers([machine_class]) if offer.stock_word != "shortage"]
    return sorted(found, key=lambda offer: (offer.stock, offer.per_card))
