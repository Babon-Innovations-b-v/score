"""tools/usd/camera_paths.py: a walkthrough camera's path keeps clear of everything. On two rooms made here, side by side
with one doorway in the wall between them, a path from a corner of one to the far corner of the other (the straight
line meets the wall) goes through the doorway and nowhere else, at eye height, clear along every step, the same seed
the same path, in the review walk's format; a loop through both rooms closes on itself; a place's characters, one
alone and a crowd's instances, stand in the way as boxes where they stand, and one who walks where they stand at each
moment; a thing the stage moves stands in the way where it is at each moment, its particles and its people aside;
and an eye's clearance is its true distance from walls and people; a still view (a look the light is rendered on)
stands in free air, outside every solid with its picture not filled by a near surface, or is turned or moved till it
does (into the room it looks across, never back out of it or into an open model like a tunnel), or left out; an eye
in a domed round room as the shell builds it stands in no solid.

Breaks that turn each test red (each applied once and seen red, 2026-10-27):
- a_path_between_rooms_goes_through_the_doorway: camera_paths.leg's
  `if edges_walkable(scenes, start, goal, clearance, eye)[0]:` made `if True:` (the straight line through the wall).
- a_loop_round_both_rooms_closes: camera_paths.laid_out's `np.array(list(path) + ([path[0]] if closed else []))` made
  `np.array(list(path))` (the loop's way back left out).
- people_stand_in_the_way: camera_paths.crowd_corners' `reshape(-1, 4, 4) @ world` made `reshape(-1, 4, 4)` (a
  crowd's instances not moved with the instancer).
- a_walking_person_is_followed: camera_paths.people_corners' `single_corners(singles, Usd.TimeCode(time))` made
  `single_corners(singles, Usd.TimeCode(times[0]))` (a walker read only where they start).
- a_moving_thing_is_followed: camera_paths.moves' `if prim.GetName() in NOT_SOLID:` made `if False:` (the people and
  the particles counted as moving things).
- clearance_is_measured_on_every_side: camera_paths.mesh_tree's `[np.asarray(mesh.area_faces) > FLAT_AREA]` made
  `[np.asarray(mesh.area_faces) >= 0]` (a triangle with no area kept in FCL's tree).
- clearance_is_measured_on_every_side (its still views, 2026-11-04): camera_paths.inside_solid's `> 0` made `< 0` (the
  eye in the crate stands outside it); view_faults' `near > NEAR_MOST` made `near > 1.0` (the view off the wall
  passes); cleared_view's `if not view_faults(scenes, tried, size)` made `if True` (a blocked view kept as it is); its sort
  key `tried[0]` made `tried[1]` (every turn where it stands before any move: the wall's view turned along the wall).
- clearance_is_measured_on_every_side (a moved eye steps into its room, 2026-11-11): camera_paths.steps_in's
  `backward = inside and ...` made `backward = False` (the lamp's eye moved 0.46 m back from its look);
  `models_round(scenes, spot) <= within` made `True` (the doorway's eye moved out into the open tunnel).
- clearance_is_measured_on_every_side (a domed room holds its eyes, 2026-11-12): camera_paths.inside_solid's
  `(behind & holds).sum()` made `behind.sum()` (the eye in the domed round room stands inside a solid, its view moved);
  `holds = np.all(...)` made `holds = np.zeros(len(faces), bool)` (the eyes in the crate and the lamp stand
  outside them: neither is moved out clear).

Run: .venv/bin/python tools/usd/test_a_walk_goes_through_doorways_clear_of_everything.py
"""
import pathlib
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_paths  # noqa: E402
import test_a_creators_edit_survives_a_regenerated_base as export_test  # noqa: E402
import renders  # noqa: E402
import test_only_real_resting_faults_are_kept as triage_test  # noqa: E402

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
    clear = camera_paths.edges_clear(scenes, eyes[:-1], eyes[1:], 0.0)
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


