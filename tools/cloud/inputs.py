"""Job inputs through the object store: each input folder or file goes up from this PC once, as a tar named for the
sha256 of its bytes (`inputs/<sha256>.tar` in the provider's object_store()), and every machine that needs it pulls it
from the bucket inside the datacenter (input_fetch.py). Before this, every machine got its inputs straight from this
PC over a ~3 MB/s link: on 2026-10-10 two review-page machines waited about 2 hours while ten agents sent at once,
and the same 438 MB of a place's parts went to several machines.

    fetched = inputs.through_store(log_folder, host, job["inputs"])   # the paths now on the machine
    ...send the rest directly (rsync), as before

- An input under SMALLEST bytes goes directly: a job file is cheaper sent than staged.
- The tar is made the same way from the same files (fixed order, owners and times), so the same input gives the same
  key from any run or session, and one already in the bucket is not sent again. A file lock per key makes a second
  session that stages the same input wait for the first one's upload instead of sending it twice.
- Hashing a big folder costs a read of it; its key is kept against its files' names, sizes and times (rsync's own
  quick check) under WORK/cloud/inputs, so an unchanged input is not read again.
- The machine gets a signed link that can only read that one object for URL_HOURS, never the store's key.
- Staging runs in the repo's environment (paths.VENV_PYTHON, which has boto3), as the cluster path does; any failure
  there or on the machine leaves the input to the direct path. SCORE_INPUTS_DIRECT=1 sends everything directly.

    <repo python> tools/cloud/inputs.py stage /abs/folder [...]   # JSON list: path, key, url, bytes, uploaded
"""
import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tarfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "props"))
sys.path.insert(0, str(HERE.parents[1] / "tools/cloud/runtime"))

from paths import VENV_PYTHON, WORK  # noqa: E402

SMALLEST = 8 * 1024 * 1024
URL_HOURS = 6
PREFIX = "inputs/"
FOLDER = WORK / "cloud" / "inputs"
REMOTE_SCRIPT = "/root/lib/input_fetch.py"
MACHINE_CACHE = "/root/inputs"
DIRECT = "SCORE_INPUTS_DIRECT"


def entries(local):
    """Every file, folder and link of an input, as (path, name in the tar), sorted by name; the input itself first."""
    local = pathlib.Path(local)
    found = [(local, local.name)]
    if local.is_dir() and not local.is_symlink():
        found += [(path, str(pathlib.PurePosixPath(local.name, path.relative_to(local).as_posix())))
                  for path in local.rglob("*")]
    return sorted(found, key=lambda entry: entry[1])


def size_of(local):
    return sum(path.lstat().st_size for path, _ in entries(local) if path.is_file() and not path.is_symlink())


def quick_signature(local):
    """The input's path, and its files' names, sizes and modification times, hashed."""
    listed = [(name, path.lstat().st_size, path.lstat().st_mtime_ns) for path, name in entries(local)]
    return hashlib.sha256(json.dumps([str(pathlib.Path(local).resolve()), listed]).encode()).hexdigest()


def add_fixed(archive, path, name):
    """One entry with fixed owners and time, so the same files give the same bytes."""
    info = archive.gettarinfo(path, name)
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    if info.isreg():
        with open(path, "rb") as source:
            archive.addfile(info, source)
    else:
        archive.addfile(info)


