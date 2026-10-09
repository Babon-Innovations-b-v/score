#!/usr/bin/env bash
# A character step's command in the characters-motion image (`characters-run <program> [<argument> ...]`): the models
# the job was handed laid where the tools look, then the program. SAM3DBody-cpp's ONNX and GGUF files are linked into
# /root/sam3dbody-cpp/onnx (beside the body_mesh.tri its source carries); the Hugging Face models (Kimodo, its LLM2Vec
# adapters and their Llama 3 base, SOMA-X's assets) go into a hub cache of links that Kimodo and SOMA-X find offline
# by repository id and tag.
set -euo pipefail
if [ -n "${SCORE_MODEL_SAM3DBODY_CPP_ONNX:-}" ]; then
  for file in "$SCORE_MODEL_SAM3DBODY_CPP_ONNX"/*; do
    ln -sfn "$file" "/root/sam3dbody-cpp/onnx/$(basename "$file")"
  done
fi
mkdir -p /tmp/hf-hub
/opt/score/venv/bin/python /opt/score/runtime/hf_cache.py \
  /work/repo/tools/cloud/images/characters-motion/models.json /tmp/hf-hub
export HF_HUB_CACHE=/tmp/hf-hub HF_HUB_OFFLINE=1 LOCAL_CACHE=true TEXT_ENCODER_MODE=local
exec "$@"
