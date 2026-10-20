"""What a film's frames see, measured free on its stage with pxr (no render): the people in view, and the things
seen moving with or without a sound of their own. The demo-film gate's people and event-sound checks (the owner's
review of 2026-10-18: no people in any film, the sound only ambient).

    seen = shots.people_seen(stage_path, views)          # {shot: frames with a person in view}, None: nobody there
    silent = shots.silent_moving(stage_path, views)      # {shot: [paths of things seen moving with no sound under them]}

A frame's view is the film's own (views.json: eye, aim, up, fov across the picture, `frame` its moment of the
stage's time). A point is in view when it stands in front of the eye, inside the picture's angle across and up
(ASPECT) and within SEEN_METRES. shortcut: nothing in front is tested, so a person behind a wall counts as seen;
upgrade to the annotate step's object ids (tools/usd/annotate.py) once the films keep them.
"""
import numpy as np

ASPECT = 16 / 9  # the films' 1280x720
# A person at this distance stands about 57 pixels tall in a 720-line frame at the films' 75 degrees: still a person.
SEEN_METRES = 25.0


def in_view(view, points, aspect=ASPECT, reach=SEEN_METRES):
    """Which of `points` ((count, 3), metres) the view sees: in front of its eye, within its angle across and up,
    and nearer than `reach`."""
    eye = np.asarray(view["eye"], dtype=float)
    ahead = np.asarray(view["aim"], dtype=float) - eye
    ahead /= np.linalg.norm(ahead)
    side = np.cross(ahead, np.asarray(view.get("up", [0.0, 1.0, 0.0]), dtype=float))
    side /= np.linalg.norm(side)
    up = np.cross(side, ahead)
    offsets = np.atleast_2d(np.asarray(points, dtype=float)) - eye
    depth = offsets @ ahead
    across = np.tan(np.radians(view.get("fov", 75.0)) / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        inside = (np.abs(offsets @ side) <= depth * across) & (np.abs(offsets @ up) <= depth * across / aspect)
    return (depth > 0) & inside & (np.linalg.norm(offsets, axis=1) <= reach)


def tools():
    """(camera_paths, demo) as the demo-film row loads them (film_tools), so the row's tools stay its declared files
    and no import here widens its code version (an `import camera_paths` here pulled snap.py and settle.py in)."""
    from score.stages import demo_film
    demo, film_checks = demo_film.film_tools()
    return film_checks.camera_paths, demo


def people_seen(stage_path, views):
    """{shot: how many of its frames see a person's middle}, or None when the stage holds nobody at any of the
    frames' moments."""
    camera_paths, demo = tools()
    corners = camera_paths.people_corners(stage_path, [view.get("frame", 0) for view in views])
    if not any(len(found) for found in corners.values()):
        return None
    seen = {}
    for view in views:
        middles = corners[view.get("frame", 0)].mean(axis=1)
        shot = demo.shot_of(view)
        seen[shot] = seen.get(shot, 0) + int(bool(len(middles)) and bool(in_view(view, middles).any()))
    return seen


def sounded(prim):
    """Whether a spatial sound stands under the prim (tools/usd/sound.py writes a motion's at <moving prim>/Sound_<n>)."""
    from pxr import Usd, UsdMedia
    return any(found.IsA(UsdMedia.SpatialAudio) for found in Usd.PrimRange(prim))


def middles_of(things, times):
    """{time: (count, 3)} each moving thing's world box middle at each time code."""
    from pxr import Usd, UsdGeom
    found = {}
    for time in times:
        cache = UsdGeom.BBoxCache(Usd.TimeCode(time), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        found[time] = np.array([list(cache.ComputeWorldBound(prim).ComputeAlignedRange().GetMidpoint())
                                for prim in things]).reshape(-1, 3)
    return found


def silent_moving(stage_path, views):
    """{shot: [the things the motion layer moves (camera_paths.moves) seen moving in it with no sound under them]}: a
    thing is seen moving in a frame when its box's middle is in view and stands elsewhere than at the shot's frame
    before."""
    from pxr import Usd
    camera_paths, demo = tools()
    stage = Usd.Stage.Open(str(stage_path))
    things = camera_paths.moves(stage)
    if not things:
        return {}
    middles = middles_of(things, sorted({view.get("frame", 0) for view in views}))
    quiet = [not sounded(prim) for prim in things]
    found, before = {}, {}
    for view in views:
        shot, now = demo.shot_of(view), middles[view.get("frame", 0)]
        moving = np.linalg.norm(now - before[shot], axis=1) > 1e-4 if shot in before else np.zeros(len(things), bool)
        before[shot] = now
        for index in np.flatnonzero(moving & in_view(view, now) & np.asarray(quiet)):
            path = str(things[index].GetPath())
            if path not in found.setdefault(shot, []):
                found[shot].append(path)
    return {shot: paths for shot, paths in found.items() if paths}
