#!/usr/bin/env bash
# Make a prop from a sentence on the locked route, and build the page that shows it beside its picture.
#
#   bash tools/props/run.sh locker "a tall narrow storage locker with a flat door"
#   bash tools/props/run.sh locker "..." 3          # three takes to choose between
#   bash tools/props/run.sh --form machine rover "..."  # a machine, not a plain solid prop
#   bash tools/props/run.sh --page locker bench     # rebuild the page for props already made
#   bash tools/props/run.sh --import bench --long 1.8 --budget furniture --keep-texture --keep-maps
#   bash tools/props/run.sh --part picker 2         # a robot part, from its brief in part_briefs.py
#
# Each take is a picture (picture.py) and a model built from it by Pixal3D with the clean finish
# (pixal.py, which holds the graphics card while it works). Robot parts in the game are built in
# code (tools/kit); a generated part is only for laying beside its kit part.
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

# Which wording says what the prop is made of. The default suits a crate or a desk; a machine
# needs "machine", because the default refuses the panels and sensors that make equipment read as
# equipment. Named here rather than left to whoever remembers to write a script.
FORM_NAME=""
if [ "${1:-}" = "--form" ]; then
  shift
  FORM_NAME="${1:-}"
  shift
  [ -n "$FORM_NAME" ] || fail "name a form: machine, space or glass"
fi

# A robot part is asked for by its id: the sentence and the form are its brief, the form
# `machine` unless the brief says otherwise.
if [ "${1:-}" = "--part" ]; then
  PART="${2:-}"
  [ -n "$PART" ] || fail "name the part to make"
  SENTENCE="$(cd "$HERE" && "$PYTHON" -c "import sys; from part_briefs import BRIEFS; print(BRIEFS[sys.argv[1]]['sentence'])" "$PART")" \
    || fail "no brief for the part $PART in part_briefs.py"
  FORM_NAME="$(cd "$HERE" && "$PYTHON" -c "import sys; from part_briefs import BRIEFS; print(BRIEFS[sys.argv[1]].get('form', 'machine'))" "$PART")"
  set -- "part-$PART" "$SENTENCE" "${3:-1}"
fi

NAME="${1:-}"
SENTENCE="${2:-}"
TAKES="${3:-1}"
[ -n "$NAME" ] && [ -n "$SENTENCE" ] || fail "usage: run.sh <name> \"<sentence>\" [takes]"

made=()
for take in $(seq 1 "$TAKES"); do
  if [ "$TAKES" -eq 1 ]; then label="$NAME"; else label="$NAME-$take"; fi
  printf '\n== %s: the picture\n' "$label"
  if [ -n "$FORM_NAME" ]; then
    "$PYTHON" "$HERE/picture.py" "$label" "$SENTENCE" --seed "$take" --form-named "$FORM_NAME" \
      || fail "making the picture for $label"
  else
    "$PYTHON" "$HERE/picture.py" "$label" "$SENTENCE" --seed "$take" || fail "making the picture for $label"
  fi
  printf '\n== %s: the model\n' "$label"
  "$PYTHON" "$HERE/pixal.py" "${PROPS_WORK:-$HOME/.farm-factory-props/work}/pictures/$label.png" "$label" \
    --who "run.sh $NAME" || fail "making the model for $label"
  made+=("$label")
done

printf '\n== the page\n'
"$PYTHON" "$HERE/review.py" "${made[@]}" --out "$NAME" || fail "building the page"
