"""The conductor spends and moves only on the owner's word, boots the same every time, never reads an unknown as
idle, and moves its checkout only when nothing it would pull from under is working.

Free and offline: no scw call, no machine, no network. `up --dry` and `move` are recorded, never made; boot.sh runs
against a temp root with its commands shimmed; score-update against a local origin and a local cockpit; the agents'
door through agent_door.sh with a recorder in place of score. Every invariant has the break that turns it red, each
applied once and seen red:

Spending and moving are the owner's (machine.py, agent_door.sh, prepare.sh):
- An agent's process is refused `up` and `move` unless the owner's yes is open; `down` needs its confirmation.
  Break: `return None` at the top of `agent_refusal`. Break: `step_refusal` returns `(None, None)` for agents.
  Break: drop the `confirmed(...)` refusal in `down`.
- `up --dry` and `move` make no scw call; every call names its zone or region and every list or create the project;
  the conductor is never tagged `farm-factory-batch`; a secret value never shows.
  Break: drop `f"zone={ZONE}"` from the server create in `make_server`.
- prepare.sh's dry run makes nothing; a second run against an scw holding everything creates nothing.
  Break: `have_secret` in prepare.sh answers no -> secrets are created again.
- The agents' door refuses a shell, a paid run, the owner's commands and anything under the free-only latch, and runs
  the allowed ones marked as an agent's (`--free` added to a run; a benchmark only under its grant).
  Break: drop `--free` from the door's `run` rewrite in agent_door.py. Break: drop `env.pop("SCORE_BENCHMARK_GRANT")` in the
  door's `environment` -> a smuggled grant passes. Break: drop the latch refusal of a benchmark.
- The env file carries no secret. Break: let SCORE_SYNC_TOKEN through `env_text`.
- The move: this PC's store units off first (a failed disable is said), its home backed up before the conductor
  restores it, the sync installed after; the PC's home set aside and made read-only last, after the yes is marked.
  Break: `pc_units_off` ignores the systemctl return code. Break: chmod before `mark_done` in `retire_pc_home`.
- `status` reads the health record with the conductor's own key (the PC's key got HTTP 403, 2026-10-24).
  Break: `bucket_key` always {} -> the PC's own key is used.

Boot (cloud-init, boot.sh, units):
- The rendered cloud-init passes `cloud-init schema`; the agent's key is bound to the door with no pty or forwarding,
  the owner's is not; no slot is left unfilled; the first boot runs boot.sh through the unit, enabled only once the
  bus is up. Break: drop `no-pty` from `authorized_keys`.
- Every unit passes `systemd-analyze --user verify`; the sync pass runs the update first, on the system python.
- boot.sh runs against a temp root and again: the data volume formatted once, its mountpoint immutable before the
  mount, the units installed as rendered, the prop environment built only after the move; a download that misses its
  pin stops it, as does a missing system bus or any failing command (named by its line).
  Break: drop `chattr +i` before the mount in boot.sh. Break: skip the SHA-256 check in boot.sh's download.
- Wording checks guarding owner rules (they read text on purpose): no unit names a path of the owner's PC; boot.sh's
  gltfpack pin is the one tools/review/viewer/export.py runs. Break: change `GLTFPACK_PIN` in boot.sh.

The health record (health_push.py) errs on busy:
- It counts claims whose pid lives, parked machines, frozen copies a process works in (a waiting-for-size run's own
  copy left out), holds a live process keeps; an empty home is idle; a claims file that does not parse raises.
  Break: `return 0` on any error in `active_runs`. Break: drop `copy not in waiting` in `frozen_in_use`.
- secret_reader.sh finds the secrets project by name; secrets.sh writes the file-shaped secrets whole at 600 in a 700
  folder, an empty read never replaces a good one, an absent optional billing reader leaves a note, a failed read
  fails. Break: drop the empty check in secrets.sh.

The checkout moves (update.py):
- It follows the cockpit's pin, refuses a pin off main, follows origin/main forward only while the cockpit has none,
  and moves nothing when the pin cannot be read. Break: fall back to origin/main when the pin read fails.
- `.venv` (and after the move the prop environment) syncs only when uv.lock moved; a missing prop environment is built.
  Break: `lock_changed` always True.
- It waits while score starts from the checkout, while a run works in its frozen copy, while the checkout has changes;
  a sync pass holds back only a uv.lock move; two updates take turns on the checkout's lock.
  Break: `frozen_users` returns []. Break: drop the lock in `main`.
"""
import base64
import contextlib
import datetime
import fcntl
import http.server
import json
import os
import pathlib
import re
import shutil
import socket
import stat
import subprocess
import sys
import threading
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import health_push  # noqa: E402
import machine  # noqa: E402
import update  # noqa: E402
from score.store import AGENT_MARKERS  # noqa: E402

# A call that lists or creates may skip the project only when it acts inside a resource the project owns (a rule in
# its own group, a function in its own namespace) or is the global project lookup itself.
INSIDE_OWNED = ("instance security-group create-rule", "function function create", "function deploy",
                "account project list")


def executable(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def owner_keys(folder):
    """A throwaway key pair standing in for the owner's (dry runs never read the private half)."""
    private = pathlib.Path(folder) / "owner"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "owner", "-f", str(private)], check=True)
    return private


# ==== spending and moving are the owner's ===========================================================================

def test_an_agent_is_refused_up_and_move_without_the_owners_open_yes_and_down_without_confirmation(monkeypatch):
    for marker in AGENT_MARKERS:
        assert machine.agent_refusal({marker: "1"}), marker
    assert machine.agent_refusal({}) is None
    yes = {"id": "y-1", "answer": "yes", "question": "Switch the conductor on?"}
    marked = {AGENT_MARKERS[0]: "1"}
    refused, found = machine.step_refusal("up", marked, open_yes=lambda step: None)
    assert refused and found is None
    assert machine.step_refusal("up", marked, open_yes=lambda step: yes) == (None, yes)
    assert machine.step_refusal("move", {}, open_yes=lambda step: yes) == (None, None)  # the owner needs no yes
    (_, environment), _ = machine.move_steps("scw", yes)
    assert environment["SCORE_CONDUCTOR_YES"] == "y-1"  # the migrate steps check the same yes

    for marker in AGENT_MARKERS:
        monkeypatch.delenv(marker, raising=False)
    scw = machine.Scw(dry=True, say=lambda line: None)
    with pytest.raises(SystemExit, match="not confirmed"):
        machine.down(types.SimpleNamespace(with_data=False), scw, say=lambda line: None, answer=lambda question: "no")
    assert scw.calls == []


