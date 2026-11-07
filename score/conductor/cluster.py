"""The conductor in the cluster (#76, the plan of 2026-11-07, steps 2, 3 and 5): what a home on the cluster does
differently from the VM. A home is the cluster's when `$PROPS_HOME/conductor/cluster.json` is there (written at the
cutover; RECORD); without it nothing here acts and every caller behaves as on the VM and the PC.

    {"namespace": "score", "image": "<the conductor image by digest>", "jobs": 16, "cpu_per_job": 0.5,
     "max_memory_gb": 64}

- **The drive as a pod** (step 2): `score run --detach` on such a home creates one Job for the run (`drive_job`,
  `detach`) in place of the systemd scope: no retries, `restartPolicy: Never`, the store's volume at the VM's paths
  beside the conductor's pod on its node (tools/cloud/k8s/conductor), its working folder the run's frozen copy on that
  volume (the run's commit), its command and output log the same as the scope's. The run's environment goes with it,
  every variable that could hold a secret left out (SECRET_NAME): those the run reads by name, as on the VM. An OOM or
  a node loss ends that run alone; `score resume` takes it up from the store.
- **Requests from the plan** (step 3): the pod's memory request is the memory guard's own reckoning
  (`memory_request`: the floor beside the largest kept stage peaks, one a job at once), its limit the same, at most
  `max_memory_gb`; its processor request `jobs` x `cpu_per_job`. A run's jobs on such a home are the record's
  (`jobs`), so a price is worked out on the jobs the pod is given, never on the cores of whatever node answers.
  Inside a pod the guard reads the pod's own memory (`pod_memory`, cgroup v2), not the node's.
- **Health from inside a pod** (step 5): the Machine card's figures from the pod and the volume, never systemd: the
  units from the cluster's own answer (`pod_view`: the conductor pod's containers, the sync and backup CronJobs'
  newest Jobs, every unit failed when the cluster does not answer), the memory and cores of the pod's own limits
  (`pod_memory`, `cores`), each unit's log tail from `kubectl logs` (`pod_log`); the disk is the volume's, read as on
  the VM.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

from score import conductor

RECORD = conductor.HOME / "cluster.json"
CGROUP = pathlib.Path("/sys/fs/cgroup")
GIB = 2 ** 30
# Variables a Job's spec never carries: the API and its store would hold their values.
SECRET_NAME = re.compile(r"TOKEN|SECRET|PASSWORD|PASSPHRASE|CREDENTIAL|_KEY$|^AWS_|KUBECONFIG")
# The pod's own variables, set again by Kubernetes in each pod.
POD_OWN = re.compile(r"^(KUBERNETES_|HOSTNAME$|PWD$|SHLVL$|_$|OLDPWD$)")
DRIVE_LABEL = "score.dev/drive"
START_SECONDS = 300  # the drive pod's start on the conductor's node, its image already there
DEFAULTS = {"namespace": "score", "jobs": 16, "cpu_per_job": 0.5, "max_memory_gb": 64}


def record(path=None):
    """The home's cluster record (DEFAULTS under what it holds), or None when the home is not the cluster's."""
    path = pathlib.Path(path or RECORD)
    if not path.is_file():
        return None
    return {**DEFAULTS, **json.loads(path.read_text())}


def jobs(found):
    """The jobs a run drives at once on the cluster's home: the record's, so its price and its pod agree."""
    return int(found["jobs"])


def memory_request(peaks, jobs_at_once, floor, most_gb):
    """The drive pod's memory in bytes: the floor the memory guard keeps free beside the `jobs_at_once` largest kept
    stage peaks (`peaks`: {stage: bytes}, the runner's memory/peaks-made.json), each never under the floor (a stage
    never measured is given it), at most `most_gb`."""
    largest = sorted((max(peak, floor) for peak in peaks.values()), reverse=True)[:jobs_at_once]
    largest += [floor] * (jobs_at_once - len(largest))
    return min(int(most_gb * GIB), floor + sum(largest))


def kept_peaks(store_root):
    """{stage: bytes} the runner keeps beside the store (graph.Runner.peaks), {} before the first measure."""
    path = pathlib.Path(store_root) / "memory" / "peaks-made.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def carried_environment(environment):
    """The run's variables a Job carries: no secret's, none Kubernetes sets in the pod itself."""
    return [{"name": name, "value": value} for name, value in sorted(environment.items())
            if not SECRET_NAME.search(name) and not POD_OWN.match(name)]


def job_name(log):
    """The log's stem (score-run-<time>, runs.log_path) as a Kubernetes name, score-run- before it when missing."""
    stem = pathlib.Path(log).stem
    name = re.sub(r"[^a-z0-9-]+", "-", (stem if stem.startswith("score-run") else f"score-run-{stem}").lower())
    name = name.strip("-")
    return name[:63].rstrip("-")


