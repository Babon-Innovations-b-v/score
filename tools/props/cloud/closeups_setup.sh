#!/usr/bin/env bash
# Runs on the rented machine, once, before closeups_gpu.py (closeups_cloud.py): a Python with torch 2.4 for CUDA 12.4,
# gsplat from its prebuilt wheel for that pair (no compile on the machine), and transformers for SAM 2.1, whose
# weights come from Hugging Face on first use.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.10 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python torch==2.4.1 torchvision==0.19.1 \
  --index-url https://download.pytorch.org/whl/cu124
# The prebuilt wheels are for Python 3.10 only (checked 2026-10-05); PyPI's gsplat has no compiled part and the image
# has no CUDA compiler, so the wheel is pinned from gsplat's own index and its plain dependencies come from PyPI.
/root/uv/uv pip install --quiet --python /root/venv/bin/python --no-deps "gsplat==1.5.3+pt24cu124" \
  --index-url https://docs.gsplat.studio/whl/pt24cu124
/root/uv/uv pip install --quiet --python /root/venv/bin/python jaxtyping rich typing_extensions
/root/uv/uv pip install --quiet --python /root/venv/bin/python "transformers==4.57.1" huggingface_hub hf_xet \
  safetensors numpy pillow trimesh setuptools ninja
ls /usr/local/cuda*/bin/nvcc 2>/dev/null || echo "no nvcc on the image"
/root/venv/bin/pip show gsplat 2>/dev/null | head -3 || /root/uv/uv pip show --python /root/venv/bin/python gsplat | head -3
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
/root/venv/bin/python -c "import gsplat, torch; print('gsplat', gsplat.__version__, 'torch', torch.__version__, torch.cuda.is_available())"
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('facebook/sam2.1-hiera-large')"
