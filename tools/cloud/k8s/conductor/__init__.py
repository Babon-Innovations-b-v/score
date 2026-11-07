"""The conductor in the cluster (#76, the plan of 2026-11-07, step 1): its objects as plain manifests (JSON for
kubectl), rendered here and checked with `kubectl apply --dry-run=server`; nothing here applies them.

    python -m tools.cloud.k8s.conductor render --image <ref>    # the objects as one List on stdout
    python -m tools.cloud.k8s.conductor check --image <ref>     # the same through kubectl's server-side dry run

The shape (namespace `score` in babon's cluster, zone fr-par-2, beside the card pools):

- **The store's volume** (`score-store`): one block volume claim, ReadWriteOnce, class `sbs-5k-retain` (the owner's
  pick, 2026-11-07), `VOLUME_SIZE` (the VM's 229 GB data disk, 109 GB used, plus room). Its subfolders are mounted at
  the paths they have on the VM (`MOUNTS`): the home `/home/score/.farm-factory-props` (PROPS_HOME: no path in any
  record changes), the checkout's folder `/home/score/projects` (a run's frozen copy is a git worktree of it, so a
  drive pod reads it at the same path), the env file's folder `/home/score/.config/score`, `~/.local` (uv's tools,
  score-lib's link, Claude Code's CLI).
- **One node** (`NODE_ROLE`: babon's pool `score-conductor-z2`, POP2-HM-16C-128G, min 1 max 1, tainted
  `tenant=score`): every pod that writes the store is placed beside the conductor's pod by pod affinity on the
  hostname, so one kernel and one file system hold the store's locks, links and fsync as on the VM. No network file
  system. Each such pod shares the node's process ids (`hostPID`): a run's registry entry, a hold's or a frozen
  copy's user names a pid that every other writer reads and signals as on the VM (the sweep's clean-frozen and the
  kill switch read and end them), never a pid of another pod's namespace.
- **The conductor** (StatefulSet `score-conductor`, one pod): the container `conductor` runs the VM's always-on units
  (`units.py`: the listener, health, update, secrets, sweep, resume at start); the container `door` is the agents'
  door as a service (port `DOOR_PORT`, `tools/cloud/conductor/door_service.py`), reached only by `kubectl
  port-forward` to this pod: the NetworkPolicy refuses every other way in.
- **CronJobs**: the sync pass (`score-sync`, every 5 min, Forbid: one pass at a time, the update first as the VM's
  sync unit does), the backup (`score-backup`, every 30 min) and its check (`score-backup-check`, 04:15). The backup
  writes its record (logs/backup-*.json, read by health) into the home, so it mounts the volume writable.
- **Rights**: the pods' ServiceAccount `score-conductor` is bound to score's existing Roles `score-conductor` in
  `score` and `score-jobs` (jobs, pods, logs, events, secrets: what the tenant login has), so a drive pod's Job and the
  submitter's Jobs are made from inside. The agents' ServiceAccount `score-door-agent` may only port-forward to the
  conductor's pod (`pods/portforward` on `score-conductor-0` and `get` on it): never `exec`, which runs any command
  past the door's allow-list.
- **Secrets by name only**: the one credential, the conductor's scw config (`SCW_SECRET`, key `config.yaml`), is made
  at the cutover from `score-conductor-key` through kubectl's stdin, and the registry's pull Secret
  (`REGISTRY_SECRET`, k8s/manifests.registry_secret: the image is private) beside it; everything else the pods read by name through
  `score-secret-reader`, as on the VM.

Money: every object carries `score.dev/cost=conductor` (COST_LABEL), apart from a batch's, so the stop line never
counts the always-on part (the VM's separate-project rule, carried over as a label).
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
IMAGES_JSON = HERE.parents[1] / "images" / "images.json"
NAMESPACE = "score"
JOBS_NAMESPACE = "score-jobs"
NAME = "score-conductor"
POD = f"{NAME}-0"  # the StatefulSet's one pod
CLAIM = "score-store"
VOLUME_CLASS = "sbs-5k-retain"
VOLUME_SIZE = "250Gi"
NODE_ROLE = ("babon/role", "score-conductor")
TOLERATION = {"key": "tenant", "operator": "Equal", "value": "score", "effect": "NoSchedule"}
COST_LABEL = ("score.dev/cost", "conductor")
APP_LABEL = "app.kubernetes.io/name"
WRITER_LABEL = "score.dev/store-writer"  # every pod that writes the store: placed beside the conductor's
UID = 1100  # user score on the VM
HOME = "/home/score"
MOUNTS = (("props", f"{HOME}/.farm-factory-props"), ("projects", f"{HOME}/projects"),
          ("config-score", f"{HOME}/.config/score"), ("local", f"{HOME}/.local"))
REPO = f"{HOME}/projects/score"
ENV_FILE = f"{HOME}/.config/score/dashboard.env"
SCW_SECRET = "score-conductor-scw"
REGISTRY_SECRET = "score-registry"  # the job images' pull Secret (k8s/manifests.registry_secret), made at the cutover
SCW_PATH = f"{HOME}/.config/scw"
RUNTIME_DIR = "/run/user/1100"  # user score's XDG_RUNTIME_DIR on the VM
DOOR_PORT = 8780
DOOR_AGENT = "score-door-agent"
PYTHON = f"{REPO}/.venv/bin/python"
# The env file's NAME=value lines in a shell's environment, as the VM's units have it (EnvironmentFile): the door reads
# its token through the secret reader, which names its project from there.
ENV_LOADED = 'set -a; [ -r "$SCORE_ENV_FILE" ] && . "$SCORE_ENV_FILE"; set +a;'
# Requests place a pod; limits keep it from taking the drive's room (the quota: 15 CPU / 120 Gi requests, 128 Gi
# limits in `score`, babon's tenants/score/quota.yaml).
CONDUCTOR = {"requests": {"cpu": "1", "memory": "4Gi"}, "limits": {"cpu": "4", "memory": "24Gi"}}
DOOR = {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"cpu": "1", "memory": "2Gi"}}
SYNC = {"requests": {"cpu": "1", "memory": "4Gi"}, "limits": {"cpu": "4", "memory": "16Gi"}}
BACKUP = {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "2", "memory": "8Gi"}}
CRONJOBS = (  # name, schedule, the VM unit's commands in order, resources
    ("score-sync", "*/5 * * * *",
     (f"/usr/bin/python3 -I {REPO}/tools/cloud/conductor/update.py --repo {REPO}",
      'SCORE_SYNC_TOKEN="$("$SCORE_SECRET_READER" score-cockpit-sync-token)" && [ -n "$SCORE_SYNC_TOKEN" ] && '
      f'export SCORE_SYNC_TOKEN && exec {PYTHON} -m score.dashboard sync'), SYNC),
    ("score-backup", "0,30 * * * *", (f"exec {PYTHON} -m score.store.backup backup",), BACKUP),
    ("score-backup-check", "15 4 * * *",
     (f"{PYTHON} -m score.store.backup forget", f"exec {PYTHON} -m score.store.backup check"), BACKUP),
)


def labels(component):
    return {APP_LABEL: NAME, "app.kubernetes.io/component": component, "app.kubernetes.io/managed-by": "score",
            "babon.eu/tenant": "score", COST_LABEL[0]: COST_LABEL[1]}


def meta(name, component, namespace=NAMESPACE):
    return {"name": name, "namespace": namespace, "labels": labels(component)}


def image_of(kind="conductor", images=IMAGES_JSON):
    """The kind's image reference pinned by digest in images.json, or None before its first build."""
    found = json.loads(pathlib.Path(images).read_text()).get(kind) or {}
    return found.get("image")


