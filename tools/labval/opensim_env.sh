#!/usr/bin/env bash
# OpenSim 4.5 for on_opensim.py (LabValidation's reference moments), beside SCORE's own environment and never in it:
# a venv at <folder>/venv holding the pyopensim wheels (OpenSim 4.5.2's Python bindings, Apache-2.0) with numpy and
# scipy, and the OpenBLAS and gfortran runtime the wheels' tools module links against unpacked from Ubuntu's packages
# into <folder>/lib (no root needed). Built once under a lock; a changed pin here builds it again (the mark is this
# file's hash). Prints the line to run on_opensim.py with.
#
#   bash tools/labval/opensim_env.sh <folder>
#   LD_LIBRARY_PATH=<folder>/lib <folder>/venv/bin/python -I tools/labval/on_opensim.py ...
set -euo pipefail

folder=${1:?usage: opensim_env.sh <folder>}
mkdir -p "$(dirname "$folder")"
exec 9>"$folder.lock"
flock 9
mark="$folder/.built-$(sha256sum < "$0" | cut -c1-16)"
if [ ! -f "$mark" ]; then
  rm -rf "$folder"
  mkdir -p "$folder/lib" "$folder/debs"
  uv venv -q -p 3.11 "$folder/venv"
  uv pip install -q -p "$folder/venv/bin/python" pyopensim==4.5.2.0 numpy==2.4.6 scipy==1.17.1
  (cd "$folder/debs" && apt-get download -q libopenblas0-pthread=0.3.32+ds-5 libgfortran5=16-20260322-1ubuntu1)
  sha256sum --check --quiet <<SUMS
50b0ff9cf93ead2cee575807f77c3a534efb4fe5083f17a05c66e64964c1dd48  $folder/debs/libopenblas0-pthread_0.3.32+ds-5_amd64.deb
3f028ea56be008c74d197006d65faa320e29824837dd111c8f76b84f6bb578d2  $folder/debs/libgfortran5_16-20260322-1ubuntu1_amd64.deb
SUMS
  for deb in "$folder"/debs/*.deb; do dpkg-deb -x "$deb" "$folder/debs/root"; done
  cp -L "$folder"/debs/root/usr/lib/x86_64-linux-gnu/openblas-pthread/libopenblas.so.0 \
    "$folder"/debs/root/usr/lib/x86_64-linux-gnu/libgfortran.so.5 "$folder/lib/"
  rm -rf "$folder/debs"
  LD_LIBRARY_PATH="$folder/lib" "$folder/venv/bin/python" -I -c "import pyopensim.tools, pyopensim.analyses"
  touch "$mark"
fi
echo "LD_LIBRARY_PATH=$folder/lib $folder/venv/bin/python -I"
