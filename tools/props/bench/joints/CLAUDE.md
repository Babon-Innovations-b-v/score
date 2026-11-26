# tools/props/bench/joints/

A made model's moving parts run in Newton (#177, PRD #159): the parts step's parted GLB laid in a place of its own,
its parts joined by `tools/usd/physics.write_parted` and driven toward their far limits, the physics trial
(`score/stages/physics/inside/physics_trial.py`, Newton with MuJoCo's solver, in its own Python) stepping it, and
each part measured: how much of its range it travels, how far past its limit it goes, a spin how far it turns.

- The object is the parts' still frame; only the parts move. A part passes at `REACHED` of its range and no more
  than `PAST_SLACK` past it. Never loosen a bar to pass a model: a part that does not open is the cut's or the
  joint's fault, found at its source (maker/parts.py).
- The trial runs on the processor (Warp's CPU device), never the card: a model's few parts take seconds, the same
  answer as on the card, and the step never waits behind another session's card job.
- Test: `test_a_made_models_parts_open_to_their_limits_in_newton.py` (its Newton run only where the trial's Python
  is built; skipped in make tests' sandbox home, said so).
