#!/usr/bin/env bash
# Runs on the rented machine, once, before unirig.py's runs: Python 3.11, torch 2.5.1 for CUDA 12.4, UniRig
# (VAST-AI-Research/UniRig, MIT) at a pinned commit and its two checkpoints (VAST-AI/UniRig on Hugging Face, MIT:
# the skeleton model and the skin model, trained on Articulation-XL2.0). Every compiled piece comes as a prebuilt wheel
# (the GPU image has no CUDA toolkit): flash-attn from its own release, spconv for CUDA 12.4, torch_scatter and
# torch_cluster from the PyG wheel index. Only OPT-350m's configuration is fetched (UniRig builds its skeleton
# transformer from it); no OPT weights are loaded.
set -euo pipefail

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git libgl1 libglib2.0-0 libxrender1 libxi6 libxkbcommon0 \
  libsm6 libxext6 libxfixes3 libxxf86vm1 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.11 /root/venv
PIP=(/root/uv/uv pip install --quiet --python /root/venv/bin/python)
"${PIP[@]}" torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
git clone -q https://github.com/VAST-AI-Research/UniRig.git /root/UniRig
git -C /root/UniRig checkout -q "${UNIRIG:?}"
grep -v -e '^flash_attn' -e '^bpy' /root/UniRig/requirements.txt > /root/unirig-requirements.txt
"${PIP[@]}" -r /root/unirig-requirements.txt bpy==4.2.0 spconv-cu124==2.3.8
"${PIP[@]}" "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.5cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"
"${PIP[@]}" torch_scatter==2.1.2 torch_cluster==1.6.3 -f https://data.pyg.org/whl/torch-2.5.0+cu124.html
"${PIP[@]}" numpy==1.26.4
/root/venv/bin/python - <<PY
from huggingface_hub import hf_hub_download
from transformers import AutoConfig
for name in ("skeleton/articulation-xl_quantization_256/model.ckpt", "skin/articulation-xl/model.ckpt"):
    print(hf_hub_download("${UNIRIG_WEIGHTS:?}", name, revision="${UNIRIG_WEIGHTS_REVISION:?}"))
AutoConfig.from_pretrained("facebook/opt-350m")
PY
