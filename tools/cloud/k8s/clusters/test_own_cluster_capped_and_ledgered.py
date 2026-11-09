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
- A change asked while the cluster applies the last one is asked again. Break: re-raise on "transient state".
"""
import importlib.util
import json
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cluster_scaleway", HERE / "scaleway.py")
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)
spec = importlib.util.spec_from_file_location("cluster_tenant", HERE / "tenant.py")
tenant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tenant)

OURS = "11111111-0000-0000-0000-000000000000"
OTHER = "22222222-0000-0000-0000-000000000000"


def fake_scw(listed, calls):
    def scw(*arguments):
        calls.append(arguments)
        if arguments[:3] == ("k8s", "cluster", "list"):
            return listed
        return None
    return scw


def test_down_deletes_only_this_projects_cluster_and_two_of_one_name_stop(monkeypatch, tmp_path):
    calls = []
    other = {"id": "c-other", "name": cluster.CLUSTER_NAME, "project_id": OTHER}
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    monkeypatch.setattr(cluster, "KUBECONFIG", tmp_path / "kubeconfig")
    monkeypatch.setattr(cluster, "scw", fake_scw([other], calls))
    assert cluster.down() is False
    assert not any(call[:3] == ("k8s", "cluster", "delete") for call in calls)
    ours = {"id": "c-ours", "name": cluster.CLUSTER_NAME, "project_id": OURS}
    monkeypatch.setattr(cluster, "scw", fake_scw([other, ours], calls))
    assert cluster.down() is True
    assert [call for call in calls if call[:3] == ("k8s", "cluster", "delete")] == [
        ("k8s", "cluster", "delete", "c-ours", "with-additional-resources=true")]

    # A tenant cluster is its owner's: never deleted, its pools' maxes never changed, only its tainted and labelled
    # pools score's, its nodes only theirs.
    with pytest.raises(SystemExit):
        tenant.down()
    tainted = [{"key": "tenant", "value": "score", "effect": "NoSchedule"}]
    pools = [{"id": "p1", "name": "score-l4", "node_type": "l4_1_24g", "zone": "fr-par-2", "max_size": 10,
              "taints": tainted, "labels": {"score.dev/class": "gpu-24gb"}},
             {"id": "p2", "name": "unlabelled", "node_type": "l4_1_24g", "zone": "fr-par-2", "taints": tainted},
             {"id": "p3", "name": "theirs", "node_type": "l4_1_24g", "zone": "fr-par-2",
              "labels": {"score.dev/class": "gpu-24gb"}},
             {"id": "p4", "name": "score-conductor", "node_type": "pop2_hm_16c_128g", "zone": "fr-par-2",
              "taints": tainted, "labels": {"score.dev/class": "conductor"}}]
    asked = []

    def tenant_scw(*arguments):
        asked.append(arguments)
        if arguments[:3] == ("k8s", "pool", "list"):
            return pools
        if arguments[:3] == ("k8s", "node", "list"):
            return [{"name": f"n-{pool['id']}", "pool_id": pool["id"], "status": "ready",
                     "created_at": "2026-11-05T10:00:00Z"} for pool in pools]
        return None
    monkeypatch.setattr(tenant, "scw", tenant_scw)
    monkeypatch.setattr(tenant, "cluster", lambda: {"id": "c-tenant"})
    monkeypatch.setattr(tenant, "price", lambda machine_type, zone: (0.0135, 1))
    assert tenant.cap_pools(100, 4) == {"score-l4": 10} and tenant.idle() == {"score-l4": 10}
    # its nodes through kubectl (2026-11-06: the conductor's scw cannot read the cluster's project), only the ones
    # tainted for score. Break: in tenant.nodes, drop the `tainted_for_score(spec)` filter
    listed = {"items": [{"metadata": {"name": name, "creationTimestamp": "2026-11-05T10:00:00Z",
                                      "labels": {"score.dev/class": "gpu-24gb", tenant.POOL_LABEL: pool}},
                         "spec": {"taints": taints}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}}
                        for name, pool, taints in (("n-p1", "score-l4", tainted), ("n-p3", "theirs", []))]}
    listed["items"].append({"metadata": {"name": "n-p4", "creationTimestamp": "2026-11-05T10:00:00Z",
                                         "labels": {"score.dev/class": "conductor", tenant.POOL_LABEL: "score-conductor"}},
                            "spec": {"taints": tainted}, "status": {"conditions": []}})
    monkeypatch.setattr(tenant, "kubectl", lambda *words: json.dumps(listed))
    assert [node["name"] for node in tenant.nodes()] == ["n-p1"]
    assert not any("update" in call or "delete" in call for call in asked)

    # leftovers (plan B4): a SCORE pool's machine that is no node an hour on, a runner machine past its deadline and a
    # loose disk over a day go; a live node, a new machine, babon's machine, a claim's disk and a fresh disk stay
    now = 1_800_000_000.0
    old, new = "2026-11-01T00:00:00Z", tenant.datetime.datetime.fromtimestamp(now - 60, tenant.datetime.timezone.utc
                                                                               ).isoformat()
    servers = [{"id": "s-node", "name": "live", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": old},
               {"id": "s-gone", "name": "orphan", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": old},
               {"id": "s-new", "name": "joining", "project": "bp", "tags": ["pool-name=score-l4-1-z2"], "creation_date": new},
               {"id": "s-babon", "name": "theirs", "project": "bp", "tags": ["pool-name=batch-l4"], "creation_date": old},
               {"id": "s-late", "name": "late", "project": "ff", "creation_date": old,
                "tags": [tenant.backend.TAG, f"deadline={now - 10}"]},
               {"id": "s-due", "name": "due", "project": "ff", "creation_date": old,
                "tags": [tenant.backend.TAG, f"deadline={now + 600}"]}]
    disks = [{"id": "d-root", "name": tenant.NODE_ROOT_DISK, "project_id": "bp", "references": [], "created_at": old},
             {"id": "d-claim", "name": "c_pvc-1", "project_id": "bp", "references": [], "created_at": old},
             {"id": "d-ff", "name": "x", "project_id": "ff", "references": [], "created_at": new},
             {"id": "d-held", "name": "y", "project_id": "ff", "references": [{"id": "s"}], "created_at": old}]
    gone = []

    def cloud_scw(*words):
        if words[:3] == ("account", "project", "list"):
            return [{"id": "bp", "name": "babon-platform"}, {"id": "ff", "name": "farm-factory"}]
        zone = next(word for word in words if word.startswith("zone="))
        if zone != "zone=fr-par-2":
            return []
        if words[:3] == ("instance", "server", "list"):
            return [server for server in servers if "project-id=ff" not in words or server["project"] == "ff"]
        return disks if words[:3] == ("block", "volume", "list") else []
    monkeypatch.setattr(tenant.backend, "scw", cloud_scw)
    monkeypatch.setattr(tenant.backend, "account", lambda: "ff")
    monkeypatch.setattr(tenant.backend, "delete", lambda server_id, zone: gone.append(server_id) or True)
    monkeypatch.setattr(tenant.backend, "delete_disk", lambda disk_id, zone: gone.append(disk_id))
    done = tenant.clean_leftovers(now, nodes={"s-node"})
    assert gone == ["s-gone", "s-late", "d-root"] and done["disks"] == [tenant.NODE_ROOT_DISK]
    # the cap's stop: every runner machine of the batch project, whatever its deadline
    gone.clear()
    assert tenant.stop_runner_servers() == ["late", "due"] and gone == ["s-late", "s-due"]

    twins = [{"id": f"c{number}", "name": cluster.CLUSTER_NAME, "project_id": OURS} for number in range(2)]
    monkeypatch.setattr(cluster, "scw", fake_scw(twins, []))
    with pytest.raises(SystemExit):
        cluster.cluster(OURS)


def test_up_makes_nothing_outside_a_cleared_run(monkeypatch):
    calls = []
    monkeypatch.delenv(cluster.compute.TICKET, raising=False)
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    monkeypatch.setattr(cluster, "scw", fake_scw([], calls))
    with pytest.raises(cluster.compute.Refused, match="nothing rents outside a cleared run"):
        cluster.up()
    assert calls == []


def ledger_at_each_order(monkeypatch, tmp_path, answers):
    """A stubbed scw that notes, for each cluster or pool create, the ledger's lines when the order went; the notes."""
    import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    seen = []

    def scw(*arguments):
        if arguments[2] == "create":
            seen.append((arguments[:3], ledger.entries()))
        return answers(arguments)
    monkeypatch.setattr(cluster, "scw", scw)
    return seen


