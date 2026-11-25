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
  a palette token; a surface painted for one model, a vent pattern (#210: a mark's openings, offered to the list's
  marks), or one with no recipe, is left out by name. TRELLIS.2 gives no
  close-up camera, so one is fitted from its outline against the cut-out close-up (`rgba.png`; surfaces
  close_up_fit.py, #171), and text marks are drawn as text decals through it; the bake is a place's and not run. The
  measures read its parts as B's finish groups and each part's surface family (`family`) against the truth's.
- **Small hardware** (#212): a hardware piece the finish laid (parts.json's `hardware`, score/stages/surfaces
  hardware_pieces.py) is drawn by the look (`finish.hardware_laid`, look.py): the model's blob closed on its plate as a
  mark's is (`cut_closed`: the cut's `closed`, decal_plates.closed_round: every point in its box standing up to its
  `most` pressed straight onto the plate, the blob's core past the box where it stands over BUMP_MOST, one card over
  the box in the plate's finish, bake.closed_points and cards_over), then the library piece's mesh laid at its point
  and facing, scaled evenly to its size, in the recipe of the finish it is. Closed to its point (r13) the blob's
  faces stretched into white cracks and starbursts; laid flat in place (tc6) it folded into a dark crumpled ring. How
  far closing the cuts stretched the mesh round them is `closed.json`'s `stretched`, judged as `look.stretched`
  (1.5 at most: r13's 4.2 to 9.2, r14l's 1.09). The look and the mesh alone both draw the piece; the measures' shape
  and the physics and parts steps do not read it yet.
- **Printed panels held to NVIDIA's** (#159 round 15): the look step writes `printed` into holes.json
  (bench.panels_printed): each panel decal's corners through the look's own camera (look_frame, from look.json and the
  box look.py logs) held to NVIDIA's look there by measures.printed (NVIDIA's look moved onto the made one, each
  way's pixels drawn in the other's colour within a few pixels of their place), judged as `look.printed`. The close-up
  box is not the region: it is axis-aligned and took the stove's top and its other ink shares in (r15p 0.72 below
  r14's torn 0.75).
- **Holes through a mark's plate** (r13's black dots, decal_plates.holes_closed): a hole TRELLIS.2 cut through a
  closed mark's plate outside every closed region is closed by a box of its own in that mark's `also`, pressed and
  carded as its own box is.
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
- **The run ends by capping its home** (`capped_home`, 2026-11-24: the bench pushes nothing, so this PC's caps never ran
  and the home's store reached 191 GB): this_pc.capped (checkouts cleared, store-evict to CACHE_GB) and the library
  file cache's cap, as after a push. A blob a later step or index read wants is fetched back from the bucket.
- **One try a step.** A step that fails is its asset's gap on that branch, its reason in the index, and the steps after
  it are not run; a step the index holds is never run again, so a stopped run is taken up with the same `--run`.
- **B's `look` step** (#182, after `finish`): the finish drawn as the bake paints it (`finish.look_job`, `look.py`
  through the card queue): the final model whole, its own vertex normals kept, each slot's recipe mixed in by its
  texel mask (the finish's texels.npz) on the model's own UVs, every base colour darkened by the model's own ambient
  occlusion baked on those UVs from its shape (bake.occlusion, as make_chunky's bake does, #206; never TRELLIS.2's
  texture), darkened in the seams its decoded mesh holds where make kept one (the final step's `decoded.glb`, the
  job's `decoded`: bake.seamed, #159 r11), from the close-up's camera and its up
  (`finish.look_axes`: a flat row straight down, +y up), closed under its marks as the place's bake closes it
  (#214: bake.pressed_under before the occlusion, bake.cards_over after), under the close-up's own light (closeup.lit, #200: under
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
- **The look's light is held to the close-up** (#206, `light_step`, the input's `light` step after `render`): NVIDIA's
  own model drawn by look.py (a job's `usd`: its own materials, the look's camera, light, size and samples) held to the
  close-up it was drawn into (`exposure_held`: mean display lightness of the opaque pixels within LIGHT_REACH, clipped
  white no more than the close-up's by CLIP_SLACK); unheld, the step is a gap and B's look is not drawn (`unheld_light`).
  On tc6's 26 NVIDIA close-ups the look held at 0.009 lightness and 0.008 clipped at most; the old two suns and grey
  world sat 0.13 to 0.26 darker, and the close-up's light 20% up or down 0.024 to 0.078 away. The close-up's light
  lifts a matte surface's picture well above its own colour (the locker's NVIDIA paint of 0.32 linear reads 0.87 on
  screen), so a colour read off the close-up is taken under it in the list (route_list, #198, #204), never by dimming
  the look: dimmed, the look no longer draws NVIDIA's own model as its close-up.
- **NVIDIA's model is drawn by the same look** (#159, the input's `look` step after `render`, NVIDIA_LOOK,
  `nvidia_look_step`): look.py on NVIDIA's own model (a job's `usd`) from the close-up's camera, framed on its own box,
  under the look's light, size, samples and renderer, so beside a made look the model is the only difference (the
  owner, 2026-11-24, beside NVIDIA's own close-up: "its hard to see if its ur drawing or the pipeline"). It is what
  every made look is held to: the picture judge (`judged_look`, whose ask now names the same renderer and light, so a
  shading is the model's), each part's pattern, colour, clipped white and shading (finish.drawn_patterns, read through
  look_camera as the made look is) and B's look step's `sheet.png` (`sheet`: NVIDIA's look, the made look, the
  close-up, each laid and cut as the judge sees them). The `light` step holds this picture to the close-up. An older
  run's `light` step holds the same picture (`nvidia_looked` reads it); a run with neither cannot be measured until
  `render` draws it.
- **A wood part's grain is judged** (#159, owner 2026-11-24 on the coffee station: "wood doesnt get shown accurate"):
  finish.grain_of reads which way each part's lightness detail runs in the look and in NVIDIA's (the structure
  tensor's way and coherence), and measures `finish.grain` (bar: every wood part) fails a part whose faces NVIDIA
  calls wood, or whose finish is timber, where NVIDIA's look runs a grain and the made look runs none or another way
  (_finish.grain_held: GRAIN_STRENGTH, GRAIN_WAY).
- **The measures count only the specks the look draws** (#159, `seen_faces`: finish.look_faces casts each drawn pixel
  of look.png through look.json's camera onto the model; the side's `face_seen`), for a truth case and a pictured one.
- **B's measures judge its look** (#184, `judged_look`): the kept look held by the picture judge
  (tools/props/bench/judge) to NVIDIA's model drawn by the same look and, with `--previous <run>`, to that run's look of the asset; the
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
