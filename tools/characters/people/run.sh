#!/usr/bin/env bash
# Build the person the game draws: the body, its skeleton, and the clips that move it.
#
#   bash tools/crew/run.sh                     # build the body from the clips already made
#   bash tools/crew/run.sh --clips             # generate whatever clips are missing first
#   bash tools/crew/run.sh --clips --again shouting   # make one clip again
#   bash tools/crew/run.sh --install           # copy the built body into the game
#
# The tool chain itself is built once per box: docs/bible.md, workflow/bootstrap.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$REPO/tools/crew"
PYTHON="${MOTION_PYTHON:-$HOME/.farm-factory-motion/env/bin/python}"
WORK="${MOTION_WORK:-$HOME/.farm-factory-motion/work}"
BUILT="$WORK/bodies/person_body.glb"
INSTALLED="$REPO/game/people/person_model/person_body.glb"

fail() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

[ -x "$PYTHON" ] || fail "no motion environment at $PYTHON; see workflow/bootstrap in docs/bible.md"

if [ "${1:-}" = "--install" ]; then
  [ -f "$BUILT" ] || fail "nothing built yet at $BUILT"
  cp "$BUILT" "$INSTALLED" || fail "copying the body into the game"
  printf 'installed %s\n' "$INSTALLED"
  exit 0
fi

if [ "${1:-}" = "--clips" ]; then
  shift
  printf '\n== the clips\n'
  "$PYTHON" "$HERE/clips.py" "$@" || fail "generating the clips"
fi

printf '\n== the body\n'
"$PYTHON" "$HERE/body.py" --report "$WORK/bodies/person_body.json" || fail "building the body"

printf '\nBuilt. Install it into the game with: bash tools/crew/run.sh --install\n'
