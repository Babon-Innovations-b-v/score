"""The Kapsule cluster module touches only its own project's cluster, makes nothing outside a cleared run, writes a
ledger line before every order, and caps every pool at what the euros left pay for within the control plane's limit.

scw is stubbed (and the ledger is a file in the sandbox home): nothing is made. Each invariant with the break that
turns it red (each applied once and seen red):

- `down` deletes only the cluster whose own record names our project; two of one name stop the module.
  Break: drop `and item.get("project_id") == project` in `cluster`. Break: drop the `len(found) > 1` refusal.
- A tenant cluster (`tenant.py`) is never deleted, its pools never resized; only its pools tainted for score and
  labelled with a class are score's, and only their nodes. Break: `cap_pools` sets the max as scaleway's does.
  Break: drop `tainted_for_score(pool) and` in `score_pools`. A pool or node of score's labelled with no capability
  class (the conductor's own) is no job pool. Break: drop the `provider.capability_class` test in `score_pools` or `nodes`. Scaleway's `class_pools` lists no
  pool so labelled either. Break: read the label raw in `class_pools`.
  Its nodes come through kubectl, only those tainted for score. Break: drop `tainted_for_score(spec)` in `nodes`.
- Leftovers go and nothing else (plan of 2026-11-09 B4): a SCORE pool's machine that is no node an hour on, a runner
  machine past its deadline, a SCORE project's loose disk or a loose node root disk over a day; never a live node, a
  machine still joining, babon's, a claim's disk. Break: drop `server["id"] not in nodes` in `stale_nodes`. Break:
  drop the NODE_ROOT_DISK name test in `loose_disks`. The cap stop deletes every runner machine. Break: filter
  `stop_runner_servers` by deadline.
- `up` makes nothing outside a cleared run (the cluster and its system pool bill by the hour).
  Break: drop `compute.require_cleared(...)` in `up`.
- A cluster or pool order writes its `order-started` line before it is sent (review of C1, 2026-10-17).
  Break: move `ledger.order_started` after the pool create in `ensure_pools`.
- A pool's max is the nodes the euros left pay for `hours` each (none for none or less), within its share of the
  control plane's node limit; pools that shrink are set first, so the sum never passes the limit on the way.
  Break: `math.ceil` for `math.floor` in `affordable_nodes`. Break: `limit // pool_count` in `node_share`.
  Break: sort the caps the other way in `cap_pools`.
- Pools scale from zero, card pools carry the GPU taint, processor pools their class taint; Kapsule pools stay in
  the cluster's region. Break: taint processor pools with GPU_TAINT. Break: `zones` returns every backend zone.
- A change asked while the cluster applies the last one is asked again. Break: re-raise on "transient state" in `scw`.
"""
import importlib.util
import json
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cluster_scaleway", HERE / "scaleway.py")
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)
spec = importlib.util.spec_from_file_location("cluster_tenant", HERE / "tenant.py")
tenant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tenant)
backend = cluster.backend

OURS, OTHER = "ff", "bp"  # farm-factory (the batch project) and babon-platform (another company's cluster, tenant)
NOW = 1_800_000_000.0
OLD = "2026-11-01T00:00:00Z"
NEW = tenant.datetime.datetime.fromtimestamp(NOW - 60, tenant.datetime.timezone.utc).isoformat()
TAINTED = [{"key": "tenant", "value": "score", "effect": "NoSchedule"}]
L4_POOL = "gpu-24gb-l4-1-24g-fr-par-2"  # the one class pool the world's fr-par-2 sells


