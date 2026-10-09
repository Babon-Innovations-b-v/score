# tools/cloud/k8s/

The provider-neutral Kubernetes path for the job images (`../images/`, `../runtime/`): a run's job specs become
Kubernetes Jobs on node pools per capability class that scale from zero. Chosen by `SCORE_CLOUD=k8s`; the machine
runners in `tools/props/cloud/` stay as they are.

- `kube.py` is kubectl (objects through stdin); `gpu_operator.py` points NVIDIA's GPU operator at the registry.
- `manifests.py` makes the plain manifests (JSON for kubectl): one Job a job, the store Secret, the pull Secret.
- `submitter.py` is the queue and the watcher: Secrets at submit time, pool caps from the month's euros, Jobs, widening
  over classes, the ledger rows. `submitter.py run <run id>`, `idle`, `down`.
- `clusters/<provider>.py` is the only provider code: make, cap and delete the cluster and its pools, list its
  nodes with their billed times, prices, the month's bill. Scaleway Kapsule is the first (its docstring holds the
  facts read from Scaleway's docs and CLI).

## Rules

- **Nothing provider-specific outside `clusters/`.** A cluster any provider runs works if its class pools label
  their nodes `score.dev/class=<class>`, taint card nodes `nvidia.com/gpu=present:NoSchedule` (processor pools
  `score.dev/class=<class>:NoSchedule`), scale from zero with the cluster autoscaler, and expose `nvidia.com/gpu`.
- **The class order is capacity.py's** (`KINDS`, `KIND_ORDER`, `LATE`), read at submit time, never copied.
- **Why plain Jobs and not Kueue.** Kueue's flavor order falls through on *quota*, not on a pool that cannot get a
  node; noticing a stock-out needs its ProvisioningRequest check, which needs an autoscaler started with
  provisioning requests, and the managed autoscalers (Kapsule's) do not take that flag. The cluster autoscaler
  already backs off a pool whose node failed and grows another that fits the pod, which is the stock fallback
  inside a class; one global priority expander cannot hold a different order per kind (Pixal3D wants 80 GB first,
  the bakes 24 GB first). So a Job is allowed on its kind's classes one at a time, widened by the submitter when the
  autoscaler says it cannot grow them (`NotTriggerScaleUp` with a backoff or max-size reason) or no node came in
  15 min, and keeps the classes it had. Nothing else is installed in the cluster.
- **Idempotent jobs.** The runtime writes `done.json` last and exits 0 when it exists; the submitter remakes a Job
  freely (new generation) and resumes a run from its labels.
- **Money.** Refuse at `SCORE_MONTH_EUROS`; each pool's max size is what the euros left pay for `BATCH_HOURS`; the
  live cost of a run's nodes is checked every poll against the batch cap and the ceiling. Empty nodes go after
  5 min (the cluster's autoscaler settings). `down` deletes the cluster; check its own project id first, and never
  touch another project's cluster.
- **Secrets only by name.** The store and registry credentials come from the provider at submit time and go to the
  cluster through kubectl's stdin; no kubeconfig, key or id is committed (the kubeconfig lives under
  `~/.farm-factory-props/cloud/`).
- **Warm nodes.** A run puts all its jobs on the cluster at once, so its nodes stay busy while any of its jobs
  wait; a node is removed 5 min after its last pod (measured 5.5 to 6.5 min). A runner that sends a run's stages
  one after another keeps its nodes if the next stage comes within those 5 min; a pod on a warm node starts in
  about 1 s, against about 5 min from zero.
- **Kapsule or Kosmos.** Both control planes are free. Kapsule reaches one region's zones (fr-par-1, fr-par-2);
  Kosmos (`SCORE_K8S_TYPE=multicloud`) also reaches pl-waw-2, which on 2026-10-09 gave the only processor machine
  after 20 min of fr-par being out of stock. Kosmos nodes lack the zone and instance-type labels and wait about
  40 s for their network.
- **The GPU operator's own setup is about 2.5 min a cold card node** (Scaleway installs NVIDIA's GPU operator;
  the measurements are in `clusters/scaleway.py`). The precompiled driver and a shorter driver probe did not cut it;
  its images mirrored into the project's registry cut node Ready to card usable from about 160 s to 146 s on one
  run, so `up` does that (`gpu_operator.py`: a crane Job in the cluster copies them once, then the ClusterPolicy's
  `repository` and `imagePullSecrets` point at them). The copies stay in the registry: they are the project's own
  copies of NVIDIA's public images, and the next cluster reuses them. Change the ClusterPolicy only with no card
  node running: a change reinstalls the driver on live nodes and their pods fail.
- Tests: `pytest tools/cloud/k8s` with scw and kubectl stubbed; nothing is rented by a test.

## Another provider

A provider is one `clusters/<name>.py` with `KUBECONFIG`, `up()`, `idle()`, `down()`, `class_pools()` (name, class,
type, zone, max, euros a minute, billing unit), `cap_pools(euros_left, hours)`, `nodes()` (name, pool, type, zone,
status, billed creation time), `price(type, zone)` and `month_spend()`; `SCORE_K8S_PROVIDER=<name>` picks it. The
manifests and the submitter do not change.

- **AWS EKS.** One managed node group per class and zone (EKS managed node groups scale from zero; the cluster
  autoscaler needs the node group's tags `k8s.io/cluster-autoscaler/node-template/label/score.dev/class` and
  `.../taint/nvidia.com/gpu` and `.../resources/nvidia.com/gpu` to build a node for an empty group; the tags
  only describe it, so the node group must also set the label and taint on its nodes) with
  `g6.xlarge` (L4, gpu-24gb), `g6e.xlarge` (L40S, gpu-48gb), `p5` slices (H100, gpu-80gb) and `c7i.8xlarge`
  (cpu-32c-128gb), the EKS GPU AMI (driver included) and the NVIDIA device plugin. The cluster autoscaler runs in
  the cluster (Helm chart `autoscaler/cluster-autoscaler`, `--balance-similar-node-groups`, scale-down 5 min).
  Karpenter is the other route: one NodePool per class with the `score.dev/class` label, the taint and
  `karpenter.k8s.aws/instance-family` requirements; Karpenter falls through instance types on
  InsufficientCapacity by itself, so widening rarely fires. The control plane costs $0.10 an hour, so `down`
  deletes the cluster between runs. Pull secret: ECR through the node role instead (registry() then gives no
  password and the submitter skips the pull Secret). `month_spend()` from Cost Explorer.
- **GKE.** One node pool per class with `--enable-autoscaling --min-nodes 0`, `--node-labels score.dev/class=...`,
  `--accelerator type=nvidia-l4,count=1,gpu-driver-version=default` (GKE installs the driver, and taints GPU nodes
  `nvidia.com/gpu=present:NoSchedule` itself in a cluster that also has non-GPU nodes, as ours has its system
  pool), machine types `g2-standard-8` (L4), `a3-highgpu-1g` (H100), `n2-standard-32` / `n2-highmem-32`; node
  locations across the region's zones. Node auto-provisioning can make pools on demand, but fixed pools keep the
  class names exact. A cluster costs $0.10 an hour; the free tier's monthly credit covers one zonal cluster.
  `month_spend()` from the billing export.
