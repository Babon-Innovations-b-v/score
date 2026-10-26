"""The store's reboot safety (C9): every write synced to disk before and after it lands, so a machine that goes down
mid-write leaves the whole object or none of it (a 0-byte record after a WSL restart stopped every later run), and an
object that still reads empty or unparsable moved to quarantine/ beside the store and read as absent, so its node is
made again rather than every later run failing on it. Never one in an owner area (accepts, rejects, waivers, spend
yeses): that raises UnreadableOwnerObject and stays where it is, since a decision read as absent would loosen a gate
(a reject undone, a paid row bought again unasked).

    durable.install()      # once per process: Store's writing and reading methods become these

It lives here, not in score/store/__init__.py, and only the framework installs it (score.graph's Runner and
score/review's commands), so it is in no row's key: the store's module is in every stage's code version that calls
the store, and an edit there re-keyed 44 paid rows (C9 review, 2026-10-17). Nothing a stage runs imports this module,
which test_an_output_is_kept_whole_once_and_never_overwritten.py checks; how a record is written and read back never changes what a make makes. A stage's own
Store in a process the framework did not start writes and reads as score/store/__init__.py says.
"""
import json
import os
import pathlib
import shutil
import sys
import threading

from score.store import (OWNER_AREAS, RUNNER, Store, listing_hash, partial_of, running_under_agent, runtime_store,
                         tree_files, tree_listing)


class UnreadableOwnerObject(RuntimeError):
    """An accept, reject, waiver or spend yes in the store that is empty or unparsable: it stops the run."""


def synced(path):
    """Flush a file's or a folder's bytes to disk, so they outlive a reboot."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def whole_file(path, data):
    """`data` written whole and synced beside `path`, ready to move or link into place; the partial file's path."""
    partial = partial_of(path)
    partial.write_bytes(data)
    synced(partial)
    return partial


def landed(partial, path):
    """Move a synced partial file into place, then sync its folder so the move outlives a reboot."""
    partial.replace(path)
    synced(path.parent)


def write_whole(path, data):
    """Write `data` to `path` so a reader or a reboot finds the old bytes or the new, never half (the run registry)."""
    landed(whole_file(path, data), path)


def put_blob(self, path, sha):
    """Store one file's bytes under their hash, once, synced; stored files are read-only."""
    key = f"blobs/{sha}"
    if self.objects.exists(key):
        return
    if not isinstance(self.objects, runtime_store.FolderStore):
        self.objects.upload(path, key)
        return
    partial = partial_of(self.objects.path(key))
    shutil.copyfile(path, partial)
    synced(partial)
    partial.chmod(0o444)
    landed(partial, self.objects.path(key))  # whole, and the same bytes whichever process lands last


def put_tree(self, folder):
    """Store a file or folder as an output, synced; its hash. Storing the same content again stores nothing new."""
    listing = tree_listing(folder)
    for name, path in tree_files(folder).items():
        self.put_blob(path, listing[name])
    output = listing_hash(listing)
    key = f"outputs/{output}.json"
    if self.objects.exists(key):
        return output
    if isinstance(self.objects, runtime_store.FolderStore):
        write_whole(self.objects.path(key), json.dumps(listing, indent=1).encode())
    else:
        runtime_store.write_json(self.objects, key, listing)
    return output


def listing(self, output):
    """{relative path: sha256} of a stored output; FileNotFoundError when it is missing or quarantined."""
    found = self.read(f"outputs/{output}.json")
    if found is None:
        raise FileNotFoundError(f"outputs/{output}.json is not in the store (missing or quarantined)")
    return found


def read(self, key):
    """A stored JSON object, or None when it is missing or unreadable (then quarantined); an unreadable one in an
    owner area (OWNER_AREAS) raises UnreadableOwnerObject instead, since reading a cut reject as absent would let the
    accept it undid stand again, and a cut accept as absent would let a paid row be bought again."""
    if not self.objects.exists(key):
        return None
    try:
        return json.loads(self.objects.read_bytes(key))
    except FileNotFoundError:  # quarantined by another process since
        return None
    except ValueError as unreadable:  # empty or cut short (json's error and a bad encoding are both ValueErrors)
        if key.startswith(OWNER_AREAS):
            raise UnreadableOwnerObject(f"{key} in the store is empty or unparsable: an owner's decision is never "
                                        "read as absent or moved; look at it by hand") from unreadable
        self.quarantine(key)
        return None


