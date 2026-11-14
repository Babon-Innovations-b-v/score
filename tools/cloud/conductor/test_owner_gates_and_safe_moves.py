"""The conductor spends and moves only on the owner's word, boots the same every time, never reads an unknown as
idle, and moves its checkout only when nothing it would pull from under is working.

Free and offline: no scw call, no machine, no network. `up --dry` and `move` are recorded, never made; boot.sh runs
against a temp root with its commands shimmed; score-update against a local origin and a local cockpit; the agents'
door through agent_door.sh with a recorder in place of score. Every invariant has the break that turns it red, each
applied once and seen red:

Spending and moving are the owner's (machine.py, agent_door.sh, prepare.sh):
- An agent's process is refused `up` and `move` unless the owner's yes is open; `down` needs its confirmation.
  Break: `return None` at the top of `agent_refusal`. Break: `step_refusal` returns `(None, None)` for agents.
  Break: drop the `confirmed(...)` refusal in `down`. Break: in agent_door.buy_started, `subprocess.Popen(...)` ->
  `subprocess.run(...)` (the door's buy holds the ssh for the Buy's whole pricing, 2026-11-04).
- `up --dry` and `move` make no scw call; every call names its zone or region and every list or create the project;
  the conductor is never tagged `farm-factory-batch`; a secret value never shows.
  Break: drop `f"zone={ZONE}"` from the server create in `make_server`.
- prepare.sh's dry run makes nothing; a second run against an scw holding everything creates nothing.
  Break: `secret_state` in prepare.sh answers nothing -> secrets are created again.
- The agents' door refuses a shell, a paid run, the owner's commands and anything under the free-only latch, and runs
  the allowed ones marked as an agent's (`--free` added to a run; a benchmark only under its grant).
  Break: drop `--free` from the door's `run` rewrite in agent_door.py.
  Break: drop `env.pop("SCORE_BENCHMARK_GRANT")` in the door's `environment` -> a smuggled grant passes.
  Break: drop the latch refusal of a benchmark.
  Break: in agent_door.move_out, drop `if stopped.returncode != 0:` -> the VM's home backed up while its units run.
  Break: `return None` at the top of `move_out_refusal` -> a live run cut by the move.
- The owner's decisions in chat go through the door as decide-yes and decide <yes id> alone, and a run's go only
  as `--go <id>` (owner, 2026-10-27). Break: drop `env.pop("SCORE_OWNERS_GO")` in `environment` -> a smuggled go
  passes. Break: drop the `GRANT_ID.match` refusal of `decide` -> `decide 'y 1'` runs.
- The door's job-log reads a cloud job's log under a frozen home's work/cloud only, its tail capped, and nothing a
  link or `..` leads out of it (2026-10-27: surfaces-bake@campgrounds' failed jobs, their logs out of reach).
  Break: in `job_log`, `and any(found.is_relative_to(folder) for folder in allowed)` -> `` (a link out of it read).
- The door's run-log and fault read the newest launch's own run log and a node's fault report of its home only, and
  no node name or link leads out of the faults folder (2026-10-27: motion@airlock's fault report out of reach).
  Break: in `read_inside`, `and any(found.is_relative_to(folder) for folder in allowed)` -> `` (a link out read).
- The door's store-push only adds regular files under store/objects and work: a file already there is kept, and an
  absolute path, `..`, another folder, a link member or a link out of those folders is refused (2026-10-27: this PC's
  run pushes back through the door).
  Break: in `store_push`, `os.replace(part, target)` for `os.link(part, target)` -> the conductor's record replaced.
  Break: in `push_target`, drop the `target.parent.resolve()` check -> a write through a link leaves work/.
  Break: in `store_push`, drop the `not member.isfile()` refusal -> a link member is accepted.
  Break: in `store_push`, `sorted(parts, key=...)` -> `parts` (a record lands before its listing and blob), or land
  each member as it is read (a stream cut short leaves the record without its output; 2026-10-31).
  Break: in `store_missing` or `store_push`, drop `evicted_here` -> a blob the conductor evicted into the store bucket
  is listed missing and landed again (#74: the PC sends evicted blobs back).
  Break: in `fault`, drop the `NODE.match` refusal -> `../../logs/x` is read.
- The door's other reads (READ_ROWS over door_world): the newest warm pool log, each running run's nodes (a resumed
  run's in its frozen home, a count as the drive's gauge writes it), a resumed run's log followed, every owner outbox,
  a run's stacks only from a process that catches SIGUSR1 (2026-11-05 to 11-08).
  Break: in `pool_log`, take `found[:1]`. Break: in `running`, drop the frozen homes' glob, or the count case.
  Break: in `followed`, return `log` at once. Break: in `outbox`, drop the frozen homes' glob.
  Break: in `stack`, drop the `catches` refusal. Break: in tools/cloud/batch.py stop_on_signals, drop `stacks_on_ask()`.
- The door's gaps prints a node's batch gaps and the batch.log lines saying why; its predicted prints the prepared
  batch's takes that may not stand (2026-10-26). Break: drop `'gaps ('` from GAPS_CODE's words.
- A Buy's options and its start (BUY_OPTION_ROWS, BUY_ROWS): --place and --leave-place reach its command, a stage
  with an underscore is left out by name, --max-machines and --take-cheap pass, --cluster only once cluster-check
  passes (the tenant module's status part of it, the tmpfs settings SCORE_K8S_* only), its run then carrying
  SCORE_CLOUD=k8s and the kinds.
  Break: in `buy_started`, drop the `--place` part of `asked`. Break: drop "--leave-place", "--max-machines" or
  "--take-cheap" from BUY_OPTIONS. Break: STAGE_LIST's `[a-z0-9_-]` -> `[a-z0-9-]`. Break: in `buy_started`, drop
  `cluster_check(os.environ)`, or `env={**os.environ, **extra}`. Break: in `tenant_status`, drop the
  `done.returncode != 0` refusal. Break: in `cluster_values`, drop the `name.startswith("SCORE_K8S_")` filter.
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
- Every unit passes `systemd-analyze --user verify` in the home the boot made, the sync's units as rendered for its
  checkout too; the sync pass runs the update first, on the system python.
- boot.sh runs against a temp root and again: the data volume formatted once, its mountpoint immutable before the
  mount, the units installed as rendered, the prop environment and the sync's units (install-sync --no-pull, after
  score-update) only after the move; a download that misses its
  pin stops it, as does a missing system bus or any failing command (named by its line).
  Break: drop `chattr +i` before the mount in boot.sh. Break: skip the SHA-256 check in boot.sh's download.
  Break: drop `sync_units "$repo"` from boot.sh's user part. Break: drop `resize2fs "$device"` from boot.sh's
  mount_data (a volume grown by `machine.py grow-data` never gets its room).
- No installed unit names a path of the owner's PC; the boot seeds the npm cache with the gltfpack pin
  tools/review/viewer/export.py runs. Break: change `GLTFPACK_PIN` in boot.sh.

The health record (health_push.py) errs on busy:
- Over the data volume the boot mounted: fresh, it is idle; then it counts claims whose pid lives, parked machines,
  frozen copies a process works in (a waiting-for-size run's own copy left out), holds a live process keeps; a claims
  file that does not parse raises.
  Break: `return 0` on any error in `active_runs`. Break: drop `copy not in waiting` in `frozen_in_use`.
- secret_reader.sh, as the boot installed it, finds the secrets project by name; secrets.sh, run as the boot's
  score-secrets.service and reading through it, writes the file-shaped secrets whole at 600 in a 700 folder (the
  door's cluster settings read there SCORE_K8S_* only; the door service opens with the token the same vault holds), an empty read never replaces a good one, an absent optional billing reader
  leaves a note, a failed read fails. Break: drop the empty check in secrets.sh. Break: `asker_reader` hands back
  the box's own SCORE_SECRET_READER.
- Claude Code's login (claude_login.py, from secrets.sh): with no claude-code-oauth-token, no `claude` on the PATH, so
  the adapter's NotHere fires; with the pinned CLI the boot found and the secret, `claude` reaches it with the login in
  CLAUDE_CODE_OAUTH_TOKEN and no API key, the login in no file and no log line; a `claude` not ours is never removed;
  boot.sh does not reinstall a CLI at its pin. Break: in `environment`, drop `TOKEN_ENV: value`. Break: in `link`,
  `and token() is not None` -> `` (the link stays without the secret, NotHere never fires).

The checkout moves (update.py):
- It follows the cockpit's pin, refuses a pin off main, follows origin/main forward only while the cockpit has none,
  and moves nothing when the pin cannot be read. Break: fall back to origin/main when the pin read fails.
- `.venv` (and after the move the prop environment) syncs only when uv.lock moved; a missing prop environment is built.
  Break: `lock_changed` always True.
- It waits while score starts from the checkout, while a run works in its frozen copy, while the checkout has changes;
  a sync pass holds back only a uv.lock move, and the line (noted for the health record) names a sync unit with no
  update before its pass; two updates take turns on the checkout's lock. A run that buys and runs nothing (its
  registry entry, fresh: running 0, buys 0) holds back only a uv.lock move (2026-11-02: a plan row run waiting ten
  hours for memory held the conductor off its pin). Break: `idle_copies` drops the `running` test -> a working run is
  passed by. Break: drop the `if runs and lock_changed` refusal -> .venv is synced under an idle run.
- A move that changes units/ installs them (`boot.sh units`), so a new unit is live without a boot; the pinned Claude
  Code is installed by a move when it is not there; a release's commit noted by the door's release-pin is followed
  while the cockpit still pins the commit it replaced.
  Break: `frozen_users` returns []. Break: drop the lock in `main`. Break: `pass_updates_first` always True.
  Break: `units_installed` returns "". Break: `claude_installed` returns "". Break: `released_over` returns the pin
  first. Break: agent_door.release_pinned drops its `run(...)` of update.py.
  (These cases are rows of CASES, each break seen red: the pin read -> unread-pin-moves-nothing; `lock_changed` ->
  a-pin-reached-moves-and-syncs-nothing; `idle_copies` -> running-run-holds-any-move; the idle-run refusal ->
  idle-run-holds-a-lock-move; `frozen_users` -> frozen-run-holds-any-move; `pass_updates_first` ->
  sync-pass-holds-a-lock-move, and returning False -> sync-pass-of-a-unit-updating-first, whose unit is the one
  rendered for the boot's checkout; `released_over` and release_pinned -> release-followed-before-the-host-builds;
  `units_installed` -> units-changed-installed; `claude_installed` -> claude-code-pinned-installed.)
- score_lib's checkout beside it gets the machine's committer when git knows no user.email there, even when nothing
  moves, and an identity it has stays (2026-10-28: every library commit on the conductor failed for want of one).
  Break: in `library_identified`, `.returncode == 0` -> `.returncode == 1` (no identity given; one there overwritten).
- The pod's door service (door_service.py, #76 step 4) answers with the ssh door's own refusals and allowed commands
  and runs nothing without its token. Break: in door_service.Handler.do_POST drop the `compare_digest` refusal.
"""
import concurrent.futures
import contextlib
import datetime
import fcntl
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import types
import urllib.error

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import door_service  # noqa: E402
import health_push  # noqa: E402
import machine  # noqa: E402
import update  # noqa: E402
from score.store import AGENT_MARKERS  # noqa: E402

# A call that lists or creates may skip the project only when it acts inside a resource the project owns (a rule in
# its own group, a function in its own namespace) or is the global project lookup itself.
INSIDE_OWNED = ("instance security-group create-rule", "function function create", "function deploy",
                "account project list")


# A test server's shutdown waits out one poll of its serve loop (0.5 s by default): every cockpit and door service a
# test opens and closes paid it.
POLL = 0.01


def executable(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def soon(check, seconds=10):
    """True once check() holds, asked every 20 ms for at most `seconds` (a detached process's words in its log)."""
    deadline = time.monotonic() + seconds
    while not check():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.02)
    return True


def owner_keys(folder, name):
    """A throwaway key pair standing in for the owner's or the agents' (dry runs never read the private half)."""
    private = pathlib.Path(folder) / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(private)], check=True)
    return private


# ==== spending and moving are the owner's ===========================================================================

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


# prepare.sh: (row, its arguments, the scw it runs against or None, whether it calls scw, words its stderr says,
# words it never says). The dry run makes nothing; a second run against an scw holding everything creates nothing; the
# conductor's key lives in its own project, which no key but the owner's may read; values go only through a file.
PREPARE_ROWS = [
    ("dry", ("--dry",), None, False, (*(f"scw secret secret create name={secret} " for secret in PREPARE_SECRETS),
                                      "name=score-conductor-key project-id=<new>", "data=@<a file in /dev/shm>"),
     ("<value>",)),
    ("again", (), HOLDING_SCW, True, (), ("<value>",)),
]


# The agents' door, end to end through agent_door.sh: a copy of the door in a fake checkout whose interpreter runs
# the door itself and records whatever the door hands on, instead of running score.
RECORDER = """#!/bin/sh
if [ "$1" = "-I" ]; then exec "{python}" "$@"; fi
printf '%s\\n' "$@" > "$DOOR_RECORD/argv"
env > "$DOOR_RECORD/env"
"""


