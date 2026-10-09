"""Checks for the submitter's class order, widening, reading of the cluster and stop at the limits, with kubectl and
the provider stubbed: nothing is rented."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import submitter as submit  # noqa: E402

POOLS = {"gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2", "cpu-32c-128gb"}


def test_class_order_comes_from_capacity():
    order, late = submit.class_order("pixal", {}, POOLS)
    assert order[0] == "gpu-80gb" and "gpu-24gb-x2" not in order
    order, late = submit.class_order("library", {}, POOLS)
    assert order == ["gpu-24gb", "gpu-48gb", "gpu-80gb"] and late == {"gpu-80gb"}
    order, _late = submit.class_order("blender", {"classes": ["cpu-32c-128gb"]}, POOLS)
    assert order == ["cpu-32c-128gb"]


def test_cards_by_class():
    assert submit.job_cards({}, ["gpu-24gb", "gpu-48gb"]) == 1
    assert submit.job_cards({}, ["cpu-32c-128gb"]) == 0


def test_widening_waits_for_the_autoscaler_or_the_node_time():
    state = {"step": 1, "since": 1000.0, "first": 1000.0}
    assert not submit.wants_widening(state, [], 1000.0 + 3600)
    assert not submit.wants_widening(state, [(1000.0, None)], 1000.0 + 60)
    assert submit.wants_widening(state, [(1000.0, 1050.0)], 1000.0 + submit.NO_GROW_GRACE_MINUTES * 60)
    assert not submit.wants_widening(state, [(1000.0, 900.0)], 1000.0 + submit.NO_GROW_GRACE_MINUTES * 60)
    assert submit.wants_widening(state, [(1000.0, None)], 1000.0 + submit.NODE_MINUTES * 60)


def test_late_classes_wait():
    order, late = ["gpu-24gb", "gpu-48gb", "gpu-80gb"], {"gpu-80gb"}
    state = {"step": 2, "since": 0.0, "first": 0.0}
    assert not submit.may_widen(state, order, late, 60.0)
    assert submit.may_widen(state, order, late, submit.capacity.LATE_MINUTES * 60.0)
    assert not submit.may_widen({"step": 3, "since": 0.0, "first": 0.0}, order, late, 1e9)


def test_reading_the_autoscaler_and_jobs():
    events = [{"reason": "NotTriggerScaleUp", "involvedObject": {"name": "pod-a"},
               "lastTimestamp": "2026-10-09T14:00:00Z",
               "message": "pod didn't trigger scale-up: 1 in backoff after failed scale-up"},
              {"reason": "TriggeredScaleUp", "involvedObject": {"name": "pod-b"}, "lastTimestamp": "2026-10-09T14:00:00Z",
               "message": "pod triggered scale-up"}]
    found = submit.no_grow_times(events)
    assert set(found) == {"pod-a"} and found["pod-a"] == submit.parse_time("2026-10-09T14:00:00Z")
    grown_after = [{"reason": "NotTriggerScaleUp", "involvedObject": {"name": "pod-c"},
                    "lastTimestamp": "2026-10-09T14:20:39Z", "message": "pod didn't trigger scale-up: 8 max node group size reached"},
                   {"reason": "TriggeredScaleUp", "involvedObject": {"name": "pod-c"},
                    "lastTimestamp": "2026-10-09T14:20:59Z", "message": "pod triggered scale-up"}]
    assert submit.no_grow_times(grown_after) == {}
    assert submit.job_outcome({"status": {"conditions": [{"type": "Complete", "status": "True"}]}}) == "done"
    assert submit.job_outcome({"status": {"conditions": [
        {"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}}) == "expired"
    assert submit.job_outcome({"status": {}}) is None
    pod = {"status": {"conditions": [{"type": "PodScheduled", "status": "False",
                                      "lastTransitionTime": "2026-10-09T14:00:00Z"}]}}
    assert submit.unscheduled_since(pod) == submit.parse_time("2026-10-09T14:00:00Z")


class FakeCluster:
    """A cluster module that bills a fixed month and records the caps it is given."""
    KUBECONFIG = "/dev/null"

    def __init__(self, spent):
        self.spent, self.caps = spent, []

    def month_spend(self):
        return self.spent

    def cap_pools(self, euros_left, hours):
        self.caps.append((euros_left, hours))
        return {}


def test_refuses_at_the_month_ceiling():
    cluster = FakeCluster(submit.ledger.MONTH_EUROS)
    try:
        submit.prepare(None, cluster, cluster.month_spend())
    except SystemExit as stop:
        assert "ceiling" in str(stop)
    else:
        raise AssertionError("a run at the ceiling was submitted")
    assert cluster.caps == []


def test_run_specs_reads_each_job_json(tmp_path):
    store = submit.runtime().stores.FolderStore(tmp_path)
    store.write_bytes("runs/r1/a/job.json", b'{"kind": "pixal"}')
    store.write_bytes("runs/r1/a/done.json", b"{}")
    store.write_bytes("runs/r1/b/job.json", b'{"kind": "judge"}')
    store.write_bytes("runs/r2/c/job.json", b'{"kind": "judge"}')
    assert submit.run_specs(store, "r1") == {"a": {"kind": "pixal"}, "b": {"kind": "judge"}}
    assert submit.runtime().state(store, "r1", "a") == "done"


class FakeKubectl:
    """kubectl answering with fixed Jobs, and recording what is applied."""

    def __init__(self, items):
        self.items, self.applied = items, []

    def json(self, *arguments):
        return {"items": self.items if arguments[1] == "jobs,pods" else []}

    def apply(self, objects):
        self.applied += objects


class PoolCluster(FakeCluster):
    def class_pools(self):
        return [{"class": name} for name in POOLS]


def test_resume_takes_up_the_newest_generation():
    spec = {"kind": "library", "image": "image", "minutes": 5}
    made = submit.manifests.job(spec, "r1", "bake", ["gpu-24gb", "gpu-48gb"], 1, generation=2)
    kubectl = FakeKubectl([made])
    run = submit.Run("r1", {"bake": spec, "other": spec}, kubectl, PoolCluster(0))
    run.resume()
    assert run.jobs["bake"]["generation"] == 2 and run.jobs["bake"]["submitted"]
    assert run.jobs["other"]["submitted"] is None
    assert run.allowed("other") == ["gpu-24gb", "gpu-48gb"]


class LiveKubectl:
    """A cluster's Jobs as kubectl sees them: what the submitter applies is there, pods and events are set by the
    test."""

    def __init__(self):
        self.jobs, self.pods, self.events, self.deleted = {}, [], [], []

    def json(self, *arguments):
        if arguments[1] == "jobs,pods":
            return {"items": list(self.jobs.values()) + self.pods}
        return {"items": self.events if arguments[1] == "events" else []}

    def apply(self, objects):
        for item in objects:
            self.jobs[item["metadata"]["name"]] = item

    def delete_job(self, name):
        self.deleted.append(name)
        self.jobs.pop(name, None)


def waiting_pod(job_name, job_label, since):
    return {"kind": "Pod", "metadata": {"name": f"{job_name}-pod", "labels": {"score.dev/job": job_label}},
            "spec": {}, "status": {"conditions": [{"type": "PodScheduled", "status": "False",
                                                   "lastTransitionTime": since}]}}


def no_stock(pod_name, when):
    return {"reason": "NotTriggerScaleUp", "involvedObject": {"name": pod_name}, "lastTimestamp": when,
            "message": "pod didn't trigger scale-up: 1 in backoff after failed scale-up"}


def test_a_run_never_settles_and_takes_stock_that_comes_back(monkeypatch):
    """The first class is out of stock, then the second; the kind widens one class at a time and keeps the earlier
    ones, a Job that waited past its deadline is made again rather than failed, and when the first class's stock
    comes back the waiting job runs there."""
    clock = [submit.parse_time("2026-10-09T14:00:00Z")]
    monkeypatch.setattr(submit.time, "time", lambda: clock[0])
    kubectl = LiveKubectl()
    spec = {"kind": "meshparts", "image": "image", "minutes": 10}
    run = submit.Run("r1", {"part": spec}, kubectl, PoolCluster(0))
    order, _late = submit.class_order("meshparts", spec, POOLS)
    assert order == ["gpu-80gb", "gpu-48gb", "gpu-24gb"]
    run.make("part")

    def poll_with_no_stock(minutes):
        name = submit.manifests.job_name("r1", "part", run.jobs["part"]["generation"])
        stamp = time_text(clock[0])
        kubectl.pods = [waiting_pod(name, "part", stamp)]
        clock[0] += minutes * 60
        kubectl.events = [no_stock(f"{name}-pod", stamp)]
        jobs, pods, no_grow = run.read()
        run.update_job("part", run.current("part", jobs), pods.get("part", []))
        run.widen(pods, no_grow)

    poll_with_no_stock(2)
    assert run.allowed("part") == ["gpu-80gb", "gpu-48gb"] and run.jobs["part"]["generation"] == 1
    poll_with_no_stock(2)
    assert run.allowed("part") == order and run.jobs["part"]["generation"] == 2
    poll_with_no_stock(2)
    assert run.allowed("part") == order and run.jobs["part"]["generation"] == 2

    current = kubectl.jobs[submit.manifests.job_name("r1", "part", 2)]
    current["status"] = {"conditions": [{"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}
    jobs, pods, _no_grow = run.read()
    run.update_job("part", run.current("part", jobs), [])
    assert run.jobs["part"]["state"] == "waiting" and run.jobs["part"]["generation"] == 3
    remade = kubectl.jobs[submit.manifests.job_name("r1", "part", 3)]
    assert remade["metadata"]["annotations"]["score.dev/classes"] == ",".join(order)

    started = time_text(clock[0])
    kubectl.pods = [{"kind": "Pod", "metadata": {"name": "p", "labels": {"score.dev/job": "part"}},
                     "spec": {"nodeName": "node-80gb"},
                     "status": {"containerStatuses": [{"state": {"running": {"startedAt": started}}}]}}]
    remade["status"] = {"conditions": [{"type": "Complete", "status": "True"}]}
    jobs, pods, _no_grow = run.read()
    run.update_job("part", run.current("part", jobs), pods["part"])
    assert run.jobs["part"]["state"] == "done" and run.jobs["part"]["node"] == "node-80gb"


def time_text(seconds):
    return submit.datetime.datetime.fromtimestamp(seconds, submit.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PricedCluster(PoolCluster):
    def price(self, machine_type, zone):
        return 0.013125, 1


def test_a_warm_node_counts_from_the_runs_start():
    spec = {"kind": "judge", "image": "image", "minutes": 5}
    run = submit.Run("r1", {"ask": spec}, FakeKubectl([]), PricedCluster(0))
    run.started = 10_000.0
    run.jobs["ask"].update(node="warm", ran=10_030.0, state="done")
    run.nodes["warm"] = {"class": "gpu-80gb", "type": "H100-1-80G", "zone": "fr-par-2", "cards": 1,
                         "created": 4_000.0, "ready": 4_200.0, "deleted": 10_600.0, "jobs": set()}
    machine, = submit.node_machines(run, "judge")
    assert machine["created"] == 10_000.0 and machine["ready"] == 10_000.0
    row = submit.ledger.machine_row(machine)
    assert row["start_wait_minutes"] == 0 and row["minutes"] == 10


class NodeKubectl(FakeKubectl):
    def json(self, *arguments):
        return {"items": self.items if arguments[1] == "nodes" else []}


class BilledCluster(PoolCluster):
    def nodes(self):
        return [{"name": "kosmos-node", "type": "POP2-32C-128G", "zone": "pl-waw-2", "created": 100.0}]


def test_a_node_without_zone_labels_takes_the_providers_record():
    node = {"metadata": {"name": "kosmos-node", "creationTimestamp": "2026-10-09T14:50:00Z",
                         "labels": {"score.dev/class": "cpu-32c-128gb"}},
            "status": {"conditions": [{"type": "Ready", "status": "True",
                                       "lastTransitionTime": "2026-10-09T14:50:13Z"}]}}
    run = submit.Run("r1", {}, NodeKubectl([node]), BilledCluster(0))
    run.watch_nodes()
    seen = run.nodes["kosmos-node"]
    assert (seen["type"], seen["zone"], seen["created"]) == ("POP2-32C-128G", "pl-waw-2", 100.0)
