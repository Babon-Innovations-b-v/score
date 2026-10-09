#!/usr/bin/env bash
# Runs on the rented machine, once, before box_masks.py: a Python with torch and transformers (the versions the scene
# steps use, scene_setup.sh) and SAM 3's weights, named by SAM3_WEIGHTS.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision transformers==5.17.0 \
  accelerate==1.15.0 huggingface_hub hf_xet safetensors numpy pillow scipy
/root/venv/bin/python -c "import os; from huggingface_hub import snapshot_download; \
snapshot_download(os.environ['SAM3_WEIGHTS'])"
