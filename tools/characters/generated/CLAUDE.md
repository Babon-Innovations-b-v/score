# tools/characters/generated/

The generated person (CONTEXT.md; PRD #223): a TRELLIS.2 model made from a picture, mended where the generator fails.
Experimental. Every step keeps the model's own paint (data/checks/library-exceptions.json: a generated model keeps its
own paint) and brings in only what the generator cannot make, from the repo's own routes and score_lib.

- **Eyes** (`eyes.py`, drawn by `blender_eyes.py`, the sheet by `eyes_sheet.py`): TRELLIS.2 paints an eye on the floor
  of a sunken hole with thick painted lids and no eyeball. `eyes.py` finds each painted pupil on the model seen from
  the front (the darkest small blob a nose's height over the nose tip), the lid opening along rays out from it (the
  first steep forward rise, the margin), and sets the face module's own eyeball there (`../face/`: ICT-FaceKit's
  eyeball and its UV rings, `face.cornea`'s dome and tear film, the score_lib eye finishes), 24 mm scaled by the pupils'
  distance over 63 mm, its cornea just behind the margins and never in front of them, both eyes looking at one point
  straight ahead (the close-up photos look into the camera). The painted floor is pushed straight back (behind the
  ball, or beside it into the socket's shade) and removed where it lies inside the ball; the lids' skin and their
  inner rim stay, the rim under a clear tear film (the wet line). The iris is the library iris toned to the colour
  read off the close-up photo's iris (its fibres scaled as the record's are over its base).
  Run: `python -m tools.characters.generated.eyes <model.glb> <close-up photo> <out> --height <m>`, then
  `blender -b --python blender_eyes.py -- <model.glb> <out>/eyes.npz <library> <height> <samples> <renders>` (CPU,
  `CUDA_VISIBLE_DEVICES=`), then `python -m tools.characters.generated.eyes_sheet <name> <renders> <photo>
  <out>/stats.json <sheet.jpg>`.
- **Look at the eye close-up.** A found pupil and a ball behind its margins say the numbers are right; only the 9 cm
  frame says whether a lid still shows paint over the ball or the white stares.
- **Skin** (`skin.py`, drawn by `blender_skin.py`, the sheet by `skin_sheet.py`): TRELLIS.2's 2K paint is a blurred
  copy of the close-up photo with the face a small part of it, so the skin reads waxy. `skin.py` gives the face its own
  4K texture: the photo seen from the front over the face's box (a planar UV, `face`), registered to the model's front
  from the pupils (`eyes.pupils` onto `eyes.photo_iris`) and refined by matching the paint's detail to the photo's
  patch by patch on a 9 x 9 grid (an affine plus a smooth displacement; `check.png` shows paint and photo as a board),
  only on the photo's face (`face_mask`: its skin in one piece, holes filled; the paint's hair is not the photo's).
  The photo's light is flattened, not removed: the broad shading fitted first-order in the front's normal divided out
  (clipped to `SHADING_RANGE`, a crease's shade is the skin's own) and highlights over the matte skin pressed down and
  recoloured (`gloss_free`), the pixel's own pores scaled, never replaced. The texture's alpha is the photo's share
  (the photo's face, how squarely the point faces the camera, clear of the eye's opening), and where it fades the
  photo is toned to the paint's broad colour, so there is no seam. `blender_skin.py` mixes it into the model's paint
  in score_lib's `face_skin_light` (its random-walk skin light, oil coat and scanned pore tiles on metric
  coordinates; the T-zone a little glossier by its `sheen` region's roughness): the finish is the library's, the
  colour the person's own (data/checks/library-exceptions.json: a generated model keeps its own paint).
  Run: `python -m tools.characters.generated.skin <model.glb> <photo> <eyes.npz> <out> --height <m>` (about a minute,
  under 2 GB), then `blender -b --python blender_skin.py -- <model.glb> <eyes.npz> <library> <height> <samples>
  <renders> <out>` (CPU; the eyes are laid as `blender_eyes.py` lays them), then `python -m
  tools.characters.generated.skin_sheet <name> <renders> <photo> <out>/stats.json <sheet.jpg>`.
- **Look at the close-up.** The detail correlation says the photo lies on the paint; only the 6 cm cheek and nose
  frame says whether the skin reads as a photograph or as wax, and the three quarters whether the edge shows.
