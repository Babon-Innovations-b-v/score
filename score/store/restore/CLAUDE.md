# score/store/restore/

The free-only restore of a lost store (#13; the old WSL disk took the store, both spend ledgers and the runner's keys
on 2026-10-19). `python -m score.store.restore <environment> --library <score_lib>` drives the environment's lines
with `FreeRunner`, the runner made unable to spend, and prints one summary line; the detail is in
`$PROPS_WORK/restore/<utc>.json`. Its docstrings hold the contract.

- **Today's key and today's gates decide; nothing is accepted by hand.** The prop route and the method were hardened
  a lot since most outputs were made, so most must be made again and nothing old may look current. A paid node is
  never made (`cleared` raises Blocked, covering paid makes and paid gatherers); an old paid output stands again only
  when its node's key today equals the `record_key` the library holds for it, the bucket's checkout rebuilds to its
  exact output hash, and the runner's own `run_held` judges it with today's gates and accepts it on a pass. Never
  write a record, judgement, evidence, accept, reject, waiver, clearance, spend yes, registry entry or stop line from
  the bucket or from the library's `accept{}`.
- **It runs only while paid work is shut** (`ledger.books_refusal` gives a reason) and takes the store's run claim.
  The process is free only (`guard_free_only`: SCORE_FREE_ONLY=1, and no Blender started from it). The Blender guard
  lives here, not in `tools/review/renders.py` or `tools/blender/`, which are in rows' keys.
- **Counting is the default; downloading is the owner's own.** Without `--reattach` a key match is only counted
  ("would re-attach"); `--reattach --max-gb N` is refused in an agent's process (the egress price is unknown and the
  yes is the owner's), downloads one tar at a time into a new empty folder, unpacks it with tarfile's data filter and
  deletes it after. `--index-checkouts` reads only each hex-named `inputs/<sha>.tar`'s first 8 KB.
- **Never downloaded:** `runs/`, `weights/`, `code/`, `kernels/`, library blobs, view sets, `.glb` files and place USD:
  no key proves any of them is today's. An old-route output stays a hole (#12, `score/stages/complete/holes`).
- Tests: `restore_test.py` drives a toy table on `Store.in_folder` with a folder bucket; every paid point fails the
  node that reaches it. Never against the real bucket.
