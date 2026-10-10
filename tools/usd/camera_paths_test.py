"""Check the walkthrough camera's path on a place made here: two rooms side by side, the wall between them with one
doorway, and a path from a corner of one to the far corner of the other (the straight line between them meets the
wall) goes through the doorway and nowhere else, at eye height, clear of everything along every step; the same seed
gives the same path; a loop through both rooms closes on itself; the views are in the review walk's format; and a
place's characters, one alone and a crowd's instances, stand in the way as boxes where they stand.

Run: .venv/bin/python tools/usd/camera_paths_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_paths  # noqa: E402
import export_test  # noqa: E402
import renders  # noqa: E402
import triage_test  # noqa: E402

# The rooms: 8 m across (x from -4 to 4), 6 m along (z from -3 to 3), walls 3 m high, the wall between them at x = 0
# with a doorway 1.2 m wide (z from -0.6 to 0.6) and 2.2 m high.
DOOR_HALF = 0.6
DOOR_HIGH = 2.2


def two_rooms():
    """The two rooms' walls as one mesh standing on its foot."""
    walls = [((-4.2, 0.0, -3.2), (4.2, 3.0, -3.0)), ((-4.2, 0.0, 3.0), (4.2, 3.0, 3.2)),
             ((-4.2, 0.0, -3.0), (-4.0, 3.0, 3.0)), ((4.0, 0.0, -3.0), (4.2, 3.0, 3.0)),
             ((-0.1, 0.0, -3.0), (0.1, 3.0, -DOOR_HALF)), ((-0.1, 0.0, DOOR_HALF), (0.1, 3.0, 3.0)),
             ((-0.1, DOOR_HIGH, -DOOR_HALF), (0.1, 3.0, DOOR_HALF))]
    return trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in walls])


def rooms_stage(folder):
    (folder / "models").mkdir()
    export_test.box_gltf(folder / "models")
    export_test.box_gltf(folder / "models", "rooms", two_rooms())
    return triage_test.place_of(folder, [("rooms", "rooms", (0, 0, 0)), ("crate", "box", (-2.0, 0, 0))],
                                [triage_test.row("rooms", fixed=True), triage_test.row("crate")])


def crossings(eyes):
    """Where each step between consecutive eyes crosses the middle wall's plane (x = 0): the z of each crossing."""
    found = []
    for first, second in zip(eyes, eyes[1:]):
        if (first[0] < 0) != (second[0] < 0):
            share = first[0] / (first[0] - second[0])
            found.append(first[2] + share * (second[2] - first[2]))
    return found


def through_the_doorway_only(views, scenes, closed=False):
    eyes = np.array([view["eye"] for view in views + (views[:1] if closed else [])])
    problems = []
    if len(views) != renders.WALK_FRAMES:
        problems.append(f"{len(views)} views, not the walk's {renders.WALK_FRAMES}")
    if set(views[0]) != {"name", "eye", "aim", "up", "fov", "look_only"} or views[0]["name"] != "walk-000":
        problems.append(f"a view reads {views[0]}, not the review walk's format")
    if np.abs(eyes[:, 1] - camera_paths.EYE_HEIGHT).max() > 1e-6:
        problems.append(f"the eyes stand {eyes[:, 1].min():.3f} to {eyes[:, 1].max():.3f} m up, not at eye height")
    walls = [z for z in crossings(eyes) if abs(z) > DOOR_HALF - camera_paths.CLEARANCE + 1e-6]
    if walls or not crossings(eyes):
        problems.append(f"the path crosses the middle wall at z = {crossings(eyes)}, not only in the doorway")
    clear = camera_paths.edges_clear(scenes["blocking"], eyes[:-1], eyes[1:], 0.0)
    if not clear.all():
        problems.append(f"steps {np.flatnonzero(~clear).tolist()} pass through something")
    return problems


def a_path_between_rooms_goes_through_the_doorway():
    with tempfile.TemporaryDirectory() as temporary:
        stage = rooms_stage(pathlib.Path(temporary))
        scenes = camera_paths.place_scenes(stage)
        views = camera_paths.walk(stage, [(-3.0, 2.0), (3.0, 2.0)], seed=1)
        problems = through_the_doorway_only(views, scenes)
        if camera_paths.walk(stage, [(-3.0, 2.0), (3.0, 2.0)], seed=1) != views:
            problems.append("the same seed gave another path")
        return problems


def a_loop_round_both_rooms_closes():
    with tempfile.TemporaryDirectory() as temporary:
        stage = rooms_stage(pathlib.Path(temporary))
        scenes = camera_paths.place_scenes(stage)
        views = camera_paths.walk(stage, [(-3.0, 2.0), (3.0, -2.0), (3.0, 2.0)], closed=True, seed=3)
        problems = through_the_doorway_only(views, scenes, closed=True)
        if len(crossings(np.array([view["eye"] for view in views + views[:1]]))) < 2:
            problems.append("the loop does not come back through the doorway")
        return problems


def people_stand_in_the_way():
    """A place's characters block a path: a character's own box and a crowd's instances, each its prototype's box
    moved where the instancer stands it."""
    from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt
    with tempfile.TemporaryDirectory() as temporary:
        path = pathlib.Path(temporary) / "people.usda"
        stage = Usd.Stage.CreateNew(str(path))
        stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/place").GetPrim())
        root = UsdSkel.Root.Define(stage, "/place/Characters/walker")
        UsdGeom.Cube.Define(stage, "/place/Characters/walker/body").GetSizeAttr().Set(1.0)
        UsdGeom.Xformable(root).AddTranslateOp().Set(Gf.Vec3d(2.0, 0.5, 0.0))
        # No skeleton here, so the character's bound is given.
        root.CreateExtentAttr().Set(Vt.Vec3fArray([(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]))
        crowd = UsdGeom.PointInstancer.Define(stage, "/place/Characters/crowd")
        UsdGeom.Xformable(crowd).AddTranslateOp().Set(Gf.Vec3d(0.0, 1.0, 0.0))
        UsdGeom.Cube.Define(stage, "/place/Characters/crowd/person").GetSizeAttr().Set(0.5)
        crowd.CreatePrototypesRel().SetTargets(["/place/Characters/crowd/person"])
        crowd.CreatePositionsAttr().Set(Vt.Vec3fArray([(-3.0, 0.0, 0.0), (0.0, 0.0, 4.0)]))
        crowd.CreateProtoIndicesAttr().Set(Vt.IntArray([0, 0]))
        stage.GetRootLayer().Save()
        found = sorted(np.round(box.bounds.mean(axis=0), 3).tolist() for box in camera_paths.people(path))
    expected = [[-3.0, 1.0, 0.0], [0.0, 1.0, 4.0], [2.0, 0.5, 0.0]]
    return [] if found == expected else [f"people boxes stand at {found}, not {expected}"]


CHECKS = (a_path_between_rooms_goes_through_the_doorway, a_loop_round_both_rooms_closes, people_stand_in_the_way)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
