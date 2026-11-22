# score/stages/place_build/finished/

The finish of a place_build scene (#128, owner 2026-11-19 on a generator shown as plain clay: "i kinda see that finish
step being off more often"; his rule of 2026-10-18: every finish a library surface). `__init__.py`'s docstring has
the rules; ready/ reports its faults in ready.json's `finishes`, and the place is ready only with none.

- **Judged from the scene, never from a mark the agent sets**: a shown part's bound material (a look of the place
  naming a surface the library holds, or its model's own paint when the entry's provenance says the surface line
  painted it from the library) and its model's own paint read from the model file (faces' colours by their texture
  coordinates, parts by maker/grade.py's `parts`).
- **An adopted model's own materials** pass when each names a surface the library holds (`score:surface`, written by
  the take-in, never by `put`); a surface withdrawn for a replacement (`replaced_by`) is judged by the end of the
  chain (#155).
- **A character's own paint passes only under a written exception** (data/checks/library-exceptions.json, the player
  models' texture), read at `/<place>/Characters/<name>`, the path the library check gives a place's characters.
- **One surface over a model's painted parts is a fault**, not a choice: it paints every part one flat paint (the
  clay the owner saw). `surface` refuses it. `refinish` takes the looks off: a paint the library made shows whole
  again (a glowing look kept on the part nearest its colour, a lantern's paper); a paint no library surface made (a
  take, a TRELLIS.2 model) is laid part by part as the palette variants nearest its colours (PROP_FAMILIES only: a
  desk is never a cairn's stone), the look it wore kept on its nearest part.
- **`put` finishes what it lays**: a model made from a picture (a take, Pixal3D, TRELLIS.2) in a paint no library
  surface made is re-finished at once when the place has its palette, so a picture's paint is never laid as a finish.
  A later whole `surface` on a one-paint model replaces that re-finish.
- A re-finish's parts are face subsets `paint<k>` laid over the model's mesh in the scene, its own colour subsets
  deactivated there (the model file is never changed); a laid layer (a monitor's lit screen) keeps its look.
- Test: `test_every_shown_part_wears_a_library_finish.py` (a temp library, no Blender).
