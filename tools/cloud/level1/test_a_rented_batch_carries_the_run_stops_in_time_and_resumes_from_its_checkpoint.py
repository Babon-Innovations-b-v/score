"""Level 1 on a rented machine (cloud.py, on_machine.py): a batch's job carries the run (never its latest evaluations),
its seeds, its cases' data folder and the model its jobs name, at their paths, runs in the Newton env and brings the
checkpoint, logs, results, evaluations and seeds back while it runs; every tuning body at once only when the run's own
level1.py takes --processes. On the machine level 1 runs from the run's own src with the card queue sized to that
card, its seeds built first from the run's own src when the seeds root lacks a case's, its workers' systemd-run scope stood in for where it does not work, and is stopped with its whole process group
at its minutes, the batch ending well so the next resumes; the chain ends when level 1 settles, a batch fails or adds
no checkpoint line. Nothing is rented: blender_cloud.py is never called, and nvidia-smi and systemd-run are stand-ins.

Breaks, each seen red once (2026-11-02):
- `carried`'s `if path.name not in LEFT_HERE` dropped -> the 451 MB of evals/ goes up every batch.
- `carried`'s `outside` made every named path -> each case's targets go up one by one beside their data folder.
- `job`'s `"bring_every"` dropped -> nothing comes back until the batch ends.
- `processes` returning the count for any run -> a run frozen before --processes fails on an unknown argument.
- on_machine's `start_new_session=True` dropped -> the stop kills only level 1, not its workers (the toy's sleeper lives).
- on_machine's `"SCORE_CARD_BUDGET_GB": str(card_gb())` dropped -> the card queue caps an 80 GB card at this PC's 13.5.
- on_machine's `scope_path()` returning PATH as it is -> a worker under systemd-run fails where root has no user manager.
- (2026-11-06) on_machine's `except FileNotFoundError` dropped -> in a cluster's pod, which has no systemd-run, the
  machine set-up dies before any go.sh runs.
- on_machine's `return 0` after the stop made `return child.returncode` -> a batch that ran its time reads as failed.
- `job`'s outputs without `seeds` -> seeds built on the machine never come back; every batch builds them again.
- on_machine's `if not seeded(run, seeds):` made `if False:` -> level 1 starts on an empty seeds root.
- on_machine's seed failure check `code != 0 or` dropped -> a seed step that failed (its angles written or not) starts level 1 anyway.
- `chain`'s `if lines(...) <= before` check dropped -> a batch that added nothing is followed by another.
- (2026-11-03) `job`'s outputs without the slice (run/home) -> what the machine kept never comes back; on_machine's
  SCORE_LEVEL1_STORE dropped -> the machine keeps its pieces outside the slice; `sliced`'s `exported` dropped -> the
  machine is given none of the seeds' marks and makes them again; `brought_back`'s merge dropped -> the pieces the
  slice brought are lost with it; `copied`'s `if target.read(key) is not None` check dropped -> a piece the PC's
  store holds is written over by the machine's.
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cloud  # noqa: E402

TOY_LEVEL1 = """import json, os, pathlib, subprocess, sys, time
run = pathlib.Path(sys.argv[1])
seeds = pathlib.Path(sys.argv[sys.argv.index("--card") + 1])
(run / "seen.json").write_text(json.dumps({"argv": sys.argv[1:], "budget": os.environ["SCORE_CARD_BUDGET_GB"],
                                          "store": os.environ["SCORE_LEVEL1_STORE"],
                                          "desktop": os.environ["SCORE_CARD_DESKTOP_GB"],
                                          "seeded": sorted(path.parent.name for path in seeds.glob("*/angles.npz"))}))
subprocess.run(["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G", "-q", "env", "A=1", "touch", str(run / "scoped")],
               check=True)
worker = subprocess.Popen(["sleep", "300"])
(run / "worker.pid").write_text(str(worker.pid))
with open(run / "checkpoint.jsonl", "a") as checkpoint:
    checkpoint.write("{}\\n")
