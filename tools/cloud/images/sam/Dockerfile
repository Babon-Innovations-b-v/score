# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-sam: the vision steps that segment and measure a picture, in one environment because a scene's steps run
# on one card (tools/props/cloud/scene.py): SAM 3 through transformers (scene/cutout.py, box_masks.py,
# closeups_gpu.py's segment), SAM 2.1 through facebookresearch/sam2 (cloud/segment_worker.py), MoGe-2 (scene/depth.py),
# BiRefNet-lite through rembg (closeups_gpu.py's matte) and FLUX.2 klein through diffusers (scene/target.py and
# redraw.py). The versions are scene_setup.sh's and closeups_setup.sh's second Python (torch 2.9.1, transformers
# 5.17.0, diffusers 0.40.0; requirements.txt, resolved and hashed); segment_setup.sh's torch 2.5.1 is not kept, since
# SAM 2 runs on 2.9.1 as well (its optional CUDA extension stays unbuilt, as there). amd64 only: every card class we
# rent is on x86 machines. No weights: models.json, fetched by the runtime into /cache, and `sam-run` (run.sh) puts
# them where the scripts look. MoGe-2's code and its helper utils3d-moge sit at the commits MoGe pins, where depth.py
# looks for them (MOGE_SOURCE, UTILS3D_SOURCE).
ARG BASE
FROM ${BASE}

ARG SAM2=2b90b9f5ceec907a1c18123530e92e794ad901a4
ARG SAM2_SHA256=1f2fbfad3ffa38110368abac76c6ef9df9c282a66d5c2807bc94abf4d2fb30f8
ARG MOGE=74fbce054ebed49800de42d0ad0e83495065719a
ARG MOGE_SHA256=cc6f3525cec7694b97d6d9af7d8854f546cda082f3abc944be17dfb6ad892309
ARG UTILS3D_MOGE=62f09d58509485564e24d5d9f6aac9ee9ebc0c37
ARG UTILS3D_MOGE_SHA256=a6917f2e641b1221daf2e2df06f4605e1754defa07abf4059fc514ddbebffc68
ENV MOGE_SOURCE=/opt/moge UTILS3D_SOURCE=/opt/utils3d-moge HF_HUB_CACHE=/tmp/hf-hub HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 U2NET_HOME=/tmp/u2net PROPS_HOME=/root/props

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/sam/requirements.txt
RUN uv venv --python 3.12.13 /opt/venv \
 && uv pip sync --python /opt/venv --require-hashes /opt/sam/requirements.txt \
 && curl -fsSL -o /tmp/sam2.tar.gz "https://github.com/facebookresearch/sam2/archive/${SAM2}.tar.gz" \
 && echo "${SAM2_SHA256}  /tmp/sam2.tar.gz" | sha256sum -c - \
 && SAM2_BUILD_CUDA=0 uv pip install --python /opt/venv --no-deps --no-build-isolation /tmp/sam2.tar.gz \
 && rm /tmp/sam2.tar.gz
RUN mkdir -p /opt/moge /opt/utils3d-moge \
 && curl -fsSL -o /tmp/moge.tar.gz "https://codeload.github.com/microsoft/MoGe/tar.gz/${MOGE}" \
 && curl -fsSL -o /tmp/utils3d.tar.gz "https://codeload.github.com/EasternJournalist/utils3d-moge/tar.gz/${UTILS3D_MOGE}" \
 && printf '%s  /tmp/moge.tar.gz\n%s  /tmp/utils3d.tar.gz\n' "${MOGE_SHA256}" "${UTILS3D_MOGE_SHA256}" | sha256sum -c - \
 && tar -xzf /tmp/moge.tar.gz --strip-components=1 -C /opt/moge \
 && tar -xzf /tmp/utils3d.tar.gz --strip-components=1 -C /opt/utils3d-moge \
 && rm /tmp/moge.tar.gz /tmp/utils3d.tar.gz \
 && PYTHONPATH=/opt/moge:/opt/utils3d-moge /opt/venv/bin/python -c \
      "import sam2.build_sam, moge.model.v2, rembg, diffusers, transformers; transformers.Sam3Model"
COPY --chmod=755 run.sh /usr/local/bin/sam-run
