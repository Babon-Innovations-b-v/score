#!/usr/bin/env bash
# Runs on the rented machine, once, before finish_masks.py's runs: the scene steps' versions of torch and
# transformers (scene_setup.sh) and SAM 3's weights (SAM License, commercial use allowed; SAM3_WEIGHTS names the
# open copy scene.py uses, as the gated facebook/sam3 is not open to the account).
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision transformers==5.17.0 \
  accelerate==1.15.0 huggingface_hub hf_xet safetensors numpy pillow
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('${SAM3_WEIGHTS:?}')"