print("eval 1: tuning score 1.0", flush=True)
time.sleep(300)
"""

TOY_INSIDE = {
    "landmarks.py": "HELD = set()\n",
    "tuning.py": "def layout(table, held, joints):\n    return sorted(table)\n\n\n"
                 "def applied(unknowns, entries, starts, table, globals_):\n    return dict(starts), dict(globals_)\n",
    "evaluation.py": "import json, os, pathlib, sys\n\n\ndef measured(rows, weights, rest, cases, out, python, most):\n"
                     "    failing = os.environ.get('TOY_SEED_FAILS')\n"
                     "    for case in cases:\n"
                     "        (out / case).mkdir(parents=True, exist_ok=True)\n"
                     "        (out / case / 'angles.npz').write_bytes(b'x')\n"
                     "    (out / 'asked.json').write_text(json.dumps({'rows': rows, 'rig': rest['rig'], 'most': most,\n"
                     "                                               'threads': os.environ['OMP_NUM_THREADS']}))\n"
                     "    if failing:\n"
                     "        sys.exit('a body failed')\n"
                     "    return cases\n",
}


def toy_run(root, processes):
    """A run folder, its seeds, its cases' data and the model their jobs name, under `root`."""
    run, data, model, seeds = root / "run", root / "data", root / "models" / "88b0", root / "seeds"
    for folder in (run / "evals" / "e00001", run / "evals" / "e00002", run / "evals" / "e00003", model, seeds):
        folder.mkdir(parents=True)
    cases = {}
    for body in ("tall", "short"):
        (data / body / "walk").mkdir(parents=True)
        (data / body / "walk" / "targets.npz").write_bytes(b"x")
        job = data / body / "walk" / "job.json"
        job.write_text(json.dumps({"model": str(model), "people": [{"targets": str(job.parent / "targets.npz")}]}))
        cases[f"{body}_walk"] = str(job)
    (run / "cases.json").write_text(json.dumps(cases))
    (run / "split.json").write_text(json.dumps({"tuning": ["tall"], "check": ["short"]}))
    (run / "checkpoint.jsonl").write_text("{}\n{}\n")
    (run / "start.pid").write_text("1")
    level1 = run / "src" / cloud.LEVEL1
    level1.parent.mkdir(parents=True)
    level1.write_text(TOY_LEVEL1 + ("# takes --processes\n" if processes else ""))
    inside = run / "src" / "score" / "stages" / "sim_body" / "inside"
    for name, text in TOY_INSIDE.items():
        (inside / name).write_text(text)
    (run / "table.json").write_text(json.dumps({"hip": {"link": "pelvis"}}))
    return run, seeds, data, model


def stand_ins(folder):
    """A PATH whose nvidia-smi says 81559 MiB and whose systemd-run fails, as root's over ssh may."""
    folder.mkdir()
    (folder / "nvidia-smi").write_text("#!/bin/sh\necho 81559\n")
    (folder / "systemd-run").write_text("#!/bin/sh\necho 'Failed to connect to bus' >&2\nexit 1\n")
    for name in ("nvidia-smi", "systemd-run"):
        (folder / name).chmod(0o755)
    return f"{folder}:{os.environ['PATH']}"


