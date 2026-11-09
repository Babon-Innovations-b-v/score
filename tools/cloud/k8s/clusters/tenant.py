"""A Kapsule cluster someone else runs, where score is a tenant: score's own namespace and node pools in it, given
to score, never made, resized or deleted from here. Picked with SCORE_K8S_PROVIDER=scaleway/tenant (the backend
before the slash still gives the registry, the store, prices and secrets; this module is the cluster).

    python3 tools/cloud/k8s/clusters/tenant.py status    # the cluster, score's class pools and their nodes

What the tenant cluster gives score (its owner sets it up and keeps it; nothing here changes it):

- **A namespace for the jobs** with a card quota (SCORE_K8S_NAMESPACE, default `score-jobs`), where the submitter
  puts its two Secrets and its Jobs. The namespace exists; the submitter does not make it (NAMESPACE_GIVEN).
- **Class pools** labelled `score.dev/class=<class>` (the pool's labels, set by the cluster's owner), tainted
  `tenant=score:NoSchedule` (TENANT_TAINT, tolerated by every Job: TOLERATIONS) and, card pools, the GPU operator's
  `nvidia.com/gpu` taint; they scale from zero with the cluster's autoscaler, whose own settings (scale-down after
  its own minutes) stand. A pool without the class label is not one of score's classes.
- **Its own maxes.** A pool's max size and the namespace's card quota are the owner's; `cap_pools` and `idle` change
  nothing and say the maxes as they stand. The batch cap still holds: the submitter adds up the live cost of the
  run's nodes every poll and stops the run's Jobs at the cap (`../submitter.py` over_limits).
- **A kubeconfig on this box** (SCORE_K8S_KUBECONFIG, else ~/.kube/config) with the cluster's context named by
  SCORE_K8S_CONTEXT, so a box holding several clusters' contexts never reaches the wrong one.
- **Pools and nodes without scw where the box cannot read the cluster's project** (the conductor's key reaches only
  its own; 2026-11-06): `SCORE_K8S_POOLS`, the class pools as JSON [{name, class, type, zone, max}] in the box's
  settings, stands for the scw list of pools; the nodes are always read through kubectl (the scoped login reads
  nodes), so a node's billed start is its own creation time.
- **No GPU operator change, no `up` or `down`**: the cluster's ClusterPolicy is its owner's (gpu_operator.py is never
  run against it), `up` only checks the context and the namespace, `down` refuses.

The cluster is found by its own name (SCORE_K8S_CLUSTER) in the Scaleway project named SCORE_K8S_PROJECT, its record's
project id checked; its pools and nodes are read by the cluster's id, never organisation-wide. No name or id is in
the repository: they come from the box's environment.
"""
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CLOUD = HERE.parents[1]
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(CLOUD))
sys.path.insert(0, str(CLOUD / "backends"))
sys.path.insert(0, str(HERE.parent))

import provider  # noqa: E402
import scaleway as backend  # noqa: E402

NAME = "tenant"
REGION = os.environ.get("SCORE_K8S_REGION", "fr-par")
CLASS_LABEL = "score.dev/class"
NAMESPACE = os.environ.get("SCORE_K8S_NAMESPACE", "score-jobs")
NAMESPACE_GIVEN = True
KUBECONFIG = pathlib.Path(os.environ.get("SCORE_K8S_KUBECONFIG") or pathlib.Path.home() / ".kube" / "config")
TENANT_TAINT = ("tenant", "score", "NoSchedule")
TOLERATIONS = [{"key": TENANT_TAINT[0], "operator": "Equal", "value": TENANT_TAINT[1], "effect": TENANT_TAINT[2]}]


def setting(name):
    """A box setting the module cannot run without, from the environment."""
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set: the tenant cluster's {name.split('_')[-1].lower()} comes from this box's "
                         "environment, never from the repository")
    return value


def context():
    """The kubeconfig context of the tenant cluster (SCORE_K8S_CONTEXT)."""
    return setting("SCORE_K8S_CONTEXT")


