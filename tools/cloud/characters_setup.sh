#!/usr/bin/env bash
# Runs on the rented card machine, once, before characters.py makes its people: every tool the prop route of the
# character maker (tools/characters/maker/prop_chain.py) runs, each in an environment of its own because they want different torch
# builds and Pythons. The repository's tools and vendored copies are already in /root/score (characters.py sent them).
#
#   /root/envs/motion    Kimodo (vendor/kimodo, Apache-2.0; weights nvidia/Kimodo-SOMA-RP-v1.1, NVIDIA Open Model
#                        License) with SOMA-X (Apache-2.0): the clips, the body model, the body build and the usd step.
#   /root/sam3dbody-cpp  SAM3DBody-cpp (vendor/sam3dbody-cpp, MIT code; its ONNX/GGUF weights are SAM 3D Body's,
#                        under Meta's SAM License): the body read off one picture.
# The retired shipped person chain's GarmentCode, Newton and Hi3DGen environments and klein base 4B with its depth
# LoRA went with it (owner, 2026-10-21: all old stuff is retired), and the prop route's own close-up drawing (klein 4B)
# and Blender with the close-ups the people line now draws.
#
# Secrets come by name: the HuggingFace read token (`hf-read-token`, for Meta-Llama-3-8B-Instruct, the gated base of
# Kimodo's text encoder) arrives in /root/hf-token, written by characters.py, never in the repo.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
LOGS=/root/setup-logs
mkdir -p "$LOGS" /root/envs /root/.cache/huggingface
cp /root/hf-token /root/.cache/huggingface/token

# A machine set up before keeps it (this PC's container from one claim to the next, park.own_set_up): this file wrote
# the mark last, named for its text and the shipped Kimodo and SAM3DBody-cpp, so a changed set-up runs again. Without
# the mark the old copies and environment go first: a copy into one already there nests, uv refuses a venv there.
done_mark="/root/.characters-setup-$( (cat "$0"; cd /root/score/vendor && find kimodo sam3dbody-cpp -type f -print0 \
  | sort -z | xargs -0 sha256sum) | sha256sum | cut -c1-16)"
if [ $# -eq 0 ]; then
  if [ -f "$done_mark" ]; then
    echo "set up already"
    exit 0
  fi
  rm -rf /root/kimodo /root/sam3dbody-cpp /root/envs/motion
fi
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader
ARCH="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')"

apt-get update -qq
apt-get install -y -qq build-essential cmake git wget unzip xz-utils libjpeg-dev libpng-dev libzstd-dev liblz4-dev \
  libopencv-dev libgl1-mesa-dev libglew-dev libgl1 libegl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libsm6 \
  libxkbcommon0 libx11-6 libglib2.0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
UV=/root/uv/uv

motion() {
  cp -r /root/score/vendor/kimodo /root/kimodo
  $UV venv --quiet --python 3.11 /root/envs/motion
  $UV pip install --quiet --python /root/envs/motion/bin/python torch --index-url https://download.pytorch.org/whl/cu128
  $UV pip install --quiet --python /root/envs/motion/bin/python cmake ninja numpy
  PATH="/root/envs/motion/bin:$PATH" $UV pip install --quiet --python /root/envs/motion/bin/python -e /root/kimodo \
    "py-soma-x @ git+https://github.com/NVlabs/SOMA-X.git@d6aa640f7787498009c4e3d57fcc14a243905d10"  # the image's SOMA_COMMIT: its assets are the stored v0.3.3
  $UV pip install --quiet --python /root/envs/motion/bin/python trimesh scipy pillow pyyaml usd-core rtree \
    opencv-python-headless
  /root/envs/motion/bin/python -c "import soma, kimodo, pxr; print('motion ok')"
}

cuda_toolkit() {
  # CUDA 12.6 and cuDNN 9 from NVIDIA's apt repository: ONNX Runtime's CUDA provider and the ggml heads link them.
  # The GPU image already lists that repository (its own keyring); adding NVIDIA's keyring package beside it makes
  # apt refuse both, so it is added only on an image without it. It is installed before the environments are built
  # side by side: Kimodo's C++ extension failed to configure while the toolkit was landing under it (an L4, 9 October).
  if ! grep -rqs "developer.download.nvidia.com/compute/cuda/repos" /etc/apt/sources.list.d/; then
    local release; release="$(. /etc/os-release && echo "${VERSION_ID//./}")"
    wget -q -O /tmp/keyring.deb \
      "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu${release}/x86_64/cuda-keyring_1.1-1_all.deb"
    dpkg -i /tmp/keyring.deb >/dev/null
    apt-get update -qq
  fi
  apt-get install -y -qq cuda-toolkit-12-6 libcudnn9-cuda-12 libcudnn9-dev-cuda-12 >/dev/null
}

sam3dbody() {
  cp -r /root/score/vendor/sam3dbody-cpp /root/sam3dbody-cpp
  cd /root/sam3dbody-cpp
  PATH=/usr/local/cuda-12.6/bin:$PATH bash scripts/setup.sh --cuda-arch "$ARCH" --skip-venv < /dev/null
  ls -la build/libfast_sam_3dbody.so onnx/
}

cuda_toolkit

# Side by side, each into its own log; the step that fails names its log. Steps named on the command line run alone
# (mending one on a held machine).
pids=()
for step in ${*:-motion sam3dbody}; do
  ( set -euo pipefail; "$step" ) > "$LOGS/$step.log" 2>&1 &
  pids+=("$!:$step")
done
failed=0
for entry in "${pids[@]}"; do
  if ! wait "${entry%%:*}"; then
    echo "setup step ${entry##*:} failed:"; tail -n 30 "$LOGS/${entry##*:}.log"; failed=1
  fi
done
[ "$failed" -eq 0 ] || exit 1
[ $# -gt 0 ] || touch "$done_mark"
echo "characters setup done"
