#!/usr/bin/env bash
# Make a prop from a sentence, and build the page that shows it beside its picture.
#
#   bash tools/props/run.sh locker "a tall narrow storage locker with a flat door"
#   bash tools/props/run.sh locker "..." 3          # three takes to choose between
#   bash tools/props/run.sh --page locker bench     # rebuild the page for props already made
#   bash tools/props/run.sh --import bench --long 1.8   # bring a made mesh into the game
#
# The tool chain itself is built once per box: docs/bible.md, workflow/bootstrap.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$REPO/tools/props"
PYTHON="${PROPS_PYTHON:-$HOME/.farm-factory-props/env/bin/python}"

fail() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

[ -x "$PYTHON" ] || fail "no prop environment at $PYTHON; see workflow/bootstrap in docs/bible.md"

if [ "${1:-}" = "--import" ]; then
  shift
  [ $# -ge 1 ] || fail "name the prop to import"
  "$PYTHON" "$HERE/import_prop.py" "$@" || fail "importing the prop"
  exit 0
fi

if [ "${1:-}" = "--page" ]; then
  shift
  [ $# -ge 1 ] || fail "name at least one prop to put on the page"
  "$PYTHON" "$HERE/review.py" "$@" || fail "building the page"
  exit 0
fi

NAME="${1:-}"
SENTENCE="${2:-}"
TAKES="${3:-1}"
[ -n "$NAME" ] && [ -n "$SENTENCE" ] || fail "usage: run.sh <name> \"<sentence>\" [takes]"

made=()
for take in $(seq 1 "$TAKES"); do
  if [ "$TAKES" -eq 1 ]; then label="$NAME"; else label="$NAME-$take"; fi
  printf '\n== %s: the picture\n' "$label"
  "$PYTHON" "$HERE/picture.py" "$label" "$SENTENCE" --seed "$take" || fail "making the picture for $label"
  printf '\n== %s: the mesh\n' "$label"
  "$PYTHON" "$HERE/mesh.py" "$label" \
    "${PROPS_WORK:-$HOME/.farm-factory-props/work}/pictures/$label.png" || fail "making the mesh for $label"
  made+=("$label")
done

printf '\n== the page\n'
"$PYTHON" "$HERE/review.py" "${made[@]}" --out "$NAME" || fail "building the page"
