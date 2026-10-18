"""Whether a proposal's after shows anything its before does not: each after still against the before still of the
same view (the same camera, moment, size and lamps rule, drawing.py), measured on the drawn picture alone (the label
strip under it left out), and the short before-and-after clip of its moments.

A pixel has changed when one of its colour channels moved by more than CHANGED_LEVEL of 255; a pair shows a change
when more than LEAST_CHANGED of its pixels changed. A proposal with no pair that shows a change (or with no pair at
all) is held out of the basket with its plain reason (`held`), never shown as a fix."""
import pathlib
import shutil
import subprocess
import tempfile

import numpy
from PIL import Image

# finish.before_stills' words when the place has nothing accepted to draw: its after is all new, so it is shown.
NOTHING_ACCEPTED = "has nothing accepted yet"
CHANGED_LEVEL = 24
LEAST_CHANGED = 0.005
CLIP_RATE = 2
CLIP_WIDE = 480


def drawn_part(path, size):
    """The still's picture as a numpy array, its label strip under it cut off (the top `size` of it)."""
    with Image.open(path) as found:
        picture = found.convert("RGB")
    wide, tall = size
    return numpy.asarray(picture.crop((0, 0, min(wide, picture.width), min(tall, picture.height))), dtype=numpy.int16)


def pair_difference(before, after, size):
    """{mean, changed} of one pair: the mean difference in levels of 255 over every channel, and the share of pixels
    that changed (CHANGED_LEVEL)."""
    old, new = drawn_part(before, size), drawn_part(after, size)
    if old.shape != new.shape:
        return {"mean": 255.0, "changed": 1.0}
    moved = numpy.abs(new - old)
    changed = (moved.max(axis=2) > CHANGED_LEVEL).mean()
    return {"mean": round(float(moved.mean()), 3), "changed": round(float(changed), 5)}


def pairs(folder, stills, before):
    """[(name, before path, after path)] of every after still with a before still of the same view."""
    befores = {still["name"]: still["file"] for still in before if "file" in still}
    return [(still["name"], pathlib.Path(folder) / befores[still["name"]], pathlib.Path(folder) / still["file"])
            for still in stills if "file" in still and still["name"] in befores]


def why_held(record, measured):
    """The plain reason a proposal is held out of the basket, or None when its pictures show its change."""
    if not any("file" in still for still in record.get("stills") or []):
        failed = next((still["error"] for still in record.get("stills") or [] if "error" in still), "none was drawn")
        return f"No after picture: {failed[:300]}"
    if not measured and any(NOTHING_ACCEPTED in still.get("error", "") for still in record.get("before") or []):
        return None  # a place with nothing accepted yet: all of its after is new
    if not measured:
        failed = next((still["error"] for still in record.get("before") or [] if "error" in still), "")
        return "No before picture from the same cameras" + (f": {failed[:300]}" if failed else "")
    if any(pair["changed"] > LEAST_CHANGED for pair in measured.values()):
        return None
    most = max(pair["changed"] for pair in measured.values())
    unshown = (record.get("drawing") or {}).get("unshown") or []
    tail = (" What it changes is made by the paid batch, and no free preview of that step is drawn yet."
            if unshown else "")
    return (f"From the same cameras the after looks the same as the before (at most {most * 100:.2f}% of a picture "
            f"changed, under the {LEAST_CHANGED * 100:.1f}% it takes).{tail}")


def difference(folder, record):
    """The record's `difference`: {commit, pairs: {view: {mean, changed}}, shows_change, held, rule}."""
    size = (record.get("drawing") or {}).get("size") or [640, 360]
    measured = {name: pair_difference(before, after, size)
                for name, before, after in pairs(folder, record.get("stills") or [], record.get("before") or [])}
    held = why_held(record, measured)
    return {"commit": record["commit"], "pairs": measured, "shows_change": held is None, "held": held,
            "rule": {"changed_level": CHANGED_LEVEL, "least_changed": LEAST_CHANGED}}


def clip(folder, record, out):
    """The before and after of the drawing's clip views side by side, CLIP_RATE frames a second, as an mp4 at `out`
    (ffmpeg); the media entry, or None when the drawing has no clip or a frame is missing."""
    names = (record.get("drawing") or {}).get("clip") or []
    found = {name: (before, after) for name, before, after in pairs(folder, record.get("stills") or [],
                                                                     record.get("before") or [])}
    if len(names) < 2 or any(name not in found for name in names):
        return None
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-clip-"))
    try:
        for number, name in enumerate(names):
            before, after = found[name]
            with Image.open(before) as old, Image.open(after) as new:
                side = Image.new("RGB", (old.width + new.width, max(old.height, new.height)))
                side.paste(old.convert("RGB"), (0, 0))
                side.paste(new.convert("RGB"), (old.width, 0))
                side.save(work / f"{number:04d}.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(CLIP_RATE), "-i", str(work / "%04d.png"),
                        "-vf", f"scale={2 * CLIP_WIDE}:-2", "-pix_fmt", "yuv420p", str(out)], check=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"name": out.name, "kind": "film", "file": f"media/{out.name}", "bytes": out.stat().st_size,
            "said": "before (left) and after (right) at the same moments, a local preview"}
