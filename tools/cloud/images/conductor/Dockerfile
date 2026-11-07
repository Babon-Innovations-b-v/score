# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-conductor: the conductor's own pod in the cluster (#76, the plan of 2026-11-07; tools/cloud/k8s/conductor/).
# FROM the runner image (the conductor's Python from uv.lock in /opt/score/env, ffmpeg, git, tzdata, the systemd-run
# shim), pinned by digest, plus what the VM's boot.sh installs for the conductor's own work: restic (the backups),
# scw (the secret reader and the runner's rents), kubectl (the submitter, the drive pods), uv (the checkout's .venv
# and the prop environment on the store volume), the system python3 (update.py, health_push.py), rsync, ssh, sqlite3,
# a compiler; each binary pinned by version and SHA-256 as boot.sh pins it. User score (uid 1100, HOME /home/score) as
# on the VM; the checkout, its .venv and the home live on the store volume, never in the image (no score code here:
# score-conductor-start clones it there once and update.py moves it to the cockpit's pin).
FROM rg.fr-par.scw.cloud/score-farm-factory/score-runner:1-679a8729e359@sha256:b0621a7c2b6a8517ec522c7414168283528e2b7b2d5cb79a336e241759c0c760

ARG RESTIC_VERSION=0.19.1
ARG RESTIC_SHA256=f415415624dcc452f2a02b8c33641791a8c6d6d3b65bbb3543fcf9a25151585c
ARG SCW_VERSION=2.65.1
ARG SCW_SHA256=b9ced8bc52c27baba76136a24e65a5e0abd53e9499edf02226513977d45da503
ARG KUBECTL_VERSION=1.37.1
ARG KUBECTL_SHA256=65691ff77eb6fa44c908b77a1082c9f092c3b9733b5cefabec0d1104890e21a8
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 sqlite3 bzip2 rsync openssh-client ca-certificates curl g++ \
      make cmake \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL -o /tmp/restic.bz2 "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" \
 && echo "${RESTIC_SHA256}  /tmp/restic.bz2" | sha256sum -c - \
 && bunzip2 -c /tmp/restic.bz2 > /usr/local/bin/restic && rm /tmp/restic.bz2 \
 && curl -fsSL -o /usr/local/bin/scw "https://github.com/scaleway/scaleway-cli/releases/download/v${SCW_VERSION}/scaleway-cli_${SCW_VERSION}_linux_amd64" \
 && echo "${SCW_SHA256}  /usr/local/bin/scw" | sha256sum -c - \
 && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && echo "${KUBECTL_SHA256}  /usr/local/bin/kubectl" | sha256sum -c - \
 && chmod 755 /usr/local/bin/restic /usr/local/bin/scw /usr/local/bin/kubectl \
 && useradd --uid 1100 --create-home --home-dir /home/score --shell /bin/bash score
COPY --chmod=755 secret-reader /usr/local/bin/score-secret-reader
COPY --chmod=755 start.sh /usr/local/bin/score-conductor-start
USER 1100
WORKDIR /home/score
