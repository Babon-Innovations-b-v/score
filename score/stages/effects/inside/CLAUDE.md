# score/stages/effects/inside/

The effects that Newton makes, run in the physics trial's own Python (`../../physics/inside/newton_env.sh`: one
shared env, built once under `$PROPS_HOME/envs/newton_env`; Newton 1.7.0 with Warp, on this PC's card or a rented
one). The effects stage (`../__init__.py` `poured`) runs a script here for each emitter whose kind's
matter the one rule in `data/checks/effects.json` (`methods`) gives to Newton, under the gravity of the scene's body,
and lays what it draws through `tools/usd/effects.py` (`write_surface_clip`). Never import these from the score venv: one USD library a process, and Newton pins
its own Warp. The rules are the parent overlay's.

- `newton_pile.py`: a granular pile by implicit MPM (Drucker-Prager, its friction angle mapped onto Newton's yield
  cone in triaxial compression), the bore's cuttings let out in slices over the pile's top: the drilling rig's
  `drill_cuttings`, its bore and volume the scene's ask (`../asked.py`). Every grain let out is drawn at each sample
  into one closed surface by Newton's own particle surface (`newton.geometry.extract_particle_surface`, the settings
  of its implicit MPM water example) on a grid as fine as the grains' spacing; never a share of them. The flank it
  settles at depends on the simulation grid: 2.5 cm gave 24 degrees, 1.5 cm 27, 1 cm 30.7 to 32 on the grains; on the
  surface 33.0 for 0.12 m3 (58 s) and 32.6 for the Campgrounds rig's asked 0.2 m3 (1.6 million grains, 75 s, a 62 MB
  clip of 33 samples, 230,000 triangles at rest; measured 2026-10-27 on an RTX 5080); never coarsen it to save time.
