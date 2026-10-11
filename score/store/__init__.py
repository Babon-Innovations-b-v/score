"""The store: every stage output kept, named by the hash of its content, never overwritten, never in a hand-named
folder or tmp.

    store = Store.default()                         # $PROPS_HOME/store, a folder; nothing in the cloud
    output = store.put_tree(folder)                 # the output's hash; its files go in once each
    folder = store.checkout(output)                 # a read-only copy to read it from
    store.write_record(node, key, record)           # a node's finish record, once per key
    store.accepted(node)                            # the node's accepted output (the runner's or the owner's), or None

Objects sit in an object store with tools/cloud/runtime/store.py's interface (its FolderStore here; its BucketStore
takes the same calls), under these keys:

    blobs/<sha256>                          one file's bytes
    outputs/<hash>.json                     an output: {relative path: blob}, its hash the hash of this list
    records/<node>/<key>.json               a node's finish record, written once when its output is made
    judgements/<node>/<key>/<evidence>.json its gates' verdicts on that output under one state of its evidence
    evidence/<check>/<output>               a check's evidence on one output (a drop run's report, say)
    accepts/<node>/<time>.json              each accept, the runner's automatic ones (by RUNNER) and the owner's
    rejects/<node>/<time>.json              each output the owner rejected; it undoes every earlier accept of it
    waivers/<node>/<key>/<check>.json       the owner's waiver of one check for one key; it ends when the key changes
    clearances/<node>/<key>/<time>.json     the runner's clearance of one paid run (score.adapters.compute)
    spend-yes/<node>/<key>.json             the owner's override: his yes to one run outside the runner
    registry/<area>/<id>.json               the world's finish registry, append-only (score/stages/surfaces/registry.py):
                                            finishes/ each finish group's one library surface, surfaces/ each new
                                            library surface proposed, the first of a name standing

The node's accepted output is the newest accept that no later reject of the same output undid. The runner writes its
automatic accepts (score/graph: every gate passed, nothing got worse, the owner never rejected that output); the
owner's accepts, rejects, waivers and spend yeses are written only by his own commands (score/review). In the
framework's store `write_once` refuses those in any process an agent started (Claude Code marks its shells:
AGENT_MARKERS), and a hook keeps agents from the other routes and from writing clearances by hand
(.claude/hooks/accept_guard.py). On one machine under YOLO that is a barrier, not a lock: an agent set on getting
round it can, and every accept names who gave it and when. Nothing else moves the accepted output: a new output lands
beside it. The local cache (checkouts, copies of the stored bytes, and the folder a stage writes into before its
output is stored) sits beside the objects.

Lines run side by side (score.graph's drive), so every write lands whole: it is written to a .partial file only its
own process writes, then moved into place; a write-once key is linked into place, so of two processes writing one key
the second is refused (FileExistsError), and a checkout two processes make at once is made by the first.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools/cloud/runtime"))
import store as runtime_store  # noqa: E402

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
CHUNK = 1 << 20
AGENT_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "AI_AGENT")
OWNER_AREAS = ("accepts/", "rejects/", "waivers/", "spend-yes/")
RUNNER = "runner"  # who an automatic accept is by


def file_hash(path):
    """The sha256 of one file's bytes."""
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_hash(text):
    """The sha256 of a text."""
    return hashlib.sha256(text.encode()).hexdigest()


def tree_files(folder):
    """{relative path: file} of every file under a folder, or of one file under its own name."""
    folder = pathlib.Path(folder)
    if folder.is_file():
        return {folder.name: folder}
    if not folder.is_dir():
        raise FileNotFoundError(f"no file or folder at {folder}")
    return {path.relative_to(folder).as_posix(): path for path in sorted(folder.rglob("*")) if path.is_file()}


def tree_listing(folder):
    """{relative path: sha256} of a file or folder."""
    return {name: file_hash(path) for name, path in tree_files(folder).items()}


