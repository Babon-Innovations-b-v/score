"""Check the rules every place shares (data/definitions/place.json) against the owner's rule of 2026-10-07: code
builds only plain plates, pipes and trims, so no shared rule may send a made thing such as a ship to code.

Run: .venv/bin/python tools/props/scene/place_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import place  # noqa: E402


def no_shared_rule_builds_a_ship_in_code():
    """Fault (design of 2026-10-11, section 9): the rule "Modules, ships and moving parts are built in code" was what
    the hangar's code-built ship cited, against the owner's rule."""
    rules = place.places()[place.SHARED]["rules"]
    return [f"a shared rule sends ships to code: {rule!r}" for rule in rules
            if "ship" in rule.lower() and "code" in rule.lower()]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = no_shared_rule_builds_a_ship_in_code()
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
