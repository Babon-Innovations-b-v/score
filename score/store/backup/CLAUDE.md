# score/store/backup/

The store's backups and the one-time move of the store's machine from the PC to the conductor
(`python -m score.store.backup backup|forget|check|restore|manifest|migrate`; the package docstring has the commands,
`_migrate.py`'s the move). restic into the repository `SCORE_BACKUP_REPO` names (on the conductor an `s3:` bucket in
nl-ams, made by `tools/cloud/conductor/machine.py up`); its units are `tools/cloud/conductor/units/score-backup*`.

- **The password is read by name, never a file**: the secret `score-backup-restic-password` through
  `SCORE_SECRET_READER`, into restic's environment only; `RESTIC_PASSWORD_FILE` and `_COMMAND` are dropped. An `s3:`
  repository's key comes from `scw config get access-key|secret-key`, the machine's one credential on disk.
- **What a backup holds**: `$PROPS_HOME` minus `_core.REBUILT` (cache, store/cache, tmp, tmp.*, downloads, frozen, env,
  store-tests, blender-mcp), the volume's `lost+found` (root's, mode 700: restic cannot open it) and `*.partial`. Each SQLite database under `dashboard/` is held as its SQLite online-backup
  copy (`_staging`: Python's `Connection.backup`, the API the CLI's `.backup` runs; no sqlite3 CLI needed), staged in
  `backup-staging/` inside the home, the live file and its -wal, -shm and -journal left out; a restore moves each copy
  back to its own path. A copy of one state is the same bytes every time, so its hash names the database's state.
- **The manifest** (`_manifest.py`): the store's `listing_hash` over `store/objects` (with its listing, so a mismatch
  names objects), and sha256 and size of every file in design, cloud, runs, dashboard (databases as copies) and work.
  It reads the store only through its public `tree_listing` and `listing_hash`; never edit `score/store/__init__.py` or
  `durable.py` from here (every stage's key holds them).
- **Every command leaves one record**, an unforeseen failure's too (then it propagates), `$PROPS_HOME/logs/backup-<UTC stamp>.json`: `{at, kind, ok, snapshot, files,
  bytes, seconds, error, detail}`. `score.conductor health` reads the newest of kind `backup` for the last backup's
  age and result: keep those keys. Kinds: backup, forget, check, check-data, restore, manifest, migrate-<mode>.
- **A plain backup is refused until `machine.json` exists** (the move writes it), so a fresh conductor's timer never
  backs up an empty home, and the move's emptiness check lets those refusals' logs (`logs/backup*`) and the volume's
  `lost+found` stand.
- **The move is the owner's** (`migrate`, every mode refused in an agent's process): `--from-pc` refuses while
  score-sync (service or timer), score-listen or score-resume is active or a claim in `runs/active.json` is alive;
  `--onto-conductor` refuses a home not empty, restores the newest `pc-final`, compares the manifests and stops on any
  difference, listed in the log, nothing put back by hand; `--pc-test-home` restores work/ and design/ read-only into
  an empty PC home (env/ is bootstrap.sh's). `forget` always keeps `pc-final`.
- **Never against the cloud from a test or an agent**: `test_a_backup_brings_the_home_back_whole.py` uses a folder repository, a shim secret reader
  and a shim systemctl; its restic tests skip only where restic is not installed.
