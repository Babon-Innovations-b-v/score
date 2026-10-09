"""Build the job images and push them to the provider's registry, on a rented processor machine (never on this PC:
its upload is about 3 MB/s), then delete the machine.

    .venv/bin/python tools/cloud/images/build.py base [blender ...] --who "<session>" [--force] [--smoke] [--dry-run]
    .venv/bin/python tools/cloud/images/build.py --all --who "<session>"

Each image folder here (`<kind>/`) holds its Dockerfile, models.json and the small files it copies. An image is built
with docker buildx from a context of its folder plus the job runtime (`runtime/`), for the platforms its Dockerfile
names on a `# platforms:` line (linux/amd64 when it names none; arm64 runs under QEMU on the builder), with the
registry as the layer cache, so rebuilding one image reuses every layer that did not change. A Dockerfile that
declares `ARG BASE` is built FROM the score-base image of this run or of images.json. The tag is
`<IMAGE_VERSION>-<hash of the folder (models.json aside: no weights are in an image), the runtime and the parent's
digest>`; an image whose tag images.json already holds is not built again unless --force.

images.json then holds, for each kind: the image reference pinned by digest (what job.json names), its tag and
digest, platforms, compressed size, the build's minutes and when it was built. --smoke runs a job of the runtime in
each freshly pulled image on the builder (plain docker, a fresh cache, then a second fresh cache that takes the
weights from the store, then the warm cache) and records the cold-start numbers in images.json under "smoke".

The machine is rented through batch.py's claim (the owner's limits, its watchdog, the self-delete, the ledger row and
the delete), from the processor classes in PROCESSORS, best stocked first.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNTIME = REPO / "tools/cloud/runtime"
sys.path.insert(0, str(REPO / "tools/props/cloud"))
sys.path.insert(0, str(REPO / "tools/props"))
sys.path.insert(0, str(RUNTIME))

import batch  # noqa: E402
import ledger  # noqa: E402
import spread  # noqa: E402
import store as stores  # noqa: E402
import submit  # noqa: E402
from provider import cloud  # noqa: E402

IMAGES_JSON = HERE / "images.json"
# Raised by hand when an image's meaning changes without its files changing (a new registry, a new layout).
IMAGE_VERSION = "1"
KIND = "images"
# The builder: a processor machine; the first in stock is taken.
PROCESSORS = ("cpu-16c-64gb", "cpu-32c-64gb", "cpu-32c-128gb")
DISK_GB = 200
SETUP_MINUTES = 5
# A first build of one image without a warm cache, the estimate the limits are checked against.
MINUTES_EACH = 25
REMOTE = pathlib.PurePosixPath("/root/build")
PARENT = "base"
BUILDER_SETUP = """set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io docker-buildx qemu-user-static binfmt-support >/dev/null
systemctl start docker
docker buildx create --name score --driver docker-container --use --bootstrap >/dev/null
docker buildx inspect score | grep -i platforms
"""
# The smoke job's model: small, Apache-2.0, pinned; enough to see the weights cache move real bytes.
SMOKE_MODELS = [{"name": "minilm", "source": "hf:sentence-transformers/all-MiniLM-L6-v2",
                 "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41", "files": ["*.json", "model.safetensors"],
                 "sha256": "d595ea736979025418d9b1521e1f45a8c51819b16941587709510cbc509b93cb",
                 "licence": "Apache-2.0", "commercial_use": True,
                 "licence_url": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
                 "note": "the image builder's smoke job only"}]
SMOKE_SCRIPT = ("import os, pathlib, sys; model = pathlib.Path(os.environ['SCORE_MODEL_MINILM']); "
                "size = (model / 'model.safetensors').stat().st_size; "
                "out = pathlib.Path('/work/out.txt'); out.write_text(f'{size} ' + pathlib.Path('/work/in.txt').read_text()); "
                "print('smoke ok', size)")


def image_kinds():
    """Every image folder with a Dockerfile, the parent first."""
    kinds = sorted(path.parent.name for path in HERE.glob("*/Dockerfile"))
    return sorted(kinds, key=lambda kind: kind != PARENT)


def dockerfile(kind):
    return (HERE / kind / "Dockerfile").read_text()


def platforms(kind):
    """The platforms the Dockerfile names on its `# platforms:` line, else linux/amd64."""
    for line in dockerfile(kind).splitlines():
        if line.startswith("# platforms:"):
            return line.split(":", 1)[1].strip()
    return "linux/amd64"


def has_parent(kind):
    return kind != PARENT and "ARG BASE" in dockerfile(kind)


def context_files(kind):
    """The build context: {path in the context: file here}, the image folder's files and the runtime's (tests and
    caches aside)."""
    files = {str(path.relative_to(HERE / kind)): path for path in (HERE / kind).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts}
    files.update({f"runtime/{path.name}": path for path in RUNTIME.glob("*.py") if not path.name.endswith("_test.py")})
    return dict(sorted(files.items()))


def tag(kind, built):
    """The image's tag: IMAGE_VERSION and a hash of its context (models.json aside) and its parent's digest."""
    digest = hashlib.sha256()
    for name, path in context_files(kind).items():
        if name != "models.json":
            digest.update(name.encode() + b"\0" + oct(path.stat().st_mode & 0o777).encode() + path.read_bytes() + b"\0")
    if has_parent(kind):
        digest.update(built[PARENT]["digest"].encode())
    return f"{IMAGE_VERSION}-{digest.hexdigest()[:12]}"


def stale(kinds, built, force):
    """The kinds to build: asked for and not built at their tag, or whose parent is being built."""
    chosen = []
    for kind in image_kinds():
        if kind not in kinds:
            continue
        parent_new = has_parent(kind) and (PARENT in chosen or PARENT not in built)
        if force or parent_new or built.get(kind, {}).get("tag") != tag(kind, built):
            chosen.append(kind)
    return chosen


def saved():
    return json.loads(IMAGES_JSON.read_text()) if IMAGES_JSON.exists() else {}


def save(built):
    IMAGES_JSON.write_text(json.dumps(dict(sorted(built.items())), indent=1) + "\n")


def set_up(machine, registry):
    """Docker, buildx with a builder of its own, QEMU for arm64, and the registry login."""
    folder, host = machine["folder"], machine["host"]
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, BUILDER_SETUP, check=True, stdout=log, stderr=subprocess.STDOUT)
    log_in(machine, registry)


def log_in(machine, registry):
    """Log the machine's docker into the registry, its password over ssh's input, never on a command line."""
    host_name = registry["endpoint"].split("/")[0]
    batch.remote(machine["folder"], machine["host"],
                 f"docker login {host_name} -u {shlex.quote(registry['username'])} --password-stdin",
                 input=registry["password"], text=True, check=True, capture_output=True)


def send_store_environment(machine, store_spec):
    """The store's SCORE_STORE_* variables into /root/smoke/store.env on the machine (only root may read it), for
    `docker run --env-file`."""
    environment = "".join(f"{name}={value}\n" for name, value in stores.environment(store_spec).items())
    batch.remote(machine["folder"], machine["host"], "umask 077; mkdir -p /root/smoke; cat > /root/smoke/store.env",
                 input=environment, text=True, check=True)


def staged_context(kind, folder):
    """The kind's build context copied into a new folder under `folder`, each file with its mode (a script the
    Dockerfile copies stays executable); the folder."""
    staged = pathlib.Path(tempfile.mkdtemp(prefix=f"context-{kind}-", dir=folder))
    for name, path in context_files(kind).items():
        (staged / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, staged / name)
    return staged


def send_context(machine, kind):
    """The kind's build context onto the builder, in REMOTE/<kind>."""
    folder, host = machine["folder"], machine["host"]
    staged = staged_context(kind, folder)
    batch.remote(folder, host, f"rm -rf {REMOTE / kind}; mkdir -p {REMOTE}", check=True)
    batch.copy(folder, [f"{staged}/"], f"root@{host}:{REMOTE / kind}/")


