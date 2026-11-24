"""A place's film path (score/stages/place_build/film.py's film/path.json: one eye, aim, up and field of view a frame)
as a Level Sequence's cine camera (#221): a key a frame of its location, rotation and focal length, at the path's
frame rate. Plain Python with no numpy: Unreal's own Python runs it.

`fov` is the angle across the picture (degrees, tools/blender/inside/usd_views.py), so the focal length is the
filmback's half width over its half tangent. The yaw is kept continuous from frame to frame (no jump from 180 to
-180 between two keys), as the sequence's curves ease between keys. The path is in its place's own frame; a package
seated in its area's frame (scene.json `seat`) has its path's eyes and ways turned and shifted onto that seat first,
or the camera stands where the place stood before it was seated (#222, run 9: 27 m off the street, behind a block).
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


def on_seat(seat, way, shifted):
    """A place-frame point (`shifted`) or way as the package's seat lays it (`seat`: scene.json's 16 numbers, column by
    column like a copy's matrix; None: the package is in its place's own frame)."""
    if seat is None:
        return list(way)
    rows = frames.column_matrix(seat)
    return [sum(rows[row][column] * way[column] for column in range(3)) + (rows[row][3] if shifted else 0.0)
            for row in range(3)]


def unlanded(values, counts, keys):
    """Why a sequence section's keys did not all land (None when they did): `values` a key gives, `counts` the keys
    each of the section's channels holds after keying (its channel order), `keys` the path's keys. A section with
    fewer channels than a key's values, or a channel holding fewer keys, leaves the camera where it was spawned (#222,
    runs 9 and 10)."""
    if len(counts) < values:
        return f"the section has {len(counts)} channels, a key {values} values"
    short = [(index, count) for index, count in enumerate(counts[:values]) if count != keys]
    if short:
        return "channels holding other than the path's {} keys: {}".format(
            keys, ", ".join(f"{index}: {count}" for index, count in short))
    return None


def keys(path, basis, seat=None):
    """The film path's camera keys, its views laid on the package's `seat` (on_seat): {fps, frames, filmback, keys
    [{frame, location (cm), rotation {roll, pitch, yaw}, focal_length}]}."""
    made = json.loads(pathlib.Path(path).read_text())
    found = []
    for view in made["views"]:
        ahead = on_seat(seat, [aim - eye for aim, eye in zip(view["aim"], view["eye"])], False)
        found.append({"frame": view.get("frame", len(found)),
                      "location": frames.point(basis, on_seat(seat, view["eye"], True)),
                      "rotation": frames.rotator(frames.turned(basis, ahead), frames.turned(
                          basis, on_seat(seat, view.get("up", [0.0, 1.0, 0.0]), False))),
                      "focal_length": focal_length(view["fov"])})
    for key, yaw in zip(found, unwound([key["rotation"]["yaw"] for key in found])):
        key["rotation"]["yaw"] = yaw
    return {"fps": made.get("fps", 24), "frames": len(found), "filmback": list(FILMBACK), "keys": found}
