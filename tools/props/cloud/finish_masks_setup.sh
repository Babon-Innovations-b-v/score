#!/usr/bin/env bash
# Runs on the rented machine, once, before finish_masks.py's runs: the scene steps' versions of torch and
# transformers (scene_setup.sh) and SAM 3's weights (SAM License, commercial use allowed; SAM3_WEIGHTS names the
# open copy scene.py uses, as the gated facebook/sam3 is not open to the account).
set -euo pipefail

# A card parked after an earlier run of its kind (park.py) is set up already: this file wrote the mark last,
# named for this file's text and its pins, so a changed set-up runs again.
done_mark="/root/.finish-masks-setup-$( (cat "$0"; echo "${SAM3_WEIGHTS:?}") | sha256sum | cut -c1-16)"
if [ -f "$done_mark" ]; then
  echo "set up already (a parked card)"
  exit 0
fi

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --clear --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision transformers==5.17.0 \
  accelerate==1.15.0 huggingface_hub hf_xet safetensors numpy pillow
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('${SAM3_WEIGHTS:?}')"
touch "$done_mark"
