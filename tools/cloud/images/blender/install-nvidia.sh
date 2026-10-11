#!/bin/sh
# The driver's user-space OptiX files from NVIDIA's installer extracted in $1, of driver version $2: libnvoptix,
# libnvidia-rtcore and nvoptix.bin, and libnvidia-gpucomp, without which OptiX's kernel load fails with an internal
# compiler error (2026-10-11).
set -eu
from=$1 version=$2 lib=/usr/lib/x86_64-linux-gnu
for name in libnvoptix libnvidia-rtcore libnvidia-gpucomp; do
  install -m 755 "$from/$name.so.$version" "$lib/"
done
ldconfig
install -D -m 644 "$from/nvoptix.bin" /usr/share/nvidia/nvoptix.bin
