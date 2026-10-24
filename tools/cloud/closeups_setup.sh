#!/usr/bin/env bash
# Runs on the rented machine, once, before closeups_gpu.py (closeups_cloud.py). Two Pythons, because the renderer and
# the segmenter want different torches:
#   /root/venv   Python 3.10, torch 2.4 for CUDA 12.4 and gsplat's prebuilt wheel for that pair (the wheels are for
#                Python 3.10 only, checked 2026-10-05; PyPI's gsplat has no compiled part and the image has no CUDA
#                compiler), for `render`.
#   /root/venv2  Python 3.12, the owner's box's torch 2.9.1 and transformers 5.17 for SAM 3, and rembg with
#                BiRefNet-lite (image-to-3dlab's remover), for `segment` and `matte`.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null

/root/uv/uv venv --quiet --python 3.10 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.4.1 torchvision==0.19.1 \
  --index-url https://download.pytorch.org/whl/cu124
/root/uv/uv pip install --quiet --python /root/venv/bin/python --no-deps "gsplat==1.5.3+pt24cu124" \
  --index-url https://docs.gsplat.studio/whl/pt24cu124
/root/uv/uv pip install --quiet --python /root/venv/bin/python jaxtyping rich typing_extensions numpy pillow packaging \
  setuptools ninja
# One tiny render, so a gsplat that cannot run fails here, before the run.
/root/venv/bin/python - <<'PY'
import torch
from gsplat import rasterization
means = torch.zeros(1, 3, device="cuda"); means[0, 2] = 2
image, alpha, _ = rasterization(means, torch.tensor([[1.0, 0, 0, 0]], device="cuda"), torch.full((1, 3), 0.1, device="cuda"),
                                torch.ones(1, device="cuda"), torch.ones(1, 1, 3, device="cuda"), torch.eye(4, device="cuda")[None],
                                torch.tensor([[[32.0, 0, 16], [0, 32, 16], [0, 0, 1]]], device="cuda"), 32, 32, sh_degree=0)
print("gsplat renders", float(alpha.max()))
PY

/root/uv/uv venv --quiet --python 3.12 /root/venv2
/root/uv/uv pip install --quiet --python /root/venv2/bin/python torch==2.9.1 torchvision transformers==5.17.0 \
  accelerate huggingface_hub hf_xet safetensors numpy pillow scipy rembg==2.0.69 onnxruntime
/root/venv2/bin/python -c "from huggingface_hub import snapshot_download; import os; snapshot_download(os.environ.get('SAM3_WEIGHTS', 'facebook/sam3'))"
mkdir -p /root/.u2net
curl -sL -o /root/.u2net/birefnet-general-lite.onnx \
  https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx
echo "4fab47adc4ff364be1713e97b7e66334  /root/.u2net/birefnet-general-lite.onnx" | md5sum -c -
