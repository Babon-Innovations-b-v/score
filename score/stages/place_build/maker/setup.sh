#!/usr/bin/env bash
# The model maker's own Python on this PC (place_build `make`, #128): TRELLIS.2 (microsoft/TRELLIS.2, MIT) at a pinned
# commit, its compiled pieces built here from their sources (o-voxel from TRELLIS.2's own tree, FlexGEMM at its v1.0.0
# tag and CuMesh at a pinned commit, both by TRELLIS.2's author), with NVIDIA's CUDA 13.0 compiler from PyPI (the PC
# has no CUDA toolkit). No prebuilt wheel from a third-party account; no flash-attn (shim/flash_attn: torch's own
# attention) and no NVIDIA nvdiffrast (shim/nvdiffrast: a UV rasterizer in torch). The weights: TRELLIS.2-4B and the
# TRELLIS-image-large structure decoder (MIT) at pinned revisions, DINOv3 ViT-L/16 checked by its file's sha256.
#
#     bash setup.sh [<env folder, default $PROPS_HOME/envs/trellis2>]
#
# Idempotent: a built piece or a fetched weight is kept. Writes <env>/ready.json last, naming what it built from.
#
#     bash setup.sh closeup [<env folder, default $PROPS_HOME/envs/closeup>]
#
# The close-up picture model beside it: FLUX.2 klein 4B (black-forest-labs, Apache-2.0, code and weights) through
# diffusers' Flux2KleinPipeline, for a clean centred picture of a small object whose concept crop is too few pixels for
# TRELLIS.2. Its weights are a cache under <env>/weights at the revision tools/cloud/images/pictures/models.json pins;
# about 8 GB of card with the pipeline's CPU offload, so it fits the 16 GB card one picture at a time.
set -euo pipefail
export UV_HTTP_TIMEOUT=600 UV_HTTP_RETRIES=8

if [ "${1:-}" = closeup ]; then
  KLEIN=e7b7dc27f91deacad38e78976d1f2b499d76a294  # black-forest-labs/FLUX.2-klein-4B
  ENV=${2:-${PROPS_HOME:?set PROPS_HOME or name the env folder}/envs/closeup}
  PY=$ENV/venv/bin/python
  mkdir -p "$ENV/weights"
  [ -x "$PY" ] || uv venv -q --python 3.12 "$ENV/venv"
  uv pip install -q --python "$PY" --index-url https://download.pytorch.org/whl/cu130 \
    --extra-index-url https://pypi.org/simple torch==2.11.0 torchvision==0.26.0
  uv pip install -q --python "$PY" diffusers==0.42.1 transformers==5.22.2 accelerate==1.15.0 pillow==12.0.0 \
    huggingface_hub==2.4.0 hf_xet safetensors numpy scipy==1.18.1
  "$PY" - "$ENV/weights/FLUX.2-klein-4B" "$KLEIN" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download("black-forest-labs/FLUX.2-klein-4B", revision=sys.argv[2], local_dir=sys.argv[1],
                  allow_patterns=["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*",
                                  "transformer/*", "vae/*", "LICENSE.md"])
PY
  "$PY" -c "from diffusers import Flux2KleinPipeline"
  printf '{"flux2_klein_4b": "%s", "diffusers": "0.42.1", "licence": "Apache-2.0"}\n' "$KLEIN" > "$ENV/ready.json"
  echo CLOSEUP-READY "$ENV"
  exit 0
fi

