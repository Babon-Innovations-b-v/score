#!/usr/bin/env bash
# Runs on the rented machine, once, before segment.py's runs: Python 3.11, torch 2.5.1 for CUDA 12.4 and SAM 2
# (facebookresearch/sam2, Apache-2.0 code and SAM 2.1 weights) at a pinned commit, its optional CUDA extension left
# unbuilt (it only fills small holes in masks; the GPU image has no CUDA toolkit), and the SAM 2.1 large weights.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libgl1 libglib2.0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.11 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cu124
# Built against the torch above (no build isolation), so the build needs setuptools in the environment.
/root/uv/uv pip install --quiet --python /root/venv/bin/python setuptools wheel
SAM2_BUILD_CUDA=0 /root/uv/uv pip install --quiet --python /root/venv/bin/python --no-build-isolation \
  "git+https://github.com/facebookresearch/sam2@${SAM2:?}" huggingface_hub pillow numpy
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('${SAM2_WEIGHTS:?}')"
