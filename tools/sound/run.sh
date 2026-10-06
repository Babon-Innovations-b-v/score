#!/usr/bin/env bash
# The game's sound tools (#35).
#
#   bash tools/sound/run.sh                   # make the sounds the game makes itself, into game/sound/made/
#   bash tools/sound/run.sh base_hum          # just these
#   bash tools/sound/run.sh --out /tmp/takes  # somewhere else, to listen first
#   bash tools/sound/run.sh pick hub          # build the hub's picking page (tools/sound/picker/)
#   bash tools/sound/run.sh apply DIR picks.json   # put the owner's picks into the game
#   bash tools/sound/run.sh needs             # the sounds the world's data names that no page asks for yet
#   bash tools/sound/run.sh loudness          # measure every game sound again (after made.py, say)
#
# Plain python3 and ffmpeg, nothing to install.
set -euo pipefail
here="$(dirname "${BASH_SOURCE[0]}")"
case "${1:-}" in
  pick|apply|needs) exec python3 "$here/picker/picker.py" "$@" ;;
  loudness) exec python3 "$here/loudness/loudness.py" manifest ;;
  *) exec python3 "$here/made.py" "$@" ;;
esac
