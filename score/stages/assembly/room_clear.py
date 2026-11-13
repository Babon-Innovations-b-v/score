"""Things nothing holds kept out of the straight wall pieces the parting and moved_out leave them in (fitting.fitted
calls cleared after moved_out; assembly@walkway failed its resting gate on them, 2026-11-12).

    cleared(stage, place, entries)    each thing still in a wall piece narrowed to its room or moved out of the wall
    into_room(low, high, box, axis, pieces)   the move that brings a thing reaching into a wall piece into its room

The parting takes a thing inside a wall by more than HELD_MOST every way, and moved_out one reaching into it by
HELD_MOST at most across it (fitting.shallow_out); neither takes the rest:
- walkway's ceiling ducts, built 11.94 m long under a roof between walls 11.87 m apart, were moved 0.035 m out of
  wall_1 and so 0.069 m into wall_3 (0.0375 by surface, past the resting check's 0.03): no move clears both ends, so
  a thing longer than the room between two facing walls is narrowed along it to that room, between their faces.
- its floor lights, 4.7 cm wide, were laid wholly in wall_4's 12.6 cm thickness, 0.05 m from its room face: never
  inside it HELD_MOST every way (they are thinner), and 0.0003 m past moved_out's step, so a thing in a wall piece
  is moved the shorter way out of it across its thickness, at most that thickness.
"""
import numpy as np

from score.stages.assembly import lamps_along

# A thing longer than the room between two facing wall pieces is narrowed along it to fit where that keeps this share
# of its length; one that would need more is left for the held gate to name.
SHRINK_MOST = 0.9


def thin_axis(box):
    """The floor axis (0 x, 2 z) a straight wall piece's box (low, high) is thin along."""
    size = np.asarray(box[1], float) - np.asarray(box[0], float)
    return 0 if size[0] <= size[2] else 2


def room_face(box, axis, middle):
    """Where along `axis` a wall piece's box (low, high) faces a point `middle` along it: its side nearer it."""
    return float(box[0][axis]) if middle <= (float(box[0][axis]) + float(box[1][axis])) / 2 else float(box[1][axis])


def facing(box, axis, low, high, pieces):
    """The wall piece box of `pieces` thin along `axis` across a thing's box (low, high) from `box`, on the other side
    of its middle, sharing its reach across and its height, nearest it; None with none."""
    middle = (float(low[axis]) + float(high[axis])) / 2
    side = 1.0 if (float(box[0][axis]) + float(box[1][axis])) / 2 > middle else -1.0
    other = 2 - axis
    found = [piece for piece in pieces if thin_axis(piece) == axis and piece is not box
             and side * ((float(piece[0][axis]) + float(piece[1][axis])) / 2 - middle) < 0
             and min(float(high[other]), float(piece[1][other])) > max(float(low[other]), float(piece[0][other]))
             and min(float(high[1]), float(piece[1][1])) > max(float(low[1]), float(piece[0][1]))]
    return min(found, key=lambda piece: abs((float(piece[0][axis]) + float(piece[1][axis])) / 2 - middle),
               default=None)


def narrowed(low, high, box, axis, pieces):
    """(scale [x, y, z], the new foot middle) of a thing's box (low, high) longer along `axis` than the room between
    the wall piece `box` it reaches into and the one facing it across it (facing): narrowed along it to that room,
    between the two faces; None where it fits the room, no piece faces it, or it would keep less than SHRINK_MOST."""
    from score.stages.assembly import fitting
    other = facing(box, axis, low, high, pieces)
    if other is None:
        return None
    middle = (float(low[axis]) + float(high[axis])) / 2
    ends = sorted((room_face(box, axis, middle), room_face(other, axis, middle)))
    room, length = ends[1] - ends[0], float(high[axis] - low[axis])
    if room >= length or room < SHRINK_MOST * length:
        return None
    scale = np.ones(3)
    scale[axis] = room / length
    target = fitting.foot_middle(low, high)
    target[axis] = (ends[0] + ends[1]) / 2
    return scale, target