class Cloud:
    """One stubbed Scaleway organisation: our project and babon's, each with a cluster of one name, the tenant
    cluster's pools in babon's project, machines and disks; every call noted, the first pool update answered "busy"."""

    def __init__(self):
        self.calls, self.gone, self.busy = [], [], 1
        self.clusters = [{"id": "c-other", "name": cluster.CLUSTER_NAME, "project_id": OTHER},
                         {"id": "c-tenant", "name": "tenant-jobs", "project_id": OTHER}]
        # Kapsule pools: seven class pools (the first at max 20) and the conductor's (a class key naming no class);
        # ensure_pools adds the eighth. Tenant pools: only score-l4 is tainted for score and labelled with a class.
        self.pools = {"c-ours": [{"id": f"id{number}", "name": f"p{number}", "node_type": "L4-1-24G",
                                  "zone": "fr-par-2", "max_size": 20 if number == 0 else 0,
                                  "labels": {cluster.CLASS_LABEL: "gpu-24gb"}} for number in range(7)]
                      + [{"id": "c", "name": "score-conductor", "node_type": "POP2-HM-16C-128G", "zone": "fr-par-2",
                          "labels": {cluster.CLASS_LABEL: "conductor"}}],
                      "c-tenant": [{"id": "p1", "name": "score-l4", "node_type": "l4_1_24g", "zone": "fr-par-2",
                                    "max_size": 10, "taints": TAINTED, "labels": {"score.dev/class": "gpu-24gb"}},
                                   {"id": "p2", "name": "unlabelled", "node_type": "l4_1_24g", "zone": "fr-par-2",
                                    "taints": TAINTED},
                                   {"id": "p3", "name": "theirs", "node_type": "l4_1_24g", "zone": "fr-par-2",
                                    "labels": {"score.dev/class": "gpu-24gb"}},
                                   {"id": "p4", "name": "score-conductor", "node_type": "pop2_hm_16c_128g",
                                    "zone": "fr-par-2", "taints": TAINTED, "labels": {"score.dev/class": "conductor"}}]}
        self.sold = {"fr-par-1": ["DEV1-M"], "fr-par-2": ["L4-1-24G"]}
        self.servers = [
            {"id": "s-node", "name": "live", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": OLD},
            {"id": "s-gone", "name": "orphan", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": OLD},
            {"id": "s-new", "name": "joining", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": NEW},
            {"id": "s-babon", "name": "theirs", "project": "bp", "tags": ["pool-name=batch-l4"], "creation_date": OLD},
            {"id": "s-late", "name": "late", "project": "ff", "creation_date": OLD,
             "tags": [backend.TAG, f"deadline={NOW - 10}"]},
            {"id": "s-due", "name": "due", "project": "ff", "creation_date": OLD,
             "tags": [backend.TAG, f"deadline={NOW + 600}"]}]
        self.disks = [
            {"id": "d-root", "name": tenant.NODE_ROOT_DISK, "project_id": "bp", "references": [], "created_at": OLD},
            {"id": "d-claim", "name": "c_pvc-1", "project_id": "bp", "references": [], "created_at": OLD},
            {"id": "d-ff", "name": "x", "project_id": "ff", "references": [], "created_at": NEW},
            {"id": "d-held", "name": "y", "project_id": "ff", "references": [{"id": "s"}], "created_at": OLD}]

    def scw(self, *words):
        """scw's JSON answer to one call, as the organisation stands."""
        self.calls.append(words)
        given = dict(word.split("=", 1) for word in words if "=" in word)
        zone = given.get("zone")
        match words[:3]:
            case ("account", "project", "list"):
                return [{"id": "bp", "name": "babon-platform"}, {"id": "ff", "name": "farm-factory"}]
            case ("k8s", "cluster", "list"):  # scw's own filter is not trusted: every record comes back
                return list(self.clusters)
            case ("k8s", "cluster", "create"):
                made = {"id": "c-ours", "name": given["name"], "project_id": given["project-id"], "type": given["type"],
                        "status": "creating"}
                self.clusters.append(made)
                return made
            case ("k8s", "cluster", "delete"):
                self.clusters = [item for item in self.clusters if item["id"] != words[3]]
                return None
            case ("k8s", "cluster-type", "list"):
                return [{"name": "kapsule", "max_nodes": 152}]
            case ("k8s", "version", "list"):
                return [{"name": "1.30.4"}, {"name": "1.31.0"}]
            case ("k8s", "pool", "list"):
                return list(self.pools.get(given["cluster-id"], []))
            case ("k8s", "pool", "create"):
                made = {"id": "id7", "name": given["name"], "node_type": given["node-type"], "zone": given["zone"],
                        "max_size": int(given["max-size"])}
                self.pools[given["cluster-id"]].append(made)
                return made
            case ("k8s", "pool", "set-label"):
                pool = next(pool for pools in self.pools.values() for pool in pools if pool["id"] == words[3])
                pool["labels"] = {given["key"]: given["value"]}
                return None
            case ("k8s", "pool", "update"):
                if self.busy:
                    self.busy -= 1
                    raise subprocess.CalledProcessError(1, "scw", stderr="is in a transient state 'updating'")
                return None
            case ("instance", "server-type", "list"):
                return [{"name": name, "availability": "available"} for name in self.sold.get(zone, [])]
            case ("instance", "server", "list") if zone == "fr-par-2":
                return [server for server in self.servers
                        if "project-id" not in given or server["project"] == given["project-id"]]
            case ("block", "volume", "list") if zone == "fr-par-2":
                return self.disks
        return []


def tenant_nodes_listed():
    """kubectl's node list of the tenant cluster: score's node, one of theirs, the conductor's (no job class)."""
    items = [{"metadata": {"name": name, "creationTimestamp": OLD,
                           "labels": {"score.dev/class": "gpu-24gb", tenant.POOL_LABEL: pool}},
              "spec": {"taints": taints}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}}
             for name, pool, taints in (("n-p1", "score-l4", TAINTED), ("n-p3", "theirs", []))]
    items.append({"metadata": {"name": "n-p4", "creationTimestamp": OLD,
                               "labels": {"score.dev/class": "conductor", tenant.POOL_LABEL: "score-conductor"}},
                  "spec": {"taints": TAINTED}, "status": {"conditions": []}})
    return json.dumps({"items": items})


# Pure judging rows: what the euros left pay for (EUR 3.15 an L4 node for 4 hours), and each pool kind's arguments.
L4_A_MINUTE = 0.013125
AFFORDABLE = [(0, 0), (-5, 0), (3.14, 0), (10, 3), (1e6, cluster.POOL_MAX)]  # (euros left, nodes); 10 / 3.15 down
POOL_KINDS = [(("gpu-24gb", "L4-1-24G", "fr-par-2"),
               ("taints.0.key=nvidia.com/gpu", "min-size=0", "autoscaling=true")),
              (("cpu-32c-128gb", "POP2-32C-128G", "fr-par-1"),
               ("taints.0.key=score.dev/class", "taints.0.value=cpu-32c-128gb", "min-size=0"))]


def test_own_cluster_capped_and_ledgered(monkeypatch, tmp_path):
    for euros, nodes in AFFORDABLE:
        assert cluster.affordable_nodes(euros, L4_A_MINUTE, 4) == nodes, f"EUR {euros} left"
    for arguments, wanted in POOL_KINDS:
        made = cluster.pool_arguments(*arguments)
        assert all(word in made for word in wanted), f"{arguments[0]} pool: {made}"

    cloud = Cloud()
    import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    at_orders = []

    def scw(*words):
        if words[2:3] == ("create",):
            at_orders.append((words[:3], ledger.entries()))
        return cloud.scw(*words)
    monkeypatch.setattr(backend, "scw", scw)
    monkeypatch.setattr(backend, "account", lambda: OURS)
    monkeypatch.setattr(backend, "price", lambda machine_type, zone: (0.013, 60))
    monkeypatch.setattr(backend, "delete", lambda server_id, zone: cloud.gone.append(server_id) or True)
    monkeypatch.setattr(backend, "delete_disk", lambda disk_id, zone: cloud.gone.append(disk_id))
    monkeypatch.setattr(cluster, "KUBECONFIG", tmp_path / "kubeconfig")
    monkeypatch.setattr(cluster, "WAIT_SECONDS", 0)
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "kapsule")
    monkeypatch.setattr(cluster, "REGION", "fr-par")
    monkeypatch.delenv(cluster.compute.TICKET, raising=False)

    # Outside a cleared run nothing is made, nothing asked.
    with pytest.raises(cluster.compute.Refused, match="nothing rents outside a cleared run"):
        cluster.up()
    assert cloud.calls == []
    # Only another project's cluster of our name stands: down deletes nothing.
    assert cluster.down() is False
    assert not any(call[:3] == ("k8s", "cluster", "delete") for call in cloud.calls)

    # The cluster and its missing class pool are ordered, each after its order-started line; only the region's zones.
    cluster.create_cluster(OURS)
    cluster.ensure_pools("c-ours")
    (cluster_order, before_cluster), (pool_order, before_pool) = at_orders
    assert cluster_order == ("k8s", "cluster", "create") and pool_order == ("k8s", "pool", "create")
    assert [(line["kind"], line["name"], line["type"], line.get("zone"), line["euros"]) for line in before_pool] == [
        ("order-started", cluster.CLUSTER_NAME, "DEV1-M", "fr-par-1", 0.0),
        ("order-started", L4_POOL, "L4-1-24G", "fr-par-2", 0.0)]
    assert before_cluster == before_pool[:1]
    asked_zones = {word for call in cloud.calls for word in call if word.startswith("zone=")}
    assert asked_zones and all(word.startswith("zone=fr-par-") for word in asked_zones)
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "multicloud")
    assert set(cluster.zones()) == set(backend.ZONES)
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "kapsule")

    # Capped: the eight class pools (never the conductor's) share the 151 nodes past the system pool's, 151 // 8, the
    # one that shrinks (20 -> 18) set first; its first update, met busy, is asked again.
    assert sorted(pool["class"] for pool in cluster.class_pools()) == ["gpu-24gb"] * 8
    cloud.calls.clear()
    assert set(cluster.cap_pools(1500, 4).values()) == {18}
    updates = [call[3] for call in cloud.calls if call[:3] == ("k8s", "pool", "update")]
    assert updates[:2] == ["id0", "id0"] and len(updates) == 9 and cloud.busy == 0

    # down deletes our project's cluster only; two of our name stop the module.
    assert cluster.down() is True
    assert [call for call in cloud.calls if call[:3] == ("k8s", "cluster", "delete")] == [
        ("k8s", "cluster", "delete", "c-ours", "with-additional-resources=true", "region=fr-par")]
    cloud.clusters += [{"id": f"c{number}", "name": cluster.CLUSTER_NAME, "project_id": OURS} for number in range(2)]
    with pytest.raises(SystemExit):
        cluster.cluster(OURS)

    # The tenant cluster is its owner's: never deleted, its pools' maxes unchanged, only score's tainted and labelled
    # pool and its node score's.
    monkeypatch.setenv("SCORE_K8S_PROJECT", "babon-platform")
    monkeypatch.setenv("SCORE_K8S_CLUSTER", "tenant-jobs")
    monkeypatch.delenv(tenant.POOLS, raising=False)
    monkeypatch.setattr(tenant, "kubectl", lambda *words: tenant_nodes_listed())
    cloud.calls.clear()
    with pytest.raises(SystemExit):
        tenant.down()
    assert tenant.cap_pools(100, 4) == {"score-l4": 10} and tenant.idle() == {"score-l4": 10}
    assert [node["name"] for node in tenant.nodes()] == ["n-p1"]
    assert not any("update" in call or "delete" in call for call in cloud.calls)

    # Leftovers go (an old SCORE pool machine that is no node, a runner machine past its deadline, an old loose node
    # root disk); a live node, a joining machine, babon's, a claim's disk and a fresh disk stay. The cap's stop takes
    # every runner machine, whatever its deadline.
    done = tenant.clean_leftovers(NOW, nodes={"s-node"})
    assert cloud.gone == ["s-gone", "s-late", "d-root"] and done["disks"] == [tenant.NODE_ROOT_DISK]
    cloud.gone.clear()
    assert tenant.stop_runner_servers() == ["late", "due"] and cloud.gone == ["s-late", "s-due"]
