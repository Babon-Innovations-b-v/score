# score/stages/settling/inside/

The settle's drop that runs in the physics trial's own Python (`../../physics/inside/newton_env.sh`: Newton, MuJoCo,
Warp, usd-core, python-fcl, every version pinned), sent by `tools/usd/drop.py` to a rented card or run on this PC.
`settle_drop.py` reads the composed stage with pxr (no UsdPhysics there: the seed's meshes are what it drops), borrows
the trial's USD-to-triangle helpers (`physics_trial.py`, so an edit there moves the settle's drop key) and writes the
record `settle.rest_poses` reads. Never import it from the score venv: one USD library a process.

- **What it holds to.** `SolverMuJoCo(use_mujoco_contacts=False, integrator="euler", cone="elliptic")` on Newton's
  sorted contacts with a 4 mm skin a shape
  (`MARGIN`: two resting on each other stand 8 mm apart, as Bullet's margins did, so stacked ones are no overlap). On
  MuJoCo's default pyramid cone every box on the toy's 5.7 degree slope spun 7 degrees about its up, and Newton sized the contact room from the ground's triangles
  (3.4 billion), so `CONTACTS` a body is given (the drop fails when it fills).
- **Not Warp's deterministic mode** (unlike the physics trial; 2026-10-27): over 32 dofs (6 loose bodies) MuJoCo
  Warp's sparse Jacobian sizes its sorted records past 2^31 (19 billion on a 20-body toy, the patched mujoco-warp of
  #60 too), a dense one is refused over 60 dofs, and its sparse inertia solve is wrong over 60 dofs in a tree (#60).
  So a drop can differ a little run to run; on the 20-body toy two runs' rests lay within the numbers on #55.
- **Bullet's rules kept**: mass 1 at the middle of the surface with the box's inertia, friction 0.9, no bounce, the
  speed damped (0.6 moving, 0.95 turning, a second), 30 s at 30 frames of 20 steps, ended early once every body
  has been still for 2 s (`QUIET`: what is left of 30 s changes no rest, only the card's minutes); a hollow piece's convex parts
  are shapes of its one body (no glued part bodies, no joints); loose objects meet only what they are stacked on; one
  laid inside a static meets the ground alone. On a card a frame is one captured graph.
