#!/usr/bin/env bash
# On the rented card: MOSS-SoundEffect v2.0 (OpenMOSS, Apache-2.0 code and weights) and transformers for CLAP, the code at a pinned MOSS-TTS
# commit and the weights at a pinned Hugging Face revision (moss_sound.py passes both).
set -euo pipefail
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
cd /root/sfx
curl -fsSL "https://codeload.github.com/OpenMOSS/MOSS-TTS/tar.gz/${MOSS_SHA}" | tar xz
mv "MOSS-TTS-${MOSS_SHA}" MOSS-TTS
/root/uv/uv venv --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cu128 -e "MOSS-TTS/moss_soundeffect_v2[torch-cu128]" hf_xet transformers
/root/venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('OpenMOSS-Team/MOSS-SoundEffect-v2.0', revision='${MOSS_MODEL_REVISION}', local_dir='/root/sfx/model')"
du -sh /root/sfx/model
