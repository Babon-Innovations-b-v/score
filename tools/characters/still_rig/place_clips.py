"""The place people's clips (2099 #161, the npc-life report): what a player model laid in a place does beyond the five
people-clips-made clips its dressed body carries (standing, walking, bench, sitting, seated). Made by Kimodo free on
this PC's card in Kimodo's own environment, with people/clips.py's model and fixed seed, Kimodo's model loaded once:

    <motion env>/bin/python place_clips.py <out folder> [<clip> ...]

Writes <out>/motions/<clip>.npz (Kimodo's NPZ) and <clip>.record.json (sentence, seconds, model, seed), then the rig
step reads them (../maker/prop_skeleton.py with MOTION_WORK=<out>): the clips on SOMA-X's mean bind, which
clips_added.py lays on a rigged still's own skeleton.

The work bodies' clips (leaning, pointing, checking, clipboard, cheering, waiting, clapping, shifting) are made again
from their own sentences in people/clips.py (read, never edited here: the paid people rows key that folder), not copied
off the work bodies' files: those were posed before 2026-11-04 through SOMA's zero-identity layer, a fixed turn off
Kimodo's at every joint (prop_skeleton.py's header). The prologue's new ones are written here.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "people"))

import clips as people_clips  # noqa: E402

# The prologue's clips no body carried (2099 #161): the street's and the flat's talk, the stairwell's climb both ways,
# the balcony's rail and view, the square's crowd cheering, waving and swaying. Every clip earns its place.
SENTENCES = {
    "talking": ("a person standing and talking with someone in front of them, gesturing with both hands while they "
                "speak and nodding their head", 6.0),
    "stairs_up": ("a person walking up a flight of stairs at a steady, easy pace", 5.0),
    "stairs_down": ("a person walking down a flight of stairs at a steady, easy pace", 5.0),
    "rail_lean": ("a person leaning forward with both forearms resting on a railing at chest height, looking out "
                  "into the distance", 6.0),
    "looking_out": ("a person standing still, slowly turning their head and shoulders to look around at the view "
                    "to the left and then to the right", 6.0),
    "waving": ("a person standing in a crowd, holding a small flag up in the right hand and waving it from side to "
               "side above their head", 5.0),
    "swaying": ("a person standing in a packed crowd, swaying gently from side to side to music", 5.0),
}
# The work bodies' clips, made again from their own sentences, and standing, which sets every clip's floor lift.
REMADE = ("standing", "cheering", "leaning", "pointing", "checking", "clipboard", "waiting", "clapping", "shifting")
# A climb's feet leave the floor Kimodo's foot correction holds them to, so it is asked without it.
NO_POSTPROCESS = {"stairs_up", "stairs_down"}
# Clips whose body rises or falls along the clip (a flight of stairs): clips_added.py takes their height's run off as
# it takes the travel off every clip's floor, the game carrying the body up the stairs.
CLIMBS = {"stairs_up": 1, "stairs_down": -1}
# Kimodo's text encoder (Llama 3 8B) runs on the processor: on the card it held 13.2 of this PC's 16 GB and ran out of
# memory beside the places' bakes (2026-11-25); the denoiser alone fits in 3 GB.
TEXT_ENCODER = "cpu"


def sentence_of(name):
    """(sentence, seconds) of a place clip: the prologue's own, else people/clips.py's."""
    return SENTENCES[name] if name in SENTENCES else people_clips.SENTENCES[name]


def wanted():
    """Every place clip, in making order."""
    return list(REMADE) + list(SENTENCES)


def record_of(name, sample):
    """What a clip was made from: its sentence, seconds, model, seed, its place in the batch made under that seed
    (`sample`) and whether Kimodo corrected its feet."""
    sentence, seconds = sentence_of(name)
    return {"clip": name, "sentence": sentence, "seconds": seconds, "model": people_clips.MODEL,
            "seed": people_clips.CLIP_SEED, "batch": batches(wanted())[name not in NO_POSTPROCESS], "sample": sample,
            "text_encoder": f"{TEXT_ENCODER} (bfloat16)",
            "postprocess": name not in NO_POSTPROCESS}


def batches(names):
    """The clips made together: (without Kimodo's foot correction, with it), each in making order."""
    return ([name for name in names if name in NO_POSTPROCESS], [name for name in names if name not in NO_POSTPROCESS])


def make(out, names):
    """Each batch of clips made by Kimodo in one pass under the fixed seed (independent motions, one a prompt), the
    model loaded once; each clip's NPZ and record into out/motions/. A batch is made whole or not at all, so a clip's
    record names the one batch it came out of."""
    os.environ.setdefault("TEXT_ENCODER_DEVICE", TEXT_ENCODER)
    import torch
    from kimodo import load_model
    from kimodo.exports.motion_io import save_kimodo_npz
    from kimodo.tools import seed_everything

    motions = out / "motions"
    motions.mkdir(parents=True, exist_ok=True)
    model = load_model(people_clips.MODEL, device="cuda:0" if torch.cuda.is_available() else "cpu",
                       default_family="Kimodo")
    for corrected, batch in enumerate(batches(names)):
        if not batch or all((motions / f"{name}.npz").exists() for name in batch):
            continue
        seed_everything(people_clips.CLIP_SEED)
        output = model([sentence_of(name)[0] for name in batch],
                       [int(sentence_of(name)[1] * model.fps) for name in batch], num_denoising_steps=100,
                       constraint_lst=[], multi_prompt=False, post_processing=bool(corrected), return_numpy=True)
        for sample, name in enumerate(batch):
            frames = int(sentence_of(name)[1] * model.fps)
            single = {key: (value[sample][:frames] if hasattr(value, "shape") and value.ndim > 1
                            and value.shape[0] == len(batch) else value) for key, value in output.items()}
            save_kimodo_npz(str(motions / f"{name}.npz"), single)
            (motions / f"{name}.record.json").write_text(json.dumps(record_of(name, sample), indent=1))
            print(f"made {name}", flush=True)


def main():
    out = pathlib.Path(sys.argv[1])
    make(out, sys.argv[2:] or wanted())


if __name__ == "__main__":
    main()
