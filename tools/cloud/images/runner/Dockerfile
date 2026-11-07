# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-runner: the conductor's own Python, so a free stage of score makes in a pod as it makes on the conductor. The
# lock's hashed export (requirements.txt and lock.sha256 come from `build.py runner --export`; the file wheels the lock
# names sit at their repository paths under this folder) in /opt/score/env, the same uv.lock the boxes sync into
# $PROPS_HOME/env, on the base's Python 3.12 (a code version's first part is "python 3.12"), beside the runtime's own
# /opt/score/venv; ffmpeg for complete's checks; a systemd-run shim, since a pod has no systemd (the pod's memory
# limit stands for the scope's MemoryMax). /opt/score/uv.lock.sha256 names the lock it was built from. No score code
# and no weights: the run's commit comes as each job's code.
ARG BASE
FROM ${BASE}

ARG PYTHON=3.12.13
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/score/lock/requirements.txt
COPY vendor/ /opt/score/lock/vendor/
RUN cd /opt/score/lock \
 && uv venv --python ${PYTHON} /opt/score/env \
 && uv pip sync --python /opt/score/env --require-hashes requirements.txt \
 && /opt/score/env/bin/python -c "import numpy, scipy; print('runner env ready')"
COPY lock.sha256 /opt/score/uv.lock.sha256
COPY --chmod=755 systemd-run /usr/local/bin/systemd-run
