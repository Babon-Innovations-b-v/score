#!/usr/bin/env bash
# Runs on the rented processor machine, once, before the Infinigen jobs (infinigen.py). The runner
# has copied the vendored copy to /root/infinigen and the repo's tools to /root/repo/tools.
#
# What the vendored copy leaves out is fetched here, each at the commit v1.19.0 pins:
#   infinigen/infinigen_gpl  GPLv3, imported by Infinigen's materials (snow), kelp, corals and lichen;
#                            never in our repo, only ever run here as part of the tool
#   infinigen/OcMesher       BSD-3, the camera mesher
#   infinigen/assets/fonts   the OFL fonts, 17 MB, used only by indoor text
# The OpenGL ground-truth sources (customgt) are not fetched: nothing here builds them.
# The apt packages are the ones Infinigen's install docs name for Ubuntu (glm is needed by the terrain build).
# Python 3.11 and Blender as the bpy 4.2.0 wheel, as Infinigen asks; terrain compiled for the processor.
set -euo pipefail

INFINIGEN=/root/infinigen
COMMIT=01c39c7f7adcf7363ccbcc57c64410c69f4a4e7c

export DEBIAN_FRONTEND=noninteractive
apt-get update -q >/dev/null
apt-get install -yq build-essential cmake git wget rsync zlib1g-dev libglm-dev libglew-dev libglfw3-dev libgles2-mesa-dev libgomp1 libgl1 libglu1-mesa libegl1 \
  libxrender1 libxi6 libxxf86vm1 libxfixes3 libxkbcommon0 libsm6 libxext6 libx11-6 >/dev/null
nproc; free -g | head -2
# rsync kept this PC's owner on the copy; git refuses folders owned by someone else.
chown -R root:root "$INFINIGEN"

pinned() {  # url folder commit
  mkdir -p "$2"
  git -C "$2" init -q
  git -C "$2" fetch -q --depth 1 "$1" "$3"
  git -C "$2" checkout -q FETCH_HEAD
}
pinned https://github.com/princeton-vl/infinigen_gpl.git "$INFINIGEN/infinigen/infinigen_gpl" \
  10c1d76f5c35003e919be7265185c9c355e3b70c
pinned https://github.com/princeton-vl/OcMesher.git "$INFINIGEN/infinigen/OcMesher" \
  bb895a01b8f574da10be1df470210df7463a75c7
for dependency in eigen argparse cnpy glm json stb glfw; do
  mkdir -p "$INFINIGEN/infinigen/datagen/customgt/dependencies/$dependency"
  echo "not fetched: the OpenGL ground truth is not built here" \
    > "$INFINIGEN/infinigen/datagen/customgt/dependencies/$dependency/NOT_FETCHED"
done
git clone -q --filter=blob:none --sparse --no-checkout https://github.com/princeton-vl/infinigen.git /root/upstream
git -C /root/upstream sparse-checkout set infinigen/assets/fonts
git -C /root/upstream checkout -q "$COMMIT"
cp -r /root/upstream/infinigen/assets/fonts "$INFINIGEN/infinigen/assets/fonts"

curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
/root/uv/uv venv --quiet --python 3.11 /root/venv
cd "$INFINIGEN"
/root/uv/uv pip install --quiet --python /root/venv/bin/python -e ".[terrain]"
ls infinigen/terrain/lib/cpu/elements
# One import of the whole asset library, so a missing piece fails here, before the run.
/root/venv/bin/python -c "import bpy, infinigen; from infinigen.assets.materials import Snow; \
from infinigen.assets.objects.creatures.fish import FishFactory; print('infinigen', bpy.app.version_string)"
