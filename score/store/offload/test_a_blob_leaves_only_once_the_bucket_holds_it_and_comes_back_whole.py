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
- offload.fetching_path: return PLAIN_PATH at once (an evicted blob is never fetched; the checkout fails), or
  missing_sha's miss asked only when marked (a PC that pulled a listing without its blob cannot read it: red).
- offload.install: drop the as_a_write wrap of Store.put_blob (a new blob's write asks the bucket; a bucket that
  fails on the network fails the write: red).
- offload.fetched: catch the bucket's error and return (a network error read as absent).
- offload.push: `for tried in range(PUSH_TRIES):` -> `for tried in range(1):` (a put whose connection the bucket drops
  is never sent again: a pod's large output failed to reach the bucket, surfaces-paint@tube 2026-11-07).
"""
import json
import os

import botocore.exceptions
import pytest

from score.conductor import disk
from score.store import Store, file_hash, offload, runtime_store


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
    home = tmp_path / "home"
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
