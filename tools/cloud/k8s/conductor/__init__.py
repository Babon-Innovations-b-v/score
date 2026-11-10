"""The conductor in the cluster (#76, the plan of 2026-11-07, step 1): its objects as plain manifests (JSON for
kubectl), rendered here and checked with `kubectl apply --dry-run=server`; the cutover applied them, and an object
added since is applied by name (`apply --only`, after the same dry run), never the whole set.

    python -m tools.cloud.k8s.conductor render --image <ref>    # the objects as one List on stdout
    python -m tools.cloud.k8s.conductor check --image <ref>     # the same through kubectl's server-side dry run
    python -m tools.cloud.k8s.conductor apply --only <name>     # those objects applied (the owner's login)

The shape (namespace `score` in babon's cluster, zone fr-par-2, beside the card pools):

- **The store's volume** (`score-store`): one block volume claim, ReadWriteOnce, class `sbs-5k-retain` (the owner's
  pick, 2026-11-07), `VOLUME_SIZE` (the VM's 229 GB data disk, 109 GB used, plus room). Its subfolders are mounted at
  the paths they have on the VM (`MOUNTS`): the home `/home/score/.farm-factory-props` (PROPS_HOME: no path in any
  record changes), the checkout's folder `/home/score/projects` (a run's frozen copy is a git worktree of it, so a
  drive pod reads it at the same path), the env file's folder `/home/score/.config/score`, `~/.local` (uv's tools,
  score-lib's link, Claude Code's CLI), the people routes' motion home `/home/score/.farm-factory-motion`.
- **One node** (`NODE_ROLE`: babon's pool `score-conductor-8c-z2`, `NODE_TYPE`, min 1 max 1, tainted
  `tenant=score`): every pod that writes the store is placed beside the conductor's pod by pod affinity on the
  hostname, so one kernel and one file system hold the store's locks, links and fsync as on the VM. No network file
  system. Each such pod shares the node's process ids (`hostPID`): a run's registry entry, a hold's or a frozen
  copy's user names a pid that every other writer reads and signals as on the VM (the sweep's clean-frozen and the
  kill switch read and end them), never a pid of another pod's namespace.
- **The conductor** (StatefulSet `score-conductor`, one pod): the container `conductor` runs the VM's always-on units
  (`units.py`: the listener, health, update, secrets, sweep, resume at start and every 5 minutes); the container `door` is the agents'
  door as a service (port `DOOR_PORT`, `tools/cloud/conductor/door_service.py`), reached only by `kubectl
  port-forward` to this pod: the NetworkPolicy refuses every other way in.
- **CronJobs**: the sync pass (`score-sync`, every 5 min, Forbid: one pass at a time, the update first as the VM's
  sync unit does), the backup (`score-backup`, every 30 min) and its check (`score-backup-check`, 04:15); the env1
  cap's watcher (`score-cap-watch`, every 5 min, 240 s, Replace) on babon's system pool, apart from the conductor's
  node and with no store volume (`cap_watch`, tools/cloud/cap_watch). The backup
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
VOLUME_SIZE = "400Gi"
NODE_ROLE = ("babon/role", "score-conductor")
# The conductor's node: POP2-HM-8C-64G since 2026-11-10 (it was a POP2-HM-16C-128G at the cutover), its allocatable as
# the cluster reported it that day, and the requests of the node's own DaemonSets (node feature discovery 5m / 64Mi,
# node-exporter 10m / 32Mi). A drive pod asking for more than `drive_room` leaves never schedules (2026-11-10: the
# record's 16 x 0.5 CPU and 64 GB on this node, and every Buy failed).
NODE_TYPE = "POP2-HM-8C-64G"
NODE_ALLOCATABLE = {"cpu": "7800m", "memory": "62592876Ki"}
NODE_DAEMONS = {"cpu": "15m", "memory": "96Mi"}
TOLERATION = {"key": "tenant", "operator": "Equal", "value": "score", "effect": "NoSchedule"}
COST_LABEL = ("score.dev/cost", "conductor")
APP_LABEL = "app.kubernetes.io/name"
WRITER_LABEL = "score.dev/store-writer"  # every pod that writes the store: placed beside the conductor's
UID = 1100  # user score on the VM
HOME = "/home/score"
# `motion`: the people routes' candidate folders (prop_person.CANDIDATES, the door's route-log), on the VM's root disk
# under ~/.farm-factory-motion and in no backup; copied once off a snapshot of it at the cutover (2026-11-08: the
# characters rows found no motion home in the cluster).
MOUNTS = (("props", f"{HOME}/.farm-factory-props"), ("projects", f"{HOME}/projects"),
          ("config-score", f"{HOME}/.config/score"), ("local", f"{HOME}/.local"),
          ("motion", f"{HOME}/.farm-factory-motion"))
REPO = f"{HOME}/projects/score"
ENV_FILE = f"{HOME}/.config/score/dashboard.env"
SCW_SECRET = "score-conductor-scw"
# The VM's login for the cluster's Jobs (score-jobs:score-conductor's token, context score-conductor), made at the
# cutover from that account's service-account-token Secret through kubectl's stdin, key `config`; every pod reads it at
# the VM's path (2026-11-08: the cluster submits failed, "stat /home/score/.kube/config: no such file or directory").
KUBECONFIG_SECRET = "score-conductor-kubeconfig"
KUBECONFIG = f"{HOME}/.kube/config"
REGISTRY_SECRET = "score-registry"  # the job images' pull Secret (k8s/manifests.registry_secret), made at the cutover
CONFIG = f"{HOME}/.config"
SCW_PATH = f"{CONFIG}/scw"
RUNTIME_DIR = "/run/user/1100"  # user score's XDG_RUNTIME_DIR on the VM
# score_lib, the library (owner, 2026-11-08: "dont keep score lib on the conductor disk"): a throwaway clone at LIBRARY
# on each pod's own /tmp, made fresh from GitHub at the pod's start (`library_clone`); a handover pushes at once
# (score_lib's handover rebases and pushes), and one whose push fails fails its row (score/stages/library/checks.py
# saved), never leaving commits on a disk. Its blobs are in the bucket, its command a tool on the volume (LIBRARY_ENV,
# the venv of the clone's uv.lock; its editable install names LIBRARY, the same path in every pod).
LIBRARY = "/tmp/score_lib"
LIBRARY_URL = "git@github.com:Babon-Innovations-b-v/score_lib.git"
LIBRARY_ENV = f"{HOME}/.local/share/score-lib/venv"
# score_lib's deploy key (secret score-lib-deploy-key, write access), made at the cutover as this Secret through
# kubectl's stdin, key `key`; the init container copies it to the secrets' tmpfs at mode 600, where secrets.sh puts
# it on the VM and score_lib's core.sshCommand reads it.
LIBRARY_KEY_SECRET = "score-lib-deploy-key"
LIBRARY_KEY = f"{RUNTIME_DIR}/score/score-lib-deploy-key"
# GitHub's published host keys (api.github.com/meta, checked 2026-11-08 against docs.github.com's fingerprints:
# ED25519 SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU, ECDSA SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM),
# the only hosts score_lib's ssh accepts (StrictHostKeyChecking=yes), as boot.sh pins them on the VM.
GITHUB_KEYS = (
    "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl\n"
    "github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYM"
    "jNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=\n")
KNOWN_HOSTS_MAP = "score-github-known-hosts"
KNOWN_HOSTS = f"{HOME}/.ssh/known_hosts_github"
LIBRARY_SSH = (f"ssh -i {LIBRARY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes "
               f"-o UserKnownHostsFile={KNOWN_HOSTS}")
DOOR_PORT = 8780
DOOR_AGENT = "score-door-agent"
HEALTH_WRITTEN = "SCORE_HEALTH_WRITTEN"  # score.conductor health prints the written health.json (the door's)
PYTHON = f"{REPO}/.venv/bin/python"
# The env file's NAME=value lines in a shell's environment, as the VM's units have it (EnvironmentFile): the door reads
# its token through the secret reader, which names its project from there.
ENV_LOADED = 'set -a; [ -r "$SCORE_ENV_FILE" ] && . "$SCORE_ENV_FILE"; set +a;'
# Requests place a pod; limits keep it from taking the drive's room (the quota: 15 CPU / 120 Gi requests, 128 Gi
# limits in `score`, babon's tenants/score/quota.yaml).
CONDUCTOR = {"requests": {"cpu": "1", "memory": "4Gi"}, "limits": {"cpu": "4", "memory": "24Gi"}}
# The door runs the agents' commands (moved, tests, a store pull): 8 CPU / 48 Gi, set live 2026-11-08.
DOOR = {"requests": {"cpu": "500m", "memory": "2Gi"}, "limits": {"cpu": "8", "memory": "48Gi"}}
SYNC = {"requests": {"cpu": "1", "memory": "4Gi"}, "limits": {"cpu": "4", "memory": "16Gi"}}
BACKUP = {"requests": {"cpu": "500m", "memory": "1Gi"}, "limits": {"cpu": "2", "memory": "8Gi"}}
# score's namespace defaults for a container that names none (LimitRange `score-defaults`): a default cpu limit of 1
# made every drive pod of 8 cores invalid until 2026-11-08, when it was set to 16 live.
LIMIT_DEFAULTS = {"default": {"cpu": "16", "memory": "1Gi"}, "defaultRequest": {"cpu": "100m", "memory": "256Mi"}}
IMAGE_VARIABLE = "SCORE_CONDUCTOR_IMAGE"  # the pod's own image by digest, which the cutover writes in cluster.json
CRONJOBS = (  # name, schedule, the VM unit's commands in order, resources
    ("score-sync", "*/5 * * * *",
     (f"/usr/bin/python3 -I {REPO}/tools/cloud/conductor/update.py --repo {REPO}",
      'SCORE_SYNC_TOKEN="$("$SCORE_SECRET_READER" score-cockpit-sync-token)" && [ -n "$SCORE_SYNC_TOKEN" ] && '
      f'export SCORE_SYNC_TOKEN && exec {PYTHON} -m score.dashboard sync'), SYNC),
    ("score-backup", "0,30 * * * *", (f"exec {PYTHON} -m score.store.backup backup",), BACKUP),
    ("score-backup-check", "15 4 * * *",
     (f"{PYTHON} -m score.store.backup forget", f"exec {PYTHON} -m score.store.backup check"), BACKUP),
)


BYTES = {"Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40}


def millicores(text):
    """A cpu quantity ("500m", "1", "7.8") in millicores."""
    text = str(text)
    return int(text[:-1]) if text.endswith("m") else int(float(text) * 1000)


def memory_bytes(text):
    """A memory quantity in the binary units these manifests use ("4Gi", "62592876Ki") in bytes."""
    text = str(text)
    return int(text[:-2]) * BYTES[text[-2:]] if text[-2:] in BYTES else int(text)


def drive_room():
    """(millicores, bytes) a drive pod may request on the conductor's node: its allocatable less the node's DaemonSets,
    the conductor pod's containers and every CronJob that runs there beside a drive."""
    beside = [NODE_DAEMONS, CONDUCTOR["requests"], DOOR["requests"], *(row[-1]["requests"] for row in CRONJOBS)]
    return (millicores(NODE_ALLOCATABLE["cpu"]) - sum(millicores(taken["cpu"]) for taken in beside),
            memory_bytes(NODE_ALLOCATABLE["memory"]) - sum(memory_bytes(taken["memory"]) for taken in beside))


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
            {"name": "kubeconfig", "secret": {"secretName": KUBECONFIG_SECRET, "defaultMode": 0o400}},
            {"name": "library-key", "secret": {"secretName": LIBRARY_KEY_SECRET, "defaultMode": 0o400}},
            {"name": "known-hosts", "configMap": {"name": KNOWN_HOSTS_MAP, "defaultMode": 0o444}},
            {"name": "scw", "emptyDir": {"medium": "Memory", "sizeLimit": "1Mi"}},
            {"name": "tmp", "emptyDir": {}}, {"name": "config", "emptyDir": {"sizeLimit": "64Mi"}},
            {"name": "run", "emptyDir": {"medium": "Memory", "sizeLimit": "64Mi"}}]


