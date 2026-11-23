"""A close-up's camera fitted from the model's outline (#171, PRD #159): TRELLIS.2 gives a model but no camera for the
picture it was made from, so nothing could be laid on it through the close-up (its colours, its printed marks). The
model is laid at the close-up's heading (place_build/maker/fit.headed), so the camera is looked for near the close-up
style's own view (its turn and look-down, maker.close_up_view): each tried view (turn, look-down, vertical field) is
framed so the model's outline spans the close-up's opaque box (`framed`), and the one whose cast outline best overlaps
the close-up's (intersection over union at FIT_SIDE pixels, route_cast's own cast) is kept, searched coarse then fine.

    fitted_camera(model, cut, turn, down) -> camera record (route_cast.close_up_camera reads it: its `look`)

The record says its fit; route_cast.CLOSE_UP_FIT decides, as for Pixal3D's own camera, whether a cast through it is
trusted.
"""
import numpy as np

import route_cast as cast

FIT_SIDE = 128  # the outlines are compared at about this many pixels across the close-up's longer side
COARSE = {"turn": (-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0), "down": (-8.0, -4.0, 0.0, 4.0, 8.0),
          "field": (20.0, 25.0, 30.0, 35.0, 40.0, 50.0)}
FINE = {"turn": (-2.0, -1.0, 0.0, 1.0, 2.0), "down": (-2.0, -1.0, 0.0, 1.0, 2.0), "field": (-2.5, 0.0, 2.5)}
FRAMING_STEPS = 12


def axes(turn, down):
    """(right, up, back) of a view turned `turn` degrees and looking down `down` (maker/fit.view_axes' frame)."""
    from score.stages.place_build.maker import fit
    right, up = fit.view_axes(turn, min(down, 90.0))
    return right, up, np.cross(right, up)


def projected(points, eye, right, up, back, focal, size):
    """The picture places ([column, row]) of `points` seen from `eye` along -`back`, `focal` pixels a unit away."""
    relative = points - eye
    depth = np.maximum(-(relative @ back), 1e-6)
    return np.c_[relative @ right / depth * focal + size[0] / 2, size[1] / 2 - relative @ up / depth * focal]


def framed(points, view, box, size):
    """The eye from which `points` (the model's hull, normalised frame) seen along `view` (right, up, back, focal)
    span the close-up's opaque `box` (left, top, right, bottom pixels): moved along the view to match the box's
    larger side and across it to match its middle, FRAMING_STEPS times."""
    right, up, back, focal = view
    target = points.mean(0)
    distance = 3.0
    for _ in range(FRAMING_STEPS):
        eye = target + back * distance
        seen = projected(points, eye, right, up, back, focal, size)
        low, high = seen.min(0), seen.max(0)
        spans = (high - low) / np.maximum(np.array([box[2] - box[0], box[3] - box[1]], dtype=float), 1.0)
        middle = (low + high) / 2 - [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]
        distance *= float(spans.max())
        target = target + (middle[0] * right - middle[1] * up) * distance / focal
    return target + back * distance


def overlap(model, camera, seen, size):
    """The cast outline's intersection over union with the close-up's (`seen`, sampled at the cast's pixels)."""
    step = max(1, round(max(size) / FIT_SIDE))
    columns, rows = np.meshgrid(np.arange(0, size[0], step), np.arange(0, size[1], step))
    faces, _ = cast.cast_points(model, camera, size, np.c_[columns.ravel() + 0.5, rows.ravel() + 0.5])
    hit, shown = faces >= 0, seen[rows.ravel(), columns.ravel()]
    return float((hit & shown).sum() / max((hit | shown).sum(), 1))


def tried(model, hull, cut, view):
    """(fit, camera) of one view (turn, look-down, vertical field in degrees) framed on the close-up `cut`."""
    turn, down, field = view
    size = (cut.shape[1], cut.shape[0])
    rows, columns = np.nonzero(cut)
    box = (columns.min(), rows.min(), columns.max() + 1, rows.max() + 1)
    right, up, back = axes(turn, down)
    focal = size[1] / 2 / np.tan(np.radians(field) / 2)
    eye = framed(hull, (right, up, back, focal), box, size)
    middle, side = model.frame
    camera = (eye * side + middle, right, up, 2 * np.arctan(size[0] / 2 / focal))
    return overlap(model, camera, cut, size), camera


def searched(model, hull, cut, around, steps):
    """The best (fit, camera, view) over every view `steps` round `around` (turn, look-down, vertical field)."""
    best = None
    for turn in steps["turn"]:
        for down in steps["down"]:
            for field in steps["field"]:
                view = (around[0] + turn, around[1] + down, around[2] + field)
                if view[2] <= 0:
                    continue
                fit, camera = tried(model, hull, cut, view)
                if best is None or fit > best[0]:
                    best = (fit, camera, view)
    return best


def fitted_camera(model, cut, turn, down):
    """The camera record (route_cast.close_up_camera's: camera_angle_x and its `look`, eye, right and up in the model
    file's own frame) whose cast outline of `model` (a route_cast.Model) best overlaps the close-up `cut` (its opaque
    pixels, rows down), looked for round the close-up style's view (`turn`, `down` degrees); its fit and view."""
    hull = np.asarray(model.mesh.convex_hull.vertices, dtype=float)
    coarse = searched(model, hull, cut, (turn, down, 0.0), COARSE)
    fit, camera, view = searched(model, hull, cut, coarse[2], FINE)
    eye, right, up, field = camera
    return {"camera_angle_x": float(field),
            "look": {"eye": [float(value) for value in eye], "right": [float(value) for value in right],
                     "up": [float(value) for value in up]},
            "fitted": {"turn": view[0], "down": view[1], "field_vertical": view[2], "fit": round(fit, 4),
                       "from": "the model's outline against the close-up's (close_up_fit.py)"}}
