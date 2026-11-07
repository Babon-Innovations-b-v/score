"""The conductor in the cluster (#76, the plan of 2026-11-07, step 2): what a home on the cluster does
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
"""
import json
import pathlib
import re
import subprocess
import sys
import time

from score import conductor

RECORD = conductor.HOME / "cluster.json"
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
    job = drive_job(found, command, log, folder, environment, int(found["max_memory_gb"] * GIB))
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
