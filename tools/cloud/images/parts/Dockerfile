# PartCrafter (wgsxm/PartCrafter, MIT code and weights) as tools/props/cloud/parts_setup.sh installs it on a rented
# machine, at a pinned commit: Python 3.11, torch 2.5.1 for CUDA 12.4 (the versions its README names), its
# requirements less the training-only ones, and the spring 2025 diffusers and transformers it was released with
# (requirements.txt, resolved and hashed). Its background remover (briaai/RMBG-1.4) is non-commercial: its download
# and loading are patched out of the script and it is never fetched. Its own weights' download is patched out too:
# score-job fetches them into the node cache (models.json) and run.sh links them where the script looks.
ARG BASE
FROM ${BASE}

ARG PARTCRAFTER=3d773bf02fad51c7ab31a5615573fec93b287b30
ARG PYTHON=3.11.15

# Its render helpers load OpenGL at import (pyrender), even when nothing is rendered.
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends ca-certificates curl libegl1 libgl1 \
      libgles2 libglu1-mesa libx11-6 libxext6 libxrender1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/parts/requirements.txt
RUN uv venv --quiet --python ${PYTHON} /opt/parts/venv \
 && uv pip sync --quiet --python /opt/parts/venv/bin/python --require-hashes \
      --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu124 \
      --find-links https://data.pyg.org/whl/torch-2.5.1+cu124.html --index-strategy unsafe-best-match \
      /opt/parts/requirements.txt

RUN mkdir -p /opt/parts \
 && curl -fsSL "https://codeload.github.com/wgsxm/PartCrafter/tar.gz/${PARTCRAFTER}" | tar -xz -C /opt/parts \
 && mv "/opt/parts/PartCrafter-${PARTCRAFTER}" /opt/parts/PartCrafter \
 && cd /opt/parts/PartCrafter \
 && sed -i -e 's/^\(\s*\)snapshot_download(repo_id="briaai\/RMBG-1.4".*$/\1pass  # RMBG-1.4 is non-commercial: not fetched/' \
      -e 's/^\(\s*\)rmbg_net = BriaRMBG.from_pretrained.*$/\1rmbg_net = None  # never loaded/' \
      -e 's/^\(\s*\)rmbg_net\.eval().*$/\1pass/' \
      -e 's/^\(\s*\)snapshot_download(repo_id="wgsxm\/PartCrafter".*$/\1pass  # the weights come from the node cache (run.sh)/' \
      scripts/inference_partcrafter.py \
 && ! grep -n 'snapshot_download(repo_id\|BriaRMBG.from_pretrained' scripts/inference_partcrafter.py

COPY run.sh /usr/local/bin/parts-run
ENV PYTHONUNBUFFERED=1
