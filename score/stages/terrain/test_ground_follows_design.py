"""The terrain stage's invariant: the ground follows the design and its measures find where it does not. A design's
top scene on the Moon at its site and a shed its plan holds stand on one ground, the true sphere (the Moon's radius,
1737.4 km) raised by the plan's terrain spots, drawn in each one's frame; its gates pass, and a ground drawn on the
wrong radius or without the spots fails them; the far landforms and the water the plan marks are laid where the
concept shows them (the 2026-10-26 incidents: the campgrounds' hills and the square's sea had no maker); the sight and
door measures find an opening onto nothing and lose it once ground lies outside, and ground-fit's (fit.py) find a hole
in the ground, an object hanging over it and one on rough ground. Answers are worked by hand (the horizon distance
sqrt(2 r h), the dip acos(r / (r + h)), the spot heights the plan gives).

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26; all again on the one test, 2026-11-13):
- outside.reach: `sqrt(2.0 * radius * HORIZON_EYE)` -> `sqrt(radius * HORIZON_EYE)`.
- design.own_points: `@ found[:, :2].T + found[:, 2]` dropped (a held scene's spots read off its hold, unturned:
  #72, the base's modules turned to meet their tubes).
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
- join.made_pieces: `elif made_one:` -> `elif False:` (a made row the record lays nowhere not named); join.laid_middles
  reading `entry["at"][1]` for along; join.AFTER without scene-record (2026-10-30: ground-join read `at` off
  inventory rows, which never had it).
- outside.under_floor: `points[inside, 1] = np.minimum(...)` -> `pass` (a room's ground through its floor, 2026-10-31:
  the moon rooms' ground stood level with their decks' tops once the decks stood at the floor).
- bounded.spline: `if is_dented(spots): return dented(spots)` dropped (2026-11-12, wreck: its three dent spots fit a
  plane 33.7 degrees steep, 6.5 m ridges round it; clipped, still tilted -0.5 m to -1 m across the place).
- bounded.dented: `(apart - DENT_FLOOR) / (DENT_REACH - DENT_FLOOR)` -> `apart / DENT_REACH` (a cone, no floor:
  wreck's tank leaned on its faces), or `np.clip(..., 0.0, 1.0)` -> its value alone (the dent running on past
  DENT_REACH as a rise).
- bounded.clipped: `np.clip(spline(...), low, high)` -> `spline(...)` (a spline rising past its highest spot).
- bounded.install: `design.spline = spline` -> `pass` (design's own thin-plate spline, wreck's plane again).
"""
import json
import math
import pathlib

import numpy as np
import trimesh

REPO = pathlib.Path(__file__).resolve().parents[3]

from score.stages import terrain
from score.stages.terrain import bounded, design, fit, gates, join, outside, sight

SPOTS = [[10.0, 10.0, 0.0], [30.0, 10.0, 2.0], [20.0, 30.0, -1.0], [20.0, 20.0, 1.0]]
SITE = {"title": "SITE", "w": 40.0, "d": 40.0, "terrain": {"spots": SPOTS}, "structure": ["regolith"],
        "holds": [{"place": "shed", "row": "shed", "x": 4.0, "y": 4.0, "w": 8.0, "d": 6.0}]}
SHED = {"title": "SHED", "w": 8.0, "d": 6.0, "walls": [{"from": [0, 0], "to": [8, 0], "thick": 0.2, "tall": 3.0}]}
ROOM = {"title": "ROOM", "w": 4.0, "d": 4.0}  # a scene no top holds and no site stands
HILLS = {"id": "hills", "terrain": True, "part": "ground", "size": [40.0, 10.0, 5.0], "box": [0, 300, 2000, 400]}
SEA = {"id": "sea", "name": "sea", "noun": "sea", "terrain": True, "part": "backdrop"}
SEA_LEVEL = {"name": "sea", "height": -1.0, "points": [[32, 0], [40, 0], [40, 40], [32, 40]]}