def into_room(low, high, box, axis, pieces):
    """The move [x, y, z] along `axis` that brings a thing's box (low, high), reaching into the wall piece `box`, wholly
    into the room between that piece and the one facing it across the thing (facing), the least way; None where no
    piece faces it or the thing is longer than that room. Quarters' wall pipe, 4 m long in a 4.23 m room, hung up to
    its roof from its plan spot ran 1.74 m on through its east wall (settle@quarters, 2026-11-13)."""
    other = facing(box, axis, low, high, pieces)
    if other is None:
        return None
    middle = (float(low[axis]) + float(high[axis])) / 2
    near, far = sorted((room_face(box, axis, middle), room_face(other, axis, middle)))
    if float(high[axis] - low[axis]) > far - near:
        return None
    move = np.zeros(3)
    move[axis] = max(near - float(low[axis]), 0.0) + min(far - float(high[axis]), 0.0)
    return move


def moved_across(low, high, box, axis, statics):
    """The move [x, y, z] the shorter way along `axis` that takes a thing's box (low, high) out of the wall piece
    `box`, where that is no more than the wall's thickness (a thing laid in the wall, never one across it: the parting
    leaves a ship longer than its place across its wall for the held gate) and leaves it in none of the `statics`
    [(name, box)] by more than the resting check's touch (floor_clear.TOUCH); None where none does."""
    from score.stages.assembly import fitting, floor_clear
    ahead = float(box[1][axis] - low[axis])
    back = float(high[axis] - box[0][axis])
    move = np.zeros(3)
    move[axis] = ahead if ahead <= back else -back
    if abs(move[axis]) > float(box[1][axis] - box[0][axis]):
        return None
    if any(fitting.depths(low + move, high + move, found).min() > floor_clear.TOUCH for _, found in statics):
        return None
    return move


def cleared(stage, place, entries):
    """Each thing nothing holds (`entries`, laid and active) reaching into a straight wall piece (fitting.statics,
    straight) by more than the resting check's touch every way: narrowed along the wall's thin axis to the room
    between it and the piece facing it across the thing where it is longer than that room (narrowed), else moved the
    shorter way out of it across its thickness (moved_across); the fits [{name, how "out", ...}]."""
    from score.stages.assembly import fitting, floor_clear
    statics = fitting.statics(fitting.walls(stage, place))
    pieces = [box for name, box in statics if name.split("_")[0] == "wall" and fitting.straight(box)]
    fits = []
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        for box in pieces:
            low, high = fitting.world_box(stage, path)
            if fitting.depths(low, high, box).min() <= floor_clear.TOUCH:
                continue
            axis = thin_axis(box)
            shrunk = narrowed(low, high, box, axis, pieces)
            if shrunk is not None:
                scale, target = shrunk
                fitting.moved_by(stage.GetPrimAtPath(path), fitting.foot_middle(low, high), scale, target)
                fits.append(fitting.laid_fit(
                    stage, path, entry, "out", None, abs(float(target[axis] - fitting.foot_middle(low, high)[axis])),
                    scale, f"narrowed to {float(scale[axis]):.1%} along its room between its walls: built "
                           f"{float(high[axis] - low[axis]):.3f} m long, longer than the room"))
                continue
            move = moved_across(low, high, box, axis, [(name, found) for name, found in statics if found is not box])
            if move is None:
                continue
            foot = fitting.foot_middle(low, high)
            lamps_along.moved_with(stage, place, low, high, foot, 1.0, foot + move)  # its lamps with it
            fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
            fits.append(fitting.laid_fit(stage, path, entry, "out", None, float(np.abs(move).max()), 1.0,
                                         f"moved {float(np.abs(move).max()):.3f} m out of a wall it was laid in"))
    return fits
