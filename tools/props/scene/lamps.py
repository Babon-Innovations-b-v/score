"""A kit's lamps from the design: a kit-piece row whose row kind glows (score/stages/row_kinds.py, from the row's
reading noun) gives its kind a light from the library's lamp (data/library/lamps.json) for the row's mount, its reach
from how high its laid pieces hang. No per-scene number decides it; the light sweep measures the strength after.

    light_of(row, laid, rows)   the light a row's kind gives ({strength, reach, high, shadows}), or None
    mount_of(row, rows)         how a row is mounted: ceiling, wall, head (a stem by its metres) or stands
    light_at(row, high, rows)   the light of a glowing row's lamp hanging `high` metres over the floor
    aimed()                     the library's lamp for a row its plan aims (a spot with its angle, reach and shaft)
"""
import json
import pathlib
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
LIBRARY = REPO / "data/library/lamps.json"
sys.path.insert(0, str(REPO / "score/stages"))
import row_kinds  # noqa: E402


def mounts(path=LIBRARY):
    return json.loads(pathlib.Path(path).read_text())["mounts"]


def aimed(path=LIBRARY):
    return json.loads(pathlib.Path(path).read_text())["aimed"]


def mount_words(path=LIBRARY):
    return json.loads(pathlib.Path(path).read_text())["mount_words"]


def mount_named(text, words):
    """The mount a row's noun or anchor names (a word of it in the library's mount words), or None."""
    said = set(row_kinds.words(text).split())
    return next((mount for mount, named in words.items() if said & set(named)), None)


# A lamp, or the row it stands on, at least this many times as tall as its widest side is a light on a stem (a post, a
# pole, a mast, a floor lamp): its bulb sits at the top, so it is mounted at its head; a squatter lamp's light sits
# within its body. Read from the row's own metres, never its words (owner, 2026-10-25: "no hax tho").
STEM = 3.0


def on_stem(row):
    """Whether a row's own metres ([wide, deep, tall]) are a stem's: tall at least STEM times its widest side."""
    size = row.get("size")
    if not isinstance(size, list) or len(size) != 3 or not all(isinstance(side, (int, float)) for side in size):
        return False
    return max(size[:2]) > 0 and size[2] >= STEM * max(size[:2])


def mount_of(row, rows=(), words=None):
    """How a row is mounted: its anchor when it is the ceiling or a wall (or names one, `mount_words`); for a row
    anchored `on:<row>` (a reading's rows), what that row is (its noun, else its own anchor, else at its head when its
    own metres are a stem's, else what it is on in turn); else at its head when its own metres are a stem's (on_stem:
    a street lamp, a floodlight tower); else it stands on something."""
    words = words if words is not None else mount_words()
    by_id = {other["id"]: other for other in rows}
    anchor, seen = row.get("anchor") or "", set()
    if not anchor.startswith("on:") and mount_named(anchor, words):
        return mount_named(anchor, words)
    while anchor.startswith("on:") and anchor[3:] in by_id and anchor[3:] not in seen:
        seen.add(anchor[3:])
        held = by_id[anchor[3:]]
        anchor = held.get("anchor") or ""
        found = mount_named(held.get("noun") or held.get("name"), words) or (
            None if anchor.startswith("on:") else mount_named(anchor, words)) or ("head" if on_stem(held) else None)
        if found:
            return found
    return "head" if on_stem(row) else "stands"


def glows(row, kinds=None):
    kinds = kinds if kinds is not None else row_kinds.table()
    return "glows" in row_kinds.does(row_kinds.kind_of(row, kinds), kinds)


def height(laid):
    """How high the laid pieces stand above the floor (their frame's y), their middle; 0 when none is laid."""
    feet = [float(piece["at"][1]) for piece in laid if "part" not in piece]
    return statistics.median(feet) if feet else 0.0


def light_of(row, laid, rows=(), kinds=None, library=None, words=None):
    """The light of a row's kind laid as `laid` (its pieces), from the library's lamp for its mount among its
    inventory's `rows`; None when the row's kind does not glow."""
    if not glows(row, kinds):
        return None
    return light_at(row, height(laid), rows, library, words)


def light_at(row, high, rows=(), library=None, words=None):
    """The light of the library's lamp for a row's mount among its inventory's `rows`, hanging `high` metres over the
    floor (its kind glowing)."""
    lamp = (library if library is not None else mounts())[mount_of(row, rows, words)]
    reach = max(float(lamp["least_reach"]), float(lamp["reach_per_height"]) * high)
    return {"strength": round(float(lamp["strength_per_reach"]) * reach, 3), "reach": round(reach, 2),
            "high": float(lamp["high"]), "shadows": bool(lamp["shadows"])}
