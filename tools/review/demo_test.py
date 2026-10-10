"""Check the demo's shots: a camera looking up at a roof is left out, the cameras kept are spread over the record's
list; on two rooms made here (tools/usd/camera_paths_test.py) a shot whose camera looks through the wall into the
other room walks towards it only as far as is clear, at eye height, every step clear, and keeps looking that way; a
view held near level; a walk in a room keeps to its recorded floor; a camera held far over every floor stands at its
own eye; a standing shot turns in place; the frames run at consecutive moments of the stage's time; a shot starts
where it keeps the clearance from walls and people, or is left out; an earlier take's clear shots are kept; and a
frame's ink lines drawn alone are laid over its look. No Blender, no cloud.

Run: .venv/bin/python tools/review/demo_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

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
    assert camera_paths.edges_clear(scenes, eyes[:-1], eyes[1:], 0.0).all(), "a step meets something"
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


def check_time(stage, scenes):
    """A film's shots follow one another at consecutive moments of the stage's time, and each records its move."""
    record = {"views": [camera("a", [-3, 1.6, 2], [-3, 1.2, -2]), camera("b", [-1, 1.6, 0], [-3, 1.2, 0])],
              "inside": True, "floor": [[-4.0, -3.0], [4.0, 3.0]]}
    moves, shots = demo.film_shots(record, stage, scenes, demo.shot_cameras(record), {})
    views = [view for shot, _ in shots for view in shot]
    per_shot = round(demo.SHOT_SECONDS * demo.RATE)
    assert len(views) == 2 * per_shot and [move["camera"] for move in moves] == ["a", "b"], moves
    assert all(fresh for _, fresh in shots) and all("path" in move or "eye" in move for move in moves), moves
    assert [view["frame"] for view in views[:3]] == [0, 1, 2]  # 24 time codes a second at 24 frames
    assert views[per_shot]["name"] == "shot1-000" and views[per_shot]["frame"] > views[per_shot - 1]["frame"]
    return moves, shots


def check_clear_start(scenes):
    """A camera 0.1 m from a wall starts its shot from the nearest spot that keeps the clearance, and every frame of
    its walk keeps it."""
    view = camera("by-the-wall", [-3.9, 1.6, 2.0], [-3.9, 1.2, -2.0])
    move = demo.shot_move(scenes, view, [[-4.0, -3.0], [4.0, 3.0]], seed=0)
    eyes = np.array([frame["eye"] for frame in demo.shot_frames(move, view, 0, 30)])
    walls, _ = camera_paths.clearances(scenes, eyes)
    assert move["moved"] > 0.1 and walls.min() >= camera_paths.CLEARANCE - camera_paths.KEPT_TO, (move, walls.min())


def check_people(stage, scenes):
    """A camera standing inside a person's box (a balcony camera the stage draws no floor under, as the square's
    stage-near) is moved out of it to keep the clearance, at its own height; one walled in by people is left out."""
    camera_paths_test.add_person(stage, "stander", (0.6, 1.8, 0.6), (2.0, 8.5, 2.0))
    crowded = camera_paths.with_people(scenes, camera_paths.people_boxes(stage))
    view = camera("among-people", [2.0, 9.0, 2.0], [2.0, 8.0, -2.0])
    move = demo.shot_move(crowded, view, None, seed=0)
    walls, persons = camera_paths.clearances(crowded, move["eye"])
    assert move["move"] == "stand" and move["eye"][1] == 9.0, move
    assert camera_paths.stands_clear(walls, persons).all() and move["moved"] > 0.3, (move, persons)
    boxed = camera_paths.with_people(scenes, np.array([camera_paths.box_corners([-1.0, 7.5, -1.0], [5.0, 9.5, 5.0])]))
    assert demo.shot_move(boxed, view, None, seed=0) is None, "a camera deep inside a person's box is not left out"


def check_kept(stage, scenes, moves, shots):
    """With an earlier take, a shot whose every frame stands clear is kept as it was (its move marked with the take);
    one that comes nearer a wall than the clearance is planned anew."""
    with tempfile.TemporaryDirectory() as temporary:
        keep = pathlib.Path(temporary)
        (keep / "views").mkdir()
        views = [view for shot, _ in shots for view in shot]
        near = [dict(view, eye=[-3.9, 1.6, 2.0]) if demo.shot_of(view) == "shot1" else view for view in views]
        (keep / "views" / "rooms.json").write_text(json.dumps({"views": near, "moves": moves}))
        kept = demo.kept_shots(keep, "rooms", scenes, stage)
    assert list(kept) == [0] and kept[0][0]["kept"] == str(keep) and kept[0][1] == shots[0][0], list(kept)
    record = {"views": [camera("a", [-3, 1.6, 2], [-3, 1.2, -2]), camera("b", [-1, 1.6, 0], [-3, 1.2, 0])],
              "inside": True, "floor": [[-4.0, -3.0], [4.0, 3.0]]}
    _, again = demo.film_shots(record, stage, scenes, demo.shot_cameras(record), kept)
    assert [fresh for _, fresh in again] == [False, True] and again[0][0] == shots[0][0], again[0][0][:1]


def check_inked():
    """A frame whose cloud job drew its ink lines alone gets them laid over its look; a frame inked already is kept."""
    with tempfile.TemporaryDirectory() as temporary:
        frames = pathlib.Path(temporary)
        Image.new("RGB", (4, 3), (200, 150, 100)).save(frames / "shot0-000-look.png")
        lines = Image.new("RGBA", (4, 3), (10, 9, 8, 0))
        lines.putpixel((1, 1), (10, 9, 8, 255))
        lines.putpixel((2, 1), (10, 9, 8, 128))
        lines.save(frames / "shot0-000-lines.png")
        found = np.asarray(Image.open(demo.inked(frames, "shot0-000")))
    assert tuple(found[1, 1]) == (10, 9, 8) and tuple(found[0, 0]) == (200, 150, 100), found[:2, :2]
    assert np.abs(found[1, 2].astype(int) - [105, 79, 54]).max() <= 1, found[1, 2]


def check_names():
    assert demo.named("old_station") == ("old_station", "Old station")
    assert demo.named("camp:Mars camp") == ("camp", "Mars camp")


if __name__ == "__main__":
    for check in (check_cameras, check_stand, check_level, check_names, check_inked):
        check()
    with tempfile.TemporaryDirectory() as temporary:
        stage = camera_paths_test.rooms_stage(pathlib.Path(temporary))
        rooms = camera_paths.place_scenes(stage)
        check_walk(rooms)
        check_floor(rooms)
        check_held(rooms)
        check_clear_start(rooms)
        check_kept(stage, rooms, *check_time(stage, rooms))
        check_people(stage, rooms)
    print("demo_test: ok")