@pytest.fixture
def door(tmp_path):
    """through(asked, env file text) -> (exit code, stderr, recorded argv or None, recorded environment);
    through.many(asks, env file text) -> the same for each ask, the asks run side by side (each its own record)."""
    checkout = tmp_path / "checkout"
    (checkout / "tools" / "cloud" / "conductor").mkdir(parents=True)
    shutil.copy(HERE / "agent_door.py", checkout / "tools" / "cloud" / "conductor" / "agent_door.py")
    (checkout / "score").symlink_to(REPO / "score")
    executable(checkout / ".venv" / "bin" / "python", RECORDER.format(python=sys.executable))

    def environment(asked, env_file_text, record):
        record.mkdir()
        env_file = record.parent / f"{record.name}.env"
        env_file.write_text(env_file_text)
        env = {name: value for name, value in os.environ.items() if name not in AGENT_MARKERS}
        env.update({"SCORE_DOOR_REPO": str(checkout), "SCORE_DOOR_ENV": str(env_file), "DOOR_RECORD": str(record),
                    "SSH_ORIGINAL_COMMAND": asked, "SCORE_BENCHMARK_GRANT": "smuggled",
                    "SCORE_OWNERS_GO": "smuggled"})
        return env

    def recorded(record):
        argv = (record / "argv").read_text().splitlines() if (record / "argv").exists() else None
        found = dict(line.split("=", 1) for line in (record / "env").read_text().splitlines() if "=" in line) \
            if (record / "env").exists() else {}
        return argv, found

    def fresh_record():
        return pathlib.Path(tempfile.mkdtemp(prefix="record-", dir=tmp_path)) / "record"

    def through(asked, env_file_text=""):
        record = fresh_record()
        done = subprocess.run(["sh", str(HERE / "agent_door.sh")], env=environment(asked, env_file_text, record),
                              capture_output=True, text=True, timeout=60)
        return (done.returncode, done.stderr, *recorded(record))

    def many(asks, env_file_text=""):
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            return list(pool.map(lambda asked: through(asked, env_file_text), asks))

    def through_service(asked, token, opened=None):
        """The same door through door_service.py (the pod's, #76 step 4), opened by `opened` (default `token`): one
        request with `token`."""
        record = fresh_record()
        server = door_service.serve(opened or token, 0, environment=environment(asked, "", record))
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL}, daemon=True).start()
        try:
            code, _, err = door_service.send(f"http://127.0.0.1:{server.server_address[1]}/", token, asked)
        finally:
            server.shutdown()
            server.server_close()
        return (code, err.decode(), *recorded(record))
    through.many = many
    through.service = through_service
    return through


# The agents' door, one table: every ask, the env file it runs under, and what the door does with it. `REFUSED` and
# `LATCHED`: exit 126, nothing handed on, the reason named; `FAILS`: any nonzero exit; otherwise the argv handed on
# (ANY: any word there; DOOR_PY: the door's own agent_door.py; `prefix`: the argv starts so) and the environment it
# carries (None: the name is absent; AGENT: every agent marker set to 1).
REFUSED, LATCHED, FAILS, ANY, DOOR_PY, AGENT = "refused", "latch", "fails", object(), object(), object()
FREE = {"SCORE_FREE_ONLY": "1"}
LATCH_ENV = "SCORE_FREE_ONLY=1\n"
GO = "20261027T170000123456Z"


def allowed(argv, prefix=False, **env):
    return {"argv": argv, "prefix": prefix, "env": env}


REFUSED_ASKS = (
    "", "bash", "sh -c id", "bash -i", "status; bash", "python -m score.review accept x", "spend --google-month 12",
    "spend --read-back", "run world1", "resume", "benchmark world1 --detach", "benchmark 'g 1' world1 --detach",
    "scw instance server list", "cat /home/score/.config/scw/config.yaml", "health --write", "gaps", "gaps a b",
    "gaps ../x", "gaps 'closeup@hub;id'", "predicted x", "buy", "buy a b", "buy 'y 1'", "buy a --phase",
    "buy a --phase 'x y'", "buy a --stage models", "buy a --phase models x", "buy a --leave-out",
    "buy a --phase models --phase surfaces", "buy a --leave-out 'sim body'", "buy-yes 30 33 'yes'",
    "buy-yes 33 30 'yes' 'q?'", "buy-yes --stop 33 30 'yes' 'q?'", "buy-yes --no-film 33 30 'yes' 'q?'",
    "batch-money --film", "batch-money --no-film x", "batch-money 1", "disk /", "clean-frozen --all",
    "clean-cache --making-only", "relink-pixal x", "offload-pixal x", "sweep --force", "store-gc --all",
    "store-gc --dry x", "store-evict --all", "score-lib", "score-lib push", "score-lib pull --force", "job-log",
    "job-log a b", "job-log x.home/work/cloud/../../../store/k", "run-log 5", "run-log --lines", "run-log --lines x",
    "run-log --lines 0", "fault", "fault a b", "fault ../store/k", "fault 'motion@airlock/../../x'",
    "store-pull cloud", "store-push --delete", "store-push --missing x", "preflight", "preflight --phase props",
    "lock-phase world1", "lock-phase --place a models", "lock-phase world1 models --stage pixal",
    "lock-phase world1 models --place", "lock-phase world1 models --place '../x'", "cluster-check x", "move-out",
    "move-out a b", "move-out ' '",
    # the owner's decisions in chat: decide by a yes id alone, decide-yes in its shape, a run's go by its id
    "decide", "decide a b", "decide 'y 1'", "decide-yes accept x 'yes'", "decide-yes --output h a x y",
    "run world1 --detach --go", "run world1 --detach --go 'g 1'")
DOOR_ROWS = [
    *((asked, "", REFUSED) for asked in REFUSED_ASKS),
    # under the free-only latch nothing that may spend runs
    *((asked, LATCH_ENV, LATCHED) for asked in (
        "benchmark g1 world1 --detach", "buy 20261025T1700000000", "buy 20261025T1700000000 --phase models",
        "buy 20261025T1700000000 --phase models,surfaces --leave-out sim-body,body-peel")),
    # a run is marked free and an agent's; a smuggled grant and a smuggled go are dropped
    ("run world1 --place hangar --detach", "", allowed(
        ["-m", "score", "run", "world1", "--place", "hangar", "--detach", "--free"], SCORE_FREE_ONLY="1",
        SCORE_BENCHMARK_GRANT=None, SCORE_OWNERS_GO=None, agent=AGENT)),
    ("run world1 --detach", "", allowed(["-m", "score", "run", "world1", "--detach", "--free"], SCORE_OWNERS_GO=None)),
    (f"run world1 --go {GO} --detach", "", allowed(
        ["-m", "score", "run", "world1", "--detach", "--free"], SCORE_OWNERS_GO=GO, SCORE_FREE_ONLY="1")),
    ("status world1 $(id)", "", allowed(["-m", "score", "status", "world1", "$(id)"])),  # never a shell
    # a benchmark only under its grant, and never free-only
    ("benchmark g-1 world1 --stage x --detach", "", allowed(
        ["-m", "score", "run", "world1", "--stage", "x", "--detach"], SCORE_BENCHMARK_GRANT="g-1",
        SCORE_FREE_ONLY=None, agent=AGENT)),
    ("benchmark 20261026T074845.442617+0000 world1 --detach", "", allowed(
        ["-m", "score", "run", "world1", "--detach"], prefix=True,
        SCORE_BENCHMARK_GRANT="20261026T074845.442617+0000")),
    ("grant-benchmark 12 'yes, go' 'may I spend EUR 12 on x?'", "", allowed(
        ["-c", ANY, "12", "yes, go", "may I spend EUR 12 on x?"])),
    # recording a yes spends nothing; the Buy itself is not free-only
    ("buy-yes --batch-total 333 30 'Yes, buy it' 'Batch 1 total EUR 333?'", "", allowed(
        ["-m", "score.dashboard", "buy-yes", "--batch-total", "333", "30", "Yes, buy it", "Batch 1 total EUR 333?"],
        **FREE)),
    ("buy-yes --no-film --batch-total 380 343 'Yes' 'Batch 1 total EUR 380, no film?'", "", allowed(
        ["-m", "score.dashboard", "buy-yes", "--no-film", "--batch-total"], prefix=True)),
    ("batch-money", "", allowed(["-m", "score.dashboard", "batch-money"], **FREE)),
    ("batch-money --no-film", "", allowed(["-m", "score.dashboard", "batch-money", "--no-film"])),
    ("buy 20261025T170000Z", "", allowed([ANY, "--buy", "20261025T170000Z"], SCORE_FREE_ONLY=None, agent=AGENT)),
    ("buy-log", "", allowed([ANY, "--buy-log"])),
    ("resume --dry", "", allowed(["-m", "score", "resume", "--dry"])),
    # 2026-11-06: a phase checked free before it is queued; its places locked as they pass
    # Break: in agent_door, drop the `lock-phase` verb
    ("preflight world1 --phase props", "", allowed(["-m", "score", "preflight", "world1", "--phase", "props"], **FREE)),
    ("lock-phase world1 surfaces --place hub --place lab", "", allowed(
        ["-m", "score", "lock-phase", "world1", "surfaces", "--place", "hub", "--place", "lab"])),
    ("logs --lines 5", "", allowed(["-m", "score.conductor", "logs", "--lines", "5"])),
    ("gaps closeup@hub", "", allowed(["-c", ANY, "closeup@hub"])),
    # 2026-10-26: the data disk full, the copies of ended runs on it; 2026-10-30 / #74: blobs into the bucket
    *((verb, "", allowed(["-m", "score.conductor", verb], **FREE))
      for verb in ("disk", "sweep", "clean-frozen", "clean-cache", "relink-pixal", "offload-pixal")),
    *((f"{verb} --dry", "", allowed(["-m", "score.conductor", verb, "--dry"], **FREE))
      for verb in ("store-gc", "store-evict")),
    # 2026-10-28: score_lib's checkout, never pulled since boot.sh cloned it
    *((f"score-lib {action}", "", allowed(["-m", "score.conductor", "score-lib", action])) for action in ("status", "pull")),
    ("job-log x.home/work/cloud/blender-1/job3.log", "", allowed(
        [DOOR_PY, "--job-log", "x.home/work/cloud/blender-1/job3.log"], **FREE)),
    ("run-log", "", allowed([DOOR_PY, "--run-log", "200"])),
    ("run-log --lines 99999", "", allowed([ANY, "--run-log", "2000"])),  # capped
    ("fault motion@airlock", "", allowed([ANY, "--fault", "motion@airlock"], **FREE)),
    ("stop-batch 'the run holds 13 idle machines'", "", allowed(
        ["-c", ANY, "the run holds 13 idle machines"], agent=AGENT)),
    ("move-out 'no u can do the conductor move asap'", "", allowed(
        [DOOR_PY, "--move-out", "no u can do the conductor move asap"], agent=AGENT)),
    *((asked, "", allowed([DOOR_PY, flag])) for asked, flag in (
        ("store-pull", "--store-pull"), ("store-push --missing", "--store-missing"), ("store-push", "--store-push"),
        ("store-push --differs", "--store-differs"), ("store-push --replace", "--store-replace"))),
    ("store-push --force", "", FAILS),
    ("store-push --replace --missing", "", FAILS),
    ('carry --no-op "score/stages/people_bodies/bodies.py=same bytes" --write', "", allowed(
        [ANY, "--carry", "--no-op", "score/stages/people_bodies/bodies.py=same bytes", "--write"])),
    # no reason, a path out, an unknown flag: refused at the door
    *((asked, "", FAILS) for asked in ("carry --write", "carry --no-op x.py", "carry --no-op ../x.py=why",
                                       "carry --rm x")),
    ("route-log /home/score/.farm-factory-motion/candidates/x/out/chain.log", "", allowed(
        [ANY, "--route-log"], prefix=True)),
    ("route-log /etc/passwd", "", FAILS),  # not a .log
    ("design-file design/props/lab.json", "", allowed([ANY, "--design-file", "design/props/lab.json"])),
    *((asked, "", FAILS) for asked in (
        "design-file", "design-file design/../cloud/ssh_key", "design-file cloud/ledger.jsonl",
        "design-file design/props/lab.json extra", "design-file design/kit/kit.json")),
    # the owner's decision in chat: decide-yes records his quoted yes, decide applies it by its id alone
    ("decide-yes accept closeup@hub --output abc 'Yes, accept it' 'Accept closeup@hub abc?'", "", allowed(
        ["-m", "score.dashboard", "decide-yes", "accept", "closeup@hub", "--output", "abc", "Yes, accept it",
         "Accept closeup@hub abc?"])),
    (f"decide {GO}", "", allowed(["-m", "score.dashboard", "decide", GO], agent=AGENT, **FREE)),
]
# Asked through the pod's door service too (#76 step 4): the same answer as the ssh door's.
SERVICE_ASKS = ("bash", "run world1", "cat /home/score/.config/scw/config.yaml", "store-push --delete")
# move-out itself (#76 step 7): (view over the idle one, the units' stop exit) -> REFUSED (nothing latched, stopped
# or backed up) or the exit with whether the vm-final backup ran with his words.
IDLE = {"claims": 0, "running": 0, "waiting": 0, "parked": 0, "working": 0, "held": ["sync-pass-1"]}
MOVE_OUT_ROWS = [
    *((busy, 0, REFUSED) for busy in ({"claims": 1}, {"running": 1}, {"waiting": 1}, {"parked": 2},
                                      {"working": 1, "held": ["film-9"]})),
    ({}, 0, (0, True)),  # a sync pass's hold is no reason: latched, the units stopped, then the backup
    ({}, 5, (5, False)),  # the stop failed: no backup
]


