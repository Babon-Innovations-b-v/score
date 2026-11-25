"""A store blob's local copy is removed only once the store bucket answers for it with its size and sha256, and an
evicted blob comes back on its first read with its sha256 checked (#74). The bucket is a local folder stand-in
(offload.FolderBucket), never the cloud.

Breaks (each applied once, seen red, reverted), in score/store/offload/__init__.py and score/conductor/disk.py:
- disk.pushed_and_evicted: drop `if not offload.proven(bucket, sha, size): return "unproven", False` (a blob whose
  upload was lost, or whose key held other bytes, is evicted before the bucket holds it: red).
- offload.proven: `return found is not None` (a bucket answering with another size or sha256 counts as holding it).
- offload.fetched: `if file_hash(partial) == sha:` -> `if True:` (a fetched blob's sha256 is not checked: other bytes
  land in the store: red).
- offload.FolderBucket.put_new / Bucket.put_new: a taken key overwritten instead of refused (the 412 is gone).
- disk.evict_why: drop the `st_nlink > 1` check (a checkout's linked blob evicted), or evict_keep: drop the standing
  outputs' listings (an accepted output the next run reads evicted).
- disk.named_outside: drop HASH_MEMO from its skipped folders (a blob kept.py's hash memo names stays local for good;
  this PC's capped store kept 114,604 so, 2026-11-24).
- disk.evict_keep: drop `home / KEPT_JOBS` from named_outside's `also` (a kept job's blob stays local for good;
  67.5 GB on this PC, 2026-11-24).
- offload.fetching_path: return PLAIN_PATH at once (an evicted blob is never fetched; the checkout fails), or
  missing_sha's miss asked only when marked (a PC that pulled a listing without its blob cannot read it: red).
- offload.install: drop the as_a_write wrap of Store.put_blob (a new blob's write asks the bucket; a bucket that
  fails on the network fails the write: red).
- offload.fetched: catch the bucket's error and return (a network error read as absent).
- offload.bucket_now: `OPENER["open"]` bound to open_bucket at import again (a patched open_bucket is not the one a
  fetch opens, so a test reaches the real store bucket with the runtime key, #81).
- offload.Bucket.put_new: drop `ChecksumSHA256=...` from put_object (no x-amz-checksum-sha256: Scaleway checks no
  sha256, it ignores x-amz-content-sha256, so a put changed at the right length lands: refused here), or in put_parts
  drop a part's `ChecksumAlgorithm`/`ChecksumSHA256` or the complete's per-part `ChecksumSHA256` (red, 2026-11-25).
- offload.Bucket: drop the `before-sign` registration of closed_after_expect (a put refused 412 before its body keeps
  its connection, the next request on it read as that body: every new blob after a "there" failed HTTP 400, #81).
- offload.store_policy: the runtime-locks Resource `{bucket}/*` (the runtime key may delete any blob), or the keeper
  statement dropped (the user applying it is shut out of the bucket).
- offload.push: `for tried in range(PUSH_TRIES):` -> `for tried in range(1):` (a put whose connection the bucket drops
  is never sent again: a pod's large output failed to reach the bucket, surfaces-paint@tube 2026-11-07).
- disk.least_used_over: drop the sort by st_atime (a capped store-evict evicts by name, a blob read since kept by none),
  or `if over <= 0: break` dropped (a cache under its cap evicted whole; this PC's 50 GB cache, 2026-11-19).
- disk.unread: a plain `open(path, "rb")` (store-evict's own scan of each blob moves its last-read time, so the cache's
  least-recently-used order is the scan's, not the runs').
"""
import hashlib
import json
import os
import time

import botocore.exceptions
import pytest

from score.conductor import disk
from score.store import Store, file_hash, offload, runtime_store


BUCKET_SENDS = [  # (the file's bytes, the bytes its sha256 was hashed from, its key, put_new's outcome, the requests)
    (b"body", b"body", "key", True, ["put"]),
    (b"bodx", b"body", "key", "InvalidRequest", ["put refused"]),  # changed after it was hashed: the bucket refuses it
    (b"0123456789", b"0123456789", "key", True, ["create", "part", "part", "part", "complete"]),
    (b"body", b"body", "taken", False, ["put there"]),  # a 412 before the body: its connection must not be reused
]
CREATED = (b"<InitiateMultipartUploadResult><Bucket>store</Bucket><Key>key</Key><UploadId>up</UploadId>"
           b"</InitiateMultipartUploadResult>")
TAKEN = b"<Error><Code>PreconditionFailed</Code><Message>taken</Message></Error>"
REFUSED = b"<Error><Code>InvalidRequest</Code><Message>checksum</Message></Error>"


