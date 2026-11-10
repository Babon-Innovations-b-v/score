"""Run environment 1's rest on this PC's card (SCORE_CLOUD=local, backends/local.py; owner, 2026-10-27: "couldnt u just
finish the rest of env1 on this gpu aswell", then "yes"): the store pulled from the conductor, a free-only run here
whose machine work runs on this PC's card at EUR 0, the new outputs pushed back so the conductor's sync shows them in
the cockpit.

    python3 tools/cloud/this_pc.py env1        # pull, run world1, push: the one command
    python3 tools/cloud/this_pc.py pull | push | run [<score run arguments>]
    python3 tools/cloud/this_pc.py decide-yes ... | decide <yes id>   # the owner's decisions in chat, below
    python3 tools/cloud/this_pc.py env1 --go <go id>   # a run the owner gave his go: a bought batch, below
    python3 tools/cloud/this_pc.py pause | resume | status   # free this PC (games), pick the run up again, below

Pull and push go through the agents' door (tools/cloud/conductor/agent_door.py, the agents' key
~/.ssh/score_conductor_agents; owner, 2026-10-27: the door route, not his own key on the conductor, agents never get a
shell): its `store-pull` and `store-push` verbs, a tar stream each way through the cluster conductor's door (door_service.py
ask, since 2026-11-08), or over ssh to `--host`.

- **Pull** copies what a run reads (the door's PULLED: the store's objects, the design, the work folder, the Google
  answer cache, score_lib's file cache, the cockpit's locked film scripts and free previews) into HOME, a home of its own (default ~/.score-this-pc): never the PC's old
  home, and never the conductor's keys, ledgers, run registry or frozen copies. It sends the door a manifest of what
  HOME holds, so only new and changed files come down, gzipped as every list it sends the door (2026-11-10: 98 MB
  of plain manifest reset the kubectl port-forward). The prop environment is the PC's (`env` linked), and the
  runner's ssh key here is one of its own, let into this PC's container only.
- **Run** is `score run <environment> --free` under SCORE_CLOUD=local, SCORE_FREE_ONLY=1 and SCORE_INPUTS_DIRECT=1:
  every free row and every paid row whose machine work this PC's card does runs for real; a row that would buy
  anything (a Google ask its cache does not answer, a rented card a kind too big for this card needs) fails, saying
  what, and is left for the Buy.
- **The design brought up to date first** (2026-10-30: the hangar's hand-in still carried plan-footprint sizes for 19
  of its 30 rows, a fix to them reaching a hand-in only when prepare writes it, and prepare ran only in the conductor's
  sync pass): before `run` and `resume` start `score run`, the sync pass's own free steps run here against HOME, free
  only, from the run's code (DESIGN_STEPS: score/dashboard/sync/client.py plans_kept, then remake_prepared): the kept
  plans (a plan row run they start for a changed place is waited out: it holds the store), then prepare's hand-ins. A
  step that fails stops the run. With a run live in HOME they are left as they are (that run reads them). Pull never
  brings the hand-ins down (OWN_DESIGN): it copies every file whose size or mtime differs from HOME's, so the
  conductor's, older or made by other code, would come back over the one written here, under a live run too.
- **Every run here pushes when it ends** (coordinator, 2026-11-02, after a run's outputs sat on this PC unpushed):
  `run` and `env1` push what they made once `score run` ends, whatever its exit, unless given `--no-push "<reason>"`.
  That reason is the run's first log line and is kept in NO_PUSH, so `status` says the newest run kept its outputs
  here and why; a run that pushes clears it. A paused and resumed run is detached and pushes nothing: push it by hand.
- **Push** adds the store's new objects and the work folder's new files (regular files; links stay here) to the
  conductor's: `store-push --missing` names what the conductor lacks, `store-push` adds those, never replacing a file
  that is there: the store is written once by content and key, so the conductor's own outputs stand and a node made
  on both sides keeps the conductor's record. Files land under the conductor's tmp/ first, so its store never lists
  half a file. Then each work/pixal file the conductor holds with other bytes (a take remade here in place) is put in
  place there (`store-push --differs`, then `--replace`, the old one kept under work/pixal/replaced/; 2026-11-03: the
  add-only push left the conductor the old close-ups of every take remade here, and 22 places' palette rows went due).
- **The owner's decisions in chat** (owner, 2026-10-27: "i hate the rule that i cant make discisions in chat
  aswell"): `decide-yes ...` and `decide <yes id>` are the door's verbs of the same name (score/dashboard/sync/
  chat_decisions.py) against HOME's store, so a decision on this run's outputs, or his spend override
  (`decide-yes spend <name> --euros E --purpose P`), or his Google month into HOME's books (`decide-yes google-month
  <YYYY-MM> --euros E`: a rent refused here as "the month's spend is unknown"), or an environment's stop line in HOME
  (`decide-yes stop <environment> --euros E`), is his recorded yes applied through the cockpit's own request
  code, and goes back to the conductor's store with the next push like any new output.
- **His go** (owner, 2026-10-27, his "sure" to: "let a free run you started accept passing results on its own, like a
  bought batch, so the run doesn't stop for clicks"): `decide-yes go world1 <answer> <question>` records it in HOME's
  store, and `env1 --go <go id>` (or `run ... --go <go id>`) tags the run SCORE_OWNERS_GO, so the runner takes it as a
  bought batch for review.IN_BATCH (score.review.web.owners_go checks the go is his); without a go nothing changes.
- **Pause, resume, status** (owner, 2026-10-28: "make it so that you can ez pause and resume using my system, as i do
  wanne be able to play some games at some points"): `pause` records the live run (HOME's run registry: its id,
  arguments, commit, and the SCORE_ variables it ran with, its go and SCORE_MIN_FREE_GB among them) in PAUSED, sends
  its leader SIGTERM (the run passes the stop on and releases; finished outputs stay in the store, an interrupted
  node runs again), waits until its process group is gone, then `docker stop`s the container (not `docker pause`:
  the card's memory and the processor are freed). `resume` refuses while a run is live, starts the container and the
  same run again, detached (its log under HOME/logs), from a worktree of its own at the recorded commit
  (HOME/resume-code). `status` says running, paused or neither, the newest heartbeat's rows, what is on the card,
  each SCORE container's own size and this PC's free disk (a warning under FREE_WARN_GB).
"""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import re
import signal
import shutil
import subprocess
import sys
import tarfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "cloud" / "conductor"))

