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
- **Hair** (`labels.py` → `scalp.py` → `volume.py`, `flow.py`, `curl.py` → `strands.py`, `beard.py`, `fibre.py`,
  `cover.py`; run by `__main__.py`, drawn by `blender_sheet.py`, the sheet by `sheet.py`; the steps are in
  `__init__.py`'s docstring): the hair TRELLIS.2 paints on one solid shell with the head is split off (its
  triangles labelled by the model's own paint and place), a smooth scalp closes the hole, and the hair is regrown as
  strands in the shell's own shape and flow; a man's lumpy painted beard the same way, as short facial hair on the
  beard's skin smoothed. Run: `python -m tools.characters.generated <model.glb>
  <style.json> <out> --height <m> --closeup <photo>` (some three minutes on the CPU, under 3 GB), then `blender -b
  --python blender_sheet.py -- <model.glb> <out> <score_lib folder> <lift m> <samples> <renders>` (CPU), then `python
  -m tools.characters.generated.sheet <renders> <out> <photo> <sheet.jpg>`.
- **Reuse `../whole/hair.py`, never copy it.** Density, baby hairs, the parting and whorl's comb, locks, the cut,
  wave, flyaways and frizz are its functions and constants; the hair here only adds what a generated model needs (the
  labels, the scalp, the volume the guides are grown through, the beard).
- **The hair's shape and flow are the model's.** Guides run along the shell's own grooves and paint streaks
  (`flow.py`), each in its layer from the scalp to the shell's outer surface, and end where they head out of the
  hair's volume, never at a length that overrides the shell (the style's `length_m` only caps it). Its curl, locks and
  frizz are read off the close-up (`curl.py`), never typed into the style. `stats.json`'s `coverage.outer` (the
  shell's outer surface within 3 mm of a strand) is 0.95 or more on a kept head. The hairline is the paint's edge
  (`labels.HAIR_SHARE`); behind the temples never under hair.py's HAIRLINE table (the paint there is hair hanging over
  the neck); never under the chin.
- **A generated model is a thin two-sided sheet** (its head hollow, open through the eyes or a bust's cut, triangles
  wound either way): the hair's volume is what its surface and the new scalp close off from the air, or what lies under
  the outermost hair seen from the head's middle (`volume.py`), never a normal's side or ray parity alone.
- **The strands' finish** is the library's strand finish (`../hair/finish.py`, `hair_strands_ash_brown`) with only
  melanin, redness and a grey head's white share fitted to the close-up's hair colour (`fibre.py`), read over the
  photo's whole hair (`labels.photo_hair`: off a backdrop found as smooth, not by colour, joined to the crown, down to
  under the pupils). The fit is drawn, not estimated: `data/people/hair/melanin_swatch.json` holds a strand swatch per
  melanin, redness and white share (`blender_swatch.py`, drawn as the sheet draws a head, at the photos' scale; run
  `blender -b -t 8 --python blender_swatch.py -- none none <library> 0 96 <out>`, about 107 pictures of 20 s, then
  `python -m tools.characters.generated.fibre <out> data/people/hair/melanin_swatch.json`; redraw it when the library
  strand finish or the sheet's light changes). A grey head's share and melanin are the swatch's matching its median
  lightness and its spread: mixed by lightness (round 2), an older woman's silver-white bob drew dark grey. The sheet prints
  the photo's hair colour against the drawn one's (`sheet.colours`, <groom>/colour.json). The scalp and the skin
  under the beard wear the model's own skin colour.
- **A hair-white bit is hair.** A fringe's white bits the clothes' colours claim (a cream scarf) are still strays
  above any collar (`labels.over_clothes`), and only paint darker than the skin is brows; the forehead never roots
  under hair.py's table less 2 cm (`strands.FOREHEAD`): a painted fringe lies on skin (round 3, 2026-11-27: a white
  shell bit and a clump of forehead-rooted strands on an older woman's brow).
- **Styles**: `data/people/hair/gen_<look>.json`, read off the close-up: `length_m` (the strands' cap), `reach_m`
  (how far under the top hair is labelled), `parting` side/none/back, `parting_m`,
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
  under the random-walk skin. Round 2 (2026-11-26): the skin's paint is first given the photo skin's colour
  statistics in CIELAB (`skin.paint_toned`, written as skin/paint.png and worn by head.glb), the photo covers slopes
  down to a tenth facing forward (`skin.FACING`) and a steep point counts as the front (`skin.visible`), and a layer
  hidden under the lid is never pulled through it by the lid's move (`lids.layers_kept`: the hollow sheet's inner
  wall came through as black flecks at the outer corners). Lashes shorten by the photo's lash share itself.
  Round 3 (2026-11-27), the orange band round the eyes, measured on the 9 cm frame (CIELAB, the socket band and the
  cheek against the photo's): neither the light under the skin (weight 0: the band's chroma 31 to 30), the paint (the
  photo's share there is 1) nor the de-lighting (off: 29 to 28) made it. The view did: against plain sRGB, AgX's
  medium high contrast look took the lit cheek's chroma from 21 to 12 and raised the shadowed band's from 27 to 33
  (band over cheek 2.6; the photo's 1.2, sRGB's 1.3), so the face's close-ups are developed in plain sRGB
  (`blender_eyes.VIEW`; the whole route's own renders keep AgX). And the photo's socket shade was laid twice, once in
  the texture and again by the model's deeper socket: `skin.shading` now fits the model's own `occlusion` too, per
  channel, so the band's albedo rises from L 55 to 64. The photo is also kept off the model's painted fringe and bob
  (`model_hair_free`), its own fringe and lid openings are left out of its face (`hair`, `eye_openings`: a second
  iris under an older woman's lids), and its share rises over 6 mm from its outer edge (the paint's edge at the
  temples).
  Run: `python -m tools.characters.generated.head <model.glb> <cut-out.png> <close-up> <marks.json> <out> --height
  <m>` (under 2 minutes, 1.6 GB), then `blender -b --python blender_head.py -- <model.glb>
  <out>/eyes/eyes.npz <library> <height> <samples> <renders> <out>` (CPU; before is the raw model), then `python -m
  tools.characters.generated.skin_sheet <name> <renders> <photo> <out>/skin/stats.json <sheet.jpg>`.
- **Colour** (`colour.py`, before every other step; it reads and writes each glTF primitive's own picture through
  its own UVs, never through trimesh's `force="mesh"`, which packed a swapped head's and body's pictures into one atlas
  and wrote it over the body's: the whole paint scrambled, round 2 of the cloth, 2026-11-26): TRELLIS.2's paint drifts
  from its photo on glossy and dark garments (2026-11-26, sRGB photo against paint: a sage puffer (131, 137, 123) painted (65, 72, 68), brown boots
  (89, 51, 41) painted (14, 3, 0)); its metalness is 0 and Blender's import reads the maps rightly, so the paint is
  toned toward the cut-out photo garment by garment in CIELAB (clusters of paint and height matched to the photo's
  connected garments through the front view; one median and spread move per garment, its folds kept). Run: `python
  -m tools.characters.generated.colour <model.glb> <cut-out.png> <out.glb> <report.json>` (10 s, 0.5 GB); the
  report lists each cluster's paint and photo colour. Look at the front render beside the photo: the boxes laid by
  their bounds miss on the head, so a head cluster that lands mostly on specks keeps its paint. **Garments only**:
  skin, hair, beard, brows, lips and eyes are never toned (the skin step repaints the face, the hair is regrown); a
  cluster landing mostly on the photo's body (`colour.body_zone`: its skin pieces, the head down to its skin's lowest
  row, the hands) keeps its paint, and a garment whose paint clusters differ past a photo garment's limits is split
  (round 1, 2026-11-26: a bearded man's skin, hair and beard moved as one to his photo's skin, ears and neck cream).
- Test: one file for the module (`test_a_generated_head_gets_real_eyes_and_regrown_hair.py`), a row per step
  (`marks.py` reads a real photo with MediaPipe and has no row; `lids.py` reads its JSON).
- **Cloth** (`cloth.py`, drawn by `blender_cloth.py`, the sheet and film by `cloth_sheet.py`; owner 2026-11-26 of the
  skinned walk: "moving creates a lot of warping"): still_rig's rigged person (rig it `--person` with a palette of no
  tokens: its own paint, ungraded) is split by its paint and place into head, skin, jacket, T-shirt, jeans and shoes
  (a vote over the faces' edges settles each cut onto the paint's edge); the jacket and the jeans move as **tethered
  cloth** (`cloth_tether.py`, game cloth's max distance, anim drive and backstop), everything else stays skinned. Each
  sim point is simulated but held within a tether of its skinned place: none at the riding points (the jacket's collar,
  shoulder yoke and cuffs, the jeans' waistband) and at a hem near the shoes, rising by a slope over the surface to 5
  cm on the jacket and 6 cm on the jeans; it feels only the gravity its limb's turn adds to its made hang, and the
  body draws it back toward its target, never sideways and never deeper than the skinning draws it. The drawn
  cloth is its own skinned place moved by as much as the sim mesh there stands off its target
  (`cloth_mesh.displaced`), shaded by its own normals as skinning turns them (round 4, 2026-11-27: carried in the sim
  triangle's frame, the puffer standing up to 10 cm off its sim mesh drew 17 mm rough, lumpy and dark beside the
  skinned person), so a cloth on its targets is drawn exactly as the skinned person is. A face hanging from a leg is
  never jacket, unless a long coat's: its hem is read down from the hips band by band as what is seen from outside
  (`jacket_hem`: the trousers inside it and its dark inner wall outnumber it). A scarf is its own garment where the
  open front shows two colours, one standing forward of the other (`scarf_split`); it rides round the neck. Each
  person's garment may get its own longest tether (`--tether jacket=0.10`: an open overshirt's fronts, a long coat's
  hem), and cloth.json records each garment's hem swing. The paint is read at the file's own row (`file_places`:
  read as stored, glTF's v running down, every face read its mirror row, and round 4's kinds came from places alone).
  The sheets and films are developed in plain sRGB (`blender_cloth.VIEW`, as `blender_eyes.VIEW`).
  The body under the clothes wears the person's own jacket and trousers (`under_colours`): where a sleeve fused to
  the trunk opens at the side, the gap shows the jacket's colour, not a fixed white (nor a turtleneck's black, which
  read as holes in a camel coat).
  Round 5 (2026-11-27): a garment reaching under the hip joints hangs as a skirt (`skirted`: its weights there across
  both thighs and the pelvis, the pelvis more lower down and toward the middle, never on its sleeves), so a coat's
  hem hangs as one piece instead of splitting with the thighs (the coat's middle between the legs grew 4.9 times its
  length skinned, `between_legs` in cloth.json); a jacket's sleeves fused to its sides are cut off them where its
  faces turn from the arm's to the trunk's, 8 cm or more under the shoulder (`sleeves_cut`), each piece's weights
  eased onto its own limb and each cut edge closed by a flap turned in toward the body (`flaps_of`), so the sleeve
  swings with the arm and the side stays; the sleeve's region spans the whole side under the arm, so its half on the
  trunk's side of the arm's line is copied onto the trunk 4 mm in under it (`covered`: cut alone, the coat's back
  opened wide as the sleeve left); blender_cloth splits the drawn garment the same way.
  The pelvis takes its share only toward the middle between the legs (0.3 to 0.6 there), the cloth over each thigh
  swings with it: a pelvis share over the thighs let the lifted thigh 11 to 12.7 cm through the coat's front, and
  pushing the targets out of the body point by point tore it (stretch 4.5). The hands' depth in
  the trunk and legs is recorded (`hands_in`); the arms are kept out of the coat in still_rig (`arms_kept_out`).
  **Free cloth is stopped** (coordinator, 2026-11-26): two free runs on Newton's VBD tore (the jeans stretched 90 cm
  down to and between the shoes, 19 cm inside the body; the jacket shredded). The tether makes the result at least as
  stable as plain skinning; cloth.json records every garment's numbers both ways (`garments` tethered, `skinned`).
  The collision body is the SOMA mean on the bind pushed under the shell (`body_under`). The person is sized to her own
  height (`--height`, the person's measured height, not the template body's). Run: `python -m
  tools.characters.generated.cloth <body.glb> <clips rig.npz> <out> --height <m>` (numpy on the processor, about 4
  minutes and 0.9 GB at nice 19, its seconds in cloth.json), then
  `blender -b --python blender_cloth.py -- <repo> <body.glb> <out>/cloth.npz <library> <renders> cloth|skinned
  <samples> <size> [<film samples> <film size>]` (CPU) for each of the two, then `python -m
  tools.characters.generated.cloth_sheet <cloth renders> <skinned renders> <out>/cloth.json <sheet.png> <title>
  [<film.mp4>]`.
- **The cloth runs on a sim mesh, never on the shell's triangles** (`cloth_mesh.py`; round 1, 2026-11-26: a 2.7e-11
  m^2 sliver's point went NaN in the hang before the first frame and the run wrote NaNs on). A garment's shell is two
  walls 3 to 4 mm apart with slivers, duplicates and three-face edges, and its outer wall alone fell apart into 28
  pieces, so the sim mesh is the collision body split to 1.2 cm and laid out along its normals onto the garment's
  first face whose joint is on the same limb (no armpit lands on the sleeve beside it, no hip on the hand by it; the
  head, hands and feet lay nothing), the reach smoothed a little (more pulls it inside a flare), cleaned to one
  manifold mesh and remeshed even (gpytoolbox's remesh_botsch in its own `uv run`, MIT; the rims resampled first, it
  keeps rim points fixed; a needle it leaves collapsed). The drawn surface (both walls, folds, paint) is bound to it
  by nearest triangle and barycentric place and moved off its own skinned place by the cloth's move there; skin
  weights and riding are blended over, and a piece with no riding point rides whole. The sleeves' inner sides, where
  TRELLIS.2 fused them to the trunk, lay nothing: the sleeve is open there and its drawn points ride the nearest cloth.
- **Look at the film.** The deepest loose point inside the body, the stretch and the drift say the run held; only the
  side-by-side film says whether the jeans swing and the jacket hangs as cloth or still read as a stretched skin.
