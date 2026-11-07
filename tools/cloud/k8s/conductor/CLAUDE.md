# tools/cloud/k8s/conductor/

The conductor in babon's cluster (#76, the plan of 2026-11-07: issue #76's comment "Plan: the conductor moves into the
cluster"): its objects as plain manifests, rendered by `__init__.py` (its docstring is the shape) and checked with
`python -m tools.cloud.k8s.conductor check --image <ref>` (kubectl's server-side dry run; nothing is applied here:
the cutover applies them, step 7).

- **One node, one file system.** The store's volume (`score-store`, ReadWriteOnce, `sbs-5k-retain`, 250 Gi) and every
  pod that writes it sit on babon's pool `score-conductor-z2` (role `score-conductor`, one POP2-HM-16C-128G in
  fr-par-2, min 1 max 1; babon's `engine/infra/ops/pool_fallbacks`, made by its sizing script), the CronJobs and the
  drive pods beside the conductor's pod by pod affinity on the hostname: the store's flock, hard links and fsync mean
  what they mean on the VM. Never a network file system.
- **The VM's paths.** The volume's folders mount where the VM has them (`MOUNTS`): no record's path changes, a frozen
  copy (a git worktree of `~/projects/score`) reads the same in every pod.
- **The units.** `units.py` runs the VM's always-on units in the conductor container (listener, health, update,
  secrets, sweep, resume at the start and every 5 minutes: a drive pod cut at this boot leaves its run `running`, started again once, `score/graph/runs.cut_at_this_boot`); sync, backup and the backup check are CronJobs (Forbid). Image:
  `tools/cloud/images/conductor/` (the runner image plus restic, scw, kubectl, the secret reader and
  `score-conductor-start`).
- **The agents** reach only the door: ServiceAccount `score-door-agent` may get and port-forward to `score-conductor-0`
  and nothing else, never exec (exec runs any command past the allow-list); the NetworkPolicy lets nothing in over the
  pod network.
- **Secrets by name**: the scw config Secret `score-conductor-scw` is made at the cutover through kubectl's stdin from
  `score-conductor-key`; every other secret is read by name through `score-secret-reader`.
- Test: `test_the_store_is_written_on_one_node_and_agents_only_reach_the_door.py`, no cluster.
