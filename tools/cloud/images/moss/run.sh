#!/usr/bin/env bash
# The moss job's command: MOSS's weights linked where moss_generate.py loads them (/root/sfx/model), CLAP linked into
# a Hugging Face cache it finds offline by its repository id, then moss_generate.py from the job's code bundle on the
# share named (`moss-run <jobs.json> [<tag>]`). The takes land in /root/sfx/out, the job's output folder.
set -euo pipefail
ln -sfn "${SCORE_MODEL_MOSS_SOUNDEFFECT_V2:?the job must name the model moss-soundeffect-v2}" /root/sfx/model
mkdir -p /root/sfx/out /tmp/hf-hub
/opt/score/venv/bin/python /opt/score/runtime/hf_cache.py /work/repo/tools/cloud/images/moss/models.json \
  /tmp/hf-hub
cd /root/sfx
HF_HUB_CACHE=/tmp/hf-hub HF_HUB_OFFLINE=1 exec /root/venv/bin/python /work/repo/tools/props/cloud/moss_generate.py "$@"
