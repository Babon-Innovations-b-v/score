"""The submitter of the job path: runs a run's jobs as Kubernetes Jobs on whatever cluster the kubeconfig points at,
waits for them, and records what each node cost.

    python3 tools/cloud/k8s/submitter.py run <run id>          # every runs/<run id>/*/job.json in the object store
    python3 tools/cloud/k8s/submitter.py idle                  # every class pool held at zero nodes
    python3 tools/cloud/k8s/submitter.py down                  # delete the cluster (SCORE_K8S_PROVIDER's, scaleway)

A run is a set of job specs (`runs/<run>/<job>/job.json`, written by the runtime's helper, `../CLAUDE.md`). The
submitter is the run's queue: it makes the namespace and the two Secrets (the object store and the image pull
secret, from the provider's object_store() and registry() at submit time, never written to disk), caps every
pool's size from the month's euros left, makes one Job a job (`manifests.py`) and then, every POLL_SECONDS, reads
the Jobs, their pods, the autoscaler's events on them and the nodes.

The order of classes. A kind's classes and their order come from `tools/props/cloud/capacity.py` (KINDS,
KIND_ORDER, LATE), never copied; a spec may name its own `classes` (as `--classes` does for the machine runners).
A Job starts allowed on the kind's first class only, so the cluster autoscaler grows that class's pools (in any of
their zones). When the autoscaler says it cannot (every pool of the allowed classes backed off after a failed
scale-up, at its max size, or out of stock), or no node came for NODE_MINUTES, the kind is widened by one class:
its waiting Jobs are made again (a new generation) allowed on one more class, keeping the earlier ones, so a card
that comes back in stock is still taken. Classes in LATE are added only after LATE_MINUTES. Once every class is
allowed, the autoscaler keeps retrying the backed-off pools on its own (5 min, doubling to 30), and a Job whose
deadline passes while it never ran is made again: the run never settles for one card, it waits for any.

Robustness. A Job's pod is retried by Kubernetes up to attempt_limit (backoffLimit); the runtime writes done.json
last and exits at once if it exists, so a Job made again (a lost node, a widened class, a restarted submitter)
redoes only unfinished work. The submitter finds a run's Jobs by label, so running it again on the same run resumes.

Cost. Nothing is submitted when the month's spend (the provider's bill or the ledger, whichever is higher) has
reached SCORE_MONTH_EUROS. Each pool's max size is what the euros left pay for ledger.BATCH_HOURS a node, and the
live cost of the run's nodes is checked every poll against the batch cap (ledger.BATCH_EUROS) and the month's
ceiling: past either, the waiting Jobs are deleted and every pool is capped to zero. Empty nodes go after the
autoscaler's scale-down time (the cluster module sets it), so an idle cluster costs only its small system pool;
`down` deletes the whole cluster. At the end the submitter waits for the run's nodes to go, then writes one ledger
row a node (ledger.machines_record: its class, type, zone, minutes and euros) and the run's jobs with their wait
until the pod ran.
"""
import argparse
import collections
import datetime
import importlib.util
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CLOUD = HERE.parents[1] / "props" / "cloud"
sys.path.insert(0, str(CLOUD.parent))
sys.path.insert(0, str(CLOUD))
sys.path.insert(0, str(HERE))

import capacity  # noqa: E402
from kube import Kubectl  # noqa: E402
import ledger  # noqa: E402
import manifests  # noqa: E402
import provider  # noqa: E402

POLL_SECONDS = 20
# How long a class may be tried with a pod still waiting and no word from the autoscaler before the next class is
# allowed: the upstream autoscaler gives up on a node that has not joined after 15 min (max-node-provision-time).
NODE_MINUTES = 15
# How long the autoscaler's "cannot grow" is watched before it counts: it says so for a moment while it reads a
# newly allowed pool.
NO_GROW_GRACE_MINUTES = 1.5
NO_GROW_WORDS = ("in backoff after failed scale-up", "max node group size reached", "max cluster", "out of stock")
# How long the end waits for the run's nodes to be removed by the autoscaler before recording them as still up.
SCALE_DOWN_WAIT_MINUTES = 20
INSTANCE_LABEL = "node.kubernetes.io/instance-type"
ZONE_LABEL = "topology.kubernetes.io/zone"