def listing_hash(listing):
    """The hash naming a listing: of its sorted JSON."""
    return text_hash(json.dumps(listing, sort_keys=True))


def tree_hash(folder):
    """The hash a file or folder would be stored under, without storing it."""
    return listing_hash(tree_listing(folder))


def running_under_agent():
    """True in a process an agent started (Claude Code marks every shell it runs)."""
    return any(name in os.environ for name in AGENT_MARKERS)


def partial_of(path):
    """A sibling of `path` that only this process and thread writes, ending in .partial (store listings skip those):
    lines run side by side, and each writes whole there before it moves into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.with_name(f"{path.name}.{os.getpid()}-{threading.get_ident()}.partial")


@contextlib.contextmanager
def locked(path):
    """An exclusive lock on `path` across every process, held while the block runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def whole_file(path, data):
    """`data` written whole beside `path`, ready to move or link into place; the partial file's path."""
    partial = partial_of(path)
    partial.write_bytes(data)
    return partial


def stamp_key(stamp):
    """A UTC time as a key part that sorts in time order."""
    return stamp.replace(":", "").replace("-", "")


class Store:
    def __init__(self, objects, cache):
        self.objects = objects
        self.cache = pathlib.Path(cache)

    @classmethod
    def default(cls):
        """The framework's store on this machine: $PROPS_HOME/store/objects, its cache beside it."""
        root = PROPS_HOME / "store"
        return cls(runtime_store.FolderStore(root / "objects"), root / "cache")

    @classmethod
    def in_folder(cls, root):
        """A store in a folder of its own (tests, a trial)."""
        root = pathlib.Path(root)
        return cls(runtime_store.FolderStore(root / "objects"), root / "cache")

    # --- outputs ---------------------------------------------------------------------------------------------

    def put_blob(self, path, sha):
        """Store one file's bytes under their hash, once; stored files are read-only."""
        key = f"blobs/{sha}"
        if self.objects.exists(key):
            return
        if not isinstance(self.objects, runtime_store.FolderStore):
            self.objects.upload(path, key)
            return
        partial = partial_of(self.objects.path(key))
        shutil.copyfile(path, partial)
        partial.chmod(0o444)
        partial.replace(self.objects.path(key))  # whole, and the same bytes whichever process lands last

    def put_tree(self, folder):
        """Store a file or folder as an output; its hash. Storing the same content again stores nothing new."""
        listing = tree_listing(folder)
        for name, path in tree_files(folder).items():
            self.put_blob(path, listing[name])
        output = listing_hash(listing)
        key = f"outputs/{output}.json"
        if self.objects.exists(key):
            return output
        if isinstance(self.objects, runtime_store.FolderStore):
            whole_file(self.objects.path(key), json.dumps(listing, indent=1).encode()).replace(self.objects.path(key))
        else:
            runtime_store.write_json(self.objects, key, listing)
        return output

    def listing(self, output):
        """{relative path: sha256} of a stored output."""
        return runtime_store.read_json(self.objects, f"outputs/{output}.json")

    def place_blob(self, sha, destination):
        """One stored file at a path, read-only: a copy of the stored bytes, never a link to them, so nothing done to
        the copy reaches the store."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.objects, runtime_store.FolderStore):
            shutil.copyfile(self.objects.path(f"blobs/{sha}"), destination)
        else:
            self.objects.download(f"blobs/{sha}", destination)
        destination.chmod(0o444)

    def read_file(self, output, name):
        """One JSON file of a stored output, read from the store without a checkout; None when the output lacks it."""
        sha = self.listing(output).get(name)
        return json.loads(self.objects.read_bytes(f"blobs/{sha}")) if sha else None

    def checkout(self, output):
        """A read-only folder holding a stored output, made once per output in the cache and made again when its
        files no longer match the output."""
        folder = self.cache / "checkouts" / output
        with locked(folder.with_name(f"{output}.lock")):  # one process at a time checks it and makes it again
            if folder.is_dir() and tree_listing(folder) == self.listing(output):
                return folder
            if folder.is_dir():
                shutil.rmtree(folder)
            partial = partial_of(folder)
            for name, sha in self.listing(output).items():
                self.place_blob(sha, partial / name)
            partial.rename(folder)
        return folder

    def making(self, key):
        """A new empty folder of this run's own for a node to write its output into before it is stored: two runs of
        one key never share one (a second run once wiped the first's work)."""
        (self.cache / "making").mkdir(parents=True, exist_ok=True)
        return pathlib.Path(tempfile.mkdtemp(prefix=f"{key}-", dir=self.cache / "making"))

    # --- records, judgements, evidence ---------------------------------------------------------------------

    def read(self, key):
        return runtime_store.read_json(self.objects, key) if self.objects.exists(key) else None

    def is_framework_store(self):
        """True for the framework's own store (any store not in a local folder counts as one)."""
        if not isinstance(self.objects, runtime_store.FolderStore):
            return True
        return self.objects.root.resolve() == (PROPS_HOME / "store" / "objects").resolve()

    def write_once(self, key, value):
        """Write a JSON object that must not exist yet: nothing in the store is overwritten, and an agent never writes
        the framework store's owner areas (the runner's own automatic accepts excepted)."""
        automatic = key.startswith("accepts/") and value.get("by") == RUNNER
        if key.startswith(OWNER_AREAS) and not automatic and self.is_framework_store() and running_under_agent():
            raise PermissionError(f"{key}: only the owner accepts, rejects, waives or says yes to a spend, from his "
                                  "own terminal; an agent's process cannot write it")
        if self.objects.exists(key):
            raise FileExistsError(f"{key} is already in the store; nothing is overwritten")
        if not isinstance(self.objects, runtime_store.FolderStore):
            runtime_store.write_json(self.objects, key, value)
            return
        target = self.objects.path(key)
        partial = whole_file(target, json.dumps(value, indent=1).encode())
        try:
            os.link(partial, target)  # atomic and exclusive: of two processes writing one key, the second is refused
        except FileExistsError as taken:
            raise FileExistsError(f"{key} is already in the store; nothing is overwritten") from taken
        finally:
            partial.unlink()

    def record(self, node, key):
        return self.read(f"records/{node}/{key}.json")

    def write_record(self, node, key, record):
        self.write_once(f"records/{node}/{key}.json", record)

    def records(self, node):
        """Every finish record of a node, oldest first."""
        found = [runtime_store.read_json(self.objects, key) for key in self.objects.keys(f"records/{node}/")]
        return sorted(found, key=lambda record: record["finished"])

    def judgement(self, node, key, evidence):
        return self.read(f"judgements/{node}/{key}/{evidence}.json")

    def write_judgement(self, node, key, evidence, judgement):
        self.write_once(f"judgements/{node}/{key}/{evidence}.json", judgement)

    def judgements(self, node, key):
        """Every judgement of one finish record, oldest first."""
        found = [runtime_store.read_json(self.objects, item)
                 for item in self.objects.keys(f"judgements/{node}/{key}/")]
        return sorted(found, key=lambda judgement: judgement["at"])

    def evidence_key(self, check, output):
        return f"evidence/{check}/{output}"

    def evidence_hash(self, check, output):
        """The hash of a check's evidence on an output, or None when there is none."""
        key = self.evidence_key(check, output)
        return hashlib.sha256(self.objects.read_bytes(key)).hexdigest() if self.objects.exists(key) else None

    def evidence_file(self, check, output):
        """A check's evidence on an output as a local file, or None when there is none."""
        key = self.evidence_key(check, output)
        if not self.objects.exists(key):
            return None
        sha = self.evidence_hash(check, output)
        path = self.cache / "evidence" / sha
        if not path.exists():
            partial = partial_of(path)
            self.objects.download(key, partial)
            partial.replace(path)
        return path

    def put_evidence(self, check, output, path):
        """Store a check's evidence on an output (an evidence run's report); the first stays, it is not replaced."""
        key = self.evidence_key(check, output)
        if self.objects.exists(key):
            raise FileExistsError(f"{key} is already in the store; nothing is overwritten")
        self.objects.upload(path, key)

    # --- the finish registry ------------------------------------------------------------------------------------

    def registry(self, area):
        """Every entry of one registry area (finishes, surfaces), in the order of their ids."""
        return [runtime_store.read_json(self.objects, key) for key in sorted(self.objects.keys(f"registry/{area}/"))]

    def write_registry(self, area, entry_id, entry):
        """Append one registry entry; an entry is never changed or removed."""
        self.write_once(f"registry/{area}/{entry_id}.json", entry)

    def registry_lock(self):
        """The registry's lock across every process, held for a whole read, decide and append."""
        return locked(self.cache.parent / "registry.lock")

    # --- accepts, rejects, waivers, clearances and spend yeses -------------------------------------------------

    def timed(self, area, node):
        """Every object of a node in one timed area (accepts/, rejects/), oldest first."""
        found = [runtime_store.read_json(self.objects, key) for key in self.objects.keys(f"{area}{node}/")]
        return sorted(found, key=lambda item: item["at"])

    def accepts(self, node):
        """Every accept a node was given, the runner's and the owner's, oldest first."""
        return self.timed("accepts/", node)

    def rejects(self, node):
        """Every reject the owner gave a node, oldest first."""
        return self.timed("rejects/", node)

    def current_accept(self, node):
        """The newest accept that no later reject of the same output undid, or None."""
        rejected = {reject["output"]: reject["at"] for reject in self.rejects(node)}
        standing = [accept for accept in self.accepts(node) if accept["at"] > rejected.get(accept["output"], "")]
        return standing[-1] if standing else None

    def accepted(self, node):
        """The node's accepted output, or None when nothing stands accepted."""
        return (self.current_accept(node) or {}).get("output")

    def rejected(self, node, output):
        """True when the owner rejected an output and it has had no accept since."""
        rejects = [reject["at"] for reject in self.rejects(node) if reject["output"] == output]
        accepts = [accept["at"] for accept in self.accepts(node) if accept["output"] == output]
        return bool(rejects) and max(rejects) > max(accepts, default="")

    def write_accept(self, node, accept):
        """Record one accept: the runner's automatic one (score/graph) or the owner's (score/review)."""
        self.write_once(f"accepts/{node}/{stamp_key(accept['at'])}-{accept['output'][:12]}.json", accept)

    def write_reject(self, node, reject):
        """Record one of the owner's rejects (score/review's reject is the only caller)."""
        self.write_once(f"rejects/{node}/{stamp_key(reject['at'])}-{reject['output'][:12]}.json", reject)

    def waivers(self, node, key):
        """{check: waiver} the owner gave a node under one key."""
        return {pathlib.PurePosixPath(item).stem: runtime_store.read_json(self.objects, item)
                for item in self.objects.keys(f"waivers/{node}/{key}/")}

    def write_waiver(self, node, key, check, waiver):
        """Record the owner's waiver of one check for one key (score/review's waive is the only caller)."""
        self.write_once(f"waivers/{node}/{key}/{check}.json", waiver)

    def clearances(self, node, key):
        """Every clearance the runner gave one paid run of a node."""
        return [runtime_store.read_json(self.objects, item) for item in self.objects.keys(f"clearances/{node}/{key}/")]

    def write_clearance(self, node, key, clearance):
        """Record the runner's clearance of one paid run (score.adapters.compute's clearance is the only caller)."""
        self.write_once(f"clearances/{node}/{key}/{stamp_key(clearance['at'])}.json", clearance)

    def spend_yes(self, node, key):
        return self.read(f"spend-yes/{node}/{key}.json")

    def write_spend_yes(self, node, key, yes):
        """Record the owner's override, his yes to one run (score/review's spend is the only caller)."""
        self.write_once(f"spend-yes/{node}/{key}.json", yes)
