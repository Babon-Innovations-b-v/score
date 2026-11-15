"""Render the planned first frames, one Blender at a time, through this PC's card queue, and save each as a JPEG.

    python3 render.py <place> ...

Each place's <work>/still.json (still.py) gives the stage, the one-view listing and the frames folder. A place is
started only while the machine has more than FREE_GB of memory available; one that is not is left for a later pass.
Appends one JSON line a place to <stills>/render.jsonl.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

STILLS = pathlib.Path(os.environ["STILLS"])
REPO = pathlib.Path(os.environ["SCORE_REPO"])
BLENDER = pathlib.Path.home() / ".farm-factory-props/blender-mcp/blender-5.2.2/blender"
QUEUE = REPO / "tools/cloud/backends/card_queue.py"
FREE_GB = 12
CARD_GB = "8"


def available_gb():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    raise RuntimeError("no MemAvailable in /proc/meminfo")


def command(still):
    blender = [str(BLENDER), "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               str(REPO / still["script"]), "--", still["stage_usda"], still["listing"], still["frames"]]
    scoped = ["systemd-run", "--user", "--scope", "--quiet", "-p", "MemoryMax=8G", "-p", "MemorySwapMax=0",
              "--setenv=FARM_CYCLES_GPU=1", f"--setenv=LD_LIBRARY_PATH={STILLS}/clibs:/usr/lib/wsl/lib", *blender]
    return ["python3", str(QUEUE), "run", "--job", f"still-{still['place']}", "--card-gb", CARD_GB,
            "--priority", "other", "--", *scoped]


def to_jpeg(png, jpeg):
    from PIL import Image
    picture = Image.open(png)
    if picture.mode == "RGBA":
        flat = Image.new("RGB", picture.size, (0, 0, 0))
        flat.paste(picture, mask=picture.getchannel("A"))
        picture = flat
    picture.convert("RGB").save(jpeg, quality=85)


def one(place):
    still = json.loads((STILLS / "work" / place / "still.json").read_text())
    free = available_gb()
    if free <= FREE_GB:
        return {"place": place, "status": "deferred", "why": f"{free:.1f} GB memory available, need over {FREE_GB}"}
    log = STILLS / "logs" / f"render-{place}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    began = time.time()
    with log.open("w") as out:
        done = subprocess.run(command(still), stdout=out, stderr=subprocess.STDOUT, cwd=REPO)
    seconds = round(time.time() - began, 1)
    png = pathlib.Path(still["frames"]) / f"{still['view']['name']}-look.png"
    if done.returncode or not png.exists():
        tail = log.read_text(errors="replace").splitlines()[-6:]
        return {"place": place, "status": "failed", "seconds": seconds, "code": done.returncode, "log": str(log),
                "why": " | ".join(tail)}
    jpeg = STILLS / "out" / f"{place}.jpg"
    to_jpeg(png, jpeg)
    return {"place": place, "status": "rendered", "seconds": seconds, "png": str(png), "jpeg": str(jpeg)}


if __name__ == "__main__":
    for name in sys.argv[1:]:
        try:
            result = one(name)
        except Exception as error:  # one place's fault is recorded and the next is drawn
            result = {"place": name, "status": "failed", "why": f"{type(error).__name__}: {error}"}
        with (STILLS / "render.jsonl").open("a") as out:
            out.write(json.dumps(result) + "\n")
        print(json.dumps(result), flush=True)
