#!/usr/bin/env bash
# The Portable Biomechanics Laboratory's own environment (IntelligentSensingAndRehabilitation/MonocularBiomechanics,
# Peiffer, Cotton et al., arXiv:2507.08268; AGPL-3.0) on a cluster card node, for tools/labval/pbl/on_pbl.py: its code
# at a pinned commit, its Python from its own uv.lock (`uv sync --frozen --extra cuda`: JAX 0.10.1 with CUDA 12,
# MuJoCo MJX 3.9.0, TensorFlow 2.21.0, every package as the lock pins and hashes it), and the MeTRAbs model its
# load_metrabs() fetches (https://bit.ly/metrabs_l, metrabs_eff2l_y4_384px_800k_28ds) by sha256. Built once a node
# into <folder> under a lock in the base image (uv and Python 3.12 there); a changed pin builds it again (the mark is
# this file's hash). Nothing of it is in SCORE: the build fetches upstream as released.
#
#   bash tools/labval/pbl/pbl_env.sh <folder>
#
# One change to the lock's packages: opencv-python is swapped for opencv-python-headless at the same version
# (4.13.0.92, hashed), the same OpenCV without its GUI, since the base image has no libGL and PBL's fitting draws
# nothing (its renderer, visualize.py, is never imported). MeTRAbs' models are for non-commercial use (their training
# sets' licences; github.com/isarandi/metrabs): this is a research baseline in a paper, nothing sold.
set -euo pipefail

folder=${1:?usage: pbl_env.sh <folder>}
mkdir -p "$(dirname "$folder")"
exec 9>"$folder.lock"
flock 9
mark="$folder/.built-$(sha256sum < "$0" | cut -c1-16)"
if [ -f "$mark" ]; then
  exit 0
fi
rm -rf "$folder"
mkdir -p "$folder"

PBL=118de08f5cfc91ba8eb02de53aa21f76cba6b75e   # 2026-10-30, main's head
PBL_SHA256=af8ce9d6cccc0f586ddd63c4ed8ca5e08a4f3cf68dfb78277281f760b0dfecd5
METRABS=https://omnomnom.vision.rwth-aachen.de/data/metrabs/metrabs_eff2l_y4_384px_800k_28ds.tar.gz
METRABS_SHA256=fa31b5b043f227588c3d224e56db89307d021bfbbb52e36028919f90e1f96c89

# <url> <sha256> <path>: downloaded beside its place, checked, then moved in; a mismatch stops the build.
fetch() {
  curl -fsSL --retry 4 --retry-delay 5 "$1" -o "$3.part"
  echo "$2  $3.part" | sha256sum -c --quiet -
  mv "$3.part" "$3"
}

fetch "https://github.com/IntelligentSensingAndRehabilitation/MonocularBiomechanics/archive/$PBL.tar.gz" \
  "$PBL_SHA256" "$folder/pbl.tar.gz"
mkdir -p "$folder/src"
tar xzf "$folder/pbl.tar.gz" -C "$folder/src" --strip-components=1
rm "$folder/pbl.tar.gz"
(cd "$folder/src" && UV_PROJECT_ENVIRONMENT="$folder/venv" uv sync --quiet --frozen --extra cuda --python 3.12)
cat > "$folder/headless.txt" <<'PINS'
opencv-python-headless==4.13.0.92 \
    --hash=sha256:0525a3d2c0b46c611e2130b5fdebc94cf404845d8fa64d2f3a3b679572a5bd22 \
    --hash=sha256:0bd48544f77c68b2941392fcdf9bcd2b9cdf00e98cb8c29b2455d194763cf99e
PINS
uv pip uninstall --quiet --python "$folder/venv/bin/python" opencv-python
uv pip install --quiet --python "$folder/venv/bin/python" --no-deps --require-hashes -r "$folder/headless.txt"

fetch "$METRABS" "$METRABS_SHA256" "$folder/metrabs.tar.gz"
mkdir -p "$folder/metrabs"
tar xzf "$folder/metrabs.tar.gz" -C "$folder/metrabs"
rm "$folder/metrabs.tar.gz"
(cd "$folder/src" && "$folder/venv/bin/python" -c \
  "import cv2, mujoco, jax, tensorflow_hub, monocular_demos.biomechanics_mjx.monocular_trajectory")
touch "$mark"
