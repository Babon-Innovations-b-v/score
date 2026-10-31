"""tools/cloud/this_pc.py: a run on this PC's card pulls only what a run reads from the conductor's home (never its
keys, ledgers or run registry), runs free only on this PC's card in a home of its own, and pushes back only by adding
files, never replacing one the conductor has. The agents' door itself (agent_door.py, as sshd's forced command runs
it) stands in for ssh, a folder for the conductor's home; nothing reaches the conductor.

Breaks (each applied once, seen red, reverted):
- agent_door.py `PULLED`: add "cloud" -> the runner's ssh key comes down with the store.
- agent_door.py `store_pull`: drop the `continue` after `kept += 1` -> a second pull sends every file again.
- agent_door.py `store_missing`: name every path, not only those missing -> the push carries files the conductor
  holds (its own add-only refusal is the door's test).
- this_pc.py `ENVIRONMENT`: drop "SCORE_FREE_ONLY": "1" -> a run here may buy (its runs are not free only).
- this_pc.py `run_environment`: drop `found.pop(OWNERS_GO, None)` -> a go from this shell tags every run.
- this_pc.py `deciding`: `run_environment(home)` -> `os.environ` -> the decision reaches the PC's old home.
- this_pc.py `push`: drop the `except FileNotFoundError: continue` -> a file a live run removed after the listing
  ends the push (2026-10-28).
- this_pc.py `pause`: drop the `while group_alive(leader)` wait -> the container stops while the run still holds it.
- this_pc.py `stop_containers`: `names or [MACHINE]` -> `[MACHINE]` -> a kind's own container keeps the card.
- this_pc.py `RUN_OWN`: drop "SCORE_FROZEN" -> a resumed run would carry the paused run's frozen copy.
- this_pc.py `resume`: drop its `live_run` refusal -> a second run starts beside the live one.
- this_pc.py `resume`: drop `**record["env"]` -> the resumed run loses its go and SCORE_MIN_FREE_GB.
- this_pc.py `newest_beat`: `found[-1]` -> `found[0]` -> status says the oldest heartbeat's rows.
- this_pc.py `DESIGN_STEPS`: drop "score.stages.complete.prepare" -> `score run` reads the stale hand-in, its
  spaceship at the plan's 13.7 x 46 m footprint (2026-10-30: a hand-in fix never landed on this PC).
- this_pc.py `design_current`: drop the `while live_run(home)` wait -> prepare runs while the plan row run the keep
  started holds the store.
- this_pc.py `design_current`: drop the `if done.returncode` refusal -> a run starts on a hand-in its step failed
  to write.
- this_pc.py `run`: drop the `entry is None` test -> the steps rewrite the design a live run reads.
- this_pc.py `resume`: drop `design_current(home, code, environment)` -> a resumed run reads the design as paused.
- this_pc.py `pull`: drop the `OWN_DESIGN` skip -> the conductor's hand-in comes back over the one written here.
"""
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import this_pc  # noqa: E402


