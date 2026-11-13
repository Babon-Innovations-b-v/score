"""The store page shows a place its own part of the audit (from its capitals heading to the next one; a place the audit
does not name reads as None), its name from place.json (its key when it has none), and the completion gate's status
in done's own words (CONTEXT.md "complete": a wording check guarding that rule, the gaps counted). No store, no stage.

Breaks (each applied once, seen red, reverted), in tools/review/store_page.py:
- section runs to the next heading: audit_section's end search never finds a heading (`if False`).
- an unnamed place reads as None: audit_section returns "" for it.
- place name: place_name indexes place.json by the key (`[place]`), a KeyError for a place without an entry.
- status in done's words: status_pill never counts the accepted gaps.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_a_place_page_reads_its_own_audit_and_status.py
"""
import pathlib
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store_page  # noqa: E402

AUDIT = """Intro line
GREENHOUSE
  People                X  no cast
  Reads wrong           an empty hall

GARAGE
  Close-ups             M
"""


def an_audit():
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "audit.txt").write_text(AUDIT)
    return folder / "audit.txt"


# Each place a page is made for: its audit section, its name, its completion record and the status words it shows.
PLACES = [
    pytest.param("greenhouse", "  People                X  no cast\n  Reads wrong           an empty hall",
                 "the greenhouse", {"verdict": "pass", "status": "complete"}, ">complete<",
                 id="section-ends-at-next-heading"),
    pytest.param("garage", "  Close-ups             M", "the garage",
                 {"verdict": "gapped", "status": "complete apart from accepted gaps", "accepted_gaps": [{}, {}]},
                 ">complete apart from accepted gaps (2)<", id="last-section-gaps-counted"),
    pytest.param("nowhere", None, "nowhere", {"verdict": "unknown", "status": "NOT complete"}, ">NOT complete<",
                 id="unnamed-place-no-entry"),
]


@pytest.mark.parametrize("place, section, name, found, pill", PLACES)
def test_a_place_page_reads_its_own_audit_and_status(place, section, name, found, pill):
    assert store_page.audit_section(an_audit(), place) == section, place
    assert store_page.place_name(place) == name, place
    assert pill in store_page.status_pill(found), place


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    for row in PLACES:
        test_a_place_page_reads_its_own_audit_and_status(*row.values)
        print("ok", row.id)
