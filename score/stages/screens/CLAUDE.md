# score/stages/screens/

The screens stage, `screens@<place>` (free, this PC, no Blender; #88): a row whose kind shows (a screen, a monitor, a
billboard: `score/stages/row_kinds.py`) gets the library's screen picture (`tools/props/screens/content.py`) on its
take's display parts, over its bake. The module docstring has the make and the gate.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish comes from score_lib
  or a written exception (`data/checks/library-exceptions.json`); bible `architecture/components`. The picture is the
  library's drawing in the scene's palette tokens; the model stays its bake's (the library check traces it by its
  bake, `score/stages/complete/library` `stored.BAKES`).
- **Nothing before the assembly moves with it.** The bake (`surfaces-bake`) stays as it baked: this stage writes a
  USD layer per pictured model over the baked asset's own namespace (`/<model>/geo` gets `screen_st`, each display
  subset a material of the picture), and the assembly makes the asset a stack of that layer over the bake
  (`take`, run after the assembly's make by `assembled`, wrapped in the stage table so the assembly package, which
  paid rows import, stays unedited). `row-kinds.json` keeps `shows` null;
  `data/checks/screens.json` names this stage for it and only the motion row's `covered` reads it, so no row that
  declares row-kinds.json (sound, settle, crops, the bake) moves. Run `score moved` before a push: an edit under
  `tools/props/library/` or to `row-kinds.json` re-buys paid rows.
- **Display parts**: a model's lit surfaces (a `glowing` recipe or the screen family in the bake's `specs.json`) whose
  library name holds a screen word (`screens.json` `words`), else its largest lit one; all of them one picture, seeded
  and inked by the largest. Each screen of them (pieces joined edge to edge over `SCREEN_LEAST` of their area) takes
  the whole picture, laid flat on its front, upright, unmirrored; crumbs take their nearest screen's frame.
- **A screen take its bake made with no display part is a gap** (`batch-gaps.json`, gate `pictured`, moved by the
  table's `BATCH_GATES`): the finish list gave it no glowing or screen part, so its fix is upstream (the list).
- **Measured on env1's accepted bakes, 2026-11-06** (free, this PC): 16 models pictured in 12 places; gaps:
  engineroom screen_1, garage monitor_screen_1, habitat tv_1, quarters laptop_1; square's and stairwell's screens
  were not baked. Where the paint labelled the screen's faces noisily (lab's monitor, quarters' monitor, greenhouse's
  computer, galley's wall screen) the picture shows only on the faces labelled the display part.
- Test: `test_a_screen_row_shows_its_picture_over_its_bake.py`.