# The door's reads, pushes and Buys over one home (door_world): a launch's run log in a frozen home that links the
# home's logs, store and work, a cloud job's log, fault reports, a node's log, warm pool logs, design files, a record,
# an evicted blob's mark and a link out of work; beside it a run registry, an empty home and the people routes'
# candidates.
FROZEN_HOME = "20261027-0918.home"
JOB = f"{FROZEN_HOME}/work/cloud/blender-1/job3.log"
JOB_TAIL = "Traceback: the paint of crane failed"
LOG = "{home}/frozen/" + FROZEN_HOME + "/logs/score-run-1.log"
GONE_BLOB, FRESH_BLOB = "a" * 64, "b" * 64  # gone: evicted into the store bucket here (its mark), never sent back
HOME, BARE, CANDIDATES, REGISTRY, RUNS = "<home>", "<bare>", "<candidates>", "<registry>", "<runs>"
# Every read: (row, agent_door's reader, its arguments (HOME and the like: that folder; {home} and the like filled in),
# whether the frozen home still stands (clean-frozen removes it, the logs stay), the job-log tail cap or None, what it
# answers: REFUSED, ("ends", text), ("lines", the lines after its header), ("is", text) or ("holds", words, never
# words), and a tag: every read of one tag answers the same text, however it is named, the frozen home there or gone).
READ_ROWS = [
    # 2026-10-27: surfaces-bake@campgrounds' eight failed jobs, their logs under the frozen home out of reach
    ("job-log under a frozen home", "job_log", (JOB, HOME), True, None, ("ends", JOB_TAIL), "job3"),
    ("job-log whole, as a fault report names it", "job_log", ("{frozen}/work/cloud/blender-1/job3.log", HOME), True,
     None, ("ends", JOB_TAIL), "job3"),
    ("job-log, its tail capped", "job_log", (JOB, HOME), True, 12, ("ends", "\ncrane failed"), None),
    *((f"job-log {why}", "job_log", (asked, HOME), True, None, REFUSED, None) for why, asked in (
        ("not a cloud log", f"{FROZEN_HOME}/design/x.log"), ("a link out", f"{FROZEN_HOME}/work/cloud/blender-1/escape.log"),
        ("`..` out", f"{FROZEN_HOME}/work/cloud/../../../store/k.txt"), ("a store file whole", "{home}/store/k.txt"),
        ("no such log", f"{FROZEN_HOME}/work/cloud/blender-1/job9.log"))),
    ("job-log, the frozen home gone: read where it lies", "job_log", (JOB, HOME), False, None, ("ends", JOB_TAIL),
     "job3"),
    # 2026-10-27: motion@airlock failed in a live run, its fault report and run log out of every agent's reach
    ("run-log, its last lines", "run_log", (LOG, HOME, 5), True, None,
     ("lines", [f"line {number}" for number in range(295, 300)]), "run-log"),
    ("run-log, its home gone: read where it lies", "run_log", (LOG, HOME, 5), False, None,
     ("lines", [f"line {number}" for number in range(295, 300)]), "run-log"),
    *((f"run-log elsewhere: {asked}", "run_log", (asked, HOME, 5), False, None, REFUSED, None) for asked in (
        "{home}/store/k.txt", "{tmp}/logs/score-run-1.log", "{home}/frozen/x/logs/score-run-1.log")),
    ("fault, its home's report", "fault", (LOG, "motion@airlock", HOME), True, None,
     ("ends", "motion@airlock: Traceback: no skeleton"), "fault"),
    ("fault, its home gone", "fault", (LOG, "motion@airlock", HOME), False, None,
     ("ends", "motion@airlock: Traceback: no skeleton"), "fault"),
    *((f"fault {node}", "fault", (LOG, node, HOME), False, None, REFUSED, None)
      for node in ("escape", "../k", "motion@airlock/../../k", "nothing@here", "../faults/motion@airlock")),
    ("node-log, a node's own log", "node_log", (LOG, "surfaces-bake@hub", HOME), True, None,
     ("ends", "waiting for a warm pool card"), None),
    ("node-log `..`", "node_log", (LOG, "../k", HOME), True, None, REFUSED, None),
    # 2026-11-05: a pool held no machine, nothing said why
    ("pool-log, no pool", "pool_log", ("{bare}/logs/score-run-1.log", BARE, 5), True, None, REFUSED, None),
    ("pool-log, the newest changed", "pool_log", (LOG, HOME, 1), True, None, ("lines", ["pool: a heartbeat failed"]),
     None),
    # 2026-11-07: Launch 33's first, stopped log was all the door showed of a run resumed after waiting for size
    ("followed, a resumed run's log", "followed", ("{first}", RUNS), True, None, ("is", "{then}"), None),
    ("followed, no entry named: itself", "followed", ("{then}", RUNS), True, None, ("is", "{then}"), None),
    # 2026-11-07: was a light-passes SIGTERM the runaway watch's? 16 slots held, nothing said which (a count since 11-08)
    ("outbox, a frozen home's too", "outbox", (REGISTRY,), True, None,
     ("holds", ("[runaway light-passes@hub k] stopped",), ()), None),
    ("running, a resumed run's nodes in its frozen home, a count", "running", (REGISTRY,), True, None,
     ("holds", ("a (beat", "1 running: pixal@hub", "2 running: sound@lab, x@y", "d (beat", "27 running"), ("old@z",)),
     None),
    # 2026-11-03: one design file read, nothing outside design/props|plans|surfaces, no link out
    ("design-file", "design_file", ("design/props/lab.json", HOME), True, None, ("is", '{"rows": []}'), None),
    *((f"design-file {name}", "design_file", (name, HOME), True, None, REFUSED, None) for name in (
        "design/props/out.json", "design/props/none.json", "cloud/ssh_key", "design/props/../x.json")),
    # 2026-11-03: a .log under the people routes' candidates only, no link out
    ("route-log", "route_log", ("officer/made/route/out/chain.log", CANDIDATES), True, None,
     ("ends", "the route failed\n"), None),
    *((f"route-log {name}", "route_log", (name, CANDIDATES), True, None, REFUSED, None) for name in (
        "out.log", "../home/store/objects/records/k1.json", "officer/made/route/out/missing.log")),
]
# Asked of store-push --missing before any push: (the paths asked, the answer or REFUSED).
MISSING_ROWS = [
    ("store/objects/records/k1.json\nwork/new.glb\n", "work/new.glb\n"),
    (f"store/objects/blobs/{GONE_BLOB}\nstore/objects/blobs/{FRESH_BLOB}\n", f"store/objects/blobs/{FRESH_BLOB}\n"),
    ("cloud/ssh_key\n", REFUSED),
]
# Every push into the one home, in order (2026-10-27: this PC's run pushes back through the door; 2026-10-31: a
# settle@airlock record named an output whose listing was missing): (row, its members (name, bytes, tar type), the
# stream cut at that byte or None, the push's answer or the error it raises, what is linked in place, in that order:
# blobs before the listings that name them before the records).
REGULAR = tarfile.REGTYPE
PUSHED = (("store/objects/records/settle@airlock/k.json", b'{"output": "o"}', REGULAR),
          ("store/objects/outputs/o.json", b'{"model.usd": "b"}', REGULAR), ("store/objects/blobs/b", b"usd bytes", REGULAR))
PUSH_ROWS = [
    ("a cut stream lands nothing", PUSHED, 5 * 512 + 4, tarfile.TarError, []),
    ("a whole stream lands blob, listing, record", PUSHED, None, (3, sum(len(body) for _, body, _ in PUSHED), 0),
     ["store/objects/blobs/b", "store/objects/outputs/o.json", "store/objects/records/settle@airlock/k.json"]),
    ("a file there is kept, a new one added", (("store/objects/records/k1.json", b"this PC's record", REGULAR),
                                                ("store/objects/records/k2.json", b"made on this PC", REGULAR)), None,
     (1, len("made on this PC"), 1), ["store/objects/records/k2.json"]),
    ("a blob evicted here is kept, never landed", ((f"store/objects/blobs/{GONE_BLOB}", b"blob", REGULAR),
                                                    (f"store/objects/blobs/{FRESH_BLOB}", b"blob", REGULAR)), None,
     (1, 4, 1), [f"store/objects/blobs/{FRESH_BLOB}"]),
    *((f"refused: {name} ({kind})", ((name, b"x", kind),), None, "Refused", []) for name, kind in (
        ("../escape", REGULAR), ("/etc/x", REGULAR), ("store/objects/../../cloud/ssh_key", REGULAR),
        ("cloud/ssh_key", REGULAR), ("design/props/hub.json", REGULAR), ("work", REGULAR), ("work/out/x", REGULAR),
        ("work/key", tarfile.SYMTYPE), ("work/key", tarfile.LNKTYPE))),
]
# A replacing push (2026-11-03): only under work/pixal/, never while a run is live; (the member, a run live, the
# refusal's words). None is ever let through here: work/pixal/take.png stays as it was.
REPLACE_ROWS = [("store/objects/records/k1.json", False, ""), ("work/other.glb", False, ""),
                ("work/pixal/replaced/x/take.png", False, ""), ("work/pixal/take.png", True, "a run is live")]
# buy's options after its yes id: (the options, accepted).
BUY_OPTION_ROWS = [
    (["--place", "hub,garage", "--leave-place", "square", "--phase", "models"], True),  # a Buy by place, 2026-11-11
    (["--place", "hub;rm"], False), (["--place", "a", "--place", "b"], False),
    (["--phase", "models", "--cluster", "pixal,blender"], True), (["--cluster", "pixal", "--cluster", "blender"], False),
    # 2026-11-10: people-body-person_uniform-made refused the Buy of the people looks' parts alone
    (["--phase", "people", "--leave-out", "people-body-person_uniform-made,settle"], True),
    (["--leave-out", "people;rm"], False),
    (["--max-machines", "cpu-64c-128gb=10,all=30"], True),  # a Buy's machine caps, 2026-11-06
    (["--max-machines", "cpu=x"], False), (["--max-machines", "a;b=1"], False),
    (["--take-cheap", "2.5", "--phase", "models"], True),  # --take-cheap's euros, 2026-11-11
    (["--take-cheap", "cheap"], False), (["--take-cheap", "-1"], False),
]
# Every Buy the door starts (2026-11-04: it answers at once, the Buy going on in its own session, its words in its
# log): (its yes id, buy_started's options, the cluster's settings ("box": every SCORE_K8S_* set; "none": none), what
# its command prints (it may go on after), the door's answer's start, its log's name, the log's last words or the
# refusal's words).
BUY_ROWS = [
    ("20261104T000000Z", {}, None, "print('checkout 18: launched', flush=True); time.sleep(5)",
     "buy 20261104T000000Z:", "20261104T000000Z.log", "checkout 18: launched\n"),
    ("20261106T000000Z", {"phase": "models"}, None, "print('phase')", "buy 20261106T000000Z --phase models:",
     "20261106T000000Z-models.log", "phase\n"),
    ("20261106T000000Z", {"phase": "models,surfaces", "leave_out": "sim-body,body-peel"}, None, "print('phases')",
     "buy 20261106T000000Z --phase models,surfaces --leave-out sim-body,body-peel:",
     "20261106T000000Z-models+surfaces.log", "phases\n"),
    ("20261106T000000Z", {"place": "hub,garage", "leave_place": "square"}, None, "print('places')",
     "buy 20261106T000000Z --place hub,garage --leave-place square:", "20261106T000000Z.log", "places\n"),
    # the cluster fallback (2026-11-06): refused until cluster-check passes, then its run carries SCORE_CLOUD=k8s
    ("20261106T000001Z", {"cluster": "pixal,blender"}, "none", "print('never')", None, None, "out of reach"),
    ("20261106T000002Z", {"phase": "models", "cluster": "pixal,blender"}, "box",
     "import os; print(os.environ.get('SCORE_CLOUD'), os.environ.get('SCORE_CLOUD_KINDS'))",
     "buy 20261106T000002Z --phase models --cluster pixal,blender:", "20261106T000002Z-models.log",
     "k8s pixal,blender\n"),
]


def door_world(folder):
    """The door's one home and the folders beside it (READ_ROWS' placeholders), each filled; the frozen home."""
    folder = pathlib.Path(folder)
    home, registry, candidates, bare = folder / "home", folder / "registry", folder / "candidates", folder / "bare"
    bare.mkdir(parents=True)
    files = {
        "logs/score-run-1.log": "".join(f"line {number}\n" for number in range(300)),
        "work/cloud/blender-1/job3.log": "x" * 10 + JOB_TAIL,
        "store/k.txt": "not a log",
        "store/faults/motion@airlock.txt": "motion@airlock: Traceback: no skeleton\n",
        "store/logs/surfaces-bake@hub.log": "[cloud] waiting for a warm pool card\n",
        "store/objects/records/k1.json": "the conductor's record",
        f"store/evicted/{GONE_BLOB}": '{"size": 4}',
        "work/pixal/take.png": "old",
        "design/props/lab.json": '{"rows": []}',
        f"frozen/{FROZEN_HOME}/design/x.log": "design",
        "cloud/pools/old/collector.log": "rented\nold pool\n",
        "cloud/pools/new/collector.log": "rented\npool: a heartbeat failed\n",
    }
    for name, text in files.items():
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_text(text)
    os.utime(home / "cloud/pools/old/collector.log", (1, 1))  # the old pool's log changed first
    links = {"store/faults/escape.txt": home / "store/k.txt", "work/cloud/blender-1/escape.log": home / "store/k.txt",
             "work/out": folder / "outside", "design/props/out.json": home / "store/objects/records/k1.json"}
    frozen = home / "frozen" / FROZEN_HOME
    for entry in ("logs", "store", "work"):  # a frozen home links the home's entries (graph/frozen.home_copy)
        links[f"frozen/{FROZEN_HOME}/{entry}"] = home / entry
    (folder / "outside").mkdir()
    for name, target in links.items():
        (home / name).symlink_to(target)
    (candidates / "officer/made/route/out").mkdir(parents=True)
    (candidates / "officer/made/route/out/chain.log").write_text("Traceback: the route failed\n")
    (candidates / "out.log").symlink_to(home / "store/objects/records/k1.json")
    for runs, name, state, nodes in ((registry / "runs", "a", "running", ["pixal@hub"]),
                                     (registry / "runs", "d", "running", 27),
                                     (registry / "frozen" / "c1.home" / "runs", "b", "running", ["sound@lab", "x@y"]),
                                     (registry / "runs", "c", "ended", ["old@z"])):
        runs.mkdir(parents=True, exist_ok=True)
        (runs / f"{name}.json").write_text(json.dumps({"id": name, "state": state, "running": nodes}))
    first, then = registry / "logs" / "score-run-1.log", registry / "logs" / "score-run-2.log"
    first.parent.mkdir(parents=True)
    first.write_text("score run: waiting for size: 16 jobs, 2 cores; registered as w1; score resume starts it\n")
    then.write_text("heartbeat\n")
    (registry / "runs" / "w1.json").write_text(json.dumps({"id": "w1", "state": "resumed",
                                                             "resumed": {"pid": 1, "log": str(then)}}))
    (registry / "frozen" / "c1.home" / "store").mkdir(parents=True)
    (registry / "frozen" / "c1.home" / "store" / "owner-outbox.txt").write_text(
        "[runaway light-passes@hub k] stopped\n")
    places = {HOME: home, BARE: bare, CANDIDATES: candidates, REGISTRY: registry, RUNS: registry / "runs"}
    words = {"{home}": str(home), "{frozen}": str(frozen), "{bare}": str(bare), "{tmp}": str(folder),
             "{first}": str(first), "{then}": str(then)}

    def filled(value):
        if value in places:
            return places[value]
        if not isinstance(value, str):
            return value
        for word, text in words.items():
            value = value.replace(word, text)
        return value
    return home, frozen, filled


