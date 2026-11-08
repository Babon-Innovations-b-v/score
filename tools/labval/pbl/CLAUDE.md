# tools/labval/pbl/

The Portable Biomechanics Laboratory (PBL; IntelligentSensingAndRehabilitation/MonocularBiomechanics, Peiffer, Cotton
et al., arXiv:2507.08268, MOTOR's inspiration) run on OpenCap LabValidation's 720 single-camera inputs and scored by
tools/labval's own scorer: MOTOR's paper's baseline beside OpenCap (#98). `pbl_env.sh` builds PBL's environment on a
card node, `on_pbl.py` runs in it, `cluster.py` puts every video on the cluster at once, `score.py` maps and scores.

- **Upstream only, pinned, never copied in.** PBL's code is AGPL-3.0: it is fetched at its commit by sha256 and
  installed from its own uv.lock (`uv sync --frozen --extra cuda`) on the card, never vendored or edited; this folder
  holds only SCORE's own files (MIT). Running it for a paper's measurements is use, not conveying. The one change to
  its lock's packages is opencv-python swapped for opencv-python-headless at the same version (the base image has no
  libGL; nothing is drawn). MeTRAbs (its keypoints, `load_metrabs`'s model by sha256) is MIT code with models for
  non-commercial use only (their training sets): a research baseline, nothing sold. LocoMuJoCo's humanoid
  (humanoid_torque.xml, PBL's model) is MIT.
- **PBL as released.** main.py's pipeline and settings (MeTRAbs bml_movi_87 at its defaults, `fit_model` at
  lr 1e-3 and 10,000 steps, the static-camera fit whose world is the camera), every frame of the 60 fps video. Two
  choices the demo leaves open (on_pbl.py's docstring): the largest detection a frame, confidence 0 where none.
- **The chain's camera, never the lab's calibration.** Each video is given GEM-X's K at MoGe-2's field of view, the
  chain's own camera (tools/cloud/gemx's `--fov-from`), and the pelvis is levelled on the floor MoGe-2 sees
  (`_floor.seen`, the chain's floor of that video); "camera up" (the camera's -y) is scored beside it.
- **The mapping is by name** (`score.MAPPED`; its docstring holds every coordinate and why): PBL's joints are
  OpenSim's (Rajagopal et al. 2016 through LocoMuJoCo), the lab's LaiUhlrich2022 builds on the same model. The knee
  is negated (gait2392's sign); pro_sup scores cMAE and r only; the knee's beta, PBL's wrists and neck and the pelvis
  translations are not mapped (`score.UNMAPPED`).
- **Scored as the chain is**: `labval.angle_scores`, `_score.shift` on the legs' flexions, `labval.pooled_angles`,
  the matched envelope Cam1 with no drop jumps; the chain's own report.json beside it, on the trials both have.
- Test: `test_pbl_angles_come_back_as_the_labs_coordinates.py` (synthetic; no number from it is a result).
