# tools/cloud/conductor/

The conductor as code: one always-on Scaleway CPU machine of our own (project `score-conductor`, zone fr-par-2,
named and tagged `score-conductor`) that holds the store, the design, the ledgers, the dashboard home and the
runner, with sync, the listener, resume and every free step. `machine.py`'s docstring is the contract: what `up`
makes, the rights of the two keys, and what is still unchecked until the first `up`.

- **`machine.py`** `up | move | status | grow | shrink | stop | down | price | dry | grow-data`. `grow-data <GB> --owners-yes "<his words>"` grows the data volume on his recorded yes, its order ledgered with his words first; boot.sh's `resize2fs` gives the file system the room at the next boot. `up` costs money and is the owner's
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
  `test_owner_gates_and_safe_moves.py` checks it and a second run against an scw holding everything (no create).
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
  version and SHA-256 (a new pin: its checksum from the release's own sums file),
  the checkout over https, `uv sync`, every unit in `units/` installed for user score; rsync, ssh, ffmpeg, g++, make and cmake from apt (the runners'
  copies, the sound rows' loudness, a compiler: Kimodo's motion correction builds with CMake), Node.js pinned by version and SHA-256 into /usr/local (the 3D web copies' gltfpack,
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
  and names the line of any failing command. Between boots `update.py` syncs the prop environment whenever it is missing and with `.venv` on a uv.lock change, and gives score_lib's checkout the committer `SCORE conductor <conductor@score.invalid>` in its own git config when it has no user.email (2026-10-28: boot.sh's clone had none, so every library commit failed). The first Buy on the conductor (2026-10-24, checkout 4)
  failed for want of it.
- **Secrets**: one credential on disk, `/home/score/.config/scw/config.yaml` (mode 600). Everything else by name
  through `/usr/local/bin/score-secret-reader` (`secret_reader.sh`: the project id found by its name,
  `SCORE_SECRETS_PROJECT`); the file-shaped ones (`score-lib-deploy-key`, optional `google-billing-reader`) only on tmpfs at
  `/run/user/1100/score` (`secrets.sh`, `score-secrets.timer`), gcloud's config with them. The tenant cluster (owner's
  yes, 2026-11-06), optional: `score-k8s-kubeconfig`, the login of a service account on babon's cluster scoped to
  score's namespaces (score, score-jobs: jobs, pods, logs, events, secrets; nodes read; never an admin's login), and
  `score-k8s-settings`, its SCORE_K8S_* lines, land there as `k8s-kubeconfig` and `k8s.env`; the door adds those
  lines (SCORE_K8S_* only) and the login's path to every command's environment (`agent_door.cluster_values`), boot.sh
  installs a pinned kubectl, and `cluster-check` says whether the cluster answers.
- **Claude Code** (owner's yes, 2026-11-05: the finish route's `claude -p` rows run here): boot.sh's user part
  (`install_claude`, also `boot.sh claude`) installs `CLAUDE_PIN` with npm into `~/.local/lib/claude-code`, off the
  PATH; `claude_login.py link` (secrets.sh, every boot and hour) links `~/.local/bin/claude` to `claude_login.py` only
  while that CLI is there and `claude-code-oauth-token` reads, else the adapter's NotHere stands; run as `claude`, it
  reads the login by name through the secret reader at each call and execs the CLI with it in
  `CLAUDE_CODE_OAUTH_TOKEN` alone, never a file, log or argument. FRAMEWORK (`score/graph/_code.py`): no row re-keys.