def add_person(stage_path, name, size, at, later=None):
    """A person of a box's size standing at `at` in a place's stage, or walking from it to `later` = (time code,
    spot)."""
    from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt
    stage = Usd.Stage.Open(str(stage_path))
    root = UsdSkel.Root.Define(stage, f"{stage.GetDefaultPrim().GetPath()}/Characters/{name}")
    half = np.asarray(size, dtype=float) / 2.0
    root.CreateExtentAttr().Set(Vt.Vec3fArray([tuple(-half), tuple(half)]))  # no skeleton here, so the bound is given
    move = UsdGeom.Xformable(root).AddTranslateOp()
    move.Set(Gf.Vec3d(*at), 0.0)
    if later is not None:
        move.Set(Gf.Vec3d(*later[1]), later[0])
    stage.GetRootLayer().Save()


def a_walking_person_is_followed():
    """A person who walks is a box where they stand at each moment asked for, and a point's distance from a box is
    measured to its nearest face (0 inside)."""
    with tempfile.TemporaryDirectory() as temporary:
        stage = rooms_stage(pathlib.Path(temporary))
        add_person(stage, "walker", (0.6, 1.8, 0.6), (-3.0, 0.9, -2.0), later=(48.0, (-1.0, 0.9, -2.0)))
        found = camera_paths.people_corners(stage, [0.0, 24.0, 48.0])
        boxes = camera_paths.people(stage, [0.0, 48.0])
    middles = [float(found[time][0].mean(axis=0)[0]) for time in (0.0, 24.0, 48.0)]
    problems = [] if np.allclose(middles, [-3.0, -2.0, -1.0]) else [f"the walker stands at x = {middles}"]
    if len(boxes) != 2:
        problems.append(f"{len(boxes)} boxes over two moments of one walker, not 2")
    distances = camera_paths.box_distances(found[0.0], [-3.0, 0.9, 0.0])
    if not np.isclose(distances[0], 1.7):  # 2 m away from its middle, its half 0.3 m deep
        problems.append(f"a point 2 m from the walker's middle measures {distances[0]:.3f} m from its box, not 1.7")
    if camera_paths.box_distances(found[0.0], [-3.0, 1.6, -2.0])[0] != 0.0:
        problems.append("a point inside the walker's box is not 0 from it")
    return problems


def add_moving(stage_path, name, size, at, later):
    """A box the stage moves, its own transform keyed from `at` (time code 0) to `later` = (time code, spot), as the
    motion layer keys a rover's drive (tools/usd/motion_layer.py)."""
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_path))
    move = UsdGeom.Xform.Define(stage, f"{stage.GetDefaultPrim().GetPath()}/Objects/{name}")
    UsdGeom.Cube.Define(stage, move.GetPath().AppendChild("body")).GetSizeAttr().Set(1.0)
    UsdGeom.Xformable(move.GetPrim().GetChild("body")).AddScaleOp().Set(Gf.Vec3f(*size))
    move = move.AddTranslateOp()
    move.Set(Gf.Vec3d(*at), 0.0)
    move.Set(Gf.Vec3d(*later[1]), later[0])
    stage.GetRootLayer().Save()


