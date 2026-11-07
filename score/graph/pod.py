"""A free node made in a pod (#76, the cluster build spec's step 3): the conductor hands a pod one node's whole key and
its inputs' listings, the pod makes the output from those alone and sends its blobs straight to the store bucket, and
the conductor proves every blob, then registers the output and writes its record and judgement. The pod writes no key,
record, judgement or accept: only content-addressed blobs and its own manifest.

    job = pod.job_of(runner, stage, place, keyed, code, table)  # on the conductor: the job a pod makes from
    pod.pushed(runner, job, bucket)                             # every blob the job reads, in the bucket first
    tree = pod.unpack(tar, cache)                               # in the pod: the run's code at <cache>/code/<sha256>
    PROPS_HOME=<empty home> python -m score.graph.pod run <job.json> <manifest.json> --cache <cache>   # from `tree`
    record = pod.collect(runner, stage, place, keyed, manifest)  # on the conductor, under the node's key's lock

In the pod, before any make, `refusal` compares the tree with the job: the tree's folder is the code's sha256 (unpack
names it so), its uv.lock is the image's ($SCORE_UV_LOCK, where the image sets it), the stage's code version and pinned
models recomputed here are the key's, and every declared file placed here hashes to the key's. A refused job comes back
as {"refused": why} and the conductor makes the node itself, as it would without a pod. Inside the make the store is a
sandbox (`sandboxed`): a key the job does not name raises Undeclared and the manifest says {"undeclared": [keys]}, the
node again made on the conductor. A make error comes back as {"error": its traceback}, a contract breach as {"broken":
why}.

The conductor never trusts a hash it is handed: `collect` works the output's hash out from the manifest's listing and
proves each blob with offload.proven (the bucket's size and sha256); one missing or off refuses the whole manifest and
nothing is stored. A blob that is not local is marked (offload.mark_remote), so a later local read fetches it. Of two
manifests for one key the first record stands.

Framework only (score/graph/_code.py FRAMEWORK lists this file), so it is in no row's key. Which stages go to pods is
the drive's (a later step); nothing here decides it.
"""
import argparse
import concurrent.futures
import contextlib
import importlib
import json
import os
import pathlib
import platform
import resource
import shutil
import sys
import tarfile
import time
import traceback

from score import checks, contracts, graph
from score.adapters import models
from score.graph import _code
import score.store as score_store
from score.store import file_hash, listing_hash, offload, text_hash, tree_listing
from score.store.durable import whole_file

PUSHED = score_store.PROPS_HOME / "cloud" / "queue" / "pushed"  # one sha256 a line: blobs the bucket answered for
BUCKET_VARIABLE = "SCORE_POD_BUCKET"  # in the pod: a bucket spec file (the mounted secret), or folder:<path>
LOCK_VARIABLE = "SCORE_UV_LOCK"  # set by the runner image: the sha256 of the uv.lock its venv was synced from
IMAGE_VARIABLE = "SCORE_POD_IMAGE"  # set by the worker: the image digest the pod runs, for the record
NOT_PROVEN = "pod output not proven"


class Undeclared(LookupError):
    """A make in a pod read a store key its job does not name."""


# --- on the conductor ------------------------------------------------------------------------------------------------

def job_of(runner, stage, place, keyed, code, table):
    """The job a pod makes the node from: its whole key, the code's sha256, the stage table (`module:attribute`), the
    repository's folders this process's code versions search (`_code.search_folders`: the stages' imports put them on
    the path, and the pod's code versions must search the same), the environment, every input's listing and every
    declared file's path and listing. A paid stage is refused."""
    if stage.paid:
        raise ValueError(f"{graph.node_name(stage, place)}: a paid stage is never made in a pod")
    files = {}
    for name in runner.files_of(stage, place):
        path = runner.file_path(stage, name, place)
        files[name] = {"path": str(path), "folder": path.is_dir(),
                       "listing": {relative: graph.stamped_hash(found)
                                   for relative, found in score_store.tree_files(path).items()
                                   if not graph.bytecode(relative)}}
    inputs = {**keyed["after"], **keyed.get("beside", {})}
    return {"node": graph.node_name(stage, place), "stage": stage.name, "place": place, "keyed": keyed,
            "code": code, "table": table, "objects": sorted(runner.objects) if runner.objects else None,
            "folders": [folder.relative_to(_code.REPO).as_posix() for folder in _code.search_folders()
                        if _code.in_repo(folder)],
            "world": {"name": runner.world.name, "seed": runner.world.seed,
                      "roots": {root: str(path) for root, path in runner.world.roots.items()}},
            "listings": {name: runner.store.listing(output) for name, output in inputs.items()},
            "files": files}


