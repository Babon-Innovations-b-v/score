"""The Scaleway Kubernetes cluster the job path runs on: one Kapsule cluster in the farm-factory project, a node pool
per capability class, machine type and zone, and its kubeconfig. The submitter (`../submitter.py`) only talks to the
cluster through kubectl; this module is what it asks of the provider: the pools and their prices, the cap on each
pool's size, and the nodes with their billed times.

    python3 tools/cloud/k8s/clusters/scaleway.py up        # make or update the cluster and its pools, fetch its kubeconfig
    python3 tools/cloud/k8s/clusters/scaleway.py status    # the cluster, its pools and their nodes
    python3 tools/cloud/k8s/clusters/scaleway.py idle      # every class pool held at 0 nodes (max 0)
    python3 tools/cloud/k8s/clusters/scaleway.py down      # delete the whole cluster with its pools and nodes

What Scaleway offers (read from its docs and the scw CLI, 2026-10-09):

- **Kapsule** is the managed Kubernetes; its mutualized control plane is free ("provided without additional
  costs"), holds up to 150 nodes and a 55 MB etcd. Dedicated control planes (4, 8, 16 GB) cost by the hour with a
  30-day commitment, so this module never makes one. Nodes are billed as the Instances they are.
- **One region a cluster, pools in any of its zones** (multi-AZ needs the private network Kapsule makes itself). The
  cards are only in fr-par-1 (L4), fr-par-2 (L4, L40S, H100, H100-SXM) and pl-waw-2 (L4, L40S, H100), so the
  default fr-par cluster reaches fr-par-1 and fr-par-2. Kosmos (cluster type `multicloud`, also free) takes Scaleway
  pools from every region with autoscaling, over the Kilo network: SCORE_K8S_TYPE=multicloud adds pl-waw-2.
- **Pools scale from zero.** A pool with autoscaling may have min-size 0. Scaleway's cluster autoscaler (upstream
  cluster-autoscaler, cloud provider `scaleway`) builds the node of an empty pool from the Kapsule API's own record of
  the pool (its capacity, labels and taints), so a pending pod that names a class makes the right pool grow.
- **The autoscaler's options** are set on the cluster (autoscaler-config): expander (random, most_pods, least_waste,
  priority, price), scale-down-unneeded-time (default 10 min), scale-down-delay-after-add,
  scale-down-utilization-threshold, balance-similar-node-groups, ignore-daemonsets-utilization,
  skip-nodes-with-local-storage (default true), max-graceful-termination-sec, expendable-pods-priority-cutoff. The
  autoscaler runs in Scaleway's control plane, not in the cluster; other flags (max-node-provision-time, backoff)
  keep upstream's defaults.
- **A node Scaleway cannot make** (a zone out of cards) comes back as `creation_error`; the autoscaler counts that
  as a failed scale-up, backs the pool off (upstream: 5 min, doubling to 30 min) and grows another pool that fits the
  pod. That is the stock fallback inside one class; between classes the submitter widens a job's classes in the
  kind's order (`../submitter.py`).
- **GPU pools** get NVIDIA's GPU operator from Scaleway (driver, container toolkit, device plugin, through Helm) on
  every GPU node, with the resource `nvidia.com/gpu` and the label `nvidia.com/gpu.present=true`; the driver lands
  shortly after the node joins, so a pod must ask for `nvidia.com/gpu` rather than only for the node.
- **Prices** are the Instances' (product catalog, 2026-10-09, per hour): L4-1-24G €0.79, L40S-1-48G €1.47,
  H100-1-80G €2.87, H100-2-80G €5.73, H100-SXM-2-80G €6.62, POP2-32C-128G €1.18; DEV1-M (the system pool) €0.02.
- **A private registry** is pulled from with an image pull secret (kubernetes.io/dockerconfigjson) holding the
  registry's user and the runtime key's secret; the submitter makes it from `provider.registry()` at submit time.

Every cluster and pool this module touches is checked by its own record: the cluster's project_id must be the
project named PROJECT_NAME and its name CLUSTER_NAME. The organisation also holds another company's cluster in
another project; nothing here lists clusters by anything but this project and name, and nothing is ever deleted
without that check.
"""
import argparse
import json
import math
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CLOUD = HERE.parents[2] / "props" / "cloud"
# This file shares its name with the backend it uses (`backends/scaleway.py`): run as a script, its own folder
# would shadow the backend, so it leaves the import path. Other code loads it by path (`../submitter.py`'s
# cluster_module) under the name cluster_scaleway.
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(CLOUD.parent))
sys.path.insert(0, str(CLOUD))
sys.path.insert(0, str(CLOUD / "backends"))

