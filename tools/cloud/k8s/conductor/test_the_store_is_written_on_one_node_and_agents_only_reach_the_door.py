"""The conductor's objects keep every writer of the store on the conductor's one node at the VM's paths, and an agent
reaches only the door; the pod's units run as the VM's systemd ran them. Nothing is applied, nothing rented.

Each invariant with the break that turns it red (each applied once, seen red, reverted):

- every pod that mounts the store (the conductor's, each CronJob's) is required on the conductor's role and beside the
  conductor's pod on its host, sharing the node's process ids, and the volume is one ReadWriteOnce claim of class
  sbs-5k-retain; each pulls the private image with the registry's Secret. Break: drop `"podAffinity": ...` from
  `beside_conductor`, or `"hostPID": True` or `"imagePullSecrets"` from `pod_spec`. The scw config reaches each
  container only as the init container's copy (mode 600, user score's), never the Secret's group-readable file.
  Break: mount `scw-secret` at SCW_PATH in `mounts`. Every container, a run's drive Job's (score/conductor/cluster.py
  drive_job) too, reads the cluster's login read-only at the VM's /home/score/.kube/config, from its Secret (the
  cluster submits of 2026-11-08 found none). Break: drop the `kubeconfig` mount from `mounts`. score_lib is a fresh
  clone on each pod's /tmp, never on the store volume (owner, 2026-11-08: "dont keep score lib on the conductor disk"),
  its deploy key copied at mode 600 to the path its sshCommand names and GitHub's host keys pinned to the published
  fingerprints at the path it reads (the handover pushes of 2026-11-08: "No ED25519 host key is known for github.com").
  Break: LIBRARY under `{HOME}/projects`, drop the `known-hosts` mount from `mounts`, or change a byte of GITHUB_KEYS.
- the store's folders mount at the VM's paths (PROPS_HOME, the checkout's folder, the people routes' motion home),
  so no record's path changes. Break: `("props", f"{HOME}/props")` in MOUNTS, or drop its `motion` entry (the
  characters rows found no ~/.farm-factory-motion in the cluster, 2026-11-08).
- the agents' account may only get and port-forward to the conductor's one pod: no exec, no other pod, no other
  verb; the network policy lets nothing in; the door starts with the env file loaded (its token is read by name).
  Break: add `"pods/exec"` to the port-forward rule's resources, or drop ENV_LOADED from the door's command.
- the sync pass and the backups run one at a time (Forbid). Break: `"concurrencyPolicy": "Allow"` in `cronjob`.
- every object carries the conductor's own cost label, apart from a batch's. Break: drop COST_LABEL from `labels`.
- score's namespace gives a container that names no cpu limit 16 (a default of 1 made every drive pod of 8 cores
  invalid, 2026-11-08), and every container knows its own image (the cutover's cluster.json names it). Break:
  `"cpu": "1"` in LIMIT_DEFAULTS' default, or drop IMAGE_VARIABLE from `container`.
- a timer's commands run in order, a failed one said and the timer going on, the listener started again after it
  ends, the one-shot resume once; a stop ends what still runs. Break: `self.every == 0` -> `False` in `Unit.tick`
  (resume runs again and again).
"""
import base64
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from tools.cloud.k8s import conductor  # noqa: E402
from tools.cloud.k8s.conductor import units  # noqa: E402
from score.conductor import cluster  # noqa: E402


class FakeProcess:
    def __init__(self, command, ends_after, code):
        self.command, self.left, self.code, self.terminated = command, ends_after, code, False

    def poll(self):
        if self.terminated:
            return -15
        self.left -= 1
        return self.code if self.left < 0 else None

    def terminate(self):
        self.terminated = True

    def wait(self):
        return -15


