"""The terrain stage's invariant: the ground follows the design and its measures find where it does not. A design's
top scene on the Moon at its site and a shed its plan holds stand on one ground, the true sphere (the Moon's radius,
1737.4 km) raised by the plan's terrain spots, drawn in each one's frame; its gates pass, and a ground drawn on the
wrong radius or without the spots fails them; the far landforms and the water the plan marks are laid where the
concept shows them (the 2026-10-26 incidents: the campgrounds' hills and the square's sea had no maker); the sight and
door measures find an opening onto nothing and lose it once ground lies outside, and ground-fit's (fit.py) find a hole
in the ground, an object hanging over it and one on rough ground. Answers are worked by hand (the horizon distance
sqrt(2 r h), the dip acos(r / (r + h)), the spot heights the plan gives).

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- outside.reach: `sqrt(2.0 * radius * HORIZON_EYE)` -> `sqrt(radius * HORIZON_EYE)`.
- design.layout: a held scene's offset `[hold["x"], hold["y"]]` -> `[0.0, 0.0]` (the shed off its hold).
- gates.spot_faults: drop `or off > SPOT_WITHIN` (a ground without its spots passes).
- gates.curve_faults: `wanted = 0.0` (the body's curve no longer wanted).
- fit.measure_standing: `gap > FEET` -> `gap > 1.0` (a hanging crate not floating); the rough check `if False`.
- fit.measure_continuous: `~np.isfinite(...)` -> `np.isnan(...)` (holes not found).
- sight.horizon: `arccos` -> `arcsin`.
- design.far_row: drop `and row["id"] in beyond`.
- design.water_level: the level's height -> 0.0.
- outside.write_mesh: `points` written whole, its extent the used ones' (the far grid's middle: ExtentsChecker).
- terrain.write_layer: `layer.Save()` unstamped (StageMetadataChecker, DefaultPrimChecker).
- outside.write: an inactive over of /<place>/Ground again (DanglingOverPrimChecker: no base drawn from a design has
  it, 9c7466b1).
"""
import json
import math
import pathlib

import numpy as np
import trimesh

REPO = pathlib.Path(__file__).resolve().parents[3]

from score.stages import terrain
from score.stages.terrain import design, fit, gates, outside, sight

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


def test_a_designs_ground_stands_its_scenes_on_the_true_sphere_with_its_spots(tmp_path):
    root = tmp_path
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
    from score.stages.complete.usd import judged
    for name in ("shed", "site"):  # each layer a whole asset alone, as the library takes it (the USD check's rules)
        errors = [issue for issue in judged.issues(judged.opened(out / f"moon/places/{name}.usdc"))
                  if issue["severity"] == "error"]
        assert errors == [], errors


def test_a_ground_on_the_wrong_radius_or_without_its_spots_fails(tmp_path):
    root = tmp_path
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


def test_a_far_landform_beyond_the_place_is_raised_over_its_bearings_and_its_curve_still_holds(tmp_path):
    root = tmp_path
    """2026-10-26: the campgrounds' distant hills had no maker. A terrain row of the ground the plan marks beyond is
    a ring of landforms at the horizon, as tall as its box rises in the concept; the near ground and the far edge
    stay as they were."""
    inputs = design_folder(root / "design")
    (inputs["plans"] / "site.json").write_text(json.dumps({**SITE, "beyond": ["hills"]}))
    hills = {"id": "hills", "terrain": True, "part": "ground", "size": [40.0, 10.0, 5.0],
             "box": [0, 300, 2000, 400]}
    (inputs["inventories"] / "site.json").write_text(json.dumps({"picture": [2000, 1000], "rows": [
        {"id": "regolith", "terrain": True}, hills]}))
    assert design.far_row(hills, {"hills"}) and not design.far_row(hills, set())
    out = root / "out"
    terrain.make({key: str(value) for key, value in inputs.items()}, out, 0, {})
    far = json.loads((out / "moon/ground.json").read_text())["far"]
    distance = math.sqrt(2 * 1737400.0 * design.EYE)  # the Moon's horizon from a person's eye
    height = distance * 100 / (1000 / math.tan(math.radians(40)))  # its 100 px rise in an 80 degree view
    assert [row["row"] for row in far] == ["hills"] and abs(far[0]["distance"] - distance) < 0.1
    assert abs(far[0]["height"] - height) < 0.1 and far[0]["broad"] == round(height * 4, 1), far
    ground = design.layout(design.kept(inputs["plans"]), design.kept(inputs["skies"]))["moon"]
    shaped, _ = design.far_reliefs(ground, design.kept(inputs["plans"]), inputs["inventories"], 6000.0)
    relief = shaped[0][1]
    out_there = relief([[20.0 + distance * math.cos(turn), 20.0 + distance * math.sin(turn)]
                        for turn in np.linspace(0, 2 * math.pi, 90)])
    assert out_there.min() >= 0.4 * height - 1e-6 and out_there.max() <= height + 1e-6 and np.ptp(out_there) > 1.0
    assert relief([[20.0, 20.0], [20.0 + distance + far[0]["broad"] + 1.0, 20.0]]).max() == 0.0
    assert far[0]["bearings"] is None  # no heading to place its bearings: all round
    ways = (np.array([0.0, -1.0]), np.array([1.0, 0.0]))  # the concept looks north
    ahead, behind = [20.0, 20.0 - distance], [20.0, 20.0 + distance]
    shown = design.far_ring([20.0, 20.0], distance, height, 100.0, 7, (-0.3, 0.3, ways))
    assert shown([ahead])[0] >= 0.4 * height - 1e-6 and shown([behind])[0] == 0.0
    assert shown([[20.0 + distance * math.sin(0.3 + 101.0 / distance), 20.0 - distance * math.cos(
        0.3 + 101.0 / distance)]])[0] == 0.0  # faded out a breadth past its bearings
    whole = design.far_ring([20.0, 20.0], distance, height, 100.0, 7, (-math.pi, math.pi, ways))
    assert np.allclose(whole([ahead, behind]), design.far_ring([20.0, 20.0], distance, height, 100.0, 7)(
        [ahead, behind]))  # a concept that shows it all round: the full ring
    for check in terrain.CHECKS:
        verdict = check.judge(out, inputs, {})
        assert verdict.answer == "pass", (verdict.check, verdict.reason)