class Answer:
    """A response body botocore reads (AWSResponse.raw)."""

    def __init__(self, body):
        self.body = body

    def stream(self, **_):
        yield self.body


def answered(request, sent):
    """The bucket's answer to `request` before it is sent, as Scaleway gives it: a put or part whose body does not
    hash to its x-amz-checksum-sha256 (or has none) refused; each request's kind and headers kept in `sent`."""
    from botocore.awsrequest import AWSResponse

    body = request.body or b""
    if hasattr(body, "read"):
        start = body.tell()
        body, _ = body.read(), body.seek(start)
    query = request.url.split("?", 1)[1] if "?" in request.url else ""
    headers = {name.lower(): value.decode() if isinstance(value, bytes) else value
               for name, value in request.headers.items()}
    summed = offload.checksum(hashlib.sha256(body).digest())
    if request.method == "PUT":
        kind = "part" if "partNumber=" in query else "put"
        if request.url.split("?", 1)[0].endswith("/taken"):  # If-None-Match: * on a taken key, answered before the body
            sent.append((f"{kind} there", headers))
            return AWSResponse(request.url, 412, {}, Answer(TAKEN))
        if headers.get("x-amz-checksum-sha256") != summed:
            sent.append((f"{kind} refused", headers))
            return AWSResponse(request.url, 400, {}, Answer(REFUSED))
        sent.append((kind, headers))
        return AWSResponse(request.url, 200, {"ETag": '"e"'}, Answer(b""))
    if request.method == "DELETE":
        sent.append(("abort", headers))
        return AWSResponse(request.url, 204, {}, Answer(b""))
    if query.startswith("uploads"):
        sent.append(("create" if headers.get("x-amz-checksum-algorithm") == "SHA256" else "create unchecked", headers))
        return AWSResponse(request.url, 200, {}, Answer(CREATED))
    listed = body.decode().count("<ChecksumSHA256>") == body.decode().count("<Part>")
    sent.append(("complete" if listed else "complete unchecked", headers))
    return AWSResponse(request.url, 200, {}, Answer(b"<CompleteMultipartUploadResult><ETag>\"e\"</ETag>"
                                                   b"</CompleteMultipartUploadResult>"))


class LostUploads(offload.FolderBucket):
    """A bucket that says it stored a blob and keeps nothing: the upload was lost on the way."""

    def put_new(self, path, key, sha):
        return True


class FailingFetch(offload.FolderBucket):
    """A bucket whose reads fail on the network."""

    def answer(self, key):
        raise ConnectionError("the bucket did not answer")

    def fetch(self, key, destination):
        raise ConnectionError("the bucket did not answer")


class Dropping(offload.FolderBucket):
    """A bucket that closes the connection on the first `drops` puts, as the store bucket did under load."""

    def __init__(self, root, drops):
        super().__init__(root)
        self.drops = drops

    def put_new(self, path, key, sha):
        if self.drops:
            self.drops -= 1
            raise botocore.exceptions.ConnectionClosedError(endpoint_url=f"https://bucket/{key}")
        return super().put_new(path, key, sha)


def stored(store, tmp_path, name, data):
    """An output of one file `name` holding `data` put in the store; (its output hash, its blob's sha256)."""
    folder = tmp_path / "made" / name
    folder.mkdir(parents=True)
    (folder / f"{name}.bin").write_bytes(data)
    return store.put_tree(folder), file_hash(folder / f"{name}.bin")