from agent_door import PULLED, PUSHED, env_file_values, manifest, walked  # noqa: E402

HOME = pathlib.Path(os.environ.get("SCORE_THIS_PC_HOME", pathlib.Path.home() / ".score-this-pc"))
DASHBOARD_ENV = pathlib.Path.home() / ".config" / "score" / "dashboard.env"  # this PC's cockpit's, its SCORE_OWNER
OWNERS_GO = "SCORE_OWNERS_GO"  # score.review.web.OWNERS_GO: the run's go, the owner's recorded in a session
PC_ENV = pathlib.Path.home() / ".farm-factory-props" / "env"  # the prop environment bootstrap.sh builds here
DOOR_SERVICE = pathlib.Path(__file__).resolve().parent / "conductor" / "door_service.py"  # the cluster's door
ENVIRONMENT = {"SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1",
               "SCORE_MAX_MACHINES": "all=1"}  # one machine: this PC
MACHINE = "score-this-pc"  # backends/local.py's first container; each other kind's is MACHINE-<kind>
FREE_WARN_GB = 100  # status warns while this PC's disk has less free
PAUSED = "paused.json"  # under HOME: the paused run, until resume starts it again
RUN_OWN = ("SCORE_FROZEN", "SCORE_FROZEN_OWNER", "SCORE_RUN_ID")  # set by `score run` itself, never carried over
STOP_SECONDS = 240  # a stopped run's 30 s grace, its batches' deletes and the detached wrapper's 90 s, with room
BEAT = re.compile(r"rows done (\d+), running (\d+), queued (\d+)")  # score.graph.heartbeat_line
# The sync pass's free steps that bring the design up to date (score/dashboard/sync/client.py plans_kept, then
# remake_prepared): the plans the plan stage reads, then the hand-ins prepare writes from them.
DESIGN_STEPS = ("score.review.plans_pass", "score.stages.complete.prepare")
OWN_DESIGN = ("design/props/", "design/surfaces/")  # prepare's hand-ins (prop_data.DESIGN, surface_data.DESIGN)
REPLACEABLE = "work/pixal"  # the takes, remade here in place; the one folder a push replaces in (agent_door.REPLACEABLE)
SET_ASIDE = ("work/pixal/retaken/", "work/pixal/replaced/")  # a retake's and a replace's kept old files, never replaced
BLOBS = "store/objects/"  # the store's objects, written once by content and key: one held here is never pulled again
NO_PUSH = "no-push.json"  # under HOME: the newest run here that pushed nothing, with the reason it was given


