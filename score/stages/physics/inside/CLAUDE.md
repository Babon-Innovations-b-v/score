# score/stages/physics/inside/

The trial that runs in its own Python, sent by the physics trial (`../__init__.py`) to a rented card
(`tools/cloud/blender_cloud.py` runs a job naming an `env` in the Python that script builds), or run on this PC:
`newton_env.sh <folder>` builds that Python once (the settle's drop, `../../settling/inside/settle_drop.py`, runs in the same one and borrows this trial script's USD helpers: a pin or helper change moves both) (Newton, MuJoCo, Warp, usd-core, python-fcl, every version pinned;
newton 1.7.0 runs the solver in deterministic mode, so a trial repeats bit for bit), `physics_trial.py` is the trial. Never import it from the score venv: one
USD library a process, and Newton pins its own MuJoCo and Warp. The rules are the parent overlay's.