def test_up_dry_names_project_and_zone_on_every_call_and_makes_none(tmp_path, monkeypatch):
    printed = []
    private = owner_keys(tmp_path)
    options = types.SimpleNamespace(owner_key=str(private), agent_key=f"{private}.pub",
                                    env_file=str(tmp_path / "none.env"))
    scw = machine.Scw(dry=True, say=printed.append)
    real_run = subprocess.run

    def no_scw(arguments, *args, **kwargs):
        assert arguments[0] != "scw", f"a dry run called scw: {arguments}"
        return real_run(arguments, *args, **kwargs)
    monkeypatch.setattr(machine.subprocess, "run", no_scw)
    machine.up(options, scw, printed.append)
    calls = scw.calls
    assert calls and all(f"scw {call}" in printed for call in calls)
    for call in calls:
        assert "farm-factory-batch" not in call, call  # the runner's leftover sweeps delete by that tag
        if not call.startswith("account project list"):
            assert any(f" {key}=" in f" {call}" for key in ("zone", "region")), f"no zone or region: {call}"
        if (" list " in f" {call} " or " create " in f" {call} ") and not call.startswith(INSIDE_OWNED):
            assert "project-id=" in call, f"no project: {call}"
    server = next(call for call in calls if call.startswith("instance server create"))
    assert "project-id=<id of project score-conductor>" in server and "tags.0=score-conductor" in server
    assert any("inbound-default-policy=drop" in call for call in calls)  # only ssh comes in
    assert all("<secret>" in call for call in calls if ".value=" in call)

    user_data = machine.Scw(dry=True, say=lambda line: None)
    machine.set_user_data(types.SimpleNamespace(owner_key=str(private), agent_key=None), user_data,
                          say=lambda line: None)
    assert any(call.startswith("instance user-data set ") and f"zone={machine.ZONE}" in call
               for call in user_data.calls)
    assert not any(" create " in f" {call} " or " delete " in f" {call} " for call in user_data.calls)


PREPARE_SECRETS = ("score-conductor-key", "score-conductor-size-key", "score-conductor-size-token",
                   "score-backup-restic-password", "score-cockpit-sync-token", "score-lib-deploy-key")
# An scw that holds everything prepare.sh makes: every list answers the one item asked for, a secret with a version.
HOLDING_SCW = """#!/bin/sh
echo "$*" >> "{log}"
name=$(for argument in "$@"; do case "$argument" in name=*|policy-name=*) echo "${{argument#*=}}";; esac; done)
case "$1 $2" in
  "config get") echo org-1 ;;
  "account project"|"iam application"|"iam policy") echo "[{{\\"name\\": \\"$name\\", \\"id\\": \\"id-$name\\"}}]" ;;
  "secret secret") echo "[{{\\"name\\": \\"$name\\", \\"id\\": \\"s-$name\\", \\"version_count\\": 1}}]" ;;
esac
"""


def prepare(folder, *arguments, scw_text=None):
    """prepare.sh run with an scw shim (logging every call to folder/scw.log) and an owner's yes in the folder's
    store (an agent's process needs one); the finished process."""
    folder = pathlib.Path(folder)
    machine.conductor_yes.record("yes", "Switch the conductor on?", machine.Store.in_folder(folder / "store"))
    env = {**os.environ, "SCORE_CONDUCTOR_YES_HOME": str(folder), "SCORE_GH": "/bin/false",
           "SCORE_PC_SECRET_READER": "/bin/false"}
    if scw_text:
        env["SCORE_SCW"] = str(executable(folder / "scw", scw_text.format(log=folder / "scw.log")))
    return subprocess.run(["bash", str(HERE / "prepare.sh"), *arguments], env=env, capture_output=True, text=True,
                          timeout=60)


def test_prepare_dry_makes_nothing_and_a_second_run_creates_nothing(tmp_path):
    dry = tmp_path / "dry"
    dry.mkdir()
    done = prepare(dry, "--dry")
    assert done.returncode == 0, done.stderr
    assert not (dry / "scw.log").exists()
    for secret in PREPARE_SECRETS:
        assert f"scw secret secret create name={secret} " in done.stderr, secret
    # the conductor's key lives in its own project, which no key but the owner's may read
    assert "name=score-conductor-key project-id=<new>" in done.stderr
    assert "data=@<a file in /dev/shm>" in done.stderr and "<value>" not in done.stderr  # values only through a file

    again = tmp_path / "again"
    again.mkdir()
    done = prepare(again, scw_text=HOLDING_SCW)
    assert done.returncode == 0, done.stderr
    calls = (again / "scw.log").read_text().splitlines()
    assert calls and not [call for call in calls if " create" in call], calls


# The agents' door, end to end through agent_door.sh: a copy of the door in a fake checkout whose interpreter runs
# the door itself and records whatever the door hands on, instead of running score.
RECORDER = """#!/bin/sh
if [ "$1" = "-I" ]; then exec "{python}" "$@"; fi
printf '%s\\n' "$@" > "$DOOR_RECORD/argv"
env > "$DOOR_RECORD/env"
"""


@pytest.fixture
def door(tmp_path):
    """through(asked, env file text) -> (exit code, stderr, recorded argv or None, recorded environment)."""
    checkout = tmp_path / "checkout"
    (checkout / "tools" / "cloud" / "conductor").mkdir(parents=True)
    shutil.copy(HERE / "agent_door.py", checkout / "tools" / "cloud" / "conductor" / "agent_door.py")
    (checkout / "score").symlink_to(REPO / "score")
    executable(checkout / ".venv" / "bin" / "python", RECORDER.format(python=sys.executable))

    def through(asked, env_file_text=""):
        record = tmp_path / "record"
        shutil.rmtree(record, ignore_errors=True)
        record.mkdir()
        env_file = tmp_path / "dashboard.env"
        env_file.write_text(env_file_text)
        env = {name: value for name, value in os.environ.items() if name not in AGENT_MARKERS}
        env.update({"SCORE_DOOR_REPO": str(checkout), "SCORE_DOOR_ENV": str(env_file), "DOOR_RECORD": str(record),
                    "SSH_ORIGINAL_COMMAND": asked, "SCORE_BENCHMARK_GRANT": "smuggled"})
        done = subprocess.run(["sh", str(HERE / "agent_door.sh")], env=env, capture_output=True, text=True,
                              timeout=60)
        argv = (record / "argv").read_text().splitlines() if (record / "argv").exists() else None
        recorded = dict(line.split("=", 1) for line in (record / "env").read_text().splitlines() if "=" in line) \
            if (record / "env").exists() else {}
        return done.returncode, done.stderr, argv, recorded
    return through


