# tools/cloud/

The container path for every model step (job cloud-k8s, 2026-10-09): one pinned image per job kind, weights from a
cache instead of a fresh download on every machine, and a job spec that Kubernetes or a hand with docker runs the
same way. The machine runners in `tools/props/cloud/` stay the default; this path is chosen by `SCORE_CLOUD=k8s`.

- **`runtime/`** is copied into every image: `job.py` (the entrypoint `score-job <run> <job>`), `weights.py` (the
  node's weights cache), `store.py` (S3 object storage, or a local folder for tests and hand runs), `kernels.py` (compiled GPU kernel caches per card and driver, for a job naming `kernel_cache`). Standard library
  plus boto3 only, Python 3.12. `submit.py` is the submit side the runners call on the coordinating machine:
  `cloud_store()`, `upload_code` (a content-addressed bundle of repo paths, the kind's `models.json` with it),
  `upload_input`, `output_key`, `write_job`, `state`, `done`, `failures`, `fetch_outputs`, `image(kind)`. Each
  module's docstring is its contract; the job spec is `job.py`'s.
- **Store layout** (the provider's `object_store()`, one bucket): `code/<sha256>.tar.gz`, `weights/<name>@<revision>.tar`
  with `.sha256` beside it, `runs/<run>/<job>/` holding `job.json`, `in/`, `out/`, `log-<attempt>.txt`,
  `failed-<attempt>.json` and `done.json` (written last: a job with it is never run again). Kernel caches: `kernels/<name>/<card>-<driver>.tar`.
- **No weights in an image, ever.** The images are public-safe and the weights' licences differ: each image folder's
  `models.json` lists its models with source, pinned revision, sha256, licence and `commercial_use`, and the runtime
  fetches them once per node into `/cache` (hostPath `/var/lib/score-cache`) under a file lock. A model not for
  commercial use runs only in a job marked `tool_only`.
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
  (2026-10-09; the L4 and L40S start at once). The provider's GPU driver has no OptiX, so Cycles renders on CUDA.
  `images/warm.py --classes ...` renders `tools/blender/inside/warm_kernels.py` on one machine a class (before,
  first node, new node) and leaves the caches in the store; run it after a new Blender or driver. Its numbers go into
  images.json (`first_render`).
- Tests run against a folder store, no cloud: `.venv/bin/python tools/cloud/runtime/job_test.py` and its siblings.
