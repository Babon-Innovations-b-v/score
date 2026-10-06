# tools/props/cloud/

The cloud batch runner: a whole batch of approved pictures through Pixal3D on a rented Scaleway
graphics card, the raw models brought back and finished here, the machine deleted after (#55).
Entry: `batch.py`; its docstring says how to call it.

- **The only way models are made**, one or a hundred: no model runs on the owner's PC (owner,
  2026-10-03; `../local_models.py`). `batch.py` makes models, `pictures.py` pictures, `scene.py`
  a scene's steps (target, SAM 3 cut-outs, MoGe-2 depth, redraws) on one card, then its objects
  through `batch.py` as one batch. Their machines run the same scripts with `FARM_LOCAL_MODELS=1`.
- **A batch builds one scene's approved rows** (2026-10-04, #121): `batch.py --inventory
  data/inventory/<scene>.json` and `scene.py` (its plan's `inventory`) refuse without the owner's
  approval on page A and the place's style text in `place.json`, and every model is named for a
  row. No per-session job scripts: the wording comes from the repo's data.
- **Three runs a card.** Measured on an L4: six at once is barely faster and ran out of memory.
- **Name the project and zone on every `scw` call** (`scaleway.py` does). The CLI's default profile
  is another company's project; never change it, and never rent from it.
- **No keys or account ids in the repo.** The project is found by its name, `farm-factory`; the
  runner's ssh key and ledger live under `~/.farm-factory-props/cloud/`.
- **The limits are the owner's:** 4 h and €60 a batch, €700 a month (`ledger.py`). A batch that
  would pass one is refused before anything is rented; raising one is the owner's call.
- **The machine is always deleted:** at the end, on an error or a signal, by the watchdog at the
  time limit, and by the next run's sweep. Anything new that rents goes through `rent`, which starts its watchdog.
- **A machine deletes itself if this PC dies** (`self_delete.py`, armed first thing on every
  machine): when the runner's heartbeat is 15 min stale or the batch's time limit has passed. It
  uses a key that can only read, stop and delete farm-factory machines, addresses and disks
  (`~/.farm-factory-props/cloud/self_delete_key.json`, never in the repo). Tested 2026-09-29 by
  killing a runner: the machine was gone 2.5 min after its last heartbeat at a 2 min limit.
- **Delete only what is checked as ours:** every server, address and disk is compared by its own
  project field, never trusted from a list filter; the organisation holds another company's
  production. Loose addresses and disks are swept only while no batch runs.
- **Spread over zones:** a zone out of cards takes the order and leaves the machine stopped, so
  `rent` starts it at once and gives it back on "out of stock", and the fleet moves on.
- **The cut-out and the raw Pixal3D step run up there;** the raw model comes back with its camera
  folder (`<name>.svviews`), and finishing stays here with `pixal.py --finish-only` (no model).
  Moving finishing up needs a measured byte-for-byte match with the same Blender and scripts first.
- The generator's arguments come from `pixal.generator_arguments`, so both routes build the same.
- **The material library bakes on a card** (`library_bake.py`, `library_setup.sh`; job robust-exp, 2026-10-06):
  Blender 5.0.1 from blender.org, Cycles on OptiX, ProcFunc and infinigen2 from the repo's vendored copies; jobs are
  `../library/inside/`'s (swatches, code-built pieces, re-materialed chunky pieces). A local bake took every core
  and WSL crashed the same day: no bake runs on the PC. A whole hub slice (28 pieces), the swatch sheet and three
  habitat pieces took 7 minutes, €0.09. When no card is in stock, `--processor` takes a POP2 machine (Cycles on its
  cores, about three times slower; the types are tried in turn as their stock moves).
- **Part splitting** (`parts.py`, `parts_setup.sh`): PartCrafter (MIT code and weights) on one card, its
  non-commercial background remover patched out and never fetched; the parts only say where a model's part
  boundaries are (`../library/labels.py --parts`).
- **Infinigen runs on a processor machine** (`infinigen.py`, `infinigen_setup.sh`; a POP2 type, plain Ubuntu,
  priced by the hour): no card, the jobs from `../infinigen/steer.py` side by side, through the same `rent`.
  `--hold` keeps the machine for ssh work until the run folder holds `release`.
