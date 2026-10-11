"""A place's picked viewpoints: the views the owner saved in the viewer, kept in `data/review/<place>/viewpoints.json`
as `{"place": ..., "viewpoints": [{name, eye, aim, fov, saved}]}` in the scene record's camera form (metres in the
stage's frame, y up; `fov` the angle across the picture in degrees), so the demo's films take them as their cameras
(`../demo.py`). Only the viewer's save writes here; a pick is the owner's, never written for him.
"""
import datetime
import json
import math
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
PICKS = REPO / "data/review"
PLACE_NAME = re.compile(r"^[a-z0-9_]+$")
NAME_LONGEST = 80


class BadViewpoint(ValueError):
    """A viewpoint the viewer sent that is not one: missing or non-finite numbers, a name too long."""


def path(place, root=PICKS):
    if not PLACE_NAME.match(place):
        raise BadViewpoint(f"not a place name: {place!r}")
    return root / place / "viewpoints.json"


def read(place, root=PICKS):
    """The place's picked viewpoints, in the order saved; [] when none was."""
    found = path(place, root)
    return json.loads(found.read_text())["viewpoints"] if found.exists() else []


def checked(view, taken):
    """A sent view as a viewpoint: its eye, aim and fov finite numbers, its name its own (a numbered `pick-<n>` when
    none or one already taken is given)."""
    try:
        eye, aim = [[float(part) for part in view[key]] for key in ("eye", "aim")]
        fov = float(view.get("fov", 75.0))
    except (KeyError, TypeError, ValueError) as error:
        raise BadViewpoint(f"a viewpoint needs eye, aim and fov numbers: {error}") from error
    if len(eye) != 3 or len(aim) != 3 or not all(map(math.isfinite, [*eye, *aim, fov])) or not 1 <= fov <= 170:
        raise BadViewpoint("eye and aim are three finite numbers each, fov between 1 and 170 degrees")
    if eye == aim:
        raise BadViewpoint("the eye and the aim are the same point")
    name = " ".join(str(view.get("name") or "").split())[:NAME_LONGEST]
    if not name or name in taken:
        name = next(f"pick-{number}" for number in range(1, len(taken) + 2) if f"pick-{number}" not in taken)
    return {"name": name, "eye": [round(part, 4) for part in eye], "aim": [round(part, 4) for part in aim],
            "fov": round(fov, 3), "saved": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def append(place, view, root=PICKS):
    """Save one more viewpoint for the place, written whole and then moved into place: the viewpoint as saved."""
    found = path(place, root)
    saved = read(place, root)
    viewpoint = checked(view, {each["name"] for each in saved})
    found.parent.mkdir(parents=True, exist_ok=True)
    partial = found.with_suffix(".json.partial")
    partial.write_text(json.dumps({"place": place, "viewpoints": [*saved, viewpoint]}, indent=1) + "\n")
    partial.replace(found)
    return viewpoint
