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
- Not here: lashes (the model has none; the face module's grow on ICT's lid cards, which a generated head lacks) and
  lids reshaped to the photo's opening (the lids stay the model's).