import provider  # noqa: E402
import scaleway as backend  # noqa: E402
from paths import HOME  # noqa: E402

NAME = "scaleway"
CLUSTER_NAME = os.environ.get("SCORE_K8S_CLUSTER", "score-jobs")
REGION = os.environ.get("SCORE_K8S_REGION", "fr-par")
# kapsule: one region's zones; multicloud (Kosmos): every zone the backend rents cards in.
CLUSTER_TYPE = os.environ.get("SCORE_K8S_TYPE", "kapsule")
CNI = {"kapsule": "cilium", "multicloud": "kilo"}
TAG = "score-jobs"
# The classes the job path keeps a pool for; their machine types come from the backend's CLASSES.
POOL_CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2", "cpu-32c-128gb")
# The small always-on pool for the cluster's own pods (DNS, the GPU operator's controller): the cheapest type that
# runs them, tried in this order.
SYSTEM_POOL = "system"
SYSTEM_TYPES = ("DEV1-M", "BASIC2-A2C-4G", "PLAY2-NANO")
# The disk of a node: the images (a vLLM image is about 10 GB) and the node's weights cache (/var/lib/score-cache;
# the 20B picture model alone is 58 GB).
ROOT_GB = {"gpu": 250, "cpu": 150, "system": 20}
ROOT_VOLUME_TYPE = "sbs_5k"
# The most nodes a pool may grow to; the month's euros may cap it lower (cap_pools).
POOL_MAX = 20
CLASS_LABEL = "score.dev/class"
GPU_TAINT = ("nvidia.com/gpu", "present", "NoSchedule")
# The autoscaler's settings: empty nodes go after 5 min (Kapsule's default is 10), the node's local cache does not
# keep it alive, the GPU operator's daemon sets do not count as use, and like pools in other zones grow in turn.
AUTOSCALER = {"expander": "random", "scale-down-unneeded-time": "5m", "scale-down-delay-after-add": "5m",
              "skip-nodes-with-local-storage": "false", "ignore-daemonsets-utilization": "true",
              "balance-similar-node-groups": "true"}
KUBECONFIG = HOME / "cloud" / f"kubeconfig-{CLUSTER_NAME}.yaml"
WAIT_SECONDS = 15
# A pool or cluster change waits out the cluster's own update (a pool max change takes about a minute) this often.
BUSY_TRIES = 20


def scw(*arguments):
    """One scw call in the cluster's region, its JSON answer. A change asked while the cluster is still applying the
    last one (Scaleway: "transient state") is asked again, BUSY_TRIES times WAIT_SECONDS apart."""
    for _ in range(BUSY_TRIES):
        try:
            return backend.scw(*arguments, f"region={REGION}")
        except subprocess.CalledProcessError as error:
            if "transient state" not in (error.stderr or "") + (error.stdout or ""):
                raise
            time.sleep(WAIT_SECONDS)
    return backend.scw(*arguments, f"region={REGION}")


def zones():
    """The zones the cluster's pools may be in: the backend's card zones inside the cluster's region (Kapsule), or
    all of them (Kosmos), and for processor machines any zone of the region."""
    if CLUSTER_TYPE == "multicloud":
        return tuple(backend.ZONES)
    return tuple(zone for zone in backend.ZONES if zone.startswith(REGION + "-"))


def cluster(project):
    """The cluster record named CLUSTER_NAME in the project, or None. Each record's own project_id is checked."""
    listed = scw("k8s", "cluster", "list", f"project-id={project}", f"name={CLUSTER_NAME}") or []
    found = [item for item in listed if item["name"] == CLUSTER_NAME and item.get("project_id") == project]
    if len(found) > 1:
        raise SystemExit(f"{len(found)} clusters named {CLUSTER_NAME} in the project; resolve that by hand")
    return found[0] if found else None


def owned_cluster(project):
    """The project's cluster, failing when there is none."""
    found = cluster(project)
    if not found:
        raise SystemExit(f"no cluster named {CLUSTER_NAME} in project {backend.PROJECT_NAME}; run `up` first")
    return found


def latest_version():
    """The newest Kubernetes version the region offers."""
    versions = [item["name"] for item in scw("k8s", "version", "list")]
    return max(versions, key=lambda name: tuple(int(part) for part in name.split(".")))


def autoscaler_arguments():
    return [f"autoscaler-config.{key}={value}" for key, value in AUTOSCALER.items()]


def create_cluster(project):
    """Make the cluster with only its system pool; the class pools are added by ensure_pools."""
    system_type, system_zone = system_offer()
    return scw("k8s", "cluster", "create", f"project-id={project}", f"name={CLUSTER_NAME}", f"type={CLUSTER_TYPE}",
               f"version={latest_version()}", f"cni={CNI[CLUSTER_TYPE]}", f"tags.0={TAG}",
               "description=SCORE job path: Kubernetes Jobs on node pools per capability class",
               *autoscaler_arguments(), *system_pool_arguments(system_type, system_zone), "--wait")


