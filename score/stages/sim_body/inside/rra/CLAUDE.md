# score/stages/sim_body/inside/rra/

OpenSim's residual reduction (RRA, the parent overlay): `reweighed` (RRATool's mass and torso centre of mass step),
`reduced` (the pelvis' and trunk's capped, low-passed move), `within_follows`, `within_frames`, and the measures the
`adjusted` record reads (`turned_off`, `off_clip`); `_linear.py` holds what a state asks of the body and its
linearisation, `_cap.py` the caps, `_footed.py` `Footing` (the feet kept where they stood by the legs: mink per frame,
set up as the fit's and through its `fit.solved`, a frame not converged fails the run; the handwritten damped least
squares it replaced, 40 fixed steps with ranges by clipping, went 2026-10-29: one solver in sim_body).

- Moved unchanged in #70's split; changed since by #70 only where its review asked (2026-10-29): the mass step bounded
  (`MASS_MOST`) and `Footing` on mink.
- `Footing` holds each moving leg joint in its range, or where the frame it puts the feet back to (`before`, the
  fitted path) already stands past a stop, within where it stands (2026-11-03, #70): camp's walking astronaut_1, its
  right knee carried 0.38 degrees past its 0 stop by the path's low-pass on 27 of 150 frames, had that knee pulled
  in at no move, the hip turned 18 degrees to keep the foot, so `within_frames` found those frames 3.55 times the cap
  with every share at 0 and failed the run. The cap and the follows limit are unchanged.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
- `Footing` holds each leg's free directions where the frame stands them (`FreeHold`, 2026-11-04, #70): the null
  space of the feet's and the pelvis' height's weighted Jacobian over the moving leads, so it moves no foot. A leg has
  more joints than its foot's six directions (the ankle's twist; the knee's shin turn freed from the flexion), and at
  the fit's damping a step along a direction no foot sees was unbounded: env1's seated astronaut's left leg, its
  subtalar on its stop, cycled for good and failed the run (`fit.NotConverged`).