def build_command(kind, reference, cache, parent):
    """The buildx command that builds the kind and pushes it with its layer cache."""
    command = ["docker", "buildx", "build", "--platform", platforms(kind), "-t", reference, "--push",
               "--provenance=false", "--cache-from", f"type=registry,ref={cache}",
               "--cache-to", f"type=registry,ref={cache},mode=max,image-manifest=true,oci-mediatypes=true",
               "--metadata-file", str(REMOTE / f"{kind}.meta.json")]
    if parent:
        command += ["--build-arg", f"BASE={parent}"]
    return command + [str(REMOTE / kind)]


def compressed_mb(machine, reference):
    """The amd64 image's compressed size in MB, from the registry's manifests."""
    folder, host = machine["folder"], machine["host"]

    def raw(name):
        answer = batch.remote(folder, host, f"docker buildx imagetools inspect --raw {shlex.quote(name)}",
                              check=True, capture_output=True, text=True)
        return json.loads(answer.stdout)

    manifest = raw(reference)
    if "manifests" in manifest:
        chosen = next(item for item in manifest["manifests"] if item.get("platform", {}).get("architecture") == "amd64")
        manifest = raw(f"{reference.rsplit(':', 1)[0]}@{chosen['digest']}")
    return round(sum(layer["size"] for layer in manifest["layers"]) / 1e6, 1)


