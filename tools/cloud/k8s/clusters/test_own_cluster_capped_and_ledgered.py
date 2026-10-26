"""The Kapsule cluster module touches only its own project's cluster, makes nothing outside a cleared run, writes a
ledger line before every order, and caps every pool at what the euros left pay for within the control plane's limit.

scw is stubbed (and the ledger is a file in the sandbox home): nothing is made. Each invariant with the break that
turns it red (each applied once and seen red):

- `down` deletes only the cluster whose own record names our project; two of one name stop the module.
  Break: drop `and item.get("project_id") == project` in `cluster`. Break: drop the `len(found) > 1` refusal.
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
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cluster_scaleway", HERE / "scaleway.py")
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)

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
