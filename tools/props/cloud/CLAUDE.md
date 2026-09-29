# tools/props/cloud/

The cloud batch runner: a whole batch of approved pictures through Pixal3D on a rented Scaleway
graphics card, the raw models brought back and finished here, the machine deleted after (#55).
Entry: `batch.py`; its docstring says how to call it.

- **Only for big batches.** A handful of models runs on the owner's card with `pixal.py`.
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
- **Only the raw Pixal3D step runs up there;** finishing stays here with `pixal.py --finish-only`.
  Moving finishing up needs a measured byte-for-byte match with the same Blender and scripts first.
- The generator's arguments come from `pixal.generator_arguments`, so both routes build the same.