def test_the_door_refuses_a_shell_a_paid_run_the_owners_commands_and_anything_under_the_latch(door):
    for asked in ("", "bash", "sh -c id", "bash -i", "status; bash", "python -m score.review accept x",
                  "spend --google-month 12", "spend --read-back", "run world1", "resume",
                  "benchmark world1 --detach", "benchmark 'g 1' world1 --detach", "scw instance server list",
                  "cat /home/score/.config/scw/config.yaml", "health --write", "gaps", "gaps a b",
                  "gaps ../x", "gaps 'closeup@hub;id'", "predicted x", "buy", "buy a b", "buy 'y 1'",
                  "buy-yes 30 33 'yes'"):
        code, why, argv, _ = door(asked)
        assert code == 126 and argv is None and "refused" in why, (asked, code, why)
    for asked in ("benchmark g1 world1 --detach", "buy 20261025T1700000000"):
        code, why, argv, _ = door(asked, "SCORE_FREE_ONLY=1\n")
        assert code == 126 and argv is None and "latch" in why, asked


def test_the_door_runs_the_allowed_commands_marked_as_an_agents(door):
    code, why, argv, env = door("run world1 --place hangar --detach")
    assert code == 0, why
    assert argv == ["-m", "score", "run", "world1", "--place", "hangar", "--detach", "--free"]
    assert env["SCORE_FREE_ONLY"] == "1" and "SCORE_BENCHMARK_GRANT" not in env  # a smuggled grant is dropped
    assert all(env.get(marker) == "1" for marker in AGENT_MARKERS)
    code, why, argv, env = door("status world1 $(id)")
    assert code == 0 and argv == ["-m", "score", "status", "world1", "$(id)"], (why, argv)  # never a shell
    code, why, argv, env = door("benchmark g-1 world1 --stage x --detach")
    assert code == 0 and argv == ["-m", "score", "run", "world1", "--stage", "x", "--detach"], (why, argv)
    assert env["SCORE_BENCHMARK_GRANT"] == "g-1" and "SCORE_FREE_ONLY" not in env
    assert all(env.get(marker) == "1" for marker in AGENT_MARKERS)
    code, why, argv, env = door("benchmark 20261026T074845.442617+0000 world1 --detach")
    assert code == 0 and env["SCORE_BENCHMARK_GRANT"] == "20261026T074845.442617+0000", why
    code, why, argv, _ = door("grant-benchmark 12 'yes, go' 'may I spend EUR 12 on x?'")
    assert code == 0 and argv[0] == "-c" and argv[2:] == ["12", "yes, go", "may I spend EUR 12 on x?"], argv
    code, why, argv, env = door("buy-yes 33 30 'Yes, buy it' 'Buy at high EUR 30, stop EUR 33?'")
    assert code == 0 and argv == ["-m", "score.dashboard", "buy-yes", "33", "30", "Yes, buy it",
                                  "Buy at high EUR 30, stop EUR 33?"], (why, argv)
    assert env["SCORE_FREE_ONLY"] == "1"  # recording a yes spends nothing
    code, why, argv, env = door("buy 20261025T170000Z")
    assert code == 0 and argv == ["-m", "score.dashboard", "buy", "20261025T170000Z"], (why, argv)
    assert "SCORE_FREE_ONLY" not in env and all(env.get(marker) == "1" for marker in AGENT_MARKERS)
    code, why, argv, _ = door("resume --dry")
    assert code == 0 and argv == ["-m", "score", "resume", "--dry"]
    code, why, argv, _ = door("logs --lines 5")
    assert code == 0 and argv == ["-m", "score.conductor", "logs", "--lines", "5"], (why, argv)
    code, why, argv, _ = door("gaps closeup@hub")
    assert code == 0 and argv[0] == "-c" and argv[2:] == ["closeup@hub"], (why, argv)
    code, why, argv, env = door("stop-batch 'the run holds 13 idle machines'")
    assert code == 0 and argv[0] == "-c" and argv[2:] == ["the run holds 13 idle machines"], (why, argv)
    assert all(env.get(marker) == "1" for marker in AGENT_MARKERS)


def test_the_doors_gaps_and_predicted_print_what_the_store_holds(tmp_path, monkeypatch, capsys):
    """2026-10-26: galley's jars and oven were "Pixal3D made no model" and only batch.log said why."""
    from unittest import mock
    import score.store
    from agent_door import GAPS_CODE, PREDICTED_CODE
    files = {"batch-gaps.json": json.dumps({"gaps": [
        {"name": "jars: Pixal3D made no model", "check": "takes", "faults": ["jars: no galley_jars.glb"]}]}),
        "batch.log": "[cloud] renting 2 cards\n[cloud] gaps (ran once or never sent, no model; a new batch and a "
                     "new ask to try again): galley_jars: out of memory\n", "takes.json": "{}"}

    class Kept:
        """The stored output of one node, its files by name (score.store.Store's reading half)."""
        objects = mock.Mock(read_bytes=lambda key: files[key.removeprefix("blobs/")].encode())

        def accepted(self, node):
            return "out1" if node == "pixal@galley" else None

        def listing(self, output):
            return {name: name for name in files}

        def read_file(self, output, name):
            return json.loads(files[name])
    monkeypatch.setattr(score.store.Store, "default", Kept)
    monkeypatch.setattr(sys, "argv", ["-c", "pixal@galley"])
    exec(GAPS_CODE, {})
    lines = capsys.readouterr().out.splitlines()
    assert "1 batch gaps" in lines[0] and lines[1].startswith("jars: Pixal3D made no model | takes |"), lines
    assert lines[2:] == ["batch.log: [cloud] gaps (ran once or never sent, no model; a new batch and a new ask to try "
                         "again): galley_jars: out of memory"], lines

    record = tmp_path / "work" / "checks" / "prepare" / "remake.json"
    record.parent.mkdir(parents=True)
    take = {"place": "street", "rows": ["street_lamp"], "route": "model", "size": [0.3, 0.3, 6], "inputs": [],
            "status": "bought", "prediction": {"outcome": "predicted gap", "mode": "close-up: every rod failed"}}
    record.write_text(json.dumps({"takes": [
        take, {**take, "rows": ["bench"], "prediction": {"outcome": "pass", "mode": None}},
        {**take, "rows": ["sign"], "status": "input gap", "inputs": ["no box or size"],
         "prediction": {"outcome": "pass", "mode": None}}]}))
    done = subprocess.run([sys.executable, "-c", PREDICTED_CODE], cwd=REPO, capture_output=True, text=True,
                          env={**os.environ, "PROPS_HOME": str(tmp_path)}, timeout=60)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert "3 takes, 2 predicted gap" in lines[0] and len(lines) == 3, lines  # the passing bench is left out
    assert lines[1] == "street | street_lamp | model | [0.3, 0.3, 6] | predicted gap | close-up: every rod failed"
    assert lines[2].endswith("| input gap | no box or size"), lines


