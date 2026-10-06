#!/usr/bin/env bash
# The game's sound tools (#35).
#
#   bash tools/sound/run.sh                   # make the sounds the game makes itself, into game/sound/made/
#   bash tools/sound/run.sh base_hum          # just these
#   bash tools/sound/run.sh --out /tmp/takes  # somewhere else, to listen first
#   bash tools/sound/run.sh auto game         # choose and put in every sound MOSS made (tools/sound/picker/)
#   bash tools/sound/run.sh pick game         # build the page to listen and swap, putting nothing in
#   bash tools/sound/run.sh apply DIR [swaps.json]  # put the chosen takes and the owner's swaps in
#   bash tools/sound/run.sh needs             # any sound the game names with no prompts yet
#   bash tools/sound/run.sh loudness          # measure every game sound again (after made.py, say)
#
# The takes themselves are made on a rented card:
#   ~/.farm-factory-props/env/bin/python tools/props/cloud/moss_sound.py game --who <session>
#
# Plain python3 and ffmpeg, nothing to install.
set -euo pipefail
here="$(dirname "${BASH_SOURCE[0]}")"
case "${1:-}" in
  pick|auto|apply|needs) exec python3 "$here/picker/picker.py" "$@" ;;
  loudness) exec python3 "$here/loudness/loudness.py" manifest ;;
  *) exec python3 "$here/made.py" "$@" ;;
esac
