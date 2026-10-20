"""Make a model from a picture on the locked route: the one way any session runs Pixal3D.

    ~/.farm-factory-props/env/bin/python tools/props/pixal.py <picture.png> <name> --who "<session>"
        [--faces 40000] [--seed 1] [--steps 12] [--long] [--feet] [--tube] [--finish-only] [--paint-from <unlit.png>]

On this PC only --finish-only runs: steps 1 and 2 load models, and no model runs here (owner,
2026-10-03; local_models.py refuses them and names the cloud batch, cloud/batch.py, which runs both
on a rented card and brings the raw model back with its camera folder).

Four steps, and only the second touches the graphics card:
1. Cut the subject out of its background (BiRefNet-lite, on the processor).
2. Build the model with Pixal3D (image-to-3dlab's pixal3d_generate.py, --steps 12 --gss 10). This
   step alone holds the card, through card.claimed(), so runs from every session queue instead of
   colliding, and it lets go as soon as the generator starts writing its file. Two Pixal3D runs
   may share the card (measured safe, card.py); a third, or a picture run, waits. Two runs on one card crash the box, which is why nothing else may call
   image-to-3dlab's generator or trellis-cli (Pixal3D's own binary, named for the TRELLIS.2 code
   pixal3d.cpp is built on) directly.
3. Finish it cleanly (clean_finish.py): loose specks dropped, thinned to --faces by the lab's
   voxel remesh and collapse, unwrapped again by xatlas, base colour and metal baked with hard
   edges and no detail normal map, then Pixel Match puts the picture's own pixels back on every
   surface it sees, using the camera folder the generator keeps beside the raw model
   (<name>.svviews; rebuilding it from the picture needs the cut-out, so it is refused here like
   step 1). On the processor.
4. Stand it upright and pad its maps (glb_file.py), on the processor.

Before step 3, a raw model image-to-3dlab 0.3.9+ turned half round to face +Z (its glb_turn stamp in
asset.extras), and the camera folder turned with it, are turned back to Pixal3D's own -Z in place
(facing_back): everything here that reads a raw model or its camera folder (the finish, labels.py's
seen faces, the outline, the splits, the turntables) reads them in that frame.

Writes <name>.glb (the raw model), <name>-<faces>.glb (finished) and <name>-final.glb (upright and
padded, the one to import) under WORK/pixal/, with each finishing step's file and log in
<name>-<faces>/. --finish-only redoes steps 3 and 4 from the raw model already there, which is how
a model already in the game is re-finished.
"""
import argparse
import contextlib
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

from card import claimed
from local_models import refuse_here
from paths import IMAGE_TO_3DLAB, REPO, WORK

sys.path.insert(0, str(REPO / "vendor" / "image-to-3dlab"))
from image_to_3dlab.glb_turn import CAMERA_KEY, FACING_KEY, VIEW_TURN  # noqa: E402

# Where every Pixal3D step runs instead of this PC (local_models.py).
CLOUD = 'tools/props/cloud/batch.py <list.txt> --who "<session>" (one line a model: name picture options)'

LAB_PYTHON = IMAGE_TO_3DLAB / ".venv" / "bin" / "python"
OUT = WORK / "pixal"
# The settings the owner locked the route on (#55): 12 steps, and structure guidance 10, which
# keeps thin parts the default drops. --steps changes the steps for one run (the P2 benchmark,
# score/stages/complete/prepare/pixal_steps.py); a shape's lower steps are taken only from there,
# with the owner's yes on #55.
STEPS, GUIDANCE = 12, 10
# The generator's banner for its last stage, writing the file, which needs no card.
WRITING = "[6/6]"
# Half a turn about glTF's up axis (y): undoes image-to-3dlab's glb_turn, which is its own inverse.
HALF_TURN = np.diag([-1.0, 1.0, -1.0])


def say(line):
    print(f"[pixal] {line}", file=sys.stderr, flush=True)


def cut_out(picture):
    """The picture cut out of its background, written beside it; the path to the cut-out.
    BiRefNet is a model, so a new cut-out is refused on this PC (local_models.py); one already
    made beside the picture (the lab's <stem>__matted.png) is used as it is."""
    made = pathlib.Path(picture).with_name(f"{pathlib.Path(picture).stem}__matted.png")
    if made.is_file():
        return str(made)
    refuse_here("the cut-out (BiRefNet)", CLOUD)
    code = ("import sys, pathlib; sys.path.insert(0, 'scripts'); "
            "from pixal3d_generate import matte; "
            f"print(matte(pathlib.Path({str(picture)!r}))[0])")
    done = subprocess.run([str(LAB_PYTHON), "-c", code], cwd=IMAGE_TO_3DLAB, check=True,
                          capture_output=True, text=True)
    return done.stdout.strip().splitlines()[-1]


def generator_arguments(cut, raw, seed, steps=STEPS):
    """The generator's script and arguments on the locked route (`steps` its sampling steps), run
    from image-to-3dlab; the cloud batch runner (cloud/batch.py) runs these same ones on a rented card."""
    return ["scripts/pixal3d_generate.py", str(cut), str(raw), "--seed", str(seed),
            "--steps", str(steps), "--gss", str(GUIDANCE)]


def generate(cut, raw, seed, who, steps=STEPS):
    """The raw model, built while holding the graphics card, which is let go the moment the
    generator starts writing its file: that last stage, about a third of the run, works on the
    processor with the card's memory already given back (measured 2026-09-28: 78 of 231 s at 1%
    load, 1.8 GB held against 7.1 GB at the peak)."""
    refuse_here("Pixal3D", CLOUD)
    command = [str(LAB_PYTHON), *generator_arguments(cut, raw, seed, steps)]
    with contextlib.ExitStack() as card:
        card.enter_context(claimed(f"Pixal3D {raw.stem} for {who}", shared=True))
        with subprocess.Popen(command, cwd=IMAGE_TO_3DLAB, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, bufsize=1) as run:
            for line in run.stdout:
                print(line, end="", file=sys.stderr, flush=True)
                if line.lstrip().startswith(WRITING):
                    card.close()
        if run.returncode:
            raise subprocess.CalledProcessError(run.returncode, command)


