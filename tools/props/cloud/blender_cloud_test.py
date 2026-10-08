"""Check the generic cloud Blender job without renting anything: a job's arguments reach the script as they are (its
files lie at the same paths up there), the script runs from the machine's copy of the repo, its folder goes up with
tools/blender/inside, and a card machine runs Cycles on the card, a processor machine on its cores.

Run: .venv/bin/python tools/props/cloud/blender_cloud_test.py   (make tests runs it)
"""
import pathlib
import shlex
import sys
import tempfile
import threading

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
        expected = [f"{folder}/stage/place.usda", f"{folder}/out.json", "--fast", "12"]
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


class Answering:
    """A stand-in for the --serve process: it answers each job file in the queue as told, without renting."""

    def __init__(self, queue, answer):
        self.queue, self.answer, self.stop = queue, answer, threading.Event()
        threading.Thread(target=self.watch, daemon=True).start()

    def watch(self):
        while not self.stop.wait(0.05):
            for job in self.queue.glob("*.json"):
                if not job.with_suffix(".done").exists() and not job.with_suffix(".failed").exists():
                    job.with_suffix(f".{self.answer}").write_text("answered")

    def poll(self):
        return None

    def wait(self):
        self.stop.set()


def a_held_machine_runs_a_chain():
    with tempfile.TemporaryDirectory() as temporary:
        problems = []
        for answer in ("done", "failed"):
            machine = blender_cloud.Machine(["cpu-32c-128gb"], "test")
            machine.queue = pathlib.Path(temporary) / answer
            machine.queue.mkdir()
            machine.process = Answering(machine.queue, answer)
            script = blender_cloud.REPO / "tools/blender/inside/usd_views.py"
            try:
                machine.run(script, ["a"], [], [])
                machine.run(script, ["b"], [], [])
                if answer == "failed":
                    problems.append("a failed job did not raise")
            except RuntimeError:
                if answer == "done":
                    problems.append("a done job raised")
            machine.__exit__(None, None, None)
            if answer == "done" and sorted(path.name for path in machine.queue.glob("*.json")) != ["1.json", "2.json"]:
                problems.append("the chain's jobs were not queued in order on one machine")
            if not (machine.queue / "close").exists():
                problems.append("the queue was not closed at the end of the chain")
        return problems


CHECKS = (paths_move_to_the_machine, the_scripts_folders_go_up, a_held_machine_runs_a_chain)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
