#!/usr/bin/env bash
# The sam image's command (installed as sam-run): puts the job's models from the node cache (SCORE_MODEL_*,
# models.json) where the scripts look for them, then runs the job's arguments with the model Python, as the machine
# runners do (for example: sam-run tools/props/scene/cutout.py <room> ...).
#   SAM 3        SAM3_WEIGHTS, the folder (scene.py and closeups_cloud.py pass it the same way)
#   SAM 2.1      by repository id through a Hugging Face hub cache of links to the node cache (runtime/hf_cache.py)
#   MoGe-2       the same
#   BiRefNet     U2NET_HOME/birefnet-general-lite.onnx, the name rembg looks for
#   FLUX.2 klein PROPS_HOME/flux2-klein (paths.PICTURE_MODEL)
set -euo pipefail

/opt/score/venv/bin/python /opt/score/runtime/hf_cache.py "${SCORE_MODELS:-/work/repo/tools/cloud/images/sam/models.json}" \
  "$HF_HUB_CACHE"
if [ -n "${SCORE_MODEL_SAM3:-}" ]; then
  export SAM3_WEIGHTS="$SCORE_MODEL_SAM3"
fi
if [ -n "${SCORE_MODEL_BIREFNET_GENERAL_LITE:-}" ]; then
  mkdir -p "$U2NET_HOME"
  ln -sfn "$SCORE_MODEL_BIREFNET_GENERAL_LITE/BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx" \
    "$U2NET_HOME/birefnet-general-lite.onnx"
fi
if [ -n "${SCORE_MODEL_FLUX2_KLEIN_4B:-}" ]; then
  mkdir -p "$PROPS_HOME"
  ln -sfn "$SCORE_MODEL_FLUX2_KLEIN_4B" "$PROPS_HOME/flux2-klein"
fi
exec /opt/venv/bin/python "$@"
