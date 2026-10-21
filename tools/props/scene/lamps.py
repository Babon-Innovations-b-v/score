"""A kit's lamps from the design: a kit-piece row whose row kind glows (score/stages/row_kinds.py, from the row's
reading noun) gives its kind a light from the library's lamp (data/library/lamps.json) for the row's mount, its reach
from how high its laid pieces hang. No per-scene number decides it; the light sweep measures the strength after.

    light_of(row, laid)     the light a row's kind gives ({strength, reach, high, shadows}), or None
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


def mount_of(row):
    """How a row is mounted: its anchor when it is the ceiling or a wall, else it stands on something."""
    return row.get("anchor") if row.get("anchor") in ("ceiling", "wall") else "stands"


def glows(row, kinds=None):
    kinds = kinds if kinds is not None else row_kinds.table()
    return "glows" in row_kinds.does(row_kinds.kind_of(row, kinds), kinds)


def height(laid):
    """How high the laid pieces stand above the floor (their frame's y), their middle; 0 when none is laid."""
    feet = [float(piece["at"][1]) for piece in laid if "part" not in piece]
    return statistics.median(feet) if feet else 0.0


def light_of(row, laid, kinds=None, library=None):
    """The light of a row's kind laid as `laid` (its pieces), from the library's lamp for its mount; None when the
    row's kind does not glow."""
    if not glows(row, kinds):
        return None
    lamp = (library if library is not None else mounts())[mount_of(row)]
    reach = max(float(lamp["least_reach"]), float(lamp["reach_per_height"]) * height(laid))
    return {"strength": round(float(lamp["strength_per_reach"]) * reach, 3), "reach": round(reach, 2),
            "high": float(lamp["high"]), "shadows": bool(lamp["shadows"])}
