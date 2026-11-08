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

Which nodes go to pods (#76, build spec S8): `dispatches(stage)` under SCORE_K8S_POD and SCORE_K8S_QUEUE, the box's
queue fresh and the runner image published, for a free stage without gatherers in POD_STAGES (each entered by a commit
after its rehearsal gave the same listing hash on the conductor, locally and on the cluster). Runner.make then calls
`make_remote`: the job's blobs pushed, the job made by a runner worker through the queue (cluster_jobs.run, the
POD_COMMAND), the manifest collected here; a node the cluster did not make is made by Runner.make itself.

    pod.make_remote(runner, stage, place, keyed)   # in the node's fork, under its key's lock: the record, or None
    pod.downstream(reads, nodes)                    # the drive's priority: how many waiting nodes read each node
    pod.expect(waiting)                             # the drive's expected/<pid>.json: {image kind: waiting nodes}

Framework only (score/graph/_code.py FRAMEWORK lists this file), so it is in no row's key.
"""
import argparse
import concurrent.futures
import contextlib
import importlib
import importlib.util
import json
import math
import os
import pathlib
import platform
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
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
FETCHES = 16  # input blobs fetched at once (one at a time a pod fetched about 15 MB/s, rehearsal 2026-11-07)
DESIGN = "design"  # the home's locked designs, which the stage table reads to say what each row declares
# The stages made in pods: each only after its rehearsal (the build spec's section 6) gave the conductor's output, a
# local pod's and a cluster worker's as one listing hash (tube, 2026-11-07: rough-align, props-inputs and cast; and
# surfaces-paint once its upload was retried, 4455a781; campgrounds, 2026-11-08: finish-route-split, 9.0 min in a pod
# against 2.1 here, its 1006 input blobs fetched, and surfaces-parts, 1.3 min against 0.6; motion, 15.5 min in a
# local pod and 19.9 on a cluster worker against 1.1 here for the make alone: a pod's minutes are the make and its
# eleven checks, each building the scene again with its bakes' maps (about 80 s a check here, 2026-11-08), which
# the drive pays after its own make). Kept here, each for its
# rehearsal's fault: finish-route-views (a take the conductor kept was made again in the pod, 25 min against 0.06, its
# record's key order another), surfaces-check and light-layer (a cluster worker's -0.0 for 0.0 in checks.json, other
# sky_dome.png bytes: this PC's numbers against the image's, so the conductor's own make decides), light (it reads
# rejects/scene-record@<place>/*, which its job does not name); earth-seed writes paths and a time into its output.
POD_STAGES = frozenset({"rough-align", "props-inputs", "cast", "surfaces-paint", "finish-route-split",
                        "surfaces-parts", "motion"})
IMAGE_OF = dict.fromkeys(POD_STAGES, "runner")  # the image kind a waiting node of the stage will want (expected/)
POD_VARIABLE = "SCORE_K8S_POD"
QUEUE_VARIABLE = "SCORE_K8S_QUEUE"
CLASSES_VARIABLE = "SCORE_POD_CLASSES"  # the classes a runner worker may take, in order (default capacity.PROCESSORS)
STORE_VARIABLE = "SCORE_POD_STORE_BUCKET"  # in the job: the store bucket's name, reached with the job store's key
TABLE = "score.stages:STAGES"
QUEUE_FOLDER = score_store.PROPS_HOME / "cloud" / "queue"  # the box's queue's control files (job_queue.QUEUE)
POD_MINUTES = 60
# A pod make's forecast, its clearance's when the run names no ticket: a free node costs only its pod's machine time
# (the tube rehearsal of 2026-11-07: one worker's node, three jobs and its idle tail, EUR 0.21), its deadline the high.
POD_FORECAST = {"euros": 0.25, "minutes": None, "high_minutes": POD_MINUTES, "measured": 0}
ARCHIVE_TIME = "2000-01-01 00:00:00 +0000"  # every file's time in the code archive (git's approxidate reads "@0" as now)
HEADROOM = 1.25  # a pod's memory request: its stage's measured peak this many times
POD_COMMAND = r"""set -e
export SCORE_UV_LOCK=$(cat /opt/score/uv.lock.sha256)
sha=$(sha256sum /work/in/code.tar | cut -d' ' -f1)
tree=/cache/code/$sha
if [ ! -d "$tree" ]; then
  mkdir -p /cache/code; part=$(mktemp -d /cache/code/.part-XXXXXX)
  tar -xf /work/in/code.tar -C "$part"; mv -T "$part" "$tree" 2>/dev/null || rm -rf "$part"
