"""tools/cloud/this_pc.py: a run on this PC's card pulls only what a run reads from the conductor's home (never its
keys, ledgers or run registry), runs free only on this PC's card in a home of its own, and pushes back only by adding
files, never replacing one the conductor has. The agents' door itself (agent_door.py, as sshd's forced command runs
it) stands in for ssh, a folder for the conductor's home; nothing reaches the conductor.

Breaks (each applied once, seen red, reverted):
- agent_door.py `PULLED`: add "cloud" -> the runner's ssh key comes down with the store; or drop "dashboard/films"
  -> the locked film script and the preview's takes stay on the conductor, environment-film Blocked here.
- agent_door.py `store_pull`: drop the `continue` after `kept += 1` -> a second pull sends every file again; or
  drop `name.startswith(STORE_OBJECTS)` -> a store object held here is sent again for its other mtime.
- agent_door.py `listed`: drop the gunzip -> this PC's gzipped manifest is read as text and the pull fails (the
  plain lines the --differs check sends still read: the ssh door's old callers).
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
- this_pc.py `stop`: drop the `os.killpg` -> a run still draining after its wait is left beside the next (#111).
- this_pc.py `start_refusal`: drop its `live_run` test -> a run starts beside a live one; or drop the `reason is
  None` test -> a restart within RESTART_HOURS goes without a reason (#112).
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
- this_pc.py `pull`: drop the `OWN_DESIGN` skip -> the conductor's hand-in comes back over the one written here;
  or drop the `BLOBS` skip -> a read-only blob held here, sent again for its other mtime, stops the pull; or
  `linked_anew` always True -> a hard link over its own path stops the pull (seeking backwards); or drop
  `cleared` -> a changed work file held here as a read-only link stops the pull, or is written through; or drop
  `cut_blobs_cleared(home)` (or `held_whole`'s hash) -> a blob held here cut short is kept and never pulled whole;
  or `landed_whole` writes straight at its path -> a pull killed midway leaves a cut blob under its name.
- agent_door.py `store_differs`: `file_sha(target) != sha` -> `False` -> a take remade here at the same size keeps
  the conductor's old bytes (2026-11-03: 22 places' palette rows due).
- agent_door.py `replaced`: drop `os.link(target, keep)` -> the conductor's old file is lost, not kept.
- agent_door.py `replaceable_target`: drop the REPLACEABLE test -> a push replaces a store object.
- this_pc.py `no_push_taken`: drop the empty-reason refusal -> a run keeps its outputs here with no reason given.
- this_pc.py `push_stated`: drop the `unlink` -> status still says a run kept its outputs after a later one pushed.
- this_pc.py `disk`: `free < FREE_WARN_GB` -> `False` -> status says 76 GB free with no warning; or drop the MACHINE
  name filter -> postgres is listed as a SCORE container.
"""
import hashlib
import io
import os
import pathlib
import subprocess
import sys
import tarfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import this_pc  # noqa: E402


STAND_INS = {
    # this PC's card as nvidia-smi answers a memory query: MiB used, MiB of its 16 GB
    "nvidia-smi": "print('1834, 16376')",
    # a docker whose daemon is not up: the container is said not running (a test that asks more stands in `asked`)
    "docker": "import sys; sys.exit('Cannot connect to the Docker daemon')",
    # a key pair at -f's path, as ssh-keygen writes it (the real one exits 255 for a uid with no passwd entry)
    "ssh-keygen": ("import pathlib, sys; key = pathlib.Path(sys.argv[sys.argv.index('-f') + 1]); "
                   "key.write_text('stand-in private key\\n'); key.chmod(0o600); "
                   "key.with_name(key.name + '.pub').write_text('ssh-ed25519 AAAA score-this-pc\\n')"),
}