def test_a_rented_batch_carries_the_run_stops_in_time_and_resumes_from_its_checkpoint(tmp_path, monkeypatch):
    run, seeds, data, model = toy_run(tmp_path, processes=True)
    job = cloud.job(run, seeds, 230, 3, 20)
    assert set(job["inputs"]) == {str(run / name) for name in ("cases.json", "checkpoint.jsonl", "split.json", "src", "table.json")} \
        | {str(seeds), str(data), str(model)}
    assert {str(run / "checkpoint.jsonl"), str(run / "level1.log"), str(run / "held_out.json"),
            str(run / "home"), str(seeds)} <= set(job["outputs"])
    assert job["env"] == "score/stages/physics/inside/newton_env.sh" and job["bring_every"] == 20
    assert job["script"] == "tools/cloud/level1/on_machine.py" and job["minutes"] == 230
    assert job["args"][-2:] == ["--processes", "1"] and "215" in job["args"]  # its minutes less STOP_EARLY
    older, _, _, _ = toy_run(tmp_path / "older", processes=False)
    assert "--processes" not in cloud.job(older, seeds, 230, 3, 20)["args"]
    cloud.pruned(run)
    assert sorted(path.name for path in (run / "evals").iterdir()) == ["e00002", "e00003"]

    machine = {**os.environ, "HOME": str(tmp_path), "PATH": stand_ins(tmp_path / "bin")}
    launch = [sys.executable, str(cloud.LAUNCHER), str(run), "--seeds", str(seeds), "--minutes", "0.05",
              "--processes", "1"]
    failed = subprocess.run(launch, capture_output=True, text=True, timeout=120,
                            env={**machine, "TOY_SEED_FAILS": "1"})
    assert failed.returncode == 1 and not (run / "seen.json").exists()  # level 1 never started on a failed seeding
    assert "level 1 not started" in (run / "level1.log").read_text()
    began = time.time()
    ended = subprocess.run(launch, capture_output=True, text=True, timeout=120, env=machine)
    assert ended.returncode == 0, ended.stdout + ended.stderr
    asked = json.loads((seeds / "asked.json").read_text())  # the seeds came from the run's own src, table and rig
    assert asked["rows"] == {"hip": "pelvis"} and asked["rig"] == str(run / "rig.npz") and asked["threads"] == "2"
    assert asked["most"] == max(1, (os.cpu_count() or 2) // 2)
    assert time.time() - began < 60  # stopped at its minutes, not after the toy's 300 s
    seen = json.loads((run / "seen.json").read_text())
    assert seen["argv"][:3] == [str(run), "--python", sys.executable] and seen["argv"][-2:] == ["--processes", "1"]
    assert seen["seeded"] == ["short_walk", "tall_walk"]  # level 1 began on every case's seed
    assert (seen["budget"], seen["desktop"]) == ("77.6", "0")  # 81559 MiB less the margin, no desktop
    assert seen["store"] == str(run / "home" / "store")  # what it makes kept in the slice the job brings back
    assert (run / "scoped").exists()  # the worker ran through the systemd-run stand-in
    worker = int((run / "worker.pid").read_text())
    time.sleep(0.5)
    gone = subprocess.run(["ps", "-o", "stat=", "-p", str(worker)], capture_output=True, text=True).stdout.strip()
    assert gone in ("", "Z")  # the worker went with level 1's process group
    log = (run / "level1.log").read_text()
    assert "eval 1: tuning score 1.0" in log and "paused" in log
    assert len((run / "checkpoint.jsonl").read_text().splitlines()) == 3
    on_machine = types.ModuleType("level1_on_machine")  # a pod: no systemd-run on PATH at all
    exec((cloud.LAUNCHER).read_text(), on_machine.__dict__)
    (tmp_path / "bare").mkdir()
    monkeypatch.setattr(on_machine, "SHIM", tmp_path / "shim")
    monkeypatch.setenv("PATH", str(tmp_path / "bare"))
    assert on_machine.scope_path() == f"{tmp_path / 'shim'}:{tmp_path / 'bare'}"

    # the slice: the PC store's marks of the seeds given to the machine, its pieces put back, the first make standing
    stored = cloud.stored_module()
    pc = stored.Store.in_folder(tmp_path / "pc-store")
    (seeds / "tall_walk" / "angles.npz").write_bytes(b"seed")
    given = pc.put_tree(seeds / "tall_walk")
    stored.written_once(pc, "level1/cpu/k1.json", {"output": given})
    assert cloud.sliced(run, seeds, stored, pc) == 1
    machine_store = stored.Store.in_folder(run / "home" / "store")
    assert machine_store.read("level1/cpu/k1.json") == {"output": given}
    (tmp_path / "made").mkdir()
    (tmp_path / "made" / "measures.json").write_text("{}")
    stored.written_once(machine_store, "level1/card/k2.json", {"output": machine_store.put_tree(tmp_path / "made")})
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "angles.npz").write_bytes(b"other")
    machine_store.objects.path("level1/cpu/k1.json").unlink()  # the machine made k1 again, differently
    stored.written_once(machine_store, "level1/cpu/k1.json", {"output": machine_store.put_tree(tmp_path / "other")})
    assert cloud.brought_back(run, stored, pc) == 1 and not (run / "home").exists()
    assert pc.read_file(pc.read("level1/card/k2.json")["output"], "measures.json") == {}
    assert pc.read("level1/cpu/k1.json") == {"output": given}

    options = types.SimpleNamespace(batches=5, dry_run=False)
    adds = lambda run, seeds, options: (run / "checkpoint.jsonl").open("a").write("{}\n") > 0  # noqa: E731
    settles = iter([False, True])

    def settling(run, seeds, options):
        adds(run, seeds, options)
        if next(settles):
            (run / "held_out.json").write_text("{}")
        return True
    assert "settled in batch 2" in cloud.chain(run, seeds, options, settling)
    (run / "held_out.json").unlink()
    assert "batch 1 added no checkpoint line" in cloud.chain(run, seeds, options, lambda *_: True)
    assert "batch 1 failed" in cloud.chain(run, seeds, options, lambda *_: False)
    assert cloud.chain(run, seeds, options, adds) == "5 batches ran; resume with another call"
