# tools/cloud/level1/

Sim body's level 1 (#70, `score/stages/sim_body/inside/evaluation/level1.py`) on a rented card machine instead of this
PC (owner, 2026-11-02: "give it a pretty strong system, so progress speeds up"). `cloud.py` runs here and drives the
batches; `on_machine.py` is the job the machine runs. Their docstrings are the contract.

- **One renting path.** A batch is one blender_cloud.py job (its `env` newton_env.sh, its `bring_every` minutes, its
  `--kind sim-body-l1`): the owner's limits, the clearance, the watchdog, the self-delete, the delete and the ledger
  are blender_cloud's and batch.py's. Never rent from here.
- **Paid.** Every batch rents a card machine (capacity.py `sim-body-l1`: `gpu-80gb-x2-48c` first, Scaleway's
  H100-2-80G with 48 cores) and needs the owner's yes; it rents only under a cleared run, as any renting call.
- **The run runs its own code.** The machine runs `<run>/src`, the copy frozen when the run began; a run frozen before
  2026-11-02 has the card queue fixed at this PC's 13.5 GB and no `--processes`, so it runs as wide as on this PC.
- **Resume, never restart.** Level 1 is stopped at its batch's minutes with its whole process group and the next batch
  resumes from checkpoint.jsonl's best (`tuning.resumed`); a chain ends on held_out.json, a failed batch or a batch
  that added no checkpoint line.
- Test: `test_a_rented_batch_carries_the_run_stops_in_time_and_resumes_from_its_checkpoint.py` (nothing rented).
