#!/usr/bin/env bash
# The meshparts image's GeoSAM2 command (installed as geosam2-run): links GeoSAM2's checkpoint from the node cache
# (SCORE_MODEL_GEOSAM2; models.json) where its inference looks for it, then runs the job's arguments with GeoSAM2's
# Python from its checkout, as meshparts.py does on a rented machine. Blender 4.0.2 is /opt/gs/blender/blender.
set -euo pipefail

CHECKOUT=/opt/gs/GeoSAM2
mkdir -p "$CHECKOUT/ckpt"
ln -sfn "$SCORE_MODEL_GEOSAM2/geosam2.pt" "$CHECKOUT/ckpt/geosam2.pt"
cd "$CHECKOUT"
export PATH=/opt/gs/venv/bin:$PATH
exec /opt/gs/venv/bin/python "$@"
