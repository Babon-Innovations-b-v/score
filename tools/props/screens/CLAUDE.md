# tools/props/screens/

The library's screen picture (#88): what a screen shows behind its glass, drawn by rule (`content.py`, numpy and
Pillow, free, no model call, no Blender), in two of the scene's palette tokens: the glass (dark) and the ink (the
display part's own token). The `screen` recipe (`tools/props/library/recipes.py`: dark glass, its content lit from
behind) is what it paints; the screens stage (`score/stages/screens`) gives it to each screen row's display parts.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish comes from score_lib
  or a written exception (`data/checks/library-exceptions.json`); bible `architecture/components`. This picture is
  the library's own drawing in the scene's palette tokens, never a picture's texture.
- **Here, not in `tools/props/library/`**, on purpose: the people's dress rows declare that whole folder and the
  surface tiles read `recipes.py`, so a drawing there re-buys them; only the screens stage reads this folder.
- **The seed chooses**: the place's plan (outline, walls, doors as gaps with a tick, items as boxes) beside status
  text and a small chart, or a dashboard (line and bar charts, status text bars, tables). Every count and value is
  the seed's; a seed's dashboard is the same with or without a plan. Levels: 0 glass, `FAINT` frames and grids,
  `ITEM_LIT` a lit plan item, 1 content.
- Preview free: `python3 tools/props/screens/content.py <glass #rrggbb> <ink #rrggbb> <seed> <out.png> [<plan.json>]`
  (the plan as the screens stage hands it: walls as straight lines).
- Test: `test_a_screen_picture_is_drawn_from_its_seed_and_plan.py`.