def test_the_env_file_carries_no_secret(tmp_path):
    owner_env = tmp_path / "dashboard.env"
    owner_env.write_text("SCORE_OWNER=owner\nSCORE_SYNC_URL=https://cockpit.example\nSCORE_SYNC_TOKEN=secret\n"
                         "SCORE_SECRET_READER=/home/someone/.local/bin/reader\n")
    text = machine.env_text(owner_env)
    values = dict(line.split("=", 1) for line in text.splitlines())
    assert "SCORE_SYNC_TOKEN" not in values and "secret" not in text.replace("secret-reader", "")
    assert values["SCORE_SECRET_READER"] == "/usr/local/bin/score-secret-reader"  # the conductor's, not the PC's
    assert values["SCORE_OWNER"] == "owner"


def test_the_move_switches_this_pc_off_and_backs_it_up_before_the_conductor_restores_it():
    printed = []
    scw = machine.Scw(dry=True, say=printed.append)
    machine.move(types.SimpleNamespace(owner_key="~/.ssh/id_ed25519"), scw, printed.append)
    (local, environment), remote = machine.move_steps("/home/someone/.local/bin/scw")
    assert local[-3:] == ["score.store.backup", "migrate", "--from-pc"]
    # the PC reads the backup's password where the conductor does: the conductor's reader, its secrets project
    assert environment["SCORE_SECRET_READER"] == str(machine.HERE / "secret_reader.sh")
    assert environment["SCORE_SECRETS_PROJECT"] == machine.SECRETS_PROJECT_NAME
    assert remote.index("--onto-conductor") < remote.index("boot.sh env") < remote.index("install-sync")
    assert "--no-pull" in remote
    disable = printed.index(next(line for line in printed if "disable --now" in line))
    assert disable < printed.index(next(line for line in printed if "--from-pc" in line))
    assert all(call.startswith(("account project list", "instance server list")) for call in scw.calls), scw.calls

    calls = []

    def systemctl(*args):
        calls.append(args)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    assert machine.pc_units_off(present=["score-sync.timer", "score-listen.service"], systemctl=systemctl) == [
        "score-sync.timer", "score-listen.service"]
    assert calls == [("disable", "--now", "score-sync.timer", "score-listen.service")]
    assert machine.pc_units_off(present=[], systemctl=systemctl) == [] and len(calls) == 1
    with pytest.raises(SystemExit, match="Access denied"):
        machine.pc_units_off(present=["score-resume.service"], systemctl=lambda *args: types.SimpleNamespace(
            returncode=1, stdout="", stderr="Access denied"))


def test_the_move_sets_the_pcs_home_aside_read_only_last(tmp_path, monkeypatch):
    home = tmp_path / "props"
    (home / "store").mkdir(parents=True)
    final = tmp_path / "props.pc-final"
    monkeypatch.setattr(machine, "PROPS_HOME", home)
    monkeypatch.setattr(machine, "PC_FINAL_HOME", final)
    ran = []
    monkeypatch.setattr(machine.conductor_yes, "mark_done", lambda yes, step, store=None: ran.append(
        ("marked", step, store.objects.root)))
    machine.retire_pc_home({"id": "y-1"}, "scw", run=lambda command, **kwargs: ran.append(
        (command, kwargs.get("env", {}))) or types.SimpleNamespace(returncode=0))
    assert final.is_dir() and home.is_dir() and not any(home.iterdir())
    assert ran[0][0][-1] == "--pc-test-home" and ran[0][1]["SCORE_CONDUCTOR_YES_HOME"] == str(final)
    assert ran[1][1]["UV_PROJECT_ENVIRONMENT"] == str(home / "env")
    assert ("marked", "move", final / "store" / "objects") in ran
    assert ran[-1][0] == ["chmod", "-R", "a-w", str(final)]  # read-only last, after the yes is marked


def test_status_reads_the_health_record_with_the_conductors_own_key(monkeypatch):
    """The PC's own key belongs to another project, so the bucket refuses it (HTTP 403, 2026-10-24)."""
    monkeypatch.setattr(machine, "stored_key", lambda scw: {"access_key": "SCWCON", "secret_key": "s-con"})
    read = []
    record = machine.health_record(types.SimpleNamespace(dry=False),
                                   read=lambda *args: read.append(args) or b'{"active_runs": 0}')
    assert record == {"active_runs": 0} and read[0][-2:] == ("SCWCON", "s-con")

    printed = []
    monkeypatch.undo()  # the real stored_key: it asks score-conductor's own project for the key, by name
    machine.stored_key(machine.Scw(dry=True, say=printed.append))
    assert any("name=score-conductor-key 'project-id=<id of project score-conductor>'" in line for line in printed)


# ==== boot ==========================================================================================================

