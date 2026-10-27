# score/stages/sim_body/

The sim body stage (experimental, #65; PRD #56; CONTEXT.md "sim body"): row `sim-body@<place>` for a place whose
design shows people, every character of its accepted cast as a musculoskeletal body, MyoFullBody, doing its clip on the
scene's own ground. `__init__.py`'s docstring has the make and the gates; `inside/sim_body.py` is the run and
`inside/myo.py` the model's sizing, both in Newton's own Python.

- **The movement is the clip's, the physics the body's** (owner, 2026-10-27: "we have kimodo for the actual movement;
  and myobody plus mujoco and newton for the physics"). The body, root included, follows the clip exactly; nothing is
  stepped. Per frame: inverse dynamics on the MuJoCo model Newton builds, the ground's contacts, the joints' range
  stops and the muscles share the needed forces (one bounded least squares, least squared activation, the pelvis'
  six balance rows `BALANCE` times a joint's), and what they cannot give is the pelvis' residual and the joints'
  reserves: measured, recorded, gated (`residual`, Hicks et al. 2015), **never applied**.
  Never bring back a helper or any force that holds the body up or on its path: a trip or a float must show as a
  residual that fails.
- **The body is MyoFullBody, never a box body or a template of our own**: MuscleMimic's wheel (`MODEL`, pinned URL and
  sha256), fetched once to `$PROPS_HOME/models/<sha>` by `fetched`, never committed. Kept under MyoHub's Apache-2.0
  (owner, 2026-10-27, #65). Attribution, also in every `sim_bodies.json` (`ATTRIBUTION`): MyoSuite and myo_sim
  (MyoHub, Apache-2.0), with the arm and hand derived from MoBL-ARMS: Holzbaur, Murray and Delp 2005
  (doi:10.1007/s10439-005-3320-7) and Saul et al. 2015 (doi:10.1080/10255842.2014.916698).
  `inside/myo.py` writes each person's file: #60's import fixes (names without '-', full muscle parameters, explicit
  inertials, multi-joint bodies split into 1 g wrappers, Euler), the floor gone.
- **Each body is the person's own build**: the rig moved onto its look's built body (`people-body-<look>`'s rig.npz,
  an optional read, `person_rig`), recorded as `size`. MyoFullBody is sized to it per segment: thigh, shin, foot, upper
  arm and forearm by the person's joint distances, the rest by its standing height (#64: SOMA's hip and shoulder widths
  carry no signal); each muscle's length range with its path (OpenSim's scaling), its peak force kept.
- **Its muscles pull at rest**: at its standing pose (the zero pose with the knee and patella couplings applied, which
  is MyoSuite's own `stand` keyframe) MyoFullBody's muscles pull 4.2 kN passively: middle deltoid 561 N each (its path
  at the hanging arm is longer than its own length range's top), rectus abdominis 308 N, short biceps femoris 204 N,
  so static optimisation holds the lumbar extensors near full activation standing. The raw qpos0 breaks the couplings
  (the patella 1 cm off) and reads 5.3 kN with rectus femoris 555 N; never measure there. It is the published
  model's, not the sizing's (the sized file gives the same forces), and neither MyoSuite, MuscleMimic nor KINESIS
  changes it (2026-10-27): changing it is changing MyoSuite's muscles, not a set-up here.
- **Set up as its makers do, and where not** (2026-10-27, sources and numbers on #65): MuscleMimic's own fixes are
  taken (1.0.6, below `MODEL`); its retargeting (GMR with a fitted SMPL-H shape; site welds) and KINESIS' (SMPL joint
  positions, SLSQP for the first pose) track joint-centre places first and turns second, on a source body fitted to
  the model; ours fits turns first with the pelvis' and feet's places. The model's hip joints stand 8.7 cm behind
  SOMA's at the bind when the pelvis rides the Hips (`RIDES`); placing them on SOMA's hip joints and reading the
  places off the model posed at the bind took the rig's walking clip from 8.3 to 7.4 degrees off but lifted the
  Kimodo walker's feet 2 to 3 cm off its ground in stance (residual 12 to 37 N median, 0 push on some frames), so it
  is not kept: the frame-0 `shift` would have to change with it. Their simulation settings (timestep, iterations,
  friction 1, joint damping and armature) are the model's for stepping; nothing is stepped here, and the damping and
  armature Newton builds match MuJoCo's own compile, as do every muscle's parameters and coupling.
- **Mass by #64's rule**: the cast's stated `weight` (kg), else `height` (m, else the body's own) squared times the
  reference BMI of `sex` (NCD-RisC 2016, the mean of both unstated), marked `estimated`, spread over the model's bodies
  as the model's masses times their scale cubed. Never tune a mass, a weight in the solve or a gate to pass: fix the
  method and measure again.
- **Rotations to angles**: each SOMA segment's turn becomes its body's (`RIDES`, `TARGETS`, a fixed turn from segment
  to body with the limb's bone swung onto SOMA's A-pose: `offsets`), fitted by damped least squares in the model's own
  leading coordinates, MuJoCo's joint couplings kept (`fitted`, `Couplings`); Newton's eval_ik and IKSolver drop the
  couplings, so they are not used. What MyoFullBody lacks (`LACKS`: a rigid neck and thorax, one lumbar joint spread
  over five levels, the shoulder rhythm, hinge knees and ankles) is recorded in each body's model record. The arms are
  calibrated as OpenSense does, on the rig's `standing` clip taken as the model's zero pose (arms hanging, palms to
  the thighs: MyoFullBody's own), since SOMA's A-pose bind is far from it (`CALIBRATED`; a rig with no standing clip
  falls back to the bind, named in `calibrated on`); the fit holds each joint lightly to the frame before
  (`FIT_STEADY`), or the hanging arm's plane of elevation (MoBL-ARMS' gimbal) swings frame to frame. The SOMA forearm
  rides the ulna, so its hand's twist is the forearm's pronation. The path is moved up once so its lowest point stands
  on the ground at the first frame (`shift`), then low-passed (zero-lag 4th-order Butterworth at 6 Hz, Winter 2009)
  before it is differentiated.
- **Its frame is the skin's**: the person's spot and turn, then the dressed body's Turned (`TURNED`, 180 degrees about
  up, prop_build.py's root node), so the ground it walks is the ground under the skin's feet (`own_frame`). MuJoCo's
  frame is Z up; `TO_OWN` turns everything back to the person's Y up.
- **It stands on the scene's own ground**: the stage the cast is measured on (`layer_base.built` with the scene record,
  `cast/measure.solids` on the terrain row's made ground), the solids within `REACH` of each clip's path, their drawn
  triangles themselves: the ground may push any collider surface point within the inside's `REACH` (3 cm) of the
  triangle under it, moving slower than `SLIDE_MOST` (1.2 m/s), along that triangle's normal within a friction 0.5
  cone (Karatsidis et al., arXiv:1801.01668). No heightfield and no MuJoCo collision: a MuJoCo heightfield met with a
  margin gave contacts 3 to 5 cm deep with sideways normals under a foot 4 mm over its ground (2026-10-27). A riser
  the toe meets is not a contact: it shows as residual.
- **One Newton environment**: `score/stages/physics/inside/newton_env.sh` (declared as `sim env`), built once at
  `$PROPS_HOME/envs/newton_env`; never a second env or a pip install of its own. Newton is given no meshes
  (`parse_meshes=False`: its mesh loading needs trimesh, which the env does not hold); the drawn bones come from
  MuJoCo's own compile of the file. MuJoCo's CPU backend, run on this machine (free).
- **Its readers** (contract version 2): the characters layer (`../cast/driven.py`) plays each person's skeleton from
  `measures/<name>.json`'s `poses`, which are the clip's own segment frames (the movement is the clip's, so the skin
  plays it), and references `layers/sim_bodies.usda`; its gate measures the skin's feet against the layer's
  `SimBody/<segment>` Xforms, which ride the body's bones at the bind's correspondence (`offsets`), so it reads how far
  the musculoskeletal body's feet are from the clip's. People-cloth reads `poses` and imports `segments_of`. The film's
  layer peel (`../demo_film/peel.py`) draws whatever geometry is under each SimBody and finds each `feet` key's prim by
  name: every SOMA segment Xform holds the bone it rides (a foot holds its calcaneus), other bones sit under `Bones`,
  muscles are one BasisCurves `Muscles` (one topology, `displayColor` by activation, every frame). The layer is text
  and about 10 MB a person (150 frames of 416 muscles' paths).
- Tests: `test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py` (a toy rig and seed, written runs;
  Newton and MuJoCo are not run there: the run's numbers are on #65).