def scw(*arguments):
    return backend.scw(*arguments, f"region={REGION}")


def project():
    """The id of the Scaleway project named SCORE_K8S_PROJECT, the cluster's own."""
    name = setting("SCORE_K8S_PROJECT")
    found = [item for item in backend.scw("account", "project", "list", f"name={name}") or [] if item["name"] == name]
    if len(found) != 1:
        raise SystemExit(f"expected one Scaleway project named {name}, found {len(found)}")
    return found[0]["id"]


def cluster():
    """The cluster record named SCORE_K8S_CLUSTER in that project, its own project id checked."""
    name, owner = setting("SCORE_K8S_CLUSTER"), project()
    listed = scw("k8s", "cluster", "list", f"project-id={owner}", f"name={name}") or []
    found = [item for item in listed if item["name"] == name and item.get("project_id") == owner]
    if len(found) != 1:
        raise SystemExit(f"expected one cluster named {name} in its project, found {len(found)}")
    return found[0]


def tainted_for_score(pool):
    """Whether the pool carries the tenant taint: one of score's pools, whatever else it is."""
    key, value, effect = TENANT_TAINT
    return any((taint.get("key"), taint.get("value"), taint.get("effect")) == (key, value, effect)
               for taint in pool.get("taints") or [])


def score_pools(pools):
    """The pools that are score's job classes: tainted for score and labelled with a capability class."""
    return [pool for pool in pools if tainted_for_score(pool) and provider.capability_class((pool.get("labels") or {}).get(CLASS_LABEL))]


def pools(cluster_id):
    return scw("k8s", "pool", "list", f"cluster-id={cluster_id}") or []


def machine_type_name(node_type):
    """A pool's node type as the Instance type's name (`l4_1_24g` is `L4-1-24G`)."""
    return node_type.upper().replace("_", "-")


def price(machine_type, zone):
    """A node's price: (euros a minute, the minutes it is billed by), as the Instance of its type."""
    return backend.price(machine_type.upper(), zone)


POOLS = "SCORE_K8S_POOLS"  # the class pools as the box's settings give them (JSON), in place of scw's list
POOL_LABEL = "k8s.scaleway.com/pool-name"
INSTANCE_LABEL = "node.kubernetes.io/instance-type"
ZONE_LABEL = "topology.kubernetes.io/zone"


def given_pools():
    """The class pools SCORE_K8S_POOLS gives ([{name, class, type, zone, max}]), or None when it is not set."""
    text = os.environ.get(POOLS)
    return None if not text else json.loads(text)


def class_pools():
    """Score's class pools: name, id, class, machine type, zone, the max its owner set and its price; from
    SCORE_K8S_POOLS when it is set, else read with scw in the cluster's project."""
    given = given_pools()
    if given is not None:
        found = []
        for pool in given:
            per_minute, unit_minutes = price(pool["type"], pool["zone"])
            found.append({"name": pool["name"], "id": pool["name"], "class": pool["class"], "type": pool["type"],
                          "zone": pool["zone"], "max": pool.get("max", 0), "euros_a_minute": per_minute,
                          "unit_minutes": unit_minutes})
        return found
    found = []
    for pool in score_pools(pools(cluster()["id"])):
        per_minute, unit_minutes = price(machine_type_name(pool["node_type"]), pool["zone"])
        found.append({"name": pool["name"], "id": pool["id"], "class": pool["labels"][CLASS_LABEL],
                      "type": machine_type_name(pool["node_type"]), "zone": pool["zone"],
                      "max": pool.get("max_size", 0), "euros_a_minute": per_minute, "unit_minutes": unit_minutes})
    return found


def cap_pools(euros_left, hours):
    """Nothing is changed: a tenant pool's max is its owner's. {pool name: its max as it stands}."""
    return {pool["name"]: pool["max"] for pool in class_pools()}


def idle():
    """Nothing is changed: the autoscaler removes score's empty nodes by its own settings."""
    return cap_pools(0, 1)