fi
/opt/score/env/bin/python -c 'import os, json; json.dump({**{k: os.environ["SCORE_STORE_" + v] for k, v in (("endpoint", "ENDPOINT"), ("region", "REGION"), ("access_key", "ACCESS_KEY"), ("secret_key", "SECRET_KEY"))}, "bucket": os.environ["SCORE_POD_STORE_BUCKET"]}, open("/work/bucket.json", "w"))'
home=$(/opt/score/env/bin/python -c 'import json; print(json.load(open("/work/in/job.json"))["world"]["roots"]["home"])')
rm -rf "$home"; mkdir -p "$home" /work/out
cd "$tree"
PROPS_HOME="$home" SCORE_POD_BUCKET=/work/bucket.json SCORE_POD_IMAGE="$SCORE_IMAGE" /opt/score/env/bin/python -m score.graph.pod run /work/in/job.json /work/out/manifest.json --cache /cache
rm -rf "$home"
"""  # the store bucket is reached with the job store's runtime key (the score-store Secret), its name from the job


class Undeclared(LookupError):
    """A make in a pod read a store key its job does not name."""


# --- on the conductor ------------------------------------------------------------------------------------------------

def job_of(runner, stage, place, keyed, code, table):
    """The job a pod makes the node from: its whole key, the code's sha256, the stage table (`module:attribute`), the
    repository's folders this process's code versions search (`_code.search_folders`: the stages' imports put them on
    the path, and the pod's code versions must search the same), the environment, every input's listing, every
    declared file's path and listing, the home's designs (`designs`), the store records its file list reads
    (`store_reads`) and the per-take calls kept under the node's code (tools/cloud/kept.py `calls_of`). A paid
    stage is refused."""
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
            "files": files, "design": designs(), **store_reads(runner, stage, place),
            "kept": kept_module().calls_of(runner.making_code(stage, place, keyed))}


def kept_module():
    """tools/cloud/kept.py as the stage table loads it (score/stages kept_module: by its path, one module)."""
    if "kept" not in sys.modules:
        spec = importlib.util.spec_from_file_location("kept", _code.REPO / "tools/cloud/kept.py")
        sys.modules["kept"] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules["kept"])
    return sys.modules["kept"]


def kept_blobs(found):
    """The sha256s of the files the kept entries `found` (kept.calls_of's form) hold."""
    return {sha for entry in found.values() for sha, _ in entry["files"].values()}


def designs():
    """{path under the home's design folder: its sha256} of each JSON there: the locked designs the stage table reads
    to say what a row declares and reads (a designed place's surfaces, an earth place's seed from its plans), which no
    key names. Without them a pod's table declares another row (light-layer@tube, 2026-11-07: its seed a lost
    file)."""
    folder = score_store.PROPS_HOME / DESIGN
    return {path.relative_to(folder).as_posix(): file_hash(path) for path in sorted(folder.rglob("*.json"))
            if path.is_file()}


def store_reads(runner, stage, place):
    """{"records": {store key: sha256}, "listed": [prefix]}: each store record a row's file list reads here (light's:
    its own place's accepted scene record, whose places say which neighbours it declares) and each prefix it lists, so
    the pod's sandbox holds them and works the list out as here (light@campgrounds, 2026-11-08: its make named
    rejects/scene-record@campgrounds/* undeclared). A blob it reads comes only with an input's listing; nothing for a
    row whose files are a fixed dict."""
    if not callable(stage.files):
        return {"records": {}, "listed": []}
    reads, listed = [], []
    remembered, runner.remembered = runner.remembered, None  # worked out again: a still pass's answer read nothing
    try:
        with traced(runner.store.objects.root, reads, listed):
            runner.files_of(stage, place)
    finally:
        runner.remembered = remembered
    root = runner.store.objects.root
    return {"records": {key: file_hash(root / key) for key in sorted(set(reads))
                        if not key.startswith(offload.BLOBS) and (root / key).is_file()},
            "listed": sorted(set(listed))}


@contextlib.contextmanager
def traced(root, reads, listed):
    """Every key this thread asks a FolderStore under `root` for (path, exists) added to `reads`, and each prefix it
    lists to `listed` with the keys listed added to `reads`, while the block runs."""
    folder_store = score_store.runtime_store.FolderStore
    plain = {name: getattr(folder_store, name) for name in ("path", "exists", "keys")}
    root, thread = pathlib.Path(root).resolve(), threading.get_ident()

    def ours(store):
        return threading.get_ident() == thread and pathlib.Path(store.root).resolve().is_relative_to(root)

    def path(self, key):
        if ours(self):
            reads.append(key)
        return plain["path"](self, key)

    def exists(self, key):
        if ours(self):
            reads.append(key)
        return plain["exists"](self, key)

    def keys(self, prefix):
        found = plain["keys"](self, prefix)
        if ours(self):
            listed.append(prefix)
            reads.extend(found)
        return found
    folder_store.path, folder_store.exists, folder_store.keys = path, exists, keys
    try:
        yield
    finally:
        for name, method in plain.items():
            setattr(folder_store, name, method)


def blob_sources(runner, job):
    """{sha256: local path} of every blob the job reads: its inputs' stored blobs, its declared files' bytes, the
    home's designs and the store records its file list reads."""
    found = {sha: offload.PLAIN_PATH(runner.store.objects, offload.blob_key(sha))  # never fetched here
             for listing in job["listings"].values() for sha in listing.values()}
    for declared in job["files"].values():
        root = pathlib.Path(declared["path"])
        for relative, sha in declared["listing"].items():
            found[sha] = root / relative if declared["folder"] else root
    for relative, sha in job["design"].items():
        found[sha] = score_store.PROPS_HOME / DESIGN / relative
    for key, sha in job["records"].items():
        found[sha] = runner.store.objects.root / key
    kept_objects = kept_module().store().objects
    for sha in kept_blobs(job.get("kept", {})):
        found.setdefault(sha, offload.PLAIN_PATH(kept_objects, offload.blob_key(sha)))
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
        return runner.make_here(stage, place, keyed) if record else None
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
    kept_back(manifest)
    made = {**graph.finish_record(node, keyed, output, stage.name, manifest["started"], time.monotonic()),
            "minutes": manifest["minutes"], "pod": {"node": manifest["node"], "image": manifest["image"]}}
    stands = runner.write_finish(node, keyed, made)
    if stands is made:
        judged(runner, stage, stands, manifest)
    return stands


def kept_back(manifest):
    """The per-take calls the pod made and kept, kept here too (kept.taken), each only when every file it holds is a
    blob of the output's listing (proven in the bucket), so the next make of a take, here or in a pod, finds it."""
    blobs = set(manifest["listing"].values())
    kept_module().taken({name: entry for name, entry in manifest.get("kept", {}).items()
                         if kept_blobs({name: entry}) <= blobs})


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


def switched_on():
    """Whether pod makes are asked for: SCORE_K8S_POD and SCORE_K8S_QUEUE both set, neither 0."""
    return all(os.environ.get(name, "") not in ("", "0") for name in (POD_VARIABLE, QUEUE_VARIABLE))


def cluster_door():
    """tools/cloud/k8s's cluster_jobs (the runners' one door) and job_queue, imported from this tree."""
    folder = str(_code.REPO / "tools" / "cloud" / "k8s")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import cluster_jobs
    import job_queue
    return cluster_jobs, job_queue


def runner_published():
    """Whether the runner image is in this tree's images.json, the image a pod make runs on."""
    path = _code.REPO / "tools" / "cloud" / "images" / "images.json"
    return path.is_file() and "runner" in json.loads(path.read_text())


def dispatching(start=False):
    """Whether this drive sends pod stages to the cluster now: switched on, the runner image published and the box's
    queue fresh; `start`: a queue not fresh is started (job_queue.start), for a later pass."""
    if not (switched_on() and runner_published()):
        return False
    queue = cluster_door()[1]
    if queue.fresh():
        return True
    if start:
        queue.start()
    return False


def eligible(stage):
    """Whether a stage's nodes may be made in pods: in POD_STAGES, free, with no gatherers."""
    return stage.name in POD_STAGES and not stage.paid and not stage.gatherers


def dispatches(stage):
    """Whether a node of `stage` is made in a pod now (eligible and dispatching)."""
    return eligible(stage) and dispatching()


def code_archive(folder=None, repo=None):
    """This tree's files as a tar: git archive of HEAD's tree at ARCHIVE_TIME, so the same files give the same bytes
    whatever commit holds them (a commit's archive carries its id and time: each run's frozen commit sent and unpacked
    the code again, tube rehearsal 2026-11-07), and its sha256 names the workers' warm tree; written once a tree under
    the system's temporary folder, an older tree's goes."""
    repo = repo or _code.REPO
    tree = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], capture_output=True, text=True,
                          check=True).stdout.strip()
    folder = pathlib.Path(folder or tempfile.gettempdir()) / "score-pod-code"
    tar = folder / f"{tree}.tar"
    if not tar.is_file():
        folder.mkdir(parents=True, exist_ok=True)
        partial = folder / f".{tree}.{os.getpid()}.partial"
        with open(partial, "wb") as target:
            subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", f"--mtime={ARCHIVE_TIME}", tree],
                           stdout=target, check=True)
        partial.replace(tar)
        for old in folder.glob("*.tar"):
            if old != tar:
                old.unlink(missing_ok=True)
    return tar


