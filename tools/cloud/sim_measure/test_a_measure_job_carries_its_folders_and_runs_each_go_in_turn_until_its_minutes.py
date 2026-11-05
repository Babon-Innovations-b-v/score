"""Measure folders on a rented machine (cloud.py, on_machine.py): the job carries the folders, the carries, the paths
their job*.json files name outside them and the repo pieces the go scripts use, brings the folders back while it runs,
in the Newton env, and refuses a folder whose script writes a repo path itself; on the machine each go.sh runs in
turn with PY, REPO (the carried repo), LANES and the card queue sized to the card, a go.sh
that failed lets the next run, and one still running at the job's minutes is stopped with its process group, the job
exiting 3. Nothing is rented: blender_cloud.py is never called, and nvidia-smi and systemd-run are stand-ins.

Breaks, each seen red once (2026-11-04):
- `carried`'s `outside` dropped -> the model folder a clip's job.json names never goes up; the fit cannot open it.
- `carried` without REPO_CARRIED -> PYTHONPATH and the card queue name a repo the machine lacks.
- `job`'s `"bring_every"` dropped -> nothing comes back until the job ends.
- on_machine's `"PY": sys.executable` dropped -> go.sh runs this PC's Newton path, absent on the machine.
- on_machine's `if code is None` return made `continue` -> the job reads as ended well after it was cut off.
- on_machine stopping at a go.sh's non-zero exit -> one failed clip keeps the next folder from running.
- (2026-11-05) on_machine's `"REPO": str(repo)` dropped -> a go.sh's ${REPO}/tools/cloud/backends/card_queue.py is
  /tools/..., absent on the machine.
- (2026-11-05) `hard_coded`'s `roots` made `[]` -> a go.sh naming the main checkout's card queue goes up from a
  worktree, whose path alone is carried, and every job dies in its first second (2026-11-04).
- (2026-11-05) `in_stock_order`'s `key` dropped -> a scarce H100 asked first is fixed for the call and its jobs wait
  for stock while an L40S and an L4 stand free.
- (2026-11-05) `uncarried`'s `path.exists()` test made `False` -> a go.sh reading clips never carried goes up, and the
  job ends at once with 0 of 6.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cloud  # noqa: E402

FIRST = """#!/bin/bash
echo "$PY $REPO $LANES $SCORE_CARD_BUDGET_GB $SCORE_CARD_DESKTOP_GB" > "$(dirname "$0")/../seen.txt"
exit 1
"""
SECOND = """#!/bin/bash
touch "$(dirname "$0")/../started"
sleep 300
"""


def stand_ins(folder):
    """A PATH whose nvidia-smi says 81559 MiB and whose systemd-run fails, as root's over ssh may."""
    folder.mkdir()
    (folder / "nvidia-smi").write_text("#!/bin/sh\necho 81559\n")
    (folder / "systemd-run").write_text("#!/bin/sh\necho 'Failed to connect to bus' >&2\nexit 1\n")
    for name in ("nvidia-smi", "systemd-run"):
        (folder / name).chmod(0o755)
    return f"{folder}:{os.environ['PATH']}"


def test_a_measure_job_carries_its_folders_and_runs_each_go_in_turn_until_its_minutes(tmp_path):
    first, second, data, model, written = (tmp_path / name for name in ("first", "second", "data", "models/88b0",
                                                                         "written"))
    repo = cloud.blender_cloud.REPO
    for folder, script in ((first, FIRST), (second, SECOND),
                           (written, f"python3 {min(cloud.checkouts())}/tools/cloud/backends/card_queue.py run\n")):
        (folder / "scripts").mkdir(parents=True)
        (folder / "scripts" / "go.sh").write_text(script)
    (data / "walk").mkdir(parents=True)
    model.mkdir(parents=True)
    (data / "walk" / "targets.npz").write_bytes(b"x")
    (data / "walk" / "job.json").write_text(json.dumps({"model": str(model),
                                                        "people": [{"targets": str(data / "walk" / "targets.npz")}]}))
    assert cloud.hard_coded([first, second, written]) == [written / "scripts" / "go.sh"]
    job = cloud.job([first, second], [data], 170, 20)
    assert set(job["inputs"]) == {str(first), str(second), str(data), str(model),
                                  *(str(repo / part) for part in cloud.REPO_CARRIED)}
    assert job["outputs"] == [str(first), str(second)] and job["bring_every"] == 20 and job["minutes"] == 170
    assert job["env"] == "score/stages/physics/inside/newton_env.sh"
    assert job["script"] == "tools/cloud/sim_measure/on_machine.py" and "155" in job["args"]  # less STOP_EARLY

    machine = {**os.environ, "HOME": str(tmp_path), "PATH": stand_ins(tmp_path / "bin")}
    began = time.time()
    ended = subprocess.run([sys.executable, str(cloud.LAUNCHER), str(first), str(second), "--minutes", "0.05",
                            "--repo", str(repo)], capture_output=True, text=True, timeout=120, env=machine)
    assert ended.returncode == 3, ended.stdout + ended.stderr  # cut off at its minutes
    assert time.time() - began < 60 and (second / "started").exists()  # the next folder ran after a failed go.sh
    python, carried, lanes, budget, desktop = (first / "seen.txt").read_text().split()
    assert python == sys.executable and carried == str(repo) and int(lanes) == max(1, (os.cpu_count() or 4) // 4)
    assert (budget, desktop) == ("77.6", "0")
    assert "go.sh exit 1" in ended.stdout and "stopped at the job's minutes" in ended.stdout

    from types import SimpleNamespace as Offer
    found = [Offer(machine_class="gpu-80gb-x2-48c", stock_word="scarce"), Offer(machine_class="gpu-80gb", stock_word="shortage"),
             Offer(machine_class="gpu-48gb", stock_word="available"), Offer(machine_class="gpu-24gb", stock_word="available")]
    asked = ["gpu-80gb-x2-48c", "gpu-80gb-x2", "gpu-80gb", "gpu-48gb", "gpu-24gb"]
    assert cloud.in_stock_order(asked, found) == ["gpu-48gb", "gpu-24gb", "gpu-80gb-x2-48c", "gpu-80gb-x2", "gpu-80gb"]

    outside = tmp_path / "clips"
    outside.mkdir()
    (first / "scripts" / "go.sh").write_text(f"#!/bin/bash\nPY=${{PY:-{outside}}}\nls {outside}\n")
    assert cloud.uncarried([first], []) == [str(outside)] and cloud.uncarried([first], [outside]) == []
