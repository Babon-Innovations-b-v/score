"""python -m tools.characters.garments <outfit.json> --clip <clip> --out <folder> [--frames N] [--turn-views N]
[--walk-every N]: the outfit's look dressed end to end (the package docstring's steps), its measures printed."""
import argparse
import json
import os
import pathlib
import subprocess

import numpy as np

from tools.characters import garments
from tools.characters.garments import cache

BLENDER = pathlib.Path(os.environ.get("BLENDER",
                                      garments.HOME / ".farm-factory-props/blender-mcp/blender-5.2.2/blender"))
BLENDER_LIBS = BLENDER.parent.parent / "libs"  # the libraries this PC's Blender lacks (libSM, libICE)
SCORE_LIB = garments.REPO.parent / "score_lib"


def fetched(outfit, out):
    """Every library surface the outfit wears fetched from score_lib into `out`/library."""
    folder = out / "library"
    addresses = [outfit["body surface"]["address"], *[garment["surface"]["address"] for garment in outfit["garments"]]]
    subprocess.run([str(SCORE_LIB / ".venv/bin/score-lib"), "fetch", *addresses, "--into", str(folder)], check=True,
                   cwd=SCORE_LIB, stdout=subprocess.DEVNULL)
    return folder / "score_lib"


def rendered(usd, out, still, turn_views, walk_every):
    """The pictures, Blender through this PC's card queue."""
    command = ["python3", str(garments.CARD_QUEUE), "run", "--job", "garment-render", "--card-gb", "4", "--priority",
               "other", "--", str(BLENDER), "-b", "--factory-startup", "-P",
               str(garments.REPO / "tools/characters/garments/inside/render.py"), "--", str(usd), str(out),
               str(still), "0", str(turn_views), str(walk_every)]
    subprocess.run(command, check=True, env={**os.environ, "LD_LIBRARY_PATH": str(BLENDER_LIBS)},
                   stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("outfit")
    parser.add_argument("--clip", default="walking")
    parser.add_argument("--out", required=True)
    parser.add_argument("--frames", type=int, default=0, help="clip frames to run (all when 0)")
    parser.add_argument("--turn-views", type=int, default=24)
    parser.add_argument("--walk-every", type=int, default=0)
    given = parser.parse_args()
    outfit = json.loads(pathlib.Path(given.outfit).read_text())
    out = pathlib.Path(given.out)
    out.mkdir(parents=True, exist_ok=True)
    body = garments.built_body(outfit["look"], given.clip)
    pattern_folder = garments.patterns(outfit, body, out)
    drape = dict(np.load(garments.draped(outfit, body, pattern_folder, out, given.frames)))
    records = {garment["name"]: dict(np.load(pattern_folder / garment["name"] / f"{garment['name']}.npz"))
               for garment in outfit["garments"]}
    found = garments.measures(drape, dict(np.load(out / "body.npz")), records, out)
    usd = out / "outfit.usda"
    usd.unlink(missing_ok=True)
    cache.written(usd, dict(np.load(out / "body.npz")), drape, records, outfit, fetched(outfit, out), garments.RATE)
    clip_frames = len(drape[outfit["garments"][0]["name"]])
    rendered(usd, out, clip_frames // 2, given.turn_views, given.walk_every)
    print(json.dumps(found, indent=1))
    failed = [f"{name}: {line}" for name, seating in found["seating"].items() for line in seating["faults"]]
    if failed:
        raise SystemExit("a garment does not stay seated:\n" + "\n".join(failed))


main()
