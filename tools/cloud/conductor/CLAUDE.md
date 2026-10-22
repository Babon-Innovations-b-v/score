# tools/cloud/conductor/

The conductor as code: one always-on Scaleway CPU machine of our own (project `score-conductor`, zone fr-par-2,
named and tagged `score-conductor`) that holds the store, the design, the ledgers, the dashboard home and the
runner, with sync, the listener, resume and every free step. `machine.py`'s docstring is the contract: what `up`
makes, the rights of the two keys, and what is still unchecked until the first `up`.

- **`machine.py`** `up | move | status | grow | shrink | stop | down | price | dry`. `up` costs money and is the owner's
  command alone: it refuses in an agent's process (the store's agent markers, imported from `score.store`), puts no
  key in user-data or the repo, and pipes the conductor's one credential over ssh. `up --dry` and `dry` are
  free and open to agents: they print every scw call and make none. `up` also pipes the sizes record
  (`SIZES`, to `~/.config/score/conductor.json`, `SCORE_CONDUCTOR_RECORD`) and writes `SCORE_CONDUCTOR_SIZE_URL`
  into the env file; `move` (the owner's, once, after `up`) backs this PC's home up tagged pc-final, then over ssh
  restores it (`migrate --onto-conductor` merges the sizes into `machine.json`, which makes it a conductor) and only
  then installs the sync and listener (`install-sync --no-pull`). score-resume (a drop-in boot.sh writes) and
  score-health wait for that machine.json: both write into the home the restore needs empty. Every scw call names its zone or region, every
  list and create the project; a record's own project id is checked before it is used or deleted.
- **Never tag the conductor `farm-factory-batch`**: the runner's leftover sweeps delete by that tag. The conductor
  lives in its own project so its hourly bill never enters the batch project's spend or a batch's 10% buffer.
- **`size_function/`** (standard library only; deployed as `handler.py` and `s3.py` alone): grow or shrink between
  exactly the two sizes, for the one server id in its own env. Either way it powers the server off, so it refuses
  both, while the server runs, when the health record (`health/conductor.json` in the backup bucket, written every
  minute by `health_push.py`) shows a live run claim, a parked paid machine or a frozen worktree a process works in
  (a waiting-for-size run's own copy left out: it waits for that grow), or is over 10
  minutes old (a power cycle mid-run cuts the run and orphans its rented machines); a refused type change still
  powers the server back on. `health_push.py` pushes nothing when the claims file does not parse, so the record
  goes stale rather than idle.
- **The data volume's bare mountpoint is immutable** (`chattr +i`, boot.sh): with `nofail`, a boot where the volume
  does not attach fails every writer there instead of starting an empty store on the root disk.
- **`cloud-init.yaml` + `boot.sh`**: user score (uid 1100) with linger, the data volume formatted only when blank
  and mounted at `/home/score/.farm-factory-props` by UUID, restic, uv, scw and the Google Cloud CLI pinned by
  version and SHA-256 (a new pin: a version at least two weeks old, its checksum from the release's own sums file),
  the checkout over https, `uv sync`, every unit in `units/` installed for user score.
- **Secrets**: one credential on disk, `/home/score/.config/scw/config.yaml` (mode 600). Everything else by name
  through `/usr/local/bin/score-secret-reader` (`secret_reader.sh`: the project id found by its name,
  `SCORE_SECRETS_PROJECT`); the file-shaped ones (`score-lib-deploy-key`, `google-billing-reader`) only on tmpfs at
  `/run/user/1100/score` (`secrets.sh`, `score-secrets.timer`), gcloud's config with them.
- **The agents' door** (`agent_door.sh` -> `agent_door.py`): the forced command of the agents' authorized_keys
  line. It runs only status, plan, price, resume --dry, a detached free run, logs, grant_benchmark and a benchmark
  run tagged with its grant, as an argument list (never a shell), every agent marker set; anything else is refused
  with the reason. The owner's key must have a passphrase (`up` refuses one without), so an agent on his PC cannot
  reach a shell past the door.
- **`units/`**: `score-resume.service` (the one template for every machine; the PC copies it), `score-secrets`,
  `score-update` (the checkout follows the hosted cockpit's pinned commit from `/healthz` `commit`, else origin/main
  forward only, never while score starts from the checkout), `score-health`. Other areas add their own units here;
  `boot.sh` installs whatever is in the folder, filling the deploy templates' slots for user score.
- Tests (free, no cloud; each file well under 120 s): `machine_test.py` (cloud-init schema, `systemd-analyze --user
  verify`, `up --dry`, boot.sh against a temp root, the door), `update_test.py`, `health_push_test.py`,
  `size_function/handler_test.py` (with AWS's SigV4 example).