def door(conductor, verb):
    """The door's command for `verb` against the folder `conductor`, as sshd would run it."""
    return ["env", f"SSH_ORIGINAL_COMMAND={verb}", f"PROPS_HOME={conductor}", "SCORE_DOOR_ENV=/nonexistent",
            sys.executable, str(HERE / "conductor" / "agent_door.py")]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_pull_brings_what_a_run_reads_and_no_key_or_ledger_and_again_only_what_changed(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    for name in ("store/objects/blobs/aa", "design/plans/hub.json", "work/pixal/take.glb", "cloud/google-cache/q.json",
                 "cache/library/swatch.png", "cloud/ssh_key", "cloud/self_delete_key.json", "cloud/ledger.jsonl",
                 "runs/active.json", "store/cache/checkouts/x", "frozen/copy/file", "dashboard/db.sqlite3"):
        write(conductor / name, name)
    home.mkdir()
    assert this_pc.pull(home, door(conductor, "store-pull")) == (5, sum(
        len(name) for name in ("store/objects/blobs/aa", "design/plans/hub.json", "work/pixal/take.glb",
                               "cloud/google-cache/q.json", "cache/library/swatch.png")))
    pulled = sorted(str(path.relative_to(home)) for path in home.rglob("*") if path.is_file())
    assert pulled == ["cache/library/swatch.png", "cloud/google-cache/q.json", "design/plans/hub.json",
                      "store/objects/blobs/aa", "work/pixal/take.glb"]
    write(conductor / "design/plans/hub.json", "the hub, changed")
    assert this_pc.pull(home, door(conductor, "store-pull")) == (1, len("the hub, changed"))
    assert (home / "design/plans/hub.json").read_text() == "the hub, changed"


def test_a_pull_never_brings_a_hand_in_over_the_one_written_here(tmp_path):
    """The conductor's hand-in differs from this PC's in mtime, so the door sends it; pull leaves it out (2026-10-30)."""
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    write(conductor / "design/props/hangar.json", "the conductor's, plan-footprint sizes")
    write(conductor / "design/surfaces/hangar.json", "the conductor's surface data")
    write(home / "design/props/hangar.json", "written here by prepare, read sizes")
    assert this_pc.pull(home, door(conductor, "store-pull")) == (0, 0)
    assert (home / "design/props/hangar.json").read_text() == "written here by prepare, read sizes"
    assert not (home / "design/surfaces/hangar.json").exists()


def stale_hand_in(home):
    """A home whose hangar hand-in carries the spaceship's plan footprint, not the size prepare writes now."""
    write(home / "design/props/hangar.json", this_pc.json.dumps({"rows": [{"id": "spaceship", "size": [13.688, 45.965,
                                                                                                        4.0]}]}))


def test_a_run_here_rewrites_a_stale_hand_in_before_score_run_starts(tmp_path, monkeypatch):
    """The sync pass's plans keep, then prepare, run against this home, free only, from the run's code; a plan row run
    the keep starts is waited out; only then `score run`, which reads the rewritten hand-in. Prepare stands in here
    (its rewrite of a hand-in is prepare's own test's): it writes the size it would write now."""
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    home = tmp_path / "home"
    (tmp_path / "env").mkdir()
    stale_hand_in(this_pc.prepared(home))  # its key made before subprocess.run stands in
    events, plan_run = [], []

    def step(command, **given):
        module = command[2]
        events.append((module, given["cwd"], given["env"]["PROPS_HOME"], given["env"]["SCORE_FREE_ONLY"]))
        if module == "score.review.plans_pass":
            plan_run.append({"id": "plan-run", "pid": 1})  # keep started a changed place's plan row, detached
        if module == "score.stages.complete.prepare":
            assert not plan_run, "prepare ran while the plan row run held the store"
            write(home / "design/props/hangar.json", this_pc.json.dumps({"rows": [{"id": "spaceship",
                                                                                   "size": [8.0, 24.0, 4.0]}]}))
        return subprocess.CompletedProcess(command, 0, f"{module} done\n", "")

    def waited(seconds):
        events.append(("waited", seconds))
        plan_run.clear()
    monkeypatch.setattr(this_pc, "asked", step)
    monkeypatch.setattr(this_pc, "live_run", lambda found: plan_run[0] if plan_run else None)
    monkeypatch.setattr(this_pc.time, "sleep", waited)

    def score_run(command, **given):
        size = this_pc.json.loads((home / "design/props/hangar.json").read_text())["rows"][0]["size"]
        events.append(("score run", size))
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(this_pc.subprocess, "run", score_run)
    assert this_pc.run(home, ["world1"]) == 0
    assert events == [("score.review.plans_pass", this_pc.REPO, str(home), "1"), ("waited", 5),
                      ("score.stages.complete.prepare", this_pc.REPO, str(home), "1"), ("score run", [8.0, 24.0, 4.0])]


def test_a_run_here_leaves_the_design_of_a_live_run_and_stops_on_a_failed_step(tmp_path, monkeypatch):
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    home = tmp_path / "home"
    (tmp_path / "env").mkdir()
    stale_hand_in(this_pc.prepared(home))  # its key made before subprocess.run stands in
    asked = []
    monkeypatch.setattr(this_pc, "asked", lambda command, **given: asked.append(command) or
                        subprocess.CompletedProcess(command, 1, "", "Traceback\nKeyError: 'hangar'\n"))
    started = []
    monkeypatch.setattr(this_pc.subprocess, "run", lambda command, **given: started.append(command) or
                        subprocess.CompletedProcess(command, 0))
    monkeypatch.setattr(this_pc, "live_run", lambda found: {"id": "live-run"})
    assert this_pc.run(home, ["world1", "--place", "hub"]) == 0 and not asked and len(started) == 1
    monkeypatch.setattr(this_pc, "live_run", lambda found: None)
    with pytest.raises(SystemExit, match="score.review.plans_pass failed .exit 1.: KeyError: 'hangar'"):
        this_pc.run(home, ["world1"])
    assert len(started) == 1  # no score run after a failed step


def test_a_push_adds_new_outputs_and_never_replaces_the_conductors(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    write(conductor / "store/objects/records/hub/k1.json", "the conductor's record")
    write(home / "store/objects/records/hub/k1.json", "this PC's record")
    write(home / "store/objects/records/hub/k2.json", "made on this PC")
    write(home / "work/pixal/new.glb", "a take")
    write(home / "cloud/ssh_key", "this PC's runner key")
    pushed = this_pc.push(home, door(conductor, "store-push --missing"), door(conductor, "store-push"))
    assert pushed == (2, len("made on this PC") + len("a take"))  # only what the conductor lacks went
    assert (conductor / "store/objects/records/hub/k1.json").read_text() == "the conductor's record"
    assert (conductor / "store/objects/records/hub/k2.json").read_text() == "made on this PC"
    assert (conductor / "work/pixal/new.glb").read_text() == "a take"
    assert not (conductor / "cloud").exists() and not list((conductor / "tmp/this-pc-push").iterdir())


def test_a_push_skips_a_file_a_live_run_removed_after_it_was_listed(tmp_path, monkeypatch):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    write(home / "store/objects/records/hub/k2.json", "made on this PC")
    write(home / "work/motion-scratch/layer/garage.usda", "scratch")
    listed = this_pc.walked
    def gone_after_listing(*arguments):
        found = list(listed(*arguments))
        (home / "work/motion-scratch/layer/garage.usda").unlink()
        return found
    monkeypatch.setattr(this_pc, "walked", gone_after_listing)
    pushed = this_pc.push(home, door(conductor, "store-push --missing"), door(conductor, "store-push"))
    assert pushed == (1, len("made on this PC"))
    assert (conductor / "store/objects/records/hub/k2.json").read_text() == "made on this PC"


def test_a_run_here_is_free_only_on_this_pcs_card_in_its_own_home(tmp_path, monkeypatch):
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    home = this_pc.prepared(tmp_path / "home")
    environment = this_pc.run_environment(home)
    assert {key: environment[key] for key in this_pc.ENVIRONMENT} == {
        "SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1", "SCORE_MAX_MACHINES": "all=1"}
    assert environment["PROPS_HOME"] == str(home) and (home / "cloud/ssh_key.pub").exists()
    assert (home / "env").is_symlink()


def test_a_run_here_carries_the_owners_go_only_when_named_and_decisions_reach_its_own_store(tmp_path, monkeypatch):
    """His go (owner, 2026-10-27) tags only the run that names it, never one from this shell; decide-yes and decide
    run the cockpit's command against this home's store with the owner his cockpit names."""
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    monkeypatch.setenv(this_pc.OWNERS_GO, "smuggled")
    home = this_pc.prepared(tmp_path / "home")
    assert this_pc.OWNERS_GO not in this_pc.run_environment(home)
    arguments, go = this_pc.go_taken(["world1", "--go", "20261027T170000Z", "--place", "hub"])
    assert arguments == ["world1", "--place", "hub"] and go == "20261027T170000Z"
    assert this_pc.run_environment(home, go)[this_pc.OWNERS_GO] == go
    assert this_pc.go_taken(["world1"]) == (["world1"], None)
    ran = []
    monkeypatch.setattr(this_pc.subprocess, "run", lambda command, **given: ran.append((command, given["env"])) or
                        subprocess.CompletedProcess(command, 0))
    monkeypatch.delenv("SCORE_OWNER", raising=False)
    monkeypatch.setattr(this_pc, "DASHBOARD_ENV", tmp_path / "dashboard.env")
    (tmp_path / "dashboard.env").write_text("SCORE_OWNER=joey\n")
    assert this_pc.deciding(home, "decide", ["20261027T170000Z"]) == 0
    command, environment = ran[0]
    assert command[1:] == ["-m", "score.dashboard", "decide", "20261027T170000Z"]
    assert environment["PROPS_HOME"] == str(home) and environment["SCORE_OWNER"] == "joey"
    assert this_pc.OWNERS_GO not in environment


def stand_in_run(home, tmp_path, **variables):
    """A stand-in `score run`: a process leading its own group with a child in it, ended by SIGTERM a second after it
    came, registered as running in `home`'s run registry; (process, its entry)."""
    script = ("import signal, subprocess, sys, time; stopping = []; "
              "signal.signal(signal.SIGTERM, lambda *_: stopping.append(1)); child = subprocess.Popen([sys.executable, "
              "'-c', 'import time; time.sleep(60)']); print('ready', flush=True)\n"
              "while not stopping: time.sleep(0.05)\n"
              "time.sleep(1); child.terminate(); child.wait()")
    log = tmp_path / "run.log"
    log.write_text("heartbeat a: rows done 1, running 2, queued 3; x\nheartbeat b: rows done 4, running 5, queued 6; y\n")
    process = subprocess.Popen([sys.executable, "-c", script, "score"], start_new_session=True, stdout=log.open("a"),
                               env={"PATH": "/usr/bin:/bin", **variables})
    while "ready" not in log.read_text():
        assert process.poll() is None, log.read_text()
        this_pc.time.sleep(0.05)
    entry = {"id": "20261028T131330-1", "argv": ["run", "world1", "--jobs", "8", "--free"], "commit": "a" * 40,
             "worktree": str(tmp_path / "frozen"), "pid": process.pid, "state": "running"}
    write(home / "runs" / f"{entry['id']}.json", this_pc.json.dumps(entry))
    write(home / "runs" / "active.json", "{}")
    return process, entry


def test_pause_records_the_run_stops_it_and_only_then_the_container(tmp_path, monkeypatch):
    """Pause (owner, 2026-10-28): the live run's arguments, commit and run variables recorded, its whole group stopped
    by one SIGTERM, and `docker stop` only once no process of it holds the card."""
    home = tmp_path / "home"
    process, entry = stand_in_run(home, tmp_path, SCORE_MIN_FREE_GB="8", SCORE_OWNERS_GO="go1", SCORE_CLOUD="local",
                                  SCORE_FROZEN="/frozen/copy", PROPS_HOME="/frozen/copy.home")
    called = []
    listed = "score-this-pc\npostgres\nscore-this-pc-segment\n"
    monkeypatch.setattr(this_pc, "asked", lambda command, **given: called.append(
        (command, this_pc.group_alive(process.pid))) or subprocess.CompletedProcess(command, 0, listed, ""))
    line = this_pc.pause(home)
    assert process.wait(timeout=5) == 0 and not this_pc.group_alive(process.pid)
    stops = [call for call in called if call[0][:2] == ["docker", "stop"]]
    assert stops == [(["docker", "stop", "score-this-pc", "score-this-pc-segment"], False)]  # every SCORE container,
    # once the run's group was gone
    record = this_pc.json.loads((home / this_pc.PAUSED).read_text())
    assert record["argv"] == entry["argv"] and record["commit"] == "a" * 40
    assert record["env"] == {"SCORE_MIN_FREE_GB": "8", "SCORE_OWNERS_GO": "go1", "SCORE_CLOUD": "local"}
    assert record["log"] == str(tmp_path / "run.log") and line.startswith(f"paused run {entry['id']}")
    assert this_pc.status_line(home).startswith(f"paused {entry['id']} since ")
    assert "rows done 4, running 5, waiting 6" in this_pc.status_line(home)


def test_resume_refuses_while_a_run_is_live_and_starts_the_paused_one_detached_as_it_ran(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    monkeypatch.setenv(this_pc.OWNERS_GO, "smuggled")
    process, entry = stand_in_run(home, tmp_path)
    try:
        with pytest.raises(SystemExit, match="refused, run .* is live"):
            this_pc.resume(home)
        assert this_pc.status_line(home).startswith(f"running {entry['id']}")
    finally:
        process.kill()
        process.wait()
    record = {"id": entry["id"], "argv": entry["argv"], "commit": "b" * 40, "log": None, "paused": "now",
              "env": {"SCORE_MIN_FREE_GB": "8", "SCORE_OWNERS_GO": "go1"}}
    write(home / this_pc.PAUSED, this_pc.json.dumps(record))
    called = []

    def stand_in(command, **given):
        called.append((command, given))
        if command[3:5] == ["worktree", "add"]:
            pathlib.Path(command[-2]).mkdir()
        out = "detached: started pid=9 log=/home/logs/score-run.log\n" if "--detach" in command else ""
        return subprocess.CompletedProcess(command, 0, out, "")
    monkeypatch.setattr(this_pc, "asked", stand_in)
    assert this_pc.resume(home) == (f"resumed run world1 --jobs 8 --free at {'b' * 12}: "
                                    "detached: started pid=9 log=/home/logs/score-run.log")
    assert called[0][0] == ["docker", "start", "score-this-pc"]
    assert called[1][0][3:] == ["worktree", "add", "--detach", "--force", str(home / "resume-code"), "b" * 40]
    # the design brought up to date by the paused run's own code, in its home, before it starts again
    assert [(command[1:], given["cwd"], given["env"]["PROPS_HOME"]) for command, given in called[2:-1]] == [
        (["-m", module], home / "resume-code", str(home)) for module in this_pc.DESIGN_STEPS]
    command, given = called[-1]
    assert command[1:] == ["-m", "score", *entry["argv"], "--detach"] and given["cwd"] == home / "resume-code"
    assert {key: given["env"][key] for key in ("SCORE_MIN_FREE_GB", this_pc.OWNERS_GO, "SCORE_FREE_ONLY",
                                               "PROPS_HOME")} == {"SCORE_MIN_FREE_GB": "8", this_pc.OWNERS_GO: "go1",
                                                                  "SCORE_FREE_ONLY": "1", "PROPS_HOME": str(home)}
    assert not (home / this_pc.PAUSED).exists()
    assert this_pc.status_line(home).startswith("neither running nor paused")
