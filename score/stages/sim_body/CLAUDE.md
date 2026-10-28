# score/stages/sim_body/

The sim body stage (experimental, #65; PRD #56; CONTEXT.md "sim body"): row `sim-body@<place>` for a place whose
design shows people, every character of its accepted cast as a musculoskeletal body, MyoFullBody, doing its clip on the
scene's own ground. `__init__.py`'s docstring has the make and the gates; `inside/sim_body.py` is the run, in Newton's
own Python, its steps the modules beside it (`inside/CLAUDE.md`).

- **The movement is the clip's, the physics the body's** (owner, 2026-10-27: "we have kimodo for the actual movement;
  and myobody plus mujoco and newton for the physics"). The body, root included, follows the clip, moved only by RRA's
  capped adjustment (below); nothing is stepped. Per frame: inverse dynamics on the MuJoCo model Newton builds, the ground's contacts, the joints' range
  stops and the muscles share the needed forces (one bounded least squares, least squared activation, the pelvis'
  six balance rows `BALANCE` times a joint's), and what they cannot give is the pelvis' residual and the joints'
  reserves: measured, recorded, gated (`residual`, Hicks et al. 2015), **never applied**.
  Never bring back a helper or any force that holds the body up or on its path: a trip or a float must show as a
  residual that fails. Limits: force 2% of the weight (owner, 2026-10-28, from 5%; Werling et al. 2023's
  AddBiomechanics results as the benchmark only), moment 1% of it times the centre's height (Hicks 2015).
- **Residual reduction, OpenSim's RRA** (owner, 2026-10-28; Delp et al. 2007, opensim-core RRATool, Apache-2.0; never
  AddBiomechanics: GPL with a data-sharing clause, neither used nor copied): `inside/rra` `reduced` adjusts
  the fitted path's pelvis and trunk (the root's six dofs and the lumbar leaders, `TRUNK`) and the body's masses and
  torso centre of mass (RRATool's own formulas) so the ground explains the movement, `RRA_ROUNDS` times, the
  owner's per-frame cap inside the solve (owner, 2026-10-28: every segment's turn within `FOLLOWED` degrees and the
  pelvis within `MOVE_MOST` of the fitted path on every frame, all rounds together; `cap_rows` linearises each
  segment's turn through the legs' `footed`, `within_balls` solves the least squares over those balls by ADMM), the
  move low-passed by construction (`filter_matrix`: a filtered move, so the filter cannot break the cap), the lumbar's
  needed moments beyond the fitted path's counted as residual moment (`demands`: RRA weighs the joints' actuators
  beside the residuals; without it the solve swung the trunk to cancel the pelvis' residual and left up to 340 N m on
  the lumbar's reserves, 2026-10-28), taken only when the measured residual, lumbar and move cost falls (halved up to `RRA_HALVINGS` times, else the rounds end), the feet kept where they stood by the legs (`footed`: a
  pelvis moved with its feet lifted them off the ground, 600 N of residual, 2026-10-28), and the result kept within the clip's
  `follows` limit (`within_follows`: the whole move, else a quarter less, down to none), then checked on every frame against the
  cap as measured (`within_frames`: a frame the linearisation left over has its share of the move lowered, the shares
  eroded and low-passed; the least share is recorded; scaling the whole move down after the solve, as before
  2026-10-28, gave back about half of what it reduced). Nothing is applied to the body. How far it moved is each body's
  `adjusted` record (pelvis cm, each segment's degrees, the largest turn on any frame, mass %, torso centre of mass cm,
  the share kept, the least frame share, follows before and after); `follows` fails a frame over the per-frame cap.
  The toes' ±30 degree stop is MyoSuite's own (myo_sim `myolegs_chain.xml` mtp_angle range ±0.523599, as Rajagopal
  2016's): never widened here. A body still over the limits after it fails `residual`: a
  dropped sample, never a forced pass.
- **The body is MyoFullBody, never a box body or a template of our own**: MuscleMimic's wheel (`MODEL`, pinned URL and
  sha256), fetched once to `$PROPS_HOME/models/<sha>` by `fetched`, never committed. Kept under MyoHub's Apache-2.0
  (owner, 2026-10-27, #65). Attribution, also in every `sim_bodies.json` (`ATTRIBUTION`): MyoSuite and myo_sim
  (MyoHub, Apache-2.0), with the arm and hand derived from MoBL-ARMS: Holzbaur, Murray and Delp 2005
  (doi:10.1007/s10439-005-3320-7) and Saul et al. 2015 (doi:10.1080/10255842.2014.916698).
  `inside/myo` writes each person's file: #60's import fixes (names without '-', full muscle parameters, explicit
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
  taken (1.0.6, below `MODEL`). Its retargeting (GMR, site welds) and KINESIS' place joint centres on a source body
  fitted to the model; ours did for the legs until 2026-10-28, when the owner moved the fit to OpenSense's ("the rot
  solver is by far the cleanest and closest to exact translation"; below). Their simulation settings (timestep,
  iterations, friction 1, joint damping and armature) are the model's for stepping; nothing is stepped here, and the
  damping and armature Newton builds match MuJoCo's own compile, as do every muscle's parameters and coupling. Their
  foot colliders are the model's (three capsules and an ellipsoid on the calcaneus, two capsules on the toes, margin
  1 mm, MuJoCo's default solref and solimp: a loaded foot rests within about 1 mm of a MuJoCo floor).
- **Mass by #64's rule**: the cast's stated `weight` (kg), else `height` (m, else the body's own) squared times the
  reference BMI of `sex` (NCD-RisC 2016, the mean of both unstated), marked `estimated`, spread over the model's bodies
  as the model's masses times their scale cubed; RRA's mass step (above) is the one change after it, recorded. Never
  tune a mass, a weight in the solve or a gate by hand to pass: fix the method and measure again.
- **Rotations to angles, as OpenSense does** (owner, 2026-10-28; Al Borno et al. 2022, J NeuroEng Rehabil 19:22,
  doi:10.1186/s12984-022-01001-x; opensim-core's IMUPlacer and IMUInverseKinematicsTool, Apache-2.0): each SOMA
  segment's world turn is a virtual orientation sensor on the body it rides (`RIDES`, `TARGETS`, weight 1 each); each
  sensor's offset to its body is calibrated on the rig's `standing` clip as the model's default pose (its couplings
  applied: MyoSuite's `stand`), heading corrected on the hip joints' line (`offsets`; a rig with no standing clip
  falls back to the bind, named in `calibrated on`), then fitted again over the whole clip (`refitted`,
  `OFFSET_ROUNDS`: the owner's change, one least squares over every frame jointly with the fit); per frame the
  model's joint angles minimise the sensors' squared error angles (`fitted`, Simbody's OrientationSensors goal) in its
  own leading coordinates, MuJoCo's couplings kept (`Couplings`; Newton's eval_ik and IKSolver drop them, so they are
  not used). The pelvis stands where SOMA's Hips carry it, its place in the Hips' frame calibrated with the model's hip
  joints' middle on SOMA's; nothing else is placed by position. **Never use the owner's own method** (arXiv:2607.17639,
  under Babon's patent application NL4001444; SCORE is public MIT): no swing-twist split into calibrated axes, no
  per-joint calibration table of axes, weights and offsets, no regression of joint angles against a reference.
  What MyoFullBody lacks (`LACKS`: a rigid neck and thorax, one lumbar joint spread over five levels, the shoulder
  rhythm, hinge knees and ankles) is recorded in each body's model record. The fit holds each joint lightly to the
  frame before (`FIT_STEADY`), or the hanging arm's plane of elevation (MoBL-ARMS' gimbal) swings frame to frame
  (at 0.05 up to 10,000 deg/s2, about 130 N m of the residual). The
  SOMA forearm rides the ulna, so its hand's twist is the forearm's pronation. The path is low-passed (zero-lag
  4th-order Butterworth at 6 Hz, Winter 2009) before it is differentiated.
- **Its feet stand on the ground, not in it** (owner, 2026-10-28: "ground contact is real"): a foot segment stands
  in a frame when its SOMA joint is within `LOW` of its standing height over its ground and slower than `STILL`
  (`stances`; Kovar, Schreiner and Gleicher 2002's footskate cleanup); the fit holds a standing foot body's lowest
  collider point on the ground, keeps it from sliding while it stood the frame before too (`unslipped`: it rolls, the
  point in contact still; a height hold alone let the rig walk's toe slide 6 cm in a frame at heel-off, 1.8 m/s, so
  the ground could only resist the slip: 416 N of residual, 2026-10-28) and keeps every foot point out of it, by the legs' joints alone (`on_ground`,
  `FIT_GROUND`; a point within `GAP` over it stays in the fit as the bound's active set, or the next step puts it
  back in), in the fit and again after the low-pass, which moves a held foot again: landed and low-passed
  `LAND_ROUNDS` times, then landed last (`landed`, each body held to its low-passed turn); the pelvis keeps its
  place. Then the path is moved once so its lowest point stands on the ground at its median frame (`grounded`, about
  0 now).
- **Its frame is the skin's**: the person's spot and turn, then the dressed body's Turned (`TURNED`, 180 degrees about
  up, prop_build.py's root node), so the ground it walks is the ground under the skin's feet (`own_frame`). MuJoCo's
  frame is Z up; `TO_OWN` turns everything back to the person's Y up.
- **It stands on the scene's own ground**: the stage the cast is measured on (`layer_base.built` with the scene
  record, `cast/measure.solids` on the terrain row's made ground), the solids within `REACH` of each clip's path,
  their drawn triangles themselves: the ground pushes only a collider surface point touching it, within the inside's
  `GAP` of the triangle under it or into it (MuJoCo's own rule: contact within the geoms' margin), one moving slower
  than `SLIDE_MOST` (1.2 m/s) inside a friction 0.5 pyramid (Karatsidis et al., arXiv:1801.01668), a faster one
  sliding (Coulomb: the normal and 0.5 of it against its slip), along that triangle's normal; no force anywhere else.
  No heightfield and no MuJoCo collision: a MuJoCo heightfield met with a margin gave contacts 3 to 5 cm deep with
  sideways normals under a foot 4 mm over its ground (2026-10-27). A riser the toe meets is not a contact: it shows as
  residual. `on floor` fails a body over `SUNK_MOST` (3 mm) into its ground, `lands` a carrying foot over `LANDED` (5
  mm) off it.
- **One Newton environment**: `score/stages/physics/inside/newton_env.sh` (declared as `sim env`), built once at
  `$PROPS_HOME/envs/newton_env`; never a second env or a pip install of its own. Newton is given no meshes
  (`parse_meshes=False`: its mesh loading needs trimesh, which the env does not hold); the drawn bones come from
  MuJoCo's own compile of the file. MuJoCo's CPU backend, run on this machine (free).
- **Its readers** (contract version 2): the characters layer (`../cast/driven.py`) plays each person's skeleton from
  `measures/<name>.json`'s `poses`, which are the clip's own segment frames moved as RRA moved the body each rides
  (the picture and the forces show one motion), and references `layers/sim_bodies.usda`; its gate measures the skin's feet against the layer's
  `SimBody/<segment>` Xforms, which ride the body's bones at the bind's correspondence (`offsets`), so it reads how far
  the musculoskeletal body's feet are from the clip's. People-cloth reads `poses` and imports `segments_of`. The film's
  layer peel (`../demo_film/peel.py`) draws whatever geometry is under each SimBody and finds each `feet` key's prim by
  name: every SOMA segment Xform holds the bone it rides (a foot holds its calcaneus), other bones sit under `Bones`,
  muscles are one BasisCurves `Muscles` (one topology, `displayColor` by activation, every frame). The layer is text
  and about 10 MB a person (150 frames of 416 muscles' paths).
- Tests: `test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py` (a toy rig and seed, written runs;
  Newton and MuJoCo are not run there: the run's numbers are on #65).
