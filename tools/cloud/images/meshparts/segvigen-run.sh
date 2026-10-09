#!/usr/bin/env bash
# The meshparts image's SegviGen command (installed as segvigen-run): links TRELLIS.2-4B's and SegviGen's weights from
# the node cache (SCORE_MODEL_TRELLIS2_4B, SCORE_MODEL_SEGVIGEN; models.json) where SegviGen looks for them, then runs
# the job's arguments with SegviGen's Python from its checkout, attention through xformers (any card), as
# meshparts.py does on a rented machine. The DINOv3 folder a worker takes is SCORE_MODEL_DINOV3_VITL16.
set -euo pipefail

CHECKOUT=/opt/sv/SegviGen
mkdir -p "$CHECKOUT/microsoft"
ln -sfn "$SCORE_MODEL_TRELLIS2_4B" "$CHECKOUT/microsoft/TRELLIS.2-4B"
ln -sfn "$SCORE_MODEL_SEGVIGEN" "$CHECKOUT/weights"
cd "$CHECKOUT"
export ATTN_BACKEND=xformers SPARSE_ATTN_BACKEND=xformers
exec /opt/sv/venv/bin/python "$@"