def a_moving_thing_is_followed():
    """A thing the stage moves stands where it is at each moment asked for (the garage's rover drove through a film's
    camera, 2026-10-18), its children with it, the people and the particles not among the moving things; an eye clear of it
    at rest is not clear where it drives."""
    from pxr import Gf, Usd, UsdGeom
    with tempfile.TemporaryDirectory() as temporary:
        stage = rooms_stage(pathlib.Path(temporary))
        add_moving(stage, "rover", (1.0, 1.0, 1.0), (-3.0, 0.5, -2.0), (48.0, (-3.0, 0.5, 2.0)))
        add_person(stage, "walker", (0.6, 1.8, 0.6), (2.0, 0.9, 2.0), later=(48.0, (2.0, 0.9, -2.0)))
        opened = Usd.Stage.Open(str(stage))
        drift = UsdGeom.Xform.Define(opened, "/" + opened.GetDefaultPrim().GetName() + "/Effects/dust")
        drift.AddTranslateOp().Set(Gf.Vec3d(0.0, 1.0, 0.0), 0.0)
        drift.GetPrim().GetAttribute("xformOp:translate").Set(Gf.Vec3d(0.0, 2.0, 0.0), 48.0)
        opened.GetRootLayer().Save()
        reopened = Usd.Stage.Open(str(stage))
        moving = [prim.GetName() for prim in camera_paths.moves(reopened)]
        found = camera_paths.thing_corners(stage, [0.0, 24.0, 48.0])
        both = camera_paths.moving_corners(stage, [48.0])
        scenes = camera_paths.place_scenes(stage, [0.0, 24.0, 48.0])
        views = [{"eye": [-3.0, 1.0, 2.0], "frame": 0}, {"eye": [-3.0, 1.0, 2.0], "frame": 48}]
        walls, persons = camera_paths.frame_clearances(scenes, stage, views)
    problems = [] if moving == ["rover"] else [f"the moving things are {moving}, not the rover alone"]
    middles = [float(found[time][0].mean(axis=0)[2]) for time in (0.0, 24.0, 48.0)]
    if not np.allclose(middles, [-2.0, 0.0, 2.0]):
        problems.append(f"the rover stands at z = {middles}")
    if len(both[48.0]) != 2:
        problems.append(f"{len(both[48.0])} moving boxes at one moment, not the walker and the rover")
    if len(scenes["boxes"]) != 6:
        problems.append(f"{len(scenes['boxes'])} boxes over three moments of a walker and a rover, not 6")
    if not (persons[0] > camera_paths.CLEARANCE and persons[1] == 0.0):
        problems.append(f"an eye where the rover drives to measures {persons} m from it, before and after")
    return problems


def clearance_is_measured_on_every_side():
    """An eye's clearance is its true distance from the nearest wall, wherever the wall lies (behind the way it goes
    too), a mesh's triangles with no area left out of FCL's tree, and a person's box counts from inside; an edge
    is clear only when every point of it, its ends too, keeps the clearance."""
    with tempfile.TemporaryDirectory() as temporary:
        stage = rooms_stage(pathlib.Path(temporary))
        add_person(stage, "stander", (0.6, 1.8, 0.6), (2.0, 0.9, 2.0))
        scenes = camera_paths.place_scenes(stage)
    problems = []
    walls, persons = camera_paths.clearances(scenes, [[-3.9, 1.6, 2.0], [2.0, 1.6, 2.0]])
    if not np.isclose(walls[0], 0.1, atol=1e-6):
        problems.append(f"an eye 0.1 m from the west wall measures {walls[0]:.4f} m")
    if persons[1] != 0.0 or camera_paths.stands_clear(walls[1], persons[1]):
        problems.append(f"an eye inside a person's box measures {persons[1]} m from it and stands clear")
    sliver = trimesh.Trimesh([[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 0, 5], [5, 0, 5]], [[0, 1, 2], [0, 3, 4]],
                             process=False)
    alone = dict(scenes, tree=camera_paths.mesh_tree(sliver), boxes=np.zeros((0, 8, 3)))
    if not np.isclose(camera_paths.clearances(alone, [1.0, 1.0, 1.0])[0][0], 1.0):
        problems.append("a mesh with a triangle of no area measures wrong")
    away = [[-3.9, 1.6, 2.0], [-2.0, 1.6, 2.0]]  # starts by the wall and walks away from it: its rays never meet it
    along = [[-3.8, 1.6, -2.0], [-3.8, 1.6, 2.0]]
    clear = camera_paths.edges_clear(scenes, [away[0], along[0]], [away[1], along[1]], camera_paths.CLEARANCE)
    if clear.any():
        problems.append(f"edges starting 0.1 m and running 0.2 m from a wall are clear: {clear}")
    if not camera_paths.edges_clear(scenes, [-3.6, 1.6, -2.0], [-3.6, 1.6, 2.0], camera_paths.CLEARANCE)[0]:
        problems.append("an edge 0.4 m from the wall is not clear")
    return problems + still_views_stand_in_free_air(scenes)