def requests_of(runner, stage):
    """A pod job's cores and memory: 4 cores, and its stage's measured peak (Runner.peaks) times HEADROOM."""
    peak = runner.peaks().get(stage.name, 0) * HEADROOM
    return {"cpu": "4", "memory": f"{max(1, math.ceil(peak / 2**30))}Gi"}


def pod_classes(door):
    """The classes a runner worker may take, in order: SCORE_POD_CLASSES, else capacity's processor classes."""
    named = os.environ.get(CLASSES_VARIABLE, "")
    return [name.strip() for name in named.split(",") if name.strip()] or list(door.submitter.capacity.PROCESSORS)


def remote_job(tar, folder, bucket, requests):
    """The cluster job (cluster_jobs.run's form) that makes the job at <folder>/job.json in a runner worker, its
    manifest coming back to <folder>/manifest.json."""
    return {"command": ["sh", "-c", POD_COMMAND], "code": [],
            "inputs": [{"local": str(tar), "path": "/work/in/code.tar"},
                       {"local": str(folder / "job.json"), "path": "/work/in/job.json"}],
            "outputs": [{"path": "/work/out/manifest.json", "local": str(folder / "manifest.json")}],
            "env": {STORE_VARIABLE: bucket.name}, "minutes": POD_MINUTES, "cards": 0, "attempt_limit": 1, **requests}


