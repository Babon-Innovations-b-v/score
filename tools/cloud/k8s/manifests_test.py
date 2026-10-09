"""Checks for the job path's manifests: a Job's classes, cards, taints, cache and deadline, and the two Secrets."""
import base64
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import manifests  # noqa: E402

SPEC = {"kind": "pixal", "image": "registry.example/score/score-pixal:1-abc@sha256:00", "minutes": 30,
        "attempt_limit": 3}


def test_job_allows_only_its_classes_in_order():
    job = manifests.job(SPEC, "run-1", "take_7", ["gpu-80gb", "gpu-48gb"], 1)
    pod = job["spec"]["template"]["spec"]
    required = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
    assert required["nodeSelectorTerms"][0]["matchExpressions"][0]["values"] == ["gpu-80gb", "gpu-48gb"]
    weights = [term["weight"] for term in pod["affinity"]["nodeAffinity"][
        "preferredDuringSchedulingIgnoredDuringExecution"]]
    assert weights == sorted(weights, reverse=True) and weights[0] > weights[1]
    assert {toleration["key"] for toleration in pod["tolerations"]} == {"nvidia.com/gpu", "score.dev/class"}


def test_job_asks_for_cards_and_mounts_the_cache():
    job = manifests.job(SPEC, "run-1", "take_7", ["gpu-24gb"], 1)
    container = job["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["limits"] == {"nvidia.com/gpu": "1"}
    assert container["args"] == ["run-1", "take_7"]
    assert {"name": "cache", "mountPath": "/cache"} in container["volumeMounts"]
    volume = job["spec"]["template"]["spec"]["volumes"][0]
    assert volume["hostPath"]["path"] == "/var/lib/score-cache"
    processor = manifests.job(dict(SPEC, kind="blender"), "run-1", "settle", ["cpu-32c-128gb"], 0)
    assert "nvidia.com/gpu" not in processor["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]


def test_job_retries_and_deadline():
    job = manifests.job(SPEC, "run-1", "take_7", ["gpu-24gb"], 1)
    assert job["spec"]["backoffLimit"] == 2
    assert job["spec"]["activeDeadlineSeconds"] == (3 * (manifests.SETUP_MINUTES + 30) + manifests.WAIT_MINUTES) * 60
    assert job["spec"]["template"]["spec"]["restartPolicy"] == "Never"


def test_job_names_are_kubernetes_names():
    name = manifests.job_name("Run_2026-10-09T15:00", "a" * 80, 3)
    assert len(name) <= 63 and name.endswith("-g3") and name == name.lower()
    assert manifests.job_name("r", "j", 0) != manifests.job_name("r", "j", 1)


def test_secrets_hold_the_values_by_name():
    store = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "AK", "secret_key": "SK"}
    secret = manifests.store_secret(store)
    assert base64.b64decode(secret["data"]["SCORE_STORE_SECRET_KEY"]).decode() == "SK"
    pull = manifests.registry_secret({"endpoint": "rg.example/space", "username": "nologin", "password": "PW"})
    config = json.loads(base64.b64decode(pull["data"][".dockerconfigjson"]))
    assert config["auths"]["rg.example"]["password"] == "PW"
    assert pull["type"] == "kubernetes.io/dockerconfigjson"