def parse_time(text):
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def nodes():
    """The nodes of score's job pools (labelled with a capability class, tainted for score): name, pool, machine type, zone, status
    (ready, else not_ready) and creation time, read through kubectl (the scoped login reads nodes; no scw read of
    the cluster's project)."""
    listed, pools = [], []
    for node in json.loads(kubectl("get", "nodes", "-l", CLASS_LABEL, "-o", "json"))["items"]:
        meta, spec = node["metadata"], node.get("spec") or {}
        labels = meta.get("labels") or {}
        if not tainted_for_score(spec) or not provider.capability_class(labels.get(CLASS_LABEL)):
            continue
        if not (labels.get(POOL_LABEL) and labels.get(INSTANCE_LABEL) and labels.get(ZONE_LABEL)):
            pools = pools or class_pools()
            labels = {**pool_labels(meta["name"], labels, pools), **labels}
        ready = any(condition["type"] == "Ready" and condition["status"] == "True"
                    for condition in (node.get("status") or {}).get("conditions", []))
        listed.append({"name": meta["name"], "pool": labels.get(POOL_LABEL, "?"),
                       "type": labels.get(INSTANCE_LABEL, "?").upper(), "zone": labels.get(ZONE_LABEL, "?"),
                       "status": "ready" if ready else "not_ready", "created": parse_time(meta["creationTimestamp"])})
    return listed


def pool_labels(name, labels, pools):
    """The pool, machine type and zone labels of a node that has joined before its cloud labels are set (seen
    2026-11-07: a new L40S node priced "? in ?" for two minutes, every poll of the run failing meanwhile), from its
    pool: the pool label, else the pool named in the node's name (scw-<cluster>-<pool>-<id>); none when neither."""
    named = labels.get(POOL_LABEL) or next((pool["name"] for pool in pools if f"-{pool['name']}-" in name), None)
    pool = next((pool for pool in pools if pool["name"] == named), None)
    if pool is None:
        return {}
    return {POOL_LABEL: pool["name"], INSTANCE_LABEL: pool["type"], ZONE_LABEL: pool["zone"]}


def kubectl(*arguments):
    done = subprocess.run(["kubectl", "--kubeconfig", str(KUBECONFIG), "--context", context(), *arguments],
                          check=True, capture_output=True, text=True)
    return done.stdout


# The env1 cap's stop and its leftover cleanup (the plan of 2026-11-09 B4, K4, K13): what a stop or a watch pass
# deletes across the organisation's projects, with the delete rights the owner gave the conductor's key (Instances and
# Block Storage in babon-platform, 2026-11-09). Never a babon machine, never a disk that holds data.
NODE_GRACE_SECONDS = 3600  # a pool's new machine joins as a node in minutes; one not a node an hour on is left over
LOOSE_DISK_SECONDS = 86400  # a disk attached to nothing this long is left over
NODE_ROOT_DISK = "k8s_base_node_instance_sbs_volume_0"  # Kapsule's name for a node's root disk: never data


def project_names():
    """{project id: name} of every project the key reads."""
    return {project["id"]: project["name"] for project in backend.scw("account", "project", "list") or []}


def runner_servers():
    """Every machine the runner rented (its tag, backend.TAG) in the batch project, in every zone the organisation may
    hold one (not only the zones it rents in): (id, zone, name, tags), each machine's own project checked."""
    project, found = backend.account(), []
    for zone in backend.ALL_ZONES:
        found += [(server["id"], zone, server["name"], server.get("tags") or [])
                  for server in backend.scw("instance", "server", "list", f"project-id={project}", f"zone={zone}",
                                            f"tags.0={backend.TAG}") or []
                  if backend.TAG in (server.get("tags") or []) and server.get("project") == project]
    return found


def stop_runner_servers():
    """The cap stop's machines: every runner-tagged machine of the batch project deleted with its disk and address,
    whatever run or box rented it; the names deleted."""
    return [name for server_id, zone, name, _tags in runner_servers() if backend.delete(server_id, zone)]


