"""The store: every stage output kept, named by the hash of its content, never overwritten, never in a hand-named
folder or tmp.

    store = Store.default()                         # $PROPS_HOME/store, a folder; nothing in the cloud
    output = store.put_tree(folder)                 # the output's hash; its files go in once each
    folder = store.checkout(output)                 # a read-only copy to read it from
    store.write_record(node, key, record)           # a node's finish record, once per key
    store.accepted(node)                            # the output the owner accepted last, or None

Objects sit in an object store with tools/cloud/runtime/store.py's interface (its FolderStore here; its BucketStore
takes the same calls), under these keys:

    blobs/<sha256>                          one file's bytes
    outputs/<hash>.json                     an output: {relative path: blob}, its hash the hash of this list
    records/<node>/<key>.json               a node's finish record, written once when its output is made
    judgements/<node>/<key>/<evidence>.json its gates' verdicts on that output under one state of its evidence
    evidence/<check>/<output>               a check's evidence on one output (a drop run's report, say)
    accepts/<node>/<time>.json              each accept the owner gave; the newest is the node's accepted output
    spend-yes/<node>/<key>.json             the owner's yes to one paid run's estimate

Accepts, waivers and spend yeses are written only by the owner's own commands (score/review). In the framework's store
`write_once` refuses them in any process an agent started (Claude Code marks its shells: AGENT_MARKERS), and a hook
keeps agents from the other routes (.claude/hooks/accept_guard.py). On one machine under YOLO that is a barrier, not a
lock: an agent set on getting round it can, and every accept names who gave it and when. Nothing here moves the
accepted output: a new output lands beside it. The local cache (checkouts, copies of the stored bytes, and the folder
a stage writes into before its output is stored) sits beside the objects.
"""
import hashlib
import json
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools/cloud/runtime"))
import store as runtime_store  # noqa: E402

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
CHUNK = 1 << 20
AGENT_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "AI_AGENT")
OWNER_AREAS = ("accepts/", "waivers/", "spend-yes/")


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
        self.objects.upload(path, key)
        if isinstance(self.objects, runtime_store.FolderStore):
            self.objects.path(key).chmod(0o444)

    def put_tree(self, folder):
        """Store a file or folder as an output; its hash. Storing the same content again stores nothing new."""
        listing = tree_listing(folder)
        for name, path in tree_files(folder).items():
            self.put_blob(path, listing[name])
        output = listing_hash(listing)
        key = f"outputs/{output}.json"
        if not self.objects.exists(key):
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

    def checkout(self, output):
        """A read-only folder holding a stored output, made once per output in the cache and made again when its
        files no longer match the output."""
        folder = self.cache / "checkouts" / output
        if folder.is_dir() and tree_listing(folder) == self.listing(output):
            return folder
        if folder.is_dir():
            shutil.rmtree(folder)
        partial = folder.with_name(output + ".partial")
        if partial.exists():
            shutil.rmtree(partial)
        for name, sha in self.listing(output).items():
            self.place_blob(sha, partial / name)
        partial.rename(folder)
        return folder

    def making(self, key):
        """An empty folder for a node to write its output into before it is stored."""
        folder = self.cache / "making" / key
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        return folder

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
        the framework store's accepts, waivers or spend yeses."""
        if key.startswith(OWNER_AREAS) and self.is_framework_store() and running_under_agent():
            raise PermissionError(f"{key}: only the owner accepts, waives or says yes to a spend, from his own "
                                  "terminal; an agent's process cannot write it")
        if self.objects.exists(key):
            raise FileExistsError(f"{key} is already in the store; nothing is overwritten")
        runtime_store.write_json(self.objects, key, value)

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
            self.objects.download(key, path)
        return path

    def put_evidence(self, check, output, path):
        """Store a check's evidence on an output (an evidence run's report); the first stays, it is not replaced."""
        key = self.evidence_key(check, output)
        if self.objects.exists(key):
            raise FileExistsError(f"{key} is already in the store; nothing is overwritten")
        self.objects.upload(path, key)

    # --- the owner's accepts and spend yeses ------------------------------------------------------------------

    def accepts(self, node):
        """Every accept the owner gave a node, oldest first."""
        found = [runtime_store.read_json(self.objects, key) for key in self.objects.keys(f"accepts/{node}/")]
        return sorted(found, key=lambda accept: accept["at"])

    def accepted(self, node):
        """The output the owner accepted last for a node, or None when he never did."""
        found = self.accepts(node)
        return found[-1]["output"] if found else None

    def write_accept(self, node, accept):
        """Record one of the owner's accepts (score/review's accept is the only caller)."""
        self.write_once(f"accepts/{node}/{stamp_key(accept['at'])}-{accept['output'][:12]}.json", accept)

    def spend_yes(self, node, key):
        return self.read(f"spend-yes/{node}/{key}.json")

    def write_spend_yes(self, node, key, yes):
        """Record the owner's yes to one paid run (score/review's spend is the only caller)."""
        self.write_once(f"spend-yes/{node}/{key}.json", yes)