def still_views_stand_in_free_air(scenes):
    """A still view across the west room sees it; one with its eye in the crate (a 1 m box at x = -2) is inside a
    solid, one 0.5 m off the west wall facing it sees a surface; each is cleared the least: the wall's stepped back still looking its
    way (two steps of MOVE_STEP beat six of TURN_STEP along the wall), the crate's moved out of it, and then sees the room; one shut in a closet is left out with why."""
    def view(eye, aim):
        return {"name": "view", "eye": eye, "aim": aim, "up": [0.0, 1.0, 0.0], "fov": 80}
    size, problems = (960, 540), []
    room = view([-3.5, 1.6, 2.5], [-1.0, 1.0, -1.0])
    crate = view([-2.0, 0.5, 0.0], [-1.0, 0.5, 0.0])
    wall = view([-3.5, 1.6, 0.0], [-5.0, 1.6, 0.0])
    if camera_paths.view_faults(scenes, room, size):
        problems.append(f"a view across the room is faulted: {camera_paths.view_faults(scenes, room, size)}")
    if camera_paths.view_faults(scenes, crate, size) != ["its eye stands inside a solid"]:
        problems.append(f"a view from inside the crate reads {camera_paths.view_faults(scenes, crate, size)}")
    if not any("of its picture" in fault for fault in camera_paths.view_faults(scenes, wall, size)):
        problems.append(f"a view 0.5 m off a wall reads {camera_paths.view_faults(scenes, wall, size)}")
    backed, _ = camera_paths.cleared_view(scenes, wall, size)  # two steps back beat six steps of turn along the wall
    if backed is None or not np.allclose(backed["eye"], [-3.0, 1.6, 0.0], atol=1e-3) or \
            not np.allclose(np.subtract(backed["aim"], backed["eye"]), [-1.5, 0.0, 0.0], atol=1e-3) or \
            camera_paths.view_faults(scenes, backed, size):
        problems.append(f"the wall's view is not stepped back 0.5 m still looking at it: {backed}")
    moved, _ = camera_paths.cleared_view(scenes, crate, size)
    if moved is None or camera_paths.inside_solid(scenes, moved["eye"]) or \
            camera_paths.view_faults(scenes, moved, size):
        problems.append(f"the crate's view is not moved out clear: {moved}")
    box = trimesh.creation.box(extents=(0.8, 0.8, 0.8))
    closet = trimesh.Trimesh(box.vertices, box.faces[:, ::-1], process=False)  # seen from inside: faces inward
    shut, why = camera_paths.cleared_view(dict(scenes, still=closet, blocking=closet, boxes=np.zeros((0, 8, 3)),
                                               tree=camera_paths.mesh_tree(closet),
                                               owners=np.zeros(len(closet.faces), dtype=np.int64),
                                               model_bounds=camera_paths.model_bounds([closet])),
                                          view([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]), size)
    if shut is not None or not why:
        problems.append(f"a view shut in a closet 0.8 m across is kept: {shut}")
    return problems + a_moved_eye_steps_into_its_room(view, size) + a_domed_room_holds_its_eyes(view, size)