def deadline_of(tags):
    """A runner machine's `deadline=` tag (seconds), or None."""
    return next((float(tag.split("=", 1)[1]) for tag in tags if tag.startswith("deadline=")), None)


def stale_nodes(servers, names, nodes, now):
    """The machines of SCORE's cluster pools (backend.owner_of: a pool-name tag of SCORE's) that are no cluster's node
    and were made over NODE_GRACE_SECONDS ago: (id, zone, name, why)."""
    return [(server["id"], zone, server["name"], "a SCORE pool's machine that is no node")
            for server, zone in servers
            if any(tag.startswith(backend.POOL_TAG) for tag in server.get("tags") or [])
            and backend.owner_of(server, names) == "score" and server["id"] not in nodes
            and now - backend.created_at(server) > NODE_GRACE_SECONDS]


def past_deadline(servers, project, now):
    """The batch project's runner machines past their deadline tag: (id, zone, name, why)."""
    return [(server["id"], zone, server["name"], "past its deadline")
            for server, zone in servers
            if server.get("project") == project and backend.TAG in (server.get("tags") or [])
            and (deadline_of(server.get("tags") or []) or now) < now]


def loose_disks(names, now):
    """The disks attached to nothing for over LOOSE_DISK_SECONDS: any of a SCORE project's, and a node's root disk
    (NODE_ROOT_DISK) of the shared project; never another disk there (a volume claim's holds data): (id, zone, name)."""
    found = []
    for zone in backend.ALL_ZONES:
        for disk in backend.scw("block", "volume", "list", f"zone={zone}") or []:
            project = names.get(disk.get("project_id"))
            ours = project in backend.SCORE_PROJECTS or (project == backend.SHARED_PROJECT
                                                         and disk.get("name") == NODE_ROOT_DISK)
            if ours and not disk.get("references") and now - backend.created_at(disk) > LOOSE_DISK_SECONDS:
                found.append((disk["id"], zone, disk.get("name")))
    return found


def clean_leftovers(now=None, nodes=None):
    """Delete what SCORE left standing (every cap stop and every watch pass): its pools' machines that are no node,
    the runner's machines past their deadline, and loose disks over a day old; {"machines": [(name, why)], "disks":
    [name]}. Nothing is deleted while the clusters' nodes cannot be read (backend.node_ids raises)."""
    now = time.time() if now is None else now
    names, project = project_names(), backend.account()
    nodes = backend.node_ids() if nodes is None else set(nodes)
    servers = [(server, zone) for zone in backend.ALL_ZONES
               for server in backend.scw("instance", "server", "list", f"zone={zone}") or []]
    done = {"machines": [], "disks": []}
    for server_id, zone, name, why in stale_nodes(servers, names, nodes, now) + past_deadline(servers, project, now):
        if backend.delete(server_id, zone):
            done["machines"].append((name, why))
    for disk_id, zone, name in loose_disks(names, now):
        backend.delete_disk(disk_id, zone)
        done["disks"].append(name)
    return done


def up():
    """Check the context reaches the cluster and the jobs' namespace is there; nothing is made. The kubeconfig."""
    kubectl("get", "namespace", NAMESPACE, "-o", "name")
    return KUBECONFIG


def down():
    raise SystemExit("the tenant cluster is its owner's: score never deletes it")


def status():
    if given_pools() is None:
        found = cluster()
        print(f"{found['name']} {found['region']} {found['status']} k8s {found['version']}; jobs in {NAMESPACE}")
    else:
        print(f"{context()} through kubectl, pools as given; jobs in {NAMESPACE}")
    for pool in class_pools():
        print(f"  {pool['name']:<24} {pool['class']:<16} max {pool['max']:>3}  €{pool['euros_a_minute'] * 60:.2f} an hour")
    for node in nodes():
        print(f"  node {node['name']} {node['pool']} {node['status']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("status", "up"))
    if parser.parse_args().command == "up":
        print(up())
    else:
        status()


if __name__ == "__main__":
    main()
