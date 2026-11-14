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
  Break: `created = seen["created"]` in `node_machines`. Break: drop the `hosted` return in `Run.share`. Runs side by side book each node at their part, whole
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

CARDS = ["gpu-24gb", "gpu-48gb", "gpu-80gb"]
LONG_RUN = "Run_2026-10-09T15:00_" + "a" * 80
LONG_NAME = "score-" + "a" * 52 + "-0-g1"  # LONG_RUN's job 0: the end kept, at 63 characters
REFUSED = "nor one that holds it"
DONE = ({"type": "Complete", "status": "True"}, True, "done")
FAILED_BEFORE_IT_RAN = ({"type": "Failed", "status": "True"}, False, "failed")  # a failure, never a wait to remake
EXPIRED_AFTER_IT_RAN = ({"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}, True, "failed")
FORBIDDEN = "forbidden"
TENANTS_OWN = "the tenant module's own taints"  # the row's cluster has tenant.TOLERATIONS; every other row has none
# a run of five jobs through the door: its jobs' runner settings (kind, the image's kind, classes, attempts), the
# cluster's pools and own taints, capacity's late classes, the run's name, how its job 0's Job ends (whether its pod
# ran first), whether the login may read the namespace's quota; then what job 0 takes: the kind it is known by, its
# classes in order, the late ones, its cards and the name of its last Job (each class added makes it again, and a
# wait past its deadline once more), or the refusal
CASES = {
    "pixal-capacitys-order-a-late-class": (dict(kind="pixal"), POOLS, (), {"pixal": ("gpu-48gb",)}, "r", DONE,
                                           "readable", ("pixal", ["gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2"],
                                                        {"gpu-48gb"}, 1, "score-r-0-g4")),
    "meshparts-capacitys-order": (dict(kind="meshparts"), POOLS, (), {}, "r1", FAILED_BEFORE_IT_RAN, "readable",
                                  ("meshparts", ["gpu-24gb", "gpu-48gb", "gpu-80gb"], set(), 1, "score-r1-0-g3")),
    "own-classes-preferred-in-their-order": (dict(kind="pixal", classes=["gpu-80gb", "gpu-48gb"], attempt_limit=3),
                                             POOLS, (), {}, "run-1", DONE, FORBIDDEN,
                                             ("pixal", ["gpu-80gb", "gpu-48gb"], set(), 1, "score-run-1-0-g2")),
    "a-bake-never-takes-an-h100": (dict(kind="library", classes=CARDS), POOLS, (), {}, "r2", EXPIRED_AFTER_IT_RAN,
                                   "readable", ("library", ["gpu-24gb", "gpu-48gb"], set(), 1, "score-r2-0-g2")),
    "a-bake-in-the-blender-image": (dict(kind="library", image="blender", classes=CARDS, attempt_limit=1), POOLS,
                                    (), {}, "Run_A", DONE, "readable",
                                    ("library", ["gpu-24gb", "gpu-48gb"], set(), 1, "score-run-a-0-g2")),
    "a-processor-class-asks-no-card": (dict(kind="blender", classes=["cpu-32c-128gb"]), POOLS, (), {}, "run-2",
                                       DONE, "readable", ("blender", ["cpu-32c-128gb"], set(), 0, "score-run-2-0-g1")),
    # the tenant's own taint, a long run name, and the tenant's scoped login that may not read the quota
    "a-long-name-and-a-login-that-may-not-read-the-quota": (dict(kind="pixal", classes=["gpu-24gb"]), POOLS,
                                                            TENANTS_OWN, {}, LONG_RUN, DONE, FORBIDDEN,
                                                            ("pixal", ["gpu-24gb"], set(), 1, LONG_NAME)),
    # no pool for any of a job's classes: the nearest pool that holds it (#76: settle's 4 cores, the paint's 16, 32)
    "settles-4-cores-on-the-32-core-pool": (dict(kind="blender", classes=["cpu-4c-32gb"]), POOLS, (), {}, "r3", DONE,
                                            FORBIDDEN, ("blender", ["cpu-32c-128gb"], set(), 0, "score-r3-0-g1")),
    "the-smallest-pool-that-holds-it": (dict(kind="blender", classes=["cpu-32c-64gb", "cpu-16c-64gb"]),
                                        POOLS | {"cpu-64c-256gb"}, (), {}, "r4", DONE, "readable",
                                        ("blender", ["cpu-32c-128gb"], set(), 0, "score-r4-0-g1")),
    "a-card-pair-on-the-h100-pair": (dict(kind="pixal", classes=["gpu-24gb-x2"]), POOLS, (), {}, "r5", DONE,
                                     "readable", ("pixal", ["gpu-80gb-x2"], set(), 1, "score-r5-0-g1")),
    "only-an-h100-pair-holds-it-never-blender": (dict(kind="blender", classes=["gpu-24gb-x2"]), POOLS, (), {}, "r6",
                                                 DONE, "readable", REFUSED),
    "no-pool-holds-it": (dict(kind="blender", classes=["cpu-64c-256gb"]), POOLS, (), {}, "r7", DONE, "readable",
                         REFUSED),
}
CANNOT_GROW = "pod didn't trigger scale-up: 1 in backoff after failed scale-up"
QUOTA_REFUSED = "Error creating: pods is forbidden: exceeded quota: score-jobs"
PARALLEL = 3  # the run's jobs at once: its five jobs go in two rounds


class LiveKubectl:
    """A cluster's Jobs as kubectl sees them: what the submitter applies is there, pods and events are set by the
    test."""

    def __init__(self):
        self.jobs, self.pods, self.events, self.deleted, self.ran = {}, [], [], [], []

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

    def run(self, *arguments):
        self.ran.append(arguments)
        return ""



class ClusterKubectl(LiveKubectl):
    """The tenant cluster as kubectl sees it: its nodes and pods as given, what the submitter applies there, and the
    commands run, answered with `answer`. Its namespace has the tenant's ResourceQuota when other runs hold `others`
    of its 24 cards (its used counting the cards of each Job not yet ended; none when `others` is None); a login
    whose Role has no resourcequotas right (`others` FORBIDDEN) is forbidden the read, as the tenant's scoped login
    is."""

    HARD = {"requests.cpu": "250", "requests.memory": "1200Gi", "requests.nvidia.com/gpu": "24"}

    def __init__(self, nodes=(), others=None, pods=(), answer=""):
        super().__init__()
        self.nodes, self.others, self.pods, self.answer = list(nodes), others, list(pods), answer

    def json(self, *arguments):
        if arguments[1] == "nodes":
            return {"items": self.nodes}
        if arguments[1] == "pods":
            return {"items": self.pods}
        if arguments[1] != "resourcequota":
            return super().json(*arguments)
        if self.others is None:
            return {"items": []}
        if self.others == FORBIDDEN:
            raise submit.subprocess.CalledProcessError(
                1, ["kubectl", *arguments], stderr='Error from server (Forbidden): resourcequotas is forbidden: User '
                                                   '"system:serviceaccount:score:score-conductor" cannot list resource')
        cards = sum(int(job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"].get(
            "nvidia.com/gpu", "0")) for job in self.jobs.values() if not job.get("status", {}).get("conditions"))
        used = {"requests.cpu": "66070m", "requests.memory": "440Gi", "requests.nvidia.com/gpu": str(self.others + cards)}
        return {"items": [{"spec": {"hard": self.HARD}, "status": {"hard": self.HARD, "used": used}}]}

    def run(self, *arguments):
        self.ran.append(arguments)
        return self.answer


STORE = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "AK", "secret_key": "SK"}
REGISTRY = {"endpoint": "registry.example/score", "username": "nologin", "password": "PW"}  # the rows' images'
OPERATOR = {"driver": {"repository": "nvcr.io/nvidia", "image": "driver", "version": "580.126.20",
                       "manager": {"repository": "nvcr.io/nvidia/cloud-native", "image": "k8s-driver-manager",
                                   "version": "v0.11.0"}},
            "toolkit": {"repository": "nvcr.io/nvidia/k8s", "image": "container-toolkit", "version": "v1.19.1"},
            "devicePlugin": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
            "gfd": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
            "validator": {"repository": "nvcr.io/nvidia", "image": "gpu-operator", "version": "v26.3.3"},
            "dcgmExporter": {"repository": "nvcr.io/nvidia/k8s", "image": "dcgm-exporter",
                             "version": "4.5.3-4.8.2-distroless"}}