def test_a_blob_leaves_only_once_the_bucket_holds_it_and_comes_back_whole(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_store.FolderStore, "path", runtime_store.FolderStore.path)  # restored after
    monkeypatch.setattr(runtime_store.FolderStore, "exists", runtime_store.FolderStore.exists)
    monkeypatch.setattr(Store, "put_blob", Store.put_blob)
    monkeypatch.setattr(offload, "OPENER", {"open": None, "bucket": None})  # install's bucket undone after too

    # the bucket checks each body's sha256 itself (Scaleway honours x-amz-checksum-sha256, not x-amz-content-sha256):
    # a put carries the blob's sha256 hashed before the upload, each part its own, and botocore adds no crc32 of its
    # own; every request is answered before it is sent, as Scaleway would (a body off its checksum refused), none leaves
    real = offload.Bucket({"endpoint": "https://s3.example.invalid", "region": "fr-par", "bucket": "store",
                           "access_key": "key", "secret_key": "secret"})
    sent = []
    real.client.meta.events.register("before-send.s3", lambda request, **_: answered(request, sent))
    for body, hashed, key, landed, kinds in BUCKET_SENDS:
        sent.clear()
        (tmp_path / "upload").write_bytes(body)
        try:
            with monkeypatch.context() as small_parts:
                small_parts.setattr(runtime_store, "part_size", lambda size: 4)  # a 10-byte file in three parts
                outcome = real.put_new(tmp_path / "upload", key, hashlib.sha256(hashed).hexdigest())
        except botocore.exceptions.ClientError as error:
            outcome = error.response["Error"]["Code"]
        assert (outcome, [kind for kind, _ in sent]) == (landed, kinds), (body, sent)
        assert not any(name.lower().startswith(("x-amz-checksum-crc", "x-amz-trailer"))
                       for _, headers in sent for name in headers), sent  # no crc32 of botocore's beside it
        assert all(headers.get("connection") == "close" for _, headers in sent  # a request botocore may leave without
                   if headers.get("expect") == "100-continue"), sent  # its body never shares its connection after
    # its policy: the runtime key lists, reads and writes, deletes only under locks/; the keeper keeps every right
    policy = offload.store_policy("store", "app-1", "user-1")
    granted = [(statement["Principal"]["SCW"], action, resource) for statement in policy["Statement"]
               for action in statement["Action"] for resource in statement["Resource"]]
    runtime = [(action, resource) for principal, action, resource in granted if principal == "application_id:app-1"]
    assert all(statement["Effect"] == "Allow" for statement in policy["Statement"]), policy
    assert {action for action, _ in runtime} >= {"s3:GetObject", "s3:PutObject", "s3:ListBucket"}, runtime
    assert all(resource.startswith("store/locks/") for action, resource in runtime
               if action.startswith("s3:Delete") or action in ("*", "s3:*")), runtime
    assert ("user_id:user-1", "s3:*", "store/*") in granted and ("user_id:user-1", "s3:*", "store") in granted

    home =tmp_path / "home"
    store = Store.in_folder(home / "store")
    blobs = home / "store" / "objects" / "blobs"
    outputs = {name: stored(store, tmp_path, name, f"{name}-".encode() * 4096)  # no 64-hex word in any
               for name in ("free", "lost", "clash", "linked", "standing", "designed", "bad")}

    # push: sent once; a second put of the key is refused as there (412), the bytes kept as first sent
    bucket = offload.FolderBucket(tmp_path / "bucket")
    sha = outputs["free"][1]
    assert offload.push(blobs / sha, sha, bucket) == "sent"
    assert offload.push(blobs / sha, sha, bucket) == "there"
    assert offload.proven(bucket, sha, (blobs / sha).stat().st_size)
    assert not offload.proven(bucket, sha, 1) and not offload.proven(bucket, outputs["lost"][1], 1)

    # a put whose connection drops is sent again; one dropped every time raises the bucket's error
    monkeypatch.setattr(offload, "PUSH_PAUSE", 0)
    dropping = Dropping(tmp_path / "dropping", drops=3)
    assert offload.push(blobs / sha, sha, dropping) == "sent"
    assert offload.proven(dropping, sha, (blobs / sha).stat().st_size)
    with pytest.raises(botocore.exceptions.ConnectionClosedError):
        offload.push(blobs / sha, sha, Dropping(tmp_path / "dead", drops=offload.PUSH_TRIES))

    # a key that holds other bytes: the put is refused as there, and the answer does not prove it
    (tmp_path / "other.bin").write_bytes(b"other bytes")
    bucket.put_new(tmp_path / "other.bin", offload.blob_key(outputs["clash"][1]), outputs["clash"][1])

    # what the next run reads stays: a checkout's link, an accepted output, a blob a design file names
    store.checkout(outputs["linked"][0])
    (home / "store" / "objects" / "accepts" / "row@place").mkdir(parents=True)
    (home / "store" / "objects" / "accepts" / "row@place" / "a.json").write_text(json.dumps(
        {"output": outputs["standing"][0], "at": "2026-11-04T00:00:00+00:00", "by": "runner"}))
    (home / "design").mkdir()
    (home / "design" / "plan.json").write_text(json.dumps({"picture": outputs["designed"][1]}))
    memo = home / disk.HASH_MEMO / "0d8b71ba"  # kept.py's hash memo names a blob it never reads: it keeps nothing
    memo.parent.mkdir(parents=True)
    memo.write_text(json.dumps({"raw": outputs["free"][1], "clean": [str(home)]}))
    job = home / disk.KEPT_JOBS / "slot" / "content" / "done"  # a kept job's blob: fetched back when a rerun places it
    job.parent.mkdir(parents=True)
    job.write_text(json.dumps({"files": {"frame.png": [outputs["lost"][1], 1]}}))

    dry = disk.store_evict(home, dry=True, repo=tmp_path / "repo", say=lambda line: None)
    assert dry["refused"] is None and dry["evicted"] == 4 and dry["sent"] == 0, dry  # free, lost, clash, bad
    lost = LostUploads(tmp_path / "bucket")
    done = disk.store_evict(home, repo=tmp_path / "repo", bucket=lost, say=lambda line: None)
    assert done["kept"][disk.UNPROVEN] == 3 and done["evicted"] == 1 and not done["failed"], done
    held = {path.name for path in blobs.iterdir()}
    assert outputs["free"][1] not in held  # proven: gone here, marked
    assert {outputs[name][1] for name in ("lost", "clash", "linked", "standing", "designed", "bad")} <= held
    assert offload.mark_of(home / "store" / "objects", outputs["free"][1]).is_file()

    done = disk.store_evict(home, repo=tmp_path / "repo", bucket=bucket, say=lambda line: None)
    assert done["evicted"] == 2 and done["kept"][disk.UNPROVEN] == 1, done  # lost and bad now held; clash never
    assert outputs["clash"][1] in {path.name for path in blobs.iterdir()}

    # fetch on demand: a checkout of an evicted output gets its blob back, checked, read-only, its mark removed
    offload.install(lambda: bucket)
    assert store.objects.exists(offload.blob_key(outputs["lost"][1]))  # counted present without a fetch
    assert not (blobs / outputs["lost"][1]).exists()
    folder = store.checkout(outputs["lost"][0])
    assert (folder / "lost.bin").read_bytes() == b"lost-" * 4096
    assert (blobs / outputs["lost"][1]).stat().st_mode & 0o777 == 0o444
    assert not offload.mark_of(home / "store" / "objects", outputs["lost"][1]).exists()

    # a blob missing with no mark (a PC that pulled a listing without it) is asked of the bucket and read; a 404 absent
    standing = outputs["standing"][1]  # sent to the bucket by store-evict above, kept here
    (blobs / standing).unlink()
    assert store.objects.read_bytes(offload.blob_key(standing)) == b"standing-" * 4096
    assert not store.objects.exists(offload.blob_key("0" * 64))

    # a fetched blob whose bytes are not its name is refused after a second try; nothing lands
    bad = outputs["bad"][1]
    os.chmod(tmp_path / "bucket" / "blobs" / bad, 0o644)
    (tmp_path / "bucket" / "blobs" / bad).write_bytes(b"cut short")
    with pytest.raises(offload.BlobMismatch):
        store.objects.read_bytes(offload.blob_key(bad))
    assert not (blobs / bad).exists() and not list(blobs.glob("*.partial"))

    # install with no opener opens the bucket by open_bucket's name at the first fetch: one patched after is used
    offload.install()
    monkeypatch.setattr(offload, "open_bucket", lambda: bucket)
    assert offload.bucket_now() is bucket

    # a network error is never read as absent: it propagates, the blob still marked
    offload.install(lambda: FailingFetch(tmp_path / "bucket"))
    with pytest.raises(ConnectionError):
        store.checkout(outputs["free"][0])
    assert store.objects.exists(offload.blob_key(outputs["free"][1]))
    (blobs / standing).unlink()
    with pytest.raises(ConnectionError):  # an unmarked miss is asked too, and the bucket's error propagates
        store.objects.read_bytes(offload.blob_key(standing))
    new, sha = stored(store, tmp_path, "new", b"new-" * 4096)  # a write never asks the bucket
    assert (blobs / sha).is_file() and store.listing(new) == {"new.bin": sha}

    # a capped cache (this_pc.py's CACHE_GB, 2026-11-19): store-evict evicts the least recently read first, only until
    # what stays fits under the cap; its own scan of the blobs leaves their read times as the runs left them
    cached = tmp_path / "cached"
    made = sorted(stored(Store.in_folder(cached / "store"), tmp_path, name, f"{name}-".encode() * 4096)[1]
                  for name in ("c1", "c2", "c3"))
    held_here = cached / "store" / "objects" / "blobs"
    now = time.time()
    for sha, days in zip(made, (2, 5, 9)):  # the first by name read last; each read over a day ago
        os.utime(held_here / sha, (now - days * 86400, (held_here / sha).stat().st_mtime))
    cap_gb = 1.5 * (held_here / made[0]).stat().st_size / 1e9  # one and a half blobs: two go
    dry = disk.store_evict(cached, dry=True, repo=tmp_path / "repo", cap_gb=cap_gb, say=lambda line: None)
    assert dry["evicted"] == 2, dry
    done = disk.store_evict(cached, repo=tmp_path / "repo", bucket=offload.FolderBucket(tmp_path / "cache-bucket"),
                            cap_gb=cap_gb, say=lambda line: None)
    assert done["sent"] == 3 and done["evicted"] == 2 and not done["failed"], done
    assert {path.name for path in held_here.iterdir()} == {made[0]}  # the most recently read stays
