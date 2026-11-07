"""Each job of the box's queue runs once, on a warm worker of its own image, within the namespace's quota, in priority
order, and the box's nodes are paid once and stopped at the stop line.

kubectl is a fake cluster (worker Jobs become pods on two-card nodes while the quota's 24 cards allow), the job store
is a folder and each running worker pod's loop is worker.py's own (`Worker.step`, one look a tick), its `score-job` a
shell script that writes the job's done.json: nothing is rented. Five runs of 40 jobs over two images; each invariant with the break that turns it
red (each applied once, seen red, reverted):

- never more than 24 card pods. Break: drop the `fits` check in `Queue.grow`.
- the higher priority is assigned first, and places alternate within a priority. Break: `sorted(by_priority)` without
  `reverse=True` in `admission.ordered`; break: serve each place's line whole before the next in `ordered`.
- a job of image A goes only to an A worker, and a worker (one pull) runs many jobs. Break: drop the chain check in
  `admission.assignments`, or assign a job to a worker of another image.
- an idle worker is told to go after WORKER_IDLE_SECONDS with nothing expected, and held while work of its image is
  expected. Break: drop `not expected.get(...)` in `Queue.send_home`.
- each job is assigned once across a queue restart, and a job whose worker died without its done.json once more, one
  generation on. Break: skip `read_assignments` in `Queue.__init__`.
- 3 looks at the cluster a tick and at most one apply. Break: one `apply` a new worker in `Queue.grow`.
- a node two workers share is counted once, and booked once when gone, a node whose `score.dev/class` names no
  capability class (the conductor's) booked with no class, never a crash (break: read the label raw in
  `Queue.count_money`). Break: sum node cost per run (or per pod) in `Queue.count_money`.
- at the stop line nothing more is made and only this box's Jobs are deleted. Break: delete without the box selector
  in `Queue.stop`.
- a client's wait returns the run's state once over, and raises Stale once the queue's beat is stale; a run its
  client took back (`job_queue.cancel`, cluster_jobs adopting it) is never assigned again, from the inbox or open.
  Break: drop `self.take_cancels()` in `Queue.take_inbox`.
- a worker's band comes back from its lower-case label as admission names it, so a processor job finds its worker
  (the B rehearsal of 2026-11-07 needed it). Break: `band_named(...)` -> `meta["labels"].get(BAND_LABEL)` in
  `workers.listed`.
- the worker loop (worker.py, mounted from the ConfigMap applied with the workers) runs each assignment's job once,
  its beat naming the job while it runs, and ends on go or after IDLE_EXIT_SECONDS with nothing assigned. Break:
  `serve` returns after its first job (a worker that exits after one job).
- a run is handed to the queue only when it is cleared: an uncleared one is refused and no inbox file is written.
  Break: drop `require_cleared` in `job_queue.enqueue`.
The tube rehearsal's faults (2026-11-07, issue #76):
- one bad inbox entry (card and processor classes mixed) is refused, its run over and failed, and the queue goes on.
  Break: `except (Exception, SystemExit)` -> `except ZeroDivisionError` in `Queue.take_inbox`.
- a chain whose worker is pending on classes not to be had widens while it waits. Break: drop
  `self.widen_pending(listed, now)` in `Queue.grow`.
- processor classes still without a node a start window after the last widening send the chain's queued jobs back
  for rented machines (`elsewhere`, `job_queue.unhad`); card work stays. Break: drop `self.send_elsewhere(listed, now)`
  in `Queue.grow`.
- a finished worker's pod, kept with its Job, holds no node, so the node is booked after its idle tail. Break: drop
  the phase test from `hosting` in `Queue.count_money`.
- the queue ends only once every node is booked. Break: drop `queue.nodes` from `active` in `serve`.
"""
import datetime
import importlib.util
import json
import os
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "runtime"))

import admission  # noqa: E402
import job_queue  # noqa: E402
import ledger  # noqa: E402
import manifests  # noqa: E402
import store as stores  # noqa: E402
import submitter  # noqa: E402
import worker as worker_loop  # noqa: E402
import workers  # noqa: E402

spec = importlib.util.spec_from_file_location("queue_process", HERE / "__main__.py")
process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process)

BOX = "box-a"
CARDS = 24
IMAGES = {"blender": "registry.example/blender@sha256:aaa", "pixal": "registry.example/pixal@sha256:bbb"}
PRICE = 0.01  # euros a node minute


