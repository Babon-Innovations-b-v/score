"""Runs on a rented machine: UniRig's three inference steps over every model in a folder.

    /root/venv/bin/python unirig_worker.py <in folder> <out folder> [--seed 12345]

Each model (<name>.glb, a finished Pixal3D model) is given a skeleton (UniRig's skeleton model), skin weights for it
(its skin model) and the two merged onto the model as it came (its own merge), written to <out>/<name>-unirig.glb, with
the skeleton alone beside it (<name>-skeleton.fbx). Each step is UniRig's own launch script, run from its folder.
A line "<name> <step> <seconds>" is printed as each step ends; a step that fails stops the run with its exit code.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import time

UNIRIG = pathlib.Path("/root/UniRig")


def step(name, label, script, arguments):
    """One of UniRig's launch scripts, run from its folder with the machine's Python first on the path."""
    began = time.time()
    environment = dict(os.environ, PATH=f"/root/venv/bin:{os.environ['PATH']}")
    done = subprocess.run(["bash", f"launch/inference/{script}", *arguments], cwd=UNIRIG, env=environment)
    print(name, label, round(time.time() - began, 1), flush=True)
    if done.returncode:
        sys.exit(done.returncode)


def rig(model, out, seed):
    """One model's skeleton, skin and merge."""
    name = model.stem
    skeleton, skin = out / f"{name}-skeleton.fbx", out / f"{name}-skin.fbx"
    step(name, "skeleton", "generate_skeleton.sh", ["--input", str(model), "--output", str(skeleton),
                                                    "--seed", str(seed)])
    step(name, "skin", "generate_skin.sh", ["--input", str(skeleton), "--output", str(skin)])
    step(name, "merge", "merge.sh", ["--source", str(skin), "--target", str(model),
                                     "--output", str(out / f"{name}-unirig.glb")])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--seed", type=int, default=12345)
    options = parser.parse_args()
    options.out.mkdir(parents=True, exist_ok=True)
    for model in sorted(options.source.glob("*.glb")):
        rig(model, options.out, options.seed)


if __name__ == "__main__":
    main()