def system_offer():
    """The system pool's machine type and zone: the first of SYSTEM_TYPES a zone of the cluster sells in stock."""
    region_zones = [zone for zone in zones() if zone.startswith(REGION + "-")] or [f"{REGION}-1"]
    for machine_type in SYSTEM_TYPES:
        for zone in region_zones:
            listed = {item["name"]: item.get("availability") for item in backend.scw(
                "instance", "server-type", "list", f"zone={zone}")}
            if listed.get(machine_type) in ("available", "scarce"):
                return machine_type, zone
    raise SystemExit("no small machine type in stock for the system pool")


def system_pool_arguments(machine_type, zone):
    return ["pools.0.name=" + SYSTEM_POOL, f"pools.0.node-type={machine_type}", f"pools.0.zone={zone}",
            "pools.0.size=1", "pools.0.autoscaling=false", "pools.0.autohealing=true",
            f"pools.0.root-volume-size={ROOT_GB['system']}GB", f"pools.0.tags.0={TAG}"]


def update_cluster(found):
    """Keep an existing cluster's autoscaler settings to AUTOSCALER."""
    return scw("k8s", "cluster", "update", found["id"], *autoscaler_arguments())


def pool_name(machine_class, machine_type, zone):
    """A class pool's name: the class, the machine type and the zone, all a node's labels need to say."""
    return f"{machine_class}-{machine_type}-{zone}".lower()


def wanted_pools():
    """Every class pool the cluster should have: (name, class, machine type, zone) for each type of each class's
    backend list that its zone sells."""
    wanted = []
    for zone in zones():
        sold = {item["name"] for item in backend.scw("instance", "server-type", "list", f"zone={zone}")}
        for machine_class in POOL_CLASSES:
            for machine_type in backend.CLASSES.get(machine_class, ()):
                if machine_type in sold:
                    wanted.append((pool_name(machine_class, machine_type, zone), machine_class, machine_type, zone))
    return wanted


def pools(cluster_id):
    """The cluster's pools as Scaleway records them."""
    return scw("k8s", "pool", "list", f"cluster-id={cluster_id}") or []


def pool_arguments(machine_class, machine_type, zone):
    """The scw arguments of one class pool: autoscaling from 0 to 0 (cap_pools sets the max), the GPU taint on card
    pools and a class taint on processor pools, so only score jobs land on them. The class label is set apart
    (label_pool): scw reads the dot in `labels.score.dev/class` as a nested field."""
    card = provider.cards(machine_class) > 0
    taint = GPU_TAINT if card else (CLASS_LABEL, machine_class, "NoSchedule")
    return [f"node-type={machine_type}", f"zone={zone}", "size=0", "min-size=0", "max-size=0", "autoscaling=true",
            "autohealing=true", f"root-volume-size={ROOT_GB['gpu' if card else 'cpu']}GB",
            f"root-volume-type={ROOT_VOLUME_TYPE}", f"tags.0={TAG}",
            f"taints.0.key={taint[0]}", f"taints.0.value={taint[1]}", f"taints.0.effect={taint[2]}"]


def ensure_pools(cluster_id):
    """Add every wanted class pool the cluster lacks, and label any that lost its class label; existing pools are
    otherwise left as they are."""
    have = {pool["name"]: pool for pool in pools(cluster_id)}
    for name, machine_class, machine_type, zone in wanted_pools():
        if name in have:
            if (have[name].get("labels") or {}).get(CLASS_LABEL) != machine_class:
                label_pool(have[name]["id"], machine_class)
            continue
        print(f"adding pool {name}")
        made = scw("k8s", "pool", "create", f"cluster-id={cluster_id}", f"name={name}",
                   *pool_arguments(machine_class, machine_type, zone))
        label_pool(made["id"], machine_class)


def label_pool(pool_id, machine_class):
    """Label the pool's nodes with their class; the autoscaler's node for an empty pool carries it too."""
    scw("k8s", "pool", "set-label", pool_id, f"key={CLASS_LABEL}", f"value={machine_class}")


def write_kubeconfig(cluster_id):
    """Fetch the cluster's kubeconfig to KUBECONFIG, readable by this user only."""
    done = subprocess.run(["scw", "k8s", "kubeconfig", "get", cluster_id, f"region={REGION}"], check=True,
                          capture_output=True, text=True)
    KUBECONFIG.parent.mkdir(parents=True, exist_ok=True)
    KUBECONFIG.touch(mode=0o600)
    KUBECONFIG.write_text(done.stdout)
    return KUBECONFIG


