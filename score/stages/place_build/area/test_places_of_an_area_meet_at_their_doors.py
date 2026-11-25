"""Invariant: places of one area meet at their doors. A flat held beside a one-storey stair core (`stairs --joined 1`,
its flat door's doorway recorded as it is laid) is seated by its door leaf onto that doorway, its floor at the plans'
storey height (3 m), the stairwell (no door joins it to a seated place) standing where the town's plan holds it,
and a walker goes from the landing through the doorway into the flat; while the same flat is
told by name when the core keeps the hall stub behind that door (no walker's way), when the plans put the flat's floor
a storey higher than the doorway it is joined at (3 m apart), when the flat's leaf in its frame is 1.2 m wide in the
core's 1.02 m doorway, and when the flat joins no doorway back (no doorway joined). A flat the town's plan holds far
from the stairwell its door leads to is still joined and seated by the built doorways, the plan told; a flat given to
stand stands as laid at its plan's storey and the stairwell is seated onto it at its own floor. A stairwell whose own
plan holds the flat (the area's outside, as the pad holds its capsule) seats the flat onto its door the same way, the
stairwell itself the area's frame, and each place's piece list keeps its own light and exposure (the flat's bulb at
its own watts, its own 2, though the stairwell is drawn at 0.5). Each seat written into its place.json is where the package
lays the place: the flat's front door packaged on the stairwell's doorway, the seat carried in its scene.json, its
scene file unseated. A block of the
flat's own standing in the stairwell's core is told (seated shells may not stand inside each other); listed as the
flat's backdrop (a neighbour place stands for it) it is no shell of the flat and its package leaves it out; such a
backdrop block standing across the way in from the flat's door walls no walker off (the game leaves it out).

Breaks that turn this red (each applied once and seen red, then reverted):
- area.seat_onto: `rise` left out of the seat's height -> the flat sits at the street's level, 3 m under its doorway
- area.seat_onto: `target` taken as the doorway's own inward (not its opposite) -> the flat is seated facing away,
  inside the stairwell, and the way is told off facing
- stair_core.structure: the `joined` storey's hall stub kept -> the meeting pair has no walker's way
- area.built_joins: a plan door with no joined doorway skipped silently -> the flat with no join back passes
- area.wider: ready.FIT taken as 0.5 m -> the 1.2 m leaf passes in the 1.02 m doorway
- area.planned_joins: a pair the holder's plan holds apart left out (`met` alone) -> the far flat is never joined
- area.with_holder: the outside left out of the joined places -> the flat its stairwell holds stands at the
  stairwell's floor, never seated onto its door 3 m up
- area.held_seat: the identity seat (as laid) for a place the outside's plan holds -> the stairwell stands on the
  town's middle, not at its hold 8 m west and 8.5 m north
- area.seated: `stands` unread (lowest first) -> the stairwell stands as laid and the flat given to stand is seated
- scene_package.seated: the seat left off the package -> the packaged front door stands at the flat's own spot
- scene_package.environment_of: the Environment's score:exposure unread -> the flat's piece list says 1, not its
  own 2
- area.area: shells_crossed unread -> the flat's block standing in the stairwell's core passes
- scene_package.written_scene: the seat left out of scene.json -> the package carries no seat to lay its film path on
  (an engine's camera stands where the place stood unseated, #222 run 9)
- scene_package.written_scene: the backdrop packaged when seated -> the flat's block is packaged beside its front door
- area.joined_stage: the backdrop laid on the join's stage -> the backdrop block across the flat's way in walls it off
"""
import json
import math

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, UsdGeom

from score.stages import place_build
from score.stages.place_build import area


def plans(folder, sill, apart, outside):
    """The area's kept plans: the town holds the stairwell and, `apart` metres south of it, the flat; the stairwell's
    flat door `sill` metres up meets the flat's front door on the town's plan when they are not apart. With the
    stairwell `outside`, its own plan holds the flat beyond its door."""
    folder.mkdir()
    door = {"kind": "door", "wide": 1.0, "angle": 0.0, "swing": "right", "head": 2.2}
    written = {
        "town": {"w": 20.0, "d": 20.0, "holds": [{"place": "stairwell", "x": 0.0, "y": 0.0, "w": 4.0, "d": 3.0},
                                                 {"place": "flat", "x": 0.0, "y": 3.0 + apart, "w": 4.0, "d": 4.0}]},
        "stairwell": {"w": 4.0, "d": 3.0, "openings": [{**door, "at": [1.0, 3.0], "sill": sill, "to": "flat"}]},
        "flat": {"w": 4.0, "d": 4.0, "openings": [{**door, "at": [1.0, 0.0], "sill": 0.0, "to": "stairwell"}]}}
    if outside == "stairwell":
        written["stairwell"]["holds"] = [{"place": "flat", "x": 0.0, "y": 3.0, "w": 4.0, "d": 4.0}]
    for name, body in written.items():
        (folder / f"{name}.json").write_text(json.dumps(body))
    return folder