def stream(members, cut=None):
    """The members (name, bytes, tar type) as a tar stream, cut at byte `cut`; a link member points out of the home."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        for name, body, kind in members:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.REGTYPE:
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
            else:
                info.linkname = "/home/score/.config/scw/config.yaml"
                archive.addfile(info)
    whole = data.getvalue()
    return io.BytesIO(whole[:cut] if cut else whole)


def store_files(home):
    return {path.relative_to(home).as_posix() for path in (home / "store").rglob("*") if path.is_file()}



def heredoc(text, end):
    """The lines of the bootcmd heredoc ending at `end`, indentation removed."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.endswith(f"<< '{end}'"))
    stop = next(index for index in range(start + 1, len(lines)) if lines[index].strip() == end)
    return [line[4:] for line in lines[start + 1:stop]]


# The owner's machine.py session, dry on one recording scw (owner_session), and the judging around it.
OWNER_ENV = ("SCORE_OWNER=owner\nSCORE_SYNC_URL=https://cockpit.example\nSCORE_SYNC_TOKEN=secret\n"
             "SCORE_SECRET_READER=/home/someone/.local/bin/reader\n")
YES = {"id": "y-1", "answer": "yes", "question": "Switch the conductor on?"}
# step_refusal: (step, the process's environment, the owner's yes open for it, whether refused, the yes it runs under)
REFUSAL_ROWS = [
    *(("up", {marker: "1"}, None, True, None) for marker in AGENT_MARKERS),
    ("up", {AGENT_MARKERS[0]: "1"}, YES, False, YES),
    ("move", {}, YES, False, None),  # the owner needs no yes
]
# grow_data: (GB added, the owner's yes, the new size or the refusal)
GROW_ROWS = [(100, "his yes", machine.DATA_GB + 100), (0, "his yes", SystemExit), (100, " ", SystemExit)]
# pc_units_off: (the units this PC has, systemctl's exit, the systemctl calls, the units switched off or the error)
UNITS_OFF_ROWS = [
    (["score-sync.timer", "score-listen.service"], 0,
     [("disable", "--now", "score-sync.timer", "score-listen.service")], ["score-sync.timer", "score-listen.service"]),
    ([], 0, [], []),
    (["score-resume.service"], 1, [("disable", "--now", "score-resume.service")], "Access denied"),
]


