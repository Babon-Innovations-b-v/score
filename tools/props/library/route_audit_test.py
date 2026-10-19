"""The route audit (data/audits/route-audit.json, PRD #10) covers every code-built row of data/inventory exactly once,
with a known decision, a reason and evidence each, so the audit cannot silently drift from the inventory.

    python3 tools/props/library/route_audit_test.py
"""
import collections
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
AUDIT = REPO / "data/audits/route-audit.json"
DECISIONS = {"keep as code", "make by the prop pipeline", "code body + picture details"}


def inventory_rows():
    """(inventory file, row id, kind) of every row of every place's inventory."""
    return [(path.name, row["id"], row["kind"]) for path in sorted((REPO / "data/inventory").glob("*.json"))
            for row in json.loads(path.read_text())["rows"]]


def audit():
    return json.loads(AUDIT.read_text())


def test_every_code_built_row_is_audited_exactly_once():
    code = collections.Counter((name, kind) for name, kind, route in inventory_rows() if route == "code")
    audited = collections.Counter((entry["inventory"], entry["kind"]) for entry in audit()["code_built"])
    assert audited == code, (f"missing: {sorted(set(code) - set(audited))[:10]}; "
                             f"not code-built or doubled: {sorted((audited - code).elements())[:10]}")


def test_every_entry_has_a_decision_a_reason_and_evidence():
    for entry in audit()["code_built"]:
        assert entry["decision"] in DECISIONS, entry
        assert entry["reason"] and entry["evidence"] and entry["current_route"], entry


def test_the_counts_are_the_inventory_s():
    kinds = collections.Counter(route for _, _, route in inventory_rows())
    counted = audit()["counted"]
    assert counted["code_built"] == kinds["code"]
    assert counted["picture_made"] == kinds["generate"] + kinds["mechanic"]
    assert counted["decisions"] == dict(collections.Counter(entry["decision"] for entry in audit()["code_built"]))


def test_every_kind_needing_a_body_is_picture_made_where_it_is_listed():
    picture = {(name, kind) for name, kind, route in inventory_rows() if route != "code"}
    for entry in audit()["picture_made_needing_body"]:
        for name in entry["inventories"]:
            assert (name, entry["kind"]) in picture, (name, entry["kind"])


def test_the_order_is_deterministic():
    entries = audit()["code_built"]
    assert entries == sorted(entries, key=lambda entry: (entry["inventory"], entry["kind"]))
    kinds = [entry["kind"] for entry in audit()["picture_made_needing_body"]]
    assert kinds == sorted(kinds)


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
