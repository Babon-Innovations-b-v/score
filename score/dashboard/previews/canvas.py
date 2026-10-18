"""The shared canvas of the top-down previews: a square matplotlib figure (Agg, no window) in the plan's colours, the
place underneath (its floor and its plan's labelled item boxes, faint), and the save that fits the view to what is
drawn, x across and z down like the plans."""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BACKGROUND = "#eeece6"
INK = "#1d2026"
FAINT = "#9a968c"
COLOURS = ("#4c6a8a", "#b4583a", "#6f8f4e", "#8a6f9e", "#c79a3b", "#3f8f8a", "#9e4f63", "#6b6862")
SIDE_INCHES = 4.5
DPI = 80


def blank(panels=1):
    """(figure, [axes]) of `panels` empty square plans side by side, no axis lines."""
    figure, found = plt.subplots(1, panels, figsize=(SIDE_INCHES * panels, SIDE_INCHES), dpi=DPI, squeeze=False)
    figure.patch.set_facecolor(BACKGROUND)
    for axes in found[0]:
        axes.set_facecolor(BACKGROUND)
        axes.set_axis_off()
    return figure, list(found[0])


def box(axes, corners, colour, alpha, label=None, fill=True):
    """A rectangle from (x0, z0, x1, z1), its label inside when given."""
    left, top = min(corners[0], corners[2]), min(corners[1], corners[3])
    wide, deep = abs(corners[2] - corners[0]), abs(corners[3] - corners[1])
    axes.add_patch(Rectangle((left, top), wide, deep, facecolor=colour if fill else "none", edgecolor=INK,
                             linewidth=0.4, alpha=alpha))
    if label:
        axes.text(left + wide / 2, top + deep / 2, label, ha="center", va="center", fontsize=6, color=INK,
                  wrap=True, clip_on=True)


def floor(axes, plan):
    """The place's floor outline from its plan (or scene record) `floor`: [[x0, z0], [x1, z1]]."""
    found = (plan or {}).get("floor")
    if found and len(found) == 2:
        box(axes, [found[0][0], found[0][1], found[1][0], found[1][1]], BACKGROUND, 1.0, fill=False)


def underlay(axes, plan):
    """The place under a map: its floor and its plan's item boxes, faint and unlabelled."""
    floor(axes, plan)
    for item in (plan or {}).get("items") or []:
        if item.get("box") and len(item["box"]) == 4:
            box(axes, item["box"], FAINT, 0.15)


def short(words, most=22):
    """A label short enough for a box: its first words up to `most` characters."""
    words = str(words)
    return words if len(words) <= most else words[:most - 1].rstrip() + "…"


def title(axes, words):
    axes.set_title(short(words, 60), fontsize=8, color=INK)


def save(figure, panels, destination):
    """Fit each panel to what is drawn (metres equal, z down), write the PNG, close the figure; the path."""
    for axes in panels:
        axes.autoscale_view()
        axes.set_aspect("equal", adjustable="datalim")
        axes.invert_yaxis()
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, format="png", facecolor=BACKGROUND, metadata={"Software": None})
    plt.close(figure)
    return destination
