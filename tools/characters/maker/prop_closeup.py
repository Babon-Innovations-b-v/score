"""The prop route's close-up of a person (owner, 2026-10-10: "soma is for the rig, not the mesh"): one front picture
of the person in one outfit, standing in SOMA-X's own bind pose, drawn by FLUX.2 klein 4B (Apache-2.0) on the rented
card, which Pixal3D makes the person's mesh from as it makes a prop's.

    /root/envs/picture/bin/python prop_closeup.py <out.png> <pose.json> "<who>" "<outfit>" [<reference> ...]
        [--seeds 1 2]

`pose.json` is the bind pose measured on the body (prop_read.py `pose`): `arm_degrees` (shoulder joint to hand joint
below level), `hands_forward_m` and `ankles_m`. The words are drawings.py's FORM with the levers the asset pictures
taught (memory: picture levers): shapes said positively, every part that must come out separable named (the gaps
between arms and body and between the legs), the outfit named by its parts, and a level front camera with a narrow
lens, which Pixal3D assumes. References (the owner's drawing of the person) go in as image references.

Writes one picture a seed, `<out stem>_s<seed>.png`.
"""
import argparse
import json
import pathlib

import drawings

POSE = ("full body seen straight from the front by a level telephoto camera at chest height, standing still and "
        "symmetrical in an A-pose: both arms straight and angled down at {arm:.0f} degrees below level from the "
        "shoulders, the hands about {forward:.0f} cm in front of the hips with the elbows very slightly bent, fingers "
        "together and palms facing the thighs, a clear gap between each arm and the body from the armpit down, the "
        "feet {ankles:.0f} cm apart with a clear gap between the legs from the crotch down, looking straight ahead, "
        "the whole figure in the picture with space around it")


def wording(who, outfit, pose, referenced):
    """The close-up's words: the person, the outfit by its parts, the measured pose and drawings.py's form."""
    lead = f"the same person as in the reference: {who}" if referenced else who
    posed = POSE.format(arm=pose["arm_degrees"], forward=pose["hands_forward_m"] * 100, ankles=pose["ankles_m"] * 100)
    return f"{lead}, wearing {outfit}, {posed}, {drawings.FORM}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("pose", type=pathlib.Path)
    parser.add_argument("who")
    parser.add_argument("outfit")
    parser.add_argument("references", nargs="*", type=pathlib.Path)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2])
    options = parser.parse_args()
    pose = json.loads(options.pose.read_text())
    prompt = wording(options.who, options.outfit, pose, bool(options.references))
    print(prompt, flush=True)
    settings = {"image": drawings.pictures(options.references) or None, "num_inference_steps": 4,
                "guidance_scale": 1.0, "prompt": prompt, "height": 1152, "width": 896}
    drawings.draw(drawings.klein(), options.out.with_name(options.out.stem + "_s{seed}.png"), options.seeds, settings)


if __name__ == "__main__":
    main()
