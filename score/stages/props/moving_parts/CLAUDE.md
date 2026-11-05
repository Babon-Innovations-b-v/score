# score/stages/props/moving_parts/

**Objects with moving parts are built in code, their parts apart and each on its pivot** (#19, decided 2026-11-05:
one Pixal3D model cannot open or turn; organic one-piece objects stay on Pixal3D). `parted(row, kinds)` names the rule
a row takes: a door kind whose words say double (two leaves hinged on the jambs' inner faces, opposite ways so both
open to one side, in a still frame), a hatch (a door kind named hatch, or lying lower than it is wide both ways: a lid
on the level hinge along one edge, in a still rim), a wheeled vehicle (a vehicle kind not on tracks and not a drone:
a body over four wheels spinning on their axles). A single hinged, sliding or rising door moves whole and is no
parted row. `build` lays it at its row's size in a final take's frame (y up, the longer ground side along z, centred
over its floor), `write` gives `model.glb` and `parts.json`.

- **The part's name is the pivot's interface.** Each part is a node named `<part>__<joint>_<axis>[n]` (`hinge` or
  `spin`, x, y or z in the object's own frame, `n` the negative way), its node's origin its pivot; a still part has
  its name alone. The motion layer reads joints off those names (`score/stages/motion/from_design.PART`,
  `parts_of`) and turns each part about its own origin (`tools/usd/motion_layer.py` `about` {"pivot": true},
  `axis`), so a route that lays the model must keep its nodes' names and origins.
- **Every part names a library recipe** (`data/library/materials.json` `recipes`: painted metal, chequer plate,
  rubber); the scene library's variant of it is the finish route's to choose, never a colour of the build's own.
- **Not wired into a paid row yet.** `pixal_row`, the finish route and the bake are what would take this build as a
  take's files; changing them re-keys paid rows, so the hookup waits for a free moment between Buys (its state on
  #19). Import this package inside functions only, never at a paid row's module level.
- `test_a_moving_thing_is_built_with_its_parts_on_their_pivots.py` holds the rules on env1's kinds of rows; the
  motion side is held by `score/stages/motion/test_a_thing_moves_as_its_design_says.py` (a parted double door and
  hatch moving on their pivots).