def door_command(host, key, verb):
    """The command that asks the conductor's agents' door for `verb` (the door decides; no shell): with no `host`, the
    door in the cluster's conductor pod (door_service.py ask, through kubectl port-forward, its token read by name by
    SCORE_SECRET_READER; the conductor runs in the cluster since 2026-11-08 and its old machine is off), else the ssh
    door at `host` with the agents' key."""
    if host is None:
        return [sys.executable, str(DOOR_SERVICE), "ask", verb]
    return ["ssh", "-i", str(pathlib.Path(key).expanduser()), "-o", "IdentitiesOnly=yes", "-o",
            "StrictHostKeyChecking=accept-new", f"score@{host}", verb]


def pull(home, command):
    """Copies PULLED down through the door's store-pull (`command`) into `home`, only what `home` lacks or holds
    changed, never the hand-ins written here (OWN_DESIGN) and never a store object `home` holds already: an object is named
    by its content or key, so the same name is the same bytes, and it is read-only here (2026-11-04: a blob sent again for
    its other mtime stopped the pull on PermissionError); (files, bytes)."""
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(gzip.compress(manifest(home, PULLED).encode()))
    process.stdin.close()
    files, size = 0, 0
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            if member.name.startswith(OWN_DESIGN) or (member.name.startswith(BLOBS) and (home / member.name).exists()):
                continue
            if member.islnk() and not linked_anew(home, member):
                continue
            if not member.isdir():
                cleared(home / member.name)
            archive.extract(member, home, filter="tar")
            files, size = files + 1, size + member.size
    if process.wait():
        raise SystemExit(f"store-pull failed (exit {process.returncode}) after {files} files")
    return files, size


def cleared(path):
    """The file at `path` removed before a pulled one takes its place, never written through: a file here may be a hard
    link to a read-only store blob (2026-11-04: work/motion-scratch's scene.json stopped the pull on PermissionError;
    a writable one would have changed the blob)."""
    if path.is_symlink() or path.is_file():
        path.unlink()


def linked_anew(home, member):
    """Whether the hard link `member` is still to be made in `home`: False when its path is already its target there;
    else its path is cleared first, since a link over a file there falls back to reading its target's data again, which
    the one-pass stream cannot (2026-11-04: `seeking backwards is not allowed`, the pull stopped)."""
    path, target = home / member.name, home / member.linkname
    return not (path.exists() and target.exists() and path.samefile(target))


def push(home, missing_command, push_command):
    """Adds `home`'s regular files under PUSHED that the conductor lacks (the door's store-push --missing, then
    store-push); (files, bytes)."""
    names = [path.relative_to(home).as_posix() for path in walked(home, PUSHED) if not path.is_symlink()]
    asked = subprocess.run(missing_command, input=gzip.compress("".join(f"{name}\n" for name in names).encode()),
                           capture_output=True, check=True).stdout.decode().split()
    process = subprocess.Popen(push_command, stdin=subprocess.PIPE)
    sent = []
    with tarfile.open(fileobj=process.stdin, mode="w|", dereference=True) as archive:
        for name in asked:
            try:  # a live run removes its scratch files meanwhile (work/motion-scratch, 2026-10-28)
                archive.add(home / name, arcname=name, recursive=False)
            except FileNotFoundError:
                continue
            sent.append(archive.getmember(name).size)
    process.stdin.close()
    if process.wait():
        raise SystemExit(f"store-push failed (exit {process.returncode})")
    return len(sent), sum(sent)


