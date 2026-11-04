# score/store/offload/

The store's blobs in the store bucket (#74, first slice; the owner's answers of 2026-11-02): a blob goes to the
bucket once, its local copy is evicted only once the bucket answers for it with its size and sha256, and an evicted
blob is fetched back on its first read. Only `store/objects/blobs/<sha256>` moves; every other object stays local.
The package docstring is the contract.

- **Never edit `score/store/__init__.py` or `tools/cloud/runtime/store.py` from here**: both are in every row's code
  version (44 paid rows re-keyed once). This folder is framework-only (`score/graph/_code.py` FRAMEWORK), installed
  beside `durable.install()` in the Runner and `score/review` only; nothing a stage runs imports it. After a change,
  `.venv/bin/python -m score.stages.moved HEAD` must move no paid row.
- **The bucket**: the backend's `RUN_STORE_BUCKET` (`score-<project>-store`, fr-par, Scaleway's default class there,
  Multi-AZ; versioning never turned on), made once by hand on 2026-11-04, never by the code. Its key is the runtime
  key, read by name (`score-cloud-runtime-key`); no key, account or project id in code.
- **Writes are conditional** (`If-None-Match: *`, PutObject or CompleteMultipartUpload; a failed multipart upload is
  aborted): a 412 means the key is taken, for a blob the same bytes. Each object carries its sha256 as metadata,
  from the bytes hashed just before the upload. Probed 2026-11-04 from this PC: the second put and the second
  complete both 412, HEAD gives the size and the metadata, a missing key 404.
- **Evicting**: `score/conductor/disk.py` store-evict picks which blobs (one link, nothing but output listings naming
  them, no output a node stands on, no text naming blobs, no run live) and calls `proven` then `evict`. The mark
  `store/evicted/<sha256>` is written and synced before the copy goes.
- **Fetching**: `install()` patches FolderStore's `path` and `exists` for marked blobs only; a blob missing with no
  mark stays missing, so a new blob's write never asks the bucket. A sha256 mismatch is fetched once more, then
  `BlobMismatch`; a network error propagates, never read as absent.
- Tests: `test_a_blob_leaves_only_once_the_bucket_holds_it_and_comes_back_whole.py`, a local folder bucket
  (`FolderBucket`), never the cloud.
