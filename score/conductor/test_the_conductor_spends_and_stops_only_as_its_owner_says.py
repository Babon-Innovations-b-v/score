"""score.conductor's invariant: the conductor spends and stops only as its owner says. It grows only for the owner's
run that asks for more cores than it has (never an agent's, never under the kill switch's latch, never while a run is
live), and for a Buy on the idle size before it prices (its command started again at the boot on the batch size, with
its launch settings; one recorded over two hours before is dropped) and shrinks only after 30 idle minutes with nothing busy (a claim, a waiting run, a parked machine, a frozen copy
in use, a hold); its ask carries the token read by name and only grow or shrink, and a failed ask takes its resize
mark back. Its own bill never enters the batch's spend, and every paid point refuses while the batch project is the
conductor's. Only the owner's process pulls the kill switch, which stops every run (and the processes left in a gone
run's frozen copy), closes the pools before it releases every parked machine, and latches every `score` command free
only; Stop this batch does the same without the latch. A detached run is capped in score-runs.slice at the memory
less 6 GB, a step's own scope inherits it, and off a conductor nothing changes; on the cluster's home it is a Job of
its own beside the conductor's pod, carrying no secret's value, and its health there is read from the pods. Its health names what the Machine card
reads and its log tails carry no secret. The free end-to-end check (`dry`) passes every step in one line. No run
starts under the data disk's floor, the health warns there, and clean-frozen removes only the frozen copies no run
needs and no process works in, never what their homes link to, and nothing while it cannot tell; clean-cache
makes the checkouts' copies links to the stored blobs even with a run live; clean-kept drops only the kept jobs no
current key asks for; `disk` accounts for the whole data disk, store-gc removes only the blobs nothing names and only
with no run live, and the sweep frees room itself, asking the owner only for a bigger disk, priced.

Break that turns it red: in size.decide grow while a run is live (drop the claims/running wait); in size.busy
leave out the commands ask_grow_for recorded (a Buy on the idle size never grows it); in kill.stop_everything
release the parked machines before closing the pools, or drop its `stop_cluster` call (score's cluster Jobs left
running), or pass no `every_box` to cluster_stopper (a cap stop leaves another box's Jobs running), or drop the
`every_box_stops` call (the runner's machines keep billing past the cap), or drop `+ starting_runs(frozen_folder)` (a
starting run goes on past the stop) or `+ checkout_starting(checkout)` (a `score run` starting from the checkout goes
on); or in kill.leftovers read frozen.users only (the two naming a copy by SCORE_FROZEN or command line stay), or drop
its `pid not in passes` (the sync pass is ended); or in kill.starting drop its young or owner test (the old copy's
owner, or the gone copy's unmarked processes, stay; dropping kill.starting itself stays green, as before this fold: the
stop's SIGTERM ends the starting run before the sweep looks); or in conductor.project_refusal drop either name from its
set (a paid point clears under the conductor's project); or in logs drop the secret-shape test (an AIza key reaches the
tails); or in disk.kept drop the registered-run test (a waiting run's copy is removed); or in disk.said_by drop the
ProcessLookupError catch (a process ending mid-read crashes store-evict); or disk.launch_refusal's
`max(FLOOR_GB, round(written_most(runs_folder), 1))` -> `FLOOR_GB` (a run starts on less room than the last one took),
or graph/runs.noted's `min(entry.get("disk_lowest", free), free)` -> `free`, or launch_refusal's `if evicting(...)`
dropped (a run starts while store-evict evicts the blobs it reads, #74), or store_evict's `alone` dropped (a second
store-evict runs beside the first); or in disk.deleted_open 'if not os.readlink(handle).endswith(" (deleted)"):' ->
'if True:' (a deleted file still open is never counted), or in disk.roots
'**({mount: 3} if mount != home.resolve() else {})}' -> '}' (the folders outside the home are never measured); or in
cluster.carried_environment drop the SECRET_NAME test (the sync token's value lands in a drive Job's spec), or drop its READER_NAMES (the drive pod reads no
secret by name: `claude` has no login, env1 2026-11-08); or in score/__main__.py default_jobs drop the cluster
record's jobs (a price on the cluster worked out on the node's cores); or in cluster.pod_view read an unanswered
cluster as no units (a dead cluster shows the conductor fine); or in cluster.pod_log drop `or own_namespace()` (a
home whose record names another namespace reads the logs of `score`'s pods); or in cluster.drive_job write `echo $$`
(Kubernetes hands the shell `echo $`, and a detached run on the cluster waits for a pid that never comes); or in
cluster.drive_job drop the cpu limit (the namespace's default limit of 1 under a request of 8 makes every drive pod
invalid), or drop its cap at drive_room, or raise DEFAULTS past it (a drive pod asking more than the conductor's
node leaves never schedules, every Buy failed 2026-11-10); or in cluster.detach drop the delete on TimeoutError (a Job whose pod never starts keeps making it again);
or in cluster.drive_job let the pods' PROPS_HOME win over the run's (the drive reads the live design, not its frozen
copy, and a sync pass's plan rewrite stops every line mid-run, env1 2026-11-08). On the full data disk: in
disk.collectable_why 'if blob.name in held:' -> 'if False:' (a blob a record names is removed), or in store_gc drop
'if refused:' and its return (blobs removed under a live run); in sweep 'escalated = force or (record is not None and
start < WARN_GB)' -> 'escalated = force' (under the warning line the sweep runs its routine only), or in warning drop
'{last['bigger']}' (the owner is never told the price), or in steps drop the clean-scratch step (a killed make's
work/motion-scratch copies stay, 2026-11-04), or in clean_scratch drop the score_commands refusal (a live `score
plan`'s copies are cleared under it, 2026-11-11); in cache_refusal '    if need:\n        return f"a registered run
needs' -> '    if False:\n        return f"a registered run needs' (the cache is cleared under a waiting run); in
clean_cache 'relinked = relink_checkouts(home, say) if "checkouts" in names else 0.0' -> 'relinked = 0.0' (checkouts
grow while a run walks its rows, 2026-10-27); in offload_pixal 'why = held_whole_why(takes, take, folder, home,
report, written)' -> 'why = None' (a take the library hands back changed is removed), or drop its 'if refused:' and
return (takes freed under a live run); in take_kept_why drop the 'gone' test (the link to nothing crashes the
offload), or in alone 'yield False' -> 'yield True' (a second offload or sweep runs beside the first); in
relinked_or_why '    if not blob.is_file():\n        return "not held in the store"' -> '    if False:\n        return
"not held in the store"' (a take the store lacks is lost), or '    if now - status.st_mtime < YOUNG_SECONDS:' -> '    if
False:' (a take a run is writing is linked), or in relink_pixal 'if laid_by_a_row(path, pixal):' -> 'if False:'
(a people look's take linked, so its row copies a file onto itself: 2026-11-03, SameFileError), or in laid_by_a_row
drop 'or code_built(path, pixal)' (a code build's take linked: 2026-11-05, every pixal row refused on input.png); in
asked_by 'return code == entry["code"] and entry["system"]' -> 'return False and entry["system"]' (the crate's views,
still asked for, are swept), or drop its 'and \\\n            all(input_stands(' (the lamp's views, made from its
old model, stay). The conductor's score_lib checkout (2026-10-28: boot.sh cloned it once and nothing pulled it, so its
pushes could fail non-fast-forward): in score/conductor/library_checkout.py '    if found["changes"] or
found["local_commits"]:' -> '    if False:' (a pull over local commits or changes goes on), or '    fetched = git(root,
"fetch", "-q", "origin")' -> '    fetched = git(root, "status")' (behind reads 0 against a stale origin ref), or in
push_check '    if tried.returncode == 0:' -> '    if True:' (a refused push reads accepted). The free
end-to-end check is red when a step fails, e.g. the memory guard letting the second node start while the first, short
of its stage's peak, still runs.
"""
import datetime
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import conductor  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.conductor import cluster, disk, health, kill, logs, size, slices  # noqa: E402
from score.graph import frozen, runs  # noqa: E402
from score.store import Store, file_hash  # noqa: E402

RECORD = {"name": "conductor", "idle_type": "POP2-HM-2C-16G", "batch_type": "POP2-HM-16C-128G", "idle_cores": 2,
          "batch_cores": 16, "project": "score-conductor"}
