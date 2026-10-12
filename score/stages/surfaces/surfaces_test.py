"""The surface stage's framework side: the finish registry keeps each proposed library surface as first proposed, the
per-place data names each take once world-wide and every model a place lays that another place claims is baked by
that place, every place's line is rows of world 1's table, the paint takes the method's surface and records its
proposal, and a gate that cannot read what it needs, or a model whose finish map never settled, blocks with a reason on
that model instead of crashing or passing. No cloud, no paid step.

Run: .venv/bin/python score/stages/surfaces/surfaces_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, graph, stages  # noqa: E402
from score.stages import surfaces  # noqa: E402
from score.stages.surfaces import finish_rows, registry, surface_data, surface_gates  # noqa: E402
from score.store import Store  # noqa: E402


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_a_proposed_library_surface_stands_as_first_proposed():
    store = a_store()
    first = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "galvanized_dull"},
                                                     {"take": "a"})
    second = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "bare_steel"},
                                                      {"take": "b"})
    assert first["spec"] == second["spec"] == {"stands_in": "galvanized_dull"}
    assert len(store.registry("surfaces")) == 1


def test_names_alike_but_for_case_stand_as_one_entry():
    store = a_store()
    first = registry.Registry(store).propose_surface("Polished Chrome", {"stands_in": "pipe_steel"}, {"take": "a"})
    second = registry.Registry(store).propose_surface("polished chrome", {"stands_in": "bare_steel"}, {"take": "b"})
    assert second == first and len(store.registry("surfaces")) == 1
    other = registry.Registry(store).propose_surface("Polished brass", {"stands_in": "brass"}, {"take": "c"})
    assert other["name"] == "Polished brass" and len(store.registry("surfaces")) == 2


def test_the_paint_takes_the_method_s_surface_and_records_its_proposal():
    store = a_store()
    rows = [{"part": 0, "judge": "dark_panel", "proposed": None},
            {"part": 1, "judge": "galvanized_dull", "proposed": {"name": "aluminium tape", "description": "shiny",
                                                                  "why": "thinner than steel"}}]
    found = surfaces.place_line.method_surfaces("power_unit-r3", "old_station", rows, registry.Registry(store))
    assert [record["surface"] for record in found] == ["dark_panel", "galvanized_dull"]
    assert found[1]["proposed"]["stands_in"] == "galvanized_dull" and found[1]["proposed"]["status"] == "proposed"
    assert [entry["name"] for entry in store.registry("surfaces")] == ["aluminium tape"]


def test_each_take_is_painted_by_one_place_and_every_claim_is_baked_by_its_place():
    owner = {}
    records = {path.stem: json.loads(path.read_text()) for path in sorted(surface_data.FOLDER.glob("*.json"))}
    for place, record in records.items():
        assert (REPO / "data/kit" / f"{place}.json").exists(), f"{place}: no such place"
        assert record["takes"] or record.get("nothing"), f"{place}: lists nothing to paint and says not why"
        assert surface_data.paints(place) == bool(record["takes"]), place
        for take, entry in record["takes"].items():
            assert take not in owner, f"{take}: painted by {owner.get(take)} and {place}"
            owner[take] = place
            assert {"place", "kind", "object", "library_places"} <= set(entry), f"{place} {take}"
        bake = record.get("bake")
        if bake:
            assert set(bake["models"].values()) <= set(record["takes"]), f"{place}: bakes a take it does not paint"
    for place, record in records.items():
        for model, claim in record.get("elsewhere", {}).items():
            other = records[claim["place"]]
            assert claim["take"] in other["takes"], f"{place} {model}: {claim['place']} does not paint {claim['take']}"
            assert claim["take"] in other["bake"]["models"].values(), f"{place} {model}: {claim['place']} bakes none"


def test_every_place_s_surface_line_is_rows_of_world_one():
    names = [stage.name for stage in stages.STAGES]
    assert {"surfaces-inputs", "surfaces-maps", "surfaces-parts", "surfaces-paint", "surfaces-bake",
            "surfaces-check"} <= set(names)
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert all(stage.grain == "place" for stage in surfaces.ROWS)
    assert set(rows["surfaces-paint"].after) == {"surfaces-parts"}  # the method's interface
    assert all(stage.euros for stage in surfaces.ROWS if stage.paid)


def test_a_place_without_data_blocks_before_anything_is_spent_and_one_with_nothing_to_paint_has_no_rows():
    world = graph.World("world1", 1, {"data": str(REPO / "data"), "home": tempfile.mkdtemp(), "repo": str(REPO),
                                      "seeds": tempfile.mkdtemp()})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert "its input surfaces is missing" in runner.node_status(rows["surfaces-inputs"], "nowhere")
    assert not any(node.endswith("@tube") for node in runner.status(["tube"]))  # code-built pieces only
    try:
        runner.file_keys(rows["surfaces-bake"], "nowhere")
    except graph.Blocked as block:
        assert "nowhere.json" in str(block)
        return
    raise AssertionError("a place with no data did not block at its bake row")


def test_a_gate_that_cannot_read_its_evidence_answers_unknown():
    folder = pathlib.Path(tempfile.mkdtemp())
    check = surface_gates.guarded("maps checked", finish_rows.judge_maps)
    found = checks.judge(check, folder, {"surfaces-inputs": str(folder)}, None)
    assert found.answer == checks.UNKNOWN and "takes.json" in found.reason
    shutil.rmtree(folder)


def test_a_model_whose_finish_map_never_settled_is_named_and_blocks():
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "flat").mkdir()
    (folder / "flat" / "takes.json").write_text(json.dumps({"chair-b": {}, "power_unit-r3": {}}))
    (folder / "chair-b").mkdir()
    (folder / "chair-b" / "map.json").write_text(json.dumps(
        {"take": "chair-b", "passes": True, "front": {"attempts": [], "passes": True}, "views": {}}))
    (folder / "power_unit-r3").mkdir()
    attempt = {"seed": 3, "iou": 0.99, "near_label": 0.6, "labels_used": 3, "labels_listed": 3, "passes": False}
    (folder / "power_unit-r3" / "map.json").write_text(json.dumps(
        {"take": "power_unit-r3", "passes": False, "front": {"attempts": [attempt], "passes": False}, "views": {}}))
    found = checks.judge(surface_gates.guarded("maps checked", finish_rows.judge_maps), folder,
                         {"surfaces-inputs": str(folder)}, None)
    assert found.answer == checks.FAIL and checks.blocks(found.answer)
    assert len(found.findings) == 1 and found.findings[0].startswith("power_unit-r3: no finish map settled")
    shutil.rmtree(folder)


# The seed tray's paper label on black plastic, as baked (greenhouse bake output 439948bc): each of its 65 triangles'
# baked L*a*b*, area (to the largest), the surfaces within its reach (potting_soil, printed_paper, tray_plastic) and
# whether its corners straddle a part border. 19 of them bake the plastic's near black.
SEED_TRAY_PAPER = [
    (79.2, -0.7, 7.6, 0.1987, "011", False),
    (79.2, -0.7, 7.6, 0.8008, "011", False),
    (9.9, 0.7, -0.5, 0.2788, "011", True),
    (79.2, -0.7, 7.6, 0.534, "011", False),
    (9.3, 0.5, -1.4, 0.4221, "011", True),
    (9.9, 0.7, -0.5, 0.1251, "011", True),
    (9.9, 0.7, -0.5, 0.1117, "011", True),
    (9.9, 0.7, -0.5, 0.1437, "011", True),
    (9.9, 0.7, -0.5, 0.4054, "111", True),
    (79.2, -0.7, 7.6, 0.2535, "011", False),
    (9.9, 0.7, -0.5, 0.1022, "011", True),
    (78.8, -0.7, 7.7, 0.8483, "111", False),
    (10.0, 1.2, -0.3, 0.4276, "011", True),
    (77.7, -0.7, 7.7, 0.5298, "011", False),
    (79.2, -0.7, 7.6, 0.3602, "011", False),
    (79.2, -0.7, 7.6, 0.2877, "011", False),
    (78.5, -0.5, 7.2, 0.5201, "011", False),
    (77.0, -0.7, 7.7, 0.2867, "011", False),
    (75.1, -1.1, 7.6, 0.3235, "011", False),
    (79.2, -0.7, 7.6, 0.1694, "011", False),
    (79.2, -0.7, 7.6, 0.676, "011", False),
    (74.5, -0.5, 7.2, 0.0633, "011", False),
    (74.9, -0.5, 7.2, 0.1252, "011", True),
    (20.8, -0.0, 1.4, 0.105, "011", True),
    (72.3, -0.5, 7.3, 0.3978, "011", True),
    (79.2, -0.7, 7.6, 0.226, "011", False),
    (76.7, -0.7, 7.7, 0.608, "011", True),
    (79.2, -0.7, 7.6, 0.7381, "011", True),
    (10.0, 1.2, -0.3, 0.0822, "011", True),
    (74.1, -0.5, 7.2, 0.2326, "011", False),
    (74.1, -0.5, 7.2, 0.1202, "010", False),
    (79.2, -0.7, 7.6, 0.0853, "011", True),
    (79.2, -0.7, 7.6, 0.4938, "011", False),
    (78.1, -0.7, 7.7, 0.3396, "011", False),
    (10.7, 1.7, 1.4, 0.1247, "011", True),
    (75.6, -0.5, 7.2, 0.5145, "011", False),
    (79.2, -0.7, 7.6, 0.896, "011", False),
    (79.2, -0.7, 7.6, 0.1385, "011", False),
    (78.8, -0.7, 7.7, 0.6235, "111", False),
    (9.9, 0.7, -0.5, 0.3203, "111", True),
    (79.2, -0.7, 7.6, 0.1366, "011", False),
    (9.9, 0.7, -0.5, 0.757, "111", True),
    (65.5, -0.5, 6.3, 0.118, "011", False),
    (79.2, -0.7, 7.6, 0.0903, "011", False),
    (9.4, 1.0, -1.2, 0.0811, "011", False),
    (73.0, -0.5, 7.3, 0.4309, "011", True),
    (79.2, -0.7, 7.6, 0.5007, "011", False),
    (10.0, 1.2, -0.3, 0.125, "011", True),
    (9.3, 0.5, -1.4, 0.4311, "011", True),
    (75.6, -0.5, 7.2, 0.3532, "011", False),
    (77.7, -0.7, 7.7, 0.5297, "011", False),
    (78.8, -0.7, 7.7, 0.5839, "011", False),
    (79.2, -0.7, 7.6, 0.1448, "011", True),
    (79.2, -0.7, 7.6, 1.0, "011", False),
    (10.7, 1.7, 1.4, 0.4031, "011", True),
    (10.7, 1.7, 1.4, 0.2377, "011", True),
    (79.2, -0.7, 7.6, 0.098, "011", False),
    (79.2, -0.7, 7.6, 0.6058, "111", True),
    (10.0, 1.2, -0.3, 0.2574, "011", False),
    (74.5, -0.5, 7.2, 0.2059, "011", False),
    (79.2, -0.7, 7.6, 0.1615, "011", False),
    (9.4, 1.0, -1.2, 0.5341, "011", True),
    (77.7, -0.7, 7.7, 0.6325, "011", False),
    (76.3, -0.7, 7.7, 0.4506, "011", False),
    (71.5, -0.5, 7.3, 0.4865, "011", True),
]
SEED_TRAY_SURFACES = [(30.5, 7.6, 15.6), (79.2, -0.7, 7.6), (9.3, 0.5, -1.4)]


def paper_record(rows):
    import numpy as np
    from score.stages.surfaces import bake_check
    colour = np.array([row[:3] for row in rows])
    reach = np.array([[flag == "1" for flag in row[4]] for row in rows])
    share = bake_check.blotch_share(colour, np.array([row[3] for row in rows]), np.ones(len(rows), dtype=bool), reach,
                                    SEED_TRAY_SURFACES)
    return {"surfaces": {"printed_paper": {"share": 0.0117, "baked_lab": [77.7, -0.7, 7.7],
                                           "surface_lab": list(SEED_TRAY_SURFACES[1]), "delta_e": 1.5,
                                           "near_black": share}}}


def test_a_clean_label_border_passes_and_a_black_smudge_along_it_fails():
    from score.stages.surfaces import bake_check
    assert bake_check.surface_faults("seed_tray_1", paper_record(SEED_TRAY_PAPER)) == []
    smudge, area = [], 0.0  # light triangles across the label's border turned black until a tenth of its area
    total = sum(row[3] for row in SEED_TRAY_PAPER)
    for row in SEED_TRAY_PAPER:
        if row[5] and row[0] > bake_check.BLOTCH_L and area < 0.1 * total:
            row, area = (0.0, 0.0, 0.0, *row[3:]), area + row[3]
        smudge.append(row)
    faults = bake_check.surface_faults("seed_tray_1", paper_record(smudge))
    assert len(faults) == 1 and "printed_paper" in faults[0] and "near black" in faults[0], faults
    assert {stage.name: stage for stage in stages.STAGES}["surfaces-check"].make is bake_check.make_check


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