TRELLIS2=75fbf0183001ed9876c8dbb35de6b68552ee08bd
FLEXGEMM=de6411284d20a6d41362db27a59a6923aeceebfe  # v1.0.0, the version TRELLIS.2's code at TRELLIS2 calls
CUMESH=12289e1062f0603f2f0d0771b02e1395d247f26f
WEIGHTS=af44b45f2e35a493886929c6d786e563ec68364d  # microsoft/TRELLIS.2-4B
IMAGE_LARGE=25e0d31ffbebe4b5a97464dd851910efc3002d96  # microsoft/TRELLIS-image-large (its sparse structure decoder)
DECODER_SHA=1c76d4a40519aa2d711cc263a8404105231ac26db31d946bed48b84fee79009a
# DINOv3 ViT-L/16 (Meta's facebook/dinov3-vitl16-pretrain-lvd1689m is gated, its file's hash hidden): an open copy at
# a pinned revision, checked by the sha256 its repository publishes; its size is the gated original's (1212559808).
DINOV3_REPO=camenduru/dinov3-vitl16-pretrain-lvd1689m
DINOV3=3c276edd87d6f6e569ff0c4400e086807d0f3881
DINOV3_SHA=dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179

ENV=${1:-${PROPS_HOME:?set PROPS_HOME or name the env folder}/envs/trellis2}
PY=$ENV/venv/bin/python
SITE=$ENV/venv/lib/python3.12/site-packages
mkdir -p "$ENV/src" "$ENV/weights"
[ -x "$PY" ] || uv venv -q --python 3.12 "$ENV/venv"
PIP=(uv pip install -q --python "$PY")
"${PIP[@]}" --index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.org/simple \
  torch==2.11.0 torchvision==0.26.0 triton==3.6.0
"${PIP[@]}" setuptools wheel ninja pillow==12.0.0 imageio==2.37.2 tqdm==4.67.1 easydict==1.13 \
  opencv-python-headless==4.12.0.88 trimesh==4.10.1 transformers==4.57.3 zstandard==0.25.0 kornia==0.8.2 \
  timm==1.0.22 huggingface_hub==0.36.2 hf_xet safetensors scipy plyfile xatlas==0.0.10 coacd==1.0.7 \
  "git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8" \
  nvidia-cuda-nvcc==13.0.88 nvidia-cuda-cccl==13.0.85 nvidia-cuda-crt==13.0.88 nvidia-nvvm==13.0.88 \
  nvidia-cuda-runtime==13.0.96

