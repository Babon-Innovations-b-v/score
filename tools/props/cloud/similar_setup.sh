#!/usr/bin/env bash
# Runs on the rented machine, once, before similar.py's runs: Python 3.11, torch 2.5.1 for CUDA 12.4, transformers and
# the DINOv2 weights (facebook/dinov2-base, Apache-2.0).
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.11 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
/root/uv/uv pip install --quiet --python /root/venv/bin/python transformers==4.46.3 pillow numpy huggingface_hub
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('${DINO_WEIGHTS:?}')"
