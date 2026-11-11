"""Scene-made clips on the rented card (tools/cloud/characters.py runs it for a make folder whose spec names
"program": "scene_clips.py"; never on the owner's PC):

    /root/envs/motion/bin/python scene_clips.py /root/make/<name>

The spec (written by score/stages/scene_clips) names each clip under `scene clips`: its sentence, its `--duration`, its
constraints file (Kimodo's constraints JSON, in its canonical frame) and whether Kimodo post-processes it. Steps:
  scene clips  each clip made by Kimodo (`kimodo_gen`, people/clips.py's model and fixed seed, `--constraints`),
               its record beside it, lowered by its `lift` (its constraints are asked with the walk's lowest
               ground on Kimodo's floor; lowered, its start's ground is y = 0 again, as the stage's placement says),
               copied into out/motions/
  rig          SOMA-X's mean rig with the spec's clips (the maker's prop_chain.py rig step, prop_skeleton.py)
Out as people-clips-made's: out/rig.npz, out/motions/ and out/make.json (the maker's step runner, ../maker/chain.py).
"""
import json
import pathlib
import shutil
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "maker"))
sys.path.insert(0, str(HERE.parent / "people"))

import chain as person_chain  # noqa: E402
import clips as sentences  # noqa: E402
import prop_chain  # noqa: E402


def arguments(clip, output):
    """kimodo_gen's arguments for one scene-made clip into `output` (its stem)."""
    return [clip["sentence"], "--model", sentences.MODEL, "--duration", clip["seconds"], "--seed",
            str(sentences.CLIP_SEED), "--constraints", clip["constraints"], "--output", str(output), "--bvh",
            "--bvh_standard_tpose", *([] if clip["postprocess"] else ["--no-postprocess"])]


def lowered(motion, lift):
    """Kimodo's NPZ at `motion` moved down `lift` metres (its root, smoothed root and every joint), in place."""
    with np.load(motion) as held:
        arrays = dict(held)
    for key in ("root_positions", "smooth_root_pos", "posed_joints"):
        arrays[key][..., 1] -= lift
    np.savez(motion, **arrays)


def made(chain):
    """Step `scene clips`: every clip made from its constraints, its record beside it, copied into out/motions/."""
    motions = chain.work / "motionwork" / "motions"
    motions.mkdir(parents=True, exist_ok=True)
    prop_chain.motion_home()
    kept = chain.out / "motions"
    kept.mkdir(exist_ok=True)
    for name, clip in chain.spec["scene clips"].items():
        clip = dict(clip, constraints=str(chain.file(clip["constraints"])))
        chain.run([person_chain.MOTION_HOME / "env/bin/kimodo_gen", *arguments(clip, motions / name)])
        lowered(motions / f"{name}.npz", clip["lift"])
        record = {"clip": name, "sentence": clip["sentence"], "seconds": clip["seconds"], "model": sentences.MODEL,
                  "seed": sentences.CLIP_SEED, "constraints": json.loads(pathlib.Path(clip["constraints"]).read_text()),
                  "postprocess": clip["postprocess"], "lift": clip["lift"]}
        (motions / f"{name}.record.json").write_text(json.dumps(record))
        for path in (motions / f"{name}.npz", motions / f"{name}.record.json"):
            shutil.copy2(path, kept / path.name)
    return f"made {len(chain.spec['scene clips'])}"


def main():
    chain = person_chain.Chain(pathlib.Path(sys.argv[1]))
    chain.step("scene clips", lambda: made(chain))
    chain.step("rig", lambda: prop_chain.rig(chain))
    print(f"made {chain.spec['name']} in {chain.record['minutes']} min", flush=True)


if __name__ == "__main__":
    main()