def heredoc(text, end):
    """The lines of the bootcmd heredoc ending at `end`, indentation removed."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.endswith(f"<< '{end}'"))
    stop = next(index for index in range(start + 1, len(lines)) if lines[index].strip() == end)
    return [line[4:] for line in lines[start + 1:stop]]


def test_cloud_init_passes_its_schema_binds_the_agents_key_to_the_door_and_boots_through_the_unit(tmp_path):
    assert machine.check_cloud_init() is None
    text = machine.render_cloud_init("ssh-ed25519 AAAA owner", "ssh-ed25519 BBBB agent", "vol-1")
    door_line = next(line for line in text.splitlines() if "BBBB" in line)
    for option in ('command=\\"/usr/local/bin/score-agent-door\\"', "no-pty", "no-port-forwarding",
                   "no-agent-forwarding"):
        assert option in door_line, (option, door_line)
    assert "command=" not in next(line for line in text.splitlines() if "AAAA" in line)
    assert "scsi-0SCW_sbs_volume-vol-1" in text
    assert re.search(r"@[A-Z_]+@", text) is None, "a slot left unfilled"

    assert "runcmd:" not in text  # the first boot runs boot.sh through the unit, as every later boot does
    unit = heredoc(text, "UNIT")
    move, system, user = [line for line in unit if line.startswith("ExecStart=")]
    assert "checkout -q --detach origin/main" in move and "boot.sh system" in system
    assert "runuser -u score --" in user and "boot.sh user" in user
    bootcmd = text[text.index("bootcmd:"):]
    # bootcmd has no bus: it only writes files; the per-boot script (cloud-init's final stage) enables and starts
    assert not any(line.strip().startswith(("systemctl", "loginctl")) for line in bootcmd.split("<< 'SCRIPT'")[0]
                   .splitlines())
    script = heredoc(text, "SCRIPT")
    assert script.index("systemctl daemon-reload") < script.index("systemctl enable -q score-boot.service")
    copy = tmp_path / "score-boot.service"
    copy.write_text("\n".join(unit) + "\n")
    done = subprocess.run(["systemd-analyze", "verify", str(copy)], capture_output=True, text=True)
    assert "score-boot.service" not in done.stderr, done.stderr


def test_every_unit_passes_systemd_verify_and_the_sync_pass_updates_first(tmp_path):
    assert machine.check_units(machine.fake_home(tmp_path / "units")) is None
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")  # the sync's modules read them
    django.setup()
    from score.dashboard.sync import timer
    home = machine.fake_home(tmp_path / "sync")
    repo, env = home / "projects" / "score", home / "dashboard.env"
    env.write_text("SCORE_SYNC_URL=https://cockpit.test\n")
    copies = []
    for name in ("score-sync.service", "score-sync.timer"):
        copy = tmp_path / name
        copy.write_text(timer.unit_text(name, repo, env, timer.SECRET, pull=False))
        copies.append(str(copy))
    service = pathlib.Path(copies[0]).read_text()
    done = subprocess.run(["systemd-analyze", "--user", "verify", *copies], capture_output=True, text=True)
    assert done.returncode == 0 and not (done.stderr + done.stdout).strip(), done.stderr + done.stdout
    assert f"\nExecStartPre=/usr/bin/python3 -I {repo}/tools/cloud/conductor/update.py --repo {repo}\n" in service


def test_wording_no_unit_names_the_pcs_paths_and_boot_seeds_the_viewers_gltfpack_pin():
    """Wording checks guarding owner rules: the conductor's units run on the conductor alone, and the web copies run
    the gltfpack the boot put in the npm cache (two pins that must agree)."""
    for unit in machine.unit_files():
        text = unit.read_text()
        assert "/home/dupe" not in text and "wsl" not in text.lower(), unit.name
    pin = re.search(r'^GLTFPACK = "(gltfpack@[0-9.]+)"', (REPO / "tools/review/viewer/export.py").read_text(), re.M)
    assert f'GLTFPACK_PIN="{pin.group(1)}"' in (HERE / "boot.sh").read_text().splitlines()


# boot.sh against a temp root. Every command it runs that touches the machine is a shim writing its words to LOG.
SHIM = """#!/bin/sh
echo "$(basename "$0") $*" >> "$SHIM_LOG"
case "$(basename "$0")" in
  blkid)
    if [ "$1" = "-p" ]; then [ -f "$SHIM_STATE/formatted" ] && exit 0; exit 2; fi
    echo 1111-uuid ;;
  mkfs.ext4) touch "$SHIM_STATE/formatted" ;;
  mountpoint) exit 1 ;;
  id) echo 1100 ;;
  runuser)
    while [ "$1" != "--" ]; do shift; done
    shift
    exec "$@" ;;
  curl)
    while [ "$1" != "-o" ]; do shift; done
    echo "not the pinned file" > "$2" ;;
  npx)
    case "$*" in *"--offline -y gltfpack@"*) echo "gltfpack 0.22"; exit 1 ;; esac ;;
esac
exit 0
"""
SHIMMED = ("apt-get", "id", "useradd", "loginctl", "blkid", "mkfs.ext4", "mountpoint", "mount", "chown", "systemctl",
           "runuser", "git", "curl", "chattr", "npx", "npm")


def boot_root(folder, installed=True):
    """A temp root for boot.sh: shims on PATH, the pinned tools already there when `installed`, user score's home
    with a checkout whose tools are this repository's, and his credential."""
    root = pathlib.Path(folder) / "root"
    shims = pathlib.Path(folder) / "shims"
    for name in SHIMMED:
        executable(shims / name, SHIM)
    (root / "etc").mkdir(parents=True)
    (pathlib.Path(folder) / "state").mkdir()
    if installed:
        bin_folder = root / "usr" / "local" / "bin"
        executable(bin_folder / "restic", "#!/bin/sh\necho 'restic 0.19.1 compiled with go'\n")
        executable(bin_folder / "uv", "#!/bin/sh\n[ \"$1\" = --version ] && echo 'uv 0.12.23' && exit 0\n"
                                      "echo \"uv $*\" >> \"$SHIM_LOG\"\n")
        executable(bin_folder / "scw", "#!/bin/sh\necho 'Version          2.65.1'\n")
        executable(bin_folder / "node", "#!/bin/sh\necho v24.21.0\n")
        (root / "opt" / "google-cloud-sdk").mkdir(parents=True)
        (root / "opt" / "google-cloud-sdk" / "VERSION").write_text("588.0.0")
    home = root / "home" / "score"
    checkout = home / "projects" / "score"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "tools").symlink_to(REPO / "tools")
    (home / ".config" / "scw").mkdir(parents=True)
    (home / ".config" / "scw" / "config.yaml").write_text("access_key: test\n")
    (home / "projects" / "score_lib" / ".git").mkdir(parents=True)
    bus = root / "run" / "dbus" / "system_bus_socket"
    bus.parent.mkdir(parents=True)
    with socket.socket(socket.AF_UNIX) as listening:
        listening.bind(str(bus))
    return root, shims


