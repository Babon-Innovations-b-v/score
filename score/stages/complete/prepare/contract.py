"""A take's inputs checked by contract before the batch, free: its row names a view of its place's plan, a box of
that view's picture that is not the whole picture, a size, and the view's picture stands in the work folder (a take
whose inputs break it is an input gap, not bought: __main__.status_of); plus the crop's risk, said apart (no
measured failure is tied to it, so it is never a predicted gap).

The crop is cut from the box with a fifth of margin and scaled up to SHORTEST_CROP on its long side when shorter
(tools/props/closeup/stage.py crop); `upscale` is that factor, read from the box alone.
"""
import pathlib

SHORTEST_CROP = 512  # tools/props/closeup/stage.py SHORTEST_CROP
MARGIN = 0.2  # tools/props/closeup/stage.py MARGIN: a fifth of the box's long side on each side
WHOLE = 0.8  # tools/props/scene/box_check.py WHOLE: a box over this share of its picture marks no place in it


def view_pictures(record):
    """{view id: its picture as written} of a place's plan."""
    return {view["id"]: view.get("picture") for view in (record.get("plan") or {}).get("views") or []}


def picture_path(written, work):
    """A view's picture as a path: `WORK/...` under `work`, else as written."""
    return pathlib.Path(work) / written.removeprefix("WORK/") if written.startswith("WORK/") else pathlib.Path(written)


def box_faults(box):
    """Why a box is not one, or None: four numbers, left above right's start and top above bottom's."""
    if not isinstance(box, list) or len(box) != 4 or not all(isinstance(side, (int, float)) for side in box):
        return "no box of four numbers"
    return None if box[0] < box[2] and box[1] < box[3] else f"box {box} has no area"


def faults(record, group, work):
    """[why] of a take's inputs that break their contract; empty when every one stands."""
    found = []
    pictures = view_pictures(record)
    if group["view"] not in pictures:
        found.append(f"view {group['view']!r} is not one of the plan's views")
    elif not pictures[group["view"]] or not picture_path(pictures[group["view"]], work).is_file():
        found.append(f"view {group['view']}'s picture is not in the work folder ({pictures[group['view']]})")
    box = box_faults(group["box"])
    if box:
        found.append(box)
    elif whole(group["box"], record.get("size")):
        found.append("its box is the whole picture, which frames no close-up (the box gate fails it)")
    if group["size"] is None or not isinstance(group["size"], list) or len(group["size"]) != 3:
        found.append("no size of three sides")
    return found


def whole(box, size):
    """Whether a box covers more than WHOLE of a picture of `size` [wide, tall] (False when the size is not said)."""
    return bool(size) and (box[2] - box[0]) * (box[3] - box[1]) > WHOLE * size[0] * size[1]


def upscale(box):
    """How much the crop is scaled up to reach SHORTEST_CROP (1.0 when it is long enough), at least: a box at the
    picture's edge loses margin there, so its crop is shorter; None with no box."""
    if box_faults(box):
        return None
    longest = max(box[2] - box[0], box[3] - box[1]) * (1 + 2 * MARGIN)
    return round(max(1.0, SHORTEST_CROP / longest), 2)