def mounts(read_only=False):
    """The store volume's folders at their VM paths, the scw config, a scratch /tmp, the secrets' tmpfs (secrets.sh
    writes the file-shaped secrets under $XDG_RUNTIME_DIR/score, memory only, as on the VM), and ~/.config as an
    emptyDir of the pods' group under them (the rehearsal of 2026-11-07: the runtime made it root's for the nested
    mounts, and matplotlib found no folder it could write), and the cluster's login at the VM's ~/.kube/config."""
    return [{"name": "config", "mountPath": CONFIG},  # ~/.config user score's, never the runtime's root-owned folder
            *({"name": "store", "subPath": folder, "mountPath": path, "readOnly": read_only}
              for folder, path in MOUNTS),
            {"name": "scw", "mountPath": SCW_PATH, "readOnly": True}, {"name": "tmp", "mountPath": "/tmp"},
            {"name": "kubeconfig", "subPath": "config", "mountPath": KUBECONFIG, "readOnly": True},
            {"name": "known-hosts", "subPath": "known_hosts", "mountPath": KNOWN_HOSTS, "readOnly": True},
            {"name": "run", "mountPath": RUNTIME_DIR}]


def environment():
    """The pods' environment: the VM user's HOME and paths; the rest comes from the env file on the volume."""
    return [{"name": "HOME", "value": HOME}, {"name": "PROPS_HOME", "value": MOUNTS[0][1]},
            {"name": "SCORE_ENV_FILE", "value": ENV_FILE}, {"name": "XDG_RUNTIME_DIR", "value": RUNTIME_DIR},
            {"name": "SCORE_DOOR_REPO", "value": REPO},
            {"name": "SCORE_LIB_ROOT", "value": LIBRARY},
            {"name": "SCORE_LIB_COMMAND", "value": f"{LIBRARY_ENV}/bin/score-lib"},
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
    return {"name": name, "image": image, "command": command,
            "env": [*environment(), {"name": IMAGE_VARIABLE, "value": image}], "resources": resources,
            "workingDir": HOME, "volumeMounts": mounts(read_only),
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}


def scw_copy(image):
    """The init container that puts the scw config where the VM has it, owned by user score at mode 600 in memory: the
    Secret's own files are group-readable under the pods' fsGroup, and the scw CLI then prints a warning on stdout,
    ahead of the JSON the secret reader parses (the rehearsal of 2026-11-07). score_lib's deploy key the same way, onto
    the secrets' tmpfs (ssh refuses a group-readable key)."""
    script = (f"umask 077 && cp /secret/config.yaml {SCW_PATH}/config.yaml && chmod 600 {SCW_PATH}/config.yaml && "
              f"mkdir -p {RUNTIME_DIR}/score && chmod 700 {RUNTIME_DIR}/score && "
              f"cp /library-key/key {LIBRARY_KEY} && chmod 600 {LIBRARY_KEY}")
    return {"name": "scw-config", "image": image, "command": ["/bin/sh", "-c", script],
            "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
            "volumeMounts": [{"name": "scw-secret", "mountPath": "/secret", "readOnly": True},
                             {"name": "scw", "mountPath": SCW_PATH},
                             {"name": "library-key", "mountPath": "/library-key", "readOnly": True},
                             {"name": "run", "mountPath": RUNTIME_DIR}],
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}


def library_clone(image):
    """The init container that clones score_lib fresh from GitHub into the pod's /tmp (LIBRARY) with its deploy key,
    then brings the command's venv on the volume to the clone's uv.lock (one pod at a time: flock) and links score-lib
    on the PATH. A clone that fails stops the pod: no library is better than a stale one."""
    lock = f"{LIBRARY_ENV}.lock"
    script = (f"rm -rf {LIBRARY} && GIT_SSH_COMMAND='{LIBRARY_SSH}' git clone -q {LIBRARY_URL} {LIBRARY} && "
              f"git -C {LIBRARY} config core.sshCommand '{LIBRARY_SSH}' && mkdir -p {LIBRARY_ENV.rsplit('/', 1)[0]} && "
              f"UV_PROJECT_ENVIRONMENT={LIBRARY_ENV} flock {lock} uv sync -q --frozen --project {LIBRARY} && "
              f"mkdir -p {HOME}/.local/bin && ln -sfn {LIBRARY_ENV}/bin/score-lib {HOME}/.local/bin/score-lib")
    return {"name": "score-lib", "image": image, "command": ["/bin/sh", "-c", script], "env": environment(),
            "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
            "workingDir": HOME, "volumeMounts": mounts(),
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}


def known_hosts():
    """GitHub's pinned host keys as a ConfigMap (public keys: no Secret)."""
    return {"apiVersion": "v1", "kind": "ConfigMap", "metadata": meta(KNOWN_HOSTS_MAP, "rights"),
            "data": {"known_hosts": GITHUB_KEYS}}


def pod_spec(containers, affinity, restart="Always"):
    return {"initContainers": [scw_copy(containers[0]["image"]), library_clone(containers[0]["image"])], "serviceAccountName": NAME, "securityContext": security(), "affinity": affinity, "hostPID": True,
            "imagePullSecrets": [{"name": REGISTRY_SECRET}], "tolerations": [TOLERATION], "volumes": volumes(), "containers": containers, "restartPolicy": restart,
            "terminationGracePeriodSeconds": 120}


def statefulset(image):
    """The conductor's one pod: its units, and the agents' door beside them."""
    door = container("door", image, ["/bin/sh", "-c", f'{ENV_LOADED} exec {PYTHON} -I '
                                     f'{REPO}/tools/cloud/conductor/door_service.py --port {DOOR_PORT}'], DOOR)
    door["ports"] = [{"name": "door", "containerPort": DOOR_PORT}]
    # The door's health is the conductor container's own, as its health unit wrote it (score.conductor health): read
    # in the door's container it would be that container's 1 CPU and 2 GiB (the rehearsal of 2026-11-07).
    door["env"].append({"name": HEALTH_WRITTEN, "value": "1"})
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


# The env1 cap's watcher (tools/cloud/cap_watch, the plan of 2026-11-09 B3): its own CronJob on babon's system pool,
# never beside the conductor, so it watches with the conductor's node off; no store volume (its records are in the
# object store), the code a fresh shallow clone of main each pass, the conductor's scw key (read rights on the whole
# bill, machines, disks, clusters) and ServiceAccount (it deletes score Jobs in score-jobs).
CAP_WATCH = "score-cap-watch"
CAP_WATCH_SCHEDULE = "*/5 * * * *"
CAP_WATCH_DEADLINE = 240  # seconds: a pass never overlaps the next (concurrencyPolicy Replace too)
CAP_WATCH_RESOURCES = {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"cpu": "1", "memory": "1Gi"}}
SYSTEM_POOL = ("k8s.scaleway.com/pool-name", "system-z1")
CAP_WATCH_CODE = "https://github.com/Babon-Innovations-b-v/score.git"
RUNNER_PYTHON = "/opt/score/env/bin/python"  # the runner image's environment (uv.lock), under the conductor image


