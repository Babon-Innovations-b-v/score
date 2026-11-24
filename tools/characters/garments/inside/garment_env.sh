#!/usr/bin/env bash
# Builds GarmentCode's own Python (pygarment, MIT, maria-korosteleva/GarmentCode at a pinned commit), once, at the
# folder it is given: sewing patterns and their box meshes only. GarmentCode's simulation is never installed or
# imported (it runs on a fork of NVIDIA Warp under a non-commercial licence); the cloth is draped by Newton
# (score/stages/physics/inside/newton_env.sh).
#
#   bash tools/characters/garments/inside/garment_env.sh <folder>    then  <folder>/bin/python inside/pattern.py ...
#
# GarmentCode's source sits in <folder>/GarmentCode (its garment programs and measurement definitions are not in the
# pygarment wheel). Every version is pinned; a changed pin builds the folder again (the mark is this file's hash).
set -euo pipefail

folder=${1:?usage: garment_env.sh <folder>}
mark="$folder/.built-$(sha256sum "$0" | cut -c1-16)"
if [ -f "$mark" ]; then
  exit 0
fi
commit=d449629979028123a5c4dc9e732a2ec19b7fce31
uv=$(command -v uv || true)
if [ -z "$uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
  uv=/root/uv/uv
fi
"$uv" venv --clear --quiet --python 3.10 "$folder"
rm -rf "$folder/GarmentCode"
git clone -q https://github.com/maria-korosteleva/GarmentCode "$folder/GarmentCode"
git -C "$folder/GarmentCode" checkout -q "$commit"
"$uv" pip install --quiet --python "$folder/bin/python" \
  "numpy==1.26.4" "scipy==1.13.1" "pyyaml==6.0.2" "svgwrite==1.4.3" "svgpathtools==1.6.1" "cairosvg==2.7.1" \
  "matplotlib==3.9.2" "trimesh==4.4.9" "libigl==2.5.1" "cgal==6.0.1.post202410241521" "psutil==6.0.0"
"$folder/bin/python" -c "import sys; sys.modules['warp'] = None; sys.path.insert(0, '$folder/GarmentCode'); \
from pygarment.meshgen.boxmeshgen import BoxMesh; print('garment ok')"
touch "$mark"
