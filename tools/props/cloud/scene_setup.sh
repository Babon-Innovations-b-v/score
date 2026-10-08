#!/usr/bin/env bash
# Runs on the rented machine, once, before a scene's steps (scene.py): a Python with the owner's
# box's own versions of torch, diffusers and transformers, the picture model (FLUX.2 klein 4B), and
# what MoGe-2's copied code imports. SAM 3's and MoGe-2's weights come from Hugging Face on first
# use; MoGe-2's code arrives from the owner's box under /root/props/moge and utils3d-moge.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision \
  transformers==5.17.0 diffusers==0.40.0 accelerate==1.15.0 huggingface_hub hf_xet safetensors \
  numpy pillow scipy opencv-python-headless matplotlib trimesh click tqdm requests einops
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; \
snapshot_download('black-forest-labs/FLUX.2-klein-4B', local_dir='/root/props/flux2-klein', \
allow_patterns=['model_index.json', 'scheduler/*', 'text_encoder/*', 'tokenizer/*', 'transformer/*', 'vae/*'])"
