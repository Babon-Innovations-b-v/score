# tools/cloud/gemx/

GEM-X Body Motion (NVlabs/GEM-X, the newest upstream release) on OpenCap LabValidation's videos on rented cards, the
input of the sim body paper's validation (#98). `cloud.py` runs here, `on_machine.py` on the machine in the Python
`gemx_env.sh` builds there; their docstrings are the contract.

- **Upstream only, pinned.** GEM-X at its commit, every dependency hashed (`requirements.txt`, from `uv pip compile
  --generate-hashes`; a new pin is a new compile, never a hand edit), the weights by Hugging Face revision and sha256,
  SOMA-X's assets at tag v0.3.3 (the runtime GEM-X pins), the person detector by sha256. Code Apache-2.0, weights the
  NVIDIA Open Model License. Never code from a noncommercial or private copy of GEM-X, and no joint-angle method of
  our own on top: what comes back is GEM-X's own SOMA prediction and SOMA's own forward kinematics.
- **LabValidation from SimTK only** (public, healthy subjects), its release's layout as it unpacks.
- **Paid.** Every call rents cards through blender_cloud.py (kind `gemx`, capacity.py) and runs only under a cleared
  run or the owner's override; `--dry-run` prices it. Never rent from here, and no model runs on this PC.
- **One job a trial**, its cameras in turn; a camera's done.json (written last) keeps it from being made again. A
  card runs one job at a time until a batch's done.json files measured the card's peak (capacity.py, measured counts
  only).
- **The camera** (#98, 2026-11-07): `--fov-from <moge out>` runs each video at the horizontal field of view MoGe-2
  estimates from it (on_machine.py `--fov-x`, upstream's `camera.intrinsics`), never at the lab's calibration (a
  check only); without it GEM-X takes the image diagonal as focal length (27.5 degrees on a 720 x 1280 video, the
  calibration 43.0). done.json records which.
- **The cluster path** (`cluster.py`, SCORE_CLOUD=k8s): one job a video in the base image, many cards at once, each
  video read from the job store (copied once from SCORE's store bucket inside the provider, never through this PC),
  GEM-X's folder built into the node's cache once a node, on_gemx.py's soma.npz made in the same pod. cloud.py's
  machine path stays the fallback when the cluster's cards are short.
- Test: `test_each_trial_is_one_pinned_job_whose_cameras_come_back_as_soma_on_their_frames.py` (nothing rented, no
  model).
