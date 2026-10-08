#!/usr/bin/env bash
# Build the people a world draws: for each, the body, its skeleton, the clips that move it, and
# their two outfits, assembled, weighted and painted from their look kept in
# ~/.farm-factory-motion/look/<person>. Who they are is paths.PEOPLE.
#
#   bash tools/characters/people/run.sh                     # build everybody from the clips already made
#   bash tools/characters/people/run.sh nev oona            # build only these
#   bash tools/characters/people/run.sh --clips             # generate whatever clips are missing first
#   bash tools/characters/people/run.sh --clips --again sitting   # make one clip again, then build everybody
#   bash tools/characters/people/run.sh --crowd             # bake the far crowd's animation texture
#
# The built bodies stay in $MOTION_WORK/bodies, where tools/characters/skel_usd.py reads them into a
# place's OpenUSD stage; the game 2099 installs them into its own tree with its own adapter.
#
# The tool chain itself is built once per box: docs/bible.md, workflow/bootstrap.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HERE="$REPO/tools/characters/people"
PYTHON="${MOTION_PYTHON:-$HOME/.farm-factory-motion/env/bin/python}"
WORK="${MOTION_WORK:-$HOME/.farm-factory-motion/work}"

fail() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

[ -x "$PYTHON" ] || fail "no motion environment at $PYTHON; see workflow/bootstrap in docs/bible.md"
PEOPLE="$(cd "$HERE" && "$PYTHON" -c 'import paths; print(*paths.PEOPLE)')" || fail "reading who to build"

if [ "${1:-}" = "--crowd" ]; then
  # The far crowd in the prologue's square (#112): one average man's far body with four clips
  # baked into textures the crowd's shader reads (crowd_vat.py).
  MOTION_PERSON=kit_m_avg CUDA_VISIBLE_DEVICES="" "$PYTHON" "$HERE/crowd_vat.py" \
    "$WORK/crowd_body" standing shifting clapping cheering || fail "baking the crowd"
  exit 0
fi

if [ "${1:-}" = "--clips" ]; then
  shift
  printf '\n== the clips\n'
  "$PYTHON" "$HERE/clips.py" "$@" || fail "generating the clips"
  set --
fi

for person in ${*:-$PEOPLE}; do
  printf '\n== %s\n' "$person"
  # The card is not needed to build a body, and a second program on it is how this box went down.
  MOTION_PERSON="$person" CUDA_VISIBLE_DEVICES="" "$PYTHON" "$HERE/body.py" \
    --report "$WORK/bodies/$person.json" || fail "building $person"
done

printf '\nBuilt into %s/bodies.\n' "$WORK"
