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


def test_a_places_section_runs_from_its_heading_to_the_next():
    audit = an_audit()
    assert store_page.audit_section(audit, "greenhouse") == ("  People                X  no cast\n"
                                                             "  Reads wrong           an empty hall")
    assert store_page.audit_section(audit, "garage") == "  Close-ups             M"


def test_a_place_the_audit_does_not_name_reads_as_none():
    assert store_page.audit_section(an_audit(), "hangar") is None


def test_a_places_name_is_its_entrys_else_its_key():
    assert store_page.place_name("nowhere") == "nowhere"  # a key with no entry in place.json, never a KeyError
    assert store_page.place_name("garage") == "the garage"


def test_the_completion_status_is_in_dones_own_words():
    assert ">complete<" in store_page.status_pill({"verdict": "pass", "status": "complete"})
    assert ">complete apart from accepted gaps (2)<" in store_page.status_pill(
        {"verdict": "gapped", "status": "complete apart from accepted gaps", "accepted_gaps": [{}, {}]})
    assert ">NOT complete<" in store_page.status_pill({"verdict": "unknown", "status": "NOT complete"})


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
