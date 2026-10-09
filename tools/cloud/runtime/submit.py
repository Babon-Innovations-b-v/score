"""The submit side of a job (job.py runs it): what a runner on the coordinating machine calls to put a job in the
store and read its result back. Kubernetes or a hand with docker then runs `score-job <run> <job>` on it.

    import submit
    store = submit.cloud_store()                                   # the provider's object_store(), opened
    code = submit.upload_code(store, ["tools/props/cloud", "data/x"], kind="blender")
    spec = {"kind": "blender", "image": submit.image("blender"), "code": code,
            "inputs": [submit.upload_input(store, run, job, "/local/in.json")],
            "outputs": [{"path": "/work/out", "key": submit.output_key(run, job, "out")}],
            "command": ["/opt/blender/blender", "-b", ...], "models": [], "minutes": 20}
    submit.write_job(store, run, job, spec)
    ...
    submit.state(store, run, job)            # "done", "failed" (attempts used up), or "waiting"
    submit.fetch_outputs(store, run, job, {"/work/out": "/local/out"})

The code bundle is content addressed (code/<sha256 of the bundle>.tar.gz) and made the same way from the same files,
so one tree uploads once however many jobs use it; the kind's models.json goes in with it, where job.py reads it.
"""
import gzip
import hashlib
import io
import json
import pathlib
import sys
import tarfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import job as jobs  # noqa: E402
import store as stores  # noqa: E402
import weights  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
IMAGES = REPO / "tools/cloud/images/images.json"
SKIPPED = {".git", "__pycache__", ".pytest_cache"}


def cloud_store():
    """The provider's object store (tools/props/cloud/provider.py object_store()), opened."""
    return stores.open_store(provider_cloud().object_store())


def provider_cloud():
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    sys.path.insert(0, str(REPO / "tools/props"))
    from provider import cloud

    return cloud


def bundled_files(paths, repo):
    """Every file under the repo paths, repo-relative and sorted, without caches and git folders."""
    found = set()
    for name in paths:
        path = repo / name
        if not path.exists():
            raise SystemExit(f"{name} is not in the repo")
        candidates = [path] if path.is_file() else path.rglob("*")
        found |= {candidate.relative_to(repo) for candidate in candidates
                  if candidate.is_file() and not SKIPPED & set(candidate.relative_to(repo).parts)}
    return sorted(found)


def bundle(paths, repo=REPO):
    """A gzipped tar of the repo paths, the same bytes for the same files (fixed order, owners and times)."""
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name in bundled_files(paths, repo):
                weights.add_fixed(archive, repo / name, str(name))
    return raw.getvalue()


def upload_code(store, paths, kind=None, repo=REPO):
    """Upload the bundle of the repo paths (with the kind's models.json) once; its key, code/<sha256>.tar.gz."""
    manifest = pathlib.Path("tools/cloud/images") / str(kind) / "models.json"
    data = bundle([*paths, *([manifest] if kind and (repo / manifest).exists() else [])], repo)
    key = f"code/{hashlib.sha256(data).hexdigest()}.tar.gz"
    if not store.exists(key):
        store.write_bytes(key, data)
    return key


def upload_input(store, run, job, local, path=None):
    """Upload one input file; the job's input entry, at `path` up there (the same absolute path by default)."""
    local = pathlib.Path(local).resolve()
    key = f"{jobs.prefix(run, job)}in/{local.name}"
    store.upload(local, key)
    return {"key": key, "path": str(path or local)}


def output_key(run, job, name):
    return f"{jobs.prefix(run, job)}out/{name}"


def write_job(store, run, job, spec):
    """Put the job's job.json in the store; its key."""
    missing = {"kind", "image", "command"} - set(spec)
    if missing:
        raise SystemExit(f"the job lacks {', '.join(sorted(missing))}")
    key = jobs.prefix(run, job) + "job.json"
    stores.write_json(store, key, spec)
    return key


def state(store, run, job):
    """'done' once done.json is in, 'failed' once its attempts are used up, else 'waiting'."""
    base = jobs.prefix(run, job)
    if store.exists(base + "done.json"):
        return "done"
    limit = stores.read_json(store, base + "job.json").get("attempt_limit", jobs.ATTEMPT_LIMIT)
    return "failed" if jobs.attempt_number(store, run, job) > limit else "waiting"


def done(store, run, job):
    """The job's done.json: its timings, where it ran, its output keys."""
    return stores.read_json(store, jobs.prefix(run, job) + "done.json")


def failures(store, run, job):
    """Every failed-<attempt>.json of the job, oldest first."""
    return [stores.read_json(store, key) for key in store.keys(jobs.prefix(run, job) + "failed-")
            if key.endswith(".json")]


def fetch_outputs(store, run, job, destinations):
    """Download a done job's outputs: {path up there: local path}, a folder output's files under its local folder."""
    spec = stores.read_json(store, jobs.prefix(run, job) + "job.json")
    uploaded = done(store, run, job)["outputs"]
    for item in spec.get("outputs") or []:
        if item["path"] not in destinations:
            continue
        local = pathlib.Path(destinations[item["path"]])
        for key in uploaded:
            if key == item["key"]:
                store.download(key, local)
            elif key.startswith(item["key"].rstrip("/") + "/"):
                store.download(key, local / key[len(item["key"].rstrip("/")) + 1:])


def image(kind):
    """The pinned image of a job kind from images.json: <registry>/score-<kind>:<tag>@<digest>."""
    built = json.loads(IMAGES.read_text()) if IMAGES.exists() else {}
    if kind not in built:
        raise SystemExit(f"no image of {kind} is built yet (tools/cloud/images/build.py {kind})")
    return built[kind]["image"]
