# GarmentCode (maria-korosteleva/GarmentCode, MIT) as tools/props/cloud/characters_setup.sh's garment step installs it:
# the code at its pinned commit in /root/garmentcode and Python 3.10 with its pattern and box-mesh requirements in
# /root/envs/garment (requirements.txt, resolved and hashed), the paths tools/characters/maker/garment.py is run with
# (GARMENTCODE, GARMENTCODE_PYTHON). Plain geometry, no model and no card: it runs on a processor machine. Its
# simulation's Warp fork is non-commercial and is never installed. amd64 only: CGAL's Python bindings at the pinned
# version have no arm64 wheel, and an arm64 image would resolve an older CGAL than the one the chain ran with.
ARG BASE
FROM ${BASE}

ARG GARMENTCODE_COMMIT=d449629979028123a5c4dc9e732a2ec19b7fce31
ARG PYTHON=3.10.20

# cairosvg draws the pattern's panels through the system cairo.
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends git libcairo2 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /root/envs/garment-requirements.txt
RUN uv venv --quiet --python ${PYTHON} /root/envs/garment \
 && uv pip sync --quiet --python /root/envs/garment/bin/python --require-hashes /root/envs/garment-requirements.txt

RUN git init -q /root/garmentcode \
 && git -C /root/garmentcode fetch -q --depth 1 https://github.com/maria-korosteleva/GarmentCode "${GARMENTCODE_COMMIT}" \
 && git -C /root/garmentcode checkout -q FETCH_HEAD \
 && test "$(git -C /root/garmentcode rev-parse HEAD)" = "${GARMENTCODE_COMMIT}" \
 && rm -rf /root/garmentcode/.git \
 && /root/envs/garment/bin/python -c "import sys; sys.path.insert(0, '/root/garmentcode'); \
from pygarment.meshgen.boxmeshgen import BoxMesh; print('garment ok')"

ENV GARMENTCODE=/root/garmentcode GARMENTCODE_PYTHON=/root/envs/garment/bin/python
