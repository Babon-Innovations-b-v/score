"""The store's blobs in the store bucket (#74, first slice; the owner's answers of 2026-11-02: Multi-AZ, local copies
may go once the bucket is shown to hold them): a blob is pushed to the bucket once, its local copy is evicted only
when the bucket answers for it with its size and its sha256, and an evicted blob comes back on its first read. Only
blobs (store/objects/blobs/<sha256>, about 99.8% of the bytes) move; every other object stays local as before.

    offload.install()                          # once per process: an evicted blob is fetched when it is read
    pushed = offload.push(path, sha, bucket)   # one blob into the bucket ("sent" or "there": a 412, the same bytes)
    offload.proven(bucket, sha, size)          # True only when the bucket answers with this size and this sha256
    offload.evict(objects_root, sha, size)     # its mark written, then its local copy removed (the caller proved it)
    offload.mark_remote(objects_root, sha, size)  # a blob made elsewhere (a pod) marked, never held here
    offload.copy_blob(sha, target, key)        # a blob copied inside the object storage into a job store, never here

The bucket is one of its own in fr-par (the backend's RUN_STORE_BUCKET, `score-<project>-store`; Scaleway's default
class there is Multi-AZ, versioning never turned on), reached with the runtime key read by name
(`score-cloud-runtime-key`) and never made here. Every put is conditional (If-None-Match: *): a second writer gets
412, which for a blob means the same bytes are already there. Each object carries its sha256 as metadata, written
from the bytes hashed just before the upload; a local copy whose bytes do not hash to its name is never sent.

An evicted blob leaves a mark, `store/evicted/<sha256>` beside the objects ({size, at}), written and synced before
the local copy goes, so at every moment the blob is local or marked. install() makes every FolderStore treat a marked
blob as present and fetch it on its first read through `path` (every read, open, download and link goes through it):
to a partial file of its own, its sha256 checked, mode 0444, renamed into place, the mark removed. A blob missing with
no mark is asked of the bucket too on a read (a PC that pulled a listing without its blob reads it): HEAD first, a 404
alone absent (it stays missing, as before), then the same fetch. A sha256 that does not match is fetched once more,
then BlobMismatch is raised; a network error propagates and is never read as absent. A write of a new blob
(Store.put_blob, which asks `exists` and then `path`) never asks the bucket: install() marks it as a write.

Like durable.py this is framework-only (score/graph's Runner and score/review install it; score/graph/_code.py's
FRAMEWORK lists this folder), so it is in no row's key: score/store/__init__.py and tools/cloud/runtime/store.py are
in every row's code version and are not edited. Which blobs may be evicted (no checkout or kept link, none a live run
or the next one reads) is score/conductor/disk.py's store-evict; this module only moves and proves bytes.
"""
import datetime
import functools
import json
import os
import pathlib
import re
import shutil
import sys
import threading
import time

from score.store import file_hash, locked, partial_of, runtime_store
from score.store.durable import landed, synced, whole_file

BLOBS = "blobs/"
EVICTED = "evicted"  # beside the objects: store/evicted/<sha256>, one mark an evicted blob
SHA_FIELD = "sha256"  # the object metadata naming the bytes' sha256
FETCH_TRIES = 2  # a fetched blob whose sha256 does not match is fetched once more, then BlobMismatch
WORKERS = 16  # uploads and answers at once
PUSH_TRIES = 5  # a push the bucket's connection drops is sent again, each wait PUSH_PAUSE doubled (see push)
PUSH_PAUSE = 1.0  # seconds before the first try again
PLAIN_PATH = runtime_store.FolderStore.path  # FolderStore's own, before install
SHA = re.compile(r"[0-9a-f]{64}")
WRITING = threading.local()  # .depth > 0 inside a put_blob of this thread: its misses are a write's, never asked


class BucketUnreachable(RuntimeError):
    """The store bucket cannot be opened: the backend names none, or its key or the bucket cannot be read."""


class BlobMismatch(OSError):
    """A blob fetched from the bucket whose bytes do not hash to its name, twice: the read fails, nothing is kept."""


