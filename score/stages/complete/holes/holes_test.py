"""The holes check through its command, over a toy store in the sandbox home and a toy environment's data: missing
rows as guide boxes at their spots, walls, parents' tops (made or missing) or nowhere, never with score:row; gate
marks from a FAIL judgement, another check's findings and a named gap, merged on the prim they name; the route's
place holes; the contract; and the completion gate's own rows rule still listing every unmade row over the overlay.
"""
import json
import pathlib

import pytest
from pxr import Usd, UsdGeom

from score import review, stages
from score.stages.complete import complete
from score.stages.complete.holes import fill
from score.stages.complete.holes.__main__ import holes_faults, main
from score.store import PROPS_HOME, Store

PLACE = "holetoy"
STAGE = f"""#usda 1.0
(
    defaultPrim = "{PLACE}"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "{PLACE}"
{{
    def Scope "Objects"
    {{
        def Cube "crate_1"
        {{
            custom string score:row = "crate"
            double size = 1
            double3 xformOp:translate = (0, 0.5, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}
    }}
}}
"""
INVENTORY = {"room": {"layout": {"inside": [6.0, 6.0], "corner": 1.0, "wall": 3.0, "doors": {}}}, "rows": [
    {"id": "crate", "name": "a crate", "kind": "generate", "made": "made by the route", "anchor": "floor",
     "size": [1, 1, 1], "count": 1, "at": [{"x": 0, "y": 0, "z": 0, "facing": 0}]},
    {"id": "shelf", "name": "a shelf", "kind": "generate", "made": "made by the route", "anchor": "floor",
     "size": [2, 0.5, 1], "count": 1, "at": [{"x": 3, "z": 2, "facing": 90}]},
    {"id": "panel", "name": "a wall panel", "kind": "generate", "made": "made by the route", "anchor": "wall",
     "size": [1, 0.1, 0.5], "count": 1, "at": [{"wall": "north", "across": 0, "bottom": 1}]},
    {"id": "cup", "name": "a cup", "kind": "generate", "made": "made by the route", "anchor": "on:crate",
     "parent": "crate", "size": [0.2, 0.2, 0.3], "count": 2, "at": []},
    {"id": "lamp", "name": "a lamp", "kind": "generate", "made": "made by the route", "anchor": "on:shelf",
     "parent": "shelf", "size": [0.3, 0.3, 0.4], "count": 1, "at": []},
    {"id": "rug", "name": "a hanging rug", "kind": "generate", "made": "made by the route", "anchor": "ceiling",
     "size": [1, 1, 0.1], "count": 1, "at": []},
    {"id": "beam", "name": "a beam", "kind": "code", "made": "kit piece", "anchor": "ceiling", "size": [3, 0.2, 0.2],
     "count": 1, "at": [{"x": 0, "y": 2.5, "z": 1, "facing": 0}]},
    {"id": "old", "name": "a dropped thing", "kind": "generate", "anchor": "floor", "size": [1, 1, 1], "count": 1,
     "at": [], "dropped": "not in the concept"}]}
GAP = {"name": f"{PLACE}: the crate's placeholder", "row": "assembly", "check": "placeholders", "objects": ["crate_1"],
       "reason": "its model comes next month", "decided": "owner, 2026-10-19", "faults": []}
STAMP = "2026-10-19T10:00:00.000000+00:00"


