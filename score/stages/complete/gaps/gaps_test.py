"""The gaps check through its command, over a toy store in the sandbox home and a toy environment's data: missing
rows as guide boxes at their spots, walls, parents' tops (made or missing) or nowhere, never with score:row; gate
marks from a FAIL judgement, another check's findings and an accepted gap, merged on the prim they name; the route's
place gaps; the contract; and the completion gate's own rows rule still listing every unmade row over the overlay.
"""
import json
import pathlib

import pytest
from pxr import Usd, UsdGeom

from score import review, stages
from score.stages.complete import complete
from score.stages.complete.gaps import fill
from score.stages.complete.gaps.__main__ import gaps_faults, main
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[4]
PLACE = "gaptoy"
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
    def Scope "Places"
    {{
        def Xform "next_door"
        {{
            def Cube "shelf_1"
            {{
                custom string score:row = "shelf"
                double size = 1
            }}
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
     "at": [], "dropped": "not in the concept"},
    {"id": "ground", "name": "the ground", "kind": "generate", "anchor": "ground", "size": None, "count": 1}]}
GAP = {"name": f"{PLACE}: the crate's placeholder", "row": "assembly", "check": "placeholders", "objects": ["crate_1"],
       "reason": "its model comes next month", "decided": "owner, 2026-10-19", "faults": []}
ROWS_GAP = {"name": f"{PLACE}: the shelf comes later", "row": "complete", "check": "rows", "objects": ["shelf"],
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
    """The command run once over the toy: (its out folder, findings.json, the gaps stage)."""
    root = tmp_path_factory.mktemp("gaps")
    data = root / "data"
    for folder, written in (("inventory", INVENTORY), ("kit", {"room": PLACE, "pieces": []}),
                            ("checks/gaps", {"gaps": [GAP, ROWS_GAP]})):
        (data / folder).mkdir(parents=True, exist_ok=True)
        (data / folder / f"{PLACE}.json").write_text(json.dumps(written))
    (data / "checks/row-kinds.json").write_text((REPO / "data/checks/row-kinds.json").read_text())  # sound's needs
    store = Store.in_folder(PROPS_HOME / "store")
    assembly = made(store, root / "assembly", f"assembly@{PLACE}", {f"{PLACE}.usda": STAGE},
                    {"placeholders": verdict("placeholders", "pass")})
    made(store, root / "complete", f"complete@{PLACE}", {"manifest.json": "{}"},
         {"people": verdict("people", "fail", ["crate_1: stands where a person should"]),
          "boxes": verdict("boxes", "fail", [f"{PLACE}.crate: its box is off the model's (crate-s1)"]),
          "rows": verdict("rows", "fail", [json.dumps({"row": "shelf", "why": "no object"})])})
    seen = root / "work/checks/visual" / PLACE
    seen.mkdir(parents=True)
    (seen / "findings.json").write_text(json.dumps({"outputs": {f"assembly@{PLACE}": assembly}, "findings": [
        {"rule": "seen", "prim": f"/{PLACE}/Objects/crate_1", "sentence": "the crate floats", "picture": None}]}))
    stale = root / "work/checks/materials" / PLACE
    stale.mkdir(parents=True)
    (stale / "findings.json").write_text(json.dumps({"outputs": {f"assembly@{PLACE}": "0" * 64}, "findings": [
        {"rule": "ragged", "prim": f"/{PLACE}/Objects/crate_1", "sentence": "a ragged border", "picture": None}]}))
    out = root / "work/checks/gaps"
    main(["--place", PLACE, "--out", str(out), "--data", str(data)])
    folder = out / PLACE
    return folder, json.loads((folder / "findings.json").read_text()), Usd.Stage.Open(str(folder / "gaps.usda"))


def by_id(written):
    return {item["id"]: item for item in written["findings"]}


def test_missing_rows_are_guide_boxes_at_their_spots_and_never_made_objects(ran):
    folder, written, stage = ran
    found = by_id(written)
    assert {item["row"] for item in written["findings"] if item["rule"] == "missing"} == {
        "shelf", "panel", "cup", "lamp", "rug", "beam", "ground"}
    shelf = stage.GetPrimAtPath(f"/{PLACE}/Gaps/shelf_1")
    assert shelf.GetAttribute("score:gap:row").Get() == "shelf" and shelf.GetAttribute("score:gap").Get() == "missing"
    box = UsdGeom.Cube(stage.GetPrimAtPath(f"/{PLACE}/Gaps/shelf_1/box"))
    assert box.GetPurposeAttr().Get() == UsdGeom.Tokens.guide
    assert tuple(stage.GetPrimAtPath(f"/{PLACE}/Gaps/shelf_1/box").GetAttribute("xformOp:scale").Get()) == (2, 1, 0.5)
    # turned 90 degrees about up: its width runs along z
    assert found["missing:shelf_1"]["low"] == pytest.approx([2.75, 0, 1]) and \
        found["missing:shelf_1"]["high"] == pytest.approx([3.25, 1, 3])
    assert found["missing:panel_1"]["placed"] == "wall" and found["missing:panel_1"]["low"][1] == pytest.approx(1)
    assert not any(prim.HasAttribute("score:row") for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{PLACE}/Gaps")))


def test_children_stand_on_their_parents_top_made_or_missing(ran):
    folder, written, stage = ran
    found = by_id(written)
    # the inventory gives no layout on the parent: both stand at the middle of its top, none spread by guess
    assert found["missing:cup_1"]["low"] == pytest.approx([-0.1, 1.0, -0.1])
    assert found["missing:cup_2"]["low"] == found["missing:cup_1"]["low"]
    assert found["missing:lamp_1"]["prim"] == f"/{PLACE}/Gaps/shelf_1/lamp_1"
    assert found["missing:lamp_1"]["placed"] == "on" and found["missing:lamp_1"]["low"][1] == pytest.approx(1.0)


def test_a_row_with_no_spot_has_no_transform_and_no_box(ran):
    folder, written, stage = ran
    rug = by_id(written)["missing:rug_1"]
    assert rug["placed"] == "unplaced" and rug["low"] is None and rug["high"] is None
    assert "no spot" in rug["sentence"]
    assert not UsdGeom.Xformable(stage.GetPrimAtPath(rug["prim"])).GetOrderedXformOps()
    # a design row read with no metres (its ground) is a gap with no box
    ground = by_id(written)["missing:ground_1"]
    assert ground["low"] is None and not stage.GetPrimAtPath(f"{ground['prim']}/box")


def test_gate_marks_merge_on_the_prim_they_name_and_a_gap_is_a_decided_fault(ran):
    folder, written, stage = ran
    crate = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert crate.GetAttribute("score:gap").Get() == "gate"
    assert set(crate.GetAttribute("score:gap:gates").Get()) == {
        "complete/people", "complete/boxes", "visual/seen", "assembly/placeholders"}
    found = by_id(written)
    gap = found["gate:assembly/placeholders:crate_1"]
    assert gap["node"] is None and gap["work"] == GAP["reason"] and gap["source"].startswith("gap:")
    seen = found["gate:visual/seen:" + f"/{PLACE}/Objects/crate_1"]
    assert seen["source"] == "check:visual" and "visual check" in seen["work"] and "floats" not in seen["work"]
    assert found["gate:complete/people:crate_1"]["source"] == f"judgement:complete@{PLACE}"
    # "<place>.<row>" names the row: found on its object, joined to its row
    boxes = found["gate:complete/boxes:crate"]
    assert boxes["prim"] == f"/{PLACE}/Objects/crate_1" and boxes["row"] == "crate"
    # complete's rows verdict and an accepted gap on it are the missing rows' own: never a gate gap too
    assert not any("complete/rows" in item["gates"] for item in written["findings"])


def test_a_check_whose_output_moved_marks_nothing(ran):
    folder, written, stage = ran
    assert not any("materials/ragged" in item["gates"] for item in written["findings"])
    assert "materials/ragged" not in stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1").GetAttribute(
        "score:gap:gates").Get()


def test_a_shown_place_s_objects_are_never_the_place_s_own(ran):
    folder, written, stage = ran
    assert "missing:shelf_1" in by_id(written)
    assert not stage.GetPrimAtPath(f"/{PLACE}/Places/next_door/shelf_1").HasAttribute("score:gap")


def test_a_kit_piece_with_no_named_failure_is_filled_by_the_loop():
    beam = INVENTORY["rows"][6]  # #19: a kit piece is the shared loop's unless the pipeline-failure record names it
    for in_kit in (True, False):
        node, work = fill.missing_row(beam, PLACE, in_kit)
        assert node == f"pixal@{PLACE}" or "design hand-in" in work, (node, work)


def test_the_place_lacks_its_concept_plan_and_rough_model(ran):
    folder, written, stage = ran
    found = by_id(written)
    assert {"place:concept", "place:plan", "place:rough-model"} <= set(found)
    assert found["place:rough-model"]["work"] and found["place:rough-model"]["node"] is None
    assert list(stage.GetPrimAtPath(f"/{PLACE}").GetAttribute("score:gaps:place").Get()) == [
        "concept", "plan", "rough-model"]
    # a layer's own gap (layers.py): the toy has no plan, so the sound layer names what its design lacks for a bed
    sound = found["place:sound:bed:room"]
    assert sound["source"] == "layer:sound" and sound["node"] is None and "no plan" in sound["work"], sound
    assert written["counts"] == {"missing": 8, "gate": 4, "place": 4}


def test_the_contract_holds_and_the_rows_gate_still_lists_every_unmade_row(ran):
    folder, written, stage = ran
    assert gaps_faults(written) == []
    # every node read is written, null when not accepted, so one accepted later makes the findings stale
    outputs = written["outputs"]
    assert set(outputs) == {f"neighbours@{PLACE}", f"assembly@{PLACE}", f"plan@{PLACE}", f"rough-model@{PLACE}",
                            f"complete@{PLACE}"}
    assert outputs[f"assembly@{PLACE}"]  # complete failed: not accepted, so null like the three never made
    assert [outputs[f"{stage}@{PLACE}"] for stage in ("neighbours", "plan", "rough-model", "complete")] == [None] * 4
    assert {fault["row"] for fault in complete.rows_faults(folder / "gaps.usda", INVENTORY, PLACE)} == {
        "shelf", "panel", "cup", "lamp", "rug", "beam", "ground"}


def test_the_contract_refuses_what_it_names():
    good = {"id": "place:plan", "rule": "place", "node": None, "work": "a plan", "low": None, "high": None}
    assert gaps_faults({"findings": [good]}) == []
    bad = [dict(good, id="z", rule="other"), dict(good, id="a", work=None), dict(good, id="b", node="plan@x"),
           dict(good, id="c", low=[0, 0, 0]), good]
    assert len(gaps_faults({"findings": [good, *bad]})) == 5


def test_every_filler_is_a_stage_of_the_table_or_the_ship_kit():
    names = {row.name for row in stages.STAGES} | {fill.SHIP_KIT}
    named = ({stage for stage, _ in fill.FILLERS.values() if stage} | set(fill.COMPLETE_GATES.values())
             | {fill.ASSEMBLY})
    assert named <= names, named - names


def test_lost_inputs_are_place_gaps_with_their_code_work():
    """On a home whose work folder is gone: the cockpit's owner's pictures, and the launch's far rocket whose bake entry
    went with its old job, each a place gap with its code work and no node; the cockpit's cast no longer asks for a
    scene record it never had. A kit-laid or designed place's seed is no lost input, the ship's rooms' too: its readers
    wait on earth-seed@<place> (#27; the owner, 2026-10-21); only a place with neither (the far city) is still lost."""
    from score.stages.complete.gaps import inputs
    from score.stages.complete.gaps.__main__ import lost_gaps
    runner = stages.runner(store=Store.in_folder(PROPS_HOME / "store"))
    cockpit = {gap["id"]: gap for gap in inputs.lost(runner, "cockpit")}
    assert {"lost:reference:cockpit.png", "lost:reference:reference-shuttle.png"} <= set(cockpit), sorted(cockpit)
    assert not any(gap.startswith(("lost:earth-seed", "lost:ship-seed")) for gap in cockpit), sorted(cockpit)
    assert "lost:views:cockpit.json" not in cockpit  # its light reads its views from its own scene record (#27)
    assert not any("data/scene/cockpit.json" in gap["sentence"] for gap in cockpit.values())
    launch = {gap["id"]: gap for gap in inputs.lost(runner, "launch")}
    assert not any("bake entry" in gap for gap in launch), sorted(launch)  # its rocket is the library's (#10)
    # no row reads the launch's own round-three seed since terrain-look was retired (#27)
    assert "lost:earth-seed:launch" not in launch and "lost:earth-seed:far_city" in launch, sorted(launch)
    found = [dict(gap, low=None, high=None) for gap in lost_gaps(runner, "launch")]
    assert gaps_faults({"findings": found}) == [] and all(gap["rule"] == "place" for gap in found)


def test_a_take_a_pixal_row_makes_is_that_row_s_gap_and_one_none_makes_has_its_work():
    """The cockpit's pilot seat take is made by pixal@cockpit, so its gap is that node's, priced through it, never
    code work; a world row's lost take no pixal row makes (demo-turntables' pliers) is a gap of the world."""
    from score.stages.complete.gaps import inputs
    runner = stages.runner(store=Store.in_folder(PROPS_HOME / "store"))
    cockpit = {gap["id"]: gap for gap in inputs.lost(runner, "cockpit")}
    seat = cockpit["lost:pixal:pilot_seat-s1"]
    assert seat["node"] == "pixal@cockpit" and seat["work"] is None, seat
    world = {gap["id"]: gap for gap in inputs.lost(runner, None)}
    pliers = world["lost:pixal:pliers-pf"]
    assert pliers["node"] is None and pliers["work"] and "demo-turntables" in pliers["sentence"], pliers


def test_an_earth_place_s_views_copy_names_the_rows_that_read_it():
    from score.stages.complete.gaps import inputs
    runner = stages.runner(store=Store.in_folder(PROPS_HOME / "store"))
    views = {gap["id"]: gap for gap in inputs.lost(runner, "launch")}["lost:views:launch.json"]
    assert "effects-look@launch" in views["work"] and "light" not in views["work"], views


def test_a_lost_input_many_places_read_counts_once():
    from score.stages.complete.gaps import inputs
    gaps = [{"id": "place:lost:earth-seed:usd-r3"}, {"id": "place:concept"}, {"id": "place:lost:earth-seed:usd-r3"},
             {"id": "place:concept"}]
    assert inputs.distinct(gaps) == gaps[:2] + gaps[3:]


def test_a_lost_input_many_nodes_read_is_one_gap():
    """Grouped by what it is: a take's files, read by two nodes, one gap; a folder's lost files one gap."""
    from score.stages.complete.gaps import inputs

    class Table:
        world = stages.world1()

        def nodes(self, places):
            return [(type("Row", (), {"name": name}), places[0]) for name in ("one", "two")]

        def files_of(self, stage, place):
            return {"model": "{home}/work/pixal/cup-s1.glb", "close-up": "{home}/work/pixal/cup-s1.svviews",
                    "picture": "{seeds}/scene/{place}/views/a.png", "other": "{seeds}/scene/{place}/views/b.png"}

        def file_path(self, stage, name, place):
            return PROPS_HOME / "no-such" / name

    found = {gap["id"]: gap for gap in inputs.lost(Table(), PLACE)}
    assert set(found) == {"lost:pixal:cup-s1", f"lost:work:scene/{PLACE}/views"}, set(found)
    assert "and 1 more" in found["lost:pixal:cup-s1"]["sentence"]