def started(folder, place):
    folder.mkdir()
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", place, concept)
    return folder / "place"


def box(stage, place, name, size, low, role):
    """An object of one cube `size` whose lowest corner is `low`, of `role`."""
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
    cube = UsdGeom.Cube.Define(stage, f"/{place}/Objects/{name}/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    holder.GetPrim().CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set(role)
    return holder.GetPrim()


def stairwell(folder, joined):
    """A one-storey stair core, its flat door (core_door1, 3 m up) joined to the flat."""
    folder = started(folder, "stairwell")
    place_build.stairs(folder, "core", storeys=1, one_block=True, joined=joined)
    area.join(folder, "core_door1", "flat")
    return folder


def flat(folder, joined_back, wide, backdrop, block):
    """A room 4 x 4 m on its own floor at 0, its front door's leaf `wide` metres (marked to open) on its north edge,
    and its concept's `block` (low corner, size): beyond that door beside the way in, where the stairwell is seated,
    or across the way in; listed as its backdrop (a neighbour place stands for it) when `backdrop`."""
    folder = started(folder, "flat")
    stage, place = place_build.opened(folder)
    box(stage, place, "floor", (4.0, 0.2, 4.1), (-2.0, -0.2, -4.0), "structure")
    leaf = box(stage, place, "front_door", (wide, 2.05, 0.05), (-wide / 2, 0.0, -0.05), "door")
    leaf.CreateAttribute("score:opens", Sdf.ValueTypeNames.Bool).Set(True)
    box(stage, place, "block", block[1], block[0], "structure")
    stage.GetRootLayer().Save()
    if backdrop:
        place_build.backdrop(folder, "block")
    if joined_back:
        area.join(folder, "front_door", "stairwell", inward=(0.0, -1.0))
    return folder


BLOCK = ((1.0, -0.5, 0.2), (3.0, 3.5, 4.0))  # the flat's concept block (low corner, size): in the core, off the way
ACROSS = ((-2.0, 0.0, -1.3), (4.0, 2.5, 0.3))  # the flat's concept block across its way in, 1 m in from its door


ROWS = [  # (case, the core's joined storeys, the stairwell's flat door sill on the plans, the flat joins back, its
    # leaf's width, metres the town's plan holds the flat apart, the place given to stand, the flat's block its
    # backdrop and where it stands, the area's outside, told)
    ("they meet", [1], 3.0, True, 0.96, 0.0, None, True, "town", None),
    ("the flat's backdrop stands across its way in", [1], 3.0, True, 0.96, 0.0, None, True, "town", None),
    ("the flat stands as laid", [1], 3.0, True, 0.96, 0.0, "flat", True, "town", "stands"),
    ("the stairwell holds the flat", [1], 3.0, True, 0.96, 0.0, None, True, "stairwell", "holder"),
    ("the town's plan holds the flat apart", [1], 3.0, True, 0.96, 6.0, None, True, "town",
     "6.00 m from stairwell's door back"),
    ("the hall stub walls the flat off", [], 3.0, True, 0.96, 0.0, None, True, "town", "no walker's way"),
    ("the plans put the flat a storey higher", [1], 6.0, True, 0.96, 0.0, None, True, "town", "3.00 m apart"),
    ("the flat's leaf is wider than the doorway", [1], 3.0, True, 1.2, 0.0, None, True, "town",
     "1.20 m wide, stairwell's core_door1"),
    ("the flat joins no doorway back", [1], 3.0, False, 0.96, 0.0, None, True, "town",
     "has no doorway joined to stairwell"),
    ("the flat's block stands in the stairwell", [1], 3.0, True, 0.96, 0.0, None, False, "town",
     "flat's block and stairwell's core stand"),
]


@pytest.mark.parametrize("case, joined, sill, joined_back, wide, apart, stands, backdrop, outside, told", ROWS,
                         ids=[row[0] for row in ROWS])
def test_places_of_an_area_meet_at_their_doors(tmp_path, case, joined, sill, joined_back, wide, apart, stands,
                                               backdrop, outside, told):
    from score.stages.place_build import scene_package
    block = ACROSS if "across its way in" in case else BLOCK
    folders = {"stairwell": stairwell(tmp_path / "stairwell", joined),
               "flat": flat(tmp_path / "flat", joined_back, wide, backdrop, block)}
    if told == "holder":  # the outside drawn at 0.5, the flat at 2 by a 100 W bulb
        moon = {"elevation": 38.0, "heading": 112.0, "strength": 0.04, "colour": [0.5, 0.6, 1.0]}
        place_build.night(folders["stairwell"], [0.01, 0.02, 0.04], [0.0, 0.0, 0.01], 0.5, moon)
        place_build.night(folders["flat"], [0.01, 0.02, 0.04], [0.0, 0.0, 0.01], 2.0, moon)
        place_build.light(folders["flat"], "bulb", at=(0.0, 2.5, 0.0), watts=100)
    record = area.area(plans(tmp_path / "plans", sill, apart, outside), outside, folders, tmp_path / "seats.json",
                       seat=True, stands=stands)
    if told == "holder":
        seats = {name: np.asarray(record["seats"][name]["matrix"]).reshape(4, 4) for name in folders}
        assert np.allclose(seats["stairwell"], np.eye(4)) and record["faults"] == [], (seats, record["faults"])
        assert "on stairwell's doorway" in record["seats"]["flat"]["from"] and abs(seats["flat"][3, 1] - 3.0) < 1e-6, \
            record["seats"]
        assert record["joins"][0]["walked"] > 1.5, record["joins"]
        from score.stages.place_build import pieces
        lit = pieces.write(folders["flat"], tmp_path / "flat_pieces")  # its own light, though seated at 0.5's
        [bulb] = [lamp for lamp in lit["lamps"] if lamp["name"] == "bulb"]
        assert "exposure" not in place_build.record_of(folders["flat"])["seat"] \
            and abs(bulb["watts"] - 100.0 * math.pi) < 1e-3 and lit["environment"]["exposure"] == 2.0 \
            and "relit" not in lit["environment"], (bulb, lit["environment"])
    elif told == "stands":
        assert "on flat's doorway" in record["seats"]["stairwell"]["from"], record["seats"]
        seats = {name: np.asarray(record["seats"][name]["matrix"]).reshape(4, 4) for name in folders}
        assert np.allclose(seats["flat"][:3, :3], np.eye(3)) and abs(seats["flat"][3, 1] - 3.0) < 1e-6, seats
        assert abs(seats["stairwell"][3, 1]) < 1e-6 and record["faults"] == [], (seats, record["faults"])
    elif told is None:
        assert record["faults"] == [], record["faults"]
        seat = np.asarray(record["seats"]["flat"]["matrix"]).reshape(4, 4)
        door = place_build.record_of(folders["stairwell"])["doorways"]["core_door1"]
        stair = np.asarray(record["seats"]["stairwell"]["matrix"]).reshape(4, 4)
        assert np.allclose(stair[:3, :3], np.eye(3)) and np.allclose(stair[3, :3], [-8.0, 0.0, -8.5]), stair
        door = {**door, "middle": np.asarray(door["middle"]) @ stair[:3, :3] + stair[3, :3]}  # where the town holds it
        assert abs(seat[3, 1] - 3.0) < 1e-6, seat
        assert np.allclose(seat[:3, :3].T @ [0.0, 0.0, -1.0], [0.0, 0.0, 1.0], atol=1e-6), seat
        assert record["joins"][0]["walked"] > 1.5, record["joins"]
        assert np.allclose(seat[:3, :3].T @ [0.0, 0.0, -0.025] + seat[3, :3], door["middle"], atol=0.03), seat
        scene = scene_package.write(folders["flat"], tmp_path / "flat_package")
        [leaf] = [copy for copy in scene["instances"] if copy["name"] == "front_door"]
        assert scene["seat"] == record["seats"]["flat"]["matrix"], scene.get("seat")  # what lays its film path
        assert "block" not in {copy["name"] for copy in scene["instances"]} and \
            "block" in {item["name"] for item in scene["left_out"]}, scene["left_out"]  # the neighbour's to stand
        at = np.asarray(leaf["matrix"]).reshape(4, 4)[3, :3]  # the leaf's middle, half its 2.05 m over the sill
        assert np.allclose(at, np.asarray(door["middle"]) + [0.0, 2.05 / 2, 0.0], atol=0.05), (leaf, door)
        stage, place = place_build.opened(folders["flat"])
        assert place_build.record_of(folders["flat"])["seat"]["area"] == "town" and not \
            UsdGeom.Xformable(stage.GetPrimAtPath(f"/{place}")).GetOrderedXformOps(), "the scene was seated"
    else:
        assert any(told in fault for fault in record["faults"]), (case, record["faults"])