def made(store, folder, node, files, verdicts):
    """One node's output stored, its finish record and judgement written, and the runner's accept when it passed."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text)
    output = store.put_tree(folder)
    key = f"key-{node.replace('@', '-')}"
    stage, place = node.split("@")
    store.write_record(node, key, {"node": node, "key": key, "output": output, "stage": stage, "place": place,
                                   "finished": STAMP, "started": STAMP, "minutes": 1.0, "euros": 0, "after": {},
                                   "files": {}})
    answer = "fail" if any(verdict["answer"] == "fail" for verdict in verdicts.values()) else "pass"
    store.write_judgement(node, key, "e1", {"node": node, "key": key, "output": output, "evidence": "e1",
                                            "at": STAMP, "answer": answer, "verdicts": verdicts})
    review.accept_automatically(store, node, output)
    return output


def verdict(name, answer, findings=()):
    return {"check": name, "answer": answer, "reason": f"{len(findings)} faults", "measures": {},
            "better": {}, "findings": list(findings)}


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    """The command run once over the toy: (its out folder, findings.json, the holes stage)."""
    root = tmp_path_factory.mktemp("holes")
    data = root / "data"
    for folder, written in (("inventory", INVENTORY), ("kit", {"room": PLACE, "pieces": []}),
                            ("checks/gaps", {"gaps": [GAP]})):
        (data / folder).mkdir(parents=True, exist_ok=True)
        (data / folder / f"{PLACE}.json").write_text(json.dumps(written))
    store = Store.in_folder(PROPS_HOME / "store")
    assembly = made(store, root / "assembly", f"assembly@{PLACE}", {f"{PLACE}.usda": STAGE},
                    {"placeholders": verdict("placeholders", "pass")})
    made(store, root / "complete", f"complete@{PLACE}", {"manifest.json": "{}"},
         {"people": verdict("people", "fail", ["crate_1: stands where a person should"]),
          "rows": verdict("rows", "fail", [json.dumps({"row": "shelf", "why": "no object"})])})
    seen = root / "work/checks/visual" / PLACE
    seen.mkdir(parents=True)
    (seen / "findings.json").write_text(json.dumps({"outputs": {f"assembly@{PLACE}": assembly}, "findings": [
        {"rule": "seen", "prim": f"/{PLACE}/Objects/crate_1", "sentence": "the crate floats", "picture": None}]}))
    out = root / "work/checks/holes"
    main(["--place", PLACE, "--out", str(out), "--data", str(data)])
    folder = out / PLACE
    return folder, json.loads((folder / "findings.json").read_text()), Usd.Stage.Open(str(folder / "holes.usda"))


def by_id(written):
    return {item["id"]: item for item in written["findings"]}


def test_missing_rows_are_guide_boxes_at_their_spots_and_never_made_objects(ran):
    folder, written, stage = ran
    found = by_id(written)
    assert {item["row"] for item in written["findings"] if item["rule"] == "missing"} == {
        "shelf", "panel", "cup", "lamp", "rug", "beam"}
    shelf = stage.GetPrimAtPath(f"/{PLACE}/Holes/shelf_1")
    assert shelf.GetAttribute("score:hole:row").Get() == "shelf" and shelf.GetAttribute("score:hole").Get() == "missing"
    box = UsdGeom.Cube(stage.GetPrimAtPath(f"/{PLACE}/Holes/shelf_1/box"))
    assert box.GetPurposeAttr().Get() == UsdGeom.Tokens.guide
    assert tuple(stage.GetPrimAtPath(f"/{PLACE}/Holes/shelf_1/box").GetAttribute("xformOp:scale").Get()) == (2, 1, 0.5)
    # turned 90 degrees about up: its width runs along z
    assert found["missing:shelf_1"]["low"] == pytest.approx([2.75, 0, 1]) and \
        found["missing:shelf_1"]["high"] == pytest.approx([3.25, 1, 3])
    assert found["missing:panel_1"]["placed"] == "wall" and found["missing:panel_1"]["low"][1] == pytest.approx(1)
    assert not any(prim.HasAttribute("score:row") for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{PLACE}/Holes")))


def test_children_stand_on_their_parents_top_made_or_missing(ran):
    folder, written, stage = ran
    found = by_id(written)
    assert [found[f"missing:cup_{number}"]["low"][1] for number in (1, 2)] == pytest.approx([1.0, 1.0])
    assert found["missing:cup_1"]["low"][0] < found["missing:cup_2"]["low"][0]
    assert found["missing:lamp_1"]["prim"] == f"/{PLACE}/Holes/shelf_1/lamp_1"
    assert found["missing:lamp_1"]["placed"] == "on" and found["missing:lamp_1"]["low"][1] == pytest.approx(1.0)


def test_a_row_with_no_spot_has_no_transform_and_no_box(ran):
    folder, written, stage = ran
    rug = by_id(written)["missing:rug_1"]
    assert rug["placed"] == "unplaced" and rug["low"] is None and rug["high"] is None
    assert "no spot" in rug["sentence"]
    assert not UsdGeom.Xformable(stage.GetPrimAtPath(rug["prim"])).GetOrderedXformOps()


def test_gate_marks_merge_on_the_prim_they_name_and_a_gap_is_a_decided_fault(ran):
    folder, written, stage = ran
    crate = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert crate.GetAttribute("score:hole").Get() == "gate"
    assert set(crate.GetAttribute("score:hole:gates").Get()) == {
        "complete/people", "visual/seen", "assembly/placeholders"}
    found = by_id(written)
    gap = found["gate:assembly/placeholders:crate_1"]
    assert gap["node"] is None and gap["work"] == GAP["reason"] and gap["source"].startswith("gap:")
    assert found["gate:visual/seen:" + f"/{PLACE}/Objects/crate_1"]["source"] == "check:visual"
    assert found["gate:complete/people:crate_1"]["source"] == f"judgement:complete@{PLACE}"
    assert not any("complete/rows" in item["gates"] for item in written["findings"])


def test_the_place_lacks_its_concept_plan_and_rough_model(ran):
    folder, written, stage = ran
    found = by_id(written)
    assert {"place:concept", "place:plan", "place:rough-model"} <= set(found)
    assert found["place:rough-model"]["work"] and found["place:rough-model"]["node"] is None
    assert list(stage.GetPrimAtPath(f"/{PLACE}").GetAttribute("score:holes:place").Get()) == [
        "concept", "plan", "rough-model"]
    assert written["counts"] == {"missing": 7, "gate": 3, "place": 3}


def test_the_contract_holds_and_the_rows_gate_still_lists_every_unmade_row(ran):
    folder, written, stage = ran
    assert holes_faults(written) == []
    assert set(written["outputs"]) == {f"assembly@{PLACE}"}
    assert {fault["row"] for fault in complete.rows_faults(folder / "holes.usda", INVENTORY)} == {
        "shelf", "panel", "cup", "lamp", "rug", "beam"}


def test_the_contract_refuses_what_it_names():
    good = {"id": "place:plan", "rule": "place", "node": None, "work": "a plan", "low": None, "high": None}
    assert holes_faults({"findings": [good]}) == []
    bad = [dict(good, id="z", rule="other"), dict(good, id="a", work=None), dict(good, id="b", node="plan@x"),
           dict(good, id="c", low=[0, 0, 0]), good]
    assert len(holes_faults({"findings": [good, *bad]})) == 5


def test_every_filler_is_a_stage_of_the_table_or_the_ship_kit():
    names = {row.name for row in stages.STAGES} | {fill.SHIP_KIT}
    named = {stage for stage, _ in fill.FILLERS.values() if stage} | set(fill.COMPLETE_GATES.values())
    assert named <= names, named - names
