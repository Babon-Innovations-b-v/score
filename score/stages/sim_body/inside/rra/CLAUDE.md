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
- On a CUDA card (2026-11-05, #70) `Footing` given the person's file solves every frame at once there
  (`_footed_card.CardFooting`: the fit's level-3 card loop, `fit._card._solve.solved`, with Footing's own tasks, each
  row's own ranges and `Held`, the card's FreeHold: Gram-Schmidt on the tasks' reduced Jacobian); its float32 legs'
  joints come back with the frame's own frozen coordinates and the followers set again in float64. mink stays the
  reference and the solve without a card; the test's toy holds the two within 1e-4. RRA's residuals, the trunk's
  moments and the linearisation's sensitivities (`sensitivities`, `CARD_STEPS`) take every frame's state at once on
  the card (`batched`).
- `Footing` holds each leg's free directions where the frame stands them (`FreeHold`, 2026-11-04, #70): the null
  space of the feet's and the pelvis' height's weighted Jacobian over the moving leads, so it moves no foot. A leg has
  more joints than its foot's six directions (the ankle's twist; the knee's shin turn freed from the flexion), and at
  the fit's damping a step along a direction no foot sees was unbounded: env1's seated astronaut's left leg, its
  subtalar on its stop, cycled for good and failed the run (`fit.NotConverged`).
- `within_frames` keeps the move's bones inside SOMA's skin as the fitted path holds them, frame by frame and region by
  region (`fit.FrameSkins`, `skin_excess`, `SKIN_SLACK`), its shares smooth (`held_share`) and the move off the fitted
  path low-passed with the feet kept again (`smoothed_off`) (2026-11-05, #70): the freed joints' pickup kept 0.75 of a
  move that turned the arms and head with the trunk, its hands 37.7% outside the skin, its shins 30 times the clip's
  jerk.
- `cap_rows` moves, lands and poses the path moved by `total` and each column's nudge of it as one stacked path
  (`moved` takes copies x frames, each frame's couplings' map once; the run's `land` takes whole copies of the clip,
  each against the fitted path), so on the card every nudge's legs are one solve, not one a column; `sensitivities`
  keeps a frame's couplings' map for a nudged state whose leaders stand as the frame's (2026-11-06, #70: the two
  together 19 s in 3 calls of the jump's 135 s). Bit for bit the column-by-column answer: each row's solve is its own.