def make_remote(runner, stage, place, keyed, table=None):
    """The node made by a runner worker through the box's queue, in its fork under its key's lock: its job and every
    blob it reads pushed to the store bucket, the job run on the cluster (cluster_jobs.run, which waits holding no
    --jobs slot), its manifest collected here (collect: proven, registered, recorded, judged); the record that
    stands, or None when the cluster did not make it (refused, or its job did not finish), so Runner.make makes it."""
    from score.adapters import compute  # here: compute imports score.graph for its tickets
    node = graph.node_name(stage, place)
    door = cluster_door()[0]
    bucket = offload.bucket_now()
    tar = code_archive()
    job = job_of(runner, stage, place, keyed, file_hash(tar), table or TABLE)
    pushed(runner, job, bucket)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="score-pod-"))
    try:
        (folder / "job.json").write_text(json.dumps(job))
        try:
            with pod_cleared(runner, node):
                failed = door.run("runner", [remote_job(tar, folder, bucket, requests_of(runner, stage))],
                                  who=f"pod {node}", classes=pod_classes(door), image="runner")
        except (compute.Refused, graph.Blocked) as refused:
            print(f"{node}: not sent to the cluster ({refused}); made here", flush=True)
            return None
        except door.Elsewhere as elsewhere:  # its processor classes cannot be had on the cluster now
            print(f"{node}: {elsewhere}; made here", flush=True)
            return None
        if failed:
            print(f"{node}: its pod job did not finish; made here", flush=True)
            return None
        manifest = json.loads((folder / "manifest.json").read_text())
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return collect(runner, stage, place, keyed, manifest, bucket)


