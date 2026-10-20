"""Check the store page's audit reader: a place's section runs from its capitals heading to the next one, and a place
the audit does not name reads as None. No store, no stage.

Run: .venv/bin/python tools/review/store_page_test.py
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


def main():
    with tempfile.TemporaryDirectory() as folder:
        audit = pathlib.Path(folder) / "audit.txt"
        audit.write_text(AUDIT)
        assert store_page.audit_section(audit, "greenhouse") == ("  People                X  no cast\n"
                                                                 "  Reads wrong           an empty hall")
        assert store_page.audit_section(audit, "garage") == "  Close-ups             M"
        assert store_page.audit_section(audit, "hangar") is None
    # A part of another place has no entry of its own in place.json (KeyError 'gdoor', 2026-10-13): named with its host.
    assert store_page.place_name("gdoor") == "gdoor, part of the garage"
    assert store_page.place_name("garage") == "the garage"
    # The completion gate's status in done's words (CONTEXT.md), the gaps counted.
    assert ">complete<" in store_page.status_pill({"verdict": "pass", "status": "complete"})
    assert ">complete apart from accepted gaps (2)<" in store_page.status_pill(
        {"verdict": "gapped", "status": "complete apart from accepted gaps", "accepted_gaps": [{}, {}]})
    assert ">NOT complete<" in store_page.status_pill({"verdict": "unknown", "status": "NOT complete"})
    print("store_page_test: pass")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