def drive_job(found, command, log, folder, environment, memory_bytes):
    """The run's one Job: its command into its log from its folder, on the conductor's node beside its pod."""
    from tools.cloud.k8s import conductor as pods  # the repository's tools, at the run's own commit
    cpu = f"{int(1000 * jobs(found) * float(found['cpu_per_job']))}m"
    memory = f"{memory_bytes // 2 ** 20}Mi"
    shell = 'echo $$ > "$SCORE_DRIVE_LOG.pid" && exec "$@" >> "$SCORE_DRIVE_LOG" 2>&1'
    container = pods.container("drive", found["image"], ["/bin/sh", "-c", shell, "drive", *command],
                               {"requests": {"cpu": cpu, "memory": memory}, "limits": {"memory": memory}})
    container["workingDir"] = str(folder)
    own = {variable["name"] for variable in container["env"]}
    container["env"] = [*(variable for variable in carried_environment(environment) if variable["name"] not in own),
                        *container["env"],
                        {"name": "SCORE_DRIVE_LOG", "value": str(log)},
                        {"name": "SCORE_DRIVE_POD", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}}]
    labels = {**pods.labels("drive"), pods.WRITER_LABEL: "true", DRIVE_LABEL: job_name(log)}
    spec = pods.pod_spec([container], pods.beside_conductor(), restart="Never")
    spec["terminationGracePeriodSeconds"] = 180  # stopped.py's own forward wait and the run's release
    return {"apiVersion": "batch/v1", "kind": "Job",
            "metadata": {"name": job_name(log), "namespace": found["namespace"], "labels": labels},
            "spec": {"backoffLimit": 0, "ttlSecondsAfterFinished": 7 * 24 * 3600,
                     "template": {"metadata": {"labels": labels}, "spec": spec}}}


def detach(found, command, log, folder, environment, store_root, apply=None, wait=None):
    """Start the run as its Job (kubectl through stdin) and wait for its command's pid (`started_pid`); (the Job's
    name, the pid)."""
    from score import graph  # the drive's own guard: its floor is the one the pod's room is reckoned beside
    request = memory_request(kept_peaks(store_root), jobs(found), graph.memory_floor(), found["max_memory_gb"])
    job = drive_job(found, command, log, folder, environment, request)
    (apply or kubectl_apply)(job)
    return job["metadata"]["name"], (wait or started_pid)(log)


def started_pid(log, seconds=START_SECONDS, sleep=time.sleep, clock=time.monotonic):
    """The pid the run's pod wrote beside its log as its command started (`<log>.pid`). Every pod that writes the
    store shares the node's process ids, so it is the run's pid here too: the cockpit and the registry follow it as
    on the VM. Raises after `seconds` with none (the pod never started: kubectl's events say why)."""
    path, until = pathlib.Path(f"{log}.pid"), clock() + seconds
    while clock() < until:
        text = path.read_text().strip() if path.is_file() else ""
        if text.isdigit():
            return int(text)
        sleep(2)
    raise TimeoutError(f"the run's pod wrote no pid beside {log} in {seconds} s: kubectl describe job names why")


def kubectl_apply(job):
    subprocess.run(["kubectl", "apply", "-f", "-"], input=json.dumps(job), text=True, check=True,
                   capture_output=True)


def cgroup_number(name, root=CGROUP):
    """One cgroup v2 file's number, None when it is `max`, missing or unreadable."""
    try:
        text = (pathlib.Path(root) / name).read_text().split()[0]
    except (OSError, IndexError):
        return None
    return None if text == "max" else int(text)


def pod_memory(root=CGROUP):
    """(total, available) bytes of this pod's own memory limit, or None outside a limited cgroup: available is the
    limit less what the cgroup holds, its page cache it may drop (inactive_file) given back."""
    limit = cgroup_number("memory.max", root)
    current = cgroup_number("memory.current", root)
    if limit is None or current is None:
        return None
    inactive = 0
    try:
        for line in (pathlib.Path(root) / "memory.stat").read_text().splitlines():
            if line.startswith("inactive_file "):
                inactive = int(line.split()[1])
    except OSError:
        pass
    return limit, max(0, limit - current + inactive)


def guard_pod_memory(graph_module, root=CGROUP, environment=None):
    """Inside a pod with a memory limit, the runner's memory guard reads the pod's memory, never the node's (the
    node's MemAvailable holds the other pods' room); whether it does. Outside a pod (no KUBERNETES_SERVICE_HOST)
    nothing changes."""
    if not (os.environ if environment is None else environment).get("KUBERNETES_SERVICE_HOST") \
            or pod_memory(root) is None:
        return False
    node_available, node_total = graph_module.AVAILABLE, graph_module.TOTAL
    graph_module.AVAILABLE = lambda: min(node_available(), pod_memory(root)[1])
    graph_module.TOTAL = lambda: min(node_total(), pod_memory(root)[0])
    return True