def run_boot(folder, root, shims, parts=("system", "user")):
    """Run boot.sh's parts in order as score-boot.service does; (the last part's process, every shimmed call)."""
    env = {**os.environ, "PATH": f"{shims}:{os.environ['PATH']}", "SHIM_LOG": str(pathlib.Path(folder) / "log"),
           "SHIM_STATE": str(pathlib.Path(folder) / "state"), "SCORE_BOOT_ROOT": str(root),
           "SCORE_DATA_DEVICE": "/dev/disk/by-id/scsi-0SCW_sbs_volume-test"}
    for part in parts:
        part_env = env if part == "system" else {**env, "HOME": str(root / "home" / "score"),
                                                 "XDG_RUNTIME_DIR": "/run/user/1100"}
        done = subprocess.run(["bash", str(HERE / "boot.sh"), part], env=part_env, capture_output=True, text=True,
                              timeout=60)
        if done.returncode != 0:
            break
    log = pathlib.Path(env["SHIM_LOG"])
    return done, log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def short_path():
    """A temp folder with a short path: the system bus socket's path must fit AF_UNIX's 108 bytes."""
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        yield pathlib.Path(folder)


def test_boot_runs_against_a_temp_root_and_again_the_same(short_path):
    tmp_path = short_path
    root, shims = boot_root(tmp_path)
    done, calls = run_boot(tmp_path, root, shims)
    assert done.returncode == 0, done.stderr + done.stdout
    assert "mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test" in calls
    assert not any(call.startswith("curl") for call in calls), "a pinned tool already there was downloaded again"
    assert "UUID=1111-uuid /home/score/.farm-factory-props ext4" in (root / "etc" / "fstab").read_text()
    mountpoint = root / "home" / "score" / ".farm-factory-props"
    assert calls.index(f"chattr +i {mountpoint}") < calls.index(f"mount {mountpoint}"), \
        "the bare mountpoint is not made immutable before the data volume is mounted on it"
    for name in ("score-secret-reader", "score-agent-door"):
        assert os.access(root / "usr" / "local" / "bin" / name, os.X_OK), name
    sshd = (root / "etc" / "ssh" / "sshd_config.d" / "50-score-conductor.conf").read_text()
    assert "PasswordAuthentication no" in sshd and "PermitRootLogin no" in sshd
    assert not any("--no-dev" in call for call in calls), "the prop environment was built before the move"
    units = root / "home" / "score" / ".config" / "systemd" / "user"
    for unit in machine.unit_files():
        installed = (units / unit.name).read_text()
        assert installed == machine.rendered_unit(unit), unit.name
        assert not any(slot in installed for slot in machine.UNIT_SLOTS), unit.name
    # resume and health write into the home, so on the conductor they wait for the move's machine.json
    waits = "ConditionPathExists=%h/.farm-factory-props/machine.json"
    assert waits in (units / "score-resume.service.d" / "conductor.conf").read_text().splitlines()
    assert waits in (units / "score-health.service").read_text().splitlines()
    assert "npm cache add gltfpack@0.22.0" in calls  # score_lib's web copies run gltfpack offline from the cache
    assert "apt-get remove -y -q nodejs" in calls  # Ubuntu's old node is never found before the pinned one

    # after the move (machine.json), every boot syncs the prop environment the rows' PROPS_PYTHON runs in
    (mountpoint / "machine.json").write_text("{}")
    again, calls_again = run_boot(tmp_path, root, shims)
    assert again.returncode == 0, again.stderr
    assert f"uv sync -q --frozen --no-dev --project {root}/home/score/projects/score" in calls_again
    assert calls_again.count("mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test") == 1
    assert (root / "etc" / "fstab").read_text().count("UUID=1111-uuid") == 1


def test_boot_stops_on_a_missed_pin_a_missing_bus_or_any_failing_command(short_path):
    tmp_path = short_path
    unpinned = tmp_path / "unpinned"
    root, shims = boot_root(unpinned, installed=False)
    done, calls = run_boot(unpinned, root, shims)
    assert done.returncode != 0 and "does not match its pinned SHA-256" in done.stderr
    assert not (root / "usr" / "local" / "bin" / "restic").exists()
    assert not any(call.startswith("runuser") for call in calls)

    busless = tmp_path / "busless"
    root, shims = boot_root(busless)
    (root / "run" / "dbus" / "system_bus_socket").unlink()
    done, calls = run_boot(busless, root, shims, parts=("system",))
    assert done.returncode != 0 and "no system bus" in done.stderr and calls == []

    failing = tmp_path / "failing"
    root, shims = boot_root(failing)
    executable(shims / "chattr", "#!/bin/sh\nexit 3\n")
    done, calls = run_boot(failing, root, shims, parts=("system",))
    assert done.returncode != 0
    assert re.search(r"boot: stopped at boot.sh line \d+, exit 3: chattr", done.stderr), done.stderr
    assert not any(call.startswith("mount ") for call in calls)


# ==== the health record errs on busy ================================================================================

@pytest.fixture
def no_metadata(monkeypatch):
    """No network: the instance's metadata service is off Scaleway here."""
    monkeypatch.setattr(health_push, "commercial_type", lambda: None)


def test_the_health_record_counts_live_claims_parked_frozen_in_use_and_holds(tmp_path, monkeypatch, no_metadata):
    home = tmp_path
    (home / "runs").mkdir()
    dead = subprocess.Popen(["true"])
    dead.wait()
    (home / "runs" / "active.json").write_text(json.dumps({str(os.getpid()): {}, str(dead.pid): {}}))
    (home / "cloud" / "parked").mkdir(parents=True)
    (home / "cloud" / "parked" / "machine-1.json").write_text("{}")
    for copy in ("run-a", "run-waiting", "run-left-behind"):
        (home / "frozen" / copy).mkdir(parents=True)
    (home / "runs" / "waiting.json").write_text(json.dumps({"state": "waiting-for-size",
                                                             "worktree": str(home / "frozen" / "run-waiting")}))
    (home / "conductor" / "holds").mkdir(parents=True)
    (home / "conductor" / "holds" / "sync-pass-1.lock").write_text("")  # its holder gone
    (home / "conductor" / "health.json").write_text(json.dumps({"disk": 12}))
    monkeypatch.setenv("SCORE_HEALTH_FILE", str(home / "conductor" / "health.json"))
    working = [subprocess.Popen(["sleep", "30"], cwd=home / "frozen" / copy) for copy in ("run-a", "run-waiting")]
    try:
        with (home / "conductor" / "holds" / "film-preview-2.lock").open("a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)  # flock is per open file: the record's own open is refused like another's
            record = health_push.record(home, datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc))
    finally:
        for process in working:
            process.kill()
            process.wait()
    # run-a has a process in it; the waiting run's copy waits for the grow itself; the left-behind one is idle
    assert (record["active_runs"], record["parked"], record["frozen"], record["working"]) == (1, 1, 1, 1)
    assert record["health"] == {"disk": 12} and record["written_at"].startswith("2026-10-22T00:00:00")
    assert health_push.working(home) == 0  # the hold released


