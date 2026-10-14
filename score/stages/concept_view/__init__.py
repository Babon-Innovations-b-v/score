"""concept-views: a concept view drawn from a creator's reference picture and a written request, one world node, paid
(Nano Banana Pro through tools/props/closeup/pro.py's draw, cleared by the runner like any paid row, each call on the
Google ledger and in its cache, so a re-keyed node draws nothing again). The first: the owner's shuttle seen straight
from above and from the side (the ship plan's correction, 2026-10-14), to trace its hull outline from.

    data/definitions/concept_views.json   {"views": [{"id", "reference" (a picture under {seeds}), "wording",
                                           "shape" (landscape, portrait or square), "why"}]}

The output: <id>.png for each view and views.json (each view's request and whether a picture came back). The gate
`drawn`: every view came back as a picture whose longer side is at least LONGEST_LEAST pixels, of the shape its
request promises (its longer side over its shorter at least SHAPE_LEAST, or square within it), and not blank (its
pixels' spread at least SPREAD_LEAST); a view with no picture fails by name.
"""
import json
import pathlib
import sys

from PIL import Image, ImageStat

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
RECORD = REPO / "data/definitions/concept_views.json"
SHAPES = ("landscape", "portrait", "square")
# One 2K Pro picture a view (pro.DOLLARS_A_PICTURE, $0.134, one dollar a euro on the Google ledger), rounded up.
EUROS_A_VIEW = 0.15
LONGEST_LEAST = 1024
SHAPE_LEAST = 1.2
SPREAD_LEAST = 8.0


def record():
    """The world's concept view requests (none when the world has no record)."""
    return json.loads(RECORD.read_text()) if RECORD.exists() else {"views": []}


def files(place=None):
    """The request record and each view's reference picture."""
    return {"views": "{data}/definitions/concept_views.json",
            **{f"reference {view['id']}": view["reference"] for view in record()["views"]}}


def euros():
    """The row's estimate: one picture a view."""
    return round(EUROS_A_VIEW * max(1, len(record()["views"])), 2)


def pro_tools():
    """pro.py and the key's reader, imported with the prop tools' folders on the path."""
    tools, kept = REPO / "tools/props", list(sys.path)
    sys.path[:0] = [str(tools / "closeup"), str(tools / "cloud")]
    try:
        import pro
        import secret_store
    finally:
        sys.path[:] = kept
    return pro, secret_store


def make(inputs, out, seed, params):
    """<id>.png for each requested view, drawn by Pro from its reference and wording, and views.json."""
    pro, secret_store = pro_tools()
    views = json.loads(pathlib.Path(inputs["views"]).read_text())["views"]
    key = secret_store.secret(pro.KEY_SECRET)
    drawn = {}
    for view in views:
        reference = Image.open(inputs[f"reference {view['id']}"])
        drawn[view["id"]] = bool(pro.draw(key, view["wording"], reference, None, out / f"{view['id']}.png"))
    (out / "views.json").write_text(json.dumps({"views": [{**view, "drawn": drawn[view["id"]]} for view in views]},
                                               indent=1))


def views_faults(folder):
    return [] if (pathlib.Path(folder) / "views.json").exists() else ["no views.json"]


CONTRACT = contracts.Contract("concept-views", 1, views_faults)


def shape_of(size):
    """A picture's shape from its (wide, tall): landscape, portrait or square."""
    wide, tall = size
    if max(wide, tall) / min(wide, tall) < SHAPE_LEAST:
        return "square"
    return "landscape" if wide > tall else "portrait"


def view_faults(view, folder):
    """Why one view's picture is not the picture its request promises; none when it is."""
    path = pathlib.Path(folder) / f"{view['id']}.png"
    if not path.exists():
        return [f"{view['id']}: no picture came back"]
    picture = Image.open(path)
    found = []
    if max(picture.size) < LONGEST_LEAST:
        found.append(f"{view['id']}: {picture.size[0]} x {picture.size[1]} px, under {LONGEST_LEAST} on its "
                     "longer side")
    if shape_of(picture.size) != view["shape"]:
        found.append(f"{view['id']}: {shape_of(picture.size)}, its request promises {view['shape']}")
    spread = max(ImageStat.Stat(picture.convert("RGB")).stddev)
    if spread < SPREAD_LEAST:
        found.append(f"{view['id']}: blank (pixel spread {spread:.1f})")
    return found


def judge_drawn(output, inputs, evidence):
    """Every requested view came back as the picture its request promises (module docstring)."""
    views = json.loads((pathlib.Path(output) / "views.json").read_text())["views"]
    faults = [fault for view in views for fault in view_faults(view, output)]
    reason = "; ".join(faults[:3]) if faults else f"all {len(views)} views drawn, each the size and shape promised"
    return checks.Verdict("drawn", checks.FAIL if faults else checks.PASS, reason,
                          {"views": len(views), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("drawn", judge_drawn),)
