"""A paint or bake row's key moves with the library surfaces and place.json entries it reads, and with nothing else
of them: a surface added for one place re-keys no other place's paint or bake (2026-10-13). On copies of the environment's
library and place.json under $PROPS_HOME/work, removed at the end.

Run: .venv/bin/python -m pytest score/stages/surfaces/library_reads_test.py
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import stages  # noqa: E402
from score.stages.surfaces import carry  # noqa: E402
from score.store import PROPS_HOME, text_hash  # noqa: E402

ROWS = {row.name: row for row in stages.STAGES}


def a_copy():
    """data/library and data/definitions/place.json copied into a folder of their own: (data folder, its remover)."""
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    data = pathlib.Path(tempfile.mkdtemp(prefix="library-reads-", dir=PROPS_HOME / "work"))
    shutil.copytree(REPO / "data/library", data / "library")
    (data / "definitions").mkdir()
    shutil.copy2(REPO / "data/definitions/place.json", data / "definitions/place.json")
    return data


def keys(row, place, data):
    files = ROWS[row].files(place)
    return {name: text_hash(files[name][1](data / path)) for name, path in
            (("library", "library"), ("places", "definitions/place.json"))}


def edit(path, change):
    found = json.loads(path.read_text())
    change(found)
    path.write_text(json.dumps(found, indent=1))


def test_a_surface_no_library_place_of_the_row_takes_moves_no_paint_key_and_every_bake_key():
    """The paint reads only its places' surfaces; the bake's job, written from git (bake_job.py), carries every
    variant of the library as its specs, as both routes write a job, so a variant added anywhere moves every bake."""
    data = a_copy()
    try:
        before = {row: keys(row, "hub", data) for row in ("surfaces-paint", "surfaces-bake")}
        added = {"recipe": "painted_metal", "token": "hull-trim", "bare": "hull"}
        edit(data / "library/materials.json",
             lambda library: library["families"]["painted"]["variants"].update(brand_new_panel=added))
        edit(data / "definitions/place.json",
             lambda places: places["greenhouse"]["materials"].update(brand_new=dict(library="brand_new_panel",
                                                                                   token="hull-trim")))
        assert keys("surfaces-paint", "hub", data) == before["surfaces-paint"]
        after = keys("surfaces-bake", "hub", data)
        assert after["library"] != before["surfaces-bake"]["library"]
        assert after["places"] == before["surfaces-bake"]["places"]
    finally:
        shutil.rmtree(data)


def test_a_surface_the_row_takes_or_its_own_materials_move_its_key():
    data = a_copy()
    try:
        record = stages.surfaces.data.record("hub")
        taken = next(entry["library"] for entry in
                     json.loads((data / "definitions/place.json").read_text())[record["library"]]["materials"].values()
                     if "library" in entry)
        before = keys("surfaces-paint", "hub", data)

        def rougher(library):
            for family in library["families"].values():
                if taken in family["variants"]:
                    family["variants"][taken]["roughness"] = 0.99
        edit(data / "library/materials.json", rougher)
        after_library = keys("surfaces-paint", "hub", data)
        assert after_library["library"] != before["library"] and after_library["places"] == before["places"]
        edit(data / "definitions/place.json",
             lambda places: places[record["library"]]["wear"].update(dirt=0.123))
        assert keys("surfaces-paint", "hub", data)["places"] != after_library["places"]
    finally:
        shutil.rmtree(data)


def test_the_paint_and_bake_rows_and_their_twins_key_the_library_by_part():
    for name, place in (("surfaces-paint", "hub"), ("surfaces-bake", "hub"), ("surfaces-paint", "people")):
        files = ROWS[name].files(place)
        assert isinstance(files["library"], tuple) and isinstance(files["places"], tuple), name
        assert ROWS[name].files.wide(place) if callable(ROWS[name].files.wide) else ROWS[name].files.wide
    assert not isinstance(ROWS["surfaces-parts"].files("hub")["library"], tuple)  # surfaces-names left the line


class StubStore:
    """The store calls the carry rules make here: one proof file, or none."""
    def __init__(self, proof=None):
        self.proof = proof

    def evidence_file(self, check, output):
        return self.proof


class StubRunner:
    def __init__(self, proof=None):
        self.store = StubStore(proof)
        self.stages = ROWS


def a_record(**changes):
    """An accepted record made at the repository's first commit, so the paint's code changed since."""
    first = subprocess.run(["git", "-C", str(REPO), "rev-list", "--max-parents=0", "HEAD"], capture_output=True,
                           text=True, check=True).stdout.split()[0]
    return {"output": "o" * 64, "key": "k" * 64, "commit": first, "uncommitted": False, "code": "old code",
            "files": {}, **changes}


def test_a_record_from_an_uncommitted_tree_or_a_changed_code_without_proof_never_carries():
    row = ROWS["surfaces-paint"]
    assert carry.why_not(StubRunner(), row, "hub", a_record(uncommitted=True), {}) == \
        "made from a tree with changes not committed"
    assert carry.why_not(StubRunner(), row, "hub", a_record(), {}) == \
        "its code changed since, with no proof its result is the same"


def test_a_proof_carries_only_when_it_names_every_changed_file_for_these_code_versions():
    row = ROWS["surfaces-paint"]
    record = a_record()
    changed = carry.changed_files(row, record["commit"])
    assert changed
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="carry-proof-", dir=PROPS_HOME / "work"))
    try:
        proof = folder / "proof.json"
        full = {"made with code": "old code", "code now": carry.wide_code(row),
                "no-ops": {name: "its change leaves the parts and surfaces as they were" for name in changed},
                "free rows": {}}
        proof.write_text(json.dumps(full))
        assert carry.proof_fault(StubRunner(proof), row, record) is None
        proof.write_text(json.dumps({**full, "no-ops": {name: "" for name in changed}}))
        assert carry.proof_fault(StubRunner(proof), row, record).startswith("its proof does not say why")
        proof.write_text(json.dumps({**full, "code now": "another code"}))
        assert carry.proof_fault(StubRunner(proof), row, record) == "its proof is for other code versions"
    finally:
        shutil.rmtree(folder)


def test_a_proof_speaks_from_the_code_rows_had_at_its_commit():
    """codes_at works the rows' code out at a commit: 46d5873 changed place_line.py alone, so the paint's code moved
    from its parent and the maps' did not (a record carries only when made from the code at the proof's commit)."""
    before, after = carry.codes_at("46d5873^"), carry.codes_at("46d5873")
    assert before["surfaces-paint"] != after["surfaces-paint"]
    assert before["surfaces-maps"] == after["surfaces-maps"]
