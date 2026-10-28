# score/stages/sim_body/inside/

The sim body run that goes in Newton's own Python (`score/stages/physics/inside/newton_env.sh`), started by the stage
(`../__init__.py` `ran`) on this machine: `sim_body.py <job.json> <out.json>` (it writes `<out>.npz` beside: bones,
bone meshes, muscle paths). Never import any of it from the score venv: Newton pins its own MuJoCo and Warp. Its rules
(the clip's movement followed exactly, residuals measured and never applied, MuJoCo's CPU backend, the ground its
drawn triangles) are the parent overlay's. A person takes 6 to 7.5 minutes on this PC's CPU for 136 to 150 frames
(the fit four times over and its landings, RRA, and one bounded least squares a frame; measured 2026-10-28 on the
two test walkers, two side by side); people run one after another in one process.

- **`sim_body.py` is the run only** (#70: "1400 line script, yuck"): it orders the steps, each a module beside it
  with its interface (`__init__.py`), its one test file and its overlay. Python puts the script's folder first on
  `sys.path`, so they import by bare name, leaves first: `bone_groups`, `ground`, `solvers` (pure: their tests run in
  the score venv), then `model`, `sizing`, `myo`, `contact`, `fit`, `muscles`, `rra`, `records` (MuJoCo-side: their
  tests run in Newton's own Python by subprocess, `skipped` where no env is built, as in `make tests`' sandbox home).
  A new module goes in its own folder here, imported the same way; never a name the env's site-packages already has.
- **The whole folder is the stage's input** (`sim inside` in `files()`): any file here, a test or an overlay too,
  re-makes `sim-body`. A file the run reads from elsewhere must be declared beside it.
- **A move is proved on the two test walkers** (the Kimodo walker and the rig's walking clip on a flat floor): run.json
  bytes and every array of run.npz equal before and after (#70's move, 2026-10-28). The person's file can differ by
  one mesh's `content_type` attribute between runs of the same code (MjSpec.to_xml; seen once, the compiled model
  and every output equal), so compare the outputs, not the file.
