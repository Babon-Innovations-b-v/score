#!/usr/bin/env bash
# The newton image's command (installed as newton-run): a script and its arguments in the image's Newton Python, as the
# machine path runs a job naming newton_env.sh as its env (for example: newton-run
# score/stages/sim_body/inside/sim_body.py <job.json> <out.json>).
set -euo pipefail
exec /opt/newton/bin/python "$@"
