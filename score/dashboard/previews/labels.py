"""Labels on a drawing that do not cover each other: each at its anchor when it fits there, else at the nearest free
spot around it with a thin line back to its anchor, else a number at its anchor and its words in a key under the
drawing. The panel must be fitted first (canvas.fit), so the places on the picture are final."""
from score.dashboard.previews import canvas

STEP = 13  # pixels between one try and the next
RINGS = 12
PAD = 3
DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1))
FONT = 10
KEY_FONT = 9


def item_words(name, most=30):
    """An item's label: its name up to its first comma, short enough to read at a glance."""
    return canvas.short(str(name).split(",")[0].strip(), most)


def tries(clear=0):
    """Pixel offsets from the anchor, nearest first: the anchor itself (unless the label must keep `clear` pixels
    off it, as beside a dot), then rings around it."""
    found = [] if clear else [(0, 0)]
    for ring in range(1, RINGS + 1):
        found.extend((across * (ring * STEP + clear * 3), down * (ring * STEP * 0.6 + clear))
                     for across, down in DIRECTIONS)
    return found


def overlaps(first, second):
    return not (first.x1 + PAD < second.x0 or second.x1 + PAD < first.x0
                or first.y1 + PAD < second.y0 or second.y1 + PAD < first.y0)


def free(box, taken, frame):
    """True when the box is inside the panel and covers no label already placed."""
    inside = frame.x0 <= box.x0 and box.x1 <= frame.x1 and frame.y0 <= box.y0 and box.y1 <= frame.y1
    return inside and not any(overlaps(box, other) for other in taken)


def spot_for(axes, text, anchor, taken, renderer, clear):
    """Move the text to the first free spot around the anchor; its box, or None when none is free."""
    at = axes.transData.transform(anchor)
    to_data = axes.transData.inverted()
    for across, down in tries(clear):
        text.set_position(to_data.transform((at[0] + across, at[1] + down)))
        box = text.get_window_extent(renderer)
        if free(box, taken, axes.bbox):
            return box, (across, down) != (0, 0)
    return None, False


def place(axes, labels, clear=0):
    """Draw each (words, (x, z) anchor) label, the first ones first, `clear` pixels off its anchor when it names a
    dot; the key lines of those numbered instead."""
    axes.apply_aspect()
    renderer = axes.figure.canvas.get_renderer()
    taken, keyed = [], []
    for words, anchor in labels:
        text = axes.text(*anchor, words, fontsize=FONT, ha="center", va="center", color=canvas.INK, zorder=5,
                         bbox={"boxstyle": "round,pad=0.15", "facecolor": canvas.BACKGROUND, "edgecolor": "none",
                               "alpha": 0.8})
        box, moved = spot_for(axes, text, anchor, taken, renderer, clear)
        if box is None:
            keyed.append(f"{len(keyed) + 1} {words}")
            text.set_text(str(len(keyed)))
            box, moved = spot_for(axes, text, anchor, taken, renderer, clear)
            if box is None:
                text.set_position(anchor)
                box = text.get_window_extent(renderer)
        taken.append(box)
        if moved:
            axes.annotate("", xy=anchor, xytext=text.get_position(), zorder=4,
                          arrowprops={"arrowstyle": "-", "color": canvas.FAINT, "linewidth": 0.6})
    return keyed


def key(figure, lines):
    """The numbered labels' words in a line under the drawing."""
    if lines:
        figure.text(0.02, 0.012, "   ".join(lines), fontsize=KEY_FONT, color=canvas.INK, wrap=True)