def pod_cleared(runner, node):
    """What a pod make runs under: the ticket the run names (SCORE_SPEND_TICKET), else the node's own clearance at
    POD_FORECAST, cleared by the runner against the stop line like a paid make's (Runner.cleared; a free node got none,
    so a run needed a run-wide ticket or its free nodes were made here, tube rehearsal 2026-11-07). Blocked in a
    free-only run, and on this PC's free-only run nothing (its queue refuses), so the node is made here."""
    from score.adapters import compute  # here: compute imports score.graph for its tickets
    if os.environ.get(compute.TICKET):
        return contextlib.nullcontext()
    return runner.cleared(node, POD_FORECAST["euros"], lambda: dict(POD_FORECAST))


def downstream(reads, nodes):
    """{node: how many of `reads`' nodes read it, directly or through others of them} for each of `nodes`; `reads` is
    {waiting node: the nodes it reads}. The queue serves the node most others wait on first."""
    readers = {}
    for reader, earlier in reads.items():
        for node in earlier:
            readers.setdefault(node, set()).add(reader)
    counts = {}
    for node in nodes:
        seen, todo = set(), list(readers.get(node, ()))
        while todo:
            reader = todo.pop()
            if reader not in seen:
                seen.add(reader)
                todo += readers.get(reader, ())
        counts[node] = len(seen)
    return counts


def expect(waiting, folder=None):
    """Write this drive's expected/<pid>.json in the queue's folder: {image kind: how many `waiting` stages
    (one a node) map to it (IMAGE_OF)}, whole; an empty count removes it. The path."""
    counts = {}
    for stage in waiting:
        if stage.name in IMAGE_OF:
            counts[IMAGE_OF[stage.name]] = counts.get(IMAGE_OF[stage.name], 0) + 1
    path = pathlib.Path(folder or QUEUE_FOLDER) / "expected" / f"{os.getpid()}.json"
    if not counts:
        path.unlink(missing_ok=True)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    whole_file(path, json.dumps(counts, sort_keys=True).encode()).replace(path)
    return path


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


def wanted_blobs(store, job):
    """The sha256s of the input blobs, declared files and store records the sandbox does not hold yet, once each."""
    listed = {sha for listing in job["listings"].values() for sha in listing.values()
              if not (store.objects.root / offload.blob_key(sha)).exists()}
    declared = {sha for declared in job["files"].values() for relative, sha in declared["listing"].items()
                if not (pathlib.Path(declared["path"]) / relative if declared["folder"]
                        else pathlib.Path(declared["path"])).exists()}
    records = {sha for key, sha in job["records"].items() if not (store.objects.root / key).exists()}
    return sorted(listed | declared | records)


def prefetched(cache, shas):
    """Each blob into the node's cache from the bucket, FETCHES at once (cached_blob; its first failure raised)."""
    with concurrent.futures.ThreadPoolExecutor(FETCHES) as pool:
        for _ in pool.map(lambda sha: cached_blob(cache, sha), shas):
            pass