def say(line):
    print(time.strftime("%H:%M:%S ") + line, flush=True)


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
    """The cluster module of SCORE_K8S_PROVIDER (default scaleway), loaded by path: its file shares its name with
    the provider's backend."""
    name = name or os.environ.get("SCORE_K8S_PROVIDER", "scaleway")
    spec = importlib.util.spec_from_file_location(f"cluster_{name}", HERE / "clusters" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# kubectl.

def kubeconfig(cluster):
    """The kubeconfig kubectl uses: KUBECONFIG when set, else the cluster module's fetched one."""
    return os.environ.get("KUBECONFIG") or str(cluster.KUBECONFIG)


# The order of classes.

def class_order(kind, spec, pool_classes):
    """The classes a job may take, in the order to take them, and which of them only after LATE_MINUTES: the spec's
    own `classes`, else capacity's for its kind in the kind's order; only classes the cluster has pools for."""
    if spec.get("classes"):
        wanted = list(spec["classes"])
    else:
        wanted = sorted(capacity.classes_for(kind), key=lambda name: capacity.speed_rank(name, kind))
    order = [name for name in wanted if name in pool_classes]
    if not order:
        raise SystemExit(f"the cluster has no pool for any class of the job kind '{kind}' ({', '.join(wanted)})")
    return order, set(capacity.late_for(kind)) & set(order)


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
        self.orders = {job_id: class_order(spec["kind"], spec, pool_classes) for job_id, spec in specs.items()}
        self.kinds = {spec["kind"]: {"step": 1, "since": self.started, "first": self.started}
                      for spec in specs.values()}
        self.jobs = {job_id: {"generation": 0, "state": "waiting", "submitted": None, "ran": None, "node": None}
                     for job_id in specs}
        self.nodes = {}

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
            record["submitted"] = record["submitted"] or self.started
            kind = self.kinds[self.specs[job_id]["kind"]]
            kind["step"] = max(kind["step"], len(notes.get("score.dev/classes", "").split(",")))

    def allowed(self, job_id):
        """The classes a job is allowed on now: its kind's first `step` classes, in order."""
        order, _late = self.orders[job_id]
        return order[:self.kinds[self.specs[job_id]["kind"]]["step"]]

    def make(self, job_id):
        """Make the job's Job at its current generation and classes."""
        spec = self.specs[job_id]
        classes = self.allowed(job_id)
        self.kubectl.apply([manifests.job(spec, self.run_id, job_id, classes, job_cards(spec, classes),
                                          self.jobs[job_id]["generation"])])
        self.jobs[job_id]["submitted"] = time.time()

    def remake(self, job_id):
        """Delete the job's Job and make the next generation (with the classes allowed now)."""
        record = self.jobs[job_id]
        self.kubectl.delete_job(manifests.job_name(self.run_id, job_id, record["generation"]))
        record["generation"] += 1
        self.make(job_id)

    def read(self):
        """The run's Jobs by name, its pods by job label, and the autoscaler's events on its pods."""
        selector = f"score.dev/run={manifests.name_part(self.run_id)[:63]}"
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
            if spec["kind"] != kind or self.jobs[job_id]["state"] != "waiting":
                continue
            for pod in pods.get(manifests.name_part(job_id)[:63], []):
                since = unscheduled_since(pod)
                if since is not None:
                    waiting.append((since, no_grow.get(pod["metadata"]["name"])))
        return waiting

    def widen(self, pods, no_grow):
        """Give each kind whose allowed classes cannot be had its next class, and make its waiting Jobs again."""
        now = time.time()
        for kind, state in self.kinds.items():
            job_ids = [job_id for job_id, spec in self.specs.items() if spec["kind"] == kind]
            order, late = self.orders[job_ids[0]]
            if not may_widen(state, order, late, now) or not wants_widening(
                    state, self.waiting_pods(kind, pods, no_grow), now):
                continue
            state["step"] += 1
            state["since"] = now
            say(f"{kind}: {', '.join(order[:state['step'] - 1])} cannot be had now; adding {order[state['step'] - 1]}")
            for job_id in job_ids:
                if self.jobs[job_id]["state"] == "waiting" and self.jobs[job_id]["ran"] is None:
                    self.remake(job_id)

    def watch_nodes(self):
        """Note every class node: its class, type and zone (from its labels, else from the provider's record), when
        the provider made it, when it was Ready, when last seen."""
        billed = {node["name"]: node for node in self.cluster.nodes()}
        listed = self.kubectl.json("get", "nodes")["items"]
        for node in listed:
            meta = node["metadata"]
            machine_class = meta["labels"].get(manifests.CLASS_LABEL)
            if not machine_class:
                continue
            provider_record = billed.get(meta["name"], {})
            seen = self.nodes.setdefault(meta["name"], {
                "class": machine_class, "cards": provider.cards(machine_class),
                "type": (meta["labels"].get(INSTANCE_LABEL) or provider_record.get("type", "?")).upper(),
                "zone": meta["labels"].get(ZONE_LABEL) or provider_record.get("zone", "?"),
                "created": provider_record.get("created") or parse_time(meta["creationTimestamp"]),
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

    def used_nodes(self):
        """The nodes a job of this run ran on."""
        return {record["node"] for record in self.jobs.values() if record["node"]}

    def our_nodes(self):
        """The nodes this run pays for: those its jobs ran on, and those the autoscaler made during the run that ran
        none of them (it grows a node for each waiting pod, and a faster node may take the pod first: a second L4
        came up unused on 2026-10-09). With two runs on one cluster an unused node is counted by both."""
        used = self.used_nodes()
        return {name: seen for name, seen in self.nodes.items()
                if name in used or (seen["created"] or 0) >= self.started}

    def live_euros(self):
        """What the run's nodes have cost so far."""
        total = 0.0
        for seen in self.our_nodes().values():
            per_minute, unit = self.cluster.price(seen["type"], seen["zone"])
            total += ledger.cost(((seen["deleted"] or time.time()) - seen["created"]) / 60, per_minute, unit)
        return total

    def unfinished(self):
        return [job_id for job_id, record in self.jobs.items() if record["state"] == "waiting"]


def month_spent(cluster):
    """What the month has cost so far: the provider's bill or the ledger, whichever is higher."""
    return max(cluster.month_spend(), ledger.month_total(ledger.this_month(), ledger.entries()))


def over_limits(run, spent_before):
    """Why the run must stop now (the batch cap or the month's ceiling), or None."""
    live = run.live_euros()
    if live >= ledger.BATCH_EUROS:
        return f"the run's nodes have cost €{live:.2f}, at the €{ledger.BATCH_EUROS:.0f} batch cap"
    if spent_before + live >= ledger.MONTH_EUROS:
        return f"€{spent_before + live:.2f} spent this month, at the €{ledger.MONTH_EUROS:.0f} ceiling"
    return None


def stop_run(run, why):
    """Delete the run's waiting Jobs and cap every pool to zero."""
    say(f"stopping: {why}")
    for job_id in run.unfinished():
        run.kubectl.delete_job(manifests.job_name(run.run_id, job_id, run.jobs[job_id]["generation"]))
        run.jobs[job_id]["state"] = "stopped"
    run.cluster.cap_pools(0, 1)


def prepare(kubectl, cluster, spent):
    """Make the namespace and the Secrets, and cap the pools from the euros left; refuse at the ceiling."""
    if spent >= ledger.MONTH_EUROS:
        raise SystemExit(f"€{spent:.2f} spent this month, at the €{ledger.MONTH_EUROS:.0f} ceiling: nothing is "
                         "submitted")
    kubectl.apply([manifests.namespace()])
    kubectl.apply([manifests.store_secret(provider.cloud.object_store()),
                   manifests.registry_secret(provider.cloud.registry())])
    caps = cluster.cap_pools(ledger.MONTH_EUROS - spent, ledger.BATCH_HOURS)
    say("pool caps: " + ", ".join(f"{name} {cap}" for name, cap in sorted(caps.items())))


def poll(run):
    """One look at the cluster: each job's state, the kinds to widen, the nodes."""
    jobs, pods, no_grow = run.read()
    for job_id in run.unfinished():
        found = run.current(job_id, jobs)
        if found is None:
            run.make(job_id)
            continue
        run.update_job(job_id, found, pods.get(manifests.name_part(job_id)[:63], []))
    run.widen(pods, no_grow)
    run.watch_nodes()


def submit(run_id, specs, store, kubectl=None, cluster=None):
    """Run every job of `specs` ({job id: job.json}) not yet done to its end on the cluster; the ledger entries
    written. `store` is the run's object store (the runtime's), where done.json says a job is finished."""
    cluster = cluster or cluster_module()
    kubectl = kubectl or Kubectl(kubeconfig(cluster))
    helper = runtime()
    finished = [job_id for job_id in specs if helper.state(store, run_id, job_id) == "done"]
    if finished:
        say(f"{len(finished)} jobs of the run are done already; they are not run again")
    specs = {job_id: spec for job_id, spec in specs.items() if job_id not in finished}
    if not specs:
        return []
    spent = month_spent(cluster)
    prepare(kubectl, cluster, spent)
    run = Run(run_id, specs, kubectl, cluster)
    run.resume()
    for job_id in specs:
        if run.jobs[job_id]["submitted"] is None:
            run.make(job_id)
    say(f"{len(specs)} jobs on the cluster for run {run_id}")
    while run.unfinished():
        time.sleep(POLL_SECONDS)
        poll(run)
        why = over_limits(run, spent)
        if why:
            stop_run(run, why)
    wait_for_scale_down(run)
    timings = {job_id: helper.done(store, run_id, job_id) for job_id, record in run.jobs.items()
               if record["state"] == "done"}
    entries = ledger_entries(run, timings)
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


def job_rows(run, kind, timings):
    """The kind's jobs: their outcome, the class and node they ran on, the wait from submit to the pod running, and
    the runtime's own timings from done.json."""
    rows = {}
    for job_id, record in run.jobs.items():
        if run.specs[job_id]["kind"] != kind:
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
            owner.setdefault(record["node"], run.specs[job_id]["kind"])
    used = run.used_nodes()
    machines = []
    for name, seen in run.our_nodes().items():
        if name not in used:
            owner[name] = next((run.specs[job_id]["kind"] for job_id in run.specs
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
                         "unit_minutes": unit, "class": seen["class"], "node": name, "unused": name not in used})
    return machines


def ledger_entries(run, timings):
    """One ledger entry a kind: its nodes' rows (class added) and its jobs."""
    entries = []
    for kind in run.kinds:
        machines = node_machines(run, kind)
        record = ledger.machines_record(machines, [], run.started)
        for row, machine in zip(record["machines"], machines):
            row.update({"class": machine["class"], "node": machine["node"], "unused": machine["unused"]})
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
