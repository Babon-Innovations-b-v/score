# Splitting our own models into parts: SegviGen and GeoSAM2 in one image, as tools/props/cloud/meshparts_setup.sh
# (job parts-test, 2026-10-09) installs them on a rented machine. One kind, two environments that cannot share a
# Python: SegviGen on Python 3.10 and torch 2.6 (TRELLIS.2's environment) and GeoSAM2 on Python 3.11 and torch 2.5.1,
# each resolved and hashed (segvigen.txt, geosam2.txt), with Blender 4.0.2 for GeoSAM2's EEVEE renders under a virtual
# display (its script uses Blender 4.0's mesh auto smooth, gone in 4.1).
#
# /opt/sv: SegviGen (MIT) at a pinned commit, TRELLIS.2's published wheels of cumesh, flex_gemm and o_voxel (MIT),
#   xformers for attention, bpy 4.0 for its conditioning render. Never installed: nvdiffrast and nvdiffrec
#   (non-commercial; o_voxel's exporter that imports nvdiffrast is cut from its package's imports, and the build
#   fails if nvdiffrast is importable) and briaai/RMBG-2.0 (non-commercial; never loaded).
# /opt/gs: GeoSAM2 (Apache-2.0) at a pinned commit, its CUDA extension left unbuilt (no CUDA toolkit here; its README
#   says results are usually unaffected), its C++ mode helper compiled at build time.
# No weights: score-job fetches them into the node cache (models.json); segvigen-run and geosam2-run link them in.
ARG BASE
FROM ${BASE}

ARG SEGVIGEN=81ec99ede1fbe566c73322dd968cd64bb508f5f7
ARG GEOSAM2=b5de23c60ab487d407b623d394a1614f9714761c
ARG BLENDER_URL=https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz
ARG BLENDER_SHA256=5583a5588736da8858c522ef17fff5d73be59c47a6fe91ad29c6f3263e22086a
ARG SEGVIGEN_PYTHON=3.10.20
ARG GEOSAM2_PYTHON=3.11.15

RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends ca-certificates curl xz-utils \
      build-essential git xvfb xauth libegl1 libgl1 libgl1-mesa-dri libglu1-mesa libx11-6 libxrender1 libxfixes3 \
      libxi6 libsm6 libxext6 libxkbcommon0 libxxf86vm1 libwayland-client0 libwayland-egl1 libdbus-1-3 libglib2.0-0 \
      libdecor-0-0 \
 && rm -rf /var/lib/apt/lists/*


# SegviGen.
COPY segvigen.txt /opt/sv/requirements.txt
RUN mkdir -p /opt/sv \
 && curl -fsSL "https://codeload.github.com/Nelipot-Lee/SegviGen/tar.gz/${SEGVIGEN}" | tar -xz -C /opt/sv \
 && mv "/opt/sv/SegviGen-${SEGVIGEN}" /opt/sv/SegviGen \
 && uv venv --quiet --python ${SEGVIGEN_PYTHON} /opt/sv/venv \
 && uv pip sync --quiet --python /opt/sv/venv/bin/python \
      --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu124 \
      --extra-index-url https://download.blender.org/pypi/ --index-strategy unsafe-best-match \
      /opt/sv/requirements.txt \
 && OVOXEL=$(/opt/sv/venv/bin/python -c "import importlib.util, os; print(os.path.dirname(importlib.util.find_spec('o_voxel').origin))") \
 && sed -i -e 's/^\(\s*\)postprocess,\s*$/\1# postprocess (needs the non-commercial nvdiffrast): not imported/' "$OVOXEL/__init__.py" \
 && grep -n "postprocess" "$OVOXEL/__init__.py" \
 && if /opt/sv/venv/bin/python -c "import nvdiffrast" 2>/dev/null; then echo "nvdiffrast must not be installed"; exit 1; fi \
 && cd /opt/sv/SegviGen \
 && /opt/sv/venv/bin/python -c "import o_voxel, cumesh, flex_gemm, xformers, bpy, trellis2; print('segvigen imports ok')"

# GeoSAM2.
COPY geosam2.txt /opt/gs/requirements.txt
ENV TORCH_EXTENSIONS_DIR=/opt/gs/torch_extensions
RUN mkdir -p /opt/gs \
 && curl -fsSL "https://codeload.github.com/VAST-AI-Research/GeoSAM2/tar.gz/${GEOSAM2}" | tar -xz -C /opt/gs \
 && mv "/opt/gs/GeoSAM2-${GEOSAM2}" /opt/gs/GeoSAM2 \
 && uv venv --quiet --python ${GEOSAM2_PYTHON} /opt/gs/venv \
 && uv pip sync --quiet --python /opt/gs/venv/bin/python --require-hashes \
      --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu124 \
      --index-strategy unsafe-best-match /opt/gs/requirements.txt \
 && cd /opt/gs/GeoSAM2 \
 && GEOSAM2_BUILD_CUDA=0 SAM2_BUILD_CUDA=0 uv pip install --quiet --python /opt/gs/venv/bin/python \
      --no-build-isolation --no-deps -e . \
 && PATH=/opt/gs/venv/bin:$PATH /opt/gs/venv/bin/python -c "import utils.mode_ext; print('geosam2 helper built')"

RUN curl -fsSL -o /tmp/blender.tar.xz "${BLENDER_URL}" \
 && echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c - \
 && mkdir -p /opt/gs/blender \
 && tar -xJf /tmp/blender.tar.xz --strip-components=1 -C /opt/gs/blender \
 && rm /tmp/blender.tar.xz \
 && /opt/gs/blender/blender --version | head -1 \
 && /opt/gs/blender/4.0/python/bin/python3.10 -m ensurepip \
 && /opt/gs/blender/4.0/python/bin/python3.10 -m pip install --quiet --no-cache-dir pillow==12.0.0

COPY segvigen-run.sh /usr/local/bin/segvigen-run
COPY geosam2-run.sh /usr/local/bin/geosam2-run
ENV PYTHONUNBUFFERED=1
