"""NVIDIA's GPU operator pulling its own images from the project's registry instead of nvcr.io: the images are
copied once into the registry (a crane Job inside the cluster, so nothing passes through this PC) and the operator's
ClusterPolicy is pointed at them. A cold card node waits for these images in turn (driver manager, driver, toolkit,
device plugin, validator); from the provider's own registry in the same region they came faster: node Ready to card
usable 146 s against about 160 s from nvcr.io (Kapsule L4, 2026-10-09, one run).

Provider-neutral: any cluster whose GPU operator is installed by the provider (Scaleway Kapsule and Kosmos) or by us
can be pointed this way; the cluster module calls `mirror(kubectl, registry)` once its first card pool exists. The
mirrored images stay in the registry (they are the project's own copies of NVIDIA's public images); a later cluster
finds them there and the copy skips what is present.

Change the ClusterPolicy only while no card node runs: a change reinstalls the driver on live nodes and their pods
fail (seen 2026-10-09).
"""
import json
import subprocess
import time

import manifests

NAMESPACE = "kube-system"
POLICY = "cluster-policy"
# The operator's components a cold node pulls, by their place in the ClusterPolicy's spec. The driver's tag carries
# the node's operating system (`<version>-ubuntu24.04`); the manager has no pull secrets of its own.
COMPONENTS = (("driver",), ("driver", "manager"), ("toolkit",), ("devicePlugin",), ("gfd",), ("validator",),
              ("dcgmExporter",))
CRANE = ("gcr.io/go-containerregistry/crane/debug:v0.22.1"
         "@sha256:e78770b31258a3846f878036d9c1f63fbe4c871f9f56990bf77fd95c013e3c1b")
MIRROR_JOB = "score-mirror-gpu-operator"
WAIT_SECONDS = 10
POLICY_MINUTES = 10
COPY_MINUTES = 15


def component(spec, path):
    """The ClusterPolicy entry at `path` (("driver", "manager") is spec.driver.manager)."""
    for key in path:
        spec = spec[key]
    return spec


def node_os(node):
    """A node's operating system as the driver's tag names it (`ubuntu24.04`), from node feature discovery's
    labels."""
    labels = node["metadata"]["labels"]
    return labels["feature.node.kubernetes.io/system-os_release.ID"] + \
        labels["feature.node.kubernetes.io/system-os_release.VERSION_ID"]


def images(spec, operating_system):
    """Each component's image as (its source, its name and tag in the mirror)."""
    found = []
    for path in COMPONENTS:
        entry = component(spec, path)
        tag = entry["version"] + (f"-{operating_system}" if path == ("driver",) else "")
        found.append((f"{entry['repository']}/{entry['image']}:{tag}", f"{entry['image']}:{tag}"))
    return found


def mirrored(spec, endpoint):
    """Whether every component already pulls from the mirror."""
    return all(component(spec, path)["repository"] == endpoint for path in COMPONENTS)


def policy_patch(endpoint, pull_secret):
    """The ClusterPolicy change that points each component at the mirror, with the pull secret where it takes one."""
    patch = {}
    for path in COMPONENTS:
        entry = patch
        for key in path:
            entry = entry.setdefault(key, {})
        entry["repository"] = endpoint
        if len(path) == 1:
            entry["imagePullSecrets"] = [pull_secret]
    return {"spec": patch}


def copy_job(pairs, endpoint):
    """A Job copying each (source, name:tag) into the registry (linux/amd64, the nodes' platform)."""
    script = "set -e\n" + "".join(f"crane copy --platform linux/amd64 {source} {endpoint}/{target}\n"
                                  for source, target in pairs)
    return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": MIRROR_JOB, "namespace": NAMESPACE},
            "spec": {"backoffLimit": 1, "ttlSecondsAfterFinished": 600, "template": {"spec": {
                "restartPolicy": "Never",
                "containers": [{"name": "crane", "image": CRANE, "command": ["sh", "-c", script],
                                "env": [{"name": "DOCKER_CONFIG", "value": "/docker"}],
                                "volumeMounts": [{"name": "docker", "mountPath": "/docker"}]}],
                "volumes": [{"name": "docker", "secret": {"secretName": manifests.REGISTRY_SECRET,
                                                          "items": [{"key": ".dockerconfigjson",
                                                                     "path": "config.json"}]}}]}}}}


def wait_for_policy(kubectl):
    """The ClusterPolicy once the operator has made it (it comes with the first card pool), or None after
    POLICY_MINUTES."""
    deadline = time.time() + POLICY_MINUTES * 60
    while time.time() < deadline:
        try:
            listed = kubectl.json("get", "clusterpolicies.nvidia.com")
        except subprocess.CalledProcessError:  # the operator's resource type is not installed yet
            listed = {}
        found = [item for item in listed.get("items", []) if item["metadata"]["name"] == POLICY]
        if found:
            return found[0]
        time.sleep(WAIT_SECONDS)
    return None


def wait_for_os(kubectl):
    """The nodes' operating system once node feature discovery has labelled a node (a minute or two after the
    operator comes); raise after POLICY_MINUTES."""
    deadline = time.time() + POLICY_MINUTES * 60
    while time.time() < deadline:
        for node in kubectl.json("get", "nodes")["items"]:
            if "feature.node.kubernetes.io/system-os_release.ID" in node["metadata"]["labels"]:
                return node_os(node)
        time.sleep(WAIT_SECONDS)
    raise RuntimeError("no node carries node feature discovery's OS labels; is the GPU operator running?")


def wait_for_job(kubectl, name):
    """Wait for a Job in kube-system to finish; raise if it failed or ran past COPY_MINUTES."""
    deadline = time.time() + COPY_MINUTES * 60
    while time.time() < deadline:
        conditions = kubectl.json("get", "job", name, "-n", NAMESPACE).get("status", {}).get("conditions") or []
        states = {condition["type"] for condition in conditions if condition["status"] == "True"}
        if "Complete" in states:
            return
        if "Failed" in states:
            raise RuntimeError(f"the Job {name} failed: kubectl -n {NAMESPACE} logs job/{name}")
        time.sleep(WAIT_SECONDS)
    raise RuntimeError(f"the Job {name} ran past {COPY_MINUTES} min")


def mirror(kubectl, registry):
    """Copy the operator's images into `registry` (the provider's registry()) and point the ClusterPolicy at them,
    once; False when the cluster has no GPU operator yet."""
    policy = wait_for_policy(kubectl)
    if policy is None:
        return False
    if mirrored(policy["spec"], registry["endpoint"]):
        return True
    secret = manifests.registry_secret(registry)
    secret["metadata"]["namespace"] = NAMESPACE
    kubectl.apply([secret])
    kubectl.run("delete", "job", MIRROR_JOB, "-n", NAMESPACE, "--ignore-not-found")
    kubectl.apply([copy_job(images(policy["spec"], wait_for_os(kubectl)), registry["endpoint"])])
    wait_for_job(kubectl, MIRROR_JOB)
    kubectl.run("patch", "clusterpolicy", POLICY, "--type", "merge", "-p",
                json.dumps(policy_patch(registry["endpoint"], manifests.REGISTRY_SECRET)))
    return True