@pytest.fixture(autouse=True)
def tools_on_path(tmp_path, monkeypatch):
    """nvidia-smi, docker and ssh-keygen as stand-ins first on PATH, so the checks run the same on a box without the card or
    with a uid ssh-keygen refuses (the cluster gate's)."""
    stand_ins = tmp_path / "stand-in-bin"
    stand_ins.mkdir()
    for name, body in STAND_INS.items():
        (stand_ins / name).write_text(f"#!{sys.executable}\n{body}\n")
        (stand_ins / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{stand_ins}{os.pathsep}{os.environ['PATH']}")
    return stand_ins


def door(conductor, verb):
    """The door's command for `verb` against the folder `conductor`, as sshd would run it."""
    return ["env", f"SSH_ORIGINAL_COMMAND={verb}", f"PROPS_HOME={conductor}", "SCORE_DOOR_ENV=/nonexistent",
            sys.executable, str(HERE / "conductor" / "agent_door.py")]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)




STALE = {"rows": [{"id": "spaceship", "size": [13.688, 45.965, 4.0]}]}  # the spaceship's plan footprint, not prepare's
GO = "20261027T170000Z"

# a run's own arguments taken off the command line: (parser, arguments, what it gives, or the refusal it raises)
PARSED = [
    ("go_taken", ["world1"], (["world1"], None), None),
    ("no_push_taken", ["world1", "--no-push", "the conductor's disk is full", "--place", "hub"],
     (["world1", "--place", "hub"], "the conductor's disk is full"), None),
    ("no_push_taken", ["world1"], (["world1"], None), None),
    ("no_push_taken", ["world1", "--no-push"], None, "needs its reason"),
    ("no_push_taken", ["world1", "--no-push", " "], None, "needs its reason"),
    ("no_push_taken", ["world1", "--no-push", "--place"], None, "needs its reason"),
    ("restart_taken", ["world1", "--restart-reason", "why", "--jobs", "16"], (["world1", "--jobs", "16"], "why"), None),
    ("restart_taken", ["world1", "--restart-reason"], None, "needs its reason"),
]


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


