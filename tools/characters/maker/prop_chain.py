"""The prop route's steps on the rented card (characters.py runs this for a make folder whose spec names
"program": "prop_chain.py"), never on the owner's PC:

    /root/envs/motion/bin/python prop_chain.py /root/make/<name>

The spec (in/spec.json, written by prop_person.py) names its `steps`, in order, out of STEPS:
  clips     the spec's clips made by Kimodo with the fixed seed (people/clips.py, chain.py's clips step), each with its
            record, copied into out/motions/ so the store keeps them
  rig       SOMA-X's mean skeleton, its surface's weights and the spec's clips exported (prop_skeleton.py)
  shell     SOMA-X's body fitted to the outside of the look (prop_shell.py fit): out/shell.npz
  build     the glTF from the fitted rig, the mean rig's clips and the parts (prop_build.py), its UsdSkel asset
            (skel_usd.py) and joins.py's record into out/checks/
  route     the people route (owner, 2026-10-18) on the built body: SOMA-X's base under the look from the identity
            (route_base.py base), its pose correctives for every clip (route_base.py correctives), the garments bound
            by limb, the webs cut, the face by route_head.FACE and the correctives as shared morph targets
            (route_build.py), its UsdSkel asset and joins.py's record: out/route/
  identity  the body under the clothes read off the person's close-up by SAM 3D Body (body_picture.py) into
            out/identity.npz: the people route's base (route_base.py) reads it; the A-pose picture it was read from
            before is lost (2026-10-19), and the close-up is the same person front on in the rig's A-pose
SOMA-X gives the skeleton and its skin weights; the identity shapes only the route's base under the look, never the
look's mesh (owner, 2026-10-10: "soma is for the rig, not the mesh").
The record of every step (minutes, card, failure) is out/make.json, as chain.py writes it.
"""
import json
import pathlib
import shutil
import sys

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))

import chain as person_chain  # noqa: E402
from chain import MOTION  # noqa: E402


def motion_home():
    """The motion home the people tools find their environment through (chain.py's MOTION_HOME, its `env` linked)."""
    home = person_chain.MOTION_HOME
    home.mkdir(exist_ok=True)
    if not (home / "env").exists():
        (home / "env").symlink_to(person_chain.ENVS / "motion")


def clips(chain):
    """The spec's clips made by Kimodo with the fixed seed (chain.py's clips step), copied with their records into
    out/motions/."""
    motions = chain.work / "motionwork" / "motions"
    motions.mkdir(parents=True, exist_ok=True)
    motion_home()
    made = person_chain.clips(chain)
    kept = chain.out / "motions"
    kept.mkdir(exist_ok=True)
    for path in sorted(motions.iterdir()):
        if path.name.endswith((".npz", ".record.json")):
            shutil.copy2(path, kept / path.name)
    return made


def rig(chain):
    """The rig file (out/rig.npz): the skeleton, the weights' source and the clips (prop_skeleton.py)."""
    motions = chain.work / "motionwork" / "motions"
    if not motions.exists():
        shutil.copytree(chain.folder / "in" / "motions", motions)
    motion_home()
    chain.run([MOTION, MAKER / "prop_skeleton.py", chain.out / "rig.npz", *chain.spec.get("clips", [])])


def shell(chain):
    """SOMA-X's body, its shape fitted to the outside of the look, laid on the fitted skeleton (prop_shell.py fit):
    out/shell.npz, the moving base the look is bound to."""
    chain.run([MOTION, MAKER / "prop_shell.py", "fit", chain.file(chain.spec["files"]["fit"]), chain.out / "shell.npz"])


def build(chain):
    """The person built: out/<name>.glb, its report, out/usd/ and out/checks/."""
    files = {name: chain.file(path) for name, path in chain.spec["files"].items()}
    glb = chain.out / f"{chain.spec['person']}.glb"
    chain.run([MOTION, MAKER / "prop_build.py", files["fit"], files["mean"], files["parts"], files["far"], glb,
               chain.out / f"{chain.spec['person']}.json", "--outfit", chain.spec["outfit"],
               *(["--prints", files["prints"]] if "prints" in files else [])])
    chain.run([MOTION, MAKER.parent / "skel_usd.py", glb, "--out", chain.out / "usd"])
    chain.run([MOTION, MAKER.parent / "people" / "joins.py", glb, "--out", chain.out / "checks", "--record-only"])


def route(chain):
    """The people route on the built body (out/<person>.glb, this make's build step's, else the spec's `body`), with
    the identity this make's identity step read: out/route/<person>.glb and its record (.json), its base and
    correctives, its UsdSkel asset (out/route/usd/) and joins.py's record (out/route/checks/). The face by
    route_head.FACE, route_build.py's default."""
    files = {name: chain.file(path) for name, path in chain.spec["files"].items()}
    person = chain.spec["person"]
    built = chain.out / f"{person}.glb"
    body = built if built.exists() else files["body"]
    out = chain.out / "route"
    out.mkdir(exist_ok=True)
    identity = chain.out / "identity.npz"
    routed = out / f"{person}.glb"
    chain.run([MOTION, MAKER / "route_base.py", "base", files["fit"], files["shell"], identity, out / "base.npz"])
    chain.run([MOTION, MAKER / "route_base.py", "correctives", out / "base.npz", body, out / "correctives.npz",
               identity])
    chain.run([MOTION, MAKER / "route_build.py", body, files["fit"], out / "base.npz", routed, "--correctives",
               out / "correctives.npz"])
    chain.run([MOTION, MAKER.parent / "skel_usd.py", routed, "--out", out / "usd"])
    chain.run([MOTION, MAKER.parent / "people" / "joins.py", routed, "--out", out / "checks", "--record-only"])
    return json.loads(routed.with_suffix(".json").read_text())["head"]["face"]


def identity(chain):
    """The body under the clothes read off the close-up (body_picture.py, SAM 3D Body): out/identity.npz."""
    chain.run([MOTION, MAKER / "body_picture.py", chain.file(chain.spec["files"]["closeup"]),
               chain.out / "identity.npz"])
    return "read off the close-up"


STEPS = {"clips": clips, "rig": rig, "shell": shell, "build": build, "route": route, "identity": identity}


def main():
    chain = person_chain.Chain(pathlib.Path(sys.argv[1]))
    for name in chain.spec["steps"]:
        chain.step(name, lambda work=STEPS[name]: work(chain))
    print(f"made {chain.spec['name']} ({', '.join(chain.spec['steps'])}) in {chain.record['minutes']} min", flush=True)


if __name__ == "__main__":
    main()
