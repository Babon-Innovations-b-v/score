# tools/props/

The prop tool chain: a picture made from a sentence, a model made from the picture, and the import
that brings it into a place. The heavy runtime lives outside the repo, under `~/.farm-factory-props`
(`paths.py` says where). Bible: `workflow/bootstrap` (the runtime); the checks a prop must pass are `gates/`.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **No model runs on this PC.** The owner, 2026-10-03: "My GPU is only for game tests; do all
  model stuff in batches in the cloud." The same day WSL died twice of running out of memory,
  six model processes of 6 to 7 GB loaded at once by three sessions. Every step that loads a
  model (the picture, the cut-out, Pixal3D, SAM 3, MoGe-2, the redraw) calls
  `local_models.refuse_here()` first and is refused here with the cloud command that does it:
  `cloud/pictures.py` for pictures, `cloud/batch.py` for models (one or a hundred), and
  `cloud/scene.py` for a scene's steps. What stays here has no model in it: the finish
  (`pixal.py --finish-only`, Blender and the processor), the import, the review page and
  snapshots. Anything new that loads a model calls `refuse_here()` before it loads.
  `FARM_LOCAL_MODELS=1` (set by the cloud runners on their machines) is an emergency switch on
  this PC for the owner to throw, never a session.
- **Pixal3D runs only through `pixal.py`.** Never call image-to-3dlab's `pixal3d_generate.py` or
  `trellis-cli` directly, from any session. `trellis-cli` is Pixal3D's own binary, named so because
  pixal3d.cpp is built on TRELLIS.2 code; the old TRELLIS mesher is gone from this chain (2026-10-03). Two runs on one graphics card crash the box, and
  `pixal.py` is what holds the card through `card.claimed()` while its generator runs.
- **One run on the card at a time, for now.** Two Pixal3D runs were measured to share safely
  (2026-09-28), but the PC blue-screened four times on 2026-09-29 and 30, twice while two runs
  shared, with its memory overclocked; `card.SHARING` is off until the owner says the machine is
  stable, and `shared=True` then waits like any claim. Never add `shared=True` to anything that
  was not measured beside a Pixal3D run. These card rules now matter on the rented machines and
  for an emergency run here.
- **Hold the card only while it works.** The cut-out, the finish (Blender) and the upright and
  padding steps run on the processor, outside the claim, so the next session's generator can
  start. Anything new that runs on the card goes inside `card.claimed()`; nothing else does.
- **Stop only your own process, by its number.** `pkill -f` on a pattern such as `pixal` or
  `run.sh` stops every session's run.
- **`vendor/image-to-3dlab` stays as released.** Change how it is called from here, never the copy.
- **Edit a finished model's file directly** (`glb_file.py`): a round trip through trimesh or
  Blender drops its maps or its smooth normals.
- Checks: one pytest file a module, named for its invariant (`test_<invariant>.py`, docs/bible.md
  `workflow/module-standard`), run by `make tests` in the framework's environment (numpy, trimesh and Pillow are
  in it) in a sandbox home; each file's docstring names the break that turns each test red. Here: `card.py`
  `test_one_run_on_the_card.py`, `local_models.py` and `heavy.py` `test_refused_on_this_pc.py`, `pixal.py`
  `test_raw_model_faces_minus_z.py`, `clean_finish.py` `test_crop_as_pixal3d_does.py`, `glb_file.py`
  `test_stood_up_and_kept_intact.py`.