def owner_session(folder):
    """The owner's machine.py session run dry on one recording scw, no scw ever called: down unconfirmed, up with his
    env file and the agents' key, the user-data set, every GROW_ROWS growth, the move, the stored key's read.
    {step: (its result or the SystemExit it raised, its scw calls, its printed lines)}, the owner's env file and every
    cloud-init the session rendered ((owner's key, agents' key, volume), its text)."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True)
    private, agent = owner_keys(folder, "owner"), owner_keys(folder, "agent")
    rendered, render = [], machine.render_cloud_init
    owner_env = folder / "dashboard.env"
    owner_env.write_text(OWNER_ENV)
    printed = []
    scw = machine.Scw(dry=True, say=printed.append)
    steps = {}
    real_run = subprocess.run

    def no_scw(arguments, *args, **kwargs):
        assert arguments[0] != "scw", f"a dry run called scw: {arguments}"
        return real_run(arguments, *args, **kwargs)

    def step(name, act):
        calls, lines = len(scw.calls), len(printed)
        try:
            result = act()
        except SystemExit as error:
            result = error
        steps[name] = (result, scw.calls[calls:], printed[lines:])
    with pytest.MonkeyPatch.context() as patched:
        for marker in AGENT_MARKERS:
            patched.delenv(marker, raising=False)
        patched.setattr(machine.subprocess, "run", no_scw)
        patched.setattr(machine, "render_cloud_init", lambda *slots: rendered.append((slots, render(*slots)))
                        or rendered[-1][1])
        step("down", lambda: machine.down(types.SimpleNamespace(with_data=False), scw, say=printed.append,
                                          answer=lambda question: "no"))
        step("up", lambda: machine.up(types.SimpleNamespace(owner_key=str(private), agent_key=f"{agent}.pub",
                                                            env_file=str(owner_env)), scw, printed.append))
        step("user-data", lambda: machine.set_user_data(types.SimpleNamespace(owner_key=str(private), agent_key=None),
                                                        scw, say=printed.append))
        for gigabytes, yes, _ in GROW_ROWS:
            step(("grow", gigabytes, yes), lambda: machine.grow_data(scw, gigabytes, yes, say=printed.append))
        step("move", lambda: machine.move(types.SimpleNamespace(owner_key="~/.ssh/id_ed25519"), scw, printed.append))
        step("stored key", lambda: machine.stored_key(scw))
    return steps, owner_env, rendered


def argv_matches(argv, want, prefix):
    if argv is None or (len(argv) < len(want) if prefix else len(argv) != len(want)):
        return False
    return all(expected is ANY or (argv[index].endswith("agent_door.py") if expected is DOOR_PY else
                                   argv[index] == expected) for index, expected in enumerate(want))


def test_the_conductor_acts_only_on_the_owners_word_and_moves_only_when_safe(door, tmp_path, monkeypatch,
                                                                          short_path, no_metadata):
    """Every PREPARE_ROWS run of prepare.sh and every row of DOOR_ROWS asked through agent_door.sh side by side,
    then held to its outcome; every
    MOVE_OUT_ROWS view through move-out; the owner's machine.py session (owner_session) held to its gates, its calls,
    the cloud-init it rendered and the boot unit in it, and its move, its home then set aside, every REFUSAL_ROWS and
    UNITS_OFF_ROWS case judged; then over one door home (door_world) every MISSING_ROWS ask, PUSH_ROWS push and
    REPLACE_ROWS replace, every READ_ROWS read before and after its frozen home goes, a node's gaps and the predicted
    takes, a run's stack, and every BUY_OPTION_ROWS and BUY_ROWS Buy. Every BOOT_ROWS boot of boot.sh, run as the
    rendered score-boot.service runs it and side by side with all of that, held to its outcome; the first boot's root
    is the conductor the rest reads: its units verified with the sync's rendered for its checkout; its data volume read
    by the health record in every HEALTH_ROWS state; one vault read by its installed reader, by its
    score-secrets.service through it, by Claude Code's login over its CLI, by the door's token (the door service's
    SERVICE_ASKS asked with it) and the cluster settings the door reads; booted again after the move; then every CASES
    moment of its checkout, cloned from an origin, through score-update or the door's release-pin."""
    import agent_door
    from score.store.backup import _migrate

    prepared = {}
    preparing = concurrent.futures.ThreadPoolExecutor(len(PREPARE_ROWS))
    for row, arguments, scw_text, _, _, _ in PREPARE_ROWS:  # side by side with the door's rows
        (tmp_path / "prepare" / row).mkdir(parents=True)
        prepared[row] = preparing.submit(prepare, tmp_path / "prepare" / row, *arguments, scw_text=scw_text)

    for step, environment, open_yes, refused, runs_under in REFUSAL_ROWS:
        why, found = machine.step_refusal(step, environment, open_yes=lambda asked: open_yes)
        assert bool(why) is refused and found == runs_under, (step, environment, why, found)
    steps, owner_env, rendered = owner_session(tmp_path / "machine")
    down, _, _ = steps["down"]
    assert isinstance(down, SystemExit) and "not confirmed" in str(down) and steps["down"][1] == [], down
    every = [(name, call) for name, (_, calls, _) in steps.items() for call in calls]
    printed = [line for _, _, lines in steps.values() for line in lines]
    assert every and all(f"scw {call}" in printed for _, call in every)
    for name, call in every:
        assert "farm-factory-batch" not in call, call  # the runner's leftover sweeps delete by that tag
        if not call.startswith("account project list"):
            assert any(f" {key}=" in f" {call}" for key in ("zone", "region")), f"no zone or region: {call}"
        if (" list " in f" {call} " or " create " in f" {call} ") and not call.startswith(INSIDE_OWNED):
            assert "project-id=" in call, f"no project: {call}"
        assert ".value=" not in call or "<secret>" in call, call
    _, up_calls, _ = steps["up"]
    server = next(call for call in up_calls if call.startswith("instance server create"))
    assert "project-id=<id of project score-conductor>" in server and "tags.0=score-conductor" in server
    assert any("inbound-default-policy=drop" in call for call in up_calls)  # only ssh comes in
    _, user_data, _ = steps["user-data"]
    assert any(call.startswith("instance user-data set ") and f"zone={machine.ZONE}" in call for call in user_data)
    assert not any(" create " in f" {call} " or " delete " in f" {call} " for call in user_data)
    # the cloud-init up rendered (and set as user-data, without the agents' key): it passes `cloud-init schema`; the
    # agents' key is bound to the door with no pty or forwarding, the owner's is not; no slot is left unfilled; the
    # first boot runs boot.sh through score-boot.service, enabled from the per-boot script once the bus is up
    ((owner_key, agent_key, volume), text), ((_, no_agent, _), _) = rendered
    assert owner_key.endswith(" owner\n") and agent_key.endswith(" agent\n") and no_agent is None, rendered
    assert machine.check_cloud_init(owner_key.strip(), agent_key.strip()) is None
    door_line = next(line for line in text.splitlines() if agent_key.split()[1] in line)
    for option in ('command=\\"/usr/local/bin/score-agent-door\\"', "no-pty", "no-port-forwarding",
                   "no-agent-forwarding"):
        assert option in door_line, (option, door_line)
    assert "command=" not in next(line for line in text.splitlines() if owner_key.split()[1] in line)
    assert f"scsi-0SCW_sbs_volume-{volume}" in text and volume == "<id of the new data volume>", volume
    assert re.search(r"@[A-Z_]+@", text) is None, "a slot left unfilled"
    assert "runcmd:" not in text  # the first boot runs boot.sh through the unit, as every later boot does
    unit = heredoc(text, "UNIT")
    move, system, user = [line for line in unit if line.startswith("ExecStart=")]
    assert "checkout -q --detach origin/main" in move and "boot.sh system" in system
    assert "runuser -u score --" in user and "boot.sh user" in user
    # the conductor boots as this unit runs boot.sh: every BOOT_ROWS boot without its own parts runs the unit's, side
    # by side with the door's rows
    unit_parts = tuple(re.search(r"boot\.sh (\w+)", line).group(1) for line in (system, user))

    def boot(row):
        name, installed, change, parts = row[:4]
        root, shims = boot_root(short_path / name, installed=installed)
        if change:
            change(root, shims)
        return (root, shims, *run_boot(short_path / name, root, shims, parts=parts or unit_parts))
    booting_pool = concurrent.futures.ThreadPoolExecutor(len(BOOT_ROWS))
    booting = {row[0]: booting_pool.submit(boot, row) for row in BOOT_ROWS}
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
    for gigabytes, yes, want in GROW_ROWS:
        grown, calls, _ = steps[("grow", gigabytes, yes)]
        resized = [call for call in calls if call.startswith("block volume update")]
        if want is SystemExit:
            assert isinstance(grown, SystemExit) and calls == [], (gigabytes, yes, grown)
        else:
            assert grown == want and resized == [
                f"block volume update '<id of the data volume>' size={want}GB zone={machine.ZONE}"], (grown, calls)
    _, move_calls, move_lines = steps["move"]
    assert all(call.startswith(("account project list", "instance server list")) for call in move_calls), move_calls
    disable = move_lines.index(next(line for line in move_lines if "disable --now" in line))
    assert disable < move_lines.index(next(line for line in move_lines if "--from-pc" in line))
    _, _, key_lines = steps["stored key"]  # asked of score-conductor's own project, by name
    assert any("name=score-conductor-key 'project-id=<id of project score-conductor>'" in line for line in key_lines)
    (local, environment), remote = machine.move_steps("/home/someone/.local/bin/scw", YES)
    assert local[-3:] == ["score.store.backup", "migrate", "--from-pc"]
    # the PC reads the backup's password where the conductor does: the conductor's reader, its secrets project
    assert environment["SCORE_SECRET_READER"] == str(machine.HERE / "secret_reader.sh")
    assert environment["SCORE_SECRETS_PROJECT"] == machine.SECRETS_PROJECT_NAME
    assert environment["SCORE_CONDUCTOR_YES"] == "y-1"  # the migrate steps check the same yes
    assert remote.index("--onto-conductor") < remote.index("boot.sh env") < remote.index("install-sync")
    assert "--no-pull" in remote
    text = machine.env_text(owner_env)
    values = dict(line.split("=", 1) for line in text.splitlines())
    assert "SCORE_SYNC_TOKEN" not in values and "secret" not in text.replace("secret-reader", "")
    assert values["SCORE_SECRET_READER"] == "/usr/local/bin/score-secret-reader"  # the conductor's, not the PC's
    assert values["SCORE_OWNER"] == "owner"
    for present, exit_code, want_calls, want in UNITS_OFF_ROWS:
        calls = []

        def systemctl(*args):
            calls.append(args)
            return types.SimpleNamespace(returncode=exit_code, stdout="", stderr="Access denied" if exit_code else "")
        if isinstance(want, str):
            with pytest.raises(SystemExit, match=want):
                machine.pc_units_off(present=present, systemctl=systemctl)
        else:
            assert machine.pc_units_off(present=present, systemctl=systemctl) == want, present
        assert calls == want_calls, (present, calls)
    # after the move the PC's home is set aside read-only, last, once the yes is marked; status reads the health
    # record with the conductor's own key (the PC's key got HTTP 403, 2026-10-24)
    home, final, ran, read = tmp_path / "machine" / "props", tmp_path / "machine" / "props.pc-final", [], []
    (home / "store").mkdir(parents=True)
    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(machine, "PROPS_HOME", home)
        patched.setattr(machine, "PC_FINAL_HOME", final)
        patched.setattr(machine.conductor_yes, "mark_done", lambda yes, step, store=None: ran.append(
            ("marked", step, store.objects.root)))
        patched.setattr(machine, "stored_key", lambda scw: {"access_key": "SCWCON", "secret_key": "s-con"})
        machine.retire_pc_home(YES, "scw", run=lambda command, **kwargs: ran.append(
            (command, kwargs.get("env", {}))) or types.SimpleNamespace(returncode=0))
        record = machine.health_record(types.SimpleNamespace(dry=False),
                                       read=lambda *args: read.append(args) or b'{"active_runs": 0}')
    assert final.is_dir() and home.is_dir() and not any(home.iterdir())
    assert ran[0][0][-1] == "--pc-test-home" and ran[0][1]["SCORE_CONDUCTOR_YES_HOME"] == str(final)
    assert ran[1][1]["UV_PROJECT_ENVIRONMENT"] == str(home / "env")
    assert ("marked", "move", final / "store" / "objects") in ran
    assert ran[-1][0] == ["chmod", "-R", "a-w", str(final)]  # read-only last, after the yes is marked
    assert record == {"active_runs": 0} and read[0][-2:] == ("SCWCON", "s-con")
    asks = {}
    for asked, env_text, want in DOOR_ROWS:
        assert asked not in asks.get(env_text, {}), f"asked twice: {asked!r}"
        asks.setdefault(env_text, {})[asked] = want
    answers = {(env_text, asked): answer for env_text, rows in asks.items()
               for asked, answer in zip(rows, door.many(tuple(rows), env_text))}
    for (env_text, asked), (code, why, argv, env) in answers.items():
        want, said = asks[env_text][asked], (asked, env_text, code, why, argv)
        if want in (REFUSED, LATCHED):
            assert code == 126 and argv is None and want in why, said
        elif want == FAILS:
            assert code != 0, said
        else:
            assert code == 0 and argv_matches(argv, want["argv"], want["prefix"]), said
            for name, value in want["env"].items():
                if value is AGENT:
                    assert all(env.get(marker) == "1" for marker in AGENT_MARKERS), (said, env)
                else:
                    assert env.get(name) == value, (said, name, env.get(name))

    for row, _, _, calls_scw, says, never in PREPARE_ROWS:
        done, log = prepared[row].result(), tmp_path / "prepare" / row / "scw.log"
        assert done.returncode == 0, (row, done.stderr)
        calls = log.read_text().splitlines() if log.exists() else []
        assert bool(calls) is calls_scw and not [call for call in calls if " create" in call], (row, calls)
        assert all(words in done.stderr for words in says), (row, done.stderr)
        assert not any(words in done.stderr for words in never), (row, done.stderr)
    preparing.shutdown()

    # ---- the conductor as boot.sh makes it: every BOOT_ROWS boot held to its outcome; the first boot's root is then
    # the one world the rest reads: its data volume the health record's home, its installed reader and secrets unit
    # reading the vault the door's token and the cluster's settings come from, its checkout the one score-update moves
    booted = {name: future.result() for name, future in booting.items()}
    booting_pool.shutdown()
    for name, _, _, _, stops, never, made, missing in BOOT_ROWS:
        root, _, done, calls = booted[name]
        said = (name, done.stderr + done.stdout)
        assert (done.returncode == 0) is (stops is None), said
        assert stops is None or re.search(stops, done.stderr), said
        assert not [call for call in calls if call.startswith(never)], (name, calls)
        assert all(os.access(root.joinpath(*BIN, file), os.X_OK) for file in made), said
        assert not any(root.joinpath(*BIN, file).exists() for file in missing), said
    root, shims, done, calls = booted["first"]
    booted_home = root / "home" / "score"
    assert "mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test" in calls
    assert "UUID=1111-uuid /home/score/.farm-factory-props ext4" in (root / "etc" / "fstab").read_text()
    mountpoint = booted_home / ".farm-factory-props"
    assert calls.index(f"mount {mountpoint}") < calls.index(
        "resize2fs /dev/disk/by-id/scsi-0SCW_sbs_volume-test")  # a grown volume gets its room at each boot
    assert calls.index(f"chattr +i {mountpoint}") < calls.index(f"mount {mountpoint}"), \
        "the bare mountpoint is not made immutable before the data volume is mounted on it"
    sshd = (root / "etc" / "ssh" / "sshd_config.d" / "50-score-conductor.conf").read_text()
    assert "PasswordAuthentication no" in sshd and "PermitRootLogin no" in sshd
    assert not any("--no-dev" in call for call in calls), "the prop environment was built before the move"
    assert not any("install-sync" in call for call in calls), "the sync's units came before the move"
    units = booted_home / ".config" / "systemd" / "user"
    for unit in machine.unit_files():
        installed = (units / unit.name).read_text()
        assert installed == machine.rendered_unit(unit), unit.name
        assert not any(slot in installed for slot in machine.UNIT_SLOTS), unit.name
        # the conductor's units run on the conductor alone: none names a path of the owner's PC
        assert "/home/dupe" not in installed and "wsl" not in installed.lower(), unit.name
    # every installed unit passes `systemd-analyze --user verify` in the home the boot made
    assert machine.check_units(booted_home) is None
    # resume and health write into the home, so on the conductor they wait for the move's machine.json
    waits = "ConditionPathExists=%h/.farm-factory-props/machine.json"
    assert waits in (units / "score-resume.service.d" / "conductor.conf").read_text().splitlines()
    assert waits in (units / "score-health.service").read_text().splitlines()
    # score_lib's web copies run gltfpack offline from the cache the boot seeded: the pin export.py runs
    pin = re.search(r'^GLTFPACK = "(gltfpack@[0-9.]+)"', (REPO / "tools/review/viewer/export.py").read_text(), re.M)
    assert f"npm cache add {pin.group(1)}" in calls, calls
    assert "apt-get remove -y -q nodejs" in calls  # Ubuntu's old node is never found before the pinned one
    assert "Claude Code 2.1.318 already installed" in done.stdout  # the pinned CLI there is not installed again
    # the sync's units as install-sync renders them for this checkout pass verify, and the pass updates first
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")  # the sync's modules read them
    django.setup()
    from score.dashboard.sync import timer
    checkout, env_file = booted_home / "projects" / "score", booted_home / ".config" / "score" / "dashboard.env"
    sync_units = [units / name for name in ("score-sync.service", "score-sync.timer")]  # where install-sync puts them
    for path in sync_units:
        path.write_text(timer.unit_text(path.name, checkout, env_file, timer.SECRET, pull=False))
    verified = subprocess.run(["systemd-analyze", "--user", "verify", *map(str, sync_units)], capture_output=True,
                              text=True)
    assert verified.returncode == 0 and not (verified.stderr + verified.stdout).strip(), verified.stderr
    rendered_sync = sync_units[0].read_text()
    assert (f"\nExecStartPre=/usr/bin/python3 -I {checkout}/tools/cloud/conductor/update.py --repo {checkout}\n"
            in rendered_sync)

    # ---- the health record (health_push.record) over the boot's data volume: fresh, it reads idle; every later
    # HEALTH_ROWS state is built on it, its processes working, its hold held
    now = datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc)
    monkeypatch.setenv("SCORE_HEALTH_FILE", str(mountpoint / "conductor" / "health.json"))
    for name, build, holds, want in HEALTH_ROWS:
        copies = build(mountpoint)
        with contextlib.ExitStack() as stack:
            for copy in copies:
                process = subprocess.Popen(["sleep", "30"], cwd=mountpoint / "frozen" / copy)
                stack.callback(process.wait)
                stack.callback(process.kill)
            if holds:
                held = stack.enter_context((mountpoint / "conductor" / "holds" / "film-preview-2.lock").open("a"))
                fcntl.flock(held, fcntl.LOCK_EX)  # flock is per open file: the record's own open is refused too
            if isinstance(want, type):
                with pytest.raises(want):
                    health_push.record(mountpoint, now)
                continue
            record = health_push.record(mountpoint, now)
        counted = (record["active_runs"], record["parked"], record["frozen"], record["working"], record["health"])
        assert counted == want and record["written_at"].startswith("2026-10-22T00:00:00"), (name, record)
        assert health_push.working(mountpoint) == 0, name  # the hold released

    # ---- the secrets: one vault, read by the reader the boot installed, by its score-secrets.service (secrets.sh)
    # through it, by Claude Code's login over the CLI the boot found, by the door's token and the cluster's settings
    vault_folder = short_path / "vault"
    vault, vault_log, runtime = vault_folder / "vault.json", vault_folder / "scw.log", root / "run" / "user" / "1100"
    for made in (vault_folder, runtime):
        made.mkdir(parents=True)
    (vault_folder / "scw.py").write_text(VAULT_SCW)
    scw = executable(vault_folder / "scw", f'#!/bin/sh\nexec "{sys.executable}" -I "{vault_folder / "scw.py"}" "$@"\n')
    reader = root.joinpath(*BIN, "score-secret-reader")
    gcloud = executable(vault_folder / "gcloud",
                        f"#!/bin/sh\necho \"$CLOUDSDK_CONFIG $*\" > {vault_folder}/gcloud.log\n")
    env = {**os.environ, "HOME": str(booted_home), "SCORE_SCW": str(scw), "SCORE_SECRETS_PROJECT": "secrets-here",
           "SCORE_READER_PYTHON": sys.executable, "VAULT": str(vault), "VAULT_LOG": str(vault_log),
           "XDG_RUNTIME_DIR": str(runtime), "SCORE_GCLOUD": "/bin/false", "SCORE_SECRET_READER": str(reader),
           "SCORE_LOGIN_PYTHON": sys.executable}
    started = next(line for line in (units / "score-secrets.service").read_text().splitlines()
                   if line.startswith("ExecStart="))
    secrets_command = started.removeprefix("ExecStart=").replace("%h", str(booted_home)).split()

    def hold(*names, **values):
        """The vault holds `names`, each valued "value of <name>", and `values` (by name, `_` for `-`)."""
        vault.write_text(json.dumps({**{name: f"value of {name}" for name in names},
                                     **{name.replace("_", "-"): value for name, value in values.items()}}))

    def read(*arguments, project="secrets-here"):
        return subprocess.run([str(reader), *arguments], env={**env, "SCORE_SECRETS_PROJECT": project},
                              capture_output=True, text=True, timeout=30)

    def secrets():
        return subprocess.run(secrets_command, env=env, capture_output=True, text=True, timeout=30)
    hold(*HELD)  # no optional secret held
    done = read("gemini-api-key")
    assert done.returncode == 0 and done.stdout == "value of gemini-api-key", done.stderr
    assert "project-id=p-1" in vault_log.read_text().splitlines()[1]  # p-1 is secrets-here's id, p-0 another project's
    absent = read("--if-present", "google-billing-reader")
    assert absent.returncode == 0 and absent.stdout == "", absent.stderr
    assert read("--if-present", "gemini-api-key").stdout == "value of gemini-api-key"
    refused = read("x", project="missing")
    assert refused.returncode != 0 and "found 0" in refused.stderr
    # An agent's `ask` reads the door's token through this reader by the secrets project's name, never the box's own
    # SCORE_SECRET_READER (2026-11-10: this PC's looked only in babon-ops); the door service opens with that token.
    # Break: `asker_reader` hands back `[environment["SCORE_SECRET_READER"], TOKEN_SECRET]`.
    elsewhere = {**env, "SCORE_SECRET_READER": str(vault_folder / "another-projects")}
    command, found = door_service.asker_reader(elsewhere)
    assert command[-2:] == [str(HERE / "secret_reader.sh"), door_service.TOKEN_SECRET]
    door_token = door_service.asker_token(elsewhere)
    assert door_token == f"value of {door_service.TOKEN_SECRET}"
    assert door_service.asker_reader({"PATH": ""})[1]["SCORE_SECRETS_PROJECT"] == door_service.SECRETS_PROJECT
    # secrets.sh: an absent optional billing reader leaves a note and no gcloud; held, every file-shaped secret goes
    # whole at 600 into a 700 folder on the runtime tmpfs and the note goes; the cluster's settings the door reads
    # there are SCORE_K8S_* only, and the login's path; an empty read replaces nothing; a failed read fails
    done = secrets()
    assert done.returncode == 0 and "skipped" in done.stdout, done.stderr
    folder = runtime / "score"
    assert sorted(path.name for path in folder.iterdir()) == ["google-billing-reader.note", "score-lib-deploy-key"]
    settings = "SCORE_K8S_CONTEXT=c\nPATH=/evil\nSCORE_K8S_KUBECONFIG=/elsewhere\n"
    hold(*HELD, *OPTIONAL, score_k8s_settings=settings, score_k8s_kubeconfig="{}")
    env["SCORE_GCLOUD"] = str(gcloud)
    done = secrets()
    assert done.returncode == 0, done.stderr
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    key = folder / "score-lib-deploy-key"
    assert key.read_text() == "value of score-lib-deploy-key\n" and stat.S_IMODE(key.stat().st_mode) == 0o600
    assert (folder / "google-billing-reader.json").read_text() == "value of google-billing-reader\n"
    assert sorted(path.name for path in folder.iterdir()) == ["google-billing-reader.json", "k8s-kubeconfig", "k8s.env",
                                                              "score-lib-deploy-key"]
    assert (folder / "k8s.env").read_text() == settings  # the tenant cluster's, optional
    assert (vault_folder / "gcloud.log").read_text().startswith(f"{folder}/gcloud auth activate-service-account")
    assert agent_door.cluster_values(folder) == {"SCORE_K8S_CONTEXT": "c",
                                                 "SCORE_K8S_KUBECONFIG": str(folder / "k8s-kubeconfig")}
    (folder / "k8s-kubeconfig").unlink()
    assert agent_door.cluster_values(folder) == {"SCORE_K8S_CONTEXT": "c"}
    hold(*HELD, *OPTIONAL, score_lib_deploy_key="")
    refused = secrets()
    assert refused.returncode != 0 and "empty" in refused.stderr
    assert key.read_text() == "value of score-lib-deploy-key\n", "an empty read replaced a good key"
    hold(*HELD, google_billing_reader=None)
    refused = secrets()
    assert refused.returncode != 0 and "reading google-billing-reader failed" in refused.stderr

    # Claude Code's login (claude_login.py, run by secrets.sh): no secret -> no `claude` and the adapter's NotHere;
    # the CLI the boot found at its pin and the secret -> `claude` asks with the login in the CLI's environment alone,
    # written nowhere.
    from score.adapters.models import claude_code
    cli, bin_folder = booted_home / ".local" / "lib" / "claude-code" / "bin" / "claude", booted_home / ".local" / "bin"
    body = {"contents": [{"parts": [{"text": "which login?"}]}], "generationConfig": {"responseSchema": {
        "type": "OBJECT", "properties": {"login": {"type": "BOOLEAN"}, "model": {"type": "STRING"}}}}}
    said = []
    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(claude_code, "LEDGER", vault_folder / "home" / "claude-ledger.jsonl")
        patched.setattr(claude_code, "CACHE", vault_folder / "home" / "claude-cache")
        for name in ("HOME", "SCORE_SCW", "SCORE_SECRETS_PROJECT", "SCORE_READER_PYTHON", "VAULT", "VAULT_LOG",
                     "SCORE_SECRET_READER"):
            patched.setenv(name, env[name])
        patched.setenv("PATH", str(bin_folder))
        patched.setenv("ANTHROPIC_API_KEY", "an-api-key")
        for linked in (False, True, False):
            hold(*HELD, **({"claude_code_oauth_token": LOGIN} if linked else {}))
            done = secrets()
            assert done.returncode == 0, done.stderr
            said.append(done.stdout + done.stderr)
            assert (bin_folder / "claude").is_symlink() is linked
            if not linked:
                with pytest.raises(claude_code.NotHere, match="runs on this PC"):
                    claude_code.asked({"one": body}, caller="finish-route-palette")
        hold(*HELD, claude_code_oauth_token=LOGIN)
        assert secrets().returncode == 0
        login_answers = claude_code.asked({"one": body}, caller="finish-route-palette")
    assert json.loads(login_answers["one"]) == {"login": True, "model": "claude-opus-5-5"}, login_answers
    written = [path.read_bytes() for folder_read in (vault_folder, runtime, booted_home / ".local")
               for path in folder_read.rglob("*")
               if path.is_file() and not path.is_symlink() and path not in (vault, cli)]  # the two hold it
    assert len(written) > 3 and (vault_folder / "home" / "claude-ledger.jsonl").exists()
    assert not any(LOGIN.encode() in text for text in written), "the login was written to a file"
    assert not any(LOGIN in text for text in said), "the login reached a log line"
    (bin_folder / "claude").unlink()
    executable(bin_folder / "claude", "#!/bin/sh\n")  # a claude that is not ours is never removed
    hold(*HELD)
    assert secrets().returncode == 0 and (bin_folder / "claude").read_text() == "#!/bin/sh\n"

    # the door service opens only with the vault's token, and answers as the ssh door does
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        served = dict(zip(SERVICE_ASKS, pool.map(lambda asked: door.service(asked, door_token), SERVICE_ASKS)))
    for asked, answer in served.items():
        assert answer == answers["", asked], asked
    code, why, argv, recorded = door.service("status", door_token)
    assert code == 0 and argv is not None and "status" in argv and all(recorded.get(name) for name in AGENT_MARKERS)
    with pytest.raises(urllib.error.HTTPError) as refused:
        door.service("status", "wrong", opened=door_token)
    assert refused.value.code == 403
    with pytest.raises(SystemExit):
        door_service.serve("", 0)  # no token read: the door stays shut

    for busy, stop_code, want in MOVE_OUT_ROWS:
        calls, latched = [], []

        def ran(argv, **options):
            calls.append((argv, options.get("env", {}).get(_migrate.MOVE_WORDS)))
            return types.SimpleNamespace(returncode=stop_code if argv[0] == "systemctl" else 0, stderr="no bus")

        def moving():
            return agent_door.move_out("his go", pathlib.Path("/nowhere"), run=ran, view={**IDLE, **busy},
                                       latch=lambda *words: latched.append(words) or "latch")
        if want == REFUSED:
            with pytest.raises(agent_door.Refused):
                moving()
            assert calls == [] and latched == [], busy
            continue
        exit_code, backed_up = want
        assert moving() == exit_code, (busy, stop_code)
        assert latched and latched[0][1] == "his go", latched
        assert calls[0][0] == ["systemctl", "--user", "stop", *_migrate.VM_UNITS], calls
        if backed_up:
            assert calls[1][0][-2:] == ["migrate", "--from-vm"] and calls[1][1] == "his go", calls
        else:
            assert len(calls) == 1, calls

    home, frozen, filled = door_world(tmp_path / "door")
    for missing, want in MISSING_ROWS:  # asked before any push lands
        if want == REFUSED:
            with pytest.raises(agent_door.Refused):
                agent_door.store_missing(home, missing)
        else:
            assert agent_door.store_missing(home, missing) == want, missing
    landed, link = [], os.link
    monkeypatch.setattr(os, "link", lambda source, target: (link(source, target), landed.append(str(target)))[0])
    for row, members, cut, want, order in PUSH_ROWS:
        landed.clear()
        before = store_files(home)
        if want == "Refused" or isinstance(want, type):
            with pytest.raises(agent_door.Refused if want == "Refused" else want):
                agent_door.store_push(home, stream(members, cut))
        else:
            assert agent_door.store_push(home, stream(members, cut)) == want, row
        assert [pathlib.Path(path).relative_to(home).as_posix() for path in landed] == order, row
        assert store_files(home) == before | set(order), row
        assert not any((home / "tmp" / "this-pc-push").glob("*")), row
    monkeypatch.setattr(os, "link", link)
    assert (home / "store/objects/records/k1.json").read_text() == "the conductor's record"
    assert (home / "store/objects/records/k2.json").read_text() == "made on this PC"
    assert not list((tmp_path / "door" / "outside").iterdir()) and not (home / "cloud" / "ssh_key").exists()
    assert not (home / "work/key").exists() and not (tmp_path / "door" / "escape").exists()
    assert not (home / "store/objects/blobs" / GONE_BLOB).exists()
    from score.conductor import disk
    for member, live, words in REPLACE_ROWS:
        with pytest.MonkeyPatch.context() as patched:
            if live:
                patched.setattr(disk, "needed", lambda folder: {"frozen/copy"})
            with pytest.raises(agent_door.Refused, match=words):
                agent_door.store_replace(home, stream(((member, b"new", REGULAR),)), "now")
    assert (home / "work/pixal/take.png").read_text() == "old"
    with pytest.MonkeyPatch.context() as patched:  # carry (2026-11-03) never runs with a run live
        patched.setattr(agent_door, "replace_refusal", lambda folder: "a run is live (r1)")
        with pytest.raises(agent_door.Refused, match="a run is live"):
            agent_door.carried(["--no-op", "x.py=why"], home)

    tags = {}
    for row, reader, arguments, standing, cap, want, tag in sorted(READ_ROWS, key=lambda row: not row[3]):
        if not standing and frozen.exists():
            shutil.rmtree(frozen)  # the run ended and its home went
        asked = [filled(argument) for argument in arguments]
        with pytest.MonkeyPatch.context() as patched:
            if cap:
                patched.setattr(agent_door, "JOB_LOG_CHARACTERS", cap)
            if want == REFUSED:
                with pytest.raises(agent_door.Refused):
                    getattr(agent_door, reader)(*asked)
                continue
            said = getattr(agent_door, reader)(*asked)
        kind, *expected = want
        if kind == "ends":
            assert said.endswith(expected[0]), (row, said)
        elif kind == "lines":
            assert said.splitlines()[1:] == expected[0], (row, said)
        elif kind == "is":
            assert said == filled(expected[0]), (row, said)
        else:
            assert all(word in said for word in expected[0]) and not any(word in said for word in expected[1]), \
                (row, said)
        if tag:
            tags.setdefault(tag, set()).add(said)
    assert sorted(tags) == ["fault", "job3", "run-log"] and all(len(said) == 1 for said in tags.values()), tags
    # a node's batch gaps and the batch.log lines that say why (2026-10-26: galley's jars and oven were "Pixal3D made
    # no model" and only batch.log said why), and the prepared batch's takes that may not stand, from the same home
    import score.store
    made = tmp_path / "door" / "pixal-output"
    made.mkdir()
    (made / "batch-gaps.json").write_text(json.dumps({"gaps": [
        {"name": "jars: Pixal3D made no model", "check": "takes", "faults": ["jars: no galley_jars.glb"]}]}))
    (made / "batch.log").write_text("[cloud] renting 2 cards\n[cloud] gaps (ran once or never sent, no model; a new "
                                    "batch and a new ask to try again): galley_jars: out of memory\n")
    (made / "takes.json").write_text("{}")
    output = score.store.Store.in_folder(home / "store").put_tree(made)  # stored in the door home's own store
    take = {"place": "street", "rows": ["street_lamp"], "route": "model", "size": [0.3, 0.3, 6], "inputs": [],
            "status": "bought", "prediction": {"outcome": "predicted gap", "mode": "close-up: every rod failed"}}
    (home / "work/checks/prepare").mkdir(parents=True)
    (home / "work/checks/prepare/remake.json").write_text(json.dumps({"takes": [
        take, {**take, "rows": ["bench"], "prediction": {"outcome": "pass", "mode": None}},
        {**take, "rows": ["sign"], "status": "input gap", "inputs": ["no box or size"],
         "prediction": {"outcome": "pass", "mode": None}}]}))
    printed = {}
    for words in (["gaps", "pixal@galley"], ["predicted"]):  # each as the door runs it, over the one home
        argv, _ = agent_door.decide(words, False)
        said = io.StringIO()
        with pytest.MonkeyPatch.context() as patched, contextlib.redirect_stdout(said):
            patched.setattr(score.store, "PROPS_HOME", home)
            # the accept is the runner's or the owner's to write; the node stands accepted on the stored output
            patched.setattr(score.store.Store, "accepted",
                            lambda self, node: output if node == "pixal@galley" else None)
            patched.setattr(sys, "argv", argv[:1] + argv[2:])
            exec(argv[1], {})
        printed[words[0]] = said.getvalue().splitlines()
    lines = printed["gaps"]
    assert f"accepted output {output}, 1 batch gaps" in lines[0], lines
    assert lines[1].startswith("jars: Pixal3D made no model | takes |"), lines
    assert lines[2:] == ["batch.log: [cloud] gaps (ran once or never sent, no model; a new batch and a new ask to try "
                         "again): galley_jars: out of memory"], lines
    lines = printed["predicted"]
    assert "3 takes, 2 predicted gap" in lines[0] and len(lines) == 3, lines  # the passing bench is left out
    assert lines[1] == "street | street_lamp | model | [0.3, 0.3, 6] | predicted gap | close-up: every rod failed"
    assert lines[2].endswith("| input gap | no box or size"), lines
    seen = agent_door.processes(5).splitlines()  # the busiest processes, read only (2026-11-06)
    assert seen[0].startswith("pid %cpu") and 1 < len(seen) <= 6

    # a run's process tells where it is: SIGUSR1, its stacks to its dump file (2026-11-06: bake calls spun unseen);
    # one with no SIGUSR1 handler is refused and lives on (2026-11-06: the verb ended a score run)
    copy = home / "frozen" / "20261106-050000-1"
    copy.mkdir(parents=True)
    spin = subprocess.Popen([sys.executable, "-c", f"import sys, time; sys.path.insert(0, {str(REPO / 'tools/cloud')!r}); "
                             "import batch; batch.stop_on_signals()\n"  # armed once inside: no stack read before
                             "def hashing_inputs():\n    print('armed', flush=True)\n    time.sleep(30)\n"
                             "hashing_inputs()", str(copy)],
                            env={**os.environ, "PROPS_HOME": str(home)}, stdout=subprocess.PIPE, text=True)
    bare = subprocess.Popen([sys.executable, "-c", "import time; print('up', flush=True); time.sleep(30)", str(copy)],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert spin.stdout.readline().strip() == "armed" and bare.stdout.readline().strip() == "up"
        assert "hashing_inputs" in agent_door.stack(spin.pid, home, wait=1.0)
        with pytest.raises(agent_door.Refused):
            agent_door.stack(os.getpid(), home)  # no run's process
        with pytest.raises(agent_door.Refused, match="does not catch SIGUSR1"):
            agent_door.stack(bare.pid, home, wait=0.2)
        assert bare.poll() is None
    finally:
        for process in (spin, bare):
            process.kill()
            process.wait()

    for options, accepted in BUY_OPTION_ROWS:
        assert bool(agent_door.buy_options(options)) is accepted, options
    with pytest.raises(agent_door.Refused) as gaps:  # cluster-check names every gap
        agent_door.cluster_check({"PATH": "", "SCORE_K8S_KUBECONFIG": str(tmp_path / "none")}, kubectl="")
    for word in ("SCORE_K8S_CONTEXT", "SCORE_K8S_PROVIDER", "no kubectl", "no kubeconfig"):
        assert word in str(gaps.value), gaps.value
    executable(tmp_path / "k8s" / "kubectl", "#!/bin/sh\necho namespace/score-jobs\n")
    config = tmp_path / "k8s" / "kubeconfig"
    config.write_text("{}")
    box = {"SCORE_K8S_PROVIDER": "scaleway/tenant", "SCORE_K8S_CONTEXT": "c", "SCORE_K8S_CLUSTER": "k",
           "SCORE_K8S_PROJECT": "p", "SCORE_K8S_KUBECONFIG": str(config), "PATH": str(tmp_path / "k8s")}
    # the tenant module's status (its scw reads, which the cost watch makes) is part of the check
    for printed, want in (("print('pools ok')", "pools ok"), ("import sys; sys.exit('scw: 403 forbidden')", REFUSED)):
        if want == REFUSED:
            with pytest.raises(agent_door.Refused, match="status failed.*403"):
                agent_door.tenant_status({}, [sys.executable, "-c", printed])
        else:
            assert agent_door.tenant_status({}, [sys.executable, "-c", printed]) == want
    monkeypatch.setattr(agent_door, "tenant_status", lambda environment: "tenant: 2 class pools")
    assert agent_door.cluster_check(box) == (f"the tenant cluster answers: namespace/score-jobs through {config}\n"
                                             "tenant: 2 class pools")
    for yes, options, cluster, printed, starts, log_name, ends in BUY_ROWS:
        with pytest.MonkeyPatch.context() as patched:
            for name, value in box.items():
                if cluster == "box":
                    patched.setenv(name, value)
                elif cluster == "none" and name.startswith("SCORE_K8S"):
                    patched.delenv(name, raising=False)
            command = [sys.executable, "-c", f"import time\n{printed}"]
            if starts is None:
                with pytest.raises(agent_door.Refused, match=ends):
                    agent_door.buy_started(yes, home, command, **options)
                continue
            started = time.monotonic()
            said = agent_door.buy_started(yes, home, command, **options)
        assert time.monotonic() - started < 2, (yes, options)  # never held for the Buy's own time
        log = re.search(r"result in (\S+) \(the door's buy-log\)$", said).group(1)
        assert said.startswith(starts) and log.endswith(f"-{log_name}"), said
        assert soon(lambda: pathlib.Path(log).read_text().endswith(ends)), (said, pathlib.Path(log).read_text())
    assert agent_door.buy_log(home).endswith(BUY_ROWS[-1][-1])  # the newest Buy's log


    # after the move (machine.json), every boot syncs the prop environment the rows' PROPS_PYTHON runs in
    (mountpoint / "machine.json").write_text("{}")
    again, calls_again = run_boot(short_path / "first", root, shims)
    assert again.returncode == 0, again.stderr
    assert f"uv sync -q --frozen --no-dev --project {checkout}" in calls_again
    # and installs the sync's units with the update before each pass, the checkout moved to the pin first
    install = f"python -m score.dashboard install-sync --env-file {env_file} --no-pull"
    assert calls_again.index("systemctl --user start score-update.service") < calls_again.index(install)
    assert calls_again.count("mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test") == 1
    assert (root / "etc" / "fstab").read_text().count("UUID=1111-uuid") == 1

    # ---- the checkout (update.py): every CASES moment of the booted conductor, its checkout now a clone of an
    # origin, its data volume the home, score_lib beside the checkout, its sync unit the one installed above
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    (short_path / "update").mkdir()
    with checkout_world(short_path / "update", booted_home) as world:
        commits, world.rendered_sync = world.commits, rendered_sync
        assert world.sync_unit == sync_units[0] and world.home == mountpoint and world.checkout == checkout
        with pytest.raises(agent_door.Refused, match="two full shas"):
            agent_door.decide(["release-pin", commits["a"][:12], commits["lock1"]], False)
        argv, _ = agent_door.decide(["release-pin", commits["a"], commits["lock1"]], False)
        assert argv[1:] == [agent_door.RELEASE_PIN, commits["a"], commits["lock1"]], argv
        places = {"home": world.home, "checkout": world.checkout}
        for row in CASES:
            stands(world, row)
            line = moved(world, row)
            said = f"{row['name']}: {line}"
            assert git(world.checkout, "rev-parse", "HEAD") == commits[row["head"]], said
            assert all(words in line for words in row["has"]), said
            assert not any(words in line for words in row["lacks"]) and line.endswith(row["ends"]), said
            asked = [[word.format(**places) for word in call] for call in row["uv"]]
            uv_calls = world.uv_log.read_text().splitlines() if world.uv_log.exists() else []
            assert [call.split() for call in uv_calls] == asked, said
            assert (world.boot_log.read_text().split() if world.boot_log.exists() else []) == list(row["boot"]), said
            noted = json.loads((world.home / "conductor" / "pin.json").read_text())
            # the health record says why a checkout lags: the update's own line (the door's adds its note before it)
            assert (line.endswith(f"; {noted['said']}") if row["release"] else noted["said"] == line), (said, noted)
            want = row["noted"] if row["noted"] in (ABSENT, None) else commits[row["noted"]]
            assert noted.get("pin", ABSENT) == want and (want == ABSENT or noted["at"]), (said, noted)
            if row["email"]:
                assert git(world.library, "config", "user.email") == row["email"], said
                assert row["library"] != "none" or git(world.library, "config", "user.name") == "SCORE conductor"
        # Claude Code already at its pin is not installed again.
        cli = executable(world.folder / "claude-cli", '#!/bin/sh\necho "9.9.9 (Claude Code)"\n')
        git(world.checkout, "checkout", "-q", "-f", "--detach", commits["claude"])
        world.boot_log.unlink(missing_ok=True)
        assert update.claude_installed(world.checkout, cli) == "" and not world.boot_log.exists()
        # Two updates take turns on the checkout's lock.
        called = []
        with pytest.MonkeyPatch.context() as patched:
            patched.setattr(update, "update", lambda repo, url: called.append(repo) or "update: at test")
            with open(world.checkout / ".git" / "score-update.lock", "w") as held:
                fcntl.flock(held, fcntl.LOCK_EX)
                second = threading.Thread(target=update.main, args=(["--repo", str(world.checkout)],))
                second.start()
                second.join(0.5)
                assert second.is_alive() and not called
            second.join(5)
        assert called == [world.checkout.resolve()]



# ==== boot ==========================================================================================================

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
# Claude Code at its pin in user score's ~/.local/lib/claude-code: its version, and asked, whether the login reached
# it in CLAUDE_CODE_OAUTH_TOKEN with no API key beside it.
LOGIN = "sk-ant-oat01-" + "q" * 40
CLAUDE_CLI = ("#!/bin/sh\n[ \"$1\" = --version ] && echo '2.1.318 (Claude Code)' && exit 0\ncat > /dev/null\n"
              "seen=false; [ \"$CLAUDE_CODE_OAUTH_TOKEN\" = %s ] && seen=true\n"
              "[ -z \"$ANTHROPIC_API_KEY\" ] || seen=false\nprintf '{\"type\":\"result\",\"is_error\":false,"
              "\"structured_output\":{\"login\":%%s,\"model\":\"%%s\"}}\\n' \"$seen\" \"$3\"\n" % LOGIN)
SHIMMED = ("apt-get", "id", "useradd", "loginctl", "blkid", "mkfs.ext4", "mountpoint", "mount", "resize2fs", "chown",
           "systemctl", "runuser", "git", "curl", "chattr", "npx", "npm")


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
        executable(bin_folder / "kubectl", "#!/bin/sh\necho 'Client Version: v1.37.1'\n")
        executable(bin_folder / "node", "#!/bin/sh\necho v24.21.0\n")
        executable(root / "home" / "score" / ".local" / "lib" / "claude-code" / "bin" / "claude", CLAUDE_CLI)
        (root / "opt" / "google-cloud-sdk").mkdir(parents=True)
        (root / "opt" / "google-cloud-sdk" / "VERSION").write_text("588.0.0")
    home = root / "home" / "score"
    checkout = home / "projects" / "score"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "tools").symlink_to(REPO / "tools")
    executable(checkout / ".venv" / "bin" / "python", SHIM)
    (home / ".config" / "score").mkdir(parents=True)
    (home / ".config" / "score" / "dashboard.env").write_text("SCORE_SYNC_URL=http://cockpit.test\n")
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