class Bucket:
    """The store bucket over boto3: conditional puts with the sha256 as metadata, answers by HEAD, a 404 alone absent."""

    def __init__(self, spec):
        import boto3
        import botocore.config

        self.name = spec["bucket"]
        self.client = boto3.client("s3", endpoint_url=spec["endpoint"], region_name=spec["region"],
                                   aws_access_key_id=spec["access_key"], aws_secret_access_key=spec["secret_key"],
                                   config=botocore.config.Config(max_pool_connections=WORKERS,
                                                                 retries={"mode": "standard"}))

    def answer(self, key):
        """(size, sha256 metadata or None) of the object at `key`, or None on a 404; any other error raises."""
        import botocore.exceptions

        try:
            head = self.client.head_object(Bucket=self.name, Key=key)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return head["ContentLength"], head.get("Metadata", {}).get(SHA_FIELD)

    def put_new(self, path, key, sha):
        """The file at `path` stored under `key` only if nothing is there: True when sent now, False on a 412. Large
        files go in parts as runtime_store sizes them; a failed multipart upload is aborted."""
        size = pathlib.Path(path).stat().st_size
        part = runtime_store.part_size(size)
        try:
            if size <= part:
                with open(path, "rb") as source:
                    self.client.put_object(Bucket=self.name, Key=key, Body=source, IfNoneMatch="*",
                                           Metadata={SHA_FIELD: sha})
            else:
                self.put_parts(path, key, sha, part)
        except Exception as error:
            if refused_as_there(error):
                return False
            raise
        return True

    def put_parts(self, path, key, sha, part):
        """A multipart upload completed with If-None-Match: *, aborted on any failure (the 412 included)."""
        upload = self.client.create_multipart_upload(Bucket=self.name, Key=key, Metadata={SHA_FIELD: sha})["UploadId"]
        try:
            parts = []
            with open(path, "rb") as source:
                while chunk := source.read(part):
                    number = len(parts) + 1
                    sent = self.client.upload_part(Bucket=self.name, Key=key, UploadId=upload, PartNumber=number,
                                                   Body=chunk)
                    parts.append({"ETag": sent["ETag"], "PartNumber": number})
            self.client.complete_multipart_upload(Bucket=self.name, Key=key, UploadId=upload, IfNoneMatch="*",
                                                  MultipartUpload={"Parts": parts})
        except BaseException:
            self.client.abort_multipart_upload(Bucket=self.name, Key=key, UploadId=upload)
            raise

    def fetch(self, key, destination):
        """The object's bytes written to `destination` (ranges side by side, as runtime_store's download)."""
        from boto3.s3.transfer import TransferConfig

        self.client.download_file(self.name, key, str(destination), Config=TransferConfig(
            multipart_threshold=runtime_store.RANGE_SIZE, multipart_chunksize=runtime_store.RANGE_SIZE,
            max_concurrency=runtime_store.RANGES_AT_ONCE))

    def copy_into(self, key, target, target_key):
        """The object at `key` copied into `target` (a runtime_store.BucketStore) under `target_key` by the object
        storage itself (a managed copy, in parts when large): its bytes never pass through this machine."""
        self.client.copy({"Bucket": self.name, "Key": key}, target.bucket, target_key)

    def listed(self, prefix):
        """Every key under `prefix` the bucket lists: a hint for what to skip sending, never a proof."""
        found = set()
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.name, Prefix=prefix):
            found |= {item["Key"] for item in page.get("Contents", [])}
        return found


def refused_as_there(error):
    """True for the bucket's 412 on a conditional put: an object is already under the key."""
    response = getattr(error, "response", None) or {}
    return (response.get("Error", {}).get("Code") == "PreconditionFailed"
            or response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 412)


class FolderBucket:
    """A local folder standing in for the store bucket (the tests, a trial): the same calls, an object's sha256
    metadata kept beside it under .meta/, a put refused when the key is taken."""

    def __init__(self, root):
        self.root = pathlib.Path(root)

    def answer(self, key):
        path = self.root / key
        if not path.is_file():
            return None
        meta = self.root / ".meta" / key
        return path.stat().st_size, meta.read_text() if meta.is_file() else None

    def put_new(self, path, key, sha):
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = partial_of(target)
        shutil.copyfile(path, partial)
        try:
            os.link(partial, target)  # exclusive, as If-None-Match: *
        except FileExistsError:
            return False
        finally:
            partial.unlink()
        (self.root / ".meta" / key).parent.mkdir(parents=True, exist_ok=True)
        (self.root / ".meta" / key).write_text(sha)
        return True

    def fetch(self, key, destination):
        shutil.copyfile(self.root / key, destination)

    def copy_into(self, key, target, target_key):
        target.path(target_key).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.root / key, target.path(target_key))

    def listed(self, prefix):
        folder = self.root / prefix
        return {f"{prefix}{path.name}" for path in folder.iterdir()} if folder.is_dir() else set()


