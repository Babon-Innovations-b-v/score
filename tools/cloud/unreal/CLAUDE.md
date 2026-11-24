# tools/cloud/unreal/

Unreal Engine 5.8 renders of a place's shot on one card of the Kubernetes cluster (PRD #215, #222; findings #216).
`render.py` runs here (the way in; its docstring has the command), `on_card.py` in the pod, `in_editor.py` inside
Unreal's editor Python; `_twice.py` and `_cost.py` are render.py's.

- **The engine is never in this repository** (Unreal Engine EULA §4): no engine code, Engine Tools or Epic content here,
  ever. What is here is ours (MIT): Python that drives `UnrealEditor-Cmd`, its settings and the image recipe. The image
  (`tools/cloud/images/unreal/`, FROM Epic's `ghcr.io/epicgames/unreal-engine`) goes only to the project's private
  registry, which the backend refuses when public (`scaleway.registry_namespace`); never push it anywhere else.
- **Logic outside Unreal, the engine part thin.** Everything that decides (the project's settings check, the shader
  cache's name, the job, the passes and their commands, the render-twice check, the cost) is plain Python tested here
  without the engine; `in_editor.py` only applies shot.json through the `unreal` module.
- **Cluster only** (SCORE_CLOUD=k8s): the nodes inject NVIDIA's compute libraries only, so the image carries the
  graphics and Vulkan user libraries for exactly the nodes' driver (NVIDIA_DRIVER in its Dockerfile); `on_card.py`
  refuses a node on another driver, naming both. A driver upgrade on the nodes means rebuilding the image. One shot, one card model (`--class`, L40S or L4; an H100 has no ray-tracing
  cores), since L40S frames come out slightly darker than other cards'.
- **The shader cache rides the runtime's kernel cache** (`runtime/kernels.py`): `kernel_cache` = `ddc_name` (engine,
  RHI, the project's Linux-target and renderer settings), the runtime adds the card and driver, restores it before the
  job and uploads it when it grew. Unreal's DDC goes into that folder through `UE-LocalDataCachePath` (set in Python:
  the dash keeps a shell from setting it). Never change the runtime for Unreal: every image's tag moves with it.
- **From a scene package** (`render.py --package`, #221): the project is made here (`project_made`: our .uproject and
  the REQUIRED settings) and the level on the card first (tools/unreal/scene/editor.py as a commandlet); what the
  editor refused is listed as faults in record.json and the run is then no result, only a debugging one.
- **A failure comes back.** on_card.py catches a failing step, writes record.json's `failure` and the editor's
  Saved/Logs into out/logs, and exits 0 (the runtime brings outputs back only from a command that succeeded);
  render.py fails the run on `card_failure`. Never let a step's failure skip `closed`.
- **Render twice.** The first CHECK_FRAMES are rendered again by a second editor process and compared tile by tile
  (`_twice.py`); a run whose check differs is not a result. `twice.json` always gives the largest tile difference.
- **Paid.** Only inside a cleared run (SCORE_SPEND_TICKET or the owner's override), held to the batch cap by the
  submitter; `--dry-run` prints the job. The job's attempt limit is 1: a paid failure is a gap, never a retry.
- **Library rule.** A project's finishes are our own baked maps (#217's placer); never an outside texture by name.
- Test: `test_a_shot_goes_up_as_one_ray_traced_job_and_comes_back_checked_twice_and_priced.py` (nothing rented, no
  engine).