class OperatorKubectl:
    """kubectl of a cluster whose GPU operator still pulls from nvcr.io, on Ubuntu 24.04 nodes: what is applied is
    recorded, the copy Job completes at once and a merge patch changes the ClusterPolicy."""

    def __init__(self):
        self.spec, self.calls, self.applied = json.loads(json.dumps(OPERATOR)), [], []

    def json(self, *arguments):
        self.calls.append(arguments)
        if arguments[1] == "nodes":
            return {"items": [{"metadata": {"labels": {"feature.node.kubernetes.io/system-os_release.ID": "ubuntu",
                                                       "feature.node.kubernetes.io/system-os_release.VERSION_ID":
                                                           "24.04"}}}]}
        if arguments[1] == "job":
            return {"status": {"conditions": [{"type": "Complete", "status": "True"}]}}
        return {"items": [{"metadata": {"name": "cluster-policy"}, "spec": self.spec}]}

    def apply(self, objects):
        self.applied += objects

    def run(self, *arguments):
        self.calls.append(arguments)
        if arguments[0] == "patch":
            merge(self.spec, json.loads(arguments[-1])["spec"])


def merge(target, patch):
    """A JSON merge patch applied to `target` in place."""
    for key, value in patch.items():
        if isinstance(value, dict):
            merge(target.setdefault(key, {}), value)
        else:
            target[key] = value


