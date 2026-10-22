"""The conductor's free end-to-end check passes every step, says it in one line and keeps its detail in a file.

Run: .venv/bin/python score/conductor/dry_test.py
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

REPO = pathlib.Path(__file__).resolve().parents[2]


def test_the_dry_check_passes_every_step_in_one_line():
    done = subprocess.run([sys.executable, "-m", "score.conductor", "dry"], cwd=REPO, capture_output=True, text=True,
                          timeout=110)
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("conductor dry: 7 of 7 steps passed; detail "), done.stdout + \
        done.stderr[-2000:]
    detail = pathlib.Path(lines[0].rpartition("detail ")[2])
    results = json.loads(detail.read_text())
    assert [result["step"] for result in results] == ["plan", "waiting for size", "resume", "memory guard",
                                                      "health and logs", "shrink", "kill switch"]
    assert done.returncode == 0


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