def open_bucket():
    """The store bucket, its runtime key read by name from the backend's secret store (tools/cloud/provider.py);
    never made here: BucketUnreachable when the backend names none (a missing bucket's 404 raises as boto3 gives it)."""
    cloud = pathlib.Path(__file__).resolve().parents[3] / "tools" / "cloud"
    for folder in (cloud / "backends", cloud):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    import provider

    backend = provider.cloud
    if not hasattr(backend, "RUN_STORE_BUCKET"):
        raise BucketUnreachable(f"the {backend.NAME} backend names no store bucket (RUN_STORE_BUCKET)")
    key = json.loads(backend.secret(backend.RUNTIME_KEY_SECRET))
    bucket = Bucket({"endpoint": f"https://s3.{backend.REGION}.scw.cloud", "region": backend.REGION,
                     "bucket": backend.RUN_STORE_BUCKET, "access_key": key["access_key"],
                     "secret_key": key["secret_key"]})
    bucket.client.head_bucket(Bucket=bucket.name)  # a 404 here: the bucket is not there; it is made by hand once
    return bucket


def blob_key(sha):
    return f"{BLOBS}{sha}"


def push(path, sha, bucket):
    """One local blob into the bucket: "sent", or "there" (412: the same bytes were there already). A local copy whose
    bytes do not hash to `sha` is never sent: ValueError. A put whose connection the bucket drops is sent again, up to
    PUSH_TRIES times (the store bucket closed about one request in four while a pod sent surfaces-paint@tube's 362
    files, three in a row more than once, 2026-11-07); the last error raised."""
    if file_hash(path) != sha:
        raise ValueError(f"{path}: its bytes do not hash to its name; not sent")
    for tried in range(PUSH_TRIES):
        try:
            return "sent" if bucket.put_new(path, blob_key(sha), sha) else "there"
        except Exception as error:
            if tried == PUSH_TRIES - 1 or not dropped(error):
                raise
        time.sleep(PUSH_PAUSE * 2 ** tried)


def dropped(error):
    """True for a connection the bucket closed or lost (botocore's HTTP client and connection errors, or the
    standard library's): a put that may be sent again. A put sent whole before the drop answers 412 the next time."""
    import botocore.exceptions

    return isinstance(error, (ConnectionError, botocore.exceptions.HTTPClientError,
                              botocore.exceptions.ConnectionError))


def proven(bucket, sha, size):
    """True only when the bucket answers for the blob with this size and this sha256 (never a local list)."""
    found = bucket.answer(blob_key(sha))
    return found is not None and found == (size, sha)


def mark_of(objects_root, sha):
    return pathlib.Path(objects_root).parent / EVICTED / sha


def evict(objects_root, sha, size):
    """The blob's mark written and synced, then its local copy removed and its folder synced. The caller has proven
    the bucket holds it (proven) and that nothing links it; a copy whose size changed is refused (ValueError)."""
    blob = pathlib.Path(objects_root) / BLOBS / sha
    status = blob.stat()
    if status.st_size != size or status.st_nlink != 1:
        raise ValueError(f"{blob}: changed or linked since it was proven; kept")
    write_mark(objects_root, sha, size)
    blob.unlink()
    synced(blob.parent)


def write_mark(objects_root, sha, size):
    """The blob's mark ({size, at}) written whole and synced."""
    mark = mark_of(objects_root, sha)
    mark.parent.mkdir(parents=True, exist_ok=True)
    at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    landed(whole_file(mark, json.dumps({"size": size, "at": at}).encode()), mark)


def mark_remote(objects_root, sha, size):
    """A blob the bucket holds and this machine never had (a pod made it, #76) marked as evicted, so a read here
    fetches it; nothing for a blob held here or marked already. The caller has proven the bucket holds it."""
    if PLAIN_PATH(runtime_store.FolderStore(objects_root), blob_key(sha)).is_file() or \
            mark_of(objects_root, sha).is_file():
        return
    write_mark(objects_root, sha, size)


