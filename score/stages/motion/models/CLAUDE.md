# score/stages/motion/models/

The motion layer's models step (experimental, PRD #6; the layer adapter of the motion layer, CONTEXT.md "motion",
for rigid moving things): `motion-models@<place>` lays each model of `data/motion/models/<place>.json` (none
today: the old records, the garage's rover, were retired on 2026-10-21 and no rule writes one from a design yet),
made by the prop pipeline, in the place as `layers/motion-models.usda` plus its asset, which the
assembly takes (`assembly.take_layer`). `__init__.py`'s docstring has the make and the gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Made models only.** A model is a prop-route take the place's surface line paints and bakes (its take listed in
  `data/surfaces/<place>.json`, which this stage never edits: ask the overseer). Code lays it out: turned across or along
  its support, centred on it, let down onto the first thing under it. Never move a model by hand to pass `resting`:
  fix the record (`on`, `turn`, `off`, `drop_from`) or the layout rule.
- **Motion and effects are not here.** They ride the model's prim, `/<place>/Objects/<model>`, from the motion and
  effects stages. Keep that path stable.
- **The likeness gate's DINOv2 half** is not judged until `likeness.LIKENESS_LEAST` is set; `outline` alone does not
  tell like shapes apart (props overlay).
- **Boxed rows.** A row added after its place's partition ran names `"ground_box": true` (the airlock's suit,
  2026-10-12; the hangar's `ship`, its box the partition's proposals round the hull); `motion-models-boxes@<place>`
  (`boxes.py`, paid, about EUR 0.03 measured) grounds their boxes with SAM 3 and records the grounded ones where the
  box gate reads them; a box SAM 3 does not ground, and a row flagged `"ground_box": "judge"`, goes to the box judge
  on Gemini (cents an ask: two seeds, one round; a split is a gap, never a third ask). The workshop robot's eight part rows were dropped (captain, 2026-10-12): concept K10
  shows no robot, and the concept decides.
- **A record is written from the design or not at all** (owner, 2026-10-21: all old stuff is retired). With no
  record a place has no row; `motion-models-boxes` never applies to a designed place, whose boxes are its reading's.
- `models_test.py` lays a stand-in rover on the garage's seed and breaks each gate once.
