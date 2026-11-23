# tools/props/bench/run/

The prop benchmark's render and route runner (#163, design on #162): each NVIDIA SimReady asset of the set drawn as
the prop route's close-up, then made again by today's two routes from that picture and its row alone. `bench.py` is the
way in (its docstring has the commands); `closeup.py` runs inside Blender.

- **Free, on this PC's card only.** The render goes through the card queue (place_build/render.queued); route A's
  takes through `tools/cloud/batch.py` and its finish through `blender_cloud.py`, both under `SCORE_CLOUD=local`
  (score/stages/props/pixal_row's own calls); route B's TRELLIS.2 through `make`'s card queue. `route` is refused
  without `SCORE_CLOUD=local`. Nothing paid runs here: the close-up redraw (Nano Banana Pro, tier 2) and the finish
  route's Gemini list are not called; the finish route and the solid copy are recorded as not run (`NOT_RUN`).
- **Nothing goes into score_lib, and the library read is a scratch checkout** (`--library`, a detached worktree; the
  shared checkout is refused). `make` runs with `take_in=False` in a scratch place folder; entries are fetched by
  score_lib's own command into job scratch, never the library's file cache.
- **Every step's output is a store object, its blobs in the store bucket at once** (`Kept.keep`: `put_tree` into the
  run store, `offload.push` of each blob). The run's folder `<PROPS_HOME>/bench/<run>/` holds only its index, the
  batch's inventory, list and logs; `index` stores that folder too. Job scratch (`<PROPS_HOME>/tmp/bench163-<run>/`)
  and a take's files in WORK/pixal are removed once kept.
- **One try a step.** A step that fails is its asset's gap on that branch, its reason in the index, and the steps after
  it are not run; a step the index holds is never run again, so a stopped run is taken up with the same `--run`.
- **The material class is the route's, never the truth's** (`material_for`: a word of the id, else the kind's
  class), the same for both branches; the truth's physics material is what the measures compare it with.
- **The measures read every side in the truth's frame** (`measure`: glTF's Y up and a Y-up stage turned to Z up by
  `Y_UP`, metres), the made model's physics from its own physics step, the withdrawn models of an overlap target at
  the size they were laid at; `measures.json` keeps `found` whole so a recalibrated bar re-judges a kept run.
- **Read a made model as the gate does** (`mesh_of`: welded across UV seams). Unwelded, TRELLIS.2's crate split into
  thousands of pieces and the gate's piece count took 40 GB (2026-11-23).
- **The close-up look** is the prop route's (tools/props/closeup/check.py: TURN_DEGREES, LOOK_DOWN_DEGREES,
  `look_down`, `lies_flat`); change it there, never here. Front is the asset's -y side; a flat row is seen from
  straight above with +y up.
- Test: `test_every_asset_is_framed_whole_and_every_step_kept.py` (a stand-in for Blender, a small USD box, a store and
  a bucket in folders, the box again as a Y-up glb and a Y-up stage).