def test_an_empty_home_is_idle_and_an_unreadable_claims_file_is_never_idle(tmp_path, no_metadata):
    now = datetime.datetime.now(datetime.timezone.utc)
    record = health_push.record(tmp_path, now)
    assert (record["active_runs"], record["parked"], record["frozen"], record["working"], record["health"]) == (
        0, 0, 0, 0, None)
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "active.json").write_text('{"123": ')
    with pytest.raises(ValueError):
        health_push.record(tmp_path, now)


SCW_SHIM = """#!/bin/sh
echo "$*" >> "{log}"
case "$1 $2" in
  "account project")
    echo '[{{"name": "other", "id": "p-0"}}, {{"name": "secrets-here", "id": "p-1"}}]' ;;
  "secret version")
    echo '{{"data": "{data}"}}' ;;
  "secret secret")
    echo '[{{"name": "gemini-api-key", "id": "s-1"}}]' ;;
esac
"""
# A secret reader printing each secret's name as its value, past the optional flag.
READER_SHIM = "#!/bin/sh\n[ \"$1\" = --if-present ] && shift\nprintf 'value of %s' \"$1\"\n"


def test_the_secret_reader_finds_the_secrets_project_by_name(tmp_path):
    log = tmp_path / "scw.log"
    scw = executable(tmp_path / "scw", SCW_SHIM.format(log=log, data=base64.b64encode(b"the value").decode()))
    env = {**os.environ, "SCORE_SCW": str(scw), "SCORE_SECRETS_PROJECT": "secrets-here",
           "SCORE_READER_PYTHON": sys.executable}

    def read(*arguments):
        return subprocess.run(["sh", str(HERE / "secret_reader.sh"), *arguments], env=env, capture_output=True,
                              text=True, timeout=30)
    done = read("gemini-api-key")
    assert done.returncode == 0 and done.stdout == "the value", done.stderr
    assert "project-id=p-1" in log.read_text().splitlines()[1]  # p-1 is secrets-here's id, p-0 another project's
    absent = read("--if-present", "google-billing-reader")
    assert absent.returncode == 0 and absent.stdout == "", absent.stderr
    assert read("--if-present", "gemini-api-key").stdout == "the value"
    env["SCORE_SECRETS_PROJECT"] = "missing"
    refused = read("x")
    assert refused.returncode != 0 and "found 0" in refused.stderr


def test_secrets_go_whole_and_private_to_the_runtime_folder_and_an_empty_read_replaces_nothing(tmp_path):
    runtime = tmp_path / "run"
    runtime.mkdir()
    gcloud = executable(tmp_path / "gcloud", f"#!/bin/sh\necho \"$CLOUDSDK_CONFIG $*\" > {tmp_path}/gcloud.log\n")
    env = {**os.environ, "XDG_RUNTIME_DIR": str(runtime), "SCORE_GCLOUD": str(gcloud),
           "SCORE_SECRET_READER": str(executable(tmp_path / "reader", READER_SHIM))}

    def secrets():
        return subprocess.run(["sh", str(HERE / "secrets.sh")], env=env, capture_output=True, text=True, timeout=30)
    done = secrets()
    assert done.returncode == 0, done.stderr
    folder = runtime / "score"
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    key = folder / "score-lib-deploy-key"
    assert key.read_text() == "value of score-lib-deploy-key\n" and stat.S_IMODE(key.stat().st_mode) == 0o600
    assert (folder / "google-billing-reader.json").read_text() == "value of google-billing-reader\n"
    assert sorted(path.name for path in folder.iterdir()) == ["google-billing-reader.json", "score-lib-deploy-key"]
    assert (tmp_path / "gcloud.log").read_text().startswith(f"{folder}/gcloud auth activate-service-account")

    env["SCORE_SECRET_READER"] = str(executable(tmp_path / "empty", "#!/bin/sh\n"))
    refused = secrets()
    assert refused.returncode != 0 and "empty" in refused.stderr
    assert key.read_text() == "value of score-lib-deploy-key\n", "an empty read replaced a good key"

    shutil.rmtree(folder)
    env.update(SCORE_GCLOUD="/bin/false", SCORE_SECRET_READER=str(executable(
        tmp_path / "absent", "#!/bin/sh\n[ \"$1\" = --if-present ] && exit 0\nprintf 'value of %s' \"$1\"\n")))
    done = secrets()
    assert done.returncode == 0 and "skipped" in done.stdout, done.stderr
    assert sorted(path.name for path in folder.iterdir()) == ["google-billing-reader.note", "score-lib-deploy-key"]
    env["SCORE_SECRET_READER"] = str(executable(
        tmp_path / "failing", "#!/bin/sh\n[ \"$1\" = --if-present ] && exit 1\nprintf 'value of %s' \"$1\"\n"))
    refused = secrets()
    assert refused.returncode != 0 and "reading google-billing-reader failed" in refused.stderr


# ==== the checkout moves only when safe =============================================================================

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.org", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
TOKEN = "t" * 40


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def commit(repo, name, text):
    (pathlib.Path(repo) / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@contextlib.contextmanager
def cockpit(answer):
    """A local cockpit, its base URL: /api/sync/pin with the token answers `answer` (a dict), anything else the
    hosting proxy's own /healthz body or 401, as the proxy and the token check do."""
    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            signed_in = self.headers.get("Authorization") == f"Bearer {TOKEN}"
            if self.path == "/healthz":
                body, status = json.dumps({"ok": True}).encode(), 200
            elif self.path == "/api/sync/pin" and signed_in:
                body, status = json.dumps(answer).encode(), 200
            else:
                body, status = b'{"detail": "a sync needs the sync token"}', 401
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Health)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


