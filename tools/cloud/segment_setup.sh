#!/usr/bin/env bash
# Runs on the rented machine, once, before segment.py's runs: Python 3.11, torch 2.9.1 for CUDA 12.8 and SAM 2
# (facebookresearch/sam2, Apache-2.0 code and SAM 2.1 weights) at a pinned commit, its optional CUDA extension left
# unbuilt (it only fills small holes in masks; the GPU image has no CUDA toolkit), and the SAM 2.1 large weights.
# CUDA 12.8 because its wheels carry Blackwell's kernels (sm_120, this PC's RTX 5080): cu124's 2.5.1 has none, so
# SAM 2 failed there with "no kernel image is available" (env1, 2026-10-31); 2.9.1 is the sam image's torch.
set -euo pipefail

# A card parked after an earlier run of its kind (park.py) is set up already: this file wrote the mark last,
# named for this file's text and its pins, so a changed set-up runs again.
done_mark="/root/.segment-setup-$( (cat "$0"; echo "${SAM2:?} ${SAM2_WEIGHTS:?}") | sha256sum | cut -c1-16)"
if [ -f "$done_mark" ]; then
  echo "set up already (a parked card)"
  exit 0
fi

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libgl1 libglib2.0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --clear --quiet --python 3.11 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.9.1 torchvision==0.24.1 \
  --index-url https://download.pytorch.org/whl/cu128
# Built against the torch above (no build isolation), so the build needs setuptools in the environment.
/root/uv/uv pip install --quiet --python /root/venv/bin/python setuptools wheel
SAM2_BUILD_CUDA=0 /root/uv/uv pip install --quiet --python /root/venv/bin/python --no-build-isolation \
  "git+https://github.com/facebookresearch/sam2@${SAM2:?}" huggingface_hub pillow numpy
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('${SAM2_WEIGHTS:?}')"
touch "$done_mark"
