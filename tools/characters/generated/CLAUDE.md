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
  checked by eye on the sheet); the scalp and the skin under the beard wear the model's own skin colour. Brows stay
  paint for now.
- **Styles**: `data/people/hair/gen_<look>.json`, read off the close-up: `length_m` (the strands' cap), `reach_m`
  (how far under the top hair is labelled), `wave_m`, `wave_period_m`, `parting` side/none/back, `parting_m`,
  `parting_side`, `fringe_side` none/left/right/down, `beard` and its `beard_length_m`, `beard_stubble_m`.
- **Look at the sheet.** The labels picture says the split follows the paint; only the photographs say whether the
  hair reads as hair, the hairline as skin and the beard as a beard.
- Not here: lashes (the model has none; the face module's grow on ICT's lid cards, which a generated head lacks) and
  lids reshaped to the photo's opening (the lids stay the model's).
- Test: one file for the module (`test_a_generated_head_gets_real_eyes_and_regrown_hair.py`), a row per step.
- **Head swap** (`head_swap.py`, inside Blender, CPU): the detailed head-and-shoulders model (made from a head
  close-up) put on the whole body. Its scale is scanned (a free-scale ICP slides along a long valley), at each scale a
  rigid two-way trimmed ICP of the head above the body's chin onto the body's head, hair and all; one level cut low on
  the neck or inside the collar, the head's cut edge laid onto the body's facing edge, eased over a band, its paint
  blended into the body's (read along each texel's normal) over a wider band, the shading normals averaged across.
  The body below the cut is never changed; a body's own hood round the neck can be kept (the `<hood>` depth). Its JSON
  holds the head-to-body matrix in the glTF frame: strand hair and eyes made on the head model follow onto the body
  with it. Run: `blender -b --python head_swap.py -- <body.glb> <head.glb> <cut depth> <out.glb> <out.json> [<hood>]`
  (about a minute, under 2 GB); look at the seam close up, front and back, before keeping a cut depth.
