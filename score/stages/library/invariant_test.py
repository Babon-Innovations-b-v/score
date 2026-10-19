"""The library invariant on small fixed sets: each mismatch gives exactly its problem, equal sets give none; and the
sweep's reading of a library folder (a temp one) and its findings file, with the entry's picture beside it.

    agree            a handed place whose entries the library holds at their outputs: no problem
    no library       every library node says no library is configured
    not handed       a place with no accepted library node, by name
    not in library   an address the handover names that the library lacks, or holds withdrawn
    moved on         an entry whose node's accepted output moved since it was made
    shown nowhere    a newest entry of a handed place that no handover names (an older version is not counted)
    not pushed       a handover whose library commit did not push
    the sweep        entry.json read with its version and picture; findings.json in the cockpit's shape

Run: .venv/bin/python score/stages/library/invariant_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

HOME = pathlib.Path(tempfile.mkdtemp(prefix="invariant-test-"))
os.environ["PROPS_HOME"] = str(HOME / "props")  # before score.store reads it
REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from score.stages.library import invariant, sweep  # noqa: E402

WORLD = "world1"


def row(address, node="pixal@garage", output="out-1", state="draft", place="garage", world=WORLD):
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    return {"address": address, "kind": kind, "id": entry_id, "version": int(version), "state": state,
            "world": world, "place": place, "node": node, "output": output}


def report(*addresses, pushed=True):
    return {"entries": [{"address": address, "node": "pixal@garage"} for address in addresses],
            "saved": {"committed": "abc", "pushed": pushed, "why": "" if pushed else "no remote"}}


def held(node, report_of=None):
    return {"node": node, "output": "lib-out" if report_of else None,
            "why": "" if report_of else "nothing stands accepted", "report": report_of}


def agreeing():
    """An environment and a library that agree: the garage handed, its one entry held at its output."""
    handed = {"world": held("library-world", report()), "garage": held("library@garage", report("model/rover@2"))}
    return handed, [row("model/rover@1"), row("model/rover@2")], {"pixal@garage": "out-1"}


def rules(found):
    return {where: [item["rule"] for item in items] for where, items in found.items() if items}


def test_agree():
    handed, rows, accepted = agreeing()
    assert invariant.problems(WORLD, handed, rows, accepted, True) == {"world": [], "garage": []}


def test_no_library():
    handed, rows, accepted = agreeing()
    found = invariant.problems(WORLD, handed, rows, accepted, False)
    assert rules(found) == {"world": ["not handed"], "garage": ["not handed"]}
    assert "no library is configured" in found["garage"][0]["sentence"]


def test_not_handed():
    handed, rows, accepted = agreeing()
    handed["hangar"] = held("library@hangar")
    found = invariant.problems(WORLD, handed, rows, accepted, True)
    assert rules(found) == {"hangar": ["not handed"]}
    assert found["hangar"][0]["sentence"] == ("The hangar is not handed to the library yet (library@hangar: nothing "
                                              "stands accepted).")


def test_not_in_library():
    handed, rows, accepted = agreeing()
    handed["garage"]["report"] = report("model/rover@2", "model/crate@1", "model/cart@1")
    rows.append(row("model/cart@1", state="withdrawn"))
    found = invariant.problems(WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["not in library", "not in library"]}
    assert [item["address"] for item in found["garage"]] == ["model/crate@1", "model/cart@1"]
    assert "withdrawn" in found["garage"][1]["sentence"]


def test_moved_on():
    handed, rows, _ = agreeing()
    found = invariant.problems(WORLD, handed, rows, {"pixal@garage": "out-2"}, True)
    assert rules(found) == {"garage": ["moved on"]}
    assert found["garage"][0]["sentence"] == ("model/rover@2 was made from an output the garage no longer holds "
                                              "(pixal@garage).")
    gone = invariant.problems(WORLD, handed, rows, {"pixal@garage": None}, True)
    assert "no longer has accepted" in gone["garage"][0]["sentence"]


def test_repo_made_entry_never_moves():
    handed, rows, accepted = agreeing()
    rows.append(row("surface/steel@1", node=None, output=None))
    handed["garage"]["report"] = report("model/rover@2", "surface/steel@1")
    assert rules(invariant.problems(WORLD, handed, rows, accepted, True)) == {}


def test_shown_nowhere():
    handed, rows, accepted = agreeing()
    rows += [row("model/old_crate@1"), row("model/tank@1", world="world2"), row("model/hut@1", place="hangar")]
    found = invariant.problems(WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["shown nowhere"], "world": ["shown nowhere"]}
    assert found["garage"][0]["address"] == "model/old_crate@1"
    assert found["world"][0]["address"] == "model/hut@1"  # the hangar has no library node: shown on the environment


def test_history_is_not_counted():
    handed, rows, accepted = agreeing()
    rows[0]["output"] = "out-0"  # rover@1 made from an older output: history, not a problem
    assert rules(invariant.problems(WORLD, handed, rows, accepted, True)) == {}


def test_not_pushed():
    handed, rows, accepted = agreeing()
    handed["garage"]["report"] = report("model/rover@2", pushed=False)
    found = invariant.problems(WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["not pushed"]}
    assert found["garage"][0]["sentence"] == "The library's last handover of the garage did not push: no remote."


def write_entry(root, blobs, address, picture=b"\x89PNG fake picture bytes"):
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    sha = "ab" + "0" * 62
    (blobs / "blobs" / sha[:2]).mkdir(parents=True, exist_ok=True)
    (blobs / "blobs" / sha[:2] / sha).write_bytes(picture)
    folder = root / "entries" / kind / entry_id / version
    folder.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps({
        "address": address, "kind": kind, "id": entry_id, "state": "draft",
        "picture": {"file": "picture.png"}, "files": {"picture.png": {"sha256": sha}},
        "provenance": {"world": WORLD, "place": "garage", "node": "pixal@garage", "output": "out-1"}}))


def test_sweep_reads_and_writes():
    root, blobs, out = HOME / "library", HOME / "blobs", HOME / "out"
    write_entry(root, blobs, "model/rover@2")
    rows = sweep.library_rows(str(root))
    assert rows == [dict(row("model/rover@2"), picture="ab" + "0" * 62)]
    handed = {"garage": held("library@garage", report("model/rover@2"))}
    found = invariant.problems(WORLD, handed, rows, {"pixal@garage": "out-2"}, True)
    written = sweep.written("garage", handed["garage"], found["garage"], rows, str(blobs), out / "garage")
    on_disk = json.loads((out / "garage" / "findings.json").read_text())
    assert on_disk == written and on_disk["answer"] == "fail" and on_disk["outputs"] == {"library@garage": "lib-out"}
    finding = on_disk["findings"][0]
    assert set(finding) == {"rule", "prim", "name", "sentence", "picture"}
    assert (out / "garage" / finding["picture"]).read_bytes() == b"\x89PNG fake picture bytes"
    assert sweep.library_rows("") == []


def test_library_free():
    path = HOME / "free.json"
    path.write_text(json.dumps({"worlds": [{"world": WORLD, "why": "a test world", "who": "@owner", "when": ""}]}))
    assert not sweep.library_free(WORLD, path)  # an undated decision is no decision
    path.write_text(json.dumps({"worlds": [{"world": WORLD, "why": "a test", "who": "@owner", "when": "2026-10-18"}]}))
    assert sweep.library_free(WORLD, path) and not sweep.library_free("world2", path)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    try:
        tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
        for test in tests:
            test()
        print(f"invariant_test: {len(tests)} passed")
    finally:
        shutil.rmtree(HOME, ignore_errors=True)
