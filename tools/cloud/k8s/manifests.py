"""The Kubernetes objects of the job path, as plain manifests (JSON that kubectl applies), from a job's spec
(`runs/<run>/<job>/job.json`, the contract in `../CLAUDE.md`): one Job a job, the object store's Secret and the
registry's pull Secret. Nothing here names a provider; a cluster on any provider that labels its nodes
`score.dev/class=<class>` and taints its card nodes `nvidia.com/gpu=present:NoSchedule` runs them.

A Job runs one pod, the image's `score-job <run> <job>`. It may only land on the classes the submitter allows it
(`score.dev/class` In [...], required), prefers them in the kind's order (preferred weights), spreads its run's pods
over zones where it can, asks for its cards as `nvidia.com/gpu`, and mounts the node's weights cache
(hostPath /var/lib/score-cache at /cache). Kubernetes retries a failed pod up to the job's attempt_limit
(backoffLimit); the runtime makes a rerun of a finished job a no-op (done.json), so a Job made again after a node
loss redoes only what was unfinished.
"""
import base64
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

import store as stores  # noqa: E402

NAMESPACE = "score"
CLASS_LABEL = "score.dev/class"
STORE_SECRET = "score-store"
REGISTRY_SECRET = "score-registry"
CACHE_HOST_PATH = "/var/lib/score-cache"
CACHE_MOUNT = "/cache"
GPU_RESOURCE = "nvidia.com/gpu"
# Minutes a pod spends before its command starts (image pull, weights from the node cache or the bucket, inputs):
# part of each attempt's deadline.
SETUP_MINUTES = 20
# Minutes a Job may wait for a node before Kubernetes ends it (activeDeadlineSeconds counts from the Job's start,
# waiting included); the submitter makes a Job that never ran again, so a long stock wait costs nothing but time.
WAIT_MINUTES = 60
# What a pod asks for besides its cards, by the kind of node: enough to place it, never a limit on what it uses. A
# processor job takes most of a 32-core node.
REQUESTS = {"gpu": {"cpu": "3", "memory": "20Gi"}, "cpu": {"cpu": "24", "memory": "96Gi"}}
# A finished Job and its pod are kept an hour for the submitter and for logs, then removed by Kubernetes.
KEEP_SECONDS = 3600
SHM_LIMIT = "16Gi"
NAME_LIMIT = 63


def name_part(text):
    """`text` as a piece of a Kubernetes name: lower case letters, digits and dashes."""
    return re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-")


def label_value(text):
    """`text` as a label value: a name piece of at most NAME_LIMIT characters."""
    return name_part(text)[:NAME_LIMIT]


def job_name(run_id, job_id, generation):
    """The Job's name for one job and generation (the submitter makes a new generation when it widens a job's
    classes); a long name keeps its end, where the job id and generation are."""
    name = f"score-{name_part(run_id)}-{name_part(job_id)}-g{generation}"
    return name if len(name) <= NAME_LIMIT else "score-" + name[-(NAME_LIMIT - 6):].lstrip("-")


def labels(run_id, job_id, kind):
    """The labels every object of a job carries, so the submitter finds them by run."""
    return {"app.kubernetes.io/part-of": "score", "score.dev/run": label_value(run_id),
            "score.dev/job": label_value(job_id), "score.dev/kind": label_value(kind)}


def deadline_seconds(spec):
    """Seconds the Job may live: each attempt's setup and minutes, and the wait for a node."""
    attempts = int(spec.get("attempt_limit", 3))
    return int((attempts * (SETUP_MINUTES + float(spec["minutes"])) + WAIT_MINUTES) * 60)


def affinity(classes):
    """Only the allowed classes, preferred in their order (the first weighs most)."""
    preferred = [{"weight": max(1, 100 - 10 * rank),
                  "preference": {"matchExpressions": [{"key": CLASS_LABEL, "operator": "In", "values": [name]}]}}
                 for rank, name in enumerate(classes)]
    required = {"nodeSelectorTerms": [{"matchExpressions": [{"key": CLASS_LABEL, "operator": "In",
                                                             "values": list(classes)}]}]}
    return {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": required,
                             "preferredDuringSchedulingIgnoredDuringExecution": preferred}}


