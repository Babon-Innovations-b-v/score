"""The surviving bucket, read only: its checkout tars indexed by their first header, and downloaded one at a time
within a run's budget once the owner said yes (#13).

A store checkout went up as a job input named for its tar's sha256 (tools/cloud/inputs.py: `inputs/<sha>.tar`,
the input folder first, named as it was here); a checkout's folder is named for its output's hash, so a tar whose
first member is a 64-hex folder holds one stored output's files.
"""
import contextlib
import io
import json
import pathlib
import re
import shutil
import tarfile
import tempfile

from score import graph
from score.store import locked, runtime_store, whole_file

HEX_TAR = re.compile(r"^inputs/[0-9a-f]{64}\.tar$")
OUTPUT_NAME = re.compile(r"^[0-9a-f]{64}$")
# Enough of a tar's front for its first member's headers: a PAX header and its data, then the ustar header.
HEAD_BYTES = 8192
# Free disk a download must leave on the WSL virtual disk at its peak (the tar, its unpacked copy, the store's copy):
# a full virtual disk is the failure this PC cannot take (2026-10-19).
DISK_MARGIN = 20e9


def open_bucket():
    """The project's bucket, read with the runtime key from its secret (provider.cloud): never makes a key or a
    bucket, unlike object_store()."""
    import provider  # tools/cloud, on the path through the restore's ledger import
    backend = provider.cloud
    key = json.loads(backend.secret(backend.RUNTIME_KEY_SECRET))
    return runtime_store.BucketStore({"endpoint": f"https://s3.{backend.REGION}.scw.cloud", "region": backend.REGION,
                                      "bucket": backend.BUCKET, "access_key": key["access_key"],
                                      "secret_key": key["secret_key"]})


def head_bytes(bucket, key, count=HEAD_BYTES):
    """The first `count` bytes of one object: a ranged read in a bucket, never the whole object."""
    if hasattr(bucket, "client"):
        return bucket.client.get_object(Bucket=bucket.bucket, Key=key, Range=f"bytes=0-{count - 1}")["Body"].read()
    with bucket.reader(key) as reader:
        return reader.read(count)


def first_member(head):
    """(name, is a folder) of the first member of a tar whose front bytes are `head`, or None when it is no tar."""
    try:
        archive = tarfile.open(fileobj=io.BytesIO(head), mode="r:")
    except tarfile.TarError:
        return None
    member = archive.firstmember
    return (member.name, member.isdir()) if member else None


def index_checkouts(bucket, say=print):
    """{output: [{key, bytes}, ...]} of every hex-named input tar in `bucket` whose first member is an output's folder,
    smallest first: one folder can go up in several tars (other modes, a copy changed before upload), and only one
    whose bytes rebuild to the output's hash may be stored."""
    found = {}
    keys = [key for key in bucket.keys("inputs/") if HEX_TAR.match(key)]
    for number, key in enumerate(keys, 1):
        member = first_member(head_bytes(bucket, key))
        if member and member[1] and OUTPUT_NAME.match(member[0]):
            found.setdefault(member[0], []).append({"key": key, "bytes": bucket.size(key)})
            found[member[0]].sort(key=lambda tar: (tar["bytes"], tar["key"]))
        if number % 100 == 0:
            say(f"read {number} of {len(keys)} tar headers, {len(found)} checkouts")
    return found


class Fetch:
    """Checkout tars downloaded from `bucket` one at a time, read only, into new empty folders under `folder`, at most
    `max_bytes` for the whole run (every node's process counts in `folder`'s downloaded.json)."""

    def __init__(self, bucket, folder, max_bytes):
        self.bucket, self.folder, self.max_bytes = bucket, pathlib.Path(folder), max_bytes

    def reserve(self, size):
        """Count `size` bytes against the run's budget; Blocked when they would pass it."""
        spent = self.folder / "downloaded.json"
        self.folder.mkdir(parents=True, exist_ok=True)
        with locked(spent.with_name("downloaded.lock")):
            done = json.loads(spent.read_text())["bytes"] if spent.exists() else 0
            if done + size > self.max_bytes:
                raise graph.Blocked(f"a {size / 1e9:.2f} GB download would pass the run's "
                                    f"{self.max_bytes / 1e9:.2f} GB ({done / 1e9:.2f} GB downloaded)")
            whole_file(spent, json.dumps({"bytes": done + size}).encode()).replace(spent)

    def room_for(self, size):
        """Blocked unless the disk under `folder` keeps DISK_MARGIN free with three times `size` written on it (the
        tar, its unpacked copy, the store's copy)."""
        self.folder.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(self.folder).free
        if free < 3 * size + DISK_MARGIN:
            raise graph.Blocked(f"a {size / 1e9:.2f} GB download needs {(3 * size + DISK_MARGIN) / 1e9:.1f} GB free "
                                f"on the disk, {free / 1e9:.1f} GB is: nothing downloaded")

    @contextlib.contextmanager
    def unpacked(self, key, output, size):
        """The folder of `output` from the tar at `key`, unpacked with tarfile's data filter, while the block runs;
        the tar is deleted once unpacked, the folder after the block. Blocked when the disk has no room for it
        (room_for), it would pass the run's budget (reserve) or the tar holds no such folder."""
        self.room_for(size)
        self.reserve(size)
        with locked(self.folder / "download.lock"):  # one tar at a time
            work = pathlib.Path(tempfile.mkdtemp(prefix="reattach-", dir=self.folder))
            try:
                tar = work / "checkout.tar"
                self.bucket.download(key, tar)
                unpacked = work / "unpacked"
                unpacked.mkdir()
                with tarfile.open(tar) as archive:
                    archive.extractall(unpacked, filter="data")
                tar.unlink()
                if not (unpacked / output).is_dir():
                    raise graph.Blocked(f"{key} holds no folder {output[:12]}: nothing stored")
                yield unpacked / output
            finally:
                shutil.rmtree(work)
