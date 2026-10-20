"""The terrain stage's own checks, with no spend: the Moon's and Mars's plans made in code give the grounds the game
laid (the same rocks to the centimetre, heights within the old fine relief), and the sight and door measures find an
opening onto nothing and lose it once ground lies outside.

Run: .venv/bin/python score/stages/terrain/terrain_test.py
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy import ndimage

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages.terrain import gates, landforms, measures, plan, record, relief, rocks, sight  # noqa: E402

GROUNDS = REPO / "data/ground"


def copied_heights(ground):
    old = json.loads((GROUNDS / f"{ground}.json").read_text())
    return record.decoded(GROUNDS / old["heights"], old["low"], old["span"])


def test_the_plans_lay_the_games_rocks_and_heights():
    for ground in ("moon", "mars"):
        made_plan = json.loads((GROUNDS / "plan" / f"{ground}.json").read_text())
        shaped = plan.shape(made_plan)
        laid = rocks.laid(shaped, made_plan)
        old = json.loads((GROUNDS / made_plan["copied"]["rocks"]).read_text())["rocks"]
        assert len(laid) == len(old), (ground, len(laid), len(old))
        assert all(abs(new["x"] - before["x"]) < 0.01 and abs(new["z"] - before["z"]) < 0.01
                   and abs(new["size"] - before["size"]) < 0.01 for new, before in zip(laid, old)), ground
        large = ndimage.zoom(shaped.heights, 1024 / made_plan["points"], order=1)
        difference = (large - copied_heights(ground)).std()
        # The copied heights hold the old fine relief (0.25 m RMS) the large shape lacks.
        assert difference < 0.3, (ground, difference)


def room(open_door, ground):
    """A 4 x 3 x 4 m box room standing on its floor at 0, a doorway 1 m wide and 2 m tall in its +x wall when asked,
    and ground at -0.1 out to 500 m when asked."""
    parts = [trimesh.creation.box(bounds=[[-2, -0.1, -2], [2, 0.0, 2]]),     # floor
             trimesh.creation.box(bounds=[[-2, 3.0, -2], [2, 3.1, 2]]),      # ceiling
             trimesh.creation.box(bounds=[[-2.1, 0, -2], [-2, 3, 2]]),       # -x wall
             trimesh.creation.box(bounds=[[-2, 0, -2.1], [2, 3, -2]]),       # -z wall
             trimesh.creation.box(bounds=[[-2, 0, 2], [2, 3, 2.1]])]         # +z wall
    if open_door:
        parts += [trimesh.creation.box(bounds=[[2, 0, -2], [2.1, 3, -0.5]]),
                  trimesh.creation.box(bounds=[[2, 0, 0.5], [2.1, 3, 2]]),
                  trimesh.creation.box(bounds=[[2, 2, -0.5], [2.1, 3, 0.5]])]
    else:
        parts.append(trimesh.creation.box(bounds=[[2, 0, -2], [2.1, 3, 2]]))
    if ground:
        parts.append(trimesh.creation.box(bounds=[[-500, -0.3, -500], [500, -0.1, 500]]))
    return trimesh.util.concatenate(parts)


def test_a_door_onto_nothing_is_found_and_ground_outside_clears_it():
    door = [{"door": "the +x doorway", "middle": np.array([2.05, 0.0, 0.0]), "normal": np.array([1.0, 0.0, 0.0])}]
    up = (0.0, 1.0, 0.0)
    for ground, onto_nothing, any_void in ((False, True, True), (True, False, False)):
        scene = room(True, ground)
        found = gates.door_floors(gates.caster(scene), door, up)[0]
        assert found["open_onto_nothing"] is onto_nothing, (ground, found)
        viewed = sight.voids(scene, np.array([[0.0, 1.6, 0.0]]), up)
        assert (viewed["void"] > 0) is any_void, (ground, viewed["void"])
    shut = sight.voids(room(False, False), np.array([[0.0, 1.6, 0.0]]), up)
    assert shut["void"] == 0, shut["void"]


def test_a_picture_drawn_smaller_than_its_frame_is_found_on_the_plan():
    made_plan = json.loads((GROUNDS / "plan" / "moon.json").read_text())
    large = plan.shape(made_plan).heights
    picture = np.full((1024, 1024), float(large.min()))
    inner = ndimage.zoom(large, 870 / large.shape[0], order=1)
    picture[77:77 + 870, 77:77 + 870] = inner  # drawn 0.85 of the frame across, a margin round it
    placed = relief.registration(picture, large, made_plan["side"], made_plan["relief"]["fine"])
    assert abs(placed["scale"] - 0.85) <= 0.021 and placed["correlation"] > 0.9, placed
    assert abs(placed["shift_x"]) < 0.021 and abs(placed["shift_z"]) < 0.021, placed


def test_hills_over_their_plan_fail_and_hills_within_it_pass():
    # The launch's Kowloon hills were made cresting at 526.8 m against the Earth plan's 240 to 495 m (2026-10-12).
    made_plan = json.loads((GROUNDS / "plan" / "earth.json").read_text())
    spec = made_plan["landforms"]["kowloon_hills"]
    grid = landforms.Grid(made_plan["side"], 256)
    gap, _ = landforms.segment_distance(grid.x, grid.z, spec["points"])
    rounding = 600.0 / measures.CODES
    for top, faulty in ((526.8, True), (spec["high"] + 2 * rounding, True), (spec["high"], False), (480.0, False)):
        heights = np.where(gap < 50.0, top, 30.0)
        found = measures.hill_ranges(heights, grid, made_plan, rounding)["kowloon_hills"]
        assert ("fault" in found) is faulty, (top, found)


def test_the_earths_hills_are_made_within_their_plan():
    # The full plan's crest: the builder's 495 m on 28.87 m of plain (4096 points, 2026-10-12), with a flank beside it.
    made_plan = json.loads((GROUNDS / "plan" / "earth.json").read_text())
    spec = made_plan["landforms"]["kowloon_hills"]
    rise, plain = np.array([495.0, 300.0, 0.5]), np.array([28.87, 20.0, 5.0])
    shaped = plan.Shaped(None, plain + rise, None, None, masks={"kowloon_hills": rise.copy()})
    plan.held_crests(shaped, made_plan)
    reach = relief.CLIP * made_plan["relief"]["amplitude"]
    top = float(shaped.heights.max())
    assert spec["low"] <= top and abs(top + reach - spec["high"]) < 1e-6, top  # its relief's clip added stays inside
    assert np.allclose(shaped.heights - shaped.masks["kowloon_hills"], plain), "the plain stays where it was"


def test_a_small_worlds_horizon_dips():
    up, dip = sight.horizon([0.0, 1.7, 0.0], (0.0, 1.0, 0.0), ((0.0, -220.0, 0.0), 220.0))
    assert abs(dip - np.degrees(np.arccos(220.0 / 221.7))) < 1e-9 and np.allclose(up, [0, 1, 0]), dip
    assert sight.horizon([0.0, 1.7, 0.0], (0.0, 1.0, 0.0), None)[1] == 0.0


def test_a_library_surface_added_for_a_model_leaves_terrains_key_alone():
    import shutil
    import tempfile
    from score import graph
    from score.stages import terrain
    from score.store import Store
    root = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "data/ground/plan", root / "ground/plan")
    (root / "library").mkdir()
    shutil.copy2(REPO / "data/library/materials.json", root / "library/materials.json")
    stage = graph.Stage("terrain", "world", None, terrain.GROUNDS, files={"library": terrain.FILES["library"]})
    runner = graph.Runner((stage,), graph.Environment("world1", 1, {"data": str(root)}), Store.in_folder(root / "store"))
    before = runner.file_keys(stage, None)["library"]
    library = json.loads((root / "library/materials.json").read_text())
    library["families"]["plastic"]["variants"]["test_plastic"] = {"recipe": "rubber", "token": "sign-red"}
    (root / "library/materials.json").write_text(json.dumps(library))
    assert runner.file_keys(stage, None)["library"] == before  # a model's surface: no ground reads it
    library["families"]["mars_surface"]["variants"]["mars_regolith"]["token"] = "sign-red"
    (root / "library/materials.json").write_text(json.dumps(library))
    assert runner.file_keys(stage, None)["library"] != before  # a ground's own surface: its key moves
    shutil.rmtree(root)


def test_a_layout_edit_terrain_never_reads_leaves_its_key_alone():
    """Fault (2026-10-12): terrain keyed the whole data/kit, data/scene and data/motion folders, so every light,
    scene-record and machine edit re-keyed the EUR 6 ground and every place's assembly after it."""
    import shutil
    import tempfile
    from score import graph
    from score.stages import terrain
    from score.stages.terrain import inputs
    from score.store import Store
    root = pathlib.Path(tempfile.mkdtemp())
    for folder in ("ground/plan", "scene", "kit", "motion"):
        shutil.copytree(REPO / "data" / folder, root / folder)
    plans = [json.loads(path.read_text()) for path in (root / "ground/plan").glob("*.json")]
    seated = set().union(*({*plan["seats"], *plan.get("judged", [])} for plan in plans))
    assert set().union(*(plan.get("dents", {}) for plan in plans)) <= seated  # dented reads a seated kit only
    files = {name: inputs.FILES[name] for name in ("scenes", "kits", "motion")}
    stage = graph.Stage("terrain", "world", None, terrain.GROUNDS, files=files)
    runner = graph.Runner((stage,), graph.Environment("world1", 1, {"data": str(root)}), Store.in_folder(root / "store"))
    before = runner.file_keys(stage, None)

    def edit(folder, place, change):
        path = root / folder / f"{place}.json"
        record = json.loads(path.read_text())
        change(record)
        path.write_text(json.dumps(record))

    edit("scene", "camp", lambda scene: scene.update(lights=[{"kind": "lamp", "at": [1, 2, 3]}]))
    edit("kit", "camp", lambda kit: kit.update(materials={"any": "thing"}))
    edit("kit", "lab", lambda kit: kit.update(on_seat=[9.0, 9.0]))  # no ground seats the lab (a base module)
    edit("kit", "camp", lambda kit: kit["pieces"].append({"kind": "lamp", "at": [0, 0, 0], "model": "lamp_a"}))
    edit("motion", "launch", lambda motion: motion.setdefault("motions", []).append({"prim": "/launch/Fan", "spin": 1}))
    assert runner.file_keys(stage, None) == before
    edit("kit", "camp", lambda kit: kit.update(on_seat=[1.0, 1.0]))
    edit("scene", "launch", lambda scene: scene.update(places=scene.get("places", []) + [{"name": "x", "stage": "x",
                                                                                           "at": [0, 0, 0]}]))
    after = runner.file_keys(stage, None)
    assert after["kits"] != before["kits"] and after["scenes"] != before["scenes"]  # what terrain reads moves it
    shutil.rmtree(root)


def test_a_remade_ground_asks_one_candidate_and_a_kept_one_takes_all_its_own_free():
    """#21: a ground whose pictures are all kept takes its plan's candidates (none bought); one being remade asks its
    first candidate only, at the seed it always had."""
    import shutil
    import tempfile
    from score.stages import terrain
    jobs =[{"name": f"terrain-{ground}-x-c{candidate}", "ground": ground, "candidate": candidate}
            for ground in ("moon", "mars") for candidate in range(4)]
    kept = pathlib.Path(tempfile.mkdtemp())
    for candidate in range(4):
        (kept / f"terrain-moon-x-c{candidate}.png").write_bytes(b"")
    (kept / "terrain-mars-x-c2.png").write_bytes(b"")  # one of mars's kept: still remade
    asked = terrain.kept_or_first(jobs, kept)
    assert [(job["ground"], job["candidate"]) for job in asked] == [("moon", 0), ("moon", 1), ("moon", 2), ("moon", 3),
                                                                    ("mars", 0)], asked
    shutil.rmtree(kept)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
