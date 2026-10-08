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
# No model runs on this PC (owner, 2026-10-03; local_models.py): every take's picture is drawn on
# a rented card (cloud/pictures.py), then all the takes go up as one batch (cloud/batch.py), which
# cuts them out and builds them there and finishes them here. For more than a few props, write the
# lists yourself and run those two once for the lot. Robot parts in the game are built in code
# (tools/kit); a generated part is only for laying beside its kit part.
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

WORK="${PROPS_WORK:-$HOME/.farm-factory-props/work}"
LISTS="$WORK/cloud/lists"
mkdir -p "$LISTS"
JOBS="$LISTS/$NAME-pictures.json"
MODELS="$LISTS/$NAME-models.txt"
made=()
for take in $(seq 1 "$TAKES"); do
  if [ "$TAKES" -eq 1 ]; then made+=("$NAME"); else made+=("$NAME-$take"); fi
done
# The lists the two cloud runners read: one picture and one model a take, seeded by the take.
"$PYTHON" -c '
import json, sys
jobs_path, models_path, pictures, sentence, form, *labels = sys.argv[1:]
jobs = [dict({"name": label, "sentence": sentence, "seed": take}, **({"form": form} if form else {}))
        for take, label in enumerate(labels, 1)]
open(jobs_path, "w").write(json.dumps(jobs))
open(models_path, "w").write("".join(f"{label} {pictures}/{label}.png\n" for label in labels))
' "$JOBS" "$MODELS" "$WORK/pictures" "$SENTENCE" "$FORM_NAME" "${made[@]}" || fail "writing the lists"

missing=0
for label in "${made[@]}"; do [ -f "$WORK/pictures/$label.png" ] || missing=1; done
if [ "$missing" -eq 1 ]; then
  printf '\n== the pictures, on a rented card\n'
  "$PYTHON" "$HERE/cloud/pictures.py" "$JOBS" --cards 1 || fail "making the pictures"
fi
printf '\n== the models, as one cloud batch\n'
"$PYTHON" "$HERE/cloud/batch.py" "$MODELS" --who "run.sh $NAME" || fail "making the models"

printf '\n== the page\n'
"$PYTHON" "$HERE/review.py" "${made[@]}" --out "$NAME" || fail "building the page"
