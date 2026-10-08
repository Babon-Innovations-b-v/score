"""How big an object's cut-out is in the target's own pixels, and which way it is drawn from that.

Plain python (no numpy), so the gate checks the limit on any box (cutsize_test.py).

  redraw    the cut-out is big enough: redraw.py redraws the object from it.
  close-up  it is too small, but the target was drawn here (target.py's takes are beside it), so
            the picture model draws the object afresh at full size, the target as its style
            reference and the object's name as its words; the cut-out is never handed in.
  dropped   too small, and the target is a picture we cannot draw again: the object is left off
            the build list and the report says so.
"""

# The shortest side, in the target's pixels, an object's box must have before its cut-out may
# feed the redraw. Measured on the habitat's round one (2026-10-02, a 1344 x 768 target): the two
# models worth keeping came from boxes 234 (bench) and 244 (counter cabinet) pixels on their short
# side; every box at 158 or under (desk, wall locker, tall cabinet, panel, water dispenser,
# monitor, lamps) gave a broken model or a redraw that copied the cut-out's blocky pixels. The
# owner: "the low-res ones look shit". Nothing between 158 and 234 was tried.
MIN_CUT_SIDE = 224

ROUTES = {
    "redraw": "redrawn from its cut-out",
    "close-up": "drawn afresh as a close-up (cut-out too small to redraw from)",
    "dropped": "too small to build from this picture",
}


def size_of(box):
    """A pixel box [left, top, right, bottom] measured: its width, height, short side and area."""
    width, height = box[2] - box[0], box[3] - box[1]
    return {"width": width, "height": height, "short_side": min(width, height), "area": width * height}


def route(box, can_close_up):
    """Which way an object is drawn: 'redraw', 'close-up' or 'dropped'."""
    if size_of(box)["short_side"] >= MIN_CUT_SIDE:
        return "redraw"
    return "close-up" if can_close_up else "dropped"
