"""A job reaches only its kind's classes, in capacity.py's order, widened one class at a time when the cluster cannot
grow the ones it has; nothing goes on the cluster outside a cleared run; outputs come back where the runner wants
them; and every node a run made is billed to it.

kubectl, the provider and the cluster module are stubbed and the store is a folder: nothing is rented. Each
invariant with the break that turns it red (each applied once and seen red):

- The class order is capacity's (the cheapest card per job first; no H100 for a bake, even in the blender image),
  narrowed to the cluster's pools. Break: drop the capacity.NEVER filter in `class_order`.
  Break: `job_kind` returns the spec's `kind` only.
- A Job requires its allowed classes and prefers them in order, tolerates the job path's taints, asks for cards only
  on card classes, mounts the node's weights cache, retries `attempt_limit - 1` times and has a Kubernetes name.
  Break: equal weights in `affinity`. Break: `backoffLimit` = attempt_limit. Break: no `.lower()` in `name_part`.
  Break: `job_name` keeps the start of a long name.
- Widening: only after the autoscaler said "cannot grow" for the grace time, or no node came for NODE_MINUTES; a
  "cannot grow" followed by a scale-up does not count; a late class waits LATE_MINUTES; the earlier classes are kept;
  a Job that waited past its deadline with no node is made again, not failed; resuming takes up the newest
  generation. Break: drop `since_step >= NO_GROW_GRACE_MINUTES * 60` in `wants_widening`.
  Break: count every NotTriggerScaleUp in `no_grow_times`. Break: `record["state"] = "failed"` for every expired Job.
  Break: drop the `late` check in `may_widen`.
- Nothing goes on the cluster outside a cleared run (design of 2026-10-11, section 6).
  Break: drop `compute.require_cleared` in `prepare`.
- A run holds to its `parallel` jobs at once. Break: drop the `parallel` return in `submit_more`.
- Inputs go up at their paths (a folder as one key a file), outputs come back where the runner wants them, a job
  that did not finish is reported by its number. Break: report every job as failed in `cluster_jobs.run`.
- Billing: a warm node counts from the run's start; an unused node made during the run is the run's; a node made
  before it, or hosting another run, is not; a node without zone labels takes the provider's record.
  Break: `created = seen["created"]` in `node_machines`.
- The Secrets hold the store and registry values by name; the GPU operator is pointed at the registry's copies
  (the manager with no pull secret of its own) and a mirrored cluster is left alone.
  Break: give the manager `imagePullSecrets` in `policy_patch`.
"""
import base64
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cluster_jobs  # noqa: E402
import gpu_operator  # noqa: E402
import manifests  # noqa: E402
import submitter as submit  # noqa: E402

POOLS = {"gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2", "cpu-32c-128gb"}


# ==== classes and Jobs ==============================================================================================

def test_the_class_order_is_capacitys_narrowed_to_the_pools():
    order, _late = submit.class_order("pixal", {}, POOLS)
    assert order[0] == "gpu-24gb" and "gpu-24gb-x2" not in order  # the cheapest card per job first (2026-10-12)
    order, late = submit.class_order("library", {"classes": ["gpu-24gb", "gpu-48gb", "gpu-80gb"]}, POOLS)
    assert order == ["gpu-24gb", "gpu-48gb"] and late == set()  # bakes never take an H100
    assert submit.class_order("blender", {"classes": ["cpu-32c-128gb"]}, POOLS)[0] == ["cpu-32c-128gb"]
    spec = {"kind": "blender", "capacity_kind": "library", "image": "image", "minutes": 5,
            "classes": ["gpu-24gb", "gpu-48gb", "gpu-80gb"]}
    run = submit.Run("r1", {"bake": spec}, FakeKubectl([]), PoolCluster())
    assert list(run.kinds) == ["library"] and run.orders["bake"] == (["gpu-24gb", "gpu-48gb"], set())
    assert submit.job_cards({}, ["gpu-24gb", "gpu-48gb"]) == 1 and submit.job_cards({}, ["cpu-32c-128gb"]) == 0


SPEC = {"kind": "pixal", "image": "registry.example/score/score-pixal:1-abc@sha256:00", "minutes": 30,
        "attempt_limit": 3}


