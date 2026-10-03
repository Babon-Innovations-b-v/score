#!/usr/bin/env bash
# Runs on the rented machine, once, before its first model: installs Pixal3D the way
# image-to-3dlab's own bootstrap does on any Linux NVIDIA box. Upstream's prebuilt CUDA 12 build
# (no compiling), its weights from Hugging Face, and a small Python for the generator's wrapper.
# Pictures arrive as they were drawn and are cut out here, by the generator's own matte with the
# BiRefNet-lite the bootstrap fetches, through rembg (the lab's requirements.txt pin): no model runs
# on the owner's PC.
set -euo pipefail

LAB=/root/lab
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python pillow huggingface_hub hf_xet \
  numpy rembg==2.0.69 onnxruntime

cd "$LAB"
/root/venv/bin/python scripts/bootstrap_pixal3d.py --yes --prebuilt
