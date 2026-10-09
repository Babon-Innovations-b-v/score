#!/usr/bin/env bash
# The parts image's command (installed as parts-run): links PartCrafter's weights from the node cache
# (SCORE_MODEL_PARTCRAFTER, models.json) where its script looks for them, then runs the job's arguments with
# PartCrafter's Python from its checkout, headless, as parts.run_line does on a rented machine
# (for example: parts-run scripts/inference_partcrafter.py --image_path ... --num_parts 4 --output_dir ...).
set -euo pipefail

CHECKOUT=/opt/parts/PartCrafter
mkdir -p "$CHECKOUT/pretrained_weights"
ln -sfn "$SCORE_MODEL_PARTCRAFTER" "$CHECKOUT/pretrained_weights/PartCrafter"
cd "$CHECKOUT"
# Its src/ is imported from the checkout; its render helpers load OpenGL and pyglet at import.
export PYTHONPATH=. PYOPENGL_PLATFORM=egl PYGLET_HEADLESS=true
exec /opt/parts/venv/bin/python "$@"