def blob_sources(runner, job):
    """{sha256: local path} of every blob the job reads: its inputs' stored blobs and its declared files' bytes."""
    found = {sha: offload.PLAIN_PATH(runner.store.objects, offload.blob_key(sha))  # never fetched here
             for listing in job["listings"].values() for sha in listing.values()}
    for declared in job["files"].values():
        root = pathlib.Path(declared["path"])
        for relative, sha in declared["listing"].items():
            found[sha] = root / relative if declared["folder"] else root
    return found


def pushed(runner, job, bucket, known=None):
    """Every blob the job reads in the bucket before it is handed out: one the bucket already answers for is only
    noted, any other pushed from its local copy (offload.push). The noted sha256s (`known`, PUSHED by default) are
    never asked again on this box. The number sent now."""
    known = pathlib.Path(known or PUSHED)
    noted = set(known.read_text().split()) if known.is_file() else set()
    wanted = {sha: path for sha, path in blob_sources(runner, job).items() if sha not in noted}

    def one(sha):
        if bucket.answer(offload.blob_key(sha)) is not None:
            return "there"
        return offload.push(wanted[sha], sha, bucket)
    with concurrent.futures.ThreadPoolExecutor(offload.WORKERS) as pool:
        answers = dict(zip(wanted, pool.map(one, wanted)))
    if answers:
        known.parent.mkdir(parents=True, exist_ok=True)
        with open(known, "a") as lines:
            lines.write("".join(f"{sha}\n" for sha in answers))
    return sum(answer == "sent" for answer in answers.values())


def collect(runner, stage, place, keyed, manifest, bucket=None, record=True):
    """The node's record from a pod's manifest, in the node's fork under its key's lock: a refused or undeclared job
    made here instead (Runner.make); a broken one raises contracts.Broken, an errored one RuntimeError. Otherwise the
    output's hash worked out from the listing, each blob proven in the bucket (else RuntimeError NOT_PROVEN, nothing
    stored), the declared files checked unchanged, the output registered, its record written (the first stands) and
    judged. `record` False (a rehearsal): only the output's hash, no record or judgement."""
    node = graph.node_name(stage, place)
    if "refused" in manifest or "undeclared" in manifest:
        why = manifest.get("refused") or f"undeclared store reads {manifest['undeclared']}"
        print(f"{node}: the pod did not make it ({why}); made here", flush=True)
        return runner.make(stage, place, keyed) if record else None
    if "broken" in manifest:
        raise contracts.Broken(manifest["broken"])
    if "error" in manifest:
        raise RuntimeError(f"{node}: its make failed in the pod:\n{manifest['error']}")
    output = listing_hash(manifest["listing"])
    proven(bucket or offload.bucket_now(), manifest, node)
    if runner.file_keys(stage, place) != keyed["files"]:
        raise RuntimeError(f"{node}: an input changed while it ran; nothing is stored")
    registered(runner.store, manifest)
    if not record:
        return output
    made = {**graph.finish_record(node, keyed, output, stage.name, manifest["started"], time.monotonic()),
            "minutes": manifest["minutes"], "pod": {"node": manifest["node"], "image": manifest["image"]}}
    stands = runner.write_finish(node, keyed, made)
    if stands is made:
        judged(runner, stage, stands, manifest)
    return stands


