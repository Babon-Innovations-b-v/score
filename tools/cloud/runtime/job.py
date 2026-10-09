"""The container entrypoint `score-job <run id> <job id>`: one unit of work, the same whether Kubernetes or a hand
with docker runs it. The store comes from SCORE_STORE_* (store.py); the job from runs/<run>/<job>/job.json:

    {"kind": "pixal", "image": "<registry>/score-pixal:<tag>@sha256:...", "code": "code/<sha256>.tar.gz",
     "inputs": [{"key": "...", "path": "/abs/path"}], "outputs": [{"path": "/abs/path", "key": "..."}],
     "command": ["..."], "env": {...}, "models": ["pixal3d"], "minutes": 30, "attempt_limit": 3,
     "tool_only": false}

A job whose done.json is in the store exits 0 at once, so a rerun after a node loss redoes only the unfinished jobs.
Otherwise it fetches the code into /work/repo, the models into the node cache (weights.py, from the kind's
models.json in the code), the inputs to their paths; runs the command in /work/repo with a timeout of `minutes`;
uploads the outputs (a folder output as one key per file under its key); and writes done.json last, with its
timings and where it ran. On a failure it writes failed-<attempt>.json with the stage and the log's tail and exits
non-zero, so Kubernetes retries it; past attempt_limit it refuses to run again. The log goes to stdout and to
log-<attempt>.txt.
"""
import datetime
import io
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import store as stores  # noqa: E402
import weights  # noqa: E402

WORK = pathlib.Path(os.environ.get("SCORE_WORK", "/work"))
TAIL_LINES = 80
ATTEMPT_LIMIT = 3
# What the job exits with when it has used up its attempts; Kubernetes may then stop retrying.
EXIT_NO_ATTEMPTS = 3


class Failure(Exception):
    """A step of the job failed; its stage says which."""

    def __init__(self, stage, why):
        super().__init__(f"{stage}: {why}")
        self.stage = stage


class Log:
    """The job's log: every line to stdout and into the attempt's log file."""

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.file = open(path, "a", buffering=1)

    def say(self, line):
        line = f"[score-job] {now()} {line}"
        print(line, flush=True)
        self.file.write(line + "\n")

    def raw(self, line):
        sys.stdout.write(line)
        sys.stdout.flush()
        self.file.write(line)

    def tail(self):
        self.file.flush()
        return self.path.read_text(errors="replace").splitlines()[-TAIL_LINES:]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def prefix(run, job):
    return f"runs/{run}/{job}/"


def attempt_number(store, run, job):
    """This attempt's number: one more than the failures the store holds."""
    return len([key for key in store.keys(prefix(run, job) + "failed-") if key.endswith(".json")]) + 1


def fetch_code(store, key, repo):
    """Unpack the job's code bundle into a fresh `repo` folder."""
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(store.read_bytes(key)), mode="r:gz") as archive:
        archive.extractall(repo, filter="data")


def fetch_inputs(store, inputs):
    for item in inputs:
        store.download(item["key"], item["path"])


def models_manifest(spec, repo):
    """The job's models.json: SCORE_MODELS, else the one of its kind's image folder in the code bundle."""
    path = pathlib.Path(os.environ.get("SCORE_MODELS") or repo / "tools/cloud/images" / spec["kind"] / "models.json")
    return weights.manifest(path) if path.exists() else {}


def fetch_models(store, spec, repo):
    """{SCORE_MODEL_<NAME>: folder} for the job's models, each in the node cache."""
    names = spec.get("models") or []
    if not names:
        return {}
    return weights.all_ready(store, names, models_manifest(spec, repo), spec.get("tool_only", False))


def stop_group(process):
    """Stop the command and everything it started."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_command(spec, environment, cwd, log):
    """Run the job's command, its output into the log; its exit code, or a Failure past its minutes."""
    minutes = spec.get("minutes", 60)
    process = subprocess.Popen(spec["command"], cwd=cwd, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True)
    expired = threading.Event()
    timer = threading.Timer(minutes * 60, lambda: (expired.set(), stop_group(process)))
    timer.start()
    try:
        for line in process.stdout:
            log.raw(line)
        process.wait()
    finally:
        timer.cancel()
    if expired.is_set():
        raise Failure("command", f"passed its {minutes} minutes")
    return process.returncode