def cap_watch(image):
    """The cap watcher's CronJob: every 5 minutes, at most 240 s a pass, a newer pass replacing a late one."""
    code = "/tmp/score"
    copy = {"name": "scw-config", "image": image, "command": ["/bin/sh", "-c", (
                f"umask 077 && cp /secret/config.yaml {SCW_PATH}/config.yaml && chmod 600 {SCW_PATH}/config.yaml")],
            "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
            "volumeMounts": [{"name": "scw-secret", "mountPath": "/secret", "readOnly": True},
                             {"name": "scw", "mountPath": SCW_PATH}],
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}
    script = (f"rm -rf {code} && git clone -q --depth 1 --filter=blob:none --sparse {CAP_WATCH_CODE} {code} && "
              f"git -C {code} sparse-checkout set score tools && cd {code} && "
              f"exec {RUNNER_PYTHON} -I tools/cloud/cap_watch/watch.py pass")
    watcher = {"name": "cap-watch", "image": image, "command": ["/bin/sh", "-c", script],
               "env": [{"name": "HOME", "value": HOME}, {"name": "PYTHONUNBUFFERED", "value": "1"},
                       {"name": "SCORE_CLOUD", "value": "scaleway"}],
               "resources": CAP_WATCH_RESOURCES, "workingDir": HOME,
               "volumeMounts": [{"name": "scw", "mountPath": SCW_PATH}, {"name": "tmp", "mountPath": "/tmp"}],
               "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}}
    pod = {"serviceAccountName": NAME, "securityContext": security(), "restartPolicy": "Never",
           "nodeSelector": {SYSTEM_POOL[0]: SYSTEM_POOL[1]}, "imagePullSecrets": [{"name": REGISTRY_SECRET}],
           "volumes": [{"name": "scw-secret", "secret": {"secretName": SCW_SECRET, "defaultMode": 0o400}},
                       {"name": "scw", "emptyDir": {"medium": "Memory", "sizeLimit": "1Mi"}},
                       {"name": "tmp", "emptyDir": {"sizeLimit": "2Gi"}}],
           "initContainers": [copy], "containers": [watcher]}
    return {"apiVersion": "batch/v1", "kind": "CronJob", "metadata": meta(CAP_WATCH, "cap-watch"),
            "spec": {"schedule": CAP_WATCH_SCHEDULE, "concurrencyPolicy": "Replace", "startingDeadlineSeconds": 120,
                     "successfulJobsHistoryLimit": 2, "failedJobsHistoryLimit": 3,
                     "jobTemplate": {"spec": {"backoffLimit": 0, "activeDeadlineSeconds": CAP_WATCH_DEADLINE,
                                              "template": {"metadata": {"labels": labels("cap-watch")},
                                                           "spec": pod}}}}}


def limit_range():
    return {"apiVersion": "v1", "kind": "LimitRange", "metadata": meta("score-defaults", "rights"),
            "spec": {"limits": [{"type": "Container", **LIMIT_DEFAULTS}]}}


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
    return [limit_range(), service_account(NAME, "rights"), service_account(DOOR_AGENT, "door"),
            binding(NAMESPACE), binding(JOBS_NAMESPACE), *door_role(), closed(), claim(), known_hosts(), headless(),
            statefulset(image), *(cronjob(*row, image) for row in CRONJOBS), cap_watch(image)]


def picked(found, names):
    """The objects of `found` named `names`, in their order; ValueError naming any name no object has."""
    unknown = sorted(set(names) - {item["metadata"]["name"] for item in found})
    if unknown:
        raise ValueError(f"no conductor object named {', '.join(unknown)}")
    return [item for item in found if item["metadata"]["name"] in names]


def as_list(found):
    return {"apiVersion": "v1", "kind": "List", "items": found}
