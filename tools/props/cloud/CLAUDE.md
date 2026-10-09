# tools/props/cloud/

The cloud batch runners: a whole batch of approved pictures through Pixal3D on rented graphics
cards, the raw models brought back and finished here, the machines deleted after (#55), and the other
model steps the same way. Entry: `batch.py`; its docstring says how to call it.

- **SCORE_CLOUD=k8s sends a runner's work to the Kubernetes cluster** (`tools/cloud/k8s/`) instead of renting
  machines; the cluster's provider (registry, store, prices, secrets) is `SCORE_K8S_PROVIDER`, Scaleway by default,
  and `provider.on_cluster()` says which path is on. A runner that supports it describes each job (command, repo
  code, inputs and outputs at their paths, minutes) to `tools/cloud/k8s/cluster_jobs.py` and keeps its own interface
  and outputs: `blender_cloud.py` (renders, settling, review pages, `Machine` chains) and `library_bake.py` with the
  blender image, `parts.py` with the parts image, `moss_sound.py` with the moss image, and `batch.py` (Pixal3D) with the pixal image, its takes grouped
  as many to a job as a 24 GB card runs at once and finished here as today. The machine runners stay the default; switch none of them over by default.
- **Provider-neutral.** Runners rent through `provider.py` by capability class (`gpu-24gb`,
  `gpu-80gb-x2`, `cpu-32c-128gb`) and never name a provider, machine type, zone or price; those live in
  the backend (`backends/`, Scaleway today, chosen by `SCORE_CLOUD`). Secrets come through
  `secret_store.py` (an environment variable, else the backend's store). Anything provider-specific a
  new runner needs goes into the provider interface and every backend, never into the runner.

- **The only way models are made**, one or a hundred: no model runs on the owner's PC (owner,
  2026-10-03; `../local_models.py`). `batch.py` makes models, `pictures.py` pictures, `scene.py`
  a scene's steps (target, SAM 3 cut-outs, MoGe-2 depth, redraws) on one card, then its objects
  through `batch.py` as one batch. Their machines run the same scripts with `FARM_LOCAL_MODELS=1`.
- **A batch builds approved scene rows** (2026-10-04, #121; several scenes a batch since 2026-10-07): `batch.py --inventory
  data/inventory/<scene>.json` and `scene.py` (its plan's `inventory`) refuse without the owner's
  approval on page A and the place's style text in `place.json`, and every model is named for a
  row. No per-session job scripts: the wording comes from the repo's data. The one other thing a batch builds is a
  character the owner asked for (`batch.py --characters data/characters/makes/<name>.json`, job characters-full,
  2026-10-09): refused without the spec's `approved`, its model named after the spec.
- **Three Pixal3D runs for every 24 GB of card** (`capacity.RUNS_PER_24GB`). Measured on a 24 GB L4: six at
  once is barely faster and ran out of memory.
- **No keys or account ids in the repo.** The backend finds its account by name; the runner's ssh
  key and ledger live under `~/.farm-factory-props/cloud/`.
- **The limits are the owner's:** 4 h and €60 a batch, and the month's ceiling `SCORE_MONTH_EUROS` (€1,500 by default, 2026-10-08), checked before every rent (`ledger.py`, `batch.rent`). A batch that
  would pass one is refused before anything is rented; raising one is the owner's call.
- **The machine is always deleted:** at the end, on an error or a signal, by the watchdog at the
  time limit, and by the next run's sweep. Anything new that rents goes through `rent`, which starts its watchdog.
- **A machine deletes itself if this PC dies** (`self_delete.py`, armed first thing on every
  machine): when the runner's heartbeat is 15 min stale or the batch's time limit has passed. It
  uses a key that can only read, stop and delete the account's machines, addresses and disks
  (`~/.farm-factory-props/cloud/self_delete_key.json`, never in the repo). Tested 2026-09-29 by
  killing a runner: the machine was gone 2.5 min after its last heartbeat at a 2 min limit.
- **Delete only what is checked as ours:** every server, address and disk is compared by its own
  account field, never trusted from a list filter; the provider account may hold other projects'
  machines. Loose addresses and disks are swept only while no batch runs.
- **Spread over zones:** a zone out of cards takes the order and leaves the machine stopped, so
  `rent` starts it at once and gives it back on "out of stock", and the fleet moves on.
- **No job is tied to one card or zone** (2026-10-08, after a day of 24 GB cards out of stock in one
  zone): each runner takes its offers from `capacity.py`'s list for its job kind (every capability
  class that holds the job), and gets its machine through `batch.claim` (a fleet through `rent_fleet`), which
  takes the best stocked offer in `SPEED_ORDER` (price barely matters: owner, 2026-10-08), drops an
  offer that is refused, out of stock for a minute or whose machine does not answer within
  `START_MINUTES`, and spreads a run's machines over the zones. A dropped offer is dropped for one round only: a claim that finds
  nothing in stock asks every class and zone again every `STOCK_RETRY_MINUTES` (3) until its run has no work for it,
  its deadline or the month's ceiling (2026-10-09: six of seven spread slots gave up on their first round and one L4
  did all the work), and a signal (`STOPPING`) ends every claim and deletes a machine that answers after it. A big card runs as many jobs at once
  as `capacity.runs_at_once` says (measured kinds only). A new runner does the same and
  records its machines with `ledger.machines_record`, so `capacity.py report` can compare cards.
- **Every kind spreads a batch over many machines** (`spread.py`, 2026-10-08, after the provider granted quotas
  for 20 H100, 50 L4 and 10 L40S machines; stock is still the real limit): `capacity.machines_for` rents enough
  that each machine works about as long as its setup takes (or one job, when a job is longer), so a small batch
  keeps one machine and a big one ends in about the setup and one job's time; machines are claimed side by side
  (each claim reserves its zone while it rents, an offer that gave nothing is dropped for the run), each takes the
  next share from one queue as it finishes one, a share whose machine failed goes to another once, and a job whose
  own command failed (`spread.JobFailed`) is recorded, not retried. Caps: `max_machines` a class (the backend's
  `QUOTAS`, else 5) and `run_cap` in all (20); `SCORE_MAX_MACHINES="gpu-80gb=20,all=30"` overrides. A new
  runner gives `spread.on_machines` a set-up and a per-share function. `scene.py` stays on one card: its steps
  feed each other.
- **The cut-out and the raw Pixal3D step run up there;** the raw model comes back with its camera
  folder (`<name>.svviews`), and finishing stays here with `pixal.py --finish-only` (no model).
  Moving finishing up needs a measured byte-for-byte match with the same Blender and scripts first.
- The generator's arguments come from `pixal.generator_arguments`, so both routes build the same.
- **Any Blender script runs on a rented machine** (`blender_cloud.py`, 2026-10-08, BLENDER IN THE CLOUD): a job
  names a repo script, its arguments, its input and output paths (at the same absolute paths up there, so neither
  the script nor the paths inside its input files change) and its minutes; a tool calls `blender_cloud.run_elsewhere`. Physics
  (settling) on a 32-core processor machine by default, renders on a card (`--classes gpu-24gb,...`, Cycles on the card
  via FARM_CYCLES_GPU). A call's jobs are spread over machines like any batch (spread.py). A tool with a
  chain of jobs (a review page's renders) holds one machine for all of them (`blender_cloud.Machine`, --serve on a queue
  folder), deleted when the tool closes the queue or after 10 idle minutes; never rent one per step. The PC's own Blender (one at a time,
  the machine lock) is for checks of seconds only.
- **The material library bakes on a card** (`library_bake.py`, `library_setup.sh`; job robust-exp, 2026-10-06):
  Blender 5.0.1 from blender.org, Cycles on OptiX, ProcFunc and infinigen2 from the repo's vendored copies; jobs are
  `../library/inside/`'s (swatches, code-built pieces, re-materialed chunky pieces). A local bake took every core
  and WSL crashed the same day: no bake runs on the PC. A whole hub slice (28 pieces), the swatch sheet and three
  habitat pieces took 7 minutes, €0.09. When no card is in stock, `--processor` takes a 32-core processor machine
  (Cycles on its cores, about three times slower; the classes are tried in turn as their stock moves).
- **Close-ups: Qwen-Image-Edit first, Nano Banana Pro for the failures** (owner, 2026-10-08): the close-up stage
  (`../closeup/stage.py`) draws every close-up with `pictures.py --model qwen-edit` (Qwen-Image-Edit-2511, 20B, an
  80 GB card, each card of a machine its own slice, about 58 s a picture), the shape check judges each with
  `judge.py` (Qwen3.8-27B in FP8 through vLLM, three sampled answers a picture and the majority decides, an 80 GB card
  first, a 48 GB one at a third of the pace; vLLM's DeepGEMM and FlashInfer sampler are
  off because the GPU image has no CUDA toolkit), and Pro draws only what fails. `--model klein` stays the
  default for other pictures.
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
  (SegviGen) and 4 min (GeoSAM2, mostly processor) an object on an L4. The spread runner does not keep asking for stock
  during a batch: a slot whose claim finds nothing in stock gives up (six of seven did, 2026-10-09).
- **The game's sound is generated on a card** (`moss_sound.py`, `moss_setup.sh`, `moss_generate.py`; job soundtool,
  2026-10-06): every sound briefed in `data/sound/sounds.json` through MOSS-SoundEffect v2.0 (Apache-2.0, code and
  weights pinned), each take scored against its prompt with CLAP up there, the takes back to the picker's cache.
  Its own budget is €8 a run on top of the owner's limits.
- **Infinigen runs on a processor machine** (`infinigen.py`, `infinigen_setup.sh`; class `cpu-32c-128gb`,
  plain Ubuntu): no card, the jobs from `../infinigen/steer.py` side by side, through the same `rent`.
  `--hold` keeps the machine for ssh work until the run folder holds `release`.
