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
# Vulkan: the cluster's GPU operator installs NVIDIA's full driver on the node, and the graphics capability mounts its
# Vulkan files into the container; vulkan-tools' vulkaninfo is how on_card.py checks ray tracing before a render.
ARG BASE
FROM ${BASE} AS score

FROM ghcr.io/epicgames/unreal-engine:dev-slim-5.8.4
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 SCORE_WORK=/work SCORE_CACHE=/cache \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display
RUN apt-get update \
 && apt-get install -y --no-install-recommends vulkan-tools ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY --from=score /opt/score /opt/score
COPY --from=score /usr/local/bin/score-job /usr/local/bin/score-job
RUN mkdir -p /work /cache \
 && test -x /home/ue4/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd \
 && id ue4 \
 && /opt/score/venv/bin/python -c "import boto3; print('runtime ok')"
WORKDIR /work
ENTRYPOINT ["score-job"]
