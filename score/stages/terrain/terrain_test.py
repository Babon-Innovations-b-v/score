"""The terrain stage's own checks, with no spend: a design's top scene on the Moon at its site and a shed its plan
holds stand on one ground, the true sphere raised by the plan's terrain spots, drawn in each one's frame; its gates
pass, and a ground drawn on the wrong radius or without the spots fails them; the sight and door measures find an
opening onto nothing and lose it once ground lies outside, and ground-fit's (fit.py) find a hole in the ground, an
object hanging over it and one on rough ground.

Run: .venv/bin/python score/stages/terrain/terrain_test.py
"""
import json
import math
import pathlib
import shutil
import sys
import tempfile

import numpy as np
import trimesh

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages import terrain  # noqa: E402
from score.stages.terrain import design, fit, gates, outside, sight  # noqa: E402

SPOTS = [[10.0, 10.0, 0.0], [30.0, 10.0, 2.0], [20.0, 30.0, -1.0], [20.0, 20.0, 1.0]]
SITE = {"title": "SITE", "w": 40.0, "d": 40.0, "terrain": {"spots": SPOTS}, "structure": ["regolith"],
        "holds": [{"place": "shed", "row": "shed", "x": 4.0, "y": 4.0, "w": 8.0, "d": 6.0}]}
SHED = {"title": "SHED", "w": 8.0, "d": 6.0, "walls": [{"from": [0, 0], "to": [8, 0], "thick": 0.2, "tall": 3.0}]}
ROOM = {"title": "ROOM", "w": 4.0, "d": 4.0}  # a scene no top holds and no site stands