def no_bus(root, shims):
    (root / "run" / "dbus" / "system_bus_socket").unlink()


def failing_chattr(root, shims):
    executable(shims / "chattr", "#!/bin/sh\nexit 3\n")


# Each boot of boot.sh against its own temp root: (name, also its folder, kept short for the bus socket; the pinned
# tools already there; a change to the root or its shims; the parts run, None: those the rendered score-boot.service
# runs; the words its stderr stops with (None: it
# boots); calls it never makes (by prefix; "": none at all); files it leaves executable; files it never installs).
BIN = ("usr", "local", "bin")
BOOT_ROWS = [
    ("first", True, None, None, None, ("curl", "npm install"),
     ("score-secret-reader", "score-agent-door"), ()),
    ("unpinned", False, None, ("system", "user"), r"does not match its pinned SHA-256",
     ("runuser",), (), ("restic",)),
    ("busless", True, no_bus, ("system",), r"no system bus", ("",), (), ()),
    ("failing", True, failing_chattr, ("system",), r"boot: stopped at boot.sh line \d+, exit 3: chattr",
     ("mount ",), (), ()),
]


# ==== the health record errs on busy ================================================================================

@pytest.fixture
def no_metadata(monkeypatch):
    """No network: the instance's metadata service is off Scaleway here."""
    monkeypatch.setattr(health_push, "commercial_type", lambda: None)


