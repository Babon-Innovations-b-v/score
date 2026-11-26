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
  complete both 412, HEAD gives the size and the metadata, a missing key 404. A single put sends its file with
  botocore's `Expect: 100-continue`; on the 412 botocore sends no body yet keeps the connection, and the bucket read
  the next request on it as the promised body (HTTP 400, no code: every new blob after a "there", #81, 2026-11-25).
  So every request carrying that Expect also says `Connection: close` (`closed_after_expect`, on `before-sign`): one
  request per push still, a fresh connection per put, right on the race too. Parts and the complete send bytes
  whole, no Expect, and keep their connection.
- **What the bucket checks** (#81, probed 2026-11-25): Scaleway verifies `x-amz-checksum-sha256` (a put whose body
  does not hash to it is refused `InvalidRequest`) and ignores `x-amz-content-sha256` (a signed put with a wrong
  payload hash landed), so payload signing is not used. A single put sends `ChecksumSHA256`, the base64 of the sha256
  offload hashed from the local copy before the upload: the bucket refuses bytes that changed after that hash. A
  multipart upload is created with `ChecksumAlgorithm="SHA256"`, each part sends the sha256 of the chunk as read and
  the complete lists each part's: that covers each part in transit, not a file changed between the hash and the read
  (only a ranged-read or the fetch's own sha256 check would). Whether Scaleway checks the per-part sums the same way
  is not yet probed. `request_checksum_calculation="when_required"` keeps botocore 1.36+ from adding a crc32 trailer
  to a request that carries no sum of ours. The test answers each request before it is sent (a `before-send` hook,
  no network) as Scaleway would: a body off its checksum refused.
- **The policy** (`store_policy`, applied by `Bucket.put_policy` with the keeper's own key, never the runtime key's):
  Scaleway's 2023-04-17 version allows only what it lists, so it has no Deny; the runtime application lists, reads
  and writes, and deletes only under `locks/`; the keeper user keeps every right. No condition key reads
  If-None-Match, so overwrites stay refused only by the conditional puts. Applied 2026-11-25 (#81). Policy actions
  follow the runtime application's IAM permission set, not the policy: since 2026-11-26 (#81, the owner's yes) that
  set is ObjectStorageObjectsRead, ObjectStorageObjectsWrite, ObjectStorageObjectsDelete and ObjectStorageBucketsRead
  in place of ObjectStorageFullAccess, so the runtime key can no longer read, put or delete the policy.
- **Evicting**: `score/conductor/disk.py` store-evict (its own command and the door's verb, never the sweep) picks which blobs (one link, nothing but output listings naming
  them, no output a node stands on, no text naming blobs, no run live) and calls `proven` then `evict`. The mark
  `store/evicted/<sha256>` is written and synced before the copy goes.
- **Fetching**: `install()` patches FolderStore's `path` and `exists`: any missing blob, marked or not (a PC that
  pulled a listing without its blob), is asked of the bucket on a read, HEAD then GET, a 404 alone absent. A write
  (`Store.put_blob`, wrapped by `install()`) never asks. A sha256 mismatch is fetched once more, then `BlobMismatch`;
  a network error propagates, never read as absent. `open_bucket` raises `BucketUnreachable`, never SystemExit.
- Tests: `test_a_blob_leaves_only_once_the_bucket_holds_it_and_comes_back_whole.py`, a local folder bucket
  (`FolderBucket`), never the cloud.