def design_folder(root):
    """A design's kept plans, skies and inventories under `root`: the site on the Moon (environment 1's setting),
    holding the shed; the room on no ground."""
    from score.review import setting
    for folder in ("plans", "sky", "inventory"):
        (root / folder).mkdir(parents=True)
    for name, plan in (("site", SITE), ("shed", SHED), ("room", ROOM)):
        (root / "plans" / f"{name}.json").write_text(json.dumps(plan))
    sky = {"time": "2099-10-01T14:00:00Z", "setting": setting.checked(setting.now()),  # as scene_sky keeps it
           "site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}}
    for name in ("site", "shed"):
        (root / "sky" / f"{name}.json").write_text(json.dumps({**sky, "place": name, "top": "site"}))
    (root / "inventory/site.json").write_text(json.dumps({"rows": [{"id": "regolith", "terrain": True}]}))
    return {"plans": root / "plans", "skies": root / "sky", "inventories": root / "inventory",
            "reference": REPO / "data/physics/bodies.json"}


def test_a_designs_ground_stands_its_scenes_on_the_true_sphere_with_its_spots():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        inputs = design_folder(root / "design")
        ground = design.layout(design.kept(inputs["plans"]), design.kept(inputs["skies"]))["moon"]
        assert set(ground["places"]) == {"site", "shed"} and ground["radius"] == 1737400.0, ground["places"]
        assert design.on_ground("shed", inputs["plans"], inputs["skies"])
        assert not design.on_ground("room", inputs["plans"], inputs["skies"])
        spot = gates.spot_in_frame(ground, "site", 30.0, 10.0)
        assert np.allclose(spot, [10.0, -10.0]), spot  # the site's frame: its plan's middle, x east, z south
        assert abs(design.ground_points(ground, "site", [spot])[0, 1] - 2.0) < 0.01
        shed = design.ground_points(ground, "shed", [[0.0, 0.0]])[0]  # the shed's middle: site plan (8, 7)
        assert abs(shed[1] - design.ground_points(ground, "site", [[-12.0, -13.0]])[0, 1]) < 1e-6, shed
        out = root / "out"
        terrain.make({key: str(value) for key, value in inputs.items()}, out, 0, {})
        assert terrain.grounds_faults(out) == [] and sorted(path.name for path in (out / "moon/places").iterdir()) == \
            ["shed.usdc", "site.usdc"]
        made = json.loads((out / "moon/ground.json").read_text())
        assert made["row"] == "regolith" and made["recipe"] == "regolith" and "airless" in made["recipe_by"]
        for check in terrain.CHECKS:
            verdict = check.judge(out, inputs, {})
            assert verdict.answer == "pass", (verdict.check, verdict.reason)
        from pxr import Usd
        layer = Usd.Stage.Open(str(out / "moon/places/shed.usdc"))  # held: a prim of a stage nobody holds is gone
        near = layer.GetPrimAtPath("/shed/Outside/near")
        assert near.GetAttribute("score:row").Get() == "regolith" and near.GetAttribute("score:surface:missing").Get()
        assert near.GetAttribute("score:ground:recipe").Get() == "regolith"  # the Moon's physics: airless
    finally:
        shutil.rmtree(root)


def test_a_ground_on_the_wrong_radius_or_without_its_spots_fails():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        inputs = design_folder(root / "design")
        ground = design.layout(design.kept(inputs["plans"]), design.kept(inputs["skies"]))["moon"]
        flat = {**ground, "sources": []}
        laid = {place: outside.meshes(flat, place) for place in ground["places"]}
        spots, faults = gates.spot_faults(ground, laid)
        assert len(spots) == 4 and len(faults) == 3, faults  # the spot at 0 m stands on the bare sphere anyway
        small = {**ground, "radius": 220.0 * 1000}
        laid = {place: outside.meshes(small, place) for place in ground["places"]}
        _, faults = gates.curve_faults(ground, laid)
        assert len(faults) == 2 and "the body's curve" in faults[0], faults
        far = outside.reach(ground)
        assert abs(far - math.sqrt(2 * 1737400.0 * outside.HORIZON_EYE)) < 1e-6, far
    finally:
        shutil.rmtree(root)


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
    record = {"doorways": [{"name": "door-1", "middle": [2.05, 0.0, 0.0], "inward": [-1.0, 0.0, 0.0]}]}
    door = gates.record_doors(record)
    up = (0.0, 1.0, 0.0)
    for ground, onto_nothing, any_void in ((False, True, True), (True, False, False)):
        scene = room(True, ground)
        found = gates.door_floors(gates.caster(scene), door, up)[0]
        assert found["open_onto_nothing"] is onto_nothing, (ground, found)
        viewed = sight.voids(scene, np.array([[0.0, 1.6, 0.0]]), up)
        assert (viewed["void"] > 0) is any_void, (ground, viewed["void"])
    shut = sight.voids(room(False, False), np.array([[0.0, 1.6, 0.0]]), up)
    assert shut["void"] == 0, shut["void"]


def test_a_hole_in_the_ground_is_found_and_ground_all_round_clears_it():
    record = {"floor": [[-2.0, -2.0], [2.0, 2.0]]}
    for ground, holes in ((False, True), (True, False)):
        found = fit.measure_continuous(gates.caster(room(True, ground)), record, 10.0)
        assert (found["holes"] > 0) is holes and found["rays"] > 400, (ground, found)


def test_an_object_hanging_over_the_ground_floats_one_on_rough_ground_is_named_and_one_high_on_a_wall_is_neither():
    boxes = {"crate_1": (np.array([0.0, 0.12, 0.0]), np.array([1.0, 1.0, 1.0])),
             "rock_1": (np.array([3.0, 0.01, 0.0]), np.array([4.0, 0.5, 1.0])),
             "lamp_1": (np.array([5.0, 2.4, 0.0]), np.array([5.2, 2.6, 0.2])),
             "tank_1": (np.array([7.0, 0.0, 0.0]), np.array([8.0, 1.0, 1.0]))}

    def under(low, high):
        return np.linspace(-0.3, 0.0, 9) if low[0] == 7.0 else np.zeros(9)
    found = fit.measure_standing(boxes, under)
    assert found["standing"] == 3 and len(found["floating"]) == 1 and found["floating"][0].startswith("crate_1")
    assert len(found["rough"]) == 1 and found["rough"][0].startswith("tank_1"), found


def test_a_small_worlds_horizon_dips():
    up, dip = sight.horizon([0.0, 1.7, 0.0], (0.0, 1.0, 0.0), ((0.0, -220.0, 0.0), 220.0))
    assert abs(dip - np.degrees(np.arccos(220.0 / 221.7))) < 1e-9 and np.allclose(up, [0, 1, 0]), dip
    assert sight.horizon([0.0, 1.7, 0.0], (0.0, 1.0, 0.0), None)[1] == 0.0


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