def volumes():
    return [{"name": "store", "persistentVolumeClaim": {"claimName": CLAIM}},
            {"name": "scw-secret", "secret": {"secretName": SCW_SECRET, "defaultMode": 0o400}},
            {"name": "scw", "emptyDir": {"medium": "Memory", "sizeLimit": "1Mi"}},
            {"name": "tmp", "emptyDir": {}},
            {"name": "run", "emptyDir": {"medium": "Memory", "sizeLimit": "64Mi"}}]


def mounts(read_only=False):
    """The store volume's folders at their VM paths, the scw config, a scratch /tmp, the secrets' tmpfs (secrets.sh
    writes the file-shaped secrets under $XDG_RUNTIME_DIR/score, memory only, as on the VM)."""
    return [*({"name": "store", "subPath": folder, "mountPath": path, "readOnly": read_only}
              for folder, path in MOUNTS),
            {"name": "scw", "mountPath": SCW_PATH, "readOnly": True}, {"name": "tmp", "mountPath": "/tmp"},
            {"name": "run", "mountPath": RUNTIME_DIR}]


def environment():
    """The pods' environment: the VM user's HOME and paths; the rest comes from the env file on the volume."""
    return [{"name": "HOME", "value": HOME}, {"name": "PROPS_HOME", "value": MOUNTS[0][1]},
            {"name": "SCORE_ENV_FILE", "value": ENV_FILE}, {"name": "XDG_RUNTIME_DIR", "value": RUNTIME_DIR},
            {"name": "SCORE_DOOR_REPO", "value": REPO},
            {"name": "PYTHONUNBUFFERED", "value": "1"}]


