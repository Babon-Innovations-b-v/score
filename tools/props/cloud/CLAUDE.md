# tools/props/cloud/

The cloud batch runners: a whole batch of approved pictures through Pixal3D on rented graphics
cards, the raw models brought back and finished here, the machines deleted after (#55), and the other
model steps the same way. Entry: `batch.py`; its docstring says how to call it.

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
  row. No per-session job scripts: the wording comes from the repo's data.
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
  `START_MINUTES`, and spreads a run's machines over the zones. A big card runs as many jobs at once
  as `capacity.runs_at_once` says (measured kinds only). A new runner does the same and
  records its machines with `ledger.machines_record`, so `capacity.py report` can compare cards.
- **The cut-out and the raw Pixal3D step run up there;** the raw model comes back with its camera
  folder (`<name>.svviews`), and finishing stays here with `pixal.py --finish-only` (no model).
  Moving finishing up needs a measured byte-for-byte match with the same Blender and scripts first.
- The generator's arguments come from `pixal.generator_arguments`, so both routes build the same.
- **Any Blender script runs on a rented machine** (`blender_cloud.py`, 2026-10-08, BLENDER IN THE CLOUD): a job
  names a repo script, its arguments, its input and output paths (at the same absolute paths up there, so neither
  the script nor the paths inside its input files change) and its minutes; a tool calls `blender_cloud.run_elsewhere`. Physics
  (settling) on a 32-core processor machine by default, renders on a card (`--classes gpu-24gb,...`, Cycles on the card
  via FARM_CYCLES_GPU). One call is one machine; run calls side by side for many. The PC's own Blender (one at a time,
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
  `judge.py` (Qwen3.8-27B in FP8 through vLLM, one 48 or 80 GB card; vLLM's DeepGEMM and FlashInfer sampler are
  off because the GPU image has no CUDA toolkit), and Pro draws only what fails. `--model klein` stays the
  default for other pictures.
- **Part splitting** (`parts.py`, `parts_setup.sh`): PartCrafter (MIT code and weights) on one card, its
  non-commercial background remover patched out and never fetched; the parts only say where a model's part
  boundaries are (`../library/labels.py --parts`).
- **The game's sound is generated on a card** (`moss_sound.py`, `moss_setup.sh`, `moss_generate.py`; job soundtool,
  2026-10-06): every sound briefed in `data/sound/sounds.json` through MOSS-SoundEffect v2.0 (Apache-2.0, code and
  weights pinned), each take scored against its prompt with CLAP up there, the takes back to the picker's cache.
  Its own budget is €8 a run on top of the owner's limits.
- **Infinigen runs on a processor machine** (`infinigen.py`, `infinigen_setup.sh`; class `cpu-32c-128gb`,
  plain Ubuntu): no card, the jobs from `../infinigen/steer.py` side by side, through the same `rent`.
  `--hold` keeps the machine for ssh work until the run folder holds `release`.
