# score/stages/machines/

The machines stage (experimental, PRD #6): `machines-layer@<place>` lays each machine of `data/machines/<place>.json`
(the garage's rover today) in the place as `layers/machines.usda` plus its asset, which the assembly takes
(`assembly.take_machines`). `__init__.py`'s docstring has the make and the gates; `ship_trial.py` the ship's prop-route
trial in a world of its own.

- **Made models only.** A machine is a prop-route take the place's surface line paints and bakes (its take listed in
  `data/surfaces/<place>.json`, which this stage never edits: ask the captain). Code lays it out: turned across or along
  its support, centred on it, let down onto the first thing under it. Never move a machine by hand to pass `resting`:
  fix the record (`on`, `turn`, `drop_from`) or the layout rule.
- **Motion and effects are not here.** They ride the machine's prim, `/<place>/Objects/<model>`, from the motion and
  effects stages. Keep that path stable.
- **The likeness gate's DINOv2 half** is not judged until `likeness.LIKENESS_LEAST` is set; `outline` alone does not
  tell like shapes apart (props overlay).
- `machines_test.py` lays a stand-in rover on the garage's seed and breaks each gate once.
