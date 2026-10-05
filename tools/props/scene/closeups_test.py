"""Check the close-up planner (closeups.py) in a room whose answers are obvious: a closed box 8 m wide, 3 m tall, in
Marble's frame (y down), with an item against one wall.

The checks need numpy, which only the prop environment has. Run by the gate with the system python, this hands
itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/closeups_test.py
"""
import math
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("CLOSEUPS_TEST_HANDED") != "1":
        os.environ["CLOSEUPS_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import closeups  # noqa: E402

DOWN = [0, 1, 0]


def box_room(half=4.0, floor=1.5, ceiling=-1.5):
    """The twelve triangles of a closed box: x and z from -half to half, y (down) from ceiling to floor."""
    corners = np.array([[x, y, z] for x in (-half, half) for y in (ceiling, floor) for z in (-half, half)], dtype=float)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return np.array([[corners[a], corners[b], corners[c]] for a, b, c, d in faces for a, b, c in ((a, b, c), (a, c, d))])


def wall_item(**changes):
    """A rack against the north wall (z = +4), facing south into the room."""
    return {"id": "rack", "centre": [0.0, 0.55, 3.7], "size": [0.6, 0.6, 1.9], "facing": [0, 0, -1], **changes}


def test_the_camera_looks_at_the_item_from_its_front():
    room = box_room()
    camera = closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[0])
    eye = np.array(camera["eye"])
    assert eye[2] < 3.7 and abs(eye[0]) < 1e-9 and abs(eye[1] - 0.55) < 1e-9
    view = closeups.view_matrix(camera["eye"], camera["target"], DOWN)
    pixel, depth = closeups.project([camera["target"]], view, closeups.lens(camera["fov"], camera["size"]))
    assert np.allclose(pixel[0], [camera["size"] / 2] * 2) and depth[0] > 0


def test_the_front_view_fills_the_frame_with_the_item():
    room = box_room()
    item = wall_item()
    camera = closeups.camera_for(item, room, DOWN, closeups.SHOTS[0])
    view = closeups.view_matrix(camera["eye"], camera["target"], DOWN)
    intrinsics = closeups.lens(camera["fov"], camera["size"])
    centre, (wide, deep, tall) = np.array(item["centre"]), item["size"]
    face = [centre + [sx * wide / 2, sy * tall / 2, -deep / 2] for sx in (-1, 1) for sy in (-1, 1)]
    pixel, _ = closeups.project(face, view, intrinsics)
    span = (pixel[:, 1].max() - pixel[:, 1].min()) / camera["size"]
    assert abs(span - closeups.FILL) < 0.02, span


def test_up_in_the_world_is_up_in_the_picture():
    room = box_room()
    camera = closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[0])
    view = closeups.view_matrix(camera["eye"], camera["target"], DOWN)
    intrinsics = closeups.lens(camera["fov"], camera["size"])
    centre = np.array(camera["target"])
    pixel, _ = closeups.project([centre + [0, -0.5, 0], centre + [0, 0.5, 0]], view, intrinsics)
    assert pixel[0, 1] < pixel[1, 1]


def test_a_wall_behind_the_camera_pulls_it_in_and_widens_the_lens():
    room = box_room(half=1.4)
    item = wall_item(centre=[0.0, 0.55, 1.1])
    camera = closeups.camera_for(item, room, DOWN, closeups.SHOTS[0])
    assert camera is not None and camera["note"]
    assert camera["eye"][2] > -1.4 + closeups.CLEARANCE_M - 1e-6
    assert camera["fov"] > closeups.FOV_DEGREES


def test_a_camera_with_no_room_to_stand_is_dropped():
    room = box_room(half=0.5)
    assert closeups.camera_for(wall_item(centre=[0.0, 0.55, 0.2]), room, DOWN, closeups.SHOTS[0]) is None


def slab(low, high):
    """The twelve triangles of a solid box from corner `low` to corner `high`."""
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])], dtype=float)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return np.array([[corners[a], corners[b], corners[c]] for a, b, c, d in faces for a, b, c in ((a, b, c), (a, c, d))])


def test_a_camera_blocked_by_a_low_wall_is_raised_to_see_over_it():
    room = np.concatenate([box_room(), slab([-4.0, 0.3, 2.8], [4.0, 1.5, 3.0])])
    assert closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[0]) is None
    camera = closeups.camera_or_raised(wall_item(), room, DOWN, closeups.SHOTS[0])
    assert camera is not None and "raised" in camera["note"] and camera["eye"][1] < 0.55


def test_every_camera_stands_inside_the_room():
    room = box_room()
    for shot in closeups.SHOTS:
        camera = closeups.camera_for(wall_item(), room, DOWN, shot)
        assert camera is not None, shot[0]
        assert closeups.inside_room(room, np.array(camera["eye"]), DOWN), shot[0]


def test_the_view_from_above_looks_down_on_the_item():
    room = box_room()
    above = closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[3])
    assert above["eye"][1] < 0.55


def test_the_side_views_stand_either_side_of_the_front():
    room = box_room()
    left = closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[1])
    right = closeups.camera_for(wall_item(), room, DOWN, closeups.SHOTS[2])
    assert left["eye"][0] * right["eye"][0] < 0


def test_the_planner_lists_the_items_each_camera_sees():
    room = box_room()
    items = [wall_item(), wall_item(id="locker", centre=[0.9, 0.55, 3.7]), wall_item(id="far", centre=[0.0, 0.55, -3.7], facing=[0, 0, 1])]
    planned = closeups.plan(room, items, DOWN)
    front = next(camera for camera in planned if camera["item"] == "rack" and camera["shot"] == "front")
    assert "rack" in front["prompts"] and "locker" in front["prompts"] and "far" not in front["prompts"]


def test_the_highest_score_wins_each_pixel_and_no_pixel_has_two_owners():
    first = np.zeros((4, 4), bool)
    first[:, :3] = True
    second = np.zeros((4, 4), bool)
    second[:, 1:] = True
    labels = closeups.resolve([first, second], [0.6, 0.9])
    assert (labels[:, 0] == 0).all() and (labels[:, 1:] == 1).all()
    labels = closeups.resolve([first, second], [0.9, 0.6])
    assert (labels[:, :3] == 0).all() and (labels[:, 3] == 1).all()
    empty = closeups.resolve([np.zeros((2, 2), bool)], [0.9])
    assert (empty == -1).all()


def test_a_cut_out_keeps_only_its_pixels_cropped_with_a_margin():
    image = np.full((50, 50, 3), 200, np.uint8)
    mask = np.zeros((50, 50), bool)
    mask[10:30, 20:40] = True
    rgba = closeups.cut(image, mask, margin=0.1)
    assert rgba.shape == (24, 24, 4) and rgba[..., 3].sum() == 20 * 20 * 255
    assert closeups.cut(image, np.zeros((50, 50), bool)) is None


def test_extents_turn_with_the_view():
    across, upright, reach = closeups.extents([2.0, 0.5, 1.0], 0.0, 0.0)
    assert (across, upright, reach) == (2.0, 1.0, 0.25)
    across, _, _ = closeups.extents([2.0, 0.5, 1.0], 90.0, 0.0)
    assert math.isclose(across, 0.5, abs_tol=1e-9)


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