@pytest.fixture
def world(tmp_path):
    """An origin with three commits on main (uv.lock, a.txt, uv.lock), a checkout detached at the first, a uv shim
    logging its calls, an empty proc folder and a home beside them; `move(url)` runs update.update on it."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    commits = [commit(origin, "uv.lock", "one"), commit(origin, "a.txt", "two"), commit(origin, "uv.lock", "three")]
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True, env={**os.environ, **GIT_ENV})
    git(checkout, "checkout", "-q", "--detach", commits[0])
    log = tmp_path / "uv.log"
    uv = executable(tmp_path / "uv", f"#!/bin/sh\necho \"${{UV_PROJECT_ENVIRONMENT:-}} $*\" >> {log}\n")
    proc = tmp_path / "proc"
    proc.mkdir()
    home = tmp_path / "home"

    def move(url, token=TOKEN):
        return update.update(checkout, url, uv=str(uv), proc=proc, token=lambda: token, home=home)

    def at():
        return git(checkout, "rev-parse", "HEAD")

    def process(pid, cmdline, cwd):
        entry = proc / str(pid)
        entry.mkdir(exist_ok=True)
        (entry / "cmdline").write_bytes(cmdline)
        if (entry / "cwd").is_symlink():
            (entry / "cwd").unlink()
        (entry / "cwd").symlink_to(cwd)
    return types.SimpleNamespace(origin=origin, checkout=checkout, commits=commits, log=log, proc=proc, home=home,
                                 move=move, at=at, process=process, folder=tmp_path)


def test_the_checkout_follows_the_pin_and_syncs_only_when_the_lock_moved(world):
    with cockpit({"ok": True, "commit": world.commits[1]}) as url:
        line = world.move(url)
    assert world.at() == world.commits[1] and not world.log.exists(), line  # a.txt only: no sync
    noted = json.loads((world.home / "conductor" / "pin.json").read_text())
    assert noted["pin"] == world.commits[1] and noted["at"]  # the Machine card's pin
    with cockpit({"ok": True, "commit": world.commits[2]}) as url:
        line = world.move(url)
    assert world.at() == world.commits[2] and ".venv synced" in line
    assert world.log.read_text().split() == ["sync", "-q", "--frozen", "--group", "dashboard"]


def test_after_the_move_a_lock_move_or_a_missing_prop_environment_syncs_it(world):
    world.home.mkdir()
    with cockpit({"ok": True, "commit": world.commits[0]}) as url:
        assert "prop environment" not in world.move(url)  # before the move: the home stays empty
        (world.home / "machine.json").write_text("{}")
        line = world.move(url)  # the prop environment is left out of every backup: built at the next update
        assert line.startswith("update: at ") and "the prop environment synced" in line, line
        (world.home / "env" / "bin").mkdir(parents=True)
        (world.home / "env" / "bin" / "python").write_text("")
        assert "prop environment" not in world.move(url)
    assert len(world.log.read_text().splitlines()) == 1
    with cockpit({"ok": True, "commit": world.commits[2]}) as url:
        assert "the prop environment synced" in world.move(url)
    assert world.log.read_text().splitlines()[-1].split() == [
        str(world.home / "env"), "sync", "-q", "--frozen", "--no-dev", "--project", str(world.checkout)]


def test_a_pin_off_main_is_refused_none_follows_main_forward_and_an_unread_pin_moves_nothing(world):
    git(world.origin, "checkout", "-q", "-b", "side")
    side = commit(world.origin, "b.txt", "off main")
    git(world.checkout, "fetch", "-q", "origin", "side")
    with cockpit({"ok": True, "commit": side}) as url:
        assert "refused" in world.move(url) and world.at() == world.commits[0]
    with cockpit({"commit": world.commits[1]}) as url:  # a wrong token: the proxy's 401
        line = world.move(url, token="wrong")
    assert line.startswith("update: not now, the cockpit's pin could not be read") and "401" in line
    assert world.at() == world.commits[0]
    with cockpit({"ok": True, "mode": "hosted"}) as url:
        line = world.move(url)
    assert world.at() == world.commits[2] and "origin/main" in line


def test_a_move_waits_while_a_run_works_in_its_frozen_copy_or_score_starts_from_the_checkout(world):
    copy = world.home / "frozen" / "abc123"
    copy.mkdir(parents=True)
    world.process(5151, b"/x/.venv/bin/python\0-m\0score\0run\0world1\0", copy)
    with cockpit({"commit": world.commits[2]}) as url:
        line = world.move(url)
    assert "not now" in line and "pid 5151: /x/.venv/bin/python -m score run world1" in line
    assert world.at() == world.commits[0] and not world.log.exists()
    with cockpit({"commit": world.commits[1]}) as url:
        assert "5151" in world.move(url) and world.at() == world.commits[0]  # a.txt only: still held
    world.process(5151, b"/x/.venv/bin/python\0-m\0score\0run\0world1\0", world.folder)  # the run ended
    world.process(4242, b"/x/.venv/bin/python\0-m\0score\0run\0world1\0", world.checkout)
    line = world.move(None)
    assert "not now" in line and "4242" in line and world.at() == world.commits[0]
    world.process(4242, b"/x/.venv/bin/python\0-m\0score\0run\0world1\0", world.folder)
    with cockpit({"commit": world.commits[2]}) as url:
        assert ".venv synced" in world.move(url) and world.at() == world.commits[2]


def test_a_sync_pass_holds_back_only_a_lock_move(world):
    """A pass outlasts the 5-minute timer and the next starts right after it (2026-10-25: the checkout sat on an old
    commit all morning)."""
    world.process(6161, b"/x/.venv/bin/python\0-m\0score.dashboard\0sync\0", world.checkout)
    with cockpit({"commit": world.commits[1]}) as url:
        assert "->" in world.move(url) and world.at() == world.commits[1]
    with cockpit({"commit": world.commits[2]}) as url:
        line = world.move(url)
    assert "not now" in line and "6161" in line and world.at() == world.commits[1]


def test_a_checkout_with_changes_waits_and_two_updates_take_turns(world, monkeypatch):
    (world.checkout / "uv.lock").write_text("edited")
    assert "tracked changes" in world.move(None) and world.at() == world.commits[0]
    git(world.checkout, "checkout", "-q", "--", "uv.lock")
    called = []
    monkeypatch.setattr(update, "update", lambda repo, url: called.append(repo) or "update: at test")
    with open(world.checkout / ".git" / "score-update.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        second = threading.Thread(target=update.main, args=(["--repo", str(world.checkout)],))
        second.start()
        second.join(0.5)
        assert second.is_alive() and not called
    second.join(5)
    assert called == [world.checkout.resolve()]