def a_moved_eye_steps_into_its_room(view, size):
    """A room 8 m by 6 m with a doorway east (x = 4, z from -0.6 to 0.6), an open glass tunnel beyond it (x from 4.2
    to 8, 1.6 m wide) and two lamp globes 0.3 m across at eye height: the eye inside the middle lamp, looking west,
    steps out sideways or ahead, never back from its look; the eye in the doorway, 0.35 m behind the other lamp, steps
    aside in the doorway, not out into the tunnel; an eye already clear stays where it is (2026-11-11: workshop's
    from-door-2 moved 1.25 m back out of its desk into the tunnel outside its door)."""
    def slab(low, high):
        return trimesh.creation.box(bounds=(low, high))

    def lamp(at):
        return trimesh.creation.icosphere(subdivisions=2, radius=0.15).apply_translation(at)
    room = trimesh.util.concatenate([slab(*bounds) for bounds in (
        ((-4.2, 0, -3.2), (4.2, 3, -3.0)), ((-4.2, 0, 3.0), (4.2, 3, 3.2)), ((-4.2, 0, -3.0), (-4.0, 3, 3.0)),
        ((4.0, 0, -3.0), (4.2, 3, -DOOR_HALF)), ((4.0, 0, DOOR_HALF), (4.2, 3, 3.0)),
        ((4.0, DOOR_HIGH, -DOOR_HALF), (4.2, 3, DOOR_HALF)))])
    tunnel = trimesh.util.concatenate([slab(*bounds) for bounds in (
        ((4.2, 0, -0.9), (8.0, 0.05, 0.9)), ((4.2, 2.4, -0.9), (8.0, 2.5, 0.9)),
        ((4.2, 0, -0.9), (8.0, 2.4, -0.8)), ((4.2, 0, 0.8), (8.0, 2.4, 0.9)))])
    scenes = camera_paths.scenes_of({"room": room, "tunnel": tunnel, "lamp": lamp((0.0, 1.6, 0.0)),
                                     "shade": lamp((3.75, 1.6, 0.0))}, slab((-10, -0.1, -10), (10, 0, 10)),
                                    lambda flat: np.zeros(len(np.atleast_2d(flat))), np.zeros((0, 8, 3)))
    problems = []
    lit, _ = camera_paths.cleared_view(scenes, view([0.0, 1.6, 0.0], [-3.0, 1.0, 0.0]), size)
    if lit is None or lit["eye"][0] > 1e-3 or camera_paths.view_faults(scenes, lit, size):
        problems.append(f"the lamp's eye does not step clear into the room it looks across: {lit}")
    door, _ = camera_paths.cleared_view(scenes, view([4.1, 1.6, 0.0], [-3.0, 1.0, 0.0]), size)
    if door is None or door["eye"][0] > 4.2 or camera_paths.models_round(scenes, door["eye"]) or \
            camera_paths.view_faults(scenes, door, size):
        problems.append(f"the doorway's eye does not step clear in the room but into the tunnel: {door}")
    if camera_paths.models_round(scenes, [4.5, 1.6, 0.2]) != {1}:
        problems.append("an eye in the open tunnel does not stand within it")
    across = view([-2.0, 1.6, 1.5], [-3.5, 1.0, -1.0])
    if camera_paths.cleared_view(scenes, across, size) != (across, None):
        problems.append(f"a clear view across the room is moved: {camera_paths.cleared_view(scenes, across, size)}")
    return problems


def built(piece):
    """A shell piece tools/usd/builders draws ({points, triangles}) as a mesh, its faces turned as it draws them."""
    return trimesh.Trimesh(piece["points"], piece["triangles"], process=False)


def a_domed_room_holds_its_eyes(view, size):
    """A round room as the shell builds it (tools/usd/builders: its deck and 24 wall pieces slabs, whose sides face
    in, its roof a dome, which faces out): an eye in it stands in no solid and a view across it is kept as it is,
    though its rays meet the walls' and the dome's faces from behind (2026-11-12: every view of lab left out)."""
    import builders
    ring = [[6.0 * np.sin(angle), -6.0 * np.cos(angle)] for angle in np.linspace(0, 2 * np.pi, 24, endpoint=False)]
    walls = [built(builders.slab([one, two, np.multiply(two, 1.05), np.multiply(one, 1.05)], -0.2, 3.0, "wall"))
             for one, two in zip(ring, ring[1:] + ring[:1])]
    shown = {"deck": built(builders.slab(ring, -0.2, 0.0, "deck")),
             "roof": built(builders.dome(6.3, 2.8, "roof", rise=1.0)), **{f"wall_{number}": wall
                                                                          for number, wall in enumerate(walls)}}
    scenes = camera_paths.scenes_of(shown, built(builders.slab([[-9, -9], [9, -9], [9, 9], [-9, 9]], -0.4, -0.2, "x")),
                                    lambda flat: np.zeros(len(np.atleast_2d(flat))), np.zeros((0, 8, 3)))
    spot = view([1.4, 1.6, -1.6], [-2.0, 1.0, 3.0])
    problems = []
    if camera_paths.inside_solid(scenes, spot["eye"]):
        problems.append("an eye in the middle of a domed round room stands inside a solid")
    if camera_paths.cleared_view(scenes, spot, size) != (spot, None):
        problems.append(f"a view across a domed round room is moved: {camera_paths.cleared_view(scenes, spot, size)}")
    return problems


CHECKS = (a_path_between_rooms_goes_through_the_doorway, a_loop_round_both_rooms_closes, people_stand_in_the_way,
          a_walking_person_is_followed, a_moving_thing_is_followed, clearance_is_measured_on_every_side)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