def test_the_store_is_written_on_one_node_and_agents_only_reach_the_door():
    found = conductor.objects("registry.example/score-conductor:1@sha256:" + "0" * 64)
    by_kind = {}
    for item in found:
        by_kind.setdefault(item["kind"], []).append(item)
    claim, = by_kind["PersistentVolumeClaim"]
    assert claim["spec"]["accessModes"] == ["ReadWriteOnce"] and claim["spec"]["storageClassName"] == "sbs-5k-retain"
    pods = [by_kind["StatefulSet"][0]["spec"]["template"]["spec"]] + [
        cron["spec"]["jobTemplate"]["spec"]["template"]["spec"] for cron in by_kind["CronJob"]]
    drive = cluster.drive_job({**cluster.DEFAULTS, "image": "registry.example/score-conductor:1"}, ["score", "run"],
                              "/tmp/score-run-1.log", "/home/score/projects/score", {}, 2 ** 30)
    pods.append(drive["spec"]["template"]["spec"])
    assert len(pods) == 5
    for pod in pods:
        assert pod["hostPID"] is True  # one process-id space with the conductor: registry pids read the same
        terms = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"]
        assert terms[0]["matchExpressions"][0]["values"] == ["score-conductor"]
        assert pod["tolerations"] == [conductor.TOLERATION]
        assert pod["imagePullSecrets"] == [{"name": "score-registry"}]  # the image is private (2026-11-07 rehearsal)
        copy, clone = pod["initContainers"]
        assert f"chmod 600 {conductor.SCW_PATH}" in copy["command"][-1]
        assert f"cp /library-key/key {conductor.LIBRARY_KEY} && chmod 600 {conductor.LIBRARY_KEY}" in copy["command"][-1]
        assert f"git clone -q {conductor.LIBRARY_URL} {conductor.LIBRARY}" in clone["command"][-1]
        assert f"-i {conductor.LIBRARY_KEY} " in conductor.LIBRARY_SSH and "StrictHostKeyChecking=yes" in conductor.LIBRARY_SSH
        assert all(mount["name"] != "library-key" for box in pod["containers"] for mount in box["volumeMounts"])
        assert all(mount["name"] != "scw-secret" for box in pod["containers"] for mount in box["volumeMounts"])
        assert {volume["persistentVolumeClaim"]["claimName"] for volume in pod["volumes"]
                if "persistentVolumeClaim" in volume} == {"score-store"}
        for box in pod["containers"]:
            paths = {mount["mountPath"]: mount.get("subPath") for mount in box["volumeMounts"]}
            assert paths["/home/score/.farm-factory-props"] == "props"
            assert paths["/home/score/projects"] == "projects"
            assert paths["/home/score/.farm-factory-motion"] == "motion"
            login, = [mount for mount in box["volumeMounts"] if mount["mountPath"] == "/home/score/.kube/config"]
            assert login["readOnly"] and login["subPath"] == "config"
            secret, = [volume["secret"] for volume in pod["volumes"] if volume["name"] == login["name"]]
            assert secret["secretName"] == "score-conductor-kubeconfig"
            hosts, = [mount for mount in box["volumeMounts"] if mount["mountPath"] == conductor.KNOWN_HOSTS]
            assert hosts["readOnly"] and hosts["name"] == "known-hosts"
            names = {variable["name"]: variable.get("value") for variable in box["env"]}
            assert names["SCORE_LIB_ROOT"] == conductor.LIBRARY  # the drive Job's too: on its own /tmp
            assert paths["/tmp"] is None and conductor.LIBRARY.startswith("/tmp/")
            assert not any(conductor.LIBRARY.startswith(path) for _, path in conductor.MOUNTS)
    for cron_pod in pods[1:]:  # the CronJobs' and the drive Job's
        beside, = cron_pod["affinity"]["podAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
        assert beside["topologyKey"] == "kubernetes.io/hostname"
        assert beside["labelSelector"]["matchLabels"]["app.kubernetes.io/component"] == "conductor"
    assert all(cron["spec"]["concurrencyPolicy"] == "Forbid" for cron in by_kind["CronJob"])
    assert [cron["metadata"]["name"] for cron in by_kind["CronJob"]] == ["score-sync", "score-backup",
                                                                          "score-backup-check"]
    door_role = next(role for role in by_kind["Role"] if role["metadata"]["name"] == "score-door-agent")
    granted = {(resource, verb) for rule in door_role["rules"] for resource in rule["resources"]
               for verb in rule["verbs"]}
    assert granted == {("pods", "get"), ("pods/portforward", "get"), ("pods/portforward", "create")}
    assert all(rule["resourceNames"] == ["score-conductor-0"] for rule in door_role["rules"])
    policy, = by_kind["NetworkPolicy"]
    assert policy["spec"]["ingress"] == [] and policy["spec"]["policyTypes"] == ["Ingress"]
    assert all(item["metadata"]["labels"]["score.dev/cost"] == "conductor" for item in found)
    hosts_map, = by_kind["ConfigMap"]
    fingerprints = {line.split()[1]: base64.b64encode(hashlib.sha256(base64.b64decode(line.split()[2])).digest())
                    .decode().rstrip("=") for line in hosts_map["data"]["known_hosts"].splitlines()}
    assert fingerprints == {"ssh-ed25519": "+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU",  # docs.github.com's
                            "ecdsa-sha2-nistp256": "p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM"}
    door = next(box for box in pods[0]["containers"] if box["name"] == "door")
    assert door["ports"] == [{"name": "door", "containerPort": conductor.DOOR_PORT}]
    assert door["command"][-1].startswith(conductor.ENV_LOADED)  # its token's project comes from the env file
    limits, = by_kind["LimitRange"]  # a default cpu limit under a drive pod's 8 cores makes that pod invalid
    assert limits["metadata"]["namespace"] == "score" and limits["spec"]["limits"][0]["default"]["cpu"] == "16"
    assert all({"name": "SCORE_CONDUCTOR_IMAGE", "value": box["image"]} in box["env"]
               for pod in pods for box in pod["containers"])  # the cutover writes the pod's own image in cluster.json

    started, clock = [], [0.0]

    def popen(argv, env, cwd):
        command = argv[-1]
        started.append(command)
        failing = command == "health-a"
        return FakeProcess(command, 0 if command != "listen" else 2, 1 if failing else 0)

    rows = (("listen", None, 0, ("listen",)), ("resume", 0, 0, ("resume",)),
            ("health", 10, 10, ("health-a", "health-b")))
    ticks = iter(range(400))
    stopping = []

    def sleep(_):
        clock[0] += 1
        if next(ticks) == 60:
            stopping.append(True)

    original = units.RESTART_SECONDS
    units.RESTART_SECONDS = 3
    try:
        units.run(rows, clock=lambda: clock[0], sleep=sleep, popen=popen, stopping=stopping)
    finally:
        units.RESTART_SECONDS = original
    assert started.count("resume") == 1
    assert started.count("listen") >= 5
    health = [command for command in started if command.startswith("health")]
    assert health[:4] == ["health-a", "health-b", "health-a", "health-b"]
