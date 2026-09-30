# tools/props/

The prop tool chain: a picture made from a sentence, a model made from the picture, and the import
that brings it into the game. The heavy runtime lives outside the repo, under `~/.farm-factory-props`
(`paths.py` says where). Skill: `make-prop`. Bible: `workflow/bootstrap` (the runtime) and
`build/release` (the asset gate a prop must pass).

- **Pixal3D runs only through `pixal.py`.** Never call image-to-3dlab's `pixal3d_generate.py` or
  `trellis-cli` directly, from any session. Two runs on one graphics card crash the box, and
  `pixal.py` is what holds the card through `card.claimed()` while its generator runs.
- **One run on the card at a time, for now.** Two Pixal3D runs were measured to share safely
  (2026-09-28), but the PC blue-screened four times on 2026-09-29 and 30, twice while two runs
  shared, with its memory overclocked; `card.SHARING` is off until the owner says the machine is
  stable, and `shared=True` then waits like any claim. Never add `shared=True` to anything that
  was not measured beside a Pixal3D run. Bulk work goes to the cloud (`cloud/`); no heavy local
  work runs unattended overnight until then.
- **Hold the card only while it works.** The cut-out, the finish (Blender) and the upright and
  padding steps run on the processor, outside the claim, so the next session's generator can
  start. Anything new that runs on the card goes inside `card.claimed()`; nothing else does.
- **Stop only your own process, by its number.** `pkill -f` on a pattern such as `trellis` or
  `run.sh` stops every session's run.
- **`vendor/image-to-3dlab` stays as released.** Change how it is called from here, never the copy.
- **Edit a finished model's file directly** (`glb_file.py`): a round trip through trimesh or
  Blender drops its maps or its smooth normals.
- Checks are plain scripts run by the gate with the system python (`*_test.py`); one that needs
  numpy hands itself to the prop environment, and says it skipped on a box without one.
