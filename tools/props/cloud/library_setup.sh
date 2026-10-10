#!/usr/bin/env bash
# Runs on the rented machine, once, before library_bake.py's jobs: Blender 5.0.1 (the version tools/blender pins,
# checked against blender.org's sha256 list), the system libraries a headless Blender still links, and pandas for
# ProcFunc in a folder of its own beside Blender (tools/props/library/inside/runtime.py reads it from PROPS_HOME).
set -euo pipefail

# A machine parked by an earlier run of its kind (park.py) is set up already: this file wrote the mark last.
done_mark=/root/.library-setup-done
if [ -f "$done_mark" ]; then
  echo "set up already (a parked machine)"
  exit 0
fi

# A processor machine (--processor) has no card; Cycles then bakes on its processor.
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || nproc
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libsm6 libxkbcommon0 libx11-6 libegl1 \
  xz-utils >/dev/null

version=5.0.1
tarball="blender-$version-linux-x64.tar.xz"
cd /root
curl -fsSL -o "$tarball" "https://download.blender.org/release/Blender${version%.*}/$tarball"
curl -fsSL "https://download.blender.org/release/Blender${version%.*}/blender-$version.sha256" | grep " $tarball\$" \
  > "$tarball.sha256"
sha256sum -c "$tarball.sha256"
tar xJf "$tarball"
mv "blender-$version-linux-x64" /root/blender
rm "$tarball" "$tarball.sha256"

/root/blender/5.0/python/bin/python3.11 -m pip install --quiet --target /root/props/blender-mcp/pf-site \
  "pandas>=1.5,<2.3" "numpy==1.26.4"
/root/blender/blender -b -setaudio None --python-expr "import bpy; print('blender ok', bpy.app.version_string)"
touch "$done_mark"
