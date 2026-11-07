"""The queue's warm workers: their Kubernetes Job, what the cluster's listing says of them, and the work the drives
expect.

A worker is a Job of one pod that takes job after job of its chain (image kind, image, commit) from its folder in the
job store, `queue/<box>/assign/<worker>/<seq>.json`, and says where it is in `queue/<box>/beat/<worker>.json`:
`{seq, at, job}`, `seq` the last assignment it took and `job` the one it is on, None while it waits. It never deletes
an assignment, so a restarted queue reads every one back. `{"go": true}` ends it; it also ends by itself once nothing
came for a while, and its Job's deadline bounds it if the queue dies.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import admission  # noqa: E402
import manifests  # noqa: E402

WORKER_POLL = 3  # seconds between a worker's looks at its folder
WORKER_IDLE_SECONDS = 120  # a worker with nothing of its chain queued or expected is told to go after this
WORKER_EXPECTED_SECONDS = 600  # held at most this long while the drives expect work of its image (WARM_MINUTES)
WORKER_HOURS = 6  # the worker Job's activeDeadlineSeconds, so a worker never outlives a dead queue for long
WORKER_LABEL = "score.dev/worker"
IMAGE_LABEL = "score.dev/image"
BAND_LABEL = "score.dev/band"
CODE_LABEL = "score.dev/code"
IMAGE_NOTE = "score.dev/image-ref"
NO_CODE = "none"


def store_prefix(box):
    return f"queue/{box}"


def assignment_key(box, worker, seq):
    return f"{store_prefix(box)}/assign/{worker}/{seq:08d}.json"


def beat_key(box, worker):
    return f"{store_prefix(box)}/beat/{worker}.json"


def chain_labels(chain):
    """The labels of a worker's chain: its image kind and its commit (sha12, or none for a tool image)."""
    kind, _image, code = chain
    return {IMAGE_LABEL: manifests.label_value(kind), CODE_LABEL: manifests.label_value(code[:12] or NO_CODE)}


def job_name(box, worker):
    """The worker Job's name: a long one keeps its end, where the worker id is."""
    name = f"score-w-{manifests.name_part(box)}-{manifests.name_part(worker)}"
    return name if len(name) <= manifests.NAME_LIMIT else "score-w-" + name[-(manifests.NAME_LIMIT - 8):].lstrip("-")


def requests_of(band):
    """The spec fields a worker of `band` asks with (manifests.resources' cpu and memory): a card worker today's."""
    return {} if band == admission.CARD_BAND else dict(admission.BANDS[band])


def manifest(box, worker, chain, band, classes, cards, extra_tolerations=()):
    """The Job of one worker of `chain` and `band`, allowed on `classes` (preferred in order), asking `cards`. Its
    container runs the queue's worker loop (worker.py, mounted from the queue's ConfigMap) in the chain's image."""
    kind, image, code = chain
    tags = {"app.kubernetes.io/part-of": "score", manifests.BOX_LABEL: manifests.label_value(box),
            "score.dev/run": manifests.label_value(f"queue-{box}"), WORKER_LABEL: manifests.label_value(worker),
            BAND_LABEL: manifests.label_value(band), **chain_labels(chain)}
    container = {"name": "worker", "image": image, "command": ["python3", "/score-worker/worker.py"],
                 "args": [box, worker], "envFrom": [{"secretRef": {"name": manifests.STORE_SECRET}}],
                 "env": [{"name": "SCORE_NODE", "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}}},
                         {"name": "SCORE_IMAGE", "value": image}],
                 "resources": manifests.resources(requests_of(band), cards),
                 "volumeMounts": [{"name": "cache", "mountPath": manifests.CACHE_MOUNT},
                                  {"name": "shm", "mountPath": "/dev/shm"}]}
    pod = {"restartPolicy": "Never", "affinity": manifests.affinity(classes),
           "tolerations": manifests.tolerations(extra_tolerations),
           "imagePullSecrets": [{"name": manifests.REGISTRY_SECRET}], "containers": [container],
           "volumes": [{"name": "cache", "hostPath": {"path": manifests.CACHE_HOST_PATH, "type": "DirectoryOrCreate"}},
                       {"name": "shm", "emptyDir": {"medium": "Memory", "sizeLimit": manifests.SHM_LIMIT}}]}
    return {"apiVersion": "batch/v1", "kind": "Job",
            "metadata": {"name": job_name(box, worker), "namespace": manifests.NAMESPACE, "labels": tags,
                         "annotations": {IMAGE_NOTE: image, "score.dev/kind": kind, "score.dev/code-ref": code,
                                         "score.dev/classes": ",".join(classes)}},
            "spec": {"backoffLimit": 0, "activeDeadlineSeconds": WORKER_HOURS * 3600,
                     "ttlSecondsAfterFinished": manifests.KEEP_SECONDS,
                     "template": {"metadata": {"labels": tags}, "spec": pod}}}


def listed(items):
    """The workers in one listing of the box's Jobs and pods: {worker id: {chain, band, job, pod, node, phase,
    cards}}. A worker whose Job is gone is not listed."""
    found = {}
    for item in items:
        meta = item["metadata"]
        worker = meta.get("labels", {}).get(WORKER_LABEL)
        if not worker or item.get("kind") != "Job":
            continue
        notes = meta.get("annotations", {})
        found[worker] = {"id": worker, "chain": (notes.get("score.dev/kind"), notes.get(IMAGE_NOTE),
                                                 notes.get("score.dev/code-ref", "")),
                         "band": meta["labels"].get(BAND_LABEL), "job": meta["name"], "pod": None, "node": None,
                         "phase": "Pending", "cards": cards_of(item["spec"]["template"]["spec"])}
    for item in items:
        worker = item["metadata"].get("labels", {}).get(WORKER_LABEL)
        if item.get("kind") != "Pod" or worker not in found:
            continue
        found[worker].update({"pod": item, "node": item["spec"].get("nodeName"),
                              "phase": item.get("status", {}).get("phase", "Pending")})
    return found


def cards_of(pod_spec):
    """The cards a pod asks for."""
    return sum(int(container.get("resources", {}).get("requests", {}).get(manifests.GPU_RESOURCE, 0))
               for container in pod_spec.get("containers", []))


def gone(worker):
    """Whether a listed worker's pod has ended (its Job allows no retry)."""
    return worker is None or worker["phase"] in ("Succeeded", "Failed")


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def expected(root):
    """The work the drives expect by image kind: the sum of `expected/<pid>.json` ({kind: waiting nodes}) over the
    drives still alive."""
    total = {}
    for path in sorted((pathlib.Path(root) / "expected").glob("*.json")):
        if not path.stem.isdigit() or not alive(int(path.stem)):
            continue
        try:
            counts = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue  # a drive writing its file this moment; its next pass writes it whole
        for kind, count in counts.items():
            total[kind] = total.get(kind, 0) + int(count)
    return total
