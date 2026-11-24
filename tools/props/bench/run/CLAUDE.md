# tools/props/bench/run/

The prop benchmark's render and route runner (#163, design on #162): each NVIDIA SimReady asset of the set drawn as
the prop route's close-up, then made again by today's two routes from that picture and its row alone. `bench.py` is the
way in (its docstring has the commands); `closeup.py` runs inside Blender.

- **Free, on this PC's card only.** The render goes through the card queue (place_build/render.queued); route A's
  takes through `tools/cloud/batch.py` and its finish through `blender_cloud.py`, both under `SCORE_CLOUD=local`
  (score/stages/props/pixal_row's own calls); route B's TRELLIS.2 through `make`'s card queue. `route` is refused
  without `SCORE_CLOUD=local`. Nothing paid runs here: the close-up redraw (Nano Banana Pro, tier 2) is not called;
  on branch A the finish route and the solid copy are recorded as not run (`NOT_RUN`).
- **Branch B's finish** (`finish.py`, #168): the final model through the surface stage's finish route (views, list,
  split, parts; the list asked of Claude as a place's line asks it, EUR 0), on the benchmark place's surface library:
  score_lib's surfaces in force with a recipe (the adopted tiling set at its fitted settings, the recipes), each colour
  a palette token; a surface painted for one model, or with no recipe, is left out by name. TRELLIS.2 gives no
  close-up camera, so one is fitted from its outline against the cut-out close-up (`rgba.png`; surfaces
  close_up_fit.py, #171), and text marks are drawn as text decals through it; the bake is a place's and not run. The
  measures read its parts as B's finish groups and each part's surface family (`family`) against the truth's.
- **A close-up's scope holds MEMORY_GB (12)** (#203): the tool organizer cart's close-up (5.5M triangles, 27 maps of
  4096) peaks at 8.8 GB and was killed under the queue's own 8 GB in tc4 to tc6, its kill read as exit 124. A Blender
  killed past its cap exits render.KILLED (137) and its gap says so; a time-out is 124 alone.
- **Nothing goes into score_lib, and the library read is a scratch checkout** (`--library`, a detached worktree; the
  shared checkout is refused). `make` runs with `take_in=False` in a scratch place folder; entries are fetched by
  score_lib's own command into job scratch, never the library's file cache.
- **Every step's output is a store object, its blobs in the store bucket at once** (`Kept.keep`: `put_tree` into the
  run store, `offload.push` of each blob). The run's folder `<PROPS_HOME>/bench/<run>/` holds only its index, the
  batch's inventory, list and logs; `index` stores that folder too. Job scratch (`<PROPS_HOME>/tmp/bench163-<run>/`)
  and a take's files in WORK/pixal are removed once kept.
- **One try a step.** A step that fails is its asset's gap on that branch, its reason in the index, and the steps after
  it are not run; a step the index holds is never run again, so a stopped run is taken up with the same `--run`.
- **B's `look` step** (#182, after `finish`): the finish drawn as the bake paints it (`finish.look_job`, `look.py`
  through the card queue): the final model whole, its own vertex normals kept, each slot's recipe mixed in by its
  texel mask (the finish's texels.npz) on the model's own UVs, from the close-up's camera and its up
  (`finish.look_axes`: a flat row straight down, +y up), under the close-up's own light (closeup.lit, #200: under
  two suns and an even grey world chrome reflected only that grey and was drawn dull); `look.png` (1080) and `look-360.png`. Then the mesh alone in
  plain white (`bare.png`) and `holes.json`: `look_holes`, the share of its silhouette the look shows as background or
  the mesh alone black (normals turned into the body, folds), which the measures judge as `look.holes` (#159). A finish with no texels.npz, or texels of several pictures, is the step's gap. Every recipe of
  recipes.py draws: a colour setting a variant names none of is its own colour, a printed or screen surface with no
  picture draws a clear one (`part_spec`). look.py lays the mesh in the model's own frame first (`laid`, #185:
  final.glb's mesh sits under a turned, scaled `fitted` node, and in its object coordinates the decals printed nowhere
  on the face). Each text mark is then read back where it was drawn (`finish.marks_read`: look.py's `marks.json`,
  each box grown by READ_MARGIN, asked of Claude on the subscription, EUR 0: no free local OCR is installed here) into
  `read.json`, which `measure` holds to the close-up's words (`look_found`, measures `look.read`). A part is resolved
  as the bake resolves it (its variant in its own token, then the list's settings over it: route_settings.set_spec,
  its second shade moved with its colour) and a glass is drawn with its alpha as the bake now carries it (#186).
- **The measures count only the specks the look draws** (#159, `seen_faces`: finish.look_faces casts each drawn pixel
  of look.png through look.json's camera onto the model; the side's `face_seen`), for a truth case and a pictured one.
- **B's measures judge its look** (#184, `judged_look`): the kept look held by the picture judge
  (tools/props/bench/judge) to NVIDIA's render and, with `--previous <run>`, to that run's look of the asset; the
  group `picture` in measures.json.
- **The material class is the route's, never the truth's** (`material_for`: a word of the id, else the kind's
  class), the same for both branches; the truth's physics material is what the measures compare it with.
- **B's `physics` step is make's physics on its finished model** (#159, #161's rules through maker/sim.py): each
  finish part's class its library surface's (the given class only where a surface names none), each of make's hulls
  the class of the faces inside it, and a real-world mass a part from Claude (EUR 0, the close-up shown), its bulk
  density held to NVIDIA's band. The measures read it, not `sim`.
- **B's `parts` step is maker/parts.py on the final model** (#177): the moving pieces Claude sees in the RGBA
  close-up (EUR 0), cut through the finish step's fitted camera (`camera.json`), jointed; each part's mass its share
  of the physics step's finish groups by area and its class theirs of most area (each part keeps its finish groups).
  It keeps `parts.json`, `face_parts.npy` and `parted.glb`; `measure` reads it (`parted`) for the parts measures.
- **A made model's own paint is read with it** (`painted`, #192): points on its surface with its base colour, which
  the measures' `orientation.heading` holds to NVIDIA's look with the model as laid, no axis turn search.
- **The measures read every side in the truth's frame** (`measure`: glTF's Y up and a Y-up stage turned to Z up by
  `Y_UP`, metres), the made model's physics from its own physics step, the withdrawn models of an overlap target at
  the size they were laid at; `measures.json` keeps `found` whole so a recalibrated bar re-judges a kept run.
- **Read a made model as the gate does** (`mesh_of`: welded across UV seams). Unwelded, TRELLIS.2's crate split into
  thousands of pieces and the gate's piece count took 40 GB (2026-11-23).
- **The close-up draws the asset as rgba.png does** (#202): its floor is a shadow catcher seen by the camera alone,
  so no bounce or mirror of it lights the asset (tc6's stove walls and desk legs, light bare metal, read white on the
  backdrop and steel in the route's input); `render_asset` refuses a close-up `drawn_apart` from rgba.png by over
  ALIKE_DE.
- **The close-up look** is the prop route's (tools/props/closeup/check.py: TURN_DEGREES, LOOK_DOWN_DEGREES,
  `look_down`, `lies_flat`); change it there, never here. Front is the asset's -y side; a flat row is seen from
  straight above with +y up.
- **A pictured case** (a set row with `picture` and no address, #159) is not drawn: its `render` is its close-up
  checked out of the store, and `measure` holds each branch's model, and the 2099 session's own makes of it
  (`made_before`, branch `old`), to that close-up and its target size (measures.pictured). Its row keeps no camera,
  so B's look is drawn from the one its finish fitted on the close-up (`finish.look_view`: camera.json), and the
  picture judge holds that look to the close-up itself (and `--previous`'s look), at PICTURED_BARS (#159 round 7).
- Test: `test_every_asset_is_framed_whole_and_every_step_kept.py` (a stand-in for Blender, a small USD box, a store and
  a bucket in folders, the box again as a Y-up glb and a Y-up stage, and through the finish on a three-surface library
  with a stand-in list).