IDLE = {"claims": 0, "running": 0, "waiting": 0, "wanted": 0, "parked": 0, "frozen": 0, "working": 0}
SLEEP = [sys.executable, "-c", "import time; time.sleep(60)"]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The conductor's own folder in the test's home."""
    monkeypatch.setattr(conductor, "HOME", tmp_path / "conductor")
    monkeypatch.setattr(conductor, "FREE_ONLY_LATCH", tmp_path / "conductor" / "free-only")
    monkeypatch.setattr(conductor, "RESIZING", tmp_path / "conductor" / "resizing.json")
    return tmp_path


# --- size: grow for the owner's run, shrink when idle ------------------------------------------------------------------

NOW = 10_000_000
WAITING = {**IDLE, "waiting": 1, "wanted": 16}
PASSING = {**IDLE, "passing": 1, "held": ["sync-pass-4242"]}

# size.decide's answers: (row, busy view, cores, idle since, now, latched) -> (action, a word its reason holds or None)
DECIDED = [
    ("grow for a waiting run", WAITING, 2, 0, 100, False, size.GROW, "waits for 16 cores"),
    ("no grow while a claim is live", {**WAITING, "claims": 1}, 2, 0, 100, False, None, "live runs"),
    ("no grow while a run is live", {**WAITING, "running": 1}, 2, 0, 100, False, None, "live runs"),
    ("no grow under the kill switch's latch", WAITING, 2, 0, 100, True, None, "free-only latch"),
    ("no shrink before thirty minutes", IDLE, 16, NOW - 29 * 60, NOW, False, None, "idle 29 of 30"),
    ("shrink after thirty idle minutes", IDLE, 16, NOW - 31 * 60, NOW, False, size.SHRINK, None),
    ("nothing at the idle size", IDLE, 2, 0, NOW, False, None, "idle size"),
    *[(f"no shrink while {busy}", {**IDLE, busy: 1}, 16, 0, NOW, False, None, busy)
      for busy in ("claims", "running", "waiting", "parked", "frozen", "working")],
    # 2026-11-04: sync passes back to back held the clock at 0 all morning; a pass waits the shrink, never the clock
    ("a pass drains the shrink", PASSING, 16, NOW - 31 * 60, NOW, False, size.DRAIN, "sync-pass-4242"),
    ("no drain before thirty minutes", PASSING, 16, NOW - 29 * 60, NOW, False, None, None),
    ("the pass ended: shrink", {**PASSING, "passing": 0, "held": []}, 16, NOW - 31 * 60, NOW, False, size.SHRINK,
     None),
]

# a run asking for size: (conductor's cores or None off one, jobs, --oversubscribe, an agent's) -> (waits' start, a
# Buy's wait's start, the default jobs of a run given none of 8)
ASKED_SIZE = [
    (None, 16, False, False, None, None, 8),  # not a conductor: refused as on the PC
    (2, 16, False, False, "16 jobs on 2 cores: waiting", "2 cores: a Buy prices on the batch size", 2),
    (2, 2, False, False, None, "2 cores: a Buy prices on the batch size", 2),  # fits
    (2, 16, True, False, None, "2 cores: a Buy prices on the batch size", 2),  # --oversubscribe runs as asked
    (2, 16, False, True, None, "2 cores: a Buy prices on the batch size", 2),  # an agent's run never grows it
    (2, 17, False, False, None, "2 cores: a Buy prices on the batch size", 2),  # more than the batch size has
    (16, 16, False, False, None, None, 16),  # at the batch size: fits, and a Buy prices at once
]

# a registered `running` entry with this process's pid, registered at an offset from now (None: when unknown); an
# out-of-memory kill leaves an entry `running`, and a later process given its pid is not the run
ENTRIES = [(datetime.timedelta(seconds=5), True), (-datetime.timedelta(days=400), False), (None, False)]

# --- the machine card: a run's memory cap, the slice's shim, health, logs, the data disk's floor and account --------

GIB = 2 ** 30
# a conductor's memory in GB -> its runs' cap in bytes: the memory less HEADROOM_GB, never below one
CAPS = [(16, 10 * GIB), (128, 122 * GIB), (4, GIB)]
# the drive pod's memory on the cluster's home (#76 step 3): (kept stage peaks, jobs, floor, the record's cap in GB) ->
# bytes asked: the floor beside the largest peaks, one a job, each at least the floor, at most the record's cap
MEMORY_ASKED = [({"a": 10 * GIB, "b": 2 * GIB, "c": 1 * GIB}, 2, 6 * GIB, 64, 22 * GIB),
                ({}, 3, 6 * GIB, 64, 24 * GIB),  # never measured: the floor each
                ({"a": 50 * GIB}, 2, 6 * GIB, 40, 40 * GIB)]
# a process's cgroup line -> whether it runs inside score-runs.slice
CGROUPS = [("0::/user.slice/user@1000.service/app.slice/run-p1.scope", False),
           ("0::/user.slice/user@1000.service/score.slice/score-runs.slice/run-p1.scope", True)]
# systemd-run's words through the shim -> the words the real one is given: --slice-inherit for a user unit without a
# slice of its own
SHIMMED = [(("--user", "--scope", "-q", "-p", "MemoryMax=16G", "nice", "x"),
            "--slice-inherit --user --scope -q -p MemoryMax=16G nice x"),
           (("--user", "--slice=other.slice", "x"), "--user --slice=other.slice x"),
           (("--scope", "x"), "--scope x"),  # not a user unit: left alone
           (("--user", "--", "x", "--slice"), "--slice-inherit --user -- x --slice")]
# the cluster record of the home, its absence or one naming a namespace -> (--jobs given none, the namespace its pods'
# logs are read in): a price on the cluster is worked out on the record's jobs, never the node's cores
RECORDS = [(None, None, "score"), ({"image": "x", "jobs": 12, "namespace": "score-rehearsal"}, 12, "score-rehearsal"),
           ({"image": "registry.example/score-conductor@sha256:0"}, 8, "score")]  # the defaults under an image alone

# systemd's answer for each unit the health reads
SHOWN = {"score-sync.timer": ("active", ""), "score-sync.service": ("inactive", "success"),
         "score-listen.service": ("failed", "exit-code"), "score-resume.service": ("inactive", "success"),
         "score-backup.timer": ("inactive", ""), "score-backup.service": ("inactive", "")}

# the conductor's score_lib checkout, one push behind origin, holding (a local commit, a local change, nothing) -> its
# pull's refusal ("" when it fast-forwards): a fast-forward only pull never moves over local work
LIBRARY_PULLS = [("a local commit", "local.json", True, "0 local changes and 1 local commits"),
                 ("a local change", "index.json", False, "1 local changes and 0 local commits"),
                 ("nothing of its own", None, False, "")]


def properties(unit):
    state, result = SHOWN[unit]
    return {"ActiveState": state, "Result": result,
            "ExecMainExitTimestamp": "@1792656000" if unit == "score-sync.service" else ""}


def test_the_conductor_spends_and_stops_only_as_its_owner_says(home, monkeypatch):
    tmp_path = home
    # the free end-to-end check (`dry`) runs beside the rest and passes every step in one line (red when a step fails,
    # e.g. the memory guard letting the second node start while the first, short of its stage's peak, still runs)
    dry = subprocess.Popen([sys.executable, "-m", "score.conductor", "dry"], cwd=REPO, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
    # the pure answers: a run's memory cap, the drive pod's memory, the size timer's decisions
    for memory, cap in CAPS:  # a detached run is capped in score-runs.slice at the memory less 6 GB
        assert slices.cap_bytes(memory) == cap, memory
    unit = (REPO / "tools/cloud/conductor/units/score-runs.slice").read_text().splitlines()
    percent = int(next(line for line in unit if line.startswith("MemoryMax=")).partition("=")[2].rstrip("%"))
    assert 16 * percent / 100 <= 16 - slices.HEADROOM_GB  # the unit file's cap is within the idle size's
    for peaks, jobs, floor, cap_gb, asked in MEMORY_ASKED:
        assert cluster.memory_request(peaks, jobs, floor, cap_gb) == asked, (peaks, jobs, cap_gb)
    for row, view, cores, idle_since, now, latched, action, word in DECIDED:
        found = size.decide(view, cores, RECORD, idle_since, now, latched)
        assert found[0] == action and (word is None or word in found[1]), (row, found)
    assert not size.is_busy(PASSING)  # a pass is no work that keeps the batch size

    # the home's machine files: the shim is used only inside the slice (this test runs outside it), and adds
    # --slice-inherit there
    for line, inside in CGROUPS:
        (tmp_path / "cgroup").write_text(f"{line}\n")
        assert bool(slices.in_slice(tmp_path / "cgroup")) is inside, line
    kept = os.environ.get("PATH")
    assert not slices.apply_shim() and os.environ.get("PATH") == kept
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "systemd-run").write_text("#!/bin/sh\necho \"$@\"\n")
    (tmp_path / "real" / "systemd-run").chmod(0o755)
    shim_path = f"{slices.SHIM}:{tmp_path / 'real'}:/usr/bin:/bin"
    for words, given in SHIMMED:
        done = subprocess.run(["systemd-run", *words], env={**os.environ, "PATH": shim_path},
                              capture_output=True, text=True, check=True)
        assert done.stdout.strip() == given, words
    # one pod's cgroup: inside a pod the guard reads the pod's memory limit and cores, never the node's; outside a
    # pod nothing changes; with no limit, nothing is read
    pod = tmp_path / "pod"
    pod.mkdir()
    (pod / "memory.max").write_text(f"{8 * GIB}\n")
    (pod / "memory.current").write_text(f"{5 * GIB}\n")
    (pod / "memory.stat").write_text(f"anon 1\ninactive_file {GIB}\n")
    (pod / "cpu.max").write_text("400000 100000\n")
    assert cluster.pod_memory(pod) == (8 * GIB, 4 * GIB) and cluster.cores(pod) == 4
    fake = type("graph", (), {"AVAILABLE": staticmethod(lambda: 100 * GIB),
                              "TOTAL": staticmethod(lambda: 128 * GIB)})
    assert not cluster.guard_pod_memory(fake, pod, environment={}) and fake.AVAILABLE() == 100 * GIB
    assert cluster.guard_pod_memory(fake, pod, environment={"KUBERNETES_SERVICE_HOST": "10.0.0.1"})
    assert (fake.AVAILABLE(), fake.TOTAL()) == (4 * GIB, 8 * GIB)
    (pod / "memory.max").write_text("max\n")
    (pod / "cpu.max").write_text("max 100000\n")
    assert cluster.pod_memory(pod) is None and cluster.cores(pod) is None
    # the home's cluster record sets a run's jobs and the namespace whose pods' logs are read (the 2026-11-07
    # rehearsal); with none, the conductor's own (none here: graph.JOBS) and the default namespace
    from score import __main__ as command, graph
    prefix = slices.scope_prefix("score-run-x")  # a detached run is its own scope in the slice; off a conductor, none
    assert prefix[:3] == ["systemd-run", "--user", "--scope"] and "--slice=score-runs.slice" in prefix
    assert "--unit=score-run-x" in prefix and prefix[-1] == "--"
    assert not slices.usable() and command.run_scope(pathlib.Path("/tmp/score-run-x.log")) == []
    kubectl = []
    for found, jobs, namespace in RECORDS:
        monkeypatch.setattr(cluster, "RECORD", tmp_path / "cluster.json" if found else tmp_path / "no-cluster.json")
        if found:
            (tmp_path / "cluster.json").write_text(json.dumps(found))
        recorded = cluster.record()
        assert (recorded is None) if found is None else (recorded["jobs"], recorded["namespace"]) == (jobs, namespace)
        if found is None:  # off the cluster's home a detached run is no Job
            assert command.detached_as_pod(["true"], tmp_path / "x.log", {}) is False
        assert command.default_jobs() == (jobs or graph.JOBS), found
        tail = cluster.pod_log("score-listen.service", 5, run=lambda argv, **_: kubectl.append(argv) or
                               subprocess.CompletedProcess(argv, 0, "[listen] up\n", ""))
        assert tail == ["[listen] up"] and kubectl[-1][1:7] == [
            "-n", namespace, "logs", "pod/score-conductor-0", "-c", "conductor"], (found, kubectl[-1])
    # On the cluster's home (#76) a detached run is a Job of its own, from its frozen copy, beside the conductor's pod,
    # its command the scope's, no retry, no secret's value in its spec; the pid its pod writes is the run's
    log, applied = tmp_path / "score-run-20261107T2000Z.log", []
    (tmp_path / "score-run-20261107T2000Z.log.pid").write_text("4242\n")
    environment = {"SCORE_FREE_ONLY": "1", "SCORE_SYNC_TOKEN": "s3cret", "SCORE_LIB_KEY": "k", "PATH": "/usr/bin",
                   "KUBERNETES_SERVICE_HOST": "10.0.0.1", "HOME": "/elsewhere",
                   "PROPS_HOME": "/home/score/.farm-factory-props/frozen/abc.home",
                   "SCORE_SECRET_READER": "/usr/local/bin/score-secret-reader", "SCORE_SECRETS_PROJECT": "a-project"}
    name, pid = cluster.detach(recorded, ["/py", "stopped.py", "--", "/py", "-m", "score", "run", "world1"], log,
                               "/home/score/.farm-factory-props/frozen/abc", environment, tmp_path,
                               apply=applied.append, wait=lambda log: cluster.started_pid(log, seconds=1))
    job, = applied
    assert (name, pid) == ("score-run-20261107t2000z", 4242) and job["spec"]["backoffLimit"] == 0
    pod_spec = job["spec"]["template"]["spec"]
    assert pod_spec["restartPolicy"] == "Never" and pod_spec["hostPID"] is True
    assert pod_spec["affinity"]["podAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"][0][
        "topologyKey"] == "kubernetes.io/hostname"
    box, = pod_spec["containers"]
    assert box["command"][-8:] == ["/py", "stopped.py", "--", "/py", "-m", "score", "run", "world1"]
    assert box["workingDir"] == "/home/score/.farm-factory-props/frozen/abc"
    assert box["command"][2].replace("$$", "$").startswith("echo $$ >")  # as Kubernetes expands it: the shell's pid
    carried = {variable["name"]: variable.get("value") for variable in box["env"]}
    assert carried["SCORE_FREE_ONLY"] == "1" and carried["PATH"] == "/usr/bin" and carried["HOME"] == "/home/score"
    assert not {"SCORE_SYNC_TOKEN", "SCORE_LIB_KEY", "KUBERNETES_SERVICE_HOST"} & set(carried)
    assert carried["SCORE_SECRET_READER"] == "/usr/local/bin/score-secret-reader"  # a secret read by name, in the pod
    assert carried["SCORE_SECRETS_PROJECT"] == "a-project"
    assert [variable["name"] for variable in box["env"]].count("HOME") == 1
    # its home is the run's frozen one (its design as it started), never the pods' live home a sync pass rewrites
    assert carried["PROPS_HOME"] == "/home/score/.farm-factory-props/frozen/abc.home"
    assert [variable["name"] for variable in box["env"]].count("PROPS_HOME") == 1
    # its processor limit is its request, so a namespace's default limit never makes the pod invalid
    assert box["resources"]["limits"]["cpu"] == box["resources"]["requests"]["cpu"] == "4000m"
    # DEFAULTS fit the conductor's node beside its own pods and CronJobs, and a record asking more is cut to that room,
    # never a pod that cannot schedule (2026-11-10: 16 x 0.5 CPU and 64 GB on the 8-core node, every Buy failed)
    from tools.cloud.k8s import conductor as pods
    room_cpu, room_memory = pods.drive_room()
    assert pods.NODE_TYPE == "POP2-HM-8C-64G" and 0 < room_cpu < pods.millicores(pods.NODE_ALLOCATABLE["cpu"])
    assert 1000 * cluster.DEFAULTS["jobs"] * cluster.DEFAULTS["cpu_per_job"] <= room_cpu
    assert cluster.DEFAULTS["max_memory_gb"] * cluster.GIB <= room_memory
    assert pods.memory_bytes(box["resources"]["requests"]["memory"]) <= room_memory
    greedy = {**recorded, "jobs": 16, "cpu_per_job": 0.5}
    wants, = cluster.drive_job(greedy, ["true"], log, tmp_path, {}, 64 * cluster.GIB)["spec"]["template"]["spec"][
        "containers"]
    assert pods.millicores(wants["resources"]["requests"]["cpu"]) == room_cpu
    assert pods.memory_bytes(wants["resources"]["requests"]["memory"]) <= room_memory
    with pytest.raises(TimeoutError):
        cluster.started_pid(tmp_path / "never.log", seconds=0.01, sleep=lambda seconds: None)
    deleted = []  # a Job whose pod wrote no pid in time is deleted before the error goes on, never left retrying
    with pytest.raises(TimeoutError):
        cluster.detach(recorded, ["/py", "-m", "score", "run", "world1"], tmp_path / "score-run-stuck.log", tmp_path,
                       {}, tmp_path, apply=applied.append, delete=deleted.append,
                       wait=lambda log: cluster.started_pid(log, seconds=0.01, sleep=lambda seconds: None))
    assert [job["metadata"]["name"] for job in deleted] == ["score-run-stuck"]
    monkeypatch.setattr(cluster, "RECORD", tmp_path / "no-cluster.json")
    # in the cluster's conductor pod (#76 step 5) the units come from the cluster's answer, never systemd, and a
    # cluster that does not answer is every unit failed
    labels = {"app.kubernetes.io/name": "score-conductor"}

    def job(unit_name, stamp, **status):
        return {"kind": "Job", "metadata": {"name": f"{unit_name}-{stamp}", "creationTimestamp": f"2026-11-07T{stamp}Z",
                                            "labels": {**labels, "app.kubernetes.io/component": unit_name}},
                "status": status}
    answer = {"items": [
        {"kind": "Pod", "metadata": {"labels": {**labels, "app.kubernetes.io/component": "conductor"}},
         "status": {"containerStatuses": [{"ready": True}, {"ready": True}]}},
        job("sync", "20:00:00", succeeded=1, completionTime="2026-11-07T20:03:00Z"),
        job("sync", "20:05:00", active=1), job("backup", "20:00:00", failed=1)]}
    seen = cluster.pod_view(answer=answer)
    assert seen["units"] == {"sync": "active", "listen": "active", "resume": "active", "backup": "failed"}
    assert seen["last_sync"] == {"at": "2026-11-07T20:03:00Z", "ok": True}
    with monkeypatch.context() as unanswered:
        unanswered.setattr(cluster, "kubectl_json", lambda *words: None)
        assert set(cluster.pod_view()["units"].values()) == {"failed"}

    def become(cores):
        """This process a conductor of `cores` cores (machine.json and the size function's url), or none at None."""
        if cores is None:
            monkeypatch.delenv(conductor.SIZE_URL, raising=False)
            return
        monkeypatch.setattr(os, "cpu_count", lambda: cores)
        monkeypatch.setenv(conductor.SIZE_URL, "https://size.invalid/")
    (tmp_path / "machine.json").write_text(json.dumps(RECORD))
    monkeypatch.setattr(conductor, "MACHINE", tmp_path / "machine.json")
    monkeypatch.setattr(conductor, "DRAINING", tmp_path / "draining.json")
    for cores_now, jobs, oversubscribe, agent, waits, buy, default in ASKED_SIZE:
        become(cores_now)
        row = (cores_now, jobs, oversubscribe, agent)
        said = size.waits(jobs, oversubscribe, agent=agent)
        assert (said is None) if waits is None else said.startswith(waits), (row, said)
        said = size.buy_waits(None, cores_now)
        assert (said is None) if buy is None else said.startswith(buy), (row, said)
        assert conductor.default_jobs(8) == default, row
    for offset, live in ENTRIES:
        entry = {"pid": os.getpid(), "state": runs.RUNNING}
        if offset is not None:
            at = datetime.datetime.now(datetime.timezone.utc) + offset
            entry["started"] = at.isoformat(timespec="seconds")
        assert size.entry_alive(entry) is live, offset

    # one world: a Buy asks the grow on the idle size before it prices, and starts again at the boot on the batch size
    folders = [tmp_path / name for name in ("runs", "parked", "frozen", "holds", "asked")]
    registered, asked, pokes = folders[0], folders[4], []
    size.ask_grow_for(["buy", "y1", "--phase", "models"], {"SCORE_CLOUD": "k8s"}, tmp_path / "buy.log", 16, asked,
                      lambda: pokes.append(1))
    view = size.busy(*folders)
    assert pokes == [1] and (view["waiting"], view["wanted"]) == (1, 16)
    assert size.decide(view, 2, RECORD, 0, 100, False)[0] == size.GROW
    started, words = [], []
    assert size.started_asked(words.append, asked, cores=2, start=lambda *a, **k: started.append(a)) == 0
    assert not started and size.asked_grows(asked)  # still waits on the idle size
    assert size.started_asked(words.append, asked, cores=16,
                              start=lambda argv, **k: started.append((argv, k["env"]["SCORE_CLOUD"]))) == 1
    assert started == [(["buy", "y1", "--phase", "models"], "k8s")] and not size.asked_grows(asked)
    size.ask_grow_for(["buy", "y2"], {}, tmp_path / "buy.log", 16, asked, lambda: None)
    late = size.asked_grows(asked)[0][1]["at"] + size.ASKED_HOURS * 3600 + 1
    assert size.started_asked(words.append, asked, cores=16, now=late, start=lambda *a, **k: 1 / 0) == 0
    assert not size.asked_grows(asked) and "not started" in words[-1]
    # ...then a claim, a waiting run, a parked machine and a frozen copy in use, and the holds
    for folder in folders[:2]:
        folder.mkdir(exist_ok=True)
    (tmp_path / "frozen" / "live-copy").mkdir(parents=True)
    (tmp_path / "frozen" / "left-over").mkdir()
    runs.claim("c0ffee", ["a@b"], os.getpid(), folder=registered)
    waiting = runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=registered)
    (tmp_path / "parked" / "machine.json").write_text("{}")
    monkeypatch.chdir(tmp_path / "frozen" / "live-copy")
    assert size.busy(*folders) == {"claims": 1, "running": 0, "waiting": 1, "wanted": 16, "parked": 1, "frozen": 1,
                                   "working": 0, "passing": 0, "held": []}
    # 2026-10-25: a shrink cut the first sync pass after a boot. A hold lasts while its process does; a holder killed
    # mid-way holds nothing
    holds = folders[3]
    with conductor.holding("sync-pass", holds), conductor.holding("reading", holds):
        assert conductor.holds(holds) == [f"reading-{os.getpid()}", f"sync-pass-{os.getpid()}"]
        view = size.busy(*folders)
    assert (view["working"], view["passing"]) == (1, 1) and len(view["held"]) == 2, view
    assert conductor.holds(holds) == [] and not list(holds.glob("*.lock"))
    code = (f"import os, sys, pathlib; sys.path.insert(0, {str(REPO)!r}); from score import conductor; "
            f"h = conductor.holding('film-preview', pathlib.Path({str(holds)!r})); h.__enter__(); "
            "print('held', flush=True); os.kill(os.getpid(), 9)")
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip() == "held"
    child.wait()
    assert conductor.holds(holds) == [] and not list(holds.glob("*.lock"))  # the dead holder's file is gone

    # the Machine card on this world. The waiting run notes its disk at its first beat and the lowest since; a run that
    # ran the disk out counts as all it had and the floor more (2026-11-04: checkout 17 began at 10.4 GB free, over
    # the 10 GB floor, and ran out 7 min in)
    runs.noted(waiting, None)
    beat = json.loads(waiting.read_text())
    assert beat["disk_lowest"] == beat["disk_start"] > 0, beat
    waiting.write_text(json.dumps({**beat, "disk_start": 30.0, "disk_lowest": 1.0}))
    runs.noted(waiting, None)
    assert json.loads(waiting.read_text())["disk_lowest"] == 1.0  # the lowest stays the lowest seen
    assert disk.written_most(registered) == 29.0 * disk.WRITTEN_MARGIN
    (registered / "ran-out.json").write_text(json.dumps({"state": "ended", "disk_start": 20.4, "disk_lowest": 0.1}))
    assert disk.written_most(registered) == (20.4 + disk.FLOOR_GB) * disk.WRITTEN_MARGIN
    # its log, a fault, the boot log and the backups in the home; the card's health reads this home's runs, parked
    # machines and holds
    for name in ("logs", "faults"):
        (tmp_path / name).mkdir()
    (tmp_path / "logs" / "score-run-1.log").write_text(
        "brief@north: made\nreading gemini-api-key by name\nsent s3cr3t-sync-value along\n"
        "header X-Auth-Token: abc\nGET /v1beta/models?key=AIzaSyA0123456789abcdefghijklmnopqrstuv\n"
        "token hf_abcdefghijklmnopqrstuvwxyz0123456789\n-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "asked with X-Score-Size-Token set\nexit: ok\n")
    (tmp_path / "faults" / "brief@south.txt").write_text("cause: the brief is empty\n")
    (tmp_path / "score-boot-system.log").write_text("boot: node 24.21.0 installed\nsent s3cr3t-sync-value along\n")
    for stamp, kind, ok in (("0900", "backup", False), ("0930", "backup", True), ("0945", "check-data", False)):
        (tmp_path / "logs" / f"backup-20261022T{stamp}.json").write_text(json.dumps(
            {"at": f"2026-10-22T{stamp[:2]}:{stamp[2:]}:00+00:00", "kind": kind, "ok": ok}))
    monkeypatch.setenv("SCORE_SYNC_TOKEN", "s3cr3t-sync-value")
    for module, name, path in ((health, "BACKUPS", tmp_path / "logs"), (runs, "RUNS", registered),
                               (size, "PARKED", folders[1]), (frozen, "FOLDER", folders[2]),
                               (conductor, "HOLDS", holds), (size, "ASKED", asked)):
        monkeypatch.setattr(module, name, path)
    floor_gb = disk.FLOOR_GB
    with monkeypatch.context() as high:  # the data disk under its floor: the card warns
        high.setattr(disk, "FLOOR_GB", 10 ** 6)
        found = health.read(properties)
    assert set(found) == {"at", "machine", "size", "state", "cores", "memory_total", "memory_available", "memory",
                          "disk_free", "disk", "load", "units", "runs_active", "runs_waiting", "parked_machines",
                          "holds", "last_backup", "backup", "last_sync", "sync", "free_only", "notes", "code"}
    assert (found["machine"], found["runs_active"], found["runs_waiting"], found["parked_machines"], found["holds"]) == (
        "conductor", 1, 1, 1, []), found
    assert found["units"] == {"sync": "active", "listen": "failed", "resume": "inactive", "backup": "inactive"}
    assert found["last_sync"] == {"at": "2026-10-22T08:00:00+00:00", "ok": True}  # @1792656000
    assert found["last_backup"] == found["backup"] == {"at": "2026-10-22T09:30:00+00:00", "ok": True}
    assert found["memory_total"] >= found["memory_available"] > 0 and len(found["load"]) == 3
    assert found["disk"]["total_gb"] >= found["disk"]["free_gb"] == found["disk_free"]
    assert found["disk"]["floor_gb"] == 10 ** 6 and any(note.startswith("disk: ") for note in found["notes"])
    path = health.write(found, tmp_path / "health.json")
    assert json.loads(path.read_text()) == found and not list(tmp_path.glob("*.partial"))
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "google-billing-reader.note").write_text("no google-billing-reader secret\n")
    assert health.notes(tmp_path / "secrets") == ["no google-billing-reader secret"]
    assert health.notes(tmp_path / "x") == []
    assert health.code(pin_path=tmp_path / "none.json")["matches"] is None  # no pin read yet
    (tmp_path / "pin.json").write_text(json.dumps({"at": "2026-10-25T10:00:00+00:00",
                                                   "pin": found["code"]["checkout"][:12]}))
    assert health.code(pin_path=tmp_path / "pin.json")["matches"] is True
    said = "update: not now, 0000 changes uv.lock and a sync pass uses .venv (pid 7)"
    (tmp_path / "pin.json").write_text(json.dumps({"at": "2026-10-25T10:00:00+00:00", "pin": "0" * 40, "said": said}))
    lagging = health.code(pin_path=tmp_path / "pin.json")
    assert lagging["matches"] is False and lagging["why"] == said  # the checkout lags the pin, and why
    # its log tails leave out every line naming or holding a secret, and list only the logs written
    tails = logs.tails(10, logs=tmp_path / "logs", faults=tmp_path / "faults",
                       read_journal=lambda unit_name, limit: [f"{unit_name}: fine"],
                       boot_logs=(tmp_path / "score-boot-system.log", tmp_path / "score-boot-user.log"))
    assert tails["run score-run-1.log"] == ["brief@north: made", "exit: ok"]
    assert tails["fault brief@south"] == ["cause: the brief is empty"]
    assert tails["journal score-listen.service"] == ["score-listen.service: fine"]
    assert tails["boot score-boot-system.log"] == ["boot: node 24.21.0 installed"]
    assert "boot score-boot-user.log" not in tails  # a boot log not written is not listed
    assert logs.tail(tmp_path / "logs" / "score-run-1.log", 1) == ["exit: ok"]
    # no run starts in this home under the data disk's floor: the floor, or what the most its runs wrote needs, or
    # while store-evict evicts; one store-evict at a time (2026-10-26: 0.24 GB free and Batch 1 died with "No space
    # left on device")
    assert disk.launch_refusal(tmp_path, floor=0) is None
    with disk.alone(tmp_path, disk.EVICT_LOCK):
        assert "store-evict is running" in disk.launch_refusal(tmp_path, floor=0)
        assert disk.store_evict(tmp_path, say=lambda line: None)["refused"] == "another store-evict is running"
    assert disk.launch_refusal(tmp_path, floor=0) is None
    refused = disk.launch_refusal(tmp_path / "not-yet", floor=10 ** 6)
    assert refused.startswith("refused: ") and "GB floor" in refused
    with monkeypatch.context() as low:
        low.setattr(disk, "free_gb", lambda path=None: 20.0)
        assert "floor" in disk.launch_refusal(runs_folder=registered)  # 20 GB free, under the 38 GB its runs need
        assert disk.launch_refusal(runs_folder=registered, floor=10) is None
        assert disk.FLOOR_GB == floor_gb and disk.warning(disk.free_gb()) is None  # over the floor: the card is quiet

    # `disk` accounts for the whole data disk in one line and a file: the biggest folders (three levels inside
    # store/cache), the frozen copies, the folders outside the home on its disk, a deleted file still open, the
    # folders it cannot read (2026-10-30: 0.01 GB free of 91, about 25 GB of it out of the door's sight)
    mount, disk_home = tmp_path / "disk", tmp_path / "disk" / "home"
    with monkeypatch.context() as mounted:
        mounted.setattr(disk, "mount_of", lambda path: mount)  # the disk's top above the home
        copy = disk_home / "frozen" / "20261026-081445-1"
        deep = disk_home / "store" / "cache" / "checkouts" / "abc" / "inner"
        for folder in (copy, deep, mount / "var" / "cache" / "apt", mount / "closed" / "inner"):
            folder.mkdir(parents=True)
        (copy / "big").write_bytes(b"x" * 300_000)
        (deep / "big").write_bytes(b"x" * 300_000)
        (mount / "var" / "cache" / "apt" / "big").write_bytes(b"x" * 12_000_000)
        (mount / "closed").chmod(0)
        held = open(disk_home / "gone.log", "wb")
        try:
            held.write(b"x" * 2_000_000)
            held.flush()
            (disk_home / "gone.log").unlink()
            summary, biggest = disk.report(disk_home, disk_home / "conductor" / "disk.json")
        finally:
            held.close()
            (mount / "closed").chmod(0o755)
    written = json.loads((disk_home / "conductor" / "disk.json").read_text())
    whole = written["whole"]
    assert summary.startswith("disk: ") and "1 frozen copies" in summary, summary
    assert str(disk_home / "conductor") in summary and "GB outside" in summary, summary
    assert written["folders"] and any(line.endswith(f"  {copy}") for line in biggest), biggest
    inside = biggest.index(next(line for line in biggest if line.startswith("inside ")))
    outside = biggest.index(next(line for line in biggest if line.startswith("outside ")))
    assert any(line.endswith(f"  {deep}") for line in biggest[inside:outside]), biggest
    assert any(line.endswith(f"  {mount / 'var' / 'cache' / 'apt'}") for line in biggest[outside:]), biggest
    assert whole["mount"] == str(mount) and whole["outside_gb"] > 0, whole
    assert any(process.endswith(f"(pid {os.getpid()})") for process in whole["deleted_open"]), whole
    assert any("deleted, still open in" in line for line in biggest)
    if os.getuid() != 0:  # root reads every folder
        assert whole["unread"] and any(line.startswith("unreadable: ") for line in biggest), whole

    class Gone:  # a process that ended between the /proc listing and its read
        name = "4242"

        def __truediv__(self, part):
            return self

        def read_bytes(self):
            raise ProcessLookupError(3, "No such process")

    with pytest.raises(FileNotFoundError):  # read as ended, so working() skips it (store-evict crashed, 2026-11-07)
        disk.said_by(Gone())

    # one full data disk, freed by the cleanups and the sweep (2026-10-27: 0.2 GB free, store/cache 37.5 GB of
    # checkouts and makes left behind; 2026-10-28: work/pixal held the only copy of every paid take; 2026-10-30:
    # store/objects 54.7 GB that nothing named, and the owner on the full disk needing him: "this should be routine")
    base = tmp_path / "full"
    base.mkdir()
    full, blobs, named, checked, big_blob, raw, copies = a_full_disk(base)
    pixal, cache, models = full / "work" / "pixal", full / "store" / "cache", base / "models"
    look, built = pixal / "officer-made-s1.svviews/input.png", [
        pixal / "pipe_1.svviews/input.png", pixal / "pipe_1-final.glb", pixal / "pipe_1-2000.glb"]
    real = disk.pixal_takes()
    taken = []

    def taken_in(takes, folder, commit, scratch):
        taken.extend(takes)
        return {"new": [f"take/{real.take_id(take)}@1" for take in takes], "unchanged": [], "changed draft": [],
                "new version": [], "refused": [], "saved": {"committed": "x", "pushed": True, "why": ""}}
    stand_in = type(real)("pixal_takes")  # the library takes every take in and hands back all but b-s1 whole
    stand_in.__dict__.update({**real.__dict__, "taken_in": taken_in, "upstream_holds": lambda take: True,
                              "newest_record": lambda take: {"address": f"take/{real.take_id(take)}@1"},
                              "read_back": lambda take, folder, scratch:
                              "b-s1.svviews/input.png came back with other bytes" if take == "b-s1" else None})
    said, everything = [], {path.name for path in blobs.iterdir()}
    with monkeypatch.context() as swept:
        swept.setattr(disk, "pixal_takes", lambda: stand_in)
        swept.setattr(disk, "REPO", base)
        swept.setattr(disk, "mount_of", lambda path: full)
        swept.setattr(disk, "bigger", lambda more, zone: f"{more} GB more, EUR 4.00 a month in {zone}")
        swept.setattr(disk.offload, "open_bucket", lambda: disk.offload.FolderBucket(base / "bucket"))
        # the routine sweep while a run waits and a process works in a copy: of the frozen copies only the dead run's is
        # removed, with its home, never what they link to, and nothing while an entry does not parse; the kept jobs
        # wait for the run, and a people look's and a code build's take files linked to their blob are copied plain
        worker = subprocess.Popen(SLEEP, cwd=frozen.home_of(copies["3-worked"]))
        try:
            time.sleep(0.3)
            for row, entry, frozen_words, laid, gone in [
                    ("an entry does not parse", "{", "refused: ", "copied 4", []),
                    ("a run waits", None, "removed 1, kept 3, failed 0,", "copied 0", ["1-dead"])]:
                if entry:
                    (full / "runs" / "broken.json").write_text(entry)
                said.clear()
                done = {step["step"]: step["said"] for step in disk.sweep(full, say=said.append)["steps"]}
                (full / "runs" / "broken.json").unlink(missing_ok=True)
                assert done["clean-frozen"].startswith(frozen_words) and done["laid-plain"] == laid, (row, done)
                assert sorted(name for name, path in copies.items() if not path.exists()) == gone, (row, said)
                assert not any(frozen.home_of(copies[name]).exists() for name in gone), row
                assert all(str(copies[name]) not in frozen.git(base / "checkout", "worktree", "list") for name in gone)
                assert all(f"removed {name}" in said for name in gone) and all(
                    any(line.startswith(f"kept {name}: ") for line in said) for name in copies
                    if name not in gone and entry is None), (row, said)
                assert {path.name for path in blobs.iterdir()} == everything and (full / "design" / "plan.json").exists()
                assert entry or "a registered run needs" in done["clean-kept"], (row, done)
                assert all(path.stat().st_nlink == 1 and os.access(path, os.W_OK) for path in [look, *built]), row
        finally:
            worker.kill()
            worker.wait()
        # nothing is removed, but the checkouts' copies become links to their blobs all the same
        assert "a registered run needs" in disk.store_gc(full, say=said.append)["refused"]
        done = disk.clean_cache(full, say=said.append)
        assert done["removed"] == [] and "a registered run needs" in done["refused"] and (cache / "making").exists()
        assert checked.samefile(big_blob) and any(line.startswith("relinked 1 checkouts") for line in said), said
        done = disk.offload_pixal(full, commit="0" * 40)
        assert "a registered run needs" in done["refused"] and (pixal / "a-s1.glb").exists() and not taken, done
        (full / "runs" / "w.json").unlink()
        (cache / "making" / "k-2").mkdir()  # a make started a minute ago
        assert "a make may be in progress" in disk.clean_cache(full, say=said.append)["refused"]
        (cache / "making" / "k-2").rmdir()
        os.utime(cache / "making", (time.time() - 2 * disk.YOUNG_SECONDS,) * 2)
        done = disk.clean_cache(full, names=("making",), say=said.append)
        assert done["removed"] == ["making"] and checked.exists(), done
        done = disk.clean_cache(full, say=said.append)
        assert sorted(done["removed"]) == ["checkouts", "evidence", "pages", "tmpab12"] and done["refused"] is None
        assert sorted(path.name for path in cache.iterdir()) == ["concepts", "convex-parts", "drops"]
        assert {path.name for path in blobs.iterdir()} == everything  # the stored objects stay
        assert any(line.startswith(f"kept {cache / 'drops'}: paid drops") for line in said), said
        # the toy per-take row's kept calls (the crate's and the lamp's views), made once, swept by the routine below
        swept.setenv("PROPS_HOME", str(full))
        from score import stages
        kept = stages.kept_module()
        for name in (kept.MAKING, kept.CODE):
            swept.delenv(name, raising=False)
        swept.setenv(kept.STORE, str(full / "store"))
        made = a_views_runner(full, models, {})
        made.run_node(made.stages["toy-views"], "airlock")
        os.utime(cache / "making", (time.time() - 2 * disk.YOUNG_SECONDS,) * 2)  # no make in progress
        # one offload and one sweep at a time (2026-10-31: two side by side, FileNotFoundError)
        with disk.alone(full, "offload-pixal") as first:
            assert first
            done = disk.offload_pixal(full, commit="0" * 40)
        assert "another offload-pixal is running" in done["refused"] and (pixal / "b-s1.glb").exists(), done
        record = (full / "conductor" / "sweep.json").read_text()
        with disk.alone(full, "sweep"):
            done = disk.sweep(full, say=said.append)
        assert "another sweep is running" in done["refused"] and not done["steps"], done
        assert (full / "conductor" / "sweep.json").read_text() == record  # a refused sweep writes no record
        # only the painted takes the library hands back whole are freed: never one changed now, one read back with
        # other bytes, or one with a file gone (2026-10-31: a link to nothing crashed the offload)
        done = disk.offload_pixal(full, commit="0" * 40)
        assert taken == ["a-s1", "b-s1"] and done["freed"] == 1, done
        assert {why: takes for why, takes in done["kept"].items() if why != "not whole (no raw or final model)"} == {
            "changed in the last 15 minutes": ["c-s1"],
            "read back: b-s1.svviews/input.png came back with other bytes": ["b-s1"],
            "a file is gone or a link to nothing: e-s1-19000.glb": ["e-s1"]}, done
        assert not list(pixal.glob("a-s1*")), list(pixal.iterdir())
        assert all((pixal / name).exists() for name in ("b-s1.glb", "c-s1.glb", "d-s1.glb", "e-s1.glb",
                                                        "b-s1.svviews/input.png"))
        # relink-pixal: only an old file whose bytes the store holds becomes a link to its blob, nothing is removed;
        # a people look's or a code build's take file stays a plain copy (a row copies over it: 2026-11-03,
        # SameFileError; 2026-11-05, input.png Permission denied), one linked before copied back
        for path in [look, *built]:  # linked before the rule (the sweeps above made them plain once already)
            path.unlink()
            os.link(raw, path)
        done = disk.relink_pixal(full)
        assert done["relinked"] == 2 and (pixal / "r.glb").samefile(raw) and (pixal / "r.svviews/input.png").samefile(
            raw), done
        assert done["kept"] == {"not held in the store": 10, "changed in the last 15 minutes": 3,
                                "not a regular file": 1, "already a link to its blob": 1,
                                "a people look's take, copied over by its row": 5}, done
        assert done["copied"] == 4 and all(path.stat().st_nlink == 1 for path in [look, *built]), done
        assert (pixal / "r-final.glb").read_bytes() == b"only here" and (pixal / "young.glb").stat().st_nlink == 1
        assert (pixal / "r.glb").read_bytes() == b"raw" * 1000 and not list(pixal.rglob("*.partial"))
        again = disk.relink_pixal(full)
        assert again["kept"]["already a link to its blob"] == 3 and again["copied"] == 0, again
        assert not look.samefile(raw) and look.read_bytes() == b"raw" * 1000 and os.access(look, os.W_OK)
        assert not disk.code_built(pixal / "t.glb", pixal)
        # the sweep: a live `score plan` (no registered run) judging gates on the scratch copies keeps them
        plan = subprocess.Popen([*SLEEP, "-m", "score", "plan"])
        try:
            assert str(plan.pid) in disk.clean_scratch(full)["refused"] and plan.pid in disk.score_commands()
            assert (full / disk.MOTION_SCRATCH / "layer-camp-x1").is_dir()
        finally:
            plan.kill()
            plan.wait()
        swept.setattr(disk, "score_commands", lambda: [])  # this PC's own runs aside
        swept.setattr(disk, "offload_pixal", lambda home, runs_folder: {"freed": 0, "refused": None, "kept": {}})
        free = {"gb": 50.0}
        swept.setattr(disk, "free_gb", lambda path=None: free["gb"])
        # the sweep's clean-kept works out the toy row's keys (its runner, this Python the one system): 2026-10-29,
        # kept jobs outlive their outputs, so they are swept once no current key could ask for them: never one still
        # asked for (the crate's views), never by age; the lamp's, made from its old model, and every one once the
        # row's code moved
        params = {}
        swept.setattr(stages, "runner", lambda store=None, world=None: a_views_runner(full, models, params))
        swept.setattr(disk, "blender_system", kept.python_system)
        said.clear()
        for row, edit, moved, dropped, left in [
                ("every kept call still asked for", None, {}, "dropped 0,", [{"views": 3}, {"views": 3}]),
                ("the lamp's model fixed", "lamp", {}, "dropped 1,", [{"views": 3}]),  # the crate's, still asked for
                ("the row's code moved", None, {"views": "finer"}, "dropped 1,", [])]:
            if edit:
                (models / f"{edit}.glb").write_text(f"{edit} model, fixed")
            params.clear()
            params.update(moved)
            done = disk.sweep(full, say=said.append)  # no machine.json: off a conductor, the routine only
            assert not done["escalated"] and [step["step"] for step in done["steps"]] == [
                "clean-frozen", "clean-cache", "clean-kept", "laid-plain", "clean-scratch"], (row, done)
            assert done["steps"][2]["said"].startswith(dropped), (row, done)
            assert [entry["record"] for _, entry in kept.entries()] == left, row
            assert list((full / disk.MOTION_SCRATCH).iterdir()) == []  # no run live: the scratch is cleared
            assert named["orphan"] in {path.name for path in blobs.iterdir()}  # the routine collects no blob
        everything = {path.name for path in blobs.iterdir()}  # the toy row's output stays stored
        dry_gc = disk.store_gc(full, dry=True, say=said.append)
        assert dry_gc["removed"] == 1 and {path.name for path in blobs.iterdir()} == everything, dry_gc
        (full / "machine.json").write_text(json.dumps({"zone": "fr-par-2"}))
        free["gb"] = 5.0  # under the warning line on a conductor: every step, store-gc's the blob nothing names
        done = disk.sweep(full, say=said.append)
        assert done["escalated"] and [step["step"] for step in done["steps"]][5:] == [
            "relink-pixal", "old-logs", "store-gc", "offload-pixal"], done  # store-evict never: hours a pass waits
        assert not (full / "logs" / "old.log").exists() and (full / "logs" / "new.log").exists()
        left = {path.name for path in blobs.iterdir()}
        assert left == everything - {named["orphan"]}, done  # what an output, a record, a link or a take names stays
        gc_said = next(step["said"] for step in done["steps"] if step["step"] == "store-gc")
        assert "removed 1" in gc_said and "'written in the last day': 1" in gc_said, gc_said
        assert "linked elsewhere too" in gc_said, gc_said
        store = Store.in_folder(full / "store")
        assert all(store.checkout(path.stem) for path in (full / "store" / "objects" / "outputs").glob("*.json"))
        assert done["bigger"] == "50 GB more, EUR 4.00 a month in fr-par-2" and done["fills"], done
        assert sum(line.startswith("sweep ") for line in said) == 3 * 5 + 9, said  # a line a step, each with what it freed
        note = disk.warning(5.0, swept=full / "conductor" / "sweep.json")
        assert "could not reach it" in note and "50 GB more, EUR 4.00 a month" in note, note
        free["gb"] = 12.0  # it reached the floor: nothing is asked
        assert disk.sweep(full, say=said.append)["bigger"] is None
        assert "routine sweep" in disk.warning(5.0, swept=full / "conductor" / "sweep.json")

    # the size timer, its asks sent through the real ask with the token read by name: the idle clock counts from the
    # last busy pass, a pass drains the shrink (no new pass while the mark is fresh), the shrink is asked once it ended
    # and marks its resize, the idle size takes the drain back, a failed grow takes its resize mark back, and an ask is
    # only grow or shrink
    become(16)
    monkeypatch.setattr(runs, "boot_time", lambda: 0)
    reader = tmp_path / "reader"
    reader.write_text("#!/bin/sh\n[ \"$1\" = score-conductor-size-token ] && echo the-token\n")
    reader.chmod(0o700)
    monkeypatch.setenv(size.READER, str(reader))
    sent, down, state = [], [], tmp_path / "size-state.json"

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout):
        if down:
            raise RuntimeError("the size function is down")
        sent.append((request.full_url, request.get_header("X-score-size-token"), json.loads(request.data)))
        return Answer(b"powering off")

    def asker(action):
        return size.ask(action, opener=opener)

    def tick(view, now):
        return size.tick(say=lambda line: None, now=now, asker=asker, state_path=state, view=view)["action"]
    assert [tick({**IDLE, "claims": 1}, NOW), tick(IDLE, NOW + 29 * 60), tick(PASSING, NOW + 31 * 60)] == [
        None, None, size.DRAIN] and sent == []
    assert size.draining(NOW + 32 * 60) and not size.draining(NOW + 31 * 60 + size.DRAIN_MINUTES * 60 + 1)
    assert tick({**PASSING, "passing": 0, "held": []}, NOW + 36 * 60) == size.SHRINK
    assert sent == [("https://size.invalid/", "the-token", {"action": "shrink"})]
    assert size.draining(NOW + 36 * 60)  # the mark stays until the machine is small
    assert json.loads(conductor.RESIZING.read_text())["action"] == size.SHRINK  # its power-off is a resize's
    become(2)  # booted at the idle size: passes go on again
    assert tick({**IDLE, "held": []}, NOW + 40 * 60) is None and not conductor.DRAINING.exists()
    down.append(1)  # a waiting run asks the grow while the size function is down: the mark is taken back
    with pytest.raises(RuntimeError):
        tick(WAITING, NOW + 41 * 60)
    assert not conductor.RESIZING.exists() and len(sent) == 1
    down.clear()
    assert tick(WAITING, NOW + 42 * 60) == size.GROW
    assert sent[1:] == [("https://size.invalid/", "the-token", {"action": "grow"})]
    assert json.loads(conductor.RESIZING.read_text())["action"] == size.GROW
    with pytest.raises(ValueError):
        asker("delete")
    assert len(sent) == 2

    # off a conductor the size timer asks nothing and a hold writes nothing
    become(None)
    assert size.tick(say=lambda line: None, asker=lambda action: 1 / 0)["action"] is None
    monkeypatch.setattr(conductor, "HOLDS", tmp_path / "off-holds")
    with conductor.holding("sync-pass"):
        assert not conductor.HOLDS.exists()

    # money: the bill the stop line counts is the batch project's alone, and every paid point refuses while the batch
    # project is the conductor's (by the environment's name, or by the machine record's, whatever its name)
    compute.ledger()  # puts tools/cloud on the path
    import provider
    projects = [{"id": "batch-id", "name": "farm-factory"}, {"id": "conductor-id", "name": "score-conductor"}]
    lines = [{"project_id": "batch-id", "product_name": "Instances", "value": {"units": 40, "nanos": 0}},
             {"project_id": "conductor-id", "product_name": "Instances", "value": {"units": 75, "nanos": 0}}]
    scw_asked = []

    def scw(*arguments):
        scw_asked.append(arguments)
        if arguments[:3] == ("account", "project", "list"):
            return [project for project in projects if project["name"] == arguments[3].partition("=")[2]]
        if arguments[:3] == ("billing", "consumption", "list"):
            return lines  # the API's answer may hold lines of other projects: each is checked to be the project's
        raise AssertionError(arguments)
    monkeypatch.setattr(provider.cloud, "scw", scw)
    for name in ("SCORE_SCALEWAY_PROJECT", conductor.FREE_ONLY, conductor.SIZE_URL):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(conductor, "MACHINE", tmp_path / "no-machine.json")  # by name alone, no record
    assert compute.cloud_bill() == 40.0
    assert not any("conductor-id" in word for arguments in scw_asked for word in arguments)
    line = {"world": "world1", "euros": 100.0, "at": "2026-10-22T09:00:00+00:00"}
    record = tmp_path / "project-machine.json"
    # (row, the batch project's name, the machine record's project or None) -> the conductor's own (refused)
    for row, named, recorded, refused in [
            ("a batch project", None, None, False),
            ("the conductor's project by name", conductor.CONDUCTOR_PROJECT, None, True),
            ("by the record, of another name", "batch-of-another-name", "batch-of-another-name", True),
            ("a record naming another project", "batch-of-another-name", "score-conductor-elsewhere", False)]:
        if named is None:
            monkeypatch.delenv("SCORE_SCALEWAY_PROJECT", raising=False)
        else:
            monkeypatch.setenv("SCORE_SCALEWAY_PROJECT", named)
        if recorded is None:
            said = [guard.refusal(line, 0.0, {}, 1.0)]
            if refused:
                said.append(compute.books_refusal())
                with pytest.raises(compute.Refused) as raised:
                    compute.require_books("a card")  # every rent point, the owner's override included
                said.append(str(raised.value))
        else:
            record.write_text(json.dumps({"project": recorded}))
            assert conductor.machine(record) is None, row  # not a conductor by the size function's name
            said = [conductor.project_refusal(record)]
        assert all(("the conductor's own project" in (words or "")) is refused for words in said), (row, said)

    # the stops. Only the owner's process pulls the switch, stops the batch or clears the latch
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(kill, "running_under_agent", lambda: True)
        for owners in (kill.stop_all, kill.allow_paid, kill.stop_batch):
            with pytest.raises(PermissionError, match="only the owner's click"):
                owners("owner", "stop")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCORE_CLOUD", "k8s")  # score's cluster Jobs: this box's and the PC's

    class Cloud:
        def stop_runner_servers(self):
            return ["r-1"]

        def clean_leftovers(self):
            return {"machines": [("scw-score-l4", "a SCORE pool's machine that is no node")], "disks": []}

    # (row, the stop's words, latched, every box: the cap's stop, its record's kind, the cluster Jobs it deletes)
    for row, words, latched, every_box, kind, deleted in [
            ("the kill switch", "stop it\nall", True, False, "kill", ["score-r-a-g0"]),
            ("stop this batch", "this batch", False, False, "batch-stop", ["score-r-a-g0"]),
            ("the env1 cap's stop", "past the stop line", False, True, "cap-stop", ["score-r-a-g0", "score-r-b-g0"])]:
        batch = a_batch(tmp_path / kind)
        jobs = {"score-r-a-g0": "conductor", "score-r-b-g0": "pc"}
        released, order = [], []

        def stopper(every_box=False):
            def stop():
                gone = sorted(name for name, box in jobs.items() if every_box or box == "conductor")
                for name in gone:
                    del jobs[name]
                return gone
            return stop

        def release(server, zone, token):
            order.append("parked")
            if server == "m2":
                raise RuntimeError("the provider said no")
            released.append((server, zone, token))
        monkeypatch.setattr(kill, "cluster_stopper", stopper)
        monkeypatch.setattr(conductor, "HOLDS", batch["home"] / "holds")
        given = {"folder": batch["home"] / "runs", "parked": batch["home"] / "parked", "release": release,
                 "close_pools": lambda: order.append("pools") or ["run-1"], "frozen_folder": batch["home"] / "frozen",
                 "checkout": batch["home"] / "checkout", "report_folder": batch["home"] / "reports"}
        try:
            if every_box:
                with pytest.raises(ValueError):
                    kill.cap_stop(" ")
                report = kill.cap_stop(words, cloud=Cloud(), **given)
            else:
                report = kill.stop_everything("owner", words, latched=latched, **given)
            stopped = [*batch["left"], batch["live"], batch["waiter"], batch["begin"], batch["starting"]]
            assert all(process.wait(10) == -15 for process in stopped), row
            assert batch["node"].poll() is None, row  # the stopping run ends its own (remove_owned)
            assert batch["passing"].poll() is None, row  # a sync pass's own process is its own to end
        finally:
            for process in batch["all"]:
                process.kill()
                process.wait()
        # no collector replaces the cards released next
        assert order[0] == "pools" and report["pools"] == ["run-1"], row
        assert released == [("m1", "fr-par-2", "t1")] and report["errors"][0].startswith("parked m2: RuntimeError")
        # a run still starting in its new copy, or from the checkout, is stopped as a run, never swept as a leftover
        # (2026-11-05: checkout 25, starting at a stop-batch, was spared and went on for hours)
        assert sorted(report["runs"]) == sorted(process.pid for process in (batch["live"], batch["begin"],
                                                                            batch["starting"])), row
        assert report["waiting"] == [batch["waiting"]["id"]], row
        assert json.loads(batch["entry"].read_text())["state"] == runs.STOPPED, row
        assert sorted(entry["pid"] for entry in report["leftovers"]) == sorted(
            process.pid for process in batch["left"]), row
        assert all(entry["command"] for entry in report["leftovers"]), row  # each named, so we learn what they were
        assert not conductor.RESIZING.exists(), row  # its SIGTERMs are his stop, never a resize's
        assert [path.name.partition("-2")[0] for path in (batch["home"] / "reports").iterdir()] == [kind], row
        # score's cluster Jobs too (#95): this box's, and with the cap's stop every box's
        assert report["cluster_jobs"] == deleted and sorted(jobs) == sorted({"score-r-a-g0", "score-r-b-g0"} -
                                                                           set(deleted)), row
        assert report.get("machines") == (["r-1"] if every_box else None), row  # every runner machine too
        assert bool(report.get("leftovers_cleaned", {}).get("machines")) is every_box, row
        assert (report["free_only"] is not None) is latched and conductor.free_only() is latched, row
        if latched:  # his words on one line; every score command then runs free only, until he clears it
            assert conductor.FREE_ONLY_LATCH.read_text().splitlines()[-1] == "SCORE_FREE_ONLY=1"
            assert "stop it all" in conductor.FREE_ONLY_LATCH.read_text()
            done = subprocess.run([sys.executable, "-c", "import os\nfrom score import __main__ as command\n"
                                   "command.main(['resume', '--dry'])\nprint(os.environ.get('SCORE_FREE_ONLY'))"],
                                  cwd=REPO, capture_output=True, text=True,
                                  env={**os.environ, "PROPS_HOME": str(tmp_path), "SCORE_FREE_ONLY": ""})
            assert done.stdout.strip().splitlines()[-1] == "1", done.stdout + done.stderr[-800:]
            assert kill.unlatch("owner", "go on")["was_held"] and not conductor.free_only()
            assert list(conductor.HOME.glob("free-only-cleared-*.json"))
    # Owner, 2026-10-25: the next Buy after a stopped batch needs no Allow paid work again
    assert not conductor.free_only()

    # the conductor's score_lib checkout counts after a fetch and pulls only as a fast-forward
    from score.conductor import library_checkout
    checkout = a_library_checkout(tmp_path)
    found = library_checkout.status(checkout)
    assert (found["upstream"], found["ahead"], found["behind"], found["fetch"]) == ("origin/main", 0, 1, ""), found
    assert "update by push" in found["last_push"] and found["changes"] == [], found
    assert found["remote"] == str(tmp_path / "origin.git") and "rejected" in found["push"], found  # behind origin
    frozen.git(checkout, "remote", "set-url", "origin", f"https://u:secret@{tmp_path}/origin.git")
    assert library_checkout.remote(checkout) == f"https://{tmp_path}/origin.git"  # its token never shown
    frozen.git(checkout, "remote", "set-url", "origin", str(tmp_path / "origin.git"))
    start = frozen.git(checkout, "rev-parse", "HEAD")
    for row, name, committed, refusal in LIBRARY_PULLS:
        if name:
            (checkout / name).write_text('{"changed": 1}')
        if committed:
            frozen.git(checkout, "add", name)
            frozen.git(checkout, "commit", "-q", "-m", row)
        held, files = frozen.git(checkout, "rev-parse", "HEAD"), sorted(path.name for path in checkout.iterdir())
        found, refused = library_checkout.pull(checkout)
        assert refused.startswith(refusal) if refusal else refused == "", (row, refused, found)
        if refusal:  # nothing moved: its commit and its change are where they were
            assert frozen.git(checkout, "rev-parse", "HEAD") == held, row
            assert sorted(path.name for path in checkout.iterdir()) == files, row
            assert (checkout / name).read_text() == '{"changed": 1}', row
            assert [line.endswith(row) for line in found["local_commits"]] == ([True] if committed else []), row
            frozen.git(checkout, "reset", "-q", "--hard", start)
        else:  # behind by origin's one push, now moved onto it, and a dry push is accepted
            assert found["behind"] == 1 and (checkout / "entry.json").is_file(), (row, found)
            assert library_checkout.status(checkout)["behind"] == 0, row
            assert library_checkout.status(checkout)["push"] == "", row
    out, err = dry.communicate(timeout=90)
    lines = out.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("conductor dry: 7 of 7 steps passed; detail "), out + err[-2000:]
    results = json.loads(pathlib.Path(lines[0].rpartition("detail ")[2]).read_text())
    assert [result["step"] for result in results] == ["plan", "waiting for size", "resume", "memory guard",
                                                      "health and logs", "shrink", "kill switch"]
    assert all(result["ok"] for result in results) and dry.returncode == 0


