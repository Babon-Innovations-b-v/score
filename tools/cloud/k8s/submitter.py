"""The submitter of the job path: runs a run's jobs as Kubernetes Jobs on whatever cluster the kubeconfig points at,
waits for them, and records what each node cost.

    python3 tools/cloud/k8s/submitter.py run <run id>          # every runs/<run id>/*/job.json in the object store
    python3 tools/cloud/k8s/submitter.py idle                  # every class pool held at zero nodes
    python3 tools/cloud/k8s/submitter.py down                  # delete the cluster (SCORE_K8S_PROVIDER's, scaleway)

A run is a set of job specs (`runs/<run>/<job>/job.json`, written by the runtime's helper, `../CLAUDE.md`). The
submitter is the run's queue: it makes the namespace and the two Secrets (the object store and the image pull
secret, from the provider's object_store() and registry() at submit time, never written to disk), caps every
pool's size from the month's euros left, makes one Job a job (`manifests.py`) while the namespace's ResourceQuota
has room for its pod (hard less used; a Job past it would only sit with its pod refused), and then, every POLL_SECONDS, reads
the Jobs, their pods, the autoscaler's events on them and the nodes.

The order of classes. A kind's classes and their order come from `tools/cloud/capacity.py` (KINDS,
KIND_ORDER, LATE), never copied; a spec may name its own `classes` (as `--classes` does for the machine runners).
A Job starts allowed on the kind's first class only, so the cluster autoscaler grows that class's pools (in any of
their zones). When the autoscaler says it cannot (every pool of the allowed classes backed off after a failed
scale-up, at its max size, or out of stock), or no node came for NODE_MINUTES, the kind is widened by one class:
its waiting Jobs are made again (a new generation) allowed on one more class, keeping the earlier ones, so a card
that comes back in stock is still taken. Classes in LATE are added only after LATE_MINUTES. Once every class is
allowed, the autoscaler keeps retrying the backed-off pools on its own (5 min, doubling to 30), and a Job whose
deadline passes while it never ran is made again: the run never settles for one card, it waits for any.

A class the cluster has no pool for is taken, when none of a job's classes has one, by the nearest pool that holds
it (`nearest_pools`: the smallest processor class with at least its cores and memory, or card class with as many
cards of at least its memory), so settling's cpu-4c-32gb and the paint's 32- and 16-core classes run on a tenant
cluster's bigger processor pool instead of being refused.

Robustness. A Job's pod is retried by Kubernetes up to attempt_limit (backoffLimit); the runtime writes done.json
last and exits at once if it exists, so a Job made again (a lost node, a widened class, a restarted submitter)
redoes only unfinished work. The submitter finds a run's Jobs by label, so running it again on the same run resumes.
A look at the cluster that fails (kubectl, the provider's node list) is tried again POLL_RETRIES times, a poll
apart; past that, and on SIGTERM (a stopped `score run`, stop-batch), the run's rows are booked from what was last
seen, its nodes still up taken as gone IDLE_ESTIMATE_MINUTES on (marked estimated), before the error goes on: a
watch that dies never loses a row (#95: run pixal-20261105-155442-3550649's EUR 0.27 went unbooked when its poll
failed). On SIGTERM the run's Jobs are deleted first, every generation (`stop_jobs`); `stop_score_jobs` does the same
for every run of score in the score-jobs namespace, for stop-batch.

Cost. Nothing is submitted outside a run the runner cleared or the owner's override names
(score.adapters.compute, `require_cleared`). Each pool's max size is what the batch cap (ledger.batch_cap: the EUR
60 cap, under the owner's override what is left of his euros less 10%) pays
for ledger.BATCH_HOURS a node, and the live cost of the run's nodes is checked every poll against the batch cap: past
it, the waiting Jobs are deleted and every pool is capped to zero. Empty nodes go after the autoscaler's scale-down
time (the cluster module sets it), past a warm hold's WARM_MINUTES once the run's queue is empty (hold_idle), so an
idle cluster costs only its small system pool; `down` deletes the whole cluster. At the end the submitter waits for the run's nodes to
go, then writes one ledger row a node (ledger.machines_record: its class, type, zone, minutes and euros) and the
run's jobs with their wait until the pod ran.
"""
import argparse
import collections
import contextlib
import datetime
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
CLOUD = HERE.parents[1] / "cloud"
sys.path.insert(0, str(CLOUD.parent / "props"))
sys.path.insert(0, str(CLOUD))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

import capacity  # noqa: E402
from kube import Kubectl  # noqa: E402
import ledger  # noqa: E402
import manifests  # noqa: E402
from paths import HOME  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402

POLL_SECONDS = 20
# How many times a failed look at the cluster is tried again, a poll apart, before the run is booked and the error
# goes on (#95: about 5 min of a control plane or a provider API that does not answer).
POLL_RETRIES = 15
# The namespace stop-batch clears of score's Jobs: the tenant cluster's (clusters/tenant.py), never another.
SCORE_JOBS_NAMESPACE = "score-jobs"
RUN_LABEL = "score.dev/run"
# How long a class may be tried with a pod still waiting and no word from the autoscaler before the next class is
# allowed: the upstream autoscaler gives up on a node that has not joined after 15 min (max-node-provision-time).
NODE_MINUTES = 15
# How long the autoscaler's "cannot grow" is watched before it counts: it says so for a moment while it reads a
# newly allowed pool.
NO_GROW_GRACE_MINUTES = 1.5
NO_GROW_WORDS = ("in backoff after failed scale-up", "max node group size reached", "max cluster", "out of stock")
# How long the end waits for the run's nodes to be removed by the autoscaler before recording them as still up.
SCALE_DOWN_WAIT_MINUTES = 20
# When a runner does not wait for that, a node still up is taken as gone this long after the run: the autoscaler's
# 5 min of idleness and its delete (5.5 to 6.5 min measured, 2026-10-09).
IDLE_ESTIMATE_MINUTES = 6.5
# How long a node a job of the run ran on is kept after it goes idle, once every job of the run is on the cluster
# (owner, 2026-11-06: "why dont machine keep kept warm while there is a queu"): the tenant cluster's autoscaler removes
# an empty node after 2 min, and a fresh card node costs ~3 min to come up and a GEM-X job ~2 min to rebuild its
# environment there, so a run's tail and the run that follows it within these minutes take warm nodes
# (manifests.warm_hold, ended by its own deadline).
WARM_MINUTES = 10
# The runner's folder of nodes waiting on a cluster run (score/graph CLUSTER_WAITING): a file named by each watching
# process's pid, touched each poll and removed when its watch ends, so its node holds no --jobs slot while its jobs
# are on the cluster (#76: the slots were held by cluster waits, no score pod Running).
CLUSTER_WAITING = HOME / "cloud" / "cluster.waiting"
INSTANCE_LABEL = "node.kubernetes.io/instance-type"
# How long before a node came up a pod placed elsewhere may still have been the one the autoscaler grew it for: a
# Kapsule card node joins 2 to 4 min after its scale-up (2026-10-09), so a pod placed on another node up to this long
# before shares the unused node it caused.
SCALE_UP_LEAD_MINUTES = 5
ZONE_LABEL = "topology.kubernetes.io/zone"


