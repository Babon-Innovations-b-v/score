"""The node's weights cache: each model a job names is fetched once per node into the cache volume, under a file
lock so that jobs side by side on one node fetch it once, from the store's `weights/<name>@<revision>.tar`, checked
against its sha256. A model the store lacks is seeded once from its source at the pinned revision and uploaded, so
every later node takes it from the store. No weights are ever in an image.

A model is described in its image folder's models.json (tools/cloud/images/<kind>/models.json), a list of

    {"name": "pixal3d", "source": "hf:<repo>" or "url:<https url>", "revision": "<commit sha or tag>",
     "files": ["glob", ...], "sha256": "<of the tar in the store>", "licence": "...", "licence_url": "...",
     "commercial_use": true, "note": "..."}

`files` (optional) narrows an hf: repo to the files that match one of its globs. `sha256` is filled once the model
is seeded (the seeding prints it and keeps it beside the tar as `<tar>.sha256` meanwhile). A model whose
commercial_use is false is refused unless the job says its output is a tool's, never shipped (job.json `tool_only`).

On the node the model lands in <cache>/weights/<name>@<revision>/, the job's command sees it as SCORE_MODEL_<NAME>
(the name in capitals, other characters as _).
"""
import fcntl
import fnmatch
import hashlib
import json
import os
import pathlib
import shutil
import tarfile
import time
import urllib.parse
import urllib.request

CACHE = pathlib.Path(os.environ.get("SCORE_CACHE", "/cache"))
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
CHUNK = 1 << 22
READY = ".ready"


def manifest(path):
    """{name: entry} of a models.json."""
    return {entry["name"]: entry for entry in json.loads(pathlib.Path(path).read_text())}


def refusal(entry, tool_only):
    """Why a job may not use the model, or None: a model not for commercial use only serves a tool's output."""
    if entry.get("commercial_use") is False and not tool_only:
        return (f"{entry['name']} is not for commercial use ({entry.get('licence')}); only a job marked tool_only, "
                "whose output is never shipped, may use it")
    return None


def tar_key(entry):
    return f"weights/{entry['name']}@{entry['revision']}.tar"


def environment_name(name):
    """The variable that hands the command a model's folder: SCORE_MODEL_ and the name in capitals."""
    return "SCORE_MODEL_" + "".join(letter if letter.isalnum() else "_" for letter in name).upper()


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ready(store, entry, cache=CACHE):
    """The model's folder in the node cache, fetched (or seeded) first if this node lacks it; the fetch runs once
    per node, whichever job asks first, the others waiting on its lock."""
    folder = cache / "weights" / f"{entry['name']}@{entry['revision']}"
    (cache / "locks").mkdir(parents=True, exist_ok=True)
    with open(cache / "locks" / f"{folder.name}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (folder / READY).exists():
            return folder
        work = cache / "partial" / f"{folder.name}-{os.getpid()}-{time.time_ns()}"
        work.mkdir(parents=True)
        try:
            tar = fetched(store, entry, work)
            unpack(tar, folder, work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return folder


def fetched(store, entry, work):
    """The model's tar in `work`, from the store, else seeded from its source; checked against its sha256."""
    key = tar_key(entry)
    tar = work / "model.tar"
    if store.exists(key):
        store.download(key, tar)
    else:
        seed(store, entry, work, tar)
    expected = entry.get("sha256") or store.read_bytes(key + ".sha256").decode().strip()
    found = sha256_of(tar)
    if found != expected:
        raise RuntimeError(f"{key}: sha256 {found} is not the expected {expected}")
    return tar


def unpack(tar, folder, work):
    """Unpack the tar into the model's folder whole: into a scratch folder first, renamed into place, marked ready."""
    scratch = work / "unpacked"
    with tarfile.open(tar) as archive:
        archive.extractall(scratch, filter="data")
    tar.unlink()
    if folder.exists():
        shutil.rmtree(folder)
    folder.parent.mkdir(parents=True, exist_ok=True)
    scratch.replace(folder)
    (folder / READY).touch()


def seed(store, entry, work, tar):
    """Fetch the model from its source at its pinned revision, pack it into `tar` and upload it with its sha256, so
    no later node goes to the source."""
    files = work / "source"
    kind, _, where = entry["source"].partition(":")
    if kind == "hf":
        for name in hf_files(where, entry["revision"], entry.get("files")):
            download(hf_url(where, entry["revision"], name), files / name, hf_token())
    elif kind == "url":
        download(where, files / pathlib.PurePosixPath(urllib.parse.urlparse(where).path).name)
    else:
        raise SystemExit(f"{entry['name']}: unknown source {entry['source']!r} (hf:<repo> or url:<url>)")
    pack(files, tar)
    shutil.rmtree(files)
    digest = sha256_of(tar)
    if entry.get("sha256") and digest != entry["sha256"]:
        raise RuntimeError(f"{entry['source']}@{entry['revision']} packs to sha256 {digest}, not the expected "
                           f"{entry['sha256']}; nothing uploaded")
    store.upload(tar, tar_key(entry))
    store.write_bytes(tar_key(entry) + ".sha256", digest.encode())
    print(f"[weights] seeded {tar_key(entry)}: sha256 {digest} (fill it into models.json)", flush=True)


def pack(folder, tar):
    """Pack a folder's files into an uncompressed tar, in name order with fixed owners and times, so one source
    always gives one sha256."""
    with tarfile.open(tar, "w", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(folder.rglob("*")):
            info = archive.gettarinfo(path, str(path.relative_to(folder)))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_file():
                with open(path, "rb") as source:
                    archive.addfile(info, source)
            else:
                archive.addfile(info)


def hf_token():
    return os.environ.get("HF_TOKEN") or os.environ.get("SCORE_SECRET_HF_READ_TOKEN")


def hf_url(repo, revision, name):
    return f"{HF_ENDPOINT}/{repo}/resolve/{revision}/{urllib.parse.quote(name)}"


def hf_files(repo, revision, patterns=None):
    """The files of a Hugging Face model repo at `revision`, narrowed to those matching one of `patterns`."""
    request = authorised(f"{HF_ENDPOINT}/api/models/{repo}/revision/{revision}", hf_token())
    with urllib.request.urlopen(request, timeout=60) as answer:
        names = [sibling["rfilename"] for sibling in json.load(answer)["siblings"]]
    return [name for name in names if not patterns or any(fnmatch.fnmatch(name, pattern) for pattern in patterns)]


def authorised(url, token):
    """A request for `url` carrying the token to its own host only: a redirect to a download host (a signed link)
    goes without it."""
    request = urllib.request.Request(url)
    if token:
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    return request


def download(url, destination, token=None):
    """Download one file to `destination`."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(authorised(url, token), timeout=300) as answer, open(destination, "wb") as written:
        shutil.copyfileobj(answer, written, CHUNK)


def all_ready(store, names, models, tool_only, cache=CACHE):
    """{environment variable: folder} for every model a job names, each refused, fetched or taken from the cache."""
    folders = {}
    for name in names:
        if name not in models:
            raise SystemExit(f"the job names the model {name}, which its image's models.json does not list")
        refused = refusal(models[name], tool_only)
        if refused:
            raise SystemExit(refused)
        folders[environment_name(name)] = str(ready(store, models[name], cache))
    return folders