def test_a_cluster_or_pool_order_writes_its_started_line_first(monkeypatch, tmp_path):
    seen = ledger_at_each_order(monkeypatch, tmp_path, lambda arguments: {"id": "made", "status": "creating"})
    monkeypatch.setattr(cluster, "system_offer", lambda: ("DEV1-M", "fr-par-1"))
    monkeypatch.setattr(cluster, "latest_version", lambda: "1.31.0")
    cluster.create_cluster(OURS)
    [(order, [line])] = seen
    assert order == ("k8s", "cluster", "create")
    assert (line["kind"], line["name"], line["type"], line["euros"]) == (
        "order-started", cluster.CLUSTER_NAME, "DEV1-M", 0.0)

    seen = ledger_at_each_order(monkeypatch, tmp_path / "pools",
                                lambda arguments: [] if arguments[:3] == ("k8s", "pool", "list") else {"id": "p1"})
    monkeypatch.setattr(cluster, "wanted_pools", lambda: [("gpu-24gb-l4-1-24g-fr-par-2", "gpu-24gb", "L4-1-24G",
                                                           "fr-par-2")])
    cluster.ensure_pools("c1")
    [(order, [line])] = seen
    assert order == ("k8s", "pool", "create")
    assert (line["kind"], line["name"], line["type"], line["zone"]) == (
        "order-started", "gpu-24gb-l4-1-24g-fr-par-2", "L4-1-24G", "fr-par-2")


