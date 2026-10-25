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
  into the env file; `move` (the owner's, once, after `up`) first disables and stops this PC's sync timer, listener and
  resume (`PC_UNITS`: one store only, a reboot never starts a second one here), backs this PC's home up tagged pc-final
  (the backup's password read through `secret_reader.sh` from `SCORE_SECRETS_PROJECT`, where the conductor reads it), then over ssh
  restores it (`migrate --onto-conductor` merges the sizes into `machine.json`, which makes it a conductor) and only
  then installs the sync and listener (`install-sync --no-pull`). score-resume (a drop-in boot.sh writes) and
  score-health wait for that machine.json: both write into the home the restore needs empty. Every scw call names its zone or region, every
  list and create the project; a record's own project id is checked before it is used or deleted.
- **`prepare.sh [--dry]`** (free, before the first `up`, idempotent: what exists is kept and said): the project
  score-conductor, both IAM applications with their policies and API keys, the size token, the restic password, the
  sync token's copy and score_lib's deploy key (gh), each secret piped into Secret Manager through a file in
  `/dev/shm`, never shown. The conductor's own key goes into `score-conductor-key` in score-conductor itself, which
  no key but the owner's may read (the conductor's reads secrets in the batch project only, the size key and the
  runtime key none); `up` reads it by name and pipes it over ssh, else asks as before. `--dry` prints every call;
  `machine_test.py` checks it and a second run against an scw holding everything (no create).
- **`google-billing-reader` is optional**: `secrets.sh` reads it `--if-present` (`secret_reader.sh`); without it,
  it leaves `google-billing-reader.note` on the tmpfs, `score.conductor.health` carries every note to the Machine
  card (the Machine link's hover text), and the books' Google read-back stays unread. A failed read still fails.
- **Never tag the conductor `farm-factory-batch`**: the runner's leftover sweeps delete by that tag. The conductor
  lives in its own project so its hourly bill never enters the batch project's spend or a batch's 10% buffer.
- **`size_function/`** (standard library only; deployed as `handler.py` and `s3.py` alone): grow or shrink between
  exactly the two sizes, for the one server id in its own env. Either way it powers the server off, so it refuses
  both, while the server runs, when the health record (`health/conductor.json` in the backup bucket, written every
  minute by `health_push.py`) shows a live run claim, a parked paid machine or a frozen worktree a process works in
  (a waiting-for-size run's own copy left out: it waits for that grow), or is over 10
  minutes old (a power cycle mid-run cuts the run and orphans its rented machines); a refused type change still
  powers the server back on. It lifts the server's protection first (Scaleway refuses to power off a protected
  server) and sets it again in every path. `status` reads the health record with the conductor's own key
  (`bucket_key`): this PC's key belongs to another project and gets 403. `health_push.py` pushes nothing when the claims file does not parse, so the record
  goes stale rather than idle.
- **The data volume's bare mountpoint is immutable** (`chattr +i`, boot.sh): with `nofail`, a boot where the volume
  does not attach fails every writer there instead of starting an empty store on the root disk.
- **`cloud-init.yaml` + `boot.sh`**: user score (uid 1100) with linger, the data volume formatted only when blank
  and mounted at `/home/score/.farm-factory-props` by UUID, restic, uv, scw and the Google Cloud CLI pinned by
  version and SHA-256 (a new pin: a version at least two weeks old, its checksum from the release's own sums file),
  the checkout over https, `uv sync`, every unit in `units/` installed for user score; rsync, ssh and ffmpeg from apt (the runners'
  copies, the sound rows' loudness), Node.js pinned by version and SHA-256 into /usr/local (the 3D web copies' gltfpack,
  the film preview's Playwright, which takes node >=20: Ubuntu's apt node is older), score_lib's `score-lib` linked into
  ~/.local/bin (on the env file's PATH) for the cockpit's lock and withdraw. Once machine.json is there,
  the user part syncs the prop environment `$PROPS_HOME/env` (the rows' PROPS_PYTHON: rough-model, people, surfaces;
  left out of every backup) from uv.lock with bootstrap.sh's command (`boot.sh env`, which the move runs after its
  restore), and score_lib's `.venv` (its `score-lib` command, which library_files.py runs). **Every boot** runs the
  root oneshot `score-boot.service`: the checkout cloned when missing and moved to origin/main as score, `boot.sh
  system` (`/var/log/score-boot-system.log`), then `boot.sh user` as score (`/var/log/score-boot-user.log`). cloud-init's
  `bootcmd` (every boot, before D-Bus is up, so files only) writes the unit and a per-boot script; cloud-init's final
  stage runs that script (bus up), which enables the unit and starts it when this boot has not. A live server gets it
  by `machine.py user-data [--dry]` (sets its user-data key `cloud-init` to the rendered template; users and
  write_files do not run again) and a reboot. `boot.sh system` stops with a clear message without the system bus,
  and names the line of any failing command. Between boots `update.py` syncs the prop environment whenever it is missing and with `.venv` on a uv.lock change. The first Buy on the conductor (2026-10-24, checkout 4)
  failed for want of it.
- **Secrets**: one credential on disk, `/home/score/.config/scw/config.yaml` (mode 600). Everything else by name
  through `/usr/local/bin/score-secret-reader` (`secret_reader.sh`: the project id found by its name,
  `SCORE_SECRETS_PROJECT`); the file-shaped ones (`score-lib-deploy-key`, optional `google-billing-reader`) only on tmpfs at
  `/run/user/1100/score` (`secrets.sh`, `score-secrets.timer`), gcloud's config with them.
- **The agents' door** (`agent_door.sh` -> `agent_door.py`): the forced command of the agents' authorized_keys
  line. It runs only status, plan, price, resume --dry, a detached free-only run (`score run ... --free`: every free row for real, paid rows left for the Buy), logs (`score.conductor logs`: the run
  logs, fault reports, unit journals and the boot logs /var/log/score-boot-{system,user}.log, secrets left out), health (read only), checkouts, gaps <node> (a node's batch gaps, read only), buy-yes and buy <yes id> (the owner's Buy
  approved in a session, score/dashboard/checkout/chat_yes.py), grant_benchmark and a benchmark
  run tagged with its grant, as an argument list (never a shell), every agent marker set; anything else is refused
  with the reason. The owner's key must have a passphrase (`up` refuses one without), so an agent on his PC cannot
  reach a shell past the door.
- **`units/`**: `score-resume.service` (the one template for every machine; the PC copies it), `score-secrets`,
  `score-update` (the checkout follows the hosted cockpit's pinned commit from `/api/sync/pin` `commit` with the sync
  token, never `/healthz`, whose body babon's Caddy writes itself; a pin it cannot read moves nothing, a cockpit
  reporting none falls back to origin/main forward only; never while a run starts from the checkout or a process
  works in a frozen copy (a live run: the move goes on at the first tick after it ends), nor a uv.lock change while a
  sync pass runs (a pass is not a run: counted as one, it kept the
  checkout on an old commit all of 2026-10-25's morning, as passes run back to back), which links this checkout's `.venv`), `score-health`. The sync
  pass runs the same update first (its ExecStartPre, rendered by `install-sync --no-pull`; two calls take turns on
  `.git/score-update.lock`): a pass outlasts its 5-minute timer, so with score-update's timer alone a pass was always
  running and the live conductor's checkout sat on an old commit for hours (2026-10-24); the timer stays for an idle
  conductor. **Hand fix to undo:** the live conductor's user-data carries a hand-written `bootcmd` (2026-10-24/25:
  fetch and check out origin/main, the prop environment's `uv sync`, and `boot.sh system` then `user`, which died there
  for want of D-Bus). After a batch ends: `python3 tools/cloud/conductor/machine.py user-data --agent-key
  ~/.ssh/score_conductor_agents.pub` (from this PC with the owner's scw profile; `--dry` first), then a reboot; check
  the boot logs through the door, then delete this note. Unless done already, the sync unit's own fix still needs, as
  score: `systemctl --user stop score-sync.timer`, wait for `systemctl --user is-active score-sync.service` to say
  inactive, `/usr/bin/python3 -I ~/projects/score/tools/cloud/conductor/update.py --repo ~/projects/score`, then
  `cd ~/projects/score && .venv/bin/python -m score.dashboard install-sync --env-file ~/.config/score/dashboard.env
  --no-pull`, and `grep ExecStartPre ~/.config/systemd/user/score-sync.service` names update.py. Other areas add their own units here;
  `boot.sh` installs whatever is in the folder, filling the deploy templates' slots for user score.
- Tests (free, no cloud; each file well under 120 s): `machine_test.py` (cloud-init schema, `systemd-analyze --user
  verify`, `up --dry`, boot.sh against a temp root, the door), `update_test.py`, `health_push_test.py`,
  `size_function/handler_test.py` (with AWS's SigV4 example).
