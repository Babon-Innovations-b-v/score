#!/usr/bin/env bash
# MoGe-2 (microsoft/MoGe, MIT; its weights Ruicheng/moge-2-vitl-normal, MIT) beside GEM-X's Python on a cluster card
# node (tools/labval/moge_cluster.py): the packages unpacked into <folder>/pkgs (put on PYTHONPATH of GEM-X's Python,
# which already holds torch, numpy, scipy, OpenCV and imageio-ffmpeg) and the weights at <folder>/model.pt, built once a
# node under a lock; a changed pin here builds it again (the mark is this file's hash).
#
#   bash tools/labval/moge_env.sh <folder>
#
# Pinned: MoGe at 07444410 (2025-11-02, the last MoGe-2 release before V3 brought compiled dependencies), its
# utils3d at the commit its pyproject names, both by archive sha256; the weights by Hugging Face revision and sha256.
set -euo pipefail

folder=${1:?usage: moge_env.sh <folder>}
mkdir -p "$(dirname "$folder")"
exec 9>"$folder.lock"
flock 9
mark="$folder/.built-$(sha256sum < "$0" | cut -c1-16)"
if [ -f "$mark" ]; then
  exit 0
fi
rm -rf "$folder"
mkdir -p "$folder/pkgs"

MOGE=07444410f1e33f402353b99d6ccd26bd31e469e8
MOGE_SHA256=08e5fcbaa4421a0e3e284ac7e3196965904677bb479c29b19c95ead47407f734
UTILS3D=3fab839f0be9931dac7c8488eb0e1600c236e183
UTILS3D_SHA256=f1f167b1f68809bea391a66dd0d2ad0e14f7382cbddf087b655181c31a285abb
WEIGHTS_REVISION=b135031bae30b5ac2ae141a0e68717795ce38340   # 2025-07-11, model.pt unchanged since
WEIGHTS_SHA256=280741fd09bc3f403ccff9967784c2a391b52d2c0742ae3efdb21d9f90cc1a01

# <url> <sha256> <path>: downloaded beside its place, checked, then moved in; a mismatch stops the build.
fetch() {
  curl -fsSL --retry 4 --retry-delay 5 "$1" -o "$3.part"
  echo "$2  $3.part" | sha256sum -c --quiet -
  mv "$3.part" "$3"
}

fetch "https://github.com/microsoft/MoGe/archive/$MOGE.tar.gz" "$MOGE_SHA256" "$folder/moge.tar.gz"
fetch "https://github.com/EasternJournalist/utils3d/archive/$UTILS3D.tar.gz" "$UTILS3D_SHA256" "$folder/utils3d.tar.gz"
tar xzf "$folder/moge.tar.gz" -C "$folder/pkgs" --strip-components=1 "MoGe-$MOGE/moge"
tar xzf "$folder/utils3d.tar.gz" -C "$folder/pkgs" --strip-components=1 "utils3d-$UTILS3D/utils3d"
fetch "https://huggingface.co/Ruicheng/moge-2-vitl-normal/resolve/$WEIGHTS_REVISION/model.pt" "$WEIGHTS_SHA256" \
  "$folder/model.pt"
touch "$mark"
