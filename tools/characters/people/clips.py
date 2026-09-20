"""The sentences the crew's movement is written from, and the clips they made.

    bash tools/crew/run.sh --clips            # make whatever is missing
    bash tools/crew/run.sh --clips --again shouting   # make one again, whatever is there

A text to motion model turns a sentence into a piece of skeletal animation. The sentences are
here rather than in somebody's shell history, because the sentence *is* the animation: changing a
word changes the walk, and a clip nobody can remake is a clip nobody can change. Everything about
how the chain is installed is in `docs/bible.md`, `workflow/bootstrap`.

Two of these were re-generated once already. The first suit walk held the hands 0.62 m apart, a
fifth wider than a plain walk, and the owner called it too wide (#36, 2026-09-20); the word that
fixed it was dropping "arms held away from the body" from the sentence.
"""
import argparse
import contextlib
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from paths import MOTIONS, VENV_PYTHON  # noqa: E402


def _card_lock():
    """There is one graphics card on this box, so there is one claim on it: the prop chain's.

    It is loaded by its path rather than put on the import path, because that directory has a
    `paths.py` of its own and importing it by name would shadow this chain's.
    """
    import importlib.util
    here = pathlib.Path(__file__).resolve().parents[1] / "props" / "card.py"
    if not here.exists():
        @contextlib.contextmanager
        def nobody_else_is_here(doing, say=None):
            yield
        return nobody_else_is_here
    spec = importlib.util.spec_from_file_location("props_card", here)
    module = importlib.util.module_from_spec(spec)
    sys.modules["props_card"] = module
    spec.loader.exec_module(module)
    return module.claimed


claimed = _card_lock()

# The checkpoint, picked on licence: NVIDIA Open Model License, trained on mocap NVIDIA licensed
# commercially. The `SEED` and `SMPLX` checkpoints are deliberately not used (#36).
MODEL = "Kimodo-SOMA-RP-v1.1"
# Kimodo wants about 17 GB to run wholly on the card and this one holds 16, so the sentence
# reading moves to the processor. Without this the run dies out of memory.
ON_THE_PROCESSOR = {"TEXT_ENCODER_DEVICE": "cpu"}

# What the crew do in the base, and what the prologue's crowd do on Earth. Every clip earns its
# place: this is a set, not a library.
SENTENCES = {
    "standing": ("a person standing still and relaxed, shifting their weight slightly", 5.0),
    "walking": ("a person walking forward at a steady, easy pace", 5.0),
    "bench": ("a person standing at a workbench, working with both hands in front of them", 6.0),
    "suit_e": ("a person walking forward slowly and stiffly in a heavy bulky spacesuit", 6.0),
    "shouting": ("a person holding one arm straight up and shouting to be picked", 5.0),
    "cheering": ("an excited person with both arms raised above their head, bouncing on the "
                 "spot", 5.0),
    "leaning": ("a person leaning forward over a barrier, holding something out in front of "
                "them", 5.0),
    "pointing": ("a person pointing forward with one arm and shouting a question", 5.0),
    "waiting": ("a person standing still with their arms folded, watching", 5.0),
    "checking": ("a person crouching down to look closely at something on the ground in front "
                 "of them", 6.0),
    "reaching": ("a person reaching up with both hands to work on something above their head",
                 6.0),
}


# The name a clip carries in the game, where it differs from the file it was generated into.
# `suit_e` is the sixth take; the first five are kept on the box as the record of what was tried.
IN_GAME = {"suit_e": "suit"}


def in_game(name):
    """What a clip is called once it is in the game."""
    return IN_GAME.get(name, name)


def missing():
    """The clips named here that are not on the box."""
    return [name for name in SENTENCES if not (MOTIONS / f"{name}.npz").exists()]


def generate(name, say=print):
    """Ask the model for one clip, and leave it beside the others."""
    sentence, seconds = SENTENCES[name]
    MOTIONS.mkdir(parents=True, exist_ok=True)
    say(f"\n== {name}: \"{sentence}\"")
    command = [
        str(VENV_PYTHON.parent / "kimodo_gen"), sentence,
        "--model", MODEL,
        "--duration", str(seconds),
        "--output", str(MOTIONS / name),
        "--bvh", "--bvh_standard_tpose",
    ]
    environment = dict(**ON_THE_PROCESSOR)
    finished = subprocess.run(command, env={**_environment(), **environment}, check=False)
    if finished.returncode:
        raise SystemExit(f"generating {name} failed with {finished.returncode}")
    return MOTIONS / f"{name}.npz"


def _environment():
    import os
    return dict(os.environ, PATH=f"{VENV_PYTHON.parent}:{os.environ.get('PATH', '')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--again", nargs="*", default=None,
                        help="clips to make again even though they are already here")
    arguments = parser.parse_args()

    wanted = arguments.again if arguments.again else missing()
    if not wanted:
        print(f"every clip is already at {MOTIONS}")
        return
    unknown = [name for name in wanted if name not in SENTENCES]
    if unknown:
        raise SystemExit(f"no sentence for: {', '.join(unknown)}")

    print(f"making {len(wanted)} clip(s): {', '.join(wanted)}")
    with claimed("the crew's motion clips"):
        for name in wanted:
            generate(name)
    print(f"\ndone, clips are at {MOTIONS}")


if __name__ == "__main__":
    main()
