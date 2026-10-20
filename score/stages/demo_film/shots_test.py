"""shots.py with no render: what a view sees, a person in view or not, and a moving door with and without its sound.

Run: .venv/bin/python score/stages/demo_film/shots_test.py
"""
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from pxr import Gf, Usd, UsdGeom, UsdMedia, UsdSkel, Vt  # noqa: E402

from score.stages.demo_film import shots  # noqa: E402

LOOKING_NORTH = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "fov": 75.0}


def views(aim_z=-10.0, frames=range(4)):
    """A standing shot looking along z, one view a frame."""
    return [{"name": f"shot0-{frame:03d}", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, aim_z], "fov": 75.0,
             "frame": frame} for frame in frames]


def a_stage(person_at=None, door_sound=False):
    """A place with a person standing at `person_at` and a door sliding along x over frames 0 to 3 at z = -5."""
    path = pathlib.Path(tempfile.mkdtemp()) / "hall.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, "/hall")
    stage.SetDefaultPrim(root.GetPrim())
    for group in ("Characters", "Objects"):
        UsdGeom.Xform.Define(stage, f"/hall/{group}")
    if person_at is not None:
        person = UsdSkel.Root.Define(stage, "/hall/Characters/walker")
        person.AddTranslateOp().Set(Gf.Vec3d(*person_at))
        person.CreateExtentAttr().Set(Vt.Vec3fArray([(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]))  # no skeleton: bound given
    door = UsdGeom.Xform.Define(stage, "/hall/Objects/door")
    slide = door.AddTranslateOp()
    for frame in range(4):
        slide.Set(Gf.Vec3d(0.5 * frame, 1.0, -5.0), frame)
    UsdGeom.Cube.Define(stage, "/hall/Objects/door/leaf").CreateSizeAttr(1.0)
    if door_sound:
        UsdMedia.SpatialAudio.Define(stage, "/hall/Objects/door/Sound_0")
    stage.GetRootLayer().Save()
    return path


def test_a_view_sees_what_stands_in_front_within_its_angle_and_reach():
    seen = shots.in_view(LOOKING_NORTH, [[0, 1.6, -5], [0, 1.6, 5], [9, 1.6, -5], [0, 1.6, -40], [0, 1.0, -3]])
    assert seen.tolist() == [True, False, False, False, True]


def test_a_place_with_people_fails_where_no_frame_shows_one():
    """The owner's review of 2026-10-18: no people in any film. Nobody there is no fault; someone there unseen is."""
    assert shots.people_seen(a_stage(), views()) is None
    assert shots.people_seen(a_stage(person_at=(0, 0.5, -6)), views()) == {"shot0": 4}
    assert shots.people_seen(a_stage(person_at=(0, 0.5, 6)), views()) == {"shot0": 0}


def test_a_thing_seen_moving_needs_a_sound_of_its_own():
    """The owner's review of 2026-10-18: the sound only ambient, no event sounds. A door seen sliding with no sound
    under it is named; with its sound, or looked away from, it is not."""
    assert shots.silent_moving(a_stage(), views()) == {"shot0": ["/hall/Objects/door"]}
    assert shots.silent_moving(a_stage(door_sound=True), views()) == {}
    assert shots.silent_moving(a_stage(), views(aim_z=10.0)) == {}
    assert shots.silent_moving(a_stage(), views(frames=[0])) == {}  # one frame: nothing seen moving


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