def cores(root=CGROUP):
    """This pod's processors by its cgroup's quota (cpu.max), else None (no quota: the node's)."""
    try:
        quota, period = (pathlib.Path(root) / "cpu.max").read_text().split()
    except (OSError, ValueError):
        return None
    return None if quota == "max" else max(1, round(int(quota) / int(period)))




def in_pod(environment=None):
    """Whether this process runs in a Kubernetes pod (the API's address in its environment)."""
    return bool((os.environ if environment is None else environment).get("KUBERNETES_SERVICE_HOST"))


def kubectl_json(namespace, *words):
    """kubectl's JSON answer from inside the pod (its ServiceAccount), or None with why on stderr."""
    try:
        done = subprocess.run(["kubectl", "-n", namespace, *words, "-o", "json"], capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"score.conductor: the cluster did not answer: {error}", file=sys.stderr)
        return None
    if done.returncode:
        print(f"score.conductor: the cluster did not answer: {done.stderr.strip()[:200]}", file=sys.stderr)
        return None
    return json.loads(done.stdout)


def component(item):
    return item["metadata"].get("labels", {}).get("app.kubernetes.io/component")


def newest_job(items, unit):
    """The newest Job of one CronJob's component (`sync`, `backup`), or None."""
    runs = sorted((item for item in items if item["kind"] == "Job" and component(item) == unit),
                  key=lambda item: item["metadata"].get("creationTimestamp", ""))
    return runs[-1] if runs else None


def job_state(job):
    status = (job or {}).get("status", {})
    if status.get("failed"):
        return "failed"
    return "active" if status.get("active") or status.get("succeeded") else "inactive"


def pod_view(namespace="score", answer=None):
    """{units: {sync, listen, resume, backup: active, failed or inactive}, last_sync: {at, ok} or None} of the
    conductor's pods and CronJobs as the cluster answers, health's own shapes (health.UNITS, health.last_sync): listen
    and resume the conductor pod's containers ready (resume is a unit of that pod, units.py), sync and backup their
    CronJob's newest Job; every unit failed when the cluster does not answer, never read as fine."""
    found = answer if answer is not None else kubectl_json(namespace, "get", "pods,jobs", "-l",
                                                           "app.kubernetes.io/name=score-conductor")
    if found is None:
        return {"units": dict.fromkeys(("sync", "listen", "resume", "backup"), "failed"), "last_sync": None}
    items = found.get("items", [])
    pods = [item for item in items if item["kind"] == "Pod" and component(item) == "conductor"]
    ready = [status.get("ready") for pod in pods for status in pod.get("status", {}).get("containerStatuses", [])]
    conductor_state = "active" if ready and all(ready) else "failed" if pods else "inactive"
    sync = newest_job(items, "sync")
    ended = [job for job in items if job["kind"] == "Job" and component(job) == "sync"
             and (job.get("status", {}).get("completionTime") or job.get("status", {}).get("failed"))]
    last = max(ended, key=lambda job: job["metadata"].get("creationTimestamp", ""), default=None)
    last_sync = None if last is None else {
        "at": last["status"].get("completionTime") or last["metadata"].get("creationTimestamp"),
        "ok": bool(last["status"].get("succeeded"))}
    return {"units": {"sync": job_state(sync), "listen": conductor_state, "resume": conductor_state,
                      "backup": job_state(newest_job(items, "backup"))}, "last_sync": last_sync}


def pod_log(unit, limit_lines, namespace="score", run=subprocess.run):
    """A unit's log tail from the cluster in place of its journal: the newest Job's pod for a CronJob's unit
    (score-sync, score-backup), else the conductor pod's `conductor` container (units.py's log, every unit's lines);
    why not, when kubectl cannot read it."""
    name = unit.removesuffix(".service")
    target = ["pod/score-conductor-0", "-c", "conductor"]
    if name in ("score-sync", "score-backup"):
        listed = kubectl_json(namespace, "get", "jobs", "-l", "app.kubernetes.io/name=score-conductor") or {}
        job = newest_job(listed.get("items", []), name.removeprefix("score-"))
        if job is None:
            return ["log not read: no Job of it yet"]
        target = [f"job/{job['metadata']['name']}"]
    try:
        done = run(["kubectl", "-n", namespace, "logs", *target, f"--tail={limit_lines * 2}"], capture_output=True,
                   text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return [f"log not read: {error}"]
    if done.returncode:
        return [f"log not read: {done.stderr.strip()[:200]}"]
    return done.stdout.splitlines()
