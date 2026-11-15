# score/stages/wall_kit/

The wall kit (#128, cause 2): the detail a room's walls carry (opening frames, riveted panels, padded sections, dado,
street facades with windows, sills, balconies and awnings) and its ceiling panels (a roof row named a panel, hung under
the roof's underside the scene record hands in, `writer.roof_under`: none where the roof rises steeply), built by code from the plan and the code rows its shell
lays (route `plan`), laid by the scene record (`scene_record.writer.kit_entries`) as `slab` entries and its rivets as
`specks` (builders tools/usd already has: a new builder there moved 83 paid rows' keys, people and pixal among them). `__init__.py`'s docstring has what each row's words lay.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Each piece's `from` ends naming
  the code that made it, `(wall_kit.<function>)`, by which the library check (`trace.MADE_BY`) traces it to the score_lib
  algorithm entry `ALGORITHM` (needs `definitions/algorithms/wall_kit.toml` in score_lib;
  D2 of #128: shell pieces are code-made library entries), and each finish is a scene library surface chosen by the
  piece's words, else the wall's, else named missing: never painted another way.
- **Geometry from the shell's own answers.** Faces, openings and heights come from `earth_seed/design_shell`
  (`wall_lines`, `face_reach`, `on_edge`, `wall_height`), so the kit stands on the walls the shell builds; never a
  second reading of the plan's walls here.
- **No row-name or place-name special cases**: what a row lays follows its words (PANEL_WORDS, PADDED_WORDS,
  DADO_WORDS, FACADE_WORDS) and its plan items.
- Free, pure numpy. Test: `test_a_wall_carries_the_kit_its_code_rows_name.py`.
