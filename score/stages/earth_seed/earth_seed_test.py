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


KIT = {"room": "x", "models": {"wall_1": {"route": "code"}, "lamp_1": {"route": "code"}, "crane_1": {"route": "model"}},
       "pieces": [{"kind": "x_wall", "model": "wall_1", "at": [0, 0, 0], "y": [0.0, 0.0, 1.0]},
                  {"kind": "x_lamp", "model": "lamp_1", "at": [0, 2, 0]},
                  {"kind": "x_lamp", "model": "lamp_1_glow", "part": "glow", "at": [0, 2, 0]},
                  {"kind": "x_crane", "model": "crane_1", "at": [3, 0, 0]}]}


def test_the_kit_row_plans_its_named_code_fallbacks_only():
    named = earth_seed.fallbacks(KIT, "x")  # no hand-in record: every code row is named not handed
    assert named == {"lamp": earth_seed.NOT_HANDED, "wall": earth_seed.NOT_HANDED}, named
    pieces = earth_seed.code_layout(KIT, "x", named)["pieces"]
    assert [piece["model"] for piece in pieces] == ["wall_1", "lamp_1"], pieces
    assert pieces[0]["y"] == [0.0, 0.0, 1.0] and pieces[1]["y"] == earth_seed.UPRIGHT, pieces
    assert [piece["model"] for piece in earth_seed.code_layout(KIT, "x", {"lamp": "why"})["pieces"]] == ["lamp_1"]
    assert earth_seed.kit_jobs("wreck") >= 1


def test_a_row_handed_to_the_loop_leaves_the_kit_row():
    kept = earth_seed.handed_rows
    earth_seed.handed_rows = lambda place: {"wall"}
    try:
        assert earth_seed.fallbacks(KIT, "x") == {"lamp": earth_seed.NOT_HANDED}  # the wall's model is the loop's
    finally:
        earth_seed.handed_rows = kept


def test_every_earth_kit_code_piece_is_a_named_fallback():
    """No earth place's kit row bakes a code piece its record does not name with why, and only the loop's own rows
    leave its bake (#41)."""
    for place in (path.stem for path in sorted((REPO / "data/kit").glob("*.json")) if stages.earth_place(path.stem)):
        kit = json.loads((REPO / "data/kit" / f"{place}.json").read_text())
        named = earth_seed.fallbacks(kit, place)
        baked = earth_seed.code_layout(kit, place, named)["pieces"]
        assert all(named.get(earth_seed.piece_row(piece, kit, place)) for piece in baked), place
        code = {earth_seed.piece_row(piece, kit, place) for piece in kit["pieces"] if earth_seed.code_built(piece, kit)}
        left = code - {earth_seed.piece_row(piece, kit, place) for piece in baked}
        assert left <= earth_seed.handed_rows(place), (place, left)


def write(folder, name, record):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record))
    return folder / name


def base_stage(seed, objects):
    """An earth seed's output: place x's base stage with `objects` ({name: (row, spot)}) under /x/Objects."""
    from pxr import Gf, Sdf, Usd, UsdGeom
    (seed / "x/layers").mkdir(parents=True)
    (seed / "x/x.usda").write_text("#usda 1.0\n")
    stage = Usd.Stage.CreateNew(str(seed / "x/layers/base.usda"))
    for name, (row, spot) in objects.items():
        xform = UsdGeom.Xform.Define(stage, f"/x/Objects/{name}")
        xform.AddTranslateOp().Set(Gf.Vec3d(*spot))
        xform.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(row)
    stage.GetRootLayer().Save()
    return seed


