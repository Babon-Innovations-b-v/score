# score/stages/effects/inside/

The effects that Newton makes, run in the physics trial's own Python (`../../physics/inside/newton_env.sh`: one
shared env, built once under `$PROPS_HOME/envs/newton_env`; Newton 1.7.0 with Warp, on this PC's card or a rented
one). The effects stage (`../__init__.py` `poured`) runs a script here for each emitter whose kind has a `newton`
block in `data/checks/effects.json`, under the gravity of the scene's body, and lays its particles through
`tools/usd/effects.py` (`baked`). Never import these from the score venv: one USD library a process, and Newton pins
its own Warp. The rules are the parent overlay's.

- `newton_pile.py`: a granular pile by implicit MPM (Drucker-Prager, its friction angle mapped onto Newton's yield
  cone in triaxial compression), the bore's cuttings let out in slices over the pile's top: the drilling rig's
  `drill_cuttings`. The flank it settles at depends on the grid: 2.5 cm gave 24 degrees, 1.5 cm 27, 1 cm 30.7 to 32
  (measured 2026-10-27 on an RTX 5080, about 55 s); never coarsen it to save time.
