"""Invariant: every locked concept in the store is the library's concept/<place> entry with the same picture. A place
whose standing pick the library holds passes; one with no entry, one whose entry holds another picture and one whose
only entry is withdrawn are each named; an unlocked place (its newest pick of no sha) asks for nothing. The store and
the library are temp folders written here.

Breaks that turn this red (each applied once and seen red, then reverted):
- concepts.finding: the picture's sha not compared (`address not in ...` dropped) -> the other picture passes
- concepts.locked: an unlock kept (`if sha` dropped) -> finding is asked for a sha of None and the unlocked place named
"""
import json

from score.stages.complete.library import entries
from score.stages.library import concepts
from score.store import Store

PICTURE = "a" * 64
OTHER = "b" * 64


def pick(root, place, sha, at):
    """Write one pick record of the temp store, as the concept review writes it."""
    folder = root / "objects" / "concepts" / place / "picks"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{at}.json").write_text(json.dumps({"place": place, "sha": sha, "by": "joey", "at": at}))


def entry(root, place, sha, state="locked"):
    """Write one concept entry of the temp library holding concept.png of `sha`."""
    folder = root / "entries" / "concept" / place / "1"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": f"concept/{place}@1", "kind": "concept", "id": place, "version": 1,
        "state": state, "files": {"concept.png": {"sha256": sha}}, "provenance": {}}))


def test_every_locked_concept_is_its_library_entry_with_its_picture(tmp_path):
    store_root, library = tmp_path / "store", tmp_path / "lib"
    for place in ("held", "missing", "repainted", "withdrawn"):
        pick(store_root, place, PICTURE, "20261020T210000")
    pick(store_root, "unlocked", PICTURE, "20261020T210000")
    pick(store_root, "unlocked", None, "20261020T220000")
    entry(library, "held", PICTURE)
    entry(library, "repainted", OTHER)
    entry(library, "withdrawn", PICTURE, state="withdrawn")
    store = Store.in_folder(store_root)
    found = concepts.findings(store, entries.read(library))
    assert [(item["place"], item["entry"]) for item in found] == [
        ("missing", None), ("repainted", "concept/repainted@1"), ("withdrawn", None)], found
    assert concepts.line(store, found).startswith("4 locked concepts, 3 not in the library as locked")
    entry(library, "missing", PICTURE)
    entry(library, "repainted", PICTURE)
    entry(library, "withdrawn", PICTURE)
    assert concepts.findings(store, entries.read(library)) == []