def time_text(seconds):
    return submit.datetime.datetime.fromtimestamp(seconds, submit.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        return f"registry.example/score/score-{kind}:1@sha256:00"


class CountedCopies(offload.FolderBucket):
    """The store bucket as a folder, counting the copies made inside it into a job store."""

    copies = 0

    def copy_into(self, key, target, target_key):
        CountedCopies.copies += 1
        super().copy_into(key, target, target_key)


def test_jobs_take_their_classes_in_order(tmp_path, monkeypatch):
    """Runs through the runners' door (cluster_jobs.run, the real submitter under it) on one tenant cluster, over a
    folder store. Each job's inputs go up once and its outputs come back where the runner wants them. A run of five
    jobs reads each job's classes (capacity's order, narrowed to the cluster's pools, else the nearest pool that holds
    them, never one its kind may not take), and is never prepared outside a cleared run. It puts `parallel` jobs on at
    once, each only while the namespace's quota has room for its pod (every one when the login may not read the
    quota), on the first class, and adds one class at a time only once the autoscaler said for the grace time that
    none can grow (a word before the last widening, about a taint, followed by a scale-up, or a quota's refusal does
    not count) or no node came for NODE_MINUTES while a pod waited, a late class after LATE_MINUTES; a Job that waited
    past its deadline is made again with the classes so far; that Job requires exactly them, prefers them in order,
    asks cards only on card classes, bears a Kubernetes name and reads the store and pulls from the registry by the
    Secrets holding them (its cards from a GPU operator mirrored into that registry); the run is marked waiting until
    its job runs, its runaway watch told its Jobs' deadlines once a round, and the job takes its Job's end and the node
    it ran on. A submitter after it takes up the newest generations; the rest go on as room comes; under the owner's
    override the run stops at what is left of his euros less 10%. Runs that are lost, stopped or capped book their row
    from what was last seen and bill only their own nodes, warm holds kept on idle nodes; runs side by side share their
    nodes; the box's queue takes runs, stop-batch ends only score's Jobs, and the cloud settings say which work goes on
    the cluster at all."""
    helper = Helper(tmp_path / "store")
    monkeypatch.setattr(cluster_jobs.submitter, "runtime", lambda: helper)
    seen, uploads, fetches = {}, [], []
    real_upload = helper.store.upload
    real_submit = cluster_jobs.submitter.submit
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
    assert spec["image"].startswith("registry.example/score/score-blender") and spec["classes"] == ["gpu-24gb"]
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

    # one tenant cluster under every run from here (SCORE_K8S_PROVIDER=scaleway/tenant, its module loaded as submit
    # loads it), launched from the conductor's box. A tenant box that cannot read the cluster's project with scw (the
    # conductor, 2026-11-06): its pools as SCORE_K8S_POOLS gives them (no max given: none), its nodes through
    # kubectl, never scw. Break: in tenant.nodes, read `scw("k8s", "node", "list", ...)` again; or in
    # tenant.class_pools, drop the `given is not None` branch. The provider's record of its nodes: a labelled node,
    # a node not tainted for score (not score's), and a node just joined, its cloud labels not set yet, priced by its
    # pool (named in its name), never "? in ?". Break: in tenant.nodes, drop the pool_labels fill
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    monkeypatch.setenv("SCORE_K8S_PROVIDER", "scaleway/tenant")
    monkeypatch.setenv("SCORE_K8S_BOX", "conductor")
    monkeypatch.delenv("SCORE_K8S_NAMESPACE", raising=False)
    monkeypatch.setattr(manifests, "NAMESPACE", manifests.NAMESPACE)  # the module's NAMESPACE, undone after
    tenant = submit.cluster_module()
    assert tenant.NAME == "tenant"
    monkeypatch.setattr(tenant, "scw", lambda *words: pytest.fail(f"scw asked: {words}"))
    monkeypatch.setattr(tenant, "price", lambda machine_type, zone: (0.01, 1))
    monkeypatch.setenv(tenant.POOLS, json.dumps([
        {"name": "score-l4", "class": "gpu-24gb", "type": "L4-1-24G", "zone": "fr-par-2", "max": 10},
        {"name": "score-l40s", "class": "gpu-48gb", "type": "L40S-1-48G", "zone": "fr-par-2"}]))  # a judge's card
    assert tenant.class_pools() == [{"name": "score-l4", "id": "score-l4", "class": "gpu-24gb", "type": "L4-1-24G",
                                     "zone": "fr-par-2", "max": 10, "euros_a_minute": 0.01, "unit_minutes": 1},
                                    {"name": "score-l40s", "id": "score-l40s", "class": "gpu-48gb",
                                     "type": "L40S-1-48G", "zone": "fr-par-2", "max": 0, "euros_a_minute": 0.01,
                                     "unit_minutes": 1}]
    taint = {"key": "tenant", "value": "score", "effect": "NoSchedule"}
    joined = "scw-babon-score-l4-0a1b"
    listed = {"items": [
        {"metadata": {"name": "kosmos-node", "creationTimestamp": "2026-10-09T14:00:00Z",
                      "labels": {tenant.CLASS_LABEL: "cpu-32c-128gb", tenant.POOL_LABEL: "score-pop2",
                                 tenant.INSTANCE_LABEL: "pop2-32c-128g", tenant.ZONE_LABEL: "pl-waw-2"}},
         "spec": {"taints": [taint]}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}},
        {"metadata": {"name": "babons", "creationTimestamp": "2026-11-06T10:00:00Z",
                      "labels": {tenant.CLASS_LABEL: "gpu-24gb"}}, "spec": {}, "status": {}},
        {"metadata": {"name": joined, "creationTimestamp": "2026-11-06T10:00:00Z",
                      "labels": {tenant.CLASS_LABEL: "gpu-24gb"}}, "spec": {"taints": [taint]}, "status": {}}]}
    monkeypatch.setattr(tenant, "kubectl", lambda *words: json.dumps(listed))
    assert tenant.nodes() == [
        {"name": "kosmos-node", "pool": "score-pop2", "type": "POP2-32C-128G", "zone": "pl-waw-2", "status": "ready",
         "created": 1791554400.0},
        {"name": joined, "pool": "score-l4", "type": "L4-1-24G", "zone": "fr-par-2", "status": "not_ready",
         "created": 1793959200.0}]  # an untainted node is not score's

    def cluster_nodes():
        """The cluster's nodes as kubectl lists them: two L4s, a node without zone labels (the provider's record gives
        them), the node just joined (its pool's machine and zone), the conductor's node (its class key no capability
        class: no class node, never a crash), a node seen before its labels came (motor-labval, 2026-11-08: "no price
        for ? in ?"), and the nodes up before a run of none of its jobs."""
        made = lambda name, when, label="gpu-24gb", **more: {  # noqa: E731
            "metadata": {"name": name, "creationTimestamp": when, "labels": {"score.dev/class": label, **more}},
            "status": {"conditions": []}}
        nodes = [made(name, "2026-11-06T10:00:00Z", **{"kubernetes.io/hostname": f"host-{name}"})
                 for name in ("l4-a", "l4-b")]
        nodes += [{"metadata": {"name": "kosmos-node", "creationTimestamp": "2026-10-09T14:50:00Z",
                                "labels": {"score.dev/class": "cpu-32c-128gb"}},
                   "status": {"conditions": [{"type": "Ready", "status": "True",
                                              "lastTransitionTime": "2026-10-09T14:50:13Z"}]}},
                  made(joined, "2026-11-06T10:00:00Z"), made("conductor-node", "2026-11-07T10:00:00Z", "conductor"),
                  made("early-node", "2026-11-08T19:16:00Z")]
        return nodes + [made(name, "2026-11-01T10:00:00Z") for name in ("grown", "other-run", "side-by-side")]

    # never a lost row (#95), the real submitter under the door, on that cluster. A run's first look finishes job 0;
    # then the looks fail, each retried POLL_RETRIES times, or a SIGTERM comes, or the run's nodes reach the batch
    # cap. However it ends, its row is booked from what was last seen (job 1 unwatched, or stopped), the mark that its
    # node holds no --jobs slot is there at every look and gone after, the door still brings back what job 0 made,
    # and its unfinished Jobs are deleted: by its label after a failure or a stop (nothing brings their outputs back
    # now), by name at the cap, its warm holds with them; while it watched it marked them alive for cap_watch's sweep
    # (2026-11-10: a stopped Buy's Jobs ran on for hours). Break: drop `delete_run_jobs(run)` from submit's `except
    # BaseException`; break: drop the `beat_alive` in `watch`.
    # In the "billed" runs job 0 runs on a warm node, the cluster grown meanwhile: the run's nodes are billed from its
    # start and only its own, the warm node it ran on from the start (its earlier minutes are other runs'), the node
    # grown unused during it whole (end estimated), never one made before it unused or hosting another run.
    # In the "warm" runs (owner, 2026-11-06) job 1 first waits for the quota's room: once every job is on the
    # cluster, an idle node a job ran on is held WARM_MINUTES by a pause pod the autoscaler may not evict, asking no
    # card, once an idle spell (a hold is no job), billed to its hold's end; the cap's stop ends the holds.
    clock = [submit.parse_time("2026-11-08T20:00:00Z")]
    monkeypatch.setattr(submit, "time", type("Clock", (), {
        "time": staticmethod(lambda: clock[0]), "sleep": staticmethod(lambda seconds: None),
        "strftime": staticmethod(time.strftime), "gmtime": staticmethod(time.gmtime)}))
    booked, looks, ran = [], [], []
    mark = tmp_path / "waiting" / str(os.getpid())
    kubectl = ClusterKubectl()
    monkeypatch.setattr(cluster_jobs.submitter, "submit", real_submit)
    real_prepare = submit.prepare
    monkeypatch.setattr(submit, "prepare", lambda kubectl, cluster: None)
    monkeypatch.setattr(submit, "cluster_module", lambda name=None: tenant)
    monkeypatch.setattr(submit, "cluster_kubectl", lambda cluster: kubectl)
    monkeypatch.setattr(submit.ledger, "record", booked.append)
    monkeypatch.setattr(submit, "POLL_SECONDS", 0)
    monkeypatch.setattr(submit, "CLUSTER_WAITING", tmp_path / "waiting")
    real_look = submit.look

    # the jobs' classes in order: each row a run of five jobs through the door on that cluster, its pools as the row
    # gives them, its job 0 driven through the run's looks (one a yield of the row's script); the run is marked waiting
    # while none of its jobs ran, told its Jobs' deadlines, and stopped at the end under the owner's override
    marks, deadlines, caps = [], [], []
    monkeypatch.setattr(submit.preflight, "mark_waiting", lambda: marks.append("waiting"))
    monkeypatch.setattr(submit.preflight, "unmark_waiting", lambda: marks.append("ran"))
    monkeypatch.setattr(submit.preflight, "declare_deadline", deadlines.append)
    monkeypatch.setattr(tenant, "cap_pools", lambda euros_left, hours: caps.append((euros_left, hours)) or {})
    allowance = {"name": "labval", "euros": 40.0, "spent": 37.53, "left": 2.47}
    monkeypatch.setattr(submit.compute, "override_room", lambda store=None: allowance)
    late_before, pools_given, taints_before = submit.capacity.LATE, os.environ[tenant.POOLS], tenant.TOLERATIONS

    def waited(seconds, words=(), waiting=True):
        """The cluster at `seconds`: job 0's pod fitting no node, the autoscaler's `words` on it (reason, message,
        when), or with `waiting` False no pod at all, the quota having refused each Job's; then the run's look at it,
        after which job 0 still waits."""
        run, = ran
        clock[0] = seconds
        pod_name = manifests.job_name(run.run_id, "0", run.jobs["0"]["generation"]) + "-pod"
        run.kubectl.pods = [{"kind": "Pod", "metadata": {"name": pod_name, "labels": {"score.dev/job": "0"}},
                             "spec": {}, "status": {"conditions": [{"type": "PodScheduled", "status": "False",
                                                                    "lastTransitionTime": time_text(seconds)}]}}
                            ] if waiting else []
        run.kubectl.events = [{"reason": reason, "involvedObject": {"name": pod_name}, "lastTimestamp": time_text(when),
                               "message": message} for reason, message, when in words] if waiting else [
            {"reason": "FailedCreate", "involvedObject": {"kind": "Job", "name": made}, "message": QUOTA_REFUSED}
            for made in run.kubectl.jobs]
        yield
        assert run.jobs["0"]["state"] == "waiting"  # a Job with no word yet runs on

    def classes_taken(row, given, taints, ends, quota, expected):
        """One row's run, a yield a look of it: job 0 widened class by class, made again past its deadline, then ended
        as the row says; the run's Jobs and the one after it checked between."""
        kind, order, late, cards, name = expected
        run, = ran
        room = 2 if cards and quota == "readable" else len(run.specs)  # what the quota lets on of the five
        assert list(run.kinds) == [kind] and run.orders["0"] == (order, late), row
        assert len(run.kubectl.jobs) == min(PARALLEL, room) and run.jobs["0"]["submitted"], row
        assert run.held == len(run.specs) - room, row  # the card jobs past the quota's 2 cards wait here, not as Jobs
        longest = manifests.deadline_seconds(run.specs["4"])  # its runaway watch: the longest Job's once a round
        assert deadlines == [run.started + 2 * longest] and submit.declared_seconds(run.specs, None) == longest, row
        first = run.kinds[kind]["first"]
        for step in range(1, len(order) + 1):
            assert run.allowed("0") == order[:step] and run.jobs["0"]["generation"] == step - 1, (row, step)
            since = run.kinds[kind]["since"]
            word = ("NotTriggerScaleUp", CANNOT_GROW, since)
            grace = since + submit.NO_GROW_GRACE_MINUTES * 60
            if step % 2:  # the autoscaler said none of the allowed pools can grow
                yield from waited(grace - 1, [word])
                assert run.allowed("0") == order[:step], (row, step)  # not for the grace time yet
                if step < len(order) and order[step] in late and grace < first + submit.capacity.LATE_MINUTES * 60:
                    yield from waited(grace, [word])
                    assert run.allowed("0") == order[:step], (row, step)  # a late class waits
                    grace = first + submit.capacity.LATE_MINUTES * 60
                yield from waited(grace, [word])
                assert run.allowed("0") == order[:step + 1], (row, step)  # one more class, or none left to add
                continue
            # no node came: the autoscaler's words that do not count, then NODE_MINUTES with a pod waiting
            yield from waited(grace, [("NotTriggerScaleUp", CANNOT_GROW, since - 1)])
            assert run.allowed("0") == order[:step], (row, step)  # said before the last widening
            noise = [("NotTriggerScaleUp", "pod didn't trigger scale-up: 8 max node group size reached", since + 10),
                     ("TriggeredScaleUp", "pod triggered scale-up", since + 20),
                     ("NotTriggerScaleUp", "pod didn't trigger scale-up: 1 node(s) had taint", since + 30)]
            node_time = since + submit.NODE_MINUTES * 60
            yield from waited(node_time - 1, noise)
            assert run.allowed("0") == order[:step], (row, step)  # a scale-up followed; a taint is no word to widen
            yield from waited(node_time, waiting=False)
            assert run.allowed("0") == order[:step], (row, step)  # nothing waits: a quota's refusal is no word
            yield from waited(node_time)
            assert run.allowed("0") == order[:step + 1], (row, step)
        assert run.jobs["0"]["generation"] == len(order) - 1, row  # nothing left to add: not made again
        assert set(marks) == {"waiting"}, (row, marks)  # no job ran yet: its runaway watch leaves the wait out

        kubectl = run.kubectl
        expired = kubectl.jobs[manifests.job_name(run.run_id, "0", len(order) - 1)]
        expired["status"] = {"conditions": [{"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}
        kubectl.pods, kubectl.events = [], []
        yield
        assert run.jobs["0"]["state"] == "waiting" and run.jobs["0"]["generation"] == len(order), row  # made again
        assert manifests.job_name(run.run_id, "0", len(order) - 1) in kubectl.deleted, row
        job = kubectl.jobs[name]
        assert job["metadata"]["annotations"]["score.dev/classes"] == ",".join(order), row  # the earlier classes kept
        pod = job["spec"]["template"]["spec"]
        required = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
        assert required["nodeSelectorTerms"][0]["matchExpressions"][0]["values"] == order, row
        preferred = pod["affinity"]["nodeAffinity"]["preferredDuringSchedulingIgnoredDuringExecution"]
        assert [term["preference"]["matchExpressions"][0]["values"] for term in preferred] == [[each] for each in order]
        weights = [term["weight"] for term in preferred]
        assert weights == sorted(set(weights), reverse=True), (row, weights)  # the first weighs most, each less
        assert {toleration["key"] for toleration in pod["tolerations"]} == {"nvidia.com/gpu", "score.dev/class"} | {
            taint["key"] for taint in taints} and all(taint in pod["tolerations"] for taint in taints), row
        container = pod["containers"][0]
        card_ask = {"nvidia.com/gpu": str(cards)} if cards else {}
        assert container["resources"]["limits"] == dict(manifests.NO_LIMIT, **card_ask), row  # past any node's
        assert container["resources"]["requests"].get("nvidia.com/gpu") == card_ask.get("nvidia.com/gpu"), row
        assert container["args"] == [run.run_id, "0"], row
        assert {"name": "cache", "mountPath": "/cache"} in container["volumeMounts"], row
        assert pod["volumes"][0]["hostPath"]["path"] == "/var/lib/score-cache", row
        assert pod["restartPolicy"] == "Never", row
        assert job["spec"]["backoffLimit"] == given.get("attempt_limit", cluster_jobs.ATTEMPTS) - 1, row
        assert job["metadata"]["name"] == name and len(name) <= 63, row  # Kubernetes' name rules
        # one store and one registry: the Job reads the store from the Secret holding its values by name and pulls
        # its image from the registry with the pull Secret holding its login; a card Job's cards come from a GPU
        # operator whose images are copied into that registry with that Secret, its ClusterPolicy pointed there (the
        # manager with no pull secret of its own), a cluster already mirrored left alone
        store_secret, pull = manifests.store_secret(STORE), manifests.registry_secret(REGISTRY)
        assert container["envFrom"] == [{"secretRef": {"name": store_secret["metadata"]["name"]}}], row
        assert base64.b64decode(store_secret["data"]["SCORE_STORE_SECRET_KEY"]).decode() == "SK"
        assert container["image"].startswith(REGISTRY["endpoint"] + "/") and pod["imagePullSecrets"] == [
            {"name": pull["metadata"]["name"]}] and pull["type"] == "kubernetes.io/dockerconfigjson", row
        assert json.loads(base64.b64decode(pull["data"][".dockerconfigjson"]))["auths"]["registry.example"][
            "password"] == "PW"
        if cards:  # the cluster's GPU operator, mirrored once into the registry this Job pulls from, then left alone
            registry = dict(REGISTRY, endpoint=container["image"].rsplit("/", 1)[0])
            secret_name = pod["imagePullSecrets"][0]["name"]
            operator = OperatorKubectl()
            assert gpu_operator.mirror(operator, registry), row
            secret, copy = operator.applied  # not mirrored yet: the pull Secret, then the copy into the registry
            assert secret["metadata"]["name"] == secret_name and secret["data"] == pull["data"], row
            copy = copy["spec"]["template"]["spec"]
            assert copy["volumes"][0]["secret"]["secretName"] == secret_name, row
            script = copy["containers"][0]["command"][2]
            assert (f"nvcr.io/nvidia/driver:580.126.20-ubuntu24.04 {registry['endpoint']}/driver:580.126.20-ubuntu24.04"
                    in script), row
            assert (f"nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.11.0 "
                    f"{registry['endpoint']}/k8s-driver-manager:v0.11.0" in script), row
            driver = operator.spec["driver"]  # the ClusterPolicy as the patch left it
            assert driver["repository"] == driver["manager"]["repository"] == registry["endpoint"], row
            assert operator.spec["validator"]["imagePullSecrets"] == [secret_name], row
            assert "imagePullSecrets" not in driver["manager"], row  # the manager has no pull secret of its own
            operator.calls.clear()
            assert gpu_operator.mirror(operator, registry), row
            assert operator.calls == [("get", "clusterpolicies.nvidia.com")], row  # nothing changed on a mirrored one

        condition, ran_first, state = ends
        node = f"node-{order[-1]}" if ran_first else None  # stock came back on its last class
        kubectl.pods = [{"kind": "Pod", "metadata": {"name": "p", "labels": {"score.dev/job": "0"}},
                         "spec": {"nodeName": node},
                         "status": {"containerStatuses": [{"state": {"running": {"startedAt": time_text(clock[0])}}}]}}
                        ] if ran_first else []
        yield
        assert marks[-1] == ("ran" if ran_first else "waiting"), (row, marks)  # its job runs on a node now: it counts
        job["status"] = {"conditions": [condition]}
        if state == "done":
            submit_run(run.run_id, {"0": run.specs["0"]}, helper.store)  # its done.json, as the job leaves it
        yield
        assert run.jobs["0"]["state"] == state and run.jobs["0"]["node"] == node, row
        assert run.jobs["0"]["generation"] == len(order), row  # a failed Job, or one past its deadline, never made again

        # a submitter after this one, given one job more, takes up each job's newest generation, and the kind's
        # classes so far for a job not made yet
        again = submit.Run(run.run_id, {**run.specs, "other": run.specs["0"]}, kubectl, tenant)
        again.resume()
        assert {each: (record["generation"], record["submitted"] is not None) for each, record in run.jobs.items()} == {
            each: (again.jobs[each]["generation"], again.jobs[each]["submitted"] is not None) for each in run.jobs}
        assert again.jobs["0"]["generation"] == len(order) and again.allowed("other") == order, row
        assert again.jobs["other"]["submitted"] is None, row

        # its job ended: the next went on at that look, while the quota has room (the 2 made counted, the ended one's
        # card freed), then every one the quota holds room for when the run is not held to `parallel`
        assert len(kubectl.jobs) == min(PARALLEL, room) + 1, row
        submit.submit_more(run, None)
        assert len(kubectl.jobs) == min(len(run.specs), room + 1) and run.held == len(run.specs) - len(kubectl.jobs)

        # under the owner's override the run is stopped at what is left of his euros less 10%, read again each look
        # (labval-motor-20261106, 2026-11-06: EUR 2.47 left, and only the EUR 60 batch cap was checked)
        monkeypatch.setenv(submit.compute.TICKET, "override labval")
        live, deleted = [2.0], len(kubectl.deleted)
        run.live_euros = lambda: live[0]
        yield
        assert len(run.unfinished()) == len(run.specs) - 1 and caps == [], row  # EUR 2.00 fits EUR 2.25 (2.47 less 10%)
        live[0] = 2.3
        yield
        assert run.unfinished() == [] and len(kubectl.deleted) - deleted == len(run.specs) - 1, row
        assert [record["state"] for record in run.jobs.values()] == [state] + ["stopped"] * (len(run.specs) - 1), row
        assert caps == [(0, 1)], row  # its pools capped to nothing, as at the batch cap
        assert "labval" in submit.over_limits(run), row
        allowance["left"] = 100.0
        assert submit.over_limits(run) is None, row  # more left than the batch cap: the EUR 60 cap stands

    def scripted(row, script):
        """The run's look: the row's script up to its next look, then the submitter's own look; a check the script
        fails ends the run past the submitter's retries."""
        def look(run, parallel):
            looks.append(mark.exists())
            ran[:] = [run]
            try:
                if next(script, "over") == "over":
                    pytest.fail(f"{row}: a look past the row's script")
            except Exception as broke:  # noqa: BLE001 - said as the row's failure, never retried as a look's
                pytest.fail(f"{row}: {type(broke).__name__}: {broke}")
            real_look(run, parallel)
        return look

    for row, (given, pools, taints, late_classes, run_id, ends, quota, expected) in CASES.items():
        taints = list(taints_before if taints == TENANTS_OWN else taints)  # the cluster's own: none, or the tenant's
        monkeypatch.setattr(tenant, "TOLERATIONS", taints)
        clock[0] = submit.parse_time("2026-10-09T14:00:00Z")
        monkeypatch.setattr(submit.capacity, "LATE", late_classes)
        monkeypatch.delenv(submit.compute.TICKET, raising=False)
        monkeypatch.setenv(tenant.POOLS, json.dumps([{"name": f"score-{name}", "class": name, "type": "L4-1-24G",
                                                       "zone": "fr-par-2"} for name in sorted(pools)]))
        allowance["left"] = 2.47
        for each in (marks, deadlines, caps, booked, looks, ran):
            each.clear()
        kubectl = ClusterKubectl(others=22 if quota == "readable" else FORBIDDEN)  # 2 of the quota's 24 cards left
        with pytest.raises(submit.compute.Refused, match="nothing rents outside a cleared run"):
            real_prepare(kubectl, tenant)
        assert caps == [] and kubectl.jobs == {}, row  # nothing applied, no pool capped
        runner = {"command": ["true"], "code": [], "inputs": [], "outputs": [], "minutes": 30,
                  **({"attempt_limit": given["attempt_limit"]} if "attempt_limit" in given else {})}
        five = [runner] * 4 + [dict(runner, minutes=90)]  # its last job the longest
        door = dict(classes=given.get("classes"), image=given.get("image"), parallel=PARALLEL, name=run_id)
        if expected == REFUSED:
            with pytest.raises(SystemExit, match=REFUSED):
                cluster_jobs.run(given["kind"], five, "test", **door)
            assert kubectl.jobs == {}, row
            continue
        script = classes_taken(row, given, taints, ends, quota, expected)
        monkeypatch.setattr(submit, "look", scripted(row, script))
        failed = cluster_jobs.run(given["kind"], five, "test", **door)
        assert next(script, "over") == "over", row  # the script's last checks, after the run's last look
        assert failed == [number for number in range(len(five)) if number or ends != DONE], (row, failed)
        entry, = booked
        assert entry["batch"] == run_id and entry["who"] == "test", row
        assert all(looks) and not mark.exists(), row  # its node held no --jobs slot while it waited, and does again
    monkeypatch.setattr(submit.capacity, "LATE", late_before)
    monkeypatch.setattr(tenant, "TOLERATIONS", taints_before)
    monkeypatch.setenv(tenant.POOLS, pools_given)
    monkeypatch.delenv(submit.compute.TICKET, raising=False)

    cap = [float("inf")]
    monkeypatch.setattr(submit.ledger, "batch_cap", lambda: (cap[0], "the batch cap"))

    def billed(run):
        """Job 0 finished on the warm node; the cluster's class nodes as the run saw them."""
        run.jobs["0"].update(node="warm", ran=run.started + 30, state="done")
        node = {"class": "gpu-24gb", "type": "L4-1-24G", "zone": "fr-par-2", "cards": 1, "jobs": set()}
        for name, created, ready, gone, hosted in (
                ("warm", -6_000, -5_800, 600, False), ("grown", 60, 150, None, False),
                ("other-run", -1_000, -900, None, False), ("side-by-side", 60, 150, None, True)):
            run.nodes[name] = dict(node, created=run.started + created, ready=run.started + ready,
                                   deleted=gone and run.started + gone, hosted=hosted)

    # the warm runs' looks, a minute apart: the cards other runs hold of the quota's 24, the phase of each job's pod
    # (job 0's on l4-a, job 1's on l4-b), whether a warm hold's pod runs on l4-b, whether the early node's labels came,
    # and the warm holds made by then
    warm_steps = [(24, "Succeeded", None, False, False, 0),  # job 1 still to put on takes the idle node: no hold
                  (23, "Succeeded", "Running", False, False, 1),  # job 1 on, l4-b busy with it: l4-a held
                  (23, "Succeeded", "Running", False, True, 1),  # one hold an idle spell
                  (23, "Running", "Succeeded", False, True, 2),  # l4-b idle now; l4-a busy again
                  (23, "Succeeded", "Succeeded", True, True, 3)]  # a hold is no job: l4-a held again

    def warm(run, step):
        """The cluster at one of the warm runs' looks, then the run's own look at it."""
        others, first, second, hold, labelled, holds = step
        clock[0] += 60
        kubectl.others = others
        label = manifests.label_value(run.run_id)
        if first == "Succeeded" and not kubectl.jobs[manifests.job_name(run.run_id, "0", 0)].get("status"):
            submit_run(run.run_id, {"0": run.specs["0"]}, helper.store)
            kubectl.jobs[manifests.job_name(run.run_id, "0", 0)]["status"] = {
                "conditions": [{"type": "Complete", "status": "True"}]}
        pod = lambda job, node, phase, began: {  # noqa: E731
            "kind": "Pod", "metadata": {"name": f"{job}-on-{node}", "labels": {"score.dev/run": label, **job}},
            "spec": {"nodeName": node},
            "status": {"phase": phase, "containerStatuses": [{"state": {"running": {"startedAt": time_text(began)}}}]}}
        kubectl.pods = [pod({"score.dev/job": "0"}, "l4-a", first, run.started + 30)]
        kubectl.pods += [pod({"score.dev/job": "1"}, "l4-b", second, clock[0])] if second else []
        kubectl.pods += [pod({"score.dev/warm": "hold"}, "l4-b", "Running", clock[0])] if hold else []
        if labelled:
            early = next(node for node in kubectl.nodes if node["metadata"]["name"] == "early-node")
            early["metadata"]["labels"].update({submit.INSTANCE_LABEL: "l4-1-24g", submit.ZONE_LABEL: "fr-par-2"})
        real_look(run, None)
        assert len(warm_holds()) == holds, (run.run_id, step)
        assert not (hold and run.nodes["l4-b"]["busy"]), (run.run_id, step)  # a hold on it is no job

    def warm_holds():
        return [job for job in kubectl.jobs.values() if manifests.WARM_LABEL in job["metadata"]["labels"]]

    def unreachable(run):
        raise subprocess.CalledProcessError(1, ["kubectl"], stderr="kubectl get jobs,pods: connection refused")

    def capped(run):
        clock[0] += 60
        cap[0] = 0.0
        real_look(run, None)

    def turned(steps, ending):
        """The run's look: its steps, one a look, then `ending` at every look after."""
        def look(run, parallel):
            looks.append(mark.exists())  # the node holds no --jobs slot while it waits (score/graph CLUSTER_WAITERS)
            ran[:] = [run]
            if len(looks) > len(steps):
                return ending(run)
            if steps[len(looks) - 1] is None:
                submit_run(run.run_id, {"0": run.specs["0"]}, helper.store)
                return billed(run)
            try:
                return warm(run, steps[len(looks) - 1])
            except AssertionError as broke:  # said as the turn's failure, never retried as a look's
                pytest.fail(f"{run.run_id}: {broke}")
        return look

    sigterm = lambda run: os.kill(os.getpid(), signal.SIGTERM)  # noqa: E731
    before = signal.getsignal(signal.SIGTERM)
    retried = 1 + submit.POLL_RETRIES + 1
    for name, steps, ending, error, left, count, nodes in (
            ("lost-run", [None], unreachable, subprocess.CalledProcessError, "unwatched", retried, ["grown", "warm"]),
            ("stopped-direct", [None], sigterm, submit.Stopped, "stopped", 2, ["grown", "warm"]),
            ("capped-run", warm_steps, capped, None, "stopped", len(warm_steps) + 1, ["l4-a", "l4-b"]),
            ("lost-warm", warm_steps, unreachable, subprocess.CalledProcessError, "unwatched",
             len(warm_steps) + retried - 1, ["l4-a", "l4-b"])):
        out_file.unlink()
        booked.clear()
        looks.clear()
        clock[0], cap[0] = submit.parse_time("2026-11-08T20:00:00Z"), float("inf")
        kubectl = ClusterKubectl(cluster_nodes(), others=23 if steps == warm_steps else None)
        monkeypatch.setattr(submit, "look", turned(steps, ending))
        if error:
            with pytest.raises(error) as raised:
                cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"], name=name)
        else:
            assert cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"], name=name) == [1]
        run, = ran
        assert out_file.read_text() == "made by 0", name  # what finished still came back
        assert signal.getsignal(signal.SIGTERM) is before and all(looks) and not mark.exists(), name
        assert len(looks) == count, (name, looks)
        whole = ("delete", "jobs", "-n", manifests.NAMESPACE, "-l", f"score.dev/run={name}", "--ignore-not-found",
                 "--wait=false", "--cascade=background")
        assert (whole in kubectl.ran) is (ending is not capped), name
        beaten = [call for call in kubectl.ran if call[0] == "annotate"]
        assert beaten and beaten[0][:6] == ("annotate", "jobs", "-n", manifests.NAMESPACE, "-l",
                                            f"score.dev/run={name}") and beaten[0][-1].startswith(
            submit.ALIVE_NOTE + "="), name
        entry, = booked
        assert entry["batch"] == name and entry["who"] == "test" and entry["jobs"]["1"]["state"] == left, name
        assert entry["jobs"]["0"]["state"] == "done", name
        rows = {row["node"]: row for row in entry["machines"]}
        assert sorted(rows) == nodes, (name, rows)
        assert all(row.get("share", 1.0) == 1.0 for row in rows.values()), name  # a node of this run alone: whole
        made = next(job for job in kubectl.jobs.values() if job["metadata"]["name"].startswith(f"score-{name}-0"))
        assert made["metadata"]["labels"][manifests.BOX_LABEL] == "conductor", name  # this box's, for its stop
        if nodes == ["grown", "warm"]:
            assert rows["warm"]["start_wait_minutes"] == 0 and rows["warm"]["minutes"] == 10, rows["warm"]
            assert not rows["warm"]["unused"] and rows["grown"]["unused"] and rows["grown"]["end_estimated"], rows
            continue
        # the provider's record for a node the cluster lists without zone labels, its pool's machine for the node
        # just joined, no class node for the conductor's, the early node's type and zone once its labels came.
        # Break: read the label raw in `watch_nodes`. Break: drop `if seen["type"] == "?":` and its line there
        seen = run.nodes["kosmos-node"]
        assert (seen["type"], seen["zone"], seen["created"]) == ("POP2-32C-128G", "pl-waw-2", 1791554400.0), name
        assert (run.nodes[joined]["type"], run.nodes[joined]["zone"]) == ("L4-1-24G", "fr-par-2"), name
        assert "conductor-node" not in run.nodes
        assert (run.nodes["early-node"]["type"], run.nodes["early-node"]["zone"]) == ("L4-1-24G", "fr-par-2"), name
        hold = warm_holds()[0]
        pod = hold["spec"]["template"]
        assert pod["metadata"]["annotations"] == {"cluster-autoscaler.kubernetes.io/safe-to-evict": "false"}
        assert pod["spec"]["nodeSelector"] == {"kubernetes.io/hostname": "host-l4-a"}
        assert "nvidia.com/gpu" not in pod["spec"]["containers"][0]["resources"]["requests"]  # the next job's card
        assert tenant.TOLERATIONS[0] in pod["spec"]["tolerations"]
        assert hold["spec"]["activeDeadlineSeconds"] == submit.WARM_MINUTES * 60  # it ends by itself
        assert hold["metadata"]["labels"]["score.dev/run"] == name and len(hold["metadata"]["name"]) <= 63
        assert hold["metadata"]["labels"][manifests.BOX_LABEL] == "conductor"
        idle = submit.IDLE_ESTIMATE_MINUTES * 60
        if ending is capped:  # the cap's stop drops the holds: the held node goes at the autoscaler's own time
            assert [call for call in kubectl.ran if call[0] == "delete"] == [
                ("delete", "jobs", "-n", manifests.NAMESPACE, "-l", f"score.dev/run={name},score.dev/warm",
                 "--ignore-not-found", "--wait=false", "--cascade=background")], kubectl.ran
            assert run.nodes["l4-a"]["deleted"] == clock[0] + idle and run.nodes["l4-a"]["estimated"]
        else:  # a lost run's held node goes once its hold ends, booked to then
            assert run.nodes["l4-a"]["deleted"] == clock[0] + submit.WARM_MINUTES * 60 + idle
        if error is submit.Stopped:
            assert raised.value.code == 128 + signal.SIGTERM  # the stop exits 143
    assert len(uploads) == 3 and CountedCopies.copies == 1  # the later runs of the same inputs sent nothing

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

    # runs side by side on that cluster (2026-11-07: a settle run of one job booked all 23 nodes the cluster grew for
    # 20 runs' pods, EUR 2.90): each run books its part of a node, by the time its pods held it, or of an unused node
    # by the pods that waited for it; between them the runs book every node whole, never less
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
    pods = [pod("r-a", "a", "shared", 10_000.0, 10_300.0, made=9_990.0, placed=10_000.0),
            pod("r-b", "b", "shared", 10_200.0, 10_600.0, made=10_150.0, placed=10_200.0),
            pod("r-c", "c-0", made=10_900.0), pod("r-c", "c-1", made=10_900.0),  # waiting: grown-0, grown-1 for them
            pod("r-a", "a-late", made=11_100.0),  # made after both came up: grew neither
            pod("r-b", "b-vain", made=10_950.0, wants="gpu-48gb"),  # both waited for vain, which neither took
            pod("r-d", "d-vain", made=10_980.0, wants="gpu-48gb")]
    parts = {}
    for run_id, started in (("r-a", 10_000.0), ("r-b", 10_150.0), ("r-c", 10_850.0), ("r-d", 10_900.0)):
        found = submit.Run(run_id, {"ask": {"kind": "judge", "image": "image", "minutes": 5}},
                           ClusterKubectl(pods=pods), tenant)
        found.started = started
        for name, created, deleted, machine_class in (
                ("shared", 9_900.0, 10_900.0, "gpu-24gb"), ("grown-0", 10_950.0, 11_500.0, "gpu-24gb"),
                ("grown-1", 11_000.0, 11_500.0, "gpu-24gb"), ("vain", 11_000.0, 11_500.0, "gpu-48gb")):
            found.nodes[name] = {"class": machine_class, "type": "L4-1-24G", "zone": "fr-par-2", "cards": 1,
                                 "created": created, "ready": None, "deleted": deleted, "jobs": set()}
        found.note_hosts()
        parts[run_id[-1]] = {name: found.share(name, seen) for name, seen in found.nodes.items()}
    shares = [  # (run, node, its part): a alone 200 s of shared then half of 100 s, the tail b's; b's window from
        # its start, half of 100 s then all; grown-0 and grown-1 grown for c's two pods alone; two runs' pods waited
        # for vain: half each
        ("a", "shared", pytest.approx(250 / 900)), ("b", "shared", pytest.approx(650 / 750)),
        ("a", "grown-0", 0), ("a", "grown-1", 0), ("a", "vain", 0), ("c", "grown-0", 1), ("c", "grown-1", 1),
        ("b", "vain", 0.5), ("d", "vain", 0.5), ("c", "vain", 0), ("b", "grown-0", 0), ("d", "grown-1", 0)]
    for run_id, name, part in shares:
        assert parts[run_id][name] == part, (run_id, name, parts[run_id])
    assert parts["a"]["shared"] * 900 + parts["b"]["shared"] * 750 == pytest.approx(900)  # whole between them
    assert sum(parts[run_id]["vain"] for run_id in "abcd") >= 1  # never less than whole
    machine = {"type": "H100-1-80G", "zone": "fr-par-2", "cards": 1, "created": 10_000.0, "ready": 10_150.0,
               "deleted": 10_900.0, "price": 0.01, "unit_minutes": 1, "share": 0.25}
    assert submit.ledger.machine_row(machine)["euros"] == pytest.approx(15 * 0.01 * 0.25)

    # stop-batch: score's Jobs in score-jobs only, and only this box's: another box's runs share score-jobs
    # (2026-11-06: the conductor's stop ended a sim body run this PC had launched). Break: in
    # submitter.stop_score_jobs, select by RUN_LABEL alone; or drop BOX_LABEL from labels. The env1 cap's stop reaches
    # every box's (the plan of 2026-11-09 B4). Break: ignore `every_box`
    for namespace, every_box, selector in (("score-jobs", False, "score.dev/run,score.dev/box=conductor"),
                                           ("score-jobs", True, "score.dev/run"), ("score", False, None)):
        monkeypatch.setattr(manifests, "NAMESPACE", namespace)
        kubectl = ClusterKubectl(answer="job.batch \"score-r-a-g0\" deleted\n")
        if selector is None:
            with pytest.raises(SystemExit, match="score-jobs only"):
                submit.stop_score_jobs(kubectl, tenant, every_box=every_box)
            assert kubectl.ran == []
            continue
        assert submit.stop_score_jobs(kubectl, tenant, every_box=every_box) == 'job.batch "score-r-a-g0" deleted'
        assert kubectl.ran == [("delete", "jobs", "-n", "score-jobs", "-l", selector, "--ignore-not-found",
                                "--wait=false", "--cascade=background")], (every_box, kubectl.ran)

    # which work goes on the cluster at all: SCORE_CLOUD=k8s, narrowed by SCORE_CLOUD_KINDS to its kinds (#76), a
    # runner naming no kind known by its script's name, one that cannot be told kept on machines; every other kind
    # rents machines from the same backend (Scaleway's, also under SCORE_K8S_PROVIDER=scaleway/tenant)
    kinds = "pixal,blender,library,settle,characters"
    routes = [  # SCORE_CLOUD, SCORE_K8S_PROVIDER, SCORE_CLOUD_KINDS, the runner's script, the job's kind: on the cluster
        ("k8s", None, None, "pytest", None, True), ("k8s", None, None, "pytest", "judge", True),
        ("k8s", "scaleway/tenant", None, "pytest", None, True), ("scaleway", None, None, "pytest", None, False),
        ("scaleway", None, kinds, "pytest", "pixal", False), ("k8s", None, kinds, "pytest", "pixal", True),
        ("k8s", None, kinds, "pytest", "settle", True), ("k8s", None, kinds, "pytest", "judge", False),
        ("k8s", None, kinds, "/repo/tools/cloud/library_bake.py", None, True),
        ("k8s", None, kinds, "/repo/tools/cloud/judge.py", None, False), ("k8s", None, kinds, "-c", None, False)]
    for cloud, k8s_provider, narrowed, script, kind, expected in routes:
        row = (cloud, k8s_provider, narrowed, script, kind)
        for name, value in (("SCORE_CLOUD", cloud), ("SCORE_K8S_PROVIDER", k8s_provider),
                            ("SCORE_CLOUD_KINDS", narrowed)):
            monkeypatch.setenv(name, value) if value else monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(submit.sys, "argv", [script])
        assert submit.provider.on_cluster(kind) is expected, row
        assert submit.provider.load().NAME == "scaleway", row

    # a run launched with cluster kinds and resumed without them (2026-11-07, Launch 33: 10 L4s rented for its
    # cluster kinds): its pool's collector rents nothing and says why; with the settings back it rents again
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import pool
    registry = tmp_path / "runs"
    registry.mkdir()
    launch = {"pid": 11, "state": "resumed", "resumed": {"pid": 22},
              "settings": {"SCORE_CLOUD": "k8s", "SCORE_CLOUD_KINDS": "pixal,blender"}}
    (registry / "20261107T100000-11.json").write_text(json.dumps(launch))
    (registry / "20261107T110000-22.json").write_text(json.dumps({"pid": 22, "state": "running", "settings": {}}))
    (registry / "active.json").write_text("[]")
    monkeypatch.setattr(pool, "RUNS", registry)
    rented, said = [], []
    for name in ("tidy", "trim", "idle_down", "beat", "hold"):
        monkeypatch.setattr(pool, name, lambda *args: None)
    monkeypatch.setattr(pool, "shortfall", lambda plan, alive: [("gpu-24gb", 0, "card-0")])
    monkeypatch.setattr(pool, "fill", lambda run_id, plan, short, account: rented.append(short) or 1)
    monkeypatch.setattr(pool.batch, "say", said.append)
    collecting = pool.Collecting()
    collecting.account = "account"
    monkeypatch.delenv("SCORE_CLOUD_KINDS", raising=False)
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    pool.collect_round("run", {"run_pid": 22}, collecting)
    pool.collect_round("run", {"run_pid": 22}, collecting)
    assert rented == [] and len(said) == 1 and "pixal,blender" in said[0] and "SCORE_CLOUD is scaleway" in said[0]
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    pool.collect_round("run", {"run_pid": 22}, collecting)  # its launch's settings back
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    pool.collect_round("run", {"run_pid": 33}, collecting)  # another run, launched with no cluster
    assert len(rented) == 2 and collecting.refused is None
