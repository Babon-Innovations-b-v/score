# tools/cloud/sim_measure/

Sim body measure folders (#70: a folder with `scripts/go.sh`, its jobs' done markers, `runs/`) on one rented card
machine instead of this PC (owner, 2026-11-04: every sim body run in the cloud, never on his PC). `cloud.py` runs here,
`on_machine.py` on the machine; their docstrings are the contract.

- **Level 1's route, not a copy.** The job is a blender_cloud.py job of level 1's kind (`sim-body-l1`), env
  (newton_env.sh) and classes; on the machine level 1's `on_machine.py` (carried up from the repo) gives the card
  queue, the systemd-run stand-in and the stop. Never rent from here.
- **Paid.** Every call rents a card machine and runs only under a cleared run or the owner's override.
- **A go.sh takes `${PY}`, `${REPO}` and `${LANES}`** from the machine (this PC's defaults beside them) and skips its
  done jobs, so a folder resumes where the PC or a cut-off job left it. Every repo path in it (the card queue,
  PYTHONPATH) is named from `${REPO}`, the carried repo, never written: `cloud.py` refuses a folder's script that
  writes a checkout's path (2026-11-04: a go.sh naming the main checkout ran from a worktree, every job dead at once).
- Test: `test_a_measure_job_carries_its_folders_and_runs_each_go_in_turn_until_its_minutes.py` (nothing rented).