def a_batch(home):
    """A batch as a stop finds it, in `home`: a claimed run working in its frozen copy (a node of its own beside it),
    a waiting run, two parked machines (the provider refuses the second), a resize mark, a sync pass holding, a run
    still starting in its new copy and one from the checkout, and five processes left in copies of runs gone (in the
    copy, in its home, naming it on the command line, by SCORE_FROZEN, an owner past the grace). 2026-10-26: after
    Stop this batch six processes of the stopped run worked on in its frozen copy for an hour and held the checkout;
    2026-11-05: two naming a stopped free run's copy by SCORE_FROZEN or command line held every carry off; 2026-11-06:
    a `score run` still starting from the checkout held the pin 54 min."""
    for name in ("runs", "parked", "holds", "checkout"):
        (home / name).mkdir(parents=True)
    frozen_folder = home / "frozen"
    gone, stopping = frozen_folder / "20261026-081445-1", frozen_folder / "20261026-091445-2"
    begun, old = frozen_folder / "20261105-101500-3", frozen_folder / "20261105-081500-4"
    for folder in (gone, frozen_folder / "20261026-081445-1.home", stopping, begun, old):
        folder.mkdir(parents=True)
    past = time.time() - disk.YOUNG_SECONDS - 60
    os.utime(old, (past, past))  # an owner past the grace: a run gone, not starting
    owner = {"SCORE_FROZEN_OWNER": "1"}
    left = [subprocess.Popen(SLEEP, cwd=gone), subprocess.Popen(SLEEP, cwd=f"{gone}.home"),
            subprocess.Popen([*SLEEP, f"{gone}/score/run.py"], cwd=home),  # the copy as an argument, as a run names it
            subprocess.Popen(SLEEP, cwd=home, env={**os.environ, "SCORE_FROZEN": str(gone)}),
            subprocess.Popen(SLEEP, cwd=old, env={**os.environ, **owner, "SCORE_FROZEN": str(old)})]
    begin = subprocess.Popen(SLEEP, cwd=home, env={**os.environ, **owner, "SCORE_FROZEN": str(begun)})
    starting = subprocess.Popen([*SLEEP, "-m", "score", "run", "world1"], cwd=home / "checkout")
    passing = subprocess.Popen([sys.executable, "-c", f"import sys, time; sys.path.insert(0, {str(REPO)!r}); "
                                f"from score import conductor; h = conductor.holding('sync-pass', "
                                f"__import__('pathlib').Path({str(home / 'holds')!r})); h.__enter__(); "
                                f"print('held', flush=True); time.sleep(60)"], cwd=home,
                               env={**os.environ, "SCORE_FROZEN": str(gone)}, stdout=subprocess.PIPE, text=True)
    live, node, waiter = (subprocess.Popen(SLEEP, cwd=stopping), subprocess.Popen(SLEEP, cwd=stopping),
                          subprocess.Popen(SLEEP, cwd=home))
    runs.claim("c0ffee", ["draw@hangar"], live.pid, folder=home / "runs")
    waiting = runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=home / "runs")
    entry = {**json.loads(waiting.read_text()), "pid": waiter.pid}
    waiting.write_text(json.dumps(entry))
    for number in (1, 2):
        (home / "parked" / f"m{number}.json").write_text(json.dumps({"id": f"m{number}", "zone": "fr-par-2",
                                                                      "token": f"t{number}"}))
    conductor.RESIZING.parent.mkdir(parents=True, exist_ok=True)
    conductor.RESIZING.write_text(json.dumps({"action": "grow", "at": time.time()}))
    assert passing.stdout.readline().strip() == "held"
    time.sleep(0.3)  # the children are in their folders before the stop looks
    return {"home": home, "left": left, "live": live, "node": node, "waiter": waiter, "begin": begin,
            "starting": starting, "passing": passing, "waiting": entry, "entry": waiting,
            "all": [*left, live, node, waiter, begin, starting, passing]}


