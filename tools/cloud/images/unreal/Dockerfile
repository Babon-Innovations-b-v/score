# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# pull-login: ghcr.io epic-ghcr-user epic-ghcr-token
# score-unreal: Unreal Engine 5.8.4's editor for headless Movie Render Queue renders (tools/cloud/unreal/, #222), FROM
# Epic's official Linux container image with score-base's job runtime (/opt/score: uv's Python 3.12, its venv and the
# runtime, the same paths) copied in, so `score-job` runs it as every other kind's image does.
# Licence (Unreal Engine EULA §4, #216): an image holding the editor goes only to a private registry shared within our
# own organisation; Epic's images need a GitHub account linked to an Epic account, whose read token the builder logs
# in with (the secrets named on the pull-login line, by name only). build.py pushes to the project's registry
# namespace, which it refuses when public. Never push this image anywhere else.
# The editor refuses to run as root: on_card.py runs it as Epic's image's user (ue4); the runtime itself stays root,
# as in every job image, to read the node's cache and write /work.
# Vulkan: the cluster nodes' container runtime injects NVIDIA's compute libraries only (measured 2026-11-24 on an L4
# node, driver 595.91.07: libnvidia-ml, ptxjitcompiler, nvvm, opencl, encode; NVIDIA_VISIBLE_DEVICES=void, so the
# graphics capability is ignored), and Epic's ICD file names libGLX_nvidia.so.0, which was absent: vulkaninfo failed
# with ERROR_INCOMPATIBLE_DRIVER. So the image carries NVIDIA's graphics user libraries for exactly the nodes' driver
# (NVIDIA_DRIVER, the one constant; on_card.py refuses a node whose driver differs, as a user library of another
# version than the kernel module fails), from NVIDIA's own CUDA apt repository, each package pinned by its sha256 there
# (libnvidia-gl: GLX, EGL, glcore, glsi, glvkspirv, rtcore, tls...; libnvidia-gpucomp, which libnvidia-gl needs). Only
# the libraries, the EGL vendor file and the Vulkan ICD are copied: no library the runtime injects is in them, so none
# is shadowed. A node driver upgrade means a new NVIDIA_DRIVER and both checksums here.
# vulkan-tools' vulkaninfo is how on_card.py checks ray tracing before a render.
ARG BASE
FROM ${BASE} AS score

# Epic's tag pinned by the digest ghcr.io gave for it on 2026-11-24 (30 layers, 24.0 GB compressed; Ubuntu 22.04).
FROM ghcr.io/epicgames/unreal-engine:dev-slim-5.8.4@sha256:b3165cf745a8a30dfeea7074c2f223c213f4cbdf45ad921fb3a0c32c9336e897
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 SCORE_WORK=/work SCORE_CACHE=/cache \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display
ARG NVIDIA_DRIVER=595.91.07
ARG NVIDIA_REPO=https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64
ARG NVIDIA_GL_SHA256=225d6bbfd403426bd8b0f77693f921d8f2909a172b43864db36d3592c406649d
ARG NVIDIA_GPUCOMP_SHA256=a24b5a86f78ca9975e12dd727c8c5123ab10cbd0922ecb5ac3f682216e156170
ENV SCORE_NVIDIA_DRIVER=${NVIDIA_DRIVER}
RUN apt-get update \
 && apt-get install -y --no-install-recommends vulkan-tools ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
RUN set -e; mkdir /tmp/nv && cd /tmp/nv \
 && curl -fsSLo gl.deb ${NVIDIA_REPO}/libnvidia-gl_${NVIDIA_DRIVER}-1ubuntu1_amd64.deb \
 && curl -fsSLo gpucomp.deb ${NVIDIA_REPO}/libnvidia-gpucomp_${NVIDIA_DRIVER}-1ubuntu1_amd64.deb \
 && printf '%s  gl.deb\n%s  gpucomp.deb\n' ${NVIDIA_GL_SHA256} ${NVIDIA_GPUCOMP_SHA256} | sha256sum -c - \
 && dpkg-deb -x gl.deb x && dpkg-deb -x gpucomp.deb x \
 && cp -a x/usr/lib/x86_64-linux-gnu/*.so* /usr/lib/x86_64-linux-gnu/ \
 && mkdir -p /usr/share/glvnd/egl_vendor.d /etc/vulkan/icd.d \
 && cp x/usr/share/glvnd/egl_vendor.d/10_nvidia.json /usr/share/glvnd/egl_vendor.d/ \
 && cp x/usr/share/vulkan/icd.d/nvidia_icd.json /etc/vulkan/icd.d/nvidia_icd.json \
 && cd / && rm -rf /tmp/nv && ldconfig \
 && test -e /usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0 \
 && test -e /usr/lib/x86_64-linux-gnu/libnvidia-rtcore.so.${NVIDIA_DRIVER} \
 && cat /etc/vulkan/icd.d/nvidia_icd.json
COPY --from=score /opt/score /opt/score
COPY --from=score /usr/local/bin/score-job /usr/local/bin/score-job
# The layout on_card.py assumes, failing the build when it differs: the editor's command-line binary, the user, and the
# Movie Render Queue and Python Editor Script plugins (found wherever Epic keeps them, their paths printed).
RUN mkdir -p /work /cache \
 && test -x /home/ue4/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd \
 && id ue4 \
 && cat /home/ue4/UnrealEngine/Engine/Build/Build.version \
 && find /home/ue4/UnrealEngine/Engine/Plugins -name MovieRenderPipeline.uplugin | grep . \
 && find /home/ue4/UnrealEngine/Engine/Plugins -name PythonScriptPlugin.uplugin | grep . \
 && /opt/score/venv/bin/python -c "import boto3; print('runtime ok')"
WORKDIR /work
ENTRYPOINT ["score-job"]