def test_a_body_of_water_lies_at_its_level_over_the_ground_lowered_under_it(tmp_path):
    root = tmp_path
    """2026-10-26: the square's sea had no maker. A terrain row whose words name water is laid at its plan level as a
    sheet on the body's curve where the ground, lowered SEABED under that line inside its level, lies under it; out
    past the outline it runs along its concept box's bearings to its shore; the gates still pass."""
    inputs = design_folder(root / "design")
    sea_level = {"name": "sea", "height": -1.0, "points": [[32, 0], [40, 0], [40, 40], [32, 40]]}
    (inputs["plans"] / "site.json").write_text(json.dumps({**SITE, "levels": [sea_level]}))
    sea = {"id": "sea", "name": "sea", "noun": "sea", "terrain": True, "part": "backdrop"}
    (inputs["inventories"] / "site.json").write_text(json.dumps({"rows": [{"id": "regolith", "terrain": True},
                                                                         sea]}))
    assert design.water_row(sea) and not design.water_row({**sea, "terrain": False})
    assert design.water_level(json.loads((inputs["plans"] / "site.json").read_text()), sea) == \
        (-1.0, sea_level["points"])
    out = root / "out"
    terrain.make({key: str(value) for key, value in inputs.items()}, out, 0, {})
    laid = json.loads((out / "moon/ground.json").read_text())["water"]
    assert [(entry["place"], entry["row"], entry["level"]) for entry in laid] == [("site", "sea", -1.0)], laid
    from pxr import Usd, UsdPhysics
    stage = Usd.Stage.Open(str(out / "moon/places/site.usdc"))
    water = stage.GetPrimAtPath("/site/Outside/water")
    assert water.GetAttribute("score:kind").Get() == "water" and water.GetAttribute("score:row").Get() == "sea"
    assert water.GetAttribute("score:ground:recipe").Get() == "ocean" and not water.HasAPI(UsdPhysics.CollisionAPI)
    ground = design.layout(design.kept(inputs["plans"]), design.kept(inputs["skies"]))["moon"]
    spot = gates.spot_in_frame(ground, "site", 36.0, 20.0)
    sheets, _ = design.waters(ground, design.kept(inputs["plans"]), inputs["inventories"], 6000.0)
    lowered = design.ground_points(ground, "site", [spot], design.reliefs(ground) + [sheets[0][:2]])[0, 1]
    points = np.asarray(water.GetAttribute("points").Get())
    assert lowered < -1.0 and abs(points[np.argmin(np.hypot(*(points[:, [0, 2]] - spot).T)), 1] + 1.0) < 0.05
    for check in terrain.CHECKS:
        verdict = check.judge(out, inputs, {})
        assert verdict.answer == "pass", (verdict.check, verdict.reason)
    region = design.water_region({"w": 40.0, "d": 40.0}, None, (-0.2, 0.2, (np.array([0.0, -1.0]),
                                                                          np.array([1.0, 0.0]))), 100.0)
    assert list(region([[20.0, -30.0], [20.0, 10.0], [20.0, -90.0], [60.0, -30.0]])) == [True, False, False,
                                                                                       False]

