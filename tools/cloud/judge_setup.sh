#!/usr/bin/env bash
# Runs on the rented machine, once, before its first question: a Python with vLLM, and the judge model named by
# its Hugging Face repository (judge.MODEL: Qwen3.8-27B in FP8, Apache-2.0).
#
#     bash judge_setup.sh <Hugging Face repository>
set -euo pipefail
REPOSITORY="$1"

# A card parked after an earlier run of its kind (park.py) is set up already: this file wrote the mark last,
# named for this file's text and the model, so a changed set-up runs again.
done_mark="/root/.judge-setup-$( (cat "$0"; echo "$REPOSITORY") | sha256sum | cut -c1-16)"
if [ -f "$done_mark" ]; then
  echo "set up already (a parked card)"
  exit 0
fi

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --clear --quiet --python 3.12 /root/venv
/root/uv/uv pip install --quiet --python /root/venv/bin/python vllm huggingface_hub hf_xet pillow
/root/venv/bin/python -c "import sys; from huggingface_hub import snapshot_download; \
snapshot_download(sys.argv[1], local_dir='/root/model')" "$REPOSITORY"
touch "$done_mark"
