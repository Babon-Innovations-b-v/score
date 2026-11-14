"""A job reaches only its kind's classes, in capacity.py's order, widened one class at a time when the cluster cannot
grow the ones it has; nothing goes on the cluster outside a cleared run; outputs come back where the runner wants
them; and every node a run made is billed to it.

kubectl, the provider and the cluster module are stubbed and the store is a folder: nothing is rented. Each
invariant with the break that turns it red (each applied once and seen red):

- The class order is capacity's (the cheapest card per job first; no H100 for a bake, even in the blender image),
  narrowed to the cluster's pools; a job none of whose classes has a pool takes the nearest pool that holds it
  (settling's 4 cores on the 32-core pool), never one its kind may not take. Break: drop the capacity.NEVER filter
  in `class_order`. Break: `job_kind` returns the spec's `kind` only. Break: raise at once when `order` is empty in
  `class_order`. Break: `fits[-1]` in `nearest_pools`. Break: drop the NEVER filter of `nearest_pools`'s pools.
- A Job requires its allowed classes and prefers them in order, tolerates the job path's taints and the cluster
  module's, asks for cards only on card classes, sets limits past any node (a namespace's default limits refused
  jobs asking more memory than them), mounts the node's weights cache, retries `attempt_limit - 1` times and has a Kubernetes name.
  Break: equal weights in `affinity`. Break: `limits = {}` in `resources`. Break: drop `*extra` in `tolerations`.
  Break: `cluster_provider` returns the whole SCORE_K8S_PROVIDER as the backend. Break: `backoffLimit` = attempt_limit. Break: no `.lower()` in `name_part`.
  Break: `job_name` keeps the start of a long name.
- Widening: only after the autoscaler said "cannot grow" for the grace time, or no node came for NODE_MINUTES; a
  "cannot grow" followed by a scale-up does not count; a late class waits LATE_MINUTES; the earlier classes are kept;
  a Job that waited past its deadline with no node is made again, not failed; resuming takes up the newest
  generation. Break: drop `since_step >= NO_GROW_GRACE_MINUTES * 60` in `wants_widening`.
  Break: count every NotTriggerScaleUp in `no_grow_times`. Break: `record["state"] = "failed"` for every expired Job.
  Break: drop the `late` check in `may_widen`. A run none of whose jobs ran yet is marked waiting, so its runaway
  watch leaves the wait for a node out, and unmarked once one runs (2026-11-08: light-passes, settle and sound
  rows stopped at twice their forecast while their pods waited). Break: `return True` in `none_ran`. Its runaway
  watch is told the Jobs' own deadlines, the longest once a round of `parallel` (2026-11-09: light-passes@campgrounds
  stopped at twice an average forecast inside them). Break: `rounds = 1` in `declared_seconds`.
- Nothing goes on the cluster outside a cleared run (design of 2026-10-11, section 6).
  Break: drop `compute.require_cleared` in `prepare`. Under the owner's override a run is stopped once its nodes
  cost what is left of his euros less 10% (ledger.batch_cap). Break: `over_limits` compares with
  `ledger.BATCH_EUROS`.
- A run holds to its `parallel` jobs at once. Break: drop the `parallel` return in `submit_more`. A Job is made
  only while the namespace's quota has room for its pod: 2 cards left and 5 card jobs make 2 and hold 3, which go on
  once room comes; a quota's FailedCreate is no word to widen; a login that may not read the quota (forbidden)
  makes every Job as before. Break: drop the `fits` check in `submit_more`, or the forbidden catch in `quota_room`.
- Inputs go up at their paths (a folder as one key a file), outputs come back where the runner wants them, a job
  that did not finish is reported by its number. Break: report every job as failed in `cluster_jobs.run`. Each
  input file is keyed by its sha256 (a checkout's from its listing) and goes up once: a second run of one input
  uploads nothing; an input whose store blob is evicted is copied inside the object storage (one copy), never
  fetched back here. Break: drop the `store.exists` ask in `send_input` (each
  run sends again). Break: `fetched` then upload in place of `offload.copy_blob` in `send_input`. A path named
  through a link (a frozen run's `<copy>.home/store`) lands up there and comes back at the path as named, the path
  the command's arguments give, since the pod holds no link, each output's folder made there first. Break:
  `.resolve()` the path up there in `placed`. Break: return `command` unchanged in `with_output_folders`.
  A named run resumed with fewer jobs brings each job its own outputs (2026-11-06: 148 of 720 GEM-X videos came
  back as another video's). Break: `ids = [str(number) for number in range(len(jobs))]` in `keyed_jobs.run`.
  A job that reads a take's faces (a `<take>/parts.npy` input) gets FACE_MINUTES more a million of them; one that
  reads none keeps its runner's minutes. Break: `"minutes": job.get("minutes", 30)` in `spec_of`. Break: `return 0`
  first in `take_faces`.
- Billing: a warm node counts from the run's start; an unused node made during the run is the run's; a node made
  before it, or hosting another run, is not; a node without zone labels takes the provider's record;
  a node whose `score.dev/class` names no capability class (the conductor's) is no class node, never a crash.
  Break: read the label raw in `watch_nodes` (`provider.cards('conductor')` raises). A node seen before its labels
  takes its type and zone when they come. Break: drop `if seen["type"] == "?":` and its line in `watch_nodes`.
  Break: `created = seen["created"]` in `node_machines`. Runs side by side book each node at their part, whole
  between them: a node shared by the time each run's pods held it (a gap to the run that held it last, before any
  hold to the first), an unused node by the pods that waited for its class when it came up; a run whose pods came
  after books none of it. Break: `paid += right - left` (no split) in `held_share`. Break: return the fallback
  (`1.0 if created >= started`) for every unused node in `Run.share` (the 23 nodes of 2026-11-07). Break: drop the
  `made > seen["created"]` check in `note_waiting`. Break: drop `* share` from `euros` in `ledger.machine_row`.
- Warm nodes: once every job of the run is on the cluster, each idle node a job ran on gets one warm hold an idle
  spell (a pause pod pinned to it, not evictable by the autoscaler, no card asked, ended by its own deadline), billed
  to the hold's end; a stop drops the holds. Break: drop the `submitted is None` return in `hold_idle`. Break: drop
  the `held_at` check in `hold_idle`. Break: drop the safe-to-evict annotation in `manifests.warm_hold`. Break: count
  a hold pod as busy in `note_hosts`. Break: `gone = now + ...` in `last_seen_scale_down`. Break: drop `drop_holds`
  in `stop_run`.
- Never a lost row (#95): a look at the cluster that fails is tried POLL_RETRIES times more, then the run's row is
  booked from what was last seen (its node marked estimated) and the error goes on; a SIGTERM deletes every Job of
  the run, books its row with the unfinished jobs stopped and exits 143; either way the door still brings back what
  the done jobs made. Break: call `look` without `retried` in `watch`. Break: drop `book` from either except in
  `submit`. Break: drop `stop_jobs` in `stop_after_signal`. Break: drop `bring_back` before `raise` in
  `cluster_jobs.run`. Under SCORE_K8S_QUEUE a run goes to the box's queue (job_queue/) when it is fresh, else on
  today's path with a queue started for later runs; one whose queue went stale while it waited is cancelled there and
  its jobs not done adopted by `submitter.submit` (#76, S6). Break: `if not job_queue.fresh():` -> `if False:` in
  `cluster_jobs.through_queue` (no fallback). Break: adopt every spec, not only those not done. A queue not fresh
  is started and waited for, and the run goes on it, never beside it as a Job of its own (settle@airlock,
  2026-11-09). Break: `job_queue.come_up()` -> `job_queue.start()` in `through_queue`. A finish's card-then-processor
  classes go on the cluster as their first class's kind, so the queue does not refuse them (pixal@galley and
  pixal@camp, 2026-11-09). Break: drop `one_kind` in `cluster_jobs.run`. A job not finished is said with the queue's
  word for its run (refused, stopped), never a bare "never finished". Break: drop the `why` in `report_failure`. While it watches, the process is marked in CLUSTER_WAITING (its node holds no --jobs slot,
  score/graph), the mark gone after an error or a stop. Break: drop the `finally` unlink in `watch`. stop-batch's
  `stop_score_jobs` deletes only Jobs labelled with a run, only in score-jobs, and refuses another namespace.
  Break: drop the namespace check in `stop_score_jobs`.
- SCORE_CLOUD_KINDS narrows SCORE_CLOUD=k8s to its kinds; a runner naming none is known by its script's name.
  Break: `return True` in place of the kinds check in `provider.on_cluster`.
  The warm pool's collector refuses to rent, saying why, while the run's launch (its registry entry, or one it was
  resumed from) sends kinds to the cluster and its own environment sends none. Break: drop the `not refused` check
  in `pool.collect_round`.
- The Secrets hold the store and registry values by name; the GPU operator is pointed at the registry's copies
  (the manager with no pull secret of its own) and a mirrored cluster is left alone.
  Break: give the manager `imagePullSecrets` in `policy_patch`.
"""
import base64
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cluster_jobs  # noqa: E402
import keyed_jobs  # noqa: E402
import gpu_operator  # noqa: E402
import manifests  # noqa: E402
import submitter as submit  # noqa: E402
from score.store import Store, offload  # noqa: E402

