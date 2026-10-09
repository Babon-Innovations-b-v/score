# Pixal3D (raven38/pixal3d.cpp) as tools/props/cloud/machine_setup.sh installs it on a rented machine: upstream's
# prebuilt CUDA 12 trellis-cli at the release vendor/image-to-3dlab/scripts/bootstrap_pixal3d.py pins (its --prebuilt
# route, checked against the release's sha256), and the Python that runs the lab's generator and its cut-out through
# rembg with BiRefNet-lite. No weights: score-job fetches them into the node cache (models.json) and run.sh lays them
# where the lab looks. The lab's own code comes with the job's code bundle (/work/repo/vendor/image-to-3dlab).
# The prebuilt bundles its CUDA runtime and needs a driver of 575 or newer (CUDA 12.9).
ARG BASE
FROM ${BASE}

ARG PIXAL3D_RELEASE=v0.10.1-desktop-alpha
ARG PIXAL3D_TARBALL=trellis-cuda12-linux-x64.tar.gz
ARG PIXAL3D_SHA256=7d7a32fd56ff64c949232602f87ac2d5b0edc84b7bf8b5ce04f2ddf4c6723ac9
ARG PYTHON=3.12.13

RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends ca-certificates curl libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/pixal/requirements.txt
RUN uv venv --quiet --python ${PYTHON} /opt/pixal/venv \
 && uv pip sync --quiet --python /opt/pixal/venv/bin/python --require-hashes /opt/pixal/requirements.txt

RUN curl -fsSL -o /tmp/trellis.tar.gz \
      "https://github.com/raven38/pixal3d.cpp/releases/download/${PIXAL3D_RELEASE}/${PIXAL3D_TARBALL}" \
 && echo "${PIXAL3D_SHA256}  /tmp/trellis.tar.gz" | sha256sum -c - \
 && mkdir -p /opt/pixal/build \
 && tar -xzf /tmp/trellis.tar.gz -C /opt/pixal/build \
 && rm /tmp/trellis.tar.gz \
 && test -x /opt/pixal/build/trellis-cli

COPY --chmod=755 run.sh /usr/local/bin/pixal-run
# rembg's model folder; run.sh links BiRefNet-lite into it from the node cache.
ENV U2NET_HOME=/opt/pixal/u2net PYTHONUNBUFFERED=1
