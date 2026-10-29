"""Runs inside Blender on a rented card (tools/cloud/blender_cloud.py, the finish route's bake,
../route_bake.py): one take painted and baked in one job, so nothing heavy runs on the owner's PC (#18, 2026-10-20).

    blender -b --python paint_bake.py -- <listing>    (route_bake.card_job's: the bake's inputs, the take, its part
                                                       records, claimed rows and job head)

First the paint, as paint_take.py runs it (place_line.py's `paint-take` in Blender's own Python with the pinned
packages, its peak memory said); then route_bake.py's `bake-job` there too (the take's models' make_chunky entries
over the labelled take); while models stand pending, make_chunky.py --shapes (their cut-down copies as they will
bake, no bake) and route_bake.py's `square-again` (each measured as surfaces-check measures it and turned again where
it stands off square, route_bake.squared_again); then make_chunky.py in a Blender of its own, Cycles on the card
(blender_cloud.py sets FARM_CYCLES_GPU and PROPS_HOME for ProcFunc's site). Any step that fails fails the job: its
models are a gap.
"""
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import paint_take  # noqa: E402

BLENDER = "/root/blender/blender"


def main():
    paint_take.main()
    listing = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
    named = json.loads(listing.read_text())
    repo = pathlib.Path(named["paint repo"])
    environment = dict(os.environ, PYTHONPATH=str(paint_take.SITE), PROPS_HOME=named["props home"])
    route_bake = [paint_take.PYTHON, str(repo / "score/stages/surfaces/route_bake.py")]
    chunky = [BLENDER, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
              str(repo / "tools/props/library/inside/make_chunky.py"), "--", named["bake chunky job"]]
    subprocess.run([*route_bake, "bake-job", str(listing), str(listing.parent)], env=environment, check=True)
    while json.loads(pathlib.Path(named["bake chunky job"]).read_text()).get("square", {}).get("pending"):
        subprocess.run([*chunky, "--shapes"], check=True)  # the pending models' copies as they bake, no bake
        subprocess.run([*route_bake, "square-again", str(listing), str(listing.parent)], env=environment, check=True)
    subprocess.run(chunky, check=True)


if __name__ == "__main__":
    main()