POOLS = {"gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2", "cpu-32c-128gb"}


# ==== classes, Jobs and widening ====================================================================================

TENANT = {"key": "tenant", "operator": "Equal", "value": "score", "effect": "NoSchedule"}
CARDS = ["gpu-24gb", "gpu-48gb", "gpu-80gb"]
LONG_NAME = "score-" + "a" * 54 + "-g1"  # 'Run_2026-10-09T15:00' and 80 a's: the end kept, at 63 characters
REFUSED = "nor one that holds it"
DONE = ({"type": "Complete", "status": "True"}, True, "done")
FAILED_BEFORE_IT_RAN = ({"type": "Failed", "status": "True"}, False, "failed")  # a failure, never a wait to remake
EXPIRED_AFTER_IT_RAN = ({"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}, True, "failed")
# job: the job's spec, the cluster's pools and own taints, capacity's late classes, the Job's run and id, how its Job
# ends (whether its pod ran first); then what it takes: the kind it is known by, its classes in order, the late ones, its cards and
# the name of its last Job (each class added makes it again, and a wait past its deadline once more), or the refusal
CASES = {
    "pixal-capacitys-order-a-late-class": (dict(kind="pixal"), POOLS, (), {"pixal": ("gpu-48gb",)}, ("r", "j"), DONE,
                                           ("pixal", ["gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2"],
                                            {"gpu-48gb"}, 1, "score-r-j-g4")),
    "meshparts-capacitys-order": (dict(kind="meshparts"), POOLS, (), {}, ("r1", "part"), FAILED_BEFORE_IT_RAN,
                                  ("meshparts", ["gpu-24gb", "gpu-48gb", "gpu-80gb"], set(), 1, "score-r1-part-g3")),
    "own-classes-preferred-in-their-order": (dict(kind="pixal", classes=["gpu-80gb", "gpu-48gb"], attempt_limit=3),
                                             POOLS, (), {}, ("run-1", "take_7"), DONE,
                                             ("pixal", ["gpu-80gb", "gpu-48gb"], set(), 1, "score-run-1-take-7-g2")),
    "a-bake-never-takes-an-h100": (dict(kind="library", classes=CARDS), POOLS, (), {}, ("r", "j"),
                                   EXPIRED_AFTER_IT_RAN, ("library", ["gpu-24gb", "gpu-48gb"], set(), 1, "score-r-j-g2")),
    "a-bake-in-the-blender-image": (dict(kind="blender", capacity_kind="library", classes=CARDS, attempt_limit=1),
                                    POOLS, (), {}, ("Run_A", "Take_7"), DONE,
                                    ("library", ["gpu-24gb", "gpu-48gb"], set(), 1, "score-run-a-take-7-g2")),
    "a-processor-class-asks-no-card": (dict(kind="blender", classes=["cpu-32c-128gb"]), POOLS, (), {},
                                       ("run-1", "settle"), DONE,
                                       ("blender", ["cpu-32c-128gb"], set(), 0, "score-run-1-settle-g1")),
    "a-tenants-own-taint": (dict(kind="pixal", classes=["gpu-24gb"]), POOLS, (TENANT,), {},
                            ("Run_2026-10-09T15:00", "a" * 80), DONE, ("pixal", ["gpu-24gb"], set(), 1, LONG_NAME)),
    # no pool for any of a job's classes: the nearest pool that holds it (#76: settle's 4 cores, the paint's 16, 32)
    "settles-4-cores-on-the-32-core-pool": (dict(kind="blender", classes=["cpu-4c-32gb"]), POOLS, (), {}, ("r", "j"),
                                            DONE, ("blender", ["cpu-32c-128gb"], set(), 0, "score-r-j-g1")),
    "the-smallest-pool-that-holds-it": (dict(kind="blender", classes=["cpu-32c-64gb", "cpu-16c-64gb"]),
                                        POOLS | {"cpu-64c-256gb"}, (), {}, ("r", "j"), DONE,
                                        ("blender", ["cpu-32c-128gb"], set(), 0, "score-r-j-g1")),
    "a-card-pair-on-the-h100-pair": (dict(kind="pixal", classes=["gpu-24gb-x2"]), POOLS, (), {}, ("r", "j"), DONE,
                                     ("pixal", ["gpu-80gb-x2"], set(), 1, "score-r-j-g1")),
    "only-an-h100-pair-holds-it-never-blender": (dict(kind="blender", classes=["gpu-24gb-x2"]), POOLS, (), {},
                                                 ("r", "j"), DONE, REFUSED),
    "no-pool-holds-it": (dict(kind="blender", classes=["cpu-64c-256gb"]), POOLS, (), {}, ("r", "j"), DONE, REFUSED),
}
CANNOT_GROW = "pod didn't trigger scale-up: 1 in backoff after failed scale-up"


class RowCluster:
    """A cluster of the row's pools and own taints."""

    def __init__(self, pools, tolerations):
        self.pools, self.TOLERATIONS = pools, list(tolerations)

    def class_pools(self):
        return [{"class": name} for name in self.pools]


@pytest.mark.parametrize("given, pools, taints, late_classes, named, ends, expected", CASES.values(),
                         ids=CASES.keys())
def test_jobs_take_their_classes_in_order(given, pools, taints, late_classes, named, ends, expected, monkeypatch):
    """A run reads each job's classes (capacity's order, narrowed to the cluster's pools, else the nearest pool that
    holds them, never one its kind may not take), starts it on the first, and adds one class at a time only once the
    autoscaler said for the grace time that none can grow (a word before the last widening, about a taint, or followed
    by a scale-up does not count) or no node came for NODE_MINUTES while a pod waited, a late class after LATE_MINUTES;
    a Job that waited past its deadline is made again with the classes so far; that Job requires exactly them, prefers
    them in order, asks cards only on card classes and bears a Kubernetes name; the run is marked waiting until its job
    runs, and the job takes its Job's end and the node it ran on."""
    clock = [submit.parse_time("2026-10-09T14:00:00Z")]
    monkeypatch.setattr(submit.time, "time", lambda: clock[0])
    monkeypatch.setattr(submit.capacity, "LATE", late_classes)
    marks = []
    monkeypatch.setattr(submit.preflight, "mark_waiting", lambda: marks.append("waiting"))
    monkeypatch.setattr(submit.preflight, "unmark_waiting", lambda: marks.append("ran"))
    spec = dict(given, image="registry.example/score/score-pixal:1-abc@sha256:00", minutes=30)
    run_id, job_id = named
    kubectl = LiveKubectl()
    if expected == REFUSED:
        with pytest.raises(SystemExit, match=REFUSED):
            submit.Run(run_id, {job_id: spec}, kubectl, RowCluster(pools, taints))
        return
    kind, order, late, cards, name = expected
    run = submit.Run(run_id, {job_id: spec}, kubectl, RowCluster(pools, taints))
    assert list(run.kinds) == [kind] and run.orders[job_id] == (order, late)
    run.make(job_id)
    label = manifests.label_value(job_id)

    def look(seconds, words=(), waiting=True):
        """The cluster at `seconds`: the job's pod fitting no node (or none), the autoscaler's `words` on it (reason,
        message, when); the run reads it and widens. The classes it may take after."""
        clock[0] = seconds
        pod_name = manifests.job_name(run_id, job_id, run.jobs[job_id]["generation"]) + "-pod"
        kubectl.pods = [{"kind": "Pod", "metadata": {"name": pod_name, "labels": {"score.dev/job": label}}, "spec": {},
                         "status": {"conditions": [{"type": "PodScheduled", "status": "False",
                                                    "lastTransitionTime": time_text(seconds)}]}}] if waiting else []
        kubectl.events = [{"reason": reason, "involvedObject": {"name": pod_name}, "lastTimestamp": time_text(when),
                           "message": message} for reason, message, when in words]
        jobs, pods, no_grow = run.read()
        run.update_job(job_id, run.current(job_id, jobs), pods.get(label, []))
        run.widen(pods, no_grow)
        assert run.jobs[job_id]["state"] == "waiting"  # a Job with no word yet runs on
        return run.allowed(job_id)

    first = run.kinds[kind]["first"]
    for step in range(1, len(order) + 1):
        assert run.allowed(job_id) == order[:step] and run.jobs[job_id]["generation"] == step - 1, step
        since = run.kinds[kind]["since"]
        word = ("NotTriggerScaleUp", CANNOT_GROW, since)
        grace = since + submit.NO_GROW_GRACE_MINUTES * 60
        if step % 2:  # the autoscaler said none of the allowed pools can grow
            assert look(grace - 1, [word]) == order[:step]  # not for the grace time yet
            if step < len(order) and order[step] in late and grace < first + submit.capacity.LATE_MINUTES * 60:
                assert look(grace, [word]) == order[:step]  # a late class waits
                grace = first + submit.capacity.LATE_MINUTES * 60
            assert look(grace, [word]) == order[:step + 1], step  # one more class, or none left to add
            continue
        # no node came: the autoscaler's words that do not count, then NODE_MINUTES with a pod waiting
        assert look(grace, [("NotTriggerScaleUp", CANNOT_GROW, since - 1)]) == order[:step]  # said before widening
        noise = [("NotTriggerScaleUp", "pod didn't trigger scale-up: 8 max node group size reached", since + 10),
                 ("TriggeredScaleUp", "pod triggered scale-up", since + 20),
                 ("NotTriggerScaleUp", "pod didn't trigger scale-up: 1 node(s) had taint", since + 30)]
        node_time = since + submit.NODE_MINUTES * 60
        assert look(node_time - 1, noise) == order[:step]  # a scale-up followed; a taint is no word to widen
        assert look(node_time, waiting=False) == order[:step]  # nothing waits
        assert look(node_time) == order[:step + 1], step
    assert run.jobs[job_id]["generation"] == len(order) - 1  # nothing left to add: not made again
    submit.note_wait(run)  # no job ran yet: its runaway watch leaves the wait out
    assert marks == ["waiting"]

    expired = kubectl.jobs[manifests.job_name(run_id, job_id, len(order) - 1)]
    expired["status"] = {"conditions": [{"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}
    jobs, _pods, _no_grow = run.read()
    run.update_job(job_id, run.current(job_id, jobs), [])
    assert run.jobs[job_id]["state"] == "waiting" and run.jobs[job_id]["generation"] == len(order)  # made again
    assert manifests.job_name(run_id, job_id, len(order) - 1) in kubectl.deleted
    job = kubectl.jobs[name]
    assert job["metadata"]["annotations"]["score.dev/classes"] == ",".join(order)  # the earlier classes kept
    pod = job["spec"]["template"]["spec"]
    required = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
    assert required["nodeSelectorTerms"][0]["matchExpressions"][0]["values"] == order
    preferred = pod["affinity"]["nodeAffinity"]["preferredDuringSchedulingIgnoredDuringExecution"]
    assert [term["preference"]["matchExpressions"][0]["values"] for term in preferred] == [[each] for each in order]
    weights = [term["weight"] for term in preferred]
    assert weights == sorted(set(weights), reverse=True), weights  # the first weighs most, each less than the last
    assert {toleration["key"] for toleration in pod["tolerations"]} == {"nvidia.com/gpu", "score.dev/class"} | {
        taint["key"] for taint in taints} and all(taint in pod["tolerations"] for taint in taints)
    container = pod["containers"][0]
    card_ask = {"nvidia.com/gpu": str(cards)} if cards else {}
    assert container["resources"]["limits"] == dict(manifests.NO_LIMIT, **card_ask)  # past any node's
    assert container["resources"]["requests"].get("nvidia.com/gpu") == card_ask.get("nvidia.com/gpu")
    assert container["args"] == [run_id, job_id]
    assert {"name": "cache", "mountPath": "/cache"} in container["volumeMounts"]
    assert pod["volumes"][0]["hostPath"]["path"] == "/var/lib/score-cache"
    assert pod["restartPolicy"] == "Never" and job["spec"]["backoffLimit"] == spec.get("attempt_limit", 3) - 1
    assert job["metadata"]["name"] == name and len(name) <= 63  # Kubernetes' name rules

    condition, ran, state = ends
    node = f"node-{order[-1]}" if ran else None  # stock came back on its last class
    kubectl.pods = [{"kind": "Pod", "metadata": {"name": "p", "labels": {"score.dev/job": label}},
                     "spec": {"nodeName": node},
                     "status": {"containerStatuses": [{"state": {"running": {"startedAt": time_text(clock[0])}}}]}}
                    ] if ran else []
    jobs, pods, _no_grow = run.read()
    run.update_job(job_id, run.current(job_id, jobs), pods.get(label, []))
    submit.note_wait(run)  # its job runs on a node now: its minutes count
    assert marks == ["waiting", "ran" if ran else "waiting"]
    job["status"] = {"conditions": [condition]}
    jobs, pods, _no_grow = run.read()
    run.update_job(job_id, run.current(job_id, jobs), pods.get(label, []))
    assert run.jobs[job_id]["state"] == state and run.jobs[job_id]["node"] == node
    assert run.jobs[job_id]["generation"] == len(order)  # a failed Job, or one that ran past its deadline, is never made again


class FakeCluster:
    """A cluster module that records the caps it is given."""
    KUBECONFIG = "/dev/null"

    def __init__(self):
        self.caps = []

    def cap_pools(self, euros_left, hours):
        self.caps.append((euros_left, hours))
        return {}


class PoolCluster(FakeCluster):
    def class_pools(self):
        return [{"class": name} for name in POOLS]


class FakeKubectl:
    """kubectl answering with fixed Jobs, and recording what is applied."""

    def __init__(self, items):
        self.items, self.applied = items, []

    def json(self, *arguments):
        return {"items": self.items if arguments[1] == "jobs,pods" else []}

    def apply(self, objects):
        self.applied += objects


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


class NoQuotaKubectl(LiveKubectl):
    """A login whose Role has no resourcequotas right: the read is forbidden, as on the tenant's scoped login."""

    def json(self, *arguments):
        if arguments[1] == "resourcequota":
            raise submit.subprocess.CalledProcessError(
                1, ["kubectl", *arguments], stderr='Error from server (Forbidden): resourcequotas is forbidden: User '
                                                   '"system:serviceaccount:score:score-conductor" cannot list resource')
        return super().json(*arguments)


class QuotaKubectl(LiveKubectl):
    """A cluster with one ResourceQuota on the jobs' namespace, its hard and used as the test sets them."""

    def __init__(self, hard, used):
        super().__init__()
        self.hard, self.used = hard, used

    def json(self, *arguments):
        if arguments[1] == "resourcequota":
            return {"items": [{"spec": {"hard": self.hard}, "status": {"hard": self.hard, "used": self.used}}]}
        return super().json(*arguments)


def time_text(seconds):
    return submit.datetime.datetime.fromtimestamp(seconds, submit.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_resume_takes_up_the_newest_generation_and_a_run_holds_to_its_parallel_jobs():
    spec = {"kind": "library", "image": "image", "minutes": 5}
    made = manifests.job(spec, "r1", "bake", ["gpu-24gb", "gpu-48gb"], 1, generation=2)
    run = submit.Run("r1", {"bake": spec, "other": spec}, FakeKubectl([made]), PoolCluster())
    run.resume()
    assert run.jobs["bake"]["generation"] == 2 and run.jobs["bake"]["submitted"]
    assert run.jobs["other"]["submitted"] is None and run.allowed("other") == ["gpu-24gb", "gpu-48gb"]

    spec = {"kind": "pixal", "image": "image", "minutes": 30, "classes": ["gpu-24gb"]}
    kubectl = LiveKubectl()
    run = submit.Run("r1", {f"take-{number}": spec for number in range(5)}, kubectl, PoolCluster())
    submit.submit_more(run, 2)
    assert len(kubectl.jobs) == 2
    run.jobs["take-0"]["state"] = "done"
    submit.submit_more(run, 2)
    assert len(kubectl.jobs) == 3
    submit.submit_more(run, None)
    assert len(kubectl.jobs) == 5
    longest = manifests.deadline_seconds({**spec, "minutes": 90})
    takes = {**run.specs, "take-4": {**spec, "minutes": 90}}
    assert submit.declared_seconds(takes, 2) == 3 * longest and submit.declared_seconds(takes, None) == longest

    # quota admission (#76): the tenant's quota by its own names, 2 of its 24 cards left; 5 card jobs make 2, hold 3
    kubectl = QuotaKubectl({"requests.cpu": "250", "requests.memory": "1200Gi", "requests.nvidia.com/gpu": "24"},
                           {"requests.cpu": "66070m", "requests.memory": "440Gi", "requests.nvidia.com/gpu": "22"})
    run = submit.Run("r2", {f"take-{number}": {"kind": "pixal", "image": "image", "minutes": 30}
                            for number in range(5)}, kubectl, PoolCluster())
    submit.submit_more(run, None)
    assert len(kubectl.jobs) == 2 and sum(record["submitted"] is None for record in run.jobs.values()) == 3
    kubectl.events = [{"reason": "FailedCreate", "involvedObject": {"kind": "Job", "name": name},
                       "message": "Error creating: pods is forbidden: exceeded quota: score-jobs"}
                      for name in kubectl.jobs]
    run.kinds["pixal"]["since"] -= (submit.NODE_MINUTES + 1) * 60
    _jobs, pods, no_grow = run.read()
    run.widen(pods, no_grow)
    assert run.kinds["pixal"]["step"] == 1  # a refused pod is no word that the classes cannot be had
    kubectl.used["requests.nvidia.com/gpu"] = "23"  # the 2 made counted, one card freed elsewhere
    submit.submit_more(run, None)
    assert len(kubectl.jobs) == 3
    # a login that may not read the quota (the conductor's scoped one): every Job goes, as before the quota check
    kubectl = NoQuotaKubectl()
    run = submit.Run("r3", {f"take-{number}": {"kind": "pixal", "image": "image", "minutes": 30}
                            for number in range(5)}, kubectl, PoolCluster())
    submit.submit_more(run, None)
    assert len(kubectl.jobs) == 5


def test_nothing_goes_on_the_cluster_outside_a_cleared_run(monkeypatch):
    monkeypatch.delenv(submit.compute.TICKET, raising=False)
    cluster = FakeCluster()
    kubectl = FakeKubectl([])
    with pytest.raises(submit.compute.Refused, match="nothing rents outside a cleared run"):
        submit.prepare(kubectl, cluster)
    assert cluster.caps == [] and kubectl.applied == []

    # under the owner's override a run is stopped at what is left of his euros less 10%, read again each look
    # (labval-motor-20261106, 2026-11-06: EUR 2.47 left, and only the EUR 60 batch cap was checked)
    room = {"name": "labval", "euros": 40.0, "spent": 37.53, "left": 2.47}
    monkeypatch.setenv(submit.compute.TICKET, "override labval")
    monkeypatch.setattr(submit.compute, "override_room", lambda store=None: room)
    monkeypatch.setattr(submit, "poll", lambda run: None)

    class StoppingKubectl(LiveKubectl):
        def run(self, *arguments):
            return ""
    run = submit.Run("r1", {"bake": {"kind": "judge", "image": "image", "minutes": 5}}, StoppingKubectl(),
                     PoolCluster())
    run.make("bake")
    live = [2.0]
    run.live_euros = lambda: live[0]
    submit.look(run, None)
    assert run.unfinished() == ["bake"] and run.cluster.caps == []  # EUR 2.00 fits EUR 2.25 (2.47 less 10%)
    live[0] = 2.3
    submit.look(run, None)
    assert run.unfinished() == [] and run.jobs["bake"]["state"] == "stopped" and run.kubectl.deleted
    assert run.cluster.caps == [(0, 1)]  # its pools capped to nothing, as at the batch cap
    assert "labval" in submit.over_limits(run)
    room["left"] = 100.0
    assert submit.over_limits(run) is None  # more left than the batch cap: the EUR 60 cap stands


# ==== the runners' door =============================================================================================

class Helper:
    """The runtime's submit side over a folder store, with a fixed image."""

    def __init__(self, store_folder):
        self.real = cluster_jobs.submitter.runtime()
        self.store = self.real.stores.FolderStore(store_folder)

    def __getattr__(self, name):
        return getattr(self.real, name)

    def cloud_store(self):
        return self.store

    def image(self, kind):
        return f"registry.example/score-{kind}:1@sha256:00"


class CountedCopies(offload.FolderBucket):
    """The store bucket as a folder, counting the copies made inside it into a job store."""

    copies = 0

    def copy_into(self, key, target, target_key):
        CountedCopies.copies += 1
        super().copy_into(key, target, target_key)


def test_inputs_go_up_at_their_paths_and_outputs_come_back_where_the_runner_wants_them(tmp_path, monkeypatch):
    helper = Helper(tmp_path / "store")
    monkeypatch.setattr(cluster_jobs.submitter, "runtime", lambda: helper)
    seen, uploads, fetches = {}, [], []
    real_upload = helper.store.upload
    monkeypatch.setattr(helper.store, "upload", lambda source, key: (uploads.append(key), real_upload(source, key)))
    kept = Store.in_folder(tmp_path / "home")  # the framework's store: one output whose only blob is evicted
    made = tmp_path / "made"
    made.mkdir()
    (made / "lamp.usda").write_text("lamp")
    output = kept.put_tree(made)
    sha = kept.listing(output)["lamp.usda"]
    bucket = CountedCopies(tmp_path / "bucket")
    offload.push(kept.objects.root / "blobs" / sha, sha, bucket)
    offload.evict(kept.objects.root, sha, 4)
    monkeypatch.setattr(cluster_jobs, "framework_store", lambda: kept)
    monkeypatch.setitem(offload.OPENER, "bucket", bucket)
    real_fetched = offload.fetched
    monkeypatch.setattr(offload, "fetched", lambda *args: (fetches.append(args), real_fetched(*args))[1])

    def submit_run(run, specs, store, wait_scale_down=True, who=None, parallel=None):
        """What the cluster would leave: each output and done.json, except job 1, which fails."""
        seen.update(specs=specs, wait=wait_scale_down, who=who, run=run)
        for job_id, spec in specs.items():
            prefix = f"runs/{run}/{job_id}/"
            if job_id == "1":
                store.write_bytes(prefix + "failed-1.json", json.dumps({"stage": "command", "error": "1"}).encode())
                continue
            uploaded = []
            for output in spec["outputs"]:
                key = output["key"] + ("/part/a.txt" if output["path"].endswith("folder") else "")
                store.write_bytes(key, f"made by {job_id}".encode())
                uploaded.append(key)
            store.write_bytes(prefix + "done.json", json.dumps({"outputs": uploaded, "timings": {}}).encode())
    monkeypatch.setattr(cluster_jobs.submitter, "submit", submit_run)
    stage = tmp_path / "in" / "stage"
    (stage / "textures").mkdir(parents=True)
    (stage / "place.usda").write_text("usda")
    (stage / "textures" / "wall.png").write_text("png")
    single = tmp_path / "in" / "job.json"
    single.write_text("{}")
    linked = tmp_path / "in" / "linked"  # a home whose folder links to another, as a frozen home's models do
    linked.symlink_to(stage / "textures")
    out_file, out_folder = tmp_path / "out" / "result.json", tmp_path / "out" / "folder"
    making = tmp_path / "frozen.home" / "making"  # a frozen run's home: its store a link to the store
    making.parent.mkdir()
    (tmp_path / "in").joinpath("making").mkdir()
    making.symlink_to(tmp_path / "in" / "making")
    (making / "views.json").write_text("{}")  # a fresh scratch file the make wrote, named by the command
    evicted = {"local": str(kept.cache / "checkouts" / output), "path": "/work/in/lamp"}  # no checkout on disk
    jobs = [{"command": ["true"], "code": ["tools/cloud/k8s"], "inputs": [str(stage), str(single), str(linked), evicted,
                                                                   str(making / "views.json")],
             "outputs": [str(out_file), str(out_folder), str(making / "folder")], "minutes": 3, "kernel_cache": "blender-5.0.1"},
            {"command": ["false"], "code": ["tools/cloud/k8s"], "inputs": [], "outputs": [], "minutes": 3}]
    assert cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"]) == [1]
    assert seen["wait"] is False and seen["who"] == "test"
    spec = seen["specs"]["0"]
    assert spec["image"].startswith("registry.example/score-blender") and spec["classes"] == ["gpu-24gb"]
    assert spec["kernel_cache"] == "blender-5.0.1" and spec["minutes"] == 3
    assert sorted(entry["path"] for entry in spec["inputs"]) == sorted(
        [str(stage / "place.usda"), str(stage / "textures/wall.png"), str(single), str(linked / "wall.png"),
         "/work/in/lamp/lamp.usda", str(making / "views.json")])
    assert spec["outputs"][2]["path"] == str(making / "folder")  # its folder made as named before the command:
    made_first = spec["command"][2].split(" && ")[0].split()
    assert made_first[:2] == ["mkdir", "-p"] and str(making) in made_first and spec["command"][4:] == ["true"]
    assert all(entry["key"].startswith("inputs/") for entry in spec["inputs"]) and len(uploads) == 3
    assert helper.store.read_bytes(f"inputs/{sha}") == b"lamp"  # copied inside the object storage
    assert CountedCopies.copies == 1 and not fetches and not (kept.objects.root / "blobs" / sha).exists()
    assert out_file.read_text() == "made by 0" and (out_folder / "part" / "a.txt").read_text() == "made by 0"
    assert (making / "folder" / "part" / "a.txt").read_text() == "made by 0"

    def watch_lost(run, specs, store, wait_scale_down=True, who=None, parallel=None):
        """Job 0 finished, then the watch failed (#95)."""
        submit_run(run, specs, store, wait_scale_down, who, parallel)
        raise RuntimeError("the control plane did not answer")
    monkeypatch.setattr(cluster_jobs.submitter, "submit", watch_lost)
    out_file.unlink()
    with pytest.raises(RuntimeError, match="did not answer"):
        cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"])
    assert out_file.read_text() == "made by 0"  # what finished still came back
    assert len(uploads) == 3 and CountedCopies.copies == 1  # the second run of the same inputs sent nothing

    # Under SCORE_K8S_QUEUE: a queue not fresh at submit time is started for later runs and the run goes on today's
    # path; a queue gone stale while the run waits gives it back, cancelled there, its jobs not done adopted by
    # submitter.submit under the run's own name (its Jobs' labels), a job the queue's worker finished not made again.
    monkeypatch.setenv("SCORE_K8S_QUEUE", "1")
    root, started = tmp_path / "queue", []
    monkeypatch.setattr(cluster_jobs.job_queue, "QUEUE", root)
    monkeypatch.setattr(cluster_jobs.job_queue, "start", lambda root=None: started.append(True))
    monkeypatch.setattr(cluster_jobs.job_queue, "QUEUE_START_SECONDS", 0)  # a queue that does not come up
    monkeypatch.setattr(cluster_jobs.submitter, "submit", submit_run)
    monkeypatch.setattr(cluster_jobs.submitter, "prepare", lambda kubectl, cluster: None)
    monkeypatch.setattr(cluster_jobs.submitter, "cluster_module", lambda: None)
    monkeypatch.setattr(cluster_jobs.submitter, "cluster_kubectl", lambda cluster: None)
    monkeypatch.setattr(cluster_jobs.submitter.compute, "require_cleared", lambda what: None)

    def worked_then_stale(run, root=None, **_):
        """The queue's worker finished job 0 of the run it was handed, then the queue's beat stopped."""
        handed = json.loads((cluster_jobs.job_queue.QUEUE / "inbox" / f"{run}.json").read_text())["specs"]
        submit_run(run, {"0": handed["0"]}, helper.store)
        raise cluster_jobs.job_queue.Stale(f"the queue has been stale 180 s; run {run} taken back")
    monkeypatch.setattr(cluster_jobs.job_queue, "wait", worked_then_stale)
    out_file.unlink()
    assert cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"], name="stale-run") == [1]
    assert started and sorted(seen["specs"]) == ["0", "1"] and not (root / "inbox").exists()
    root.mkdir(exist_ok=True)
    (root / "beat").touch()
    out_file.unlink()
    assert cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"], name="taken-run") == [1]
    assert sorted(seen["specs"]) == ["1"] and seen["run"] == "taken-run" and (root / "cancel" / "taken-run").exists()
    assert out_file.read_text() == "made by 0" and len(started) == 1  # job 0's outputs, made on the queue

    # A queue just started is waited for, not gone around (settle@airlock, 2026-11-09, a Job of its own beside the
    # queue's workers); a finish's card-then-processor classes reach it as one kind, the cards (pixal@galley and
    # pixal@camp, 2026-11-09: the whole mix refused, "job 0 never finished"); a job not finished is said with the
    # queue's word for its run.
    def beats(root=None):
        started.append(True)
        (root or cluster_jobs.job_queue.QUEUE).joinpath("beat").touch()
    monkeypatch.setattr(cluster_jobs.job_queue, "start", beats)
    monkeypatch.setattr(cluster_jobs.job_queue, "QUEUE_START_SECONDS", 45)
    said, words = [], {}
    monkeypatch.setattr(cluster_jobs.submitter, "say", said.append)

    def queue_takes(run, root=None, **_):
        """The queue's intake (job_cards refuses a mix whole, as refuse_entry writes it), then its worker's job 0."""
        entry = json.loads((cluster_jobs.job_queue.QUEUE / "inbox" / f"{run}.json").read_text())
        words.update(classes=entry["classes"])
        try:
            [cluster_jobs.submitter.job_cards(spec, entry["classes"]) for spec in entry["specs"].values()]
        except SystemExit as error:
            return {"run": run, "over": True, "refused": f"refused by the queue: SystemExit: {error}",
                    "jobs": {job_id: {"state": "failed"} for job_id in entry["specs"]}}
        submit_run(run, {"0": entry["specs"]["0"]}, helper.store)
        return {"run": run, "over": True, "stopped": "stop line EUR 1.00 reached at EUR 1.02",
                "jobs": {"0": {"state": "done"}, "1": {"state": "stopped"}}}
    monkeypatch.setattr(cluster_jobs.job_queue, "wait", queue_takes)
    direct = []
    monkeypatch.setattr(cluster_jobs.submitter, "submit", lambda run, *args, **kwargs: direct.append(run))
    (root / "beat").unlink()
    finish = ["gpu-24gb", "gpu-48gb", "cpu-16c-64gb", "cpu-32c-128gb"]  # pixal_row.FINISH_CLASSES
    for case in ("galley", "camp"):
        out_file.unlink()
        assert cluster_jobs.run("blender", jobs, who="test", classes=finish, name=f"finish-{case}") == [1], said
        assert words["classes"] == ["gpu-24gb", "gpu-48gb"] and not direct  # on the queue, never beside it
        assert out_file.read_text() == "made by 0" and said[-1] == (
            "job 1 never finished: stop line EUR 1.00 reached at EUR 1.02"), said
        (root / "beat").unlink()
    assert len(started) == 3 and cluster_jobs.one_kind(["cpu-16c-64gb", "gpu-24gb"]) == ["cpu-16c-64gb"]

    # A client stopped while it waits on the queue (SIGTERM: stop-batch, a stopped run) cancels its run there, so the
    # queue deletes the workers on its jobs and assigns none again (2026-11-10: checkout 75's stopped runs kept 4 L4
    # workers on their meshparts jobs for hours); what finished still comes back. Break: drop the
    # `except BaseException` cancel in `through_queue`; break: drop its `stopped_on_signal()`.
    def stopped_wait(run, root=None, **_):
        submit_run(run, {"0": json.loads((root_of_queue() / "inbox" / f"{run}.json").read_text())["specs"]["0"]},
                   helper.store)
        os.kill(os.getpid(), signal.SIGTERM)
        raise AssertionError("the SIGTERM did not stop the wait")
    root_of_queue = lambda: cluster_jobs.job_queue.QUEUE  # noqa: E731
    monkeypatch.setattr(cluster_jobs.job_queue, "wait", stopped_wait)
    handler = signal.getsignal(signal.SIGTERM)
    out_file.unlink()
    with pytest.raises(cluster_jobs.submitter.Stopped):
        cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"], name="stopped-run")
    assert (root / "cancel" / "stopped-run").exists() and out_file.read_text() == "made by 0"
    assert signal.getsignal(signal.SIGTERM) is handler

    def resumable(run, specs, store, wait_scale_down=True, who=None, parallel=None):
        """A named run: a job whose done.json is there is not run again; each job writes its own command."""
        for job_id, spec in specs.items():
            prefix = f"runs/{run}/{job_id}/"
            command = spec["command"][-1]  # the job's own, after its output folders are made
            if not store.exists(prefix + "done.json") and command != "fails":
                store.write_bytes(spec["outputs"][0]["key"], command.encode())
                store.write_bytes(prefix + "done.json", json.dumps({"outputs": [spec["outputs"][0]["key"]]}).encode())
    monkeypatch.setattr(cluster_jobs.submitter, "submit", resumable)
    videos = {name: tmp_path / "keyed" / name for name in ("a", "b")}
    keyed = lambda name, command: {"command": [command], "code": [], "inputs": [], "outputs": [str(videos[name])],
                                   "minutes": 3}
    assert keyed_jobs.run("gemx", "base", [keyed("a", "made a"), keyed("b", "fails")], "test", ["gpu-24gb"],
                          name="resumed") == [1]
    assert keyed_jobs.run("gemx", "base", [keyed("b", "made b")], "test", ["gpu-24gb"], name="resumed") == []
    assert videos["b"].read_text() == "made b"  # its own job, never the earlier run's first

    # A job reading a take's faces may run FACE_MINUTES more a million of them (wreck crashed_rocket_front, 953,008
    # faces, cut at its declared 3.5 min, 2026-11-08); one reading none keeps its runner's minutes (job 0's 3 above).
    import numpy as np
    take = tmp_path / "in" / ".bake-take-parts" / "take"
    take.mkdir(parents=True)
    np.save(take / "parts.npy", np.zeros(200_000, dtype=np.int8))
    bake = {"command": ["true"], "code": [], "inputs": [str(take.parent)], "outputs": [], "minutes": 3.5}
    spec = cluster_jobs.spec_of(helper, helper.store, "faces", "0", "blender", "blender", ["gpu-24gb"], bake)[0]
    assert spec["minutes"] == pytest.approx(3.5 + cluster_jobs.FACE_MINUTES * 0.2), spec["minutes"]


# ==== billing =======================================================================================================

class PricedCluster(PoolCluster):
    def price(self, machine_type, zone):
        return 0.013125, 1


def test_a_runs_nodes_are_billed_from_its_start_and_only_its_own(monkeypatch, tmp_path):
    spec = {"kind": "judge", "image": "image", "minutes": 5}
    run = submit.Run("r1", {"ask": spec}, FakeKubectl([]), PricedCluster())
    run.started = 10_000.0
    run.jobs["ask"].update(node="warm", ran=10_030.0, state="done")
    run.nodes["warm"] = {"class": "gpu-80gb", "type": "H100-1-80G", "zone": "fr-par-2", "cards": 1,
                         "created": 4_000.0, "ready": 4_200.0, "deleted": 10_600.0, "jobs": set()}
    machine, = submit.node_machines(run, "judge")
    assert machine["created"] == 10_000.0 and machine["ready"] == 10_000.0  # its earlier minutes are other runs'
    row = submit.ledger.machine_row(machine)
    assert row["start_wait_minutes"] == 0 and row["minutes"] == 10

    run = submit.Run("r1", {"ask": spec}, FakeKubectl([]), PricedCluster())
    run.started = 10_000.0
    run.jobs["ask"].update(node="first", ran=10_200.0, state="done")
    for name in ("first", "second"):
        run.nodes[name] = {"class": "gpu-80gb", "type": "H100-1-80G", "zone": "fr-par-2", "cards": 1,
                           "created": 10_060.0, "ready": 10_150.0, "deleted": 10_660.0, "jobs": set()}
    run.nodes["other-run"] = dict(run.nodes["first"], created=9_000.0)
    run.nodes["side-by-side"] = dict(run.nodes["first"], hosted=True)
    assert sorted((machine["node"], machine["unused"]) for machine in submit.node_machines(run, "judge")) == [
        ("first", False), ("second", True)]

    # runs side by side (2026-11-07: a settle run of one job booked all 23 nodes the cluster grew for 20 runs' pods,
    # EUR 2.90): each run books its part of a node, by the time its pods held it, or of an unused node by the pods
    # that waited for it; between them the runs book every node whole, never less
    class PodsKubectl(FakeKubectl):
        def json(self, *arguments):
            return {"items": self.items if arguments[1] == "pods" else []}

    def pod(run_id, name, node=None, start=None, end=None, made=0.0, placed=None, wants="gpu-24gb"):
        status = {"phase": "Succeeded" if end else ("Running" if node else "Pending"), "conditions": []}
        if start:
            status["startTime"] = time_text(start)
        if end:
            status["containerStatuses"] = [{"state": {"terminated": {"finishedAt": time_text(end)}}}]
        if placed:
            status["conditions"].append({"type": "PodScheduled", "status": "True",
                                         "lastTransitionTime": time_text(placed)})
        return {"metadata": {"name": name, "creationTimestamp": time_text(made),
                             "labels": {"score.dev/run": run_id}},
                "spec": {"nodeName": node, "affinity": manifests.affinity([wants])}, "status": status}

    def side_by_side(run_id, started, pods):
        """Run `run_id`'s part of each node, the cluster's pods as `pods`."""
        found = submit.Run(run_id, {"ask": spec}, PodsKubectl(pods), PricedCluster())
        found.started = started
        for name, created, deleted, machine_class in (
                ("shared", 9_900.0, 10_900.0, "gpu-24gb"), ("grown-0", 10_950.0, 11_500.0, "gpu-24gb"),
                ("grown-1", 11_000.0, 11_500.0, "gpu-24gb"), ("vain", 11_000.0, 11_500.0, "gpu-48gb")):
            found.nodes[name] = {"class": machine_class, "type": "L4-1-24G", "zone": "fr-par-2", "cards": 1,
                                 "created": created, "ready": None, "deleted": deleted, "jobs": set()}
        found.note_hosts()
        return {name: found.share(name, seen) for name, seen in found.nodes.items()}
    pods = [pod("r-a", "a", "shared", 10_000.0, 10_300.0, made=9_990.0, placed=10_000.0),
            pod("r-b", "b", "shared", 10_200.0, 10_600.0, made=10_150.0, placed=10_200.0),
            pod("r-c", "c-0", made=10_900.0), pod("r-c", "c-1", made=10_900.0),  # waiting: grown-0, grown-1 for them
            pod("r-a", "a-late", made=11_100.0),  # made after both came up: grew neither
            pod("r-b", "b-vain", made=10_950.0, wants="gpu-48gb"),  # both waited for vain, which neither took
            pod("r-d", "d-vain", made=10_980.0, wants="gpu-48gb")]
    a_parts, b_parts = side_by_side("r-a", 10_000.0, pods), side_by_side("r-b", 10_150.0, pods)
    c_parts, d_parts = side_by_side("r-c", 10_850.0, pods), side_by_side("r-d", 10_900.0, pods)
    assert a_parts["shared"] == pytest.approx(250 / 900)  # alone 200 s, half of 100 s; the tail is b's
    assert b_parts["shared"] == pytest.approx(650 / 750)  # its window from its start: half of 100 s, then all
    assert a_parts["shared"] * 900 + b_parts["shared"] * 750 == pytest.approx(900)  # whole between them
    assert a_parts["grown-0"] == a_parts["grown-1"] == a_parts["vain"] == 0  # grown for others: none of a's
    assert c_parts["grown-0"] == c_parts["grown-1"] == 1  # its two pods were all that waited for them
    assert b_parts["vain"] == d_parts["vain"] == 0.5  # two runs' pods waited for it: half each, whole between them
    assert c_parts["vain"] == b_parts["grown-0"] == d_parts["grown-1"] == 0
    assert a_parts["vain"] + b_parts["vain"] + c_parts["vain"] + d_parts["vain"] >= 1  # never less than whole
    rows = [submit.ledger.machine_row(machine) for machine in submit.node_machines(run, "judge")]
    assert all(row.get("share", 1.0) == 1.0 for row in rows)  # a node of this run alone: booked whole as before
    machine = dict(run.nodes["first"], created=10_000.0, deleted=10_900.0, price=0.01, unit_minutes=1, share=0.25)
    assert submit.ledger.machine_row(machine)["euros"] == pytest.approx(15 * 0.01 * 0.25)

    # warm nodes (owner, 2026-11-06): once every job is on the cluster, an idle node a job ran on is held WARM_MINUTES
    # by a pause pod the autoscaler may not evict, asking no card; once an idle spell; billed to its hold's end
    clock = [50_000.0]
    monkeypatch.setattr(submit.time, "time", lambda: clock[0])

    class NodesKubectl(LiveKubectl):
        def __init__(self):
            super().__init__()
            self.nodes, self.all_pods, self.ran = [], [], []

        def json(self, *arguments):
            if arguments[1] == "nodes":
                return {"items": self.nodes}
            if arguments[1] == "pods":
                return {"items": self.all_pods}
            return super().json(*arguments)

        def run(self, *arguments):
            self.ran.append(arguments)
            return ""

    class NodedCluster(PricedCluster):
        TOLERATIONS = [{"key": "tenant", "operator": "Equal", "value": "score", "effect": "NoSchedule"}]

        def nodes(self):
            return [{"name": "kosmos-node", "type": "POP2-32C-128G", "zone": "pl-waw-2", "created": 100.0}]
    kubectl = NodesKubectl()
    kubectl.nodes = [{"metadata": {"name": name, "creationTimestamp": "2026-11-06T10:00:00Z",
                                   "labels": {"score.dev/class": "gpu-24gb", "kubernetes.io/hostname": f"host-{name}"}},
                      "status": {"conditions": []}} for name in ("l4-a", "l4-b")]
    # beside them: a node without zone labels (the provider's record gives them), the conductor's node (its class key
    # no capability class: no class node, never a crash) and a node seen before its labels came (motor-labval,
    # 2026-11-08: "no price for ? in ?"), its type and zone taken once they come
    early = {"metadata": {"name": "early-node", "creationTimestamp": "2026-11-08T19:16:00Z",
                          "labels": {"score.dev/class": "gpu-24gb"}}, "status": {"conditions": []}}
    kubectl.nodes += [
        {"metadata": {"name": "kosmos-node", "creationTimestamp": "2026-10-09T14:50:00Z",
                      "labels": {"score.dev/class": "cpu-32c-128gb"}},
         "status": {"conditions": [{"type": "Ready", "status": "True", "lastTransitionTime": "2026-10-09T14:50:13Z"}]}},
        {"metadata": {"name": "conductor-node", "creationTimestamp": "2026-11-07T10:00:00Z",
                      "labels": {"score.dev/class": "conductor"}}, "status": {"conditions": []}},
        early]
    run = submit.Run("r-warm", {"one": spec, "two": spec}, kubectl, NodedCluster())
    run.jobs["one"].update(node="l4-a", ran=49_000.0, state="done", submitted=48_000.0)
    job_pod = lambda node, phase: {"metadata": {"labels": {"score.dev/job": "two"}}, "spec": {"nodeName": node},
                                   "status": {"phase": phase}}
    kubectl.all_pods = [job_pod("l4-a", "Succeeded"), job_pod("l4-b", "Running")]
    run.watch_nodes()
    seen = run.nodes["kosmos-node"]
    assert (seen["type"], seen["zone"], seen["created"]) == ("POP2-32C-128G", "pl-waw-2", 100.0)
    assert "conductor-node" not in run.nodes
    early["metadata"]["labels"].update({submit.INSTANCE_LABEL: "l4-1-24g", submit.ZONE_LABEL: "fr-par-2"})
    submit.hold_idle(run)
    assert kubectl.jobs == {}  # a job still to put on takes the idle node: no hold
    run.jobs["two"].update(node="l4-b", ran=49_500.0, submitted=49_400.0)
    submit.hold_idle(run)
    hold, = kubectl.jobs.values()  # l4-a idle, l4-b busy with job two
    pod = hold["spec"]["template"]
    assert pod["metadata"]["annotations"] == {"cluster-autoscaler.kubernetes.io/safe-to-evict": "false"}
    assert pod["spec"]["nodeSelector"] == {"kubernetes.io/hostname": "host-l4-a"}
    assert "nvidia.com/gpu" not in pod["spec"]["containers"][0]["resources"]["requests"]  # the next job's card free
    assert NodedCluster.TOLERATIONS[0] in pod["spec"]["tolerations"]
    assert hold["spec"]["activeDeadlineSeconds"] == submit.WARM_MINUTES * 60  # it ends by itself
    assert hold["metadata"]["labels"]["score.dev/run"] == "r-warm" and len(hold["metadata"]["name"]) <= 63
    clock[0] += 60
    run.watch_nodes()
    submit.hold_idle(run)
    assert len(kubectl.jobs) == 1  # one hold an idle spell
    assert (run.nodes["early-node"]["type"], run.nodes["early-node"]["zone"]) == ("L4-1-24G", "fr-par-2")
    kubectl.all_pods = [job_pod("l4-a", "Running"), job_pod("l4-b", "Succeeded")]
    clock[0] += 60
    run.watch_nodes()
    submit.hold_idle(run)
    assert len(kubectl.jobs) == 2  # l4-b idle now; l4-a busy again
    kubectl.all_pods = [job_pod("l4-a", "Succeeded"), job_pod("l4-b", "Succeeded"),
                        {"metadata": {"labels": {"score.dev/warm": "hold"}}, "spec": {"nodeName": "l4-b"},
                         "status": {"phase": "Running"}}]
    clock[0] += 60
    run.watch_nodes()
    submit.hold_idle(run)
    assert len(kubectl.jobs) == 3 and not run.nodes["l4-b"]["busy"]  # a hold is no job: l4-a held again
    submit.last_seen_scale_down(run)
    assert run.nodes["l4-a"]["deleted"] == clock[0] + (submit.WARM_MINUTES + submit.IDLE_ESTIMATE_MINUTES) * 60
    run.nodes["l4-a"]["deleted"] = None
    submit.stop_run(run, "the batch cap")
    assert kubectl.ran == [("delete", "jobs", "-n", manifests.NAMESPACE, "-l", "score.dev/run=r-warm,score.dev/warm",
                            "--ignore-not-found", "--wait=false", "--cascade=background")]
    submit.last_seen_scale_down(run)
    assert run.nodes["l4-a"]["deleted"] == clock[0] + submit.IDLE_ESTIMATE_MINUTES * 60  # a stop ends the holds
    monkeypatch.undo()

    # never a lost row (#95): a look that keeps failing is retried, then the row is booked from the last look
    def unreachable():
        raise subprocess.CalledProcessError(1, ["kubectl"], stderr="kubectl get jobs,pods: connection refused")
    booked, error, deleted, looks = a_watched_run(tmp_path, monkeypatch, unreachable)
    assert isinstance(error, subprocess.CalledProcessError) and len(looks) == 1 + submit.POLL_RETRIES + 1
    # its own failure deletes its Jobs too (nothing brings their outputs back now), and while it watched it marked
    # them alive for cap_watch's sweep (2026-11-10: a stopped Buy's Jobs ran on for hours). Break: drop
    # `delete_run_jobs(run)` from submit's `except BaseException`; break: drop the `beat_alive` in `watch`.
    assert ("delete", "jobs", "-n", manifests.NAMESPACE, "-l", "score.dev/run=r-lost", "--ignore-not-found",
            "--wait=false", "--cascade=background") in deleted
    beaten = [call for call in deleted if call[0] == "annotate"]
    assert beaten and beaten[0][:6] == ("annotate", "jobs", "-n", manifests.NAMESPACE, "-l", "score.dev/run=r-lost") \
        and beaten[0][-1].startswith(submit.ALIVE_NOTE + "=")
    entry, = booked
    assert entry["batch"] == "r-lost" and entry["who"] == "test" and entry["jobs"]["ask"]["state"] == "unwatched"
    assert [row["node"] for row in entry["machines"]] == ["n1"] and entry["machines"][0]["end_estimated"]

    # a stop: the run's Jobs deleted (every generation, by its label), its row booked, the process ends 143
    booked, error, deleted, looks = a_watched_run(tmp_path / "stop", monkeypatch,
                                                  lambda: os.kill(os.getpid(), signal.SIGTERM))
    assert isinstance(error, submit.Stopped) and error.code == 128 + signal.SIGTERM and len(looks) == 2
    assert ("delete", "jobs", "-n", manifests.NAMESPACE, "-l", "score.dev/run=r-lost", "--ignore-not-found",
            "--wait=false", "--cascade=background") in deleted
    entry, = booked
    assert entry["jobs"]["ask"]["state"] == "stopped" and [row["node"] for row in entry["machines"]] == ["n1"]

    # stop-batch: score's Jobs in score-jobs only
    class Recording(LiveKubectl):
        def run(self, *arguments):
            self.deleted.append(arguments)
            return "job.batch \"score-r-a-g0\" deleted\n"
    kubectl = Recording()
    monkeypatch.setattr(manifests, "NAMESPACE", "score-jobs")
    assert submit.stop_score_jobs(kubectl, PoolCluster()) == 'job.batch "score-r-a-g0" deleted'
    # only this box's: another box's runs share score-jobs (2026-11-06: the conductor's stop ended a sim body run this
    # PC had launched). Break: in submitter.stop_score_jobs, select by RUN_LABEL alone; or drop BOX_LABEL from labels
    monkeypatch.setenv("SCORE_K8S_BOX", "conductor")
    kubectl.deleted.clear()
    assert submit.stop_score_jobs(kubectl, PoolCluster()) == 'job.batch "score-r-a-g0" deleted'
    assert kubectl.deleted == [("delete", "jobs", "-n", "score-jobs", "-l", "score.dev/run,score.dev/box=conductor",
                                "--ignore-not-found", "--wait=false", "--cascade=background")]
    # the env1 cap's stop reaches every box's (the plan of 2026-11-09 B4). Break: ignore `every_box`
    kubectl.deleted.clear()
    submit.stop_score_jobs(kubectl, PoolCluster(), every_box=True)
    assert kubectl.deleted == [("delete", "jobs", "-n", "score-jobs", "-l", "score.dev/run",
                                "--ignore-not-found", "--wait=false", "--cascade=background")]
    assert manifests.labels("r", "a", "pixal")[manifests.BOX_LABEL] == "conductor"
    assert manifests.warm_hold("r", "node-1", "host-1", 10, 0)["metadata"]["labels"][manifests.BOX_LABEL] == "conductor"
    monkeypatch.setattr(manifests, "NAMESPACE", "score")
    with pytest.raises(SystemExit, match="score-jobs only"):
        submit.stop_score_jobs(Recording(), PoolCluster())


def a_watched_run(tmp_path, monkeypatch, failing_look):
    """submit() of one job over stubs, its first look putting the job on a node and `failing_look` after: the rows
    booked, the error it raised, the kubectl deletes and the looks made."""
    (tmp_path / "store").mkdir(parents=True)
    helper = Helper(tmp_path / "store")
    booked, looks = [], []
    monkeypatch.setattr(submit, "runtime", lambda: helper)
    monkeypatch.setattr(submit, "prepare", lambda kubectl, cluster: None)
    monkeypatch.setattr(submit.ledger, "record", booked.append)
    monkeypatch.setattr(submit.time, "sleep", lambda seconds: None)

    monkeypatch.setattr(submit, "CLUSTER_WAITING", tmp_path / "waiting")
    mark = tmp_path / "waiting" / str(os.getpid())

    def look(run, parallel):
        looks.append(mark.exists())  # the node holds no --jobs slot while it waits (score/graph CLUSTER_WAITERS)
        if len(looks) == 1:
            run.jobs["ask"].update(node="n1", ran=time.time())
            run.nodes["n1"] = {"class": "gpu-80gb", "type": "H100-1-80G", "zone": "fr-par-2", "cards": 1,
                               "created": time.time(), "ready": time.time(), "deleted": None, "jobs": set()}
            return
        failing_look()
    monkeypatch.setattr(submit, "look", look)

    class DeletingKubectl(LiveKubectl):
        def run(self, *arguments):
            self.deleted.append(arguments)
            return ""
    kubectl = DeletingKubectl()
    before = signal.getsignal(signal.SIGTERM)
    spec = {"kind": "judge", "image": "image", "minutes": 5, "command": ["true"]}
    helper.write_job(helper.store, "r-lost", "ask", spec)
    with pytest.raises(BaseException) as raised:
        submit.submit("r-lost", {"ask": spec}, helper.store, kubectl=kubectl, cluster=PricedCluster(), who="test")
    assert signal.getsignal(signal.SIGTERM) is before  # the handler before is put back
    assert all(looks) and not mark.exists()  # marked at every look, the mark gone after the error
    return booked, raised.value, kubectl.deleted, looks


def test_score_cloud_k8s_keeps_the_providers_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    monkeypatch.delenv("SCORE_K8S_PROVIDER", raising=False)
    assert submit.provider.on_cluster() and submit.provider.load().NAME == "scaleway"
    monkeypatch.setenv("SCORE_K8S_PROVIDER", "scaleway/tenant")  # Scaleway's backend, a tenant cluster
    assert submit.provider.load().NAME == "scaleway" and submit.provider.cluster_name() == "tenant"
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    assert not submit.provider.on_cluster() and submit.provider.load().NAME == "scaleway"
    # SCORE_CLOUD_KINDS narrows the cluster to its kinds (#76); every other kind rents machines from the same backend
    monkeypatch.setenv("SCORE_CLOUD_KINDS", "pixal,blender,library,settle,characters")
    assert not submit.provider.on_cluster("pixal")  # SCORE_CLOUD is not k8s
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    assert submit.provider.on_cluster("pixal") and submit.provider.on_cluster("settle")
    assert not submit.provider.on_cluster("judge") and submit.provider.load().NAME == "scaleway"
    monkeypatch.setattr(submit.sys, "argv", ["/repo/tools/cloud/library_bake.py", "job.json"])
    assert submit.provider.on_cluster()  # a runner naming no kind: its script's
    monkeypatch.setattr(submit.sys, "argv", ["/repo/tools/cloud/judge.py"])
    assert not submit.provider.on_cluster()
    monkeypatch.setattr(submit.sys, "argv", ["-c"])
    assert not submit.provider.on_cluster()  # a kind that cannot be told stays on machines
    monkeypatch.delenv("SCORE_CLOUD_KINDS")
    assert submit.provider.on_cluster("judge")  # unset: every kind
    # a run launched with cluster kinds and resumed without them (2026-11-07, Launch 33: 10 L4s rented for its
    # cluster kinds): its pool's collector rents nothing and says why; with the settings back it rents again
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import pool
    launch = {"pid": 11, "state": "resumed", "resumed": {"pid": 22},
              "settings": {"SCORE_CLOUD": "k8s", "SCORE_CLOUD_KINDS": "pixal,blender"}}
    (tmp_path / "20261107T100000-11.json").write_text(json.dumps(launch))
    (tmp_path / "20261107T110000-22.json").write_text(json.dumps({"pid": 22, "state": "running", "settings": {}}))
    (tmp_path / "active.json").write_text("[]")
    monkeypatch.setattr(pool, "RUNS", tmp_path)
    rented, said = [], []
    for name in ("tidy", "trim", "idle_down", "beat", "hold"):
        monkeypatch.setattr(pool, name, lambda *args: None)
    monkeypatch.setattr(pool, "shortfall", lambda plan, alive: [("gpu-24gb", 0, "card-0")])
    monkeypatch.setattr(pool, "fill", lambda run_id, plan, short, account: rented.append(short) or 1)
    monkeypatch.setattr(pool.batch, "say", said.append)
    collecting = pool.Collecting()
    collecting.account = "account"
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    pool.collect_round("run", {"run_pid": 22}, collecting)
    pool.collect_round("run", {"run_pid": 22}, collecting)
    assert rented == [] and len(said) == 1 and "pixal,blender" in said[0] and "SCORE_CLOUD is scaleway" in said[0]
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    pool.collect_round("run", {"run_pid": 22}, collecting)  # its launch's settings back
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    pool.collect_round("run", {"run_pid": 33}, collecting)  # another run, launched with no cluster
    assert len(rented) == 2 and collecting.refused is None
    # a tenant box that cannot read the cluster's project with scw (the conductor, 2026-11-06): its pools as
    # SCORE_K8S_POOLS gives them, its nodes through kubectl, never scw. Break: in tenant.nodes, read
    # `scw("k8s", "node", "list", ...)` again; or in tenant.class_pools, drop the `given is not None` branch
    import importlib.util
    spec = importlib.util.spec_from_file_location("tenant_under_test", pathlib.Path(__file__).parent / "clusters/tenant.py")
    tenant = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tenant)
    monkeypatch.setattr(tenant, "scw", lambda *words: pytest.fail(f"scw asked: {words}"))
    monkeypatch.setattr(tenant, "price", lambda machine_type, zone: (0.01, 1))
    monkeypatch.setenv(tenant.POOLS, json.dumps([{"name": "score-l4", "class": "gpu-24gb", "type": "L4-1-24G",
                                                  "zone": "fr-par-2", "max": 10}]))
    assert tenant.class_pools() == [{"name": "score-l4", "id": "score-l4", "class": "gpu-24gb", "type": "L4-1-24G",
                                     "zone": "fr-par-2", "max": 10, "euros_a_minute": 0.01, "unit_minutes": 1}]
    taint = {"key": "tenant", "value": "score", "effect": "NoSchedule"}
    listed = {"items": [
        {"metadata": {"name": "n1", "creationTimestamp": "2026-11-06T10:00:00Z",
                      "labels": {tenant.CLASS_LABEL: "gpu-24gb", tenant.POOL_LABEL: "score-l4",
                                 tenant.INSTANCE_LABEL: "l4-1-24g", tenant.ZONE_LABEL: "fr-par-2"}},
         "spec": {"taints": [taint]}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}},
        {"metadata": {"name": "babons", "creationTimestamp": "2026-11-06T10:00:00Z",
                      "labels": {tenant.CLASS_LABEL: "gpu-24gb"}}, "spec": {}, "status": {}}]}
    monkeypatch.setattr(tenant, "kubectl", lambda *words: json.dumps(listed))
    assert tenant.nodes() == [{"name": "n1", "pool": "score-l4", "type": "L4-1-24G", "zone": "fr-par-2",
                               "status": "ready", "created": 1793959200.0}]  # an untainted node is not score's
    # a node just joined, its cloud labels not set yet, is priced by its pool (named in its name), never "? in ?".
    # Break: in tenant.nodes, drop the pool_labels fill
    listed["items"] = [{"metadata": {"name": "scw-babon-score-l4-0a1b", "creationTimestamp": "2026-11-06T10:00:00Z",
                                     "labels": {tenant.CLASS_LABEL: "gpu-24gb"}},
                        "spec": {"taints": [taint]}, "status": {}}]
    assert tenant.nodes() == [{"name": "scw-babon-score-l4-0a1b", "pool": "score-l4", "type": "L4-1-24G",
                               "zone": "fr-par-2", "status": "not_ready", "created": 1793959200.0}]


# ==== secrets and the GPU operator ==================================================================================

OPERATOR = {"driver": {"repository": "nvcr.io/nvidia", "image": "driver", "version": "580.126.20",
                       "manager": {"repository": "nvcr.io/nvidia/cloud-native", "image": "k8s-driver-manager",
                                   "version": "v0.11.0"}},
            "toolkit": {"repository": "nvcr.io/nvidia/k8s", "image": "container-toolkit", "version": "v1.19.1"},
            "devicePlugin": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
            "gfd": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
            "validator": {"repository": "nvcr.io/nvidia", "image": "gpu-operator", "version": "v26.3.3"},
            "dcgmExporter": {"repository": "nvcr.io/nvidia/k8s", "image": "dcgm-exporter",
                             "version": "4.5.3-4.8.2-distroless"}}
MIRROR = "rg.example/space"


def test_the_secrets_hold_the_registry_the_gpu_operator_is_pointed_at():
    """One store and one registry: the Secrets hold their values by name, and the GPU operator's images are copied
    into that registry with its pull Secret, the ClusterPolicy pointed there, and a cluster already mirrored left
    alone."""
    store = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "AK", "secret_key": "SK"}
    assert base64.b64decode(manifests.store_secret(store)["data"]["SCORE_STORE_SECRET_KEY"]).decode() == "SK"
    registry = {"endpoint": MIRROR, "username": "nologin", "password": "PW"}
    pull = manifests.registry_secret(registry)
    assert json.loads(base64.b64decode(pull["data"][".dockerconfigjson"]))["auths"]["rg.example"]["password"] == "PW"
    assert pull["type"] == "kubernetes.io/dockerconfigjson"

    pairs = dict(gpu_operator.images(OPERATOR, "ubuntu24.04"))
    assert pairs["nvcr.io/nvidia/driver:580.126.20-ubuntu24.04"] == "driver:580.126.20-ubuntu24.04"
    assert pairs["nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.11.0"] == "k8s-driver-manager:v0.11.0"
    job = gpu_operator.copy_job(list(pairs.items()), registry["endpoint"])
    assert f"{MIRROR}/driver:580.126.20-ubuntu24.04" in job["spec"]["template"]["spec"]["containers"][0]["command"][2]

    secret_name = pull["metadata"]["name"]
    patch = gpu_operator.policy_patch(registry["endpoint"], secret_name)["spec"]
    assert patch["driver"]["repository"] == MIRROR and patch["driver"]["manager"]["repository"] == MIRROR
    assert patch["validator"]["imagePullSecrets"] == [secret_name]
    assert "imagePullSecrets" not in patch["driver"]["manager"]
    assert not gpu_operator.mirrored(OPERATOR, MIRROR)

    class Policy:
        """kubectl whose cluster's ClusterPolicy already pulls from the mirror."""

        def __init__(self):
            self.calls = []

        def json(self, *arguments):
            self.calls.append(arguments)
            spec = {key: dict(value, repository=MIRROR) for key, value in OPERATOR.items()}
            spec["driver"]["manager"] = dict(OPERATOR["driver"]["manager"], repository=MIRROR)
            return {"items": [{"metadata": {"name": "cluster-policy"}, "spec": spec}]}
    kubectl = Policy()
    assert gpu_operator.mirror(kubectl, registry)
    assert kubectl.calls == [("get", "clusterpolicies.nvidia.com")]  # nothing changed on a live cluster