- **Hair** (`labels.py` → `scalp.py` → `volume.py` → `strands.py`, `beard.py`, `fibre.py`; run by `__main__.py`, drawn
  by `blender_sheet.py`, the sheet by `sheet.py`; the steps are in `__init__.py`'s docstring): the hair TRELLIS.2 paints
  on one solid shell with the head is split off (its triangles labelled by the model's own paint and place), a smooth
  scalp closes the hole, and the hair is regrown as strands in the shell's own shape; a man's lumpy painted beard the
  same way, as short facial hair on the beard's skin smoothed. Run: `python -m tools.characters.generated <model.glb>
  <style.json> <out> --height <m> --closeup <photo>` (about a minute on the CPU, under 2 GB), then `blender -b
  --python blender_sheet.py -- <model.glb> <out> <score_lib folder> <lift m> <samples> <renders>` (CPU), then `python
  -m tools.characters.generated.sheet <renders> <out> <photo> <sheet.jpg>`.
- **Reuse `../whole/hair.py`, never copy it.** Density, baby hairs, the parting and whorl's comb, locks, the cut,
  wave, flyaways and frizz are its functions and constants; the hair here only adds what a generated model needs (the
  labels, the scalp, the volume the guides are grown through, the beard).
- **The hair's shape is the model's.** Guides end where they would leave the hair's volume, never at a length that
  overrides the shell (the style's `length_m` only caps it). The hairline is the paint's edge (`labels.HAIR_SHARE`);
  behind the temples never under hair.py's HAIRLINE table (the paint there is hair hanging over the neck).
- **A generated model is a thin two-sided sheet** (its head hollow, open through the eyes or a bust's cut, triangles
  wound either way): the hair's volume is what its surface and the new scalp close off from the air, or what lies under
  the outermost hair seen from the head's middle (`volume.py`), never a normal's side or ray parity alone.
- **The strands' finish** is the library's strand finish (`../hair/finish.py`, `hair_strands_ash_brown`) with only
  melanin and redness fitted to the close-up's hair colour (`fibre.py`; its lightness-to-pigment table is an estimate,
  checked by eye on the sheet); the scalp and the skin under the beard wear the model's own skin colour.
- **Styles**: `data/people/hair/gen_<look>.json`, read off the close-up: `length_m` (the strands' cap), `reach_m`
  (how far under the top hair is labelled), `wave_m`, `wave_period_m`, `parting` side/none/back, `parting_m`,
  `parting_side`, `fringe_side` none/left/right/down, `beard` and its `beard_length_m`, `beard_stubble_m`.
- **Look at the sheet.** The labels picture says the split follows the paint; only the photographs say whether the
  hair reads as hair, the hairline as skin and the beard as a beard.
- **Head swap** (`head_swap.py`, inside Blender, CPU): the detailed head-and-shoulders model (made from a head
  close-up) put on the whole body. Its scale is scanned (a free-scale ICP slides along a long valley), at each scale a
  rigid two-way trimmed ICP of the head above the body's chin onto the body's head, hair and all; one level cut low on
  the neck or inside the collar, the head's cut edge laid onto the body's facing edge, eased over a band, its paint
  blended into the body's (read along each texel's normal) over a wider band, the shading normals averaged across.
  The body below the cut is never changed; a body's own hood round the neck can be kept (the `<hood>` depth). Its JSON
  holds the head-to-body matrix in the glTF frame: strand hair and eyes made on the head model follow onto the body
  with it. Run: `blender -b --python head_swap.py -- <body.glb> <head.glb> <cut depth> <out.glb> <out.json> [<hood>]`
  (about a minute, under 2 GB); look at the seam close up, front and back, before keeping a cut depth.
- **Lids, lashes and brows** (`lids.py`, after the eyes; the photo's landmarks by `marks.py`, drawn by
  `blender_lids.py`, the sheet by `lids_sheet.py`): each lid opening reshaped to the photo's (MediaPipe Face
  Landmarker's lid margins laid on the model by the iris, held inside the ball's silhouette: the photo's inner corner
  is the caruncle's, past a 12 mm ball), the lids' triangles refined (2.8 mm to 0.35 mm at the margin, closed with no
  crack) and moved: the lid's front 1.5 mm over the eye with a rounded margin, the rim's inner wall run into the ball
  (never ended under its clear film: it showed through as black), the socket's floor (anything more than 2 mm inside
  the old edge) only moved across and sunk behind the ball (laid on the margin, it folded the lid into black
  wedges). The eyeball stays `eyes.py`'s; where it sits deep (the generated corners stand 6 to 8 mm in front of it)
  the lid is pulled back over a longer fall (DEPTH_SLOPE), or the light never reaches the eye's sides. Lashes are the
  face module's (`../face/strands.py`'s lengths, curl, radius and `lash_line`) rooted on the new margins; the painted
  brows are painted over on the texture from the front view's light skin round them and regrown as hairs on the
  photo's brow band, as dense as the photo is dark there, turned as the face module's brows (`brow_angle`). The
  lashes' and brows' finish is `fibre.fibre_of` on the photo's darkest lash and brow pixels.
  Run: `uv run --no-project -p 3.12 --with mediapipe==1.2.3 --with pillow python -m
  tools.characters.generated.marks <photo> <marks.json>` (MediaPipe stays out of the repo's own environment; it
  needs libGLESv2 and libEGL, unpacked from Ubuntu's packages onto LD_LIBRARY_PATH on a box without them), then
  `python -m tools.characters.generated.lids <model.glb> <eyes out> <photo> <marks.json> <out> --height <m>` (half a
  minute, 1 GB), then `blender -b --python blender_lids.py -- <model.glb> <eyes.npz> <library> <height> <samples>
  <renders> <lids out>` (CPU; `blender_eyes.py` and `blender_sheet.py` import cleanly for it), then `python -m
  tools.characters.generated.lids_sheet <name> <eyes renders> <lids renders> <photo> <eyes stats.json> <lids
  stats.json> <sheet.jpg>`.
- **Look for black in the opening.** Black inside a lid opening is the head, never the eye: a fold (the floor laid on
  the margin), the wall under the clear film, or a slot too narrow for the light. Ray-cast the pixel in Blender
  (`scene.ray_cast`) before guessing.
- **The head in one run** (`head.py`, drawn by `blender_head.py`, the sheet by `skin_sheet.py`): colour → eyes → lids
  → skin → (hair later) → onto the body, each step on what the one before made. The eyes sit `eyes.EYE_FORWARD_M`
  forward of their rim rest and wear the photo's own iris (`eyes.iris_picture`: unrolled off the photo, its pupil at
  the photo's share, catchlights and the lid's shade filled from the turned iris, the limbal ring darkened; the
  pupil's triangles wear it too). The lids grow no brows and leave the painted ones (`lids.made(brows_grown=False)`):
  the skin runs on the lids' mended mesh with no clearance from the eye's floor, so the photo covers the brows and
  the lids up to their margins, and its triangles are skin wherever they wear the photo. Lashes come as many and as
  long as the photo's dark pixels over the upper margin say (`lids.lash_share`). Registered on the raw paint (the
  toning moves the face's clusters apart). Where the photo does not reach, the paint's dark baked shading is lifted
  and its light under the surface lowered (`skin.paint_shade`): TRELLIS.2's dark socket and nose paint goes orange
  under the random-walk skin. Run: `python -m tools.characters.generated.head <model.glb> <cut-out.png> <close-up>
  <marks.json> <out> --height <m>` (under 2 minutes, 1.6 GB), then `blender -b --python blender_head.py -- <model.glb>
  <out>/eyes/eyes.npz <library> <height> <samples> <renders> <out>` (CPU; before is the raw model), then `python -m
  tools.characters.generated.skin_sheet <name> <renders> <photo> <out>/skin/stats.json <sheet.jpg>`.
- **Colour** (`colour.py`, before every other step): TRELLIS.2's paint drifts from its photo on glossy and dark
  garments (2026-11-26, sRGB photo against paint: a sage puffer (131, 137, 123) painted (65, 72, 68), brown boots
  (89, 51, 41) painted (14, 3, 0)); its metalness is 0 and Blender's import reads the maps rightly, so the paint is
  toned toward the cut-out photo garment by garment in CIELAB (clusters of paint and height matched to the photo's
  connected garments through the front view; one median and spread move per garment, its folds kept). Run: `python
  -m tools.characters.generated.colour <model.glb> <cut-out.png> <out.glb> <report.json>` (10 s, 0.5 GB); the
  report lists each cluster's paint and photo colour. Look at the front render beside the photo: the boxes laid by
  their bounds miss on the head, so a head cluster that lands mostly on specks keeps its paint.
- Test: one file for the module (`test_a_generated_head_gets_real_eyes_and_regrown_hair.py`), a row per step
  (`marks.py` reads a real photo with MediaPipe and has no row; `lids.py` reads its JSON).
- **Cloth** (`cloth.py`, drawn by `blender_cloth.py`, the sheet and film by `cloth_sheet.py`; owner 2026-11-26 of the
  skinned walk: "moving creates a lot of warping"): still_rig's rigged person (rig it `--person` with a palette of no
  tokens: its own paint, ungraded) is split by its paint and place into head, skin, jacket, T-shirt, jeans and shoes
  (a vote over the faces' edges settles each cut onto the paint's edge); the jacket and the jeans hang as cloth on
  Newton's VBD through the people cloth stage's own run (`score/stages/people_cloth/inside/cloth.py`, reused, never
  copied), everything else stays skinned. The garment is the shell's own surface (its folds and paint stay); its rest
  is the generated shape. Riding points: the jacket's collar and shoulder yoke and its cuffs, the jeans' waistband;
  the rest is free. The collision body is the SOMA mean on the bind pushed under the shell (`body_under`), the shell's
  own shoes on the feet. The person is sized to her own height (`--height`, the person's measured height, not the
  template body's). Cloth values are `data/physics/cloth.json`'s rows, never typed: no puffer row exists, so the
  jacket hangs as denim (named in cloth.json's record). Run: `python -m tools.characters.generated.cloth <body.glb>
  <clips rig.npz> <out> --height <m> [--device cuda:0]` (on the processor about 6 s a frame: about 25 min for the
  walk; on the card through the card queue), then `blender -b --python blender_cloth.py -- <repo> <body.glb>
  <out>/cloth.npz <library> <renders> cloth|skinned <samples> <size> [<film samples> <film size>]` (CPU) for each of
  the two, then `python -m tools.characters.generated.cloth_sheet <cloth renders> <skinned renders> <out>/cloth.json
  <sheet.png> <title> [<film.mp4>]`.
- **Look at the film.** The deepest loose point inside the body, the stretch and the drift say the run held; only the
  side-by-side film says whether the jeans swing and the jacket hangs as cloth or still read as a stretched skin.
