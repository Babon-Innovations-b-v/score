#!/usr/bin/env bash
# The pictures image's command (installed as pictures-run): links the one picture model the job names from the node
# cache (SCORE_MODEL_*, models.json) to /root/model, where picture_worker.py loads it, then runs the job's arguments
# with the model Python (for example: pictures-run tools/props/cloud/picture_worker.py jobs.json
# QwenImageEditPlusPipeline 80).
set -euo pipefail

if [ -n "${SCORE_MODEL_QWEN_IMAGE_EDIT_2511:-}" ] && [ -n "${SCORE_MODEL_FLUX2_KLEIN_4B:-}" ]; then
  echo "pictures-run: a job names one picture model, not both" >&2
  exit 2
fi
ln -sfn "${SCORE_MODEL_QWEN_IMAGE_EDIT_2511:-${SCORE_MODEL_FLUX2_KLEIN_4B:?the job names a picture model}}" /root/model
exec /opt/venv/bin/python "$@"