def prepared(home):
    """The home made ready for a run: the PC's prop environment linked, the runner's own key for this PC's container,
    and a self-delete key file (a container never deletes itself; batch.py sends the file to every machine)."""
    cloud = home / "cloud"
    cloud.mkdir(parents=True, exist_ok=True)
    if not (home / "env").exists():
        (home / "env").symlink_to(PC_ENV)
    if not (cloud / "ssh_key").exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "score-this-pc", "-f",
                        str(cloud / "ssh_key")], check=True)
    if not (cloud / "self_delete_key.json").exists():
        (cloud / "self_delete_key.json").write_text(json.dumps({"secret_key": "", "for": "this PC: never used"}))
    return home


def run_environment(home, go=None):
    """The environment a run here gets: PROPS_HOME the pulled home, this PC's card, free only, inputs direct, and the
    owner's go when one is named (no go taken from this shell)."""
    found = {**os.environ, **ENVIRONMENT, "PROPS_HOME": str(home)}
    found.pop(OWNERS_GO, None)
    return {**found, **({OWNERS_GO: go} if go else {})}


def go_taken(arguments):
    """(arguments without `--go <go id>`, the go id or None)."""
    if "--go" not in arguments:
        return list(arguments), None
    at = arguments.index("--go")
    if at + 1 >= len(arguments):
        raise SystemExit("--go names the go id decide-yes go printed")
    return [*arguments[:at], *arguments[at + 2:]], arguments[at + 1]


def no_push_taken(arguments):
    """(arguments without `--no-push <reason>`, the reason or None); a `--no-push` with no reason is refused."""
    if "--no-push" not in arguments:
        return list(arguments), None
    at = arguments.index("--no-push")
    reason = arguments[at + 1].strip() if at + 1 < len(arguments) else ""
    if not reason or reason.startswith("--"):
        raise SystemExit('--no-push needs its reason: --no-push "<why this run\'s outputs stay on this PC>"')
    return [*arguments[:at], *arguments[at + 2:]], reason


