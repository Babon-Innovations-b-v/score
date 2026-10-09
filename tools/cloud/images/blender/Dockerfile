# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-blender: headless Blender 5.0.1 for every Blender job (blender_cloud.py's renders, settling and review pages,
# and library_bake.py's bakes share this one environment, as their machines share library_setup.sh). Blender from
# blender.org, checked against its sha256; the system libraries a headless Blender still links; pandas and NumPy for
# ProcFunc in PROPS_HOME's blender-mcp/pf-site (tools/props/library/inside/runtime.py). /root/blender and
# PROPS_HOME=/root/props keep the machine runner's paths, so the same run lines work in here.
# GPU kernels: Blender 5.0.1 ships Cycles CUDA binaries for sm_50 to sm_89 and sm_120 but none for sm_90, so an H100's
# first render waited 218 s for the driver to compile Cycles' PTX; the L4 and L40S (sm_89) start at once. A job naming
# kernel_cache "blender-5.0.1" keeps the compiled cache per card and driver in the node cache and the store
# (tools/cloud/runtime/kernels.py, warmed by tools/cloud/images/warm.py): a new H100 node's first render then takes
# 0.3 s. The provider's GPU machines carry NVIDIA's headless compute driver, which has no OptiX library, so Cycles
# renders on CUDA there; the graphics capability lets the container toolkit mount OptiX where a driver has it.
ARG BASE
FROM ${BASE}
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics PROPS_HOME=/root/props BLENDER=/opt/blender/blender
RUN apt-get update \
 && apt-get install -y --no-install-recommends libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libsm6 \
    libxkbcommon0 libx11-6 libegl1 \
 && rm -rf /var/lib/apt/lists/*
ARG BLENDER_VERSION=5.0.1
ARG BLENDER_SHA256=8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09
RUN curl -fsSL -o /tmp/blender.tar.xz \
    "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
 && echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum -c - \
 && mkdir -p /opt/blender \
 && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
 && rm /tmp/blender.tar.xz \
 && ln -s /opt/blender /root/blender
COPY requirements.txt /opt/score/blender-requirements.txt
RUN /opt/blender/5.0/python/bin/python3.11 -m pip install --quiet --no-cache-dir --require-hashes \
    --target /root/props/blender-mcp/pf-site -r /opt/score/blender-requirements.txt \
 && /opt/blender/blender -b -setaudio None --python-expr "import bpy; print('blender ok', bpy.app.version_string)"