def test_a_pools_cap_is_what_the_euros_left_pay_for_within_the_node_limit(monkeypatch):
    l4 = 0.013125  # euros a minute: EUR 3.15 for 4 hours
    assert cluster.affordable_nodes(0, l4, 4) == 0
    assert cluster.affordable_nodes(-5, l4, 4) == 0
    assert cluster.affordable_nodes(3.14, l4, 4) == 0
    assert cluster.affordable_nodes(10, l4, 4) == 3  # 10 / 3.15, rounded down
    assert cluster.affordable_nodes(1e6, l4, 4) == cluster.POOL_MAX

    class_pools = cluster.class_pools
    pools = [{"name": f"p{number}", "id": f"id{number}", "max": 20 if number == 0 else 0, "euros_a_minute": 0.013}
             for number in range(8)]
    calls = []

    def scw(*arguments):
        calls.append(arguments)
        if arguments[:3] == ("k8s", "cluster-type", "list"):
            return [{"name": "kapsule", "max_nodes": 152}]
        return None
    monkeypatch.setattr(cluster, "scw", scw)
    monkeypatch.setattr(cluster, "class_pools", lambda: pools)
    monkeypatch.setattr(cluster, "owned_cluster", lambda project: {"type": "kapsule"})
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    caps = cluster.cap_pools(1500, 4)
    assert set(caps.values()) == {18}  # (152 nodes less the system pool's one) // 8 pools: 151 // 8
    updates = [call[3] for call in calls if call[:3] == ("k8s", "pool", "update")]
    assert updates[0] == "id0"  # the one that shrinks, 20 -> 18, first
    # A pool whose class key names no capability class (the conductor's) is no class pool.
    listed = [{"name": "score-l4", "id": "l4", "node_type": "L4-1-24G", "zone": "fr-par-2",
               "labels": {"score.dev/class": "gpu-24gb"}},
              {"name": "score-conductor", "id": "c", "node_type": "POP2-HM-16C-128G", "zone": "fr-par-2",
               "labels": {"score.dev/class": "conductor"}}]
    monkeypatch.setattr(cluster, "pools", lambda cluster_id: listed)
    monkeypatch.setattr(cluster, "owned_cluster", lambda project: {"id": "k"})
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    monkeypatch.setattr(cluster, "price", lambda machine_type, zone: (0.013, 60))
    assert [pool["class"] for pool in class_pools()] == ["gpu-24gb"]


def test_pools_scale_from_zero_tainted_by_kind_in_the_clusters_region(monkeypatch):
    card = cluster.pool_arguments("gpu-24gb", "L4-1-24G", "fr-par-2")
    assert "taints.0.key=nvidia.com/gpu" in card and "min-size=0" in card and "autoscaling=true" in card
    processor = cluster.pool_arguments("cpu-32c-128gb", "POP2-32C-128G", "fr-par-1")
    assert "taints.0.key=score.dev/class" in processor and "taints.0.value=cpu-32c-128gb" in processor
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "kapsule")
    monkeypatch.setattr(cluster, "REGION", "fr-par")
    assert cluster.zones() and all(zone.startswith("fr-par-") for zone in cluster.zones())
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "multicloud")
    assert set(cluster.zones()) == set(cluster.backend.ZONES)


def test_a_busy_cluster_is_asked_again(monkeypatch):
    answers = [cluster.subprocess.CalledProcessError(1, "scw", stderr="is in a transient state 'updating'"), {"ok": 1}]

    def scw(*arguments):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer
    monkeypatch.setattr(cluster.backend, "scw", scw)
    monkeypatch.setattr(cluster, "WAIT_SECONDS", 0)
    assert cluster.scw("k8s", "pool", "update", "p", "max-size=1") == {"ok": 1}
