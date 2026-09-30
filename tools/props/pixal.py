"""Make a model from a picture on the locked route: the one way any session runs Pixal3D.

    ~/.farm-factory-props/env/bin/python tools/props/pixal.py <picture.png> <name> --who "<session>"
        [--faces 40000] [--seed 1] [--long] [--feet] [--tube] [--finish-only]

Four steps, and only the second touches the graphics card:
1. Cut the subject out of its background (BiRefNet-lite, on the processor).
2. Build the model with Pixal3D (image-to-3dlab's pixal3d_generate.py, --steps 12 --gss 10). This
   step alone holds the card, through card.claimed(), so runs from every session queue instead of
   colliding, and it lets go as soon as the generator starts writing its file. Two Pixal3D runs
   may share the card (measured safe, card.py); a third, or a picture run, waits. Two runs on one card crash the box, which is why nothing else may call
   image-to-3dlab's generator or trellis-cli directly.
3. Finish it: retopo_repaint.py thins it to --faces and bakes the base colour, detail and metal
   maps back on, in Blender on the processor.
4. Stand it upright and pad its maps (glb_file.py), on the processor.

Writes <name>.glb (the raw model), <name>-<faces>.glb (finished) and <name>-final.glb (upright and
padded, the one to import) under WORK/pixal/. --finish-only redoes steps 3 and 4 from the raw
model already there. Import the final file with `run.sh --import ... --keep-texture --keep-maps`.
"""
import argparse
import contextlib
import subprocess
import sys
import time

from card import claimed
from paths import BLENDER, IMAGE_TO_3DLAB, WORK

LAB_PYTHON = IMAGE_TO_3DLAB / ".venv" / "bin" / "python"
OUT = WORK / "pixal"
# The settings the owner locked the route on (#55): 12 steps, and structure guidance 10, which
# keeps thin parts the default drops.
STEPS, GUIDANCE = 12, 10
# The generator's banner for its last stage, writing the file, which needs no card.
WRITING = "[6/6]"


def say(line):
    print(f"[pixal] {line}", file=sys.stderr, flush=True)


def run_lab(arguments):
    """Run a script from image-to-3dlab with its own Python, failing loudly."""
    subprocess.run([str(LAB_PYTHON), *arguments], cwd=IMAGE_TO_3DLAB, check=True)


def cut_out(picture):
    """The picture cut out of its background, written beside it; the path to the cut-out."""
    code = ("import sys, pathlib; sys.path.insert(0, 'scripts'); "
            "from pixal3d_generate import matte; "
            f"print(matte(pathlib.Path({str(picture)!r}))[0])")
    done = subprocess.run([str(LAB_PYTHON), "-c", code], cwd=IMAGE_TO_3DLAB, check=True,
                          capture_output=True, text=True)
    return done.stdout.strip().splitlines()[-1]


def generator_arguments(cut, raw, seed):
    """The generator's script and arguments on the locked route, run from image-to-3dlab; the
    cloud batch runner (cloud/batch.py) runs these same ones on a rented card."""
    return ["scripts/pixal3d_generate.py", str(cut), str(raw), "--seed", str(seed),
            "--steps", str(STEPS), "--gss", str(GUIDANCE)]


def generate(cut, raw, seed, who):
    """The raw model, built while holding the graphics card, which is let go the moment the
    generator starts writing its file: that last stage, about a third of the run, works on the
    processor with the card's memory already given back (measured 2026-09-28: 78 of 231 s at 1%
    load, 1.8 GB held against 7.1 GB at the peak)."""
    command = [str(LAB_PYTHON), *generator_arguments(cut, raw, seed)]
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


def finish(raw, picture, finished, faces):
    """The raw model thinned to `faces` with its maps baked back on."""
    run_lab(["scripts/retopo_repaint.py", str(raw), str(picture), str(finished), "--faces", str(faces),
             "--skip-paint", "--blender", str(BLENDER)])


def stand_and_pad(finished, final, long, feet, tube=False):
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
    parser.add_argument("--long", action="store_true", help="stand it on its longest side")
    parser.add_argument("--feet", action="store_true", help="level it on its lowest points")
    parser.add_argument("--tube", action="store_true", help="stand a round body's axis straight up")
    parser.add_argument("--finish-only", action="store_true", help="reuse the raw model")
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
        generate(cut, raw, options.seed, options.who)
        seconds["generate (card)"] = time.time() - start
    elif not raw.exists():
        sys.exit(f"--finish-only needs the raw model at {raw}")
    start = time.time()
    finish(raw, options.picture, finished, options.faces)
    seconds["finish"] = time.time() - start
    start = time.time()
    stand_and_pad(finished, final, options.long, options.feet, options.tube)
    seconds["upright and pad"] = time.time() - start
    say(", ".join(f"{step} {value:.0f} s" for step, value in seconds.items()))
    print(final)


if __name__ == "__main__":
    main()