def proven(bucket, manifest, node):
    """Raise RuntimeError NOT_PROVEN unless the bucket answers for every blob of the listing with its size."""
    sizes = manifest["sizes"]
    missing = sorted(sha for sha in set(manifest["listing"].values())
                     if sha not in sizes or not offload.proven(bucket, sha, sizes[sha]))
    if missing:
        raise RuntimeError(f"{node}: {NOT_PROVEN}: the store bucket does not hold {', '.join(missing)} as named")


def registered(store, manifest):
    """The output's listing written into the store whole, once, after a mark for each blob not held here."""
    objects = store.objects.root
    for sha in set(manifest["listing"].values()):
        offload.mark_remote(objects, sha, manifest["sizes"][sha])
    key = f"outputs/{listing_hash(manifest['listing'])}.json"
    target = offload.PLAIN_PATH(store.objects, key)
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        whole_file(target, json.dumps(manifest["listing"], indent=1).encode()).replace(target)


def judged(runner, stage, record, manifest):
    """The record's judgement as Runner.judge writes it, its verdicts the pod's when the pod judged under the evidence
    state the conductor has for the output now, else judged here; the judgement that stands."""
    evidence = runner.evidence_state(stage, record["output"])
    if manifest.get("verdicts") is None or manifest["evidence"] != evidence:
        return runner.judge(stage, record["place"], record)
    judgement = {"node": record["node"], "key": record["key"], "output": record["output"], "evidence": evidence,
                 "at": graph.now(), "answer": manifest["answer"], "verdicts": manifest["verdicts"]}
    try:
        runner.store.write_judgement(record["node"], record["key"], evidence, judgement)
    except FileExistsError:  # another run judged it first: its judgement stands
        return runner.store.judgement(record["node"], record["key"], evidence)
    return judgement


# --- in the pod ------------------------------------------------------------------------------------------------------

def unpack(tar, cache):
    """The code archive unpacked once into <cache>/code/<its sha256> (a partial folder renamed into place); the tree."""
    sha = file_hash(tar)
    tree = pathlib.Path(cache) / "code" / sha
    if not tree.is_dir():
        partial = score_store.partial_of(tree)
        with tarfile.open(tar) as archive:
            archive.extractall(partial, filter="data")
        partial.rename(tree)
    return tree


def tree_refusal(job):
    """Why this process's tree is not the job's code (its folder is not the code's sha256, or its uv.lock not the
    image's), or None."""
    if _code.REPO.name != job["code"]:
        return f"code: this tree ({_code.REPO.name[:12]}) is not the job's code ({job['code'][:12]})"
    lock = os.environ.get(LOCK_VARIABLE)
    if lock and file_hash(_code.REPO / "uv.lock") != lock:
        return f"lock: the tree's uv.lock is not the image's ({lock[:12]})"
    return None


def refusal(job, runner, stage):
    """Why the stage here would not make the job's key (its code version, pinned models or a declared file's hash
    differ), or None."""
    keyed = job["keyed"]
    if graph.stage_code(stage) != keyed["code"]:
        return "code version: the stage's code here is not its key's"
    if {kind: models.record(kind) for kind in stage.models} != keyed["models"]:
        return "models: the pinned images here are not its key's"
    files = runner.file_keys(stage, job["place"])
    moved = sorted(name for name in keyed["files"] if files.get(name) != keyed["files"][name])
    return f"files: {', '.join(moved)} placed here hash otherwise" if moved or files != keyed["files"] else None


def pod_bucket():
    """The store bucket a pod reads and writes: a folder for `folder:<path>`, else the spec file the variable names,
    else the backend's (offload.open_bucket)."""
    named = os.environ.get(BUCKET_VARIABLE, "")
    if named.startswith("folder:"):
        return offload.FolderBucket(named[len("folder:"):])
    if named:
        return offload.Bucket(json.loads(pathlib.Path(named).read_text()))
    return offload.open_bucket()


