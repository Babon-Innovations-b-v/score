"""Runs inside Blender on a rented card (tools/props/cloud/blender_cloud.py, the finish route's bake,
../route_bake.py): one take painted and baked in one job, so nothing heavy runs on the owner's PC (#18, 2026-10-20).

    blender -b --python paint_bake.py -- <listing>    (route_bake.card_job's: the bake's inputs, the take, its part
                                                       records, claimed rows and job head)

First the paint, as paint_take.py runs it (place_line.py's `paint-take` in Blender's own Python with the pinned
packages, its peak memory said); then route_bake.py's `bake-job` there too (the take's models' make_chunky entries
over the labelled take); then make_chunky.py in a Blender of its own, Cycles on the card (blender_cloud.py sets
FARM_CYCLES_GPU and PROPS_HOME for ProcFunc's site). Any step that fails fails the job: its models are a hole.
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
    subprocess.run([paint_take.PYTHON, str(repo / "score/stages/surfaces/route_bake.py"), "bake-job", str(listing),
                    str(listing.parent)], env=dict(os.environ, PYTHONPATH=str(paint_take.SITE),
                                                   PROPS_HOME=named["props home"]), check=True)
    subprocess.run([BLENDER, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                    str(repo / "tools/props/library/inside/make_chunky.py"), "--", named["bake chunky job"]], check=True)


if __name__ == "__main__":
    main()
