# tools/cloud/k8s/job_queue/

The box's one job queue (#76, build spec step S4; owner, 2026-11-07: "make every score job a cluster job ... jobs that
need the same env setup, get chained in a qeue, and idle time is minimized"). Behind `SCORE_K8S_QUEUE`: `cluster_jobs.run`
sends its runs through it (S6), the runner's pod makes among them (S8, `score/graph/pod.py`), so with it unset every path is today's.

- `__init__.py` is the client: `enqueue` (inbox file written whole), `wait` (state file; the CLUSTER_WAITING mark;
  `Stale` after `QUEUE_TAKEOVER_SECONDS`), `cancel` (a run its client took back, never assigned again), `spent` (the
  box's euros, a stop line's base), `fresh`, `start` (the process through `detached.py`, one a box by its lock).
- `__main__.py` is the process (`Queue.tick`): four looks at the cluster a tick (the box's Jobs and pods, the nodes,
  the quota's room, the autoscaler's events) and at most one apply; runs from `state/`, assignments from the job store, so a restart assigns
  nothing twice.
- `admission.py` is pure: priority first, places round robin within it, a job only to a worker of its chain (image
  kind, image, commit) and band (or the next larger), the same place's worker first; room is the quota's less this
  tick's creations and this box's share (`SCORE_K8S_SHARES`, as `gpu=24,cpu=400`).
- `workers.py`: the worker Job (labels `score.dev/box`, `run=queue-<box>`, `image`, `band`, `worker`, `code`),
  what a listing says of each worker, the drives' `expected/<pid>.json`, and the ConfigMap that mounts the loop
  (`score-worker-<sha12 of worker.py>`, applied with the workers it serves).
- `worker.py` is the loop inside a worker's pod (standard library only at its top, since it is mounted alone):
  `score-job <run> <job>` once an assignment, its beat before, during and after each job, ended by go or after
  `IDLE_EXIT_SECONDS` with nothing assigned. It owns the store keys (`assignment_key`, `beat_key`).

## Rules

- **Named `job_queue`, not `queue`**: these modules put `tools/cloud/k8s` first on `sys.path`, where a package named
  `queue` would shadow the standard library's (`concurrent.futures`, boto3's transfers import it).
- **Commits stay on the conductor.** The queue writes control files under `$PROPS_HOME/cloud/queue/` and assignments
  in the job store; it writes no key, record, clearance, judgement or accept.
- **A worker is the warm hold.** An idle worker is told to go at once when a job of another chain waits for the room
  it holds, after `WORKER_IDLE_SECONDS` with nothing of its image queued or expected, and after
  `WORKER_EXPECTED_SECONDS` at most while the drives expect work of its image. No pause pods for queue workers.
- **Money is per box**: each node any of the box's pods ran on counted once (its minutes at its price), to its
  removal or the autoscaler's idle tail; one ledger row a node, kind `queue-node`. At the lowest stop line of the open
  runs nothing more is assigned or made and only this box's Jobs are deleted (`score.dev/box`).
- **Nothing one run brings stops the box's queue**: an inbox entry the queue cannot take is refused (its state over,
  each job failed, `refused` saying why) and the tick goes on.
- **A pending worker never waits for good**: its chain widens every tick its waiting shows the classes cannot be had
  (the autoscaler's "cannot grow" for its pod held NO_GROW_GRACE_MINUTES, else no node in NODE_MINUTES: submitter's
  rule; 2026-11-08, score's Paris processor pools at a most of 0 cost a processor chain 15 min a class before);
  a chain of processor classes alone that still cannot be had after its last class gives its
  queued jobs back as `elsewhere` and notes the classes in `unhad.json` for UNHAD_MINUTES, so `cluster_jobs.run`
  raises `Elsewhere` and the runner sends that work to rented machines (blender_cloud runs itself again off the
  cluster; a pod make is made here). Card work stays on the cluster.
- **A node is booked before the queue ends**: a finished worker's pod (kept with its Job an hour) hosts nothing, and
  the process keeps ticking while a node is unbooked.
- Test: `test_each_job_runs_once_on_a_warm_worker_of_its_image.py`, a fake cluster and a folder job store.
