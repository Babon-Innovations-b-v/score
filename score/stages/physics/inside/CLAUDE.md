# score/stages/physics/inside/

The trial that runs in its own Python, sent by the physics trial (`../__init__.py`) to a rented card
(`tools/cloud/blender_cloud.py` runs a job naming an `env` in the Python that script builds), or run on this PC:
`newton_env.sh <folder>` builds that Python once (the settle's drop, `../../settling/inside/settle_drop.py`, runs in the same one and borrows this trial script's USD helpers: a pin or helper change moves both) (Newton, MuJoCo, Warp, usd-core, python-fcl, every version pinned;
not in Warp's deterministic mode: over 32 dofs, about 5 free bodies, MuJoCo Warp's sparse Jacobian sizes its sorted
records past 2^31, and its sparse inertia solve is wrong over 60 dofs in a tree, #60; the contacts stay sorted, so a
trial repeats closely but not bit for bit), `physics_trial.py` is the trial. Never import it from the score venv: one
USD library a process, and Newton pins its own MuJoCo and Warp. The rules are the parent overlay's.
