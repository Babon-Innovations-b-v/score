#!/usr/bin/env bash
# Runs on the rented machine, once, before its first picture: a Python with torch and transformers, and Depth
# Anything V2 Small (Apache-2.0, depth-anything/Depth-Anything-V2-Small-hf at a pinned revision) from Hugging Face.
set -euo pipefail
REVISION=5426e4f0f36572d16453bbda7a8389317b1bef99

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch torchvision transformers pillow numpy \
  huggingface_hub hf_xet
/root/venv/bin/python -c "import sys; from huggingface_hub import snapshot_download; \
snapshot_download('depth-anything/Depth-Anything-V2-Small-hf', revision=sys.argv[1], \
local_dir='/root/dav2')" "$REVISION"
