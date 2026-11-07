"""Each job of the box's queue runs once, on a warm worker of its own image, within the namespace's quota, in priority
order, and the box's nodes are paid once and stopped at the stop line.

kubectl is a fake cluster (worker Jobs become pods on two-card nodes while the quota's 24 cards allow), the job store
is a folder and the workers are played by the test (each takes its next assignment, writes the job's done.json and
its beat): nothing is rented. Five runs of 40 jobs over two images; each invariant with the break that turns it
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
- a node two workers share is counted once, and booked once when gone. Break: sum node cost per run (or per pod) in `Queue.count_money`.
- at the stop line nothing more is made and only this box's Jobs are deleted. Break: delete without the box selector
  in `Queue.stop`.
- a client's wait returns the run's state once over, and raises Stale once the queue's beat is stale.
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
        self.clock, self.jobs, self.pods, self.nodes, self.calls = clock, {}, {}, {}, []
        foreign = {"kind": "Job", "metadata": {"name": "score-other", "labels": {manifests.BOX_LABEL: "box-b",
                                                                    "app.kubernetes.io/part-of": "score"}}}
        self.jobs["score-other"] = foreign
        self.made = 0

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
            self.jobs[job["metadata"]["name"]] = job
            self.made += 1
            cards = workers.cards_of(job["spec"]["template"]["spec"])
            node = self.free_node() if self.cards_used() + cards <= CARDS else None
            worker = job["metadata"]["labels"][workers.WORKER_LABEL]
            self.pods[worker] = {"kind": "Pod", "job": job["metadata"]["name"], "cards": cards,
                                 "metadata": {"labels": job["spec"]["template"]["metadata"]["labels"]},
                                 "spec": {"nodeName": node}, "status": {"phase": "Running" if node else "Pending"}}

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


def play_workers(kube, store, now, ran, went):
    """Each running worker takes its next assignment: a job gets its done.json at once, go ends the pod."""
    for worker, pod in kube.pods.items():
        if pod["status"]["phase"] != "Running" or pod["job"] not in kube.jobs:
            continue
        beat_key = workers.beat_key(BOX, worker)
        beat = json.loads(store.read_bytes(beat_key)) if store.exists(beat_key) else None
        if beat is None:
            store.write_bytes(beat_key, json.dumps({"seq": -1, "at": now, "job": None}).encode())
            continue
        key = workers.assignment_key(BOX, worker, beat["seq"] + 1)
        if not store.exists(key):
            continue
        given = json.loads(store.read_bytes(key))
        if given.get("go"):
            pod["status"]["phase"] = "Succeeded"
            went[worker] = now
            continue
        store.write_bytes(f"runs/{given['run']}/{given['job']}/done.json", b"{}")
        ran.setdefault(worker, []).append((given["run"], given["job"], given["generation"], now))
        store.write_bytes(beat_key, json.dumps({"seq": beat["seq"] + 1, "at": now, "job": None}).encode())


def test_each_job_runs_once_on_a_warm_worker_of_its_image(tmp_path, monkeypatch):
    monkeypatch.setenv("SCORE_K8S_BOX", BOX)
    monkeypatch.delenv("SCORE_K8S_SHARES", raising=False)
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(submitter, "CLUSTER_WAITING", tmp_path / "waiting")
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
    ran, went, most_cards, killed, ticks = {}, {}, 0, None, 0

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
        play_workers(kube, store, now[0], ran, went)
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

    # A node two workers share is counted once.
    counted = process.Queue(FakeKube(clock), stores.FolderStore(tmp_path / "other"), Cluster(), tmp_path / "q2", BOX,
                            clock)
    pods = [{"kind": "Pod", "metadata": {"labels": {}}, "spec": {"nodeName": "shared"}}] * 2
    nodes = [{"metadata": {"name": "shared", "creationTimestamp": time_text(now[0]), "labels": {}}}]
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
