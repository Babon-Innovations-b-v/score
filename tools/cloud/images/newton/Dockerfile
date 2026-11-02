# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-newton: the Python of the physics trial, the sim body stage and sim body's level 1 (Newton with its MuJoCo
# solver, Warp, MuJoCo, mink, usd-core), as score/stages/physics/inside/newton_env.sh builds it on a rented machine and
# on this PC: its pins, every dependency resolved and hashed (requirements.txt), in /opt/newton. amd64 only: every card
# class we rent is on x86 machines. No weights: MyoFullBody comes with its job, at the path its job.json names
# (score/stages/sim_body fetched). `newton-run` (run.sh) runs a script in that Python.
ARG BASE
FROM ${BASE}

ARG PYTHON=3.12.13
COPY requirements.txt /opt/newton-requirements.txt
RUN uv venv --python ${PYTHON} /opt/newton \
 && uv pip sync --python /opt/newton --require-hashes /opt/newton-requirements.txt \
 && /opt/newton/bin/python -c "import fcl, newton, mujoco, pxr, mink, warp; print('newton', newton.__version__, 'mujoco', mujoco.__version__)"
COPY --chmod=755 run.sh /usr/local/bin/newton-run
