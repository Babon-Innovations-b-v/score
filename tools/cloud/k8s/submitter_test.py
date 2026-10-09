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