class Cluster:
    TOLERATIONS = ()

    def price(self, machine_type, zone):
        return PRICE, 1


class FakeKube:
    """A cluster of two-card nodes: a worker Job becomes a pod at once, Running on a node with a free card while the
    quota's cards allow, else Pending; a foreign box's Job sits beside them."""

    def __init__(self, clock):
        self.clock, self.jobs, self.pods, self.nodes, self.calls, self.configmaps = clock, {}, {}, {}, [], []
        foreign = {"kind": "Job", "metadata": {"name": "score-other", "labels": {manifests.BOX_LABEL: "box-b",
                                                                    "app.kubernetes.io/part-of": "score"}}}
        self.jobs["score-other"] = foreign
        self.made, self.stock = 0, None  # stock: the classes a node can be had of (None: every class)

    def json(self, *arguments):
        self.calls.append(arguments[:2])
        if arguments[1] == "jobs,pods":
            box = arguments[-1].split("=")[1]
            mine = [job for job in self.jobs.values() if job["metadata"]["labels"].get(manifests.BOX_LABEL) == box]
            return {"items": mine + [pod for pod in self.pods.values() if pod["job"] in self.jobs]}
        if arguments[1] == "nodes":
            return {"items": [{"metadata": {"name": name, "creationTimestamp": stamp, "labels": {
                manifests.CLASS_LABEL: "gpu-24gb-x2"}}} for name, stamp in self.nodes.items()]}
        return {"items": [{"status": {"hard": {"requests.nvidia.com/gpu": str(CARDS)},
                                      "used": {"requests.nvidia.com/gpu": str(self.cards_used())}}}]}

    def cards_used(self):
        return sum(pod["cards"] for pod in self.pods.values()
                   if pod["status"]["phase"] in ("Pending", "Running") and pod["job"] in self.jobs)

    def apply(self, objects):
        self.calls.append(("apply",))
        for job in objects:
            if job["kind"] == "ConfigMap":
                self.configmaps.append(job)
                continue
            self.jobs[job["metadata"]["name"]] = job
            self.made += 1
            cards = workers.cards_of(job["spec"]["template"]["spec"])
            node = self.free_node() if self.cards_used() + cards <= CARDS else None
            worker = job["metadata"]["labels"][workers.WORKER_LABEL]
            classes = set(job["metadata"]["annotations"]["score.dev/classes"].split(","))
            if self.stock is not None and not classes & self.stock:
                node = None  # none of its classes can be had: unscheduled
            self.pods[worker] = {"kind": "Pod", "job": job["metadata"]["name"], "cards": cards,
                                 "metadata": {"labels": job["spec"]["template"]["metadata"]["labels"]},
                                 "spec": {"nodeName": node}, "status": {"phase": "Running" if node else "Pending",
                                                                        "conditions": [] if node else [{
                                                                            "type": "PodScheduled", "status": "False",
                                                                            "lastTransitionTime": time_text(
                                                                                self.clock())}]}}

    def free_node(self):
        for name in self.nodes:
            if sum(1 for pod in self.pods.values() if pod["spec"]["nodeName"] == name
                   and pod["status"]["phase"] == "Running") < 2:
                return name
        name = f"node-{len(self.nodes)}"
        self.nodes[name] = time_text(self.clock())
        return name

    def run(self, *arguments):
        self.calls.append(arguments[:2])
        selector = arguments[arguments.index("-l") + 1]
        label, value = selector.split("=")
        for name in [name for name, job in self.jobs.items() if job["metadata"]["labels"].get(label) == value]:
            del self.jobs[name]

    def delete_job(self, name):
        self.calls.append(("delete",))
        self.jobs.pop(name, None)


def time_text(seconds):
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fake_job(folder, log):
    """A `score-job <run> <job>` for the folder store at `folder`: it notes the job in `log` when a worker's beat names
    it, then writes its done.json."""
    script = folder.parent / f"{folder.name}-score-job"
    script.write_text(f"""#!/bin/sh
grep -qs '"'"$1/$2"'"' {folder}/queue/{BOX}/beat/*.json && echo "$1/$2" >> {log}
mkdir -p {folder}/runs/$1/$2 && echo '{{}}' > {folder}/runs/$1/$2/done.json
""")
    script.chmod(0o755)
    return [str(script)]


