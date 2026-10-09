#!/usr/bin/env bash
# Runs on the rented card machine, once, before characters.py makes its people: every tool the person route of the
# character maker (tools/characters/maker/) runs, each in an environment of its own because they want different torch
# builds and Pythons. The repository's tools and vendored copies are already in /root/score (characters.py sent them).
#
#   /root/envs/motion    Kimodo (vendor/kimodo, Apache-2.0; weights nvidia/Kimodo-SOMA-RP-v1.1, NVIDIA Open Model
#                        License) with SOMA-X (Apache-2.0): the clips, the body model, the body build and the usd step.
#   /root/sam3dbody-cpp  SAM3DBody-cpp (vendor/sam3dbody-cpp, MIT code; its ONNX/GGUF weights are SAM 3D Body's,
#                        under Meta's SAM License): the body read off one picture.
#   /root/envs/garment   GarmentCode (MIT), pinned: sewing patterns and their box meshes, no simulation (its Warp fork
#                        is non-commercial and is never installed; Blender's cloth drapes them).
#   /root/envs/hi3dgen   Hi3DGen (Stable-X, MIT code and weights), pinned: hair meshes from clay pictures.
#   /root/envs/picture   FLUX.2 klein 4B and klein base 4B (Apache-2.0) with diffusers: the A-pose picture, the clay
#                        hair picture and the face drawing (base 4B with the refcontrol depth LoRA, Apache-2.0).
#   /root/blender        Blender 4.2 LTS, the version the people tools thin, unwrap and render with.
#
# Secrets come by name: the HuggingFace read token (`hf-read-token`, for Meta-Llama-3-8B-Instruct, the gated base of
# Kimodo's text encoder) arrives in /root/hf-token, written by characters.py, never in the repo.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
LOGS=/root/setup-logs
mkdir -p "$LOGS" /root/envs
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader
ARCH="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')"

GARMENTCODE_COMMIT=d449629979028123a5c4dc9e732a2ec19b7fce31
HI3DGEN_COMMIT=c29f668ecec44b197275e9bf77f823c0c8a21076
BLENDER_VERSION=4.2.23

apt-get update -qq
apt-get install -y -qq build-essential cmake git wget unzip xz-utils libjpeg-dev libpng-dev libzstd-dev liblz4-dev \
  libopencv-dev libgl1-mesa-dev libglew-dev libgl1 libegl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libsm6 \
  libxkbcommon0 libx11-6 libglib2.0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
UV=/root/uv/uv
mkdir -p /root/.cache/huggingface
cp /root/hf-token /root/.cache/huggingface/token

motion() {
  cp -r /root/score/vendor/kimodo /root/kimodo
  $UV venv --quiet --python 3.11 /root/envs/motion
  $UV pip install --quiet --python /root/envs/motion/bin/python torch --index-url https://download.pytorch.org/whl/cu128
  $UV pip install --quiet --python /root/envs/motion/bin/python cmake ninja numpy
  PATH="/root/envs/motion/bin:$PATH" $UV pip install --quiet --python /root/envs/motion/bin/python -e "/root/kimodo[soma]"
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

garment() {
  git clone -q https://github.com/maria-korosteleva/GarmentCode /root/garmentcode
  git -C /root/garmentcode checkout -q "$GARMENTCODE_COMMIT"
  $UV venv --quiet --python 3.10 /root/envs/garment
  $UV pip install --quiet --python /root/envs/garment/bin/python numpy==1.26.4 scipy libigl==2.6.3 cgal \
    svgpathtools svgwrite cairosvg matplotlib pyyaml trimesh psutil
  /root/envs/garment/bin/python -c "import sys; sys.path.insert(0, '/root/garmentcode'); \
from pygarment.meshgen.boxmeshgen import BoxMesh; print('garment ok')"
}

hi3dgen() {
  git clone -q https://github.com/Stable-X/Stable3DGen /root/hi3dgen
  git -C /root/hi3dgen checkout -q "$HI3DGEN_COMMIT"
  $UV venv --quiet --python 3.11 /root/envs/hi3dgen
  $UV pip install --quiet --python /root/envs/hi3dgen/bin/python torch==2.9.0 torchvision==0.24.0 \
    --index-url https://download.pytorch.org/whl/cu128
  $UV pip install --quiet --python /root/envs/hi3dgen/bin/python spconv-cu126==2.3.8 diffusers==0.31.0 \
    transformers==4.46.3 kornia==0.8.0 timm==0.9.16 accelerate numpy==1.26.4 scipy scikit-image \
    opencv-python-headless einops easydict plyfile trimesh huggingface_hub pillow tqdm triton safetensors \
    xformers==0.0.33.post1
  cd /root/hi3dgen
  /root/envs/hi3dgen/bin/python -c "from huggingface_hub import snapshot_download as get; \
[get(repo_id=name, local_dir='weights/' + name.split('/')[-1]) for name in \
('Stable-X/trellis-normal-v0-1', 'Stable-X/yoso-normal-v1-8-1', 'ZhengPeng7/BiRefNet')]"
  /root/envs/hi3dgen/bin/python -c "import sys; sys.path.insert(0, '/root/hi3dgen'); \
from hi3dgen.pipelines import Hi3DGenPipeline; print('hi3dgen ok')"
}

picture() {
  $UV venv --quiet --python 3.12 /root/envs/picture
  $UV pip install --quiet --python /root/envs/picture/bin/python torch torchvision diffusers transformers accelerate \
    peft pillow numpy huggingface_hub hf_xet
  /root/envs/picture/bin/python -c "from huggingface_hub import snapshot_download as get; \
get('black-forest-labs/FLUX.2-klein-4B', local_dir='/root/models/klein-4b'); \
get('black-forest-labs/FLUX.2-klein-base-4B', local_dir='/root/models/klein-base-4b', \
allow_patterns=['model_index.json', 'scheduler/*', 'transformer/*']); \
get('thedeoxen/refcontrol-FLUX.2-klein-4B-reference-depth-lora', local_dir='/root/models/refcontrol', \
allow_patterns=['flux2_klein_4b_refcontrol_depth.safetensors'])"
}

blender() {
  local tarball="blender-$BLENDER_VERSION-linux-x64.tar.xz"
  cd /root
  curl -fsSL -o "$tarball" "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/$tarball"
  curl -fsSL "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-$BLENDER_VERSION.sha256" \
    | grep " $tarball\$" > "$tarball.sha256"
  sha256sum -c "$tarball.sha256"
  tar xJf "$tarball"
  mv "blender-$BLENDER_VERSION-linux-x64" /root/blender
  rm "$tarball" "$tarball.sha256"
  /root/blender/blender -b -setaudio None --python-expr "import bpy; print('blender ok', bpy.app.version_string)"
}

cuda_toolkit

# Side by side, each into its own log; the step that fails names its log. Steps named on the command line run alone
# (mending one on a held machine).
pids=()
for step in ${*:-motion sam3dbody garment hi3dgen picture blender}; do
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
echo "characters setup done"