def read_all(self, keys):
    """The readable objects of `keys`, in order; an unreadable one is quarantined and left out (one in an owner area
    raises, see read)."""
    found = (self.read(key) for key in keys)
    return [value for value in found if value is not None]


def quarantine(self, key):
    """Move an unreadable object out of the store to quarantine/ beside it, with one line on stderr; a store not in
    a local folder keeps it and only says so."""
    if not isinstance(self.objects, runtime_store.FolderStore):
        print(f"store: {key} is unreadable, read as absent", file=sys.stderr, flush=True)
        return
    source = self.objects.path(key)
    target = self.cache.parent / "quarantine" / f"{key}.{os.getpid()}-{threading.get_ident()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(source, target)
    except FileNotFoundError:  # another process moved it first
        return
    synced(source.parent)
    print(f"store: {key} is empty or unparsable, moved to {target} and read as absent", file=sys.stderr, flush=True)


def write_once(self, key, value):
    """Write a JSON object that must not exist yet, synced before it is linked into place and its folder after:
    nothing in the store is overwritten, and an agent never writes the framework store's owner areas (the runner's own
    automatic accepts excepted)."""
    automatic = key.startswith("accepts/") and value.get("by") == RUNNER
    if key.startswith(OWNER_AREAS) and not automatic and self.is_framework_store() and running_under_agent():
        raise PermissionError(f"{key}: only the owner accepts, rejects, waives or says yes to a spend, from his own "
                              "terminal; an agent's process cannot write it")
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
    synced(target.parent)


def records(self, node):
    """Every readable finish record of a node, oldest first."""
    return sorted(self.read_all(self.objects.keys(f"records/{node}/")), key=lambda record: record["finished"])


def judgements(self, node, key):
    """Every readable judgement of one finish record, oldest first."""
    found = self.read_all(self.objects.keys(f"judgements/{node}/{key}/"))
    return sorted(found, key=lambda judgement: judgement["at"])


def put_evidence(self, check, output, path):
    """Store a check's evidence on an output, synced; the first stays, it is not replaced."""
    key = self.evidence_key(check, output)
    if self.objects.exists(key):
        raise FileExistsError(f"{key} is already in the store; nothing is overwritten")
    if not isinstance(self.objects, runtime_store.FolderStore):
        self.objects.upload(path, key)
        return
    partial = partial_of(self.objects.path(key))
    shutil.copyfile(path, partial)
    synced(partial)
    landed(partial, self.objects.path(key))


def registry(self, area):
    """Every readable entry of one registry area (finishes, surfaces), in the order of their ids."""
    return self.read_all(sorted(self.objects.keys(f"registry/{area}/")))


def timed(self, area, node):
    """Every object of a node in one timed area (accepts/, rejects/), oldest first; an unreadable one raises."""
    return sorted(self.read_all(self.objects.keys(f"{area}{node}/")), key=lambda item: item["at"])


def waivers(self, node, key):
    """{check: waiver} the owner gave a node under one key; an unreadable one raises."""
    found = {pathlib.PurePosixPath(item).stem: self.read(item) for item in self.objects.keys(f"waivers/{node}/{key}/")}
    return {check: waiver for check, waiver in found.items() if waiver is not None}


def clearances(self, node, key):
    """Every readable clearance the runner gave one paid run of a node."""
    return self.read_all(self.objects.keys(f"clearances/{node}/{key}/"))


METHODS = {"put_blob": put_blob, "put_tree": put_tree, "listing": listing, "read": read, "read_all": read_all,
           "quarantine": quarantine, "write_once": write_once, "records": records, "judgements": judgements,
           "put_evidence": put_evidence, "registry": registry, "timed": timed, "waivers": waivers,
           "clearances": clearances}


def install():
    """Give every Store in this process the synced writes and the quarantining reads above (idempotent)."""
    for name, method in METHODS.items():
        setattr(Store, name, method)
