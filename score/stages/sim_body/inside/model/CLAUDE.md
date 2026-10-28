# score/stages/sim_body/inside/model/

The person's MyoFullBody as Newton builds it (`built`: SolverMuJoCo's MuJoCo model, MuJoCo's CPU backend, `DEVICE`;
no meshes given to Newton, nothing stepped) and what every later step reads off it: `body_index` (a body by the
MyoFullBody name, Newton naming it by its path), `Couplings` (MuJoCo's joint couplings: the leading dofs and each
follower's polynomial), `limited`, `own_pose` and `TO_OWN` (MuJoCo's Z up to the person's Y up), `default_pose`
(MyoSuite's `stand`), `posed_path` (each SOMA segment riding its bone), `filtered` (the zero-lag low-pass) and `rates`.

- `limited` does not clamp today: its `model.jnt_type[joint] in (mujoco.mjtJoint.mjJNT_HINGE, ...)` is False for
  numpy's int32 against MuJoCo's enum (measured 2026-10-28; `==` is True), and `muscles.Physics.stops` reads joint
  types the same way. Kept as it was by the #70 move (behaviour unchanged first); fixing it changes every body's
  numbers, so it is a change of its own, measured on the two walkers.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built (`make tests`).
