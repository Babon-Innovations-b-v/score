"""python -m tools.characters.garments <outfit.json> --clip <clip> --out <folder> [--frames N] [--turn-views N]
[--walk-every N] [--turn-frame N] [--face <face.npz> --face-body <body.npz>]: the outfit's look dressed end to end
(the package docstring's steps) with its accessories (shoes, a belt: tools/characters/accessories), its measures
printed. With --face the body is the person's own with its face (tools/characters/whole)."""
import argparse
import json
import os
import pathlib
import subprocess

import numpy as np

from tools.characters import accessories, garments
from tools.characters.garments import cache

BLENDER = pathlib.Path(os.environ.get("BLENDER",
                                      garments.HOME / ".farm-factory-props/blender-mcp/blender-5.2.2/blender"))
BLENDER_LIBS = BLENDER.parent.parent / "libs"  # the libraries this PC's Blender lacks (libSM, libICE)
SCORE_LIB = pathlib.Path(os.environ.get("SCORE_LIB_ROOT", garments.REPO.parent / "score_lib"))  # its checkout


def fetched(outfit, out):
    """Every library surface the outfit wears fetched from score_lib into `out`/library."""
    folder = out / "library"
    addresses = [outfit["body surface"]["address"], *[garment["surface"]["address"] for garment in outfit["garments"]],
                 *[surface["address"] for surface in accessories.surfaces(outfit.get("accessories", {}))]]
    subprocess.run([str(SCORE_LIB / ".venv/bin/score-lib"), "fetch", *addresses, "--into", str(folder)], check=True,
                   cwd=SCORE_LIB, stdout=subprocess.DEVNULL)
    return folder / "score_lib"


def rendered(usd, out, still, turn_frame, turn_views, walk_every):
    """The pictures, Blender through this PC's card queue."""
    command = ["python3", str(garments.CARD_QUEUE), "run", "--job", "garment-render", "--card-gb", "4", "--priority",
               "other", "--", str(BLENDER), "-b", "--factory-startup", "-P",
               str(garments.REPO / "tools/characters/garments/inside/render.py"), "--", str(usd), str(out),
               str(still), str(turn_frame), str(turn_views), str(walk_every)]
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
    parser.add_argument("--turn-frame", type=int, default=0, help="clip frame the turn is drawn at (-1: the middle)")
    parser.add_argument("--face", help="the person's face.npz (tools/characters/face): worn on its own body")
    parser.add_argument("--face-body", help="body_face.py's npz the face was fitted to (with --face)")
    given = parser.parse_args()
    outfit = json.loads(pathlib.Path(given.outfit).read_text())
    out = pathlib.Path(given.out)
    out.mkdir(parents=True, exist_ok=True)
    face = {"face": given.face, "body": given.face_body} if given.face else None
    body = garments.built_body(outfit["look"], given.clip, outfit.get("body"), face)
    pattern_folder = garments.patterns(outfit, body, out)
    drape = dict(np.load(garments.draped(outfit, body, pattern_folder, out, given.frames)))
    records = {garment["name"]: dict(np.load(pattern_folder / garment["name"] / f"{garment['name']}.npz"))
               for garment in outfit["garments"]}
    found = garments.measures(drape, dict(np.load(out / "body.npz")), records, out, outfit)
    dressed = accessories.worn(outfit.get("accessories", {}), body, drape, records)
    found["accessories"] = dict(dressed["found"], faults=dressed["faults"])
    (out / "measures.json").write_text(json.dumps(found, indent=1))
    usd = out / "outfit.usda"
    usd.unlink(missing_ok=True)
    library = fetched(outfit, out)
    stage = cache.written(usd, dict(np.load(out / "body.npz")), drape, records, outfit, library, garments.RATE)
    accessories.written_into(stage, dressed, outfit.get("accessories", {}), library)
    stage.GetRootLayer().Save()
    clip_frames = len(drape[outfit["garments"][0]["name"]])
    turn_frame = clip_frames // 2 if given.turn_frame < 0 else given.turn_frame
    rendered(usd, out, clip_frames // 2, turn_frame, given.turn_views, given.walk_every)
    print(json.dumps(found, indent=1))
    failed = [f"{name}: {line}" for name, seating in found["seating"].items() for line in seating["faults"]]
    failed += [line for layer in found["layers"].values() for line in layer["faults"]]
    failed += [f"accessories: {line}" for line in dressed["faults"]]
    if failed:
        raise SystemExit("a garment or an accessory does not stay seated:\n" + "\n".join(failed))


main()
