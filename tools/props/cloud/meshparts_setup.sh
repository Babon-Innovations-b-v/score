#!/usr/bin/env bash
# Runs on the rented machine, once, before meshparts.py's runs (job parts-test, 2026-10-09). Two environments:
#
# /root/sv: SegviGen (MIT) at a pinned commit on Python 3.10 and torch 2.6 (its TRELLIS.2 environment, the compiled
#   cumesh, flex_gemm and o_voxel from TRELLIS.2's own published wheels, all MIT), xformers for attention (any card),
#   bpy 4.0 for its conditioning render, TRELLIS.2-4B's encoders, decoders and texture flow model (MIT), SegviGen's two
#   full-segmentation checkpoints (MIT) and DINOv3 ViT-L/16 (DINOv3 Licence) from an open copy whose weights file is
#   checked against its sha256. Never installed: nvdiffrast and nvdiffrec (non-commercial; o_voxel's exporter that
#   imports nvdiffrast is cut from its package's imports) and briaai/RMBG-2.0 (non-commercial; never loaded).
# /root/gs: GeoSAM2 (Apache-2.0 code and weights) at a pinned commit on Python 3.11 and torch 2.5.1, its CUDA
#   extension left unbuilt (the GPU image has no CUDA toolkit; its README says results are usually unaffected), and
#   Blender 4.0.2 from blender.org with a virtual display for its EEVEE renders (its script uses Blender 4.0's mesh
#   auto smooth, gone in 4.1).
set -euo pipefail

: "${SEGVIGEN:?}" "${SEGVIGEN_WEIGHTS:?}" "${TRELLIS_WEIGHTS:?}" "${DINOV3:?}" "${DINOV3_REVISION:?}" "${DINOV3_SHA256:?}"
: "${GEOSAM2:?}" "${GEOSAM2_WEIGHTS:?}" "${WHEELS:?}" "${UTILS3D:?}" "${BLENDER_URL:?}"

nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential git xvfb xauth libegl1 libgl1 libgl1-mesa-dri \
  libglu1-mesa libx11-6 libxrender1 libxfixes3 libxi6 libsm6 libxext6 libxkbcommon0 libxxf86vm1 libwayland-client0 \
  libwayland-egl1 libdbus-1-3 libglib2.0-0 libdecor-0-0 >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
UV=/root/uv/uv

# SegviGen.
mkdir -p /root/sv && cd /root/sv
curl -fsSL "https://codeload.github.com/Nelipot-Lee/SegviGen/tar.gz/${SEGVIGEN}" | tar xz
mv "SegviGen-${SEGVIGEN}" SegviGen
$UV venv --quiet --python 3.10 /root/sv/venv
SV=/root/sv/venv/bin/python
$UV pip install --quiet --python $SV torch==2.6.0 torchvision==0.21.0 triton==3.2.0 xformers==0.0.29.post3 \
  --index-url https://download.pytorch.org/whl/cu124
$UV pip install --quiet --python $SV pillow==12.0.0 imageio==2.37.2 imageio-ffmpeg==0.6.0 tqdm easydict==1.13 \
  opencv-python-headless==4.12.0.88 trimesh==4.10.1 transformers==4.57.6 zstandard==0.25.0 kornia==0.8.2 \
  timm==1.0.22 accelerate fast-simplification safetensors huggingface_hub hf_xet scipy setuptools \
  "git+https://github.com/EasternJournalist/utils3d.git@${UTILS3D}" \
  "${WHEELS}/cumesh-0.0.1-cp310-cp310-linux_x86_64.whl" \
  "${WHEELS}/flex_gemm-0.0.1-cp310-cp310-linux_x86_64.whl" \
  "${WHEELS}/o_voxel-0.0.1-cp310-cp310-linux_x86_64.whl"
$UV pip install --quiet --python $SV bpy==4.0.0 --extra-index-url https://download.blender.org/pypi/
# o_voxel imports its glb exporter (and with it nvdiffrast) at import; the exporter is never used here.
OVOXEL=$($SV -c "import importlib.util, os; print(os.path.dirname(importlib.util.find_spec('o_voxel').origin))")
sed -i -e 's/^\(\s*\)postprocess,\s*$/\1# postprocess (needs the non-commercial nvdiffrast): not imported/' "$OVOXEL/__init__.py"
grep -n "postprocess" "$OVOXEL/__init__.py"
if $SV -c "import nvdiffrast" 2>/dev/null; then echo "nvdiffrast must not be installed"; exit 1; fi
cd /root/sv/SegviGen
$SV - <<EOF
from huggingface_hub import hf_hub_download, snapshot_download
snapshot_download("microsoft/TRELLIS.2-4B", revision="${TRELLIS_WEIGHTS}", local_dir="microsoft/TRELLIS.2-4B",
                  allow_patterns=["pipeline.json", "ckpts/shape_enc_next_dc_f16c32_fp16.*",
                                  "ckpts/shape_dec_next_dc_f16c32_fp16.*", "ckpts/tex_enc_next_dc_f16c32_fp16.*",
                                  "ckpts/tex_dec_next_dc_f16c32_fp16.*", "ckpts/slat_flow_imgshape2tex_dit_1_3B_512_bf16.*"])
for name in ("full_seg.ckpt", "full_seg_w_2d_map.ckpt"):
    hf_hub_download("fenghora/SegviGen", name, revision="${SEGVIGEN_WEIGHTS}", local_dir="weights")
snapshot_download("${DINOV3}", revision="${DINOV3_REVISION}", local_dir="/root/sv/dinov3")
EOF
echo "${DINOV3_SHA256}  /root/sv/dinov3/model.safetensors" | sha256sum -c -
$SV -c "import o_voxel, cumesh, flex_gemm, xformers, bpy, trellis2; print('segvigen imports ok')"

# GeoSAM2.
mkdir -p /root/gs && cd /root/gs
curl -fsSL "https://codeload.github.com/VAST-AI-Research/GeoSAM2/tar.gz/${GEOSAM2}" | tar xz
mv "GeoSAM2-${GEOSAM2}" GeoSAM2
$UV venv --quiet --python 3.11 /root/gs/venv
GS=/root/gs/venv/bin/python
$UV pip install --quiet --python $GS torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
$UV pip install --quiet --python $GS setuptools wheel ninja numpy hydra-core omegaconf iopath pillow opencv-python==4.10.0.84 \
  matplotlib tqdm trimesh pandas scipy huggingface_hub hf_xet
cd /root/gs/GeoSAM2
GEOSAM2_BUILD_CUDA=0 SAM2_BUILD_CUDA=0 $UV pip install --quiet --python $GS --no-build-isolation -e .
$GS -c "from huggingface_hub import hf_hub_download; hf_hub_download('VAST-AI/GeoSAM2', 'geosam2.pt', revision='${GEOSAM2_WEIGHTS}', local_dir='ckpt')"
mkdir -p /root/gs/blender
curl -fsSL "${BLENDER_URL}" | tar xJ --strip-components=1 -C /root/gs/blender
/root/gs/blender/blender --version | head -1
# GeoSAM2's render script imports Pillow inside Blender's own Python.
/root/gs/blender/4.0/python/bin/python3.10 -m ensurepip >/dev/null
/root/gs/blender/4.0/python/bin/python3.10 -m pip install --quiet pillow
# Its mode_ext C++ helper is compiled on first import; compile it now so the first take does not.
cd /root/gs/GeoSAM2 && PATH=/root/gs/venv/bin:$PATH $GS -c "import utils.mode_ext; print('geosam2 helper built')"
echo "setup done"