- **The agents' door** (`agent_door.sh` -> `agent_door.py`): the forced command of the agents' authorized_keys
  line. It runs only status, plan, price, preflight <environment> [--phase P] (a phase's free check before it is queued: plan, imports, warm pool, stock; read only, 2026-11-06), lock-phase <environment> <phase> [--place P ...] (the phase's stages standing accepted now, at those places, locked so a later code change keeps them: `score lock-phase`, the runner's bookkeeping; 2026-11-06), cluster-check (whether this box reaches the tenant cluster, read only), resume --dry, a detached free-only run (`score run ... --free`: every free row for real, paid rows left for the Buy), logs (`score.conductor logs`: the run
  logs, fault reports, unit journals and the boot logs /var/log/score-boot-{system,user}.log, secrets left out), health (read only), disk (free room, the biggest folders and the whole data disk accounted for, read only), sweep (the data disk's routine sweep, every step under its warning line, `score/conductor/disk.py`), store-gc [--dry] (with no run live, the store's blobs nothing names), store-evict [--dry] (with no run live, blobs into the store bucket, the proven ones nothing here reads evicted, #74), clean-frozen (removes the frozen copies no run needs, `score/conductor/disk.py`), relink-pixal (work/pixal's files the store holds made links to its blobs), offload-pixal (with no run live, work/pixal's takes into score_lib, freed once read back whole), score-lib status | pull (score_lib's checkout after a fetch against its origin, the newest push its reflog holds; pull fast-forwards only, refused on local changes or commits, `score/conductor/library_checkout.py`), checkouts, gaps <node> (a node's batch gaps, read only), job-log <path> (a cloud job's log under a frozen home's
  `work/cloud`, as a fault report names it, its tail capped, read only), run-log [--lines N] (the newest launch's own run log, the path its handles record, default 200 lines, at most 2000, secrets left out, read only), pool-log [--lines N] (the newest launch's warm pool collector log, read only, 2026-11-05), fault <node> (the node's fault report `<copy>.home/store/faults/<node>.txt` of the newest launch's home, the node name checked so no path leaves the faults folder, read only), design-file <design/props|plans|surfaces/name.json> (one design file, read only, size-capped, no link out of design/; 2026-11-03), batch-money [--no-film] (what a Buy question names, read only; --no-film prices this try without the demo films' rows), store-pull and store-push [--missing] (`this_pc.py`'s copy of the store: a tar stream each way, the pull only the run's folders, store/objects, design, work, cloud/google-cache, cache/library, less what the PC's manifest on stdin already holds; the push only adds regular files under store/objects and work, linked in from tmp/ so a file already there is kept, an absolute path, `..`, a link or a path out of those folders refused; owner, 2026-10-27: the door route, never his key on the conductor; `store-push --differs` names the work/pixal files held here with other bytes and `--replace` puts the PC's in place, only under work/pixal/, never while a run is live, each old file kept under work/pixal/replaced/<time>/, 2026-11-03), buy-yes [--no-film] --batch-total and buy <yes id> [--phase <phase>,...] [--leave-out <stage>,...] [--cluster <kind>,...] (the owner's Buy, --phase only those phases' rows of the basket under the same yes and batch total, its log named with the phases (score/stages/phases, 2026-11-06), --leave-out stages it neither buys nor makes, --cluster its run's job kinds sent to the tenant cluster (SCORE_CLOUD=k8s, SCORE_CLOUD_KINDS), refused unless cluster-check passes: the env file's SCORE_K8S_PROVIDER scaleway/tenant, SCORE_K8S_CONTEXT, SCORE_K8S_CLUSTER and SCORE_K8S_PROJECT, kubectl and the kubeconfig reaching the jobs' namespace; none of them are on the conductor yet, 2026-11-06), --no-film his Buy without the demo films
  approved in a session, score/dashboard/checkout/chat_yes.py), decide-yes and decide <yes id> (his other
  owner-only decisions made in a session, a spend override among them: `decide-yes spend <name> --euros E --purpose P`, and his Google month: `decide-yes google-month <YYYY-MM> --euros E`, owner 2026-11-02; score/dashboard/sync/chat_decisions.py; owner, 2026-10-27), `run ... --go <id>`
  (his go, SCORE_OWNERS_GO), grant_benchmark and a benchmark
  run tagged with its grant, as an argument list (never a shell), every agent marker set; anything else is refused
  with the reason. The owner's key must have a passphrase (`up` refuses one without), so an agent on his PC cannot
  reach a shell past the door.
- **`door_service.py`** (#76 step 4): the same door in the cluster's conductor pod (its `door` container), reached by
  `kubectl port-forward` to `score-conductor-0` alone (the agents' role, `tools/cloud/k8s/conductor`): each POST runs
  `agent_door.sh` as sshd does, the asked command in SSH_ORIGINAL_COMMAND and the body on stdin, so its verbs and
  refusals are agent_door.py's; it listens on the pod's loopback only and refuses (403, nothing run) without the token
  `score-agent-door-token`, read by name at its start (it does not start without one). An agent asks through it with
  `python3 tools/cloud/conductor/door_service.py ask "<command>"`, which reads the token through this folder's
  `secret_reader.sh` by the secrets project's name (`SCORE_SECRETS_PROJECT`, else farm-factory), never the box's own
  reader (2026-11-10: this PC's looked in another project). The ssh door stays until the cutover.
- **`units/`**: `score-resume.service` (the one template for every machine; the PC copies it), `score-secrets`,
  `score-update` (the checkout follows the hosted cockpit's pinned commit from `/api/sync/pin` `commit` with the sync
  token, never `/healthz`, whose body babon's Caddy writes itself; a pin it cannot read moves nothing, a cockpit
  reporting none falls back to origin/main forward only; never while a run starts from the checkout or a process
  works in a frozen copy (a live run: the move goes on at the first tick after it ends; its line names each
  holding process with its command line), nor a uv.lock change while a
  sync pass runs (a pass is not a run: counted as one, it kept the
  checkout on an old commit all of 2026-10-25's morning, as passes run back to back), which links this checkout's `.venv`), `score-health`. The sync
  pass runs the same update first (its ExecStartPre, rendered by `install-sync --no-pull`; two calls take turns on
  `.git/score-update.lock`): a pass outlasts its 5-minute timer, so with score-update's timer alone a pass was always
  running and the live conductor's checkout sat on an old commit for hours (2026-10-24); the timer stays for an idle
  conductor. `boot.sh user` installs the sync's units every boot once machine.json is there (`sync_units`:
  score-update first, then `install-sync --no-pull`), so a changed sync unit reaches the live machine at its next boot
  with no hand step (2026-10-26: a sync unit installed before its ExecStartPre held the checkout off the pin from
  ~12:00 to 14:35 UTC). update.py notes its every line in `conductor/pin.json` (`said`), and the health record's
  `code.why` gives it while the checkout is off the pin; a uv.lock move held by a pass names a sync unit with no
  update before its pass. Other areas add their own units here;
  `boot.sh` installs whatever is in the folder, filling the deploy templates' slots for user score.
  A move that changes this folder installs it again (update.py, `boot.sh units`), so a new unit is live without a
  boot. `score-sweep` runs the disk sweep every 10 min (score/conductor/disk.py). The door's store-push writes and
  syncs the whole stream under tmp/ before it links anything, then lands blobs, then output listings, then the rest:
  a cut stream lands nothing, and no record lands before the output it names (2026-10-31).
- Tests (free, no cloud; each file well under 120 s): `test_owner_gates_and_safe_moves.py` (the owner's gates and
  the door, `up --dry` and the move, cloud-init schema and `systemd-analyze --user verify`, boot.sh against a temp
  root, the health record, the secrets, score-update) and `size_function/test_never_powered_off_under_work.py` (with
  AWS's SigV4 example).
