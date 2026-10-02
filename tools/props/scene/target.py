"""Draw the target picture a scene is composed from: one wide, level view of a room or a place.

    ~/.farm-factory-props/env/bin/python tools/props/scene/target.py <scene> "<sentence>" \
        [--shot inside|outside] [--takes 4] [--ref photo.png ...] [--refs-on 2]
    ~/.farm-factory-props/env/bin/python tools/props/scene/target.py --list scenes.json [--takes 2]

The picture model is the prop chain's own (FLUX.2 klein 4B, picture.py), told to draw a scene
instead of an object on grey. Writes <scene>-target-<take>.png under WORK/scene/<scene>/. The
first `--refs-on` takes are drawn with the owner's reference photographs handed in, the rest from
the words alone, so a page can show what the references change. Holds the card while it draws.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import picture  # noqa: E402
from card import claimed  # noqa: E402
from paths import WORK  # noqa: E402

# Wide, but near the picture model's one megapixel; both sides a multiple of 16.
WIDTH, HEIGHT = 1344, 768
# The camera the scene is later rebuilt from: level, at a standing player's eyes, a normal lens.
# A long lens, as the prop pictures use, would show one wall; a wide one bends the walls and
# MoGe then reads bent furniture. People are the sentence's to ask for or refuse: a crew member
# is the clearest measure of a big room's size (the owner, 2026-10-02).
SHOTS = {
    "inside": ("photograph taken from inside, level camera, horizon straight, natural 35 mm lens, "
               "from floor to ceiling, sharp focus everywhere, no text overlay"),
    "outside": ("photograph taken standing on the lunar surface, level camera, horizon straight, "
                "natural 35 mm lens, the ground in front and the black sky above, sharp focus "
                "everywhere, no text overlay"),
}


def folder(scene):
    """Where everything made for one scene lands."""
    path = WORK / "scene" / scene
    path.mkdir(parents=True, exist_ok=True)
    return path


def wording(sentence, shot):
    """What the picture model is told: the scene, then the shot."""
    return f"{sentence}, {SHOTS[shot]}"


def draw(pipeline, sentence, shot, seed, refs):
    """One target picture from a loaded picture model."""
    references = [Image.open(ref).convert("RGB") for ref in refs]
    return pipeline(
        image=references or None,
        prompt=wording(sentence, shot),
        num_inference_steps=picture.STEPS,
        guidance_scale=picture.GUIDANCE,
        height=HEIGHT,
        width=WIDTH,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]


def draw_takes(pipeline, job, takes, refs_on):
    """Every take of one scene from a loaded picture model, each printed as it lands."""
    out = folder(job["scene"])
    for take in range(1, takes + 1):
        refs = job.get("refs", []) if take <= refs_on else []
        path = out / f"{job['scene']}-target-{take}.png"
        draw(pipeline, job["sentence"], job.get("shot", "inside"), take, refs).save(path)
        print(path, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("scene", nargs="?")
    parser.add_argument("sentence", nargs="?")
    parser.add_argument("--shot", choices=tuple(SHOTS), default="inside")
    parser.add_argument("--takes", type=int, default=4)
    parser.add_argument("--ref", action="append", default=[])
    parser.add_argument("--refs-on", type=int, default=2, help="how many takes see the references")
    parser.add_argument("--list", type=pathlib.Path,
                        help='a JSON list of {"scene", "sentence", "shot", "refs"}, drawn with the model loaded once')
    options = parser.parse_args()
    if options.list:
        jobs = json.loads(options.list.read_text())
    elif options.scene and options.sentence:
        jobs = [{"scene": options.scene, "sentence": options.sentence, "shot": options.shot, "refs": options.ref}]
    else:
        parser.error("give a scene and a sentence, or --list")
    with claimed(f"target pictures for {', '.join(job['scene'] for job in jobs)}"):
        pipeline = picture.load()
        for job in jobs:
            draw_takes(pipeline, job, options.takes, options.refs_on)


if __name__ == "__main__":
    main()
