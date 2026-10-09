# MOSS-SoundEffect v2.0 (OpenMOSS, Apache-2.0 code and weights) and LAION's CLAP, as tools/props/cloud/moss_setup.sh
# installs them on a rented card: the MOSS-TTS code at moss_sound.py's MOSS_SHA in /root/sfx/MOSS-TTS (where
# moss_generate.py imports it from), Python 3.12 with MOSS's own pins and its torch-cu128 extra (torch 2.9.0+cu128),
# hf_xet and transformers (requirements.txt, resolved and hashed). No weights: score-job fetches MOSS and CLAP into the
# node cache (models.json) and run.sh links them where moss_generate.py looks.
ARG BASE
FROM ${BASE}

ARG MOSS_SHA=934d6826b084c46a0d033402174d5f8ac4ed2519
ARG PYTHON=3.12.13

RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /root/sfx/requirements.txt
RUN uv venv --quiet --python ${PYTHON} /root/venv \
 && uv pip sync --quiet --python /root/venv/bin/python --require-hashes --index-strategy unsafe-best-match \
      --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu128 \
      /root/sfx/requirements.txt

RUN git init -q /root/sfx/MOSS-TTS \
 && git -C /root/sfx/MOSS-TTS fetch -q --depth 1 https://github.com/OpenMOSS/MOSS-TTS "${MOSS_SHA}" \
 && git -C /root/sfx/MOSS-TTS checkout -q FETCH_HEAD \
 && test "$(git -C /root/sfx/MOSS-TTS rev-parse HEAD)" = "${MOSS_SHA}" \
 && rm -rf /root/sfx/MOSS-TTS/.git \
 && uv pip install --quiet --python /root/venv/bin/python --no-deps -e /root/sfx/MOSS-TTS/moss_soundeffect_v2 \
 && mkdir -p /root/sfx/out \
 && /root/venv/bin/python -c "import sys; sys.path.insert(0, '/root/sfx/MOSS-TTS'); \
from moss_soundeffect_v2 import MossSoundEffectPipeline; import transformers, soundfile; print('moss ok')"

COPY --chmod=755 run.sh /usr/local/bin/moss-run
ENV TORCHDYNAMO_DISABLE=1
