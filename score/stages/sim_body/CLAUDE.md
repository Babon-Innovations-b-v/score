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
  torso centre of mass (RRATool's own formulas; the mass at most `MASS_MOST`, 2%, from the mass it was made
  with over every round together, never compounding, and RRA's own recommended change recorded beside it as `mass %
  recommended`, OpenSim's report: unbounded, a floating body lost 98 to 99.9% of its mass, 2026-10-28) so the ground explains the movement, `RRA_ROUNDS` times, the
  owner's per-frame cap inside the solve (owner, 2026-10-28: every segment's turn within `FOLLOWED` degrees and the
  pelvis within `MOVE_MOST` of the fitted path on every frame, all rounds together; `cap_rows` linearises each
  segment's turn through the legs' `Footing`, `within_balls` solves the least squares over those balls by ADMM), the
  move low-passed by construction (`filter_matrix`: a filtered move, so the filter cannot break the cap), the lumbar's
  needed moments beyond the fitted path's counted as residual moment (`demands`: RRA weighs the joints' actuators
  beside the residuals; without it the solve swung the trunk to cancel the pelvis' residual and left up to 340 N m on
  the lumbar's reserves, 2026-10-28), taken only when the measured residual, lumbar and move cost falls (halved up to `RRA_HALVINGS` times, else the rounds end), the feet kept where they stood by the legs (`Footing`, mink as the fit, its largest
  miss recorded as `feet held mm, deg`: a pelvis moved with its feet lifted them off the ground, 600 N of residual, 2026-10-28), and the result kept within the clip's
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
  an optional read, `person_rig`), recorded as `size`. MyoFullBody is sized to it by bone group (#70, `inside/sizing`;
  the stage hands the run the person's mesh and skin weights in its targets): every group, trunk and pelvis included,
  so its stretch is SOMA's joint distance (before 2026-10-28 the limbs only, the rest by standing height: 15 of 22
  groups within 1 cm, now all within 0.1 mm); its widths are not sized (the solver's joint centres); each muscle's
  length range with its path (OpenSim's scaling), its peak force kept.
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
  reference BMI of `sex` (NCD-RisC 2016, the mean of both unstated), marked `estimated`, spread over the bone groups by
  SOMA's segment volumes at Dempster's densities (`inside/volumes`, the owner's #70: motion cannot tell weight), each
  group's centre of mass and inertia's trace SOMA's; the kneecaps, the abdominal wrapper and the 1 g frames keep the
  model's share; what SOMA does not give (muscle strength, joint ranges, density, bone shape) is marked assumed with a
  plausible range in the model record (`assumed`). RRA's mass step (above) is the one change after it, recorded. Never
  tune a mass, a weight in the solve or a gate by hand to pass: fix the method and measure again.
- **One solver fits MyoFullBody to SOMA** (#70, owner 2026-10-28; `inside/fit`): the person's constants (each bone
  group's size, the limbs' joint centres, each virtual marker's place on its bone) and every frame's joint angles,
  against the bone groups' turns (the main term: each SOMA segment's world turn on its group, through the static
  calibration table, as OpenSense tracks orientations: Al Borno et al. 2022, doi:10.1186/s12984-022-01001-x), the
  SOMA mesh's bony landmarks skinned on the clip (`inside/landmarks`) and SOMA's joints on MyoFullBody's centres as
  markers, weighed as OpenSim's IK weighs its goals, within the leading joints' ranges, MuJoCo's couplings held
  exactly, each group's stretch held to SOMA's length: mink per frame and scipy's bounded `least_squares` over the
  constants with the angles of frames spread over the clip. **Never use the owner's own
  method** (arXiv:2607.17639, under Babon's patent application NL4001444; SCORE is public MIT): no swing-twist split
  into calibrated axes, no per-joint calibration table of axes, weights and offsets, no regression of joint angles
  against a reference. What MyoFullBody lacks (`LACKS`: a rigid neck and thorax, one lumbar joint spread over five
  levels, the shoulder rhythm, hinge knees and ankles) is recorded in each body's model record; how closely it
  follows SOMA (each joint's mm, each group's degrees, at a range limit or not, before and after RRA) is its `fit`.
  The SOMA forearm rides the ulna, so its hand's twist is the forearm's pronation. The path is low-passed (zero-lag
  4th-order Butterworth at 6 Hz, Winter 2009) before it is differentiated.
- **Its feet are where SOMA's are** (#70: SOMA is the truth, never moved, scaled or grounded): MyoFullBody's root
  follows the markers on SOMA's skin and nothing moves it onto the ground; the ground pushes whatever collider point
  the fit puts within `GAP` of it. Before 2026-10-28 the fit held standing feet on the ground (`stances`,
  `on_ground`, `unslipped`, `landed`) and moved the path once onto it (`grounded`); those went with the old fit.
  Measured 2026-10-28: the two test walkers' SOMA skin stood 26 to 57 mm over their ground (its lowest point, every
  10th frame), so the sim body following it stood 10 to 13 mm over it on the median, its feet seldom pushed, and
  RRA's mass step then took the body's mass by 98 to 99.9%. The float was the clip's, not the sim body's (2026-10-29,
  #70): people-clips-made's clips are posed on SOMA's zero-identity body (prop_skeleton.py, body.posed_by_the_model:
  1.685 m, its leg 56 mm short) beside the template bind and surface (1.757 m) the file also holds, and `person_rig`
  played them raw with no build. It now plays every clip as the people build does (prop_build.py fk and floor_lift):
  the build's offsets (with none, the rig's own bind's), the standing clip's first frame lifted to put the feet where
  the bind does. Measured on the two walkers: ankles 118 to 121 mm at their lowest before, 70 to 72 mm after
  (Kimodo's own skeleton: 68 to 70); the skin's lowest point -20 to 9 mm. The rig file's own mix (its clips' offsets
  are not its bind's) is prop_skeleton.py's to fix at its next paid re-make (the owner's call); never read its clips
  raw: play them through `person_rig`.
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
  `$PROPS_HOME/envs/newton_env`; never a second env or a pip install of its own. mink, qpsolvers and daqp are pinned
  there for the fit (#70); the script is declared by physics-trial, settle and effects too, so a pin moves their keys.
  Newton is given no meshes (`parse_meshes=False`: its mesh loading needs trimesh, which the env does not hold); the
  drawn bones come from MuJoCo's own compile of the file. MuJoCo's CPU backend, run on this machine (free).
- **Its readers** (contract version 2): the characters layer (`../cast/driven.py`) plays each person's skeleton from
  `measures/<name>.json`'s `poses`, which are the clip's own segment frames, written by the stage itself, never
  moved, scaled or grounded to the sim body (owner, 2026-10-28: SOMA is the truth; the stage's test checks them bit
  for bit), and references `layers/sim_bodies.usda`; its gate measures the skin's feet against the layer's
  `SimBody/<segment>` Xforms, which ride the body's bones (`fit.riding`: the calibration table's turn, at the
  group's start joint), so it reads how far the musculoskeletal body's feet are from the clip's. People-cloth reads
  `poses` and imports `segments_of`. The film's
  layer peel (`../demo_film/peel.py`) draws whatever geometry is under each SimBody and finds each `feet` key's prim by
  name: every SOMA segment Xform holds the bone it rides (a foot holds its calcaneus), other bones sit under `Bones`,
  muscles are one BasisCurves `Muscles` (one topology, `displayColor` by activation, every frame). The layer is text
  and about 10 MB a person (150 frames of 416 muscles' paths).
- Tests: `test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py` (a toy rig and seed, written runs;
  Newton and MuJoCo are not run there: the run's numbers are on #65).