def turned_by_lab(raw):
    """Whether image-to-3dlab turned the raw model to face +Z (glb_turn's stamp in asset.extras)."""
    import glb_file
    document, _ = glb_file.read(raw)
    return FACING_KEY in (document.get("asset", {}).get("extras") or {})


def model_turned_back(raw):
    """The raw model turned back half round to face -Z, its stamp taken off, written over itself."""
    import glb_file
    document, views = glb_file.read(raw)
    glb_file.turned(document, views, HALF_TURN)
    extras = document["asset"]["extras"]
    extras.pop(FACING_KEY)
    if not extras:
        document["asset"].pop("extras")
    turning = raw.with_name(raw.name + ".turning")
    glb_file.write(document, views, turning)
    turning.replace(raw)


def cameras_turned_back(views):
    """The camera folder's cameras turned back with their model, when image-to-3dlab turned them (its stamp in
    transforms.json); a folder it never turned is left as it is."""
    cameras = views / "transforms.json"
    if not cameras.is_file():
        return
    transforms = json.loads(cameras.read_text())
    if not transforms.pop(CAMERA_KEY, False):
        return
    for frame in transforms["frames"]:
        frame["transform_matrix"] = (VIEW_TURN @ np.asarray(frame["transform_matrix"], dtype=float)).tolist()
    cameras.write_text(json.dumps(transforms, indent=2) + "\n")


def facing_back(raw):
    """A raw model image-to-3dlab turned to face +Z, and its camera folder, turned back to Pixal3D's -Z; True when
    they were turned."""
    if not turned_by_lab(raw):
        return False
    model_turned_back(raw)
    cameras_turned_back(raw.with_suffix(".svviews"))
    return True


def camera_folder(raw, picture):
    """The camera folder Pixal3D staged beside the raw model, or one rebuilt from the picture's
    cut-out when the raw model came without it (a cloud batch brings back the model alone)."""
    import clean_finish
    kept = raw.with_suffix(".svviews")
    if (kept / "transforms.json").exists():
        return kept
    return clean_finish.staged_views(cut_out(picture), raw.with_name(f"{raw.stem}-rebuilt.svviews"))


def finish(raw, picture, finished, faces, paint_from=None):
    """The raw model thinned to `faces` and painted cleanly (clean_finish.py); with `paint_from`,
    an unlit paint copy of the picture (cloud/delight.py), Pixel Match paints from that instead."""
    import clean_finish
    views = camera_folder(raw, picture)
    if paint_from:
        views = clean_finish.unlit_views(views, picture, paint_from, raw.with_name(f"{raw.stem}-unlit.svviews"))
    clean_finish.finish(raw, picture, finished, faces, views)


def stand_and_pad(finished, final, long, feet, tube):
    """The finished model stood upright, its maps padded, written to `final`."""
    import glb_file
    document, views = glb_file.read(finished)
    turn = glb_file.upright_turn(glb_file.positions(document, views), long=long, feet=feet, tube=tube)
    glb_file.turned(document, views, turn)
    glb_file.turned(document, views, glb_file.level_turn(*glb_file.faces(document, views)))
    glb_file.padded(document, views)
    glb_file.write(document, views, final)


def options_parser():
    """This script's options, which the cloud batch runner also reads a batch list with."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("picture")
    parser.add_argument("name")
    parser.add_argument("--who", required=True, help="the session asking, shown to anyone waiting")
    parser.add_argument("--faces", type=int, default=40000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=STEPS, help=f"sampling steps (default {STEPS}, "
                        "the #55 lock); lower only for the P2 benchmark or a shape the owner allowed")
    parser.add_argument("--long", action="store_true", help="stand it on its longest side")
    parser.add_argument("--feet", action="store_true", help="level it on its lowest points")
    parser.add_argument("--tube", action="store_true", help="stand a round body's axis straight up")
    parser.add_argument("--finish-only", action="store_true", help="reuse the raw model")
    parser.add_argument("--paint-from", help="an unlit paint copy of the picture (cloud/delight.py) "
                        "for Pixel Match to paint from, so the picture's light stays off the model")
    return parser


def main():
    options = options_parser().parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / f"{options.name}.glb"
    finished = OUT / f"{options.name}-{options.faces}.glb"
    final = OUT / f"{options.name}-final.glb"
    seconds = {}

    if not options.finish_only:
        start = time.time()
        cut = cut_out(options.picture)
        seconds["cut out"] = time.time() - start
        start = time.time()
        generate(cut, raw, options.seed, options.who, options.steps)
        seconds["generate (card)"] = time.time() - start
    elif not raw.exists():
        sys.exit(f"--finish-only needs the raw model at {raw}")
    if facing_back(raw):
        say(f"{raw.name}: turned back from image-to-3dlab's +Z to -Z, with its camera folder")
    start = time.time()
    finish(raw, options.picture, finished, options.faces, options.paint_from)
    seconds["finish"] = time.time() - start
    start = time.time()
    stand_and_pad(finished, final, options.long, options.feet, options.tube)
    seconds["upright and pad"] = time.time() - start
    say(", ".join(f"{step} {value:.0f} s" for step, value in seconds.items()))
    print(final)


if __name__ == "__main__":
    main()
