#!/usr/bin/env bash
# Builds the physics trial's own Python (Newton with its MuJoCo solver, usd-core), once, at the folder it is given:
# on a rented machine (tools/cloud/blender_cloud.py runs it before a job naming it as its "env") and on this PC.
#
#   bash score/stages/physics/inside/newton_env.sh <folder>      then  <folder>/bin/python physics_trial.py ...
#
# Its own environment, never the score venv's: Newton pins its own MuJoCo and Warp. Every version is pinned, each at
# least two weeks old when chosen (2026-10-27); a changed pin builds the folder again (the mark is this file's hash).
set -euo pipefail

folder=${1:?usage: newton_env.sh <folder>}
mark="$folder/.built-$(sha256sum "$0" | cut -c1-16)"
if [ -f "$mark" ]; then
  exit 0
fi
uv=$(command -v uv || true)
if [ -z "$uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
  uv=/root/uv/uv
fi
"$uv" venv --clear --quiet --python 3.12 "$folder"
"$uv" pip install --quiet --python "$folder/bin/python" \
  "newton==1.6.1" "mujoco==3.12.0" "mujoco-warp==3.12.0" "warp-lang==1.18.0" "usd-core==26.8" \
  "newton-usd-schemas==0.5.0" "numpy==2.5.3" "scipy==1.18.1" "python-fcl==0.7.0.11"
"$folder/bin/python" -c "import fcl, newton, mujoco, pxr; print('newton', newton.__version__, 'mujoco', mujoco.__version__)"
touch "$mark"
