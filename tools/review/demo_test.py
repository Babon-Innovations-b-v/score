"""Check the demo's shots: a camera looking up at a roof is left out, the cameras kept are spread over the record's
list, a shot's eye moves only a little way towards its aim (never past the cap) while its view turns, and the frames
run at consecutive moments of the stage's time. No Blender, no cloud.

Run: .venv/bin/python tools/review/demo_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import demo  # noqa: E402


def camera(name, eye, aim):
    return {"name": name, "eye": eye, "aim": aim, "fov": 75}


def check_cameras():
    record = {"views": [camera(f"spot{number}", [number, 1.6, 0], [number, 1.2, -4]) for number in range(7)]
              + [camera("up-roof", [0, 1.6, 0], [0.2, 4.1, 0])]}
    chosen = demo.shot_cameras(record, count=4)
    assert [view["name"] for view in chosen] == ["spot0", "spot2", "spot4", "spot6"], chosen
    assert all(view["name"] != "up-roof" for view in demo.shot_cameras(record, count=10))


def check_shot():
    view = camera("spot", [0.0, 1.6, 4.0], [0.0, 1.2, -6.0])
    frames = demo.shot_frames(view, 0, 30, inside=True)
    eyes = np.array([frame["eye"] for frame in frames])
    moved = np.linalg.norm(eyes[-1] - eyes[0])
    assert abs(moved - demo.DOLLY_CAP_INSIDE) < 1e-3, moved
    first, last = (np.array(frames[index]["aim"]) - eyes[index] for index in (0, -1))
    turn = np.degrees(np.arccos(np.dot(first[[0, 2]], last[[0, 2]])
                                / np.linalg.norm(first[[0, 2]]) / np.linalg.norm(last[[0, 2]])))
    assert abs(turn - demo.TURN_DEGREES) < 0.1, turn
    other = demo.shot_frames(view, 1, 30, inside=True)
    assert np.sign(other[0]["aim"][0]) == -np.sign(frames[0]["aim"][0]), "shots turn the other way in turn"


def check_time():
    record = {"views": [camera("a", [0, 1.6, 2], [0, 1.2, -2]), camera("b", [2, 1.6, 0], [-2, 1.2, 0])]}
    views = demo.place_views(record, 30.0)
    per_shot = round(demo.SHOT_SECONDS * demo.RATE)
    assert len(views) == 2 * per_shot
    assert [view["frame"] for view in views[:3]] == [0, 1, 2]  # 30 time codes a second at 24 frames: 0, 1.25, 2.5
    assert views[per_shot]["name"] == "shot1-000" and views[per_shot]["frame"] > views[per_shot - 1]["frame"]


def check_names():
    assert demo.named("old_station") == ("old_station", "Old station")
    assert demo.named("camp:Mars camp") == ("camp", "Mars camp")


if __name__ == "__main__":
    for check in (check_cameras, check_shot, check_time, check_names):
        check()
    print("demo_test: ok")
