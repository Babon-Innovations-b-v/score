"""The sentences the crew's movement is written from, and the clips they made.

    bash tools/characters/people/run.sh --clips            # make whatever is missing
    bash tools/characters/people/run.sh --clips --again shouting   # make one again, whatever is there

A text to motion model turns a sentence into a piece of skeletal animation. The sentences are
here rather than in somebody's shell history, because the sentence *is* the animation: changing a
word changes the walk, and a clip nobody can remake is a clip nobody can change. Everything about
how the chain is installed is in `docs/bible.md`, `workflow/bootstrap`.

Two of these were re-generated once already. The first suit walk held the hands 0.62 m apart, a
fifth wider than a plain walk, and the owner called it too wide (#36, 2026-09-20); the word that
fixed it was dropping "arms held away from the body" from the sentence.
"""
import argparse
import importlib.util
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from paths import MOTIONS, VENV_PYTHON  # noqa: E402


def _card_lock():
    """There is one graphics card on this box, so there is one claim on it: the prop chain's.

    It is loaded by its path rather than put on the import path, because that directory has a
    `paths.py` of its own and importing it by name would shadow this chain's. The other way round
    bites too: `card.py` reads HOME from `import paths`, which here is this chain's, so it claimed
    ~/.farm-factory-motion/card.claim, a lock nobody else reads, and a clip ran beside another
    job's card work (2026-09-30). So the prop chain's `paths.py` stands in while `card.py` loads,
    and the claim's path is checked.
    """
    props = pathlib.Path(__file__).resolve().parents[2] / "props"
    crew_paths = sys.modules.get("paths")
    props_paths = _module_at("props_paths", props / "paths.py")
    sys.modules["paths"] = props_paths
    try:
        card = _module_at("props_card", props / "card.py")
    finally:
        sys.modules["paths"] = crew_paths
    if card.CLAIM != props_paths.HOME / "card.claim":
        raise SystemExit(f"the card claim is at {card.CLAIM}, not the prop chain's; nothing may run")
    return card.claimed


def _module_at(name, path):
    """A module loaded from a file under a name of its own."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


claimed = _card_lock()

# The checkpoint, picked on licence: NVIDIA Open Model License, trained on mocap NVIDIA licensed
# commercially. The `SEED` and `SMPLX` checkpoints are deliberately not used (#36).
MODEL = "Kimodo-SOMA-RP-v1.1"
# Kimodo wants about 17 GB to run wholly on the card and this one holds 16, so the sentence
# reading moves to the processor. Without this the run dies out of memory.
ON_THE_PROCESSOR = {"TEXT_ENCODER_DEVICE": "cpu"}

# What the crew do in the base, and what the leader does on his podium in the prologue. Every clip earns its
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
    "lying": ("a person lying flat on their back on the ground, limp and completely still",
              5.0),
    "dragging": ("a person walking slowly backwards, bent forward at the waist, gripping "
                 "something heavy low in front of them with both hands and pulling it along the "
                 "ground", 6.0),
    # Played once, not looped: the rescuer taking hold of a player lying on the ground before the
    # drag (#83). Without it the drag started from a standing pose with the body already in the
    # hands, which read as a glitch in the playtest (2026-09-26).
    "lifting": ("a person bending down to grab something heavy lying on the ground in front of "
                "them with both hands, then straightening up and lifting it to waist height", 3.0),
    # The prologue (#112): the driver beside the car holding its rear door open for the player,
    # the crowd in the square, and a technician on launch day with a clipboard. The first door
    # sentence ("a chauffeur standing still beside a car, holding the open rear car door with the
    # right hand at waist height ...") came back as plain standing, the hand at 0.91 m; this one
    # holds the right hand out at 1.11 m (the others are kept on the box as door_a to door_c).
    "door": ("a man standing beside an open car door, his right hand holding the door's top edge "
             "out to his right at hip height with a straight arm, waiting for someone to get in",
             6.0),
    "clapping": ("a person standing in a crowd, clapping their hands in front of their chest",
                 5.0),
    "shifting": ("a person standing in a crowd, shifting their weight from one foot to the "
                 "other and looking around", 5.0),
    "clipboard": ("a person standing still, holding a clipboard in front of their chest with "
                  "the left hand and writing on it with the right hand", 5.0),
    # Oona in the dust beside Bram, and against the boot rock facing his cairn (#112, #109).
    "sitting": ("a person sitting on the ground with their knees drawn up, arms resting on their "
                "knees, completely still", 5.0),
}
# Clips that play once rather than round and round: the build keeps them whole instead of cutting
# them to a loop, and the game holds the last frame. The driver takes hold of the door once and
# keeps holding it.
ONCE = {"lifting", "door"}
# Clips where nobody is on their feet: the build leaves their legs as they are rather than bringing the feet in to a
# standing stance (`stance.py`).
OFF_THEIR_FEET = {"lying", "sitting"}


# The name a clip carries in the game, where it differs from the file it was generated into.
# `suit_e` is the sixth take; the first five are kept on the box as the record of what was tried.
# The drag holds its hands at hip height, about a metre up. A second take asking for "bent far
# forward, both hands down near their knees" came back standing straighter with the hands higher,
# 1.1 m, so the first stands and the second is kept on the box as `dragging_b` (#83).
IN_GAME = {"suit_e": "suit"}


def in_game(name):
    """What a clip is called once it is in the game."""
    return IN_GAME.get(name, name)


def missing():
    """The clips named here that are not on the box."""
    return [name for name in SENTENCES if not (MOTIONS / f"{name}.npz").exists()]


def generate(name):
    """Ask the model for one clip, and leave it beside the others."""
    sentence, seconds = SENTENCES[name]
    MOTIONS.mkdir(parents=True, exist_ok=True)
    print(f"\n== {name}: \"{sentence}\"")
    command = [
        str(VENV_PYTHON.parent / "kimodo_gen"), sentence,
        "--model", MODEL,
        "--duration", str(seconds),
        "--output", str(MOTIONS / name),
        "--bvh", "--bvh_standard_tpose",
    ]
    environment = dict(os.environ, PATH=f"{VENV_PYTHON.parent}:{os.environ.get('PATH', '')}", **ON_THE_PROCESSOR)
    finished = subprocess.run(command, env=environment, check=False)
    if finished.returncode:
        raise SystemExit(f"generating {name} failed with {finished.returncode}")
    return MOTIONS / f"{name}.npz"


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
