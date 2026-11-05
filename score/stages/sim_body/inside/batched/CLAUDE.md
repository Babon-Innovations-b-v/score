# score/stages/sim_body/inside/batched/

Every frame at once on the card (#70, 2026-11-05; the owner: "should prob just fix that now aswell, so we know what
were working with"). `Card`: MuJoCo Warp on the model Newton's SolverMuJoCo puts on the card (`model.built` with a
CUDA card, `model.on_card`), one world a state: the position and velocity stages and the inverse dynamics with the
accelerations, so every frame's needed forces, kinematics, tendon and muscle paths, lengths, speeds and moment arms
come in one launch a stage (`evaluate`, chunks of CHUNK worlds); `load` lays one state into the CPU's `MjData`, so the
frame's own reads (the skin riding its bones, `mj_jac`, the muscle curves, the drawn paths) read it as they read
MuJoCo's C. `sync` puts the model's masses, inertias and centres of mass on the card again after RRA's model step.
`_least.least_all`: `solvers.least` for every frame's static optimisation stage (`muscles.staged`, and RRA's balance) at once, float64, the
same projected Newton steps. `apart` and `CARD_TOLERANCES`: how far a person's record on the card may lie from the same
run on the processor, the measure that proves a move to the card.

- MuJoCo Warp is float32: the card's state is MuJoCo's C to about 1e-6 of each value. RRA's central differences take
  `rra._linear.CARD_STEPS` there (a place's 1e-3; a speed's and an acceleration's 1, exact for the needed forces'
  quadratic and linear dependence), never RRA_STEP's 1e-5, which float32's rounding swamps.
- Collision and constraints are disabled on the card's model: nothing here reads them (the ground's pushes are
  `contact`'s, on the drawn skin).
- Without a card everything runs as before on MuJoCo's C (`Physics.each`, `Physics.solved_all`, `rra.sensitivities`):
  that path is the reference the card is measured against.
- Measured 2026-11-05 (L4, one lane; pickup, jump, env1 standing against origin/main 290737b2, itself deterministic:
  two base runs equal): whole run 818/830/412 s to 398 (cold card cache)/288/183 s; the bones outside the skin, the
  joint error and follows within 0.03 pp, 0.03 mm and 0.002 deg, the largest residual within 1.7% of the weight and
  the largest reserve within 0.2 N m, but not CARD_TOLERANCES frame by frame: the muscles' sharing is fragile in the
  base itself. On the jump's fitted path the card's problem differs from MuJoCo's C by 1e-6 to 1e-3 (the moment arms
  float32), and `least` on it puts the mean activation at 0.21 against 0.05 on one frame, with the residual (0.1 N)
  and reserve (0.3 N m) alike, while `least` on the C problem nudged by 1e-6 moves nothing: the activations are
  decided by the moment arms' last digits. Not landed on that (#70).
- The frames' static optimisation stays on `solvers.least` (`records.frames`, `Physics.solved_all(card=False)`):
  on the card the pickup's and jump's muscles came out 24% more active on the mean (0.203 to 0.252, 2026-11-05) with
  the residuals, reserves and bones as `least`'s, and `least_all` equals `least` on every settling problem tried; the
  cause is open (#70). RRA's balance (six rows a frame) takes `least_all`.
- `least` ends its 1000 rounds unsettled on random problems with the balance rows weighed 100 against costs of 1e-3
  (2026-11-05): two runs of the same steps then part by rounding, so the test's least squares are ones it settles,
  and the clips' records are judged by `apart`.
- Test: `test_every_frame_on_the_card_is_mujocos_own_to_its_rounding.py` (Newton's Python and a CUDA card; the judge's
  check runs without one).
