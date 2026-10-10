"""Check the demo's shots: a camera looking up at a roof is left out, the cameras kept are spread over the record's
list; on two rooms made here (tools/usd/camera_paths_test.py) a shot whose camera looks through the wall into the
other room walks towards it only as far as is clear, at eye height, every step clear, and keeps looking that way; a
view held near level; a walk in a room keeps to its recorded floor; a camera held far over every floor stands at its
own eye; a standing shot turns in place; and the frames run at consecutive moments of the stage's time. No Blender,
no cloud.

Run: .venv/bin/python tools/review/demo_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import demo  # noqa: E402
import camera_paths  # noqa: E402  (tools/usd, on the path through demo)
import camera_paths_test  # noqa: E402


def camera(name, eye, aim):
    return {"name": name, "eye": eye, "aim": aim, "fov": 75}


def check_cameras():
    record = {"views": [camera(f"spot{number}", [number, 1.6, 0], [number, 1.2, -4]) for number in range(7)]
              + [camera("up-roof", [0, 1.6, 0], [0.2, 4.1, 0])]}
    chosen = demo.shot_cameras(record, count=4)
    assert [view["name"] for view in chosen] == ["spot0", "spot2", "spot4", "spot6"], chosen
    assert all(view["name"] != "up-roof" for view in demo.shot_cameras(record, count=10))
    assert [view["name"] for view in demo.shot_cameras(record, names=["spot5", "spot1"])] == ["spot5", "spot1"]
    assert demo.chosen("hub=wide-north,wide-east") == ("hub", "hub", ["wide-north", "wide-east"])
    assert demo.chosen("hub") == ("hub", "hub", [])
    assert demo.chosen("campgrounds@camp=outside_far") == ("campgrounds", "camp", ["outside_far"])


def check_walk(scenes):
    """A camera in the left room looking at the right one through the wall between them walks half the way, not into
    the wall; its eyes stay at eye height, every step is clear, and it keeps looking towards the right room."""
    view = camera("through-the-wall", [-3.0, 1.6, 2.0], [3.0, 1.2, 2.0])
    move = demo.shot_move(scenes, view, [[-4.0, -3.0], [4.0, 3.0]], seed=0)
    frames = demo.shot_frames(move, view, 0, 30)
    eyes = np.array([frame["eye"] for frame in frames])
    assert move["move"] == "walk" and len(frames) == 30, move
    assert np.abs(eyes[:, 1] - camera_paths.EYE_HEIGHT).max() < 1e-6, eyes[:, 1]
    assert eyes[:, 0].max() < -camera_paths.CLEARANCE, f"the walk reaches x = {eyes[:, 0].max():.2f}, the wall"
    assert np.linalg.norm(eyes[-1] - eyes[0]) > demo.SHORTEST_WALK, "the walk does not move"
    assert camera_paths.edges_clear(scenes["blocking"], eyes[:-1], eyes[1:], 0.0).all(), "a step meets something"
    looks = np.array([frame["aim"] for frame in frames]) - eyes
    assert (looks[:, 0] > 0).all(), "the walk looks away from what its camera looks at"


def check_floor(scenes):
    """A room's walk keeps to the record's floor: with the floor ending well short of the wall ahead, the walk goes
    sideways instead, every eye on the floor."""
    floor = [[-4.0, -3.0], [-2.5, 3.0]]
    view = camera("short-floor", [-3.0, 1.6, 2.0], [3.0, 1.2, 2.0])
    move = demo.shot_move(scenes, view, floor, seed=0)
    eyes = np.array([frame["eye"] for frame in demo.shot_frames(move, view, 0, 30)])[:, [0, 2]]
    assert move["move"] == "walk" and np.linalg.norm(eyes[-1] - eyes[0]) > demo.SHORTEST_WALK, move
    assert (eyes >= np.array(floor[0]) - 1e-9).all() and (eyes <= np.array(floor[1]) + 1e-9).all(), eyes


def check_held(scenes):
    """A camera held far over any floor of the stage (a balcony the stage does not draw) stands at its own eye and
    keeps looking where it looks, steeply down, not levelled."""
    view = camera("over-the-rooms", [-3.0, 9.0, 2.0], [3.0, 0.0, 2.0])
    move = demo.shot_move(scenes, view, None, seed=0)
    assert move["move"] == "stand" and move["eye"] == view["eye"] and not move["level"], move
    frame = demo.shot_frames(move, view, 0, 30)[15]
    looked = np.array(frame["aim"]) - frame["eye"]
    assert np.degrees(np.arctan2(looked[1], np.linalg.norm(looked[[0, 2]]))) < -45, frame


def check_stand():
    """A standing shot keeps its eye and turns its view through TURN_DEGREES, each shot the other way."""
    view = camera("spot", [0.0, 1.6, 4.0], [0.0, 1.2, -6.0])
    frames = demo.standing_frames(np.array(view["eye"]), np.array(view["aim"]), view, 0, 30)
    eyes = np.array([frame["eye"] for frame in frames])
    assert np.linalg.norm(eyes[-1] - eyes[0]) < 1e-9
    first, last = (np.array(frames[index]["aim"]) - eyes[index] for index in (0, -1))
    turn = np.degrees(np.arccos(np.dot(first[[0, 2]], last[[0, 2]])
                                / np.linalg.norm(first[[0, 2]]) / np.linalg.norm(last[[0, 2]])))
    assert abs(turn - demo.TURN_DEGREES) < 0.1, turn
    other = demo.standing_frames(np.array(view["eye"]), np.array(view["aim"]), view, 1, 30)
    assert np.sign(other[0]["aim"][0]) == -np.sign(frames[0]["aim"][0]), "shots turn the other way in turn"


def check_level():
    eye = np.array([0.0, 1.6, 0.0])
    for aim, most in (([0.0, 9.0, -2.0], demo.LOOK_UP), ([0.0, -9.0, -2.0], -demo.LOOK_DOWN), ([0.0, 1.4, -4.0], None)):
        looked = demo.levelled(eye, aim) - eye
        pitch = np.degrees(np.arctan2(looked[1], np.linalg.norm(looked[[0, 2]])))
        expected = most if most is not None else np.degrees(np.arctan2(-0.2, 4.0))
        assert abs(pitch - expected) < 1e-6, (aim, pitch)


def check_time(scenes):
    record = {"views": [camera("a", [-3, 1.6, 2], [-3, 1.2, -2]), camera("b", [-1, 1.6, 0], [-3, 1.2, 0])],
              "inside": True, "floor": [[-4.0, -3.0], [4.0, 3.0]]}
    cameras = demo.shot_cameras(record)
    moves = demo.place_moves(record, scenes, cameras)
    views = demo.place_views(cameras, moves, 30.0)
    per_shot = round(demo.SHOT_SECONDS * demo.RATE)
    assert len(views) == 2 * per_shot and [move["camera"] for move in moves] == ["a", "b"], moves
    assert [view["frame"] for view in views[:3]] == [0, 1, 2]  # 30 time codes a second at 24 frames: 0, 1.25, 2.5
    assert views[per_shot]["name"] == "shot1-000" and views[per_shot]["frame"] > views[per_shot - 1]["frame"]


def check_names():
    assert demo.named("old_station") == ("old_station", "Old station")
    assert demo.named("camp:Mars camp") == ("camp", "Mars camp")


if __name__ == "__main__":
    for check in (check_cameras, check_stand, check_level, check_names):
        check()
    with tempfile.TemporaryDirectory() as temporary:
        rooms = camera_paths.place_scenes(camera_paths_test.rooms_stage(pathlib.Path(temporary)))
        check_walk(rooms)
        check_floor(rooms)
        check_held(rooms)
        check_time(rooms)
    print("demo_test: ok")
