"""Checks for pointing the GPU operator at the registry's copies of its images, with kubectl stubbed."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gpu_operator  # noqa: E402

SPEC = {"driver": {"repository": "nvcr.io/nvidia", "image": "driver", "version": "580.126.20",
                   "manager": {"repository": "nvcr.io/nvidia/cloud-native", "image": "k8s-driver-manager",
                               "version": "v0.11.0"}},
        "toolkit": {"repository": "nvcr.io/nvidia/k8s", "image": "container-toolkit", "version": "v1.19.1"},
        "devicePlugin": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
        "gfd": {"repository": "nvcr.io/nvidia", "image": "k8s-device-plugin", "version": "v0.19.3"},
        "validator": {"repository": "nvcr.io/nvidia", "image": "gpu-operator", "version": "v26.3.3"},
        "dcgmExporter": {"repository": "nvcr.io/nvidia/k8s", "image": "dcgm-exporter",
                         "version": "4.5.3-4.8.2-distroless"}}
MIRROR = "rg.example/space"


def test_images_name_the_drivers_os():
    pairs = dict(gpu_operator.images(SPEC, "ubuntu24.04"))
    assert pairs["nvcr.io/nvidia/driver:580.126.20-ubuntu24.04"] == "driver:580.126.20-ubuntu24.04"
    assert pairs["nvcr.io/nvidia/cloud-native/k8s-driver-manager:v0.11.0"] == "k8s-driver-manager:v0.11.0"
    job = gpu_operator.copy_job(list(pairs.items()), MIRROR)
    assert f"{MIRROR}/driver:580.126.20-ubuntu24.04" in job["spec"]["template"]["spec"]["containers"][0]["command"][2]


def test_the_patch_points_every_component_at_the_mirror():
    patch = gpu_operator.policy_patch(MIRROR, "score-registry")["spec"]
    assert patch["driver"]["repository"] == MIRROR and patch["driver"]["manager"]["repository"] == MIRROR
    assert patch["validator"]["imagePullSecrets"] == ["score-registry"]
    assert "imagePullSecrets" not in patch["driver"]["manager"]
    merged = {key: dict(value) for key, value in SPEC.items()}
    for key, value in patch.items():
        merged[key].update({name: item for name, item in value.items() if name != "manager"})
    merged["driver"]["manager"] = dict(SPEC["driver"]["manager"], repository=MIRROR)
    assert gpu_operator.mirrored(merged, MIRROR) and not gpu_operator.mirrored(SPEC, MIRROR)


class Policy:
    """kubectl whose cluster's ClusterPolicy already pulls from the mirror."""

    def __init__(self):
        self.calls = []

    def json(self, *arguments):
        self.calls.append(arguments)
        spec = {key: dict(value, repository=MIRROR) for key, value in SPEC.items()}
        spec["driver"]["manager"] = dict(SPEC["driver"]["manager"], repository=MIRROR)
        return {"items": [{"metadata": {"name": "cluster-policy"}, "spec": spec}]}


def test_a_mirrored_cluster_is_left_alone():
    kubectl = Policy()
    assert gpu_operator.mirror(kubectl, {"endpoint": MIRROR, "username": "u", "password": "p"})
    assert kubectl.calls == [("get", "clusterpolicies.nvidia.com")]