def play_workers(kube, store, now, ran, went, loops, command):
    """Each running worker pod's loop (worker.py) takes one look: its first writes its beat, a job runs `command`,
    go ends the pod."""
    for worker, pod in kube.pods.items():
        if pod["status"]["phase"] != "Running" or pod["job"] not in kube.jobs:
            continue
        if worker not in loops:
            loops[worker] = worker_loop.Worker(store, BOX, worker, command, clock=lambda: now)
            continue
        key = workers.assignment_key(BOX, worker, loops[worker].seq + 1)
        given = json.loads(store.read_bytes(key)) if store.exists(key) else None
        taken = loops[worker].step()
        if taken == "go":
            pod["status"]["phase"] = "Succeeded"
            went[worker] = now
        elif taken == "ran":
            ran.setdefault(worker, []).append((given["run"], given["job"], given["generation"], now))


def test_each_job_runs_once_on_a_warm_worker_of_its_image(tmp_path, monkeypatch):
    monkeypatch.setenv("SCORE_K8S_BOX", BOX)
    monkeypatch.delenv("SCORE_K8S_SHARES", raising=False)
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(submitter, "CLUSTER_WAITING", tmp_path / "waiting")
    monkeypatch.setenv(submitter.compute.TICKET, "")
    with pytest.raises(submitter.compute.Refused):
        job_queue.enqueue("r0", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender"}},
                          root=tmp_path / "q0")
    assert not list((tmp_path / "q0").glob("inbox/*.json"))
    monkeypatch.setattr(submitter.compute, "require_cleared", lambda what: None)  # the runs below are cleared
    now = [1_800_000_000.0]
    clock = lambda: now[0]  # noqa: E731
    root, store = tmp_path / "queue", stores.FolderStore(tmp_path / "jobs")
    kube = FakeKube(clock)
    runs = {"r1": ("blender", 5, "lab"), "r2": ("blender", 5, "hub"), "r3": ("blender", 1, "camp"),
            "r4": ("pixal", 1, "lab"), "r5": ("pixal", 0, "hub")}
    for run, (kind, priority, place) in runs.items():
        monkeypatch.setenv("SCORE_QUEUE_PRIORITY", str(priority))
        monkeypatch.setenv("SCORE_QUEUE_PLACE", place)
        job_queue.enqueue(run, kind, IMAGES[kind], ["gpu-24gb"],
                          {f"j{index:02d}": {"kind": kind, "minutes": 5} for index in range(40)}, root=root)
    (root / "expected").mkdir(parents=True)
    expected = root / "expected" / f"{os.getpid()}.json"
    expected.write_text(json.dumps({"pixal": 3}))
    queue = process.Queue(kube, store, Cluster(), root, BOX, clock)
    ran, went, most_cards, killed, ticks, loops = {}, {}, 0, None, 0, {}
    command = fake_job(tmp_path / "jobs", tmp_path / "ran.txt")

    def kill_one():
        """A worker dies holding an assignment it never took."""
        for worker, pod in kube.pods.items():
            beat = json.loads(store.read_bytes(workers.beat_key(BOX, worker)))
            key = workers.assignment_key(BOX, worker, beat["seq"] + 1)
            if pod["status"]["phase"] == "Running" and store.exists(key):
                pod["status"]["phase"] = "Failed"
                return json.loads(store.read_bytes(key))
        return None

    def tick(between=None):
        nonlocal most_cards
        before = len(kube.calls)
        queue.tick(now[0])
        calls = kube.calls[before:]
        assert sum(1 for call in calls if call[0] == "get") == 3 and sum(1 for call in calls if call == ("apply",)) <= 1
        most_cards = max(most_cards, kube.cards_used())
        found = between() if between else None
        play_workers(kube, store, now[0], ran, went, loops, command)
        now[0] += process.QUEUE_TICK
        return found

    while any((root / "state" / f"{run}.json").exists() and not json.loads(
            (root / "state" / f"{run}.json").read_text())["over"] for run in runs) or ticks < 3:
        ticks += 1
        assert ticks < 400
        if ticks == 4:
            queue = process.Queue(kube, store, Cluster(), root, BOX, clock)  # a restarted queue
        found = tick(kill_one if ticks == 3 else None)
        killed = killed or found
    assert most_cards <= CARDS and killed

    # Each job once, on a worker of its image; the dead worker's job once more, one generation on.
    kinds = {worker: pod["metadata"]["labels"][workers.IMAGE_LABEL] for worker, pod in kube.pods.items()}
    taken = {}
    for worker, jobs in ran.items():
        for run, job, generation, _at in jobs:
            assert kinds[worker] == runs[run][0]
            taken.setdefault((run, job), []).append(generation)
    assert len(taken) == 200
    assert all(generations == [0] for key, generations in taken.items() if key != (killed["run"], killed["job"]))
    assigned = {}
    for key in store.keys(f"queue/{BOX}/assign/"):
        given = json.loads(store.read_bytes(key))
        if not given.get("go"):
            assigned.setdefault((given["run"], given["job"]), []).append(given["generation"])
    assert assigned[(killed["run"], killed["job"])] == [0, 1]
    assert all(len(generations) == 1 for key, generations in assigned.items() if key != (killed["run"], killed["job"]))
    assert kube.made <= 60 and sum(len(jobs) for jobs in ran.values()) / len(ran) >= 3  # a pull a worker, many jobs
    assert sorted((tmp_path / "ran.txt").read_text().split()) == sorted(
        f"{run}/{job}" for jobs in ran.values() for run, job, _generation, _at in jobs)  # each with its beat on it
    loop_name = workers.configmap_name()
    assert kube.configmaps and all(made["metadata"]["name"] == loop_name and made["data"]["worker.py"] == (
        HERE / "worker.py").read_text() for made in kube.configmaps)
    assert all({"name": "loop", "configMap": {"name": loop_name}} in job["spec"]["template"]["spec"]["volumes"]
               for job in kube.jobs.values() if workers.WORKER_LABEL in job["metadata"]["labels"])

    # The loop in one pod: each assignment's job once, ended by go; a worker with nothing assigned ends by itself.
    lone = stores.FolderStore(tmp_path / "lone")
    lone_command = fake_job(tmp_path / "lone", tmp_path / "lone-ran.txt")
    given = [{"run": "r9", "job": f"j{index}", "generation": 0} for index in range(3)] + [{"go": True}]
    for seq, value in enumerate(given):
        lone.write_bytes(workers.assignment_key(BOX, "w1", seq), json.dumps(value).encode())
    assert worker_loop.serve(worker_loop.Worker(lone, BOX, "w1", lone_command), poll=0) == "go"
    assert (tmp_path / "lone-ran.txt").read_text().split() == ["r9/j0", "r9/j1", "r9/j2"]
    assert all(lone.exists(f"runs/r9/j{index}/done.json") for index in range(3))
    assert json.loads(lone.read_bytes(workers.beat_key(BOX, "w1")))["seq"] == 2
    waited = [0.0]
    lonely = worker_loop.Worker(lone, BOX, "w2", lone_command, clock=lambda: waited[0])
    assert worker_loop.serve(lonely, sleep=lambda seconds: waited.__setitem__(0, waited[0] + seconds)) == "idle"
    assert worker_loop.IDLE_EXIT_SECONDS <= waited[0] and worker_loop.IDLE_EXIT_SECONDS > workers.WORKER_EXPECTED_SECONDS

    # Priority first, places round robin within it.
    order = sorted((at, run) for jobs in ran.values() for run, _job, _generation, at in jobs)
    first = [run for _at, run in order[:CARDS]]
    assert set(first) <= {"r1", "r2"} and first.count("r1") == first.count("r2")
    last_high = max(at for at, run in order if run in ("r1", "r2"))
    assert all(at >= last_high for at, run in order if run in ("r3", "r4", "r5"))
    assert [job["place"] for job in admission.ordered(
        [{"priority": 1, "place": place} for place in ("lab", "lab", "hub", "hub")], {})] == ["hub", "lab"] * 2

    # Held while pixal work is expected, told to go WORKER_IDLE_SECONDS after it no longer is.
    pixal = [worker for worker, kind in kinds.items() if kind == "pixal" and worker not in went]
    assert pixal
    for _ in range(30):
        tick()
    assert not set(pixal) & set(went)
    expected.unlink()
    tick()
    tick()
    assert set(pixal) <= set(went)
    monkeypatch.setenv("SCORE_QUEUE_PRIORITY", "0")
    job_queue.enqueue("r6", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender", "minutes": 5}},
                      root=root)
    for _ in range(18):
        tick()
    worker = next(worker for worker, jobs in ran.items() if jobs[-1][0] == "r6")
    idle_from = ran[worker][-1][3]
    assert worker in went
    assert workers.WORKER_IDLE_SECONDS <= went[worker] - idle_from <= workers.WORKER_IDLE_SECONDS + 30

    # A client's wait: the state once over; Stale once the beat is stale.
    assert job_queue.wait("r6", root=root, sleep=lambda seconds: None)["jobs"]["j0"]["state"] == "done"
    job_queue.enqueue("r7", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender"}}, root=root)
    os.utime(root / "beat", (now[0] - 3600, now[0] - 3600))
    late = iter(range(int(now[0]), int(now[0]) + 10_000, 60))
    with pytest.raises(job_queue.Stale):
        job_queue.wait("r7", root=root, clock=lambda: float(next(late)), sleep=lambda seconds: None)
    assert not list((tmp_path / "waiting").iterdir())
    # A run its client took back (job_queue.cancel) is never assigned: not from the inbox, not once open.
    process.Queue(kube, store, Cluster(), root, BOX, clock).take_inbox()  # r7 open there
    job_queue.enqueue("r10", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender"}}, root=root)
    job_queue.cancel("r7", root=root)
    job_queue.cancel("r10", root=root)
    back = process.Queue(kube, store, Cluster(), root, BOX, clock)
    back.take_inbox()
    assert not [job for job in back.queued() if job["run"] in ("r7", "r10")] and "r10" not in back.runs
    assert back.runs["r7"]["over"] and back.runs["r7"]["jobs"]["j0"]["state"] == "stopped"
    # A worker's band comes back from its label as admission names it (a label is lower case).
    made = workers.manifest(BOX, "wm", ("runner", IMAGES["blender"], "abc"), "M", ["cpu-32c-128gb"], 0)
    assert workers.listed([made])["wm"]["band"] == "M" and admission.serves(workers.listed([made])["wm"]["band"], "S")

    # A node two workers share is counted once.
    counted = process.Queue(FakeKube(clock), stores.FolderStore(tmp_path / "other"), Cluster(), tmp_path / "q2", BOX,
                            clock)
    pods = [{"kind": "Pod", "metadata": {"labels": {}}, "spec": {"nodeName": "shared"}}] * 2
    nodes = [{"metadata": {"name": "shared", "creationTimestamp": time_text(now[0]),
                           "labels": {"score.dev/class": "conductor"}}}]
    assert counted.count_money(pods, nodes, now[0] + 600) == pytest.approx(10 * PRICE)
    assert counted.count_money([], [], now[0] + 900) == pytest.approx(10 * PRICE)  # gone: booked, once
    rows = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [(row["kind"], row["node"], round(row["euros"], 6)) for row in rows] == [("queue-node", "shared", 10 * PRICE)]

    # At the stop line: only this box's Jobs deleted, nothing more made.
    stopping_kube = FakeKube(clock)
    stopping = process.Queue(stopping_kube, stores.FolderStore(tmp_path / "stop"), Cluster(), tmp_path / "q3", BOX,
                             clock)
    job_queue.enqueue("r8", "blender", IMAGES["blender"], ["gpu-24gb"],
                      {f"j{index}": {"kind": "blender"} for index in range(400)}, stop_line=0.5, root=tmp_path / "q3")
    for _ in range(40):
        stopping.tick(now[0])
        now[0] += process.QUEUE_TICK
    state = json.loads((tmp_path / "q3" / "state" / "r8.json").read_text())
    assert state["over"] and "stop line" in state["stopped"]
    assert list(stopping_kube.jobs) == ["score-other"]
    stops = [index for index, call in enumerate(stopping_kube.calls) if call == ("delete", "jobs")]
    assert len(stops) == 1 and ("apply",) not in stopping_kube.calls[stops[0]:]

    # One bad inbox entry is refused, its run over and failed, and the queue goes on with the next.
    bad_root, bad_kube = tmp_path / "q4", FakeKube(clock)
    job_queue.enqueue("bad", "runner", IMAGES["blender"], ["gpu-24gb", "cpu-32c-64gb"],
                      {"j0": {"kind": "runner"}}, root=bad_root)
    job_queue.enqueue("good", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender"}}, root=bad_root)
    after_bad = process.Queue(bad_kube, stores.FolderStore(tmp_path / "bad"), Cluster(), bad_root, BOX, clock)
    after_bad.tick(now[0])
    refused = json.loads((bad_root / "state" / "bad.json").read_text())
    assert refused["over"] and "mix card and processor" in refused["refused"] and \
        refused["jobs"] == {"j0": {"state": "failed"}}
    assert "good" in after_bad.runs and not list(bad_root.glob("inbox/*.json")) and bad_kube.made == 1

    # A chain whose worker is pending on classes that cannot be had widens while it waits: the pending worker deleted,
    # one made again on the wider classes.
    wide_kube = FakeKube(clock)
    wide_kube.stock = set()  # no class of it can be had
    wide_root = tmp_path / "q5"
    job_queue.enqueue("wide", "runner", IMAGES["blender"], ["cpu-64c-128gb", "cpu-32c-64gb"],
                      {"j0": {"kind": "runner", "cards": 0}}, root=wide_root)
    widening = process.Queue(wide_kube, stores.FolderStore(tmp_path / "wide"), Cluster(), wide_root, BOX, clock)
    for _ in range(int(submitter.NODE_MINUTES * 60 / process.QUEUE_TICK) + 3):
        widening.tick(now[0])
        now[0] += process.QUEUE_TICK
    made_on = [job["metadata"]["annotations"]["score.dev/classes"] for job in wide_kube.jobs.values()
               if workers.WORKER_LABEL in job["metadata"]["labels"]]
    assert made_on == ["cpu-64c-128gb,cpu-32c-64gb"] and wide_kube.made == 2, (made_on, wide_kube.made)

    # Processor classes still without a node a start window after the last widening: the chain's queued jobs given
    # back for rented machines, its pending worker deleted, the classes noted, a new run of them not waited on.
    # Card work stays on the cluster.
    job_queue.enqueue("cards", "blender", IMAGES["blender"], ["gpu-24gb"], {"j0": {"kind": "blender"}},
                      root=wide_root)
    for _ in range(int(submitter.NODE_MINUTES * 60 / process.QUEUE_TICK) + 3):
        widening.tick(now[0])
        now[0] += process.QUEUE_TICK
    gave_back = json.loads((wide_root / "state" / "wide.json").read_text())
    assert gave_back["over"] and gave_back["jobs"]["j0"]["state"] == job_queue.ELSEWHERE, gave_back
    assert not [job for job in wide_kube.jobs.values() if workers.WORKER_LABEL in job["metadata"]["labels"]
                and job["metadata"]["labels"][workers.IMAGE_LABEL] == "runner"]
    assert job_queue.unhad(["cpu-64c-128gb", "cpu-32c-64gb"], root=wide_root, now=now[0])
    assert not job_queue.unhad(["cpu-64c-128gb", "cpu-32c-64gb"], root=wide_root,
                               now=now[0] + job_queue.UNHAD_MINUTES * 60)
    assert not job_queue.unhad(["gpu-24gb"], root=wide_root, now=now[0]) and "cards" in widening.runs

    # A finished worker's pod (kept with its Job) holds no node: the node is booked after its idle tail.
    tail = submitter.IDLE_ESTIMATE_MINUTES * 60
    finished = process.Queue(FakeKube(clock), stores.FolderStore(tmp_path / "fin"), Cluster(), tmp_path / "q6", BOX,
                             clock)
    on_node = {"kind": "Pod", "metadata": {"labels": {}}, "spec": {"nodeName": "kept"}, "status": {"phase": "Running"}}
    kept_node = [{"metadata": {"name": "kept", "creationTimestamp": time_text(now[0]), "labels": {}}}]
    finished.count_money([on_node], kept_node, now[0] + 600)
    for at in (600, 600 + tail):
        finished.count_money([{**on_node, "status": {"phase": "Succeeded"}}], kept_node, now[0] + at)
    assert not finished.nodes and finished.booked == pytest.approx(-(-(600 + tail) // 60) * PRICE)  # whole minutes

    # The queue ends only once its nodes are booked.
    class Unbooked:
        runs, ticks = {}, 0

        def __init__(self):
            self.nodes = {"kept": {}}

        def tick(self):
            self.ticks += 1
            if self.ticks == 3:
                self.nodes.clear()
            return {}
    monkeypatch.setattr(process.time, "sleep", lambda seconds: None)
    unbooked = Unbooked()
    process.serve(unbooked, idle_exit=0)
    assert unbooked.ticks == 3