def placed_designs(job, cache):
    """The job's designs written under this home's design folder (fetched side by side first), before the stage table
    is read; why not, when the bucket lacks one (the conductor did not push it), else None."""
    folder = score_store.PROPS_HOME / DESIGN
    try:
        prefetched(cache, sorted(set(job["design"].values())))
        for relative, sha in job["design"].items():
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached_blob(cache, sha), target)
    except FileNotFoundError as missing:
        return f"designs: {missing}"
    return None


def placed_inputs(store, job, cache):
    """Each input's listing and blobs into the sandbox store (blobs hard-linked from the cache, fetched side by side
    first), each declared file that is not at its path already put there, each store record its file list reads
    (`store_reads`) into the sandbox store; the store keys the job names, a listed prefix as `<prefix>*`."""
    prefetched(cache, wanted_blobs(store, job))
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
    for key, sha in job["records"].items():
        target = store.objects.root / key
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached_blob(cache, sha), target)
        allowed.add(key)
    return allowed | {f"{prefix}*" for prefix in job["listed"]}


def placed_kept(store, job, cache):
    """The job's kept per-take calls written in this home's kept folder, their files' blobs fetched side by side and
    linked into the sandbox store; the store keys they read. An entry a blob of which the bucket lacks is left out:
    its take is made again."""
    found, keys = {}, set()
    for name, entry in job.get("kept", {}).items():
        try:
            prefetched(cache, sorted(kept_blobs({name: entry})))
        except FileNotFoundError:
            continue
        for sha in kept_blobs({name: entry}):
            blob = store.objects.root / offload.blob_key(sha)
            blob.parent.mkdir(parents=True, exist_ok=True)
            if not blob.exists() and not score_store.linked_read_only(cached_blob(cache, sha), blob):
                shutil.copyfile(cached_blob(cache, sha), blob)
                blob.chmod(0o444)
            keys.add(offload.blob_key(sha))
        found[name] = entry
    kept_module().taken(found)
    return keys


@contextlib.contextmanager
def sandboxed(root, allowed, reads):
    """Every FolderStore under `root` refuses a key not in `allowed` (Undeclared, the key added to `reads`) and every
    listing of keys, while the block runs. A write of a new blob (Store.put_blob, offload.writing: a kept take's files,
    tools/cloud/kept.py's call) reads nothing and is let through (finish-route-views@tube, 2026-11-07: its first take
    kept was named an undeclared read)."""
    folder_store = score_store.runtime_store.FolderStore
    plain = {name: getattr(folder_store, name) for name in ("path", "exists", "keys")}
    root = pathlib.Path(root).resolve()

    def guarded(store, key):
        if key not in allowed and not offload.writing() and pathlib.Path(store.root).resolve().is_relative_to(root):
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
    allowed |= placed_kept(runner.store, job, cache)
    inputs, code = runner.input_paths(stage, place, keyed), runner.making_code(stage, place, keyed)
    before = set(kept_module().calls_of(code))
    out, reads = runner.store.making(keyed["key"]), []
    os.environ[kept_module().REPOSITORY_AS] = job["world"]["roots"].get("repo", str(_code.REPO))
    try:
        try:
            with sandboxed(runner.store.objects.root, allowed, reads), graph.making_in(out, code):
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
        made = kept_module().calls_of(code)
        return {**sent(out, bucket), **pod_verdicts(stage, out, inputs),
                "kept": {name: entry for name, entry in made.items() if name not in before}}
    finally:
        os.environ.pop(kept_module().REPOSITORY_AS, None)
        graph.gone(out)


def sent(out, bucket):
    """The output folder's listing and blob sizes, each blob put into the bucket once (a 412: the same bytes there;
    files of the same bytes are one blob)."""
    listing = tree_listing(out)
    files = score_store.tree_files(out)
    for sha, name in {sha: name for name, sha in listing.items()}.items():
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
            bucket = pod_bucket()
            offload.install(lambda: bucket)
            why = placed_designs(job, cache)
            if why:
                answer = {"refused": why}
            else:
                runner, stage = sandbox_runner(job)
                offload.install(lambda: bucket)  # the runner installed the backend's bucket: the pod's again
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
