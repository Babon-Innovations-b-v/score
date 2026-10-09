# syntax=docker/dockerfile:1.7
# platforms: linux/amd64,linux/arm64
# score-base: the parent of every job image. NVIDIA's CUDA base image (the CUDA runtime library only, Ubuntu 24.04,
# amd64 and arm64), Python 3.12 through uv, and the job runtime (tools/cloud/runtime/) as `score-job`. The base
# flavour rather than NVIDIA's runtime one: PyTorch wheels carry their own CUDA libraries and Cycles uses the driver
# alone, so the larger image would only slow every pull. No weights (tools/cloud/CLAUDE.md).
FROM ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a AS uv

FROM nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:133c78a0575303be34164d0b90137a042172bdf60696af01a3c424ab402d86e2
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 UV_PYTHON_INSTALL_DIR=/opt/score/python \
    UV_NO_CACHE=1 SCORE_WORK=/work SCORE_CACHE=/cache
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl xz-utils zstd \
 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
COPY requirements.txt /opt/score/requirements.txt
RUN uv venv --python 3.12.13 /opt/score/venv \
 && uv pip install --python /opt/score/venv --require-hashes -r /opt/score/requirements.txt
COPY runtime/ /opt/score/runtime/
RUN printf '#!/bin/sh\nexec /opt/score/venv/bin/python /opt/score/runtime/job.py "$@"\n' > /usr/local/bin/score-job \
 && chmod 755 /usr/local/bin/score-job \
 && mkdir -p /work /cache
WORKDIR /work
ENTRYPOINT ["score-job"]
