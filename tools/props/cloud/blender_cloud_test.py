"""Check the generic cloud Blender job without renting anything: a job's paths and arguments land under /root/fs on
the machine, an argument outside them is left alone, the script's folder goes up with tools/blender/inside, and a card
machine runs Cycles on the card.

Run: .venv/bin/python tools/props/cloud/blender_cloud_test.py   (make tests runs it)
"""
import pathlib
import shlex
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_cloud  # noqa: E402


def paths_move_to_the_machine():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary).resolve()
        job = {"script": "tools/blender/inside/settle_stage.py", "inputs": [str(folder / "stage")],
               "outputs": [str(folder / "out.json")],
               "args": [str(folder / "stage/place.usda"), str(folder / "out.json"), "--fast", "12"]}
        words = shlex.split(blender_cloud.run_line(job, card=False))
        arguments = words[words.index("--") + 1:]
        expected = [f"/root/fs{folder}/stage/place.usda", f"/root/fs{folder}/out.json", "--fast", "12"]
        problems = []
        if arguments != expected:
            problems.append(f"the arguments up there are {arguments}, not {expected}")
        if "/root/lib/repo/tools/blender/inside/settle_stage.py" not in words:
            problems.append("the script is not run from the machine's copy of the repo")
        if "FARM_CYCLES_CPU=1" not in words or "FARM_CYCLES_GPU=1" not in shlex.split(blender_cloud.run_line(job, True)):
            problems.append("a processor machine does not render with Cycles on its cores, or a card machine on the card")
        return problems


def the_scripts_folders_go_up():
    found = blender_cloud.shipped([{"script": "tools/props/library/inside/show.py"},
                                   {"script": "tools/blender/inside/usd_views.py"}])
    expected = ["tools/blender/inside", "tools/props/library/inside"]
    return [] if found == expected else [f"the folders sent are {found}, not {expected}"]


CHECKS = (paths_move_to_the_machine, the_scripts_folders_go_up)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