def busy_home(home):
    """A home with a claim whose pid lives and one whose pid is gone, a parked machine, three frozen copies (one a
    waiting-for-size run's own), a hold whose holder is gone and the health file; the copies a process will work in."""
    (home / "runs").mkdir(parents=True, exist_ok=True)
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
    return ("run-a", "run-waiting")


def unreadable_home(home):
    """A home whose claims file does not parse."""
    (home / "runs").mkdir(parents=True, exist_ok=True)
    (home / "runs" / "active.json").write_text('{"123": ')
    return ()


# Each state of the boot's data volume the health record reads, in order, each built on the one before: (name, its builder, whether a live process holds its film-preview lock while it
# is read, what the record counts as (active_runs, parked, frozen, working, health) or the error it raises). The busy
# home's run-a has a process in it; the waiting run's copy waits for the grow itself; the left-behind one is idle.
HEALTH_ROWS = [
    ("the boot's fresh data volume is idle", lambda home: (), False, (0, 0, 0, 0, None)),
    ("busy home counts live claims, parked, frozen in use and holds", busy_home, True, (1, 1, 1, 1, {"disk": 12})),
    ("unreadable claims file is never idle", unreadable_home, False, ValueError),
]


# The secrets project's account, as the secret reader's scw sees it (run as `python -I` with the call's words): its
# projects, and the vault VAULT ({name: value}; a value of None fails every read of that secret), each call written
# to VAULT_LOG.
VAULT_SCW = r"""import base64, json, os, sys
words = sys.argv[1:]
with open(os.environ["VAULT_LOG"], "a") as log:
    log.write(" ".join(words) + "\n")
with open(os.environ["VAULT"]) as held:
    vault = json.load(held)
named = dict(word.split("=", 1) for word in words if "=" in word)
secret = named.get("name", named.get("secret-name"))
if words[:2] == ["account", "project"]:
    print(json.dumps([{"name": "other", "id": "p-0"}, {"name": "secrets-here", "id": "p-1"}]))
elif secret in vault and vault[secret] is None:
    sys.exit(f"scw: reading {secret} failed")
elif words[:2] == ["secret", "secret"]:
    print(json.dumps([{"name": secret, "id": "s-" + secret}] if secret in vault else []))
elif secret not in vault:
    sys.exit(f"scw: no secret {secret}")
else:
    print(json.dumps({"data": base64.b64encode(vault[secret].encode()).decode()}))
"""
# The secrets every vault holds, and the optional ones secrets.sh writes when the vault has them.
HELD = ("score-lib-deploy-key", "gemini-api-key", door_service.TOKEN_SECRET)
OPTIONAL = ("google-billing-reader", "score-k8s-kubeconfig", "score-k8s-settings")


