# score/stages/ship_kits/

The ship-kit stage: a ship place's shell kit (its code-built pieces) baked with the material library on rented cards,
one paid node `ship_kit@<place>` of its own runner (`python -m score.stages.ship_kits run <place>`).

- **ship_kit.py writes the whole layout** from the place's plan and inventory; the stage keeps the code pieces only
  (a prop-route row's pieces come from its own take); route.py plan makes the make_kit jobs; library_bake.py bakes them
  in the cloud. Nothing heavy runs on this PC.
- **Gates are the late-bake stage's**: every planned model made, every slot a library surface.
- **After it passes**, route.py `layout` and `install` put each kit in place (data/kit/<place>.json), all ship places in
  one push: an installed kit re-keys every place's free scene-record.
- Its own table, like the late-bake stage: a kit is not a place's stage.