def upload_outputs(store, outputs):
    """Upload every output, a folder as one key per file under its key; the keys uploaded."""
    uploaded = []
    for item in outputs:
        path = pathlib.Path(item["path"])
        if path.is_dir():
            for file in sorted(found for found in path.rglob("*") if found.is_file()):
                key = f"{item['key'].rstrip('/')}/{file.relative_to(path)}"
                store.upload(file, key)
                uploaded.append(key)
        elif path.is_file():
            store.upload(path, item["key"])
            uploaded.append(item["key"])
        else:
            raise FileNotFoundError(f"the command made no {path}")
    return uploaded


def card():
    """The node's card name and driver (nvidia-smi), or 'none' on a processor node."""
    try:
        answer = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "none"
    return answer.stdout.strip().splitlines()[0] if answer.returncode == 0 and answer.stdout.strip() else "none"


def command_environment(spec, run, job, attempt, models):
    """The command's environment: the container's, the job's env, its models' folders and its own names."""
    return {**os.environ, **spec.get("env", {}), **models,
            "SCORE_RUN": run, "SCORE_JOB": job, "SCORE_ATTEMPT": str(attempt)}


def work(store, run, job, attempt, spec, log, timings):
    """Every step of the job, its timings filled as it goes; the output keys uploaded."""
    repo = WORK / "repo"
    log.say(f"job {run}/{job} attempt {attempt}: {spec['kind']} on {socket.gethostname()}")
    try:
        if spec.get("code"):
            fetch_code(store, spec["code"], repo)
        else:
            repo.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        raise Failure("code", error) from error
    try:
        models = fetch_models(store, spec, repo)
    except (Exception, SystemExit) as error:
        raise Failure("models", error) from error
    timings["weights_ready"] = now()
    log.say(f"models ready: {', '.join(spec.get('models') or []) or 'none'}")
    try:
        fetch_inputs(store, spec.get("inputs") or [])
    except Exception as error:
        raise Failure("inputs", error) from error
    timings["inputs_ready"] = now()
    returncode = run_command(spec, command_environment(spec, run, job, attempt, models), repo, log)
    timings["first_result"] = now()
    if returncode:
        raise Failure("command", f"exited with {returncode}")
    try:
        uploaded = upload_outputs(store, spec.get("outputs") or [])
    except Exception as error:
        raise Failure("outputs", error) from error
    timings["uploaded"] = now()
    return uploaded


def where(spec):
    """Where the job ran: the node, the card, the image."""
    return {"node": os.environ.get("SCORE_NODE") or socket.gethostname(), "card": card(),
            "image": os.environ.get("SCORE_IMAGE") or spec.get("image")}


def run_job(store, run, job):
    """Run one job from the store; the process's exit code."""
    base = prefix(run, job)
    if store.exists(base + "done.json"):
        print(f"[score-job] {run}/{job} is done already", flush=True)
        return 0
    timings = {"pod_start": now()}
    attempt = attempt_number(store, run, job)
    spec = stores.read_json(store, base + "job.json")
    if attempt > spec.get("attempt_limit", ATTEMPT_LIMIT):
        print(f"[score-job] {run}/{job} failed {attempt - 1} times, its limit; not run again", flush=True)
        return EXIT_NO_ATTEMPTS
    log = Log(WORK / "logs" / f"log-{attempt}.txt")
    try:
        uploaded = work(store, run, job, attempt, spec, log, timings)
    except Failure as failure:
        log.say(f"failed at {failure}")
        stores.write_json(store, base + f"failed-{attempt}.json",
                          {"attempt": attempt, "stage": failure.stage, "error": str(failure), "timings": timings,
                           **where(spec), "log_tail": log.tail()})
        store.upload(log.path, base + f"log-{attempt}.txt")
        return 1
    log.say(f"done: {len(uploaded)} output files")
    store.upload(log.path, base + f"log-{attempt}.txt")
    stores.write_json(store, base + "done.json", {"attempt": attempt, "timings": timings, **where(spec),
                                                  "outputs": uploaded})
    return 0


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if len(arguments) != 2:
        raise SystemExit("usage: score-job <run id> <job id>")
    return run_job(stores.from_environment(), *arguments)


if __name__ == "__main__":
    sys.exit(main())