def tolerations():
    """The taints of the job path's pools: the card taint and the processor pools' class taint."""
    return [{"key": GPU_RESOURCE, "operator": "Exists", "effect": "NoSchedule"},
            {"key": CLASS_LABEL, "operator": "Exists", "effect": "NoSchedule"}]


def resources(spec, cards):
    """What the pod asks for: its cards (none on a processor class), and the CPU and memory to place it."""
    requests = dict(REQUESTS["gpu" if cards else "cpu"])
    requests.update({key: str(spec[key]) for key in ("cpu", "memory") if spec.get(key)})
    limits = {}
    if cards:
        requests[GPU_RESOURCE] = str(cards)
        limits[GPU_RESOURCE] = str(cards)
    return {"requests": requests, "limits": limits}


def container(spec, run_id, job_id, cards):
    """The job's one container: the image's entrypoint with the run and job, the store's Secret as its environment,
    the node's name and the image for done.json, and the weights cache."""
    return {"name": "job", "image": spec["image"], "args": [run_id, job_id],
            "envFrom": [{"secretRef": {"name": STORE_SECRET}}],
            "env": [{"name": "SCORE_NODE", "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}}},
                    {"name": "SCORE_IMAGE", "value": spec["image"]}],
            "resources": resources(spec, cards),
            "volumeMounts": [{"name": "cache", "mountPath": CACHE_MOUNT}, {"name": "shm", "mountPath": "/dev/shm"}]}


def job(spec, run_id, job_id, classes, cards, generation=0):
    """The Kubernetes Job of one job spec, allowed on `classes` (in the order to prefer them), asking for `cards`."""
    tags = labels(run_id, job_id, spec["kind"])
    pod = {"restartPolicy": "Never", "affinity": affinity(classes), "tolerations": tolerations(),
           "imagePullSecrets": [{"name": REGISTRY_SECRET}],
           "topologySpreadConstraints": [{"maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone",
                                          "whenUnsatisfiable": "ScheduleAnyway",
                                          "labelSelector": {"matchLabels": {"score.dev/run": tags["score.dev/run"]}}}],
           "containers": [container(spec, run_id, job_id, cards)],
           "volumes": [{"name": "cache", "hostPath": {"path": CACHE_HOST_PATH, "type": "DirectoryOrCreate"}},
                       {"name": "shm", "emptyDir": {"medium": "Memory", "sizeLimit": SHM_LIMIT}}]}
    return {"apiVersion": "batch/v1", "kind": "Job",
            "metadata": {"name": job_name(run_id, job_id, generation), "namespace": NAMESPACE, "labels": tags,
                         "annotations": {"score.dev/classes": ",".join(classes),
                                         "score.dev/generation": str(generation),
                                         "score.dev/run-id": run_id, "score.dev/job-id": job_id}},
            "spec": {"backoffLimit": max(0, int(spec.get("attempt_limit", 3)) - 1),
                     "activeDeadlineSeconds": deadline_seconds(spec), "ttlSecondsAfterFinished": KEEP_SECONDS,
                     "template": {"metadata": {"labels": tags}, "spec": pod}}}


def namespace():
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}}


def store_secret(store):
    """The object store as the runtime's environment (the SCORE_STORE_* variables of `../runtime/store.py`), from
    the provider's object_store()."""
    data = stores.environment(store)
    return {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
            "metadata": {"name": STORE_SECRET, "namespace": NAMESPACE},
            "data": {key: base64.b64encode(value.encode()).decode() for key, value in data.items()}}


def registry_secret(registry):
    """The image pull Secret for the provider's registry(): its host with the user and password."""
    host = registry["endpoint"].split("/")[0]
    login = f"{registry['username']}:{registry['password']}"
    config = {"auths": {host: {"username": registry["username"], "password": registry["password"],
                               "auth": base64.b64encode(login.encode()).decode()}}}
    return {"apiVersion": "v1", "kind": "Secret", "type": "kubernetes.io/dockerconfigjson",
            "metadata": {"name": REGISTRY_SECRET, "namespace": NAMESPACE},
            "data": {".dockerconfigjson": base64.b64encode(json.dumps(config).encode()).decode()}}


def as_list(objects):
    """Objects as one kubectl List."""
    return {"apiVersion": "v1", "kind": "List", "items": list(objects)}
