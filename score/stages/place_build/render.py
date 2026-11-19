"""The scene seen from the concept's camera at preview quality: tools/blender/inside/usd_views.py (through
blender_views.py: a laid ground as the ground, see-through looks as thin glass) on this PC's card (Cycles on the card, its review samples, denoised), through the card queue, in a memory-capped scope, one Blender at
a time. Writes <folder>/render/concept-look.png and concept-mask.png (the objects' silhouette), copied to
<folder>/render.png and <folder>/render-mask.png beside the concept.

    views(record, width, names)     usd_views' views.json for the concept's camera and the named views, `width` across
    command(folder, width, names, final)   the queued Blender command
    queued(job, script, arguments, card)   any Blender script queued so (review.py's too)
    render(folder, width, names, final)    run it; {"render", "mask", "views", "seconds"} or RenderFailed with the log's tail

A long render is started detached (tools/cloud/detached.py), never waited on in the foreground.
"""
import json
import os
import pathlib
import shutil
import subprocess
import time

from score.stages import place_build

REPO = place_build.REPO
SCRIPT = pathlib.Path(__file__).resolve().parent / "blender_views.py"
QUEUE = REPO / "tools/cloud/backends/card_queue.py"
BLENDER = pathlib.Path(os.environ.get(
    "SCORE_BLENDER", pathlib.Path.home() / ".farm-factory-props/blender-mcp/blender-5.2.2/blender"))
# Exit 127: the Blender could not start, a library it links missing.
UNLINKED = 127
WIDTH = 768  # the preview's pixels across
FINAL_SIZE = (1920, 1080)  # a final render's pixels (owner, 2026-11-16: final views at 1920x1080), whatever the concept's aspect
FREE_GB = 12  # a Blender starts only with more memory than this available
MEMORY = "8G"  # its scope's cap
CARD_GB = "8"  # its share of the card


class RenderFailed(RuntimeError):
    """The preview render did not write its pictures."""


def views(record, width=WIDTH, names=(), final=False):
    """usd_views' listing of the concept view and the named views `names` (place_build.view; their look only), the
    concept's aspect kept; at the review's samples, or the films' at FINAL_SIZE when `final`; `cut` the objects the
    camera sees through (place.json `cut`, blender_views.camera_cut)."""
    wide, tall = record["size"]
    camera = record["camera"]
    unknown = sorted(set(names) - set(record.get("views", {})))
    if unknown:
        raise place_build.Refused(f"no view {', '.join(unknown)} (views: {', '.join(record.get('views', {}))})")
    listed = [{"name": "concept", "eye": camera["eye"], "aim": camera["aim"], "up": [0.0, 1.0, 0.0],
               "fov": camera["fov"]}]
    listed += [{"name": name, "eye": record["views"][name]["eye"], "aim": record["views"][name]["aim"],
                "up": [0.0, 1.0, 0.0], "fov": record["views"][name]["fov"], "look_only": True} for name in names]
    size = list(FINAL_SIZE) if final else [width, max(1, round(width * tall / wide))]
    return {"size": size, "review": not final, "views": listed, "cut": record.get("cut") or []}


def libraries():
    """The X and GL libraries this box's Blender needs (colon separated), put before WSL's own on LD_LIBRARY_PATH:
    SCORE_BLENDER_LIBS, else the libs/ folder beside the Blender's own that tools/blender/setup.sh fills with the ones
    this box lacks."""
    return os.environ.get("SCORE_BLENDER_LIBS") or str(BLENDER.parent.parent / "libs")


def available_gb():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    raise RuntimeError("no MemAvailable in /proc/meminfo")


def command(folder, width=WIDTH, names=(), final=False):
    """The card queue's command rendering the scene: its views.json written into <folder>/render."""
    folder = pathlib.Path(folder).resolve()
    out = folder / "render"
    out.mkdir(exist_ok=True)
    listing = out / "views.json"
    listing.write_text(json.dumps(views(place_build.record_of(folder), width, names, final), indent=1))
    return queued(f"place-build-{folder.name}", SCRIPT, [str(place_build.scene_path(folder)), str(listing), str(out)])


def queued(job, script, arguments, card=True):
    """The card queue's command running a Blender script with its arguments in a memory-capped scope (with no `card`,
    the scoped command alone: an export that draws nothing waits for no card)."""
    blender = [str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python", str(script), "--",
               *arguments]
    linked = ":".join(filter(None, [libraries(), "/usr/lib/wsl/lib"]))
    scoped = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={MEMORY}", "-p", "MemorySwapMax=0",
              "--setenv=FARM_CYCLES_GPU=1", f"--setenv=LD_LIBRARY_PATH={linked}", *blender]
    if not card:
        return scoped
    return ["python3", str(QUEUE), "run", "--job", job, "--card-gb", CARD_GB,
            "--priority", "other", "--", *scoped]


def unlinked_hint(code):
    """The fix named for a Blender that could not start for a missing library (exit UNLINKED), else nothing."""
    if code != UNLINKED:
        return ""
    return (f" (a library Blender links is missing: run bash tools/blender/setup.sh, which fetches it into "
            f"{libraries()}, or set SCORE_BLENDER_LIBS)")


def render(folder, width=WIDTH, names=(), final=False):
    """The preview rendered and copied beside the concept, and each named view in `names` as <folder>/view-<name>.png."""
    free = available_gb()
    if free <= FREE_GB:
        raise RenderFailed(f"{free:.1f} GB memory available, a Blender needs over {FREE_GB}")
    folder = pathlib.Path(folder)
    log = folder / "render" / "blender.log"
    queued = command(folder, width, names, final)
    stale_views = [f"render/{name}-look.png" for name in names] + [f"view-{name}.png" for name in names]
    for stale in ("render/concept-look.png", "render/concept-mask.png", "render.png", "render-mask.png", *stale_views):
        (folder / stale).unlink(missing_ok=True)
    began = time.time()
    with log.open("w") as out:
        done = subprocess.run(queued, stdout=out, stderr=subprocess.STDOUT, cwd=REPO)
    look, mask = folder / "render" / "concept-look.png", folder / "render" / "concept-mask.png"
    if done.returncode or not look.exists():
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise RenderFailed(f"exit {done.returncode}, log {log}: {tail}{unlinked_hint(done.returncode)}")
    shutil.copyfile(look, folder / "render.png")
    shutil.copyfile(mask, folder / "render-mask.png")
    shown = {}
    for name in names:
        made = folder / "render" / f"{name}-look.png"
        if not made.exists():
            raise RenderFailed(f"the view {name} wrote no picture, log {log}")
        shutil.copyfile(made, folder / f"view-{name}.png")
        shown[name] = str(folder / f"view-{name}.png")
    return {"render": str(folder / "render.png"), "mask": str(folder / "render-mask.png"), "views": shown,
            "seconds": round(time.time() - began, 1)}