def cached_blob(cache, sha):
    """One blob in the node's cache (<cache>/objects/blobs/<sha256>), fetched once from the bucket, its sha256
    checked; FileNotFoundError when the bucket does not hold it."""
    found = offload.fetched(pathlib.Path(cache) / "objects", sha)
    if found is None:
        raise FileNotFoundError(f"{offload.blob_key(sha)} is not in the store bucket")
    return found


def placed_inputs(store, job, cache):
    """Each input's listing and blobs into the sandbox store (blobs hard-linked from the cache), each declared file
    that is not at its path already put there; the store keys the job names."""
    allowed = set()
    for listing in job["listings"].values():
        key = f"outputs/{listing_hash(listing)}.json"
        target = store.objects.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        whole_file(target, json.dumps(listing, indent=1).encode()).replace(target)
        allowed.add(key)
        for sha in listing.values():
            blob = store.objects.root / offload.blob_key(sha)
            blob.parent.mkdir(parents=True, exist_ok=True)
            if not blob.exists() and not score_store.linked_read_only(cached_blob(cache, sha), blob):
                shutil.copyfile(cached_blob(cache, sha), blob)
                blob.chmod(0o444)
            allowed.add(offload.blob_key(sha))
    for declared in job["files"].values():
        root = pathlib.Path(declared["path"])
        for relative, sha in declared["listing"].items():
            target = root / relative if declared["folder"] else root
            if not target.exists():  # one already there is kept as it is: refusal compares its hash
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cached_blob(cache, sha), target)
    return allowed


@contextlib.contextmanager
def sandboxed(root, allowed, reads):
    """Every FolderStore under `root` refuses a key not in `allowed` (Undeclared, the key added to `reads`) and every
    listing of keys, while the block runs."""
    folder_store = score_store.runtime_store.FolderStore
    plain = {name: getattr(folder_store, name) for name in ("path", "exists", "keys")}
    root = pathlib.Path(root).resolve()

    def guarded(store, key):
        if key not in allowed and pathlib.Path(store.root).resolve().is_relative_to(root):
            reads.append(key)
            raise Undeclared(f"{key}: the pod's job does not name it")

    def path(self, key):
        guarded(self, key)
        return plain["path"](self, key)

    def exists(self, key):
        guarded(self, key)
        return plain["exists"](self, key)

    def keys(self, prefix):
        guarded(self, f"{prefix}*")
        return plain["keys"](self, prefix)
    folder_store.path, folder_store.exists, folder_store.keys = path, exists, keys
    try:
        yield
    finally:
        for name, method in plain.items():
            setattr(folder_store, name, method)


def sandbox_runner(job):
    """A runner over the job's table and environment on this process's store (PROPS_HOME, empty), its env linked to
    this Python's venv, the job's folders on the path before any code version is worked out; its stage."""
    home = score_store.PROPS_HOME
    if (home / "store" / "objects").exists():
        raise RuntimeError(f"{home}: a pod's home starts empty")
    (home / "store" / "objects").mkdir(parents=True)
    if not (home / "env").exists():
        (home / "env").symlink_to(pathlib.Path(sys.prefix))
    module, attribute = job["table"].split(":")
    world = graph.Environment(job["world"]["name"], job["world"]["seed"],
                              {root: pathlib.Path(path) for root, path in job["world"]["roots"].items()})
    runner = graph.Runner(getattr(importlib.import_module(module), attribute), world, score_store.Store.default())
    sys.path += [str(_code.REPO / folder) for folder in job["folders"] if str(_code.REPO / folder) not in sys.path]
    runner.objects = job["objects"]
    return runner, runner.stages[job["stage"]]


