# tools/cloud/

The cloud batch runners: a whole batch of approved pictures through Pixal3D on rented graphics
cards, the raw models brought back and finished here, the machines deleted after (#55), and the other
model steps the same way. Entry: `batch.py`; its docstring says how to call it.

- **Nothing rents outside a cleared run** (design of 2026-10-11, step 0): `batch.rent`, the one place a machine is
  ordered, asks `score.adapters.compute.require_cleared` first, so `blender_cloud.py`, `detached.py`, every runner,
  `tools/review/demo.py` and the coordinator's scripts refuse to spend unless SCORE_SPEND_TICKET names a node the
  runner cleared (`score.adapters.engines` sets it) or the owner's override (his spend yes under the node
  `override`). A refusal is `compute.Refused`; never route round it.
- **SCORE_CLOUD=k8s sends a runner's work to the Kubernetes cluster** (`tools/cloud/k8s/`) instead of renting
  machines; the cluster's provider (registry, store, prices, secrets) is `SCORE_K8S_PROVIDER`, Scaleway by default,
  and `provider.on_cluster()` says which path is on. A runner that supports it describes each job (command, repo
  code, inputs and outputs at their paths, minutes) to `tools/cloud/k8s/cluster_jobs.py` and keeps its own interface
  and outputs: `blender_cloud.py` (renders, settling, review pages, `Machine` chains) and `library_bake.py` with the
  blender image, `parts.py` with the parts image, `meshparts.py` with the meshparts image, `segment.py` and
  `scene.py` (its steps as one job) with the sam image, `judge.py` with the judge image, `pictures.py` (klein and
  Qwen-Image-Edit) with the pictures image, `moss_sound.py` with the moss image, and `batch.py` (Pixal3D) with the
  pixal image, its takes grouped as many to a job as a 24 GB card runs at once and finished here as today.
  `characters.py` stays on machines: its person chain runs every step's environment on one machine, while an
  image holds one (characters-motion), so it needs the chain cut by image first. The machine
  runners stay the default; switch none of them over by default.
