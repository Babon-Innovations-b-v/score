"""The Scaleway Kubernetes cluster the job path runs on: one Kapsule cluster in the farm-factory project, a node pool
per capability class, machine type and zone, and its kubeconfig. The submitter (`../submitter.py`) only talks to the
cluster through kubectl; this module is what it asks of the provider: the pools and their prices, the cap on each
pool's size, and the nodes with their billed times.

    python3 tools/cloud/k8s/clusters/scaleway.py up        # make or update the cluster and its pools; kubeconfig
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

Measured on this cluster (2026-10-09, fr-par Kapsule `score-jobs` and a Kosmos `score-jobs-kosmos`):

- A cluster is ready in about 5 min with its system node; adding the 8 class pools takes seconds. The free control
  plane refuses pool max sizes adding up past 150 nodes (cap_pools shares that). scw cannot set a label with a dot
  in its key at pool creation (`labels.score.dev/class` reads as a nested field); `pool set-label` can.
- An L4 from zero, order to pod running: 290 to 324 s over four runs. The autoscaler acts about 40 s after the pod
  appears; the node is Ready about 100 s later; then NVIDIA's GPU operator takes about 2.7 min (node feature
  discovery, the driver image, the driver's load, the toolkit, the device plugin, each image pulled in turn). Neither
  NVIDIA's precompiled driver (595; no 580 build exists for the node's kernel) nor a shorter driver startup probe
  cut it. The operator's images mirrored into the project's registry (copied in the cluster with crane in 68 s)
  gave 146 s from node Ready to card usable and 249 s from order to pod running, on one run. A pod on a warm node
  starts in about 1 s; the 174 MB base image pulls from the private registry in 5.6 s.
- End to end through `../submitter.py`: two base-image jobs ran, their done.json read back and their ledger rows
  written, on Kapsule (a warm L4) and on Kosmos (a cold L4 in fr-par-2 after pl-waw-2 and fr-par-1 were out of
  stock: 4.1 min from submit to the pod running, EUR 0.12).
- Out of stock: an L4 in fr-par-1 came back `creation_error` ("L4-1-24G is out of stock") 5 s after its order, and
  the autoscaler ordered from the fr-par-2 pool 42 s later. With POP2-32C-128G out in both fr-par zones it kept
  ordering from each pool every one to five minutes; the Kosmos cluster's pl-waw-2 pool got one after 20 min.
- An empty node is deleted 5.5 to 6.5 min after its last pod ends (scale-down-unneeded-time 5 min).
- With the priority expander and its ConfigMap (`cluster-autoscaler-priority-expander` in kube-system), the first
  order went to the preferred pool; one sample, so the job path does not rely on it (expander random).
- Kosmos nodes carry no `topology.kubernetes.io/zone` or instance-type label (`nodes()` gives both from the pool),
  and their first pods wait about 40 s for the Kilo network.

Every cluster and pool this module touches is checked by its own record: the cluster's project_id must be the
project named PROJECT_NAME and its name CLUSTER_NAME. The organisation also holds another company's cluster in
another project; nothing here lists clusters by anything but this project and name, and nothing is ever deleted
without that check.
"""
import argparse
import datetime
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
sys.path.insert(0, str(HERE.parent))

import gpu_operator  # noqa: E402
import provider  # noqa: E402
import scaleway as backend  # noqa: E402
from kube import Kubectl  # noqa: E402
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
    """Make the cluster if missing (else keep its autoscaler settings), add its class pools, fetch its kubeconfig
    and point the GPU operator at the registry's copies of its images (gpu_operator.py); the kubeconfig's path."""
    project = backend.account()
    found = cluster(project) or create_cluster(project)
    if found.get("status") != "creating":
        scw("k8s", "cluster", "update", found["id"], *autoscaler_arguments())
    wait_ready(found["id"])
    ensure_pools(found["id"])
    config = write_kubeconfig(found["id"])
    if not gpu_operator.mirror(Kubectl(str(config)), backend.registry()):
        print("the GPU operator is not installed yet; run `up` again to point it at the registry's copies")
    return config


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
                      "type": machine_type_name(pool["node_type"]), "zone": pool["zone"],
                      "max": pool.get("max_size", 0),
                      "euros_a_minute": per_minute, "unit_minutes": unit_minutes})
    return found


def affordable_nodes(euros_left, euros_a_minute, hours, most=POOL_MAX):
    """How many nodes of a pool the month's remaining euros pay for `hours` each, at most `most`."""
    if euros_left <= 0:
        return 0
    return min(most, math.floor(euros_left / (euros_a_minute * 60 * hours)))


def node_share(pool_count):
    """The most nodes one class pool may have: Scaleway refuses pools whose max sizes add up to more than the
    control plane's node limit (150 on the free one, measured 2026-10-09), so the limit less the system pool's node
    is shared over the class pools."""
    found = owned_cluster(backend.account())
    limit = next(item["max_nodes"] for item in scw("k8s", "cluster-type", "list") if item["name"] == found["type"])
    return min(POOL_MAX, (limit - 1) // max(1, pool_count))


def cap_pools(euros_left, hours):
    """Set each class pool's max size to what the euros left pay for `hours` a node, within its share of the
    cluster's node limit; the autoscaler never grows a pool past it. Pools that shrink are set first, so the sum
    never passes the limit on the way. Returns {pool name: max}."""
    found = class_pools()
    share = node_share(len(found))
    caps = {pool["name"]: affordable_nodes(euros_left, pool["euros_a_minute"], hours, share) for pool in found}
    for pool in sorted(found, key=lambda item: caps[item["name"]] - item["max"]):
        if caps[pool["name"]] != pool["max"]:
            scw("k8s", "pool", "update", pool["id"], f"max-size={caps[pool['name']]}")
    return caps


def nodes():
    """The cluster's nodes as Scaleway bills them: name, pool, machine type, zone, status and creation time (epoch
    seconds). Kosmos nodes carry no zone or instance-type label, so the pool's record is what says them."""
    found = owned_cluster(backend.account())
    pools_by_id = {pool["id"]: pool for pool in pools(found["id"])}
    listed = []
    for node in scw("k8s", "node", "list", f"cluster-id={found['id']}") or []:
        pool = pools_by_id.get(node["pool_id"], {})
        listed.append({"name": node["name"], "pool": pool.get("name", node["pool_id"]),
                       "type": machine_type_name(pool.get("node_type", "?")), "zone": pool.get("zone", "?"),
                       "status": node["status"], "created": parse_time(node["created_at"])})
    return listed


def machine_type_name(node_type):
    """A pool's node type as the Instance type's name: Kapsule says `L4-1-24G`, Kosmos `l4_1_24g`."""
    return node_type.upper().replace("_", "-")


def price(machine_type, zone):
    """A node's price: (euros a minute, the minutes it is billed by), as the Instance of its type."""
    return backend.price(machine_type.upper(), zone)


def month_spend():
    """What Scaleway has billed the project this month, in euros."""
    return backend.month_spend(backend.account())


def parse_time(text):
    """An RFC 3339 time from the API as epoch seconds."""
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
