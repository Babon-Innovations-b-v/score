#!/usr/bin/env bash
# Builds motion_correction's manylinux_2_28 x86_64 wheels (CPython 3.11 and 3.12, pyproject's requires-python) from
# vendor/kimodo/MotionCorrection into this directory, in the official manylinux image pinned by digest, so no machine
# that runs `uv sync` compiles it. Needs docker and network (setuptools from PyPI; pybind11 v2.11.1 and Eigen 3.4.0
# fetched by its CMakeLists at their tags); the vendored source is built from a scratch copy, left as released. Usage: bash vendor/kimodo/wheels/build.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
image=quay.io/pypa/manylinux_2_28_x86_64@sha256:7e41b1c7fd64dfc69703a1124b43c404382973ee06ec5d764b85c34d2221fded
docker run --rm -e SOURCE_DATE_EPOCH=1700000000 -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  -v "$here/../MotionCorrection:/src:ro" -v "$here:/out" "$image" bash -euo pipefail -c '
for py in cp311-cp311 cp312-cp312; do
  rm -rf /tmp/src /tmp/raw && cp -r /src /tmp/src
  # manylinux ships no libpython (extensions link none); its CMakeLists asks for Development (Module plus Embed).
  sed -i "s/COMPONENTS Interpreter Development REQUIRED/COMPONENTS Interpreter Development.Module REQUIRED/" \
    /tmp/src/CMakeLists.txt
  /opt/python/$py/bin/python -m pip install --quiet setuptools==80.9.0 wheel==0.45.1
  /opt/python/$py/bin/python -m pip wheel --quiet --no-deps --no-build-isolation -w /tmp/raw /tmp/src
  auditwheel repair --plat manylinux_2_28_x86_64 -w /out /tmp/raw/*.whl
done
chown "$HOST_UID:$HOST_GID" /out/*.whl'
