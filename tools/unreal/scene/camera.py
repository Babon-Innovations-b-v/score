"""A place's film path (score/stages/place_build/film.py's film/path.json: one eye, aim, up and field of view a frame)
as a Level Sequence's cine camera (#221): a key a frame of its location, rotation and focal length, at the path's
frame rate. Plain Python with no numpy: Unreal's own Python runs it.

`fov` is the angle across the picture (degrees, tools/blender/inside/usd_views.py), so the focal length is the
filmback's half width over its half tangent. The yaw is kept continuous from frame to frame (no jump from 180 to
-180 between two keys), as the sequence's curves ease between keys.
"""
import json
import math
import pathlib

import frames

FILMBACK = (36.0, 20.25)  # millimetres: a 16:9 filmback 36 mm wide, the film's 1920 x 1080 frame


def focal_length(fov):
    """The focal length (mm) that sees `fov` degrees across FILMBACK's width."""
    return FILMBACK[0] / 2.0 / math.tan(math.radians(fov) / 2.0)


def unwound(yaws):
    """Yaws (degrees) each moved by whole turns to lie within half a turn of the one before."""
    found = []
    for yaw in yaws:
        if found:
            yaw += 360.0 * round((found[-1] - yaw) / 360.0)
        found.append(yaw)
    return found


def keys(path, basis):
    """The film path's camera keys: {fps, frames, filmback, keys [{frame, location (cm), rotation {roll, pitch, yaw},
    focal_length}]}."""
    made = json.loads(pathlib.Path(path).read_text())
    found = []
    for view in made["views"]:
        ahead = [aim - eye for aim, eye in zip(view["aim"], view["eye"])]
        found.append({"frame": view.get("frame", len(found)), "location": frames.point(basis, view["eye"]),
                      "rotation": frames.rotator(frames.turned(basis, ahead),
                                                 frames.turned(basis, view.get("up", [0.0, 1.0, 0.0]))),
                      "focal_length": focal_length(view["fov"])})
    for key, yaw in zip(found, unwound([key["rotation"]["yaw"] for key in found])):
        key["rotation"]["yaw"] = yaw
    return {"fps": made.get("fps", 24), "frames": len(found), "filmback": list(FILMBACK), "keys": found}
