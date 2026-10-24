#!/usr/bin/env bash
# Runs on the rented machine, once, before its first picture: a Python with torch and diffusers,
# and Marigold-IID appearance v1-1 (prs-eth, CreativeML Open RAIL++-M) from Hugging Face.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch diffusers transformers \
  accelerate pillow matplotlib huggingface_hub hf_xet
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; \
snapshot_download('prs-eth/marigold-iid-appearance-v1-1', local_dir='/root/marigold')"