def design_folder(root):
    """A design's kept plans, skies and inventories under `root`: the site on the Moon (environment 1's setting),
    holding the shed, marking hills beyond it and a sea level along its east edge; the room on no ground."""
    from score.review import setting
    for folder in ("plans", "sky", "inventory"):
        (root / folder).mkdir(parents=True)
    for name, plan in (("site", {**SITE, "beyond": ["hills"], "levels": [SEA_LEVEL]}), ("shed", SHED),
                       ("room", ROOM)):
        (root / "plans" / f"{name}.json").write_text(json.dumps(plan))
    sky = {"time": "2099-10-01T14:00:00Z", "setting": setting.checked(setting.now()),  # as scene_sky keeps it
           "site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}}
    for name in ("site", "shed"):
        (root / "sky" / f"{name}.json").write_text(json.dumps({**sky, "place": name, "top": "site"}))
    (root / "inventory/site.json").write_text(json.dumps({"picture": [2000, 1000], "rows": [
        {"id": "regolith", "terrain": True}, HILLS, SEA]}))
    return {"plans": root / "plans", "skies": root / "sky", "inventories": root / "inventory",
            "reference": REPO / "data/physics/bodies.json"}


def box_room(open_door, ground):
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


# (door open, ground outside) -> the doorway opens onto nothing, the eye sees void, the floor's rays find holes;
# None where the row pins nothing
ROOMS = [((True, False), (True, True, True)),
         ((True, True), (False, False, False)),
         ((False, False), (None, False, None))]

# a body's (middle, radius) -> the horizon's dip from an eye 1.7 m up, worked by hand
HORIZONS = [(((0.0, -220.0, 0.0), 220.0), np.degrees(np.arccos(220.0 / 221.7))), (None, 0.0)]

# a 4 x 3 m room (walls, an inside place: its shell lays a deck 0.2 m thick, its top at the floor, out 0.15 m past its
# outline) on flat ground at its floor: the ground under its deck lies at the deck's foot, -0.2 m, the ground round it
# stays at the floor, an open place's ground is left as it is, and a deck cut open over a stair's hatch is several
# pieces: each lowers the ground under it, the hatch none (2026-11-05: terrain stopped, "too many values to unpack",
# once the hangar's deck got its hatch)
FLOOR_ROOM = {"w": 4.0, "d": 3.0, "inside": True, "outline": [[0, 0], [4, 0], [4, 3], [0, 3]],
              "walls": [{"from": [0, 0], "to": [4, 0]}], "levels": []}
HATCH = {"points": [[1.5, 1.0], [2.5, 1.0], [2.5, 2.0], [1.5, 2.0]], "from": -3.0, "to": 0.0}
FLOOR_POINTS = np.array([[0.0, 0.0, 0.0], [1.9, 0.0, 1.4], [2.1, 0.0, 0.0], [2.5, 0.0, 0.0], [0.0, 0.0, 1.8]])
UNDER_DECK = np.array([True, True, True, False, False])  # the points the whole deck stands over
# (row, plan, how many of the points under the deck the ground drops to -0.2 under; every other point stays at 0)
FLOORS = [("deck", FLOOR_ROOM, 3),
          ("open place", {**FLOOR_ROOM, "inside": False, "walls": []}, 0),
          ("deck with a hatch", {**FLOOR_ROOM, "stairs": [HATCH]}, 2)]


def test_ground_follows_design(tmp_path, monkeypatch):
    inputs = design_folder(tmp_path / "design")
    plans = design.kept(inputs["plans"])
    ground = design.layout(plans, design.kept(inputs["skies"]))["moon"]
    out = tmp_path / "out"
    terrain.make({key: str(value) for key, value in inputs.items()}, out, 0, {})

    # one ground for the site and the shed it holds: the true sphere raised by the plan's spots, in each one's frame
    assert set(ground["places"]) == {"site", "shed"} and ground["radius"] == 1737400.0, ground["places"]
    assert design.on_ground("shed", inputs["plans"], inputs["skies"])
    assert not design.on_ground("room", inputs["plans"], inputs["skies"])
    spot = gates.spot_in_frame(ground, "site", 30.0, 10.0)
    assert np.allclose(spot, [10.0, -10.0]), spot  # the site's frame: its plan's middle, x east, z south
    assert abs(design.ground_points(ground, "site", [spot])[0, 1] - 2.0) < 0.01
    shed = design.ground_points(ground, "shed", [[0.0, 0.0]])[0]  # the shed's middle: site plan (8, 7)
    assert abs(shed[1] - design.ground_points(ground, "site", [[-12.0, -13.0]])[0, 1]) < 1e-6, shed
    # a held scene turned 90 degrees reads its own plan's spots through its hold's turn (the base's modules, #72)
    turned = {"place": "shed", "turn": 90, "x": 4.0, "y": 4.0, "w": 6.0, "d": 8.0}
    source = {"to_own": design.to_own(turned, SHED)}
    point = design.place_plan.on_holder(turned, SHED, [1.0, 2.0])
    assert np.allclose(point, [8.0, 5.0]) and np.allclose(design.own_points(source, [point]), [[1.0, 2.0]])
    assert np.allclose(design.on_top(source, [[1.0, 2.0]]), [point])

    # the made layers: every gate passes, each layer a whole asset alone (the USD check's rules)
    assert terrain.grounds_faults(out) == [] and sorted(path.name for path in (out / "moon/places").iterdir()) == \
        ["shed.usdc", "site.usdc"]
    made = json.loads((out / "moon/ground.json").read_text())
    assert made["row"] == "regolith" and made["recipe"] == "regolith" and "airless" in made["recipe_by"]
    for check in terrain.CHECKS:
        verdict = check.judge(out, inputs, {})
        assert verdict.answer == "pass", (verdict.check, verdict.reason)
    from pxr import Usd, UsdPhysics
    from score.stages.complete.usd import judged
    shed_layer = Usd.Stage.Open(str(out / "moon/places/shed.usdc"))  # held: a prim of a stage nobody holds is gone
    near = shed_layer.GetPrimAtPath("/shed/Outside/near")
    assert near.GetAttribute("score:row").Get() == "regolith" and near.GetAttribute("score:surface:missing").Get()
    assert near.GetAttribute("score:ground:recipe").Get() == "regolith"  # the Moon's physics: airless
    for name in ("shed", "site"):
        errors = [issue for issue in judged.issues(judged.opened(out / f"moon/places/{name}.usdc"))
                  if issue["severity"] == "error"]
        assert errors == [], errors

    # a ground drawn without its spots or on the wrong radius fails the gates; the horizon's reach is sqrt(2 r h)
    laid = {place: outside.meshes({**ground, "sources": []}, place) for place in ground["places"]}
    spots, faults = gates.spot_faults(ground, laid)
    assert len(spots) == 4 and len(faults) == 3, faults  # the spot at 0 m stands on the bare sphere anyway
    laid = {place: outside.meshes({**ground, "radius": 220.0 * 1000}, place) for place in ground["places"]}
    _, faults = gates.curve_faults(ground, laid)
    assert len(faults) == 2 and "the body's curve" in faults[0], faults
    assert abs(outside.reach(ground) - math.sqrt(2 * 1737400.0 * outside.HORIZON_EYE)) < 1e-6

    # the spots' relief: wreck's three spots, none above the floor, are dents local to each (its plan's notes: "a 2.5 m
    # dent where it struck", "shallow dents"): each spot's height deep at it, the floor past DENT_REACH, never a plane
    # or one dip; a spline that bends keeps its shape inside its heights, and is clipped past them
    dents = np.array([[11.036, 12.536, -0.5], [8.143, 13.286, -1.0], [19.071, 13.286, -1.0]])
    relief = design.spline({"spots": dents.tolist(), "middle": [10.714, 10.714]})
    grid = np.array([[x / 2, y / 2] for x in range(-30, 74) for y in range(-30, 74)])
    heights = relief(grid)
    apart = np.hypot(grid[:, None, 0] - dents[None, :, 0], grid[:, None, 1] - dents[None, :, 1]).min(axis=1)
    assert np.allclose(relief(dents[:, :2]), dents[:, 2]) and heights.min() >= -1.0 - 1e-9, heights.min()
    assert np.all(heights[apart >= bounded.DENT_REACH] == 0.0) and np.all(heights[apart < 1.0] < -0.1), heights.max()
    down = relief([[19.071 + step, 13.286] for step in (1.2, 1.1, 0.95, 0.5, 0.0)])  # its floor flat, its side
    assert np.allclose(down, [-0.2, -0.6, -1.0, -1.0, -1.0]), down  # straight
    mixed = np.array(SPOTS)
    assert not bounded.is_dented(mixed) and bounded.is_dented(-np.abs(mixed))
    beyond = bounded.shaped(mixed)([[x, y] for x in range(-60, 100, 4) for y in range(-60, 100, 4)])
    assert beyond.min() >= -1.0 and beyond.max() <= 2.0 and np.allclose(bounded.shaped(mixed)(mixed[:, :2]),
                                                                        mixed[:, 2], atol=0.01), beyond

    # the hills the plan marks beyond (2026-10-26: the campgrounds' distant hills had no maker): a ring of landforms at
    # the horizon, as tall as its box rises in the concept; the near ground and the far edge stay as they were
    assert design.far_row(HILLS, {"hills"}) and not design.far_row(HILLS, set())
    far = made["far"]
    distance = math.sqrt(2 * 1737400.0 * design.EYE)  # the Moon's horizon from a person's eye
    height = distance * 100 / (1000 / math.tan(math.radians(40)))  # its 100 px rise in an 80 degree view
    assert [row["row"] for row in far] == ["hills"] and abs(far[0]["distance"] - distance) < 0.1
    assert abs(far[0]["height"] - height) < 0.1 and far[0]["broad"] == round(height * 4, 1), far
    relief = design.far_reliefs(ground, plans, inputs["inventories"], 6000.0)[0][0][1]
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

    # the sea (2026-10-26: the square's sea had no maker): a sheet at its plan level on the body's curve where the
    # ground, lowered SEABED under that line inside its level, lies under it; past the outline it runs along its
    # concept box's bearings to its shore
    assert design.water_row(SEA) and not design.water_row({**SEA, "terrain": False})
    assert design.water_level(json.loads((inputs["plans"] / "site.json").read_text()), SEA) == \
        (-1.0, SEA_LEVEL["points"])
    assert [(entry["place"], entry["row"], entry["level"]) for entry in made["water"]] == [("site", "sea", -1.0)]
    site_layer = Usd.Stage.Open(str(out / "moon/places/site.usdc"))
    water = site_layer.GetPrimAtPath("/site/Outside/water")
    assert water.GetAttribute("score:kind").Get() == "water" and water.GetAttribute("score:row").Get() == "sea"
    assert water.GetAttribute("score:ground:recipe").Get() == "ocean" and not water.HasAPI(UsdPhysics.CollisionAPI)
    spot = gates.spot_in_frame(ground, "site", 36.0, 20.0)
    sheets, _ = design.waters(ground, plans, inputs["inventories"], 6000.0)
    lowered = design.ground_points(ground, "site", [spot], design.reliefs(ground) + [sheets[0][:2]])[0, 1]
    points = np.asarray(water.GetAttribute("points").Get())
    assert lowered < -1.0 and abs(points[np.argmin(np.hypot(*(points[:, [0, 2]] - spot).T)), 1] + 1.0) < 0.05
    region = design.water_region({"w": 40.0, "d": 40.0}, None, (-0.2, 0.2, ways), 100.0)
    assert list(region([[20.0, -30.0], [20.0, 10.0], [20.0, -90.0], [60.0, -30.0]])) == [True, False, False, False]

    # the sight, door and hole measures find an opening onto nothing and lose it once ground lies outside
    up = (0.0, 1.0, 0.0)
    door = gates.record_doors({"doorways": [{"name": "door-1", "middle": [2.05, 0.0, 0.0],
                                             "inward": [-1.0, 0.0, 0.0]}]})
    for (open_door, outside_ground), (onto_nothing, any_void, holes) in ROOMS:
        scene = box_room(open_door, outside_ground)
        row = (open_door, outside_ground)
        viewed = sight.voids(scene, np.array([[0.0, 1.6, 0.0]]), up)
        assert (viewed["void"] > 0) is any_void, (row, viewed["void"])
        if onto_nothing is not None:
            found = gates.door_floors(gates.caster(scene), door, up)[0]
            assert found["open_onto_nothing"] is onto_nothing, (row, found)
        if holes is not None:
            found = fit.measure_continuous(gates.caster(scene), {"floor": [[-2.0, -2.0], [2.0, 2.0]]}, 10.0)
            assert (found["holes"] > 0) is holes and found["rays"] > 400, (row, found)
    for body, dip in HORIZONS:
        turned_up, found = sight.horizon([0.0, 1.7, 0.0], up, body)
        assert abs(found - dip) < 1e-9 and np.allclose(turned_up, [0, 1, 0]), (body, found)

    # ground-fit: an object hanging over the ground floats, one on rough ground is named, one high on a wall is neither
    boxes = {"crate_1": (np.array([0.0, 0.12, 0.0]), np.array([1.0, 1.0, 1.0])),
             "rock_1": (np.array([3.0, 0.01, 0.0]), np.array([4.0, 0.5, 1.0])),
             "lamp_1": (np.array([5.0, 2.4, 0.0]), np.array([5.2, 2.6, 0.2])),
             "tank_1": (np.array([7.0, 0.0, 0.0]), np.array([8.0, 1.0, 1.0]))}
    found = fit.measure_standing(boxes, lambda low, high: np.linspace(-0.3, 0.0, 9) if low[0] == 7.0 else np.zeros(9))
    assert found["standing"] == 3 and len(found["floating"]) == 1 and found["floating"][0].startswith("crate_1")
    assert len(found["rough"]) == 1 and found["rough"][0].startswith("tank_1"), found

    # the ground runs under a room's floor (rows above)
    for name, plan, dropped in FLOORS:
        under = outside.under_floor(FLOOR_POINTS, plan)
        low = np.isclose(under[:, 1], -0.2)
        assert np.all(low | np.isclose(under[:, 1], 0.0)) and np.allclose(under[:, [0, 2]], FLOOR_POINTS[:, [0, 2]])
        assert np.all(low <= UNDER_DECK) and low.sum() == dropped, (name, under)

    # ground-join: a made terrain row stands at its scene record object's (x, z), its first piece's; one the record
    # lays nowhere is left to the code ground with why, never a KeyError (inventory rows carry no `at`)
    model = tmp_path / "rock.gltf"
    model.write_text("{}")
    made_rows = {row: {"route": "prop", "model": str(model), "finishes": []} for row in ("rock_1", "crater")}
    monkeypatch.setattr(join.made, "made", lambda inputs, layer: made_rows)
    record = {"objects": [{"name": "rock_1_1", "row": "rock_1", "at": [-8.4, 0.0, 6.1]},
                          {"name": "rock_1_2", "row": "rock_1", "at": [3.0, 0.0, 3.0]}, {"name": "lamp", "at": [0, 0, 0]}]}
    inventory = {"rows": [{"id": "rock_1", "size": [0.3, 0.2, 0.1]}, {"id": "crater", "size": [4.0, 4.0, 1.0]}]}
    left, pieces = join.made_pieces({}, inventory, join.laid_middles(record))
    assert [(row["id"], middle) for row, _, _, middle in pieces] == [("rock_1", (-8.4, 6.1))]
    assert list(left) == ["crater"] and "nowhere" in left["crater"]
    assert join.AFTER["scene-record"] == ("scene-record", 1)