def say(line):
    print(time.strftime("%H:%M:%S ") + line, flush=True)


class Stopped(SystemExit):
    """A stop signal reached a cluster submit: its Jobs are deleted and its rows booked, then the process exits with
    128 + the signal's number."""


def runtime():
    """The runtime's submit side (`../runtime/submit.py`), loaded by path: it shares a name with no module here but
    the runtime's own folder holds a `submit` the runners import."""
    spec = importlib.util.spec_from_file_location("runtime_submit", HERE.parent / "runtime" / "submit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_specs(store, run_id):
    """Every job.json of the run in the store: {job id: spec}."""
    found = {}
    for key in store.keys(f"runs/{run_id}/"):
        parts = key.split("/")
        if len(parts) == 4 and parts[3] == "job.json":
            found[parts[2]] = json.loads(store.read_bytes(key))
    return found


# The provider's cluster module (clusters/<name>.py).

def cluster_module(name=None):
    """The cluster module of SCORE_K8S_PROVIDER (default scaleway; `<backend>/<cluster>` names a cluster module apart
    from its backend, as `scaleway/tenant`), loaded by path: its file may share its name with the provider's backend.
    A module naming its NAMESPACE puts the jobs there."""
    name = name or provider.cluster_name()
    spec = importlib.util.spec_from_file_location(f"cluster_{name}", HERE / "clusters" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifests.use_namespace(getattr(module, "NAMESPACE", manifests.NAMESPACE))
    return module


def cluster_kubectl(cluster):
    """kubectl at the cluster's kubeconfig (KUBECONFIG when set) and its context, when the module names one."""
    chosen = getattr(cluster, "context", None)
    return Kubectl(os.environ.get("KUBECONFIG") or str(cluster.KUBECONFIG), chosen() if chosen else None)


# The order of classes.

def kind_classes(kind):
    """capacity's classes for a job kind, in the kind's order."""
    return sorted(capacity.classes_for(kind), key=lambda name: capacity.speed_rank(name, kind))


def job_kind(spec):
    """The job kind capacity.py and the ledger know a job by: its `capacity_kind` when the runner names one (a
    library bake runs in the blender image, whose name is the spec's `kind`), else its `kind`."""
    return spec.get("capacity_kind") or spec["kind"]


def class_order(kind, spec, pool_classes):
    """The classes a job may take, in the order to take them, and which of them only after LATE_MINUTES: the spec's
    own `classes`, else capacity's for its kind in the kind's order; only classes the cluster has pools for, never one
    the kind may not take (capacity.NEVER: no H100 for Blender or bakes)."""
    wanted = [name for name in (spec["classes"] if spec.get("classes") else kind_classes(kind))
              if name not in capacity.NEVER.get(kind, ())]
    order = [name for name in wanted if name in pool_classes]
    if not order:
        order = nearest_pools(wanted, [name for name in pool_classes if name not in capacity.NEVER.get(kind, ())])
        if order:
            say(f"{kind}: the cluster has no pool for {', '.join(wanted)}; taking the nearest that holds it: "
                f"{', '.join(order)}")
    if not order:
        raise SystemExit(f"the cluster has no pool for any class of the job kind '{kind}' ({', '.join(wanted)}), "
                         "nor one that holds it")
    return order, set(capacity.late_for(kind)) & set(order)


def class_size(name):
    """A class's size, smallest first among its own sort: (cores, memory) of a processor class, (card memory, cores)
    of a card class."""
    found = provider.CPU.match(name)
    if found:
        return int(found.group(1)), int(found.group(2))
    found = provider.GPU.match(name)
    return int(found.group(1)), int(found.group(3) or 0)


def holds(pooled, wanted):
    """Whether a machine of class `pooled` holds a job asked on `wanted`: both processor classes and `pooled` with at
    least its cores and memory, or both with as many cards and `pooled`'s at least as big (and its cores, if named)."""
    if provider.cards(pooled) != provider.cards(wanted):
        return False
    return all(have >= need for have, need in zip(class_size(pooled), class_size(wanted)))


def nearest_pools(wanted, pool_classes):
    """For each class of `wanted` in order, the smallest of `pool_classes` that holds it (holds), each once."""
    order = []
    for name in wanted:
        fits = sorted((class_size(pooled), pooled) for pooled in pool_classes if holds(pooled, name))
        if fits and fits[0][1] not in order:
            order.append(fits[0][1])
    return order


def job_cards(spec, order):
    """The cards a job's pod asks for: the spec's `cards` (1 by default) on card classes, none on processor classes.
    A kind's classes are all card classes or all processor classes."""
    with_cards = {provider.cards(name) > 0 for name in order}
    if len(with_cards) > 1:
        raise SystemExit(f"classes {order} mix card and processor machines; give the job one kind of machine")
    return int(spec.get("cards", 1)) if with_cards.pop() else 0


def may_widen(state, order, late, now):
    """Whether the kind may take one more class now: there is one, and it is not a late class before LATE_MINUTES."""
    if state["step"] >= len(order):
        return False
    upcoming = order[state["step"]]
    return upcoming not in late or now - state["first"] >= capacity.LATE_MINUTES * 60


def wants_widening(state, waiting, now):
    """Whether a kind's waiting pods show its allowed classes cannot be had: a pod has waited unscheduled since the
    last widening, and either the autoscaler has said for NO_GROW_GRACE_MINUTES that no allowed pool can grow, or no
    node came for NODE_MINUTES. `waiting` is each unscheduled pod's (unscheduled since, last "cannot grow" time or
    None)."""
    since_step = now - state["since"]
    for _unscheduled, no_grow in waiting:
        if no_grow is not None and no_grow >= state["since"] and since_step >= NO_GROW_GRACE_MINUTES * 60:
            return True
    return bool(waiting) and since_step >= NODE_MINUTES * 60


# Reading the cluster.

def parse_time(text):
    """A Kubernetes time (RFC 3339) as epoch seconds, or None."""
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() if text else None


def pod_running_since(pod):
    """When the pod's container started, or None while it has not."""
    for status in pod.get("status", {}).get("containerStatuses") or []:
        state = status.get("state", {})
        started = (state.get("running") or state.get("terminated") or {}).get("startedAt")
        if started:
            return parse_time(started)
    return None


def unscheduled_since(pod):
    """When the pod was found to fit no node, or None when it is scheduled."""
    for condition in pod.get("status", {}).get("conditions") or []:
        if condition["type"] == "PodScheduled" and condition["status"] == "False":
            return parse_time(condition.get("lastTransitionTime")) or time.time()
    return None


def pod_key(pod, node, index):
    """A pod's name among the pods listed (its uid, else its name, else where it was in the list)."""
    meta = pod.get("metadata", {})
    return meta.get("uid") or meta.get("name") or f"{node}:{index}"


def pod_start(pod, now):
    """When the pod took its node: the kubelet's start of it, else its scheduling, else now."""
    status = pod.get("status", {})
    return parse_time(status.get("startTime")) or scheduled_at(pod) or now


def pod_end(pod, now):
    """When the pod let its node go: its containers' last finish once it ended, else now (it holds it still)."""
    status = pod.get("status", {})
    if status.get("phase") not in ("Succeeded", "Failed"):
        return now
    finished = [parse_time((entry.get("state", {}).get("terminated") or {}).get("finishedAt"))
                for entry in status.get("containerStatuses") or []]
    return max([moment for moment in finished if moment] or [now])


def scheduled_at(pod):
    """When the pod was placed on a node, or None while it is not."""
    for condition in pod.get("status", {}).get("conditions") or []:
        if condition["type"] == "PodScheduled" and condition["status"] == "True":
            return parse_time(condition.get("lastTransitionTime"))
    return None


def pod_classes(pod):
    """The classes a pod may take (its required node affinity), none for a pod pinned to one node (a warm hold)."""
    terms = (pod.get("spec", {}).get("affinity", {}).get("nodeAffinity", {})
             .get("requiredDuringSchedulingIgnoredDuringExecution", {}).get("nodeSelectorTerms", []))
    return {value for term in terms for expression in term.get("matchExpressions", [])
            if expression.get("key") == manifests.CLASS_LABEL for value in expression.get("values", [])}


def gap_holder(holds, moment):
    """The run a moment no pod held the node belongs to: the one whose pod held it last before (its idle tail, its
    warm hold's gaps), else, before any pod, the one whose pod held it first (its start-up)."""
    before = [hold for hold in holds if hold["end"] <= moment]
    if before:
        return max(before, key=lambda hold: (hold["end"], hold["run"]))["run"]
    return min(holds, key=lambda hold: (hold["start"], hold["run"]))["run"]


def held_share(holds, mine, start, end):
    """The part of a node's [start, end] the run `mine` pays, from the times its pods and other runs' held the node
    (`holds`, {run, start, end} each): a moment several runs' pods held it is split between them evenly, a moment none
    held it goes to `gap_holder`. Every moment goes to some run, so the runs that shared a node book it whole between
    them, none of them more than its own part. A window with no length yet (the node's clock ahead of this one) is
    the whole of each run that held it: it costs nothing, and the run keeps the node."""
    if end <= start:
        return 1.0 if any(hold["run"] == mine for hold in holds) else 0.0
    cuts = sorted({start, end, *(moment for hold in holds for moment in (hold["start"], hold["end"])
                                 if start < moment < end)})
    paid = 0.0
    for left, right in zip(cuts, cuts[1:]):
        holding = {hold["run"] for hold in holds if hold["start"] <= left and hold["end"] >= right}
        if not holding:
            holding = {gap_holder(holds, left)}
        if mine in holding:
            paid += (right - left) / len(holding)
    return paid / (end - start)


def no_grow_times(events):
    """For each pod whose latest word from the cluster autoscaler is that none of its pools can grow for it, the time
    it said so. A "cannot grow" followed by a scale-up for the pod does not count: right after a pool's size cap
    changes the autoscaler says "max node group size reached" for a moment and then grows it (2026-10-09)."""
    latest = {}
    for event in events:
        reason = event.get("reason")
        if reason not in ("NotTriggerScaleUp", "TriggeredScaleUp"):
            continue
        message = event.get("message", "").lower()
        if reason == "NotTriggerScaleUp" and not any(word in message for word in NO_GROW_WORDS):
            continue
        when = parse_time(event.get("lastTimestamp") or event.get("eventTime")) or 0
        name = event["involvedObject"]["name"]
        if name not in latest or when >= latest[name][0]:
            latest[name] = (when, reason)
    return {name: when for name, (when, reason) in latest.items() if reason == "NotTriggerScaleUp"}


def job_outcome(job):
    """What a Job's status says: 'done', 'failed', 'expired' (its deadline passed), or None while it runs."""
    for condition in job.get("status", {}).get("conditions") or []:
        if condition["status"] != "True":
            continue
        if condition["type"] in ("Complete", "SuccessCriteriaMet"):
            return "done"
        if condition["type"] in ("Failed", "FailureTarget"):
            return "expired" if condition.get("reason") == "DeadlineExceeded" else "failed"
    return None


# The run.

class Run:
    """One run's jobs on the cluster: their Jobs, generations and classes, the kinds' widening, the nodes seen."""

    def __init__(self, run_id, specs, kubectl, cluster):
        self.run_id, self.specs, self.kubectl, self.cluster = run_id, specs, kubectl, cluster
        self.started = time.time()
        pool_classes = {pool["class"] for pool in cluster.class_pools()}
        self.orders = {job_id: class_order(job_kind(spec), spec, pool_classes) for job_id, spec in specs.items()}
        self.kinds = {job_kind(spec): {"step": 1, "since": self.started, "first": self.started}
                      for spec in specs.values()}
        self.jobs = {job_id: {"generation": 0, "state": "waiting", "submitted": None, "ran": None, "node": None}
                     for job_id in specs}
        self.nodes = {}
        self.held = 0  # jobs submit_more holds for room in the namespace's quota, as last said

    def resume(self):
        """Take up the run's Jobs a submitter before this one made: each job's newest generation and each kind's
        classes so far, read from their annotations."""
        jobs, _pods, _no_grow = self.read()
        for found in jobs.values():
            notes = found["metadata"].get("annotations", {})
            job_id = notes.get("score.dev/job-id")
            if job_id not in self.jobs:
                continue
            record = self.jobs[job_id]
            record["generation"] = max(record["generation"], int(notes.get("score.dev/generation", 0)))
            record["submitted"] = self.started
            kind = self.kinds[job_kind(self.specs[job_id])]
            kind["step"] = max(kind["step"], len(notes.get("score.dev/classes", "").split(",")))

    def allowed(self, job_id):
        """The classes a job is allowed on now: its kind's first `step` classes, in order."""
        order, _late = self.orders[job_id]
        return order[:self.kinds[job_kind(self.specs[job_id])]["step"]]

    def make(self, job_id):
        """Make the job's Job at its current generation and classes."""
        spec = self.specs[job_id]
        classes = self.allowed(job_id)
        self.kubectl.apply([manifests.job(spec, self.run_id, job_id, classes, job_cards(spec, classes),
                                          self.jobs[job_id]["generation"], getattr(self.cluster, "TOLERATIONS", ()))])
        self.jobs[job_id]["submitted"] = time.time()

    def remake(self, job_id):
        """Delete the job's Job and make the next generation (with the classes allowed now)."""
        record = self.jobs[job_id]
        self.kubectl.delete_job(manifests.job_name(self.run_id, job_id, record["generation"]))
        record["generation"] += 1
        self.make(job_id)

    def read(self):
        """The run's Jobs by name, its pods by job label, and the autoscaler's events on its pods."""
        selector = f"score.dev/run={manifests.label_value(self.run_id)}"
        listed = self.kubectl.json("get", "jobs,pods", "-n", manifests.NAMESPACE, "-l", selector)["items"]
        jobs, pods = {}, collections.defaultdict(list)
        for item in listed:
            if item["kind"] == "Job":
                jobs[item["metadata"]["name"]] = item
            else:
                pods[item["metadata"]["labels"].get("score.dev/job")].append(item)
        events = self.kubectl.json("get", "events", "-n", manifests.NAMESPACE)["items"]
        return jobs, pods, no_grow_times(events)

    def current(self, job_id, jobs):
        """The job's Job at its current generation, or None."""
        return jobs.get(manifests.job_name(self.run_id, job_id, self.jobs[job_id]["generation"]))

    def update_job(self, job_id, found, pods):
        """Take one job's state from its Job and pods: when its pod first ran and where, and its outcome."""
        record = self.jobs[job_id]
        for pod in pods:
            began = pod_running_since(pod)
            if began and (record["ran"] is None or began < record["ran"]):
                record["ran"], record["node"] = began, pod["spec"].get("nodeName")
        outcome = job_outcome(found)
        if outcome == "expired" and record["ran"] is None:
            say(f"{job_id} waited past its deadline without a node; making it again")
            self.remake(job_id)
        elif outcome == "expired":
            record["state"] = "failed"
        elif outcome:
            record["state"] = outcome

    def waiting_pods(self, kind, pods, no_grow):
        """The kind's pods that fit no node yet: (unscheduled since, last "cannot grow" time)."""
        waiting = []
        for job_id, spec in self.specs.items():
            if job_kind(spec) != kind or self.jobs[job_id]["state"] != "waiting":
                continue
            for pod in pods.get(manifests.label_value(job_id), []):
                since = unscheduled_since(pod)
                if since is not None:
                    waiting.append((since, no_grow.get(pod["metadata"]["name"])))
        return waiting

    def widen(self, pods, no_grow):
        """Give each kind whose allowed classes cannot be had its next class, and make its waiting Jobs again."""
        now = time.time()
        for kind, state in self.kinds.items():
            job_ids = [job_id for job_id, spec in self.specs.items() if job_kind(spec) == kind]
            order, late = self.orders[job_ids[0]]
            if not may_widen(state, order, late, now) or not wants_widening(
                    state, self.waiting_pods(kind, pods, no_grow), now):
                continue
            state["step"] += 1
            state["since"] = now
            say(f"{kind}: {', '.join(order[:state['step'] - 1])} cannot be had now; adding {order[state['step'] - 1]}")
            for job_id in job_ids:
                record = self.jobs[job_id]
                if record["state"] == "waiting" and record["ran"] is None and record["submitted"] is not None:
                    self.remake(job_id)

    def watch_nodes(self):
        """Note every class node: its class, type and zone (from its labels, else from the provider's record), when
        the provider made it, when it was Ready, when last seen."""
        billed = {node["name"]: node for node in self.cluster.nodes()}
        listed = self.kubectl.json("get", "nodes")["items"]
        for node in listed:
            meta = node["metadata"]
            machine_class = provider.capability_class(meta["labels"].get(manifests.CLASS_LABEL))
            if not machine_class:
                continue
            provider_record = billed.get(meta["name"], {})
            seen = self.nodes.setdefault(meta["name"], {
                "class": machine_class, "cards": provider.cards(machine_class),
                "type": (meta["labels"].get(INSTANCE_LABEL) or provider_record.get("type", "?")).upper(),
                "zone": meta["labels"].get(ZONE_LABEL) or provider_record.get("zone", "?"),
                "created": provider_record.get("created") or parse_time(meta["creationTimestamp"]),
                "hostname": meta["labels"].get(manifests.HOSTNAME_LABEL, meta["name"]),
                "ready": None, "deleted": None, "jobs": set()})
            ready = [condition for condition in node["status"].get("conditions", [])
                     if condition["type"] == "Ready" and condition["status"] == "True"]
            if ready and seen["ready"] is None:
                seen["ready"] = parse_time(ready[0]["lastTransitionTime"])
            seen["last_seen"] = time.time()
        present = {node["metadata"]["name"] for node in listed}
        for name, seen in self.nodes.items():
            if name not in present and seen["deleted"] is None:
                seen["deleted"] = seen["last_seen"]
        self.note_hosts()

    def note_hosts(self):
        """Mark the nodes any job pod of any run has been placed on, so a node another run used is not taken for one
        the autoscaler made for this run in vain; each node's pods, by run, with the time each held it (a warm hold
        is its run's); each node's last time a job pod (a warm hold is none) was live on it, and whether one is now;
        and, for a node no pod is on yet, the pods that were waiting for its class when it came up."""
        now = time.time()
        for seen in self.nodes.values():
            seen["busy"] = False
        pods = self.kubectl.json("get", "pods", "-n", manifests.NAMESPACE)["items"]
        for index, pod in enumerate(pods):
            name = pod["spec"].get("nodeName")
            if name not in self.nodes:
                continue
            seen = self.nodes[name]
            seen["hosted"] = True
            key = pod_key(pod, name, index)
            labels = pod["metadata"].get("labels", {})
            known = seen.setdefault("holds", {}).get(key)
            seen["holds"][key] = {"run": labels.get(RUN_LABEL) or key,
                                  "start": min(pod_start(pod, now), known["start"]) if known else pod_start(pod, now),
                                  "end": pod_end(pod, now)}
            held = manifests.WARM_LABEL in labels
            if not held and pod.get("status", {}).get("phase") not in ("Succeeded", "Failed"):
                seen["busy"], seen["busy_last"] = True, now
        self.note_waiting(pods)

    def note_waiting(self, pods):
        """For each node no pod is on yet, the pods (by run) that may have made the autoscaler grow it: those that may
        take its class, made before it came up and not placed on a node until SCALE_UP_LEAD_MINUTES before; kept
        across looks, so a pod gone since still counts."""
        for seen in self.nodes.values():
            if seen.get("hosted") or not seen["created"]:
                continue
            for index, pod in enumerate(pods):
                labels = pod["metadata"].get("labels", {})
                made = parse_time(pod["metadata"].get("creationTimestamp"))
                placed = scheduled_at(pod)
                if (manifests.WARM_LABEL in labels or seen["class"] not in pod_classes(pod) or made is None
                        or made > seen["created"]
                        or (placed is not None and placed < seen["created"] - SCALE_UP_LEAD_MINUTES * 60)):
                    continue
                key = pod_key(pod, "waiting", index)
                seen.setdefault("waiting", {})[key] = labels.get(RUN_LABEL) or key

    def used_nodes(self):
        """The nodes a job of this run ran on."""
        return {record["node"] for record in self.jobs.values() if record["node"]}

    def share(self, name, seen):
        """The part of the node's minutes since the run's start (from its creation when later) this run pays.
        A node pods were on: split by the time each run's pods held it (held_share; a job of this run seen on it
        holds it from when it ran, should its pod have gone between looks). A node no pod was on: the run's part of
        the pods that were waiting for it when it came up (note_waiting; the autoscaler grows a node for a waiting
        pod, and a faster node may take the pod first: a second L4 came up unused on 2026-10-09), so runs side by
        side book it whole between them, not each of them whole (2026-11-07: a settle run of one job booked the 23
        nodes the cluster grew for 20 runs' pods, EUR 2.90). One made during the run with no waiting pod seen is
        the run's whole: an overcount, never an undercount."""
        mine = manifests.label_value(self.run_id)
        holds = list(seen.get("holds", {}).values())
        holds += [{"run": mine, "start": record["ran"] or self.started, "end": record["ran"] or self.started}
                  for record in self.jobs.values() if record["node"] == name]
        if holds:
            start = max(seen["created"] or self.started, self.started)
            return held_share(holds, mine, start, max(seen["deleted"] or time.time(), start))
        if seen.get("hosted"):
            return 0.0
        waiting = list(seen.get("waiting", {}).values())
        if waiting:
            return waiting.count(mine) / len(waiting)
        return 1.0 if (seen["created"] or 0) >= self.started else 0.0

    def our_nodes(self):
        """The nodes this run pays a part of (`share`)."""
        return {name: seen for name, seen in self.nodes.items() if self.share(name, seen) > 0}

    def live_euros(self):
        """What the run's part of its nodes has cost so far."""
        total = 0.0
        for name, seen in self.our_nodes().items():
            per_minute, unit = self.cluster.price(seen["type"], seen["zone"])
            start = max(seen["created"] or self.started, self.started)
            total += ledger.cost(((seen["deleted"] or time.time()) - start) / 60, per_minute,
                                 unit) * self.share(name, seen)
        return total

    def unfinished(self):
        return [job_id for job_id, record in self.jobs.items() if record["state"] == "waiting"]


def hold_idle(run):
    """Keep each node a job of the run ran on for WARM_MINUTES once it is idle, when every job of the run is on the
    cluster (before that, the run's next job takes the node): one warm hold a node an idle spell, the run's to pay."""
    if any(record["submitted"] is None for record in run.jobs.values()):
        return
    now = time.time()
    for name in sorted(run.used_nodes()):
        seen = run.nodes.get(name)
        if seen is None or seen["deleted"] is not None or seen.get("busy"):
            continue
        if seen.get("held_at", -1) >= seen.get("busy_last", 0):
            continue  # held already since it was last busy
        run.kubectl.apply([manifests.warm_hold(run.run_id, name, seen.get("hostname", name), WARM_MINUTES, now,
                                               getattr(run.cluster, "TOLERATIONS", ()))])
        seen["held_at"], seen["warm_until"] = now, now + WARM_MINUTES * 60
        say(f"{name} kept warm {WARM_MINUTES} min for the next job")


def drop_holds(run):
    """Delete the run's warm holds, so its idle nodes go at the autoscaler's own time."""
    run.kubectl.run("delete", "jobs", "-n", manifests.NAMESPACE, "-l",
                    f"{RUN_LABEL}={manifests.label_value(run.run_id)},{manifests.WARM_LABEL}", "--ignore-not-found",
                    "--wait=false", "--cascade=background")
    for seen in run.nodes.values():
        seen.pop("warm_until", None)


def over_limits(run):
    """Why the run must stop now (ledger.batch_cap: the batch cap, or under the owner's override what is left of his
    euros, read again each look), or None."""
    live = run.live_euros()
    cap, words = ledger.batch_cap()
    if live >= cap:
        return f"the run's nodes have cost €{live:.2f}, at {words}"
    return None


def stop_run(run, why):
    """Delete the run's waiting Jobs and cap every pool to zero."""
    say(f"stopping: {why}")
    for job_id in run.unfinished():
        run.kubectl.delete_job(manifests.job_name(run.run_id, job_id, run.jobs[job_id]["generation"]))
        run.jobs[job_id]["state"] = "stopped"
    drop_holds(run)
    run.cluster.cap_pools(0, 1)


def prepare(kubectl, cluster):
    """Make the namespace and the Secrets, and cap the pools from the batch cap; refused outside a cleared run
    (compute.require_cleared raises Refused)."""
    compute.require_cleared("the cluster's pools")
    if not getattr(cluster, "NAMESPACE_GIVEN", False):
        kubectl.apply([manifests.namespace()])
    kubectl.apply([manifests.store_secret(provider.cloud.object_store()),
                   manifests.registry_secret(provider.cloud.registry())])
    caps = cluster.cap_pools(ledger.batch_cap()[0], ledger.BATCH_HOURS)
    say("pool caps: " + ", ".join(f"{name} {cap}" for name, cap in sorted(caps.items())))


def stop_jobs(kubectl, run_id):
    """Delete every Job of the run, each generation (its label), in the jobs' namespace."""
    kubectl.run("delete", "jobs", "-n", manifests.NAMESPACE, "-l", f"{RUN_LABEL}={manifests.label_value(run_id)}",
                "--ignore-not-found", "--wait=false", "--cascade=background")


def stop_score_jobs(kubectl=None, cluster=None):
    """stop-batch's part on the cluster: delete every Job of score's (labelled with a run) in the score-jobs namespace
    that this box launched (manifests.BOX_LABEL), and nothing else: another box's runs share the namespace (2026-11-06:
    the conductor's stop deleted a sim body run this PC had launched); the cluster's answer. Refused when the cluster
    module puts the jobs elsewhere."""
    cluster = cluster or cluster_module()
    if manifests.NAMESPACE != SCORE_JOBS_NAMESPACE:
        raise SystemExit(f"the cluster's jobs are in {manifests.NAMESPACE}; stop-batch clears {SCORE_JOBS_NAMESPACE} "
                         "only")
    kubectl = kubectl or cluster_kubectl(cluster)
    return kubectl.run("delete", "jobs", "-n", SCORE_JOBS_NAMESPACE, "-l",
                       f"{RUN_LABEL},{manifests.BOX_LABEL}={manifests.box()}", "--ignore-not-found",
                       "--wait=false", "--cascade=background").strip()


@contextlib.contextmanager
def stopped_on_signal():
    """SIGTERM raises Stopped in the block, once, and not while the run's rows are being booked (the yielded list
    holds True then): a stop then is said and remembered, and Stopped is raised once the rows are written
    (`booking`). The handler before is put back after; outside the main thread nothing is set."""
    if threading.current_thread() is not threading.main_thread():
        yield []
        return
    booking, stopping = [], []

    def stop(number, _frame):
        if stopping or booking:
            say("a stop while the run's rows are booked: they are written first")
            stopping.append(number)
            return
        stopping.append(number)
        raise Stopped(128 + number)
    before = signal.signal(signal.SIGTERM, stop)
    try:
        yield booking
    finally:
        signal.signal(signal.SIGTERM, before)
    if stopping and booking:
        raise Stopped(128 + stopping[0])


def retried(step, run, retries=POLL_RETRIES):
    """`step(run)`, tried again a poll apart up to `retries` times when it fails; a stop is never retried."""
    for attempt in range(retries + 1):
        try:
            return step(run)
        except Stopped:
            raise
        except (Exception, SystemExit) as error:  # noqa: BLE001 - kubectl or the provider: tried again, then raised
            if attempt == retries:
                raise
            say(f"the look at the cluster failed ({attempt + 1} of {retries + 1}): {type(error).__name__}: {error}; "
                f"again in {POLL_SECONDS} s")
            time.sleep(POLL_SECONDS)


def poll(run):
    """One look at the cluster: each job's state, the kinds to widen, the nodes."""
    jobs, pods, no_grow = run.read()
    for job_id in run.unfinished():
        if run.jobs[job_id]["submitted"] is None:
            continue
        found = run.current(job_id, jobs)
        if found is None:
            run.make(job_id)
            continue
        run.update_job(job_id, found, pods.get(manifests.label_value(job_id), []))
    run.widen(pods, no_grow)
    run.watch_nodes()


def look(run, parallel):
    """One turn of the run's loop: a poll, the next jobs put on, the batch cap checked."""
    poll(run)
    submit_more(run, parallel)
    why = over_limits(run)
    if why:
        stop_run(run, why)
    else:
        hold_idle(run)


QUANTITY_UNITS = {"m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15,
                  "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50}


def quantity(text):
    """A Kubernetes quantity ("70m", "1200Gi", "24") as a number."""
    text = str(text)
    for unit in sorted(QUANTITY_UNITS, key=len, reverse=True):
        if text.endswith(unit):
            return float(text[:-len(unit)]) * QUANTITY_UNITS[unit]
    return float(text)


FORBIDDEN_QUOTA = []  # said once a process: the login may not read the namespace's quotas (quota_room)


def quota_room(kubectl):
    """What the jobs' namespace's ResourceQuotas leave, hard less used, by the quotas' own resource names (the
    tenant's: requests.cpu, requests.memory, requests.nvidia.com/gpu), the least over its quotas; {} with none, and
    {} (said once) when the login may not read them: Jobs then go as before the quota check, the quota still refusing
    a pod past it (2026-11-07, checkout 43: the conductor's scoped login has no resourcequotas right, and every
    cluster submit failed its row)."""
    try:
        quotas = kubectl.json("get", "resourcequota", "-n", manifests.NAMESPACE)["items"]
    except subprocess.CalledProcessError as refused:
        if "forbidden" not in str(refused.stderr or "").lower():
            raise
        if not FORBIDDEN_QUOTA:
            FORBIDDEN_QUOTA.append(True)
            say(f"the quota of {manifests.NAMESPACE} is not readable by this login (forbidden): Jobs go unchecked "
                "against it")
        return {}
    room = {}
    for quota in quotas:
        status = quota.get("status", {})
        used = status.get("used", {})
        for name, hard in (status.get("hard") or quota.get("spec", {}).get("hard", {})).items():
            left = quantity(hard) - quantity(used.get(name, "0"))
            room[name] = min(room.get(name, left), left)
    return room


def quota_demand(spec, cards):
    """What one pod of the job takes from a quota, by the names a ResourceQuota counts it under."""
    asked = manifests.resources(spec, cards)
    demand = {"pods": 1, "count/pods": 1, "count/jobs.batch": 1}
    for name, value in asked["requests"].items():
        demand[f"requests.{name}"] = quantity(value)
        if name in ("cpu", "memory"):
            demand[name] = quantity(value)
    for name, value in asked["limits"].items():
        demand[f"limits.{name}"] = quantity(value)
    return demand


def fits(demand, room):
    """Whether a pod asking `demand` fits in the quota's `room` (only what it asks is checked)."""
    return all(left >= demand[name] for name, left in room.items() if demand.get(name))


def submit_more(run, parallel=None):
    """Put the run's next jobs on the cluster while fewer than `parallel` of its jobs are there unfinished (all of
    them when `parallel` is None): the run's queue, which holds a run to that many nodes of one card each. A Job is
    made only while the namespace's quota has room for its pod (quota_room, read once a call); the rest wait here,
    not as Jobs whose pods the quota refuses (a refused pod's Job sat to its deadline and was made again)."""
    if all(run.jobs[job_id]["submitted"] is not None for job_id in run.unfinished()):
        return
    room, held = quota_room(run.kubectl), 0
    for job_id in run.unfinished():
        on_cluster = sum(1 for record in run.jobs.values()
                         if record["submitted"] is not None and record["state"] == "waiting")
        if parallel is not None and on_cluster >= parallel:
            break
        if run.jobs[job_id]["submitted"] is not None:
            continue
        spec = run.specs[job_id]
        demand = quota_demand(spec, job_cards(spec, run.allowed(job_id)))
        if not fits(demand, room):
            held += 1
            continue
        run.make(job_id)
        room = {name: left - demand.get(name, 0) for name, left in room.items()}
    if held != run.held:
        say(f"{held} jobs wait for room in the {manifests.NAMESPACE} quota" if held else "the quota has room again")
        run.held = held


def submit(run_id, specs, store, kubectl=None, cluster=None, wait_scale_down=True, who=None, parallel=None):
    """Run every job of `specs` ({job id: job.json}) not yet done to its end on the cluster; the ledger entries
    written. `store` is the run's object store (the runtime's), where done.json says a job is finished. A runner
    that must not wait for its nodes to go (`wait_scale_down=False`) records them as gone after
    IDLE_ESTIMATE_MINUTES, marked estimated; `who` is the session asking, kept in the ledger; `parallel` holds the
    run to that many jobs on the cluster at once (submit_more)."""
    cluster = cluster or cluster_module()
    kubectl = kubectl or cluster_kubectl(cluster)
    helper = runtime()
    finished = [job_id for job_id in specs if helper.state(store, run_id, job_id) == "done"]
    if finished:
        say(f"{len(finished)} jobs of the run are done already; they are not run again")
    specs = {job_id: spec for job_id, spec in specs.items() if job_id not in finished}
    if not specs:
        return []
    prepare(kubectl, cluster)
    run = Run(run_id, specs, kubectl, cluster)
    with stopped_on_signal() as booking:
        try:
            watch(run, parallel, wait_scale_down)
        except Stopped:
            booking.append(True)
            say("stopped by a signal: deleting the run's Jobs and booking its rows")
            stop_after_signal(run)
            book(run, store, helper, who)
            raise
        except BaseException as error:
            booking.append(True)
            say(f"the run's watch ended ({type(error).__name__}: {error}): booking its rows from what was last seen")
            lost_watch(run)
            book(run, store, helper, who)
            raise
        booking.append(True)
        return book(run, store, helper, who)


def watch(run, parallel, wait_scale_down):
    """The run on the cluster to its end: its Jobs taken up and put on, a look every POLL_SECONDS (each retried) while
    any is unfinished, this process marked in CLUSTER_WAITING meanwhile, then its nodes' end waited for or estimated
    (from what was last seen when the cluster cannot be read)."""
    retried(Run.resume, run)
    retried(lambda found: submit_more(found, parallel), run)
    say(f"{len(run.specs)} jobs for run {run.run_id}" + (f", {parallel} at a time" if parallel else ""))
    mark = CLUSTER_WAITING / str(os.getpid())
    try:
        while run.unfinished():
            mark.parent.mkdir(parents=True, exist_ok=True)
            mark.touch()
            time.sleep(POLL_SECONDS)
            retried(lambda found: look(found, parallel), run)
    finally:  # the outputs come back after this: the node counts for a --jobs slot again
        mark.unlink(missing_ok=True)
    try:
        if wait_scale_down:
            wait_for_scale_down(run)
        else:
            estimate_scale_down(run)
    except Stopped:
        raise
    except (Exception, SystemExit) as error:  # noqa: BLE001 - every job has ended: booked from the last look
        say(f"the run's nodes could not be read at its end ({type(error).__name__}: {error}); booked as last seen")
        last_seen_scale_down(run)


def stop_after_signal(run):
    """A stopped run: every Job of it deleted (said, not raised, when kubectl fails: the rows are booked still), its
    jobs not done marked stopped, its nodes taken as gone after the autoscaler's idle time from one more look, else
    from what was last seen."""
    try:
        stop_jobs(run.kubectl, run.run_id)
    except (Exception, SystemExit) as error:  # noqa: BLE001 - the rows are booked whatever kubectl said
        say(f"the run's Jobs could not be deleted ({type(error).__name__}: {error}); delete them by the label "
            f"{RUN_LABEL}={manifests.label_value(run.run_id)}")
    for job_id in run.unfinished():
        run.jobs[job_id]["state"] = "stopped"
    for seen in run.nodes.values():
        seen.pop("warm_until", None)  # its holds went with its Jobs
    try:
        estimate_scale_down(run)
    except (Exception, SystemExit) as error:  # noqa: BLE001 - booked from the last look instead
        say(f"the run's nodes could not be read ({type(error).__name__}: {error}); booked as last seen")
        last_seen_scale_down(run)


def lost_watch(run):
    """A run whose watch failed past its retries: its jobs not done marked unwatched, its nodes as last seen."""
    for job_id in run.unfinished():
        run.jobs[job_id]["state"] = "unwatched"
    last_seen_scale_down(run)


def book(run, store, helper, who):
    """Write the run's ledger rows (one a kind) with the runtime's timings of its done jobs, and say them; the rows. A
    store that cannot be read leaves the timings out, said, never the rows."""
    try:
        timings = {job_id: helper.done(store, run.run_id, job_id) for job_id, record in run.jobs.items()
                   if record["state"] == "done"}
    except Exception as error:  # noqa: BLE001 - the rows are booked without the timings
        say(f"the done jobs' timings could not be read ({type(error).__name__}: {error}); booked without them")
        timings = {}
    entries = [dict(entry, who=who) if who else entry for entry in ledger_entries(run, timings)]
    for entry in entries:
        ledger.record(entry)
    report(run, entries)
    return entries


def wait_for_scale_down(run):
    """Wait until the run's nodes are gone (the autoscaler removes empty nodes), at most SCALE_DOWN_WAIT_MINUTES."""
    deadline = time.time() + SCALE_DOWN_WAIT_MINUTES * 60
    while time.time() < deadline:
        run.watch_nodes()
        if all(seen["deleted"] for seen in run.our_nodes().values()):
            return
        time.sleep(POLL_SECONDS)
    say("some of the run's nodes are still up; their minutes are counted until now")


def estimate_scale_down(run):
    """Take each of the run's nodes still up as gone IDLE_ESTIMATE_MINUTES from now (the autoscaler's measured
    scale-down), marked estimated."""
    run.watch_nodes()
    last_seen_scale_down(run)


def last_seen_scale_down(run):
    """estimate_scale_down from the nodes as last seen, with no look at the cluster: a node kept warm goes once its
    hold ends (a later run that takes it counts it again from its own start: an overcount, never an undercount)."""
    now = time.time()
    for seen in run.our_nodes().values():
        if seen["deleted"] is None:
            gone = max(now, seen.get("warm_until") or 0) + IDLE_ESTIMATE_MINUTES * 60
            seen["deleted"], seen["estimated"] = gone, True


def job_rows(run, kind, timings):
    """The kind's jobs: their outcome, the class and node they ran on, the wait from submit to the pod running, and
    the runtime's own timings from done.json."""
    rows = {}
    for job_id, record in run.jobs.items():
        if job_kind(run.specs[job_id]) != kind:
            continue
        seen = run.nodes.get(record["node"] or "", {})
        rows[job_id] = {"state": record["state"], "generation": record["generation"], "node": record["node"],
                        "class": seen.get("class"), "type": seen.get("type"), "zone": seen.get("zone"),
                        "wait_minutes": (record["ran"] - run.started) / 60 if record["ran"] else None,
                        "timings": timings.get(job_id, {}).get("timings")}
    return rows


def node_machines(run, kind):
    """The kind's nodes as ledger machine records: the first kind that ran on a node owns it, and a node that ran
    none of the run's jobs belongs to the first kind whose classes hold it (marked unused)."""
    owner = {}
    for job_id, record in sorted(run.jobs.items(), key=lambda item: item[1]["ran"] or 0):
        if record["node"]:
            owner.setdefault(record["node"], job_kind(run.specs[job_id]))
    used = run.used_nodes()
    machines = []
    for name, seen in run.our_nodes().items():
        if name not in used:
            owner[name] = next((job_kind(run.specs[job_id]) for job_id in run.specs
                                if seen["class"] in run.orders[job_id][0]), None)
        if owner.get(name) != kind:
            continue
        per_minute, unit = run.cluster.price(seen["type"], seen["zone"])
        # A node up before the run (a warm one) counts from the run's start, ready at once: its earlier minutes
        # belong to the runs before.
        created = max(seen["created"] or run.started, run.started)
        machines.append({"type": seen["type"], "zone": seen["zone"], "cards": seen["cards"], "created": created,
                         "ready": max(seen["ready"], created) if seen["ready"] else None,
                         "deleted": seen["deleted"] or time.time(), "price": per_minute,
                         "unit_minutes": unit, "class": seen["class"], "node": name, "unused": name not in used,
                         "estimated": seen.get("estimated", False), "share": run.share(name, seen)})
    return machines


def ledger_entries(run, timings):
    """One ledger entry a kind: its nodes' rows (class added) and its jobs."""
    entries = []
    for kind in run.kinds:
        machines = node_machines(run, kind)
        record = ledger.machines_record(machines, [], run.started)
        for row, machine in zip(record["machines"], machines):
            row.update({"class": machine["class"], "node": machine["node"], "unused": machine["unused"],
                        "end_estimated": machine["estimated"]})
        jobs = job_rows(run, kind, timings)
        entries.append({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(run.started)),
                        "batch": run.run_id, "kind": kind, "path": "k8s", **record, "jobs": jobs,
                        "jobs_done": sum(1 for row in jobs.values() if row["state"] == "done"),
                        "wall_minutes": (time.time() - run.started) / 60})
    return entries


def report(run, entries):
    for entry in entries:
        say(f"{entry['kind']}: {entry['jobs_done']} of {len(entry['jobs'])} jobs done in {entry['wall_minutes']:.0f} "
            f"min on {len(entry['machines'])} nodes, {entry['machine_minutes']:.0f} node minutes, "
            f"€{entry['euros']:.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run every job.json of a run in the object store")
    run.add_argument("run_id")
    commands.add_parser("idle", help="hold every class pool at zero nodes")
    commands.add_parser("down", help="delete the cluster")
    options = parser.parse_args()
    cluster = cluster_module()
    if options.command == "idle":
        print(json.dumps(cluster.idle(), indent=1))
    elif options.command == "down":
        cluster.down()
    else:
        store = runtime().cloud_store()
        submit(options.run_id, run_specs(store, options.run_id), store, cluster=cluster)


if __name__ == "__main__":
    main()
