# score/stages/sim_body/inside/rra/

OpenSim's residual reduction (RRA, the parent overlay): `reweighed` (RRATool's mass and torso centre of mass step),
`reduced` (the pelvis' and trunk's capped, low-passed move), `within_follows`, `within_frames`, and the measures the
`adjusted` record reads (`turned_off`, `off_clip`); `_linear.py` holds what a state asks of the body and its
linearisation, `_cap.py` the caps, `_footed.py` `Footing` (the feet kept where they stood by the legs: mink per frame,
set up as the fit's and through its `fit.solved`, a frame not converged fails the run; the handwritten damped least
squares it replaced, 40 fixed steps with ranges by clipping, went 2026-10-29: one solver in sim_body).

- Moved unchanged in #70's split; changed since by #70 only where its review asked (2026-10-29): the mass step bounded
  (`MASS_MOST`) and `Footing` on mink.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
