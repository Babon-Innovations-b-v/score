"""Check the demo's shots: the owner's picked viewpoints are a film's cameras where he picked any; a camera looking up
at a roof is left out, the cameras kept are spread over the record's list; on two rooms made here
(tools/usd camera_paths.py's test) a shot whose camera looks through the wall into the other room walks towards it only as
far as is clear, at eye height, every step clear, and keeps looking that way; a view held near level; a walk in a room
keeps to its recorded floor, glides at one speed between its eased ends and rounds its corners; a camera held far over
every floor, or one that says stand, stands; a standing shot turns in place;
the frames run at consecutive moments of the stage's time; a shot starts where it keeps the clearance from walls and
people (never inside a solid), or is left out; an earlier take's clear shots are kept; and a frame's ink lines drawn alone are laid over its
look. No Blender, no cloud.

One film of the two rooms (with two people added high over them) is planned through film_cameras and film_shots, and
again with an earlier take of it, each shot judged against its camera's row (RECORD); its walks by one judge
(walk_faults), a sharp corner rounded by rounded_corners too. Each break (applied once, seen red, reverted), in
tools/review/demo.py, by the behaviour's key words:
- a roof look left out: shot_cameras keeps a camera looking up at a roof.
- through the wall: walked_frames looks away from the camera's aim.
- keeps to its floor: walk_path drops its on_floor test.
- held over every floor: shot_frames levels a held camera's view too.
- picked viewpoints: film_cameras never takes the owner's picks first.
- turns in place: standing_frames turns every shot the same way.
- glides at one speed: eased is one cosine over the whole shot.
- corner rounded: rounded_corners keeps every corner sharp.
- corner ends kept: rounded_corners moves the path's last point (5 cm).
- says stand, stands: shot_move walks a camera that says stand.
- near level: levelled clamps nothing.
- consecutive moments: shot_times starts every shot at the same moment.
- keeps the clearance: clear_spot returns the camera's own eye, clear or not; or (2026-11-04) camera_paths.clearances
  measures an eye inside a closed mesh by its walls (`0.0 if inside_solid(...) else` dropped: the crate's camera stays
  in it).
- among people: clear_spot moves a held camera a metre down.
- earlier take kept: kept_shots keeps a shot that comes near a wall.
- spare camera: film_shots never tries a spare camera.
- ink drawn alone: inked saves the look without its lines.
- key and title: named keeps the key as the title.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_a_films_shots_keep_clear_and_move_smoothly.py
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
import test_a_walk_goes_through_doorways_clear_of_everything as camera_paths_test  # noqa: E402


def camera(name, eye, aim, **more):
    return {"name": name, "eye": eye, "aim": aim, "fov": 75, **more}


FLOOR = [[-4.0, -3.0], [4.0, 3.0]]
SHORT_FLOOR = [[-4.0, -3.0], [-2.5, 3.0]]  # the left room's floor ending well short of the wall ahead
# The owner's picked viewpoints of the rooms, in the order he saved them: the first looks up past the near-level hold
# into the other room, its walk turning through the doorway.
PICKS = [dict(camera("by the stair", [-2.0, 1.6, 2.5], [4.0, 3.0, -1.0]), fov=70),
         camera("door", [5.0, 1.6, 2.0], [5.0, 1.4, -2.0])]
# The record's cameras and what each one's shot does in the film: "walk", "stand", or "left" (None from shot_move:
# no clear spot near it, the film falls back to a spare, or leaves the shot out without one); `moved` the least the
# start moves off the camera's own spot; `reach` the furthest x a walk goes; `own eye` a stand at the camera's eye.
RECORD = [
    (camera("through-the-wall", [-3.0, 1.6, 2.0], [3.0, 1.2, 2.0]), {"move": "walk", "reach": -camera_paths.CLEARANCE}),
    (camera("by-the-wall", [-3.9, 1.6, 2.0], [-3.9, 1.2, -2.0]), {"move": "walk", "moved": 0.1}),
    (camera("in-the-crate", [-2.0, 0.5, 0.0], [-1.0, 0.5, 0.0]), {"move": ("walk", "stand", "left"), "moved": 0.5}),
    (camera("over-the-rooms", [-3.0, 9.0, 2.0], [3.0, 0.0, 2.0]), {"move": "stand", "own eye": True, "level": False}),
    (camera("held", [-3.0, 1.6, 2.0], [-3.0, -9.0, -2.0], stand=True), {"move": "stand", "level": True}),
    (camera("among-people", [2.0, 9.0, 2.0], [2.0, 8.0, -2.0]), {"move": "stand", "height": 9.0, "moved": 0.3}),
    (camera("walled", [3.0, 9.0, -2.0], [3.0, 8.0, -4.0]), {"move": "left"}),
    (camera("up-roof", [0.0, 1.6, 0.0], [0.2, 4.1, 0.0]), {}),
    (camera("far", [-3.0, 1.6, -2.0], [-1.0, 1.2, 0.0]), {"move": "walk"}),
    (camera("near", [1.0, 1.6, 0.5], [1.0, 1.2, -2.0]), {"move": "walk"}),
]
FILMED = ["by the stair", "through-the-wall", "by-the-wall", "over-the-rooms", "held", "among-people", "in-the-crate",
          "walled"]  # the shots that may be left out last, so a take planned again keeps its shots' numbers
# A person standing by the among-people camera, and one whose box walls the walled camera in (balcony cameras over
# floors the stage does not draw, as the square's stage-near): (name, size, centre).
PEOPLE = [("stander", (0.6, 1.8, 0.6), (2.0, 8.5, 2.0)), ("crowd", (6.0, 2.0, 6.0), (3.0, 8.5, -2.0))]
# The film as given to plan, read as (film, place, cameras named); a film's name read as (key, title).
GIVEN = [("hub=wide-north,wide-east", ("hub", "hub", ["wide-north", "wide-east"])), ("hub", ("hub", "hub", [])),
         ("campgrounds@camp=outside_far", ("campgrounds", "camp", ["outside_far"]))]
NAMES = [("old_station", ("old_station", "Old station")), ("camp:Mars camp", ("camp", "Mars camp"))]
# A view's aim from an eye at 1.6 m, and the pitch (degrees) levelled holds it at.
PITCHES = [([0.0, 9.0, -2.0], demo.LOOK_UP), ([0.0, -9.0, -2.0], -demo.LOOK_DOWN),
           ([0.0, 1.4, -4.0], float(np.degrees(np.arctan2(-0.2, 4.0))))]


def rooms_with_people(folder):
    """The two rooms (tools/usd camera_paths.py's test) with PEOPLE added: (stage, scenes)."""
    stage = camera_paths_test.rooms_stage(folder)
    for name, size, centre in PEOPLE:
        camera_paths_test.add_person(stage, name, size, centre)
    return stage, camera_paths.place_scenes(stage)


def pitch(looked):
    return float(np.degrees(np.arctan2(looked[1], np.linalg.norm(looked[[0, 2]]))))


def on(floor, eyes):
    return bool((eyes[:, [0, 2]] >= np.array(floor[0]) - 1e-9).all() and (eyes[:, [0, 2]] <= np.array(floor[1]) + 1e-9).all())


def walk_faults(scenes, move, frames, view, floor):
    """What a walk's frames do wrong: off eye height, a step meeting something, not moving, off its room's floor,
    looking away from its camera's aim, or a corner turned sharper than 60 degrees between two steps of its path."""
    eyes = np.array([frame["eye"] for frame in frames])
    looks = np.array([frame["aim"] for frame in frames]) - eyes
    ahead = (np.asarray(view["aim"]) - np.asarray(view["eye"]))[[0, 2]]
    path = np.array(move["path"])
    ways = np.diff(path, axis=0)[:, [0, 2]]
    ways = ways[np.linalg.norm(ways, axis=1) > 0]  # a rounded corner's curve may start on the point before it
    ways = ways / np.linalg.norm(ways, axis=1)[:, None]
    turns = np.degrees(np.arccos(np.clip((ways[1:] * ways[:-1]).sum(axis=1), -1.0, 1.0)))
    faults = {
        "off eye height": np.abs(eyes[:, 1] - camera_paths.EYE_HEIGHT).max() >= 1e-6,
        "a step meets something": not camera_paths.edges_clear(scenes, eyes[:-1], eyes[1:], 0.0).all(),
        "its path is not walkable": not camera_paths.edges_walkable(scenes, path[:-1], path[1:],
                                                                   camera_paths.CLEARANCE).all(),
        "it does not move": np.linalg.norm(eyes[-1] - eyes[0]) <= demo.SHORTEST_WALK,
        "off its floor": floor is not None and not on(floor, eyes),
        "looks away from its camera's aim": not (looks[:, [0, 2]] @ ahead > 0).all(),
        f"a corner turns {turns.max() if len(turns) else 0:.0f} degrees at once": len(turns) and turns.max() >= 60.0,
        "its ends moved": not (np.allclose(path[0], frames[0]["eye"], atol=1e-4)
                               and np.allclose(path[-1], frames[-1]["eye"], atol=1e-4)),
    }
    return [fault for fault, found in faults.items() if found]


def stand_turn(frames):
    """A standing shot's eye drift (metres) and its view's turn from first to last frame (signed degrees about up)."""
    eyes = np.array([frame["eye"] for frame in frames])
    first, last = (np.array(frames[index]["aim"])[[0, 2]] - eyes[index][[0, 2]] for index in (0, -1))
    turn = np.degrees(np.arccos(np.dot(first, last) / np.linalg.norm(first) / np.linalg.norm(last)))
    return float(np.linalg.norm(eyes[-1] - eyes[0])), float(turn * np.sign(first[1] * last[0] - first[0] * last[1]))


def test_a_films_shots_keep_clear_and_move_smoothly():
    """One film of the rooms planned through film_cameras and film_shots (and again with an earlier take of it), every
    shot judged against its camera's row; then the film's names, eases, levels and ink."""
    folder = pathlib.Path(tempfile.mkdtemp())
    stage, scenes = rooms_with_people(folder)
    record = {"views": [view for view, _ in RECORD], "inside": True, "floor": FLOOR}
    expected = {view["name"]: row for view, row in RECORD}
    expected["by the stair"] = {"move": "walk"}
    picks = folder / "picks"

    # The cameras: the record's spread (none looking up at a roof) until the owner picks; then his picks in order.
    level = [view["name"] for view, _ in RECORD if view["name"] != "up-roof"]
    assert [view["name"] for view in demo.film_cameras("rooms", record, picks=picks)] == [
        level[index] for index in (0, 3, 5, 8)]
    assert "up-roof" not in [view["name"] for view in demo.shot_cameras(record, count=len(RECORD))]
    for pick in PICKS:
        demo.viewpoints.append("rooms", pick, picks)
    found = demo.film_cameras("rooms", record, picks=picks)
    assert [(view["name"], view["fov"]) for view in found] == [("by the stair", 70), ("door", 75)], found
    cameras = demo.film_cameras("rooms", record, FILMED, picks=picks)
    assert [view["name"] for view in cameras] == FILMED
    spares = demo.spare_cameras(record, cameras)
    assert [view["name"] for view in spares] == ["far", "near"], spares

    moves, shots = demo.film_shots(record, stage, scenes, cameras, {}, spares=spares)
    views = [view for shot, _ in shots for view in shot]
    per_shot = round(demo.SHOT_SECONDS * demo.RATE)
    made = [move["camera"] for move in moves]
    left = [name for name in FILMED if expected[name]["move"] == "left"
            or "left" in expected[name]["move"] and name not in made]
    queue = [view["name"] for view in spares]
    assert made == [queue.pop(0) if name in left else name for name in FILMED], made
    assert all(fresh for _, fresh in shots) and len(views) == len(moves) * per_shot, moves
    assert [view["frame"] for view in views] == list(range(len(views))), "the shots' moments are not consecutive"
    assert [view["name"] for view in views[per_shot - 1:per_shot + 1]] == [f"shot0-{per_shot - 1:03d}", "shot1-000"]
    people = camera_paths.moving_boxes(stage)
    sides = set()
    for number, (move, (frames, _)) in enumerate(zip(moves, shots)):
        view, row = next(view for view in cameras + spares if view["name"] == move["camera"]), expected[move["camera"]]
        eyes = np.array([frame["eye"] for frame in frames])
        allowed = row["move"] if isinstance(row["move"], tuple) else (row["move"],)
        assert move["move"] in allowed and len(frames) == per_shot, (row, move)
        assert {frame["fov"] for frame in frames} == {view["fov"]}, view
        walls, persons = camera_paths.clearances(camera_paths.with_people(scenes, people), eyes)
        assert camera_paths.stands_clear(walls, persons).all(), (move, walls.min(), persons.min())
        assert move["moved"] > row.get("moved", -1.0), (move, row)
        if move["move"] == "walk":
            faults = walk_faults(scenes, move, frames, view, FLOOR)
            assert not faults, (move["camera"], faults)
            assert eyes[:, 0].max() < row.get("reach", np.inf), f"{move['camera']} reaches x = {eyes[:, 0].max():.2f}"
            continue
        drift, turn = stand_turn(frames)
        assert drift < 1e-9 and abs(abs(turn) - demo.TURN_DEGREES) < 0.1, (move["camera"], drift, turn)
        sides.add(np.sign(turn) * (1 if number % 2 == 0 else -1))
        assert move["level"] == row.get("level", move["level"]), move
        if row.get("own eye"):
            assert move["eye"] == view["eye"] and pitch(np.array(frames[per_shot // 2]["aim"]) - eyes[0]) < -45, move
        assert move["eye"][1] == row.get("height", move["eye"][1]), move
    assert len(sides) == 1, "standing shots do not turn the other way each in turn"
    # A walk's path cornered 148 degrees at once in the right room, rounded as a walk's is, walks as smoothly.
    sharp = [np.array([x, camera_paths.EYE_HEIGHT, z]) for x, z in ((1.0, 2.0), (2.0, -1.5), (3.0, 2.0))]
    rounded = demo.rounded_corners(scenes, sharp)
    assert np.allclose(rounded[0], sharp[0]) and np.allclose(rounded[-1], sharp[-1]), rounded
    view = camera("corner", [1.0, 1.6, 2.0], [5.0, 1.2, 2.0])
    move = {"camera": "corner", "move": "walk", "path": [point.tolist() for point in rounded]}
    assert len(rounded) == demo.ROUND_STEPS + 3, len(rounded)
    faults = walk_faults(scenes, move, demo.shot_frames(move, view, 0, per_shot), view, FLOOR)
    assert not faults, faults

    # An earlier take whose second shot comes nearer a wall than the clearance, planned again on the floor recorded
    # shorter since and with no spare: the clear shots are kept as they were, the near one planned anew on the
    # shorter floor (it goes sideways), and the walled shot is left out.
    keep = folder / "take"
    (keep / "views").mkdir(parents=True)
    near = [dict(view, eye=[-3.9, 1.6, 2.0]) if demo.shot_of(view) == "shot1" else view for view in views]
    (keep / "views" / "rooms.json").write_text(json.dumps({"views": near, "moves": moves}))
    kept = demo.kept_shots(keep, "rooms", scenes, stage)
    assert sorted(kept) == [number for number in range(len(moves)) if number != 1], sorted(kept)
    assert kept[0][0] == dict(moves[0], kept=str(keep)) and kept[0][1] == shots[0][0], kept[0][0]
    shorter = dict(record, floor=SHORT_FLOOR)
    again_moves, again = demo.film_shots(shorter, stage, scenes, cameras, kept)
    assert [move["camera"] for move in again_moves] == [name for name in FILMED if name not in left], again_moves
    assert [fresh for _, fresh in again] == [number == 1 for number in range(len(again))], [fresh for _, fresh in again]
    assert again[0][0] == shots[0][0]
    assert again_moves[1]["move"] == "walk", again_moves[1]
    faults = walk_faults(scenes, again_moves[1], again[1][0], cameras[1], SHORT_FLOOR)
    assert not faults, faults

    # A shot's progress: still at its ends, eased over EASE_SECONDS, one speed between, never going back.
    shares = demo.eased(per_shot)
    speeds = np.diff(shares) * demo.RATE
    middle = speeds[round(demo.EASE_SECONDS * demo.RATE) + 1:-round(demo.EASE_SECONDS * demo.RATE) - 1]
    assert shares[0] == 0.0 and abs(shares[-1] - 1.0) < 1e-9 and (np.diff(shares) >= 0).all(), shares
    assert np.ptp(middle) < 1e-9, "the walk's speed changes between its eased ends"
    assert speeds.max() < 1.2 / ((per_shot - 1) / demo.RATE), "its top speed over 1.2 times its mean (the cosine's 1.57)"
    eye = np.array([0.0, 1.6, 0.0])
    for aim, most in PITCHES:
        assert abs(pitch(demo.levelled(eye, aim) - eye) - most) < 1e-6, (aim, most)
    for given, reading in GIVEN:
        assert demo.chosen(given) == reading, given
    for given, reading in NAMES:
        assert demo.named(given) == reading, given

    # The film's first frame drawn by a cloud job as its look and its ink lines alone: the lines laid over the look.
    first = views[0]["name"]
    Image.new("RGB", (4, 3), (200, 150, 100)).save(folder / f"{first}-look.png")
    lines = Image.new("RGBA", (4, 3), (10, 9, 8, 0))
    lines.putpixel((1, 1), (10, 9, 8, 255))
    lines.putpixel((2, 1), (10, 9, 8, 128))
    lines.save(folder / f"{first}-lines.png")
    inked = np.asarray(Image.open(demo.inked(folder, first)))
    assert tuple(inked[1, 1]) == (10, 9, 8) and tuple(inked[0, 0]) == (200, 150, 100), inked[:2, :2]
    assert np.abs(inked[1, 2].astype(int) - [105, 79, 54]).max() <= 1, inked[1, 2]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    test_a_films_shots_keep_clear_and_move_smoothly()
    print("ok")
