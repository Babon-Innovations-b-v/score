# score/stages/sim_body/inside/rra/

OpenSim's residual reduction (RRA, the parent overlay): `reweighed` (RRATool's mass and torso centre of mass step),
`reduced` (the pelvis' and trunk's capped, low-passed move), `within_follows`, `within_frames`, and the measures the
`adjusted` record reads (`turned_off`, `off_clip`); `_linear.py` holds what a state asks of the body and its
linearisation, `_cap.py` the caps and `footed` (the feet kept where they stood by the legs).

- Out of #70's scope ("no residual tuning here"): moved unchanged.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