def copy_blob(sha, target, key):
    """A blob the store bucket holds copied into `target`, a job store (the cluster's cache bucket), under `key`, by
    the object storage itself: an evicted blob reaches a job without landing on this machine's disk (#76)."""
    bucket_now().copy_into(blob_key(sha), target, key)


# --- fetch on demand: install() -------------------------------------------------------------------------------------

OPENER = {"open": open_bucket, "bucket": None}  # the bucket a fetch reads, opened at the first fetch


def bucket_now():
    """The bucket fetches read from, opened once a process."""
    if OPENER["bucket"] is None:
        OPENER["bucket"] = OPENER["open"]()
    return OPENER["bucket"]


def fetched(objects_root, sha):
    """A missing blob back in place from the bucket, marked or not: asked first (HEAD; a 404 alone is absent: None,
    except for a marked blob, which the bucket proved it held: FileNotFoundError), then downloaded to a partial file of
    this process, its sha256 checked (fetched once more on a mismatch, then BlobMismatch), mode 0444, synced, renamed
    into place, its mark removed. Any other error of the bucket propagates."""
    target = pathlib.Path(objects_root) / BLOBS / sha
    mark = mark_of(objects_root, sha)
    with locked(mark.parent / "locks" / sha[:2]):  # one fetch of a blob at a time on this machine
        if target.is_file():
            return target
        if bucket_now().answer(blob_key(sha)) is None:
            if mark.is_file():
                raise FileNotFoundError(f"{blob_key(sha)} is marked evicted and the store bucket does not hold it")
            return None
        for _ in range(FETCH_TRIES):
            partial = partial_of(target)
            try:
                bucket_now().fetch(blob_key(sha), partial)
                if file_hash(partial) == sha:
                    partial.chmod(0o444)
                    synced(partial)
                    landed(partial, target)
                    mark.unlink(missing_ok=True)
                    return target
            finally:
                partial.unlink(missing_ok=True)
        raise BlobMismatch(f"{blob_key(sha)} came from the bucket {FETCH_TRIES} times with other bytes than its name")


def missing_sha(store, key):
    """The blob's sha256 when `key` names a blob that is not here, else None."""
    if not key.startswith(BLOBS) or PLAIN_PATH(store, key).is_file():
        return None
    sha = key[len(BLOBS):]
    return sha if SHA.fullmatch(sha) else None


def writing():
    return getattr(WRITING, "depth", 0) > 0


def fetching_path(self, key):
    """FolderStore.path, a missing blob fetched first (marked or not; a write's miss never asked): every read, open,
    download and link of a blob passes here."""
    sha = missing_sha(self, key)
    if sha is not None and not writing():
        fetched(self.root, sha)
    return PLAIN_PATH(self, key)


def present(self, key):
    """FolderStore.exists, a missing blob counted as present when it is marked evicted or, outside a write, the bucket
    answers for it (HEAD only, nothing fetched)."""
    if PLAIN_PATH(self, key).is_file():
        return True
    sha = missing_sha(self, key)
    if sha is None:
        return False
    return mark_of(self.root, sha).is_file() or (not writing() and bucket_now().answer(blob_key(sha)) is not None)


def as_a_write(put_blob):
    """Store.put_blob run as a write: its own `exists` and `path` on the new blob never ask the bucket."""
    @functools.wraps(put_blob)  # __wrapped__: the put_blob durable installed stays readable under it
    def put(self, path, sha):
        WRITING.depth = getattr(WRITING, "depth", 0) + 1
        try:
            return put_blob(self, path, sha)
        finally:
            WRITING.depth -= 1
    put.as_a_write = True
    return put


def install(opener=None):
    """Every FolderStore in this process fetches an evicted blob when it is read and counts it as present
    (idempotent); `opener` gives the bucket (a FolderBucket in the tests), open_bucket by default."""
    from score.store import Store

    OPENER["open"], OPENER["bucket"] = opener or open_bucket, None
    runtime_store.FolderStore.path = fetching_path
    runtime_store.FolderStore.exists = present
    if not getattr(Store.put_blob, "as_a_write", False):
        Store.put_blob = as_a_write(Store.put_blob)
