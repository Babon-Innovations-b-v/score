"""The prop route's steps on the rented card (characters.py runs this for a make folder whose spec names
"program": "prop_chain.py"), never on the owner's PC:

    /root/envs/motion/bin/python prop_chain.py /root/make/<name>

The spec (in/spec.json, written by prop_person.py) names its `steps`, in order, out of STEPS:
  pose      SOMA-X's bind pose measured on the mean skeleton (prop_read.py)
  closeup   the front close-up in that pose, two klein seeds (prop_closeup.py)
  rig       SOMA-X's mean skeleton, its surface's weights and the spec's clips exported (prop_skeleton.py)
  build     the glTF from the fitted rig, the mean rig's clips and the parts (prop_build.py), its UsdSkel asset
            (skel_usd.py) and joins.py's record into out/checks/
  review    turntables and clip frames rendered by Cycles (blender_review.py), as the shipped route's review
No body is read off a picture on this route (owner, 2026-10-10): SOMA-X gives the skeleton and its skin weights only.
The record of every step (minutes, card, failure) is out/make.json, as chain.py writes it.
"""
import pathlib
import shutil
import sys

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))

import chain as person_chain  # noqa: E402
from chain import MOTION, PICTURE  # noqa: E402

SEEDS = (1, 2)


def pose(chain):
    """The bind pose the close-up is drawn in."""
    chain.run([MOTION, MAKER / "prop_read.py", chain.out / "pose.json"])


def closeup(chain):
    """The close-up, one picture a seed, into out/closeup/."""
    spec = chain.spec
    target = chain.out / "closeup" / f"{spec['name']}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    references = [chain.file(path) for path in spec.get("references", [])]
    chain.run([PICTURE, MAKER / "prop_closeup.py", target, chain.out / "pose.json", spec["who"],
               spec["outfit_words"], *references, "--seeds", *map(str, SEEDS)])
    return f"{len(SEEDS)} seeds, {len(references)} references"


def rig(chain):
    """The rig file (out/rig.npz): the skeleton, the weights' source and the clips (prop_skeleton.py)."""
    motions = chain.work / "motionwork" / "motions"
    if not motions.exists():
        shutil.copytree(chain.folder / "in" / "motions", motions)
    home = person_chain.MOTION_HOME
    home.mkdir(exist_ok=True)
    if not (home / "env").exists():
        (home / "env").symlink_to(person_chain.ENVS / "motion")
    chain.run([MOTION, MAKER / "prop_skeleton.py", chain.out / "rig.npz", *chain.spec.get("clips", [])])


def build(chain):
    """The person built: out/<name>.glb, its report, out/usd/ and out/checks/."""
    files = {name: chain.file(path) for name, path in chain.spec["files"].items()}
    glb = chain.out / f"{chain.spec['person']}.glb"
    chain.run([MOTION, MAKER / "prop_build.py", files["fit"], files["mean"], files["parts"], glb,
               chain.out / f"{chain.spec['person']}.json", "--outfit", chain.spec["outfit"]])
    chain.run([MOTION, MAKER.parent / "skel_usd.py", glb, "--out", chain.out / "usd"])
    chain.run([MOTION, MAKER.parent / "people" / "joins.py", glb, "--out", chain.out / "checks", "--record-only"])


def review(chain):
    """The review pictures of the built person (blender_review.py, the shipped route's cameras)."""
    shown = [name for name in person_chain.REVIEW_CLIPS if name in chain.spec.get("review_clips", [])]
    chain.run([person_chain.BLENDER, "-b", "-P", MAKER / "blender_review.py", "--",
               chain.out / f"{chain.spec['person']}.glb", chain.out / "review", "--clips", *shown, "--angles", "8",
               "--frames", "4", "--size", "448"])
    return f"turntables and {len(shown)} clips"


STEPS = {"pose": pose, "closeup": closeup, "rig": rig, "build": build, "review": review}


def main():
    chain = person_chain.Chain(pathlib.Path(sys.argv[1]))
    for name in chain.spec["steps"]:
        chain.step(name, lambda work=STEPS[name]: work(chain))
    print(f"made {chain.spec['name']} ({', '.join(chain.spec['steps'])}) in {chain.record['minutes']} min", flush=True)


if __name__ == "__main__":
    main()