def section_inputs(root):
    """Place x's base with two wall panels and a floor plate, its plan's two sections, and the loop's ends: the wall
    made (take wall-k1, its parts two finishes), the floor a gap."""
    sections = [{"name": "bolted walls", "surface": "walls", "rows": ["wall"]},
                {"name": "deck plates", "surface": "floor", "rows": ["floor"]}]
    rows = [{"id": "wall", "take": "wall-k1", "layer": "kit"}, {"id": "floor", "take": "floor-k1", "layer": "kit"}]
    parts = {"takes": {"wall-k1": {"parts": [{"judge": "dark_panel", "share": 0.3}, {"judge": "painted_panel",
                                                                                        "share": 0.7}]}}}
    objects = {"wall_1": ("wall", (2.0, 0.0, 5.0)), "wall_2": ("wall", (3.2, 0.0, 5.0)),
               "floor_1": ("floor", (0.0, 0.0, 0.0))}
    return {"earth-seed": base_stage(root / "seed", objects),
            "plan": write(root / "plan", "x.json", {"sections": sections}),
            "places": write(root, "place.json", {"x_library": {"wear": {"level": "worked", "dirt": 0.4}}}),
            "surfaces": write(root / "surfaces", "x.json", {"library": "x_library"}),
            "props-inputs": write(root / "inputs", "rows.json", {"rows": rows}).parent,
            "likeness": write(root / "likeness", "likeness.json", {"objects": {"wall": {"route": "prop"}, "floor": {
                "missing": "no model"}}}).parent,
            "surfaces-bake": write(root / "bake", "baked.json", {"wall_1": {"parts": "wall-k1"}}).parent,
            "surfaces-parts": write(root / "parts", "parts.json", parts).parent}


def test_kit_sections_lay_one_style_one_finish_and_wear_across_the_seams():
    from pxr import Gf, Usd
    from score.stages.earth_seed import kit_sections
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        inputs, out = section_inputs(root), root / "out"
        out.mkdir()
        kit_sections.make(inputs, out, 0, {})
        assert kit_sections.faults(out) == []
        walls, deck = json.loads((out / kit_sections.OUTPUT).read_text())["sections"]
        assert walls["finish"] == "painted_panel" and walls["made"] == {"wall": "wall-k1"}, walls
        assert walls["origin"] == [2.0, 0.0, 5.0] and walls["gap"] is None and walls["wear"]["level"] == "worked"
        assert deck["finish"] is None and deck["gap"] and deck["made"]["floor"].startswith("gap: no model"), deck
        layer = Usd.Stage.Open(str(out / kit_sections.LAYER))
        first, second = (layer.GetPrimAtPath(f"/x/Objects/wall_{number}") for number in (1, 2))
        assert second.GetAttribute("score:section").Get() == "bolted walls"
        assert second.GetAttribute("score:finish").Get() == "painted_panel"
        assert second.GetAttribute("score:wear_seed").Get() == first.GetAttribute("score:wear_seed").Get()
        assert second.GetAttribute("score:wear_at").Get() == Gf.Vec3f(1.2, 0.0, 0.0)  # wear runs on past the seam
        verdict = kit_sections.judge_sections(out, inputs, {})
        assert verdict.answer == checks.PASS and verdict.measures["gaps"] == 1, verdict
        twice = [{"name": "a", "surface": "walls", "rows": ["wall"]}, {"name": "b", "surface": "walls",
                                                                        "rows": ["wall", "door"]}]
        write(root / "plan", "x.json", {"sections": twice})
        again = root / "again"
        again.mkdir()
        kit_sections.make(inputs, again, 0, {})
        failed = kit_sections.judge_sections(again, inputs, {})
        assert failed.answer == checks.FAIL and any("in two sections" in line for line in failed.findings), failed
    finally:
        shutil.rmtree(root)


def test_the_kit_adapter_is_on_the_loop_and_every_plan_section_is_laid():
    from score.stages import assembly, shapes_first
    assert shapes_first.KIT in shapes_first.ADAPTERS and shapes_first.KIT.layer == earth_seed.KIT_LAYER
    step = next(row for row in shapes_first.rows() if row.name == "kit-sections")
    assert not step.applies("hangar")  # no kit row handed to the loop yet (earth_seed.NOT_HANDED)
    assert "kit-sections" in assembly.LAYERS
    for path in sorted((REPO / "data/plans").glob("*.json")):
        sections = json.loads(path.read_text()).get("sections", [])
        if not sections:
            continue
        kit = json.loads((REPO / "data/kit" / path.name).read_text())
        laid = {earth_seed.piece_row(piece, kit, path.stem) for piece in kit["pieces"]}
        rows = [row for section in sections for row in section["rows"]]
        assert len(rows) == len(set(rows)) and set(rows) <= laid, (path.stem, set(rows) - laid)
        assert {section["surface"] for section in sections} <= {"walls", "floor", "ceiling"}, path.stem



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
    # kit-sections reads its own place's earth seed (its base stage), never the round-three folder
    reading = ({row.name for row in stages.STAGES if "earth-seed" in row.after}
               - {stages.library.PLACE_ROW, "kit-sections"})
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
