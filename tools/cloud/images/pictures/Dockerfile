# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-pictures: diffusers for the open picture models (tools/props/cloud/picture_worker.py): FLUX.2 klein 4B
# (Flux2KleinPipeline) and Qwen-Image-Edit-2511 (QwenImageEditPlusPipeline, whose processor needs torchvision). The
# versions are the ones picture_setup.sh's unpinned install takes today (2026-10-09: torch 2.14.1, diffusers 0.41.0,
# transformers 5.19.0; requirements.txt, resolved and hashed). amd64 only: every card class we rent is on x86
# machines. No weights: models.json, fetched by the runtime into /cache, and `pictures-run` (run.sh) links the one a
# job names where the worker looks.
ARG BASE
FROM ${BASE}

ENV HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
COPY requirements.txt /opt/pictures/requirements.txt
RUN uv venv --python 3.12.13 /opt/venv \
 && uv pip sync --python /opt/venv --require-hashes /opt/pictures/requirements.txt \
 && /opt/venv/bin/python -c "import diffusers; diffusers.Flux2KleinPipeline; diffusers.QwenImageEditPlusPipeline"
COPY run.sh /usr/local/bin/pictures-run