def write_tar(local, target):
    """The input as a plain tar streamed into `target`, anything with a binary write()."""
    with tarfile.open(fileobj=target, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        for path, name in entries(local):
            add_fixed(archive, path, name)


class Hasher:
    """A write-only file that keeps the sha256 of what is written to it, passing it on to `target` when one is given."""

    def __init__(self, target=None):
        self.digest = hashlib.sha256()
        self.target = target

    def write(self, data):
        self.digest.update(data)
        if self.target is not None:
            self.target.write(data)
        return len(data)


def content_key(local):
    """The input's store key, inputs/<sha256 of its tar>.tar; read from the quick-check memo when its files are
    unchanged."""
    memo = FOLDER / "memo" / quick_signature(local)
    if memo.exists():
        return memo.read_text().strip()
    hasher = Hasher()
    write_tar(local, hasher)
    key = f"{PREFIX}{hasher.digest.hexdigest()}.tar"
    memo.parent.mkdir(parents=True, exist_ok=True)
    memo.write_text(key)
    return key


@contextlib.contextmanager
def held(key):
    """The key's lock on this PC, so two sessions staging the same input send it once."""
    FOLDER.mkdir(parents=True, exist_ok=True)
    with open(FOLDER / (key.rsplit("/", 1)[-1] + ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def uploaded(store, local, key):
    """The input's tar into the store under `key` unless it is there; whether it was sent now. A tar whose bytes no
    longer hash to `key` (the files changed, or the quick-check memo is stale) is refused, never stored under it."""
    with held(key):
        if store.exists(key):
            return False
        partial = FOLDER / f"{key.rsplit('/', 1)[-1]}.{os.getpid()}.partial"
        try:
            with open(partial, "wb") as target:
                written = Hasher(target)
                write_tar(local, written)
            if f"{PREFIX}{written.digest.hexdigest()}.tar" != key:
                raise ValueError(f"{local} changed since its key {key} was taken; not uploaded")
            store.upload(partial, key)
        finally:
            partial.unlink(missing_ok=True)
        return True


def signed_link(store, key):
    """A link that reads the one object for URL_HOURS; a folder store's own path in the tests."""
    if hasattr(store, "client"):
        return store.client.generate_presigned_url("get_object", Params={"Bucket": store.bucket, "Key": key},
                                                   ExpiresIn=URL_HOURS * 3600)
    return f"file://{store.path(key)}"


def staged(store, local):
    """One input in the store: its path, key, signed link, size and whether it was sent now."""
    local = pathlib.Path(local).resolve()
    began = time.time()
    key = content_key(local)
    sent = uploaded(store, local, key)
    return {"path": str(local), "key": key, "url": signed_link(store, key), "bytes": size_of(local),
            "uploaded": sent, "seconds": round(time.time() - began, 1)}


def big_inputs(locals_):
    """The inputs worth staging: those that exist and hold at least SMALLEST bytes."""
    found = [pathlib.Path(local).resolve() for local in locals_]
    return [local for local in found if local.exists() and size_of(local) >= SMALLEST]


def stage(log_folder, locals_):
    """The big inputs staged in the store by the repo's environment; [] (all sent directly) when that fails."""
    big = big_inputs(locals_)
    if not big or os.environ.get(DIRECT):
        return []
    done = subprocess.run([str(VENV_PYTHON), str(HERE / "inputs.py"), "stage", *map(str, big)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        (pathlib.Path(log_folder) / "inputs-stage.log").write_text(done.stdout + done.stderr)
        say(f"inputs: staging in the store failed, sending directly ({log_folder}/inputs-stage.log)")
        return []
    return json.loads(done.stdout.strip().splitlines()[-1])


def say(line):
    """A line in the runner's own progress format (batch.say)."""
    print(f"[cloud] {time.strftime('%H:%M:%S')} {line}", file=sys.stderr, flush=True)


def fetch(log_folder, host, items):
    """The staged inputs pulled from the store by the machine; the paths it reports done."""
    import batch

    request = json.dumps({"cache": MACHINE_CACHE, "items": [
        {field: item[field] for field in ("path", "key", "url")} for item in items]})
    with open(pathlib.Path(log_folder) / "inputs-fetch.log", "a") as log:
        try:
            batch.copy(log_folder, [HERE / "input_fetch.py"], f"root@{host}:{REMOTE_SCRIPT}")
        except subprocess.CalledProcessError as failed:
            log.write(f"sending the fetch script failed: {failed}\n")
            return set()
        done = batch.remote(log_folder, host, f"python3 {REMOTE_SCRIPT}", input=request, capture_output=True,
                            text=True)
        log.write(done.stdout + done.stderr)
    reported = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
    if done.returncode != 0:
        say(f"inputs: the machine's fetch failed after {len(reported)} of {len(items)}, sending the rest directly")
    return {entry["path"] for entry in reported}


def named_links(locals_):
    """{where a link lies on the machine: what it resolves to} for each link on the way to an input as the job names
    it, top down: an input lands at its resolved path (staged and sent alike), so every link of its named path is
    made up there too, and every other path the job names through the same links (its outputs, a file beside its
    listing) is the same place on the machine as here. A folder link made as a folder of file links wrote a job's
    outputs into a second folder up there that nothing brought back (surfaces-bake@campgrounds, 2026-10-27: its
    making folder named through the frozen run's home, `<copy>.home/store` a link to the store)."""
    found = {}
    for local in locals_:
        parts = pathlib.PurePath(os.path.abspath(local)).parts
        for end in range(2, len(parts) + 1):
            named = os.path.join(*parts[:end])
            if os.path.islink(named):
                at = os.path.join(os.path.realpath(os.path.dirname(named)), parts[end - 1])
                target = os.path.realpath(named)
                if at != target:
                    found[at] = target
    return found


def link_named(log_folder, host, locals_):
    """Each link on the way to the job's paths made on the machine (named_links), so a path the job names reaches
    what it reaches here (garage's rover, named work/pixal/kit5-rover-3.glb, lands at work/pixal5/: Blender's import
    found no file there, 2026-10-12). One already right is left alone; a folder up there where a link lies here holds
    only what a job wrote there through the old file links, and is replaced."""
    import batch

    links = named_links(locals_)
    if links:
        batch.remote(log_folder, host, " && ".join(
            f"mkdir -p {shlex.quote(os.path.dirname(at))} && {{ [ \"$(readlink -f {shlex.quote(at)})\" = "
            f"{shlex.quote(target)} ] || {{ {{ [ -L {shlex.quote(at)} ] || rm -rf {shlex.quote(at)}; }} && "
            f"ln -sfnT {shlex.quote(target)} {shlex.quote(at)}; }}; }}"
            for at, target in links.items()), check=True)


def through_store(log_folder, host, locals_):
    """The job's inputs reachable on the machine at the paths the job names (link_named), its big ones sent through
    the store; the resolved paths that arrived that way. Nothing here stops a job: what does not arrive is sent
    directly, and why is said."""
    link_named(log_folder, host, locals_)
    try:
        items = stage(log_folder, locals_)
    except (OSError, ValueError, IndexError) as failed:
        say(f"inputs: staging in the store failed ({failed}), sending directly")
        return set()
    if not items:
        return set()
    began = time.time()
    arrived = fetch(log_folder, host, items)
    sent = sum(item["bytes"] for item in items if item["uploaded"])
    say(f"inputs: {len(arrived)} of {len(items)} from the store in {time.time() - began:.0f} s on the machine "
        f"({sum(item['bytes'] for item in items) / 1e6:.0f} MB; {sent / 1e6:.0f} MB uploaded now, staging "
        f"{sum(item['seconds'] for item in items):.0f} s)")
    return arrived


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "stage":
        raise SystemExit(__doc__.rsplit("\n\n", 1)[-1])
    import submit

    store = submit.cloud_store()
    print(json.dumps([staged(store, local) for local in sys.argv[2:]]))


if __name__ == "__main__":
    main()
