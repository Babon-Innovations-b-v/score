"""Check the layout rules (layout.py) on rooms whose right answer is obvious.

Plain python, run by the gate with the system python: python3 tools/props/scene/layout_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from layout import (half_width_at, layout, resting_height, section_points, snapped_height,  # noqa: E402
                    squared)

MEASURES = {"floor_half_width": 1.2, "widest_half_width": 1.8, "widest_height": 1.4,
            "ceiling": 3.0, "far_end": -5.0}


def box(low, high, key="thing"):
    return {"key": key, "low": list(low), "high": list(high)}


def test_the_section_runs_from_floor_edge_over_the_top_and_is_mirrored():
    outline = section_points(MEASURES)
    assert outline[0] == [1.2, 0.0]
    assert outline[-1] == [-1.2, 0.0]
    assert max(point[1] for point in outline) == 3.0
    assert max(point[0] for point in outline) == 1.8
    for (across, up), (other_across, other_up) in zip(outline, reversed(outline)):
        assert abs(across + other_across) < 1e-9 and up == other_up


def test_the_wall_is_widest_at_its_widest_height_and_meets_the_floor_edge():
    outline = section_points(MEASURES)
    assert abs(half_width_at(outline, 1.4) - 1.8) < 1e-6
    assert abs(half_width_at(outline, 0.0) - 1.2) < 1e-6
    assert half_width_at(outline, 2.9) < half_width_at(outline, 2.0)


def test_a_turn_is_squared_to_the_nearest_room_axis_and_the_error_kept():
    assert squared(84.0) == (90.0, -6.0)
    assert squared(-3.0) == (0.0, -3.0)
    yaw, error = squared(181.0)
    assert yaw == 180.0 and error == 1.0


def test_a_height_near_its_known_measure_snaps_and_a_far_one_does_not():
    assert snapped_height("desk", 0.8) == 0.75
    assert snapped_height("desk", 1.2) == 1.2
    assert snapped_height("unknown_thing", 0.33) == 0.33


def test_a_box_rests_on_the_floor_on_what_is_under_it_or_hangs_where_seen():
    desk = box((1.0, 0.1, -3.0), (1.6, 0.8, -2.0), "desk")
    tops = [(desk, 0.75)]
    assert resting_height(desk, tops) == 0.0
    assert resting_height(box((1.2, 0.85, -2.6), (1.4, 1.2, -2.4)), tops) == 0.75
    assert resting_height(box((1.2, 1.5, -2.6), (1.4, 1.8, -2.4)), tops) == 1.5
    assert resting_height(box((-1.4, 0.85, -2.6), (-1.2, 1.2, -2.4)), tops) == 0.85


def test_a_model_seen_from_its_front_faces_the_camera_and_its_back_fits_the_wall():
    boxes = {"camera": {"position": [0.0, 1.5, 0.0]}, "section": MEASURES,
             "objects": [box((1.0, 0.05, -3.4), (1.5, 0.75, -2.6), "desk-1")]}
    models = {"desk": {"size": [1.0, 0.75, 0.6], "front": [0.0, 1.0], "file": "desk.glb"}}
    placed = layout(boxes, {"objects": {"desk-1": "desk"}}, models)["objects"][0]
    # On the right wall, a front along +z is turned to face the aisle, -x: a quarter turn back.
    assert placed["yaw"] == -90.0
    # The camera saw it from ahead and to the left, about 23 degrees round from the aisle.
    assert 20.0 < abs(placed["turn_error"]) < 70.0
    assert placed["position"][1] == 0.0
    outline = section_points(MEASURES)
    assert placed["position"][0] + 0.3 <= half_width_at(outline, 0.75) + 1e-6


def test_an_object_at_the_far_end_faces_down_the_room():
    boxes = {"camera": {"position": [0.0, 1.5, 0.0]}, "section": MEASURES,
             "objects": [box((-0.3, 0.0, -4.9), (0.3, 1.8, -4.6), "locker-1")]}
    models = {"locker": {"size": [0.6, 1.8, 0.4], "front": [1.0, 0.0], "file": "locker.glb"}}
    placed = layout(boxes, {"objects": {"locker-1": "locker"}}, models)["objects"][0]
    assert placed["yaw"] == -90.0


def test_two_copies_of_one_model_are_one_size_the_best_seen_ones():
    near = box((-1.6, 0.0, -2.6), (-1.0, 0.9, -1.8), "bench-2")
    near["points"] = 900
    far = box((-1.6, 0.0, -4.0), (-1.0, 1.2, -3.0), "bench-1")
    far["points"] = 4000
    boxes = {"camera": {"position": [0.0, 1.5, 0.0]}, "section": MEASURES, "objects": [near, far]}
    models = {"bench": {"size": [0.9, 0.9, 0.9], "front": [0.0, 1.0], "file": "bench.glb"}}
    placed = layout(boxes, {"objects": {"bench-1": "bench", "bench-2": "bench"}}, models)["objects"]
    assert placed[0]["scale"] == placed[1]["scale"]
    assert placed[0]["height"] == 1.2


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
