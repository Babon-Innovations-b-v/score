#!/usr/bin/env bash
# Runs on the rented machine, once, before its first picture: a Python with torch, torchvision (the
# Qwen-Image models' processor needs it) and diffusers, and the picture model named by its Hugging
# Face repository (pictures.MODELS; by default FLUX.2 klein 4B, Apache-2.0, the same weights the
# owner's box keeps under ~/.farm-factory-props/flux2-klein).
#
#     bash picture_setup.sh <Hugging Face repository>
set -euo pipefail
REPOSITORY="${1:-black-forest-labs/FLUX.2-klein-4B}"

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch torchvision diffusers transformers \
  accelerate pillow huggingface_hub hf_xet
/root/venv/bin/python -c "import sys; from huggingface_hub import snapshot_download; \
snapshot_download(sys.argv[1], local_dir='/root/model', \
allow_patterns=['model_index.json', 'scheduler/*', 'text_encoder/*', 'tokenizer/*', 'processor/*', \
'transformer/*', 'vae/*'])" "$REPOSITORY"
