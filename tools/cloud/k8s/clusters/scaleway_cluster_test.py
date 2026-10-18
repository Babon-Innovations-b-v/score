"""Checks for the Kapsule cluster module with scw stubbed: its pools' labels and taints, the caps from the month's
euros, and that it deletes only its own project's cluster."""
import importlib.util
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cluster_scaleway", HERE / "scaleway.py")
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)

OURS = "11111111-0000-0000-0000-000000000000"
OTHER = "22222222-0000-0000-0000-000000000000"


def test_pools_carry_the_taint_and_scale_from_zero():
    card = cluster.pool_arguments("gpu-24gb", "L4-1-24G", "fr-par-2")
    assert "taints.0.key=nvidia.com/gpu" in card and "min-size=0" in card and "autoscaling=true" in card
    processor = cluster.pool_arguments("cpu-32c-128gb", "POP2-32C-128G", "fr-par-1")
    assert "taints.0.key=score.dev/class" in processor and "taints.0.value=cpu-32c-128gb" in processor


def test_caps_follow_the_euros_left():
    l4 = 0.013125
    assert cluster.affordable_nodes(0, l4, 4) == 0
    assert cluster.affordable_nodes(-5, l4, 4) == 0
    assert cluster.affordable_nodes(10, l4, 4) == 3
    assert cluster.affordable_nodes(1e6, l4, 4) == cluster.POOL_MAX


def test_zones_stay_in_the_region(monkeypatch):
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "kapsule")
    monkeypatch.setattr(cluster, "REGION", "fr-par")
    assert all(zone.startswith("fr-par-") for zone in cluster.zones())
    monkeypatch.setattr(cluster, "CLUSTER_TYPE", "multicloud")
    assert set(cluster.zones()) == set(cluster.backend.ZONES)


def fake_scw(listed, calls):
    def scw(*arguments):
        calls.append(arguments)
        if arguments[:3] == ("k8s", "cluster", "list"):
            return listed
        return None
    return scw


def test_down_deletes_only_this_projects_cluster(monkeypatch, tmp_path):
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
    assert ("k8s", "cluster", "delete", "c-ours", "with-additional-resources=true") in calls


def test_up_makes_nothing_outside_a_cleared_run(monkeypatch):
    """Fault (design of 2026-10-11, section 6): `up` made the Kapsule cluster and its system pool, billed by the
    hour, for any caller, outside the runner's gate and the owner's yes."""
    calls = []
    monkeypatch.delenv(cluster.compute.TICKET, raising=False)
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    monkeypatch.setattr(cluster, "scw", fake_scw([], calls))
    with pytest.raises(cluster.compute.Refused, match="nothing rents outside a cleared run"):
        cluster.up()
    assert calls == []


def test_two_clusters_of_one_name_stop(monkeypatch):
    twins = [{"id": f"c{number}", "name": cluster.CLUSTER_NAME, "project_id": OURS} for number in range(2)]
    monkeypatch.setattr(cluster, "scw", fake_scw(twins, []))
    with pytest.raises(SystemExit):
        cluster.cluster(OURS)


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


def test_caps_fit_the_control_planes_node_limit(monkeypatch):
    pools = [{"name": f"p{number}", "id": f"id{number}", "max": 20 if number == 0 else 0, "euros_a_minute": 0.013}
             for number in range(8)]
    calls = []

    def scw(*arguments):
        calls.append(arguments)
        if arguments[:3] == ("k8s", "cluster-type", "list"):
            return [{"name": "kapsule", "max_nodes": 150}]
        return None
    monkeypatch.setattr(cluster, "scw", scw)
    monkeypatch.setattr(cluster, "class_pools", lambda: pools)
    monkeypatch.setattr(cluster, "owned_cluster", lambda project: {"type": "kapsule"})
    monkeypatch.setattr(cluster.backend, "account", lambda: OURS)
    caps = cluster.cap_pools(1500, 4)
    assert set(caps.values()) == {18} and sum(caps.values()) <= 149
    updates = [call[3] for call in calls if call[:3] == ("k8s", "pool", "update")]
    assert updates[0] == "id0"


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


def test_a_cluster_order_writes_its_started_line_first(monkeypatch, tmp_path):
    """Fault (review of C1, 2026-10-17): the cluster set-up ordered its cluster (an always-on system pool, billed by
    the hour) and its class pools with no ledger line, while the lint listed it as a ledgered client."""
    seen = ledger_at_each_order(monkeypatch, tmp_path, lambda arguments: {"id": "made", "status": "creating"})
    monkeypatch.setattr(cluster, "system_offer", lambda: ("DEV1-M", "fr-par-1"))
    monkeypatch.setattr(cluster, "latest_version", lambda: "1.31.0")
    cluster.create_cluster(OURS)
    [(order, [line])] = seen
    assert order == ("k8s", "cluster", "create")
    assert line["kind"] == "order-started" and line["name"] == cluster.CLUSTER_NAME and line["type"] == "DEV1-M"
    assert line["euros"] == 0.0


def test_a_pool_order_writes_its_started_line_first(monkeypatch, tmp_path):
    seen = ledger_at_each_order(monkeypatch, tmp_path,
                                lambda arguments: [] if arguments[:3] == ("k8s", "pool", "list") else {"id": "p1"})
    monkeypatch.setattr(cluster, "wanted_pools", lambda: [("gpu-24gb-l4-1-24g-fr-par-2", "gpu-24gb", "L4-1-24G",
                                                           "fr-par-2")])
    cluster.ensure_pools("c1")
    [(order, [line])] = seen
    assert order == ("k8s", "pool", "create")
    assert line["kind"] == "order-started" and line["name"] == "gpu-24gb-l4-1-24g-fr-par-2"
    assert line["type"] == "L4-1-24G" and line["zone"] == "fr-par-2"
