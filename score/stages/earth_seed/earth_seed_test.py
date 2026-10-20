"""The earth seed rows' own checks, with no spend: the kit row plans only code-built pieces, every row that read a
round-three seed reads earth-seed instead, a reader is handed its seeds under their
old names, the export leaves out and names a piece no row made, and the gates fail by name.

Run: .venv/bin/python score/stages/earth_seed/earth_seed_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, stages  # noqa: E402
from score.stages import earth_seed  # noqa: E402

PLACES = ("hangar", "wreck", "street", "airlock", "launch", "camp")


def test_the_kit_row_plans_the_code_built_pieces_only():
    kit = {"models": {"wall_1": {"route": "code"}, "lamp_1": {"route": "code"}, "crane_1": {"route": "model"}},
           "pieces": [{"kind": "x_wall", "model": "wall_1", "at": [0, 0, 0], "y": [0.0, 0.0, 1.0]},
                      {"kind": "x_lamp", "model": "lamp_1", "at": [0, 2, 0]},
                      {"kind": "x_lamp", "model": "lamp_1_glow", "part": "glow", "at": [0, 2, 0]},
                      {"kind": "x_crane", "model": "crane_1", "at": [3, 0, 0]}]}
    pieces = earth_seed.code_layout(kit)["pieces"]
    assert [piece["model"] for piece in pieces] == ["wall_1", "lamp_1"], pieces
    assert pieces[0]["y"] == [0.0, 0.0, 1.0] and pieces[1]["y"] == earth_seed.UPRIGHT, pieces
    assert earth_seed.kit_jobs("wreck") >= 1


def test_no_row_reads_an_earth_place_s_round_three_seed():
    readers = set()
    for row in stages.STAGES:
        for place in PLACES:
            if row.applies is not None and not row.applies(place):
                continue
            found = row.files(place) if callable(row.files) else row.files
            if any(stages.seed_named(path, place) for path in found.values()):
                readers.add(row.name)
    assert not readers, readers  # terrain-look, the last, retired (#27)
    reading = {row.name for row in stages.STAGES if "earth-seed" in row.after} - {stages.library.PLACE_ROW}
    assert reading == set(stages.EARTH_SEEDED), reading ^ set(stages.EARTH_SEEDED)


def test_a_reader_gets_its_seeds_under_their_old_names():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        for node, place in (("own", "airlock"), ("hub", "hub")):
            (root / node / place).mkdir(parents=True)
        inputs = {"earth-seed": root / "own", "earth-seed@hub": root / "hub", "kit": "k"}
        found = {"seed": "{seeds}/usd-r3/{place}", "neighbour hub": "{seeds}/usd-r3/hub",
                 "neighbour far_city": "{seeds}/usd-r3/far_city", "kit": "{data}/kit/{place}.json"}
        assert stages.seeded_place(inputs) == "airlock"
        taken = stages.seed_inputs(inputs, found, "airlock")
        assert taken["seed"] == root / "own/airlock" and taken["neighbour hub"] == root / "hub/hub", taken
        assert "neighbour far_city" not in taken and taken["kit"] == "k", taken  # no kit: still a declared file
    finally:
        shutil.rmtree(root)


def test_a_piece_no_row_made_is_left_out_and_named():
    sys.path.insert(0, str(REPO / "tools/usd"))
    import export
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "wall_1.gltf").write_text("{}")
        holes = []
        pieces = [{"model": "wall_1"}, {"model": "lamp_1"}, {"model": "lamp_1"}]
        assert export.made_only(pieces, [root], holes) == [{"model": "wall_1"}]
        export.made_only(pieces, [root], holes)
        assert holes == [{"model": "lamp_1"}], holes
    finally:
        shutil.rmtree(root)


def test_the_seed_gates_fail_by_name():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "wreck").mkdir()
        (root / "wreck/wreck.usda").write_text("#usda 1.0\n")
        (root / earth_seed.HOLES).write_text(json.dumps({"models": [], "picks": []}))
        assert earth_seed.seed_faults(root) == []
        assert earth_seed.judge_laid(root, {}, {}).answer == checks.PASS
        (root / earth_seed.HOLES).write_text(json.dumps({"models": ["cable_run_1p4"], "picks": [
            {"row": "aft_section", "object": None, "why": "no object of this row is on the stage"}]}))
        laid, picked = earth_seed.judge_laid(root, {}, {}), earth_seed.judge_picks(root, {}, {})
        assert laid.answer == checks.FAIL and laid.findings == ("cable_run_1p4",), laid
        assert picked.answer == checks.FAIL and "aft_section" in picked.findings[0], picked
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