def push_stated(home, reason, arguments):
    """The run's first line on whether it pushes: with a `reason` it keeps it in NO_PUSH for `status`, without one it
    clears an earlier run's."""
    if reason is None:
        (home / NO_PUSH).unlink(missing_ok=True)
        return "push: what this run makes goes to the conductor when it ends"
    record = {"reason": reason, "argv": list(arguments), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (home / NO_PUSH).write_text(json.dumps(record, indent=1))
    return f"no push: {reason}"


def unpushed(home):
    """'not pushed: <reason> (<argv>, <at>)' for the newest run here that pushed nothing, or None."""
    if not (home / NO_PUSH).exists():
        return None
    record = json.loads((home / NO_PUSH).read_text())
    return f"not pushed: {record['reason']} ({' '.join(record['argv'])}, {record['at']})"


def design_current(home, code, environment):
    """The design brought up to date before a run reads it, as the conductor's sync pass does: DESIGN_STEPS run from
    `code` under `environment` (HOME's, free only), a plan row run the kept plans start waited out; their first
    lines. A step that fails stops the run: a stale hand-in builds the wrong sizes."""
    said = []
    for module in DESIGN_STEPS:
        done = asked([str(REPO / ".venv/bin/python"), "-m", module], cwd=code, env=environment,
                     stdin=subprocess.DEVNULL)
        if done.returncode:
            raise SystemExit(f"{module} failed (exit {done.returncode}): "
                             f"{(done.stderr.strip().splitlines() or ['no output'])[-1]}")
        said.append((done.stdout.strip().splitlines() or [f"{module} wrote nothing"])[0])
        while live_run(home):  # plans keep starts a changed place's plan row as a detached run, holding the store
            time.sleep(5)
    return "; ".join(said)


def run(home, arguments, go=None):
    """`score run` here on this PC's card, tagged with the owner's go when one is named, its design brought up to
    date first unless a run is live in `home`; its exit status."""
    environment = run_environment(prepared(home), go)
    entry = live_run(home)
    print(design_current(home, REPO, environment) if entry is None else
          f"the design left as it is: run {entry['id']} is live and reads it", flush=True)
    command = [str(REPO / ".venv/bin/python"), "-m", "score", "run", *arguments]
    if "--free" not in command:
        command.append("--free")
    return subprocess.run(command, cwd=REPO, env=environment).returncode


def file_sha(path):
    """The sha256 of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_changed(home, differs_command, replace_command):
    """Puts in place on the conductor every regular file of `home`'s work/pixal (not its retaken/ or replaced/) that
    the conductor holds with other bytes: the door's store-push --differs names them, --replace takes them; (files,
    bytes)."""
    lines = []
    for path in walked(home, (REPLACEABLE,)):
        name = path.relative_to(home).as_posix()
        if path.is_symlink() or not path.is_file() or name.startswith(SET_ASIDE):
            continue
        lines.append(f"{path.stat().st_size}\t{file_sha(path)}\t{name}\n")
    asked = subprocess.run(differs_command, input=gzip.compress("".join(lines).encode()), capture_output=True,
                           check=True).stdout.decode().split()
    if not asked:
        return 0, 0
    process = subprocess.Popen(replace_command, stdin=subprocess.PIPE)
    size = 0
    with tarfile.open(fileobj=process.stdin, mode="w|", dereference=True) as archive:
        for name in asked:
            archive.add(home / name, arcname=name, recursive=False)
            size += (home / name).stat().st_size
    process.stdin.close()
    if process.wait():
        raise SystemExit(f"store-push --replace failed (exit {process.returncode})")
    return len(asked), size


def deciding(home, verb, arguments):
    """`python -m score.dashboard decide-yes|decide ...` against `home`'s store, the owner named as this PC's
    cockpit names him; its exit status."""
    owner = os.environ.get("SCORE_OWNER") or env_file_values(DASHBOARD_ENV).get("SCORE_OWNER", "")
    environment = {**run_environment(home), "SCORE_OWNER": owner}
    return subprocess.run([str(REPO / ".venv/bin/python"), "-m", "score.dashboard", verb, *arguments], cwd=REPO,
                          env=environment).returncode


def asked(command, **given):
    """One tool call (docker, nvidia-smi, git); its CompletedProcess, output as text, never raising on its exit."""
    return subprocess.run(command, capture_output=True, text=True, check=False, **given)


def alive(pid):
    """True while `pid` is a live `score` process (a reused pid is another program's)."""
    try:
        return b"score" in pathlib.Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False


def group_alive(leader):
    """True while any process of `leader`'s process group lives (`score run` leads one of its own); a zombie, ended
    and not yet reaped by its parent, holds nothing."""
    for stat in pathlib.Path("/proc").glob("[0-9]*/stat"):
        try:
            state, _parent, group = stat.read_text().rsplit(")", 1)[1].split()[:3]
        except (OSError, IndexError, ValueError):
            continue  # gone meanwhile
        if int(group) == leader and state != "Z":
            return True
    return False


def live_run(home):
    """The registry entry of `home`'s live `score run` (state running, its leader alive), or None."""
    for path in sorted((home / "runs").glob("*.json"), reverse=True):
        if path.name == "active.json":
            continue
        entry = json.loads(path.read_text())
        if entry.get("state") == "running" and alive(entry.get("pid", 0)):
            return entry
    return None


def run_variables(pid):
    """The SCORE_ variables process `pid` runs with, less those `score run` sets itself."""
    pairs = (line.split("=", 1) for line in pathlib.Path(f"/proc/{pid}/environ").read_text().split("\0") if "=" in line)
    return {key: value for key, value in pairs if key.startswith("SCORE_") and key not in RUN_OWN}


def run_log(pid):
    """The file `pid` writes its output to, or None (a terminal, a pipe)."""
    target = pathlib.Path(os.path.realpath(f"/proc/{pid}/fd/1"))
    return str(target) if target.is_file() else None


def pause(home):
    """Stop the live run cleanly and record it in PAUSED, then stop the containers once the run's processes are gone;
    one line."""
    entry = live_run(home)
    if entry is None:
        stop_containers()
        held = " (the paused run stays recorded)" if (home / PAUSED).exists() else ""
        return f"paused: no run was live; {MACHINE} stopped{held}"
    leader = entry["pid"]
    record = {"id": entry["id"], "argv": entry["argv"], "commit": entry.get("commit"),
              "env": run_variables(leader), "log": run_log(leader), "paused": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (home / PAUSED).write_text(json.dumps(record, indent=1))
    os.kill(leader, signal.SIGTERM)
    deadline = time.monotonic() + STOP_SECONDS
    while group_alive(leader):
        if time.monotonic() > deadline:
            raise SystemExit(f"pause: run {entry['id']} (pid {leader}) still has processes after {STOP_SECONDS} s; "
                             f"the container is left running")
        time.sleep(0.5)
    stop_containers()
    return f"paused run {entry['id']} ({' '.join(entry['argv'])}); {MACHINE} stopped, {card()}"


def stop_containers():
    """`docker stop` every SCORE container on this PC: MACHINE and each kind's own (MACHINE-<kind>, PRD #73)."""
    listed = asked(["docker", "ps", "--format", "{{.Names}}"])
    names = [name for name in listed.stdout.split() if name == MACHINE or name.startswith(f"{MACHINE}-")]
    asked(["docker", "stop", *(names or [MACHINE])])


def resume(home):
    """Start the container and the paused run again, detached, at its recorded commit, its design brought up to date
    by that commit's code first; one line."""
    entry = live_run(home)
    if entry is not None:
        raise SystemExit(f"resume: refused, run {entry['id']} is live (pid {entry['pid']})")
    if not (home / PAUSED).exists():
        raise SystemExit("resume: nothing paused")
    record = json.loads((home / PAUSED).read_text())
    commit = record.get("commit") or ""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit(f"resume: the paused run's commit is {commit!r}, not one commit: start it again by hand")
    asked(["docker", "start", MACHINE])
    code = home / "resume-code"
    if code.exists():
        asked(["git", "-C", str(REPO), "worktree", "remove", "--force", str(code)])
    added = asked(["git", "-C", str(REPO), "worktree", "add", "--detach", "--force", str(code), commit])
    if added.returncode:
        raise SystemExit(f"resume: no worktree at {commit[:12]}: {added.stderr.strip()}")
    (code / ".venv").symlink_to((REPO / ".venv").resolve())
    environment = {**run_environment(prepared(home)), **record["env"]}
    design_current(home, code, environment)
    started = asked([str(REPO / ".venv/bin/python"), "-m", "score", *record["argv"], "--detach"], cwd=code,
                    stdin=subprocess.DEVNULL, env=environment)
    line = re.search(r"^detached: started .*$", started.stdout, re.MULTILINE)
    if started.returncode or not line:
        raise SystemExit(f"resume: the run did not start (exit {started.returncode}): "
                         f"{(started.stdout + started.stderr).strip()[-400:]}")
    (home / PAUSED).unlink()
    return f"resumed {' '.join(record['argv'])} at {commit[:12]}: {line.group(0)}"


def newest_beat(log):
    """'rows done N, running N, waiting N' from the newest heartbeat line in `log`'s last 4 MB, or None."""
    if not log or not pathlib.Path(log).is_file():
        return None
    with open(log, "rb") as handle:
        handle.seek(max(0, handle.seek(0, os.SEEK_END) - 4_000_000))
        found = BEAT.findall(handle.read().decode(errors="replace"))
    return "rows done {}, running {}, waiting {}".format(*found[-1]) if found else None


def card():
    """What is on the card: its memory used, and the container's biggest process when it runs."""
    memory = asked(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
    parts = memory.stdout.split(",")
    used = (f"card {parts[0].strip()} of {parts[1].strip()} MiB used" if memory.returncode == 0 and len(parts) == 2
            else "card unread")
    top = asked(["docker", "top", MACHINE, "-eo", "pid,rss,args"])  # docker top needs the pid column
    if top.returncode:
        return f"{used}, {MACHINE} not running"
    rows = [line.split(None, 2)[1:] for line in top.stdout.splitlines()[1:] if len(line.split(None, 2)) == 3]
    biggest = max(rows, key=lambda row: int(row[0]) if row[0].isdigit() else 0, default=None)
    return f"{used}, {MACHINE}'s top job: {biggest[1][:100] if biggest else 'none'}"


def disk(home):
    """Each SCORE container's own writable layer (docker's size) and this PC's free disk, warned under FREE_WARN_GB
    (2026-11-03: the disk 98% full, 476 GB in the containers' layers)."""
    listed = asked(["docker", "ps", "-a", "--size", "--format", "{{.Names}}\t{{.Size}}"])
    rows = [line.split("\t") for line in listed.stdout.splitlines() if "\t" in line] if listed.returncode == 0 else []
    sizes = ", ".join(f"{name} {size.split(' (')[0]}" for name, size in rows
                      if name == MACHINE or name.startswith(f"{MACHINE}-")) or "no container"
    free = shutil.disk_usage(home).free / 1e9
    warning = f" WARNING: under {FREE_WARN_GB} GB free" if free < FREE_WARN_GB else ""
    return f"containers {sizes}; disk {free:.0f} GB free{warning}"


def status_line(home):
    """One line: running, paused or neither, the newest heartbeat's rows, what is on the card, the containers' sizes
    and the free disk."""
    entry = live_run(home)
    logs = sorted((home / "logs").glob("*.log"), key=lambda path: path.stat().st_mtime)
    if entry is not None:
        state, log = f"running {entry['id']} ({' '.join(entry['argv'])})", run_log(entry["pid"])
    elif (home / PAUSED).exists():
        record = json.loads((home / PAUSED).read_text())
        state, log = f"paused {record['id']} since {record['paused']}", record.get("log")
    else:
        state, log = "neither running nor paused", None
    beat = newest_beat(log or (str(logs[-1]) if logs else None)) or "no heartbeat yet"
    kept_here = unpushed(home)
    return f"{state}; {beat}; {card()}; {disk(home)}" + (f"; {kept_here}" if kept_here else "")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("env1", "pull", "run", "push", "decide-yes", "decide",
                                                        "pause", "resume", "status"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="run: score run's arguments (default world1), "
                        "--go <go id> and --no-push <reason> among them; decide-yes and decide: the door's verbs' arguments")
    parser.add_argument("--host", help="an ssh door's address (default: the cluster conductor's door)")
    parser.add_argument("--key", default="~/.ssh/score_conductor_agents", help="the agents' ssh key to the door")
    options = parser.parse_args(argv)
    home = prepared(HOME)
    if options.command in ("pause", "resume", "status"):
        print({"pause": pause, "resume": resume, "status": status_line}[options.command](home))
        return 0
    if options.command in ("decide-yes", "decide"):
        return deciding(home, options.command, options.arguments)
    arguments, go = go_taken(options.arguments)
    arguments, reason = no_push_taken(arguments)
    running = options.command in ("env1", "run")
    if running:
        print(push_stated(home, reason, arguments or ["world1"]), flush=True)
    host = None
    if options.command in ("env1", "pull"):
        host = options.host
        files, size = pull(home, door_command(host, options.key, "store-pull"))
        print(f"pulled {files} files ({size / 1e9:.2f} GB) into {home}")
    status = run(home, arguments or ["world1"], go) if running else 0
    if options.command == "push" or (running and reason is None):
        host = host or options.host
        files, size = push(home, door_command(host, options.key, "store-push --missing"),
                           door_command(host, options.key, "store-push"))
        print(f"pushed {files} files ({size / 1e9:.2f} GB)")
        files, size = replace_changed(home, door_command(host, options.key, "store-push --differs"),
                                      door_command(host, options.key, "store-push --replace"))
        print(f"replaced {files} remade takes' files ({size / 1e9:.2f} GB)")
    return status


if __name__ == "__main__":
    sys.exit(main())