def security():
    return {"runAsUser": UID, "runAsGroup": UID, "fsGroup": UID, "fsGroupChangePolicy": "OnRootMismatch",
            "runAsNonRoot": True, "seccompProfile": {"type": "RuntimeDefault"}}


def beside_conductor():
    """Required: on the conductor's node (its role) and on the same host as its pod (the volume is ReadWriteOnce)."""
    return {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [
                {"matchExpressions": [{"key": NODE_ROLE[0], "operator": "In", "values": [NODE_ROLE[1]]}]}]}},
            "podAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": [
                {"labelSelector": {"matchLabels": {APP_LABEL: NAME, "app.kubernetes.io/component": "conductor"}},
                 "topologyKey": "kubernetes.io/hostname"}]}}


def on_conductor_node():
    return {"nodeAffinity": beside_conductor()["nodeAffinity"]}


def container(name, image, command, resources, read_only=False):
    return {"name": name, "image": image, "command": command, "env": environment(), "resources": resources,
            "workingDir": HOME, "volumeMounts": mounts(read_only),
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}


def scw_copy(image):
    """The init container that puts the scw config where the VM has it, owned by user score at mode 600 in memory: the
    Secret's own files are group-readable under the pods' fsGroup, and the scw CLI then prints a warning on stdout,
    ahead of the JSON the secret reader parses (the rehearsal of 2026-11-07)."""
    return {"name": "scw-config", "image": image, "command": ["/bin/sh", "-c",
            f"umask 077 && cp /secret/config.yaml {SCW_PATH}/config.yaml && chmod 600 {SCW_PATH}/config.yaml"],
            "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
            "volumeMounts": [{"name": "scw-secret", "mountPath": "/secret", "readOnly": True},
                             {"name": "scw", "mountPath": SCW_PATH}],
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}


def pod_spec(containers, affinity, restart="Always"):
    return {"initContainers": [scw_copy(containers[0]["image"])], "serviceAccountName": NAME, "securityContext": security(), "affinity": affinity, "hostPID": True,
            "imagePullSecrets": [{"name": REGISTRY_SECRET}], "tolerations": [TOLERATION], "volumes": volumes(), "containers": containers, "restartPolicy": restart,
            "terminationGracePeriodSeconds": 120}


def statefulset(image):
    """The conductor's one pod: its units, and the agents' door beside them."""
    door = container("door", image, ["/bin/sh", "-c", f'{ENV_LOADED} exec {PYTHON} -I '
                                     f'{REPO}/tools/cloud/conductor/door_service.py --port {DOOR_PORT}'], DOOR)
    door["ports"] = [{"name": "door", "containerPort": DOOR_PORT}]
    door["readinessProbe"] = {"periodSeconds": 20, "exec": {"command": [  # it listens on the pod's loopback only
        "/usr/bin/python3", "-c", f"import socket; socket.create_connection(('127.0.0.1', {DOOR_PORT}), 5)"]}}
    units = container("conductor", image, ["/usr/local/bin/score-conductor-start"], CONDUCTOR)
    pod_labels = {**labels("conductor"), WRITER_LABEL: "true"}
    return {"apiVersion": "apps/v1", "kind": "StatefulSet", "metadata": meta(NAME, "conductor"),
            "spec": {"replicas": 1, "serviceName": NAME, "podManagementPolicy": "OrderedReady",
                     "selector": {"matchLabels": {APP_LABEL: NAME, "app.kubernetes.io/component": "conductor"}},
                     "template": {"metadata": {"labels": pod_labels, "annotations": {
                                      "cluster-autoscaler.kubernetes.io/safe-to-evict": "false"}},
                                  "spec": pod_spec([units, door], on_conductor_node())}}}


