#!/usr/bin/env bash
# Runs on the rented machine, once, before box_masks.py: a Python with torch and transformers (the versions the scene
# steps use, scene_setup.sh) and SAM 3's weights, named by SAM3_WEIGHTS.
set -euo pipefail

# A card that ran this set-up before (this PC's container, whose `segment` venv is kept between claims; a parked card)
# is set up already: this file wrote the mark last, named for this file's text and its weights, so a changed set-up
# runs again. The mark holds only while /root/venv imports what box_masks.py needs: segment_setup.sh's SAM 2 shares
# the kind `segment` and rebuilds /root/venv. (2026-11-23, pixal@walkway: with no mark, every claim fetched uv,
# torch and the weights again, and one failed name lookup of astral.sh in this PC's container stopped the place.)
done_mark="/root/.box-masks-setup-$( (cat "$0"; echo "${SAM3_WEIGHTS:?}") | sha256sum | cut -c1-16)"
if [ -f "$done_mark" ] && /root/venv/bin/python -c "import scipy; from transformers import Sam3Model" 2>/dev/null; then
  echo "set up already (a parked card)"
  exit 0
fi

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --clear --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision transformers==5.17.0 \
  accelerate==1.15.0 huggingface_hub hf_xet safetensors numpy pillow scipy
/root/venv/bin/python -c "import os; from huggingface_hub import snapshot_download; \
snapshot_download(os.environ['SAM3_WEIGHTS'])"
touch "$done_mark"