def build_one(machine, kind, registry, built):
    """Build and push one image; its images.json entry (also written into `built`)."""
    folder, host = machine["folder"], machine["host"]
    name = f"{registry['endpoint']}/score-{kind}"
    reference = f"{name}:{tag(kind, built)}"
    send_context(machine, kind)
    began = time.time()
    command = build_command(kind, reference, f"{name}:buildcache", built[PARENT]["image"] if has_parent(kind) else None)
    with (folder / f"build-{kind}.log").open("w") as log:
        done = batch.remote(folder, host, shlex.join(command), stdout=log, stderr=subprocess.STDOUT)
    spread.raise_for(done.returncode, f"the {kind} build ({folder / f'build-{kind}.log'})")
    minutes = (time.time() - began) / 60
    answer = batch.remote(folder, host, f"cat {REMOTE / f'{kind}.meta.json'}", check=True, capture_output=True,
                          text=True)
    digest = json.loads(answer.stdout)["containerimage.digest"]
    entry = {"image": f"{reference}@{digest}", "tag": reference.rsplit(":", 1)[1], "digest": digest,
             "platforms": platforms(kind), "size_mb": compressed_mb(machine, reference),
             "build_minutes": round(minutes, 1),
             "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    built[kind] = {**built.get(kind, {}), **entry}  # what other tools measured of the kind (warm.py) stays
    save(built)
    batch.say(f"{kind}: pushed {entry['image']} ({entry['size_mb']} MB) in {minutes:.1f} min")
    return built[kind]


def seconds_between(timings, first, last):
    def parse(value):
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    return round(parse(timings[last]) - parse(timings[first]), 1)


def remote_seconds(machine, command):
    """Run a command on the builder; the seconds it took (it must succeed)."""
    folder, host = machine["folder"], machine["host"]
    began = time.time()
    with (folder / "smoke.log").open("a") as log:
        log.write(f"$ {command}\n")
        log.flush()
        batch.remote(folder, host, command, check=True, stdout=log, stderr=subprocess.STDOUT)
    return round(time.time() - began, 1)


def smoke_job(store, run, job, kind, entry):
    """One smoke job in the store: the runtime's code, a small input, the smoke model, an output."""
    local = pathlib.Path(tempfile.mkdtemp()) / "in.txt"
    local.write_text(f"{kind} {job}")
    spec = {"kind": kind, "image": entry["image"], "code": submit.upload_code(store, ["tools/cloud/runtime"]),
            "inputs": [submit.upload_input(store, run, job, local, "/work/in.txt")],
            "outputs": [{"path": "/work/out.txt", "key": submit.output_key(run, job, "out.txt")}],
            "command": ["/opt/score/venv/bin/python", "-c", SMOKE_SCRIPT], "models": ["minilm"], "minutes": 10}
    submit.write_job(store, run, job, spec)


def smoke(machine, kind, entry, store_spec):
    """Pull the pushed image afresh and run three smoke jobs in it: a fresh node cache, a second fresh cache (the
    weights from the store), the warm cache; the cold-start numbers."""
    folder, host = machine["folder"], machine["host"]
    store = stores.open_store(store_spec)
    run = time.strftime(f"smoke-{kind}-%Y%m%d-%H%M%S")
    send_store_environment(machine, store_spec)
    batch.remote(folder, host, "cat > /root/smoke/models.json", input=json.dumps(SMOKE_MODELS), text=True, check=True)
    remote_seconds(machine, f"docker image rm -f {entry['image']} >/dev/null 2>&1; docker image prune -af >/dev/null")
    numbers = {"pull_seconds": remote_seconds(machine, f"docker pull -q {shlex.quote(entry['image'])}"), "runs": {}}
    for job, cache in (("first-node", "a"), ("second-node", "b"), ("warm", "b")):
        smoke_job(store, run, job, kind, entry)
        wall = remote_seconds(machine, shlex.join([
            "docker", "run", "--rm", "--env-file", "/root/smoke/store.env", "-e", "SCORE_MODELS=/opt/smoke/models.json",
            "-e", f"SCORE_NODE={folder.name}", "-v", "/root/smoke/models.json:/opt/smoke/models.json:ro",
            "-v", f"/var/lib/score-cache-{cache}:/cache", entry["image"], run, job]))
        timings = submit.done(store, run, job)["timings"]
        numbers["runs"][job] = {"container_seconds": wall,
                                "weights_seconds": seconds_between(timings, "pod_start", "weights_ready"),
                                "job_seconds": seconds_between(timings, "pod_start", "uploaded")}
    batch.say(f"{kind} smoke: {json.dumps(numbers)}")
    return numbers


def build_all(machine, kinds, registry, built, store_spec):
    """Build each kind in order on one builder, smoke-testing each when asked."""
    for kind in kinds:
        entry = build_one(machine, kind, registry, built)
        if store_spec:
            entry["smoke"] = smoke(machine, kind, entry, store_spec)
            save(built)


def price(kinds, account):
    """Print the estimate and refuse what passes the owner's limits; the offers and the minutes allowed."""
    found = batch.offers(list(PROCESSORS))
    if not found:
        raise SystemExit("no processor machine is sold by the backend")
    minutes = SETUP_MINUTES + MINUTES_EACH * len(kinds)
    dearest = max(offer.price for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(kinds)} images ({', '.join(kinds)}) on one machine: about {minutes} min, "
              f"€{ledger.cost(minutes, dearest, 60):.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def build(kinds, who, smoke_test):
    """Rent a builder, build and push the kinds, delete it; the ledger's entry."""
    import pictures as picture_runs

    account = cloud.account()
    batch.sweep(account)
    found, allowed_minutes = price(kinds, account)
    registry, store_spec = cloud.registry(), cloud.object_store() if smoke_test else None
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("images-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    built = saved()
    shares = spread.Shares([kinds], deadline=run.deadline)  # one share: the kinds in order, on one builder
    try:
        spread.on_machines(run, account, found, 1, KIND, shares, lambda machine: set_up(machine, registry),
                           lambda machine, share, _card: build_all(machine, share, registry, built, store_spec),
                           disk_gb=DISK_GB)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run_folder.name,
                 "kind": KIND, "who": who, "images": kinds,
                 **ledger.machines_record(run.machines, run.attempts, started),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        batch.say(f"images: {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f} (logs under {run_folder})")
    if shares.failed or shares.waiting:
        raise SystemExit(f"the build did not finish (logs under {run_folder})")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("kinds", nargs="*", help="image folders to build")
    parser.add_argument("--all", action="store_true", help="every image folder")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--force", action="store_true", help="build even when images.json holds the tag")
    parser.add_argument("--smoke", action="store_true", help="run the smoke jobs in each pushed image")
    parser.add_argument("--dry-run", action="store_true", help="say what would be built and price it, rent nothing")
    options = parser.parse_args()
    asked = image_kinds() if options.all else options.kinds
    unknown = set(asked) - set(image_kinds())
    if unknown or not asked:
        raise SystemExit(f"no image folder named {', '.join(sorted(unknown)) or '(none given)'}; "
                         f"there are {', '.join(image_kinds())}")
    kinds = stale(asked, saved(), options.force)
    if not kinds:
        batch.say("every image asked for is built at its tag")
        return
    if options.dry_run:
        price(kinds, cloud.account())
        return
    build(kinds, options.who, options.smoke)


if __name__ == "__main__":
    main()
