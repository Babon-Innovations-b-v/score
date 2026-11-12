"""Runs inside Blender on the bake's card: paint_bake.py's job (the paint, the take's make_chunky entries, the pending
models stood square) with its last step, the bake, run through layout_fit.py, so each model's texture layout is laid
again before it bakes where surfaces-check's "texture layout sound" would fail it (#118), and its paint through
../base_level.py, so a take's base counts level within 3 cm through its standing height, as its feet do.

    blender -b --python paint_fit.py -- <listing>    (route_bake.card_job's, its script set by ../bake_fitted.py)

Its own script, not an edit of paint_bake.py: every row whose code reaches route_bake.py declares paint_bake.py and what
it starts, so an edit there moved 28 rows (11 paid); this one only the bake row starts.
"""
import json
import os
import pathlib
import signal
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import paint_bake  # noqa: E402
import paint_take  # noqa: E402


def paint():
    """paint_take.main with the paint run by ../base_level.py (place_line's paint-take, its base levelled within 3 cm
    through the take's standing height)."""
    listing = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
    named = json.loads(listing.read_text())
    paint_take.install()
    repo = pathlib.Path(named["paint repo"])
    environment = dict(os.environ, PYTHONPATH=str(paint_take.SITE), PROPS_HOME=named["props home"],
                       FARM_LOCAL_MODELS="1")
    code, peak = paint_take.measured([paint_take.PYTHON, str(repo / "score/stages/surfaces/base_level.py"),
                                      "paint-take", str(listing), str(listing.parent)], environment)
    killed = f", killed by {signal.Signals(-code).name}" if code < 0 else ""
    print(f"paint {named['paint take']}: exit code {code}{killed}, peak memory {peak:.2f} GB", flush=True)
    if code:
        raise RuntimeError(f"the paint of {named['paint take']} failed")


def main():
    paint()
    listing = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
    named = json.loads(listing.read_text())
    repo = pathlib.Path(named["paint repo"])
    environment = dict(os.environ, PYTHONPATH=str(paint_take.SITE), PROPS_HOME=named["props home"])
    route_bake = [paint_take.PYTHON, str(repo / "score/stages/surfaces/route_bake.py")]
    blender = [paint_bake.BLENDER, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python"]
    chunky = [*blender, str(repo / "tools/props/library/inside/make_chunky.py"), "--", named["bake chunky job"]]
    fitted = [*blender, str(repo / "score/stages/surfaces/inside/layout_fit.py"), "--", named["bake chunky job"]]
    subprocess.run([*route_bake, "bake-job", str(listing), str(listing.parent)], env=environment, check=True)
    while json.loads(pathlib.Path(named["bake chunky job"]).read_text()).get("square", {}).get("pending"):
        subprocess.run([*chunky, "--shapes"], check=True)  # the pending models' copies as they bake, no bake
        subprocess.run([*route_bake, "square-again", str(listing), str(listing.parent)], env=environment, check=True)
    subprocess.run(fitted, check=True)


if __name__ == "__main__":
    main()
