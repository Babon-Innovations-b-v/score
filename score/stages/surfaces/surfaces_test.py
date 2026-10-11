"""The surface stage's framework side: the finish registry is an append-only store item (a finish group gets its
surface on first sight and keeps it, the owner's picks read first), the per-place data names each take once, every
place's line is rows of world 1's table, and a gate that cannot read what it needs, or a model whose split fails,
blocks with a reason on that model instead of crashing or passing. No cloud, no paid step.

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
from score.stages.surfaces import registry, split_batch, surface_data, surface_gates  # noqa: E402
from score.store import Store  # noqa: E402

GREY = ([45.0, 0.0, 5.0, 0.1, 0.9], [2.0, 1.0, 1.0, 0.05, 0.05])
GOLD = ([65.0, 6.0, 40.0, 0.99, 0.6], [2.0, 1.0, 1.0, 0.05, 0.05])


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_a_finish_group_gets_its_surface_on_first_sight_and_keeps_it():
    store = a_store()
    found = registry.Registry(store).surfaces_for([(GREY, "dark_panel", {"take": "a"}),
                                                   (GREY, "galvanized_dull", {"take": "b"}),
                                                   (GOLD, None, {"take": "c"})])
    assert found[0][:3] == ("F0001", "dark_panel", False)
    assert found[1][:3] == ("F0001", "dark_panel", True)  # one finish, one surface, whatever the judge said again
    assert found[2] is None  # nothing matches and the judge named nothing: no group
    again = registry.Registry(store).surfaces_for([(GOLD, "gold_foil", {"take": "d"}), (GREY, "x", {"take": "e"})])
    assert [entry[:2] for entry in again] == [("F0002", "gold_foil"), ("F0001", "dark_panel")]
    assert [group["id"] for group in store.registry("finishes")] == ["F0001", "F0002"]
    try:
        store.write_registry("finishes", "F0001", {"surface": "changed"})
    except FileExistsError:
        return
    raise AssertionError("a registry entry was overwritten")


def test_the_owners_picks_are_read_first_and_never_appended():
    store = a_store()
    seeded = [{"id": "S-chair-b-pipe_steel", "surface": "pipe_steel", "centre": GREY[0], "spread": GREY[1]}]
    found = registry.Registry(store, seeded).surfaces_for([(GREY, "dark_panel", {"take": "a"})])
    assert found[0][:3] == ("S-chair-b-pipe_steel", "pipe_steel", True) and store.registry("finishes") == []


def test_a_proposed_library_surface_stands_as_first_proposed():
    store = a_store()
    first = registry.Registry(store).propose_surface("rust_orange", {"colour": [0.6, 0.3, 0.1]}, {"take": "a"})
    second = registry.Registry(store).propose_surface("rust_orange", {"colour": [0.1, 0.1, 0.1]}, {"take": "b"})
    assert first["spec"] == second["spec"] == {"colour": [0.6, 0.3, 0.1]} and len(store.registry("surfaces")) == 1


def test_each_take_is_split_by_one_place_and_its_data_is_whole():
    owner = {}
    for path in sorted(surface_data.FOLDER.glob("*.json")):
        if path.stem == surface_data.SEED:
            continue
        record = json.loads(path.read_text())
        assert (REPO / "data/kit" / f"{path.stem}.json").exists(), f"{path.stem}: no such place"
        assert record["takes"], f"{path.stem}: a place with nothing to split has no data file"
        for take, entry in record["takes"].items():
            assert take not in owner, f"{take}: split by {owner.get(take)} and {path.stem}"
            owner[take] = path.stem
            assert {"place", "kind", "object", "library_places"} <= set(entry), f"{path.stem} {take}"
        bake = record.get("bake")
        if bake:
            assert set(bake["models"].values()) <= set(record["takes"]), f"{path.stem}: bakes a take it does not split"
    seed = surface_data.takes(None)
    assert seed and all((REPO / "data/parts" / f"{take}.npz").exists() for take in seed)


def test_every_place_s_surface_line_is_rows_of_world_one():
    names = [stage.name for stage in stages.STAGES]
    assert {"split-inputs", "split-split", "surfaces-parts", "surfaces-paint", "surfaces-bake", "surfaces-check",
            "surfaces-seed"} <= set(names)
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert rows["surfaces-seed"].grain == "world" and rows["surfaces-paint"].grain == "place"
    assert set(rows["surfaces-paint"].after) == {"surfaces-parts", "surfaces-seed"}  # the method's interface
    assert rows["surfaces-judge"].params["judge"]["model"].startswith("gemini-")


def test_a_place_without_data_or_without_a_bake_job_blocks_before_anything_is_spent():
    world = graph.World("world1", 1, {"data": str(REPO / "data"), "home": tempfile.mkdtemp(), "repo": str(REPO),
                                      "seeds": tempfile.mkdtemp()})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert "its input surfaces is missing" in runner.node_status(rows["split-inputs"], "camp")
    no_bake = next(path.stem for path in surface_data.FOLDER.glob("*.json")
                   if path.stem != surface_data.SEED and "bake" not in json.loads(path.read_text()))
    try:
        runner.file_keys(rows["surfaces-bake"], no_bake)
    except graph.Blocked as block:
        assert "names no bake job" in str(block)
        return
    raise AssertionError(f"{no_bake}'s bake row did not block on its missing bake job")


def test_a_gate_that_cannot_read_its_evidence_answers_unknown():
    folder = pathlib.Path(tempfile.mkdtemp())
    check = surface_gates.guarded("split", split_batch.judge_split)
    found = checks.judge(check, folder, {}, None)
    assert found.answer == checks.UNKNOWN and "splits.json" in found.reason
    shutil.rmtree(folder)


def test_a_model_whose_split_fails_is_named_and_blocks():
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "splits.json").write_text(json.dumps({
        "chair-b": {"method": "multiview", "mixing_parts": []},
        "telephone-r6": {"method": "multiview", "mixing_parts": [3, 7]},
        "lamp": {"method": "multiview", "error": "RuntimeError('no finishes')"}}))
    found = checks.judge(surface_gates.guarded("split", split_batch.judge_split), folder, {}, None)
    assert found.answer == checks.FAIL and checks.blocks(found.answer)
    assert any(line.startswith("telephone-r6: parts [3, 7]") for line in found.findings)
    assert any(line.startswith("lamp: RuntimeError") for line in found.findings) and len(found.findings) == 2
    shutil.rmtree(folder)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
