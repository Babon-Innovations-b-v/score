# score/stages/sim_body/inside/

The sim body run that goes in Newton's own Python (`score/stages/physics/inside/newton_env.sh`), started by the stage
(`../__init__.py` `ran`) on this machine: `sim_body.py <job.json> <out.json>` (it writes `<out>.npz` beside: bones,
bone meshes, muscle paths), importing `myo.py` (MyoFullBody's sizing and #60's import fixes) from its own folder. Never
import either from the score venv: Newton pins its own MuJoCo and Warp. Its rules (the clip's movement followed
exactly, residuals measured and never applied, MuJoCo's CPU backend, the ground its drawn triangles) are the
parent overlay's. A person takes about 40 to 60 s on this PC's CPU for 150 frames (the fit, and one bounded
least squares a frame); people run one after another in one process.
