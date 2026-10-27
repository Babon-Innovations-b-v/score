# score/stages/people_cloth/inside/

The people cloth run that goes in Newton's own Python (`score/stages/physics/inside/newton_env.sh`), started by the
stage (`../__init__.py` `ran`) on this machine's card: `cloth.py <job.json> <out.npz>`. Never import it from the score
venv: Newton pins its own Warp. Its rules (a world a person, riding points massless and set at each substep's end,
no cloth damping of its own, run-to-run deterministic) are the parent overlay's.