# A CUDA home for torch's extension builder out of NVIDIA's wheels: bin, include and lib64 side by side.
CUDA=$ENV/cuda
mkdir -p "$CUDA/bin" "$CUDA/include" "$CUDA/lib64"
for found in "$SITE"/nvidia/cu13/bin/* "$SITE"/nvidia/cu13/nvvm; do ln -sfn "$found" "$CUDA/bin/$(basename "$found")"; done
ln -sfn "$SITE/nvidia/cu13/nvvm" "$CUDA/nvvm"
for found in "$SITE"/nvidia/cu13/include/* "$SITE"/nvidia/cu13/include/cccl/*; do
  [ -e "$found" ] && ln -sfn "$found" "$CUDA/include/$(basename "$found")"
done
for found in "$SITE"/nvidia/cu13/lib/*; do ln -sfn "$found" "$CUDA/lib64/$(basename "$found")"; done
ln -sfn "$CUDA/lib64/libcudart.so.13" "$CUDA/lib64/libcudart.so"
# glibc 2.41 and later declare rsqrt and rsqrtf (C23) noexcept; CUDA 13.0's crt/math_functions.h declares them
# without, and nvcc refuses the pair. Its crt folder here is a copy whose math_functions.h gives the two declarations
# glibc's noexcept, as NVIDIA's own headers already do for cospi and sinpi.
rm -rf "$CUDA/include/crt" && mkdir "$CUDA/include/crt"
for found in "$SITE"/nvidia/cu13/include/crt/*; do ln -sfn "$found" "$CUDA/include/crt/$(basename "$found")"; done
rm "$CUDA/include/crt/math_functions.h"
sed -E 's/^(extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ (double|float) +rsqrtf?\((double|float) x\));/\1 noexcept (true);/' \
  "$SITE/nvidia/cu13/include/crt/math_functions.h" > "$CUDA/include/crt/math_functions.h"
grep -q "rsqrtf(float x) noexcept (true);" "$CUDA/include/crt/math_functions.h"
# One compile at a time: one of nvcc's cicc takes 2.7 GB, and two of CuMesh's passed an 8 GB scope (OOM, 2026-11-16).
export CUDA_HOME=$CUDA PATH=$CUDA/bin:$PATH TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-12.0} MAX_JOBS=${MAX_JOBS:-1}
export LIBRARY_PATH=$CUDA/lib64${LIBRARY_PATH:+:$LIBRARY_PATH}

fetched() {  # <folder> <url> <commit>: a recursive clone at that commit
  [ -d "$1/.git" ] || git clone -q --recursive "$2" "$1"
  git -C "$1" fetch -q origin "$3" 2>/dev/null || true
  git -C "$1" checkout -q "$3"
  git -C "$1" submodule update -q --init --recursive
}
fetched "$ENV/src/TRELLIS.2" https://github.com/microsoft/TRELLIS.2.git "$TRELLIS2"
fetched "$ENV/src/FlexGEMM" https://github.com/JeffreyXiang/FlexGEMM.git "$FLEXGEMM"
fetched "$ENV/src/CuMesh" https://github.com/JeffreyXiang/CuMesh.git "$CUMESH"
built() { "$PY" -c "import $1" 2>/dev/null; }
built flex_gemm || "${PIP[@]}" --no-build-isolation "$ENV/src/FlexGEMM"
built cumesh || "${PIP[@]}" --no-build-isolation "$ENV/src/CuMesh"
# o_voxel imports nvdiffrast at import: built here, checked with the shim on the path.
PYTHONPATH="$(dirname "$0")/shim" "$PY" -c "import o_voxel" 2>/dev/null \
  || "${PIP[@]}" --no-build-isolation --no-deps "$ENV/src/TRELLIS.2/o-voxel"
# (--no-deps: o-voxel's own list names CuMesh and FlexGEMM at their newest commits; they are built above at the pins)

"$PY" - "$ENV/weights" "$WEIGHTS" "$IMAGE_LARGE" "$DINOV3_REPO" "$DINOV3" <<'PY'
import sys
from huggingface_hub import hf_hub_download, snapshot_download
weights, revision, image_large, dinov3_repo, dinov3 = sys.argv[1:]
snapshot_download("microsoft/TRELLIS.2-4B", revision=revision, local_dir=f"{weights}/TRELLIS.2-4B")
for name in ("ss_dec_conv3d_16l8_fp16.json", "ss_dec_conv3d_16l8_fp16.safetensors"):
    hf_hub_download("microsoft/TRELLIS-image-large", f"ckpts/{name}", revision=image_large,
                    local_dir=f"{weights}/TRELLIS-image-large")
snapshot_download(dinov3_repo, revision=dinov3, local_dir=f"{weights}/dinov3")
PY
echo "$DECODER_SHA  $ENV/weights/TRELLIS-image-large/ckpts/ss_dec_conv3d_16l8_fp16.safetensors" | sha256sum -c --quiet -
echo "$DINOV3_SHA  $ENV/weights/dinov3/model.safetensors" | sha256sum -c --quiet -

PYTHONPATH="$(dirname "$0")/shim:$ENV/src/TRELLIS.2" "$PY" -c "import flex_gemm, cumesh, o_voxel, trellis2, coacd"
cat > "$ENV/ready.json" <<JSON
{"trellis2": "$TRELLIS2", "flexgemm": "$FLEXGEMM", "cumesh": "$CUMESH", "weights": "$WEIGHTS",
 "image_large": "$IMAGE_LARGE", "dinov3": "$DINOV3_SHA", "cuda": "nvidia-cuda-nvcc 13.0.88 (PyPI)",
 "arch": "$TORCH_CUDA_ARCH_LIST"}
JSON
echo TRELLIS2-READY "$ENV"
