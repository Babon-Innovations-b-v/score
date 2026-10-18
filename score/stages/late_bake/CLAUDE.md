# score/stages/late_bake/

The late-bake stage: a code-built kit's pieces laid after its run, baked with the material library on rented cards,
one paid node `late_bake@<room>` of its own runner (`python -m score.stages.late_bake run <room>`).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **The room's kit script writes the layout** (KITS: today the camp's, tools/props/scene/camp_kit.py); route.py's
  late-plan plans the pieces whose `model` is not in the room's made folder; library_bake.py bakes them.
- **Gates read make_kit's reports**: every planned model made, every slot a library surface (variant or printed
  picture). A part painted outside the library fails.
- **After it passes**, `route.py late-lay <output layout> <output made> <room>` puts the pieces into data/kit/<room>.json;
  a laid piece needs a `row` of its own, or late-lay takes out every piece of the row its kind names.
- Its own table, like the people stage: a kit is not a place's stage.
