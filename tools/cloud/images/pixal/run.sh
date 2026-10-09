#!/usr/bin/env bash
# The pixal image's command (installed as pixal-run): lays the image's trellis-cli build and the node cache's weights
# where image-to-3dlab looks for them, then runs the lab's script with the job's arguments from the lab's folder, as
# machine_run.py does on a rented machine. The arguments are pixal.generator_arguments' (the script first).
# The weights' folders come from score-job as SCORE_MODEL_PIXAL3D, SCORE_MODEL_TRELLIS2_BIREFNET and
# SCORE_MODEL_BIREFNET_GENERAL_LITE (models.json).
set -euo pipefail

LAB=/work/repo/vendor/image-to-3dlab
PIXAL=$LAB/vendor/pixal3d-cpp
MODELS=$PIXAL/models/pixal3d-sv

mkdir -p "$MODELS" "$U2NET_HOME"
ln -sfn /opt/pixal/build "$PIXAL/build"
# trellis-cli looks for every model flat in one folder (bootstrap_pixal3d.flatten_matte).
for file in "$SCORE_MODEL_PIXAL3D"/*; do
  ln -sfn "$file" "$MODELS/$(basename "$file")"
done
ln -sfn "$SCORE_MODEL_TRELLIS2_BIREFNET/q8/birefnet.gguf" "$MODELS/birefnet.gguf"
ln -sfn "$SCORE_MODEL_BIREFNET_GENERAL_LITE/BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx" \
  "$U2NET_HOME/birefnet-general-lite.onnx"

cd "$LAB"
exec /opt/pixal/venv/bin/python "$@"
