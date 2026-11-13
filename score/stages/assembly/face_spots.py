"""A thing laid against its holder's side where nothing of the holder's built surface stands behind it, slid along
the face and up or down it to the nearest spot where some does (fitting.on_face, before its back is put on that
surface): on_face keeps a face thing at its plan spot within its holder's box and, where front_face meets no surface
there, stands its back on the box's side, touching nothing. Lab's valve_3 (settle@lab, 2026-11-11), laid on pipe_3's
room side at 1.5 m, hung free 0.41 m off it: the pipe model zig-zags across its 0.9 m box, and at that height its
tube runs 0.5 m along the face from the valve's spot.

    met(surface, on, box, size, target, clear)   the foot middle, slid where its back meets the surface
"""
import numpy as np

from score.stages.assembly import fitting


def met(surface, on, box, size, target, clear=()):
    """The foot middle `target` of a thing of `size` (as laid, scaled) against its holder box's (`box`, low, high)
    side `on`'s `out` points from, kept where front_face meets the holder's built `surface` over its span (widened by
    FACE_REACH, as on_face measures it) and height; else moved to the nearest spot within the box, RAY_STEP apart
    along the face and in height, where it meets it in line with the thing's middle at its foot and at its top, so it
    stands on the surface and not on its edge, out of the boxes `clear` (the swing and passage boxes, the things laid
    on the face before it: a box (low, high) or a turned one's corners); kept where none does. Met at its top alone,
    quarters' 1.3 cm wrench was hung 0.2 m up by the slanting lower edge of its desk's back panel, across a side of
    the desk as laid, 0.12 m (settle@quarters, 2026-11-13)."""
    axis, side, sign = fitting.face_axes(on)
    below, above = fitting.beside(on, side)
    size, target = np.asarray(size, float), np.asarray(target, float)
    half = size / 2
    if fitting.front_face(surface, axis, sign, side, (target[side] - half[side] - below - fitting.FACE_REACH,
                                                      target[side] + half[side] + above + fitting.FACE_REACH),
                          (target[1], target[1] + size[1])) is not None:
        return target
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    alongs = np.arange(hold_low[side] + half[side], hold_high[side] - half[side] + 1e-9, fitting.RAY_STEP)
    heights = np.arange(hold_low[1], hold_high[1] - size[1] + 1e-9, fitting.RAY_STEP)
    taken = [(points.min(axis=0), points.max(axis=0)) for points in (np.asarray(found, float) for found in clear)]
    spots = sorted(((along, height) for along in alongs for height in heights),
                   key=lambda spot: float(np.hypot(spot[0] - target[side], spot[1] - target[1])))
    for along, height in spots:
        ends = [fitting.front_face(surface, axis, sign, side, (along, along), (level, level))
                for level in (height, height + size[1])]
        if None in ends:  # its foot or its top in line with nothing: on the surface's edge
            continue
        face = max(end * sign for end in ends) * sign
        moved = target.copy()
        moved[side], moved[1], moved[axis] = along, height, face + sign * half[axis]
        reach = np.array([half[0], 0.0, half[2]])
        if fitting.meets_any(moved - reach, moved + reach + [0.0, size[1], 0.0], taken):
            continue
        return moved
    return target
