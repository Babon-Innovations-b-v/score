#!/usr/bin/env bash
# Build the people the game draws: for each, the body, its skeleton, the clips that move it, and
# their two outfits, assembled, weighted and painted from their look kept in
# ~/.farm-factory-motion/look/<person>. Who they are is paths.PEOPLE.
#
#   bash tools/crew/run.sh                     # build everybody from the clips already made
#   bash tools/crew/run.sh nev oona            # build only these
#   bash tools/crew/run.sh --clips             # generate whatever clips are missing first
#   bash tools/crew/run.sh --clips --again sitting   # make one clip again, then build everybody
#   bash tools/crew/run.sh --install           # copy every built body into the game
#
# The tool chain itself is built once per box: docs/bible.md, workflow/bootstrap.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$REPO/tools/crew"
PYTHON="${MOTION_PYTHON:-$HOME/.farm-factory-motion/env/bin/python}"
WORK="${MOTION_WORK:-$HOME/.farm-factory-motion/work}"
MODELS="$REPO/game/people/person_model"

fail() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

[ -x "$PYTHON" ] || fail "no motion environment at $PYTHON; see workflow/bootstrap in docs/bible.md"
PEOPLE="$(cd "$HERE" && "$PYTHON" -c 'import paths; print(*paths.PEOPLE)')" || fail "reading who to build"

# One person's built body into the game. Godot writes a body's pictures out beside it on import
# and keeps them across a re-import, so the old ones go first or the new body wears them; and it
# skips importing a file it has imported before unchanged, so its record of the import goes too,
# or the pictures just cleared are never written again.
install_one() {
  local person="$1" built="$WORK/bodies/$1.glb" into="$MODELS/$1"
  [ -f "$built" ] || fail "nothing built yet for $person at $built"
  mkdir -p "$into"
  rm -f "$into/${person}"_*.png "$into/${person}"_*.png.import
  rm -f "$REPO/.godot/imported/${person}.glb-"* "$REPO/.godot/imported/${person}_"*.png-*
  cp "$built" "$into/$person.glb" || fail "copying $person into the game"
  printf 'installed %s\n' "$into/$person.glb"
}

if [ "${1:-}" = "--install" ]; then
  for person in $PEOPLE; do install_one "$person"; done
  printf 'Run bash tools/godot/run.sh check (it imports first) so Godot writes the pictures out.\n'
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

printf '\nBuilt. Install them into the game with: bash tools/crew/run.sh --install\n'
