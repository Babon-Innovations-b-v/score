#!/usr/bin/env bash
# Runs on the rented machine, once, before parts.py's PartCrafter runs: Python 3.11, torch 2.5.1 for CUDA 12.4 (the
# versions PartCrafter's README names), its requirements less the training-only ones, and its MIT weights.
# Its background remover (briaai/RMBG-1.4) is non-commercial: its download is taken out of the script here and it is
# never used; the pictures come cut out already.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
# Its render helpers load OpenGL at import (pyrender), even when nothing is rendered.
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libegl1 libgl1 libgles2 libglu1-mesa libx11-6 libxext6 libxrender1 libglib2.0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
cd /root/parts
curl -fsSL "https://codeload.github.com/wgsxm/PartCrafter/tar.gz/${PARTCRAFTER:-main}" | tar xz
mv "PartCrafter-${PARTCRAFTER:-main}" PartCrafter
cd PartCrafter
# Only PartCrafter's own weights; the non-commercial remover is never fetched.
sed -i -e 's/^\(\s*\)snapshot_download(repo_id="briaai\/RMBG-1.4".*$/\1pass  # RMBG-1.4 is non-commercial: not fetched/' \
  -e 's/^\(\s*\)rmbg_net = BriaRMBG.from_pretrained.*$/\1rmbg_net = None  # never loaded/' \
  -e 's/^\(\s*\)rmbg_net\.eval().*$/\1pass/' scripts/inference_partcrafter.py
grep -n "RMBG\|rmbg_net" scripts/inference_partcrafter.py || true

/root/uv/uv venv --quiet --python 3.11 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cu124
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch-cluster \
  -f https://data.pyg.org/whl/torch-2.5.1+cu124.html
grep -v -E '^(deepspeed|wandb)' settings/requirements.txt \
  > /root/parts/requirements.txt
/root/uv/uv pip install --quiet --python /root/venv/bin/python -r /root/parts/requirements.txt accelerate
# Newer diffusers and transformers want torch 2.6+ (torch.accelerator); held at the spring 2025 versions PartCrafter
# was released with.
/root/uv/uv pip install --quiet --python /root/venv/bin/python diffusers==0.33.1 transformers==4.51.3 accelerate==1.6.0 \
  peft==0.15.2 huggingface_hub==0.30.2
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('wgsxm/PartCrafter', local_dir='pretrained_weights/PartCrafter')"