def made_listing(runner, stage, job, cache, bucket):
    """The pod's answer for the job: its listing and sizes with every blob sent to the bucket and the verdicts it
    judged, or why it did not make it (refused: an input not in the bucket or `refusal`; undeclared; broken)."""
    try:
        allowed = placed_inputs(runner.store, job, cache)
    except FileNotFoundError as missing:  # an input the conductor did not push: made there
        return {"refused": f"inputs: {missing}"}
    why = refusal(job, runner, stage)
    if why:
        return {"refused": why}
    keyed, place, node = job["keyed"], job["place"], job["node"]
    inputs = runner.input_paths(stage, place, keyed)
    out, reads = runner.store.making(keyed["key"]), []
    try:
        try:
            with sandboxed(runner.store.objects.root, allowed, reads), \
                    graph.making_in(out, runner.making_code(stage, place, keyed)):
                stage.make(inputs, out, keyed["seed"], keyed["params"])
        except Exception:
            if reads:
                return {"undeclared": sorted(set(reads))}
            raise
        if reads:
            return {"undeclared": sorted(set(reads))}
        if runner.file_keys(stage, place) != keyed["files"]:
            raise RuntimeError(f"{node}: an input changed while it ran; nothing is stored")
        runner.unchanged_checkouts(node, inputs, keyed)
        try:
            contracts.stamp(stage.contract, out)
        except contracts.Broken as broken:
            return {"broken": str(broken)}
        return {**sent(out, bucket), **pod_verdicts(stage, out, inputs)}
    finally:
        graph.gone(out)


def sent(out, bucket):
    """The output folder's listing and blob sizes, each blob put into the bucket (a 412: the same bytes there)."""
    listing = tree_listing(out)
    files = score_store.tree_files(out)
    for name, sha in listing.items():
        offload.push(files[name], sha, bucket)
    return {"listing": listing, "sizes": {sha: files[name].stat().st_size for name, sha in listing.items()}}


def pod_verdicts(stage, out, inputs):
    """The stage's checks on the made output with no evidence (none is known for a new output) and that evidence
    state; none for a stage with gatherers, which the conductor judges."""
    if stage.gatherers:
        return {"verdicts": None}
    verdicts = [checks.judge(check, out, inputs, None) for check in stage.checks]
    state = {check.name: "missing" if check.evidence else "none" for check in stage.checks}
    return {"verdicts": checks.scorecard(verdicts), "answer": checks.overall(verdicts),
            "evidence": text_hash(json.dumps(state, sort_keys=True))}


def run(job_path, manifest_path, cache):
    """The pod's make of one job (`job_path`), its manifest written whole to `manifest_path`: what it made or why not,
    with when it started, its minutes, its peak bytes, the machine and the image."""
    started, clock = graph.now(), time.monotonic()
    job = json.loads(pathlib.Path(job_path).read_text())
    why = tree_refusal(job)
    answer = {"refused": why} if why else None
    if answer is None:
        try:
            runner, stage = sandbox_runner(job)
            bucket = pod_bucket()
            offload.install(lambda: bucket)
            answer = made_listing(runner, stage, job, cache, bucket)
        except Exception:  # noqa: BLE001 - the make's failure is the manifest's answer, the conductor raises it
            answer = {"error": traceback.format_exc()}
    peak = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            + resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * 1024
    manifest = {**answer, "started": started, "minutes": round((time.monotonic() - clock) / 60, 3), "peak": peak,
                "node": platform.node(), "image": os.environ.get(IMAGE_VARIABLE)}
    target = pathlib.Path(manifest_path)
    whole_file(target, json.dumps(manifest, indent=1, sort_keys=True).encode()).replace(target)
    return manifest


def main(arguments=None):
    """`run <job> <manifest> --cache <folder>`: one job made in this pod."""
    parser = argparse.ArgumentParser(prog="python -m score.graph.pod")
    verbs = parser.add_subparsers(dest="verb", required=True)
    making = verbs.add_parser("run")
    making.add_argument("job")
    making.add_argument("manifest")
    making.add_argument("--cache", default="/cache")
    given = parser.parse_args(arguments)
    manifest = run(given.job, given.manifest, given.cache)
    print(next(iter(sorted(set(manifest) & {"refused", "undeclared", "broken", "error"})), "made"), flush=True)


if __name__ == "__main__":
    main()