def test_a_job_takes_only_its_classes_preferred_in_order_with_its_cards_and_cache():
    job = manifests.job(SPEC, "run-1", "take_7", ["gpu-80gb", "gpu-48gb"], 1)
    pod = job["spec"]["template"]["spec"]
    required = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
    assert required["nodeSelectorTerms"][0]["matchExpressions"][0]["values"] == ["gpu-80gb", "gpu-48gb"]
    preferred = pod["affinity"]["nodeAffinity"]["preferredDuringSchedulingIgnoredDuringExecution"]
    weights = {term["preference"]["matchExpressions"][0]["values"][0]: term["weight"] for term in preferred}
    assert weights["gpu-80gb"] > weights["gpu-48gb"]
    assert {toleration["key"] for toleration in pod["tolerations"]} == {"nvidia.com/gpu", "score.dev/class"}
    container = pod["containers"][0]
    assert container["resources"]["limits"] == {"nvidia.com/gpu": "1"} and container["args"] == ["run-1", "take_7"]
    assert {"name": "cache", "mountPath": "/cache"} in container["volumeMounts"]
    assert pod["volumes"][0]["hostPath"]["path"] == "/var/lib/score-cache"
    assert pod["restartPolicy"] == "Never" and job["spec"]["backoffLimit"] == 2  # three attempts in all
    processor = manifests.job(dict(SPEC, kind="blender"), "run-1", "settle", ["cpu-32c-128gb"], 0)
    assert "nvidia.com/gpu" not in processor["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]

    name = manifests.job_name("Run_2026-10-09T15:00", "a" * 80, 3)
    assert len(name) <= 63 and name.endswith("-g3") and name == name.lower()  # Kubernetes' name rules
    assert manifests.job_name("r", "j", 0) != manifests.job_name("r", "j", 1)
    assert manifests.job_name("Run_A", "Take_7", 1) == "score-run-a-take-7-g1"


# ==== widening ======================================================================================================

def test_widening_waits_for_the_autoscalers_word_or_the_node_time_and_late_classes_wait():
    state = {"step": 1, "since": 1000.0, "first": 1000.0}
    assert not submit.wants_widening(state, [], 1000.0 + 3600)  # nothing waits
    assert not submit.wants_widening(state, [(1000.0, None)], 1000.0 + 60)
    grace = 1000.0 + submit.NO_GROW_GRACE_MINUTES * 60
    assert not submit.wants_widening(state, [(1000.0, 1050.0)], grace - 1)
    assert submit.wants_widening(state, [(1000.0, 1050.0)], grace)
    assert not submit.wants_widening(state, [(1000.0, 900.0)], grace)  # said before the last widening
    assert submit.wants_widening(state, [(1000.0, None)], 1000.0 + submit.NODE_MINUTES * 60)

    order, late = ["gpu-24gb", "gpu-48gb", "gpu-80gb"], {"gpu-80gb"}
    assert not submit.may_widen({"step": 2, "since": 0.0, "first": 0.0}, order, late, 60.0)
    assert submit.may_widen({"step": 2, "since": 0.0, "first": 0.0}, order, late,
                            submit.capacity.LATE_MINUTES * 60.0)
    assert not submit.may_widen({"step": 3, "since": 0.0, "first": 0.0}, order, late, 1e9)  # none left


def test_the_autoscalers_cannot_grow_counts_only_when_no_scale_up_followed():
    """Right after a pool's cap changes the autoscaler says "max node group size reached" for a moment and then grows
    it (2026-10-09)."""
    events = [{"reason": "NotTriggerScaleUp", "involvedObject": {"name": "pod-a"},
               "lastTimestamp": "2026-10-09T14:00:00Z",
               "message": "pod didn't trigger scale-up: 1 in backoff after failed scale-up"},
              {"reason": "NotTriggerScaleUp", "involvedObject": {"name": "pod-d"},
               "lastTimestamp": "2026-10-09T14:00:00Z", "message": "pod didn't trigger scale-up: 1 node(s) had taint"},
              {"reason": "TriggeredScaleUp", "involvedObject": {"name": "pod-b"},
               "lastTimestamp": "2026-10-09T14:00:00Z", "message": "pod triggered scale-up"},
              {"reason": "NotTriggerScaleUp", "involvedObject": {"name": "pod-c"},
               "lastTimestamp": "2026-10-09T14:20:39Z",
               "message": "pod didn't trigger scale-up: 8 max node group size reached"},
              {"reason": "TriggeredScaleUp", "involvedObject": {"name": "pod-c"},
               "lastTimestamp": "2026-10-09T14:20:59Z", "message": "pod triggered scale-up"}]
    assert submit.no_grow_times(events) == {"pod-a": 1791554400.0}  # 2026-10-09T14:00:00Z
    assert submit.job_outcome({"status": {"conditions": [{"type": "Complete", "status": "True"}]}}) == "done"
    assert submit.job_outcome({"status": {"conditions": [
        {"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}}) == "expired"
    assert submit.job_outcome({"status": {"conditions": [{"type": "Failed", "status": "True"}]}}) == "failed"
    assert submit.job_outcome({"status": {}}) is None


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


def time_text(seconds):
    return submit.datetime.datetime.fromtimestamp(seconds, submit.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_a_run_widens_one_class_at_a_time_remakes_an_expired_wait_and_takes_stock_that_comes_back(monkeypatch):
    clock = [submit.parse_time("2026-10-09T14:00:00Z")]
    monkeypatch.setattr(submit.time, "time", lambda: clock[0])
    kubectl = LiveKubectl()
    spec = {"kind": "meshparts", "image": "image", "minutes": 10}
    run = submit.Run("r1", {"part": spec}, kubectl, PoolCluster())
    order, _late = submit.class_order("meshparts", spec, POOLS)
    assert order == ["gpu-24gb", "gpu-48gb", "gpu-80gb"]
    run.make("part")
    assert run.allowed("part") == ["gpu-24gb"]

    def poll_with_no_stock(minutes):
        name = manifests.job_name("r1", "part", run.jobs["part"]["generation"])
        stamp = time_text(clock[0])
        kubectl.pods = [{"kind": "Pod", "metadata": {"name": f"{name}-pod", "labels": {"score.dev/job": "part"}},
                         "spec": {}, "status": {"conditions": [{"type": "PodScheduled", "status": "False",
                                                                "lastTransitionTime": stamp}]}}]
        clock[0] += minutes * 60
        kubectl.events = [{"reason": "NotTriggerScaleUp", "involvedObject": {"name": f"{name}-pod"},
                           "lastTimestamp": stamp,
                           "message": "pod didn't trigger scale-up: 1 in backoff after failed scale-up"}]
        jobs, pods, no_grow = run.read()
        run.update_job("part", run.current("part", jobs), pods.get("part", []))
        run.widen(pods, no_grow)

    poll_with_no_stock(2)
    assert run.allowed("part") == ["gpu-24gb", "gpu-48gb"] and run.jobs["part"]["generation"] == 1
    poll_with_no_stock(2)
    assert run.allowed("part") == order and run.jobs["part"]["generation"] == 2
    poll_with_no_stock(2)
    assert run.allowed("part") == order and run.jobs["part"]["generation"] == 2  # nothing left to add

    current = kubectl.jobs[manifests.job_name("r1", "part", 2)]
    current["status"] = {"conditions": [{"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}
    jobs, _pods, _no_grow = run.read()
    run.update_job("part", run.current("part", jobs), [])
    assert run.jobs["part"]["state"] == "waiting" and run.jobs["part"]["generation"] == 3
    remade = kubectl.jobs[manifests.job_name("r1", "part", 3)]
    assert remade["metadata"]["annotations"]["score.dev/classes"] == ",".join(order)  # the earlier classes kept

    kubectl.pods = [{"kind": "Pod", "metadata": {"name": "p", "labels": {"score.dev/job": "part"}},
                     "spec": {"nodeName": "node-80gb"},
                     "status": {"containerStatuses": [{"state": {"running": {"startedAt": time_text(clock[0])}}}]}}]
    remade["status"] = {"conditions": [{"type": "Complete", "status": "True"}]}
    jobs, pods, _no_grow = run.read()
    run.update_job("part", run.current("part", jobs), pods["part"])
    assert run.jobs["part"]["state"] == "done" and run.jobs["part"]["node"] == "node-80gb"


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


def test_nothing_goes_on_the_cluster_outside_a_cleared_run(monkeypatch):
    monkeypatch.delenv(submit.compute.TICKET, raising=False)
    cluster = FakeCluster()
    kubectl = FakeKubectl([])
    with pytest.raises(submit.compute.Refused, match="nothing rents outside a cleared run"):
        submit.prepare(kubectl, cluster)
    assert cluster.caps == [] and kubectl.applied == []


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


def test_inputs_go_up_at_their_paths_and_outputs_come_back_where_the_runner_wants_them(tmp_path, monkeypatch):
    helper = Helper(tmp_path / "store")
    monkeypatch.setattr(cluster_jobs.submitter, "runtime", lambda: helper)
    seen = {}

    def submit_run(run, specs, store, wait_scale_down=True, who=None, parallel=None):
        """What the cluster would leave: each output and done.json, except job 1, which fails."""
        seen.update(specs=specs, wait=wait_scale_down, who=who)
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
    out_file, out_folder = tmp_path / "out" / "result.json", tmp_path / "out" / "folder"
    jobs = [{"command": ["true"], "code": ["tools/cloud/k8s"], "inputs": [str(stage), str(single)],
             "outputs": [str(out_file), str(out_folder)], "minutes": 3, "kernel_cache": "blender-5.0.1"},
            {"command": ["false"], "code": ["tools/cloud/k8s"], "inputs": [], "outputs": [], "minutes": 3}]
    assert cluster_jobs.run("blender", jobs, who="test", classes=["gpu-24gb"]) == [1]
    assert seen["wait"] is False and seen["who"] == "test"
    spec = seen["specs"]["0"]
    assert spec["image"].startswith("registry.example/score-blender") and spec["classes"] == ["gpu-24gb"]
    assert spec["kernel_cache"] == "blender-5.0.1" and spec["minutes"] == 3
    assert sorted(entry["path"] for entry in spec["inputs"]) == sorted(
        [str(stage / "place.usda"), str(stage / "textures/wall.png"), str(single)])
    assert out_file.read_text() == "made by 0" and (out_folder / "part" / "a.txt").read_text() == "made by 0"


# ==== billing =======================================================================================================

class PricedCluster(PoolCluster):
    def price(self, machine_type, zone):
        return 0.013125, 1


def test_a_runs_nodes_are_billed_from_its_start_and_only_its_own(monkeypatch):
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


def test_a_node_without_zone_labels_takes_the_providers_record():
    class NodeKubectl(FakeKubectl):
        def json(self, *arguments):
            return {"items": self.items if arguments[1] == "nodes" else []}

    class BilledCluster(PoolCluster):
        def nodes(self):
            return [{"name": "kosmos-node", "type": "POP2-32C-128G", "zone": "pl-waw-2", "created": 100.0}]
    node = {"metadata": {"name": "kosmos-node", "creationTimestamp": "2026-10-09T14:50:00Z",
                         "labels": {"score.dev/class": "cpu-32c-128gb"}},
            "status": {"conditions": [{"type": "Ready", "status": "True",
                                       "lastTransitionTime": "2026-10-09T14:50:13Z"}]}}
    run = submit.Run("r1", {}, NodeKubectl([node]), BilledCluster())
    run.watch_nodes()
    seen = run.nodes["kosmos-node"]
    assert (seen["type"], seen["zone"], seen["created"]) == ("POP2-32C-128G", "pl-waw-2", 100.0)


def test_score_cloud_k8s_keeps_the_providers_backend(monkeypatch):
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    monkeypatch.delenv("SCORE_K8S_PROVIDER", raising=False)
    assert submit.provider.on_cluster() and submit.provider.load().NAME == "scaleway"
    monkeypatch.setenv("SCORE_CLOUD", "scaleway")
    assert not submit.provider.on_cluster() and submit.provider.load().NAME == "scaleway"


# ==== secrets and the GPU operator ==================================================================================

def test_the_secrets_hold_the_values_by_name():
    store = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "AK", "secret_key": "SK"}
    assert base64.b64decode(manifests.store_secret(store)["data"]["SCORE_STORE_SECRET_KEY"]).decode() == "SK"
    pull = manifests.registry_secret({"endpoint": "rg.example/space", "username": "nologin", "password": "PW"})
    assert json.loads(base64.b64decode(pull["data"][".dockerconfigjson"]))["auths"]["rg.example"]["password"] == "PW"
    assert pull["type"] == "kubernetes.io/dockerconfigjson"


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


def test_the_gpu_operator_is_pointed_at_the_mirror_and_a_mirrored_cluster_is_left_alone():
    pairs = dict(gpu_operator.images(OPERATOR, "ubuntu24.04"))
    assert pairs["nvcr.io/nvidia/driver:580.126.20-ubuntu24.04"] == "driver:580.126.20-ubuntu24.04"
    assert pairs["nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.11.0"] == "k8s-driver-manager:v0.11.0"
    job = gpu_operator.copy_job(list(pairs.items()), MIRROR)
    assert f"{MIRROR}/driver:580.126.20-ubuntu24.04" in job["spec"]["template"]["spec"]["containers"][0]["command"][2]

    patch = gpu_operator.policy_patch(MIRROR, "score-registry")["spec"]
    assert patch["driver"]["repository"] == MIRROR and patch["driver"]["manager"]["repository"] == MIRROR
    assert patch["validator"]["imagePullSecrets"] == ["score-registry"]
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
    assert gpu_operator.mirror(kubectl, {"endpoint": MIRROR, "username": "u", "password": "p"})
    assert kubectl.calls == [("get", "clusterpolicies.nvidia.com")]  # nothing changed on a live cluster
