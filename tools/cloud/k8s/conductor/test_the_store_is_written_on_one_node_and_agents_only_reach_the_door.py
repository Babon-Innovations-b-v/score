"""The conductor's objects keep every writer of the store on the conductor's one node at the VM's paths, and an agent
reaches only the door; the pod's units run as the VM's systemd ran them. Nothing is applied, nothing rented.

Each invariant with the break that turns it red (each applied once, seen red, reverted):

- every pod that mounts the store (the conductor's, each CronJob's) is required on the conductor's role and beside the
  conductor's pod on its host, and the volume is one ReadWriteOnce claim of class sbs-5k-retain. Break: drop
  `"podAffinity": ...` from `beside_conductor`.
- the store's folders mount at the VM's paths (PROPS_HOME, the checkout's folder), so no record's path changes.
  Break: `("props", f"{HOME}/props")` in MOUNTS.
- the agents' account may only get and port-forward to the conductor's one pod: no exec, no other pod, no other
  verb; the network policy lets nothing in. Break: add `"pods/exec"` to the port-forward rule's resources.
- the sync pass and the backups run one at a time (Forbid). Break: `"concurrencyPolicy": "Allow"` in `cronjob`.
- every object carries the conductor's own cost label, apart from a batch's. Break: drop COST_LABEL from `labels`.
- a timer's commands run in order, a failed one said and the timer going on, the listener started again after it
  ends, the one-shot resume once; a stop ends what still runs. Break: `self.every == 0` -> `False` in `Unit.tick`
  (resume runs again and again).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from tools.cloud.k8s import conductor  # noqa: E402
from tools.cloud.k8s.conductor import units  # noqa: E402


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
    assert len(pods) == 4
    for pod in pods:
        terms = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"]
        assert terms[0]["matchExpressions"][0]["values"] == ["score-conductor"]
        assert pod["tolerations"] == [conductor.TOLERATION]
        assert {volume["persistentVolumeClaim"]["claimName"] for volume in pod["volumes"]
                if "persistentVolumeClaim" in volume} == {"score-store"}
        for box in pod["containers"]:
            paths = {mount["mountPath"]: mount.get("subPath") for mount in box["volumeMounts"]}
            assert paths["/home/score/.farm-factory-props"] == "props"
            assert paths["/home/score/projects"] == "projects"
    for cron_pod in pods[1:]:
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
    door = next(box for box in pods[0]["containers"] if box["name"] == "door")
    assert door["ports"] == [{"name": "door", "containerPort": conductor.DOOR_PORT}]

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
