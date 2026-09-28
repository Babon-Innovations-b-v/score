#!/usr/bin/env bash
# Make the sounds the game makes itself (#35) into game/sound/made/.
#
#   bash tools/sound/run.sh                   # every sound
#   bash tools/sound/run.sh base_hum          # just these
#   bash tools/sound/run.sh --out /tmp/takes  # somewhere else, to listen first
#
# Plain python3, nothing to install.
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/made.py" "$@"