# --- disk: the copies no run needs -----------------------------------------------------------------------------------

def a_full_disk(base):
    """A home whose data disk fills with every kind of thing a cleanup frees or must keep: a store whose blobs an
    output, a record, a link, a listing blob, a work/pixal take and nothing name (one written now), an output whose
    checkout is a read-only copy (as an earlier commit made it), a store cache holding every kind of folder (a make's
    read-only one too), painted takes in work/pixal (one changed now, one with a link to nothing), an old and a new log,
    a killed make's scratch copy, and a waiting run registered. Beside the painted takes, takes the store holds (a raw
    model and its input picture, a young one), a final model only work/pixal holds, a people look's and a code build's
    take files linked to their blob; a crate's and a lamp's models a toy per-take row reads; and four frozen copies of a checkout: a dead run's, the waiting run's, one a
    process works in, one made now."""
    home = base / "home"
    store = Store.in_folder(home / "store")
    made = base / "made"
    made.mkdir()
    (made / "listed.bin").write_bytes(b"listed")
    store.put_tree(made)
    blobs = store.objects.path("blobs")
    named = {}
    for name in ("record", "linked", "inner", "orphan", "young", "pixal"):
        path = base / f"{name}.bin"
        path.write_bytes(name.encode() * 100)
        named[name] = file_hash(path)
        store.put_blob(path, named[name])
    index = base / "index.json"  # a listing kept as a blob, named by a record: what it names stays too
    index.write_text(json.dumps({"inner": named["inner"]}))
    named["index"] = file_hash(index)
    store.put_blob(index, named["index"])
    (home / "store" / "objects" / "concepts").mkdir(parents=True)
    (home / "store" / "objects" / "concepts" / "c.json").write_text(json.dumps(
        {"pick": named["record"], "index": named["index"]}))
    (home / "dashboard").mkdir()
    (home / "dashboard" / "view.glb").symlink_to(blobs / named["linked"])
    pixal = home / "work" / "pixal"
    pixal.mkdir(parents=True)
    os.link(blobs / named["pixal"], pixal / "t.glb")
    big = base / "big"
    big.mkdir()
    (big / "big.bin").write_bytes(b"x" * 4096)
    output = store.put_tree(big)
    takes = base / "takes"  # 2026-10-28: 16 GB free of 91, work/pixal 20.5 GB, most of it kept nowhere else
    takes.mkdir()
    (takes / "raw.glb").write_bytes(b"raw" * 1000)
    (takes / "new.glb").write_bytes(b"new" * 1000)
    raw = store.objects.path(f"blobs/{store.listing(store.put_tree(takes))['raw.glb']}")
    checked = store.checkout(output) / "big.bin"
    checked.unlink()  # a checkout an earlier commit made as a copy
    checked.write_bytes(b"x" * 4096)
    checked.chmod(0o444)
    cache = home / "store" / "cache"
    for name in ("making/k-1", "evidence", "pages/n", "tmpab12", "drops/d", "convex-parts", "concepts/asked"):
        (cache / name).mkdir(parents=True)
        (cache / name / "file").write_text(name)
    (cache / "making" / "k-1").chmod(0o555)
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "p.json").write_text(json.dumps(
        {"takes": {take: {} for take in ("a-s1", "b-s1", "c-s1", "e-s1")}}))
    for take in ("a-s1", "b-s1", "c-s1", "d-s1", "e-s1"):
        names = (f"{take}.glb", f"{take}-final.glb") + ((f"{take}.svviews/input.png",) if take != "e-s1" else ())
        if take != "e-s1":
            (pixal / f"{take}.svviews").mkdir()
        for name in names:
            (pixal / name).write_bytes(take.encode() * 100)
    (pixal / "e-s1-19000.glb").symlink_to(base / "gone.glb")
    for name in ("r.svviews", "officer-made-s1.svviews", "pipe_1.svviews"):
        (pixal / name).mkdir()
    for name, data in (("r.glb", b"raw" * 1000), ("young.glb", b"new" * 1000), ("r-final.glb", b"only here"),
                       ("r.svviews/input.png", b"raw" * 1000), ("pipe_1.svviews/code.json", b"{}")):
        (pixal / name).write_bytes(data)
    for name in ("officer-made-s1.svviews/input.png", "pipe_1.svviews/input.png", "pipe_1-final.glb",
                 "pipe_1-2000.glb"):  # a people look's and a code build's take files, linked to the blob
        os.link(raw, pixal / name)
    (home / "logs").mkdir()
    for name, days in (("old.log", disk.LOG_DAYS + 1), ("new.log", 1)):
        (home / "logs" / name).write_text(name)
        os.utime(home / "logs" / name, (time.time() - days * 86400,) * 2)
    (home / disk.MOTION_SCRATCH / "layer-camp-x1" / "camp").mkdir(parents=True)  # a killed make's seed copy
    (home / "design" / "plan.json").write_text("{}")
    (base / "models").mkdir()  # the models a per-take kept call (the finish route's views) is made from
    for take in ("crate", "lamp"):
        (base / "models" / f"{take}.glb").write_text(f"{take} model")
    repo = base / "checkout"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "-m", "one"], check=True)
    (home / "frozen").mkdir()
    copies = {name: a_copy(repo, home / "frozen", name, home) for name in ("1-dead", "2-waiting", "3-worked")}
    copies["4-young"] = home / "frozen" / "4-young"
    copies["4-young"].mkdir()
    (home / "runs").mkdir()
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(copies["2-waiting"])}))
    (home / "runs" / "e.json").write_text(json.dumps({"state": "ended", "worktree": str(copies["1-dead"])}))
    old = time.time() - 2 * disk.GC_YOUNG_SECONDS
    for path in [*cache.rglob("*"),
                 *[path for path in pixal.rglob("*") if not path.name.startswith(("c-s1", "young"))]]:
        os.utime(path, (old, old), follow_symlinks=False)
    for blob in blobs.iterdir():
        if blob.name != named["young"]:
            os.utime(blob, (old, old))
    return home, blobs, named, checked, store.objects.path(f"blobs/{store.listing(output)['big.bin']}"), raw, copies


