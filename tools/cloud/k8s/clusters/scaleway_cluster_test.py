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
