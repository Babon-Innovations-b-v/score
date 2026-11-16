"""The scene seen from the concept's camera at preview quality: tools/blender/inside/usd_views.py (through
blender_views.py: a laid ground as the ground, see-through looks as thin glass) on this PC's card (Cycles on the card, its review samples, denoised), through the card queue, in a memory-capped scope, one Blender at
a time. Writes <folder>/render/concept-look.png and concept-mask.png (the objects' silhouette), copied to
<folder>/render.png and <folder>/render-mask.png beside the concept.

    views(record, width)        usd_views' views.json for the concept's camera at `width` pixels across
    command(folder, width)      the queued Blender command
    render(folder, width)       run it; {"render", "mask", "seconds"} or RenderFailed with the log's tail

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
# The X and GL libraries this PC's Blender needs (colon separated), put before WSL's own on LD_LIBRARY_PATH.
LIBRARIES = os.environ.get("SCORE_BLENDER_LIBS", "")
WIDTH = 768  # the preview's pixels across
FREE_GB = 12  # a Blender starts only with more memory than this available
MEMORY = "8G"  # its scope's cap
CARD_GB = "8"  # its share of the card


class RenderFailed(RuntimeError):
    """The preview render did not write its pictures."""


def views(record, width=WIDTH):
    """usd_views' listing of the one concept view, the concept's aspect kept."""
    wide, tall = record["size"]
    camera = record["camera"]
    return {"size": [width, max(1, round(width * tall / wide))], "review": True,
            "views": [{"name": "concept", "eye": camera["eye"], "aim": camera["aim"], "up": [0.0, 1.0, 0.0],
                       "fov": camera["fov"]}]}


def available_gb():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    raise RuntimeError("no MemAvailable in /proc/meminfo")


def command(folder, width=WIDTH):
    """The card queue's command rendering the scene: its views.json written into <folder>/render."""
    folder = pathlib.Path(folder).resolve()
    out = folder / "render"
    out.mkdir(exist_ok=True)
    listing = out / "views.json"
    listing.write_text(json.dumps(views(place_build.record_of(folder), width), indent=1))
    blender = [str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python", str(SCRIPT), "--",
               str(place_build.scene_path(folder)), str(listing), str(out)]
    libraries = ":".join(filter(None, [LIBRARIES, "/usr/lib/wsl/lib"]))
    scoped = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={MEMORY}", "-p", "MemorySwapMax=0",
              "--setenv=FARM_CYCLES_GPU=1", f"--setenv=LD_LIBRARY_PATH={libraries}", *blender]
    return ["python3", str(QUEUE), "run", "--job", f"place-build-{folder.name}", "--card-gb", CARD_GB,
            "--priority", "other", "--", *scoped]


def render(folder, width=WIDTH):
    """The preview rendered and copied beside the concept."""
    free = available_gb()
    if free <= FREE_GB:
        raise RenderFailed(f"{free:.1f} GB memory available, a Blender needs over {FREE_GB}")
    folder = pathlib.Path(folder)
    log = folder / "render" / "blender.log"
    queued = command(folder, width)
    for stale in ("render/concept-look.png", "render/concept-mask.png", "render.png", "render-mask.png"):
        (folder / stale).unlink(missing_ok=True)
    began = time.time()
    with log.open("w") as out:
        done = subprocess.run(queued, stdout=out, stderr=subprocess.STDOUT, cwd=REPO)
    look, mask = folder / "render" / "concept-look.png", folder / "render" / "concept-mask.png"
    if done.returncode or not look.exists():
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise RenderFailed(f"exit {done.returncode}, log {log}: {tail}")
    shutil.copyfile(look, folder / "render.png")
    shutil.copyfile(mask, folder / "render-mask.png")
    return {"render": str(folder / "render.png"), "mask": str(folder / "render-mask.png"),
            "seconds": round(time.time() - began, 1)}