def a_views_runner(home, models, params):
    """A runner over one toy per-take row in `home`'s store: the crate's and the lamp's views, one kept call a take,
    made from `models` under `params`."""
    from score import checks, contracts, graph, stages

    def make_views(inputs, out, seed, params):
        (out / "views.json").write_text(json.dumps({take: take_views(inputs[f"model {take}"], out / take)
                                                    for take in ("crate", "lamp")}))
    row = graph.Stage("toy-views", "place", stages.per_take_kept(make_views, "take_views", lambda found: found[1]),
                      contracts.Contract("toy-views", 1, lambda folder: []),
                      (checks.Check("views", lambda output, inputs, evidence: checks.Verdict(
                          "views", checks.PASS, "made")),),
                      files={f"model {take}": str(models / f"{take}.glb") for take in ("crate", "lamp")},
                      params=dict(params))
    return graph.Runner([row], graph.Environment("toy", 1, {}), Store.in_folder(str(home / "store")))


def a_copy(repo, folder, name, home):
    """A frozen copy `name` of `repo` under `folder` with its home: the design copied read-only, the rest linked."""
    path = folder / name
    frozen.git(repo, "worktree", "add", "-q", "--detach", str(path), "HEAD")
    frozen.home_copy(path, home)
    (frozen.home_of(path) / "design" / "plan.json").chmod(0o444)
    (frozen.home_of(path) / "design").chmod(0o555)
    old = time.time() - 2 * disk.YOUNG_SECONDS
    os.utime(path, (old, old))
    os.utime(frozen.home_of(path), (old, old))
    return path


def a_library_checkout(tmp_path):
    """The conductor's clone of a bare repository standing in for score_lib's origin, one push behind it (a second
    clone pushed past it)."""
    origin, checkout, other = tmp_path / "origin.git", tmp_path / "score_lib", tmp_path / "other"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    for clone in (checkout, other):
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
        for key, value in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
            frozen.git(clone, "config", key, value)
    (checkout / "index.json").write_text("{}")
    frozen.git(checkout, "add", "index.json")
    frozen.git(checkout, "commit", "-q", "-m", "first")
    frozen.git(checkout, "push", "-q", "-u", "origin", "HEAD:main")
    frozen.git(other, "pull", "-q", "origin", "main")
    (other / "entry.json").write_text("{}")
    frozen.git(other, "add", "entry.json")
    frozen.git(other, "commit", "-q", "-m", "pushed from elsewhere")
    frozen.git(other, "push", "-q", "origin", "HEAD:main")
    return checkout


def take_views(source, folder):
    """A per-take call (the finish route's views, made one take a call): the take's views from its model."""
    folder.mkdir(parents=True)
    (folder / "views.npz").write_text(f"views of {pathlib.Path(source).read_text()}")
    return {"views": 3}