- **Provider-neutral.** Runners rent through `provider.py` by capability class (`gpu-24gb`,
  `gpu-80gb-x2`, `cpu-32c-128gb`) and never name a provider, machine type, zone or price; those live in
  the backend (`backends/`, Scaleway today, chosen by `SCORE_CLOUD`). Secrets come through
  `secret_store.py` (an environment variable, else the backend's store). Anything provider-specific a
  new runner needs goes into the provider interface and every backend, never into the runner.

- **This PC's card is one machine of its own** (`SCORE_CLOUD=local`, `backends/local.py`, `this_pc.py`; owner,
  2026-10-27: "couldnt u just finish the rest of env1 on this gpu aswell", then "yes"): one Docker container on this
  PC (Ubuntu 24.04 with CUDA's base, sshd, the card through WSL's `/dev/dxg`), reached as root over ssh like a
  rented machine, so no runner changes; never rented and never billed (its offers are `parked` at EUR 0, so
  `batch.rent` orders nothing, and `park.adopt` hands it out through `park.here`, no clearance asked, its ledger rows
  EUR 0 with the measured minutes), one claim a container at a time (its lock; a busy claim waits and asks
  again; kinds side by side by the card queue, below) but Blender's (`local.SHARED`), which share it across places: Blender jobs run side by side as many as the
  container's memory holds at a take's measured peak (`local.RUNS_AT_ONCE`, four in 27 GiB at the takes' p90, 2026-10-29; env1, 2026-10-28: one
  take at a time left about 20 of 24 cores idle), one a turn (a lock file each) that a Blender claim takes while
  free and lets go as its slot runs out of work, so several places' bake rows fill the turns together (2026-10-29:
  26 bake rows waited on one place's claim); an exclusive claim that asks keeps new Blender claims out until it has
  its turn, and a running Blender claim's slots take no next job meanwhile: it lets the machine go and asks again for
  the rest (`spread.work_slot`; 2026-10-29: straight-masks@lab waited 20 min while base's bake kept all three turns),
  set-ups run one at a time (`local.setting_up`), and only the claim leaving the container alone restarts it; with
  every card call (the Cycles bake, a render) taking one of the card's two turns (`backends/card_turn.py`
  `CARD_SLOTS`, a Blender startup script each claim copies into the container; a bake call is mostly processor work,
  the card busy about 1 s of its 4 to 9, and two calls fit the card's memory), their outputs brought back and kept one job at a time a machine
  (`blender_cloud.BRINGING`), never parked, its claim ended by a container restart that ends whatever the job left on the card, its
  set-up kept, each kind's own (`park.own_set_up`, 2026-10-29: a characters set-up ran from scratch while every
  Blender bake waited): at its claim a kind gets its own `/root/venv` back (the one held moved under `/root/kinds/`),
  and no set-up mark is removed there (`park.THIS_PC` makes `park.ALL_MARKS` a no-op), so a kind sets up once; apt's
  system packages stay. A kind too big for its 16 GB (`local.TOO_BIG`: judge, pictures-20b,
  characters, meshparts, moss-sound) is refused at its claim with the GB, and a class above one 24 GB card is never
  offered: those stay cloud jobs. A run that gives its own measured need (`run.need`) is refused by that instead: a
  characters run of clip steps only (people-clips-made, scene-clips; `characters.card_need`) needs 4 GB of card and
  17 GB of memory with Kimodo's text encoder on the processor (`TEXT_ENCODER_DEVICE=cpu`, set on this PC only;
  measured 2026-10-27: 3.66 GB card peak, 16.7 GB memory, 87 s), so it runs here; so does a sound row's MOSS takes
  (`moss_sound.on_this_pc`, the machine path, since this PC has no image registry; `THIS_PC_NEED`, 10 GB of card
  and 20 GB of memory with MOSS's models on the card one at a time, `MOSS_ONE_AT_A_TIME=1` on this PC only, measured
  2026-10-28: 9.83 GB card, 17 to 26 s a take); a body build still needs the whole
  machine. A Blender run's need is its biggest job's prediction (`blender_cloud.alone_need`): past the container's
  memory, its claim runs alone, exclusive, one job at a time, once that room is free (`local.alone_room`), in the
  container raised to this PC's memory less 8 GB and its RAM drives (`local.alone_cap`), set back at its delete
  (round 31: base's light passes, 29.8 GB beside the shared 27 GiB). `python3 tools/cloud/this_pc.py env1` (through the agents' door's `store-pull` and `store-push`, the
  agents' key: owner, 2026-10-27, never his own key on the conductor) pulls what a run reads into `~/.score-this-pc`, runs `score run world1 --free` there (a free-only run on this PC's
  card also makes its paid rows, with no ticket, so a Google ask its cache does not answer fails, saying so:
  `graph.on_this_pc`) and pushes the new store objects and takes back, adding only: the door never replaces a file the conductor holds. Its `decide-yes` and `decide <yes id>`
  are the door's, against that run's home (owner, 2026-10-27), and `env1 --go <id>` tags the run with his go
  (SCORE_OWNERS_GO: a bought batch for the in-batch accept). `pause`, `resume` and `status` free the PC for the
  owner's games (owner, 2026-10-28: "make it so that you can ez pause and resume using my system"): `pause` records
  the live run (arguments, commit, its SCORE_ variables, the go among them) in `~/.score-this-pc/paused.json`, stops
  it with SIGTERM to its leader, waits until its process group is gone and `docker stop`s the container (never
  `docker pause`: the card's memory stays held); `resume` refuses while a run is live, starts the container and the
  same run detached from `~/.score-this-pc/resume-code` at the recorded commit (log under `~/.score-this-pc/logs`);
  `status` says running, paused or neither, the newest heartbeat's rows and what is on the card. The owner's one-time
  step: `sudo usermod -aG docker $USER`. The rule below that no model runs on the owner's PC holds everywhere else.
- **One card queue for this PC** (`backends/card_queue.py`, PRD #73; owner, 2026-10-31: "go full docker ... even for
  local, then we can control and manage this way better"; 2026-10-31: a SAM 3 masks job failed with
  `cudaErrorDevicesUnavailable` while sim body's level 1 seeds held the card outside the run): every user of the card
  holds a measured share of it while it works, and the shares never pass the card less the desktop
  (`card_queue.BUDGET_GB`). The run's container claims take theirs in `local.take` (`local.CARD_NEED`, else the run's
  own `card_gb`, else the whole card) at priority `first` (the sim body tuning too: the owner, 2026-10-31, sim bodies before the film); any other card user (a proof container, a
  scratch run) starts under `python3 tools/cloud/backends/card_queue.py run --job <name> --card-gb <measured GB>
  --priority side -- <command>`, which waits for its share and execs the command holding it, and `card_queue.py
  status` is the PC's line (the card's shares, what waits, each container's memory) and what holds the card. A first
  claim that waits keeps side jobs off until it has its share, and after `card_queue.YIELD_SECONDS` (60) asks the side
  shares back: `run` stops its command's session (SIGTERM, SIGKILL after 30 s; never SIGSTOP, which keeps the card's
  memory held), waits again and starts the command again once the card is free, so a side job must resume from its own
  checkpoints (sim body's level 1 tuning does). Every `run` and every claim of the container is measured while it holds its
  share (`card_queue.watch`: the card's highest reading less the desktop, and whether it was the only share at each
  reading; a `run`'s cores and memory from its children's rusage, a claim's cores from the container's cgroup), one line
  in the queue's `measures.jsonl`; `card_queue.py measured` gives each job's highest, the card only from takes alone on
  it (a card user outside the queue still counts in a reading). The container keeps `local.HOST_CORES` (4) of this PC's
  cores (`--cpus 20`), and a claim whose run gives its measured memory (characters' steps, MOSS) runs held to it times
  `local.MEMORY_MARGIN` (1.5), set back to `memory_cap` at its delete. Under `SCORE_THIS_PC_OWN_CONTAINERS=1` (set by
  the run at a restart; `local.OWN`) each kind runs in a container of its own made from the same image,
  `score-this-pc:1` (`local.container`: Blender and the library bakes stay in `score-this-pc`, which holds their
  set-up; every other kind `score-this-pc-<kind>`, set up once there with its own set-up script: its system packages
  are outside `/root`, so no copy of the old container's set-up, and no commit of it, so the image id in every kept
  job stays); a claim's end restarts only its own container, once no other claim holds it. Then claims of different kinds run side by side while their card and memory
  shares fit the queue (memory: the PC's less 16 GiB; a Blender claim 6.7 GB a turn and 2 GB, as many turns as fit;
  a run's measured `memory_gb`; an unmeasured kind the whole), first come first served among the run's claims. The
  run's memory room sums every SCORE container's cgroup (`score/graph` `container_cgroups`), and `this_pc.py pause`
  stops them all. The queue's folder (`~/.score-card`, `SCORE_CARD_QUEUE`) is one for
  the whole PC, whatever `PROPS_HOME` a run works under.
- **The only way models are made**, one or a hundred: no model runs on the owner's PC (owner,
  2026-10-03; `../local_models.py`). `batch.py` makes models, `pictures.py` pictures, `scene.py`
  a scene's steps (target, SAM 3 cut-outs, MoGe-2 depth, redraws) on one card, then its objects
  through `batch.py` as one batch. Their machines run the same scripts with `FARM_LOCAL_MODELS=1`.
- **A batch builds approved scene rows** (2026-10-04, #121; several scenes a batch since 2026-10-07): `batch.py --inventory
  data/inventory/<scene>.json` and `scene.py` (its plan's `inventory`) refuse without the owner's
  approval on page A (`scene.py` also without the scene's locked concept: its words are the scene's style,
  `../scene/place.py`), and every model is named for a row; Pixal3D is worded by nothing, so `batch.py` asks no style. A designed place's hand-in (`{home}/design/props/<place>.json`, `score/stages/complete/prepare/handin.py`) is
  approved by the creator's lock (owner, 2026-10-21) and taken as it stands (`batch.built_from`): its rows are his
  locked concept's reading, not page A's shape. No per-session job scripts: the wording comes from the repo's data. The one other thing a batch builds is a
  character the owner asked for (`batch.py --characters data/people/specs/<name>.json`, job characters-full,
  2026-10-09): refused without the spec's `approved`, its model named after the spec.
- **Three Pixal3D runs for every 24 GB of card** (`capacity.RUNS_PER_24GB`). Measured on a 24 GB L4: six at
  once is barely faster and ran out of memory.
- **No keys or account ids in the repo.** The backend finds its account by name; the runner's ssh
  key and ledger live under `~/.farm-factory-props/cloud/`.
- **The limits are the owner's:** 4 h and €60 a batch (`ledger.py`); a batch that would pass one is refused before
  anything is rented; raising one is the owner's call. There is no month's ceiling (owner, 2026-10-20): a batch's own
  stop is its high estimate plus 10%, set by his yes (score.adapters.compute's stop line, or a benchmark grant).
- **Nothing paid runs while the month's books are unknown** (#13, after the old WSL disk took both ledgers and the
  runner's keys, 2026-10-19): `ledger.books_refusal` gives a reason unless `cloud/books.json` says this month is
  `known`, or the cloud ledger and the Google ledger each hold a line from before the month began; a ledger begun
  again after a loss (a refused rent's line) holds none, so it stays refused until the books are known or the next
  month. `score spend --read-back` (and the runner's books check, `compute.books_refusal`, whenever an export is set)
  reads both bills, read-only: Scaleway's consumption and Google's from Cloud Billing's standard usage cost export in
  BigQuery (`google_bill.py`, the bq CLI; cost plus credits in EUR for this invoice month), and makes the books
  `known` once Google's was read; the Google month is then the higher of that bill and the Google ledger. The table
  is named by SCORE_GOOGLE_BILLING_TABLE, else one line in `cloud/google-billing-table`, never in this repo; an
  unset, missing or empty table leaves the books as they were and the refusal says why. The owner's `score spend
  --google-month EUR` (refused in an agent's process; the owner gives it with the cockpit's money card button,
  applied by his sync) stays an override. `compute.books_refusal`, `compute.require_cleared` (so
  `batch.rent`, `park`, the cluster and every Google and World Labs caller) and `compute.submit` ask it before anything
  is ordered; `tools/cloud/runtime/submit.py` is left alone, as it is in every job image's tag (`google_spend.py`
  is not, run machinery outside every code version since 2026-10-23). Under SCORE_FREE_ONLY=1 the same points raise `ledger.FreeOnly`.
  `batch.rent` refuses before any provider call without `ssh_key` and `self_delete_key.json`, and `batch.ssh_key`
  never makes a key: the owner makes the runner's key and deletes the stale IAM key `farm-factory-batch`.
- **The month's spend is the provider's own bill when that is higher** (2026-10-12: Scaleway billed EUR 1,554 for
  October, the ledger held EUR 1,387): the stop check (`score.adapters.compute.guard.spent_since`) and `batch.month_spent` take the higher of
  the bill (`provider.cloud.consumption`, lagging by hours) and the ledger. The gap was disks (EUR 71) and addresses
  (EUR 37), each billed by the started hour from a machine's creation whether it ran or not, storage and registry
  (EUR 16), and card time the ledger missed (about EUR 44). The backend's `delete` now writes each machine's disk and
  address euros to the ledger (`disk-and-address-<id>`). `python3 tools/costs/costs.py today` prints the bill's day and
  month to date by product, for the 09:00, 15:00 and 21:00 reports.
- **Card counts come from measured numbers, never a guess** (`preflight.py`, owner 2026-10-18): under a runner's
  ticket, `capacity.machines_for` sizes a batch on its stage's measured numbers in the ledger (seconds a job, a fresh
  card's set-up, euros a card-minute; the ledger line's `ticket` names the stage), whatever minutes the runner passed,
  keeps the batch's pre-flight (cards, likely and high minutes and euros) in `forecasts/<node>/<key>.jsonl` beside the
  store and says it in the run's log. A stage with fewer than 3 measured machines, or batches of two kinds, keeps its
  runner's own rule. A unit is one job as the stage splits them: the ledger names jobs, not frames. The runner's
  clearance reserves a paid node at its stage's measured runs (`preflight.node_run`: the high euros, the likely
  minutes) rather than the stage's hand-written estimate.
- **A batch of props is priced per prop from measured units before it is bought** (`prop_batch.py`, owner 2026-10-18):
  the upgraded route's paid steps (close-up, image-to-3D, finish pick, bake) each as one batch over every prop still in
  it, a free check before each, kept steps and unchanged props never paid again; `price` reads the ledgers (the repo's
  evidence copy with the live one, since the live ledger was reset on 2026-10-17) and says an unmeasured step rather
  than guess. It is imported by no stage, so it re-keys nothing. `prop_batch.py run <props.json> --yes` (the
  props environment's python; the trial's props file, `data/props/batches/trial.json`, retired with the old takes on
  2026-10-21) prints the price, then makes
  the batch through `prop_makers.py`'s real runners (Pro close-ups and the finish list through google_spend from the
  PC, `batch.py` for Pixal3D, `library_bake.py` make_chunky jobs for the bake), refused without `--yes` and outside
  a cleared run or the owner's override; one warm batch per step, not one machine per prop (the steps' images
  differ, the finish stays here), and a prop naming no `parts` for its bake stops before anything is paid.
- **A finished job is kept by its own content** (`kept.py`, owner 2026-10-18; 2026-10-29, after a fix to 3 objects
  baked whole places again and the free run on this PC kept nothing): inside any make (the runner names its folder,
  SCORE_MAKING, and its row's code, SCORE_MAKING_CODE: code version, contract, params, seed, models and its files in
  the repository: the node, then their hash), `kept.keep` keeps a job that ended well at `kept/<slot>/<content>/done`
  beside the store, its files in the store's own blobs (each content once, read-only), and `kept.missing` links back
  every job of the same content, at this key or a new one, and returns the rest, so a rerun or a re-keyed row pays
  only for the jobs whose own inputs changed. An entry kept as copies (5a46a96e) is turned into blobs at the same
  key on its first read (the content holds the row code's hash alone, not the node named before it), and the sweep
  leaves it until then. A place row that makes its takes one call a take (finish-route-views,
  finish-route-split, surfaces-parts: the stage table's `PER_TAKE`, wired by `per_take_kept` so no row moves) has
  each call kept the same way (`kept.call`: the function, its arguments with the files they name, the row's code and
  this Python with its packages). `clean-kept` (score/conductor/disk.py, the sync pass) drops what no current key
  asks for, never by age. The content is the job's JSON and its input
  files' bytes (the making folder, the frozen copy and the home written as stand-ins), the row's code and the system
  (`blender_cloud.system`: this PC's container image id, the cloud's images, the cluster's Blender image, and
  library_setup.sh); the repository's Python and docs among the inputs, and the run machinery's files, are left to
  the row's code. One content a slot (the job's script, arguments and outputs), kept past the stored output for the
  next key. A job keeps only the files its own copy back wrote (rsync's list), and no two jobs of a call write into
  one output (`blender_cloud.shared_outputs` refuses them by name before anything is put back or rented): a shared
  folder came back with either job's copy, so each bake take named the others beside it as peers and was baked
  again whenever one was (#36, 2026-10-30); each bake take brings back into its own (`route_bake.made_of`), gathered
  into `made/` after the jobs. `blender_cloud.py` calls both: `still_to_run`
  before pricing a call's jobs, `keep` after each job ends well on a machine or the cluster; a held machine's chain
  (`--serve`) keeps nothing.
- **The cheapest card that fits** (owner, 2026-10-12): `capacity.next_offer` takes the kind's cheapest card per job
  first (`KIND_ORDER`, measured from the ledger; an offer out of stock last, a scarce one still first): an L4 for
  Pixal3D and the mesh splitting (EUR 0.14 a job against 0.73 on an H100), an L40S for the judge (0.33 against 0.78),
  an H100 only for the 20B picture model or when nothing smaller is in stock. Blender and bakes never take one
  (`capacity.NEVER`). The rule lives in capacity.py, not the runners: `blender_cloud.py`, `library_bake.py` and
  `meshparts.py` are declared inputs of the surfaces rows (`Stage.files`), so an edit to them re-buys every place's
  turntables and maps. A parked machine is taken by a claim of another kind that cleans up when its own kind has none
  (`park.take`): the same system image, its run's files gone, the claiming kind's set-up run on it. The run machinery
  (`batch.py`, `capacity.py`, `park.py`, `pool.py`, `spread.py`, `provider.py`, `backends/`, `ledger.py`,
  `preflight.py`, `kept.py`, `self_delete.py`, `secret_store.py`, `detached.py`, `google_spend.py`, `google_bill.py`,
  `blender_cloud.py`) is outside the stages' code keys (`score/graph/_code.py` FRAMEWORK): it changes what a run costs,
  never what it makes. A runner module that sends a maker's scripts up (`pictures.py`, `similar.py`, `scene.py`, ...)
  stays in, so a clean-up registered there (`park.CLEANUPS`) still moves the rows that import it; register new ones in
  `park.py` (pictures', scene's and every mark-less kind's live there since 2026-10-23).
- **The machine is always deleted:** at the end, on an error or a signal, by the watchdog at the
  time limit, and by the next run's sweep. Anything new that rents goes through `rent`, which starts its watchdog.
- **A processor machine is parked, not deleted, while its paid hour has time left** (`park.py`, job hours,
  2026-10-10): they are billed by the started hour and a Blender run takes 9 to 33 min, so they cost 1.6 to 3.2 times
  their hourly price (about €48 of €88 in October). A healthy machine of a kind that registered a clean-up
  (`park.CLEANUPS`: `blender`, `library`) has its run's files removed and is listed in `~/.farm-factory-props/cloud/parked/`;
  the next `batch.claim` of that kind on this PC (else of another kind that cleans up) takes it, set-up done, and the ledger charges it only what it adds.
  It is gone 5 min before its paid hour ends, never idle into the next: its `--expire` process deletes it, its own
  `self_delete.py` is re-armed to that time, and its tags hold that time for any run's sweep. Failed machines and runs
  stopped by a signal are deleted as before.
- **Outside a warm pool, a card is parked for its kind's measured cold start, at most 10 min, and only while a claim waits for one**
  (`park.idle_minutes`, 2026-10-11; `park.queued`, 2026-10-22, after an H100 sat parked unused after a one-model
  Pixal3D batch: a card with no queued work is released at once): every
  cloud job waited for a fresh card to answer and set up (blender on cards: median 5.4 min outside its jobs, 40% of
  what its cards cost, October 2026). A healthy card of a kind in `park.CLEANUPS` (`blender`, `library`, `depth`,
  `judge`, and since #20 `pixal`, `finish-masks`, `segment` and `meshparts`, so one card takes many jobs across a
  batch; Pixal3D's fleet takes a parked card in `rent_fleet` before it orders one) is parked as above for the median minutes its kind's last 30 fresh cards took from order to first job
  (the ledger's `start_wait_minutes` + `setup_minutes`), so one nobody takes costs at most one cold start. Every
  claim of a cleared run waits on its kind's queue (`park.wanting`, `~/.farm-factory-props/cloud/wanted/<kind>/`) and
  takes a card parked meanwhile within 10 s; taking one needs a cleared run like `rent`. A card nobody took is
  deleted at its time and `--expire` writes its idle minutes and euros to the ledger (`parked-<id>`). A kind opts in
  with a clean-up in `park.CLEANUPS` and a set-up script that skips a machine it already set up (a mark named for the
  script's text, written last). Pixal3D's and meshparts' clean-ups live in park.py (batch.py imports park; meshparts.py
  is a declared input of the segvigen rows). A taken machine keeps only its newest set-up mark (`park.STALE_MARKS`):
  most kinds share `/root/venv`, so an older kind's mark no longer says what is installed (rented machines only;
  this PC's container keeps each kind's own, above).
- **A run's machines end with the run** (2026-10-17, after orphaned machines and boxes billed by the started hour):
  `score run` names itself SCORE_RUN_ID and leads a process group of its own (taking the terminal along and giving it
  back at its end); stopped by a signal it passes the stop on once (`stopped.PASS_ON` to its nodes, each sending
  SIGTERM to its children; each batch deletes its machines through `delete_machine`; none when the signal already
  reached the group, since `batch.stop_on_signals` leaves its delete loop at a second signal), SIGKILL after 30 s to
  all but the cloud tools and the nodes they write to, and however it ends it releases the run's spend reservations
  (`compute.release_run`), once those cloud tools have ended. A stopped node waits for its children before it exits,
  so a batch's output pipe stays open while it deletes. A node process whose runner died sends the group SIGTERM
  itself, one node for the whole group (`graph.watch_runner`); a runner that leads no group (every runner but `score
  run`) leaves its nodes alone, as before. Under a run, `run_cap` counts the whole run's machines from what bills:
  each live machine's watchdog (the run's id in its environment), each parked machine's record, and for
  `capacity.RESERVE_SECONDS` a process's written count of machines it is renting (`capacity.reserve_run_slot`, a count
  per process in `cloud/runs/<run>/` under a lock), so a slot whose offer gave no machine frees itself; `park.adopt`
  counts a taken machine the same way. Left open: a run's orphan process (its node gone) that had the group's stop is
  sent a second one when no node shows the stop within 1 s. A node that dies while its runner lives (killed alone, out
  of memory) no longer leaves its batch renting (audit, 2026-10-22): under SCORE_RUN_ID, `batch.stop_on_signals` (every
  runner calls it) watches the parent and, once it is gone, sends itself SIGTERM, so every machine is deleted at once;
  `batch.say` moves to `cloud/orphaned-batches.log` on a broken pipe, so the delete loop survives the gone reader. Not
  done: run-id tags on fresh machines. A machine whose run's process is gone is deleted by the next run's sweep
  (`batch.is_leftover`); `park.reap`, never called, was deleted (2026-10-22).
- **A Buy's warm pool: its cards rented once and warm from its start to its end** (`pool.py`, CONTEXT.md "warm
  pool"). The owner, 2026-10-23: "huh dont we keep them warm for the entire thing anyway? that sounds very
  inefficient, i would use like 10 gpus but warm for the entire batch"; "this should be the same for all steps, and a
  buy is just start to finish, so just make them keep retrying and cant u just do it in the same pool as 1, then they
  would be warm anyway"; and, the pool grown beside the run rather than gating it: "i think the buy run can just start
  as soon as one is warm, in the background u just try collecting more till 10, so its sepperate". So a Buy (one
  detached `score run`, start to finish) holds about 10 cards, mostly L4, an L40S or H100 only when its rows need that
  class; every cloud step (Pixal3D, Blender, library bakes, people, judge, segment, meshparts, finish masks, depth)
  queues its jobs on the pool and each warm card takes the next, switching kinds (set-up scripts skip what is done);
  no step rents, retries a rent or waits on stock itself, and nothing warns about or waits out an afternoon Buy.
  `pool.start(run, sizes, deadline)` (sizes by `pool.size_for` from the run's planned card work: each
  step's `capacity.machines_for` on its kind's first class, at most `MOST_CARDS` 10 and each class's quota) opens it
  and starts its collector (`pool.py --collect`, a process of its own under the pool's ticket), which rents beside the
  run until the pool holds its size, backing off for stock as a claim does and never giving up before the pool's end, and parks each warm card for the pool at
  once, so the run's card work starts on the first card. Once a run opened a pool its steps never rent:
  `batch.claim` (every spread runner) and `batch.rent_fleet` (Pixal3D) take a pool card (`park.adopt`, by class in
  any zone, another kind's cleaned and set up again) or wait for one, the wait outside the step's own time limit
  (`pool.paused`, `spread.one_machine`, the Pixal3D fleet's `keep_the_fleet`: fault of 2026-10-23, sound@hub's takes
  made gaps by 15 min of shortage), a class the pool lacks or a bigger disk asked of it (`pool.want`: an ask of the
  claiming process, never a change of the pool's sizes or disk; the collector rents that one card beside the pool
  while the asker lives and `pool.trim` lets it go once idle after; fault of 2026-10-24: a sound row's 200 GB raised
  every later L4's disk and threw a warm one away);
  `batch.delete_machine` gives a healthy card back (parked until the pool's end, its self-delete on
  the usual 15-minute quiet limit, the collector beating it) and deletes a broken one, which the collector replaces;
  a card whose taker died is deleted by the collector. A card goes back only from a kind with a clean-up in
  `park.CLEANUPS`: every Buy kind has one (blender, library, pixal, judge, segment, meshparts, finish-masks, and
  since the pool `characters`, `pictures`, `pictures-20b` and `scene`, its depth step's); the kinds whose set-up
  writes no mark (parts, unlit, similar, unirig, closeups, moss-sound) remove their whole folder and every set-up mark
  (`park.ALL_MARKS`: their set-up rebuilds `/root/venv`), so the next kind sets up again (fault of 2026-10-23: the
  likeness threw its pool L4 away); `prove` (`images/prove.py`, every sound row's takes) stops its containers and
  removes its store credentials, docker and its caches staying (fault of 2026-10-24). A card not given back is struck
  off the pool only once its delete went through (`park.park`), so a release still sees it. A dead card's unfinished share (`spread.Shares.again`) or
  Pixal3D jobs (`Fleet.again`) go back on the queue once (a finished job never runs again; a second death makes it a gap).
  Dead means it no longer answers (`batch.answers`, review of 2026-10-23): a share that failed on a card that still
  answers (a copy-in, a local fault) is a gap and the card works on, and a card that failed in set-up, answering or
  dead, is followed by one more, never a third, so a broken set-up script never takes card after card (fault of
  2026-10-25: a set-up that failed once on an answering parked card ended its slot). The collector says a failed round (the provider's API, a delete) and tries again,
  backing off as for stock; only the pool's end, its release or its run's end stop it. Stop everything closes every
  open pool and ends its collector (`pool.close_all`) before it releases the parked cards, and a release tries every
  card, side by side, before it raises, `score run`'s release going on past it. A stopped `score run` releases its
  pool first, before its 30 s grace (`stop_run`), so no card is rented in the place of one a stopping taker deletes;
  the detached wrapper waits `stopped.FORWARD_WAIT_SECONDS` (90) for it; a collector stops at its first signal and
  ignores the next, so its rents under way delete their machines (faults of 2026-10-24), and one still there
  `pool.COLLECTOR_STOP_SECONDS` after a release deleted the cards is sent SIGKILL (`pool.end_collector`); a card of a
  closed pool still parked when its run's release was cut off goes at once (`park.outlive`); a zombie holds no card
  (`pool.process_alive`). Every machine minute is charged once, by the pool
  (`pool.hold`, `pool-hold-<run>-...` lines, kind `pool-hold`): from its creation to its delete, busy or idle, at its
  offer's price and billing unit, booked each collector beat and when it is struck off (`pool.left`), under the run
  and the pool's ticket, so the run's heartbeat, the cockpit's Spent and the money guards count it as it accrues
  (fault of 2026-10-25: Batch 1's pool held 11 h booked EUR 0, its heartbeat gauges reading the run's id before the
  run took it); its rent to first parking, idle spells and takers' rows keep their minutes and book no euros
  (`card_euros`, read by the measurements), and its first booking closes its rent's started line. The pool's idle time is the run's own cost, to be counted in
  its high estimate, its stop line and a benchmark grant's balance, never cut by a smaller pool or a cheaper class
  (quality is never a cost lever). Every `score run` with card rows opens its pool before it drives
  (`score/__main__.py` `opened_pool`): sized by `pool_sizes` (`pool.counts_for`: the most cards one row of a line is
  priced on, summed over the `--jobs` lines holding most, cards and processor machines together, at most
  `MOST_CARDS`, all L4; another class is asked for by its claim) and held just in time by the run's heartbeat (owner,
  2026-10-25: "cant u just do the start up earlier then when u need them again"): each machine, card or processor,
  only for the rows whose first job is due within its class's lead (`pool.leads`: the median minutes its class's last
  30 pool machines took to answer, and `LEAD_MARGIN_MINUTES`), on a forecast of each row's due time (`due_rows`,
  `due_in`: the rows it reads still to run at their likely minutes, a running one at what is left of them and,
  once it has run past them, as long again as it has overrun: `still_to_run`; Batch 1 try 5 of 2026-10-26 parked 13
  machines idle 30 min while finish lists forecast at 3.7 min waited 18 to 43 min on Google's Batch API queue), so a machine is rented its start-up before its
  first job and let go while its next job is further away; it opens at what is due then (`pool.sized`), and an
  idle machine billed by the started hour stays till its paid hour ends (`pool.paid_ahead`) (`pool_tender`,
  `pool.resize`: never above its reserved size; Batch 1 of 2026-10-24 and 2026-10-25 held three processor machines
  idle an hour and ten cards idle while the close-ups ran 2.5 h; fault of 2026-10-24: 10 L4s and 3 POP2s held for 8
  jobs, the cards about 40% busy), held until a batch's longest
  run (the ledger's `BATCH_HOURS`) and then, while the run goes on, another `BATCH_HOURS` at a time once its end
  is within an hour (`score/__main__.py` `extend_pool`, `compute.extend_pool`, `pool.extend`: each further holding
  cleared first against the same stop line or grant and added to the pool's one reservation; refused, the pool ends at
  its cleared end; Batch 1 of 2026-10-24 closed at 4 h with ~550 rows queued and every finish after failed), its
  holding cost (`holding_euros`: every card every hour at its class's dearest
  offer) cleared first as its own node (`compute.pool_clearance`, node `gpu-pool`, key the run's id: the stop line
  or the benchmark grant, reserved for the whole run) and its collector started under that ticket alone; on the
  cluster no pool. The pool opens at the largest size whose holding cost fits beside the run's own rows' high
  (`pool.shrinking`, one machine fewer at a time from the class with the most, a processor class before a card on a
  tie, so a small pool keeps one processor machine beside its cards; fault of 2026-10-23: three 48-core processor
  machines held 4 h passed a EUR 20 grant), and with no room for one machine opens none, its rows
  renting their own: never a failed run. `pool.release(run)` (from `score run`'s release, first thing, so
  also on a failed run, its stop line and Stop everything; the collector's own end when the pool's end passes or the run's
  process is gone) closes it and ends the collector: idle cards deleted at
  once, held ones by their takers; then the pool's clearance ends and a grant draws what its cards billed. A stop
  signal reaching the collector while it already releases (its own end) is said and ignored too, so its release
  reaches the last card (fault of 2026-10-24: 6 of 13 parked machines left billing). No run waits on a pool that
  cannot fill (fault of 2026-10-26: a benchmark's Pixal3D rows waited an hour, silent, on a pool whose only card had
  gone with every card class sold out): a waiting claim's time limit is paused only while its pool is open
  (`pool.claim`, and the Pixal3D fleet's `batch.pool_closed`: a closed pool once paused it for ever), so a pool closed
  under its run ends its claims as gaps; the run's heartbeat starts a collector again for an open pool whose
  collector is gone (`pool.revive`, under the pool's ticket), and says each 10 min a pool has held no machine while
  rows are due on it, with why: closed, collector gone, or the collector's last line (`said_empty_pool`). Every
  rent is priced (`pool.rents`, `pool.fits`): every card alive and chosen, at the class rented for the pool's whole
  hours, within the euros its clearance reserved, so the run's high stays a bound; an asked card with no room makes
  room by letting an idle card go (`pool.make_room`), and one no pool of that clearance can hold is refused
  (`pool.TooDear`). Not yet wired: the cockpit's cards-warm figure.
- **With L4s sold out, the pool rents a bigger card in an L4's place** (owner, 2026-10-23, "yes" to: "when L4s are sold
  out, should the pool take a bigger GPU (L40S or H100) instead? It costs more per hour but gives the same quality
  ... within the run's money limit"): `pool.stand_in` takes the next larger single card in stock (L40S, then H100)
  within its quota, only while the pool's cards, each at the class rented and its dearest offer for the pool's
  hours, fit the euros its clearance reserved (`pool.fits`, `plan["euros"]` from `opened_pool`), so the high stays a
  true upper bound and the pool may hold fewer, bigger cards; once a stand-in is in, every reserved place is held to
  that sum (`pool.rents`). The card fills the L4's place (`for`), a claim on a 24 GB card takes it (`pool.takes`: the
  larger single cards a kind allows, never its `capacity.NEVER`), it is never swapped while it works, and its place's
  next card is asked as an L4 first. A pool opened without its euros rents none.
- **The warm pool holds a few processor machines beside its cards, for renders and bakes** (owner, 2026-10-23: "why
  isnt rendering on cpu better?", then "yeah" to: Blender renders the same picture on processor and card, processor
  machines are almost never out of stock, so bakes and small renders take whichever machine is free first; and "cant
  u just get a faster cpu"). `capacity.PROCESSOR_KINDS` (`blender`, `library`: every Blender job and library bake) take
  a pool machine of their own classes or any `capacity.PROCESSORS` class (`pool.takes`), a free processor machine
  before a card (`park.processor_first`; measured 2026-10-23, #26: the 48-core beat the L4 on every Blender job), a call
  asked on processor machines alone (settling, the paint, a body's checks) taking its own classes or a pool processor
  no smaller in cores and memory (`pool.no_smaller`; fault of 2026-10-23: the checks rented a 16-core machine beside
  the pool's idle 48-core one); every other kind takes a card only.
  Cycles follows the machine (`spread.slots`: FARM_CYCLES_GPU on a card, the processor otherwise) at the same samples,
  size and denoising, so `blender_cloud.py` and `library_bake.py` are unchanged and no surfaces row moves.
  `score run`'s `pool_sizes` sizes the render and bake rows (`pool.processor_able`: a stage the ledger knows as those
  kinds) on processor machines, not cards (`pool.with_processors`): as many as the most cards such a row of a line
  is priced on, at most `MOST_PROCESSORS` 3, of the
  first `PROCESSORS` class in stock (64, then 48, then 32 cores, POP2-HC first: EUR 0.027 a core-hour against 0.037).
  The backend offers a processor class in every zone that sells it (`scaleway.rent_zones`; the cards' zones were short
  of every big POP2 on 2026-10-23) and only a type and zone with quota (`zone_quotas`, read from Scaleway's IAM: no
  64-core quota yet). Money: a pool machine's every minute is in the pool's clearance at its class's dearest price,
  so the run's high holds whichever machine a job takes; time: under a pool with a processor machine a render or bake
  stage's high minutes are its card ones times the slowest held processor class's `capacity.processor_times`
  (measured: `PROCESSOR_TIMES`, the 48-core 0.69 of an L4, so never under 1; else `PROCESSOR_SLOWER` 3, a 32-core
  bake) (`preflight.processor_margin`), so the runaway watch never stops one for landing there. Every ledger machine
  row carries its `class`, so `capacity.py report` gives each kind's processor time per class to add to the table.
- **A machine deletes itself if this PC dies** (`self_delete.py`, armed first thing on every
  machine): when the runner's heartbeat is 15 min stale or the batch's time limit has passed. It
  uses a key that can only read, stop and delete the account's machines, addresses and disks
  (`~/.farm-factory-props/cloud/self_delete_key.json`, never in the repo). Tested 2026-09-29 by
  killing a runner: the machine was gone 2.5 min after its last heartbeat at a 2 min limit. When this PC sleeps past
  that limit, the Pixal3D fleet sees it on waking (`Fleet.woke`: a machine's last heartbeat older than QUIET_MINUTES),
  stops, records the jobs it had not made as `lost_to_sleep` (never gaps: nothing about them failed) and exits non-zero,
  so the row runs again and buys only those; the models already back are not made again (audit, 2026-10-22).
- **Delete only what is checked as ours:** every server, address and disk is compared by its own
  account field, never trusted from a list filter; the provider account may hold other projects'
  machines. Loose addresses and disks are swept only while no batch runs.
- **Spread over zones:** a zone out of cards takes the order and leaves the machine stopped, so
  `rent` starts it at once and gives it back on "out of stock", and the fleet moves on.
- **No job is tied to one card or zone** (2026-10-08, after a day of 24 GB cards out of stock in one
  zone; under a warm pool the collector is the one claimant that rents, the steps take its cards): each runner takes its offers from `capacity.py`'s list for its job kind (every capability
  class that holds the job), and gets its machine through `batch.claim` (a fleet through `rent_fleet`), which
  takes the best stocked offer in `SPEED_ORDER` (price barely matters: owner, 2026-10-08), drops an
  offer that is refused or out of stock for a minute (nothing billed), and spreads a run's machines over the zones. A dropped offer is dropped for one round only: a claim that finds
  nothing in stock asks every class and zone again after `stock_wait_minutes` (3, 6, 12, 24, then 30 min, never past
  the deadline; the Pixal3D fleet's wait starts again at 3 once a round rents) until its run has no work for it
  or its deadline (2026-10-09: six of seven spread slots gave up on their first round and one L4 did all the work);
  `rent` orders nothing from an offer the backend's stock read says is out (`NO_STOCK`: shortage or parked), since
  each such order billed a disk and an address for a machine that never started (pixal@people, 2026-10-22: 438
  orders, EUR 2.19). A refused order's loose address and disk are deleted at once
  (`scaleway.delete_loose_left_by_refusal`), and a run's ledger row carries `rent_fees`, its machines' and failed
  rents' disk-and-address euros, which stay on their own lines and out of its `euros`. A signal (`STOPPING`) ends every claim and deletes a machine that answers after it. A big card runs as many jobs at once
  as `capacity.runs_at_once` says (measured kinds only). A machine rented that does not answer within
  `START_MINUTES`, or refuses the runner's key, was billed: it is deleted (`batch.BootFailed`); under a warm pool the
  collector rents another and the jobs wait on the queue, outside one the slot is a gap with no machine rented in its
  place and the Pixal3D fleet counts its cards, and those of a machine that broke, as lost. A new runner does the same and
  records its machines with `ledger.machines_record`, so `capacity.py report` can compare cards.
- **Every kind spreads a batch over many machines** (`spread.py`, 2026-10-08, after the provider granted quotas
  for 20 H100, 50 L4 and 10 L40S machines; stock is still the real limit): `capacity.machines_for` rents enough
  that each machine works about as long as its setup takes (or one job, when a job is longer), so a small batch
  keeps one machine and a big one ends in about the setup and one job's time; machines are claimed side by side
  (each claim reserves its zone while it rents, an offer that gave nothing is dropped for the run), each takes the
  next share from one queue as it finishes one, every share runs once: one whose own command failed
  (`spread.JobFailed`) is a gap, never handed to another machine; one whose warm pool card died goes back on the
  queue once for the pool's next card (`Shares.again`), outside a pool it is a gap. Caps: `max_machines` a class (the backend's
  `QUOTAS`, else 5) and `run_cap` in all (the largest class quota, at least 20: 50 with the L4 quota since #20); `SCORE_MAX_MACHINES="gpu-80gb=20,all=30"` overrides. A new
  runner gives `spread.on_machines` a set-up and a per-share function. `scene.py` stays on one card: its steps
  feed each other.
- **The cut-out and the raw Pixal3D step run up there;** the raw model comes back with its camera
  folder (`<name>.svviews`), and finishing stays here with `pixal.py --finish-only` (no model).
  Moving finishing up needs a measured byte-for-byte match with the same Blender and scripts first. The one
  exception is the rough model (never shipped, `score/stages/rough_model/_finish.py`): finished on a rented
  machine through `blender_cloud.run_elsewhere`, since the PC has no lab environment or Blender for it.
- The generator's arguments come from `pixal.generator_arguments`, so both routes build the same.
- **Any Blender script runs on a rented machine** (`blender_cloud.py`, 2026-10-08, BLENDER IN THE CLOUD): a job
  names a repo script, its arguments, its input and output paths (at the same absolute paths up there, so neither
  the script nor the paths inside its input files change) and its minutes; a tool calls `blender_cloud.run_elsewhere`. Physics
  (settling) on a 32-core processor machine by default, renders on a card (`--classes gpu-24gb,...`, Cycles on the card
  via FARM_CYCLES_GPU, on OptiX since library_setup.sh adds the driver's own libnvidia-gl: the provider's headless
  driver has no OptiX, and until 2026-10-11 every card render fell back to CUDA). A call's jobs are spread over machines like any batch (spread.py). A tool with a
  chain of jobs (a review page's renders) holds one machine for all of them (`blender_cloud.Machine`, --serve on a queue
  folder), deleted when the tool closes the queue or after 10 idle minutes; never rent one per step. The PC's own Blender (one at a time,
  the machine lock) is for checks of seconds only. An agent starts a cloud Blender call with `--detach` under `run_in_background`
  (`detached.py`: progress to a log, one result line at the end) and never polls it in the foreground.
- **A path a job names reaches the same place up there as here** (`inputs.link_named`, for a job's inputs and its
  outputs): every link on its way (a frozen run's `<copy>.home/store`, a take's `work/pixal` file link) is made a link
  on the machine, never a folder of file links; a job whose script ended well and brought none of its outputs back is
  a failed job (`blender_cloud.one_job`; fault of 2026-10-27: surfaces-bake@campgrounds' paint and bake wrote every
  take into a second making folder up there, and the jobs counted done).
- **A Blender job's big inputs go up once, through the bucket** (`inputs.py`, `input_fetch.py`; 2026-10-10, after two
  review-page machines waited about 2 hours for inputs while ten agents sent over this PC's ~3 MB/s link, the same
  438 MB of parts to several machines): an input of 8 MB or more is tarred the same way from the same files, named
  `inputs/<sha256>.tar` in the provider's `object_store()`, uploaded only when it is not there (a lock per key on
  this PC, so two sessions do not send it twice), and the machine pulls it in byte ranges from a signed link that
  reads that one object, checks it and keeps it for its next job. Small inputs, and any the store path fails to bring,
  go directly as before; `SCORE_INPUTS_DIRECT=1` sends everything directly. Staging runs in the repo's environment
  (boto3), as the cluster path does. Measured 2026-10-10 on a real review_models batch (two L4 machines sharing the
  wreck's 631 MB of made models and parts): sent directly, inputs took 28 min on each machine and the batch 30.1 min
  (EUR 0.79); through the bucket, 3.6 min (the one upload, the second machine waiting on its lock, then 9 and 14 s of
  pulling) and 5.3 min (EUR 0.16); once in the bucket, 14 and 24 s and 2.2 min (EUR 0.07).
- **The material library bakes on a card** (`library_bake.py`, `library_setup.sh`; job robust-exp, 2026-10-06):
  Blender 5.0.1 from blender.org, Cycles on OptiX, ProcFunc and infinigen2 from the repo's vendored copies; jobs are
  `../library/inside/`'s (swatches, code-built pieces, re-materialed chunky pieces). A local bake took every core
  and WSL crashed the same day: no bake runs on the PC. A whole hub slice (28 pieces), the swatch sheet and three
  habitat pieces took 7 minutes, €0.09. One class is fixed for the whole call at price time
  (`batch.one_class_in_stock`): the first asked that the run's warm pool holds, else the first in stock, else the
  first sold, its claims then taking pool cards, or under a warm pool its processor machines too (above). A
  processor class asked for by `--classes` is its own estimate, priced at `PROCESSOR_SLOWER` (three times).
- **Close-ups: Qwen-Image-Edit first, Nano Banana Pro for the failures** (owner, 2026-10-08): the close-up stage
  (`../closeup/stage.py`) draws every close-up with `pictures.py --model qwen-edit` (Qwen-Image-Edit-2511, 20B, an
  80 GB card, each card of a machine its own slice, about 58 s a picture), the shape check judges each with
  `judge.py` (Qwen3.8-27B in FP8 through vLLM, three sampled answers a picture and the majority decides, an 80 GB card
  first, a 48 GB one at a third of the pace; vLLM's DeepGEMM and FlashInfer sampler are
  off because the GPU image has no CUDA toolkit), and Pro draws only what fails. `--model klein` stays the
  default for other pictures.
- **Every Gemini API call goes through `google_spend.generate`** (2026-10-11, after a EUR 257 day): it writes a
  `started` line to `~/.farm-factory-props/cloud/google-ledger.jsonl` before the call, then a `finished` line priced
  from the response's usageMetadata at Google's published prices and its service tier, or a `failed` line. With
  `cache=True` the same request is asked once and read back from `google-cache/` by every place line and rerun. A
  line written under a `score run` carries its run's id as `tag` (`score/__main__.py` `tag_ledgers`, through
  `score/stages/props/ledger_tag`, so this file stays unedited: the close-up rows declare it), and the run monitor
  counts its calls' cost by it (2026-10-24: a run's Pro close-ups were missing from its spend). An answer is read
  through `google_spend.answer_text`: a finishReason other than STOP (MAX_TOKENS: the 65,536-token output limit,
  thinking included; SAFETY, RECITATION, ...) is `Unfinished` naming it and its tokens, never the JSONDecodeError a
  cut answer parses into; it is priced (its `finish` on the ledger line) and never cached (`keep`, the batch's answers
  too) (fault, 2026-10-25: surface-library@camp). Every JSON ask sets a responseSchema. No day
  cap (owner, 2026-10-11). The runner's stop check (`score.adapters.compute.months_since`) adds `month_euros`: a call
  started and never finished counts at its estimate (Oct 11: Google billed EUR 549, this ledger, then written only
  after a call came back, held EUR 30). Nothing calls generativelanguage.googleapis.com any other way:
  `test_google_spend_ledgers_every_call_before_it_is_sent.py` fails on any tracked file that does. The one other client is **`google_batch.py`**
  (2026-10-20, #18 and #21): Google's Batch API at half price on google_spend's ledger and cache, a started line for
  each request before its job is sent, the job's name kept beside the cache so a run cut off mid-wait picks up the
  same job and never sends it again, each answer priced at the batch tier; a failed, cancelled or expired job, an
  error answer or a send cut off is Unanswered, never asked again (the finish route's list and recheck, and
  since 2026-10-24 every Pro close-up, `../closeup/pro.py`: a step's close-ups one job, the owner's choice of the batch
  rate they are priced at).
- **Paid calls only through the ledgered clients** (2026-10-17): `tools/costs/test_every_euro_is_ledgered_measured_and_adds_up_to_the_bill.py` reads every tracked
  file's syntax tree and fails on a Gemini host, key header or client, or an scw order of a machine, disk, address or
  cluster pool (words read through variables as their own function set them, joined and starred lists, `.append`,
  `.extend` and `.insert`, each setting checked; strings joined with `+` and f-strings; an unread word, as a
  parameter, between a product and `create` counts; a client loaded by `importlib.import_module` or `__import__`
  too), and every other runnable file (scripts, Makefiles, Dockerfiles, manifests) line by line with backslash
  lines joined, outside the functions and constants its `ALLOWED` names in each allowed file. It does not follow
  words across modules, through other functions' return values, through attributes, indexed or sliced lists, or
  built with `%` or `.format`; docs and data are not read. Known gap: the bad address `quarantine_bad_address`
  detaches stays in the project for good, billed by the hour with no ledger line; reconcile-day shows it in disks
  and addresses.
  Every order `batch.rent` makes writes a `rent-started` line first (its run, name, offer, deadline and ticket, no
  euros; `ledger.rent_started`, called in the backend's `create` because the pixal rows declare `batch.py` and an
  edit there re-keys them), and a refused order a `rent-refused` line. Until its run's row, its machine's
  disk-and-address row or its refusal closes it, a started line counts in `month_total` at its price up to its
  deadline (`ledger.open_rents`), so the guard sees machines running and not yet billed. The cluster set-up writes
  `ledger.order_started` before each cluster and pool order.
- **The surface judge asks Gemini, not rented cards** (`gemini_judge.py`, 2026-10-11): judge.py's question list and
  answer files, asked of the models adapter's `gemini-judge` (Gemini 3.1 Pro, temperature 0, the answer an enum of
  the question's codes plus `unknown`), through google_spend with `cache=True`; the key is the secret
  `gemini-api-key`, refused outside a cleared run like any rent. The surface stage's g-texture judge rows called it
  until 2026-10-12 (the finish-map method replaced them); the close-up check stays on judge.py.
- **Close-up regions** (`segment.py`, `segment_setup.sh`, `segment_worker.py`; job repaint, 2026-10-08): SAM 2.1's
  automatic masks (facebookresearch/sam2 at a pinned commit, code and weights Apache-2.0) of every clean close-up,
  spread over cards (`spread.py`); 73 close-ups took 6 minutes on three L4s, €0.24.
- **Likeness** (`similar.py`, `similar_setup.sh`, `similar_worker.py`; job agent-tools, 2026-10-09): DINOv2
  (facebook/dinov2-base, Apache-2.0) cosine likeness of picture pairs on one card, for the render-and-compare
  (`tools/usd/compare.py`).
- **Rigging** (`unirig.py`, `unirig_setup.sh`, `unirig_worker.py`; job characters-full, 2026-10-09): UniRig
  (VAST-AI-Research/UniRig at a pinned commit, MIT code; VAST-AI/UniRig weights, MIT) gives a finished model a skeleton
  and skin weights on one card, for the character maker's animals (`../../characters/animals/`). Every compiled piece
  is a prebuilt wheel; only OPT-350m's configuration is fetched, never its weights. Its launch scripts end with
  `echo done`, so the worker checks each step's file, not its exit code.
- **Part splitting** (`parts.py`, `parts_setup.sh`): PartCrafter (MIT code and weights) on one card, its
  non-commercial background remover patched out and never fetched; the parts only say where a model's part
  boundaries are (`../library/labels.py --parts`).
- **Splitting our own model** (`meshparts.py`, `meshparts_setup.sh`, `segvigen_worker.py`, `geosam2_worker.py`; job
  parts-test, 2026-10-09): SegviGen (MIT, on TRELLIS.2's published wheels; nvdiffrast never installed, RMBG-2.0 never
  loaded, DINOv3 from an open copy checked by sha256) and GeoSAM2 (Apache-2.0, Blender 4.0.2 under xvfb, the model cut
  to 150,000 faces: its label completion is a Python loop) on the spread runner, every pin in `PINS`. About 1 min
  (SegviGen) and 4 min (GeoSAM2, mostly processor) an object on an L4.
- **The game's sound is generated on a card** (`moss_sound.py`, `moss_setup.sh`, `moss_generate.py`; job soundtool,
  2026-10-06): every sound briefed in `data/sound/sounds.json` through MOSS-SoundEffect v2.0 (Apache-2.0, code and
  weights pinned), each take scored against its prompt with CLAP up there, the takes back to the picker's cache.
  Its own budget is €8 a run on top of the owner's limits.

## The container path

The container path for every model step (job cloud-k8s, 2026-10-09): one pinned image per job kind, weights from a
cache instead of a fresh download on every machine, and a job spec that Kubernetes or a hand with docker runs the
same way. The machine runners in `tools/cloud/` stay the default; this path is chosen by `SCORE_CLOUD=k8s`.
**Experimental: not used for environment 1** (no environment was built through it; 06cf411's image pins are read only by this
path); it proves itself when a stage's paid node runs through it end to end. `k8s/submitter.py` and the cluster's
`up` (`k8s/clusters/scaleway.py`) refuse outside a cleared run, as the machine path does
(`score.adapters.compute.require_cleared`).

- **`runtime/`** is copied into every image: `job.py` (the entrypoint `score-job <run> <job>`), `weights.py` (the
  node's weights cache), `store.py` (S3 object storage, or a local folder for tests and hand runs), `kernels.py` (compiled GPU kernel caches per card and driver, for a job naming `kernel_cache`). Standard library
  plus boto3 only, Python 3.12. `submit.py` is the submit side the runners call on the coordinating machine:
  `cloud_store()`, `upload_code` (a content-addressed bundle of repo paths, the kind's `models.json` with it),
  `upload_input`, `output_key`, `write_job`, `state`, `done`, `failures`, `fetch_outputs`, `image(kind)`. Each
  module's docstring is its contract; the job spec is `job.py`'s.
- **Store layout** (the provider's `object_store()`, one bucket): `code/<sha256>.tar.gz`, `weights/<name>@<revision>.tar`
  with `.sha256` beside it, `runs/<run>/<job>/` holding `job.json`, `in/`, `out/`, `log-<attempt>.txt`,
  `failed-<attempt>.json` and `done.json` (written last: a job with it is never run again). Kernel caches: `kernels/<name>/<card>-<driver>.tar`.
  The machine runners' job inputs: `inputs/<sha256>.tar` (`inputs.py`).
- **No weights in an image, ever.** The images are public-safe and the weights' licences differ: each image folder's
  `models.json` lists its models with source, pinned revision, sha256, licence and `commercial_use`, and the runtime
  fetches them once per node into `/cache` (hostPath `/var/lib/score-cache`) under a file lock. A model not for
  commercial use runs only in a job marked `tool_only`. The tar is read from the bucket in ranges side by side and
  unpacked and checked in one pass, never written whole to the disk; when the disk is short, the least recently used
  models no running job holds are evicted first.
- **`images/<kind>/`**: a Dockerfile pinned by digest with pinned versions, `models.json`, and any small file it
  copies. `images/build.py` builds and pushes them on a rented processor machine (never on this PC: its upload is
  about 3 MB/s) through `batch.claim`, so the watchdog, the self-delete, the ledger row and the delete are
  batch.py's; the pushed tag and digest go into `images/images.json`, which `submit.image` reads. The tag is
  `<IMAGE_VERSION>-<hash of the image folder, the runtime and the parent image's digest>`, so a changed file gives a
  new tag and an unchanged one rebuilds nothing.
- **Secrets by name only.** The registry and store credentials come from `registry()` / `object_store()` at run time
  (Scaleway: the secret `score-cloud-runtime-key`, a key that may use the project's object storage and registry
  only); a node gets them as the SCORE_STORE_* variables of a Kubernetes Secret, never from the repo or an image.
- **First-use GPU compiles are paid once per card and driver, never per job.** Blender 5.0.1 ships no Cycles binary
  for the H100 (sm_90): its first render waited 218 s for the driver's compile, and 0.3 s once the cache was restored
  (2026-10-09; the L4 and L40S start at once). The provider's GPU driver (Ubuntu's headless compute set) has no
  OptiX: the blender image carries the driver's own OptiX files (`images/blender/install-nvidia.sh`), and OptiX's
  first render with ambient occlusion or bevel nodes compiled for 173 s on an L4 (2026-10-11), so warm it too.
  `images/warm.py --classes ...` renders `tools/blender/inside/warm_kernels.py` on one machine a class (before,
  first node, new node) and leaves the caches in the store; run it after a new Blender or driver. Its numbers go into
  images.json (`first_render`).
- **An image is proved with real jobs before a runner uses it:** `images/prove.py <plan.json>` rents one card from
  the plan's classes (asked again every 3 min while none is in stock), pulls each kind's image and runs its jobs through
  `score-job` in plain docker, each with a named node cache (a new name is a new node), and writes the pull and
  every job's marks into images.json (`proof`, by card). A job's command is the image's run wrapper (`sam-run`,
  `judge-run`, `pictures-run`), which puts the cached weights where the machine runner's worker looks.
- **A rebuild goes through the runner** once its kind has a plan (`images/<kind>/prove.json`): `python -m score run
  images` checks the pins for free, then builds and proves the kind cleared like any paid row, and `python -m score
  images publish <kind>` writes the accepted record into images.json (`score/stages/images`). No hand build.py run
  needs the owner's override.
- Tests run against a folder store, no cloud: `runtime/test_a_job_runs_once_on_checked_weights.py` (pytest, in a
  sandbox home); a test file in `runtime/` is never copied into an image (`images/build.py` `context_files`).
