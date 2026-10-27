# score/stages/sim_body/inside/

The sim body run that goes in Newton's own Python (`score/stages/physics/inside/newton_env.sh`), started by the stage
(`../__init__.py` `ran`) on this machine: `sim_body.py <job.json> <out.json>`. Never import it from the score venv:
Newton pins its own MuJoCo and Warp. Its rules (CPU backend, Euler, damping on the joints, contacts for the ground
push) are the parent overlay's.