def cronjob(name, schedule, commands, resources, image):
    """A VM timer as a CronJob beside the conductor: its unit's commands in order, one pass at a time."""
    script = " && ".join(f"( {command} )" if not command.startswith("exec ") else command for command in commands)
    shell = f'{ENV_LOADED} cd {REPO} && {script}'
    pod = pod_spec([container(name.removeprefix("score-"), image, ["/bin/sh", "-c", shell], resources)],
                   beside_conductor(), restart="Never")
    return {"apiVersion": "batch/v1", "kind": "CronJob", "metadata": meta(name, name.removeprefix("score-")),
            "spec": {"schedule": schedule, "concurrencyPolicy": "Forbid", "startingDeadlineSeconds": 300,
                     "successfulJobsHistoryLimit": 2, "failedJobsHistoryLimit": 3,
                     "jobTemplate": {"spec": {"backoffLimit": 0, "template": {
                         "metadata": {"labels": {**labels(name.removeprefix("score-")), WRITER_LABEL: "true"}},
                         "spec": pod}}}}}


def claim():
    return {"apiVersion": "v1", "kind": "PersistentVolumeClaim", "metadata": meta(CLAIM, "store"),
            "spec": {"accessModes": ["ReadWriteOnce"], "storageClassName": VOLUME_CLASS,
                     "resources": {"requests": {"storage": VOLUME_SIZE}}}}


def service_account(name, component):
    return {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": meta(name, component),
            "automountServiceAccountToken": name == NAME}


def binding(namespace):
    """score's Role `score-conductor` in `namespace` for the pods' ServiceAccount."""
    return {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding",
            "metadata": meta(f"{NAME}-pods", "rights", namespace),
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": NAME},
            "subjects": [{"kind": "ServiceAccount", "name": NAME, "namespace": NAMESPACE}]}


def door_role():
    """The agents' only right: port-forward to the conductor's pod (and see that pod), never exec."""
    return [{"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": meta(DOOR_AGENT, "door"),
             "rules": [{"apiGroups": [""], "resources": ["pods"], "resourceNames": [POD], "verbs": ["get"]},
                       {"apiGroups": [""], "resources": ["pods/portforward"], "resourceNames": [POD],
                        "verbs": ["get", "create"]}]},
            {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": meta(DOOR_AGENT, "door"),
             "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": DOOR_AGENT},
             "subjects": [{"kind": "ServiceAccount", "name": DOOR_AGENT, "namespace": NAMESPACE}]}]


def closed():
    """No way into the conductor's pods over the network: port-forward goes through the kubelet, not the pod network."""
    return {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": meta(f"{NAME}-closed", "door"),
            "spec": {"podSelector": {"matchLabels": {APP_LABEL: NAME}}, "policyTypes": ["Ingress"], "ingress": []}}


def headless():
    return {"apiVersion": "v1", "kind": "Service", "metadata": meta(NAME, "conductor"),
            "spec": {"clusterIP": "None", "selector": {APP_LABEL: NAME, "app.kubernetes.io/component": "conductor"},
                     "ports": [{"name": "door", "port": DOOR_PORT}]}}


def objects(image):
    """Every object of the conductor in the cluster, in the order they are applied."""
    if not image:
        raise ValueError("no conductor image: build tools/cloud/images/conductor first, or pass --image")
    return [service_account(NAME, "rights"), service_account(DOOR_AGENT, "door"),
            binding(NAMESPACE), binding(JOBS_NAMESPACE), *door_role(), closed(), claim(), headless(),
            statefulset(image), *(cronjob(*row, image) for row in CRONJOBS)]


def as_list(found):
    return {"apiVersion": "v1", "kind": "List", "items": found}