def test_this_pc_pulls_what_a_run_reads_runs_free_and_pushes_without_replacing(tmp_path, monkeypatch):
    """One home on this PC against one conductor's home: pulled (never its keys, ledgers, registry or the hand-in
    written here, again only what changed, a cut blob made whole), prepared and pushed back by adding (a file a live
    run removed after the listing skipped, a take remade here replacing the conductor's with its old copy kept); runs
    here free only with the design brought up to date unless a run is live; then a live run in it paused, resumed as
    it ran, and stopped."""
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    (tmp_path / "env").mkdir()
    monkeypatch.setenv(this_pc.OWNERS_GO, "smuggled")  # a go in this shell, never one a run here carries
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    hand_in = home / "design/props/hangar.json"
    write(hand_in, this_pc.json.dumps(STALE))  # written here by an older prepare
    write(conductor / "design/props/hangar.json", "the conductor's, plan-footprint sizes")
    write(conductor / "design/surfaces/hangar.json", "the conductor's surface data")
    for name in ("store/objects/blobs/aa", "design/plans/hub.json", "work/pixal/take.glb", "cloud/google-cache/q.json",
                 "cache/library/swatch.png", "cloud/ssh_key", "cloud/self_delete_key.json", "cloud/ledger.jsonl",
                 "runs/active.json", "store/cache/checkouts/x", "frozen/copy/file", "dashboard/db.sqlite3",
                 "dashboard/films/locked/env1_demo.json", "dashboard/films/previews/env1_demo-takes/002.mp4"):
        write(conductor / name, name)
    write(conductor / "runs/active.json", "{}")  # the conductor's run registry: no run live, a replace may go

    # pull: what a run reads, never a key, ledger, registry or the conductor's hand-ins (they differ in mtime)
    assert this_pc.pull(home, door(conductor, "store-pull")) == (7, sum(
        len(name) for name in ("store/objects/blobs/aa", "design/plans/hub.json", "work/pixal/take.glb",
                               "cloud/google-cache/q.json", "cache/library/swatch.png",
                               "dashboard/films/locked/env1_demo.json",
                               "dashboard/films/previews/env1_demo-takes/002.mp4")))
    pulled = sorted(str(path.relative_to(home)) for path in home.rglob("*")
                    if path.is_file() and path.name != this_pc.BLOBS_CHECKED)
    assert pulled == ["cache/library/swatch.png", "cloud/google-cache/q.json",
                      "dashboard/films/locked/env1_demo.json", "dashboard/films/previews/env1_demo-takes/002.mp4",
                      "design/plans/hub.json", "design/props/hangar.json", "store/objects/blobs/aa",
                      "work/pixal/take.glb"]
    write(conductor / "design/plans/hub.json", "the hub, changed")
    (home / "store/objects/blobs/aa").chmod(0o444)  # a blob is read-only here, and its mtime differs there
    os.utime(conductor / "store/objects/blobs/aa", (1, 1))
    assert this_pc.pull(home, door(conductor, "store-pull")) == (1, len("the hub, changed"))
    sys.path.insert(0, str(HERE / "conductor"))
    import agent_door
    sent, _, kept = agent_door.store_pull(conductor, {"store/objects/blobs/aa": (0, 0)}, io.BytesIO())
    assert kept == 1 and sent == 8  # the store object the PC names goes by name, whatever its size and mtime
    # a listing linked to its blob there, already linked here: the stream's hard link is left as it is
    for side in (conductor, home):
        (side / "store/objects/records").mkdir(parents=True)
        os.link(side / "store/objects/blobs/aa", side / "store/objects/records/k.json")
    os.utime(conductor / "store/objects/blobs/aa", (2, 2))
    this_pc.pull(home, door(conductor, "store-pull"))
    assert (home / "store/objects/records/k.json").samefile(home / "store/objects/blobs/aa")
    # a work file held here as a link to a read-only blob, changed there: replaced, the blob untouched
    os.link(home / "store/objects/blobs/aa", home / "work/pixal/scene.json")
    write(conductor / "work/pixal/scene.json", "the scene, changed")
    this_pc.pull(home, door(conductor, "store-pull"))
    assert (home / "work/pixal/scene.json").read_text() == "the scene, changed"
    assert (home / "store/objects/blobs/aa").read_text() == "store/objects/blobs/aa"
    assert (home / "design/plans/hub.json").read_text() == "the hub, changed"
    # a blob named by its bytes: one held here cut short is not kept but pulled whole; one held whole is not sent again
    body = b"a blob's whole bytes" * 4096
    blob = f"store/objects/blobs/{hashlib.sha256(body).hexdigest()}"
    (conductor / blob).write_bytes(body)
    (home / blob).write_bytes(body[:65536])
    assert this_pc.pull(home, door(conductor, "store-pull")) == (1, len(body))
    assert (home / blob).read_bytes() == body
    assert this_pc.pull(home, door(conductor, "store-pull")) == (0, 0)
    # a pull killed midway through a blob: nothing under its name, and the next pull brings it whole
    (home / blob).unlink()
    stream = io.BytesIO()
    agent_door.store_pull(conductor, agent_door.held(agent_door.manifest(home, agent_door.PULLED)), stream)
    killed = tmp_path / "killed-stream"
    killed.write_bytes(stream.getvalue()[:-len(body) // 2 - 1024])
    with pytest.raises((tarfile.ReadError, SystemExit, EOFError)):
        this_pc.pull(home, [sys.executable, "-c", "import shutil, sys; sys.stdin.buffer.read(); "
                            f"shutil.copyfileobj(open({str(killed)!r}, 'rb'), sys.stdout.buffer); sys.exit(1)"])
    assert not (home / blob).exists()
    assert this_pc.pull(home, door(conductor, "store-pull")) == (1, len(body))
    assert (home / blob).read_bytes() == body
    assert hand_in.read_text() == this_pc.json.dumps(STALE)  # every pull left the hand-in written here
    assert not (home / "design/surfaces/hangar.json").exists()

    # prepared: its own key and the PC's environment linked
    this_pc.prepared(home)
    assert (home / "cloud/ssh_key.pub").exists() and (home / "env").is_symlink()

    # push: only what the conductor lacks, never its keys, a file a live run removed after the listing skipped
    write(conductor / "store/objects/records/hub/k1.json", "the conductor's record")
    write(home / "store/objects/records/hub/k1.json", "this PC's record")
    write(home / "store/objects/records/hub/k2.json", "made on this PC")
    write(home / "work/pixal/new.glb", "a take")
    write(home / "work/motion-scratch/layer/garage.usda", "scratch")
    listed = this_pc.walked

    def gone_after_listing(*arguments):
        found = list(listed(*arguments))
        (home / "work/motion-scratch/layer/garage.usda").unlink()
        return found
    with monkeypatch.context() as live_scratch:
        live_scratch.setattr(this_pc, "walked", gone_after_listing)
        pushed = this_pc.push(home, door(conductor, "store-push --missing"), door(conductor, "store-push"))
    assert pushed == (2, len("made on this PC") + len("a take"))
    assert (conductor / "store/objects/records/hub/k1.json").read_text() == "the conductor's record"
    assert (conductor / "store/objects/records/hub/k2.json").read_text() == "made on this PC"
    assert (conductor / "work/pixal/new.glb").read_text() == "a take"
    assert not (conductor / "work/motion-scratch").exists()
    assert not (conductor / "cloud/ssh_key.pub").exists()
    assert (conductor / "cloud/ssh_key").read_text() == "cloud/ssh_key"
    assert not list((conductor / "tmp/this-pc-push").iterdir())
    # a take remade here in place (same size, other bytes) replaces the conductor's, whose old copy is kept;
    # a store object is never replaced, a take already the same stays as it is
    write(conductor / "work/pixal/lamp.svviews/input.png", "old close-up")
    write(home / "work/pixal/lamp.svviews/input.png", "new close-up")
    write(conductor / "work/pixal/same.glb", "the same")
    write(home / "work/pixal/same.glb", "the same")
    replaced = this_pc.replace_changed(home, door(conductor, "store-push --differs"),
                                       door(conductor, "store-push --replace"))
    assert replaced == (1, len("new close-up"))
    assert (conductor / "work/pixal/lamp.svviews/input.png").read_text() == "new close-up"
    kept = list((conductor / "work/pixal/replaced").rglob("input.png"))
    assert len(kept) == 1 and kept[0].read_text() == "old close-up"
    assert (conductor / "store/objects/records/hub/k1.json").read_text() == "the conductor's record"
    refused = subprocess.run(door(conductor, "store-push --differs"), input="1\tx\tstore/objects/records/hub/k1.json\n",
                             capture_output=True, text=True)
    assert refused.returncode != 0 and "work/pixal/ only" in refused.stderr

    # a run's own arguments, and whether it pushes
    for parser, arguments, gives, refusal in PARSED:
        if refusal:
            with pytest.raises(SystemExit, match=refusal):
                getattr(this_pc, parser)(arguments)
        else:
            assert getattr(this_pc, parser)(arguments) == gives, (parser, arguments)
    assert this_pc.push_stated(home, "disk full", ["world1"]) == "no push: disk full"
    assert this_pc.unpushed(home).startswith("not pushed: disk full (world1, ")
    assert this_pc.push_stated(home, None, ["world1"]).startswith("push: ") and this_pc.unpushed(home) is None

    # runs here: a live run's design left as it is; else the plans keep, its plan row run waited out, then prepare,
    # free only from the run's code, before `score run` reads the rewritten hand-in; a failed step starts no run.
    # Prepare stands in (its rewrite of a hand-in is prepare's own test's): it writes the size it would write now.
    holding = [{"id": "live-run", "pid": 1}]  # a live run's entry, later the plan row run the keep starts, detached
    failing, events, started = set(), [], []

    def step(command, **given):
        module = command[2]
        events.append((module, given["cwd"], given["env"]["PROPS_HOME"], given["env"]["SCORE_FREE_ONLY"]))
        if module in failing:
            return subprocess.CompletedProcess(command, 1, "", "Traceback\nKeyError: 'hangar'\n")
        if module == "score.review.plans_pass":
            holding.append({"id": "plan-run", "pid": 1})
        if module == "score.stages.complete.prepare":
            assert not holding, "prepare ran while the plan row run held the store"
            write(hand_in, this_pc.json.dumps({"rows": [{"id": "spaceship", "size": [8.0, 24.0, 4.0]}]}))
        return subprocess.CompletedProcess(command, 0, f"{module} done\n", "")

    def waited(seconds):
        events.append(("waited", seconds))
        holding.clear()

    def launched(command, **given):
        started.append((command, given["env"], this_pc.json.loads(hand_in.read_text())["rows"][0]["size"]))
        return subprocess.CompletedProcess(command, 0)
    with monkeypatch.context() as here:
        here.setattr(this_pc, "asked", step)
        here.setattr(this_pc, "live_run", lambda found: holding[0] if holding else None)
        here.setattr(this_pc.time, "sleep", waited)
        here.setattr(this_pc.subprocess, "run", launched)
        assert this_pc.run(home, *this_pc.go_taken(["world1", "--go", GO, "--place", "hub"])) == 0
        assert not events and len(started) == 1
        command, environment, size = started[0]
        assert command[1:] == ["-m", "score", "run", "world1", "--place", "hub", "--free"] and size == [13.688, 45.965,
                                                                                                      4.0]
        assert {key: environment[key] for key in this_pc.ENVIRONMENT} == {
            "SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1"}
        assert environment["PROPS_HOME"] == str(home) and environment[this_pc.OWNERS_GO] == GO
        holding.clear()  # the live run ended
        assert this_pc.run(home, ["world1"]) == 0
        assert events == [("score.review.plans_pass", this_pc.REPO, str(home), "1"), ("waited", 5),
                          ("score.stages.complete.prepare", this_pc.REPO, str(home), "1")]
        command, environment, size = started[1]
        assert size == [8.0, 24.0, 4.0] and this_pc.OWNERS_GO not in environment
        failing.add("score.review.plans_pass")
        with pytest.raises(SystemExit, match="score.review.plans_pass failed .exit 1.: KeyError: 'hangar'"):
            this_pc.run(home, ["world1"])
        assert len(started) == 2  # no score run after a failed step
        # decide-yes and decide: the cockpit's command against this home's store, the owner his cockpit names
        here.delenv("SCORE_OWNER", raising=False)
        here.setattr(this_pc, "DASHBOARD_ENV", tmp_path / "dashboard.env")
        (tmp_path / "dashboard.env").write_text("SCORE_OWNER=joey\n")
        assert this_pc.deciding(home, "decide", [GO]) == 0
        command, environment, _ = started[2]
        assert command[1:] == ["-m", "score.dashboard", "decide", GO]
        assert environment["PROPS_HOME"] == str(home) and environment["SCORE_OWNER"] == "joey"
        assert this_pc.OWNERS_GO not in environment

    # a live run here: no second beside it; paused (recorded, its whole group stopped by one SIGTERM, every SCORE
    # container stopped only once none of it holds the card), resumed as it ran, and a draining one stopped by SIGKILL
    runs, calls = [], []
    names = "score-this-pc\npostgres\nscore-this-pc-segment\n"
    sizes = ("score-this-pc\t379GB (virtual 380GB)\npostgres\t1GB (virtual 2GB)\n"
             "score-this-pc-segment\t24GB (virtual 25GB)\n")

    def tool(command, **given):
        calls.append((command, given, any(this_pc.group_alive(process.pid) for process in runs)))
        if command[3:5] == ["worktree", "add"]:
            pathlib.Path(command[-2]).mkdir()
        out = (names if command[:3] == ["docker", "ps", "--format"] else sizes if command[:3] == ["docker", "ps", "-a"]
               else "detached: started pid=9 log=/home/logs/score-run.log\n" if "--detach" in command else "")
        return subprocess.CompletedProcess(command, 0, out, "")
    try:
        with monkeypatch.context() as card:
            card.setattr(this_pc, "asked", tool)
            card.setattr(this_pc.shutil, "disk_usage",
                         lambda path: this_pc.shutil._ntuple_diskusage(1007e9, 931e9, 76e9))
            process, entry = stand_in_run(home, tmp_path, SCORE_MIN_FREE_GB="8", SCORE_OWNERS_GO="go1",
                                          SCORE_CLOUD="local", SCORE_FROZEN="/frozen/copy",
                                          PROPS_HOME="/frozen/copy.home")
            runs.append(process)
            with pytest.raises(SystemExit, match="refused, run .* is live"):
                this_pc.resume(home)
            assert this_pc.start_refusal(home, "a fix").startswith(f"run {entry['id']} is live")
            assert this_pc.status_line(home).startswith(f"running {entry['id']}")
            line = this_pc.pause(home)
            assert process.wait(timeout=5) == 0 and not this_pc.group_alive(process.pid)
            stops = [(command, alive) for command, _, alive in calls if command[:2] == ["docker", "stop"]]
            assert stops == [(["docker", "stop", "score-this-pc", "score-this-pc-segment"], False)]
            record = this_pc.json.loads((home / this_pc.PAUSED).read_text())
            assert record["argv"] == entry["argv"] and record["commit"] == "a" * 40
            assert record["env"] == {"SCORE_MIN_FREE_GB": "8", "SCORE_OWNERS_GO": "go1", "SCORE_CLOUD": "local"}
            assert record["log"] == str(tmp_path / "run.log") and line.startswith(f"paused run {entry['id']}")
            status = this_pc.status_line(home)
            assert status.startswith(f"paused {entry['id']} since ") and "rows done 4, running 5, waiting 6" in status
            assert status.endswith("containers score-this-pc 379GB, score-this-pc-segment 24GB; "
                                   "disk 76 GB free WARNING: under 100 GB free")  # 2026-11-03's disk
            resuming = len(calls)
            assert this_pc.resume(home) == (f"resumed run world1 --jobs 8 --free at {'a' * 12}: "
                                            "detached: started pid=9 log=/home/logs/score-run.log")
            resumed = [(command, given) for command, given, _ in calls[resuming:] if command[0] != "nvidia-smi"]
            assert resumed[0][0] == ["docker", "start", "score-this-pc"]
            assert resumed[1][0][3:] == ["worktree", "add", "--detach", "--force", str(home / "resume-code"), "a" * 40]
            # the design brought up to date by the paused run's own code, in its home, before it starts again
            assert [(command[1:], given["cwd"], given["env"]["PROPS_HOME"]) for command, given in resumed[2:-1]] == [
                (["-m", module], home / "resume-code", str(home)) for module in this_pc.DESIGN_STEPS]
            command, given = resumed[-1]
            assert command[1:] == ["-m", "score", *entry["argv"], "--detach"] and given["cwd"] == home / "resume-code"
            assert {key: given["env"][key] for key in ("SCORE_MIN_FREE_GB", this_pc.OWNERS_GO, "SCORE_FREE_ONLY",
                                                       "PROPS_HOME")} == {
                "SCORE_MIN_FREE_GB": "8", this_pc.OWNERS_GO: "go1", "SCORE_FREE_ONLY": "1", "PROPS_HOME": str(home)}
            assert not (home / this_pc.PAUSED).exists()
            assert this_pc.status_line(home).startswith("neither running nor paused")
            # stop (#111): a run still draining after STOP_SECONDS has its whole group killed, never left beside
            # the next
            process, entry = stand_in_run(home, tmp_path)
            runs.append(process)
            card.setattr(this_pc, "STOP_SECONDS", 0.2)
            assert this_pc.stop(home) == f"stopped run {entry['id']} (pid {process.pid}) by SIGKILL after 0.2 s"
            assert process.wait(timeout=5) == -this_pc.signal.SIGKILL and not this_pc.group_alive(process.pid)
            assert this_pc.stop(home) == "stop: no run was live"
    finally:
        for process in runs:
            process.kill()
            process.wait()
    # a start within RESTART_HOURS of the last is refused without a reason (#112)
    started_at = this_pc.datetime.datetime(2026, 11, 11, 9, 0, tzinfo=this_pc.datetime.timezone.utc)
    write(home / "runs" / "20261111T090000-2.json", this_pc.json.dumps({"id": "2", "state": "ended", "pid": 1,
                                                                         "started": started_at.isoformat()}))
    soon, later = started_at + this_pc.datetime.timedelta(hours=1), started_at + this_pc.datetime.timedelta(hours=3)
    assert "--restart-reason" in this_pc.start_refusal(home, None, now=soon)
    assert this_pc.start_refusal(home, "the people chain is stopped", now=soon) is None
    assert this_pc.start_refusal(home, None, now=later) is None
