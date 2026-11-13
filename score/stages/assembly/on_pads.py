"""A thing nothing holds, laid with its middle on a raised floor piece (a pad a row lays on the floor:
design_shell.floor_pieces, its slab's low at the floor or over it) but across that piece's edge, turned a quarter about
its middle where that lays its footprint wholly on the piece. The scene record lays a row deeper than wide with its
long side across its item's facing (writer.yaw_turn), whatever the item's box says: on a pad laid for it, the thing
stands half on the pad and half on the floor beside it, its weight on one end.

settle@hangar, 2026-11-13: its spaceship (28.4 by 13.8 m built) was laid across the hall on its 15.6 by 39.8 m landing
pad, which the plan lays along the hall under the ship's 13.7 by 46 m item; parted 6.9 m off a wall, its port gear
stood on the deck and its starboard on the pad, and the resting gate failed it tipping, its weight 6.7 m outside what
it touched. Turned a quarter it lies wholly on the pad. Here, before the fitting parts what is laid (made_waiting.lay),
not in the scene record, whose writer every place's record and every row after it hash.

    turned(entry, record, matrix, low, high)   the matrix laying a model's box (low, high) for the entry, turned a
                                               quarter about its middle where the rule above says so, else as given
"""
import numpy as np

# How far, metres, a footprint's corner may stand past a piece's outline and still lie on it.
EDGE = 0.01


def pieces(record):
    """[outline [n, 2] (x, z)] of the record's raised floor pieces: each slab a row lays on the floor, its low at the
    floor or over it (a landing pad, floor grates), never a level's deck under the floor."""
    return [np.asarray(entry["points"], float) for entry in record.get("structure") or []
            if entry.get("builder") == "slab" and entry.get("row") and len(entry.get("points") or []) >= 3
            and float(entry.get("low", -1.0)) >= 0.0]


def footprint(matrix, low, high):
    """[4, 2] (x, z) corners of a model's box (low, high) laid by `matrix` (a Gf.Matrix4d, row vectors), seen from
    above."""
    from pxr import Gf
    corners = [matrix.Transform(Gf.Vec3d(x, low[1], z)) for x in (low[0], high[0]) for z in (low[2], high[2])]
    return np.array([[corner[0], corner[2]] for corner in corners])


def on_piece(points, outline):
    """Which points [n, 2] lie on a piece's outline [m, 2] (within EDGE of it)."""
    from matplotlib.path import Path
    return Path(outline).contains_points(points, radius=EDGE) | Path(outline[::-1]).contains_points(points,
                                                                                                    radius=EDGE)


def quarter(matrix, middle):
    """`matrix` turned a quarter about up through `middle` (x, z)."""
    from pxr import Gf
    there = Gf.Vec3d(float(middle[0]), 0.0, float(middle[1]))
    turn = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), 90.0))
    return matrix * Gf.Matrix4d().SetTranslate(-there) * turn * Gf.Matrix4d().SetTranslate(there)


def turned(entry, record, matrix, low, high):
    """The matrix laying the entry's model box (low, high): `matrix` turned a quarter about its middle where nothing
    holds the entry (no `on`, filling nothing, not hung from the roof), its footprint reaches past a raised floor
    piece (pieces) it lies wholly on turned (its middle on it, then); else `matrix`."""
    if entry.get("on") or entry.get("fills") or entry.get("under roof"):
        return matrix
    laid = footprint(matrix, low, high)
    turn = quarter(matrix, laid.mean(axis=0))
    for outline in pieces(record):
        if not on_piece(laid, outline).all() and on_piece(footprint(turn, low, high), outline).all():
            return turn
    return matrix
