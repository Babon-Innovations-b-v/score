# score/stages/ship_kits/

The ship-kit stage: a ship place's shell kit (its code-built pieces) baked with the material library on rented cards,
one paid node `ship_kit@<place>` of its own runner (`python -m score.stages.ship_kits run <place>`).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **ship_kit.py writes the whole layout** from the place's plan and inventory: the creator's kept ones
  ({home}/design/plans, {home}/design/inventory, the plan row's `creator_plan`) where kept, the filed ones only
  for a place with none kept; the stage keeps the code pieces only
  (a prop-route row's pieces come from its own take, which the assembly lays where this layout puts them:
  `assembly/ship_made.py`, from the bake of the place that paints the take); route.py plan makes the make_kit jobs; library_bake.py bakes them
  in the cloud. Nothing heavy runs on this PC.
- **Gates are the late-bake stage's**: every planned model made, every slot a library surface.
- **After it passes**, route.py `layout` and `install` put each kit in place (data/kit/<place>.json), all ship places in
  one push: an installed kit re-keys every place's free scene-record.
- Its own table, like the late-bake stage: a kit is not a place's stage.
