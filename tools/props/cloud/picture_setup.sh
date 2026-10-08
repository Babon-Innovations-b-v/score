#!/usr/bin/env bash
# Runs on the rented machine, once, before its first picture: a Python with torch and diffusers,
# and the picture model (FLUX.2 klein 4B, Apache-2.0) from Hugging Face, the same weights the
# owner's box keeps under ~/.farm-factory-props/flux2-klein.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch diffusers transformers \
  accelerate pillow huggingface_hub hf_xet
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; \
snapshot_download('black-forest-labs/FLUX.2-klein-4B', local_dir='/root/klein', \
allow_patterns=['model_index.json', 'scheduler/*', 'text_encoder/*', 'tokenizer/*', 'transformer/*', 'vae/*'])"