def up():
    """Make the cluster if missing (else keep its autoscaler settings), add its class pools and fetch its
    kubeconfig; the path to it."""
    project = backend.account()
    found = cluster(project) or create_cluster(project)
    if found.get("status") != "creating":
        update_cluster(found)
    wait_ready(found["id"])
    ensure_pools(found["id"])
    return write_kubeconfig(found["id"])


def wait_ready(cluster_id):
    """Wait until the cluster is ready (a new one takes minutes)."""
    while scw("k8s", "cluster", "get", cluster_id)["status"] != "ready":
        time.sleep(WAIT_SECONDS)


def class_pools():
    """The cluster's class pools: name, id, class, machine type, zone, its max size and its price."""
    found = []
    for pool in pools(owned_cluster(backend.account())["id"]):
        machine_class = (pool.get("labels") or {}).get(CLASS_LABEL)
        if not machine_class:
            continue
        per_minute, unit_minutes = price(pool["node_type"], pool["zone"])
        found.append({"name": pool["name"], "id": pool["id"], "class": machine_class,
                      "type": pool["node_type"].upper(), "zone": pool["zone"], "max": pool.get("max_size", 0),
                      "euros_a_minute": per_minute, "unit_minutes": unit_minutes})
    return found


def affordable_nodes(euros_left, euros_a_minute, hours):
    """How many nodes of a pool the month's remaining euros pay for `hours` each, at most POOL_MAX."""
    if euros_left <= 0:
        return 0
    return max(0, min(POOL_MAX, math.floor(euros_left / (euros_a_minute * 60 * hours))))


def cap_pools(euros_left, hours):
    """Set each class pool's max size to what the euros left pay for `hours` a node; the autoscaler never grows a
    pool past it. Returns {pool name: max}."""
    caps = {}
    for pool in class_pools():
        cap = affordable_nodes(euros_left, pool["euros_a_minute"], hours)
        if cap != pool["max"]:
            scw("k8s", "pool", "update", pool["id"], f"max-size={cap}")
        caps[pool["name"]] = cap
    return caps


def nodes():
    """The cluster's nodes as Scaleway bills them: name, pool, status and creation time (epoch seconds)."""
    found = owned_cluster(backend.account())
    names = {pool["id"]: pool["name"] for pool in pools(found["id"])}
    return [{"name": node["name"], "pool": names.get(node["pool_id"], node["pool_id"]), "status": node["status"],
             "created": parse_time(node["created_at"])}
            for node in scw("k8s", "node", "list", f"cluster-id={found['id']}") or []]


def price(machine_type, zone):
    """A node's price: (euros a minute, the minutes it is billed by), as the Instance of its type."""
    return backend.price(machine_type.upper(), zone)


def month_spend():
    """What Scaleway has billed the project this month, in euros."""
    return backend.month_spend(backend.account())


def parse_time(text):
    """An RFC 3339 time from the API as epoch seconds."""
    import datetime

    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def idle():
    """Hold every class pool at zero nodes: max 0, so the autoscaler removes what it has and adds none."""
    return cap_pools(0, 1)


def down():
    """Delete the cluster with its pools, nodes and the private network Kapsule made for it, after checking it is
    this project's cluster by its own record."""
    project = backend.account()
    found = cluster(project)
    if not found:
        print(f"no cluster named {CLUSTER_NAME} in the project; nothing to delete")
        return False
    if found.get("project_id") != project or found["name"] != CLUSTER_NAME:
        raise SystemExit("the cluster record is not this project's; refusing to delete it")
    scw("k8s", "cluster", "delete", found["id"], "with-additional-resources=true")
    KUBECONFIG.unlink(missing_ok=True)
    return True


def status():
    """Print the cluster, its class pools with their caps and prices, and its nodes."""
    found = cluster(backend.account())
    if not found:
        print(f"no cluster named {CLUSTER_NAME}")
        return
    print(f"{found['name']} {found['type']} {found['region']} {found['status']} k8s {found['version']}")
    for pool in class_pools():
        print(f"  {pool['name']:<48} max {pool['max']:>3}  €{pool['euros_a_minute'] * 60:.2f} an hour")
    for node in nodes():
        print(f"  node {node['name']} {node['pool']} {node['status']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("up", "status", "idle", "down", "kubeconfig"))
    command = parser.parse_args().command
    if command == "up":
        print(up())
    elif command == "kubeconfig":
        print(write_kubeconfig(owned_cluster(backend.account())["id"]))
    elif command == "idle":
        print(json.dumps(idle(), indent=1))
    elif command == "down":
        down()
    else:
        status()


if __name__ == "__main__":
    main()