# ==== the checkout moves only when safe =============================================================================

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.org", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
TOKEN = "t" * 40
HOSTED = "hosted"  # a cockpit that pins nothing yet (its mode, no commit)
ABSENT = "absent"  # pin.json holds no pin: the update stopped before it read one
RUN = b"/x/.venv/bin/python\0-m\0score\0run\0world1\0"
SYNC_PASS = b"/x/.venv/bin/python\0-m\0score.dashboard\0sync\0"
RENDERED = "rendered"  # the sync unit as timer.unit_text renders it for the boot's checkout
DASHBOARD_SYNC = ["sync", "-q", "--frozen", "--group", "dashboard"]
PROPS_SYNC = ["{home}/env", "sync", "-q", "--frozen", "--no-dev", "--project", "{checkout}"]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def commit(repo, name, text):
    path = pathlib.Path(repo) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@contextlib.contextmanager
def cockpit(answer):
    """A local cockpit, its base URL: /api/sync/pin with the token answers what `answer` (a dict, changed between
    calls) holds, anything else the hosting proxy's own /healthz body or 401, as the proxy and the token check do."""
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
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


def origin_commits(origin, boot_log):
    """Main's commits by name (uv.lock, a.txt, uv.lock, boot.sh, a unit, b.txt, boot.sh pinning Claude Code 9.9.9)
    and `side`, one commit on a branch off main."""
    git(origin, "init", "-q", "-b", "main")
    boot = "tools/cloud/conductor/boot.sh"
    commits = {"lock1": commit(origin, "uv.lock", "one"), "a": commit(origin, "a.txt", "two"),
               "lock3": commit(origin, "uv.lock", "three"),
               "boot": commit(origin, boot, f'echo "$1" >> {boot_log}\n'),
               "unit": commit(origin, "tools/cloud/conductor/units/score-sweep.timer", "[Timer]\n"),
               "b": commit(origin, "b.txt", "not a unit"),
               "claude": commit(origin, boot, f'CLAUDE_PIN="@anthropic-ai/claude-code@9.9.9"\necho "$1" >> {boot_log}\n')}
    git(origin, "checkout", "-q", "-b", "side")
    commits["side"] = commit(origin, "c.txt", "off main")
    git(origin, "checkout", "-q", "main")
    return commits


def case(name, start, pin, *, head=None, has=(), lacks=(), ends="", uv=(), boot=(), noted="pin", token=TOKEN,
         release=None, home=(), processes=(), registry=None, sync_unit=None, dirty=False, library=None, email=None):
    """One moment of the conductor's checkout: where it stands (`start`), what the cockpit pins (`pin`, a commit's
    name or HOSTED), what lives beside it (`home` files, `processes` {pid: (command line, "frozen" or "checkout")},
    a `registry` entry (gauges, fresh) for the frozen copy, the installed `sync_unit`, uncommitted changes, score_lib's
    `library` identity: "none" or an email), whether the door's release-pin brings it (`release`: (commit, replaced));
    then what the update leaves: the commit it stands at (`head`, default `start`), words the line has, lacks and ends
    with, the uv and boot.sh calls made, the pin noted for the Machine card (default the pin read) and score_lib's
    email."""
    if noted == "pin":
        noted = None if pin == HOSTED else pin
    return dict(name=name, start=start, pin=pin, head=head or start, has=has, lacks=lacks, ends=ends, uv=uv, boot=boot,
                noted=noted, token=token, release=release, home=home, processes=dict(processes), registry=registry,
                sync_unit=sync_unit, dirty=dirty, library=library, email=email)


IN_FROZEN = {5151: (RUN, "frozen")}
CASES = [
    # A release's commit, noted through the door's release-pin, is followed while the cockpit still pins the commit
    # it replaced (the door runs released code before the host has built); a pin that moved on is followed again.
    case("release-followed-before-the-host-builds", "lock1", "lock1", head="a", release=("a", "lock1"),
         has=("release-pin: ", "the release's commit"), noted="a"),
    case("release-passed-by-a-pin-that-moved-on", "a", "lock3", release=("a", "lock1"), head="lock3",
         has=(".venv synced",), uv=(DASHBOARD_SYNC,)),
    case("a-pin-reached-moves-and-syncs-nothing", "a", "a", has=("update: at ",)),
    # A move that changes units/ installs them (2026-10-31: the disk sweep's own timer waited for a boot); the pinned
    # Claude Code is installed by a move when it is not there (owner, 2026-11-05).
    case("units-changed-installed", "lock3", "unit", head="unit", ends=", the units installed", boot=("units",)),
    case("no-unit-changed-none-installed", "unit", "b", head="b", lacks=("units",)),
    case("claude-code-pinned-installed", "b", "claude", head="claude", has=(", Claude Code 9.9.9 installed",),
         boot=("claude",)),
    # After the move (machine.json), a missing prop environment (left out of every backup) or a lock move syncs it.
    case("before-the-move-no-prop-environment", "lock1", "lock1", lacks=("prop environment",)),
    case("prop-environment-missing-built", "lock1", "lock1", home=("machine.json",),
         has=("update: at ", "the prop environment synced"), uv=(PROPS_SYNC,)),
    case("prop-environment-there-kept", "lock1", "lock1", home=("machine.json", "env/bin/python"),
         lacks=("prop environment",)),
    case("lock-move-syncs-the-prop-environment", "lock1", "lock3", head="lock3", home=("machine.json", "env/bin/python"),
         has=("the prop environment synced",), uv=(DASHBOARD_SYNC, PROPS_SYNC)),
    # A pin off main is refused, an unread pin moves nothing, no pin follows origin/main forward.
    case("pin-off-main-refused", "lock1", "side", has=("refused",)),
    case("unread-pin-moves-nothing", "lock1", "a", token="wrong", noted=ABSENT,
         has=("update: not now, the cockpit's pin could not be read", "401")),
    case("no-pin-follows-main", "lock1", HOSTED, head="claude", has=("origin/main",),
         uv=(DASHBOARD_SYNC,), boot=("units", "claude")),
    # A live run in its frozen copy holds every move; one whose fresh registry entry runs and buys nothing (2026-11-02)
    # holds back only a uv.lock move; a stale entry says nothing of now; score starting from the checkout holds it.
    case("frozen-run-holds-a-lock-move", "lock1", "lock3", processes=IN_FROZEN,
         has=("not now", "pid 5151: /x/.venv/bin/python -m score run world1")),
    case("frozen-run-holds-any-move", "lock1", "a", processes=IN_FROZEN, has=("5151",)),
    case("running-run-holds-a-lock-move", "lock1", "lock3", processes=IN_FROZEN,
         registry=({"running": 1, "buys": 0}, True), has=("not now",)),
    case("running-run-holds-any-move", "lock1", "a", processes=IN_FROZEN, registry=({"running": 1, "buys": 0}, True),
         has=("not now",)),
    case("buying-run-holds-a-lock-move", "lock1", "lock3", processes=IN_FROZEN,
         registry=({"running": 0, "buys": 2}, True), has=("not now",)),
    case("buying-run-holds-any-move", "lock1", "a", processes=IN_FROZEN, registry=({"running": 0, "buys": 2}, True),
         has=("not now",)),
    case("idle-run-holds-a-lock-move", "lock1", "lock3", processes=IN_FROZEN,
         registry=({"running": 0, "buys": 0}, True), has=("not now", "an idle run's copy links .venv")),
    case("idle-run-passed-by", "lock1", "a", head="a", processes=IN_FROZEN, registry=({"running": 0, "buys": 0}, True),
         has=("->",)),
    case("stale-idle-entry-holds", "lock1", "a", processes=IN_FROZEN, registry=({"running": 0, "buys": 0}, False),
         has=("5151",)),
    case("score-starting-from-the-checkout-holds", "lock1", HOSTED, processes={4242: (RUN, "checkout")},
         noted=ABSENT, has=("not now", "4242")),
    # A sync pass holds back only a uv.lock move (2026-10-25); the line names a unit with no update before its pass.
    case("sync-pass-lets-a-move-by", "lock1", "a", head="a", processes={6161: (SYNC_PASS, "checkout")}, has=("->",)),
    case("sync-pass-holds-a-lock-move", "a", "lock3", processes={6161: (SYNC_PASS, "checkout")},
         has=("not now", "6161", "runs no update")),
    case("sync-pass-of-a-unit-updating-first", "a", "lock3", processes={6161: (SYNC_PASS, "checkout")},
         sync_unit=RENDERED, has=("not now", "6161"), lacks=("runs no update",)),
    case("tracked-changes-wait", "lock1", "lock3", dirty=True, noted=ABSENT, has=("tracked changes",)),
    # score_lib's checkout gets the machine's committer when git knows none there, even when nothing moves (2026-10-28).
    case("library-without-identity-given-one", "claude", "claude", library="none",
         has=("given its committer SCORE conductor",), email="conductor@score.invalid"),
    case("library-identity-kept", "claude", "claude", library="owner@example.org", lacks=("committer",),
         email="owner@example.org"),
]


@contextlib.contextmanager
def checkout_world(folder, home):
    """User score's `home` as boot.sh left it, its checkout replaced by a clone of an origin (origin_commits) in
    `folder`, with a uv and a boot.sh logging their calls, a proc folder, the data volume as the update's home, the
    installed sync unit's path, score_lib's place beside the checkout and one cockpit whose answer each case sets."""
    origin = folder / "origin"
    origin.mkdir()
    commits = origin_commits(origin, folder / "boot.log")
    checkout = home / "projects" / "score"
    shutil.rmtree(checkout)
    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True, env={**os.environ, **GIT_ENV})
    uv = executable(folder / "uv", f"#!/bin/sh\necho \"${{UV_PROJECT_ENVIRONMENT:-}} $*\" >> {folder / 'uv.log'}\n")
    answer = {}
    with cockpit(answer) as url:
        yield types.SimpleNamespace(folder=folder, commits=commits, checkout=checkout, uv=uv, url=url, answer=answer,
                                    home=home / ".farm-factory-props", proc=folder / "proc",
                                    sync_unit=home / ".config" / "systemd" / "user" / "score-sync.service",
                                    library=home / "projects" / "score_lib", uv_log=folder / "uv.log",
                                    boot_log=folder / "boot.log")


def stands(world, row):
    """The world set to the row's moment, every trace of the case before wiped."""
    for path in (world.home, world.proc, world.library):
        shutil.rmtree(path, ignore_errors=True)
    for path in (world.uv_log, world.boot_log, world.sync_unit):
        path.unlink(missing_ok=True)
    git(world.checkout, "checkout", "-q", "-f", "--detach", world.commits[row["start"]])
    world.home.mkdir()
    world.proc.mkdir()
    copy = world.home / "frozen" / "abc123"
    copy.mkdir(parents=True)
    for name in row["home"]:
        (world.home / name).parent.mkdir(parents=True, exist_ok=True)
        (world.home / name).write_text("{}")
    for pid, (cmdline, where) in row["processes"].items():
        (world.proc / str(pid)).mkdir()
        (world.proc / str(pid) / "cmdline").write_bytes(cmdline)
        (world.proc / str(pid) / "cwd").symlink_to(copy if where == "frozen" else world.checkout)
    if row["registry"]:
        gauges, fresh = row["registry"]
        entry = world.home / "runs" / "r1.json"
        entry.parent.mkdir()
        entry.write_text(json.dumps({"state": "running", "worktree": str(copy), **gauges}))
        if not fresh:  # an entry not noted lately says nothing of what its run does now
            old = time.time() - update.IDLE_FRESH - 60
            os.utime(entry, (old, old))
    if row["sync_unit"]:
        rendered = world.rendered_sync if row["sync_unit"] == RENDERED else row["sync_unit"]
        world.sync_unit.write_text(rendered)
    if row["dirty"]:
        (world.checkout / "uv.lock").write_text("edited")
    if row["library"]:
        subprocess.run(["git", "init", "-q", str(world.library)], check=True)
        if row["library"] != "none":
            git(world.library, "config", "user.email", row["library"])
    world.answer.clear()
    world.answer.update({"ok": True, "mode": "hosted"} if row["pin"] == HOSTED else
                        {"ok": True, "commit": world.commits[row["pin"]]})


def moved(world, row):
    """The update's line: score-update's own call, or the door's release-pin running it."""
    import agent_door

    def move():
        return update.update(world.checkout, world.url, uv=str(world.uv), proc=world.proc, token=lambda: row["token"],
                             home=world.home, sync_unit=world.sync_unit)
    if not row["release"]:
        return move()
    ran = []

    def update_now(command, **_):
        ran.append(command)
        return types.SimpleNamespace(returncode=0, stdout=move() + "\n", stderr="")
    released, replaced = (world.commits[name] for name in row["release"])
    code, said = agent_door.release_pinned(released, replaced, world.home, run=update_now, values={})
    assert code == 0 and ran and ran[0][-3:] == [str(agent_door.REPO / "tools/cloud/conductor/update.py"), "--repo",
                                                 str(agent_door.REPO)], ran
    return said

