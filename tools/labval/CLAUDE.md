# tools/labval/

The sim body validated on OpenCap's LabValidation (#98): GEM-X Motion on one phone video, the sim body on the lab's
floor, scored against the lab's own IK, force plates and EMG. `__init__.py` is the interface (`prepared`, `scored`,
`pooled`), `__main__.py` its commands (`prepare`, `score`), `on_gemx.py` and `on_moge.py` the scripts that run
elsewhere: on the rented card, in GEM-X's own environment, turning `gem-infer motion-video`'s `motion.pt` into the
SOMA body npz, and MoGe-2's point maps of each video.

- **Never the owner's patented method** (arXiv:2607.17639, NL4001444; SCORE is public MIT): no swing-twist split, no
  calibration table of axes and offsets, no regression of angles against the reference. The angles are MyoFullBody's
  own coordinates after the sim body's fit (`_run`; the run saves them, `<name>/coordinates`), the pelvis and lumbar
  OpenSim's intrinsic Z, X, Y of the model's own body frames, the shoulders the same of each humerus on the torso
  (acromial_l's negated X and Y), the elbows MyoFullBody's own; pro_sup scores cMAE and r only, its zero another
  forearm in each model (`_run`'s docstring). Only that paper's scoring protocol is used (`_score`:
  the sub-frame shift of the reference on the centred residual of both sides' hip, knee and ankle flexion, RMSE, MAE,
  centred MAE and r, † under 15 degrees of range, the per-subject bootstrap of 20,000 draws).
- **Nothing from the companion repo** (the movalytics repo is under a noncommercial licence) and no Babon
  infrastructure named anywhere (no bucket, database or pool). LabValidation comes from SimTK, public; GEM-X from
  NVlabs/GEM-X upstream (code Apache-2.0, weights the NVIDIA Open Model License), never an older copy.
- **SOMA is the truth** (#70): `_soma.person` drops the joints the people route drops (body.py's UNSEEN, the test holds
  the two equal), turns each joint's frame onto the clips rig's template frame (a relabelling: the skin and movement
  are unchanged, the static calibration table reads the template's frames) and moves only the travelling joint up or
  down: the clip as a whole onto the floor (GEM-X's raw world has none), then the stage's own `stood`. The mesh must be
  the template's topology (LOD low): the landmark set is its faces.
- **The floor is seen, not assumed** (#98, 2026-11-06): GEM-X's world up is its network's per-frame gravity estimate,
  and its Motion takes the image diagonal as the focal length (27.5 degrees across a 720 x 1280 video; the lab's
  calibration 43.0). MoGe-2 (microsoft/MoGe at 07444410, MIT; weights Ruicheng/moge-2-vitl-normal, MIT;
  `moge_cluster.py` on the cluster, `on_moge.py` in the pod, `moge_env.sh` its pins) gives each video's metric point
  map at its own field of view (median 44.1 degrees); `_floor.seen` fits the floor in the camera (RANSAC on the
  floor-like points beside GEM-X's person box) and `_floor.levelled` turns the whole clip, one rigid turn, onto it.
  Measured on all 572 right videos: MoGe-2's floor 0.49 degrees from the calibration's up (median; p95 1.6), GEM-X's
  up 3.44 (p95 8.5). `prepare --gemx --moge` takes GEM-X's own Contact/IK result (contact_ik.npz: its static feet
  held, where the raw prediction's still feet drifted 86 to 165 mm) and levels it; `--gemx` given GEM-X run at
  MoGe-2's field of view (tools/cloud/gemx `--fov-from`) put the person 2.7 to 3.5 m from Cam1 where the diagonal focal
  put them 4.3 to 5.6 (MoGe-2's metric depth 2.3 to 3.1, the lab's back-wall board 3.4 to 3.7): matched MAE 6.08 to
  5.35 on 55 envelope trials (floor and calibration 5.73). Laying carried feet flat was tried and not kept (2026-11-07):
  turning the foot alone broke the ankle's shape (left cMAE 3.2 to 4.9), and by the whole leg both feet pushed (squats'
  carries 0.14 to 0.79) but the angles lost (matched MAE 5.25 to 5.89, the left knee 6.0 to 7.9). The lab's calibration
  is the check only, never an input.
- **Forces as OpenCap scored them** (`_grf`; Uhlrich et al. 2023, Methods): the plates and the run's pushes
  low-passed alike at the activity's cutoff (walking 6 Hz, squats and sit-to-stand 4, drop jump 30, held under 0.8 of
  the 30 Hz run's Nyquist: 12), the MAE in % body weight on each of the three axes and as % of the measured range,
  over the frames both give, per foot and both feet summed; each whole stance's impulse and the centre of pressure's
  travel inside it (centred: the run's world is not registered to the lab's) are beyond OpenCap. `grf-tables` writes
  them per activity, per camera and per both.
- **The run is the stage's**: one job.json a trial, the stage's own limits and caps (`_job.job_of`), the subject's
  measured mass, a flat floor at y = 0; the measure folder's `scripts/go.sh` runs through tools/cloud/sim_measure on
  a rented card, names every path from `${REPO}` and skips a trial whose out.json is there. Never on this PC.
- **The reference's files are read as they are** (`_files`): a column, unit or file not as expected raises with what
  it found; EMG is optional per trial. The file layout under `subject<N>/` (`WHERE`) and the EMG and marker names
  (`_score.EMG_MUSCLES`, `MARKERS`) are read from the dataset's documentation, not yet checked against the download:
  the first real run says, and a miss raises rather than scoring the wrong channel.
- **The cluster path** (`cluster.py`, SCORE_CLOUD=k8s): a measure folder's trials in jobs of `--per-job` each, in the
  newton image, the model sent once for the run, every trial run on its own (a failure in its run.log, the next trial
  still run) and its folder brought back whole.
- **The moments' reference is OpenSim's, remade** (`opensim_reference.py`, `on_opensim.py` in the venv
  `opensim_env.sh` builds: pyopensim 4.5.2, never SCORE's environment): the lab's scaled LaiArnoldModified2017 model,
  IK, plates and ID setup read from the store, OpenSim's ID tool on the lab's settings (it reproduces the dataset's own
  ID .sto), and the knee adduction moment both OpenCap's way (computeKAM's joint reaction, muscles removed, the ID's
  forces on coordinate actuators) and as the plates' external moment about the model's knee. `_moments` scores the
  run's generalized forces against it by OpenCap's protocol (%BW*ht MAE of its 15 degrees of freedom, with the elbows
  and forearms; early-stance KAM, peak knee extension, sit-to-stand's rising means); `moments` is its command.
- **The final validation is one command** (`validate.py`): `cluster.py` over the measure folder (a named run
  resumes), then every trial that came back scored and every table written into one folder, per group (all, each
  activity, each camera, each activity and camera): angles with the arms, forces, GRF, EMG, moments (given the
  reference ID) and the per-step timing per card from out.json's "seconds".
- Test: `test_a_labvalidation_trial_scores_the_errors_built_into_it.py` (synthetic files and a synthetic run with known
  errors built in; no number from it is a result).
- **Each foot's seen stance and GEM-X's drift** (#98, 2026-11-07): `_soma.seen_stance` (GEM-X's static contact on a
  foot's ankle or toe, or the stage's own stance) goes into the targets as `stance`, from which the sim body's ground
  pushes a standing foot (`inside/contact` `Skin.credited`): GEM-X held the deepest squat's right foot static 18 to 28
  mm up, so only the left foot was pushed. `_soma.undrifted` holds the still feet's lowest sole at one height between
  flights (GEM-X's world drifted 30 to 80 mm on 12 of 64 trials but the drop jumps), the drop jumps' box and floor
  each kept. Both move only the travelling joint: the angles are unchanged (matched MAE 5.81 to 5.81 on 12 trials).
- **EMG** is the store's processed envelopes (`emg/<trial>.sto`, channels `<muscle>_<side>_activation`, 100 Hz).
- **The chair and the box** (#98, 2026-11-07, `_supports`): a sit-to-stand's seat is drawn ground at 0.40 m (Uhlrich
  et al. 2023: "rising from a 40 cm chair") under the Hips' seated skin, a drop jump's box top where the clip's first
  feet stand (no box height in the paper's text, SimTK's pages or sessionMetadata.yaml; the lab's markers, the
  check only, put it 0.33 to 0.36 m up, the clips 0.07 to 0.30), each footprint clear of the feet on the floor; they go
  into the targets' ground with the floor. A foot's push whose centre of pressure stands off the floor (`_run.OFF_FLOOR`)
  is no plate's: the box stands off the plates, which read 0 before the drop.
